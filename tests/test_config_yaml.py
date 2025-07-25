"""Tests for configuration file support."""

import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import yaml

from versiontracker.config import Config


class TestConfigFile(TestCase):
    """Test cases for configuration file support."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear any environment variables that might affect tests
        for var in list(os.environ.keys()):
            if var.startswith("VERSIONTRACKER_"):
                del os.environ[var]

    def test_load_from_yaml_file(self):
        """Test loading configuration from YAML file."""
        # Create a temporary configuration file
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w", encoding="utf-8") as f:
            yaml_config = {
                "api-rate-limit": 5,
                "max-workers": 20,
                "similarity-threshold": 90,
                "blacklist": ["App1", "App2"],
                "show-progress": False,
            }
            yaml.dump(yaml_config, f)
            config_path = f.name

        try:
            # Create a test Config instance
            with patch.object(Config, "_load_from_env"):  # Prevent loading from environment
                test_config = Config()
                test_config._config["config_file"] = config_path
                test_config._load_from_file()

            # Verify the configuration values were loaded correctly
            self.assertEqual(test_config.get("api_rate_limit"), 5)
            self.assertEqual(test_config.get("max_workers"), 20)
            self.assertEqual(test_config.get("similarity_threshold"), 90)
            self.assertEqual(test_config.get_blacklist(), ["App1", "App2"])
            self.assertFalse(test_config.get("show_progress"))
        finally:
            # Clean up the temporary file
            os.unlink(config_path)

    def test_generate_default_config(self):
        """Test generating a default configuration file."""
        # Create a temporary directory for the configuration file
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"

            # Create a test Config instance and generate the configuration file
            test_config = Config()
            test_config.set("blacklist", ["TestApp1", "TestApp2"])
            result = test_config.generate_default_config(config_path)

            # Verify the configuration file was generated correctly
            self.assertEqual(result, str(config_path))
            self.assertTrue(config_path.exists())

            # Read the generated configuration file and verify its contents
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)

            self.assertEqual(yaml_config["api-rate-limit"], test_config.get("api_rate_limit"))
            self.assertEqual(yaml_config["max-workers"], test_config.get("max_workers"))
            self.assertEqual(
                yaml_config["similarity-threshold"],
                test_config.get("similarity_threshold"),
            )
            self.assertEqual(yaml_config["blacklist"], ["TestApp1", "TestApp2"])
            self.assertEqual(yaml_config["show-progress"], test_config.get("show_progress"))

    def test_env_vars_override_file(self):
        """Test that environment variables override file configuration."""
        # Create a temporary configuration file
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w", encoding="utf-8") as f:
            yaml_config = {
                "api-rate-limit": 5,
                "max-workers": 20,
                "blacklist": ["App1", "App2"],
            }
            yaml.dump(yaml_config, f)
            config_path = f.name

        try:
            # Set environment variables to override the file configuration
            os.environ["VERSIONTRACKER_API_RATE_LIMIT"] = "10"
            os.environ["VERSIONTRACKER_BLACKLIST"] = "App3,App4"

            # Create a test Config instance and load the configuration
            test_config = Config()
            test_config._config["config_file"] = config_path
            test_config._load_from_file()
            test_config._load_from_env()

            # Verify the environment variables override the file configuration
            self.assertEqual(test_config.get("api_rate_limit"), 10)
            self.assertEqual(test_config.get("max_workers"), 20)  # Not overridden
            self.assertEqual(test_config.get_blacklist(), ["App3", "App4"])  # Overridden
        finally:
            # Clean up the temporary file
            os.unlink(config_path)

    def test_load_nonexistent_file(self):
        """Test loading a non-existent configuration file."""
        # Use a path that definitely doesn't exist
        non_existent_path = "/tmp/definitely_not_a_real_config_file_12345.yaml"

        # Create a test Config instance
        test_config = Config()
        test_config._config["config_file"] = non_existent_path

        # This should not raise an exception and should use default values
        test_config._load_from_file()

        # Verify default values are used
        self.assertEqual(test_config.get("api_rate_limit"), 3)  # Default value
        self.assertEqual(test_config.get("max_workers"), 10)  # Default value
        self.assertEqual(len(test_config.get_blacklist()), 8)  # Default value

    def test_custom_config_path(self):
        """Test using a custom configuration path."""
        # Create a temporary configuration file with custom settings
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w", encoding="utf-8") as f:
            yaml_config = {
                "api-rate-limit": 8,
                "max-workers": 6,
                "blacklist": ["CustomApp1", "CustomApp2"],
                "additional-app-dirs": ["/custom/path1", "/custom/path2"],
            }
            yaml.dump(yaml_config, f)
            custom_config_path = f.name

        try:
            # Create a test Config instance with the custom path
            with patch.object(Config, "_load_from_env"):  # Prevent loading from environment
                test_config = Config(config_file=custom_config_path)

            # Verify the configuration values were loaded from the custom path
            self.assertEqual(test_config.get("api_rate_limit"), 8)
            self.assertEqual(test_config.get("max_workers"), 6)
            self.assertEqual(test_config.get_blacklist(), ["CustomApp1", "CustomApp2"])
            self.assertEqual(
                test_config.get("additional_app_dirs"),
                ["/custom/path1", "/custom/path2"],
            )
        finally:
            # Clean up the temporary file
            os.unlink(custom_config_path)
