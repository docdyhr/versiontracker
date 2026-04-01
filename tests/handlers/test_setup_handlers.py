"""Test module for the setup handlers.

This module contains tests for the setup handler functions
in the versiontracker.handlers.setup_handlers module.
"""

import logging
from unittest import mock

from versiontracker.handlers.setup_handlers import (
    handle_configure_from_options,
    handle_initialize_config,
    handle_setup_logging,
)


class TestSetupHandlers:
    """Tests for the setup handlers."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset logging to default state before each test
        logging.root.handlers = []
        logging.root.setLevel(logging.WARNING)

    @mock.patch("versiontracker.handlers.setup_handlers.Config")
    @mock.patch("versiontracker.handlers.setup_handlers.get_config")
    @mock.patch("versiontracker.handlers.setup_handlers.logging")
    def test_handle_initialize_config_success(self, mock_logging, mock_get_config, mock_config_class):
        """Test successful config initialization."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.config = "test_config.yaml"

        # Mock the Config constructor to do nothing
        mock_config_class.side_effect = None

        # Execute
        result = handle_initialize_config(mock_options)

        # Assert
        assert result == 0
        # We're just checking the success case, not the specific calls

    @mock.patch("versiontracker.handlers.setup_handlers.Config")
    @mock.patch("versiontracker.handlers.setup_handlers.get_config")
    @mock.patch("versiontracker.handlers.setup_handlers.logging")
    def test_handle_initialize_config_no_config_file(self, mock_logging, mock_get_config, mock_config_class):
        """Test config initialization without a config file."""
        # Setup
        mock_options = mock.MagicMock()
        # Ensure config attribute doesn't exist
        mock_options.config = None

        # Mock the Config constructor to do nothing
        mock_config_class.side_effect = None

        # Execute
        result = handle_initialize_config(mock_options)

        # Assert
        assert result == 0
        # We're just checking the success case, not the specific calls

    @mock.patch("versiontracker.handlers.setup_handlers.Config")
    @mock.patch("versiontracker.handlers.setup_handlers.get_config")
    @mock.patch("versiontracker.handlers.setup_handlers.logging")
    def test_handle_initialize_config_error(self, mock_logging, mock_get_config, mock_config_class):
        """Test error handling during config initialization."""
        # Setup
        mock_options = mock.MagicMock()
        mock_get_config.side_effect = Exception("Test error")
        mock_config_class.side_effect = Exception("Another error")

        # Execute
        result = handle_initialize_config(mock_options)

        # Assert
        assert result == 1
        mock_logging.error.assert_called_once()

    @mock.patch("versiontracker.handlers.setup_handlers.get_config")
    @mock.patch("versiontracker.handlers.setup_handlers.logging")
    def test_handle_configure_from_options_success(self, mock_logging, mock_get_config):
        """Test successful configuration from options."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.no_color = True
        mock_options.no_progress = True
        mock_options.no_adaptive_rate = True

        mock_config = mock.MagicMock()
        mock_get_config.return_value = mock_config

        # Execute
        result = handle_configure_from_options(mock_options)

        # Assert config.set() was called with the canonical keys
        assert result == 0
        mock_config.set.assert_any_call("ui.use_color", False)
        mock_config.set.assert_any_call("no_progress", True)
        mock_config.set.assert_any_call("ui.adaptive_rate_limiting", False)

    @mock.patch("versiontracker.handlers.setup_handlers.get_config")
    @mock.patch("versiontracker.handlers.setup_handlers.logging")
    def test_handle_configure_from_options_error(self, mock_logging, mock_get_config):
        """Test error handling during configuration from options."""
        # Setup
        mock_options = mock.MagicMock()
        mock_get_config.side_effect = Exception("Test error")

        # Execute
        result = handle_configure_from_options(mock_options)

        # Assert
        assert result == 1
        mock_logging.error.assert_called_once()

    @mock.patch("versiontracker.handlers.setup_handlers.logging")
    def test_handle_setup_logging_debug_level_1(self, mock_logging):
        """Test setting up logging with debug level 1."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.debug = 1

        # Mock logging.INFO with an integer
        mock_logging.INFO = 20

        # Execute
        handle_setup_logging(mock_options)

        # Assert
        mock_logging.basicConfig.assert_called_once_with(level=20)
        mock_logging.debug.assert_called_once()

    @mock.patch("versiontracker.handlers.setup_handlers.logging")
    def test_handle_setup_logging_debug_level_2(self, mock_logging):
        """Test setting up logging with debug level 2."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.debug = 2

        # Mock logging.DEBUG with an integer
        mock_logging.DEBUG = 10

        # Execute
        handle_setup_logging(mock_options)

        # Assert
        mock_logging.basicConfig.assert_called_once_with(level=10)
        mock_logging.debug.assert_called_once()

    @mock.patch("versiontracker.handlers.setup_handlers.logging")
    def test_handle_setup_logging_no_debug(self, mock_logging):
        """Test setting up logging without debug."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.debug = 0

        # Mock logging.WARNING with an integer
        mock_logging.WARNING = 30

        # Execute
        handle_setup_logging(mock_options)

        # Assert
        mock_logging.basicConfig.assert_called_once_with(level=30)
        mock_logging.debug.assert_called_once()

    @mock.patch("versiontracker.handlers.setup_handlers.logging")
    def test_handle_setup_logging_error(self, mock_logging):
        """Test error handling during logging setup."""
        # Setup
        mock_options = mock.MagicMock()
        # Only mock the first call to raise exception
        mock_logging.basicConfig.side_effect = Exception("First error")

        # Execute — should not raise, errors are handled internally
        handle_setup_logging(mock_options)

        # Assert
        assert mock_logging.basicConfig.call_count >= 1


