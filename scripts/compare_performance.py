#!/usr/bin/env python3
"""Compare current performance results against a stored baseline.

Wall-clock time on shared CI runners is not a regression signal: with no runtime change, `apps` (system_profiler)
measured +8% and +104% best-of-3 in two runs three days apart, and the Homebrew-API benchmarks swing more. So
relative time changes are reported as warnings only. The gate fails on what runner noise cannot produce: a memory
regression beyond REGRESSION_THRESHOLD, or a benchmark whose best iteration exceeds TIME_ABSOLUTE_LIMIT (a hang or
a gross slowdown).

Exit codes:
  0 — no gated regression (or no baseline to compare against)
  1 — a memory regression, or a best-of-N time above TIME_ABSOLUTE_LIMIT
"""

import json
import sys
from pathlib import Path

REGRESSION_THRESHOLD = 0.20  # 20%; gates memory, reports time
TIME_ABSOLUTE_LIMIT = 30.0  # seconds; a best-of-N time above this fails
MEMORY_ABSOLUTE_LIMIT = 500.0  # MB
MIN_BASELINE_TIME = 0.05  # seconds; below this, relative deltas are just timing noise
MIN_BASELINE_MEMORY = 1.0  # MB; ditto for memory


def _load_json(path: Path) -> "dict | None":
    if not path.exists():
        return None
    with open(path) as f:
        data: dict = json.load(f)
        return data


def _check_absolute_limits(name: str, result: dict) -> tuple[list[str], list[str]]:
    """Return ``(failures, warnings)``; the time ceiling uses best-of-N so one slow iteration cannot trip it."""
    failures: list[str] = []
    warnings: list[str] = []
    metric = "min_time" if "min_time" in result else "avg_time"
    best = result.get(metric, 0)
    if best > TIME_ABSOLUTE_LIMIT:
        failures.append(f"  REGRESSION: {name} {metric} {best:.2f}s exceeds the {TIME_ABSOLUTE_LIMIT:.0f}s ceiling")
    if result.get("avg_memory_mb", 0) > MEMORY_ABSOLUTE_LIMIT:
        warnings.append(
            f"  WARNING: {name} avg_memory_mb {result['avg_memory_mb']:.2f}MB exceeds {MEMORY_ABSOLUTE_LIMIT}MB limit"
        )
    return failures, warnings


def _time_metric(current: dict, baseline: dict) -> str:
    """Pick the time metric to compare.

    Best-of-N (``min_time``) when both runs recorded it, because runner and network noise only ever add
    time; older result files only carry ``avg_time``.
    """
    return "min_time" if "min_time" in current and "min_time" in baseline else "avg_time"


def _check_regression(name: str, current: dict, baseline: dict) -> tuple[list[str], list[str]]:
    """Return ``(failures, warnings)`` for one benchmark compared with its baseline."""
    failures: list[str] = []
    warnings: list[str] = []
    checks = [
        (_time_metric(current, baseline), "time", MIN_BASELINE_TIME),
        ("avg_memory_mb", "memory", MIN_BASELINE_MEMORY),
    ]
    for metric, label, floor in checks:
        cur = current.get(metric, 0)
        base = baseline.get(metric, 0)
        if base < floor:
            continue
        delta = (cur - base) / base
        if delta <= REGRESSION_THRESHOLD:
            continue
        detail = (
            f"{name} {label} ({metric}) degraded {delta * 100:.1f}% "
            f"({base:.3f} → {cur:.3f}, threshold {REGRESSION_THRESHOLD * 100:.0f}%)"
        )
        if label == "time":
            warnings.append(f"  WARNING: {detail}; time is advisory (shared-runner noise)")
        else:
            failures.append(f"  REGRESSION: {detail}")
    return failures, warnings


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

        failed, warned = _check_absolute_limits(name, result)
        regressions.extend(failed)
        warnings.extend(warned)

        if name in baseline_results:
            failed, warned = _check_regression(name, result, baseline_results[name])
            regressions.extend(failed)
            warnings.extend(warned)

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
        print(
            f"\nGated metrics OK: memory within {REGRESSION_THRESHOLD * 100:.0f}% of baseline, "
            f"best times under {TIME_ABSOLUTE_LIMIT:.0f}s."
        )

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
