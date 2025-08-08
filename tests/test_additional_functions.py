"""Tests for additional functions in the apps module."""

import sys
import unittest
from unittest.mock import patch

from tests.mock_adaptive_rate_limiter import MockAdaptiveRateLimiter
from versiontracker.app_finder import (
    filter_brew_candidates,
    get_homebrew_casks_list,
)
from versiontracker.exceptions import BrewTimeoutError, NetworkError


class TestAdditionalAppsFunctions(unittest.TestCase):
    """Test cases for additional functions in the apps module."""

    @patch("versiontracker.apps.finder.is_homebrew_available")
    @patch("versiontracker.utils.run_command")
    def test_get_homebrew_casks_list(self, mock_run_command, mock_is_homebrew_available):
        """Test get_homebrew_casks_list function."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew_available.return_value = True

        # Mock the brew list command to return a list of casks
        mock_run_command.return_value = ("firefox\ngoogle-chrome\nvisual-studio-code\n", 0)

        # Call the function
        result = get_homebrew_casks_list()

        # Verify the result contains the expected casks
        self.assertEqual(sorted(result), ["firefox", "google-chrome", "visual-studio-code"])

        # Test when Homebrew is not available
        mock_is_homebrew_available.return_value = False

        # Should raise HomebrewError when Homebrew is not available
        from versiontracker.exceptions import HomebrewError

        with self.assertRaises(HomebrewError):
            get_homebrew_casks_list()

        # Test error propagation with NetworkError
        mock_is_homebrew_available.return_value = True
        mock_run_command.side_effect = NetworkError("Network error")
        with self.assertRaises(NetworkError):
            get_homebrew_casks_list()

        # Test error propagation with BrewTimeoutError
        mock_run_command.side_effect = BrewTimeoutError("Timeout error")
        with self.assertRaises(BrewTimeoutError):
            get_homebrew_casks_list()

    def test_filter_brew_candidates(self):
        """Test filter_brew_candidates function."""
        # Create test data
        data = [
            ("Firefox", "100.0", True),  # Installable
            ("Chrome", "99.0", False),  # Not installable
            ("Safari", "15.0", False),  # Not installable
            ("VSCode", "1.67.0", True),  # Installable
        ]

        # Test with installable=True (filter to only show installable apps)
        result_installable = filter_brew_candidates(data, installable=True)
        self.assertEqual(len(result_installable), 2)
        self.assertEqual(result_installable[0], ("Firefox", "100.0", True))
        self.assertEqual(result_installable[1], ("VSCode", "1.67.0", True))

        # Test with installable=False (filter to only show non-installable apps)
        result_not_installable = filter_brew_candidates(data, installable=False)
        self.assertEqual(len(result_not_installable), 2)
        self.assertEqual(result_not_installable[0], ("Chrome", "99.0", False))
        self.assertEqual(result_not_installable[1], ("Safari", "15.0", False))

        # Test with None (return all apps)
        result_all = filter_brew_candidates(data, installable=None)
        self.assertEqual(len(result_all), 4)
        self.assertEqual(result_all, data)

    def test_adaptive_rate_limiter(self):
        """Test AdaptiveRateLimiter class."""
        # Create an AdaptiveRateLimiter instance
        rate_limiter = MockAdaptiveRateLimiter(
            base_rate_limit_sec=1.0,
            min_rate_limit_sec=0.5,
            max_rate_limit_sec=2.0,
            adaptive_factor=0.1,
        )

        # Test initial state
        self.assertEqual(rate_limiter._base_rate_limit_sec, 1.0)
        self.assertEqual(rate_limiter._min_rate_limit_sec, 0.5)
        self.assertEqual(rate_limiter._max_rate_limit_sec, 2.0)
        self.assertEqual(rate_limiter._adaptive_factor, 0.1)
        self.assertEqual(rate_limiter._current_rate_limit_sec, 1.0)
        self.assertEqual(rate_limiter._success_count, 0)
        self.assertEqual(rate_limiter._failure_count, 0)

        # Test success feedback
        rate_limiter.feedback(success=True)
        self.assertEqual(rate_limiter._success_count, 1)
        self.assertEqual(rate_limiter._failure_count, 0)

        # After 10 successes, rate should decrease (get faster)
        for _ in range(9):
            rate_limiter.feedback(success=True)
        self.assertLess(rate_limiter._current_rate_limit_sec, 1.0)

        # Test failure feedback
        rate_limiter.feedback(success=False)
        self.assertEqual(rate_limiter._success_count, 10)
        self.assertEqual(rate_limiter._failure_count, 1)

        # After 5 failures, rate should increase (get slower)
        for _ in range(4):
            rate_limiter.feedback(success=False)
        self.assertGreater(rate_limiter._current_rate_limit_sec, 1.0)

        # Test wait method
        with patch("time.time") as mock_time, patch("time.sleep") as mock_sleep:
            # Mock time.time to return increasing values
            mock_time.side_effect = [0.0, 0.5]  # First call, second call

            # Call wait method
            rate_limiter.wait()

            # Should sleep for (current_rate - elapsed) = current_rate - 0.5
            expected_sleep = rate_limiter._current_rate_limit_sec - 0.5
            if expected_sleep > 0:
                mock_sleep.assert_called_once_with(expected_sleep)


if __name__ == "__main__":
    unittest.main()
