"""Asynchronous Homebrew operations for VersionTracker.

This module provides asynchronous implementations of Homebrew operations,
using asyncio for improved performance and resource utilization.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from aiohttp import ClientError, ClientResponseError, ClientTimeout

from versiontracker.async_network import AsyncBatchProcessor, async_to_sync, fetch_json
from versiontracker.cache import read_cache, write_cache
from versiontracker.exceptions import (
    HomebrewError,
    NetworkError,
    TimeoutError,
)
from versiontracker.homebrew import (
    is_homebrew_available,
)
from versiontracker.utils import get_user_agent

# Constants
HOMEBREW_API_BASE = "https://formulae.brew.sh/api/cask"
HOMEBREW_SEARCH_BASE = "https://formulae.brew.sh/api/search"
DEFAULT_TIMEOUT = 10  # seconds
CACHE_EXPIRY = 86400  # 1 day in seconds


async def fetch_cask_info(
    cask_name: str, timeout: int = DEFAULT_TIMEOUT, use_cache: bool = True
) -> Dict[str, Any]:
    """Fetch information about a Homebrew cask asynchronously.

    Args:
        cask_name: Name of the cask
        timeout: Request timeout in seconds
        use_cache: Whether to use cached results

    Returns:
        Dict[str, Any]: Cask information

    Raises:
        NetworkError: If there's a network issue
        TimeoutError: If the request times out
    """
    url = f"{HOMEBREW_API_BASE}/{cask_name}.json"
    cache_key = f"cask_info_{cask_name}"

    return await fetch_json(url, cache_key, timeout, use_cache)


async def search_casks(
    query: str, timeout: int = DEFAULT_TIMEOUT, use_cache: bool = True
) -> List[Dict[str, Any]]:
    """Search for Homebrew casks asynchronously.

    Args:
        query: Search query
        timeout: Request timeout in seconds
        use_cache: Whether to use cached results

    Returns:
        List[Dict[str, Any]]: List of matching casks

    Raises:
        NetworkError: If there's a network issue
        TimeoutError: If the request times out
    """
    url = f"{HOMEBREW_SEARCH_BASE}.json?q={query}"
    cache_key = f"cask_search_{query}"

    # Try to get from cache first
    if use_cache:
        cached_data = read_cache(cache_key, CACHE_EXPIRY)
        if cached_data:
            logging.debug(f"Using cached search results for {query}")
            return cached_data

    # Configure timeout
    timeout_obj = ClientTimeout(total=timeout)

    try:
        # Create a user agent string
        headers = {"User-Agent": get_user_agent()}

        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                # Filter to only return casks (not formulas)
                casks = [item for item in data if "cask" in item.get("token", "")]

                # Cache the result
                if use_cache:
                    write_cache(cache_key, casks)

                return casks

    except asyncio.TimeoutError as e:
        logging.error(f"Search request to {url} timed out after {timeout}s: {e}")
        raise TimeoutError(f"Search request timed out: {query}") from e
    except ClientResponseError as e:
        logging.error(f"HTTP error from {url}: {e.status} {e.message}")
        raise NetworkError(f"HTTP error {e.status}: {e.message}") from e
    except ClientError as e:
        logging.error(f"Network error searching {url}: {e}")
        raise NetworkError(f"Network error: {str(e)}") from e
    except Exception as e:
        logging.error(f"Unexpected error searching {url}: {e}")
        raise NetworkError(f"Unexpected error: {str(e)}") from e


class HomebrewBatchProcessor(
    AsyncBatchProcessor[Tuple[str, str], Tuple[str, str, bool]]
):
    """Process batches of applications to check for Homebrew installability."""

    def __init__(
        self,
        batch_size: int = 50,
        max_concurrency: int = 10,
        rate_limit: float = 1.0,
        use_cache: bool = True,
        strict_match: bool = False,
    ):
        """Initialize the Homebrew batch processor.

        Args:
            batch_size: Number of items per batch
            max_concurrency: Maximum number of concurrent tasks
            rate_limit: Minimum time between requests in seconds
            use_cache: Whether to use cached results
            strict_match: Whether to use strict matching (exact name match)
        """
        super().__init__(batch_size, max_concurrency, rate_limit)
        self.use_cache = use_cache
        self.strict_match = strict_match

    async def process_item(self, item: Tuple[str, str]) -> Tuple[str, str, bool]:
        """Check if an application can be installed with Homebrew.

        Args:
            item: Tuple of (app_name, version)

        Returns:
            Tuple of (app_name, version, installable)
        """
        app_name, version = item

        # Skip empty names
        if not app_name:
            return (app_name, version, False)

        # Format the name for cask search
        search_name = app_name.lower().replace(" ", "-")

        try:
            # First check if we have an exact match
            result = await self._check_exact_match(search_name)

            # If no exact match and not strict mode, try fuzzy search
            if not result and not self.strict_match:
                result = await self._check_fuzzy_match(app_name)

            return (app_name, version, result)

        except (NetworkError, TimeoutError, HomebrewError) as e:
            logging.error(f"Error checking installability for {app_name}: {e}")
            return (app_name, version, False)

    async def _check_exact_match(self, cask_name: str) -> bool:
        """Check if there's an exact match for a cask name.

        Args:
            cask_name: Cask name to check

        Returns:
            bool: True if installable, False otherwise
        """
        try:
            # Try to fetch the cask info
            await fetch_cask_info(cask_name, use_cache=self.use_cache)
            return True
        except NetworkError as e:
            # 404 error means the cask doesn't exist
            if "404" in str(e):
                return False
            # Other network errors should be propagated
            raise

    async def _check_fuzzy_match(self, app_name: str) -> bool:
        """Check for fuzzy matches of an app name.

        Args:
            app_name: Application name to check

        Returns:
            bool: True if a matching cask is found, False otherwise
        """
        # Create simplified search term
        search_term = re.sub(r"[^a-zA-Z0-9]", "", app_name.lower())

        # Search for the app
        search_results = await search_casks(search_term, use_cache=self.use_cache)

        # Check if any results contain our app name
        if search_results:
            for result in search_results:
                cask_name = result.get("token", "")
                # Check if the app name is a significant part of the cask name
                if self._is_significant_match(app_name, cask_name):
                    return True

        return False

    def _is_significant_match(self, app_name: str, cask_name: str) -> bool:
        """Determine if an app name and cask name are a significant match.

        Args:
            app_name: Application name
            cask_name: Cask name

        Returns:
            bool: True if names are a significant match
        """
        # Clean up names for comparison
        clean_app = re.sub(r"[^a-zA-Z0-9]", "", app_name.lower())
        clean_cask = re.sub(r"[^a-zA-Z0-9]", "", cask_name.lower())

        # Check if one name contains the other
        if clean_app in clean_cask or clean_cask in clean_app:
            # Calculate ratio of length to avoid false positives
            min_len = min(len(clean_app), len(clean_cask))
            max_len = max(len(clean_app), len(clean_cask))

            # If the shorter name is at least 60% of the longer name, consider it a match
            if min_len / max_len >= 0.6:
                return True

        return False

    def handle_error(
        self, item: Tuple[str, str], error: Exception
    ) -> Tuple[str, str, bool]:
        """Handle an error that occurred during processing.

        Args:
            item: Item that caused the error
            error: Exception that was raised

        Returns:
            Tuple of (app_name, version, False)
        """
        app_name, version = item
        logging.error(f"Error checking installability for {app_name}: {error}")
        return (app_name, version, False)


@async_to_sync
async def async_check_brew_install_candidates(
    data: List[Tuple[str, str]], rate_limit: float = 1.0, strict_match: bool = False
) -> List[Tuple[str, str, bool]]:
    """Check which applications can be installed via Homebrew (async version).

    Args:
        data: List of (app_name, version) tuples for installed applications
        rate_limit: Seconds between API calls
        strict_match: Whether to use strict matching

    Returns:
        List[Tuple[str, str, bool]]: List of (app_name, version, installable) tuples
    """
    # Fast path for non-homebrew systems
    if not is_homebrew_available():
        return [(name, version, False) for name, version in data]

    # Use async batch processor
    processor = HomebrewBatchProcessor(
        batch_size=50,
        max_concurrency=int(10 / rate_limit),  # Adjust concurrency based on rate limit
        rate_limit=rate_limit,
        strict_match=strict_match,
    )

    return processor.process_all(data)


@async_to_sync
async def async_get_cask_version(
    cask_name: str, use_cache: bool = True
) -> Optional[str]:
    """Get the latest version of a Homebrew cask asynchronously.

    Args:
        cask_name: Name of the cask
        use_cache: Whether to use cached results

    Returns:
        Optional[str]: Latest version or None if not found

    Raises:
        HomebrewError: If there's an error with the Homebrew operation
        NetworkError: If there's a network issue
        TimeoutError: If the request times out
    """
    try:
        cask_info = await fetch_cask_info(cask_name, use_cache=use_cache)
        return cask_info.get("version")
    except NetworkError as e:
        # 404 error means the cask doesn't exist
        if "404" in str(e):
            return None
        # Other network errors should be propagated
        raise
    except Exception as e:
        logging.error(f"Error getting cask version for {cask_name}: {e}")
        raise HomebrewError(f"Error getting cask version: {e}") from e


class HomebrewVersionChecker(
    AsyncBatchProcessor[Tuple[str, str, str], Tuple[str, str, str, Optional[str]]]
):
    """Process batches of applications to check for updates via Homebrew."""

    def __init__(
        self,
        batch_size: int = 10,
        max_concurrency: int = 5,
        rate_limit: float = 1.0,
        use_cache: bool = True,
    ):
        """Initialize the Homebrew version checker.

        Args:
            batch_size: Number of items per batch
            max_concurrency: Maximum number of concurrent tasks
            rate_limit: Minimum time between requests in seconds
            use_cache: Whether to use cached results
        """
        super().__init__(batch_size, max_concurrency, rate_limit)
        self.use_cache = use_cache

    async def process_item(
        self, item: Tuple[str, str, str]
    ) -> Tuple[str, str, str, Optional[str]]:
        """Check for updates to a Homebrew-installed application.

        Args:
            item: Tuple of (app_name, version, cask_name)

        Returns:
            Tuple of (app_name, version, cask_name, latest_version)
        """
        app_name, version, cask_name = item

        try:
            # Get the latest version from Homebrew
            latest_version = await async_get_cask_version(cask_name, self.use_cache)
            return (app_name, version, cask_name, latest_version)

        except (NetworkError, TimeoutError, HomebrewError) as e:
            logging.error(f"Error checking version for {app_name} ({cask_name}): {e}")
            return (app_name, version, cask_name, None)

    def handle_error(
        self, item: Tuple[str, str, str], error: Exception
    ) -> Tuple[str, str, str, Optional[str]]:
        """Handle an error that occurred during processing.

        Args:
            item: Item that caused the error
            error: Exception that was raised

        Returns:
            Tuple of (app_name, version, cask_name, None)
        """
        app_name, version, cask_name = item
        logging.error(f"Error checking version for {app_name} ({cask_name}): {error}")
        return (app_name, version, cask_name, None)


@async_to_sync
async def async_check_brew_update_candidates(
    data: List[Tuple[str, str, str]], rate_limit: float = 1.0
) -> List[Tuple[str, str, str, Optional[str]]]:
    """Check for updates to Homebrew-installed applications (async version).

    Args:
        data: List of (app_name, version, cask_name) tuples
        rate_limit: Seconds between API calls

    Returns:
        List[Tuple[str, str, str, Optional[str]]]: List with latest versions
    """
    # Fast path for non-homebrew systems
    if not is_homebrew_available():
        return [(name, version, cask, None) for name, version, cask in data]

    # Use async batch processor
    processor = HomebrewVersionChecker(
        batch_size=10,
        max_concurrency=int(5 / rate_limit),  # Adjust concurrency based on rate limit
        rate_limit=rate_limit,
    )

    return processor.process_all(data)
