#!/usr/bin/env python3
"""Performance regression testing script."""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

from versiontracker.__main__ import versiontracker_main as cli_main
from versiontracker.profiling import disable_profiling, enable_profiling, generate_report, get_profiler


def run_benchmark(command: str, iterations: int = 3) -> Dict[str, Any]:
    """Run a benchmark for a specific command."""
    print(f"Benchmarking: {command}")

    times = []
    memory_peaks = []

    for i in range(iterations):
        print(f"  Iteration {i + 1}/{iterations}")

        # Reset profiler
        profiler = get_profiler()
        profiler.function_timings.clear()

        # Enable profiling
        enable_profiling()

        start_time = time.time()

        # Mock sys.argv for the command
        original_argv = sys.argv
        sys.argv = ["versiontracker"] + command.split()

        try:
            # Run the command with profiling
            cli_main()
        except SystemExit:
            pass  # Expected for help/version commands
        except Exception as e:
            print(f"    Error: {e}")
            continue
        finally:
            sys.argv = original_argv

        end_time = time.time()

        # Stop profiling and get results
        disable_profiling()
        report = generate_report()

        execution_time = end_time - start_time
        times.append(execution_time)

        # Extract memory usage from profiling data
        max_memory = 0
        if "timings" in report:
            for func_data in report["timings"].values():
                if "memory_diff_mb" in func_data:
                    max_memory = max(max_memory, func_data["memory_diff_mb"])
        memory_peaks.append(max_memory)

    if not times:
        return {"error": "No successful runs"}

    return {
        "command": command,
        "iterations": len(times),
        "avg_time": sum(times) / len(times),
        "min_time": min(times),
        "max_time": max(times),
        "avg_memory_mb": sum(memory_peaks) / len(memory_peaks) if memory_peaks else 0,
        "max_memory_mb": max(memory_peaks) if memory_peaks else 0,
    }


def main():
    """Main performance testing function."""
    target = os.environ.get("BENCHMARK_TARGET", "all")

    # Define commands to benchmark
    commands = {
        "apps": "--apps --no-progress",
        "brews": "--brews --no-progress",
        "recommend": "--recommend --no-progress",
        "outdated": "--outdated --no-progress",
    }

    if target != "all":
        commands = {target: commands.get(target, "--help")}

    results = {}

    for name, command in commands.items():
        print(f"\n=== Benchmarking {name} ===")
        result = run_benchmark(command)
        results[name] = result

        if "error" not in result:
            print(f"  Average time: {result['avg_time']:.2f}s")
            print(f"  Memory usage: {result['avg_memory_mb']:.2f}MB")

    # Save results
    results_file = Path("performance_results.json")
    with open(results_file, "w") as f:
        json.dump({"timestamp": time.time(), "python_version": sys.version, "results": results}, f, indent=2)

    print(f"\nResults saved to {results_file}")

    # Print summary
    print("\n=== Performance Summary ===")
    for name, result in results.items():
        if "error" not in result:
            print(f"{name:12} | {result['avg_time']:6.2f}s | {result['avg_memory_mb']:6.2f}MB")


if __name__ == "__main__":
    main()
