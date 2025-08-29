"""Tests for the cache module."""

import json
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from versiontracker.cache import (
    CACHE_DIR,
    CacheError,
    _ensure_cache_dir,
    clear_cache,
    read_cache,
    write_cache,
)


class TestCache(unittest.TestCase):
    """Test cases for the cache module."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        # Save the original CACHE_DIR
        self.original_cache_dir = CACHE_DIR
        # Patch CACHE_DIR to use our temporary directory
        self.patcher = patch("versiontracker.cache.CACHE_DIR", self.temp_dir)
        self.mock_cache_dir = self.patcher.start()

    def tearDown(self):
        """Tear down test fixtures."""
        # Stop the patcher
        self.patcher.stop()
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ensure_cache_dir(self):
        """Test _ensure_cache_dir creates the directory."""
        # Call the function
        _ensure_cache_dir()
        # Check the directory exists
        self.assertTrue(os.path.exists(self.temp_dir))

    def test_ensure_cache_dir_already_exists(self):
        """Test _ensure_cache_dir when directory already exists."""
        # Create the directory
        os.makedirs(self.temp_dir, exist_ok=True)
        # Call the function
        _ensure_cache_dir()
        # Check the directory exists
        self.assertTrue(os.path.exists(self.temp_dir))

    def test_ensure_cache_dir_error(self):
        """Test _ensure_cache_dir when an error occurs."""
        # Mock os.path.exists to return False so makedirs is called
        # Mock os.makedirs to raise an exception
        with (
            patch("os.path.exists", return_value=False),
            patch("os.makedirs", side_effect=PermissionError("Permission denied")),
        ):
            # Call the function and check it raises CacheError
            with self.assertRaises(CacheError):
                _ensure_cache_dir()

    def test_read_cache_not_exists(self):
        """Test reading non-existent cache."""
        # Call the function
        result = read_cache("test_cache")
        # Check the result is None
        self.assertIsNone(result)

    def test_read_cache_expired(self):
        """Test reading expired cache."""
        # Create a cache file
        cache_file = os.path.join(self.temp_dir, "test_cache.json")
        os.makedirs(self.temp_dir, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump({"test": "data"}, f)

        # Set the modification time to a day ago
        old_time = time.time() - 100000  # More than a day ago
        os.utime(cache_file, (old_time, old_time))

        # Call the function with a max age of 1 hour
        result = read_cache("test_cache", max_age_seconds=3600)

        # Check the result is None (cache expired)
        self.assertIsNone(result)

    def test_read_cache_valid(self):
        """Test reading valid cache."""
        # Create a cache file
        cache_file = os.path.join(self.temp_dir, "test_cache.json")
        os.makedirs(self.temp_dir, exist_ok=True)
        test_data = {"test": "data"}
        with open(cache_file, "w") as f:
            json.dump(test_data, f)

        # Call the function
        result = read_cache("test_cache")

        # Check the result matches the data
        self.assertEqual(result, test_data)

    def test_read_cache_invalid_json(self):
        """Test reading cache with invalid JSON."""
        # Create a cache file with invalid JSON
        cache_file = os.path.join(self.temp_dir, "test_cache.json")
        os.makedirs(self.temp_dir, exist_ok=True)
        with open(cache_file, "w") as f:
            f.write("invalid json")

        # Call the function
        result = read_cache("test_cache")

        # Check the result is None
        self.assertIsNone(result)

    def test_read_cache_exception(self):
        """Test reading cache with an exception."""
        # Mock open to raise an exception
        with patch("builtins.open", side_effect=Exception("Test error")):
            # Call the function
            result = read_cache("test_cache")
            # Check the result is None
            self.assertIsNone(result)

    def test_write_cache_success(self):
        """Test successful cache writing."""
        # Test data
        test_data = {"test": "data"}

        # Call the function
        result = write_cache("test_cache", test_data)

        # Check the function returned True
        self.assertTrue(result)

        # Check the file was created with the correct data
        cache_file = os.path.join(self.temp_dir, "test_cache.json")
        with open(cache_file) as f:
            data = json.load(f)
        self.assertEqual(data, test_data)

    def test_write_cache_exception(self):
        """Test writing cache with an exception."""
        # Mock open to raise an exception
        with patch("builtins.open", side_effect=Exception("Test error")):
            # Call the function and check it raises CacheError
            with self.assertRaises(CacheError):
                write_cache("test_cache", {"test": "data"})

    def test_clear_cache_specific(self):
        """Test clearing a specific cache."""
        # Create two cache files
        os.makedirs(self.temp_dir, exist_ok=True)
        cache_file1 = os.path.join(self.temp_dir, "test_cache1.json")
        cache_file2 = os.path.join(self.temp_dir, "test_cache2.json")
        with open(cache_file1, "w") as f:
            f.write("{}")
        with open(cache_file2, "w") as f:
            f.write("{}")

        # Call the function to clear only the first cache
        result = clear_cache("test_cache1")

        # Check the function returned True
        self.assertTrue(result)

        # Check the first file was removed and the second still exists
        self.assertFalse(os.path.exists(cache_file1))
        self.assertTrue(os.path.exists(cache_file2))

    def test_clear_cache_all(self):
        """Test clearing all caches."""
        # Create two cache files
        os.makedirs(self.temp_dir, exist_ok=True)
        cache_file1 = os.path.join(self.temp_dir, "test_cache1.json")
        cache_file2 = os.path.join(self.temp_dir, "test_cache2.json")
        with open(cache_file1, "w") as f:
            f.write("{}")
        with open(cache_file2, "w") as f:
            f.write("{}")

        # Call the function to clear all caches
        result = clear_cache()

        # Check the function returned True
        self.assertTrue(result)

        # Check both files were removed
        self.assertFalse(os.path.exists(cache_file1))
        self.assertFalse(os.path.exists(cache_file2))

    def test_clear_cache_exception(self):
        """Test clearing cache with an exception."""
        # Mock os.remove to raise an exception
        with patch("os.remove", side_effect=Exception("Test error")):
            # Create a cache file
            os.makedirs(self.temp_dir, exist_ok=True)
            cache_file = os.path.join(self.temp_dir, "test_cache.json")
            with open(cache_file, "w") as f:
                f.write("{}")

            # Call the function and check it raises CacheError
            with self.assertRaises(CacheError):
                clear_cache("test_cache")


if __name__ == "__main__":
    unittest.main()
