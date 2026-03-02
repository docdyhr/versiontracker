"""Tests for versiontracker.profiling — coverage improvement.

Covers PerformanceProfiler (enabled/disabled paths), nested call tracking,
memory usage, timing stats, time_function decorator, report/print_report,
and module-level convenience functions.
"""

from unittest.mock import patch

import versiontracker.profiling as profiling_module
from versiontracker.profiling import (
    PerformanceProfiler,
    disable_profiling,
    enable_profiling,
    generate_report,
    get_profiler,
    print_report,
    profile_function,
)

# ---------------------------------------------------------------------------
# PerformanceProfiler — init
# ---------------------------------------------------------------------------


class TestPerformanceProfilerInit:
    """Tests for PerformanceProfiler initialization."""

    def test_enabled_creates_real_profiler(self):
        """enabled=True creates a cProfile.Profile instance."""
        p = PerformanceProfiler(enabled=True)
        assert p.enabled is True
        assert p.profiler is not None

    def test_disabled_has_no_profiler(self):
        """enabled=False sets profiler to None."""
        p = PerformanceProfiler(enabled=False)
        assert p.enabled is False
        assert p.profiler is None


# ---------------------------------------------------------------------------
# start / stop
# ---------------------------------------------------------------------------


class TestStartStop:
    """Tests for start() and stop()."""

    def test_start_stop_when_enabled(self):
        """start() and stop() succeed without error when enabled."""
        p = PerformanceProfiler(enabled=True)
        p.start()
        p.stop()
        # No exception means success

    def test_start_stop_when_disabled(self):
        """start() and stop() are no-ops when disabled."""
        p = PerformanceProfiler(enabled=False)
        p.start()
        p.stop()
        # No exception means success


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------


class TestGetStats:
    """Tests for get_stats()."""

    def test_get_stats_when_enabled(self):
        """get_stats returns a string when enabled (may be empty for trivial code)."""
        p = PerformanceProfiler(enabled=True)
        p.start()
        # Run some code that is heavy enough for cProfile to capture
        for _ in range(1000):
            _ = sum(range(100))
        p.stop()
        stats = p.get_stats()
        assert isinstance(stats, str)

    def test_get_stats_when_disabled(self):
        """get_stats returns None when disabled."""
        p = PerformanceProfiler(enabled=False)
        assert p.get_stats() is None


# ---------------------------------------------------------------------------
# _track_nested_calls
# ---------------------------------------------------------------------------


class TestTrackNestedCalls:
    """Tests for _track_nested_calls()."""

    def test_first_call_returns_true(self):
        """First call for a function name returns True (outermost)."""
        p = PerformanceProfiler(enabled=True)
        assert p._track_nested_calls("my_func") is True
        assert "my_func" in p._active_functions

    def test_second_call_returns_false(self):
        """Second call for same function name returns False (nested)."""
        p = PerformanceProfiler(enabled=True)
        p._track_nested_calls("my_func")
        assert p._track_nested_calls("my_func") is False
        assert p._nested_calls["my_func"] == 1

    def test_different_functions_both_outermost(self):
        """Different function names are independently tracked as outermost."""
        p = PerformanceProfiler(enabled=True)
        assert p._track_nested_calls("func_a") is True
        assert p._track_nested_calls("func_b") is True


# ---------------------------------------------------------------------------
# _get_memory_usage
# ---------------------------------------------------------------------------


class TestGetMemoryUsage:
    """Tests for _get_memory_usage()."""

    def test_with_psutil_available(self):
        """Returns float > 0 when psutil is available."""
        p = PerformanceProfiler(enabled=True)
        # Only test if psutil is actually available
        if profiling_module.HAS_PSUTIL:
            result = p._get_memory_usage()
            assert isinstance(result, float)
            assert result > 0.0

    def test_without_psutil(self):
        """Returns 0.0 when HAS_PSUTIL is False."""
        p = PerformanceProfiler(enabled=True)
        with patch.object(profiling_module, "HAS_PSUTIL", False):
            result = p._get_memory_usage()
            assert result == 0.0


