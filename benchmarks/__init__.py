"""Performance benchmarking framework for VersionTracker.

This module provides utilities for measuring and tracking performance metrics
across different components of the VersionTracker application.
"""

import statistics
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import psutil


@dataclass
class BenchmarkResult:
    """Container for benchmark measurement results."""

    name: str
    duration: float  # seconds
    memory_peak: int  # bytes
    memory_start: int  # bytes
    memory_end: int  # bytes
    cpu_percent_avg: float
    iterations: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def memory_delta(self) -> int:
        """Memory difference from start to end."""
        return self.memory_end - self.memory_start

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        return self.duration * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "duration_s": self.duration,
            "memory_peak_mb": self.memory_peak / (1024 * 1024),
            "memory_delta_mb": self.memory_delta / (1024 * 1024),
            "cpu_percent_avg": self.cpu_percent_avg,
            "iterations": self.iterations,
            "metadata": self.metadata,
        }


class PerformanceMonitor:
    """Monitor system resources during benchmark execution."""

    def __init__(self, interval: float = 0.1):
        """Initialize performance monitor with sampling interval."""
        self.interval = interval
        self.monitoring = False
        self.memory_samples: List[int] = []
        self.cpu_samples: List[float] = []
        self._thread: Optional[threading.Thread] = None
        self.process = psutil.Process()

    def start(self) -> None:
        """Start monitoring system resources."""
        if self.monitoring:
            return

        self.monitoring = True
        self.memory_samples = []
        self.cpu_samples = []
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> Dict[str, Any]:
        """Stop monitoring and return collected metrics."""
        self.monitoring = False
        if self._thread:
            self._thread.join(timeout=1.0)

        return {
            "memory_peak": max(self.memory_samples) if self.memory_samples else 0,
            "memory_avg": statistics.mean(self.memory_samples) if self.memory_samples else 0,
            "cpu_avg": statistics.mean(self.cpu_samples) if self.cpu_samples else 0,
            "samples_count": len(self.memory_samples),
        }

    def _monitor_loop(self) -> None:
        """Internal monitoring loop."""
        while self.monitoring:
            try:
                memory_info = self.process.memory_info()
                self.memory_samples.append(memory_info.rss)

                # CPU percent over interval
                cpu_percent = self.process.cpu_percent()
                if cpu_percent > 0:  # Skip first measurement (usually 0)
                    self.cpu_samples.append(cpu_percent)

                time.sleep(self.interval)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break


@contextmanager
def benchmark_context(name: str, metadata: Optional[Dict[str, Any]] = None):
    """Context manager for benchmarking code blocks."""
    monitor = PerformanceMonitor()
    process = psutil.Process()

    # Initial measurements
    start_memory = process.memory_info().rss
    start_time = time.perf_counter()

    monitor.start()

    try:
        yield
    finally:
        # Final measurements
        end_time = time.perf_counter()
        end_memory = process.memory_info().rss

        metrics = monitor.stop()

        result = BenchmarkResult(
            name=name,
            duration=end_time - start_time,
            memory_start=start_memory,
            memory_end=end_memory,
            memory_peak=metrics["memory_peak"],
            cpu_percent_avg=metrics["cpu_avg"],
            metadata=metadata or {},
        )

        BenchmarkCollector.instance().add_result(result)


