"""Performance profiling tools for VersionTracker.

This module provides tools for profiling and measuring the performance of
VersionTracker operations, including function timing, memory usage tracking,
and detailed performance reporting.
"""

import cProfile
import functools
import io
import logging
import pstats
import time
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Callable, Dict, Optional, Set, TypeVar

try:
    import psutil

    HAS_PSUTIL = True
    psutil_module: Optional[ModuleType] = psutil
except ImportError:
    HAS_PSUTIL = False
    psutil_module = None

# Type variable for generic function decorator
T = TypeVar("T")


@dataclass
class FunctionTimingInfo:
    """Information about a function's execution time and resource usage."""

    name: str
    calls: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    avg_time: float = 0.0
    memory_before: float = 0.0
    memory_after: float = 0.0
    memory_diff: float = 0.0


class PerformanceProfiler:
    """Performance profiling tools for VersionTracker."""

    def __init__(self, enabled: bool = False):
        """Initialize the profiler.

        Args:
            enabled: Whether profiling is enabled
        """
        self.enabled = enabled
        self.profiler = None if not enabled else cProfile.Profile()
        self.function_timings: Dict[str, FunctionTimingInfo] = {}
        self._active_functions: Set[str] = set()
        self._nested_calls: Dict[str, int] = {}

    def start(self) -> None:
        """Start profiling."""
        if self.enabled and self.profiler:
            self.profiler.enable()

    def stop(self) -> None:
        """Stop profiling."""
        if self.enabled and self.profiler:
            self.profiler.disable()

    def get_stats(self) -> Optional[str]:
        """Get profiling statistics as a string.

        Returns:
            str: Formatted profiling statistics or None if profiling is disabled
        """
        if not self.enabled or not self.profiler:
            return None

        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s).sort_stats("cumulative")
        ps.print_stats(20)  # Top 20 functions by cumulative time
        return s.getvalue()

    def time_function(self, func_name: Optional[str] = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Create a timing decorator for a function.

        Args:
            func_name: The name to use for this function in timing reports.
                      If None, the function's __qualname__ will be used.

        Returns:
            Callable: A decorator function
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            if not self.enabled:
                return func

            name = func_name or func.__qualname__

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                if not self.enabled:
                    return func(*args, **kwargs)

                # Track nested calls to avoid double-counting
                is_outermost_call = False
                if name not in self._active_functions:
                    is_outermost_call = True
                    self._active_functions.add(name)
                else:
                    self._nested_calls[name] = self._nested_calls.get(name, 0) + 1

                # Only measure memory for outermost calls to avoid skewed measurements
                if is_outermost_call and HAS_PSUTIL and psutil_module is not None:
                    process = psutil_module.Process()
                    memory_before = process.memory_info().rss / 1024 / 1024  # MB
                else:
                    memory_before = 0

                # Time the function
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()

                    # Only record stats for outermost calls
                    if is_outermost_call:
                        elapsed = end_time - start_time

                        # Get final memory usage
                        if HAS_PSUTIL and psutil_module is not None:
                            process = psutil_module.Process()
                            memory_after = process.memory_info().rss / 1024 / 1024  # MB
                            memory_diff = memory_after - memory_before
                        else:
                            memory_after = 0
                            memory_diff = 0

                        # Update timing info
                        if name not in self.function_timings:
                            self.function_timings[name] = FunctionTimingInfo(name=name)

                        timing = self.function_timings[name]
                        timing.calls += 1
                        timing.total_time += elapsed
                        timing.min_time = min(timing.min_time, elapsed)
                        timing.max_time = max(timing.max_time, elapsed)
                        timing.avg_time = timing.total_time / timing.calls
                        timing.memory_before = memory_before
                        timing.memory_after = memory_after
                        timing.memory_diff = memory_diff

                        logging.debug(
                            "Performance: %s took %.4fs, used %.2fMB memory",
                            name,
                            elapsed,
                            memory_diff,
                        )

                        # Remove from active functions
                        self._active_functions.remove(name)
                    else:
                        # Decrement nested call counter
                        self._nested_calls[name] = self._nested_calls.get(name, 1) - 1
                        if self._nested_calls[name] == 0:
                            del self._nested_calls[name]

            return wrapper

        return decorator

    def report(self) -> Dict[str, Any]:
        """Generate a performance report.

        Returns:
            Dict[str, Any]: Performance report data
        """
        if not self.enabled:
            return {}

        timings = {
            name: {
                "calls": info.calls,
                "total_time": info.total_time,
                "min_time": info.min_time,
                "max_time": info.max_time,
                "avg_time": info.avg_time,
                "memory_diff_mb": info.memory_diff,
            }
            for name, info in self.function_timings.items()
        }

        return {
            "timings": timings,
            "profile": self.get_stats(),
        }

    def print_report(self, detailed: bool = False) -> None:
        """Print a performance report to the console.

        Args:
            detailed: Whether to include the detailed profiling information
        """
        if not self.enabled:
            print("Profiling is disabled.")
            return

        if not self.function_timings:
            print("No timing data collected.")
            return

        # Sort functions by total time (descending)
        sorted_timings = sorted(self.function_timings.values(), key=lambda x: x.total_time, reverse=True)

        print("\n=== Performance Report ===")
        print(f"{'Function':<40} {'Calls':<8} {'Total(s)':<10} {'Avg(s)':<10} {'Memory(MB)':<10}")
        print("-" * 80)

        for timing in sorted_timings:
            print(
                f"{timing.name:<40} {timing.calls:<8} {timing.total_time:<10.4f} "
                f"{timing.avg_time:<10.4f} {timing.memory_diff:<10.2f}"
            )

        if detailed and self.profiler:
            print("\n=== Detailed Profile ===")
            print(self.get_stats())


# Global profiler instance
_global_profiler = PerformanceProfiler(enabled=False)


def get_profiler() -> PerformanceProfiler:
    """Get the global profiler instance.

    Returns:
        PerformanceProfiler: The global profiler instance
    """
    return _global_profiler


def enable_profiling() -> None:
    """Enable profiling."""
    global _global_profiler
    _global_profiler.enabled = True
    _global_profiler.start()


def disable_profiling() -> None:
    """Disable profiling."""
    global _global_profiler
    _global_profiler.stop()
    _global_profiler.enabled = False


def profile_function(
    func_name: Optional[str] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Create a profiling decorator for a function.

    Args:
        func_name: Optional name for the function in profile reports

    Returns:
        Callable: Decorator function
    """
    return _global_profiler.time_function(func_name)


def generate_report() -> Dict[str, Any]:
    """Generate a performance report.

    Returns:
        Dict[str, Any]: Performance report data
    """
    return _global_profiler.report()


def print_report(detailed: bool = False) -> None:
    """Print a performance report.

    Args:
        detailed: Whether to include detailed profiling information
    """
    _global_profiler.print_report(detailed)
