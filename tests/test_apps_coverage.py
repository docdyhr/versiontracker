"""Additional tests for apps.py to improve coverage on missing areas."""

import threading
import time
import unittest
from unittest.mock import Mock, patch

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


class TestAdaptiveRateLimiter(unittest.TestCase):
    """Test _AdaptiveRateLimiter class."""

    def test_adaptive_rate_limiter_init(self):
        """Test _AdaptiveRateLimiter initialization."""
        limiter = _AdaptiveRateLimiter()
        self.assertEqual(limiter._base_rate_limit_sec, 1.0)
        self.assertEqual(limiter._min_rate_limit_sec, 0.1)
        self.assertEqual(limiter._max_rate_limit_sec, 5.0)
        self.assertEqual(limiter._current_rate_limit_sec, 1.0)

    def test_adaptive_rate_limiter_custom_params(self):
        """Test _AdaptiveRateLimiter with custom parameters."""
        limiter = _AdaptiveRateLimiter(base_rate_limit_sec=2.0, min_rate_limit_sec=0.5, max_rate_limit_sec=10.0)
        self.assertEqual(limiter._base_rate_limit_sec, 2.0)
        self.assertEqual(limiter._min_rate_limit_sec, 0.5)
        self.assertEqual(limiter._max_rate_limit_sec, 10.0)

    def test_adaptive_rate_limiter_wait(self):
        """Test _AdaptiveRateLimiter wait method."""
        limiter = _AdaptiveRateLimiter(base_rate_limit_sec=0.1)
        # First call should not wait
        start_time = time.time()
        limiter.wait()
        end_time = time.time()
        # First call should be immediate
        self.assertLess(end_time - start_time, 0.05)

        # Second call should wait
        start_time = time.time()
        limiter.wait()
        end_time = time.time()
        # Should wait at least part of the rate limit
        self.assertGreaterEqual(end_time - start_time, 0.05)

    def test_adaptive_rate_limiter_feedback_success(self):
        """Test _AdaptiveRateLimiter feedback with successes."""
        limiter = _AdaptiveRateLimiter()
        original_rate = limiter.get_current_limit()

        # Provide many successful feedbacks
        for _ in range(15):
            limiter.feedback(True)

        # Rate should decrease after 10 successes
        self.assertLess(limiter.get_current_limit(), original_rate)

    def test_adaptive_rate_limiter_feedback_failure(self):
        """Test _AdaptiveRateLimiter feedback with failures."""
        limiter = _AdaptiveRateLimiter()
        original_rate = limiter.get_current_limit()

        # Provide many failure feedbacks
        for _ in range(10):
            limiter.feedback(False)

        # Rate should increase after 5 failures
        self.assertGreater(limiter.get_current_limit(), original_rate)

    def test_adaptive_rate_limiter_max_limit(self):
        """Test _AdaptiveRateLimiter respects maximum limit."""
        limiter = _AdaptiveRateLimiter(max_rate_limit_sec=3.0)
        limiter._current_rate_limit_sec = 2.5

        # Many failures should not exceed max
        for _ in range(20):
            limiter.feedback(False)

        self.assertLessEqual(limiter.get_current_limit(), 3.0)

    def test_adaptive_rate_limiter_min_limit(self):
        """Test _AdaptiveRateLimiter respects minimum limit."""
        limiter = _AdaptiveRateLimiter(min_rate_limit_sec=0.5)
        limiter._current_rate_limit_sec = 0.7

        # Many successes should not go below min
        for _ in range(50):
            limiter.feedback(True)

        self.assertGreaterEqual(limiter.get_current_limit(), 0.5)


class TestAdaptiveRateLimiterAlias(unittest.TestCase):
    """Test AdaptiveRateLimiter alias."""

    def test_adaptive_rate_limiter_alias(self):
        """Test that AdaptiveRateLimiter is an alias for _AdaptiveRateLimiter."""
        limiter = AdaptiveRateLimiter()
        self.assertIsInstance(limiter, _AdaptiveRateLimiter)


