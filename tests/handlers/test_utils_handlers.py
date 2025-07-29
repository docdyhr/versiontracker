"""Test module for the utils handlers.

This module contains tests for the utility handler functions
in the versiontracker.handlers.utils_handlers module.
"""

from unittest import mock

from versiontracker.handlers.utils_handlers import (
    setup_logging,
    suppress_console_warnings,
)


class TestUtilsHandlers:
    """Tests for the utility handlers."""

    @mock.patch("versiontracker.handlers.utils_handlers.logging")
    def test_setup_logging_basic(self, mock_logging):
        """Test basic setup of logging."""
        # Call the function with minimal arguments
        setup_logging(level=20)  # INFO level

        # Verify logging was configured
        mock_root_logger = mock_logging.getLogger.return_value
        mock_root_logger.setLevel.assert_called_once_with(20)

        # Verify formatter was created
        assert mock_logging.Formatter.call_count == 1

    @mock.patch("versiontracker.handlers.utils_handlers.logging")
    def test_setup_logging_with_files(self, mock_logging):
        """Test setup of logging with file handlers."""
        # Call the function with file handlers
        setup_logging(level=10, log_file="test.log", warnings_file="warnings.log")

        # Verify file handlers were created
        assert mock_logging.FileHandler.call_count >= 2

        # Verify handlers were added to logger
        mock_root_logger = mock_logging.getLogger.return_value
        assert mock_root_logger.addHandler.call_count >= 2

    @mock.patch("warnings.filterwarnings")
    def test_suppress_console_warnings(self, mock_filter_warnings):
        """Test suppressing console warnings."""
        # Call the function
        suppress_console_warnings()

        # Verify warnings.filterwarnings was called with the expected parameters
        mock_filter_warnings.assert_called_with("default")

    @mock.patch("sys.stderr")
    @mock.patch("logging.getLogger")
    @mock.patch("warnings.filterwarnings")
    def test_suppress_console_warnings_with_handlers(self, mock_filter_warnings, mock_get_logger, mock_stderr):
        """Test suppressing console warnings with handlers."""
        # Setup the mock logger and handler
        mock_logger = mock.MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_handler = mock.MagicMock()
        mock_logger.handlers = [mock_handler]
        mock_handler.stream = mock_stderr

        # Call the function
        suppress_console_warnings()

        # Verify filter was added to handler
        mock_handler.addFilter.assert_called_once()
