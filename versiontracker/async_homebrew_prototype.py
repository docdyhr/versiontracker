"""Asynchronous Homebrew prototype layer.

This module provides an experimental asynchronous interface over the existing
synchronous Homebrew access utilities. It is intentionally lightweight and
wraps synchronous calls in an executor (via ``asyncio.to_thread``) to provide
a non-blocking API without duplicating parsing logic.

Enablement:
    Set environment variable ``VERSIONTRACKER_ASYNC_BREW=1`` (or one of
    '1', 'true', 'yes', 'on') to enable. When disabled, helper functions
    transparently fall back to synchronous execution semantics (still
    returned from `await`, but performed in a thread for interface
    uniformity).

Design Goals:
    1. Provide a stable, typed facade for future native async
       implementations (e.g., parallel `brew` invocations, caching
       prefetch orchestration).
    2. Avoid premature coupling to internal synchronous module details.
    3. Allow incremental adoption guarded by a feature flag.

Non-Goals (Prototype Phase):
    * Direct parsing of `brew` JSON output (delegated to existing sync
      functions in `homebrew.py`).
    * Advanced cancellation semantics beyond cooperative checks.
    * Integrated timeout + retry policy (hook points are provided).

Usage Example:
    import asyncio
    from versiontracker.async_homebrew_prototype import (
        get_async_client,
        is_async_brew_enabled,
    )

    async def main():
        client = get_async_client()
        info = await client.get_cask_info("visual-studio-code")
        print(info)

    asyncio.run(main())

Testing Strategy:
    * Unit tests can mock the underlying synchronous functions to assert
      delegation.
    * Integration tests can enable the feature flag and verify functional
      parity (output shape) with synchronous calls.

"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Dict, Iterable, List, Optional, Sequence, Tuple, Union

# Fail-safe imports: these modules are expected to exist in the project.
# They are imported lazily in methods where possible to reduce import-time cost
# and avoid circular dependencies during partial refactors.
try:  # pragma: no cover - import guard
    from . import homebrew  # type: ignore
except Exception:  # pragma: no cover - best-effort fallback
    homebrew = None  # type: ignore

try:  # pragma: no cover
    from .exceptions import NetworkError, TimeoutError  # type: ignore
except Exception:  # pragma: no cover
    # Fallback minimal stand-ins (should rarely occur)
    class NetworkError(Exception):  # type: ignore
        """Fallback NetworkError."""

    class TimeoutError(Exception):  # type: ignore
        """Fallback TimeoutError."""


ASYNC_FEATURE_ENV = "VERSIONTRACKER_ASYNC_BREW"
ASYNC_ENABLED_VALUES = {"1", "true", "yes", "on"}
DEFAULT_CONCURRENCY = 10
DEFAULT_TIMEOUT = 30.0  # seconds (placeholder; not strictly enforced yet)
LOG_NAMESPACE = "versiontracker.async_homebrew"


@dataclass
class CaskResult:
    """Container for a single cask operation result.

    Attributes:
        name: Cask identifier.
        data: Parsed info dictionary (shape defined by underlying sync layer).
        error: Optional exception if retrieval failed.
        elapsed: Time in seconds for the retrieval.
    """

    name: str
    data: Optional[Dict[str, Any]]
    error: Optional[Exception]
    elapsed: float


class AsyncHomebrewClient:
    """Prototype asynchronous Homebrew client.

    Wraps synchronous homebrew utility functions in a non-blocking API
    using thread offloading. This allows the rest of the application to
    evolve toward async architectures incrementally.

    Args:
        enabled: Whether async mode is enabled (feature flag).
        max_concurrency: Maximum parallel operations for batch methods.
        loop: Event loop (auto-detected if None).

    Raises:
        ValueError: If max_concurrency is invalid.
    """

    def __init__(
        self,
        enabled: bool,
        max_concurrency: int = DEFAULT_CONCURRENCY,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        """Initialize the async Homebrew client."""
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self._enabled = enabled
        self._loop = loop
        self._max_concurrency = max_concurrency
        self._logger = logging.getLogger(LOG_NAMESPACE)

    # --------------------------------------------------------------------- #
    # Public properties
    # --------------------------------------------------------------------- #
    @property
    def enabled(self) -> bool:
        """Whether the async feature flag was enabled at construction."""
        return self._enabled

    @property
    def max_concurrency(self) -> int:
        """Maximum parallel cask operations."""
        return self._max_concurrency

    # --------------------------------------------------------------------- #
    # Core internal helpers
    # --------------------------------------------------------------------- #
    async def _to_thread(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a synchronous function in a worker thread.

        Args:
            func: Callable to execute.
            *args: Positional args.
            **kwargs: Keyword args.

        Returns:
            The callable's return value.
        """
        return await asyncio.to_thread(func, *args, **kwargs)

    def _now(self) -> float:
        """Monotonic time helper."""
        return time.perf_counter()

    # --------------------------------------------------------------------- #
    # Public async API methods
    # --------------------------------------------------------------------- #
    async def get_cask_info(self, cask: str, timeout: float = DEFAULT_TIMEOUT) -> Optional[Dict[str, Any]]:
        """Get information about a single Homebrew cask.

        Delegates to the synchronous `homebrew.get_homebrew_cask_info` function.

        Args:
            cask: Cask name.
            timeout: Soft timeout (not strictly enforced yet; placeholder for future).

        Returns:
            Parsed cask info dictionary or None if not found.

        Raises:
            NetworkError: On simulated or underlying network errors.
            TimeoutError: If operation exceeds provisional timeout (future hook).
        """
        if homebrew is None:  # pragma: no cover
            self._logger.warning("Homebrew module unavailable; returning None for cask %s", cask)  # type: ignore[unreachable]
            return None

        start = self._now()
        try:
            result = await self._to_thread(homebrew.get_homebrew_cask_info, cask)  # type: ignore[attr-defined]
            elapsed = self._now() - start
            self._logger.debug("Fetched cask %s in %.3fs", cask, elapsed)
            return result
        except TimeoutError:
            raise
        except NetworkError:
            raise
        except Exception as exc:
            # Wrap unexpected exceptions to keep interface stable.
            self._logger.error("Unexpected error fetching cask %s: %s", cask, exc)
            return None

    async def get_casks_info(
        self,
        casks: Sequence[str],
        concurrency: Optional[int] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Dict[str, CaskResult]:
        """Fetch multiple cask infos in parallel.

        Args:
            casks: Sequence of cask names.
            concurrency: Optional override for per-call concurrency.
            timeout: Soft timeout placeholder.

        Returns:
            Mapping of cask name to CaskResult objects (data or error populated).
        """
        limit = concurrency or self._max_concurrency
        if limit < 1:
            raise ValueError("concurrency must be >= 1")

        semaphore = asyncio.Semaphore(limit)
        results: Dict[str, CaskResult] = {}

        async def worker(name: str) -> None:
            async with semaphore:
                start = self._now()
                try:
                    data = await self.get_cask_info(name, timeout=timeout)
                    results[name] = CaskResult(name=name, data=data, error=None, elapsed=self._now() - start)
                except Exception as exc:  # noqa: BLE001 - we intentionally capture for result encapsulation
                    results[name] = CaskResult(name=name, data=None, error=exc, elapsed=self._now() - start)

        await asyncio.gather(*(worker(c) for c in casks))
        return results

    async def search_casks(self, term: str) -> List[str]:
        """Search for casks matching a term using underlying sync logic.

        Args:
            term: Search query.

        Returns:
            List of matching cask names (may be empty).
        """
        if homebrew is None:  # pragma: no cover
            self._logger.warning("Homebrew module unavailable; search returns empty list")  # type: ignore[unreachable]
            return []

        try:
            # Assume homebrew.search function; fallback gracefully if absent.
            if hasattr(homebrew, "search_casks"):
                return await self._to_thread(homebrew.search_casks, term)  # type: ignore[attr-defined]
            if hasattr(homebrew, "search"):
                return await self._to_thread(homebrew.search, term)  # type: ignore[attr-defined]
            self._logger.debug("No search function available in homebrew module")
            return []
        except Exception as exc:  # noqa: BLE001
            self._logger.error("Search failed for term %s: %s", term, exc)
            return []

    async def warm_cache(self, casks: Sequence[str], concurrency: Optional[int] = None) -> Dict[str, bool]:
        """Prime underlying cache layers by pre-fetching info for specified casks.

        Args:
            casks: Cask names to warm.
            concurrency: Optional concurrency override.

        Returns:
            Mapping of cask name to success boolean.
        """
        info_map = await self.get_casks_info(casks, concurrency=concurrency)
        return {name: (res.data is not None and res.error is None) for name, res in info_map.items()}

    # --------------------------------------------------------------------- #
    # Convenience synchronous-style wrappers
    # --------------------------------------------------------------------- #
    def run(self, coro: "Coroutine[Any, Any, Any]") -> Any:
        """Run a coroutine, creating a loop if needed.

        If an event loop is already running, the coroutine is scheduled
        and the created Task is returned (caller can await it).
        If no loop is running, the coroutine is executed to completion
        and its result returned.

        Args:
            coro: A coroutine object.

        Returns:
            Result of the coroutine (new loop) or Task (existing loop).
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        else:
            # Return task so caller can await in existing loop context
            return asyncio.create_task(coro)

    # --------------------------------------------------------------------- #
    # Future extension hooks
    # --------------------------------------------------------------------- #
    def with_concurrency(self, max_concurrency: int) -> "AsyncHomebrewClient":
        """Return a shallow clone with a different concurrency limit."""
        return AsyncHomebrewClient(
            enabled=self._enabled,
            max_concurrency=max_concurrency,
            loop=self._loop,
        )


# ------------------------------------------------------------------------- #
# Module-level helpers
# ------------------------------------------------------------------------- #
def is_async_brew_enabled(env: Optional[Dict[str, str]] = None) -> bool:
    """Check whether the async prototype feature is enabled.

    Args:
        env: Optional environment mapping (for testing).

    Returns:
        True if the feature flag is enabled.
    """
    source = env if env is not None else os.environ
    raw = source.get(ASYNC_FEATURE_ENV, "").strip().lower()
    return raw in ASYNC_ENABLED_VALUES


def get_async_client(
    max_concurrency: int = DEFAULT_CONCURRENCY,
    force: Optional[bool] = None,
) -> AsyncHomebrewClient:
    """Factory for the async Homebrew client.

    Args:
        max_concurrency: Concurrency limit for batch operations.
        force: Force enable/disable irrespective of environment variable.

    Returns:
        AsyncHomebrewClient instance.
    """
    enabled = force if force is not None else is_async_brew_enabled()
    return AsyncHomebrewClient(enabled=enabled, max_concurrency=max_concurrency)


# ------------------------------------------------------------------------- #
# Convenience top-level async functions (thin wrappers)
# ------------------------------------------------------------------------- #
async def async_get_cask_info(cask: str) -> Optional[Dict[str, Any]]:
    """Convenience function to get a single cask's info asynchronously."""
    client = get_async_client()
    return await client.get_cask_info(cask)


async def async_get_casks_info(
    casks: Sequence[str],
    concurrency: Optional[int] = None,
) -> Dict[str, CaskResult]:
    """Convenience function to fetch multiple casks' info asynchronously."""
    client = get_async_client()
    return await client.get_casks_info(casks, concurrency=concurrency)


async def async_search_casks(term: str) -> List[str]:
    """Convenience function to search casks asynchronously."""
    client = get_async_client()
    return await client.search_casks(term)


__all__ = [
    "AsyncHomebrewClient",
    "CaskResult",
    "async_get_cask_info",
    "async_get_casks_info",
    "async_search_casks",
    "get_async_client",
    "is_async_brew_enabled",
    "ASYNC_FEATURE_ENV",
]
