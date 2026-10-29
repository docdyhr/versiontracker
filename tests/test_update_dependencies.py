"""Tests for scripts/update_dependencies.py lock-file generation."""

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "update_dependencies.py"
_spec = importlib.util.spec_from_file_location("update_dependencies", _SCRIPT)
assert _spec is not None and _spec.loader is not None
update_dependencies = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(update_dependencies)


def _generate(tmp_path, monkeypatch, with_constraints: bool) -> list[list[str]]:
    """Run _generate_lock_file with venv creation and every subprocess faked; return the commands."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "requirements-dev.txt").write_text("pytest\n")
    if with_constraints:
        (root / "constraints.txt").write_text("certifi>=2026.10.18\n")
    calls: list[list[str]] = []

    def fake_run(cmd, cwd=None):
        calls.append(list(cmd))
        return ("certifi==2026.10.23\npytest==9.2.0\n" if "freeze" in cmd else ""), 0

    monkeypatch.setattr(update_dependencies.venv, "create", lambda *a, **k: None)
    monkeypatch.setattr(update_dependencies, "run_command", fake_run)
    lock = root / "requirements-dev.lock"
    assert update_dependencies._generate_lock_file(root / "requirements-dev.txt", lock, root, "Development")
    assert lock.read_text().splitlines()[-2:] == ["certifi==2026.10.23", "pytest==9.2.0"]
    return calls


def _install_cmd(calls: list[list[str]]) -> list[str]:
    installs = [c for c in calls if "install" in c and "-r" in c]
    assert len(installs) == 1, calls
    return installs[0]


def test_lock_resolves_under_constraints(tmp_path, monkeypatch):
    """The lock is resolved with -c constraints.txt, the same constraints CI installs with."""
    cmd = _install_cmd(_generate(tmp_path, monkeypatch, with_constraints=True))
    assert cmd[cmd.index("-c") + 1] == str(tmp_path / "repo" / "constraints.txt")


def test_lock_without_constraints_file(tmp_path, monkeypatch):
    """A checkout without constraints.txt still generates, unconstrained."""
    cmd = _install_cmd(_generate(tmp_path, monkeypatch, with_constraints=False))
    assert "-c" not in cmd
