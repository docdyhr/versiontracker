"""Tests for versiontracker.audit.service."""

from __future__ import annotations

import json
from pathlib import Path

import versiontracker.audit.homebrew as homebrew_module
import versiontracker.audit.service as service_module
from versiontracker.audit.models import (
    ApplicationRecord,
    AppStoreEvidence,
    AppStoreStatus,
    AuditBucket,
    AuditClassification,
    AuditResult,
    AutoUpdateEvidence,
    AutoUpdateStatus,
    BlocklistEvidence,
    BlocklistMatchKind,
    BlocklistStatus,
    ClassifiedApplication,
    EvidenceSource,
    HomebrewEvidence,
    HomebrewStatus,
)
from versiontracker.audit.service import classify_record, filter_result, run_audit


def _app_store(status: AppStoreStatus = AppStoreStatus.NOT_APP_STORE, error: str | None = None) -> AppStoreEvidence:
    return AppStoreEvidence(status=status, reason="test", source=EvidenceSource.SYSTEM_PROFILER, error=error)


def _homebrew(
    status: HomebrewStatus = HomebrewStatus.NOT_AVAILABLE,
    token: str | None = None,
    reason: str = "test",
    error: str | None = None,
) -> HomebrewEvidence:
    return HomebrewEvidence(
        status=status, reason=reason, source=EvidenceSource.HOMEBREW_CLI, matched_identifier=token, error=error
    )


def _auto_update(
    status: AutoUpdateStatus = AutoUpdateStatus.NONE_DETECTED, error: str | None = None
) -> AutoUpdateEvidence:
    return AutoUpdateEvidence(status=status, reason="test", source=EvidenceSource.FILESYSTEM, error=error)


def _blocklist(
    status: BlocklistStatus = BlocklistStatus.NOT_BLOCKED,
    matched_by: BlocklistMatchKind | None = None,
    error: str | None = None,
) -> BlocklistEvidence:
    return BlocklistEvidence(
        status=status, reason="test", source=EvidenceSource.CONFIG, matched_by=matched_by, error=error
    )


def _make_record(
    *,
    name: str = "App",
    canonical_path: Path = Path("/Applications/App.app"),
    app_store: AppStoreEvidence | None = None,
    homebrew: HomebrewEvidence | None = None,
    auto_update: AutoUpdateEvidence | None = None,
    blocklist: BlocklistEvidence | None = None,
) -> ApplicationRecord:
    return ApplicationRecord(
        name=name,
        version="1.0",
        path=canonical_path,
        canonical_path=canonical_path,
        bundle_id=None,
        obtained_from=None,
        parent_bundle_path=None,
        app_store=app_store if app_store is not None else _app_store(),
        homebrew=homebrew if homebrew is not None else _homebrew(),
        auto_update=auto_update if auto_update is not None else _auto_update(),
        blocklist=blocklist if blocklist is not None else _blocklist(),
    )


class TestClassifyRecordAttention:
    def test_all_quiet_is_attention(self) -> None:
        classification = classify_record(_make_record())

        assert classification.bucket == AuditBucket.ATTENTION

    def test_homebrew_available_stays_attention_eligible(self) -> None:
        """Regression: the classification bug caught during design review --
        only MANAGED should exclude from attention, not "!= NOT_AVAILABLE",
        which would have wrongly excluded a future AVAILABLE result."""
        record = _make_record(homebrew=_homebrew(status=HomebrewStatus.AVAILABLE, reason="cask 'foo' available"))

        classification = classify_record(record)

        assert classification.bucket == AuditBucket.ATTENTION
        assert "remediation suggestion" in classification.why