# ---------------------------------------------------------------------------
# handle_initialize_config — config_file path and OSError fallback (lines 37, 39-41)
# ---------------------------------------------------------------------------


class TestHandleInitializeConfigBranches:
    """Tests for uncovered branches in handle_initialize_config."""

    @mock.patch("versiontracker.handlers.setup_handlers.Config")
    @mock.patch("versiontracker.handlers.setup_handlers.get_config")
    def test_config_file_path_used_when_no_config_attr(self, mock_get_config, mock_Config):
        """When get_config() has no _config, Config(config_file=...) is called."""
        mock_cfg = mock.MagicMock(spec=[])  # no _config attribute
        mock_get_config.return_value = mock_cfg
        opts = mock.MagicMock()
        opts.config = "/tmp/my.yaml"

        handle_initialize_config(opts)

        mock_Config.assert_called_once_with(config_file="/tmp/my.yaml")

    @mock.patch("versiontracker.handlers.setup_handlers.Config")
    @mock.patch("versiontracker.handlers.setup_handlers.get_config")
    def test_oserror_falls_back_to_default_config(self, mock_get_config, mock_Config):
        """OSError during Config init triggers fallback Config() with no args."""
        mock_cfg = mock.MagicMock(spec=[])  # no _config attribute
        mock_get_config.return_value = mock_cfg
        # First call raises OSError, second (fallback) succeeds
        mock_Config.side_effect = [OSError("file not found"), mock.MagicMock()]
        opts = mock.MagicMock()
        opts.config = "/bad/path.yaml"

        result = handle_initialize_config(opts)

        assert result == 0
        assert mock_Config.call_count == 2
        # Fallback called with no arguments
        mock_Config.assert_called_with()


# ---------------------------------------------------------------------------
# handle_setup_logging — error recovery path (line 105)
# ---------------------------------------------------------------------------


class TestHandleSetupLoggingErrorRecovery:
    """Tests for the exception recovery path in handle_setup_logging."""

    @mock.patch("versiontracker.handlers.setup_handlers.logging")
    def test_logs_error_after_recovery(self, mock_logging):
        """When basicConfig() raises, recovery succeeds and logs the original error."""
        mock_logging.WARNING = 30
        # First basicConfig call raises; second (recovery) succeeds
        mock_logging.basicConfig.side_effect = [Exception("setup failed"), None]

        opts = mock.MagicMock()
        opts.debug = 0

        handle_setup_logging(opts)

        # Recovery basicConfig called
        assert mock_logging.basicConfig.call_count == 2
        # Error logged after recovery
        mock_logging.error.assert_called_once()
