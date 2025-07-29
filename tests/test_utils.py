"""Tests for the utils module."""

import json
import os
import subprocess
import tempfile
import time
import unittest
from unittest.mock import Mock, mock_open, patch

from versiontracker.exceptions import (
    DataParsingError,
    FileNotFoundError,
    NetworkError,
    PermissionError,
    TimeoutError,
)
from versiontracker.utils import (
    APP_CACHE_FILE,
    APP_CACHE_TTL,
    SYSTEM_PROFILER_CMD,
    RateLimiter,
    get_json_data,
    get_shell_json_data,
    normalise_name,
    run_command,
    setup_logging,
)


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

    @patch("logging.basicConfig")
    def test_setup_logging_debug(self, mock_basic_config):
        """Test setup_logging with debug enabled."""
        setup_logging(debug=True)
        mock_basic_config.assert_called_once()
        # Check that DEBUG level was used
        call_args = mock_basic_config.call_args
        self.assertIn("level", call_args.kwargs)

    @patch("logging.basicConfig")
    def test_setup_logging_no_debug(self, mock_basic_config):
        """Test setup_logging with debug disabled."""
        setup_logging(debug=False)
        mock_basic_config.assert_called_once()

    @patch("subprocess.Popen")
    def test_run_command_success(self, mock_popen):
        """Test run_command with successful execution."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("test output", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        output, returncode = run_command("test command")

        self.assertEqual(output, "test output")
        self.assertEqual(returncode, 0)

    @patch("subprocess.Popen")
    def test_run_command_timeout(self, mock_popen):
        """Test run_command with timeout."""
        mock_process = Mock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired("test command", 30)
        mock_popen.return_value = mock_process

        with self.assertRaises(TimeoutError):
            run_command("test command", timeout=30)

    @patch("subprocess.Popen")
    def test_run_command_permission_error(self, mock_popen):
        """Test run_command with permission error."""
        mock_popen.side_effect = PermissionError("Permission denied")

        with self.assertRaises(PermissionError):
            run_command("test command")

    @patch("subprocess.Popen")
    def test_run_command_file_not_found(self, mock_popen):
        """Test run_command with file not found."""
        mock_popen.side_effect = FileNotFoundError("Command not found")

        with self.assertRaises(FileNotFoundError):
            run_command("test command")

    @patch("versiontracker.utils.run_command")
    def test_get_json_data_success(self, mock_run_command):
        """Test get_json_data with successful execution."""
        mock_run_command.return_value = ('{"test": "data"}', 0)

        result = get_json_data("test command")

        self.assertEqual(result, {"test": "data"})

    @patch("versiontracker.utils.run_command")
    def test_get_json_data_invalid_json(self, mock_run_command):
        """Test get_json_data with invalid JSON."""
        mock_run_command.return_value = ("invalid json", 0)

        with self.assertRaises(DataParsingError):
            get_json_data("test command")

    @patch("versiontracker.utils.run_command")
    def test_get_json_data_command_failed(self, mock_run_command):
        """Test get_json_data with command failure."""
        mock_run_command.side_effect = subprocess.CalledProcessError(1, "test", "error")

        with self.assertRaises(DataParsingError):
            get_json_data("test command")

    @patch("versiontracker.utils.run_command")
    def test_get_shell_json_data_success(self, mock_run_command):
        """Test get_shell_json_data with success."""
        mock_run_command.return_value = ('{"test": "data"}', 0)

        result = get_shell_json_data("test command")

        self.assertEqual(result, {"test": "data"})

    @patch("versiontracker.utils.run_command")
    def test_get_shell_json_data_command_failed(self, mock_run_command):
        """Test get_shell_json_data with command failure."""
        mock_run_command.return_value = ("error output", 1)

        with self.assertRaises(DataParsingError):
            get_shell_json_data("test command")

    @patch("versiontracker.utils.run_command")
    def test_get_shell_json_data_invalid_json(self, mock_run_command):
        """Test get_shell_json_data with invalid JSON."""
        mock_run_command.return_value = ("invalid json", 0)

        with self.assertRaises(DataParsingError):
            get_shell_json_data("test command")


if __name__ == "__main__":
    unittest.main()
