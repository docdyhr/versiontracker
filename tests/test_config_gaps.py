"""Coverage tests for versiontracker.config — uncovered error paths and edge cases."""

import logging
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from versiontracker.config import Config, ConfigLoader, ConfigValidator
from versiontracker.exceptions import ConfigError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**env_overrides):
    """Create a Config with CI env set (skips brew detection)."""
    env = {"CI": "true", "VERSIONTRACKER_SKIP_BREW_DETECTION": "1"}
    env.update(env_overrides)
    with patch.dict(os.environ, env):
        return Config()


# ---------------------------------------------------------------------------
# ConfigValidator
# ---------------------------------------------------------------------------


class TestConfigValidatorEdgeCases:
    """Edge-case paths in ConfigValidator."""

    def test_validate_percentage_non_numeric_string(self):
        assert ConfigValidator.validate_percentage("not_a_number") is False

    def test_validate_percentage_none(self):
        assert ConfigValidator.validate_percentage(None) is False

    def test_validate_percentage_list(self):
        assert ConfigValidator.validate_percentage([]) is False

    def test_validate_nested_section_non_dict_value(self):
        """Section present but not a dict → error recorded."""
        errors: dict = {}
        ConfigValidator._validate_nested_section(
            {"ui": "should_be_a_dict"},
            "ui",
            {},
            errors,
        )
        assert "ui" in errors
        assert "Must be a dictionary" in errors["ui"][0]

    def test_validate_config_nested_rule_violation(self):
        """Invalid nested bool value is caught."""
        errors = ConfigValidator.validate_config({"ui": {"use_color": "yes_please"}})
        assert "ui.use_color" in errors


# ---------------------------------------------------------------------------
# ConfigLoader.load_from_file error paths
# ---------------------------------------------------------------------------


