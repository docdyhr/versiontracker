"""Tests for versiontracker.audit.homebrew."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import versiontracker.audit.homebrew as homebrew_module
from versiontracker.audit.homebrew import (
    apply_homebrew_evidence,
    build_artifact_index,
    fetch_installed_casks,
    resolve_homebrew_evidence,
)
from versiontracker.audit.models import (
    ApplicationRecord,
    AppStoreEvidence,
    AppStoreStatus,
    EvidenceSource,
    HomebrewStatus,
)
from versiontracker.exceptions import DataParsingError, HomebrewError, NetworkError
from versiontracker.exceptions import TimeoutError as VtTimeoutError


def _make_record(canonical_path: Path, *, bundle_id: str | None = None, name: str = "App") -> ApplicationRecord:
    return ApplicationRecord(
        name=name,
        version="1.0",
        path=canonical_path,
        canonical_path=canonical_path,
        bundle_id=bundle_id,
        obtained_from=None,
        parent_bundle_path=None,
        app_store=AppStoreEvidence(
            status=AppStoreStatus.NOT_APP_STORE, reason="test", source=EvidenceSource.SYSTEM_PROFILER
        ),
    )


@pytest.fixture(autouse=True)
def _fake_brew_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test gets a fixed, fake brew path -- no dependency on the real
    test-running machine's actual Homebrew installation."""
    monkeypatch.setattr(homebrew_module, "get_brew_command", lambda: "/opt/homebrew/bin/brew")


class TestFetchInstalledCasks:
    def test_success_returns_casks_list(self, monkeypatch, installed_casks_payload_factory, cask_factory) -> None:
        payload = installed_casks_payload_factory(cask_factory("firefox", app_name="Firefox.app"))
        monkeypatch.setattr(homebrew_module, "run_command_secure", lambda *a, **k: (json.dumps(payload), 0))

        casks = fetch_installed_casks()

        assert len(casks) == 1
        assert casks[0]["token"] == "firefox"

    def test_nonzero_returncode_raises_homebrew_error(self, monkeypatch) -> None:
        monkeypatch.setattr(homebrew_module, "run_command_secure", lambda *a, **k: ("some error", 1))

        with pytest.raises(HomebrewError):
            fetch_installed_casks()

    def test_timeout_raises_network_error(self, monkeypatch) -> None:
        def raise_timeout(*args: object, **kwargs: object) -> tuple[str, int]:
            raise VtTimeoutError("timed out")

        monkeypatch.setattr(homebrew_module, "run_command_secure", raise_timeout)

        with pytest.raises(NetworkError):
            fetch_installed_casks()

    def test_missing_brew_binary_raises_homebrew_error(self, monkeypatch) -> None:
        """Confirmed live: run_command_secure surfaces a bare builtins.Exception
        for a missing executable -- its own FileNotFoundError except clause is
        bound to versiontracker's custom subclass, not the plain builtin
        subprocess.Popen actually raises. fetch_installed_casks must still
        degrade this to HomebrewError, not let it propagate uncaught."""

        def raise_bare_exception(*args: object, **kwargs: object) -> tuple[str, int]:
            raise Exception("[Errno 2] No such file or directory: 'brew'")

        monkeypatch.setattr(homebrew_module, "run_command_secure", raise_bare_exception)

        with pytest.raises(HomebrewError):
            fetch_installed_casks()

    def test_malformed_json_raises_data_parsing_error(self, monkeypatch) -> None:
        monkeypatch.setattr(homebrew_module, "run_command_secure", lambda *a, **k: ("not json", 0))

        with pytest.raises(DataParsingError):
            fetch_installed_casks()

    def test_missing_casks_key_returns_empty_list(self, monkeypatch) -> None:
        monkeypatch.setattr(homebrew_module, "run_command_secure", lambda *a, **k: ("{}", 0))

        assert fetch_installed_casks() == []


