"""Tests for app store related functions in the apps module."""

import unittest
from unittest.mock import MagicMock, patch

from versiontracker.apps import (
    is_app_in_app_store,
)
from versiontracker.exceptions import BrewTimeoutError, NetworkError


class TestAppStore(unittest.TestCase):
    """Test cases for app store functions."""

    @patch("versiontracker.apps.read_cache")
    def test_is_app_in_app_store_found(self, mock_read_cache):
        """Test is_app_in_app_store when app is found in App Store."""
        # Mock cache data with the app
        mock_read_cache.return_value = {"apps": ["Test App"]}

        # Call the function with test data
        result = is_app_in_app_store("Test App")

        # Verify result is True when app is found in the cache
        self.assertTrue(result)

        # Verify the cache was checked
        mock_read_cache.assert_called_once_with("app_store_apps")

    @patch("versiontracker.apps.read_cache")
    def test_is_app_in_app_store_not_found(self, mock_read_cache):
        """Test is_app_in_app_store when app is not found."""
        # Mock cache with other apps
        mock_read_cache.return_value = {"apps": ["Some Other App"]}

        # Call the function
        result = is_app_in_app_store("Non-existent App")

        # Verify result is False when app is not found
        self.assertFalse(result)

    @patch("versiontracker.apps.read_cache")
    def test_is_app_in_app_store_error(self, mock_read_cache):
        """Test is_app_in_app_store when read_cache fails."""
        # Mock read_cache to return None
        mock_read_cache.return_value = None

        # Call the function
        result = is_app_in_app_store("Some App")

        # Verify result is False when cache is unavailable
        self.assertFalse(result)

    @patch("versiontracker.apps.read_cache")
    def test_is_app_in_app_store_exception(self, mock_read_cache):
        """Test is_app_in_app_store exception handling."""
        # Mock read_cache to raise an exception
        mock_read_cache.side_effect = Exception("Cache read failed")

        # Call the function
        result = is_app_in_app_store("Some App")

        # Verify result is False when exception occurs
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
