"""Homebrew query module for VersionTracker.

This module provides functions for querying Homebrew casks with advanced caching
to reduce network calls and improve performance. It implements batch operations,
rate limiting, and error handling for Homebrew-related operations.
"""

import json
import logging
import os
import re
import subprocess
import time
from typing import Any

from versiontracker.advanced_cache import (
    CacheLevel,
    CachePriority,
    get_cache,
)
from versiontracker.config import get_config
from versiontracker.exceptions import DataParsingError, HomebrewError, NetworkError
from versiontracker.ui import create_progress_bar
from versiontracker.utils import run_command

# Cache keys for different Homebrew operations
CACHE_KEY_ALL_CASKS = "homebrew:all_casks"
CACHE_KEY_CASK_PREFIX = "homebrew:cask:"
CACHE_KEY_SEARCH_PREFIX = "homebrew:search:"
CACHE_KEY_INFO_PREFIX = "homebrew:info:"

# Cache TTLs (in seconds)
CACHE_TTL_ALL_CASKS = 86400  # 1 day
CACHE_TTL_CASK_INFO = 43200  # 12 hours
CACHE_TTL_SEARCH = 86400  # 1 day

# Batch size for parallel operations
DEFAULT_BATCH_SIZE = 10


def is_homebrew_available() -> bool:
    """Check if Homebrew is available on the system.

    Returns:
        bool: True if Homebrew is available
    """
    try:
        # Try to run brew --version
        stdout, returncode = run_command("brew --version", timeout=5)
        return returncode == 0
    except Exception as e:
        logging.warning(f"Homebrew availability check failed: {e}")
        return False


def get_homebrew_path() -> str:
    """Get the path to the Homebrew executable.

    Returns:
        str: Path to Homebrew executable

    Raises:
        HomebrewError: If Homebrew is not found
    """
    try:
        # Check common locations
        common_paths = [
            "/usr/local/bin/brew",  # Intel Mac
            "/opt/homebrew/bin/brew",  # Apple Silicon Mac
            os.path.expanduser("~/.homebrew/bin/brew"),  # Custom install
        ]

        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path

        # Try to find using which
        stdout, returncode = run_command("which brew", timeout=5)
        if returncode == 0 and stdout.strip():
            return stdout.strip()

        raise HomebrewError("Homebrew not found in common locations")
    except Exception as e:
        logging.error(f"Failed to find Homebrew: {e}")
        raise HomebrewError(f"Homebrew not found: {e}") from e


def get_brew_command() -> str:
    """Return the Homebrew command path, using system detection and config if available.

    Returns:
        str: The path to the Homebrew executable
    Raises:
        HomebrewError: If Homebrew cannot be found
    """
    # Try config first
    config = get_config()
    brew_path = getattr(config, "brew_path", None)
    if isinstance(brew_path, str) and os.path.exists(brew_path):
        return str(brew_path)
    # Fallback to detection logic
    return get_homebrew_path()


def get_all_homebrew_casks() -> list[dict[str, Any]]:
    """Get a list of all available Homebrew casks with advanced caching.

    Returns:
        List[Dict[str, Any]]: List of cask data dictionaries

    Raises:
        HomebrewError: If there's an error retrieving casks
        NetworkError: If there's a network error
        DataParsingError: If there's an error parsing the response
    """
    cache = get_cache()

    # Try to get from cache first
    cached_casks = cache.get(CACHE_KEY_ALL_CASKS, ttl=CACHE_TTL_ALL_CASKS)
    if cached_casks is not None:
        return cached_casks  # type: ignore

    try:
        brew_path = get_brew_command()
        command = (
            f"{brew_path} info --json=v2 --cask $(ls $(brew --repository)/Library/Taps/homebrew/homebrew-cask/Casks/)"
        )

        # Show progress message
        progress_bar = create_progress_bar()
        print(progress_bar.color("blue")("Fetching all Homebrew casks (this may take a while)..."))

        # Execute command with timeout
        stdout, returncode = run_command(command, timeout=120)  # 2 minute timeout

        if returncode != 0:
            error_msg = f"Failed to retrieve Homebrew casks: {stdout}"
            logging.error(error_msg)
            raise HomebrewError(error_msg)

        try:
            # Parse JSON response
            data = json.loads(stdout)
            casks = data.get("casks", [])

            # Store in cache
            cache.put(
                CACHE_KEY_ALL_CASKS,
                casks,
                level=CacheLevel.ALL,
                priority=CachePriority.HIGH,
                source="homebrew",
            )

            return casks
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse Homebrew casks JSON: {e}"
            logging.error(error_msg)
            raise DataParsingError(error_msg) from e
    except subprocess.TimeoutExpired as e:
        error_msg = f"Timeout while retrieving Homebrew casks: {e}"
        logging.error(error_msg)
        raise NetworkError(error_msg) from e
    except Exception as e:
        error_msg = f"Error retrieving Homebrew casks: {e}"
        logging.error(error_msg)
        raise HomebrewError(error_msg) from e


