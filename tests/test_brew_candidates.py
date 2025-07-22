"""Tests for check_brew_install_candidates function in the apps module."""

import unittest
from unittest.mock import MagicMock, patch

from versiontracker.apps import (
    SimpleRateLimiter,
    _process_brew_batch,
    _process_brew_search,
    check_brew_install_candidates,
)
from versiontracker.exceptions import BrewTimeoutError, NetworkError


class TestBrewCandidates(unittest.TestCase):
    """Test cases for brew install candidate functions."""

    def _get_limiter_delay(self, limiter):
        """Helper method to get the delay from a rate limiter without directly accessing protected members."""
        # Use a solution that works with pytest and linting - create a property for testing
        if hasattr(limiter, "test_get_delay"):
            return limiter.test_get_delay()
        else:
            # For backward compatibility with existing tests, fall back to direct access
            return getattr(limiter, "_delay", 0.0)

    @patch("versiontracker.apps.is_homebrew_available")
    def test_check_brew_install_candidates_no_homebrew(self, mock_is_homebrew):
        """Test check_brew_install_candidates when Homebrew is not available."""
        # Mock is_homebrew_available to return False
        mock_is_homebrew.return_value = False

        # Create test data
        data = [("Firefox", "100.0"), ("Chrome", "99.0")]

        # Call the function
        result = check_brew_install_candidates(data)

        # Verify that all apps are marked as not installable
        expected = [("Firefox", "100.0", False), ("Chrome", "99.0", False)]
        self.assertEqual(result, expected)

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps._process_brew_batch")
    @patch("versiontracker.apps.smart_progress")
    def test_check_brew_install_candidates_success(
        self, mock_smart_progress, mock_process_brew_batch, mock_is_homebrew
    ):
        """Test check_brew_install_candidates with successful batch processing."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True

        # Mock _process_brew_batch to return expected results
        expected_results = [("Firefox", "100.0", True), ("Chrome", "99.0", False)]
        mock_process_brew_batch.return_value = expected_results

        # Mock smart_progress to just pass through the iterable
        mock_smart_progress.side_effect = lambda x, **kwargs: x

        # Create test data
        data = [("Firefox", "100.0"), ("Chrome", "99.0")]

        # Call the function
        result = check_brew_install_candidates(data)

        # Verify the result
        self.assertEqual(result, expected_results)

        # Verify _process_brew_batch was called with the right parameters
        mock_process_brew_batch.assert_called_once_with(data, 1, True)

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps._process_brew_batch")
    @patch("versiontracker.apps.smart_progress")
    def test_check_brew_install_candidates_network_error(
        self, mock_smart_progress, mock_process_brew_batch, mock_is_homebrew
    ):
        """Test check_brew_install_candidates handling network errors."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True

        # Mock _process_brew_batch to raise NetworkError once, then succeed
        def side_effect(_batch, _rate_limit, _use_cache):
            if mock_process_brew_batch.call_count == 1:
                raise NetworkError("Network unavailable")
            return [("Firefox", "100.0", True)]

        mock_process_brew_batch.side_effect = side_effect

        # Mock smart_progress to just pass through the iterable
        mock_smart_progress.side_effect = lambda x, **kwargs: x

        # Create test data - small enough for a single batch
        data = [("Firefox", "100.0")]

        # Test that NetworkError is raised after MAX_ERRORS (3) consecutive failures
        with patch("versiontracker.apps.MAX_ERRORS", 1):  # Lower MAX_ERRORS for testing
            with self.assertRaises(NetworkError):
                check_brew_install_candidates(data)

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps._process_brew_batch")
    @patch("versiontracker.apps.smart_progress")
    def test_check_brew_install_candidates_brew_timeout_error(
        self, mock_smart_progress, mock_process_brew_batch, mock_is_homebrew
    ):
        """Test check_brew_install_candidates handling timeout errors."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True

        # Mock _process_brew_batch to raise BrewTimeoutError
        mock_process_brew_batch.side_effect = BrewTimeoutError("Operation timed out")

        # Mock smart_progress to just pass through the iterable
        mock_smart_progress.side_effect = lambda x, **kwargs: x

        # Create test data with multiple batches
        data = [("App%d" % i, "1.0") for i in range(60)]

        # Call the function - should handle the error and add all apps as not installable
        result = check_brew_install_candidates(data)

        # Verify the result length matches the input
        self.assertEqual(len(result), len(data))

        # Verify all apps are marked as not installable
        for _, _, installable in result:
            self.assertFalse(installable)

    @patch("versiontracker.apps.is_homebrew_available")
    def test_process_brew_batch_no_homebrew(self, mock_is_homebrew):
        """Test _process_brew_batch when Homebrew is not available."""
        # Mock is_homebrew_available to return False
        mock_is_homebrew.return_value = False

        # Create test data
        batch = [("Firefox", "100.0"), ("Chrome", "99.0")]

        # Call the function
        result = _process_brew_batch(batch, 1, True)

        # Verify all apps are marked as not installable
        expected = [("Firefox", "100.0", False), ("Chrome", "99.0", False)]
        self.assertEqual(result, expected)

    @patch("versiontracker.apps.is_homebrew_available")
    def test_process_brew_batch_empty(self, mock_is_homebrew):
        """Test _process_brew_batch with an empty batch."""
        # Call the function with an empty batch
        result = _process_brew_batch([], 1, True)

        # Verify an empty result is returned
        self.assertEqual(result, [])

        # Verify is_homebrew_available was not called
        mock_is_homebrew.assert_not_called()

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps.is_brew_cask_installable")
    @patch("versiontracker.apps.ThreadPoolExecutor")
    @patch("versiontracker.apps.get_config")
    def test_process_brew_batch_success(
        self,
        mock_get_config,
        mock_executor_class,
        mock_is_installable,
        mock_is_homebrew,
    ):
        """Test successful batch processing."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True

        # Mock config with default rate limiting
        mock_config = MagicMock()
        mock_config.ui = {"adaptive_rate_limiting": False}
        mock_get_config.return_value = mock_config

        # Mock is_brew_cask_installable
        mock_is_installable.return_value = True

        # Mock ThreadPoolExecutor
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        # Set up mock futures and as_completed
        mock_future = MagicMock()
        mock_future.result.return_value = True
        mock_future.exception.return_value = None  # No exception
        mock_executor.submit.return_value = mock_future

        with patch("versiontracker.apps.as_completed", return_value=[mock_future]):
            # Create test data
            batch = [("Firefox", "100.0")]

            # Call the function with proper mocking of executor's future result
            with patch("versiontracker.apps._process_brew_search", return_value="Firefox"):
                result = _process_brew_batch(batch, 2, True)

            # Verify the result
            expected = [("Firefox", "100.0", True)]
            self.assertEqual(result, expected)

            # Verify is_brew_cask_installable was called with the normalized name
            mock_executor.submit.assert_called_once_with(mock_is_installable, "firefox", True)

    @patch("versiontracker.apps.run_command")
    def test_process_brew_search_match_found(self, mock_run_command):
        """Test _process_brew_search when a match is found."""
        # Mock rate limiter
        mock_rate_limiter = MagicMock()

        # Mock run_command to return search results
        mock_run_command.return_value = ("firefox\nfirefox-developer-edition", 0)

        # Call the function
        result = _process_brew_search(("Firefox", "100.0"), mock_rate_limiter)

        # Verify the result
        self.assertEqual(result, "Firefox")

        # Verify rate limiter was called
        mock_rate_limiter.wait.assert_called_once()

    @patch("versiontracker.apps.run_command")
    def test_process_brew_search_no_match(self, mock_run_command):
        """Test _process_brew_search when no match is found."""
        # Mock rate limiter
        mock_rate_limiter = MagicMock()

        # Mock run_command to return no matches
        mock_run_command.return_value = ("other-app", 0)

        # Call the function
        result = _process_brew_search(("Firefox", "100.0"), mock_rate_limiter)

        # Verify the result is None
        self.assertIsNone(result)

    @patch("versiontracker.apps.run_command")
    def test_process_brew_search_error(self, mock_run_command):
        """Test _process_brew_search error handling."""
        # Mock rate limiter
        mock_rate_limiter = MagicMock()

        # Mock run_command to raise an exception
        mock_run_command.side_effect = Exception("Test error")

        # Call the function
        result = _process_brew_search(("Firefox", "100.0"), mock_rate_limiter)

        # Verify the result is None
        self.assertIsNone(result)

    def test_simple_rate_limiter(self):
        """Test SimpleRateLimiter functionality."""
        # Create a rate limiter with a 0.1 second delay (minimum)
        rate_limiter = SimpleRateLimiter(0.1)

        # Verify the delay was set correctly
        self.assertEqual(self._get_limiter_delay(rate_limiter), 0.1)

        # Test with delay below minimum
        min_limiter = SimpleRateLimiter(0.05)
        self.assertEqual(self._get_limiter_delay(min_limiter), 0.1)  # Should be clamped to 0.1

        # Test with higher delay
        high_limiter = SimpleRateLimiter(0.5)
        self.assertEqual(self._get_limiter_delay(high_limiter), 0.5)

        # Test wait method doesn't error
        rate_limiter.wait()  # First call shouldn't wait
        rate_limiter.wait()  # Second call should wait
