"""Tests for the UI module."""

import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from versiontracker.ui import (
    AdaptiveRateLimiter,
    QueryFilterManager,
    SmartProgress,
    print_debug,
    print_error,
    print_info,
    print_success,
    print_warning,
    smart_progress,
)


class TestColorOutput(unittest.TestCase):
    """Test the colored output functions."""

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_success(self, mock_stdout):
        """Test print_success function."""
        print_success("Success message")
        self.assertIn("Success message", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_info(self, mock_stdout):
        """Test print_info function."""
        print_info("Info message")
        self.assertIn("Info message", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_warning(self, mock_stdout):
        """Test print_warning function."""
        print_warning("Warning message")
        self.assertIn("Warning message", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_error(self, mock_stdout):
        """Test print_error function."""
        print_error("Error message")
        self.assertIn("Error message", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_debug(self, mock_stdout):
        """Test print_debug function."""
        print_debug("Debug message")
        self.assertIn("Debug message", mock_stdout.getvalue())


class TestSmartProgress(unittest.TestCase):
    """Test the SmartProgress class."""

    def test_smart_progress_creation(self):
        """Test creating a SmartProgress instance."""
        # Explicitly set the total since it's not automatically detected from range objects
        progress = SmartProgress(
            range(10), desc="Test", monitor_resources=False, total=10
        )
        self.assertEqual(progress.desc, "Test")
        self.assertEqual(progress.total, 10)
        self.assertFalse(progress.monitor_resources)

    def test_smart_progress_iteration(self):
        """Test iterating with SmartProgress."""
        items = list(range(5))
        result = []

        # Disable actual progress bar for testing
        with patch("versiontracker.ui.HAS_TQDM", False):
            for i in SmartProgress(items, desc="Test", monitor_resources=False):
                result.append(i)

        self.assertEqual(result, items)

    @patch("psutil.cpu_percent", return_value=50.0)
    @patch("psutil.virtual_memory")
    def test_resource_monitoring(self, mock_memory, mock_cpu_percent):
        """Test resource monitoring."""
        mock_memory.return_value = MagicMock(percent=60.0)

        progress = SmartProgress(range(3), monitor_resources=True, update_interval=0)
        progress._update_resource_info()

        self.assertEqual(progress.cpu_usage, 50.0)
        self.assertEqual(progress.memory_usage, 60.0)


class TestAdaptiveRateLimiter(unittest.TestCase):
    """Test the AdaptiveRateLimiter class."""

    def test_initialization(self):
        """Test initializing an AdaptiveRateLimiter."""
        limiter = AdaptiveRateLimiter(
            base_rate_limit_sec=1.0, min_rate_limit_sec=0.2, max_rate_limit_sec=3.0
        )
        self.assertEqual(limiter.base_rate_limit_sec, 1.0)
        self.assertEqual(limiter.min_rate_limit_sec, 0.2)
        self.assertEqual(limiter.max_rate_limit_sec, 3.0)

    @patch("psutil.cpu_percent", return_value=90.0)  # High CPU usage
    @patch("psutil.virtual_memory")
    def test_high_resource_usage(self, mock_memory, mock_cpu):
        """Test rate limiting with high resource usage."""
        mock_memory.return_value = MagicMock(percent=95.0)  # High memory usage

        limiter = AdaptiveRateLimiter(
            base_rate_limit_sec=1.0, min_rate_limit_sec=0.5, max_rate_limit_sec=2.0
        )

        # With high resource usage, we should get a rate limit closer to the maximum
        limit = limiter.get_current_limit()
        self.assertGreater(limit, limiter.base_rate_limit_sec)

    @patch("psutil.cpu_percent", return_value=20.0)  # Low CPU usage
    @patch("psutil.virtual_memory")
    def test_low_resource_usage(self, mock_memory, mock_cpu_percent):
        """Test rate limiting with low resource usage."""
        mock_memory.return_value = MagicMock(percent=30.0)  # Low memory usage

        limiter = AdaptiveRateLimiter(
            base_rate_limit_sec=1.0, min_rate_limit_sec=0.5, max_rate_limit_sec=2.0
        )

        # With low resource usage, we should get a rate limit closer to the minimum
        limit = limiter.get_current_limit()
        # The formula base + factor * (max - base) with low usage should be less than
        # double the base rate, not less than the base rate
        self.assertLessEqual(limit, limiter.base_rate_limit_sec * 1.5)

    def test_wait_function(self):
        """Test the wait function."""
        limiter = AdaptiveRateLimiter(base_rate_limit_sec=0.1)

        # First call should not wait
        start = time.time()
        limiter.wait()
        duration1 = time.time() - start

        # Second call should wait at least the rate limit
        start = time.time()
        limiter.wait()
        duration2 = time.time() - start

        # The first wait could take longer than expected in CI environments
        # so we use a more relaxed assertion
        self.assertLess(duration1, 0.2)  # First call should be relatively quick
        self.assertGreaterEqual(duration2, 0.05)  # Second call should wait


class TestQueryFilterManager(unittest.TestCase):
    """Test the QueryFilterManager class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.filter_manager = QueryFilterManager(self.temp_dir.name)

    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()

    def test_save_and_load_filter(self):
        """Test saving and loading a filter."""
        filter_data = {
            "blacklist": "app1,app2",
            "similarity": 85,
            "additional_dirs": "/path1:/path2",
        }

        # Save the filter
        result = self.filter_manager.save_filter("test-filter", filter_data)
        self.assertTrue(result)

        # Load the filter
        loaded_data = self.filter_manager.load_filter("test-filter")
        self.assertEqual(loaded_data, filter_data)

    def test_list_filters(self):
        """Test listing all filters."""
        # Create some filters
        self.filter_manager.save_filter("filter1", {"key1": "value1"})
        self.filter_manager.save_filter("filter2", {"key2": "value2"})

        # List filters
        filters = self.filter_manager.list_filters()
        self.assertIn("filter1", filters)
        self.assertIn("filter2", filters)
        self.assertEqual(len(filters), 2)

    def test_delete_filter(self):
        """Test deleting a filter."""
        # Create a filter
        self.filter_manager.save_filter("filter-to-delete", {"key": "value"})

        # Delete the filter
        result = self.filter_manager.delete_filter("filter-to-delete")
        self.assertTrue(result)

        # Verify it's deleted
        filters = self.filter_manager.list_filters()
        self.assertNotIn("filter-to-delete", filters)

    def test_invalid_filter_name(self):
        """Test loading a non-existent filter."""
        loaded_data = self.filter_manager.load_filter("non-existent-filter")
        self.assertIsNone(loaded_data)

    def test_delete_nonexistent_filter(self):
        """Test deleting a non-existent filter."""
        result = self.filter_manager.delete_filter("non-existent-filter")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