def get_cask_info(cask_name: str) -> dict[str, Any]:
    """Get detailed information about a specific Homebrew cask.

    Args:
        cask_name: Name of the cask

    Returns:
        Dict[str, Any]: Cask information

    Raises:
        HomebrewError: If there's an error retrieving cask info
        NetworkError: If there's a network error
        DataParsingError: If there's an error parsing the response
    """
    cache = get_cache()
    cache_key = f"{CACHE_KEY_CASK_PREFIX}{cask_name}"

    # Try to get from cache first
    cached_info = cache.get(cache_key, ttl=CACHE_TTL_CASK_INFO)
    if cached_info is not None:
        return cached_info  # type: ignore

    try:
        brew_path = get_brew_command()
        command = f"{brew_path} info --json=v2 --cask {cask_name}"

        # Execute command with timeout
        stdout, returncode = run_command(command, timeout=30)

        if returncode != 0:
            error_msg = f"Failed to retrieve info for cask {cask_name}: {stdout}"
            logging.error(error_msg)
            raise HomebrewError(error_msg)

        try:
            # Parse JSON response
            data = json.loads(stdout)
            casks = data.get("casks", [])

            if not casks:
                error_msg = f"No information found for cask {cask_name}"
                logging.warning(error_msg)
                return {}

            cask_info = casks[0]

            # Store in cache
            cache.put(
                cache_key,
                cask_info,
                level=CacheLevel.ALL,
                priority=CachePriority.NORMAL,
                source="homebrew",
            )

            return cask_info
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse cask info JSON for {cask_name}: {e}"
            logging.error(error_msg)
            raise DataParsingError(error_msg) from e
    except subprocess.TimeoutExpired as e:
        error_msg = f"Timeout while retrieving info for cask {cask_name}: {e}"
        logging.error(error_msg)
        raise NetworkError(error_msg) from e
    except Exception as e:
        error_msg = f"Error retrieving info for cask {cask_name}: {e}"
        logging.error(error_msg)
        raise HomebrewError(error_msg) from e


def search_casks(query: str) -> list[dict[str, Any]]:
    """Search for Homebrew casks matching a query.

    Args:
        query: Search query

    Returns:
        List[Dict[str, Any]]: List of matching cask data dictionaries

    Raises:
        HomebrewError: If there's an error searching for casks
        NetworkError: If there's a network error
        DataParsingError: If there's an error parsing the response
    """
    cache = get_cache()
    cache_key = f"{CACHE_KEY_SEARCH_PREFIX}{query}"

    # Try to get from cache first
    cached_results = cache.get(cache_key, ttl=CACHE_TTL_SEARCH)
    if cached_results is not None:
        return cached_results  # type: ignore

    try:
        brew_path = get_brew_command()
        # Escape special characters in query
        safe_query = re.sub(r"([^\w\s-])", r"\\\1", query)
        command = f"{brew_path} search --cask --json=v2 {safe_query}"

        # Execute command with timeout
        stdout, returncode = run_command(command, timeout=30)

        if returncode != 0:
            error_msg = f"Failed to search for casks with query '{query}': {stdout}"
            logging.error(error_msg)
            raise HomebrewError(error_msg)

        try:
            # Parse JSON response
            data = json.loads(stdout)
            casks = data.get("casks", [])

            # Store in cache
            cache.put(
                cache_key,
                casks,
                level=CacheLevel.ALL,
                priority=CachePriority.NORMAL,
                source="homebrew",
            )

            return casks
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse search results JSON for '{query}': {e}"
            logging.error(error_msg)
            raise DataParsingError(error_msg) from e
    except subprocess.TimeoutExpired as e:
        error_msg = f"Timeout while searching for casks with query '{query}': {e}"
        logging.error(error_msg)
        raise NetworkError(error_msg) from e
    except Exception as e:
        error_msg = f"Error searching for casks with query '{query}': {e}"
        logging.error(error_msg)
        raise HomebrewError(error_msg) from e


