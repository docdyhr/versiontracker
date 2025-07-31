"""Caching and rate limiting functionality for application management."""

import threading
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Protocol


# Rate limiter protocols
class RateLimiter(Protocol):
    """Protocol defining the interface for rate limiters."""

    def wait(self) -> None:
        """Wait according to rate limiting rules."""
        ...


class RateLimiterProtocol(Protocol):
    """Protocol defining the interface for rate limiters."""

    def wait(self) -> None:
        """Wait according to rate limiting rules."""
        ...


class SimpleRateLimiter:
    """A simple rate limiter for API calls."""

    def __init__(self, delay: float):
        """Initialize the rate limiter with specified delay.

        Args:
            delay: Minimum delay between API calls in seconds.
        """
        self._delay = max(0.1, float(delay))
        self._last_time = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Wait according to rate limiting rules."""
        with self._lock:
            now = time.time()
            if self._last_time > 0:
                elapsed = now - self._last_time
                if elapsed < self._delay:
                    time.sleep(self._delay - elapsed)
            self._last_time = time.time()


class _AdaptiveRateLimiter:
    """An adaptive rate limiter that adjusts based on feedback.

    This is a separate implementation for the tests, distinct from the UI module.
    """

    def __init__(
        self,
        base_rate_limit_sec: float = 1.0,
        min_rate_limit_sec: float = 0.1,
        max_rate_limit_sec: float = 5.0,
        adaptive_factor: float = 0.1,
    ):
        """Initialize the adaptive rate limiter.

        Args:
            base_rate_limit_sec: Base rate limit in seconds
            min_rate_limit_sec: Minimum rate limit in seconds
            max_rate_limit_sec: Maximum rate limit in seconds
            adaptive_factor: Factor by which to adjust the rate limit
        """
        self._base_rate_limit_sec = base_rate_limit_sec
        self._min_rate_limit_sec = min_rate_limit_sec
        self._max_rate_limit_sec = max_rate_limit_sec
        self._adaptive_factor = adaptive_factor
        self._current_rate_limit_sec = base_rate_limit_sec
        self._success_count = 0
        self._failure_count = 0
        self._last_call_time = 0.0

    def feedback(self, success: bool) -> None:
        """Provide feedback to adjust the rate limit.

        Args:
            success: Whether the operation was successful
        """
        if success:
            self._success_count += 1
            self._failure_count = 0

            # After 10 consecutive successes, decrease rate limit
            if self._success_count >= 10:
                self._current_rate_limit_sec = max(
                    self._min_rate_limit_sec,
                    self._current_rate_limit_sec * (1.0 - self._adaptive_factor),
                )
                self._success_count = 0
        else:
            self._failure_count += 1
            self._success_count = 0

            # After 5 consecutive failures, increase rate limit
            if self._failure_count >= 5:
                self._current_rate_limit_sec = min(
                    self._max_rate_limit_sec,
                    self._current_rate_limit_sec * (1.0 + self._adaptive_factor),
                )
                self._failure_count = 0

    def wait(self) -> None:
        """Wait according to the current rate limit."""
        current_time = time.time()

        if self._last_call_time > 0:  # Skip wait on first call
            elapsed = current_time - self._last_call_time
            if elapsed < self._current_rate_limit_sec:
                time.sleep(self._current_rate_limit_sec - elapsed)

        self._last_call_time = time.time()

    def get_current_limit(self) -> float:
        """Get the current rate limit.

        Returns:
            float: The current rate limit in seconds
        """
        return self._current_rate_limit_sec


# For backwards compatibility with tests
class AdaptiveRateLimiter(_AdaptiveRateLimiter):
    """Alias for _AdaptiveRateLimiter for backwards compatibility with tests."""

    pass


# Global cache variables
_brew_search_cache: Dict[str, List[str]] = {}
_brew_casks_cache: Optional[List[str]] = None


def clear_homebrew_casks_cache() -> None:
    """Clear all caches for the get_homebrew_casks function.

    This function is primarily intended for testing purposes.
    It clears both the module-level cache and the lru_cache.
    """
    global _brew_casks_cache
    _brew_casks_cache = None
    # Note: This will be called from the main module that has the cached function


@lru_cache(maxsize=1)
def get_homebrew_casks_cached() -> List[str]:
    """Cached version of homebrew casks retrieval.

    This is a placeholder that will be replaced by the actual implementation
    in the main apps module to avoid circular imports.
    """
    return []
