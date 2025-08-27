"""
Test module for configuration functionality.

This module provides basic tests for the config module.
"""

import os
import tempfile
from unittest.mock import patch

from versiontracker.config import Config, get_config


class TestConfig:
    """Tests for configuration management."""

    def test_default_config(self):
        """Test that default configuration loads properly."""
        config = Config()
        assert config is not None
        # Test some expected defaults
        assert hasattr(config, "max_workers")
        assert config.max_workers > 0

    def test_get_config_singleton(self):
        """Test that get_config returns the same instance."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_config_from_file(self):
        """Test loading configuration from a YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("max_workers: 10\n")
            f.write("cache_dir: /tmp/test_cache\n")
            temp_file = f.name

        try:
            config = Config(config_file=temp_file)
            assert config.max_workers == 10
            assert config.cache_dir == "/tmp/test_cache"
        finally:
            os.unlink(temp_file)

    def test_config_from_env(self):
        """Test that environment variables override config file."""
        # Save original env
        original_workers = os.environ.get("VERSIONTRACKER_MAX_WORKERS")

        try:
            os.environ["VERSIONTRACKER_MAX_WORKERS"] = "5"
            config = Config()
            assert config.max_workers == 5
        finally:
            # Restore original env
            if original_workers is not None:
                os.environ["VERSIONTRACKER_MAX_WORKERS"] = original_workers
            else:
                os.environ.pop("VERSIONTRACKER_MAX_WORKERS", None)
        self.assertEqual(config.get("log_level"), logging.DEBUG)

    @patch.dict(os.environ, {"VERSIONTRACKER_BLACKLIST": "App1,App2,App3"})
    def test_env_blacklist(self):
        """Test loading blacklist from environment."""
        config = Config()
        self.assertEqual(len(config.get_blacklist()), 3)
        self.assertTrue(config.is_blacklisted("App1"))
        self.assertTrue(config.is_blacklisted("App2"))
        self.assertTrue(config.is_blacklisted("App3"))


if __name__ == "__main__":
    unittest.main()