class TestBuildArtifactIndex:
    def test_single_app_cask_indexed_by_canonical_target(self, cask_factory) -> None:
        casks = [
            cask_factory("firefox", app_name="Firefox.app", app_target="/Applications/Firefox.app", installed="120.0")
        ]

        index = build_artifact_index(casks)

        key = Path("/Applications/Firefox.app").resolve()
        assert key in index
        assert index[key].token == "firefox"
        assert index[key].installed_version == "120.0"

    def test_zero_app_artifact_cask_contributes_nothing(self, cask_factory) -> None:
        casks = [cask_factory("font-hack-nerd-font", app_name=None)]

        assert build_artifact_index(casks) == {}

    def test_multi_app_cask_produces_two_separate_index_entries(self, cask_factory) -> None:
        cask = cask_factory(
            "caffeine-mini-pro", app_name="Caffeine Mini.app", app_target="/Applications/Caffeine Mini.app"
        )
        cask["artifacts"].append({"app": ["Caffeine Pro.app"], "target": "/Applications/Caffeine Pro.app"})

        index = build_artifact_index([cask])

        assert Path("/Applications/Caffeine Mini.app").resolve() in index
        assert Path("/Applications/Caffeine Pro.app").resolve() in index
        assert len(index) == 2

    def test_non_app_artifacts_alongside_app_artifact_are_skipped(self, cask_factory) -> None:
        """Real casks always mix artifact kinds (uninstall/zap/binary/preflight
        alongside app) -- confirm non-app-keyed entries don't confuse indexing."""
        cask = cask_factory("firefox", app_name="Firefox.app", app_target="/Applications/Firefox.app")
        cask["artifacts"] = [
            {"preflight": None},
            {"uninstall": [{"quit": "org.mozilla.firefox"}]},
            *cask["artifacts"],
            {"binary": ["firefox"], "target": "/opt/homebrew/bin/firefox"},
        ]

        index = build_artifact_index([cask])

        assert len(index) == 1
        assert Path("/Applications/Firefox.app").resolve() in index

    def test_cask_without_token_is_skipped(self, cask_factory) -> None:
        cask = cask_factory("firefox", app_name="Firefox.app")
        del cask["token"]

        assert build_artifact_index([cask]) == {}

    def test_unresolvable_target_is_skipped(self, monkeypatch, cask_factory) -> None:
        monkeypatch.setattr(homebrew_module, "_canonicalize_target", lambda target: None)
        casks = [cask_factory("firefox", app_name="Firefox.app", app_target="/Applications/Firefox.app")]

        assert build_artifact_index(casks) == {}

    def test_third_party_tap_cask_indexed_same_as_official(self, cask_factory) -> None:
        casks = [cask_factory("container-use", tap="dagger/tap", app_name="Container Use.app")]

        index = build_artifact_index(casks)

        assert len(index) == 1
        assert next(iter(index.values())).tap == "dagger/tap"

    def test_canonical_path_collision_keeps_first_seen(self, cask_factory) -> None:
        first = cask_factory("app-a", app_name="Shared.app", app_target="/Applications/Shared.app")
        second = cask_factory("app-b", app_name="Shared.app", app_target="/Applications/Shared.app")

        index = build_artifact_index([first, second])

        assert len(index) == 1
        assert next(iter(index.values())).token == "app-a"

    def test_artifact_without_target_is_skipped(self, cask_factory) -> None:
        cask = cask_factory("weird", app_name="Weird.app")
        cask["artifacts"][0].pop("target")

        assert build_artifact_index([cask]) == {}


