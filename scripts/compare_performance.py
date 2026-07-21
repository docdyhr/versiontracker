#!/usr/bin/env python3
"""Compare current performance results against a stored baseline.

Exit codes:
  0 — no regression detected (or no baseline to compare against)
  1 — one or more metrics degraded by more than REGRESSION_THRESHOLD
"""

import json
import sys
from pathlib import Path

REGRESSION_THRESHOLD = 0.20  # 20%; benchmarks hit live Homebrew API calls, which vary run to run
TIME_ABSOLUTE_LIMIT = 30.0  # seconds
MEMORY_ABSOLUTE_LIMIT = 500.0  # MB
MIN_BASELINE_TIME = 0.05  # seconds; below this, relative deltas are just timing noise
MIN_BASELINE_MEMORY = 1.0  # MB; ditto for memory


def _load_json(path: Path) -> "dict | None":
    if not path.exists():
        return None
    with open(path) as f:
        data: dict = json.load(f)
        return data


def _check_absolute_limits(name: str, result: dict) -> list[str]:
    warnings = []
    if result.get("avg_time", 0) > TIME_ABSOLUTE_LIMIT:
        warnings.append(f"  WARNING: {name} avg_time {result['avg_time']:.2f}s exceeds {TIME_ABSOLUTE_LIMIT}s limit")
    if result.get("avg_memory_mb", 0) > MEMORY_ABSOLUTE_LIMIT:
        warnings.append(
            f"  WARNING: {name} avg_memory_mb {result['avg_memory_mb']:.2f}MB exceeds {MEMORY_ABSOLUTE_LIMIT}MB limit"
        )
    return warnings


def _check_regression(name: str, current: dict, baseline: dict) -> list[str]:
    failures = []
    min_baseline = {"avg_time": MIN_BASELINE_TIME, "avg_memory_mb": MIN_BASELINE_MEMORY}
    for metric, label in [("avg_time", "time"), ("avg_memory_mb", "memory")]:
        cur = current.get(metric, 0)
        base = baseline.get(metric, 0)
        if base < min_baseline[metric]:
            continue
        delta = (cur - base) / base
        if delta > REGRESSION_THRESHOLD:
            failures.append(
                f"  REGRESSION: {name} {label} degraded {delta * 100:.1f}% "
                f"({base:.3f} → {cur:.3f}, threshold {REGRESSION_THRESHOLD * 100:.0f}%)"
            )
    return failures


def compare_results(baseline_path: Path) -> int:
    """Return 0 on success, 1 if regressions found."""
    current_file = Path("performance_results.json")
    current_data = _load_json(current_file)
    if current_data is None:
        print("No current results found (performance_results.json missing); skipping comparison.")
        return 0

    print("=== Performance Results ===")
    print(f"{'Benchmark':<20} {'Time (s)':>10} {'Memory (MB)':>12}")
    print("-" * 44)

    regressions: list[str] = []
    warnings: list[str] = []

    baseline_data = _load_json(baseline_path)
    baseline_results: dict = baseline_data.get("results", {}) if baseline_data else {}

    for name, result in current_data["results"].items():
        if "error" in result:
            print(f"  {name}: ERROR — {result['error']}")
            continue

        avg_time = result.get("avg_time", 0)
        avg_mem = result.get("avg_memory_mb", 0)
        print(f"{name:<20} {avg_time:>10.3f} {avg_mem:>12.1f}")

        warnings.extend(_check_absolute_limits(name, result))

        if name in baseline_results:
            regressions.extend(_check_regression(name, result, baseline_results[name]))

    if baseline_data is None:
        print("\nNo baseline found — this run will become the baseline for future comparisons.")
    else:
        print(f"\nBaseline: {baseline_path}")

    if warnings:
        print()
        for w in warnings:
            print(w)

    if regressions:
        print("\n=== REGRESSION FAILURES ===")
        for r in regressions:
            print(r)
        return 1

    if baseline_data is not None:
        print(f"\nAll metrics within {REGRESSION_THRESHOLD * 100:.0f}% regression threshold.")

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("performance_baseline.json"),
        help="Path to baseline results file (default: performance_baseline.json)",
    )
    args = parser.parse_args()
    sys.exit(compare_results(args.baseline))
