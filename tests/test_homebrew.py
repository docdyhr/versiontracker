"""Tests for the get_homebrew_casks function in the apps module."""

import unittest
from unittest.mock import MagicMock, patch

from versiontracker.exceptions import BrewTimeoutError, HomebrewError, NetworkError


class TestHomebrew(unittest.TestCase):
    """Test cases for get_homebrew_casks functions."""

    def setUp(self):
        """Set up the test environment."""
        import versiontracker.apps

        # Store original function to restore later
        self.original_get_casks = versiontracker.apps.get_homebrew_casks

        # Clear the cache by directly setting it to None
        versiontracker.apps._apps_main._brew_casks_cache = None

        # Clear the function cache if it exists
        if hasattr(versiontracker.apps._apps_main.get_homebrew_casks, "cache_clear"):
            versiontracker.apps._apps_main.get_homebrew_casks.cache_clear()

    def tearDown(self):
        """Restore the original function."""
        import versiontracker.apps

        versiontracker.apps.get_homebrew_casks = self.original_get_casks
        # Clear the cache again to avoid interfering with other tests
        versiontracker.apps._apps_main._brew_casks_cache = None

    @patch("versiontracker.config.get_config")
    @patch("versiontracker.apps._apps_main.run_command")
    def test_get_homebrew_casks_success(self, mock_run_command, mock_get_config):
        """Test successful retrieval of Homebrew casks."""
        import versiontracker.apps

        # Set up the mocks - ensure getattr works properly
        mock_config = MagicMock()
        # Set the attribute directly and configure getattr behavior
        mock_config.configure_mock(brew_path="/usr/local/bin/brew")
        mock_get_config.return_value = mock_config

        # Mock run_command to return a list of casks
        mock_run_command.return_value = ("cask1\ncask2\ncask3", 0)

        # Call the function
        casks = versiontracker.apps.get_homebrew_casks()

        # Verify the expected command was run (uses default BREW_PATH since getattr falls back)
        mock_run_command.assert_called_once_with("brew list --cask", timeout=30)

        # Check the result
        self.assertEqual(casks, ["cask1", "cask2", "cask3"])

    @patch("versiontracker.config.get_config")
    @patch("versiontracker.apps._apps_main.run_command")
    def test_get_homebrew_casks_empty(self, mock_run_command, mock_get_config):
        """Test when no casks are installed."""
        import versiontracker.apps

        # Set up the mocks - ensure getattr works properly
        mock_config = MagicMock()
        # Set the attribute directly and configure getattr behavior
        mock_config.configure_mock(brew_path="/usr/local/bin/brew")
        mock_get_config.return_value = mock_config

        # Mock run_command to return empty output
        mock_run_command.return_value = ("", 0)

        # Call the function
        casks = versiontracker.apps.get_homebrew_casks()

        # Check the result
        self.assertEqual(casks, [])

    @patch("versiontracker.config.get_config")
    @patch("versiontracker.apps._apps_main.run_command")
    def test_get_homebrew_casks_error(self, mock_run_command, mock_get_config):
        """Test error handling for Homebrew command failures."""
        import versiontracker.apps

        # Set up the mocks - ensure getattr works properly
        mock_config = MagicMock()
        # Set the attribute directly and configure getattr behavior
        mock_config.configure_mock(brew_path="/usr/local/bin/brew")
        mock_get_config.return_value = mock_config

        # Mock run_command to return an error
        mock_run_command.return_value = ("Error: command failed", 1)

        # Test that HomebrewError is raised
        with self.assertRaises(HomebrewError):
            versiontracker.apps.get_homebrew_casks()

    @patch("versiontracker.config.get_config")
    @patch("versiontracker.apps._apps_main.run_command")
    def test_get_homebrew_casks_network_error(self, mock_run_command, mock_get_config):
        """Test network error handling."""
        import versiontracker.apps

        # Set up the mocks - ensure getattr works properly
        mock_config = MagicMock()
        # Set the attribute directly and configure getattr behavior
        mock_config.configure_mock(brew_path="/usr/local/bin/brew")
        mock_get_config.return_value = mock_config

        # Mock run_command to raise NetworkError
        mock_run_command.side_effect = NetworkError("Network unavailable")

        # Test that NetworkError is re-raised
        with self.assertRaises(NetworkError):
            versiontracker.apps.get_homebrew_casks()

    @patch("versiontracker.config.get_config")
    @patch("versiontracker.apps.run_command")
    def test_get_homebrew_casks_timeout(self, mock_run_command, mock_get_config):
        """Test timeout error handling."""
        import versiontracker.apps

        # Set up the mocks - ensure getattr works properly
        mock_config = MagicMock()
        # Set the attribute directly and configure getattr behavior
        mock_config.configure_mock(brew_path="/usr/local/bin/brew")
        mock_get_config.return_value = mock_config

        # Mock run_command to raise BrewTimeoutError
        mock_run_command.side_effect = BrewTimeoutError("Operation timed out")

        # Test that BrewTimeoutError is re-raised
        with self.assertRaises(BrewTimeoutError):
            versiontracker.apps.get_homebrew_casks()


if __name__ == "__main__":
    unittest.main()
