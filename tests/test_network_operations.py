"""Test module for network operations.

This module contains tests for network operations using the mock server,
focusing on testing Homebrew-related functionality with simulated
network conditions including timeouts, errors, and malformed responses.
"""

import os
import subprocess
import unittest
from unittest.mock import patch

import pytest

from tests.mock_homebrew_server import with_mock_homebrew_server
from versiontracker.exceptions import (
    DataParsingError,
    HomebrewError,
    NetworkError,
)
from versiontracker.exceptions import TimeoutError as VTTimeoutError
from versiontracker.utils import run_command
from versiontracker.version import check_latest_version, find_matching_cask


def _is_ci_environment():
    """Check if we're in a CI environment."""
    return any(os.getenv(var) for var in ["CI", "GITHUB_ACTIONS", "TRAVIS", "CIRCLECI"])


class TestNetworkOperations(unittest.TestCase):
    """Tests for network operations using the mock server."""

    @with_mock_homebrew_server
    def test_find_matching_cask_success(self, mock_server, server_url):
        """Test finding a matching cask with successful network operation."""
        # Add a test cask
        mock_server.add_cask("firefox", "120.0.1", "Web browser")

        # Patch the subprocess execution to return mock data
        with patch("subprocess.run") as mock_subprocess:
            from subprocess import CompletedProcess

            mock_subprocess.return_value = CompletedProcess(
                args=["brew", "search", "--cask"],
                returncode=0,
                stdout="firefox\nchrome\nvscode",
                stderr="",
            )

            # Test the function
            result = find_matching_cask("Firefox")
            self.assertIsNotNone(result)
            self.assertEqual(result, "firefox")

    @with_mock_homebrew_server
    def test_find_matching_cask_timeout(self, mock_server, server_url):
        """Test finding a matching cask with network timeout."""
        # Configure server to timeout
        mock_server.set_timeout(True)

        # Patch subprocess.run to simulate timeout
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.side_effect = subprocess.TimeoutExpired(cmd=["brew", "search", "--cask"], timeout=60)

            # Test the function - should return None for timeout, not raise exception
            result = find_matching_cask("Firefox")
            self.assertIsNone(result)

    @with_mock_homebrew_server
    def test_find_matching_cask_error(self, mock_server, server_url):
        """Test finding a matching cask with network error."""
        # Configure server to return an error
        mock_server.set_error_response(True, 500, "Internal Server Error")

        # Patch subprocess.run to simulate command error
        with patch("subprocess.run") as mock_subprocess:
            from subprocess import CompletedProcess

            mock_subprocess.return_value = CompletedProcess(
                args=["brew", "search", "--cask"],
                returncode=1,
                stdout="",
                stderr="Error: failed to execute command",
            )

            # Test the function - should return None for error
            result = find_matching_cask("Firefox")
            self.assertIsNone(result)

    @with_mock_homebrew_server
    def test_find_matching_cask_malformed(self, mock_server, server_url):
        """Test finding a matching cask with malformed response."""
        # Configure server to return malformed data
        mock_server.set_malformed_response(True)

        # Patch subprocess.run to return valid cask data that find_matching_cask can process
        with patch("subprocess.run") as mock_subprocess:
            from subprocess import CompletedProcess

            mock_subprocess.return_value = CompletedProcess(
                args=["brew", "search", "--cask"],
                returncode=0,
                stdout="firefox\nchrome\nvscode",
                stderr="",
            )

            # Test the function - should find a match despite malformed server response
            result = find_matching_cask("Firefox")
            self.assertEqual(result, "firefox")

    @pytest.mark.skipif(_is_ci_environment(), reason="Skipping brew-dependent test in CI environment")
    @with_mock_homebrew_server
    def test_check_latest_version_success(self, mock_server, server_url):
        """Test checking latest version with successful network operation."""
        # Add a test cask
        mock_server.add_cask("firefox", "120.0.1", "Web browser")

        # Mock get_homebrew_cask_info to return version info
        with patch("versiontracker.version_legacy.get_homebrew_cask_info") as mock_get_info:
            mock_get_info.return_value = {
                "name": "firefox",
                "version": "120.0.1",
                "desc": "Web browser",
            }

            # Test the function
            result = check_latest_version("Firefox")
            self.assertEqual(result, "120.0.1")

    @pytest.mark.skipif(_is_ci_environment(), reason="Skipping brew-dependent test in CI environment")
    @with_mock_homebrew_server
    def test_check_latest_version_timeout(self, mock_server, server_url):
        """Test checking latest version with network timeout."""
        # Configure server to timeout
        mock_server.set_timeout(True)

        # Mock get_homebrew_cask_info to raise timeout error
        with patch("versiontracker.version_legacy.get_homebrew_cask_info") as mock_get_info:
            mock_get_info.side_effect = VTTimeoutError("Connection timed out")

            # Test the function - should raise timeout error
            with pytest.raises(VTTimeoutError):
                check_latest_version("Firefox")

    @pytest.mark.skipif(_is_ci_environment(), reason="Skipping brew-dependent test in CI environment")
    @with_mock_homebrew_server
    def test_check_latest_version_with_delay(self, mock_server, server_url):
        """Test checking latest version with delayed response."""
        # Configure server with a short delay (not a timeout)
        mock_server.set_delay(0.5)
        mock_server.add_cask("firefox", "120.0.1", "Web browser")

        # Mock get_homebrew_cask_info to return version info
        with patch("versiontracker.version_legacy.get_homebrew_cask_info") as mock_get_info:
            mock_get_info.return_value = {
                "name": "firefox",
                "version": "120.0.1",
                "desc": "Web browser",
            }

            # Test the function
            result = check_latest_version("Firefox")
            self.assertEqual(result, "120.0.1")

    @with_mock_homebrew_server
    def test_run_command_with_real_timeout(self, mock_server, server_url):
        """Test run_command with a real timeout."""
        # Configure a command that will time out
        command = "sleep 10"  # This will take 10 seconds
        timeout = 1  # But we only wait 1 second (changed from 0.5 to int)

        # Test with a real timeout
        with pytest.raises((VTTimeoutError, Exception)):
            run_command(command, timeout=timeout)

    @pytest.mark.skipif(_is_ci_environment(), reason="Skipping brew-dependent test in CI environment")
    @with_mock_homebrew_server
    def test_check_multiple_casks(self, mock_server, server_url):
        """Test checking multiple casks in sequence."""
        # Add multiple test casks
        mock_server.add_cask("firefox", "120.0.1", "Web browser")
        mock_server.add_cask("chrome", "119.0.0", "Web browser")
        mock_server.add_cask("vscode", "1.85.0", "Code editor")

        # Mock get_homebrew_cask_info with side effect for different apps
        with patch("versiontracker.version_legacy.get_homebrew_cask_info") as mock_get_info:

            def side_effect(app_name):
                if "firefox" in app_name.lower():
                    return {"name": "firefox", "version": "120.0.1"}
                elif "chrome" in app_name.lower():
                    return {"name": "chrome", "version": "119.0.0"}
                elif "visual studio code" in app_name.lower() or "vscode" in app_name.lower():
                    return {"name": "vscode", "version": "1.85.0"}
                return None

            mock_get_info.side_effect = side_effect

            # Test with Firefox
            result1 = check_latest_version("Firefox")
            self.assertEqual(result1, "120.0.1")

            # Test with Chrome
            result2 = check_latest_version("Chrome")
            self.assertEqual(result2, "119.0.0")

            # Test with VS Code
            result3 = check_latest_version("Visual Studio Code")
            self.assertEqual(result3, "1.85.0")


if __name__ == "__main__":
    unittest.main()
