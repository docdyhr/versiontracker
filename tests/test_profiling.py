"""Tests for the profiling module."""

import time
import unittest
from unittest.mock import Mock, patch

from versiontracker.profiling import (
    FunctionTimingInfo,
    PerformanceProfiler,
)


class TestFunctionTimingInfo(unittest.TestCase):
    """Test cases for FunctionTimingInfo class."""

    def test_init_default_values(self):
        """Test FunctionTimingInfo initialization with default values."""
        info = FunctionTimingInfo(name="test_function")
        self.assertEqual(info.name, "test_function")
        self.assertEqual(info.calls, 0)
        self.assertEqual(info.total_time, 0.0)
        self.assertEqual(info.min_time, float("inf"))
        self.assertEqual(info.max_time, 0.0)
        self.assertEqual(info.avg_time, 0.0)
        self.assertEqual(info.memory_before, 0.0)
        self.assertEqual(info.memory_after, 0.0)
        self.assertEqual(info.memory_diff, 0.0)

    def test_init_custom_values(self):
        """Test FunctionTimingInfo initialization with custom values."""
        info = FunctionTimingInfo(
            name="test_function",
            calls=5,
            total_time=10.0,
            min_time=1.0,
            max_time=3.0,
            avg_time=2.0,
            memory_before=100.0,
            memory_after=110.0,
            memory_diff=10.0,
        )
        self.assertEqual(info.name, "test_function")
        self.assertEqual(info.calls, 5)
        self.assertEqual(info.total_time, 10.0)
        self.assertEqual(info.min_time, 1.0)
        self.assertEqual(info.max_time, 3.0)
        self.assertEqual(info.avg_time, 2.0)
        self.assertEqual(info.memory_before, 100.0)
        self.assertEqual(info.memory_after, 110.0)
        self.assertEqual(info.memory_diff, 10.0)


class TestPerformanceProfiler(unittest.TestCase):
    """Test cases for PerformanceProfiler class."""

    def test_init_enabled(self):
        """Test PerformanceProfiler initialization when enabled."""
        profiler = PerformanceProfiler(enabled=True)
        self.assertTrue(profiler.enabled)
        self.assertIsNotNone(profiler.function_timings)
        self.assertIsNotNone(profiler.profiler)

    def test_init_disabled(self):
        """Test PerformanceProfiler initialization when disabled."""
        profiler = PerformanceProfiler(enabled=False)
        self.assertFalse(profiler.enabled)
        self.assertIsNotNone(profiler.function_timings)
        self.assertIsNone(profiler.profiler)

    def test_start_stop(self):
        """Test starting and stopping profiler."""
        profiler = PerformanceProfiler(enabled=True)

        # These methods should not raise exceptions
        profiler.start()
        profiler.stop()

    def test_function_timings_dict(self):
        """Test function_timings dictionary."""
        profiler = PerformanceProfiler()
        # Add some dummy timing info
        profiler.function_timings["test"] = FunctionTimingInfo("test", calls=5)

        self.assertIn("test", profiler.function_timings)
        self.assertEqual(len(profiler.function_timings), 1)

    def test_get_stats_disabled(self):
        """Test get_stats when profiler is disabled."""
        profiler = PerformanceProfiler(enabled=False)
        stats = profiler.get_stats()
        self.assertIsNone(stats)

    def test_get_stats_enabled(self):
        """Test get_stats when profiler is enabled."""
        profiler = PerformanceProfiler(enabled=True)
        # Start and stop profiling to populate the profiler
        profiler.start()
        profiler.stop()
        stats = profiler.get_stats()
        # Should return a string or None, not raise an exception
        self.assertTrue(isinstance(stats, (str, type(None))))

    def test_function_timings_attribute(self):
        """Test that function_timings attribute exists."""
        profiler = PerformanceProfiler(enabled=True)
        # The profiler should have a function_timings attribute (based on actual implementation)
        self.assertTrue(hasattr(profiler, "function_timings"))

    def test_time_function_decorator(self):
        """Test the time_function decorator method."""
        profiler = PerformanceProfiler(enabled=True)

        # Create a decorator
        decorator = profiler.time_function("test_function")

        # Test that it returns a callable
        self.assertTrue(callable(decorator))

    def test_report_method(self):
        """Test report method exists."""
        profiler = PerformanceProfiler()
        report = profiler.report()
        self.assertIsInstance(report, dict)

    def test_print_report_method(self):
        """Test print_report method exists."""
        profiler = PerformanceProfiler()
        # Should not raise an exception
        profiler.print_report()


class TestGlobalFunctions(unittest.TestCase):
    """Test cases for global profiling functions."""

    def test_get_profiler(self):
        """Test get_profiler function."""
        from versiontracker.profiling import get_profiler

        profiler = get_profiler()
        self.assertIsInstance(profiler, PerformanceProfiler)

    def test_enable_disable_profiling(self):
        """Test enable and disable profiling functions."""
        from versiontracker.profiling import (
            disable_profiling,
            enable_profiling,
            get_profiler,
        )

        profiler = get_profiler()
        initial_state = profiler.enabled

        enable_profiling()
        self.assertTrue(profiler.enabled)

        disable_profiling()
        self.assertFalse(profiler.enabled)

        # Restore initial state
        profiler.enabled = initial_state

    def test_generate_report(self):
        """Test generate_report function."""
        from versiontracker.profiling import generate_report

        report = generate_report()
        self.assertIsInstance(report, dict)

    def test_print_report_function(self):
        """Test print_report function."""
        from versiontracker.profiling import print_report

        # Should not raise an exception
        print_report()


if __name__ == "__main__":
    unittest.main()