class TestClassifyRecordManaged:
    def test_app_store_managed(self) -> None:
        record = _make_record(app_store=_app_store(status=AppStoreStatus.APP_STORE))

        classification = classify_record(record)

        assert classification.bucket == AuditBucket.MANAGED
        assert "App Store" in classification.why

    def test_homebrew_managed(self) -> None:
        record = _make_record(homebrew=_homebrew(status=HomebrewStatus.MANAGED, token="firefox"))

        classification = classify_record(record)

        assert classification.bucket == AuditBucket.MANAGED
        assert "firefox" in classification.why

    def test_auto_update_enabled(self) -> None:
        classification = classify_record(_make_record(auto_update=_auto_update(status=AutoUpdateStatus.ENABLED)))

        assert classification.bucket == AuditBucket.MANAGED

    def test_auto_update_capable(self) -> None:
        classification = classify_record(_make_record(auto_update=_auto_update(status=AutoUpdateStatus.CAPABLE)))

        assert classification.bucket == AuditBucket.MANAGED

    def test_blocklisted(self) -> None:
        record = _make_record(
            blocklist=_blocklist(status=BlocklistStatus.BLOCKED, matched_by=BlocklistMatchKind.DISPLAY_NAME)
        )

        classification = classify_record(record)

        assert classification.bucket == AuditBucket.MANAGED
        assert "blocklisted" in classification.why.lower()


class TestClassifyRecordUnknown:
    def test_app_store_unknown(self) -> None:
        record = _make_record(app_store=_app_store(status=AppStoreStatus.UNKNOWN, error="probe failed"))

        classification = classify_record(record)

        assert classification.bucket == AuditBucket.UNKNOWN
        assert "app_store" in classification.why
        assert "probe failed" in classification.why

    def test_homebrew_unknown(self) -> None:
        record = _make_record(homebrew=_homebrew(status=HomebrewStatus.UNKNOWN, error="brew missing"))

        assert classify_record(record).bucket == AuditBucket.UNKNOWN

    def test_auto_update_unknown(self) -> None:
        record = _make_record(auto_update=_auto_update(status=AutoUpdateStatus.UNKNOWN, error="permission denied"))

        assert classify_record(record).bucket == AuditBucket.UNKNOWN

    def test_blocklist_unknown(self) -> None:
        record = _make_record(blocklist=_blocklist(status=BlocklistStatus.UNKNOWN, error="config malformed"))

        assert classify_record(record).bucket == AuditBucket.UNKNOWN

    def test_not_evaluated_treated_as_unknown(self) -> None:
        record = _make_record(auto_update=AutoUpdateEvidence.not_evaluated())

        assert classify_record(record).bucket == AuditBucket.UNKNOWN

    def test_blocked_plus_different_axis_unknown_is_unknown_not_managed(self) -> None:
        """Precedence case surfaced during design review: an unconditional
        UNKNOWN axis must win even alongside a confident BLOCKED elsewhere.
        The blocklist match itself is never lost -- it's still on
        record.blocklist regardless of which bucket the record lands in."""
        record = _make_record(
            blocklist=_blocklist(status=BlocklistStatus.BLOCKED, matched_by=BlocklistMatchKind.BUNDLE_ID),
            auto_update=_auto_update(status=AutoUpdateStatus.UNKNOWN, error="permission denied"),
        )

        classification = classify_record(record)

        assert classification.bucket == AuditBucket.UNKNOWN
        assert record.blocklist.status == BlocklistStatus.BLOCKED


class TestFetchSystemProfilerData:
    def test_success_returns_data(self, monkeypatch) -> None:
        monkeypatch.setattr(service_module, "get_json_data", lambda cmd: {"SPApplicationsDataType": []})

        assert service_module._fetch_system_profiler_data() == {"SPApplicationsDataType": []}

    def test_failure_degrades_to_none(self, monkeypatch) -> None:
        def raise_error(cmd: str) -> None:
            raise Exception("simulated failure")

        monkeypatch.setattr(service_module, "get_json_data", raise_error)

        assert service_module._fetch_system_profiler_data() is None