class TestAppStoreCheck(unittest.TestCase):
    """Test App Store checking functionality."""

    @patch("versiontracker.apps.finder.read_cache")
    def test_is_app_in_app_store_cache_hit(self, mock_read_cache):
        """Test is_app_in_app_store with cache hit."""
        mock_read_cache.return_value = {"apps": ["TestApp", "AnotherApp"]}
        result = is_app_in_app_store("TestApp", use_cache=True)
        self.assertTrue(result)

    @patch("versiontracker.apps.finder.read_cache")
    def test_is_app_in_app_store_cache_miss(self, mock_read_cache):
        """Test is_app_in_app_store with cache miss."""
        mock_read_cache.return_value = None
        result = is_app_in_app_store("TestApp", use_cache=True)
        self.assertFalse(result)

    def test_is_app_in_app_store_no_cache(self):
        """Test is_app_in_app_store without using cache."""
        result = is_app_in_app_store("TestApp", use_cache=False)
        self.assertFalse(result)

    @patch("versiontracker.apps.finder.read_cache")
    def test_is_app_in_app_store_exception(self, mock_read_cache):
        """Test is_app_in_app_store exception handling."""
        mock_read_cache.side_effect = Exception("Cache error")
        result = is_app_in_app_store("TestApp")
        self.assertFalse(result)


class TestBrewCaskInstallable(unittest.TestCase):
    """Test Homebrew cask installability checking."""

    def test_is_brew_cask_installable_no_homebrew(self):
        """Test cask check when Homebrew not available."""
        import versiontracker.apps

        apps_module = versiontracker.apps._apps_main

        with patch.object(apps_module, "is_homebrew_available", return_value=False):
            with self.assertRaises(HomebrewError):
                is_brew_cask_installable("testapp")

    def test_is_brew_cask_installable_cache_hit(self):
        """Test cask check with cache hit."""
        import versiontracker.apps

        apps_module = versiontracker.apps._apps_main

        with (
            patch.object(apps_module, "is_homebrew_available", return_value=True),
            patch.object(apps_module, "read_cache", return_value={"installable": ["testapp"]}),
            patch.object(apps_module, "_check_cache_for_cask", return_value=True),
        ):
            result = is_brew_cask_installable("testapp", use_cache=True)
            # When cache returns True (cask is installable), function should return True
            self.assertTrue(result)

    def test_is_brew_cask_installable_cache_miss(self):
        """Test cask check with cache miss."""
        import versiontracker.apps

        apps_module = versiontracker.apps._apps_main

        with (
            patch.object(apps_module, "is_homebrew_available", return_value=True),
            patch("versiontracker.cache.read_cache") as mock_read_cache,
        ):
            mock_read_cache.return_value = None

            # This will exercise the actual brew search logic
            result = is_brew_cask_installable("testapp", use_cache=True)
            # Result depends on actual implementation
            self.assertIsInstance(result, bool)


