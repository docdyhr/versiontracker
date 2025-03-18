"""Application management functionality for VersionTracker."""

import concurrent.futures
import logging
import subprocess
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast
import functools

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    # Simple fallback if tqdm is not available
    def tqdm(iterable, **kwargs):
        return iterable
    HAS_TQDM = False

# Import fuzzy matching
try:
    from rapidfuzz.fuzz import partial_ratio
    USE_RAPIDFUZZ = True
except ImportError:
    from fuzzywuzzy.fuzz import partial_ratio
    USE_RAPIDFUZZ = False

from versiontracker.config import config
from versiontracker.utils import (
    normalise_name,
    run_command,
    RateLimiter,
)

# Command constants
BREW_CMD = "brew list --cask"
BREW_SEARCH = "brew search --casks"

# Global cache for Homebrew search results
_brew_search_cache: Dict[str, List[str]] = {}


def get_applications(data: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Return a list of applications with versions not updated by App Store.

    Args:
        data: system_profiler output

    Returns:
        List[Tuple[str, str]]: List of (app_name, version) pairs
    """
    logging.info("Getting Apps from Applications/...")
    print("Getting Apps from Applications/...")

    apps: List[Tuple[str, str]] = []
    for app in data["SPApplicationsDataType"]:
        # Skip Apple and Mac App Store applications
        if not app["path"].startswith("/Applications/"):
            continue

        if "apple" in app.get("obtained_from", "").lower():
            continue

        if "mac_app_store" in app.get("obtained_from", "").lower():
            continue

        try:
            app_name = normalise_name(app["_name"])
            app_version = app.get("version", "").strip()

            # Check if we already have this app (avoid duplicates)
            if not any(existing[0] == app_name for existing in apps):
                apps.append((app_name, app_version))

            logging.debug("\t%s %s", app_name, app_version)
        except KeyError:
            continue

    return apps


def get_homebrew_casks() -> List[str]:
    """Return a list of installed Homebrew casks.

    Returns:
        List[str]: List of installed cask names
    """
    logging.info("Getting installed Homebrew casks...")

    try:
        return run_command(BREW_CMD)
    except RuntimeError as e:
        logging.error(f"Failed to get Homebrew casks: {e}")
        return []


def filter_out_brews(
    applications: List[Tuple[str, str]], brews: List[str], strict_mode: bool = False
) -> List[Tuple[str, str]]:
    """Filter out applications that are already managed by Homebrew.

    Args:
        applications (List[Tuple[str, str]]): List of (app_name, version) tuples
        brews (List[str]): List of installed Homebrew casks
        strict_mode (bool, optional): If True, be more strict in filtering.
                                     Defaults to False.

    Returns:
        List[Tuple[str, str]]: Filtered list of applications
    """
    logging.info("Getting installable casks from Homebrew...")
    print("Getting installable casks from Homebrew...")

    candidates = []
    search_list = []

    # Find apps that match installed brews with fuzzy matching
    for app in applications:
        app_name = app[0].strip().lower()
        for brew in brews:
            # If the app name matches a brew with 75% or higher similarity
            if partial_ratio(app_name, brew) > 75:
                # Skip this app if in strict mode
                if strict_mode:
                    break
                # Otherwise add as a candidate
                candidates.append((app_name, app[1]))
                break
        else:
            # If no match was found, add to the search list
            search_list.append(app)

    return search_list


# Use functools.lru_cache to cache search results
@functools.lru_cache(maxsize=1024)
def _cached_brew_search(search_term: str) -> List[str]:
    """Cached version of brew search command.
    
    Args:
        search_term (str): Application name to search for
        
    Returns:
        List[str]: List of search results
    """
    brew_search = f"{BREW_SEARCH} '{search_term}'"
    try:
        response = run_command(brew_search)
        # Filter out header lines
        response = [item for item in response if item and "==>" not in item]
        return response
    except Exception as e:
        logging.error(f"Error searching for {search_term}: {e}")
        return []


def _process_brew_search(app: Tuple[str, str], rate_limiter: Any) -> Optional[str]:
    """Process a single brew search for an application.

    Args:
        app (Tuple[str, str]): The application (name, version) to search for
        rate_limiter (Any): Rate limiter for API calls

    Returns:
        Optional[str]: The application name if it can be installed with Homebrew, None otherwise
    """
    try:
        # Wait if necessary to comply with the rate limit
        rate_limiter.wait()

        # Use the cached search function instead of running directly
        brew_search = f"{BREW_SEARCH} '{app[0]}'"
        logging.debug(f"Searching for {app[0]}...")
        
        # For direct testing compatibility
        try:
            response = run_command(brew_search)
            # Filter out header lines
            response = [item for item in response if item and "==>" not in item]
        except Exception:
            # Fall back to cached function if direct call fails
            response = _cached_brew_search(app[0])
            
        logging.debug("\tBREW SEARCH: %s", response)

        # Check if any brew matches the app name
        for brew in response:
            if partial_ratio(app[0], brew) > 75:
                return app[0]

    except Exception as e:
        logging.error(f"Error searching for {app[0]}: {e}")

    return None


def _batch_process_brew_search(apps_batch: List[Tuple[str, str]], rate_limiter: Any) -> List[str]:
    """Process a batch of brew searches to reduce API calls.
    
    Args:
        apps_batch (List[Tuple[str, str]]): Batch of applications to search for
        rate_limiter (Any): Rate limiter for API calls
        
    Returns:
        List[str]: List of application names that can be installed with Homebrew
    """
    results = []
    
    for app in apps_batch:
        app_name, _ = app
        
        # Wait for rate limit if needed
        if hasattr(rate_limiter, "wait"):
            rate_limiter.wait()
        
        try:
            # Normalize the app name
            search_term = normalise_name(app_name)
            
            # Skip empty search terms
            if not search_term:
                continue
                
            # Search for the app with cached function
            search_results = _cached_brew_search(search_term)
            
            # Process results if found
            if search_results:
                # Normalize names for better matching
                search_results_normalized = [normalise_name(r) for r in search_results]
                app_name_normalized = normalise_name(app_name)
                
                for i, result in enumerate(search_results_normalized):
                    if not result:
                        continue
                        
                    # Check for exact match
                    if result == app_name_normalized:
                        # Found exact match
                        return_value = search_results[i]
                        results.append(return_value)
                        break
                        
                    # Check for substring match (app name in result)
                    if app_name_normalized in result or result in app_name_normalized:
                        return_value = search_results[i]
                        results.append(return_value)
                        break
                        
                    # Use fuzzy matching for less strict matches
                    if USE_RAPIDFUZZ:
                        similarity = partial_ratio(app_name_normalized, result)
                    else:
                        similarity = partial_ratio(app_name_normalized, result)
                        
                    if similarity >= 80:
                        return_value = search_results[i]
                        results.append(return_value)
                        break
                
        except Exception as e:
            logging.error(f"Error searching for {app_name}: {e}")
            
    return results


def check_brew_install_candidates(
    data: List[Tuple[str, str]],
    rate_limit: Union[int, Any] = 1,
    strict: bool = False,
    batch_size: int = 5,
) -> List[str]:
    """Return list of apps that can be installed with Homebrew.

    Args:
        data (List[Tuple[str, str]]): List of (app_name, version) tuples to check
        rate_limit (Union[int, Any], optional): Seconds to wait between API calls or config object. Defaults to 1.
        strict (bool, optional): If True, only include apps that are not already
            installable via Homebrew
        batch_size (int, optional): Number of apps to process in each batch. Defaults to 5.

    Returns:
        List[str]: List of app names that can be installed with Homebrew
    """
    if not data:
        return []

    # Get installed casks for checking against strict filtering
    existing_brews = []
    if strict:
        try:
            brew_list_output = run_command(f"{config.brew_path} list --cask")
            existing_brews = [
                brew.strip().lower() for brew in brew_list_output.strip().split("\n") if brew.strip()
            ]
        except Exception as e:
            logging.error(f"Error getting installed casks: {e}")

    # Set up rate limiter
    rate_limit_seconds = 1  # Default
    if isinstance(rate_limit, int):
        rate_limit_seconds = rate_limit
    else:
        # Try to get from config object
        try:
            if hasattr(rate_limit, "rate_limit"):
                rate_limit_seconds = cast(int, rate_limit.rate_limit)
            elif hasattr(rate_limit, "get"):
                rate_limit_seconds = int(rate_limit.get("rate_limit", 1))
        except (ValueError, TypeError, AttributeError):
            # If conversion fails, use default
            rate_limit_seconds = 1

    # Initialize rate limiter with the converted rate limit
    class RateLimiter:
        def __init__(self, rate_limit_sec: int):
            self.rate_limit_sec = rate_limit_sec
            self.last_called = 0

        def wait(self):
            """Wait if necessary to respect rate limit."""
            now = time.time()
            if self.last_called > 0:
                elapsed = now - self.last_called
                if elapsed < self.rate_limit_sec:
                    time.sleep(self.rate_limit_sec - elapsed)
            self.last_called = time.time()

    rate_limiter = RateLimiter(rate_limit_seconds)

    # Clear cache if needed (optimization)
    _cached_brew_search.cache_clear()

    # Create batches for parallel processing
    batches = [data[i : i + batch_size] for i in range(0, len(data), batch_size)]
    max_workers = min(4, len(batches))  # Don't create too many workers

    # Set to track installable apps (avoid duplicates)
    installers = set()
    
    # Check if progress bars should be shown
    show_progress = getattr(config, "show_progress", True)
    if hasattr(config, "no_progress") and config.no_progress:
        show_progress = False

    # Use ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit batch processing tasks
        future_to_batch = {
            executor.submit(_batch_process_brew_search, batch, rate_limiter): batch for batch in batches
        }

        # Process results as they complete
        if HAS_TQDM and show_progress:
            # Use progress bar
            for future in tqdm(
                concurrent.futures.as_completed(future_to_batch),
                total=len(future_to_batch),
                desc="Searching for Homebrew casks",
                unit="batch",
                ncols=80,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
            ):
                batch = future_to_batch[future]
                try:
                    batch_results = future.result()
                    for result in batch_results:
                        if result and (not strict or result.lower() not in existing_brews):
                            installers.add(result)
                except Exception as e:
                    logging.error(f"Error processing batch: {e}")
        else:
            # Process without progress bar
            for future in concurrent.futures.as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    batch_results = future.result()
                    for result in batch_results:
                        if result and (not strict or result.lower() not in existing_brews):
                            installers.add(result)
                except Exception as e:
                    logging.error(f"Error processing batch: {e}")

    # Convert set to sorted list
    installers_list = list(installers)
    installers_list.sort(key=str.casefold)
    return installers_list
