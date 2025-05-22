"""Test module for the advanced Homebrew functionality.

This module contains tests for the homebrew.py module, which provides
enhanced Homebrew querying capabilities with advanced caching.
"""

import json
import unittest
from unittest.mock import patch

import pytest

from versiontracker.advanced_cache import (
    AdvancedCache,
    set_cache_instance,
)
from versiontracker.exceptions import HomebrewError
from versiontracker.homebrew import (
    batch_get_cask_info,
    clear_homebrew_cache,
    get_all_homebrew_casks,
    get_cask_info,
    get_cask_version,
    get_homebrew_path,
    get_installed_homebrew_casks,
    get_outdated_homebrew_casks,
    is_homebrew_available,
    search_casks,
)


class TestHomebrewModule(unittest.TestCase):
    """Tests for the Homebrew module functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create a test cache
        self.test_cache = AdvancedCache(cache_dir="/tmp/versiontracker_test_cache")
        # Set the test cache as the global instance
        set_cache_instance(self.test_cache)
        # Clear the cache before each test
        self.test_cache.clear()

    def tearDown(self):
        """Clean up after tests."""
        # Clear the test cache
        self.test_cache.clear()

    @patch('versiontracker.homebrew.run_command')
    def test_is_homebrew_available_success(self, mock_run_command):
        """Test checking Homebrew availability when it is available."""
        mock_run_command.return_value = ("Homebrew 3.6.0", 0)
        self.assertTrue(is_homebrew_available())

    @patch('versiontracker.homebrew.run_command')
    def test_is_homebrew_available_failure(self, mock_run_command):
        """Test checking Homebrew availability when it is not available."""
        mock_run_command.return_value = ("Command not found", 1)
        self.assertFalse(is_homebrew_available())

    @patch('versiontracker.homebrew.run_command')
    @patch('os.path.exists')
    @patch('os.access')
    def test_get_homebrew_path_intel(self, mock_access, mock_exists, mock_run_command):
        """Test getting Homebrew path on Intel Mac."""
        # Mock Intel Mac path exists
        mock_exists.side_effect = lambda path: path == "/usr/local/bin/brew"
        mock_access.side_effect = lambda path, mode: path == "/usr/local/bin/brew"
        
        result = get_homebrew_path()
        self.assertEqual(result, "/usr/local/bin/brew")
        mock_run_command.assert_not_called()

    @patch('versiontracker.homebrew.run_command')
    @patch('os.path.exists')
    @patch('os.access')
    def test_get_homebrew_path_apple_silicon(self, mock_access, mock_exists, mock_run_command):
        """Test getting Homebrew path on Apple Silicon Mac."""
        # Mock Apple Silicon path exists
        mock_exists.side_effect = lambda path: path == "/opt/homebrew/bin/brew"
        mock_access.side_effect = lambda path, mode: path == "/opt/homebrew/bin/brew"
        
        result = get_homebrew_path()
        self.assertEqual(result, "/opt/homebrew/bin/brew")
        mock_run_command.assert_not_called()

    @patch('versiontracker.homebrew.run_command')
    @patch('os.path.exists')
    @patch('os.access')
    def test_get_homebrew_path_fallback(self, mock_access, mock_exists, mock_run_command):
        """Test getting Homebrew path using which command fallback."""
        # Mock no paths exist
        mock_exists.return_value = False
        mock_access.return_value = False
        mock_run_command.return_value = ("/custom/path/brew", 0)
        
        result = get_homebrew_path()
        self.assertEqual(result, "/custom/path/brew")
        mock_run_command.assert_called_once()

    @patch('versiontracker.homebrew.run_command')
    @patch('os.path.exists')
    @patch('os.access')
    def test_get_homebrew_path_not_found(self, mock_access, mock_exists, mock_run_command):
        """Test getting Homebrew path when it is not found."""
        # Mock no paths exist
        mock_exists.return_value = False
        mock_access.return_value = False
        mock_run_command.return_value = ("Command not found", 1)
        
        with pytest.raises(HomebrewError):
            get_homebrew_path()

    @patch('versiontracker.homebrew.get_homebrew_path')
    @patch('versiontracker.homebrew.run_command')
    def test_get_all_homebrew_casks_cached(self, mock_run_command, mock_get_homebrew_path):
        """Test getting all Homebrew casks when they are cached."""
        # Put test data in cache
        test_casks = [
            {"token": "firefox", "name": "Firefox", "version": "100.0"},
            {"token": "chrome", "name": "Google Chrome", "version": "90.0"},
        ]
        self.test_cache.put("homebrew:all_casks", test_casks, source="homebrew")
        
        # Test function
        result = get_all_homebrew_casks()
        
        # Verify result and that no command was executed
        self.assertEqual(result, test_casks)
        mock_run_command.assert_not_called()
        mock_get_homebrew_path.assert_not_called()

    @patch('versiontracker.homebrew.get_homebrew_path')
    @patch('versiontracker.homebrew.run_command')
    def test_get_all_homebrew_casks_uncached(self, mock_run_command, mock_get_homebrew_path):
        """Test getting all Homebrew casks when they are not cached."""
        # Setup mocks
        mock_get_homebrew_path.return_value = "/usr/local/bin/brew"
        test_casks = [
            {"token": "firefox", "name": "Firefox", "version": "100.0"},
            {"token": "chrome", "name": "Google Chrome", "version": "90.0"},
        ]
        mock_run_command.return_value = (json.dumps({"casks": test_casks}), 0)
        
        # Test function
        result = get_all_homebrew_casks()
        
        # Verify result
        self.assertEqual(result, test_casks)
        mock_run_command.assert_called_once()
        
        # Verify cache was updated
        cached = self.test_cache.get("homebrew:all_casks")
        self.assertEqual(cached, test_casks)

    @patch('versiontracker.homebrew.get_homebrew_path')
    @patch('versiontracker.homebrew.run_command')
    def test_get_cask_info_cached(self, mock_run_command, mock_get_homebrew_path):
        """Test getting cask info when it is cached."""
        # Put test data in cache
        test_cask = {"token": "firefox", "name": "Firefox", "version": "100.0"}
        self.test_cache.put("homebrew:cask:firefox", test_cask, source="homebrew")
        
        # Test function
        result = get_cask_info("firefox")
        
        # Verify result and that no command was executed
        self.assertEqual(result, test_cask)
        mock_run_command.assert_not_called()
        mock_get_homebrew_path.assert_not_called()

    @patch('versiontracker.homebrew.get_homebrew_path')
    @patch('versiontracker.homebrew.run_command')
    def test_get_cask_info_uncached(self, mock_run_command, mock_get_homebrew_path):
        """Test getting cask info when it is not cached."""
        # Setup mocks
        mock_get_homebrew_path.return_value = "/usr/local/bin/brew"
        test_cask = {"token": "firefox", "name": "Firefox", "version": "100.0"}
        mock_run_command.return_value = (json.dumps({"casks": [test_cask]}), 0)
        
        # Test function
        result = get_cask_info("firefox")
        
        # Verify result
        self.assertEqual(result, test_cask)
        mock_run_command.assert_called_once()
        
        # Verify cache was updated
        cached = self.test_cache.get("homebrew:cask:firefox")
        self.assertEqual(cached, test_cask)

    @patch('versiontracker.homebrew.get_homebrew_path')
    @patch('versiontracker.homebrew.run_command')
    def test_search_casks(self, mock_run_command, mock_get_homebrew_path):
        """Test searching for casks."""
        # Setup mocks
        mock_get_homebrew_path.return_value = "/usr/local/bin/brew"
        test_casks = [
            {"token": "firefox", "name": "Firefox", "version": "100.0"},
            {"token": "firefox-developer-edition", "name": "Firefox Developer Edition", "version": "101.0"},
        ]
        mock_run_command.return_value = (json.dumps({"casks": test_casks}), 0)
        
        # Test function
        result = search_casks("firefox")
        
        # Verify result
        self.assertEqual(result, test_casks)
        mock_run_command.assert_called_once()
        
        # Verify cache was updated
        cached = self.test_cache.get("homebrew:search:firefox")
        self.assertEqual(cached, test_casks)

    @patch('versiontracker.homebrew.get_homebrew_path')
    @patch('versiontracker.homebrew.run_command')
    def test_batch_get_cask_info(self, mock_run_command, mock_get_homebrew_path):
        """Test getting info for multiple casks in a batch."""
        # Setup mocks
        mock_get_homebrew_path.return_value = "/usr/local/bin/brew"
        test_casks = [
            {"token": "firefox", "name": "Firefox", "version": "100.0"},
            {"token": "chrome", "name": "Google Chrome", "version": "90.0"},
        ]
        mock_run_command.return_value = (json.dumps({"casks": test_casks}), 0)
        
        # Test function
        result = batch_get_cask_info(["firefox", "chrome"])
        
        # Verify result
        self.assertEqual(result["firefox"], test_casks[0])
        self.assertEqual(result["chrome"], test_casks[1])
        mock_run_command.assert_called_once()
        
        # Verify cache was updated
        cached_firefox = self.test_cache.get("homebrew:cask:firefox")
        cached_chrome = self.test_cache.get("homebrew:cask:chrome")
        self.assertEqual(cached_firefox, test_casks[0])
        self.assertEqual(cached_chrome, test_casks[1])

    @patch('versiontracker.homebrew.get_homebrew_path')
    @patch('versiontracker.homebrew.run_command')
    def test_get_installed_homebrew_casks(self, mock_run_command, mock_get_homebrew_path):
        """Test getting installed Homebrew casks."""
        # Setup mocks
        mock_get_homebrew_path.return_value = "/usr/local/bin/brew"
        test_casks = [
            {"token": "firefox", "name": "Firefox", "version": "100.0"},
            {"token": "chrome", "name": "Google Chrome", "version": "90.0"},
        ]
        mock_run_command.return_value = (json.dumps({"casks": test_casks}), 0)
        
        # Test function
        result = get_installed_homebrew_casks()
        
        # Verify result
        self.assertEqual(result, test_casks)
        mock_run_command.assert_called_once()

    def test_clear_homebrew_cache(self):
        """Test clearing Homebrew cache."""
        # Put test data in cache
        self.test_cache.put("homebrew:all_casks", [{"token": "firefox"}], source="homebrew")
        self.test_cache.put("homebrew:cask:firefox", {"token": "firefox"}, source="homebrew")
        self.test_cache.put("other:key", {"data": "value"}, source="other")
        
        # Clear homebrew cache
        result = clear_homebrew_cache()
        
        # Verify result
        self.assertTrue(result)
        
        # Homebrew cache should be empty
        self.assertIsNone(self.test_cache.get("homebrew:all_casks"))
        self.assertIsNone(self.test_cache.get("homebrew:cask:firefox"))
        
        # Other cache should still exist
        self.assertIsNotNone(self.test_cache.get("other:key"))

    @patch('versiontracker.homebrew.get_homebrew_path')
    @patch('versiontracker.homebrew.run_command')
    def test_get_outdated_homebrew_casks(self, mock_run_command, mock_get_homebrew_path):
        """Test getting outdated Homebrew casks."""
        # Setup mocks
        mock_get_homebrew_path.return_value = "/usr/local/bin/brew"
        test_casks = [
            {"token": "firefox", "name": "Firefox", "installed_versions": ["99.0"], "current_version": "100.0"},
        ]
        mock_run_command.return_value = (json.dumps({"casks": test_casks}), 0)
        
        # Test function
        result = get_outdated_homebrew_casks()
        
        # Verify result
        self.assertEqual(result, test_casks)
        mock_run_command.assert_called_once()

    @patch('versiontracker.homebrew.get_cask_info')
    def test_get_cask_version(self, mock_get_cask_info):
        """Test getting a cask version."""
        # Setup mocks
        mock_get_cask_info.return_value = {"token": "firefox", "version": "100.0"}
        
        # Test function
        result = get_cask_version("firefox")
        
        # Verify result
        self.assertEqual(result, "100.0")
        mock_get_cask_info.assert_called_once_with("firefox")

    @patch('versiontracker.homebrew.get_cask_info')
    def test_get_cask_version_error(self, mock_get_cask_info):
        """Test getting a cask version with error."""
        # Setup mocks
        mock_get_cask_info.side_effect = HomebrewError("Test error")
        
        # Test function
        with pytest.raises(HomebrewError):
            get_cask_version("firefox")


if __name__ == "__main__":
    unittest.main()