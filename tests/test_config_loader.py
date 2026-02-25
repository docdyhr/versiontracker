"""Tests for ConfigLoader — direct method calls and backward-compat wrappers."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from versiontracker.config import Config, ConfigLoader

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
# ConfigLoader.detect_brew_path
# ---------------------------------------------------------------------------


class TestConfigLoaderDetectBrewPath:
    """Tests for ConfigLoader.detect_brew_path() static method."""

    @patch.dict(os.environ, {"CI": "true"})
    def test_ci_returns_default(self):
        assert ConfigLoader.detect_brew_path() == "/usr/local/bin/brew"

    @patch.dict(os.environ, {}, clear=True)
    @patch("subprocess.run")
    @patch("os.path.exists", return_value=True)
    @patch("versiontracker.config.platform")
    def test_arm_finds_opt_homebrew(self, mock_platform, _exists, mock_run):
        mock_platform.machine.return_value = "arm64"
        mock_run.return_value = type("R", (), {"returncode": 0})()
        assert ConfigLoader.detect_brew_path() == "/opt/homebrew/bin/brew"


# ---------------------------------------------------------------------------
# ConfigLoader.normalize_config_keys
# ---------------------------------------------------------------------------


class TestConfigLoaderNormalizeKeys:
    """Tests for ConfigLoader.normalize_config_keys()."""

    def test_kebab_to_snake(self):
        result = ConfigLoader.normalize_config_keys({"api-rate-limit": 5})
        assert "api_rate_limit" in result
        assert result["api_rate_limit"] == 5

    def test_nested_dicts(self):
        result = ConfigLoader.normalize_config_keys({"outer-key": {"inner-key": 1}})
        assert result["outer_key"]["inner_key"] == 1

    def test_list_with_dicts(self):
        result = ConfigLoader.normalize_config_keys({"items": [{"item-name": "a"}, "plain"]})
        assert result["items"][0]["item_name"] == "a"
        assert result["items"][1] == "plain"

    def test_non_dict_passthrough(self):
        assert ConfigLoader.normalize_config_keys("not a dict") == "not a dict"


# ---------------------------------------------------------------------------
# ConfigLoader.load_from_file
# ---------------------------------------------------------------------------


class TestConfigLoaderLoadFromFile:
    """Tests for ConfigLoader.load_from_file()."""

    def test_missing_file_does_nothing(self):
        config = {"key": "original"}
        ConfigLoader.load_from_file(config, Path("/nonexistent/path.yaml"))
        assert config["key"] == "original"

    def test_empty_file_does_nothing(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write("")
            f.flush()
            config = {"key": "original"}
            ConfigLoader.load_from_file(config, Path(f.name))
            assert config["key"] == "original"
        os.unlink(f.name)

    def test_valid_yaml_updates_config(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump({"max-workers": 42}, f)
            f.flush()
            config = {"max_workers": 10}
            ConfigLoader.load_from_file(config, Path(f.name))
            assert config["max_workers"] == 42
        os.unlink(f.name)


# ---------------------------------------------------------------------------
# ConfigLoader.save
# ---------------------------------------------------------------------------


class TestConfigLoaderSave:
    """Tests for ConfigLoader.save()."""

    def test_saves_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yml"
            config = {"api_rate_limit": 5, "max_workers": 8}
            result = ConfigLoader.save(config, path)
            assert result is True
            assert path.exists()
            with open(path) as f:
                data = yaml.safe_load(f)
            assert data["api_rate_limit"] == 5

    def test_excludes_config_file_and_log_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yml"
            config = {"config_file": "/some/path", "log_dir": Path("/logs"), "api_rate_limit": 3}
            ConfigLoader.save(config, path)
            with open(path) as f:
                data = yaml.safe_load(f)
            assert "config_file" not in data
            assert "log_dir" not in data


# ---------------------------------------------------------------------------
# ConfigLoader.generate_default_config
# ---------------------------------------------------------------------------


class TestConfigLoaderGenerateDefault:
    """Tests for ConfigLoader.generate_default_config()."""

    def test_generates_valid_yaml(self):
        cfg = _make_config()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "default.yml"
            result = ConfigLoader.generate_default_config(cfg._config, path)
            assert result == str(path)
            with open(path) as f:
                data = yaml.safe_load(f)
            assert "api-rate-limit" in data
            assert "version-comparison" in data


# ---------------------------------------------------------------------------
# Config backward-compat wrappers
# ---------------------------------------------------------------------------


class TestConfigBackwardCompat:
    """Tests that Config methods delegate to ConfigLoader."""

    def test_detect_brew_path_delegates(self):
        cfg = _make_config()
        result = cfg._detect_brew_path()
        assert result == ConfigLoader.detect_brew_path()

    def test_normalize_config_keys_delegates(self):
        cfg = _make_config()
        result = cfg._normalize_config_keys({"some-key": 1})
        assert result == {"some_key": 1}

    def test_save_delegates(self):
        cfg = _make_config()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yml"
            cfg._config["config_file"] = str(path)
            result = cfg.save()
            assert result is True
            assert path.exists()

    def test_generate_default_config_delegates(self):
        cfg = _make_config()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "default.yml"
            result = cfg.generate_default_config(path)
            assert result == str(path)
            assert path.exists()