class TestRunAuditOrchestration:
    def _patch_pipeline(self, monkeypatch, call_order: list[str]) -> None:
        def fake_discover(**kwargs: object) -> list[ApplicationRecord]:
            call_order.append("discover")
            return []

        def fake_homebrew(records: list[ApplicationRecord]) -> list[ApplicationRecord]:
            call_order.append("homebrew")
            return records

        def fake_blocklist(
            records: list[ApplicationRecord], blocklist_entries: object = None
        ) -> list[ApplicationRecord]:
            call_order.append("blocklist")
            return records

        def fake_auto_update(
            records: list[ApplicationRecord], launch_agent_dirs: object = None
        ) -> list[ApplicationRecord]:
            call_order.append("auto_update")
            return records

        monkeypatch.setattr(service_module, "discover_applications", fake_discover)
        monkeypatch.setattr(service_module, "apply_homebrew_evidence", fake_homebrew)
        monkeypatch.setattr(service_module, "apply_blocklist_evidence", fake_blocklist)
        monkeypatch.setattr(service_module, "apply_auto_update_evidence", fake_auto_update)

    def test_calls_resolvers_in_correct_order(self, monkeypatch) -> None:
        """Homebrew must resolve before BOTH blocklist and auto-update."""
        call_order: list[str] = []
        self._patch_pipeline(monkeypatch, call_order)
        monkeypatch.setattr(service_module, "_fetch_system_profiler_data", lambda: None)

        run_audit()

        assert call_order[0] == "discover"
        assert call_order.index("homebrew") < call_order.index("blocklist")
        assert call_order.index("homebrew") < call_order.index("auto_update")

    def test_explicit_system_profiler_data_skips_fetch(self, monkeypatch) -> None:
        call_order: list[str] = []
        self._patch_pipeline(monkeypatch, call_order)
        fetch_called = []
        monkeypatch.setattr(service_module, "_fetch_system_profiler_data", lambda: fetch_called.append(True))

        run_audit(system_profiler_data={"SPApplicationsDataType": []})

        assert fetch_called == []

    def test_none_system_profiler_data_triggers_fetch(self, monkeypatch) -> None:
        call_order: list[str] = []
        self._patch_pipeline(monkeypatch, call_order)
        fetch_called = []

        def fake_fetch() -> None:
            fetch_called.append(True)
            return None

        monkeypatch.setattr(service_module, "_fetch_system_profiler_data", fake_fetch)

        run_audit()

        assert fetch_called == [True]

    def test_summary_counts_match_classifications(self, monkeypatch) -> None:
        records = [
            _make_record(name="Attention", canonical_path=Path("/Applications/Attention.app")),
            _make_record(
                name="Managed",
                canonical_path=Path("/Applications/Managed.app"),
                app_store=_app_store(status=AppStoreStatus.APP_STORE),
            ),
            _make_record(
                name="Unknown",
                canonical_path=Path("/Applications/Unknown.app"),
                app_store=_app_store(status=AppStoreStatus.UNKNOWN, error="probe failed"),
            ),
        ]
        monkeypatch.setattr(service_module, "discover_applications", lambda **kwargs: records)
        monkeypatch.setattr(service_module, "apply_homebrew_evidence", lambda r: r)
        monkeypatch.setattr(service_module, "apply_blocklist_evidence", lambda r, blocklist_entries=None: r)
        monkeypatch.setattr(service_module, "apply_auto_update_evidence", lambda r, launch_agent_dirs=None: r)
        monkeypatch.setattr(service_module, "_fetch_system_profiler_data", lambda: None)

        result = run_audit()

        assert result.summary == {"total": 3, "attention": 1, "managed": 1, "unknown": 1}
        assert len(result.applications) == 3


