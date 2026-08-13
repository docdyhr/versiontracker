"""Test module for the setup handlers.

This module contains tests for the setup handler functions
in the versiontracker.handlers.setup_handlers module.
"""

import logging
from unittest import mock

from versiontracker.config import get_config
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

    def test_handle_initialize_config_no_config_file(self):
        """No --config: the default configuration loads successfully."""
        mock_options = mock.MagicMock()
        mock_options.config = None

        result = handle_initialize_config(mock_options)

        assert result == 0

    def test_handle_initialize_config_explicit_valid_file(self, tmp_path):
        """--config PATH: the requested file is loaded and installed globally."""
        config_path = tmp_path / "custom.yaml"
        config_path.write_text("max_workers: 5\n")
        mock_options = mock.MagicMock()
        mock_options.config = str(config_path)

        result = handle_initialize_config(mock_options)

        assert result == 0
        assert get_config().get("max_workers") == 5
        assert str(get_config().get("config_file")) == str(config_path)

    def test_handle_initialize_config_missing_explicit_file(self):
        """--config PATH pointing at a nonexistent file fails clearly, no fallback."""
        mock_options = mock.MagicMock()
        mock_options.config = "/nonexistent/versiontracker-test-config.yaml"

        result = handle_initialize_config(mock_options)

        assert result == 1

    def test_handle_initialize_config_malformed_explicit_file(self, tmp_path):
        """--config PATH pointing at malformed YAML fails clearly, no fallback."""
        config_path = tmp_path / "bad.yaml"
        config_path.write_text("not: valid: yaml: [unterminated\n")
        mock_options = mock.MagicMock()
        mock_options.config = str(config_path)

        result = handle_initialize_config(mock_options)

        assert result == 1

    @mock.patch("versiontracker.handlers.setup_handlers.get_config")
    @mock.patch("versiontracker.handlers.setup_handlers.logging")
    def test_handle_initialize_config_error(self, mock_logging, mock_get_config):
        """Default (no --config) initialization failure is reported, not swallowed."""
        mock_options = mock.MagicMock()
        mock_options.config = None
        mock_get_config.side_effect = OSError("Test error")

        result = handle_initialize_config(mock_options)

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
        mock_options.max_workers = None

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
    def test_handle_configure_from_options_wires_max_workers(self, mock_logging, mock_get_config):
        """Regression: --max-workers was previously parsed but never wired
        into Config anywhere -- every real consumer (async_homebrew.py,
        async_network.py, apps/finder.py, version/batch.py) reads
        max_workers exclusively from Config, so the CLI flag had zero
        effect."""
        mock_options = mock.MagicMock()
        mock_options.no_color = False
        mock_options.no_progress = False
        mock_options.no_adaptive_rate = False
        mock_options.max_workers = 16

        mock_config = mock.MagicMock()
        mock_get_config.return_value = mock_config

        result = handle_configure_from_options(mock_options)

        assert result == 0
        mock_config.set.assert_any_call("max_workers", 16)

    @mock.patch("versiontracker.handlers.setup_handlers.get_config")
    @mock.patch("versiontracker.handlers.setup_handlers.logging")
    def test_handle_configure_from_options_no_max_workers_not_wired(self, mock_logging, mock_get_config):
        """When --max-workers isn't passed, Config.set('max_workers', ...) is never called."""
        mock_options = mock.MagicMock()
        mock_options.no_color = False
        mock_options.no_progress = False
        mock_options.no_adaptive_rate = False
        mock_options.max_workers = None

        mock_config = mock.MagicMock()
        mock_get_config.return_value = mock_config

        result = handle_configure_from_options(mock_options)

        assert result == 0
        for call in mock_config.set.call_args_list:
            assert call.args[0] != "max_workers"

    @mock.patch("versiontracker.handlers.setup_handlers.get_config")
    @mock.patch("versiontracker.handlers.setup_handlers.logging")
    def test_handle_configure_from_options_error(self, mock_logging, mock_get_config):
        """Test error handling during configuration from options."""
        # Setup
        mock_options = mock.MagicMock()
        mock_get_config.side_effect = ValueError("Test error")

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
        mock_logging.basicConfig.side_effect = ValueError("First error")

        # Execute — should not raise, errors are handled internally
        handle_setup_logging(mock_options)

        # Assert
        assert mock_logging.basicConfig.call_count >= 1


# ---------------------------------------------------------------------------
# handle_initialize_config's --config PATH resolution (valid/missing/malformed
# explicit files, no-config default) is covered directly in TestSetupHandlers
# above via real tmp_path files -- the old dead-code-encoding branch tests
# (asserting the discarded `Config(config_file=...)` call and an OSError ->
# bare-`Config()` fallback that must no longer happen) were removed.
# ---------------------------------------------------------------------------

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
        mock_logging.basicConfig.side_effect = [ValueError("setup failed"), None]

        opts = mock.MagicMock()
        opts.debug = 0

        handle_setup_logging(opts)

        # Recovery basicConfig called
        assert mock_logging.basicConfig.call_count == 2
        # Error logged after recovery
        mock_logging.error.assert_called_once()
