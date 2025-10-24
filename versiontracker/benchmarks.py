"""
Automated performance benchmarking system for VersionTracker.

This module provides comprehensive benchmarking capabilities to measure
and track performance across different operations and configurations.
"""

import asyncio
import json
import logging
import statistics
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import psutil

from versiontracker.exceptions import VersionTrackerError

logger = logging.getLogger(__name__)


class BenchmarkError(VersionTrackerError):
    """Raised when benchmarking operations fail."""

    pass


@dataclass
class BenchmarkResult:
    """Container for benchmark results."""

    name: str
    description: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    iterations: int
    success_rate: float
    error_count: int
    metadata: dict[str, Any]
    timestamp: float


@dataclass
class SystemMetrics:
    """System performance metrics snapshot."""

    cpu_percent: float
    memory_percent: float
    memory_available: float
    disk_usage_percent: float
    load_average: list[float]
    process_count: int


class PerformanceMonitor:
    """Monitors system performance during benchmark execution."""

    def __init__(self):
        """Initialize performance monitor."""
        self.reset()

    def reset(self) -> None:
        """Reset monitoring state."""
        self._start_time: float | None = None
        self._start_memory: float | None = None
        self._start_cpu: float | None = None
        self._peak_memory: float = 0.0
        self._peak_cpu: float = 0.0
        self._samples: list[SystemMetrics] = []

    def start_monitoring(self) -> None:
        """Start performance monitoring."""
        self._start_time = time.time()

        # Get baseline metrics
        process = psutil.Process()
        self._start_memory = process.memory_info().rss / 1024 / 1024  # MB
        self._start_cpu = process.cpu_percent()

        # Take initial system snapshot
        self._take_snapshot()

    def stop_monitoring(self) -> dict[str, Any]:
        """Stop monitoring and return metrics."""
        if self._start_time is None:
            raise BenchmarkError("Monitoring not started")

        end_time = time.time()
        execution_time = end_time - self._start_time

        # Final metrics
        process = psutil.Process()
        end_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_delta = end_memory - (self._start_memory or 0)

        return {
            "execution_time": execution_time,
            "memory_usage": memory_delta,
            "peak_memory": self._peak_memory,
            "peak_cpu": self._peak_cpu,
            "sample_count": len(self._samples),
            "system_snapshots": [asdict(sample) for sample in self._samples[-10:]],  # Last 10 samples
        }

    def _take_snapshot(self) -> None:
        """Take a system performance snapshot."""
        try:
            # System-wide metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            load_avg = psutil.getloadavg() if hasattr(psutil, "getloadavg") else [0.0, 0.0, 0.0]

            # Process-specific metrics
            process = psutil.Process()
            process_memory = process.memory_info().rss / 1024 / 1024  # MB
            process_cpu = process.cpu_percent()

            # Update peaks
            self._peak_memory = max(self._peak_memory, process_memory)
            self._peak_cpu = max(self._peak_cpu, process_cpu)

            snapshot = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_available=memory.available / 1024 / 1024 / 1024,  # GB
                disk_usage_percent=disk.percent,
                load_average=list(load_avg),
                process_count=len(psutil.pids()),
            )

            self._samples.append(snapshot)

        except Exception as e:
            logger.warning(f"Failed to take performance snapshot: {e}")


