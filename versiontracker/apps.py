"""Application management functionality for VersionTracker."""

import concurrent.futures
import logging
import subprocess
import time
from typing import Any, Dict, List, Optional, Set, Tuple, cast

from fuzzywuzzy.fuzz import partial_ratio  # type: ignore
from tqdm import tqdm  # type: ignore

from versiontracker.utils import (
    normalise_name,
    run_command,
)

# Command constants
BREW_CMD = "brew list --cask"
BREW_SEARCH = "brew search --casks"


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
                candidates.append(app[0])
                break

    # Add apps that don't match any installed brews to search list
    search_list = [app for app in applications if app[0] not in candidates]

    # Sort the search list alphabetically
    search_list.sort(key=lambda item: item[0].casefold())
    return search_list


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

        brew_search = f"{BREW_SEARCH} '{app[0]}'"
        logging.debug(f"Searching for {app[0]}...")

        response = run_command(brew_search)

        # Filter out header lines
        response = [item for item in response if item and "==>" not in item]

        logging.debug("\tBREW SEARCH: %s", response)

        # Check if any brew matches the app name
        for brew in response:
            if partial_ratio(app[0], brew) > 75:
                return app[0]

    except Exception as e:
        logging.error(f"Error searching for {app[0]}: {e}")

    return None


def check_brew_install_candidates(
    data: List[Tuple[str, str]],
    rate_limit: int = 1,
    strict: bool = False,
) -> List[str]:
    """Return list of apps that can be installed with Homebrew.

    Args:
        data (List[Tuple[str, str]]): List of (app_name, version) tuples to check
        rate_limit (int, optional): Seconds to wait between API calls. Defaults to 1.
        strict (bool, optional): If True, only include apps that are not already
            installable via Homebrew

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
    class RateLimiter:
        def __init__(self, calls_per_period, period):
            self.calls_per_period = calls_per_period
            self.period = period
            self.last_call_time = time.time()

        def wait(self):
            elapsed_time = time.time() - self.last_call_time
            if elapsed_time < self.period:
                time.sleep(self.period - elapsed_time)
            self.last_call_time = time.time()

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

    # Determine the optimal number of workers
    # Use less workers for small data to avoid overhead
    max_workers = min(10, (total + 1) // 2) if total > 5 else 1

    print(f"Processing {total} applications with {max_workers} workers...")

    # Use ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_app = {
            executor.submit(_process_brew_search, app, rate_limiter): app for app in data
        }

        # Process results as they complete
        for future in tqdm(
            concurrent.futures.as_completed(future_to_app),
            total=len(future_to_app),
            desc="Searching for Homebrew casks",
            unit="app",
            ncols=80,
        ):
            app = future_to_app[future]
            try:
                result = future.result()
                if result and (not strict or result.lower() not in existing_brews):
                    installers.add(result)
            except Exception as e:
                logging.error(f"Error processing {app[0]}: {e}")

    # Convert set to sorted list
    installers_list = list(installers)
    installers_list.sort(key=str.casefold)
    return installers_list
