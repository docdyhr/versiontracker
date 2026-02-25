"""Fuzzy matching and Homebrew search functionality."""

import logging
from typing import cast

from versiontracker.cache import read_cache, write_cache
from versiontracker.config import get_config
from versiontracker.utils import normalise_name, run_command
from versiontracker.version.fuzzy import partial_ratio

from .cache import RateLimiterProtocol, SimpleRateLimiter, _AdaptiveRateLimiter

# Module constants
BREW_PATH = "brew"  # Will be updated based on architecture detection


def search_brew_cask(search_term: str) -> list[str]:
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
        cmd = f'{brew_path} search --casks "{search_term_escaped}"'

        logging.debug("Running search command: %s", cmd)
        output, return_code = run_command(cmd, timeout=30)

        if return_code != 0:
            logging.warning("Homebrew search failed with code %d: %s", return_code, output)
            return []

        # Process the output
        results: list[str] = []
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


def _process_brew_search(app: tuple[str, str], rate_limiter: RateLimiterProtocol | None = None) -> str | None:
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
        brew_search = f'{brew_path} search --casks "{search_term_escaped}"'

        try:
            stdout, return_code = run_command(brew_search)
            if return_code == 0:
                response = [item for item in stdout.splitlines() if item and "==>" not in item]
            else:
                logging.warning("Homebrew search failed with code %d: %s", return_code, stdout)
                response = []
        except Exception as e:
            logging.warning("Command failed, falling back to cached search: %s", e)
            response = search_brew_cask(app[0])

        logging.debug("Brew search results: %s", response)

        # Check if any brew matches the app name
        for brew in response:
            if partial_ratio(app[0], brew) > 75:
                return app[0]

    except Exception as e:
        logging.error("Error searching for %s: %s", app[0], e)

    return None


def get_homebrew_cask_name(app_name: str, rate_limiter: RateLimiterProtocol | None = None) -> str | None:
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

    # Normalize app_name for consistent cache key
    import unicodedata

    normalized_app_name = unicodedata.normalize("NFKC", app_name).strip().lower()

    # Check the cache first
    cache_key = f"brew_cask_name_{normalized_app_name}"
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
    candidates: list[tuple[str, str, bool]], installable: bool | None = None
) -> list[tuple[str, str, bool]]:
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
    applications: list[tuple[str, str]], brews: list[str], strict_mode: bool = False
) -> list[tuple[str, str]]:
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


# --- Search helper functions ---


def _wait_for_rate_limit(rate_limiter: object) -> None:
    """Wait for rate limit if needed.

    Args:
        rate_limiter: Rate limiter object with wait() method
    """
    if rate_limiter is not None and isinstance(rate_limiter, SimpleRateLimiter | _AdaptiveRateLimiter):
        rate_limiter.wait()


def _normalize_and_validate_search_term(app_name: str) -> str | None:
    """Normalize app name and validate for search.

    Args:
        app_name: Application name to normalize

    Returns:
        str or None: Normalized search term or None if invalid
    """
    search_term = normalise_name(app_name)
    return search_term if search_term else None


def _find_matching_cask(search_results: list[str], app_name: str) -> str | None:
    """Find matching cask from search results using various strategies.

    Args:
        search_results: List of search results from brew
        app_name: Original application name

    Returns:
        str or None: Matching cask name or None if no match found
    """
    search_results_normalized = [normalise_name(r) for r in search_results]
    app_name_normalized = normalise_name(app_name)

    for i, result in enumerate(search_results_normalized):
        if not result:
            continue

        # Check for exact match
        if result == app_name_normalized:
            return search_results[i]

        # Check for substring match (app name in result)
        if app_name_normalized in result or result in app_name_normalized:
            return search_results[i]

        # Use fuzzy matching for less strict matches
        similarity = partial_ratio(app_name_normalized, result)
        if similarity >= 80:
            return search_results[i]

    return None


def _process_single_app_search(app_name: str, rate_limiter: object) -> str | None:
    """Process search for a single application.

    Args:
        app_name: Application name to search for
        rate_limiter: Rate limiter object

    Returns:
        str or None: Matching cask name or None if no match found
    """
    _wait_for_rate_limit(rate_limiter)

    try:
        search_term = _normalize_and_validate_search_term(app_name)
        if not search_term:
            return None

        search_results = search_brew_cask(search_term)

        if search_results:
            return _find_matching_cask(search_results, app_name)

    except Exception as e:
        logging.error("Error searching for %s: %s", app_name, e)

    return None


def _batch_process_brew_search(apps_batch: list[tuple[str, str]], rate_limiter: object) -> list[str]:
    """Process a batch of brew searches to reduce API calls.

    Args:
        apps_batch: List of (app_name, version) tuples
        rate_limiter: Rate limiter object with wait() method

    Returns:
        List of Homebrew cask names that could be used to install the applications
    """
    results: list[str] = []

    for app in apps_batch:
        app_name, _ = app
        match = _process_single_app_search(app_name, rate_limiter)
        if match:
            results.append(match)

    return results
