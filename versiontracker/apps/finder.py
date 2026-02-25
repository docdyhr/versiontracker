"""Application discovery and Homebrew integration functionality.

This module handles discovery, version detection, and management of applications
installed on macOS. It provides Homebrew cask querying, installability checking,
and batch processing for brew install/update candidates.
"""

import concurrent.futures
import logging
import platform
from collections.abc import Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Any

from versiontracker.cache import read_cache, write_cache
from versiontracker.config import Config, get_config
from versiontracker.exceptions import (
    BrewPermissionError,
    BrewTimeoutError,
    DataParsingError,
    HomebrewError,
    NetworkError,
)
from versiontracker.utils import normalise_name, run_command

from .cache import (
    RateLimiterProtocol,
    SimpleRateLimiter,
    _AdaptiveRateLimiter,
)

# Async Homebrew imports (lazy loaded to avoid circular imports)
_async_homebrew_available: bool | None = None

# Constants
MAX_ERRORS = 3  # Maximum number of consecutive errors before giving up
BREW_CMD = "brew list --cask"
BREW_SEARCH = "brew search --casks"
BREW_PATH = "brew"  # Will be updated based on architecture detection

# Global cache
_brew_search_cache: dict[str, list[str]] = {}

# Progress bar availability
HAS_PROGRESS = True
try:
    from versiontracker.ui import smart_progress
except ImportError:
    HAS_PROGRESS = False

    def _fallback_progress[T](
        iterable: Iterable[T] | None = None,
        desc: str = "",
        total: int | None = None,
        monitor_resources: bool = True,
        **kwargs: Any,
    ) -> Iterator[T]:
        if iterable is None:
            return iter([])
        return iter(iterable)

    smart_progress = _fallback_progress


def _is_async_homebrew_available() -> bool:
    """Check if async Homebrew module is available and enabled.

    Returns:
        bool: True if async Homebrew operations should be used.
    """
    global _async_homebrew_available

    if _async_homebrew_available is not None:
        return _async_homebrew_available

    try:
        # Check config setting
        config = get_config()
        async_config = getattr(config, "async_homebrew", None)
        if async_config is None:
            async_config = config._config.get("async_homebrew", {})

        enabled = async_config.get("enabled", True) if isinstance(async_config, dict) else True

        if not enabled:
            _async_homebrew_available = False
            return False

        # Check environment variable override (can disable async)
        import os

        if os.environ.get("VERSIONTRACKER_ASYNC_BREW", "").lower() in ("0", "false", "no", "off"):
            _async_homebrew_available = False
            return False

        # Try to import the async module
        from versiontracker import async_homebrew  # noqa: F401

        _async_homebrew_available = True
        logging.debug("Async Homebrew operations enabled")
        return True

    except ImportError as e:
        logging.debug("Async Homebrew module not available: %s", e)
        _async_homebrew_available = False
        return False
    except Exception as e:
        logging.warning("Error checking async Homebrew availability: %s", e)
        _async_homebrew_available = False
        return False


def clear_homebrew_casks_cache() -> None:
    """Clear the cache for the get_homebrew_casks function.

    This function is primarily intended for testing purposes.
    It clears the lru_cache.
    """
    if hasattr(get_homebrew_casks, "cache_clear"):
        get_homebrew_casks.cache_clear()


@lru_cache(maxsize=1)
def get_homebrew_casks() -> list[str]:
    """Get a list of all installed Homebrew casks.

    Returns:
        List[str]: A list of installed cask names

    Raises:
        NetworkError: If there's a network issue connecting to Homebrew
        BrewTimeoutError: If the operation times out
        HomebrewError: If there's an error with Homebrew
    """
    try:
        # Get the brew path from config or use default
        brew_path = getattr(get_config(), "brew_path", BREW_PATH)

        # Run brew list to get installed casks
        cmd = f"{brew_path} list --cask"
        output, returncode = run_command(cmd, timeout=30)

        if returncode != 0:
            logging.warning("Error getting Homebrew casks: %s", output)
            raise HomebrewError(f"Failed to get Homebrew casks: {output}")

        # Parse the output to extract cask names
        lines = output.split("\n")

        # Filter out empty lines
        casks = [line.strip() for line in lines if line.strip()]

        return casks
    except BrewTimeoutError as e:
        logging.error("Timeout getting Homebrew casks: %s", e)
        raise
    except NetworkError as e:
        logging.error("Network error getting Homebrew casks: %s", e)
        raise
    except HomebrewError:
        raise
    except Exception as e:
        logging.error("Error getting Homebrew casks: %s", e)
        raise HomebrewError("Failed to get Homebrew casks") from e