class TestResolveHomebrewEvidence:
    def test_exact_match_is_managed(self, cask_factory) -> None:
        casks = [
            cask_factory("firefox", app_name="Firefox.app", app_target="/Applications/Firefox.app", installed="120.0")
        ]
        index = build_artifact_index(casks)
        record = _make_record(Path("/Applications/Firefox.app").resolve())

        evidence = resolve_homebrew_evidence(record, index)

        assert evidence.status == HomebrewStatus.MANAGED
        assert evidence.matched_identifier == "firefox"
        assert evidence.installed_version == "120.0"
        assert evidence.artifact_target == Path("/Applications/Firefox.app").resolve()

    def test_cask_auto_updates_true_is_threaded_through(self, cask_factory) -> None:
        casks = [
            cask_factory("firefox", app_name="Firefox.app", app_target="/Applications/Firefox.app", auto_updates=True)
        ]
        index = build_artifact_index(casks)
        record = _make_record(Path("/Applications/Firefox.app").resolve())

        evidence = resolve_homebrew_evidence(record, index)

        assert evidence.cask_auto_updates is True

    def test_cask_auto_updates_false_is_threaded_through(self, cask_factory) -> None:
        casks = [
            cask_factory("firefox", app_name="Firefox.app", app_target="/Applications/Firefox.app", auto_updates=False)
        ]
        index = build_artifact_index(casks)
        record = _make_record(Path("/Applications/Firefox.app").resolve())

        evidence = resolve_homebrew_evidence(record, index)

        assert evidence.cask_auto_updates is False

    def test_no_match_cask_auto_updates_stays_none(self, cask_factory) -> None:
        casks = [cask_factory("firefox", app_name="Firefox.app", app_target="/Applications/Firefox.app")]
        index = build_artifact_index(casks)
        record = _make_record(Path("/Applications/ManuallyInstalled.app").resolve())

        evidence = resolve_homebrew_evidence(record, index)

        assert evidence.cask_auto_updates is None

    def test_no_match_is_not_available(self, cask_factory) -> None:
        casks = [cask_factory("firefox", app_name="Firefox.app", app_target="/Applications/Firefox.app")]
        index = build_artifact_index(casks)
        record = _make_record(Path("/Applications/ManuallyInstalled.app").resolve())

        evidence = resolve_homebrew_evidence(record, index)

        assert evidence.status == HomebrewStatus.NOT_AVAILABLE

    def test_empty_index_is_not_available(self) -> None:
        record = _make_record(Path("/Applications/Anything.app").resolve())

        evidence = resolve_homebrew_evidence(record, {})

        assert evidence.status == HomebrewStatus.NOT_AVAILABLE


class TestApplyHomebrewEvidence:
    def test_success_attaches_resolved_evidence_per_record(
        self, monkeypatch, installed_casks_payload_factory, cask_factory
    ) -> None:
        payload = installed_casks_payload_factory(
            cask_factory("firefox", app_name="Firefox.app", app_target="/Applications/Firefox.app")
        )
        monkeypatch.setattr(homebrew_module, "run_command_secure", lambda *a, **k: (json.dumps(payload), 0))
        managed_record = _make_record(Path("/Applications/Firefox.app").resolve(), name="Firefox")
        unmanaged_record = _make_record(Path("/Applications/Manual.app").resolve(), name="Manual")

        result = apply_homebrew_evidence([managed_record, unmanaged_record])

        by_name = {r.name: r for r in result}
        assert by_name["Firefox"].homebrew.status == HomebrewStatus.MANAGED
        assert by_name["Manual"].homebrew.status == HomebrewStatus.NOT_AVAILABLE

    def test_fetch_failure_degrades_every_record_to_unknown(self, monkeypatch) -> None:
        """Exit criterion 3: Homebrew failure produces unknown, never not_managed."""
        monkeypatch.setattr(homebrew_module, "run_command_secure", lambda *a, **k: ("boom", 1))
        records = [
            _make_record(Path("/Applications/A.app").resolve()),
            _make_record(Path("/Applications/B.app").resolve()),
        ]

        result = apply_homebrew_evidence(records)

        assert all(r.homebrew.status == HomebrewStatus.UNKNOWN for r in result)
        assert all(r.homebrew.error is not None for r in result)

    def test_original_records_are_not_mutated(self, monkeypatch) -> None:
        monkeypatch.setattr(homebrew_module, "run_command_secure", lambda *a, **k: ('{"casks": []}', 0))
        record = _make_record(Path("/Applications/A.app").resolve())

        apply_homebrew_evidence([record])

        assert record.homebrew.status == HomebrewStatus.NOT_EVALUATED
