"""Tests for versiontracker.handlers.audit_handlers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

import versiontracker.handlers.audit_handlers as audit_handlers_module
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
    BlocklistStatus,
    ClassifiedApplication,
    EvidenceSource,
    HomebrewEvidence,
    HomebrewStatus,
)
from versiontracker.handlers.audit_handlers import handle_audit


def _make_options(**overrides: object) -> Mock:
    options = Mock()
    options.additional_dirs = None
    options.blocklist = None
    options.blacklist = None
    options.all = False
    options.status = None
    options.explain = False
    options.export_format = None
    options.output_file = None
    for key, value in overrides.items():
        setattr(options, key, value)
    return options


def _make_result(bucket: AuditBucket = AuditBucket.ATTENTION) -> AuditResult:
    path = Path("/Applications/Firefox.app")
    record = ApplicationRecord(
        name="Firefox",
        version="120.0",
        path=path,
        canonical_path=path,
        bundle_id="org.mozilla.firefox",
        obtained_from=None,
        parent_bundle_path=None,
        app_store=AppStoreEvidence(
            status=AppStoreStatus.NOT_APP_STORE, reason="test", source=EvidenceSource.SYSTEM_PROFILER
        ),
        homebrew=HomebrewEvidence(
            status=HomebrewStatus.NOT_AVAILABLE, reason="test", source=EvidenceSource.HOMEBREW_CLI
        ),
        auto_update=AutoUpdateEvidence(
            status=AutoUpdateStatus.NONE_DETECTED, reason="test", source=EvidenceSource.FILESYSTEM
        ),
        blocklist=BlocklistEvidence(status=BlocklistStatus.NOT_BLOCKED, reason="test", source=EvidenceSource.CONFIG),
    )
    app = ClassifiedApplication(record=record, classification=AuditClassification(bucket=bucket, why="test why"))
    summary = {"total": 1, "attention": 0, "unknown": 0, "managed": 0}
    summary[bucket.value] = 1
    return AuditResult(applications=(app,), summary=summary)


class TestHandleAuditTerminalOutput:
    def test_default_prints_terminal_sections(self, monkeypatch, capsys) -> None:
        monkeypatch.setattr(audit_handlers_module, "run_audit", lambda **kwargs: _make_result())

        exit_code = handle_audit(_make_options())

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Needs manual management" in captured.out
        assert "Firefox" in captured.out


class TestHandleAuditExport:
    def test_export_json_prints_only_json(self, monkeypatch, capsys) -> None:
        monkeypatch.setattr(audit_handlers_module, "run_audit", lambda **kwargs: _make_result())

        exit_code = handle_audit(_make_options(export_format="json"))

        assert exit_code == 0
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)  # raises if anything else was printed alongside it
        assert parsed["schema_version"] == 1

    def test_export_with_output_file_writes_file_and_prints_confirmation_only(
        self, monkeypatch, capsys, tmp_path
    ) -> None:
        monkeypatch.setattr(audit_handlers_module, "run_audit", lambda **kwargs: _make_result())
        output_file = tmp_path / "audit.json"

        exit_code = handle_audit(_make_options(export_format="json", output_file=str(output_file)))

        assert exit_code == 0
        assert output_file.exists()
        content = json.loads(output_file.read_text())
        assert content["schema_version"] == 1
        captured = capsys.readouterr()
        assert "Exported" in captured.out
        with pytest.raises(json.JSONDecodeError):
            json.loads(captured.out)  # a confirmation line, not the export content itself

    def test_export_output_file_write_failure_returns_error(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setattr(audit_handlers_module, "run_audit", lambda **kwargs: _make_result())
        unwritable_path = tmp_path / "does-not-exist" / "audit.json"

        exit_code = handle_audit(_make_options(export_format="json", output_file=str(unwritable_path)))

        assert exit_code == 1
        assert not unwritable_path.exists()

    def test_export_unsupported_format_returns_error(self, monkeypatch) -> None:
        monkeypatch.setattr(audit_handlers_module, "run_audit", lambda **kwargs: _make_result())

        exit_code = handle_audit(_make_options(export_format="xml"))

        assert exit_code == 1

    def test_export_yaml_and_csv_also_work(self, monkeypatch) -> None:
        monkeypatch.setattr(audit_handlers_module, "run_audit", lambda **kwargs: _make_result())

        assert handle_audit(_make_options(export_format="yaml")) == 0
        assert handle_audit(_make_options(export_format="csv")) == 0


class TestAdditionalDirsParsing:
    def test_colon_separated_dirs_passed_as_extra_roots(self, monkeypatch) -> None:
        captured_kwargs: dict[str, Any] = {}

        def fake_run_audit(**kwargs: Any) -> AuditResult:
            captured_kwargs.update(kwargs)
            return _make_result()

        monkeypatch.setattr(audit_handlers_module, "run_audit", fake_run_audit)

        handle_audit(_make_options(additional_dirs="/path/one:/path/two"))

        assert captured_kwargs["extra_roots"] == ["/path/one", "/path/two"]

    def test_no_additional_dirs_is_none(self, monkeypatch) -> None:
        captured_kwargs: dict[str, Any] = {}

        def fake_run_audit(**kwargs: object) -> AuditResult:
            captured_kwargs.update(kwargs)
            return _make_result()

        monkeypatch.setattr(audit_handlers_module, "run_audit", fake_run_audit)

        handle_audit(_make_options())

        assert captured_kwargs["extra_roots"] is None


class TestBlocklistMerging:
    def test_config_and_cli_blocklist_both_apply(self, monkeypatch) -> None:
        """Merge, not override -- per the spec's explicit merge-semantics
        requirement for an audit filter."""
        mock_config = Mock()
        mock_config.get_blocklist.return_value = ["Little Snitch"]
        monkeypatch.setattr(audit_handlers_module, "get_config", lambda: mock_config)
        captured_kwargs: dict[str, Any] = {}

        def fake_run_audit(**kwargs: object) -> AuditResult:
            captured_kwargs.update(kwargs)
            return _make_result()

        monkeypatch.setattr(audit_handlers_module, "run_audit", fake_run_audit)

        handle_audit(_make_options(blocklist="Visual Studio Code,Firefox"))

        entries = captured_kwargs["blocklist_entries"]
        assert "Little Snitch" in entries
        assert "Visual Studio Code" in entries
        assert "Firefox" in entries

    def test_deduplicates_entries(self, monkeypatch) -> None:
        mock_config = Mock()
        mock_config.get_blocklist.return_value = ["Firefox"]
        monkeypatch.setattr(audit_handlers_module, "get_config", lambda: mock_config)
        captured_kwargs: dict[str, Any] = {}

        def fake_run_audit(**kwargs: object) -> AuditResult:
            captured_kwargs.update(kwargs)
            return _make_result()

        monkeypatch.setattr(audit_handlers_module, "run_audit", fake_run_audit)

        handle_audit(_make_options(blocklist="Firefox"))

        assert captured_kwargs["blocklist_entries"].count("Firefox") == 1


class TestStatusAndAllFiltering:
    def test_status_option_converted_to_audit_bucket(self, monkeypatch) -> None:
        captured_kwargs: dict[str, Any] = {}

        def fake_filter_result(result: AuditResult, **kwargs: object) -> AuditResult:
            captured_kwargs.update(kwargs)
            return result

        monkeypatch.setattr(audit_handlers_module, "run_audit", lambda **kwargs: _make_result())
        monkeypatch.setattr(audit_handlers_module, "filter_result", fake_filter_result)

        handle_audit(_make_options(status="managed"))

        assert captured_kwargs["status"] == AuditBucket.MANAGED
        assert captured_kwargs["show_all"] is False

    def test_all_option_passed_through(self, monkeypatch) -> None:
        captured_kwargs: dict[str, Any] = {}

        def fake_filter_result(result: AuditResult, **kwargs: object) -> AuditResult:
            captured_kwargs.update(kwargs)
            return result

        monkeypatch.setattr(audit_handlers_module, "run_audit", lambda **kwargs: _make_result())
        monkeypatch.setattr(audit_handlers_module, "filter_result", fake_filter_result)

        handle_audit(_make_options(all=True))

        assert captured_kwargs["show_all"] is True
        assert captured_kwargs["status"] is None