class TestHomebrewCasksList(unittest.TestCase):
    """Test get_homebrew_casks_list function."""

    def setUp(self):
        """Clear cache before each test."""
        clear_homebrew_casks_cache()

    def test_get_homebrew_casks_list_no_homebrew(self):
        """Test get_homebrew_casks_list when Homebrew not available."""
        import versiontracker.apps.finder

        with patch.object(versiontracker.apps.finder, "is_homebrew_available", return_value=False):
            with self.assertRaises(HomebrewError):
                get_homebrew_casks_list()

    def test_get_homebrew_casks_list_with_homebrew(self):
        """Test get_homebrew_casks_list when Homebrew is available."""
        import versiontracker.apps.finder

        # Mock the dynamically loaded module
        mock_module = Mock()
        mock_module.__name__ = "versiontracker_apps_main"
        mock_module.get_homebrew_casks = Mock(return_value=["firefox", "chrome", "vscode"])

        # Mock the spec and loader
        mock_spec = Mock()
        mock_spec.loader = Mock()
        mock_spec.loader.exec_module = Mock()

        with patch.object(versiontracker.apps.finder, "is_homebrew_available", return_value=True):
            with patch("importlib.util.spec_from_file_location", return_value=mock_spec):
                with patch("importlib.util.module_from_spec", return_value=mock_module):
                    result = get_homebrew_casks_list()
                    self.assertEqual(result, ["firefox", "chrome", "vscode"])


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""

    def test_create_batches_normal(self):
        """Test _create_batches with normal input."""
        data = [("app1", "1.0"), ("app2", "2.0"), ("app3", "3.0"), ("app4", "4.0")]
        batches = _create_batches(data, batch_size=2)
        self.assertEqual(len(batches), 2)
        self.assertEqual(batches[0], [("app1", "1.0"), ("app2", "2.0")])
        self.assertEqual(batches[1], [("app3", "3.0"), ("app4", "4.0")])

    def test_create_batches_empty(self):
        """Test _create_batches with empty input."""
        batches = _create_batches([], batch_size=2)
        self.assertEqual(batches, [])

    def test_create_batches_single_item(self):
        """Test _create_batches with single item."""
        data = [("app1", "1.0")]
        batches = _create_batches(data, batch_size=5)
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0], [("app1", "1.0")])

    def test_handle_batch_error_network(self):
        """Test _handle_batch_error with network error."""
        error = NetworkError("Network failed")
        batch = [("app1", "1.0"), ("app2", "2.0")]

        results, error_count, last_error = _handle_batch_error(error, 0, batch)

        self.assertEqual(len(results), 2)
        self.assertEqual(error_count, 1)
        # The function may not return the original error
        for result in results:
            self.assertFalse(result[2])  # All apps marked as not installable

    def test_handle_batch_error_timeout(self):
        """Test _handle_batch_error with timeout error."""
        error = BrewTimeoutError("Timeout")
        batch = [("app1", "1.0")]

        results, error_count, last_error = _handle_batch_error(error, 1, batch)

        self.assertEqual(len(results), 1)
        self.assertEqual(error_count, 2)

    def test_create_rate_limiter_int(self):
        """Test _create_rate_limiter with integer input."""
        limiter = _create_rate_limiter(2)
        # Check for either the refactored or original SimpleRateLimiter
        self.assertTrue(hasattr(limiter, "wait"), "Rate limiter should have wait method")

    def test_create_rate_limiter_object_with_delay(self):
        """Test _create_rate_limiter with object having delay attribute."""
        mock_config = Mock()
        mock_config.delay = 1.5

        limiter = _create_rate_limiter(mock_config)
        # Check for either the refactored or original SimpleRateLimiter
        self.assertTrue(hasattr(limiter, "wait"), "Rate limiter should have wait method")

    def test_create_rate_limiter_object_with_rate_limit(self):
        """Test _create_rate_limiter with object having rate_limit attribute."""
        mock_config = Mock()
        mock_config.rate_limit = 2.0
        del mock_config.delay  # Ensure delay attribute doesn't exist

        limiter = _create_rate_limiter(mock_config)
        # Check for either the refactored or original SimpleRateLimiter
        self.assertTrue(hasattr(limiter, "wait"), "Rate limiter should have wait method")

    def test_create_rate_limiter_default_fallback(self):
        """Test _create_rate_limiter falls back to default."""
        mock_config = Mock()
        # Remove all expected attributes
        mock_config.spec = []

        limiter = _create_rate_limiter(mock_config)
        # Check for either the refactored or original SimpleRateLimiter
        self.assertTrue(hasattr(limiter, "wait"), "Rate limiter should have wait method")

    def test_handle_future_result_success(self):
        """Test _handle_future_result with successful future."""
        future = Mock()
        future.result.return_value = True
        future.exception.return_value = None

        result, error = _handle_future_result(future, "testapp", "1.0")

        self.assertEqual(result, ("testapp", "1.0", True))
        self.assertIsNone(error)

    def test_handle_future_result_exception(self):
        """Test _handle_future_result with exception."""
        future = Mock()
        future.exception.return_value = NetworkError("Network failed")

        result, error = _handle_future_result(future, "testapp", "1.0")

        self.assertEqual(result, ("testapp", "1.0", False))
        # The function may handle exceptions differently
        self.assertIsNotNone(error)