def benchmark(name: Optional[str] = None, iterations: int = 1):
    """Decorator for benchmarking functions."""

    def decorator(func: Callable) -> Callable:
        benchmark_name = name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            if iterations == 1:
                with benchmark_context(benchmark_name):
                    return func(*args, **kwargs)
            else:
                # Multiple iterations
                results = []
                for i in range(iterations):
                    with benchmark_context(f"{benchmark_name}_iter_{i}"):
                        result = func(*args, **kwargs)
                        results.append(result)

                # Create summary result
                collector = BenchmarkCollector.instance()
                iter_results = [r for r in collector.results if r.name.startswith(benchmark_name)]

                if iter_results:
                    avg_duration = statistics.mean(r.duration for r in iter_results)
                    avg_memory_peak = statistics.mean(r.memory_peak for r in iter_results)
                    avg_cpu = statistics.mean(r.cpu_percent_avg for r in iter_results)

                    summary = BenchmarkResult(
                        name=f"{benchmark_name}_summary",
                        duration=avg_duration,
                        memory_peak=int(avg_memory_peak),
                        memory_start=iter_results[0].memory_start,
                        memory_end=iter_results[-1].memory_end,
                        cpu_percent_avg=avg_cpu,
                        iterations=iterations,
                        metadata={
                            "type": "summary",
                            "min_duration": min(r.duration for r in iter_results),
                            "max_duration": max(r.duration for r in iter_results),
                            "std_duration": statistics.stdev(r.duration for r in iter_results)
                            if len(iter_results) > 1
                            else 0,
                        },
                    )
                    collector.add_result(summary)

                return results[-1] if results else None

        return wrapper

    return decorator


class BenchmarkCollector:
    """Singleton collector for benchmark results."""

    _instance = None

    def __init__(self):
        """Initialize benchmark result collector."""
        self.results: List[BenchmarkResult] = []

    @classmethod
    def instance(cls) -> "BenchmarkCollector":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_result(self, result: BenchmarkResult) -> None:
        """Add a benchmark result."""
        self.results.append(result)

    def get_results(self, name_filter: Optional[str] = None) -> List[BenchmarkResult]:
        """Get results, optionally filtered by name."""
        if name_filter:
            return [r for r in self.results if name_filter in r.name]
        return self.results.copy()

    def clear(self) -> None:
        """Clear all collected results."""
        self.results.clear()

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of all benchmarks."""
        if not self.results:
            return {}

        durations = [r.duration for r in self.results]
        memory_peaks = [r.memory_peak for r in self.results]
        cpu_avgs = [r.cpu_percent_avg for r in self.results]

        return {
            "total_benchmarks": len(self.results),
            "total_duration": sum(durations),
            "avg_duration": statistics.mean(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "avg_memory_peak_mb": statistics.mean(memory_peaks) / (1024 * 1024),
            "max_memory_peak_mb": max(memory_peaks) / (1024 * 1024),
            "avg_cpu_percent": statistics.mean(cpu_avgs),
            "max_cpu_percent": max(cpu_avgs),
        }

    def print_summary(self) -> None:
        """Print formatted summary of all benchmarks."""
        summary = self.get_summary()

        if not summary:
            print("No benchmark results collected.")
            return

        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)
        print(f"Total Benchmarks: {summary['total_benchmarks']}")
        print(f"Total Duration: {summary['total_duration']:.3f}s")
        print(f"Average Duration: {summary['avg_duration'] * 1000:.2f}ms")
        print(f"Duration Range: {summary['min_duration'] * 1000:.2f}ms - {summary['max_duration'] * 1000:.2f}ms")
        print(f"Average Memory Peak: {summary['avg_memory_peak_mb']:.2f}MB")
        print(f"Max Memory Peak: {summary['max_memory_peak_mb']:.2f}MB")
        print(f"Average CPU Usage: {summary['avg_cpu_percent']:.1f}%")
        print(f"Max CPU Usage: {summary['max_cpu_percent']:.1f}%")
        print("=" * 60)

        # Individual results
        print("\nINDIVIDUAL RESULTS:")
        print("-" * 60)
        for result in self.results:
            memory_mb = result.memory_peak / (1024 * 1024)
            print(f"{result.name:<40} {result.duration_ms:>8.2f}ms {memory_mb:>8.2f}MB {result.cpu_percent_avg:>6.1f}%")
        print("-" * 60)


# Convenience functions
def clear_benchmarks() -> None:
    """Clear all collected benchmark results."""
    BenchmarkCollector.instance().clear()


def get_benchmark_results() -> List[BenchmarkResult]:
    """Get all collected benchmark results."""
    return BenchmarkCollector.instance().get_results()


def print_benchmark_summary() -> None:
    """Print summary of all benchmark results."""
    BenchmarkCollector.instance().print_summary()
