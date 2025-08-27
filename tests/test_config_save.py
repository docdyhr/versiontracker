"""Test cases for Config save method functionality."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

import yaml

from versiontracker.config import Config


class TestConfigSave(unittest.TestCase):
    """Test cases for Config save method."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "config.yaml"
        self.config = Config(config_file=str(self.config_file))

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_creates_directory_if_not_exists(self):
        """Test that save creates parent directories if they don't exist."""
        # Create config with non-existent directory
        nested_path = Path(self.temp_dir) / "nested" / "dir" / "config.yaml"
        config = Config(config_file=str(nested_path))

        # Set some values
        config.set("test_key", "test_value")
        config.set("blacklist", ["app1", "app2"])

        # Save should create directories
        result = config.save()

        self.assertTrue(result)
        self.assertTrue(nested_path.parent.exists())
        self.assertTrue(nested_path.exists())

    def test_save_writes_correct_yaml_content(self):
        """Test that save writes correct YAML content."""
        # Set various configuration values
        self.config.set("blacklist", ["app1", "app2", "app3"])
        self.config.set("api_rate_limit", 5)
        self.config.set("show_progress", True)
        self.config.set("ui", {"use_color": True, "monitor_resources": False})

        # Save configuration
        result = self.config.save()
        self.assertTrue(result)

        # Read and verify the saved content
        with open(self.config_file) as f:
            saved_data = yaml.safe_load(f)

        self.assertEqual(saved_data["blacklist"], ["app1", "app2", "app3"])
        self.assertEqual(saved_data["api_rate_limit"], 5)
        self.assertEqual(saved_data["show_progress"], True)
        self.assertEqual(saved_data["ui"]["use_color"], True)
        self.assertEqual(saved_data["ui"]["monitor_resources"], False)

    def test_save_excludes_non_serializable_fields(self):
        """Test that save excludes config_file and log_dir fields."""
        # Set some values including ones that should be excluded
        self.config.set("blacklist", ["app1"])
        self.config.set("test_value", "included")

        # Save configuration
        result = self.config.save()
        self.assertTrue(result)

        # Read and verify the saved content
        with open(self.config_file) as f:
            saved_data = yaml.safe_load(f)

        # These should not be in the saved file
        self.assertNotIn("config_file", saved_data)
        self.assertNotIn("log_dir", saved_data)

        # These should be included
        self.assertIn("blacklist", saved_data)
        self.assertIn("test_value", saved_data)

    def test_save_converts_path_objects_to_strings(self):
        """Test that Path objects are converted to strings when saving."""
        # Set a Path value
        test_path = Path("/some/test/path")
        self.config.set("custom_path", test_path)

        # Save configuration
        result = self.config.save()
        self.assertTrue(result)

        # Read and verify the saved content
        with open(self.config_file) as f:
            saved_data = yaml.safe_load(f)

        self.assertEqual(saved_data["custom_path"], "/some/test/path")
        self.assertIsInstance(saved_data["custom_path"], str)

    def test_save_preserves_nested_structures(self):
        """Test that nested configuration structures are preserved."""
        # Set nested configuration
        self.config.set(
            "version_comparison",
            {"rate_limit": 3, "cache_ttl": 24, "similarity_threshold": 80, "nested": {"deep": {"value": "preserved"}}},
        )

        # Save configuration
        result = self.config.save()
        self.assertTrue(result)

        # Read and verify the saved content
        with open(self.config_file) as f:
            saved_data = yaml.safe_load(f)

        self.assertEqual(saved_data["version_comparison"]["rate_limit"], 3)
        self.assertEqual(saved_data["version_comparison"]["cache_ttl"], 24)
        self.assertEqual(saved_data["version_comparison"]["nested"]["deep"]["value"], "preserved")

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    @patch("pathlib.Path.mkdir")
    def test_save_handles_permission_error(self, mock_mkdir, mock_open_file):
        """Test that save handles permission errors gracefully."""
        # Try to save when file cannot be written
        self.config.set("test_key", "test_value")

        result = self.config.save()

        self.assertFalse(result)

    @patch("yaml.dump", side_effect=yaml.YAMLError("YAML error"))
    def test_save_handles_yaml_error(self, mock_yaml_dump):
        """Test that save handles YAML serialization errors."""
        # Try to save when YAML serialization fails
        self.config.set("test_key", "test_value")

        with patch("builtins.open", mock_open()):
            result = self.config.save()

        self.assertFalse(result)

    def test_save_with_empty_config(self):
        """Test saving an empty configuration."""
        # Don't set any values, just save
        result = self.config.save()

        self.assertTrue(result)
        self.assertTrue(self.config_file.exists())

        # Read and verify the content
        with open(self.config_file) as f:
            saved_data = yaml.safe_load(f)

        # Should have default values but not config_file or log_dir
        self.assertIsInstance(saved_data, dict)
        self.assertNotIn("config_file", saved_data)
        self.assertNotIn("log_dir", saved_data)

    def test_save_sorts_keys(self):
        """Test that saved YAML has sorted keys."""
        # Set values in non-alphabetical order
        self.config.set("zebra", "value")
        self.config.set("alpha", "value")
        self.config.set("beta", "value")

        # Save configuration
        result = self.config.save()
        self.assertTrue(result)

        # Read the raw file content
        with open(self.config_file) as f:
            content = f.read()

        # Keys should appear in alphabetical order
        alpha_pos = content.find("alpha:")
        beta_pos = content.find("beta:")
        zebra_pos = content.find("zebra:")

        self.assertLess(alpha_pos, beta_pos)
        self.assertLess(beta_pos, zebra_pos)

    def test_save_updates_existing_file(self):
        """Test that save updates an existing file correctly."""
        # Create initial config file
        initial_data = {"existing_key": "existing_value", "blacklist": ["old_app"]}
        with open(self.config_file, "w") as f:
            yaml.dump(initial_data, f)

        # Load config and modify
        config = Config(config_file=str(self.config_file))
        config.set("blacklist", ["new_app1", "new_app2"])
        config.set("new_key", "new_value")

        # Save configuration
        result = config.save()
        self.assertTrue(result)

        # Read and verify the updated content
        with open(self.config_file) as f:
            saved_data = yaml.safe_load(f)

        # Should have new values
        self.assertEqual(saved_data["blacklist"], ["new_app1", "new_app2"])
        self.assertEqual(saved_data["new_key"], "new_value")
        # Original keys should still exist if not overwritten
        self.assertIn("existing_key", saved_data)

    @patch("logging.error")
    def test_save_logs_errors(self, mock_log_error):
        """Test that save logs errors when they occur."""
        # Create a config with an invalid path
        with patch("builtins.open", side_effect=OSError("File error")):
            result = self.config.save()

        self.assertFalse(result)
        mock_log_error.assert_called_once()
        error_message = mock_log_error.call_args[0][0]
        self.assertIn("Failed to save configuration", error_message)

    def test_save_with_special_characters(self):
        """Test saving configuration with special characters."""
        # Set values with special characters
        self.config.set("blacklist", ["App with spaces", "App-with-dashes", "App_with_underscores"])
        self.config.set("special_chars", "Value with 'quotes' and \"double quotes\"")
        self.config.set("unicode", "App with émojis 🚀 and ñ characters")

        # Save configuration
        result = self.config.save()
        self.assertTrue(result)

        # Read and verify the saved content
        with open(self.config_file, encoding="utf-8") as f:
            saved_data = yaml.safe_load(f)

        self.assertEqual(len(saved_data["blacklist"]), 3)
        self.assertIn("App with spaces", saved_data["blacklist"])
        self.assertEqual(saved_data["special_chars"], "Value with 'quotes' and \"double quotes\"")
        self.assertEqual(saved_data["unicode"], "App with émojis 🚀 and ñ characters")


if __name__ == "__main__":
    unittest.main()
