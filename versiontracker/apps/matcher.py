"""Fuzzy matching and Homebrew search functionality."""

# Import partial_ratio directly from the main version.py file (not the version/ submodule)
import importlib.util
import logging
import os
from typing import List, Optional, Tuple, cast

# Import from main version module (partial_ratio wasn't moved to submodules)
from versiontracker.cache import read_cache, write_cache
from versiontracker.config import get_config
from versiontracker.utils import normalise_name, run_command

# Import the main version.py file directly (not the version/ package)
_version_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "version.py")
_spec = importlib.util.spec_from_file_location("versiontracker_version_main", _version_py_path)
if _spec is not None and _spec.loader is not None:
    _version_main = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_version_main)
    partial_ratio = _version_main.partial_ratio
else:
    raise ImportError("Could not load version.py module")


from .cache import RateLimiterProtocol

# Module constants
BREW_PATH = "brew"  # Will be updated based on architecture detection


def search_brew_cask(search_term: str) -> List[str]:
    """Search for a cask on Homebrew.

    Args:
        search_term: Term to search for

    Returns:
        List of matching cask names
    """
    search_term = search_term.strip()
    if not search_term:
        return []

    try:
        # Import here to avoid circular imports
        from .finder import is_homebrew_available

        # Make sure homebrew is available first
        if not is_homebrew_available():
            logging.warning("Homebrew is not available, skipping search")
            return []

        # Get brew path from config or use default
        brew_path = getattr(get_config(), "brew_path", BREW_PATH)

        # Escape search term for shell safety
        search_term_escaped = search_term.replace('"', '\\"').replace("'", "\\'")
        cmd = '%s search --casks "%s"' % (brew_path, search_term_escaped)

        logging.debug("Running search command: %s", cmd)
        output, return_code = run_command(cmd, timeout=30)

        if return_code != 0:
            logging.warning("Homebrew search failed with code %d: %s", return_code, output)
            return []

        # Process the output
        results: List[str] = []
        for line in output.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("==>"):
                # Extract the cask name (first word)
                cask_name = line.split()[0] if " " in line else line
                results.append(cask_name)

        return results
    except Exception as e:
        logging.error("Error searching Homebrew: %s", e)
        return []


def _process_brew_search(app: Tuple[str, str], rate_limiter: Optional[RateLimiterProtocol] = None) -> Optional[str]:
    """Process a single brew search for an application.

    Args:
        app: The application (name, version) to search for
        rate_limiter: Rate limiter for API calls

    Returns:
        Optional[str]: The application name if installable with Homebrew, None otherwise
    """
    try:
        # Wait for rate limit if needed
        if rate_limiter is not None:
            rate_limiter.wait()

        # Normalize the app name for search
        search_term = normalise_name(app[0])
        if not search_term:
            return None

        # Get brew path and run search
        brew_path = getattr(get_config(), "brew_path", BREW_PATH)
        search_term_escaped = search_term.replace('"', '\\"')
        brew_search = '%s search --casks "%s"' % (brew_path, search_term_escaped)

        try:
            stdout, return_code = run_command(brew_search)
            if return_code == 0:
                response = [item for item in stdout.splitlines() if item and "==>" not in item]
            else:
                # Log with % formatting
                logging.warning("Homebrew search failed with code %d: %s", return_code, stdout)
                response = []
        except Exception as e:
            # Log with % formatting
            logging.warning("Command failed, falling back to cached search: %s", e)
            response = search_brew_cask(app[0])

        # Log with % formatting
        logging.debug("Brew search results: %s", response)

        # Check if any brew matches the app name
        for brew in response:
            if partial_ratio(app[0], brew) > 75:
                return app[0]

    except Exception as e:
        # Log with % formatting
        logging.error("Error searching for %s: %s", app[0], e)

    return None


def get_homebrew_cask_name(app_name: str, rate_limiter: Optional[RateLimiterProtocol] = None) -> Optional[str]:
    """Get the Homebrew cask name for an application.

    Searches Homebrew for a cask matching the given application name,
    using a rate limiter to prevent API abuse.

    Args:
        app_name: Name of the application to search for
        rate_limiter: Optional rate limiter for API calls

    Returns:
        Homebrew cask name if found, None if no match
    """
    if not app_name:
        return None

    # Check the cache first
    cache_key = f"brew_cask_name_{app_name.lower()}"
    cached_result = read_cache(cache_key)
    if cached_result is not None:
        # The cache stores the result as a dict with a "cask_name" key
        return cast(str, cached_result.get("cask_name"))

    # No cache hit, search for the cask
    result = _process_brew_search((app_name, ""), rate_limiter)

    # Cache the result (even if None)
    write_cache(cache_key, {"cask_name": result})

    return result


def filter_brew_candidates(
    candidates: List[Tuple[str, str, bool]], installable: Optional[bool] = None
) -> List[Tuple[str, str, bool]]:
    """Filter brew candidates by installability.

    Args:
        candidates: List of (name, version, installable) tuples
        installable: If True, only return installable candidates.
                    If False, only return non-installable candidates.
                    If None, return all candidates.

    Returns:
        Filtered list of (name, version, installable) tuples
    """
    if installable is None:
        return candidates

    return [candidate for candidate in candidates if candidate[2] == installable]


def filter_out_brews(
    applications: List[Tuple[str, str]], brews: List[str], strict_mode: bool = False
) -> List[Tuple[str, str]]:
    """Filter out applications that are already managed by Homebrew.

    Args:
        applications: List of (app_name, version) tuples
        brews: List of installed Homebrew casks
        strict_mode: If True, be more strict in filtering.
                    Defaults to False.

    Returns:
        List of application tuples that are not managed by Homebrew
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
