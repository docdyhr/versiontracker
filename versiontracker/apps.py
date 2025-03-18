"""Application management functionality for VersionTracker."""

import concurrent.futures
import logging
import subprocess
import time
from typing import Any, Dict, List, Optional, Set, Tuple, cast, Callable
import functools

from fuzzywuzzy.fuzz import partial_ratio  # type: ignore
from tqdm import tqdm  # type: ignore

from versiontracker.utils import (
    normalise_name,
    run_command,
    RateLimiter,
)

# Command constants
BREW_CMD = "brew list --cask"
BREW_SEARCH = "brew search --casks"

# Global cache for Homebrew search results
_brew_search_cache = {}


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
    
    # First, check if we can do a broader search to cover multiple apps
    # Get top-level domain names to use as search terms
    search_terms = set()
    app_map = {}
    
    for app in apps_batch:
        # Extract first word or first part of camelCase/kebab-case/snake_case name
        clean_name = app[0].strip().lower()
        first_part = clean_name.split()[0].split('-')[0].split('_')[0].split('.')[0]
        
        # If the first part is too short, use more of the name
        if len(first_part) <= 3 and len(clean_name) > 5:
            first_part = clean_name
            
        search_terms.add(first_part)
        
        # Map the search term back to the original apps
        if first_part not in app_map:
            app_map[first_part] = []
        app_map[first_part].append(app)
    
    # Do the batch searches
    for term in search_terms:
        # Wait if necessary to comply with the rate limit
        rate_limiter.wait()
        
        response = _cached_brew_search(term)
        
        # Check all applications that might match this search term
        for app in app_map.get(term, []):
            for brew in response:
                if partial_ratio(app[0], brew) > 75:
                    results.append(app[0])
                    break
    
    return results


def check_brew_install_candidates(
    data: List[Tuple[str, str]],
    rate_limit: int = 1,
    strict: bool = False,
    batch_size: int = 5,
) -> List[str]:
    """Return list of apps that can be installed with Homebrew.

    Args:
        data (List[Tuple[str, str]]): List of (app_name, version) tuples to check
        rate_limit (int, optional): Seconds to wait between API calls. Defaults to 1.
        strict (bool, optional): If True, only include apps that are not already
            installable via Homebrew
        batch_size (int, optional): Number of apps to process in each batch. Defaults to 5.

    Returns:
        List[str]: List of app names that can be installed with Homebrew
    """
    if strict:
        logging.info("Finding strictly new applications that can be installed with Homebrew...")
        print("Finding strictly new applications that can be installed with Homebrew...")
    else:
        logging.info("Filtering out installed brews from Homebrew casks...")
        print("Filtering out installed brews from Homebrew casks...")

    if not data:
        return []

    # Create a rate limiter with 1 call per rate_limit seconds
    rate_limiter = RateLimiter(calls_per_period=1, period=rate_limit)

    installers: Set[str] = set()
    total = len(data)

    # Get existing Homebrew cask names (lowercase for comparison)
    existing_brews = set()
    if strict:
        brew_casks_cmd = "brew search --casks"
        try:
            all_casks = run_command(brew_casks_cmd)
            existing_brews = {cask.lower() for cask in all_casks if cask.strip()}
            logging.debug(f"Found {len(existing_brews)} existing Homebrew casks")
        except Exception as e:
            logging.error(f"Error getting existing Homebrew casks: {e}")

    # Determine the optimal number of workers based on data size
    max_workers = min(4, (total + batch_size - 1) // batch_size)
    
    # For very small datasets, processing in sequence might be more efficient
    if total <= 5:
        max_workers = 1
        batch_size = total
    
    print(f"Processing {total} applications with {max_workers} workers...")

    # Organize data into batches for processing
    batches = [data[i:i + batch_size] for i in range(0, len(data), batch_size)]
    
    # Use ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit batch processing tasks
        future_to_batch = {
            executor.submit(_batch_process_brew_search, batch, rate_limiter): batch for batch in batches
        }

        # Process results as they complete
        for future in tqdm(
            concurrent.futures.as_completed(future_to_batch),
            total=len(future_to_batch),
            desc="Searching for Homebrew casks",
            unit="batch",
            ncols=80,
        ):
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