# ---------------------------------------------------------------------------
# _update_timing_stats
# ---------------------------------------------------------------------------


class TestUpdateTimingStats:
    """Tests for _update_timing_stats()."""

    def test_first_call_creates_entry(self):
        """First call creates a FunctionTimingInfo entry."""
        p = PerformanceProfiler(enabled=True)
        p._update_timing_stats("func", 0.5, 100.0, 101.0)
        assert "func" in p.function_timings
        info = p.function_timings["func"]
        assert info.calls == 1
        assert info.total_time == 0.5
        assert info.min_time == 0.5
        assert info.max_time == 0.5
        assert info.avg_time == 0.5
        assert info.memory_diff == 1.0

    def test_multiple_calls_update_stats(self):
        """Multiple calls update min, max, avg correctly."""
        p = PerformanceProfiler(enabled=True)
        p._update_timing_stats("func", 0.2, 100.0, 100.5)
        p._update_timing_stats("func", 0.8, 100.0, 101.0)
        info = p.function_timings["func"]
        assert info.calls == 2
        assert info.total_time == 1.0
        assert info.min_time == 0.2
        assert info.max_time == 0.8
        assert abs(info.avg_time - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# _cleanup_nested_calls
# ---------------------------------------------------------------------------


class TestCleanupNestedCalls:
    """Tests for _cleanup_nested_calls()."""

    def test_outermost_removes_from_active(self):
        """Outermost call cleanup removes function from _active_functions."""
        p = PerformanceProfiler(enabled=True)
        p._active_functions.add("func")
        p._cleanup_nested_calls("func", is_outermost_call=True)
        assert "func" not in p._active_functions

    def test_nested_decrements_count(self):
        """Nested call cleanup decrements the nested call counter."""
        p = PerformanceProfiler(enabled=True)
        p._nested_calls["func"] = 2
        p._cleanup_nested_calls("func", is_outermost_call=False)
        assert p._nested_calls["func"] == 1

    def test_nested_removes_when_count_reaches_zero(self):
        """Nested call cleanup removes entry when count reaches 0."""
        p = PerformanceProfiler(enabled=True)
        p._nested_calls["func"] = 1
        p._cleanup_nested_calls("func", is_outermost_call=False)
        assert "func" not in p._nested_calls


# ---------------------------------------------------------------------------
# time_function decorator
# ---------------------------------------------------------------------------


class TestTimeFunctionDecorator:
    """Tests for time_function() decorator."""

    def test_enabled_wraps_function_and_records_timing(self):
        """Decorator wraps function and records timing when enabled."""
        p = PerformanceProfiler(enabled=True)

        @p.time_function("test_add")
        def add(a, b):
            return a + b

        result = add(2, 3)
        assert result == 5
        assert "test_add" in p.function_timings
        assert p.function_timings["test_add"].calls == 1

    def test_disabled_returns_original_function(self):
        """Decorator returns original function without wrapping when disabled."""
        p = PerformanceProfiler(enabled=False)

        def original(x):
            return x * 2

        decorated = p.time_function("test")(original)
        # When disabled, the decorator should return the original function
        assert decorated is original

    def test_uses_qualname_when_no_name_given(self):
        """Decorator uses func.__qualname__ when func_name is None."""
        p = PerformanceProfiler(enabled=True)

        @p.time_function()
        def my_special_func():
            return 42

        my_special_func()
        # The key should contain the qualname
        keys = list(p.function_timings.keys())
        assert any("my_special_func" in k for k in keys)

    def test_nested_calls_only_time_outermost(self):
        """Nested calls to the same decorated function only time the outermost."""
        p = PerformanceProfiler(enabled=True)

        call_count = 0

        @p.time_function("recursive")
        def recursive_func(n):
            nonlocal call_count
            call_count += 1
            if n <= 0:
                return 0
            return recursive_func(n - 1)

        recursive_func(3)
        # Should record timing data (outermost call updates stats)
        assert "recursive" in p.function_timings
        # The function was called 4 times (n=3,2,1,0) but outermost call is once
        assert p.function_timings["recursive"].calls == 1


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


class TestReport:
    """Tests for report()."""

    def test_report_when_enabled_with_data(self):
        """report() returns dict with 'timings' and 'profile' when enabled."""
        p = PerformanceProfiler(enabled=True)
        # The profiler must have been started/stopped with actual code to
        # produce valid stats for pstats.Stats
        p.start()
        _ = sum(range(100))
        p.stop()
        p._update_timing_stats("func_a", 0.1, 50.0, 50.5)
        report = p.report()
        assert "timings" in report
        assert "profile" in report
        assert "func_a" in report["timings"]
        assert report["timings"]["func_a"]["calls"] == 1

    def test_report_when_disabled(self):
        """report() returns empty dict when disabled."""
        p = PerformanceProfiler(enabled=False)
        assert p.report() == {}


# ---------------------------------------------------------------------------
# print_report
# ---------------------------------------------------------------------------


class TestPrintReport:
    """Tests for print_report()."""

    def test_print_report_when_disabled(self, capsys):
        """print_report prints 'Profiling is disabled.' when disabled."""
        p = PerformanceProfiler(enabled=False)
        p.print_report()
        output = capsys.readouterr().out
        assert "Profiling is disabled." in output

    def test_print_report_when_enabled_no_data(self, capsys):
        """print_report prints 'No timing data collected.' when no data."""
        p = PerformanceProfiler(enabled=True)
        p.print_report()
        output = capsys.readouterr().out
        assert "No timing data collected." in output

    def test_print_report_with_data(self, capsys):
        """print_report prints table with timing data."""
        p = PerformanceProfiler(enabled=True)
        p._update_timing_stats("func_x", 1.234, 100.0, 101.0)
        p.print_report()
        output = capsys.readouterr().out
        assert "Performance Report" in output
        assert "func_x" in output

    def test_print_report_detailed(self, capsys):
        """print_report(detailed=True) prints detailed profile stats."""
        p = PerformanceProfiler(enabled=True)
        p.start()
        _ = sum(range(100))
        p.stop()
        p._update_timing_stats("func_y", 0.01, 50.0, 50.1)
        p.print_report(detailed=True)
        output = capsys.readouterr().out
        assert "Performance Report" in output
        assert "Detailed Profile" in output


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions."""

    def test_get_profiler_returns_instance(self):
        """get_profiler() returns a PerformanceProfiler instance."""
        p = get_profiler()
        assert isinstance(p, PerformanceProfiler)

    def test_enable_profiling(self):
        """enable_profiling() sets enabled=True on the global profiler."""
        original = profiling_module._global_profiler
        try:
            profiling_module._global_profiler = PerformanceProfiler(enabled=False)
            enable_profiling()
            assert profiling_module._global_profiler.enabled is True
        finally:
            profiling_module._global_profiler = original

    def test_disable_profiling(self):
        """disable_profiling() sets enabled=False on the global profiler."""
        original = profiling_module._global_profiler
        try:
            profiling_module._global_profiler = PerformanceProfiler(enabled=True)
            disable_profiling()
            assert profiling_module._global_profiler.enabled is False
        finally:
            profiling_module._global_profiler = original

    def test_profile_function_returns_decorator(self):
        """profile_function() returns a decorator callable."""
        decorator = profile_function("test_func")
        assert callable(decorator)

    def test_generate_report_returns_dict(self):
        """generate_report() returns a dict (empty when profiling disabled)."""
        result = generate_report()
        assert isinstance(result, dict)

    def test_print_report_module_level(self, capsys):
        """Module-level print_report() delegates to global profiler."""
        print_report()
        output = capsys.readouterr().out
        # Global profiler is disabled by default
        assert "Profiling is disabled." in output