class TestLoadFromFileErrors:
    """YAML error, OSError, and validation-failure paths in load_from_file."""

    def test_yaml_error_raises_config_error(self, tmp_path):
        config_file = tmp_path / "bad.yaml"
        config_file.write_text(":\n  {invalid yaml content")
        with pytest.raises(ConfigError, match="Invalid YAML"):
            ConfigLoader.load_from_file({}, config_file)

    def test_os_error_raises_config_error(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_workers: 4\n")
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with pytest.raises(ConfigError, match="Error loading configuration"):
                ConfigLoader.load_from_file({}, config_file)

    def test_validation_failure_raises_config_error(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_workers: -1\n")  # must be > 0
        with pytest.raises(ConfigError, match="Configuration validation failed"):
            ConfigLoader.load_from_file({}, config_file)

    def test_unexpected_error_raises_config_error(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_workers: 4\n")
        with patch("versiontracker.config.ConfigValidator.validate_config", side_effect=RuntimeError("boom")):
            with pytest.raises(ConfigError, match="Error in configuration processing"):
                ConfigLoader.load_from_file({}, config_file)


# ---------------------------------------------------------------------------
# ConfigLoader env-var loading edge cases
# ---------------------------------------------------------------------------


class TestEnvVarLoading:
    """Invalid and nested env var paths."""

    def test_load_integer_env_var_invalid_value(self, monkeypatch):
        monkeypatch.setenv("VERSIONTRACKER_MAX_WORKERS", "not_an_int")
        env_config: dict = {}
        ConfigLoader._load_integer_env_var("VERSIONTRACKER_MAX_WORKERS", "max_workers", env_config)
        assert "max_workers" not in env_config

    def test_load_boolean_env_var_nested_key_not_in_config(self, monkeypatch):
        monkeypatch.setenv("VERSIONTRACKER_UI_USE_COLOR", "false")
        env_config: dict = {}
        ConfigLoader._load_boolean_env_var("VERSIONTRACKER_UI_USE_COLOR", "use_color", env_config, nested_key="ui")
        assert env_config["ui"]["use_color"] is False

    def test_load_boolean_env_var_nested_key_already_exists(self, monkeypatch):
        monkeypatch.setenv("VERSIONTRACKER_UI_USE_COLOR", "0")
        env_config: dict = {"ui": {"monitor_resources": True}}
        ConfigLoader._load_boolean_env_var("VERSIONTRACKER_UI_USE_COLOR", "use_color", env_config, nested_key="ui")
        assert env_config["ui"]["use_color"] is False
        assert env_config["ui"]["monitor_resources"] is True

    def test_load_int_env_var_invalid_value(self, monkeypatch):
        monkeypatch.setenv("VERSIONTRACKER_VERSION_COMPARISON_RATE_LIMIT", "bad")
        config: dict = {"version_comparison": {}}
        ConfigLoader._load_int_env_var(
            config,
            "VERSIONTRACKER_VERSION_COMPARISON_RATE_LIMIT",
            "version_comparison",
            "rate_limit",
        )
        assert "rate_limit" not in config["version_comparison"]

    def test_load_bool_env_var_true_path(self, monkeypatch):
        monkeypatch.setenv("VERSIONTRACKER_VERSION_COMPARISON_INCLUDE_BETA_VERSIONS", "true")
        config: dict = {"version_comparison": {}}
        ConfigLoader._load_bool_env_var(
            config,
            "VERSIONTRACKER_VERSION_COMPARISON_INCLUDE_BETA_VERSIONS",
            "version_comparison",
            "include_beta_versions",
        )
        assert config["version_comparison"]["include_beta_versions"] is True

    def test_load_bool_env_var_yes_path(self, monkeypatch):
        monkeypatch.setenv("VERSIONTRACKER_VERSION_COMPARISON_SORT_BY_OUTDATED", "yes")
        config: dict = {"version_comparison": {}}
        ConfigLoader._load_bool_env_var(
            config,
            "VERSIONTRACKER_VERSION_COMPARISON_SORT_BY_OUTDATED",
            "version_comparison",
            "sort_by_outdated",
        )
        assert config["version_comparison"]["sort_by_outdated"] is True


class TestHandleValidationErrors:
    """_handle_validation_errors filters invalid keys and applies valid ones."""

    def test_valid_keys_applied_invalid_filtered(self):
        config: dict = {}
        validation_errors = {"max_workers": ["Must be greater than 0"]}
        env_config = {"max_workers": -1, "timeout": 30}
        ConfigLoader._handle_validation_errors(config, validation_errors, env_config)
        assert "max_workers" not in config
        assert config.get("timeout") == 30

    def test_no_valid_keys_config_unchanged(self):
        config: dict = {"existing": True}
        validation_errors = {"max_workers": ["Must be greater than 0"]}
        env_config = {"max_workers": -1}
        ConfigLoader._handle_validation_errors(config, validation_errors, env_config)
        assert config == {"existing": True}


# ---------------------------------------------------------------------------
# Config instance methods — uncovered branches
# ---------------------------------------------------------------------------


class TestConfigInstanceGaps:
    """Uncovered branches on the Config class."""

    def test_get_log_level_from_config(self):
        """Line 700: log_level explicitly set in _config."""
        cfg = _make_config()
        cfg._config["log_level"] = logging.WARNING
        assert cfg.get("log_level") == logging.WARNING

    def test_get_log_level_from_debug_env(self, monkeypatch):
        """Lines 701-706: log_level inferred from VERSIONTRACKER_DEBUG env var."""
        cfg = _make_config()
        cfg._config.pop("log_level", None)
        monkeypatch.setenv("VERSIONTRACKER_DEBUG", "true")
        assert cfg.get("log_level") == logging.DEBUG

    def test_set_dot_notation_creates_nested(self):
        """Lines 738-774: Config.set() with dot notation builds and applies nested key."""
        cfg = _make_config()
        cfg.set("ui.use_color", True)
        assert cfg._config["ui"]["use_color"] is True

    def test_set_validation_failure_raises(self):
        """Lines 754-763: Config.set() raises ConfigError on invalid value."""
        cfg = _make_config()
        with pytest.raises(ConfigError):
            cfg.set("max_workers", -5)

    def test_get_blacklist_both_keys_deduped(self):
        """Lines 800-806: both blacklist and blocklist present → merged, de-duplicated."""
        cfg = _make_config()
        cfg._config["blacklist"] = ["App1", "App2"]
        cfg._config["blocklist"] = ["App2", "App3"]
        result = cfg.get_blacklist()
        assert "App1" in result
        assert "App2" in result
        assert "App3" in result
        assert result.count("App2") == 1
        assert result.index("App2") < result.index("App1")

    def test_log_dir_property(self):
        """Line 851: log_dir returns a Path."""
        cfg = _make_config()
        assert isinstance(cfg.log_dir, Path)


# ---------------------------------------------------------------------------
# setup_logging and set_global_config (lines 954-962, 979)
# ---------------------------------------------------------------------------


class TestSetupLoggingAndGlobalConfig:
    """setup_logging and set_global_config paths."""

    def test_setup_logging_debug(self, tmp_path):
        from versiontracker.config import setup_logging

        mock_cfg = MagicMock()
        mock_cfg.log_dir = tmp_path
        with patch("versiontracker.config.get_config", return_value=mock_cfg):
            with patch("logging.basicConfig"):
                setup_logging(debug=True)

    def test_setup_logging_info(self, tmp_path):
        from versiontracker.config import setup_logging

        mock_cfg = MagicMock()
        mock_cfg.log_dir = tmp_path
        with patch("versiontracker.config.get_config", return_value=mock_cfg):
            with patch("logging.basicConfig"):
                setup_logging(debug=False)

    def test_setup_logging_creates_dir_if_missing(self, tmp_path):
        from versiontracker.config import setup_logging

        log_dir = tmp_path / "logs"
        mock_cfg = MagicMock()
        mock_cfg.log_dir = log_dir
        with patch("versiontracker.config.get_config", return_value=mock_cfg):
            with patch("logging.basicConfig"):
                setup_logging()
        assert log_dir.exists()

    def test_set_global_config(self):
        from versiontracker import config as cfg_module
        from versiontracker.config import set_global_config

        original = cfg_module._config_instance
        new_cfg = _make_config()
        try:
            set_global_config(new_cfg)
            assert cfg_module._config_instance is new_cfg
        finally:
            cfg_module._config_instance = original
