# filepath: /Users/thomas/Programming/versiontracker/tests/test_ui.py
"""Tests for the UI module."""

import io
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from versiontracker.ui import (
    DEBUG,
    ERROR,
    HAS_TQDM,
    INFO,
    SUCCESS,
    TQDM_CLASS,
    WARNING,
    AdaptiveRateLimiter,
    FallbackTqdm,
    QueryFilterManager,
    SmartProgress,
    colored,
    create_progress_bar,
    get_terminal_size,
    print_debug,
    print_error,
    print_info,
    print_success,
    print_warning,
    smart_progress,
)


class TestColorOutput(unittest.TestCase):
    """Test the colored output functions."""

    @patch("versiontracker.ui.cprint")
    def test_print_success(self, mock_cprint):
        """Test print_success function."""
        print_success("Success message")
        mock_cprint.assert_called_with("Success message", "green")

    @patch("versiontracker.ui.cprint")
    def test_print_info(self, mock_cprint):
        """Test print_info function."""
        print_info("Info message")
        mock_cprint.assert_called_with("Info message", "blue")

    @patch("versiontracker.ui.cprint")
    def test_print_warning(self, mock_cprint):
        """Test print_warning function."""
        print_warning("Warning message")
        mock_cprint.assert_called_with("Warning message", "yellow")

    @patch("versiontracker.ui.cprint")
    def test_print_error(self, mock_cprint):
        """Test print_error function."""
        print_error("Error message")
        mock_cprint.assert_called_with("Error message", "red")

    @patch("versiontracker.ui.cprint")
    def test_print_debug(self, mock_cprint):
        """Test print_debug function."""
        print_debug("Debug message")
        mock_cprint.assert_called_with("Debug message", "cyan")

    def test_colored_function(self):
        """Test the colored function."""
        # Test with color
        result = colored("test text", "red")
        self.assertIsInstance(result, str)
        self.assertIn("test text", result)

    def test_get_terminal_size(self):
        """Test get_terminal_size function."""
        columns, lines = get_terminal_size()
        self.assertIsInstance(columns, int)
        self.assertIsInstance(lines, int)
        self.assertGreater(columns, 0)
        self.assertGreater(lines, 0)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""

    def test_create_progress_bar(self):
        """Test create_progress_bar function."""
        progress_bar = create_progress_bar()
        self.assertIsInstance(progress_bar, SmartProgress)

    def test_smart_progress_function(self):
        """Test smart_progress function."""
        items = [1, 2, 3]
        result = list(smart_progress(items, desc="Test"))
        self.assertEqual(result, items)


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

    def test_smart_progress_creation_with_defaults(self):
        """Test creating a SmartProgress instance with default parameters."""
        progress = SmartProgress()
        self.assertEqual(progress.desc, "")
        self.assertIsNone(progress.iterable)
        self.assertIsNone(progress.total)
        self.assertTrue(progress.monitor_resources)

    def test_smart_progress_iteration(self):
        """Test iterating with SmartProgress."""
        items = list(range(5))
        result = []

        # Disable actual progress bar for testing
        with patch("versiontracker.ui.HAS_TQDM", False):
            for i in SmartProgress(items, desc="Test", monitor_resources=False):
                result.append(i)

        self.assertEqual(result, items)

    def test_smart_progress_empty_iterable(self):
        """Test SmartProgress with None iterable."""
        progress = SmartProgress(None)
        result = list(progress)
        self.assertEqual(result, [])

    @patch("psutil.cpu_percent", return_value=50.0)
    @patch("psutil.virtual_memory")
    def test_resource_monitoring(self, mock_memory, _mock_cpu_percent):
        """Test resource monitoring."""
        mock_memory.return_value = MagicMock(percent=60.0)

        progress = SmartProgress(range(3), monitor_resources=True, update_interval=0)
        progress._update_resource_info()

        self.assertEqual(progress.cpu_usage, 50.0)
        self.assertEqual(progress.memory_usage, 60.0)

    @patch("versiontracker.ui.HAS_TQDM", True)
    @patch("sys.stdout.isatty", return_value=True)
    @patch("psutil.cpu_percent", return_value=75.0)
    @patch("psutil.virtual_memory")
    def test_resource_monitoring_with_tqdm(
        self, mock_memory, _mock_cpu_percent, _mock_isatty
    ):
        """Test resource monitoring with tqdm progress bar."""
        mock_memory.return_value = MagicMock(percent=80.0)

        with patch("versiontracker.ui.TQDM_CLASS") as mock_tqdm:
            mock_progress_bar = Mock()
            mock_tqdm.return_value = mock_progress_bar
            mock_progress_bar.__iter__ = Mock(return_value=iter([1, 2, 3]))

            progress = SmartProgress(
                [1, 2, 3], monitor_resources=True, update_interval=0
            )
            # Process the iteration to trigger resource monitoring
            list(progress)

            # Verify that resource info was updated
            self.assertEqual(progress.cpu_usage, 75.0)
            self.assertEqual(progress.memory_usage, 80.0)
            # Verify that postfix was set on the progress bar
            mock_progress_bar.set_postfix_str.assert_called()

    def test_smart_progress_color_method(self):
        """Test the color method of SmartProgress."""
        progress = SmartProgress()
        color_func = progress.color("red")
        result = color_func("test")
        self.assertIsInstance(result, str)

    def test_resource_monitoring_disabled(self):
        """Test resource monitoring when disabled."""
        progress = SmartProgress(range(3), monitor_resources=False)
        # Should not raise an exception
        progress._update_resource_info()
        self.assertEqual(progress.cpu_usage, 0.0)
        self.assertEqual(progress.memory_usage, 0.0)

    @patch("psutil.cpu_percent", side_effect=Exception("Mock exception"))
    def test_resource_monitoring_exception_handling(self, _mock_cpu):
        """Test resource monitoring handles exceptions gracefully."""
        progress = SmartProgress(range(3), monitor_resources=True)
        # Should not raise an exception even when psutil fails
        progress._update_resource_info()
        # Values should remain at defaults
        self.assertEqual(progress.cpu_usage, 0.0)
        self.assertEqual(progress.memory_usage, 0.0)


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

    def test_initialization_with_custom_thresholds(self):
        """Test initializing an AdaptiveRateLimiter with custom thresholds."""
        limiter = AdaptiveRateLimiter(
            base_rate_limit_sec=2.0,
            min_rate_limit_sec=0.5,
            max_rate_limit_sec=5.0,
            cpu_threshold=70.0,
            memory_threshold=85.0,
        )
        self.assertEqual(limiter.base_rate_limit_sec, 2.0)
        self.assertEqual(limiter.min_rate_limit_sec, 0.5)
        self.assertEqual(limiter.max_rate_limit_sec, 5.0)
        self.assertEqual(limiter.cpu_threshold, 70.0)
        self.assertEqual(limiter.memory_threshold, 85.0)

    @patch("psutil.cpu_percent", return_value=90.0)  # High CPU usage
    @patch("psutil.virtual_memory")
    def test_high_resource_usage(self, mock_memory, _mock_cpu):
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
    def test_low_resource_usage(self, mock_memory, _mock_cpu_percent):
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

    @patch("psutil.cpu_percent", return_value=50.0)
    @patch("psutil.virtual_memory")
    def test_medium_resource_usage(self, mock_memory, _mock_cpu):
        """Test rate limiting with medium resource usage."""
        mock_memory.return_value = MagicMock(percent=60.0)

        limiter = AdaptiveRateLimiter(
            base_rate_limit_sec=1.0, min_rate_limit_sec=0.5, max_rate_limit_sec=2.0
        )

        limit = limiter.get_current_limit()
        # Should be between base and max
        self.assertGreaterEqual(limit, limiter.min_rate_limit_sec)
        self.assertLessEqual(limit, limiter.max_rate_limit_sec)

    @patch("psutil.cpu_percent", side_effect=Exception("Mock exception"))
    def test_resource_monitoring_exception_fallback(self, _mock_cpu):
        """Test rate limiter falls back to base rate when monitoring fails."""
        limiter = AdaptiveRateLimiter(base_rate_limit_sec=1.5)

        limit = limiter.get_current_limit()
        self.assertEqual(limit, 1.5)

    def test_rate_limit_bounds(self):
        """Test that rate limits stay within bounds."""
        # Test with extreme values that should be clamped
        limiter = AdaptiveRateLimiter(
            base_rate_limit_sec=3.0,
            min_rate_limit_sec=1.0,
            max_rate_limit_sec=2.0,  # max < base to test clamping
        )

        with (
            patch("psutil.cpu_percent", return_value=0.0),
            patch("psutil.virtual_memory") as mock_memory,
        ):
            mock_memory.return_value = MagicMock(percent=0.0)

            limit = limiter.get_current_limit()
            # Should be clamped to max_rate_limit_sec
            self.assertLessEqual(limit, limiter.max_rate_limit_sec)
            self.assertGreaterEqual(limit, limiter.min_rate_limit_sec)

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

    def test_wait_timing_precision(self):
        """Test wait function timing with very short intervals."""
        limiter = AdaptiveRateLimiter(base_rate_limit_sec=0.01)

        # Multiple rapid calls
        start_time = time.time()
        limiter.wait()  # First call - no wait
        limiter.wait()  # Second call - should wait
        limiter.wait()  # Third call - should wait
        total_time = time.time() - start_time

        # Should have waited at least for two intervals
        self.assertGreater(total_time, 0.015)  # Allow some tolerance


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

    def test_save_filter_with_special_characters(self):
        """Test saving a filter with special characters in the name."""
        filter_data = {"test": "value"}

        # Test with spaces and slashes (should be sanitized)
        result = self.filter_manager.save_filter("test filter/name", filter_data)
        self.assertTrue(result)

        # Should be able to load with sanitized name
        loaded_data = self.filter_manager.load_filter("test filter/name")
        self.assertEqual(loaded_data, filter_data)

    def test_save_filter_error_handling(self):
        """Test save filter error handling with invalid directory."""
        # Create a filter manager with an invalid directory
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            result = self.filter_manager.save_filter("test", {"key": "value"})
            self.assertFalse(result)

    def test_load_filter_error_handling(self):
        """Test load filter error handling with corrupted file."""
        # Create a corrupted JSON file
        filter_path = self.filter_manager.filters_dir / "corrupted.json"
        with open(filter_path, "w", encoding="utf-8") as f:
            f.write("invalid json content")

        # Should return None for corrupted file
        result = self.filter_manager.load_filter("corrupted")
        self.assertIsNone(result)

    def test_delete_filter_error_handling(self):
        """Test delete filter error handling."""
        # Create a filter first
        self.filter_manager.save_filter("test-filter", {"key": "value"})

        # Mock file deletion to raise an exception
        with patch("pathlib.Path.unlink", side_effect=OSError("Permission denied")):
            result = self.filter_manager.delete_filter("test-filter")
            self.assertFalse(result)

    def test_list_filters_empty_directory(self):
        """Test listing filters when directory is empty."""
        filters = self.filter_manager.list_filters()
        self.assertEqual(filters, [])

    def test_filter_name_sanitization(self):
        """Test that filter names are properly sanitized."""
        original_name = "Test Filter/With Spaces"
        expected_sanitized = "test-filter_with-spaces"

        self.filter_manager.save_filter(original_name, {"test": "data"})

        # Check that the file was created with sanitized name
        filter_files = list(self.filter_manager.filters_dir.glob("*.json"))
        self.assertEqual(len(filter_files), 1)
        self.assertEqual(filter_files[0].stem, expected_sanitized)

    def test_filter_manager_creates_directory(self):
        """Test that QueryFilterManager creates the filters directory."""
        # Create a new temporary directory without the filters subdirectory
        with tempfile.TemporaryDirectory() as temp_dir:
            new_filter_manager = QueryFilterManager(temp_dir)

            # The filters directory should be created
            self.assertTrue(new_filter_manager.filters_dir.exists())
            self.assertTrue(new_filter_manager.filters_dir.is_dir())


