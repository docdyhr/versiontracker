"""Tests for versiontracker.config — coverage improvement.

Targets untested paths in Config.get(), _detect_brew_path(),
_load_basic_env_vars(), debug/no_progress/show_progress properties,
and generate_default_config().
"""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from versiontracker.config import Config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**env_overrides):
    """Create a Config instance with CI/brew detection disabled."""
    default_env = {
        "CI": "true",
        "VERSIONTRACKER_SKIP_BREW_DETECTION": "1",
    }
    default_env.update(env_overrides)
    with patch.dict(os.environ, default_env):
        return Config()


# ---------------------------------------------------------------------------
# Config.get() — dot notation
# ---------------------------------------------------------------------------


class TestConfigGet:
    """Tests for Config.get() with dot notation and fallbacks."""

    def test_simple_key(self):
        cfg = _make_config()
        result = cfg.get("max_workers")
        assert isinstance(result, int)

    def test_dot_notation_success(self):
        cfg = _make_config()
        # version_comparison.rate_limit is a default key
        result = cfg.get("version_comparison.rate_limit")
        assert result is not None

    def test_dot_notation_missing_with_default(self):
        cfg = _make_config()
        result = cfg.get("nonexistent.path.deep", default="fallback")
        assert result == "fallback"

    def test_dot_notation_missing_no_default_raises(self):
        cfg = _make_config()
        with pytest.raises(KeyError, match="not found"):
            cfg.get("nonexistent.path.deep")

    def test_deep_nesting(self):
        cfg = _make_config()
        cfg._config["a"] = {"b": {"c": 42}}
        assert cfg.get("a.b.c") == 42

    def test_missing_key_returns_default(self):
        cfg = _make_config()
        assert cfg.get("totally_missing", "sentinel") == "sentinel"

    def test_log_level_default_is_info(self):
        cfg = _make_config()
        # Remove log_level to force the fallback path
        cfg._config.pop("log_level", None)
        result = cfg.get("log_level")
        # In CI env VERSIONTRACKER_DEBUG is not set, so should return INFO
        assert result == logging.INFO

    @patch.dict(os.environ, {"VERSIONTRACKER_DEBUG": "true"})
    def test_log_level_debug_from_env(self):
        cfg = _make_config()
        cfg._config.pop("log_level", None)
        result = cfg.get("log_level")
        assert result == logging.DEBUG


# ---------------------------------------------------------------------------
# _detect_brew_path
# ---------------------------------------------------------------------------


class TestDetectBrewPath:
    """Tests for Config._detect_brew_path()."""

    @patch.dict(os.environ, {"CI": "true"})
    def test_ci_env_returns_default(self):
        cfg = Config.__new__(Config)
        cfg._config = {}
        result = cfg._detect_brew_path()
        assert result == "/usr/local/bin/brew"

    @patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False)
    def test_github_actions_env(self):
        cfg = Config.__new__(Config)
        cfg._config = {}
        result = cfg._detect_brew_path()
        assert result == "/usr/local/bin/brew"

    @patch.dict(os.environ, {"VERSIONTRACKER_SKIP_BREW_DETECTION": "1"}, clear=False)
    def test_skip_detection_env(self):
        cfg = Config.__new__(Config)
        cfg._config = {}
        result = cfg._detect_brew_path()
        assert result == "/usr/local/bin/brew"

    @patch.dict(os.environ, {}, clear=True)
    @patch("subprocess.run")
    @patch("os.path.exists", return_value=False)
    @patch("versiontracker.config.platform")
    def test_no_working_brew_fallback(self, mock_platform, _exists, _subproc):
        """When no brew path exists, falls back to Intel default."""
        mock_platform.machine.return_value = "x86_64"
        # Bare "brew" command should also fail
        _subproc.side_effect = FileNotFoundError("brew not found")

        cfg = Config.__new__(Config)
        cfg._config = {}
        result = cfg._detect_brew_path()
        assert result == "/usr/local/bin/brew"

    @patch.dict(os.environ, {}, clear=True)
    @patch("subprocess.run")
    @patch("os.path.exists", return_value=True)
    @patch("versiontracker.config.platform")
    def test_arm_priority(self, mock_platform, _exists, mock_subproc):
        """ARM architecture tries /opt/homebrew/bin/brew first."""
        mock_platform.machine.return_value = "arm64"

        # First call succeeds
        mock_result = type("R", (), {"returncode": 0})()
        mock_subproc.return_value = mock_result

        cfg = Config.__new__(Config)
        cfg._config = {}
        result = cfg._detect_brew_path()
        assert result == "/opt/homebrew/bin/brew"


