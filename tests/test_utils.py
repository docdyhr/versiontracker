"""
Test module for utility functions.

This module provides basic tests for utility functions.
"""

import subprocess
import unittest
from unittest.mock import Mock, patch

from versiontracker.exceptions import DataParsingError
from versiontracker.exceptions import TimeoutError as VTTimeoutError
from versiontracker.utils import (
    format_size,
    get_json_data,
    get_shell_json_data,
    get_terminal_width,
    is_homebrew_installed,
    run_command,
    sanitize_filename,
)


class TestFormatSize:
    """Tests for size formatting utility."""

    def test_format_bytes(self):
        """Test formatting of byte sizes."""
        assert format_size(0) == "0 B"
        assert format_size(1) == "1 B"
        assert format_size(1023) == "1023 B"

    def test_format_kilobytes(self):
        """Test formatting of kilobyte sizes."""
        assert format_size(1024) == "1.0 KB"
        assert format_size(1536) == "1.5 KB"
        assert format_size(1024 * 1023) == "1023.0 KB"

    def test_format_megabytes(self):
        """Test formatting of megabyte sizes."""
        assert format_size(1024 * 1024) == "1.0 MB"
        assert format_size(1024 * 1024 * 1.5) == "1.5 MB"

    def test_format_gigabytes(self):
        """Test formatting of gigabyte sizes."""
        assert format_size(1024 * 1024 * 1024) == "1.0 GB"


class TestSanitizeFilename:
    """Tests for filename sanitization."""

    def test_sanitize_normal_filename(self):
        """Test sanitization of normal filenames."""
        assert sanitize_filename("test.txt") == "test.txt"
        assert sanitize_filename("my_file-123.json") == "my_file-123.json"

    def test_sanitize_special_characters(self):
        """Test removal of special characters."""
        assert sanitize_filename("test/file.txt") == "test_file.txt"
        assert sanitize_filename("test:file.txt") == "test_file.txt"
        assert sanitize_filename("test*file?.txt") == "test_file_.txt"

    def test_sanitize_spaces(self):
        """Test handling of spaces."""
        assert sanitize_filename("test file.txt") == "test_file.txt"
        assert sanitize_filename("  test  file  .txt  ") == "test_file_.txt"

    def test_sanitize_empty(self):
        """Test sanitization of empty or invalid names."""
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("   ") == "unnamed"
        assert sanitize_filename("///") == "unnamed"


class TestTerminalWidth:
    """Tests for terminal width detection."""

    def test_get_terminal_width(self):
        """Test that terminal width returns a reasonable value."""
        width = get_terminal_width()
        assert isinstance(width, int)
        assert width > 0
        # Most terminals are at least 40 chars wide
        assert width >= 40


class TestHomebrewDetection(unittest.TestCase):
    """Tests for Homebrew detection."""

    def test_is_homebrew_installed(self):
        """Test Homebrew installation check."""
        # This test just verifies the function runs without error
        # The actual result depends on the system
        result = is_homebrew_installed()
        assert isinstance(result, bool)

    @patch("versiontracker.utils.subprocess.Popen")
    def test_run_command_success(self, mock_popen):
        """Test run_command with successful execution."""
        mock_process = Mock()
        mock_process.communicate.return_value = (b"test output", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        output, returncode = run_command("test command")

        self.assertEqual(output, b"test output")  # run_command returns bytes
        self.assertEqual(returncode, 0)

    @patch("versiontracker.utils.subprocess.Popen")
    def test_run_command_timeout(self, mock_popen):
        """Test run_command with timeout."""
        mock_process = Mock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired("test command", 30)
        mock_popen.return_value = mock_process

        with self.assertRaises(VTTimeoutError):
            run_command("test command", timeout=30)

    @patch("versiontracker.utils.subprocess.Popen")
    def test_run_command_permission_error(self, mock_popen):
        """Test run_command with permission error."""
        mock_popen.side_effect = PermissionError("Permission denied")

        with self.assertRaises(PermissionError):
            run_command("test command")

    @patch("versiontracker.utils.subprocess.Popen")
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
