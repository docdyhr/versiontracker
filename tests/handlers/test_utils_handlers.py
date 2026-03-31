"""Test module for the utils handlers.

This module contains tests for the utility handler functions
in the versiontracker.handlers.utils_handlers module.
"""

from unittest import mock

from versiontracker.handlers.utils_handlers import (
    safe_function_call,
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


class TestSafeFunctionCall:
    """Tests for safe_function_call()."""

    def test_success_returns_result(self):
        result = safe_function_call(lambda: 42)
        assert result == 42

    def test_exception_returns_default(self):
        result = safe_function_call(lambda: 1 / 0, default_value="fallback")
        assert result == "fallback"

    def test_custom_default_value(self):
        result = safe_function_call(lambda: [][0], default_value=-1)
        assert result == -1

    def test_passes_args_and_kwargs(self):
        result = safe_function_call(lambda x, y=0: x + y, 10, y=5)
        assert result == 15


# ---------------------------------------------------------------------------
# warning_filter / WarningFilter — uncovered branches (lines 92-119)
# ---------------------------------------------------------------------------


class TestSuppressConsoleWarningsInternals:
    """Tests for warning_filter() inner branches via suppress_console_warnings()."""

    def _get_warning_filter(self):
        """Install suppress_console_warnings and return the attached WarningFilter."""
        import sys
        from unittest.mock import MagicMock

        with mock.patch("logging.getLogger") as mock_get_logger, mock.patch("warnings.filterwarnings"):
            mock_logger = MagicMock()
            mock_handler = MagicMock()
            # stream must equal sys.stderr to pass the guard in suppress_console_warnings
            mock_handler.stream = sys.stderr
            mock_logger.handlers = [mock_handler]
            mock_get_logger.return_value = mock_logger

            suppress_console_warnings()
            return mock_handler.addFilter.call_args[0][0]

    def test_warning_filter_versiontracker_filename_not_suppressed(self):
        """Warnings from versiontracker source files are always shown (return True)."""
        import logging
        from unittest.mock import MagicMock

        added_filter = self._get_warning_filter()

        record = MagicMock()
        record.levelno = logging.WARNING
        record.filename = "/path/to/versiontracker/config.py"
        record.lineno = 1
        record.getMessage.return_value = "some warning"

        assert added_filter.filter(record) is True

    def test_warning_filter_deprecation_from_external_suppressed(self):
        """UserWarning from external code is suppressed (return False)."""
        import logging
        from unittest.mock import MagicMock

        added_filter = self._get_warning_filter()

        record = MagicMock()
        record.levelno = logging.WARNING
        record.filename = "/site-packages/third_party/lib.py"
        record.lineno = 1
        record.getMessage.return_value = "deprecated"
        # WarningFilter.filter() passes UserWarning as category → matches warn_type list → False
        assert added_filter.filter(record) is False

    def test_warning_filter_non_warning_level_passes_through(self):
        """Non-WARNING log records always pass through WarningFilter (return True)."""
        import logging
        from unittest.mock import MagicMock

        added_filter = self._get_warning_filter()

        record = MagicMock()
        record.levelno = logging.INFO  # not WARNING
        assert added_filter.filter(record) is True