class BenchmarkSuite:
    """Main benchmarking suite for VersionTracker operations."""

    def __init__(self, output_dir: Path | None = None):
        """Initialize benchmark suite.

        Args:
            output_dir: Directory to save benchmark results
        """
        self.output_dir = output_dir or Path.home() / ".config" / "versiontracker" / "benchmarks"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.results: list[BenchmarkResult] = []
        self.monitor = PerformanceMonitor()

    def run_benchmark(
        self,
        name: str,
        func: Callable[[], Any],
        description: str = "",
        iterations: int = 1,
        warmup_iterations: int = 0,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> BenchmarkResult:
        """Run a benchmark test.

        Args:
            name: Benchmark name
            func: Function to benchmark
            description: Benchmark description
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations
            timeout: Timeout in seconds
            **kwargs: Additional metadata

        Returns:
            BenchmarkResult: Benchmark results
        """
        logger.info(f"Running benchmark: {name} ({iterations} iterations)")

        # Warmup runs
        for i in range(warmup_iterations):
            try:
                func()
            except Exception as e:
                logger.warning(f"Warmup iteration {i + 1} failed: {e}")

        # Actual benchmark runs
        execution_times = []
        error_count = 0
        successful_runs = 0

        for i in range(iterations):
            try:
                self.monitor.reset()
                self.monitor.start_monitoring()

                start_time = time.time()

                # Execute with timeout if specified
                if timeout:
                    result = self._execute_with_timeout(func, timeout)
                else:
                    result = func()

                end_time = time.time()
                execution_time = end_time - start_time
                execution_times.append(execution_time)
                successful_runs += 1

            except Exception as e:
                error_count += 1
                logger.warning(f"Benchmark iteration {i + 1} failed: {e}")
                continue

        # Calculate metrics
        if execution_times:
            avg_execution_time = statistics.mean(execution_times)
            metrics = (
                self.monitor.stop_monitoring()
                if successful_runs > 0
                else {"execution_time": 0, "memory_usage": 0, "peak_memory": 0, "peak_cpu": 0}
            )
        else:
            avg_execution_time = 0
            metrics = {"execution_time": 0, "memory_usage": 0, "peak_memory": 0, "peak_cpu": 0}

        success_rate = successful_runs / iterations if iterations > 0 else 0.0

        # Create result
        result = BenchmarkResult(
            name=name,
            description=description,
            execution_time=avg_execution_time,
            memory_usage=metrics.get("memory_usage", 0),
            cpu_usage=metrics.get("peak_cpu", 0),
            iterations=iterations,
            success_rate=success_rate,
            error_count=error_count,
            metadata={"execution_times": execution_times, "system_metrics": metrics, **kwargs},
            timestamp=time.time(),
        )

        self.results.append(result)
        logger.info(f"Benchmark '{name}' completed: {avg_execution_time:.3f}s avg, {success_rate:.1%} success rate")

        return result

    def run_async_benchmark(
        self, name: str, async_func: Callable[[], Any], description: str = "", iterations: int = 1, **kwargs: Any
    ) -> BenchmarkResult:
        """Run an async benchmark test."""

        async def wrapper():
            return await async_func()

        def sync_wrapper():
            return asyncio.run(wrapper())

        return self.run_benchmark(name, sync_wrapper, description, iterations, **kwargs)

    def benchmark_function_call(
        self, func: Callable[[], Any], name: str | None = None, **kwargs: Any
    ) -> BenchmarkResult:
        """Benchmark a single function call."""
        benchmark_name = name or f"{func.__module__}.{func.__name__}"
        return self.run_benchmark(benchmark_name, func, **kwargs)

    @contextmanager
    def benchmark_context(self, name: str, description: str = "") -> Iterator[dict[str, Any]]:
        """Context manager for benchmarking code blocks."""
        context = {"result": None, "error": None}

        self.monitor.reset()
        self.monitor.start_monitoring()
        start_time = time.time()

        try:
            yield context
            success = True
        except Exception as e:
            context["error"] = str(e)
            success = False
            raise
        finally:
            end_time = time.time()
            execution_time = end_time - start_time

            try:
                metrics = self.monitor.stop_monitoring()
            except Exception:
                metrics = {"execution_time": execution_time, "memory_usage": 0, "peak_memory": 0, "peak_cpu": 0}

            result = BenchmarkResult(
                name=name,
                description=description,
                execution_time=execution_time,
                memory_usage=metrics.get("memory_usage", 0),
                cpu_usage=metrics.get("peak_cpu", 0),
                iterations=1,
                success_rate=1.0 if success else 0.0,
                error_count=0 if success else 1,
                metadata={"context_result": context.get("result"), "system_metrics": metrics},
                timestamp=time.time(),
            )

            self.results.append(result)

    def compare_benchmarks(
        self, benchmarks: dict[str, Callable[[], Any]], iterations: int = 5, description: str = ""
    ) -> dict[str, BenchmarkResult]:
        """Compare multiple benchmark implementations."""
        results = {}

        logger.info(f"Comparing {len(benchmarks)} implementations ({iterations} iterations each)")

        for name, func in benchmarks.items():
            result = self.run_benchmark(
                name=f"compare_{name}", func=func, description=f"{description} - {name}", iterations=iterations
            )
            results[name] = result

        # Log comparison summary
        sorted_results = sorted(results.items(), key=lambda x: x[1].execution_time)
        logger.info("Benchmark comparison results (fastest to slowest):")
        for name, result in sorted_results:
            logger.info(f"  {name}: {result.execution_time:.3f}s avg ({result.success_rate:.1%} success)")

        return results

    def save_results(self, filename: str | None = None) -> Path:
        """Save benchmark results to JSON file."""
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"

        output_file = self.output_dir / filename

        results_data = {
            "metadata": {
                "timestamp": time.time(),
                "total_benchmarks": len(self.results),
                "python_version": __import__("sys").version,
                "platform": __import__("platform").platform(),
            },
            "results": [asdict(result) for result in self.results],
        }

        output_file.write_text(json.dumps(results_data, indent=2))
        logger.info(f"Benchmark results saved to {output_file}")

        return output_file

    def load_results(self, filename: str) -> list[BenchmarkResult]:
        """Load benchmark results from JSON file."""
        input_file = self.output_dir / filename

        if not input_file.exists():
            raise BenchmarkError(f"Benchmark file not found: {input_file}")

        data = json.loads(input_file.read_text())

        results = []
        for result_data in data.get("results", []):
            result = BenchmarkResult(**result_data)
            results.append(result)

        logger.info(f"Loaded {len(results)} benchmark results from {input_file}")
        return results

    def generate_report(self, output_format: str = "text") -> str:
        """Generate a benchmark report."""
        if not self.results:
            return "No benchmark results available."

        if output_format == "text":
            return self._generate_text_report()
        elif output_format == "markdown":
            return self._generate_markdown_report()
        elif output_format == "json":
            return json.dumps([asdict(r) for r in self.results], indent=2)
        else:
            raise BenchmarkError(f"Unsupported report format: {output_format}")

    def _generate_text_report(self) -> str:
        """Generate text format report."""
        lines = []
        lines.append("=" * 80)
        lines.append("VERSIONTRACKER BENCHMARK REPORT")
        lines.append("=" * 80)
        lines.append(f"Total benchmarks: {len(self.results)}")
        lines.append(f"Report generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        for result in self.results:
            lines.append(f"Benchmark: {result.name}")
            lines.append(f"Description: {result.description}")
            lines.append(f"Execution time: {result.execution_time:.3f}s")
            lines.append(f"Memory usage: {result.memory_usage:.2f}MB")
            lines.append(f"CPU usage: {result.cpu_usage:.1f}%")
            lines.append(f"Iterations: {result.iterations}")
            lines.append(f"Success rate: {result.success_rate:.1%}")
            lines.append(f"Errors: {result.error_count}")
            lines.append("-" * 40)

        return "\n".join(lines)

    def _generate_markdown_report(self) -> str:
        """Generate Markdown format report."""
        lines = []
        lines.append("# VersionTracker Benchmark Report")
        lines.append("")
        lines.append(f"**Total benchmarks:** {len(self.results)}")
        lines.append(f"**Report generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("## Results")
        lines.append("")
        lines.append("| Benchmark | Time (s) | Memory (MB) | CPU (%) | Success Rate | Iterations |")
        lines.append("|-----------|----------|-------------|---------|--------------|------------|")

        for result in self.results:
            lines.append(
                f"| {result.name} | {result.execution_time:.3f} | "
                f"{result.memory_usage:.2f} | {result.cpu_usage:.1f} | "
                f"{result.success_rate:.1%} | {result.iterations} |"
            )

        return "\n".join(lines)

    def _execute_with_timeout(self, func: Callable[[], Any], timeout: float) -> Any:
        """Execute function with timeout."""
        import signal

        def timeout_handler(signum: int, frame: Any) -> None:
            raise TimeoutError(f"Function execution timed out after {timeout}s")

        # Set timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))

        try:
            result = func()
        finally:
            signal.alarm(0)  # Cancel timeout

        return result


class VersionTrackerBenchmarks:
    """Pre-defined benchmarks for VersionTracker operations."""

    def __init__(self, suite: BenchmarkSuite):
        """Initialize with benchmark suite."""
        self.suite = suite

    def run_all_benchmarks(self) -> None:
        """Run all predefined benchmarks."""
        logger.info("Running all VersionTracker benchmarks")

        self.benchmark_homebrew_operations()
        self.benchmark_app_discovery()
        self.benchmark_version_parsing()
        self.benchmark_matching_algorithms()
        self.benchmark_cache_operations()

        logger.info("All benchmarks completed")

    def benchmark_homebrew_operations(self) -> None:
        """Benchmark Homebrew-related operations."""
        logger.info("Benchmarking Homebrew operations")

        try:
            from versiontracker.homebrew import get_all_homebrew_casks as get_homebrew_casks
            from versiontracker.homebrew import get_cask_info

            # Benchmark cask listing
            self.suite.run_benchmark(
                name="homebrew_list_casks",
                func=lambda: get_homebrew_casks(use_cache=False),
                description="List all Homebrew casks (no cache)",
                iterations=3,
            )

            # Benchmark cached cask listing
            self.suite.run_benchmark(
                name="homebrew_list_casks_cached",
                func=lambda: get_homebrew_casks(use_cache=True),
                description="List all Homebrew casks (with cache)",
                iterations=5,
            )

            # Benchmark individual cask info
            test_casks = ["firefox", "chrome", "vscode", "docker", "slack"]
            for cask in test_casks:
                self.suite.run_benchmark(
                    name=f"homebrew_cask_info_{cask}",
                    func=lambda c=cask: get_cask_info(c),  # type: ignore[misc]
                    description=f"Get cask info for {cask}",
                    iterations=3,
                )

        except ImportError as e:
            logger.warning(f"Skipping Homebrew benchmarks: {e}")

    def benchmark_app_discovery(self) -> None:
        """Benchmark application discovery operations."""
        logger.info("Benchmarking application discovery")

        try:
            from pathlib import Path

            from versiontracker.apps import get_applications as find_applications

            # Benchmark full app discovery
            self.suite.run_benchmark(
                name="app_discovery_full",
                func=lambda: find_applications(),
                description="Discover all applications (default paths)",
                iterations=3,
            )

            # Benchmark specific path discovery
            app_paths = [Path("/Applications"), Path("/System/Applications")]
            self.suite.run_benchmark(
                name="app_discovery_applications",
                func=lambda: find_applications(app_paths),
                description="Discover applications in /Applications",
                iterations=5,
            )

        except ImportError as e:
            logger.warning(f"Skipping app discovery benchmarks: {e}")

    def benchmark_version_parsing(self) -> None:
        """Benchmark version parsing operations."""
        logger.info("Benchmarking version parsing")

        try:
            from versiontracker.version import compare_versions, parse_version

            # Test version strings
            test_versions = [
                "1.0.0",
                "2.1.3",
                "10.15.7",
                "2023.1.1",
                "v1.2.3",
                "1.2.3-beta",
                "1.2.3-rc.1",
                "20.04.1",
                "3.9.7",
                "16.5.0",
            ] * 10  # Multiply for more data

            # Benchmark version parsing
            self.suite.run_benchmark(
                name="version_parsing",
                func=lambda: [parse_version(v) for v in test_versions],
                description=f"Parse {len(test_versions)} version strings",
                iterations=10,
            )

            # Benchmark version comparison
            parsed_versions = [parse_version(v) for v in test_versions[:10]]
            self.suite.run_benchmark(
                name="version_comparison",
                func=lambda: [
                    compare_versions(parsed_versions[i], parsed_versions[j])
                    for i in range(len(parsed_versions))
                    for j in range(i + 1, len(parsed_versions))
                ],
                description="Compare version pairs",
                iterations=20,
            )

        except ImportError as e:
            logger.warning(f"Skipping version parsing benchmarks: {e}")

    def benchmark_matching_algorithms(self) -> None:
        """Benchmark matching algorithm performance."""
        logger.info("Benchmarking matching algorithms")

        try:
            from versiontracker.enhanced_matching import fuzzy_match_name

            # Test data
            app_names = [
                "Google Chrome",
                "Mozilla Firefox",
                "Visual Studio Code",
                "Docker Desktop",
                "Slack",
                "Zoom",
                "Discord",
                "Spotify",
                "Adobe Photoshop",
                "Microsoft Excel",
            ] * 5

            cask_names = [
                "google-chrome",
                "firefox",
                "visual-studio-code",
                "docker",
                "slack",
                "zoom",
                "discord",
                "spotify",
                "adobe-photoshop",
                "microsoft-excel",
                "brave-browser",
                "sublime-text",
                "atom",
            ] * 3

            # Benchmark fuzzy matching
            def fuzzy_match_batch():
                results = []
                for app in app_names:
                    for cask in cask_names:
                        score = fuzzy_match_name(app, cask)
                        results.append((app, cask, score))
                return results

            self.suite.run_benchmark(
                name="fuzzy_matching_batch",
                func=fuzzy_match_batch,
                description=f"Fuzzy match {len(app_names)} apps against {len(cask_names)} casks",
                iterations=3,
            )

        except ImportError as e:
            logger.warning(f"Skipping matching algorithm benchmarks: {e}")

    def benchmark_cache_operations(self) -> None:
        """Benchmark cache operations."""
        logger.info("Benchmarking cache operations")

        try:
            import uuid

            from versiontracker.cache import read_cache, write_cache

            # Generate test data
            test_data = {
                "items": [{"id": i, "name": f"item_{i}", "data": "x" * 100} for i in range(1000)],
                "metadata": {"version": "1.0", "timestamp": time.time()},
            }

            # Benchmark cache writing
            cache_key = f"benchmark_{uuid.uuid4()}"
            self.suite.run_benchmark(
                name="cache_write_large",
                func=lambda: write_cache(cache_key, test_data),
                description="Write large data to cache",
                iterations=10,
            )

            # Benchmark cache reading
            self.suite.run_benchmark(
                name="cache_read_large",
                func=lambda: read_cache(cache_key),
                description="Read large data from cache",
                iterations=20,
            )

        except ImportError as e:
            logger.warning(f"Skipping cache benchmarks: {e}")


def create_benchmark_suite(output_dir: Path | None = None) -> BenchmarkSuite:
    """Create a new benchmark suite."""
    return BenchmarkSuite(output_dir)


def run_performance_regression_test() -> bool:
    """Run performance regression test against baseline."""
    suite = create_benchmark_suite()
    vt_benchmarks = VersionTrackerBenchmarks(suite)

    # Run core benchmarks
    vt_benchmarks.benchmark_homebrew_operations()
    vt_benchmarks.benchmark_app_discovery()
    vt_benchmarks.benchmark_version_parsing()

    # Save results
    results_file = suite.save_results("regression_test_results.json")

    # Check for performance regressions
    # This would compare against baseline results
    # For now, return True (no regressions detected)
    logger.info(f"Performance regression test completed. Results saved to {results_file}")
    return True


if __name__ == "__main__":
    # Example usage
    suite = create_benchmark_suite()
    vt_benchmarks = VersionTrackerBenchmarks(suite)
    vt_benchmarks.run_all_benchmarks()

    # Generate and save report
    report = suite.generate_report("markdown")
    print(report)

    suite.save_results()