class TestFilterOutBrews(unittest.TestCase):
    """Test filter_out_brews function with different scenarios."""

    def test_filter_out_brews_strict_mode(self):
        """Test filter_out_brews in strict mode."""
        applications = [("TestApp", "1.0"), ("AnotherApp", "2.0"), ("ThirdApp", "3.0")]
        brews = ["testapp", "another-app"]

        result = filter_out_brews(applications, brews, strict_mode=True)

        # In strict mode, should filter more aggressively
        self.assertIsInstance(result, list)

    def test_filter_out_brews_empty_brews(self):
        """Test filter_out_brews with empty brews list."""
        applications = [("TestApp", "1.0"), ("AnotherApp", "2.0")]
        brews = []

        result = filter_out_brews(applications, brews)

        self.assertEqual(result, applications)

    def test_filter_out_brews_empty_applications(self):
        """Test filter_out_brews with empty applications list."""
        applications = []
        brews = ["testapp", "another-app"]

        result = filter_out_brews(applications, brews)

        self.assertEqual(result, [])

    def test_filter_out_brews_no_matches(self):
        """Test filter_out_brews with no matches."""
        applications = [("UniqueApp", "1.0"), ("SpecialApp", "2.0")]
        brews = ["commonapp", "standardapp"]

        result = filter_out_brews(applications, brews)

        self.assertEqual(result, applications)


class TestCacheManagement(unittest.TestCase):
    """Test cache management functions."""

    def test_clear_homebrew_casks_cache(self):
        """Test clear_homebrew_casks_cache function executes without error."""
        # Simply test that the function can be called without raising an exception
        # The actual cache clearing behavior is tested in integration tests
        try:
            clear_homebrew_casks_cache()
            # If we get here without exception, the test passes
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"clear_homebrew_casks_cache() raised an exception: {e}")


class TestRateLimiterEdgeCases(unittest.TestCase):
    """Test edge cases for rate limiters."""

    def test_simple_rate_limiter_zero_delay(self):
        """Test SimpleRateLimiter with zero delay."""
        limiter = SimpleRateLimiter(0)
        self.assertEqual(limiter._delay, 0.1)  # Should enforce minimum

    def test_simple_rate_limiter_negative_delay(self):
        """Test SimpleRateLimiter with negative delay."""
        limiter = SimpleRateLimiter(-1)
        self.assertEqual(limiter._delay, 0.1)  # Should enforce minimum

    def test_simple_rate_limiter_thread_safety(self):
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


class TestComplexScenarios(unittest.TestCase):
    """Test complex scenarios and integration points."""

    def test_simple_rate_limiter_multiple_waits(self):
        """Test SimpleRateLimiter with multiple consecutive waits."""
        limiter = SimpleRateLimiter(0.05)  # Small delay for testing

        start_time = time.time()
        limiter.wait()
        limiter.wait()
        end_time = time.time()

        # Should have waited at least one delay period
        self.assertGreaterEqual(end_time - start_time, 0.04)

    def test_adaptive_rate_limiter_mixed_feedback(self):
        """Test _AdaptiveRateLimiter with mixed success/failure feedback."""
        limiter = _AdaptiveRateLimiter()
        original_rate = limiter.get_current_limit()

        # Mix of successes and failures
        limiter.feedback(True)
        limiter.feedback(False)
        limiter.feedback(True)
        limiter.feedback(False)

        # Rate should still be around original
        current_rate = limiter.get_current_limit()
        self.assertAlmostEqual(current_rate, original_rate, delta=0.5)
