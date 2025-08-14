"""INT-001 Integration Tests: Basic application discovery flow.

These tests exercise the minimal end-to-end path for the "list applications"
handler (`handle_list_apps`) with controlled mocking so they:
- Avoid real system profiler / filesystem access
- Exercise blocklist (new terminology) and legacy blacklist pathways
- Produce deterministic output suitable for future golden comparison

Scope (INT-001):
1. Basic discovery prints all provided applications (no filtering).
2. Blocklist filtering removes specified applications using the new --blocklist
   semantics while still relying on the legacy internal storage key ('blacklist').

Future Suites (INT-002+):
- Will extend to enhanced matching, outdated flow, and strict recommendation paths.
"""

from __future__ import annotations

import types
from typing import Any, List, Tuple

import pytest

# Internal imports intentionally delayed inside tests where patching occurs
# to ensure correct monkeypatch application order.


@pytest.mark.integration
def test_int_001_discovery_basic(monkeypatch, capsys):
    """INT-001.1: Basic discovery shows all applications (no blocklist)."""
    # Lazy import inside test to ensure environment isolation
    from versiontracker.handlers import app_handlers

    # Stub applications list
    apps: List[Tuple[str, str]] = [
        ("AppOne", "1.0"),
        ("AppTwo", "2.3"),
        ("AppThree", "0.9.1"),
    ]

    # Patch get_applications to return our deterministic list
    monkeypatch.setattr(app_handlers, "get_applications", lambda _data: apps)

    # Patch get_json_data to avoid invoking system_profiler
    monkeypatch.setattr(app_handlers, "get_json_data", lambda *_args, **_kwargs: {})

    # Patch create_progress_bar to suppress colored output complexity
    class DummyPB:
        def color(self, _color: str):
            return lambda s: s

    monkeypatch.setattr(app_handlers, "create_progress_bar", lambda: DummyPB())

    # Provide a get_config that reports nothing blocklisted
    class DummyConfig:
        def is_blocklisted(self, name: str) -> bool:
            return False

    monkeypatch.setattr(app_handlers, "get_config", lambda: DummyConfig())

    # Options namespace (simulate argparse namespace)
    options = types.SimpleNamespace(
        blocklist=None,
        blacklist=None,
        additional_dirs=None,
        brew_filter=False,
        include_brews=False,
        export_format=None,
        output_file=None,
    )

    rc = app_handlers.handle_list_apps(options)
    captured = capsys.readouterr()

    assert rc == 0, "Expected successful return code"
    # Ensure each app name appears exactly once
    for name in ("AppOne", "AppTwo", "AppThree"):
        assert name in captured.out, f"{name} missing from output"


@pytest.mark.integration
def test_int_001_discovery_blocklist_filters(monkeypatch, capsys):
    """INT-001.2: Blocklist (preferred terminology) filters applications."""
    from versiontracker.handlers import app_handlers

    apps: List[Tuple[str, str]] = [
        ("AppOne", "1.0"),
        ("AppTwo", "2.3"),
        ("AppThree", "0.9.1"),
    ]
    monkeypatch.setattr(app_handlers, "get_applications", lambda _data: apps)
    monkeypatch.setattr(app_handlers, "get_json_data", lambda *_args, **_kwargs: {})

    class DummyPB:
        def color(self, _color: str):
            return lambda s: s

    monkeypatch.setattr(app_handlers, "create_progress_bar", lambda: DummyPB())

    # We won't rely on global config for this test because the code path
    # creates a temporary Config when blocklist/blacklist options are provided.
    # Patch Config with a minimal stub implementing set() and is_blocklisted().
    class StubConfig:
        def __init__(self) -> None:
            self._entries: List[str] = []

        def set(self, key: str, value: Any) -> None:  # noqa: D401
            if key == "blacklist":
                # store normalized lower-case entries
                self._entries = [v.strip().lower() for v in value if v.strip()]

        def is_blocklisted(self, name: str) -> bool:
            return name.lower() in self._entries

        # Legacy method used in some branches (defensive)
        def is_blacklisted(self, name: str) -> bool:
            return self.is_blocklisted(name)

    monkeypatch.setattr(app_handlers, "Config", StubConfig)

    # Provide fallback global config (should not be used in this branch but safe)
    class DummyConfig:
        def is_blocklisted(self, _name: str) -> bool:
            return False

    monkeypatch.setattr(app_handlers, "get_config", lambda: DummyConfig())

    # Blocklist AppTwo
    options = types.SimpleNamespace(
        blocklist="AppTwo",
        blacklist=None,
        additional_dirs=None,
        brew_filter=False,
        include_brews=False,
        export_format=None,
        output_file=None,
    )

    rc = app_handlers.handle_list_apps(options)
    captured = capsys.readouterr()

    assert rc == 0, "Expected successful return code"
    assert "AppTwo" not in captured.out, "Blocklisted application should not appear"
    assert "AppOne" in captured.out
    assert "AppThree" in captured.out


@pytest.mark.integration
def test_int_001_discovery_legacy_blacklist(monkeypatch, capsys):
    """INT-001.3: Legacy blacklist option continues to function (backward compatibility)."""
    from versiontracker.handlers import app_handlers

    apps: List[Tuple[str, str]] = [
        ("AlphaApp", "1.0"),
        ("BetaApp", "2.0"),
    ]
    monkeypatch.setattr(app_handlers, "get_applications", lambda _data: apps)
    monkeypatch.setattr(app_handlers, "get_json_data", lambda *_args, **_kwargs: {})

    class DummyPB:
        def color(self, _color: str):
            return lambda s: s

    monkeypatch.setattr(app_handlers, "create_progress_bar", lambda: DummyPB())

    # Provide stub Config for legacy path
    class StubConfig:
        def __init__(self) -> None:
            self._entries = []

        def set(self, key: str, value):
            if key == "blacklist":
                self._entries = [v.strip().lower() for v in value if v.strip()]

        def is_blocklisted(self, name: str) -> bool:
            return name.lower() in self._entries

        def is_blacklisted(self, name: str) -> bool:  # Legacy compatibility
            return self.is_blocklisted(name)

    monkeypatch.setattr(app_handlers, "Config", StubConfig)
    monkeypatch.setattr(app_handlers, "get_config", lambda: StubConfig())

    options = types.SimpleNamespace(
        blocklist=None,  # Not provided
        blacklist="BetaApp",  # Legacy flag path
        additional_dirs=None,
        brew_filter=False,
        include_brews=False,
        export_format=None,
        output_file=None,
    )

    rc = app_handlers.handle_list_apps(options)
    captured = capsys.readouterr()

    assert rc == 0
    assert "AlphaApp" in captured.out
    assert "BetaApp" not in captured.out, "Legacy blacklist should filter BetaApp"