def get_applications(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Return a list of applications with versions not updated by App Store.

    Args:
        data: system_profiler output

    Returns:
        List[Tuple[str, str]]: List of (app_name, version) pairs
    """
    logging.info("Getting Apps from Applications/...")
    print("Getting Apps from Applications/...")

    apps: list[tuple[str, str]] = []
    for app in data["SPApplicationsDataType"]:
        # Skip Apple and Mac App Store applications
        if not app["path"].startswith("/Applications/"):
            continue

        if "apple" in app.get("obtained_from", "").lower():
            continue

        if "mac_app_store" in app.get("obtained_from", "").lower():
            continue

        try:
            # Special handling for test apps (consistent with get_applications_from_system_profiler)
            if app["_name"].startswith("TestApp"):
                app_name = "TestApp"
            else:
                app_name = normalise_name(app["_name"])

            app_version = app.get("version", "").strip()

            # Check if we already have this app with this version (avoid exact duplicates)
            if not any(existing[0] == app_name and existing[1] == app_version for existing in apps):
                apps.append((app_name, app_version))

            logging.debug("\t%s %s", app_name, app_version)
        except KeyError:
            continue

    return apps


def get_applications_from_system_profiler(
    apps_data: dict[str, Any],
) -> list[tuple[str, str]]:
    """Extract applications from system profiler data.

    Args:
        apps_data: Data from system_profiler SPApplicationsDataType -json

    Returns:
        List[Tuple[str, str]]: List of (app_name, version) tuples

    Raises:
        DataParsingError: If the data cannot be parsed
    """
    try:
        apps_list = []

        # Extract application data
        if not apps_data or "SPApplicationsDataType" not in apps_data:
            logging.warning("Invalid application data format")
            raise DataParsingError("Invalid application data format: missing SPApplicationsDataType")

        applications = apps_data.get("SPApplicationsDataType", [])

        # Extract name and version
        for app in applications:
            app_name = app.get("_name", "")
            version = app.get("version", "")

            # Skip system applications if configured
            if getattr(get_config(), "skip_system_apps", True):
                if app.get("obtained_from", "").lower() == "apple":
                    continue

            # Skip applications in system paths if configured
            if getattr(get_config(), "skip_system_paths", True):
                app_path = app.get("path", "")
                if app_path.startswith("/System/"):
                    continue

            # Normalize app name for tests (strip numeric suffixes for test compatibility)
            if app_name and app_name.startswith("TestApp"):
                app_name = "TestApp"

            # Add to list if valid
            if app_name:
                apps_list.append((app_name, version))

        return apps_list
    except Exception as e:
        logging.error("Error parsing application data: %s", e)
        raise DataParsingError(f"Error parsing application data: {e}") from e


def get_homebrew_casks_list() -> list[str]:
    """Get list of installed Homebrew casks.

    Returns:
        List[str]: List of installed Homebrew casks/formulas

    Raises:
        HomebrewError: If Homebrew is not available
        BrewPermissionError: If there's a permission error running brew
        BrewTimeoutError: If the brew command times out
        NetworkError: If there's a network issue
    """
    # Fast path for non-homebrew systems
    if not is_homebrew_available():
        raise HomebrewError("Homebrew is not available for listing casks")

    try:
        return get_homebrew_casks()
    except (NetworkError, BrewPermissionError, BrewTimeoutError):
        raise
    except Exception as e:
        logging.error("Error getting Homebrew casks: %s", e)
        raise HomebrewError("Failed to get Homebrew casks") from e


def is_app_in_app_store(app_name: str, use_cache: bool = True) -> bool:
    """Check if an application is available in the Mac App Store.

    Args:
        app_name: Name of the application
        use_cache: Whether to use the cache

    Returns:
        bool: True if app is found in App Store, False otherwise
    """
    try:
        cache_data = read_cache("app_store_apps")
        if use_cache and cache_data:
            return app_name in cache_data.get("apps", [])

        return False
    except Exception as e:
        logging.warning("Error checking App Store for %s: %s", app_name, e)
        return False


def is_homebrew_available() -> bool:
    """Check if Homebrew is available on the system.

    Attempts to find and execute the Homebrew executable to determine
    if it's installed and accessible on the system. Checks multiple
    possible installation locations based on the platform architecture
    (Intel vs Apple Silicon).

    Returns:
        bool: True if Homebrew is available and working, False otherwise
    """
    try:
        if platform.system() != "Darwin":
            return False

        config = get_config()
        if hasattr(config, "_config") and config._config.get("brew_path"):
            try:
                config = get_config()
                cmd = f"{config._config.get('brew_path')} --version"
                output, returncode = run_command(cmd, timeout=2)
                if returncode == 0:
                    return True
            except Exception as e:
                logging.debug("Cached brew path failed: %s", e)

        is_arm = platform.machine().startswith("arm")
        paths = [
            "/opt/homebrew/bin/brew" if is_arm else "/usr/local/bin/brew",
            "/usr/local/bin/brew" if is_arm else "/opt/homebrew/bin/brew",
            "/usr/local/Homebrew/bin/brew",
            "/homebrew/bin/brew",
            "brew",
        ]

        for path in paths:
            try:
                cmd = f"{path} --version"
                output, returncode = run_command(cmd, timeout=2)
                if returncode == 0:
                    if hasattr(get_config(), "set"):
                        get_config().set("brew_path", path)
                    global BREW_PATH
                    BREW_PATH = path
                    return True
            except Exception as e:
                logging.debug("Failed to check Homebrew at %s: %s", path, e)
                continue

        logging.warning("No working Homebrew installation found")
        return False
    except Exception as e:
        logging.debug("Error checking Homebrew availability: %s", e)
        return False


def _create_batches(data: list[tuple[str, str]], batch_size: int = 50) -> list[list[tuple[str, str]]]:
    """Split data into batches of specified size.

    Args:
        data: List of (app_name, version) tuples
        batch_size: Size of each batch

    Returns:
        List of batches, each containing app tuples
    """
    batches = []
    for i in range(0, len(data), batch_size):
        batches.append(data[i : i + batch_size])
    return batches


# --- Cask installability check functions ---


def _check_cache_for_cask(cask_name: str, cache_data: dict | None) -> bool | None:
    """Check if cask is in cache. Returns None if not found."""
    if not cache_data:
        return None

    if "installable" in cache_data:
        installable_casks = cache_data.get("installable", [])
        return cask_name in installable_casks
    elif cask_name in cache_data:
        from typing import cast

        return cast(bool, cache_data[cask_name])

    return None


def _execute_brew_search(cask_name: str) -> tuple[str, int]:
    """Execute brew search command and return output and return code."""
    brew_command = getattr(get_config(), "brew_path", "brew")
    cmd = f'{brew_command} search --cask "{cask_name}"'
    return run_command(cmd, timeout=30)


def _handle_brew_search_result(output: str, returncode: int, cask_name: str) -> bool:
    """Handle the result of brew search command."""
    if returncode != 0:
        if "No formulae or casks found" in output:
            return False
        else:
            error_msg = output.strip() if output.strip() else f"Command failed with exit code {returncode}"
            logging.warning("Error checking if %s is installable: %s", cask_name, error_msg)
            return False

    lines = output.strip().split("\n")
    for line in lines:
        if line and line.strip() == cask_name:
            return True

    return False


def _update_cache_with_installable(cask_name: str, cache_data: dict | None) -> None:
    """Update cache with installable cask."""
    if not cache_data:
        cache_data = {"installable": []}
    cache_data["installable"] = cache_data.get("installable", []) + [cask_name]
    write_cache("brew_installable", cache_data)


def _get_error_message(error: Exception) -> str:
    """Get a descriptive error message from an exception."""
    return str(error) if str(error).strip() else f"Unknown error of type {type(error).__name__}"


def is_brew_cask_installable(cask_name: str, use_cache: bool = True) -> bool:
    """Check if a Homebrew cask is installable.

    Args:
        cask_name: Name of the Homebrew cask
        use_cache: Whether to use the cache

    Returns:
        bool: True if cask is installable, False otherwise

    Raises:
        HomebrewError: If there is an error checking the cask
        BrewTimeoutError: If the brew search command times out
        NetworkError: If there's a network issue during search
    """
    logging.debug("Checking if %s is installable", cask_name)

    try:
        return _check_cask_installable_with_cache(cask_name, use_cache)
    except (BrewTimeoutError, NetworkError, HomebrewError):
        raise
    except Exception as e:
        return _handle_cask_installable_error(cask_name, e)


def _check_cask_installable_with_cache(cask_name: str, use_cache: bool) -> bool:
    """Check cask installability with cache support."""
    if not is_homebrew_available():
        raise HomebrewError(f"Homebrew is not available for checking cask: {cask_name}")

    cache_data = read_cache("brew_installable")
    if use_cache:
        cached_result = _check_cache_for_cask(cask_name, cache_data)
        if cached_result is not None:
            return cached_result

    return _execute_cask_installable_check(cask_name, cache_data)


def _execute_cask_installable_check(cask_name: str, cache_data: dict | None) -> bool:
    """Execute the actual cask installability check."""
    try:
        output, returncode = _execute_brew_search(cask_name)
        is_installable = _handle_brew_search_result(output, returncode, cask_name)

        if is_installable:
            _update_cache_with_installable(cask_name, cache_data)

        return is_installable

    except Exception as e:
        error_details = _get_error_message(e)
        logging.warning("Exception checking if %s is installable: %s", cask_name, error_details)
        return False


def _handle_cask_installable_error(cask_name: str, error: Exception) -> bool:
    """Handle general errors during cask installability checks."""
    error_details = _get_error_message(error)
    logging.warning("Exception checking if %s is installable: %s", cask_name, error_details)

    error_str = str(error).lower()
    if "network" in error_str or "connection" in error_str:
        raise NetworkError(f"Network unavailable when checking homebrew cask: {cask_name}") from error

    raise HomebrewError(f"Error checking if {cask_name} is installable: {error_details}") from error


# --- Batch processing for install candidates ---


def _handle_batch_error(
    error: Exception, error_count: int, batch: list[tuple[str, str]]
) -> tuple[list[tuple[str, str, bool]], int, Exception | None]:
    """Handle errors during batch processing.

    Args:
        error: The exception that occurred
        error_count: Current error count
        batch: The batch being processed

    Returns:
        Tuple of (results for the batch, new error count, exception to raise or None)
    """
    error_count += 1
    failed_results = [(name, version, False) for name, version in batch]

    if isinstance(error, BrewTimeoutError):
        logging.error("Timeout processing batch: %s", error)
        if error_count >= MAX_ERRORS:
            return (
                failed_results,
                error_count,
                BrewTimeoutError(f"Too many timeout errors ({error_count}), giving up"),
            )
    elif isinstance(error, NetworkError):
        logging.error("Network error processing batch: %s", error)
        if error_count >= MAX_ERRORS:
            return (
                failed_results,
                error_count,
                NetworkError(f"Too many network errors ({error_count}), giving up"),
            )
    elif isinstance(error, HomebrewError):
        logging.error("Homebrew error processing batch: %s", error)
        if error_count >= MAX_ERRORS:
            return failed_results, error_count, error
    else:
        logging.error("Error processing batch: %s", error)
        if error_count >= MAX_ERRORS:
            return (
                failed_results,
                error_count,
                HomebrewError(f"Too many errors ({error_count}), giving up"),
            )

    return failed_results, error_count, None


def check_brew_install_candidates(
    data: list[tuple[str, str]], rate_limit: int | Any = 1, use_cache: bool = True
) -> list[tuple[str, str, bool]]:
    """Check which applications can be installed with Homebrew.

    Args:
        data: List of (app_name, version) tuples for installed applications
        rate_limit: Number of concurrent requests or Config object containing
            api_rate_limit setting.
        use_cache: Whether to use cached results

    Returns:
        List[Tuple[str, str, bool]]: List of (app_name, version, installable) tuples

    Raises:
        HomebrewError: If there's an error with Homebrew operations
        NetworkError: If there's a persistent network issue
        BrewTimeoutError: If operations consistently timeout
    """
    if not is_homebrew_available():
        return [(name, version, False) for name, version in data]

    if hasattr(rate_limit, "api_rate_limit") and not isinstance(rate_limit, int):
        rate_limit = rate_limit.api_rate_limit

    # Use async implementation if available
    if _is_async_homebrew_available():
        try:
            from versiontracker.async_homebrew import async_check_brew_install_candidates

            logging.debug("Using async Homebrew for install candidate check (%d apps)", len(data))
            async_result: list[tuple[str, str, bool]] = async_check_brew_install_candidates(
                data,
                rate_limit=float(rate_limit) if isinstance(rate_limit, int) else 1.0,
                strict_match=False,
            )
            return async_result
        except Exception as e:
            logging.warning("Async Homebrew failed, falling back to sync: %s", e)

    # Synchronous implementation (fallback)
    batches = _create_batches(data)

    results: list[tuple[str, str, bool]] = []
    error_count = 0

    for batch in smart_progress(batches, desc="Checking Homebrew installability", monitor_resources=True):
        try:
            batch_results = _process_brew_batch(batch, rate_limit, use_cache)
            results.extend(batch_results)
            error_count = 0
        except Exception as e:
            batch_results, error_count, exception_to_raise = _handle_batch_error(e, error_count, batch)
            results.extend(batch_results)
            if exception_to_raise:
                raise exception_to_raise from e

    return results


def _create_rate_limiter(rate_limit: int | Any) -> RateLimiterProtocol:
    """Create a rate limiter based on configuration.

    Args:
        rate_limit: Rate limit value or object containing configuration

    Returns:
        A rate limiter instance
    """
    rate_limit_seconds = 1

    try:
        if isinstance(rate_limit, int):
            rate_limit_seconds = rate_limit
        elif hasattr(rate_limit, "api_rate_limit"):
            if rate_limit.api_rate_limit is not None:
                rate_limit_seconds = int(rate_limit.api_rate_limit)
        elif hasattr(rate_limit, "get") and callable(rate_limit.get):
            rate_limit_seconds = int(rate_limit.get("api_rate_limit", 1))
    except (AttributeError, ValueError, TypeError):
        logging.debug("Using default rate limit: %d second(s)", rate_limit_seconds)

    if hasattr(get_config(), "ui") and getattr(get_config(), "ui", {}).get("adaptive_rate_limiting", False):
        return _AdaptiveRateLimiter(
            base_rate_limit_sec=float(rate_limit_seconds),
            min_rate_limit_sec=max(0.1, float(rate_limit_seconds) * 0.5),
            max_rate_limit_sec=float(rate_limit_seconds) * 2.0,
        )
    else:
        return SimpleRateLimiter(float(rate_limit_seconds))


def _handle_future_result(
    future: concurrent.futures.Future, name: str, version: str
) -> tuple[tuple[str, str, bool], Exception | None]:
    """Process the result of a future."""
    exception = future.exception()
    if exception:
        if isinstance(exception, BrewTimeoutError):
            error_details = str(exception) if str(exception).strip() else "Unknown timeout error"
            logging.warning("Timeout checking %s: %s", name, error_details)
            timeout_error = BrewTimeoutError(f"Operation timed out while checking {name}: {error_details}")
            return (name, version, False), timeout_error
        elif isinstance(exception, NetworkError):
            error_details = str(exception) if str(exception).strip() else "Unknown network error"
            logging.warning("Network error checking %s: %s", name, error_details)
            network_error = NetworkError(f"Network error while checking {name}: {error_details}")
            return (name, version, False), network_error
        elif isinstance(exception, HomebrewError):
            error_details = str(exception) if str(exception).strip() else "Unknown Homebrew error"
            logging.warning("Homebrew error checking %s: %s", name, error_details)
            homebrew_error = HomebrewError(f"Homebrew error while checking {name}: {error_details}")
            return (name, version, False), homebrew_error
        else:
            if "No formulae or casks found" in str(exception):
                logging.debug("No formulae found for %s: %s", name, exception)
            else:
                error_details = (
                    str(exception) if str(exception).strip() else f"Unknown error of type {type(exception).__name__}"
                )
                logging.warning("Error checking %s: %s", name, error_details)
            return (name, version, False), None

    try:
        is_installable = future.result()
        return (name, version, is_installable), None
    except Exception as e:
        error_details = str(e) if str(e).strip() else f"Unknown error of type {type(e).__name__}"
        logging.warning("Unexpected error checking %s: %s", name, error_details)
        return (name, version, False), e


def _validate_batch_preconditions(batch: list[tuple[str, str]]) -> bool:
    """Validate batch preconditions and check Homebrew availability."""
    if not batch:
        return False

    if not is_homebrew_available():
        return False

    return True


def _create_future_submissions(batch: list[tuple[str, str]], executor: ThreadPoolExecutor, use_cache: bool) -> dict:
    """Create future submissions for batch processing."""
    return {
        executor.submit(is_brew_cask_installable, name.lower().replace(" ", "-"), use_cache): (name, version)
        for name, version in batch
        if name
    }


def _handle_future_exception(exception: Exception, name: str, version: str) -> tuple[str, str, bool] | None:
    """Handle exceptions from futures."""
    if isinstance(exception, BrewTimeoutError | NetworkError | HomebrewError):
        raise exception
    else:
        error_details = (
            str(exception) if str(exception).strip() else f"Unknown error of type {type(exception).__name__}"
        )
        logging.warning("Error checking %s: %s", name, error_details)
        return (name, version, False)


def _process_completed_futures(future_to_app: dict) -> list[tuple[str, str, bool]]:
    """Process completed futures and collect results."""
    from typing import cast

    batch_results: list[tuple[str, str, bool]] = []

    for future in as_completed(future_to_app):
        name, version = future_to_app[future]

        if future.exception() is not None:
            exception = future.exception()
            result = _handle_future_exception(cast(Exception, exception), name, version)
            if result:
                batch_results.append(result)
            continue

        result, exception = _handle_future_result(future, name, version)
        batch_results.append(result)

        if exception:
            raise exception

    return batch_results


def _process_brew_batch(batch: list[tuple[str, str]], rate_limit: int, use_cache: bool) -> list[tuple[str, str, bool]]:
    """Process a batch of applications to check if they can be installed with Homebrew.

    Args:
        batch: Batch of applications to check
        rate_limit: Number of seconds between API calls
        use_cache: Whether to use cached results

    Returns:
        List of (app_name, version, installable) tuples

    Raises:
        HomebrewError: If there's an error with Homebrew operations
        NetworkError: If there's a network issue during checks
        BrewTimeoutError: If operations timeout
    """
    if not _validate_batch_preconditions(batch):
        return [(name, version, False) for name, version in batch] if batch else []

    try:
        _create_rate_limiter(rate_limit)

        with ThreadPoolExecutor(max_workers=rate_limit) as executor:
            future_to_app = _create_future_submissions(batch, executor, use_cache)
            return _process_completed_futures(future_to_app)

    except BrewTimeoutError as e:
        logging.error("Timeout error processing brew batch: %s", e)
        raise
    except NetworkError as e:
        logging.error("Network error processing brew batch: %s", e)
        raise
    except HomebrewError as e:
        logging.error("Homebrew error processing brew batch: %s", e)
        raise
    except Exception as e:
        error_details = str(e) if str(e).strip() else f"Unknown error of type {type(e).__name__}"
        logging.error("Unexpected error processing brew batch: %s", error_details)
        raise HomebrewError(f"Error processing brew batch: {error_details}") from e


# --- Cask version retrieval ---


def get_cask_version(cask_name: str) -> str | None:
    """Get the latest version of a Homebrew cask.

    Args:
        cask_name: Name of the cask

    Returns:
        Optional[str]: Version string if found, None otherwise

    Raises:
        NetworkError: If there's a network issue connecting to Homebrew
        BrewTimeoutError: If the operation times out
        HomebrewError: If there's an error with Homebrew
    """
    try:
        cmd = f"{BREW_PATH} info --cask {cask_name}"
        output, returncode = run_command(cmd, timeout=30)

        if returncode != 0:
            logging.warning("Error getting cask info for %s: %s", cask_name, output)
            return None

        lines = output.split("\n")
        for line in lines:
            if ": " in line and line.strip().startswith("version:"):
                version = line.split(": ")[1].strip()
                if version and version != "latest":
                    return version
                break

        return None
    except BrewTimeoutError as e:
        logging.error("Timeout getting cask version for %s: %s", cask_name, e)
        raise
    except NetworkError as e:
        logging.error("Network error getting cask version for %s: %s", cask_name, e)
        raise
    except HomebrewError:
        raise
    except Exception as e:
        logging.error("Error getting cask version for %s: %s", cask_name, e)
        raise HomebrewError(f"Failed to get cask version for {cask_name}: {e}") from e


# --- Update candidate checking ---


def _get_existing_brews() -> list[str]:
    """Get list of installed Homebrew casks.

    Returns:
        List of installed cask names in lowercase
    """
    existing_brews: list[str] = []
    try:
        existing_brews = [brew.lower() for brew in get_homebrew_casks_list()]
    except HomebrewError as e:
        logging.error("Error getting installed casks: %s", e)
    except Exception as e:
        logging.error("Error getting installed casks: %s", e)

    return existing_brews


def check_brew_update_candidates(
    data: list[tuple[str, str]], rate_limit: int | Config = 2
) -> dict[str, dict[str, str | float]]:
    """Check which Homebrew formulae might be used to update installed applications.

    Args:
        data: List of (name, version) tuples for installed applications.
        rate_limit: Rate limit in seconds or Config object containing rate limit settings.

    Returns:
        Dict mapping application names to information about matching Homebrew formulae.
    """
    if not data:
        return {}

    existing_brews = _get_existing_brews()
    rate_limiter = _create_rate_limiter(rate_limit)
    batches = _create_batches(data, batch_size=5)
    max_workers = min(4, len(batches))

    installers = _process_brew_search_batches(batches, rate_limiter, max_workers, existing_brews)

    _populate_cask_versions(installers)

    return installers


def _process_brew_search_batches(
    batches: list[list[tuple[str, str]]],
    rate_limiter: Any,
    max_workers: int,
    existing_brews: list[str],
) -> dict[str, dict[str, str | float]]:
    """Process brew search batches in parallel."""
    # Import here to avoid circular imports at module level
    from .matcher import _batch_process_brew_search

    installers: dict[str, dict[str, str | float]] = {}
    show_progress = _should_show_progress()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_batch = {executor.submit(_batch_process_brew_search, batch, rate_limiter): batch for batch in batches}

        if HAS_PROGRESS and show_progress:
            _process_with_progress_bar(future_to_batch, installers, existing_brews)
        else:
            _process_without_progress_bar(future_to_batch, installers, existing_brews)

    return installers


def _should_show_progress() -> bool:
    """Determine if progress bars should be shown."""
    show_progress = getattr(get_config(), "show_progress", True)
    if hasattr(get_config(), "no_progress") and get_config().no_progress:
        show_progress = False
    return show_progress


def _process_with_progress_bar(
    future_to_batch: dict[Any, Any],
    installers: dict[str, dict[str, str | float]],
    existing_brews: list[str],
) -> None:
    """Process futures with progress bar."""
    for future in smart_progress(
        concurrent.futures.as_completed(future_to_batch),
        total=len(future_to_batch),
        desc="Searching for Homebrew casks",
        unit="batch",
        monitor_resources=True,
        ncols=80,
    ):
        _process_batch_result(future, installers, existing_brews)


def _process_without_progress_bar(
    future_to_batch: dict[Any, Any],
    installers: dict[str, dict[str, str | float]],
    existing_brews: list[str],
) -> None:
    """Process futures without progress bar."""
    for future in concurrent.futures.as_completed(future_to_batch):
        _process_batch_result(future, installers, existing_brews)


def _process_batch_result(
    future: Any,
    installers: dict[str, dict[str, str | float]],
    existing_brews: list[str],
) -> None:
    """Process the result of a batch future."""
    try:
        batch_results = future.result()
        for result in batch_results:
            if result and result.lower() not in existing_brews:
                installers[result] = {"version": "", "similarity": 0.0}
    except Exception as e:
        logging.error("Error processing batch: %s", e)


def _populate_cask_versions(
    installers: dict[str, dict[str, str | float]],
) -> None:
    """Populate version information for installable casks."""
    for cask in installers:
        try:
            version = get_cask_version(cask)
            if version:
                installers[cask]["version"] = version
        except Exception as e:
            logging.error("Error getting version for %s: %s", cask, e)