# ---------------------------------------------------------------------------
# _load_basic_env_vars
# ---------------------------------------------------------------------------


class TestLoadBasicEnvVars:
    """Tests for Config._load_basic_env_vars()."""

    @patch.dict(os.environ, {"VERSIONTRACKER_DEBUG": "true"})
    def test_debug_mode(self):
        cfg = _make_config(VERSIONTRACKER_DEBUG="true")
        assert cfg._config.get("log_level") == logging.DEBUG

    @patch.dict(os.environ, {"VERSIONTRACKER_API_RATE_LIMIT": "5"})
    def test_integer_env_var(self):
        cfg = _make_config(VERSIONTRACKER_API_RATE_LIMIT="5")
        assert cfg._config.get("api_rate_limit") == 5

    def test_additional_dirs_colon_split(self, tmp_path):
        d1 = tmp_path / "dir1"
        d1.mkdir()
        d2 = tmp_path / "dir2"
        d2.mkdir()
        dirs_str = f"{d1}:{d2}"
        cfg = _make_config(VERSIONTRACKER_ADDITIONAL_APP_DIRS=dirs_str)
        assert str(d1) in cfg._config.get("additional_app_dirs", [])
        assert str(d2) in cfg._config.get("additional_app_dirs", [])

    def test_blacklist_comma_split(self):
        cfg = _make_config(VERSIONTRACKER_BLACKLIST="app1,app2,app3")
        bl = cfg._config.get("blacklist", [])
        assert "app1" in bl
        assert "app3" in bl


# ---------------------------------------------------------------------------
# debug, no_progress, show_progress properties
# ---------------------------------------------------------------------------


class TestConfigProperties:
    """Tests for Config properties: debug, no_progress, show_progress."""

    def test_debug_getter_default_false(self):
        cfg = _make_config()
        cfg._config["debug"] = False
        assert cfg.debug is False

    def test_debug_setter(self):
        cfg = _make_config()
        cfg.debug = True
        assert cfg._config["debug"] is True
        assert cfg.debug is True

    def test_no_progress_default_false(self):
        cfg = _make_config()
        cfg._config["no_progress"] = False
        assert cfg.no_progress is False

    def test_no_progress_true(self):
        cfg = _make_config()
        cfg._config["no_progress"] = True
        assert cfg.no_progress is True

    def test_show_progress_inverse(self):
        cfg = _make_config()
        cfg._config["no_progress"] = True
        assert cfg.show_progress is False

        cfg._config["no_progress"] = False
        assert cfg.show_progress is True


# ---------------------------------------------------------------------------
# generate_default_config
# ---------------------------------------------------------------------------


class TestGenerateDefaultConfig:
    """Tests for Config.generate_default_config()."""

    def test_generates_yaml_at_custom_path(self):
        cfg = _make_config()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "subdir" / "config.yml"
            result = cfg.generate_default_config(path)
            assert result == str(path)
            assert path.exists()

            import yaml

            with open(path) as f:
                data = yaml.safe_load(f)
            assert "api-rate-limit" in data
            assert "version-comparison" in data

    def test_generates_at_default_path(self):
        cfg = _make_config()
        with tempfile.TemporaryDirectory() as tmp:
            default_path = Path(tmp) / "vt_config.yml"
            cfg._config["config_file"] = str(default_path)
            result = cfg.generate_default_config()
            assert result == str(default_path)
            assert default_path.exists()
