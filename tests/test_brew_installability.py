"""Tests for brew cask installability functions in the apps module."""

import unittest
from unittest.mock import MagicMock, patch

from versiontracker.apps import (
    is_brew_cask_installable,
    get_brew_cask_name,
)
from versiontracker.exceptions import NetworkError, BrewTimeoutError


class TestBrewCaskInstallability(unittest.TestCase):
    """Test cases for brew cask installability functions."""
    
    @patch("versiontracker.apps.get_brew_cask_name")
    def test_is_brew_cask_installable_found(self, mock_get_brew_cask_name):
        """Test is_brew_cask_installable when cask is found."""
        # Mock get_brew_cask_name to return a valid cask name
        mock_get_brew_cask_name.return_value = "firefox"
        
        # Call the function
        result = is_brew_cask_installable("firefox")
        
        # Verify result is True when cask is found
        self.assertTrue(result)
        
    @patch("versiontracker.apps.get_brew_cask_name")
    def test_is_brew_cask_installable_not_found(self, mock_get_brew_cask_name):
        """Test is_brew_cask_installable when cask is not found."""
        # Mock get_brew_cask_name to return None (not found)
        mock_get_brew_cask_name.return_value = None
        
        # Call the function
        result = is_brew_cask_installable("non-existent-app")
        
        # Verify result is False when cask is not found
        self.assertFalse(result)
        
    @patch("versiontracker.apps.get_brew_cask_name")
    def test_is_brew_cask_installable_error(self, mock_get_brew_cask_name):
        """Test is_brew_cask_installable error handling."""
        # Mock get_brew_cask_name to raise an exception
        mock_get_brew_cask_name.side_effect = Exception("Some error")
        
        # Call the function
        result = is_brew_cask_installable("problematic-app")
        
        # Verify result is False when an error occurs
        self.assertFalse(result)
        
    @patch("versiontracker.apps.get_brew_cask_name")
    def test_is_brew_cask_installable_with_cache(self, mock_get_brew_cask_name):
        """Test is_brew_cask_installable with caching."""
        # Set up the test
        import versiontracker.apps
        original_cache = versiontracker.apps._brew_installable_cache
        
        try:
            # Reset the cache
            versiontracker.apps._brew_installable_cache = {}
            
            # First call - should query get_brew_cask_name
            mock_get_brew_cask_name.return_value = "firefox"
            result1 = is_brew_cask_installable("firefox", use_cache=True)
            self.assertTrue(result1)
            mock_get_brew_cask_name.assert_called_once()
            
            # Second call with same app - should use cache
            mock_get_brew_cask_name.reset_mock()
            result2 = is_brew_cask_installable("firefox", use_cache=True)
            self.assertTrue(result2)
            mock_get_brew_cask_name.assert_not_called()
            
            # Call with use_cache=False - should query again
            mock_get_brew_cask_name.reset_mock()
            result3 = is_brew_cask_installable("firefox", use_cache=False)
            self.assertTrue(result3)
            mock_get_brew_cask_name.assert_called_once()
        finally:
            # Restore original cache
            versiontracker.apps._brew_installable_cache = original_cache
    
    @patch("versiontracker.apps.read_cache")
    @patch("versiontracker.apps.write_cache")
    @patch("versiontracker.apps._process_brew_search")
    def test_get_brew_cask_name_search_match(self, mock_process_brew_search, 
                                            mock_write_cache, mock_read_cache):
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
        
    @patch("versiontracker.apps.read_cache")
    def test_get_brew_cask_name_from_cache(self, mock_read_cache):
        """Test get_brew_cask_name retrieving from cache."""
        # Mock cache to return a hit
        mock_read_cache.return_value = "firefox"
        
        # Create a mock rate limiter
        mock_rate_limiter = MagicMock()
        
        # Call the function
        result = get_brew_cask_name("firefox", mock_rate_limiter)
        
        # Verify result matches the cached value
        self.assertEqual(result, "firefox")


if __name__ == "__main__":
    unittest.main()
