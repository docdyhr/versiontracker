"""INT-004 Integration Tests: Async feature flag output parity.

Goal:
    Ensure that enabling the experimental async Homebrew prototype via the
    environment variable `VERSIONTRACKER_ASYNC_BREW=1` does not alter the
    observable output of the recommendation workflow (handle_brew_recommendations)
    compared to the default (flag disabled) path.

Rationale:
    Before deeper native async logic is adopted (currently the prototype
    uses thread offloading only), we want a safety net ensuring consistent
    user-visible results. This protects future refactors from silently
    changing counts, formatting, or filtering semantics.

Test Strategy:
    1. Monkeypatch all external side-effect functions used by
       handle_brew_recommendations:
        - _get_application_data
        - _get_homebrew_casks
        - filter_out_brews
        - check_brew_install_candidates
        - get_casks_with_auto_updates
        - create_progress_bar
        - get_config
    2. Execute the handler twice:
        a. Async flag disabled (unset env)
        b. Async flag enabled (set env)
    3. Capture stdout both times and assert:
        - Return code == 0
        - The summary line "Found N applications installable with Homebrew" matches
        - No unexpected differences (allowing for timing variations which we do not assert)
    4. Also assert that the prototype client reports enabled/disabled correctly
       via is_async_brew_enabled() for clarity and future regression detection.

Notes:
    - We DO NOT call any real Homebrew or system profiler operations.
    - This test is forward-compatible: if future logic begins *using* the async
      layer internally when enabled, the parity assertion remains valid.
"""

from __future__ import annotations

import os
import types
from typing import Any, List, Tuple

import pytest


class DummyProgressBar:
    """Neutral progress bar stub to avoid colored or dynamic output."""

    def color(self, _color: str):
        return lambda s: s


@pytest.mark.integration
def test_int_004_async_parity(monkeypatch, capsys):
    """INT-004: Recommendation output parity with and without async flag enabled."""
    from versiontracker.async_homebrew_prototype import (
        get_async_client,
        is_async_brew_enabled,
    )
    from versiontracker.handlers import brew_handlers

    # Canonical deterministic application list
    apps: List[Tuple[str, str]] = [
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

    # Shared monkeypatches (environment will toggle async behavior)
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

    # Run WITHOUT async flag
    if "VERSIONTRACKER_ASYNC_BREW" in os.environ:
        monkeypatch.delenv("VERSIONTRACKER_ASYNC_BREW", raising=False)
    apply_shared_patches()
    opts_sync = build_options()
    rc_sync = brew_handlers.handle_brew_recommendations(opts_sync)
    out_sync = capsys.readouterr().out

    assert rc_sync == 0
    assert is_async_brew_enabled({}) is False
    assert "Found 3 applications installable with Homebrew" in out_sync

    client_sync = get_async_client(force=None)
    assert client_sync.enabled is False

    # Run WITH async flag
    monkeypatch.setenv("VERSIONTRACKER_ASYNC_BREW", "1")
    apply_shared_patches()
    opts_async = build_options()
    rc_async = brew_handlers.handle_brew_recommendations(opts_async)
    out_async = capsys.readouterr().out

    assert rc_async == 0
    assert is_async_brew_enabled({"VERSIONTRACKER_ASYNC_BREW": "1"}) is True
    assert "Found 3 applications installable with Homebrew" in out_async

    client_async = get_async_client(force=None)
    assert client_async.enabled is True

    # Parity assertion: summary line count must match
    # (We avoid full output diff to remain resilient to incidental formatting changes.)
    summary_sync = [line for line in out_sync.splitlines() if "Found 3 applications installable" in line]
    summary_async = [line for line in out_async.splitlines() if "Found 3 applications installable" in line]
    assert summary_sync == summary_async, "Async flag altered summary output unexpectedly"

    # Sanity: ensure no accidental duplication in async run
    assert out_async.count("Found 3 applications installable with Homebrew") == 1
