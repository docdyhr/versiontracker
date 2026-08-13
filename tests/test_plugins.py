"""Tests for versiontracker.plugins.

Regression coverage: load_plugins() previously guarded its
plugin-directories loop with hasattr(config, "plugin_directories"), which
is always False for a real Config (no such attribute exists -- Config
stores settings in a plain dict, not instance attributes), so any
configured plugin_directories setting was silently never loaded. This had
zero test coverage before this file.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from versiontracker.plugins import load_plugins


@patch("versiontracker.plugins.plugin_manager")
@patch("versiontracker.plugins.get_config")
def test_load_plugins_honors_configured_plugin_directories(mock_get_config, mock_plugin_manager):
    mock_config = MagicMock()
    mock_config.get.return_value = ["/custom/plugins/one", "/custom/plugins/two"]
    mock_get_config.return_value = mock_config

    with patch("versiontracker.plugins.Path.exists", return_value=False):
        load_plugins()

    mock_plugin_manager.load_plugins_from_directory.assert_any_call(Path("/custom/plugins/one"))
    mock_plugin_manager.load_plugins_from_directory.assert_any_call(Path("/custom/plugins/two"))


@patch("versiontracker.plugins.plugin_manager")
@patch("versiontracker.plugins.get_config")
def test_load_plugins_no_configured_directories_is_a_noop(mock_get_config, mock_plugin_manager):
    mock_config = MagicMock()
    mock_config.get.return_value = []
    mock_get_config.return_value = mock_config

    with patch("versiontracker.plugins.Path.exists", return_value=False):
        load_plugins()

    mock_plugin_manager.load_plugins_from_directory.assert_not_called()
