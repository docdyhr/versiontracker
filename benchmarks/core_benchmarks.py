#!/usr/bin/env python3
"""Core benchmarks for VersionTracker performance testing.

This script benchmarks the most important operations in VersionTracker
to establish baseline performance metrics and identify optimization opportunities.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add the parent directory to the path to import VersionTracker modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks import benchmark, benchmark_context, clear_benchmarks, print_benchmark_summary
from versiontracker.app_finder import (
    check_brew_install_candidates,
    get_applications,
    get_homebrew_casks_list,
    is_brew_cask_installable,
)
from versiontracker.config import get_config
from versiontracker.utils import run_command
from versiontracker.version import compare_versions, parse_version

# Mock data for consistent benchmarking
MOCK_APP_DATA = [
    ("Firefox", "120.0.1"),
    ("Google Chrome", "119.0.6045.199"),
    ("Visual Studio Code", "1.84.2"),
    ("Slack", "4.35.126"),
    ("Docker Desktop", "4.25.2"),
    ("Spotify", "1.2.26.1187"),
    ("Discord", "0.0.295"),
    ("Zoom", "5.16.10"),
    ("Notion", "3.1.0"),
    ("1Password 7 - Password Manager", "7.9.10"),
]

MOCK_SYSTEM_PROFILER_DATA = {
    "SPApplicationsDataType": [
        {
            "_name": "Firefox",
            "path": "/Applications/Firefox.app",
            "version": "120.0.1",
            "obtained_from": "identified_developer",
        },
        {
            "_name": "Google Chrome",
            "path": "/Applications/Google Chrome.app",
            "version": "119.0.6045.199",
            "obtained_from": "identified_developer",
        },
        {
            "_name": "Safari",
            "path": "/Applications/Safari.app",
            "version": "17.1",
            "obtained_from": "apple",
        },
        {
            "_name": "Visual Studio Code",
            "path": "/Applications/Visual Studio Code.app",
            "version": "1.84.2",
            "obtained_from": "identified_developer",
        },
        {
            "_name": "TestApp1",
            "path": "/Applications/TestApp1.app",
            "version": "1.0.0",
            "obtained_from": "identified_developer",
        },
    ]
}

VERSION_COMPARISON_PAIRS = [
    ("1.0.0", "1.0.1"),
    ("2.1.0", "2.0.9"),
    ("1.0.0-beta", "1.0.0"),
    ("3.2.1", "3.2.1"),
    ("10.0.0", "9.9.9"),
    ("1.0.0-alpha.1", "1.0.0-alpha.2"),
    ("2.0.0-rc.1", "2.0.0"),
    ("1.2.3+build.1", "1.2.3+build.2"),
    ("119.0.6045.199", "120.0.1"),
    ("7.9.10", "8.0.0"),
]


@benchmark("app_discovery_mock", iterations=5)
def benchmark_app_discovery():
    """Benchmark application discovery using mock data."""
    # Use mock data to ensure consistent benchmarking
    apps = get_applications(MOCK_SYSTEM_PROFILER_DATA)
    return len(apps)


@benchmark("version_comparisons", iterations=10)
def benchmark_version_comparisons():
    """Benchmark version comparison operations."""
    results = []
    for v1, v2 in VERSION_COMPARISON_PAIRS:
        result = compare_versions(v1, v2)
        results.append(result)
    return results


@benchmark("version_parsing", iterations=10)
def benchmark_version_parsing():
    """Benchmark version string parsing."""
    versions = [pair[0] for pair in VERSION_COMPARISON_PAIRS] + [pair[1] for pair in VERSION_COMPARISON_PAIRS]
    results = []
    for version in versions:
        try:
            parsed = parse_version(version)
            results.append(parsed)
        except Exception:
            results.append(None)
    return results


@benchmark("config_loading", iterations=5)
def benchmark_config_loading():
    """Benchmark configuration loading."""
    config = get_config()
    return config


@benchmark("homebrew_cask_check_single", iterations=3)
def benchmark_single_cask_check():
    """Benchmark single Homebrew cask installability check."""
    # This will use real Homebrew if available, or handle gracefully if not
    try:
        result = is_brew_cask_installable("firefox", use_cache=False)
        return result
    except Exception as e:
        return f"Error: {e}"


@benchmark("brew_batch_processing", iterations=2)
def benchmark_brew_batch_processing():
    """Benchmark batch processing of Homebrew install candidates."""
    # Use a subset of mock data for batch processing
    batch_data = MOCK_APP_DATA[:5]  # First 5 apps
    try:
        results = check_brew_install_candidates(batch_data, rate_limit=2, use_cache=False)
        return len(results)
    except Exception as e:
        return f"Error: {e}"


@benchmark("large_app_collection", iterations=1)
def benchmark_large_app_collection():
    """Benchmark handling of large application collections."""
    # Create a larger dataset for stress testing
    large_dataset = MOCK_APP_DATA * 10  # 100 apps

    with benchmark_context("large_app_processing"):
        # Simulate processing large number of apps
        results = []
        for name, version in large_dataset:
            # Simulate some processing per app
            processed = {
                "name": name,
                "version": version,
                "comparison": compare_versions(version, "1.0.0"),
                "parsed": parse_version(version) if version else None,
            }
            results.append(processed)

    return len(results)


def run_memory_stress_test():
    """Run a memory stress test with varying data sizes."""
    print("\nRunning memory stress test...")

    sizes = [10, 50, 100, 200]
    for size in sizes:
        dataset = MOCK_APP_DATA * (size // len(MOCK_APP_DATA))

        with benchmark_context(f"memory_stress_{size}_apps", {"app_count": size}):
            # Process the dataset
            results = []
            for name, version in dataset:
                result = {
                    "name": name,
                    "version": version,
                    "parsed": parse_version(version) if version else None,
                }
                results.append(result)

        print(f"  Processed {size} apps")


def save_benchmark_results(filename: str = "benchmark_results.json"):
    """Save benchmark results to a JSON file."""
    from benchmarks import get_benchmark_results

    results = get_benchmark_results()
    data = {
        "timestamp": time.time(),
        "results": [result.to_dict() for result in results],
        "summary": {
            "total_benchmarks": len(results),
            "total_duration": sum(r.duration for r in results),
        },
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nBenchmark results saved to {filename}")


def main():
    """Run all core benchmarks."""
    print("Starting VersionTracker Core Benchmarks")
    print("=" * 50)

    # Clear any previous results
    clear_benchmarks()

    print("\n1. Application Discovery Benchmark...")
    benchmark_app_discovery()

    print("2. Version Comparison Benchmark...")
    benchmark_version_comparisons()

    print("3. Version Parsing Benchmark...")
    benchmark_version_parsing()

    print("4. Configuration Loading Benchmark...")
    benchmark_config_loading()

    print("5. Single Cask Check Benchmark...")
    benchmark_single_cask_check()

    print("6. Batch Processing Benchmark...")
    benchmark_brew_batch_processing()

    print("7. Large Collection Benchmark...")
    benchmark_large_app_collection()

    # Memory stress test
    run_memory_stress_test()

    # Print summary
    print_benchmark_summary()

    # Save results
    save_benchmark_results()

    print("\nBenchmarking complete!")


if __name__ == "__main__":
    main()