class TestPipelineOrderIntegration:
    """Real on-disk bundles, real discover_applications()/apply_blocklist_evidence()/
    apply_auto_update_evidence() -- only fetch_installed_casks is mocked.
    These prove the load-bearing pipeline order end-to-end, not just that
    the resolver functions are *called* in order."""

    def test_homebrew_auto_updates_supplement_requires_homebrew_first(
        self, monkeypatch, tmp_path, app_bundle_factory, cask_factory, installed_casks_payload_factory
    ) -> None:
        bundle = app_bundle_factory(tmp_path, "ManagedApp")
        payload = installed_casks_payload_factory(
            cask_factory("managedapp", app_name="ManagedApp.app", app_target=str(bundle), auto_updates=True)
        )
        monkeypatch.setattr(homebrew_module, "run_command_secure", lambda *a, **k: (json.dumps(payload), 0))
        monkeypatch.setattr(homebrew_module, "get_brew_command", lambda: "/opt/homebrew/bin/brew")
        empty_launch_agent_dir = tmp_path / "EmptyLaunchAgents"
        empty_launch_agent_dir.mkdir()

        result = run_audit(
            roots=[tmp_path],
            system_profiler_data={"SPApplicationsDataType": []},
            launch_agent_dirs=[empty_launch_agent_dir],
        )

        app = next(a for a in result.applications if a.record.name == "ManagedApp")
        assert app.record.homebrew.status == HomebrewStatus.MANAGED
        assert app.record.auto_update.status == AutoUpdateStatus.CAPABLE

    def test_blocklist_by_homebrew_token_requires_homebrew_first(
        self, monkeypatch, tmp_path, app_bundle_factory, cask_factory, installed_casks_payload_factory
    ) -> None:
        bundle = app_bundle_factory(tmp_path, "BlockedApp")
        payload = installed_casks_payload_factory(
            cask_factory("blockedapp", app_name="BlockedApp.app", app_target=str(bundle))
        )
        monkeypatch.setattr(homebrew_module, "run_command_secure", lambda *a, **k: (json.dumps(payload), 0))
        monkeypatch.setattr(homebrew_module, "get_brew_command", lambda: "/opt/homebrew/bin/brew")
        empty_launch_agent_dir = tmp_path / "EmptyLaunchAgents"
        empty_launch_agent_dir.mkdir()

        result = run_audit(
            roots=[tmp_path],
            system_profiler_data={"SPApplicationsDataType": []},
            launch_agent_dirs=[empty_launch_agent_dir],
            blocklist_entries=["blockedapp"],
        )

        app = next(a for a in result.applications if a.record.name == "BlockedApp")
        assert app.record.homebrew.status == HomebrewStatus.MANAGED
        assert app.record.blocklist.status == BlocklistStatus.BLOCKED


class TestFilterResult:
    def _make_result(self) -> AuditResult:
        attention_app = ClassifiedApplication(
            record=_make_record(name="Attention"),
            classification=AuditClassification(bucket=AuditBucket.ATTENTION, why="test"),
        )
        unknown_app = ClassifiedApplication(
            record=_make_record(name="Unknown"),
            classification=AuditClassification(bucket=AuditBucket.UNKNOWN, why="test"),
        )
        managed_app = ClassifiedApplication(
            record=_make_record(name="Managed"),
            classification=AuditClassification(bucket=AuditBucket.MANAGED, why="test"),
        )
        summary = {"total": 3, "attention": 1, "unknown": 1, "managed": 1}
        return AuditResult(applications=(attention_app, unknown_app, managed_app), summary=summary)

    def test_default_shows_attention_and_unknown_only(self) -> None:
        result = self._make_result()

        filtered = filter_result(result, show_all=False, status=None)

        assert {app.record.name for app in filtered.applications} == {"Attention", "Unknown"}
        assert filtered.summary == result.summary

    def test_all_shows_everything(self) -> None:
        result = self._make_result()

        filtered = filter_result(result, show_all=True, status=None)

        assert len(filtered.applications) == 3
        assert filtered.summary == result.summary

    def test_status_filters_to_exactly_one_bucket(self) -> None:
        result = self._make_result()

        filtered = filter_result(result, show_all=False, status=AuditBucket.MANAGED)

        assert {app.record.name for app in filtered.applications} == {"Managed"}
        assert filtered.summary == result.summary
