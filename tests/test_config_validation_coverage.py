"""Tests for versiontracker.config — coverage improvement.

Covers check_dependencies() platform branches, and Config.get()
with dot-notation nested keys and default values.
"""

from unittest.mock import patch

import pytest

from versiontracker.config import Config, ConfigLoader, check_dependencies
from versiontracker.exceptions import ConfigError

# ---------------------------------------------------------------------------
# check_dependencies — platform branches
# ---------------------------------------------------------------------------


class TestCheckDependencies:
    """Tests for check_dependencies()."""

    @patch("versiontracker.config.shutil.which", return_value="/usr/sbin/system_profiler")
    @patch("versiontracker.config.platform.system", return_value="Darwin")
    def test_darwin_with_system_profiler(self, _system, _which):
        """Returns True on Darwin when system_profiler is found."""
        assert check_dependencies() is True

    @patch("versiontracker.config.shutil.which", return_value=None)
    @patch("versiontracker.config.platform.system", return_value="Darwin")
    def test_darwin_without_system_profiler(self, _system, _which):
        """Raises ConfigError on Darwin when system_profiler is missing."""
        with pytest.raises(ConfigError, match="system_profiler"):
            check_dependencies()

    @patch("versiontracker.config.platform.system", return_value="Linux")
    def test_non_darwin_skips_system_profiler(self, _system):
        """Returns True on non-Darwin platforms without checking system_profiler."""
        assert check_dependencies() is True

    @patch("versiontracker.config.platform.system", return_value="Windows")
    def test_windows_returns_true(self, _system):
        """Returns True on Windows (no macOS-specific deps checked)."""
        assert check_dependencies() is True


# ---------------------------------------------------------------------------
# Config.get — dot notation and defaults
# ---------------------------------------------------------------------------


class TestConfigGet:
    """Tests for Config.get() with nested keys and defaults."""

    @patch.object(ConfigLoader, "detect_brew_path", return_value="/usr/local/bin/brew")
    @patch.object(ConfigLoader, "load_from_file")
    @patch.object(ConfigLoader, "load_from_env")
    def test_get_nested_key_with_dot_notation(self, _env, _file, _brew):
        """Config.get('ui.use_color') retrieves a nested value."""
        config = Config()
        result = config.get("ui.use_color")
        assert result is True

    @patch.object(ConfigLoader, "detect_brew_path", return_value="/usr/local/bin/brew")
    @patch.object(ConfigLoader, "load_from_file")
    @patch.object(ConfigLoader, "load_from_env")
    def test_get_nested_key_version_comparison(self, _env, _file, _brew):
        """Config.get('version_comparison.rate_limit') retrieves nested value."""
        config = Config()
        result = config.get("version_comparison.rate_limit")
        assert result == 2

    @patch.object(ConfigLoader, "detect_brew_path", return_value="/usr/local/bin/brew")
    @patch.object(ConfigLoader, "load_from_file")
    @patch.object(ConfigLoader, "load_from_env")
    def test_get_nonexistent_key_with_default(self, _env, _file, _brew):
        """Config.get('nonexistent', default) returns the default value."""
        config = Config()
        result = config.get("no_such_key", "fallback")
        assert result == "fallback"

    @patch.object(ConfigLoader, "detect_brew_path", return_value="/usr/local/bin/brew")
    @patch.object(ConfigLoader, "load_from_file")
    @patch.object(ConfigLoader, "load_from_env")
    def test_get_nonexistent_key_no_default(self, _env, _file, _brew):
        """Config.get('nonexistent') returns None when no default is provided."""
        config = Config()
        result = config.get("no_such_key")
        assert result is None

    @patch.object(ConfigLoader, "detect_brew_path", return_value="/usr/local/bin/brew")
    @patch.object(ConfigLoader, "load_from_file")
    @patch.object(ConfigLoader, "load_from_env")
    def test_get_nonexistent_nested_key_with_default(self, _env, _file, _brew):
        """Config.get('ui.nonexistent', default) returns default for missing nested key."""
        config = Config()
        result = config.get("ui.nonexistent_key", "default_val")
        assert result == "default_val"

    @patch.object(ConfigLoader, "detect_brew_path", return_value="/usr/local/bin/brew")
    @patch.object(ConfigLoader, "load_from_file")
    @patch.object(ConfigLoader, "load_from_env")
    def test_get_nonexistent_nested_key_raises_without_default(self, _env, _file, _brew):
        """Config.get('ui.nonexistent') raises KeyError when no default and default is None."""
        config = Config()
        # When default is None (the default parameter), and key is not found,
        # it returns None per the code logic (default is not None check fails
        # because default IS None)
        # Actually looking at the code: if default is not None: return default
        # else: raise KeyError
        with pytest.raises(KeyError, match="not found"):
            config.get("ui.nonexistent_key")

    @patch.object(ConfigLoader, "detect_brew_path", return_value="/usr/local/bin/brew")
    @patch.object(ConfigLoader, "load_from_file")
    @patch.object(ConfigLoader, "load_from_env")
    def test_get_deeply_nested_nonexistent_section(self, _env, _file, _brew):
        """Config.get('nonexistent_section.key') raises KeyError for missing section."""
        config = Config()
        with pytest.raises(KeyError, match="not found"):
            config.get("nonexistent_section.some_key")

    @patch.object(ConfigLoader, "detect_brew_path", return_value="/usr/local/bin/brew")
    @patch.object(ConfigLoader, "load_from_file")
    @patch.object(ConfigLoader, "load_from_env")
    def test_get_top_level_key(self, _env, _file, _brew):
        """Config.get('max_workers') retrieves a top-level value."""
        config = Config()
        assert config.get("max_workers") == 10

    @patch.object(ConfigLoader, "detect_brew_path", return_value="/usr/local/bin/brew")
    @patch.object(ConfigLoader, "load_from_file")
    @patch.object(ConfigLoader, "load_from_env")
    def test_get_log_level_default(self, _env, _file, _brew):
        """Config.get('log_level') returns the configured log level."""
        config = Config()
        import logging

        assert config.get("log_level") == logging.INFO
