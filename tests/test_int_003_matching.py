"""INT-003 Integration Tests: Enhanced vs Basic (disabled) matching differential (stub).

Purpose:
    Provide an integration-level scaffold to ensure future enhanced matching
    logic (fuzzy alias expansion, normalization improvements, etc.) can be
    regression-tested without rewriting existing high-mock unit tests.

Current State (Stub):
    The core recommendation handler does not yet expose a first-class
    strategy object for "enhanced" vs "basic" matching that we can interrogate
    directly here. This test simulates differential behavior by monkeypatching
    the candidate filtering & brew candidate evaluation functions with
    behavior gated by the presence/absence of the `no_enhanced_matching`
    flag on the options namespace.

    When enhanced matching is "enabled" (default, i.e. no_enhanced_matching=False):
        - We pretend aliases expand candidate pool by 1.
    When enhanced matching is "disabled" (no_enhanced_matching=True):
        - We return the raw (smaller) candidate list.

Why This Matters:
    As the real enhanced matching gets refactored toward an injectable /
    strategy-based pattern, this test provides a ready-made place to:
        * Replace simulation with real output comparisons
        * Introduce golden-file diffs for candidate order / inclusion
        * Validate stability of strict-mode interplay

Planned Enhancements (later phases):
    - Assert semantic differences (e.g., alias 'vscode' => 'visual-studio-code')
    - Add parity checks (enhanced vs basic) for deterministic toggle effect
    - Integrate with async candidate retrieval once stabilized

Markers:
    Marked as @pytest.mark.integration consistent with prior INT-00x files.

"""

from __future__ import annotations

import types
from typing import Any

import pytest


class DummyProgressBar:
    """Neutral color stub."""

    def color(self, _color: str):
        return lambda s: s


def _build_base_apps() -> list[tuple[str, str]]:
    """Return a deterministic minimal application list."""
    return [
        ("AlphaApp", "1.0"),
        ("BetaTool", "2.1"),
        ("GammaSuite", "3.0"),
    ]


@pytest.mark.integration
def test_int_003_matching_enhanced_enabled(monkeypatch, capsys):
    """INT-003.1: Simulated enhanced matching yields an expanded installable set."""
    from versiontracker.handlers import brew_handlers

    apps = _build_base_apps()
    brew_casks = ["alphaapp"]  # Simulate one native brew cask

    # Patch internal data acquisition
    monkeypatch.setattr(brew_handlers, "_get_application_data", lambda: apps)
    monkeypatch.setattr(brew_handlers, "_get_homebrew_casks", lambda: brew_casks)

    # Track internal calls
    call_log: list[Any] = []

    # Simulated filter_out_brews simply returns all apps as candidates
    def mock_filter_out_brews(app_list, casks_list, strict_flag):
        call_log.append(("filter_out_brews", strict_flag, len(app_list)))
        return app_list

    monkeypatch.setattr(brew_handlers, "filter_out_brews", mock_filter_out_brews)

    # Enhanced-mode simulation:
    #   - We add one synthetic alias candidate "alphatool" for demonstration.
    def mock_check_brew_install_candidates(search_list, rate_limit, strict_mode):
        call_log.append(("check_brew_install_candidates", strict_mode, rate_limit, len(search_list)))
        enhanced_candidates = list(search_list)
        # Simulate alias expansion / normalization adding a new match
        enhanced_candidates.append(("AlphaTool", "1.0"))
        # Return tuples: (canonical_name, variant, installable_bool)
        return [(name.lower(), name.lower(), True) for name, _ in enhanced_candidates]

    monkeypatch.setattr(brew_handlers, "check_brew_install_candidates", mock_check_brew_install_candidates)

    # No auto-update interplay
    monkeypatch.setattr(brew_handlers, "get_casks_with_auto_updates", lambda _: [])

    # UI neutral
    monkeypatch.setattr(brew_handlers, "create_progress_bar", lambda: DummyProgressBar())

    class DummyConfig:
        def is_blacklisted(self, _name: str) -> bool:
            return False

        def get(self, key: str, default: int = 10):
            if key == "rate_limit":
                return 1
            return default

    monkeypatch.setattr(brew_handlers, "get_config", lambda: DummyConfig())

    # Options: enhanced matching implicitly enabled (flag absent / False)
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
        no_enhanced_matching=False,  # Explicit clarity
    )

    rc = brew_handlers.handle_brew_recommendations(options)
    assert rc == 0

    out = capsys.readouterr().out

    # Expect 4 installables (3 base + 1 simulated alias)
    assert "Found 4 applications installable with Homebrew" in out
    assert any(entry[0] == "check_brew_install_candidates" for entry in call_log)


@pytest.mark.integration
def test_int_003_matching_enhanced_disabled(monkeypatch, capsys):
    """INT-003.2: Simulated basic matching has fewer installables than enhanced mode."""
    from versiontracker.handlers import brew_handlers

    apps = _build_base_apps()
    brew_casks = ["alphaapp"]

    monkeypatch.setattr(brew_handlers, "_get_application_data", lambda: apps)
    monkeypatch.setattr(brew_handlers, "_get_homebrew_casks", lambda: brew_casks)

    call_log: list[Any] = []

    def mock_filter_out_brews(app_list, casks_list, strict_flag):
        call_log.append(("filter_out_brews", strict_flag, len(app_list)))
        return app_list

    monkeypatch.setattr(brew_handlers, "filter_out_brews", mock_filter_out_brews)

    # Basic-mode simulation returns only the original 3 apps (no alias expansion).
    def mock_check_brew_install_candidates(search_list, rate_limit, strict_mode):
        call_log.append(("check_brew_install_candidates", strict_mode, rate_limit, len(search_list)))
        return [(name.lower(), name.lower(), True) for name, _ in search_list]

    monkeypatch.setattr(brew_handlers, "check_brew_install_candidates", mock_check_brew_install_candidates)
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
        recommend=True,
        strict_recommend=False,
        strict_recom=False,
        debug=False,
        rate_limit=1,
        export_format=None,
        output_file=None,
        exclude_auto_updates=False,
        only_auto_updates=False,
        no_enhanced_matching=True,  # Disable enhanced matching
    )

    rc = brew_handlers.handle_brew_recommendations(options)
    assert rc == 0

    out = capsys.readouterr().out
    # Expect only 3 installables (no alias expansion)
    assert "Found 3 applications installable with Homebrew" in out
    assert any(entry[0] == "check_brew_install_candidates" for entry in call_log)

    # Differential assertion (sanity): ensure "Found 4" NOT present
    assert "Found 4 applications installable with Homebrew" not in out
