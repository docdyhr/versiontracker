"""Test module for network operations.

This module contains tests for network operations using the mock server,
focusing on testing Homebrew-related functionality with simulated
network conditions including timeouts, errors, and malformed responses.
"""

import os
import pytest
import unittest
from unittest.mock import patch, MagicMock

from versiontracker.version import find_matching_cask, check_latest_version
from versiontracker.exceptions import NetworkError, HomebrewError, DataParsingError
from versiontracker.utils import run_command
from tests.mock_homebrew_server import MockHomebrewServer, with_mock_homebrew_server


class TestNetworkOperations(unittest.TestCase):
    """Tests for network operations using the mock server."""
    
    @with_mock_homebrew_server
    def test_find_matching_cask_success(self, mock_server, server_url):
        """Test finding a matching cask with successful network operation."""
        # Add a test cask
        mock_server.add_cask("firefox", "120.0.1", "Web browser")
        
        # Patch the command execution to return mock data
        with patch('versiontracker.version.run_command') as mock_run_command:
            mock_run_command.return_value = (
                0, 
                '{"name": "firefox", "version": "120.0.1", "desc": "Web browser"}', 
                ""
            )
            
            # Test the function
            result = find_matching_cask("Firefox")
            self.assertIsNotNone(result)
            self.assertEqual(result[0], "firefox")
            self.assertEqual(result[1], "120.0.1")
    
    @with_mock_homebrew_server
    def test_find_matching_cask_timeout(self, mock_server, server_url):
        """Test finding a matching cask with network timeout."""
        # Configure server to timeout
        mock_server.set_timeout(True)
        
        # Patch the command execution to simulate timeout
        with patch('versiontracker.version.run_command') as mock_run_command:
            mock_run_command.side_effect = TimeoutError("Connection timed out")
            
            # Test the function
            with pytest.raises(NetworkError):
                find_matching_cask("Firefox")
    
    @with_mock_homebrew_server
    def test_find_matching_cask_error(self, mock_server, server_url):
        """Test finding a matching cask with network error."""
        # Configure server to return an error
        mock_server.set_error_response(True, 500, "Internal Server Error")
        
        # Patch the command execution to simulate error
        with patch('versiontracker.version.run_command') as mock_run_command:
            mock_run_command.return_value = (1, "", "Error: failed to execute command")
            
            # Test the function
            with pytest.raises(HomebrewError):
                find_matching_cask("Firefox")
    
    @with_mock_homebrew_server
    def test_find_matching_cask_malformed(self, mock_server, server_url):
        """Test finding a matching cask with malformed response."""
        # Configure server to return malformed data
        mock_server.set_malformed_response(True)
        
        # Patch the command execution to return malformed data
        with patch('versiontracker.version.run_command') as mock_run_command:
            mock_run_command.return_value = (0, "{malformed json", "")
            
            # Test the function
            with pytest.raises(DataParsingError):
                find_matching_cask("Firefox")
    
    @with_mock_homebrew_server
    def test_check_latest_version_success(self, mock_server, server_url):
        """Test checking latest version with successful network operation."""
        # Add a test cask
        mock_server.add_cask("firefox", "120.0.1", "Web browser")
        
        # Patch the command execution to return mock data
        with patch('versiontracker.version.run_command') as mock_run_command:
            mock_run_command.return_value = (
                0, 
                '{"name": "firefox", "version": "120.0.1", "desc": "Web browser"}', 
                ""
            )
            
            # Test the function
            app_name = "Firefox"
            cask_name = "firefox"
            current_version = "119.0.0"
            
            result = check_latest_version(app_name, cask_name, current_version)
            self.assertEqual(result.app_name, app_name)
            self.assertEqual(result.cask_name, cask_name)
            self.assertEqual(result.current_version, current_version)
            self.assertEqual(result.latest_version, "120.0.1")
            self.assertTrue(result.is_outdated)
    
    @with_mock_homebrew_server
    def test_check_latest_version_timeout(self, mock_server, server_url):
        """Test checking latest version with network timeout."""
        # Configure server to timeout
        mock_server.set_timeout(True)
        
        # Patch the command execution to simulate timeout
        with patch('versiontracker.version.run_command') as mock_run_command:
            mock_run_command.side_effect = TimeoutError("Connection timed out")
            
            # Test the function
            with pytest.raises(NetworkError):
                check_latest_version("Firefox", "firefox", "119.0.0")
    
    @with_mock_homebrew_server
    def test_check_latest_version_with_delay(self, mock_server, server_url):
        """Test checking latest version with delayed response."""
        # Configure server with a short delay (not a timeout)
        mock_server.set_delay(0.5)
        mock_server.add_cask("firefox", "120.0.1", "Web browser")
        
        # Patch the command execution to return mock data after delay
        with patch('versiontracker.version.run_command') as mock_run_command:
            mock_run_command.return_value = (
                0, 
                '{"name": "firefox", "version": "120.0.1", "desc": "Web browser"}', 
                ""
            )
            
            # Test the function
            result = check_latest_version("Firefox", "firefox", "119.0.0")
            self.assertEqual(result.latest_version, "120.0.1")
    
    @with_mock_homebrew_server
    def test_run_command_with_real_timeout(self, mock_server, server_url):
        """Test run_command with a real timeout."""
        # Configure a command that will time out
        command = "sleep 10"  # This will take 10 seconds
        timeout = 0.5  # But we only wait 0.5 seconds
        
        # Test with a real timeout
        with pytest.raises((TimeoutError, Exception)):
            run_command(command, timeout=timeout)
    
    @with_mock_homebrew_server
    def test_check_multiple_casks(self, mock_server, server_url):
        """Test checking multiple casks in sequence."""
        # Add multiple test casks
        mock_server.add_cask("firefox", "120.0.1", "Web browser")
        mock_server.add_cask("chrome", "119.0.0", "Web browser")
        mock_server.add_cask("vscode", "1.85.0", "Code editor")
        
        # Patch the command execution to return mock data
        with patch('versiontracker.version.run_command') as mock_run_command:
            def side_effect(cmd, *args, **kwargs):
                if "firefox" in cmd:
                    return (0, '{"name": "firefox", "version": "120.0.1"}', "")
                elif "chrome" in cmd:
                    return (0, '{"name": "chrome", "version": "119.0.0"}', "")
                elif "vscode" in cmd:
                    return (0, '{"name": "vscode", "version": "1.85.0"}', "")
                return (1, "", "Command not found")
            
            mock_run_command.side_effect = side_effect
            
            # Test with Firefox
            result1 = check_latest_version("Firefox", "firefox", "120.0.0")
            self.assertEqual(result1.latest_version, "120.0.1")
            
            # Test with Chrome
            result2 = check_latest_version("Chrome", "chrome", "119.0.0")
            self.assertEqual(result2.latest_version, "119.0.0")
            self.assertFalse(result2.is_outdated)
            
            # Test with VS Code
            result3 = check_latest_version("Visual Studio Code", "vscode", "1.84.0")
            self.assertEqual(result3.latest_version, "1.85.0")
            self.assertTrue(result3.is_outdated)


if __name__ == "__main__":
    unittest.main()