def _filter_cached_casks(cask_names: list[str]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Filter cask names by checking cache first.
    
    Args:
        cask_names: List of cask names to filter
        
    Returns:
        Tuple of (cached_results, casks_to_fetch)
    """
    cache = get_cache()
    result: dict[str, dict[str, Any]] = {}
    casks_to_fetch: list[str] = []

    for cask_name in cask_names:
        cache_key = f"{CACHE_KEY_CASK_PREFIX}{cask_name}"
        cached_info = cache.get(cache_key, ttl=CACHE_TTL_CASK_INFO)

        if cached_info is not None:
            result[cask_name] = cached_info  # type: ignore
        else:
            casks_to_fetch.append(cask_name)
            
    return result, casks_to_fetch


def _fetch_cask_batch(batch: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch information for a single batch of casks.
    
    Args:
        batch: List of cask names in this batch
        
    Returns:
        Dict mapping cask names to their info
    """
    try:
        # Construct a command to get info for multiple casks at once
        brew_path = get_brew_command()
        casks_arg = " ".join(batch)
        command = f"{brew_path} info --json=v2 --cask {casks_arg}"

        # Execute command with timeout
        stdout, returncode = run_command(command, timeout=60)

        if returncode != 0:
            logging.warning(f"Failed to retrieve info for cask batch: {stdout}")
            return {}

        return _parse_and_cache_batch_response(stdout)
        
    except Exception as e:
        logging.warning(f"Error retrieving info for cask batch: {e}")
        return {}


def _parse_and_cache_batch_response(stdout: str) -> dict[str, dict[str, Any]]:
    """Parse JSON response and cache individual cask info.
    
    Args:
        stdout: JSON response from homebrew command
        
    Returns:
        Dict mapping cask names to their info
    """
    try:
        # Parse JSON response
        data = json.loads(stdout)
        casks = data.get("casks", [])
        result: dict[str, dict[str, Any]] = {}
        cache = get_cache()

        # Process each cask in the response
        for cask in casks:
            cask_name = cask.get("token")
            if cask_name:
                # Store in result
                result[cask_name] = cask

                # Store in cache
                cache_key = f"{CACHE_KEY_CASK_PREFIX}{cask_name}"
                cache.put(
                    cache_key,
                    cask,
                    level=CacheLevel.ALL,
                    priority=CachePriority.NORMAL,
                    source="homebrew",
                )
        
        return result
        
    except json.JSONDecodeError as e:
        logging.warning(f"Failed to parse cask info JSON for batch: {e}")
        return {}


def _apply_rate_limiting(config: Any, current_batch_index: int, total_casks: int, batch_size: int) -> None:
    """Apply rate limiting between batch requests.
    
    Args:
        config: Configuration object with rate limiting settings
        current_batch_index: Current batch starting index
        total_casks: Total number of casks being processed
        batch_size: Size of each batch
    """
    rate_limit = getattr(config, "api_rate_limit", 0.5)
    if rate_limit > 0 and current_batch_index + batch_size < total_casks:
        time.sleep(rate_limit)


def batch_get_cask_info(cask_names: list[str]) -> dict[str, dict[str, Any]]:
    """Get information for multiple casks in a batch operation.

    Args:
        cask_names: List of cask names

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary mapping cask names to their info

    Raises:
        HomebrewError: If there's an error retrieving cask info
    """
    if not cask_names:
        return {}

    # Filter by cache first
    result, casks_to_fetch = _filter_cached_casks(cask_names)

    # If all casks were in cache, return early
    if not casks_to_fetch:
        return result

    # Process remaining casks in batches
    config = get_config()
    batch_size = getattr(config, "homebrew_batch_size", DEFAULT_BATCH_SIZE)
    progress_bar = create_progress_bar()

    print(progress_bar.color("blue")(f"Fetching info for {len(casks_to_fetch)} casks..."))

    for i in range(0, len(casks_to_fetch), batch_size):
        batch = casks_to_fetch[i : i + batch_size]
        
        # Fetch batch and merge results
        batch_result = _fetch_cask_batch(batch)
        result.update(batch_result)

        # Apply rate limiting
        _apply_rate_limiting(config, i, len(casks_to_fetch), batch_size)

    return result


def get_installed_homebrew_casks() -> list[dict[str, Any]]:
    """Get a list of all installed Homebrew casks.

    Returns:
        List[Dict[str, Any]]: List of installed cask data dictionaries

    Raises:
        HomebrewError: If there's an error retrieving installed casks
        NetworkError: If there's a network error
        DataParsingError: If there's an error parsing the response
    """
    try:
        brew_path = get_brew_command()
        command = f"{brew_path} list --cask --json=v2"

        # Execute command with timeout
        stdout, returncode = run_command(command, timeout=30)

        if returncode != 0:
            error_msg = f"Failed to retrieve installed Homebrew casks: {stdout}"
            logging.error(error_msg)
            raise HomebrewError(error_msg)

        try:
            # Parse JSON response
            data = json.loads(stdout)
            casks = data.get("casks", [])

            return casks
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse installed casks JSON: {e}"
            logging.error(error_msg)
            raise DataParsingError(error_msg) from e
    except subprocess.TimeoutExpired as e:
        error_msg = f"Timeout while retrieving installed casks: {e}"
        logging.error(error_msg)
        raise NetworkError(error_msg) from e
    except Exception as e:
        error_msg = f"Error retrieving installed casks: {e}"
        logging.error(error_msg)
        raise HomebrewError(error_msg) from e


def clear_homebrew_cache() -> bool:
    """Clear all Homebrew-related cache.

    Returns:
        bool: True if cache was cleared successfully
    """
    cache = get_cache()
    return cache.clear(source="homebrew")


def get_outdated_homebrew_casks() -> list[dict[str, Any]]:
    """Get a list of outdated Homebrew casks.

    Returns:
        List[Dict[str, Any]]: List of outdated cask data dictionaries

    Raises:
        HomebrewError: If there's an error retrieving outdated casks
        NetworkError: If there's a network error
        DataParsingError: If there's an error parsing the response
    """
    try:
        brew_path = get_brew_command()
        command = f"{brew_path} outdated --cask --json=v2"

        # Execute command with timeout
        stdout, returncode = run_command(command, timeout=30)

        if returncode != 0:
            error_msg = f"Failed to retrieve outdated Homebrew casks: {stdout}"
            logging.error(error_msg)
            raise HomebrewError(error_msg)

        try:
            # Parse JSON response
            data = json.loads(stdout)
            casks = data.get("casks", [])

            return casks
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse outdated casks JSON: {e}"
            logging.error(error_msg)
            raise DataParsingError(error_msg) from e
    except subprocess.TimeoutExpired as e:
        error_msg = f"Timeout while retrieving outdated casks: {e}"
        logging.error(error_msg)
        raise NetworkError(error_msg) from e
    except Exception as e:
        error_msg = f"Error retrieving outdated casks: {e}"
        logging.error(error_msg)
        raise HomebrewError(error_msg) from e


def get_cask_version(cask_name: str) -> str:
    """Get the current version of a Homebrew cask.

    Args:
        cask_name: Name of the cask

    Returns:
        str: Current version of the cask

    Raises:
        HomebrewError: If there's an error retrieving the cask version
    """
    try:
        cask_info = get_cask_info(cask_name)
        return str(cask_info.get("version", ""))
    except Exception as e:
        error_msg = f"Error retrieving version for cask {cask_name}: {e}"
        logging.error(error_msg)
        raise HomebrewError(error_msg) from e


def get_caskroom_path() -> str:
    """Return the default Homebrew Caskroom path used for cask installations.

    Returns:
        str: The path to the Homebrew Caskroom directory
    """
    # Standard Homebrew Caskroom location
    paths = [
        "/usr/local/Caskroom",  # Intel Macs
        "/opt/homebrew/Caskroom",  # Apple Silicon Macs
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    # Fallback to the first path if none exist
    return paths[0]


def has_auto_updates(cask_name: str) -> bool:
    """Check if a Homebrew cask has auto-updates enabled.

    Args:
        cask_name: Name of the cask

    Returns:
        bool: True if the cask has auto-updates enabled, False otherwise
    """
    try:
        cask_info = get_cask_info(cask_name)

        # Check if auto_updates field exists and is True
        # The auto_updates field is typically in the cask metadata
        if cask_info.get("auto_updates"):
            return True

        # Also check in the caveats for auto-update mentions
        caveats = cask_info.get("caveats", "")
        if caveats and isinstance(caveats, str):
            auto_update_patterns = [
                "auto.?update",
                "automatically update",
                "self.?update",
                "sparkle",
                "update automatically",
            ]
            caveats_lower = caveats.lower()
            for pattern in auto_update_patterns:
                if re.search(pattern, caveats_lower):
                    return True

        return False
    except Exception as e:
        logging.debug(f"Error checking auto-updates for cask {cask_name}: {e}")
        return False


def get_casks_with_auto_updates(cask_names: list[str]) -> list[str]:
    """Get a list of cask names that have auto-updates enabled.

    Args:
        cask_names: List of cask names to check

    Returns:
        List[str]: List of cask names with auto-updates enabled
    """
    auto_update_casks = []

    for cask_name in cask_names:
        if has_auto_updates(cask_name):
            auto_update_casks.append(cask_name)

    return auto_update_casks