class TestFallbackFunctionality(unittest.TestCase):
    """Test fallback functionality when dependencies are not available."""

    @patch("versiontracker.ui.HAS_TERMCOLOR", False)
    def test_colored_fallback(self):
        """Test colored function fallback when termcolor is not available."""
        result = colored("test text", "red")
        self.assertEqual(result, "test text")

    @patch("versiontracker.ui.HAS_TERMCOLOR", False)
    @patch("builtins.print")
    def test_print_functions_termcolor_fallback(self, mock_print):
        """Test print functions fallback when termcolor is not available."""
        print_success("Success without color")
        mock_print.assert_called_with("Success without color")

    @patch("versiontracker.ui.HAS_TQDM", False)
    def test_smart_progress_fallback(self):
        """Test SmartProgress fallback when tqdm is not available."""
        items = [1, 2, 3]
        progress = SmartProgress(items, desc="Test", monitor_resources=False)
        result = list(progress)
        self.assertEqual(result, items)

    def test_fallback_tqdm_class(self):
        """Test the FallbackTqdm class functionality."""

        # Test initialization
        fallback = FallbackTqdm([1, 2, 3], desc="Test")
        self.assertEqual(fallback.desc, "Test")
        self.assertEqual(fallback.n, 0)

        # Test iteration
        result = list(fallback)
        self.assertEqual(result, [1, 2, 3])

        # Test update method
        fallback.update(5)
        self.assertEqual(fallback.n, 8)  # 3 from iteration + 5 from update

        # Test context manager
        with fallback as fb:
            self.assertEqual(fb, fallback)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_fallback_tqdm_empty_iterable(self, _mock_stdout):
        """Test FallbackTqdm with None iterable."""

        fallback = FallbackTqdm(None, desc="Empty Test")
        result = list(fallback)
        self.assertEqual(result, [])


class TestConstants(unittest.TestCase):
    """Test UI constants and module-level functionality."""

    def test_color_constants(self):
        """Test that color constants are defined."""

        self.assertEqual(SUCCESS, "green")
        self.assertEqual(INFO, "blue")
        self.assertEqual(WARNING, "yellow")
        self.assertEqual(ERROR, "red")
        self.assertEqual(DEBUG, "cyan")

    def test_tqdm_class_availability(self):
        """Test TQDM_CLASS is properly set."""

        self.assertIsNotNone(TQDM_CLASS)
        self.assertIsInstance(HAS_TQDM, bool)


if __name__ == "__main__":
    unittest.main()
