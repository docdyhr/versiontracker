"""Tests for app store related functions in the apps module."""

import unittest
from unittest.mock import MagicMock, patch

from versiontracker.apps import (
    is_app_in_app_store,
)
from versiontracker.exceptions import NetworkError, BrewTimeoutError


class TestAppStore(unittest.TestCase):
    """Test cases for app store functions."""
    
    @patch("versiontracker.apps.run_command")
    def test_is_app_in_app_store_found(self, mock_run_command):
        """Test is_app_in_app_store when app is found in App Store."""
        # Mock successful command execution with results
        mock_run_command.return_value = (
            "1234567890 com.example.app Test App (1.0.0)",
            0
        )
        
        # Call the function with test data
        result = is_app_in_app_store("Test App")
        
        # Verify result is True when app is found
        self.assertTrue(result)
        
        # Verify the command that was run
        mock_run_command.assert_called_once()
        
    @patch("versiontracker.apps.run_command")
    def test_is_app_in_app_store_not_found(self, mock_run_command):
        """Test is_app_in_app_store when app is not found."""
        # Mock command execution with no results
        mock_run_command.return_value = ("No results found", 0)
        
        # Call the function
        result = is_app_in_app_store("Non-existent App")
        
        # Verify result is False when app is not found
        self.assertFalse(result)
        
    @patch("versiontracker.apps.run_command")
    def test_is_app_in_app_store_error(self, mock_run_command):
        """Test is_app_in_app_store when command fails."""
        # Mock command failure
        mock_run_command.return_value = ("Error executing command", 1)
        
        # Call the function
        result = is_app_in_app_store("Some App")
        
        # Verify result is False when command fails
        self.assertFalse(result)
        
    @patch("versiontracker.apps.run_command")
    def test_is_app_in_app_store_exception(self, mock_run_command):
        """Test is_app_in_app_store exception handling."""
        # Mock run_command to raise an exception
        mock_run_command.side_effect = Exception("Command execution failed")
        
        # Call the function
        result = is_app_in_app_store("Some App")
        
        # Verify result is False when exception occurs
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
