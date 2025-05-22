"""Tests for the __main__ module and handler functions."""

import logging
import sys
import unittest
from unittest.mock import MagicMock, call, patch

from versiontracker.__main__ import (
    _suppress_console_warnings as suppress_console_warnings,
)
from versiontracker.__main__ import setup_logging
from versiontracker.export import export_data
from versiontracker.handlers.export_handlers import handle_export
from versiontracker.handlers.ui_handlers import get_status_color, get_status_icon


class TestMain(unittest.TestCase):
    """Test cases for the __main__ module."""

    @patch("versiontracker.handlers.ui_handlers.create_progress_bar")
    def test_get_status_icon_with_color(self, mock_progress_bar):
        """Test getting status icons with color support."""
        # Setup the mock for color support
        mock_color = MagicMock()
        mock_progress_bar.return_value.color.return_value = mock_color
        mock_color.return_value = "✅"

        # Test different status values
        self.assertEqual(get_status_icon("uptodate"), "✅")
        self.assertEqual(get_status_icon("outdated"), str(mock_color("🔄")))
        self.assertEqual(get_status_icon("not_found"), str(mock_color("❓")))
        self.assertEqual(get_status_icon("error"), str(mock_color("❌")))
        self.assertEqual(get_status_icon("unknown"), "")

        # Verify the colors were called with the right values
        mock_progress_bar.return_value.color.assert_any_call("green")
        mock_progress_bar.return_value.color.assert_any_call("yellow")
        mock_progress_bar.return_value.color.assert_any_call("blue")
        mock_progress_bar.return_value.color.assert_any_call("red")

    @patch(
        "versiontracker.handlers.ui_handlers.create_progress_bar",
        side_effect=Exception("No color support"),
    )
    def test_get_status_icon_without_color(self, mock_progress_bar):
        """Test getting status icons with no color support."""
        # Test fallback to text-based icons
        self.assertEqual(get_status_icon("uptodate"), "[OK]")
        self.assertEqual(get_status_icon("outdated"), "[OUTDATED]")
        self.assertEqual(get_status_icon("not_found"), "[NOT FOUND]")
        self.assertEqual(get_status_icon("error"), "[ERROR]")
        self.assertEqual(get_status_icon("unknown"), "")

    @patch("versiontracker.handlers.ui_handlers.create_progress_bar")
    def test_get_status_color(self, mock_progress_bar):
        """Test getting status colors."""
        # Setup the mock
        mock_color_func = MagicMock()
        mock_progress_bar.return_value.color.return_value = mock_color_func

        # Test different status values
        get_status_color("uptodate")("test")
        get_status_color("outdated")("test")
        get_status_color("newer")("test")
        get_status_color("unknown")("test")

        # Verify the colors were called with the right values
        mock_progress_bar.return_value.color.assert_any_call("green")
        mock_progress_bar.return_value.color.assert_any_call("red")
        mock_progress_bar.return_value.color.assert_any_call("cyan")
        mock_progress_bar.return_value.color.assert_any_call("yellow")

    @patch("versiontracker.handlers.export_handlers.export_data")
    def test_handle_export_success(self, mock_export_data):
        """Test successful data export."""
        mock_export_data.return_value = "export result"

        # Test export without a filename (stdout)
        result = handle_export({"test": "data"}, "json")
        self.assertEqual(result, "export result")
        mock_export_data.assert_called_with({"test": "data"}, "json", None)

        # Test export with a filename
        result = handle_export({"test": "data"}, "csv", "output.csv")
        self.assertEqual(result, 0)
        mock_export_data.assert_called_with({"test": "data"}, "csv", "output.csv")

    @patch(
        "versiontracker.handlers.export_handlers.export_data",
        side_effect=ValueError("Invalid format"),
    )
    @patch("versiontracker.handlers.export_handlers.create_progress_bar")
    def test_handle_export_value_error(self, mock_progress_bar, mock_export_data):
        """Test export with ValueError."""
        result = handle_export({"test": "data"}, "invalid_format")
        self.assertEqual(result, 1)  # Should return error code 1

    @patch(
        "versiontracker.handlers.export_handlers.export_data",
        side_effect=PermissionError("Permission denied"),
    )
    @patch("versiontracker.handlers.export_handlers.create_progress_bar")
    def test_handle_export_permission_error(self, mock_progress_bar, mock_export_data):
        """Test export with PermissionError."""
        result = handle_export({"test": "data"}, "json", "/root/test.json")
        self.assertEqual(result, 1)  # Should return error code 1

    @patch("versiontracker.__main__.logging")
    @patch("versiontracker.__main__.Path")
    @patch("versiontracker.__main__.get_config")
    def test_setup_logging(self, mock_get_config, mock_path, mock_logging):
        """Test logging setup."""
        # Mock options object
        mock_options = MagicMock()
        mock_options.debug = True

        # Mock Path
        mock_home = MagicMock()
        mock_log_dir = MagicMock()
        mock_path.home.return_value = mock_home
        mock_home.__truediv__.return_value = mock_home
        mock_home.__truediv__.return_value.__truediv__.return_value = mock_log_dir
        mock_log_dir.__truediv__.return_value = mock_log_dir

        # Call the function
        setup_logging(mock_options)

        # Verify mkdir was called
        mock_log_dir.mkdir.assert_called_with(parents=True, exist_ok=True)

        # Verify logging was configured
        mock_logging.basicConfig.assert_called_once()

    @patch("logging.getLogger")
    def test_suppress_console_warnings(self, mock_get_logger):
        """Test that console warnings are suppressed correctly."""
        # Setup mock logger and handler
        mock_handler = MagicMock(spec=logging.StreamHandler)
        mock_handler.stream = (
            sys.stderr
        )  # Add stream attribute to avoid attribute error
        mock_root_logger = MagicMock()
        mock_root_logger.handlers = [mock_handler]
        mock_get_logger.return_value = mock_root_logger

        # Call the function
        suppress_console_warnings()

        # Verify that a filter was added to the StreamHandler
        mock_handler.addFilter.assert_called_once()


if __name__ == "__main__":
    unittest.main()
