"""Asynchronous network operations for VersionTracker.

This module provides asynchronous network operation support using asyncio,
allowing for more efficient handling of network requests, especially when
dealing with multiple Homebrew API calls or other network operations.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

import aiohttp
from aiohttp import ClientError, ClientResponseError, ClientTimeout

from versiontracker.cache import read_cache, write_cache
from versiontracker.config import get_config
from versiontracker.exceptions import NetworkError, TimeoutError
from versiontracker.utils import get_user_agent

# Type variables for generic functions
T = TypeVar("T")
R = TypeVar("R")

# Default timeout in seconds
DEFAULT_TIMEOUT = 10

# Cache settings
CACHE_EXPIRY = 86400  # 1 day in seconds


async def fetch_json(
    url: str,
    cache_key: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Fetch JSON data from a URL asynchronously.

    Args:
        url: URL to fetch
        cache_key: Key to use for caching (defaults to URL if None)
        timeout: Request timeout in seconds
        use_cache: Whether to use cached results

    Returns:
        Dict[str, Any]: JSON response data

    Raises:
        NetworkError: If there's a network issue
        TimeoutError: If the request times out
    """
    # Use URL as cache key if none provided
    cache_key = cache_key or f"url_{url.replace('/', '_')}"

    # Try to get from cache first
    if use_cache:
        cached_data = read_cache(cache_key, CACHE_EXPIRY)
        if cached_data:
            logging.debug(f"Using cached data for {url}")
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

                # Cache the result
                if use_cache:
                    write_cache(cache_key, data)

                return data

    except asyncio.TimeoutError as e:
        logging.error(f"Request to {url} timed out after {timeout}s: {e}")
        raise TimeoutError(f"Request timed out: {url}") from e
    except ClientResponseError as e:
        logging.error(f"HTTP error from {url}: {e.status} {e.message}")
        raise NetworkError(f"HTTP error {e.status}: {e.message}") from e
    except ClientError as e:
        logging.error(f"Network error accessing {url}: {e}")
        raise NetworkError(f"Network error: {str(e)}") from e
    except Exception as e:
        logging.error(f"Unexpected error fetching {url}: {e}")
        raise NetworkError(f"Unexpected error: {str(e)}") from e


async def batch_fetch_json(
    urls: List[str],
    cache_keys: Optional[List[str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    use_cache: bool = True,
    max_concurrency: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Fetch multiple JSON resources concurrently.

    Args:
        urls: List of URLs to fetch
        cache_keys: Optional list of cache keys (must match length of urls)
        timeout: Request timeout in seconds
        use_cache: Whether to use cached results
        max_concurrency: Maximum number of concurrent requests (None for unlimited)

    Returns:
        List[Dict[str, Any]]: List of JSON responses in the same order as URLs

    Raises:
        NetworkError: If there's a network issue
        TimeoutError: If requests time out
        ValueError: If cache_keys length doesn't match urls length
    """
    if not urls:
        return []

    if cache_keys and len(cache_keys) != len(urls):
        raise ValueError("cache_keys length must match urls length")

    # Use URLs as cache keys if none provided
    if not cache_keys:
        cache_keys = [f"url_{url.replace('/', '_')}" for url in urls]

    # Determine concurrency limit
    config = get_config()
    if max_concurrency is None:
        max_concurrency = getattr(config, "api_rate_limit", 10)

    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrency)

    async def fetch_with_semaphore(url: str, cache_key: str) -> Dict[str, Any]:
        """Fetch a URL with concurrency limiting."""
        async with semaphore:
            # Add a small delay to avoid overwhelming the server
            await asyncio.sleep(0.1)
            return await fetch_json(url, cache_key, timeout, use_cache)

    # Create tasks for all URLs
    tasks = [
        fetch_with_semaphore(url, cache_key) for url, cache_key in zip(urls, cache_keys)
    ]

    # Execute all tasks concurrently and gather results
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results, re-raising any exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logging.error(f"Error fetching {urls[i]}: {result}")
            # Convert to appropriate exception type
            if isinstance(result, TimeoutError):
                raise result
            elif isinstance(result, NetworkError):
                raise result
            else:
                raise NetworkError(
                    f"Error fetching {urls[i]}: {str(result)}"
                ) from result
        else:
            processed_results.append(result)

    return processed_results


def async_to_sync(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to convert an async function to a synchronous one.

    Args:
        func: Async function to convert

    Returns:
        Synchronous wrapper function
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Synchronous wrapper for async function."""
        # Get event loop or create a new one
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the async function in the event loop
        return loop.run_until_complete(func(*args, **kwargs))

    return wrapper


def run_async_in_thread(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run an async function in a separate thread.

    Args:
        func: Async function to run
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Result of the async function
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(async_to_sync(func), *args, **kwargs)
        return future.result()


class AsyncBatchProcessor:
    """Process batches of data asynchronously with rate limiting."""

    def __init__(
        self,
        batch_size: int = 50,
        max_concurrency: int = 10,
        rate_limit: float = 1.0,
    ):
        """Initialize the batch processor.

        Args:
            batch_size: Number of items per batch
            max_concurrency: Maximum number of concurrent tasks
            rate_limit: Minimum time between requests in seconds
        """
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency
        self.rate_limit = rate_limit
        self.semaphore = asyncio.Semaphore(max_concurrency)

    def create_batches(self, data: List[T]) -> List[List[T]]:
        """Split data into batches.

        Args:
            data: List of items to batch

        Returns:
            List of batches
        """
        batches = []
        for i in range(0, len(data), self.batch_size):
            batches.append(data[i : i + self.batch_size])
        return batches

    async def process_item(self, item: T) -> R:
        """Process a single item.

        Args:
            item: Item to process

        Returns:
            Processed result

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement process_item")

    async def process_batch(self, batch: List[T]) -> List[R]:
        """Process a batch of items with rate limiting.

        Args:
            batch: Batch of items to process

        Returns:
            List of processed results
        """

        async def process_with_rate_limit(item: T) -> R:
            """Process an item with rate limiting."""
            async with self.semaphore:
                # Add rate limiting delay
                await asyncio.sleep(self.rate_limit)
                return await self.process_item(item)

        # Create tasks for all items in the batch
        tasks = [process_with_rate_limit(item) for item in batch]

        # Execute all tasks concurrently and gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results, logging any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logging.error(f"Error processing item {batch[i]}: {result}")
                # Handle the error in a subclass-specific way
                processed_results.append(self.handle_error(batch[i], result))
            else:
                processed_results.append(result)

        return processed_results

    def handle_error(self, item: T, error: Exception) -> R:
        """Handle an error that occurred during processing.

        Args:
            item: Item that caused the error
            error: Exception that was raised

        Returns:
            Default value or error indicator

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement handle_error")

    @async_to_sync
    async def process_all(self, data: List[T]) -> List[R]:
        """Process all data in batches.

        Args:
            data: List of items to process

        Returns:
            List of processed results
        """
        if not data:
            return []

        # Create batches
        batches = self.create_batches(data)

        # Process each batch
        all_results = []
        for batch in batches:
            batch_results = await self.process_batch(batch)
            all_results.extend(batch_results)

        return all_results
