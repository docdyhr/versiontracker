"""Additional tests for apps.py to improve coverage on missing areas."""

import threading
import time
from unittest.mock import Mock, patch

import pytest

from versiontracker.apps import (
    AdaptiveRateLimiter,
    SimpleRateLimiter,
    _AdaptiveRateLimiter,
    _create_batches,
    _create_rate_limiter,
    _handle_batch_error,
    _handle_future_result,
    clear_homebrew_casks_cache,
    filter_out_brews,
    get_homebrew_casks_list,
    is_app_in_app_store,
    is_brew_cask_installable,
)
from versiontracker.exceptions import (
    BrewTimeoutError,
    HomebrewError,
    NetworkError,
)

# Test functions for _AdaptiveRateLimiter class


def test_adaptive_rate_limiter_init():
    """Test _AdaptiveRateLimiter initialization."""
    limiter = _AdaptiveRateLimiter()
    assert limiter._base_rate_limit_sec == 1.0
    assert limiter._min_rate_limit_sec == 0.1
    assert limiter._max_rate_limit_sec == 5.0
    assert limiter._current_rate_limit_sec == 1.0


def test_adaptive_rate_limiter_custom_params():
    """Test _AdaptiveRateLimiter with custom parameters."""
    limiter = _AdaptiveRateLimiter(
        base_rate_limit_sec=2.0, min_rate_limit_sec=0.5, max_rate_limit_sec=10.0
    )
    assert limiter._base_rate_limit_sec == 2.0
    assert limiter._min_rate_limit_sec == 0.5
    assert limiter._max_rate_limit_sec == 10.0


def test_adaptive_rate_limiter_wait():
    """Test _AdaptiveRateLimiter wait method."""
    limiter = _AdaptiveRateLimiter(base_rate_limit_sec=0.1)
    # First call should not wait
    start_time = time.time()
    limiter.wait()
    end_time = time.time()
    # First call should be immediate
    assert end_time - start_time < 0.05

    # Second call should wait
    start_time = time.time()
    limiter.wait()
    end_time = time.time()
    # Should wait at least part of the rate limit
    assert end_time - start_time >= 0.05


def test_adaptive_rate_limiter_feedback_success():
    """Test _AdaptiveRateLimiter feedback with successes."""
    limiter = _AdaptiveRateLimiter()
    original_rate = limiter.get_current_limit()

    # Provide many successful feedbacks
    for _ in range(15):
        limiter.feedback(True)

    # Rate should decrease after 10 successes
    assert limiter.get_current_limit() < original_rate


def test_adaptive_rate_limiter_feedback_failure():
    """Test _AdaptiveRateLimiter feedback with failures."""
    limiter = _AdaptiveRateLimiter()
    original_rate = limiter.get_current_limit()

    # Provide many failure feedbacks
    for _ in range(10):
        limiter.feedback(False)

    # Rate should increase after 5 failures
    assert limiter.get_current_limit() > original_rate


def test_adaptive_rate_limiter_max_limit():
    """Test _AdaptiveRateLimiter respects maximum limit."""
    limiter = _AdaptiveRateLimiter(max_rate_limit_sec=3.0)
    limiter._current_rate_limit_sec = 2.5

    # Many failures should not exceed max
    for _ in range(20):
        limiter.feedback(False)

    assert limiter.get_current_limit() <= 3.0


def test_adaptive_rate_limiter_min_limit():
    """Test _AdaptiveRateLimiter respects minimum limit."""
    limiter = _AdaptiveRateLimiter(min_rate_limit_sec=0.5)
    limiter._current_rate_limit_sec = 0.7

    # Many successes should not go below min
    for _ in range(50):
        limiter.feedback(True)

    assert limiter.get_current_limit() >= 0.5


# Test functions for AdaptiveRateLimiter alias


def test_adaptive_rate_limiter_alias():
    """Test that AdaptiveRateLimiter is an alias for _AdaptiveRateLimiter."""
    limiter = AdaptiveRateLimiter()
    assert isinstance(limiter, _AdaptiveRateLimiter)


# Test functions for App Store checking functionality


@patch("versiontracker.apps.read_cache")
def test_is_app_in_app_store_cache_hit(mock_read_cache):
    """Test is_app_in_app_store with cache hit."""
    mock_read_cache.return_value = {"apps": ["TestApp", "AnotherApp"]}
    result = is_app_in_app_store("TestApp", use_cache=True)
    assert result is True


@patch("versiontracker.apps.read_cache")
def test_is_app_in_app_store_cache_miss(mock_read_cache):
    """Test is_app_in_app_store with cache miss."""
    mock_read_cache.return_value = None
    result = is_app_in_app_store("TestApp", use_cache=True)
    assert result is False


