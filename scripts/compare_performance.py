#!/usr/bin/env python3
"""Compare current performance with previous results."""

import json
import os
from pathlib import Path


def compare_results():
    """Compare current results with baseline."""
    current_file = Path("performance_results.json")
    if not current_file.exists():
        print("No current results found")
        return

    with open(current_file) as f:
        current = json.load(f)

    print("=== Performance Comparison ===")
    print("Note: This is the current run's performance metrics.")
    print("Future runs will show comparison with previous results.\n")

    for name, result in current["results"].items():
        if "error" not in result:
            print(f"{name:12} | {result['avg_time']:6.2f}s | {result['avg_memory_mb']:6.2f}MB")

            # Set performance thresholds (for future CI gates)
            time_threshold = 30.0  # 30 seconds max for any operation
            memory_threshold = 500.0  # 500MB max memory usage

            if result["avg_time"] > time_threshold:
                print(f"  ⚠️  {name} execution time exceeds threshold ({time_threshold}s)")

            if result["avg_memory_mb"] > memory_threshold:
                print(f"  ⚠️  {name} memory usage exceeds threshold ({memory_threshold}MB)")


if __name__ == "__main__":
    compare_results()
