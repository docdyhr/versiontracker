"""Tests for the config module."""

import os
import unittest
from unittest.mock import patch

from versiontracker.config import Config


class TestConfig(unittest.TestCase):
    """Test cases for the Config class."""

    def setUp(self):
        """Set up test fixtures, if any."""
        # Clear any environment variables that might affect tests
        for var in os.environ.keys():
            if var.startswith("VERSIONTRACKER_"):
                del os.environ[var]

    def test_init_default_values(self):
        """Test that default values are set correctly."""
        config = Config()
        self.assertEqual(config.get("api_rate_limit"), 3)
        self.assertEqual(len(config.get_blacklist()), 8)
        self.assertTrue(config.get("show_progress"))

    def test_set_get(self):
        """Test setting and getting values."""
        config = Config()
        config.set("test_key", "test_value")
        self.assertEqual(config.get("test_key"), "test_value")
        self.assertIsNone(config.get("nonexistent_key"))
        self.assertEqual(config.get("nonexistent_key", "default"), "default")

    def test_is_blacklisted(self):
        """Test blacklist functionality."""
        config = Config()
        config.set("blacklist", ["App1", "App2"])
        self.assertTrue(config.is_blacklisted("App1"))
        self.assertTrue(config.is_blacklisted("app1"))  # Case insensitive
        self.assertFalse(config.is_blacklisted("App3"))

    @patch.dict(os.environ, {"VERSIONTRACKER_API_RATE_LIMIT": "5"})
    def test_env_api_rate_limit(self):
        """Test loading API rate limit from environment."""
        config = Config()
        self.assertEqual(config.get("api_rate_limit"), 5)

    @patch.dict(os.environ, {"VERSIONTRACKER_DEBUG": "true"})
    def test_env_debug(self):
        """Test loading debug mode from environment."""
        import logging

        config = Config()
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
