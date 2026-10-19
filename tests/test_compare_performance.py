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


def test_gates_on_best_of_n_so_one_slow_iteration_does_not_fail(tmp_path, monkeypatch, capsys):
    # avg +30% (one slow iteration), best-of-3 only +8%: not a regression
    code = _run(tmp_path, monkeypatch, {"apps": _bench(2.154, 1.650)}, {"apps": _bench(2.804, 1.788)})

    assert code == 0
    assert "REGRESSION" not in capsys.readouterr().out


def test_local_benchmark_best_of_n_regression_fails(tmp_path, monkeypatch, capsys):
    code = _run(tmp_path, monkeypatch, {"apps": _bench(2.0, 1.650)}, {"apps": _bench(2.6, 2.200)})

    assert code == 1
    assert "REGRESSION: apps time (min_time) degraded" in capsys.readouterr().out


def test_network_bound_time_regression_warns_without_failing(tmp_path, monkeypatch, capsys):
    code = _run(tmp_path, monkeypatch, {"outdated": _bench(7.198, 6.308)}, {"outdated": _bench(13.660, 10.157)})

    out = capsys.readouterr().out
    assert code == 0
    assert "WARNING: outdated time (min_time) degraded" in out
    assert "network-bound, not gated" in out
    assert "REGRESSION" not in out


def test_network_bound_memory_regression_still_fails(tmp_path, monkeypatch, capsys):
    code = _run(
        tmp_path,
        monkeypatch,
        {"recommend": _bench(6.0, 5.0, memory=50.0)},
        {"recommend": _bench(6.0, 5.0, memory=80.0)},
    )

    assert code == 1
    assert "REGRESSION: recommend memory (avg_memory_mb) degraded" in capsys.readouterr().out


def test_falls_back_to_avg_time_when_a_file_has_no_min_time(tmp_path, monkeypatch, capsys):
    code = _run(tmp_path, monkeypatch, {"apps": _bench(2.0)}, {"apps": _bench(2.6, 1.0)})

    assert code == 1
    assert "REGRESSION: apps time (avg_time) degraded" in capsys.readouterr().out


def test_replays_the_2026_10_18_scheduled_run_as_passing_with_network_warnings(tmp_path, monkeypatch, capsys):
    # Baseline: scheduled run 38182609131 (2026-10-11). Current: run 39174628747 attempt 2. No runtime code changed
    # between them; under the old avg_time gate this failed apps/recommend/outdated.
    baseline = {
        "apps": _bench(2.154, 1.650),
        "brews": _bench(0.002, 0.002),
        "recommend": _bench(6.121, 5.032),
        "outdated": _bench(7.198, 6.308),
    }
    current = {
        "apps": _bench(2.804, 1.788),
        "brews": _bench(0.005, 0.004),
        "recommend": _bench(7.589, 6.344),
        "outdated": _bench(13.660, 10.157),
    }

    code = _run(tmp_path, monkeypatch, baseline, current)

    out = capsys.readouterr().out
    assert code == 0
    assert "REGRESSION" not in out
    assert out.count("network-bound, not gated") == 2
