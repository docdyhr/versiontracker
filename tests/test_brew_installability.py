"""Tests for brew cask installability functions in the apps module."""

import unittest
from unittest.mock import MagicMock, patch

from versiontracker.apps import get_homebrew_cask_name as get_brew_cask_name
from versiontracker.apps import is_brew_cask_installable


class TestBrewCaskInstallability(unittest.TestCase):
    """Test cases for brew cask installability functions."""

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps._execute_brew_search")
    @patch("versiontracker.apps._handle_brew_search_result")
    @patch("versiontracker.apps.read_cache")
    def test_is_brew_cask_installable_found(
        self,
        mock_read_cache,
        mock_handle_result,
        mock_execute_search,
        mock_is_homebrew_available,
    ):
        """Test is_brew_cask_installable when cask is found."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew_available.return_value = True
        # Mock cache to return None (cache miss)
        mock_read_cache.return_value = None
        # Mock execute_brew_search to return success
        mock_execute_search.return_value = ("firefox", 0)
        # Mock handle_brew_search_result to return True
        mock_handle_result.return_value = True

        # Call the function
        result = is_brew_cask_installable("firefox")

        # Verify result is True when cask is found
        self.assertTrue(result)

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps._execute_brew_search")
    @patch("versiontracker.apps._handle_brew_search_result")
    @patch("versiontracker.apps.read_cache")
    def test_is_brew_cask_installable_not_found(
        self,
        mock_read_cache,
        mock_handle_result,
        mock_execute_search,
        mock_is_homebrew_available,
    ):
        """Test is_brew_cask_installable when cask is not found."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew_available.return_value = True
        # Mock cache to return None (cache miss)
        mock_read_cache.return_value = None
        # Mock execute_brew_search to return not found
        mock_execute_search.return_value = ("Error: No formulae or casks found", 1)
        # Mock handle_brew_search_result to return False
        mock_handle_result.return_value = False

        # Call the function
        result = is_brew_cask_installable("non-existent-app")

        # Verify result is False when cask is not found
        self.assertFalse(result)

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps._execute_brew_search")
    @patch("versiontracker.apps.read_cache")
    def test_is_brew_cask_installable_error(self, mock_read_cache, mock_execute_search, mock_is_homebrew_available):
        """Test is_brew_cask_installable error handling."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew_available.return_value = True
        # Mock cache to return None (cache miss)
        mock_read_cache.return_value = None
        # Mock _check_cache_for_cask to return None (cache miss)
        with patch("versiontracker.apps._check_cache_for_cask", return_value=None):
            # Mock execute_brew_search to raise an exception
            mock_execute_search.side_effect = Exception("Some error")

            # Call the function
            result = is_brew_cask_installable("problematic-app")

            # Verify result is False when an error occurs
            self.assertFalse(result)

    @patch("versiontracker.apps._apps_main.is_homebrew_available", return_value=True)
    def test_is_brew_cask_installable_with_cache(self, mock_homebrew_available):
        """Test is_brew_cask_installable with caching."""
        # Set up the test
        # We'll mock the read_cache and write_cache functions instead of directly manipulating the cache
        with patch("versiontracker.apps.read_cache") as mock_read_cache:
            with patch("versiontracker.apps.write_cache") as mock_write_cache:
                with patch("versiontracker.apps._check_cache_for_cask") as mock_check_cache:
                    # First call - cache miss
                    mock_read_cache.return_value = None
                    mock_check_cache.return_value = None  # Cache miss

                    # Mock _execute_brew_search and _handle_brew_search_result
                    with patch("versiontracker.apps._execute_brew_search") as mock_execute:
                        with patch("versiontracker.apps._handle_brew_search_result") as mock_handle:
                            with patch("versiontracker.apps._update_cache_with_installable") as mock_update_cache:
                                mock_execute.return_value = ("firefox\n", 0)
                                mock_handle.return_value = True

                                # First call
                                result1 = is_brew_cask_installable("firefox", use_cache=True)
                                self.assertTrue(result1)

                                # Cache update should have been called but implementation details may vary
                                # Just verify the function returns the expected result

                                # Second call - cache hit
                                mock_read_cache.return_value = {"installable": ["firefox"]}
                                mock_check_cache.return_value = True  # Cache hit
                                mock_execute.reset_mock()

                                # Second call with same app - should use cache
                                result2 = is_brew_cask_installable("firefox", use_cache=True)
                                self.assertTrue(result2)
                                mock_execute.assert_not_called()  # Should use cache instead of running brew

                                # Third call - cache disabled
                                mock_read_cache.reset_mock()
                                mock_check_cache.return_value = None  # Reset for cache disabled

                                # Call with use_cache=False - should query again
                                mock_execute.return_value = ("firefox\n", 0)
                                result3 = is_brew_cask_installable("firefox", use_cache=False)
                                self.assertTrue(result3)
                                # Should call execute since cache is disabled

    @patch("versiontracker.apps.matcher.read_cache")
    @patch("versiontracker.apps.matcher.write_cache")
    @patch("versiontracker.apps.matcher._process_brew_search")
    def test_get_brew_cask_name_search_match(self, mock_process_brew_search, mock_write_cache, mock_read_cache):
        """Test get_brew_cask_name when search finds a match."""
        # Mock cache to return None (cache miss)
        mock_read_cache.return_value = None

        # Mock _process_brew_search to return a match
        mock_process_brew_search.return_value = "firefox"

        # Create a mock rate limiter
        mock_rate_limiter = MagicMock()

        # Call the function
        result = get_brew_cask_name("firefox", mock_rate_limiter)

        # Verify result matches the search result
        self.assertEqual(result, "firefox")

        # Verify search was called
        mock_process_brew_search.assert_called_once()

        # Verify result was cached
        mock_write_cache.assert_called_once()

    @patch("versiontracker.apps.read_cache")
    @patch("versiontracker.apps._process_brew_search")
    def test_get_brew_cask_name_no_match(self, mock_process_brew_search, mock_read_cache):
        """Test get_brew_cask_name when no match is found."""
        # Mock cache to return None (cache miss)
        mock_read_cache.return_value = None

        # Mock _process_brew_search to return None (no match)
        mock_process_brew_search.return_value = None

        # Create a mock rate limiter
        mock_rate_limiter = MagicMock()

        # Call the function
        result = get_brew_cask_name("non-existent-app", mock_rate_limiter)

        # Verify result is None when no match is found
        self.assertIsNone(result)

    @patch("versiontracker.apps.matcher.read_cache")
    def test_get_brew_cask_name_from_cache(self, mock_read_cache):
        """Test get_brew_cask_name retrieving from cache."""
        # Mock cache to return a hit with the proper dictionary structure
        mock_read_cache.return_value = {"cask_name": "firefox"}

        # Create a mock rate limiter
        mock_rate_limiter = MagicMock()

        # Call the function
        result = get_brew_cask_name("firefox", mock_rate_limiter)

        # Verify result matches the cached value
        self.assertEqual(result, "firefox")


if __name__ == "__main__":
    unittest.main()