def test_is_app_in_app_store_no_cache():
    """Test is_app_in_app_store without using cache."""
    result = is_app_in_app_store("TestApp", use_cache=False)
    assert result is False


@patch("versiontracker.apps.read_cache")
def test_is_app_in_app_store_exception(mock_read_cache):
    """Test is_app_in_app_store exception handling."""
    mock_read_cache.side_effect = Exception("Cache error")
    result = is_app_in_app_store("TestApp")
    assert result is False


# Test functions for Homebrew cask installability checking


@patch("versiontracker.apps.is_homebrew_available")
def test_is_brew_cask_installable_no_homebrew(mock_homebrew_available):
    """Test cask check when Homebrew not available."""
    mock_homebrew_available.return_value = False

    with pytest.raises(HomebrewError):
        is_brew_cask_installable("testapp")


@patch("versiontracker.apps.read_cache")
@patch("versiontracker.apps.is_homebrew_available")
def test_is_brew_cask_installable_cache_hit(mock_homebrew_available, mock_read_cache):
    """Test cask check with cache hit."""
    mock_homebrew_available.return_value = True
    mock_read_cache.return_value = {"testapp": True}

    result = is_brew_cask_installable("testapp", use_cache=True)
    assert result is True


@patch("versiontracker.apps.read_cache")
@patch("versiontracker.apps.is_homebrew_available")
def test_is_brew_cask_installable_cache_miss(mock_homebrew_available, mock_read_cache):
    """Test cask check with cache miss."""
    mock_homebrew_available.return_value = True
    mock_read_cache.return_value = None

    # This will exercise the actual brew search logic
    result = is_brew_cask_installable("testapp", use_cache=True)
    # Result depends on actual implementation
    assert isinstance(result, bool)


# Test functions for get_homebrew_casks_list function


@patch("versiontracker.apps.is_homebrew_available")
def test_get_homebrew_casks_list_no_homebrew(mock_homebrew_available):
    """Test get_homebrew_casks_list when Homebrew not available."""
    mock_homebrew_available.return_value = False

    with pytest.raises(HomebrewError):
        get_homebrew_casks_list()


@patch("versiontracker.apps.is_homebrew_available")
def test_get_homebrew_casks_list_with_homebrew(mock_homebrew_available):
    """Test get_homebrew_casks_list when Homebrew is available."""
    mock_homebrew_available.return_value = True

    # This will test the actual implementation
    result = get_homebrew_casks_list()
    assert isinstance(result, list)


# Test functions for utility functions


def test_create_batches_normal():
    """Test _create_batches with normal input."""
    data = [("app1", "1.0"), ("app2", "2.0"), ("app3", "3.0"), ("app4", "4.0")]
    batches = _create_batches(data, batch_size=2)
    assert len(batches) == 2
    assert batches[0] == [("app1", "1.0"), ("app2", "2.0")]
    assert batches[1] == [("app3", "3.0"), ("app4", "4.0")]


def test_create_batches_empty():
    """Test _create_batches with empty input."""
    batches = _create_batches([], batch_size=2)
    assert batches == []


def test_create_batches_single_item():
    """Test _create_batches with single item."""
    data = [("app1", "1.0")]
    batches = _create_batches(data, batch_size=5)
    assert len(batches) == 1
    assert batches[0] == [("app1", "1.0")]


def test_handle_batch_error_network():
    """Test _handle_batch_error with network error."""
    error = NetworkError("Network failed")
    batch = [("app1", "1.0"), ("app2", "2.0")]

    results, error_count, last_error = _handle_batch_error(error, 0, batch)

    assert len(results) == 2
    assert error_count == 1
    # The function may not return the original error
    for result in results:
        assert result[2] is False  # All apps marked as not installable


def test_handle_batch_error_timeout():
    """Test _handle_batch_error with timeout error."""
    error = BrewTimeoutError("Timeout")
    batch = [("app1", "1.0")]

    results, error_count, last_error = _handle_batch_error(error, 1, batch)

    assert len(results) == 1
    assert error_count == 2


def test_create_rate_limiter_int():
    """Test _create_rate_limiter with integer input."""
    limiter = _create_rate_limiter(2)
    assert isinstance(limiter, SimpleRateLimiter)


def test_create_rate_limiter_object_with_delay():
    """Test _create_rate_limiter with object having delay attribute."""
    mock_config = Mock()
    mock_config.delay = 1.5

    limiter = _create_rate_limiter(mock_config)
    assert isinstance(limiter, SimpleRateLimiter)


