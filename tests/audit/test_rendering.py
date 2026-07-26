"""Tests for versiontracker.audit.rendering."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import yaml

from versiontracker.audit.models import (
    ApplicationRecord,
    AppStoreEvidence,
    AppStoreStatus,
    AuditBucket,
    AuditClassification,
    AuditResult,
    AutoUpdateEvidence,
    AutoUpdateMechanism,
    AutoUpdateStatus,
    BlocklistEvidence,
    BlocklistMatchKind,
    BlocklistStatus,
    ClassifiedApplication,
    EvidenceSource,
    HomebrewEvidence,
    HomebrewStatus,
)
from versiontracker.audit.rendering import render_csv, render_json, render_terminal, render_yaml


def _record(
    *,
    name: str = "Firefox",
    canonical_path: Path | None = None,
    bundle_id: str | None = "org.mozilla.firefox",
    app_store_status: AppStoreStatus = AppStoreStatus.NOT_APP_STORE,
    homebrew_status: HomebrewStatus = HomebrewStatus.NOT_AVAILABLE,
    auto_update_status: AutoUpdateStatus = AutoUpdateStatus.NONE_DETECTED,
    blocklist_status: BlocklistStatus = BlocklistStatus.NOT_BLOCKED,
) -> ApplicationRecord:
    path = canonical_path if canonical_path is not None else Path(f"/Applications/{name}.app")
    return ApplicationRecord(
        name=name,
        version="120.0",
        path=path,
        canonical_path=path,
        bundle_id=bundle_id,
        obtained_from=None,
        parent_bundle_path=None,
        app_store=AppStoreEvidence(
            status=app_store_status, reason="app store reason", source=EvidenceSource.SYSTEM_PROFILER
        ),
        homebrew=HomebrewEvidence(
            status=homebrew_status,
            reason="homebrew reason",
            source=EvidenceSource.HOMEBREW_CLI,
            matched_identifier="firefox" if homebrew_status == HomebrewStatus.MANAGED else None,
        ),
        auto_update=AutoUpdateEvidence(
            status=auto_update_status,
            reason="auto-update reason",
            source=EvidenceSource.FILESYSTEM,
            mechanisms=(AutoUpdateMechanism.SPARKLE_FRAMEWORK,)
            if auto_update_status != AutoUpdateStatus.NONE_DETECTED
            else (),
        ),
        blocklist=BlocklistEvidence(
            status=blocklist_status,
            reason="blocklist reason",
            source=EvidenceSource.CONFIG,
            matched_by=BlocklistMatchKind.DISPLAY_NAME if blocklist_status == BlocklistStatus.BLOCKED else None,
        ),
    )


def _classified(record: ApplicationRecord, bucket: AuditBucket, why: str = "test why") -> ClassifiedApplication:
    return ClassifiedApplication(record=record, classification=AuditClassification(bucket=bucket, why=why))


def _result(*classified_apps: ClassifiedApplication) -> AuditResult:
    summary = {"total": len(classified_apps), "attention": 0, "unknown": 0, "managed": 0}
    for app in classified_apps:
        summary[app.classification.bucket.value] += 1
    return AuditResult(applications=tuple(classified_apps), summary=summary)


class TestRenderTerminal:
    def test_compact_table_shows_expected_columns(self) -> None:
        result = _result(_classified(_record(), AuditBucket.ATTENTION))

        output = render_terminal(result, explain=False)

        assert "Needs manual management" in output
        assert "Firefox" in output
        assert "120.0" in output
        assert "Summary" in output

    def test_explain_shows_full_evidence_per_axis(self) -> None:
        result = _result(_classified(_record(), AuditBucket.ATTENTION))

        output = render_terminal(result, explain=True)

        assert "app store reason" in output
        assert "homebrew reason" in output
        assert "auto-update reason" in output
        assert "blocklist reason" in output
        assert "source=" in output
        assert "confidence=" in output

    def test_unknown_section_shown_when_present(self) -> None:
        result = _result(_classified(_record(name="Unknown App"), AuditBucket.UNKNOWN))

        output = render_terminal(result, explain=False)

        assert "Needs review (unknown evidence)" in output
        assert "Needs manual management" not in output

    def test_managed_section_absent_when_not_in_result(self) -> None:
        """render_terminal only groups what it's given -- excluding managed
        apps from the default view is filter_result's job (see
        TestFilterResult in test_service.py), not render_terminal's; this
        just confirms no stray "Managed" section header leaks in when there
        are no managed apps in the (already-filtered) input."""
        result = _result(_classified(_record(name="Attention App"), AuditBucket.ATTENTION))

        output = render_terminal(result, explain=False)

        assert "Needs manual management" in output
        assert "Managed\n" not in output

    def test_managed_section_shown_when_present(self) -> None:
        """A regression test for a real bug: `--status managed` (show_all=False,
        status=MANAGED) filters `result.applications` down to managed apps
        only, so render_terminal must show them even though show_all=False
        -- gating on show_all here previously produced an empty list."""
        result = _result(_classified(_record(name="Managed App"), AuditBucket.MANAGED))

        output = render_terminal(result, explain=False)

        assert "Managed App" in output

    def test_summary_always_present_even_when_empty(self) -> None:
        output = render_terminal(_result(), explain=False)

        assert "Summary" in output


class TestRenderJson:
    def test_schema_and_summary(self) -> None:
        result = _result(_classified(_record(), AuditBucket.ATTENTION))

        parsed = json.loads(render_json(result))

        assert parsed["schema_version"] == 1
        assert parsed["summary"] == result.summary
        assert len(parsed["applications"]) == 1

    def test_full_evidence_present(self) -> None:
        result = _result(_classified(_record(homebrew_status=HomebrewStatus.MANAGED), AuditBucket.MANAGED))

        app_dict = json.loads(render_json(result))["applications"][0]

        assert app_dict["app_store"]["status"] == "not_app_store"
        assert app_dict["homebrew"]["status"] == "managed"
        assert app_dict["homebrew"]["matched_identifier"] == "firefox"
        assert app_dict["classification"] == "managed"
        assert "why" in app_dict

    def test_path_and_none_serialize_correctly(self) -> None:
        result = _result(_classified(_record(canonical_path=Path("/Applications/Firefox.app")), AuditBucket.ATTENTION))

        app_dict = json.loads(render_json(result))["applications"][0]

        assert app_dict["canonical_path"] == "/Applications/Firefox.app"
        assert app_dict["obtained_from"] is None
        assert app_dict["parent_bundle_path"] is None

    def test_tuple_fields_serialize_as_lists(self) -> None:
        result = _result(_classified(_record(auto_update_status=AutoUpdateStatus.CAPABLE), AuditBucket.MANAGED))

        app_dict = json.loads(render_json(result))["applications"][0]

        assert app_dict["auto_update"]["mechanisms"] == ["sparkle_framework"]
        assert isinstance(app_dict["diagnostics"], list)


class TestRenderYaml:
    def test_round_trips_and_matches_json_shape(self) -> None:
        result = _result(_classified(_record(), AuditBucket.ATTENTION))

        assert yaml.safe_load(render_yaml(result)) == json.loads(render_json(result))

    def test_schema_version_is_first_key(self) -> None:
        result = _result(_classified(_record(), AuditBucket.ATTENTION))

        assert render_yaml(result).strip().startswith("schema_version:")


class TestRenderCsv:
    def test_header_and_row_count(self) -> None:
        result = _result(
            _classified(_record(name="App1"), AuditBucket.ATTENTION),
            _classified(_record(name="App2"), AuditBucket.MANAGED),
        )

        rows = list(csv.DictReader(io.StringIO(render_csv(result))))

        assert len(rows) == 2
        assert rows[0]["name"] == "App1"

    def test_empty_result_produces_header_only(self) -> None:
        output = render_csv(_result())

        rows = list(csv.DictReader(io.StringIO(output)))

        assert rows == []
        assert "name" in output
        assert "app_store_status" in output

    def test_evidence_fields_flattened_with_prefix(self) -> None:
        result = _result(_classified(_record(homebrew_status=HomebrewStatus.MANAGED), AuditBucket.MANAGED))

        rows = list(csv.DictReader(io.StringIO(render_csv(result))))

        assert rows[0]["homebrew_status"] == "managed"
        assert rows[0]["homebrew_matched_identifier"] == "firefox"

    def test_none_values_become_empty_string(self) -> None:
        result = _result(_classified(_record(), AuditBucket.ATTENTION))

        rows = list(csv.DictReader(io.StringIO(render_csv(result))))

        assert rows[0]["obtained_from"] == ""

    def test_list_values_semicolon_joined(self) -> None:
        result = _result(_classified(_record(auto_update_status=AutoUpdateStatus.CAPABLE), AuditBucket.MANAGED))

        rows = list(csv.DictReader(io.StringIO(render_csv(result))))

        assert rows[0]["auto_update_mechanisms"] == "sparkle_framework"
