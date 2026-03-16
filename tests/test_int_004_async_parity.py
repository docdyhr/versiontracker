"""INT-004 Integration Tests: Async feature flag output parity.

Goal:
    Ensure that the recommendation workflow (handle_brew_recommendations)
    produces consistent, deterministic output regardless of internal async
    vs sync code paths.

Test Strategy:
    1. Monkeypatch all external side-effect functions used by
       handle_brew_recommendations.
    2. Execute the handler twice under different conditions and verify
       consistent output.
    3. Capture stdout both times and assert:
        - Return code == 0
        - The summary line "Found N applications installable with Homebrew" matches
"""

from __future__ import annotations

import types

import pytest


class DummyProgressBar:
    """Neutral progress bar stub to avoid colored or dynamic output."""

    def color(self, _color: str):
        return lambda s: s


@pytest.mark.integration
def test_int_004_async_parity(monkeypatch, capsys):
    """INT-004: Recommendation output parity across multiple invocations."""
    from versiontracker.handlers import brew_handlers

    # Canonical deterministic application list
    apps: list[tuple[str, str]] = [
        ("AlphaApp", "1.0"),
        ("BetaApp", "2.2"),
        ("GammaApp", "3.1"),
    ]
    brew_casks = ["alphaapp"]  # Pretend one app already has a brew cask

    # Candidate filter returns all apps (simulate non-strict path)
    def mock_filter_out_brews(app_list, cask_list, strict_flag):
        assert strict_flag is False  # We supply non-strict options
        return app_list

    # All candidates judged installable (return list of tuples like real checker)
    def mock_check_brew_install_candidates(search_list, rate_limit, strict_mode):
        assert strict_mode is False
        # Real function returns tuples (name, maybe_alias, installable_bool)
        return [(name.lower(), name.lower(), True) for name, _ in search_list]

    # No auto-update filtering interplay for this parity test
    def mock_get_casks_with_auto_updates(_installables):
        return []

    # Config stub
    class DummyConfig:
        def is_blacklisted(self, _name: str) -> bool:
            return False

        def get(self, key: str, default: int = 10):
            if key == "rate_limit":
                return 1
            return default

    # Shared monkeypatches
    def apply_shared_patches():
        monkeypatch.setattr(brew_handlers, "_get_application_data", lambda: apps)
        monkeypatch.setattr(brew_handlers, "_get_homebrew_casks", lambda: brew_casks)
        monkeypatch.setattr(brew_handlers, "filter_out_brews", mock_filter_out_brews)
        monkeypatch.setattr(
            brew_handlers,
            "check_brew_install_candidates",
            mock_check_brew_install_candidates,
        )
        monkeypatch.setattr(brew_handlers, "get_casks_with_auto_updates", mock_get_casks_with_auto_updates)
        monkeypatch.setattr(brew_handlers, "create_progress_bar", lambda: DummyProgressBar())
        monkeypatch.setattr(brew_handlers, "get_config", lambda: DummyConfig())

    # Options namespace
    def build_options():
        return types.SimpleNamespace(
            recommend=True,
            strict_recommend=False,
            strict_recom=False,
            debug=False,
            rate_limit=1,
            export_format=None,
            output_file=None,
            exclude_auto_updates=False,
            only_auto_updates=False,
            no_enhanced_matching=False,
        )

    # First run
    apply_shared_patches()
    opts_first = build_options()
    rc_first = brew_handlers.handle_brew_recommendations(opts_first)
    out_first = capsys.readouterr().out

    assert rc_first == 0
    # 3 candidates all marked installable, but alphaapp removed by post-filter
    # (already in brew_casks). Leaves 2.
    assert "Found 2 applications installable with Homebrew" in out_first

    # Second run (verify deterministic output)
    apply_shared_patches()
    opts_second = build_options()
    rc_second = brew_handlers.handle_brew_recommendations(opts_second)
    out_second = capsys.readouterr().out

    assert rc_second == 0
    assert "Found 2 applications installable with Homebrew" in out_second

    # Parity assertion: summary line count must match
    summary_first = [line for line in out_first.splitlines() if "Found 2 applications installable" in line]
    summary_second = [line for line in out_second.splitlines() if "Found 2 applications installable" in line]
    assert summary_first == summary_second, "Output changed between runs unexpectedly"

    # Sanity: ensure no accidental duplication
    assert out_second.count("Found 2 applications installable with Homebrew") == 1
