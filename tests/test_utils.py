"""Tests for the utils module."""

import unittest
from unittest.mock import MagicMock, patch

from versiontracker.utils import RateLimiter, normalise_name


class TestUtils(unittest.TestCase):
    """Test cases for utility functions."""

    def test_normalise_name(self):
        """Test normalising application names."""
        self.assertEqual(normalise_name("Test App"), "Test App")
        self.assertEqual(normalise_name(" Test App "), "Test App")
        self.assertEqual(normalise_name("Test123 App456"), "Test App")
        self.assertEqual(normalise_name("Test\x00App"), "TestApp")

    @patch("time.time")
    @patch("time.sleep")
    def test_rate_limiter(self, mock_sleep, mock_time):
        """Test the rate limiter."""
        # Set up the time.time() mock to return increasing values
        mock_time.side_effect = [0.0, 0.1, 0.2, 1.1, 1.2]

        # Create a rate limiter with 2 calls per second
        limiter = RateLimiter(calls_per_period=2, period=1.0)

        # First call should not wait
        limiter.wait()
        mock_sleep.assert_not_called()

        # Second call should not wait
        limiter.wait()
        mock_sleep.assert_not_called()

        # Third call should wait
        limiter.wait()
        mock_sleep.assert_called_once_with(0.8)  # 1.0 - (0.2 - 0.0) = 0.8

        # Fourth call should not wait (first call should be expired)
        limiter.wait()
        # sleep should still have been called only once (from third call)
        self.assertEqual(mock_sleep.call_count, 1)


if __name__ == "__main__":
    unittest.main()