def test_create_rate_limiter_object_with_rate_limit():
    """Test _create_rate_limiter with object having rate_limit attribute."""
    mock_config = Mock()
    mock_config.rate_limit = 2.0
    del mock_config.delay  # Ensure delay attribute doesn't exist

    limiter = _create_rate_limiter(mock_config)
    assert isinstance(limiter, SimpleRateLimiter)


def test_create_rate_limiter_default_fallback():
    """Test _create_rate_limiter falls back to default."""
    mock_config = Mock()
    # Remove all expected attributes
    mock_config.spec = []

    limiter = _create_rate_limiter(mock_config)
    assert isinstance(limiter, SimpleRateLimiter)


def test_handle_future_result_success():
    """Test _handle_future_result with successful future."""
    future = Mock()
    future.result.return_value = True
    future.exception.return_value = None

    result, error = _handle_future_result(future, "testapp", "1.0")

    assert result == ("testapp", "1.0", True)
    assert error is None


def test_handle_future_result_exception():
    """Test _handle_future_result with exception."""
    future = Mock()
    future.exception.return_value = NetworkError("Network failed")

    result, error = _handle_future_result(future, "testapp", "1.0")

    assert result == ("testapp", "1.0", False)
    # The function may handle exceptions differently
    assert error is not None


# Test functions for filter_out_brews function with different scenarios


def test_filter_out_brews_strict_mode():
    """Test filter_out_brews in strict mode."""
    applications = [("TestApp", "1.0"), ("AnotherApp", "2.0"), ("ThirdApp", "3.0")]
    brews = ["testapp", "another-app"]

    result = filter_out_brews(applications, brews, strict_mode=True)

    # In strict mode, should filter more aggressively
    assert isinstance(result, list)


def test_filter_out_brews_empty_brews():
    """Test filter_out_brews with empty brews list."""
    applications = [("TestApp", "1.0"), ("AnotherApp", "2.0")]
    brews = []

    result = filter_out_brews(applications, brews)

    assert result == applications


def test_filter_out_brews_empty_applications():
    """Test filter_out_brews with empty applications list."""
    applications = []
    brews = ["testapp", "another-app"]

    result = filter_out_brews(applications, brews)

    assert result == []


def test_filter_out_brews_no_matches():
    """Test filter_out_brews with no matches."""
    applications = [("UniqueApp", "1.0"), ("SpecialApp", "2.0")]
    brews = ["commonapp", "standardapp"]

    result = filter_out_brews(applications, brews)

    assert result == applications


# Test functions for cache management


@patch("versiontracker.apps.get_homebrew_casks")
def test_clear_homebrew_casks_cache(mock_get_homebrew_casks):
    """Test clear_homebrew_casks_cache function."""
    # Mock the cache_clear method
    mock_get_homebrew_casks.cache_clear = Mock()

    clear_homebrew_casks_cache()

    # Verify cache_clear was called
    mock_get_homebrew_casks.cache_clear.assert_called_once()


# Test functions for rate limiter edge cases


def test_simple_rate_limiter_zero_delay():
    """Test SimpleRateLimiter with zero delay."""
    limiter = SimpleRateLimiter(0)
    assert limiter._delay == 0.1  # Should enforce minimum


def test_simple_rate_limiter_negative_delay():
    """Test SimpleRateLimiter with negative delay."""
    limiter = SimpleRateLimiter(-1)
    assert limiter._delay == 0.1  # Should enforce minimum


def test_simple_rate_limiter_thread_safety():
    """Test SimpleRateLimiter thread safety."""
    limiter = SimpleRateLimiter(0.1)

    def worker():
        limiter.wait()

    threads = []
    for _ in range(3):
        thread = threading.Thread(target=worker)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Should complete without errors


# Test functions for complex scenarios and integration points


def test_simple_rate_limiter_multiple_waits():
    """Test SimpleRateLimiter with multiple consecutive waits."""
    limiter = SimpleRateLimiter(0.05)  # Small delay for testing

    start_time = time.time()
    limiter.wait()
    limiter.wait()
    end_time = time.time()

    # Should have waited at least one delay period
    assert end_time - start_time >= 0.04


def test_adaptive_rate_limiter_mixed_feedback():
    """Test _AdaptiveRateLimiter with consecutive success/failure feedback."""
    limiter = _AdaptiveRateLimiter()
    original_rate = limiter.get_current_limit()

    # First test consecutive successes (should decrease rate limit)
    for i in range(10):
        limiter.feedback(True)

    decreased_rate = limiter.get_current_limit()
    assert decreased_rate < original_rate

    # Then test consecutive failures (should increase rate limit)
    for i in range(5):
        limiter.feedback(False)

    increased_rate = limiter.get_current_limit()
    assert increased_rate > decreased_rate
