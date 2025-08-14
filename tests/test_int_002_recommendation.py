"""INT-002 Integration Tests: Recommendation workflow (basic vs strict).

This suite validates that:
1. Basic recommendation mode (non-strict) processes the full candidate list.
2. Strict mode reduces candidate set as expected (filter_out_brews called with strict=True).
3. The output reflects differing installable counts.

The tests mock:
- Application discovery
- Homebrew cask retrieval
- Filtering logic (filter_out_brews)
- Brew candidate evaluation (check_brew_install_candidates)
- Progress bar coloring (neutralized)
- Configuration (no blocklist)

We focus on observable behavior (installable counts) and internal call semantics
(filter_out_brews third argument). This ensures future refactors to matching
logic still preserve the contract.

Note:
The underlying handler prints progress and informative lines; tests assert only
on stable summary lines to remain resilient to cosmetic changes.
"""

from __future__ import annotations

import types
from typing import Any, List, Tuple

import pytest


class DummyProgressBar:
    """Minimal progress bar stub to neutralize colored output in tests."""

    def color(self, _color: str):
        return lambda s: s


@pytest.mark.integration
def test_int_002_recommendation_basic(monkeypatch, capsys):
    """INT-002.1: Basic recommendation mode includes all non-brew apps."""
    from versiontracker.handlers import brew_handlers

    # Stub application + brew environment
    apps: List[Tuple[str, str]] = [
        ("AlphaApp", "1.0"),
        ("BetaApp", "2.1"),
        ("GammaApp", "3.0"),
    ]
    brew_casks = ["alphaapp"]  # Suppose one app has a brew cask already

    # Patch filtered application data retrieval
    monkeypatch.setattr(brew_handlers, "_get_application_data", lambda: apps)
    monkeypatch.setattr(brew_handlers, "_get_homebrew_casks", lambda: brew_casks)

    # Track calls to validate strict flag propagation
    calls: List[Any] = []

    def mock_filter_out_brews(app_list, casks_list, strict_flag):
        # Record arguments for later assertions
        calls.append(("filter_out_brews", strict_flag))
        # In non-strict mode we return all apps for candidate scanning
        return app_list

    monkeypatch.setattr(brew_handlers, "filter_out_brews", mock_filter_out_brews)

    # Mock candidate checker: return tuple (origin_name, mapped_name, installable_bool)
    def mock_check_candidates(search_list, rate_limit, strict_mode):
        calls.append(("check_candidates", strict_mode, rate_limit, len(search_list)))
        # Mark everything installable in basic mode
        return [(name.lower(), name.lower(), True) for name, _ in search_list]

    monkeypatch.setattr(brew_handlers, "check_brew_install_candidates", mock_check_candidates)

    # No auto-update filtering in this test
    monkeypatch.setattr(brew_handlers, "get_casks_with_auto_updates", lambda _: [])

    # Neutralize progress UI
    monkeypatch.setattr(brew_handlers, "create_progress_bar", lambda: DummyProgressBar())

    # Config stub (no blocklist behavior triggered here)
    class DummyConfig:
        def is_blacklisted(self, _name: str) -> bool:
            return False

        def get(self, key: str, default: int = 10):
            if key == "rate_limit":
                return 1
            return default

    monkeypatch.setattr(brew_handlers, "get_config", lambda: DummyConfig())

    # Build options namespace (non-strict)
    options = types.SimpleNamespace(
        recommend=True,
        strict_recommend=False,
        strict_recom=False,
        debug=False,
        rate_limit=1,
        export_format=None,
        output_file=None,
        exclude_auto_updates=False,
        only_auto_updates=False,
    )

    rc = brew_handlers.handle_brew_recommendations(options)
    assert rc == 0

    out = capsys.readouterr().out
    # Expect all three applications (minus those filtered by brew casks inside
    # filter_out_brews, which we did not modify)
    # filter_out_brews returns list including all 3; candidate checker returns 3 installables
    assert "Found 3 applications installable with Homebrew" in out

    # Validate that strict flag seen as False
    assert ("filter_out_brews", False) in calls
    # Candidate checker called once and received strict_mode False
    assert any(call[0] == "check_candidates" and call[1] is False for call in calls)


@pytest.mark.integration
def test_int_002_recommendation_strict(monkeypatch, capsys):
    """INT-002.2: Strict recommendation mode reduces candidate pool."""
    from versiontracker.handlers import brew_handlers

    # Stub data (same as basic to isolate strict effect)
    apps: List[Tuple[str, str]] = [
        ("AlphaApp", "1.0"),
        ("BetaApp", "2.1"),
        ("GammaApp", "3.0"),
    ]
    brew_casks = ["alphaapp"]

    monkeypatch.setattr(brew_handlers, "_get_application_data", lambda: apps)
    monkeypatch.setattr(brew_handlers, "_get_homebrew_casks", lambda: brew_casks)

    calls: List[Any] = []

    def mock_filter_out_brews(app_list, casks_list, strict_flag):
        calls.append(("filter_out_brews", strict_flag))
        # Simulate stricter filtering reducing candidates to BetaApp only
        if strict_flag:
            return [("BetaApp", "2.1")]
        return app_list

    monkeypatch.setattr(brew_handlers, "filter_out_brews", mock_filter_out_brews)

    def mock_check_candidates(search_list, rate_limit, strict_mode):
        calls.append(("check_candidates", strict_mode, rate_limit, len(search_list)))
        return [(name.lower(), name.lower(), True) for name, _ in search_list]

    monkeypatch.setattr(brew_handlers, "check_brew_install_candidates", mock_check_candidates)
    monkeypatch.setattr(brew_handlers, "get_casks_with_auto_updates", lambda _: [])
    monkeypatch.setattr(brew_handlers, "create_progress_bar", lambda: DummyProgressBar())

    class DummyConfig:
        def is_blacklisted(self, _name: str) -> bool:
            return False

        def get(self, key: str, default: int = 10):
            if key == "rate_limit":
                return 1
            return default

    monkeypatch.setattr(brew_handlers, "get_config", lambda: DummyConfig())

    options = types.SimpleNamespace(
        recommend=False,  # Strict recommendation path
        strict_recommend=True,
        strict_recom=True,  # Some legacy code paths check strict_recom
        debug=False,
        rate_limit=1,
        export_format=None,
        output_file=None,
        exclude_auto_updates=False,
        only_auto_updates=False,
    )

    rc = brew_handlers.handle_brew_recommendations(options)
    assert rc == 0

    out = capsys.readouterr().out
    # Expect only 1 installable due to strict filtering
    assert "Found 1 applications installable with Homebrew" in out

    # Validate strict flag propagation
    assert ("filter_out_brews", True) in calls
    assert any(call[0] == "check_candidates" and call[1] is True for call in calls)
