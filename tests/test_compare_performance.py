"""Tests for scripts/compare_performance.py, the scheduled performance regression gate."""

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "compare_performance.py"
_spec = importlib.util.spec_from_file_location("compare_performance", _SCRIPT)
assert _spec is not None and _spec.loader is not None
compare_performance = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compare_performance)

# Scheduled run 38182609131 (2026-10-11), the cached baseline both real runs below were compared with.
BASELINE_2026_10_11 = {
    "apps": {"avg_time": 2.154, "min_time": 1.650, "avg_memory_mb": 50.0},
    "brews": {"avg_time": 0.002, "min_time": 0.002, "avg_memory_mb": 50.0},
    "recommend": {"avg_time": 6.121, "min_time": 5.032, "avg_memory_mb": 50.0},
    "outdated": {"avg_time": 7.198, "min_time": 6.308, "avg_memory_mb": 50.0},
}


def _bench(avg: float, best: float | None = None, memory: float = 50.0) -> dict:
    result = {"avg_time": avg, "avg_memory_mb": memory, "iterations": 3}
    if best is not None:
        result["min_time"] = best
    return result


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, baseline: dict, current: dict) -> int:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "performance_results.json").write_text(json.dumps({"results": current}))
    baseline_path = tmp_path / "performance_baseline.json"
    baseline_path.write_text(json.dumps({"results": baseline}))
    return compare_performance.compare_results(baseline_path)


@pytest.mark.parametrize(
    "current",
    [
        # run 39174628747 attempt 2 (2026-10-18): failed apps/recommend/outdated under the old mean-based gate
        {"apps": _bench(2.804, 1.788), "recommend": _bench(7.589, 6.344), "outdated": _bench(13.660, 10.157)},
        # run 39243572918 (2026-10-19): apps best-of-3 +104% with no runtime change
        {"apps": _bench(3.9, 3.362), "recommend": _bench(7.2, 6.445), "outdated": _bench(15.0, 13.852)},
    ],
    ids=["2026-10-18", "2026-10-19"],
)
def test_replayed_noisy_runs_pass_with_time_warnings(tmp_path, monkeypatch, capsys, current):
    code = _run(tmp_path, monkeypatch, BASELINE_2026_10_11, current)

    out = capsys.readouterr().out
    assert code == 0
    assert "REGRESSION" not in out
    assert "time is advisory (shared-runner noise)" in out


def test_time_regression_on_any_benchmark_only_warns(tmp_path, monkeypatch, capsys):
    code = _run(tmp_path, monkeypatch, {"apps": _bench(2.0, 1.650)}, {"apps": _bench(6.0, 5.0)})

    out = capsys.readouterr().out
    assert code == 0
    assert "WARNING: apps time (min_time) degraded" in out


def test_memory_regression_fails(tmp_path, monkeypatch, capsys):
    code = _run(tmp_path, monkeypatch, {"apps": _bench(2.0, 1.6, memory=50.0)}, {"apps": _bench(2.0, 1.6, memory=70.0)})

    assert code == 1
    assert "REGRESSION: apps memory (avg_memory_mb) degraded" in capsys.readouterr().out


def test_best_time_above_the_ceiling_fails(tmp_path, monkeypatch, capsys):
    code = _run(tmp_path, monkeypatch, {"outdated": _bench(7.2, 6.3)}, {"outdated": _bench(40.0, 31.0)})

    assert code == 1
    assert "REGRESSION: outdated min_time 31.00s exceeds the 30s ceiling" in capsys.readouterr().out


def test_one_slow_iteration_cannot_trip_the_ceiling(tmp_path, monkeypatch, capsys):
    # mean above 30 s from a single network spike, but the best iteration is well under it
    code = _run(tmp_path, monkeypatch, {"outdated": _bench(7.2, 6.3)}, {"outdated": _bench(32.0, 9.0)})

    assert code == 0
    assert "ceiling" not in capsys.readouterr().out


def test_ceiling_falls_back_to_avg_time_without_min_time(tmp_path, monkeypatch, capsys):
    code = _run(tmp_path, monkeypatch, {"apps": _bench(2.0)}, {"apps": _bench(31.0)})

    assert code == 1
    assert "REGRESSION: apps avg_time 31.00s exceeds the 30s ceiling" in capsys.readouterr().out


def test_no_baseline_still_enforces_the_ceiling(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "performance_results.json").write_text(json.dumps({"results": {"apps": _bench(40.0, 35.0)}}))

    code = compare_performance.compare_results(tmp_path / "missing_baseline.json")

    out = capsys.readouterr().out
    assert code == 1
    assert "No baseline found" in out
