"""Test module for the configuration handlers.

This module contains tests for the configuration handler functions
in the versiontracker.handlers.config_handlers module.
"""

from pathlib import Path
from unittest import mock


from versiontracker.handlers.config_handlers import handle_config_generation


class TestConfigHandlers:
    """Tests for the configuration handlers."""

    @mock.patch("versiontracker.handlers.config_handlers.get_config")
    @mock.patch("versiontracker.handlers.config_handlers.logging")
    @mock.patch("versiontracker.handlers.config_handlers.print")
    def test_handle_config_generation_success(self, mock_print, mock_logging, mock_get_config):
        """Test generating a config file successfully."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.config_path = None
        
        # Mock the config return value
        mock_config_instance = mock_get_config.return_value
        mock_config_instance.generate_default_config.return_value = "/path/to/config.yaml"
        
        # Execute
        result = handle_config_generation(mock_options)
        
        # Assert
        assert result == 0
        mock_config_instance.generate_default_config.assert_called_once_with(None)
        mock_print.assert_any_call("Configuration file generated: /path/to/config.yaml")
    
    @mock.patch("versiontracker.handlers.config_handlers.get_config")
    @mock.patch("versiontracker.handlers.config_handlers.logging")
    @mock.patch("versiontracker.handlers.config_handlers.print")
    def test_handle_config_generation_custom_path(self, mock_print, mock_logging, mock_get_config):
        """Test generating a config file with a custom path."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.config_path = "/custom/path/config.yaml"
        
        # Mock the config return value
        mock_config_instance = mock_get_config.return_value
        mock_config_instance.generate_default_config.return_value = "/custom/path/config.yaml"
        
        # Execute
        result = handle_config_generation(mock_options)
        
        # Assert
        assert result == 0
        mock_config_instance.generate_default_config.assert_called_once_with(Path("/custom/path/config.yaml"))
        mock_print.assert_any_call("Configuration file generated: /custom/path/config.yaml")
    
    @mock.patch("versiontracker.handlers.config_handlers.get_config")
    @mock.patch("versiontracker.handlers.config_handlers.logging")
    @mock.patch("versiontracker.handlers.config_handlers.print")
    def test_handle_config_generation_exception(self, mock_print, mock_logging, mock_get_config):
        """Test handling an exception when generating a config file."""
        # Setup
        mock_options = mock.MagicMock()
        mock_options.config_path = None
        
        # Set up the exception
        mock_config_instance = mock_get_config.return_value
        mock_config_instance.generate_default_config.side_effect = Exception("Failed to generate config")
        
        # Execute
        result = handle_config_generation(mock_options)
        
        # Assert
        assert result == 1
        mock_logging.error.assert_called_once()
        # The function should continue and return the error code