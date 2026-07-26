"""Terminal rendering and versioned JSON/YAML/CSV export for audit results.

Every function here is pure -- takes an AuditResult, returns a str. None of
them print anything; printing is exclusively versiontracker.handlers.
audit_handlers.handle_audit()'s job, extending the Phase 1-3 rule that
library code never touches stdout into Phase 4.
"""

from __future__ import annotations

import csv
import dataclasses
import io
import json
from collections.abc import Sequence
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from tabulate import tabulate

from versiontracker.audit.models import (
    AppStoreEvidence,
    AuditBucket,
    AuditResult,
    AutoUpdateEvidence,
    BlocklistEvidence,
    ClassifiedApplication,
    HomebrewEvidence,
)

_SCHEMA_VERSION = 1
_EVIDENCE_GROUPS: tuple[tuple[str, type], ...] = (
    ("app_store", AppStoreEvidence),
    ("homebrew", HomebrewEvidence),
    ("auto_update", AutoUpdateEvidence),
    ("blocklist", BlocklistEvidence),
)


def _to_json_safe(value: Any) -> Any:
    """Recursively convert dataclasses/Enums/Paths/tuples into JSON-safe values.

    Handles ApplicationRecord and every Evidence type generically (via
    dataclasses.fields()) rather than hand-listing each type's fields --
    the field sets genuinely differ per Evidence type (installed_version/
    artifact_target/cask_auto_updates on Homebrew, mechanisms on
    auto-update, matched_by on blocklist), and a generic walk can't drift
    out of sync when a new field is added to any of them.
    """
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _to_json_safe(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple | list):
        return [_to_json_safe(v) for v in value]
    return value


def _result_to_dict(result: AuditResult) -> dict[str, Any]:
    """Shared builder for render_json/render_yaml.

    Keeps the two formats from ever drifting apart, since both call this
    exactly once.
    """
    applications = []
    for app in result.applications:
        app_dict = _to_json_safe(app.record)
        app_dict["classification"] = app.classification.bucket.value
        app_dict["why"] = app.classification.why
        applications.append(app_dict)
    return {
        "schema_version": _SCHEMA_VERSION,
        "summary": dict(result.summary),
        "applications": applications,
    }


def render_json(result: AuditResult) -> str:
    """Full evidence for every application, regardless of --explain.

    The spec states this as an unconditional export property, and keeping
    the shape independent of --explain keeps the versioned schema stable
    for any script parsing it.
    """
    return json.dumps(_result_to_dict(result), indent=2)


def render_yaml(result: AuditResult) -> str:
    """Same shape as render_json via the same shared builder."""
    return yaml.safe_dump(_result_to_dict(result), sort_keys=False, default_flow_style=False)


def _csv_fieldnames() -> list[str]:
    """Derived from the model classes themselves, not from any instance.

    This way an empty result still produces a correct header-only CSV.
    """
    fields = [
        "name",
        "version",
        "path",
        "canonical_path",
        "bundle_id",
        "obtained_from",
        "parent_bundle_path",
        "diagnostics",
        "classification",
        "why",
    ]
    for group_name, evidence_cls in _EVIDENCE_GROUPS:
        fields.extend(f"{group_name}_{f.name}" for f in dataclasses.fields(evidence_cls))
    return fields


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ";".join(str(v) for v in value)
    return str(value)


def _flatten_application(app: ClassifiedApplication) -> dict[str, str]:
    record_dict = _to_json_safe(app.record)
    row: dict[str, str] = {
        "name": _csv_cell(record_dict["name"]),
        "version": _csv_cell(record_dict["version"]),
        "path": _csv_cell(record_dict["path"]),
        "canonical_path": _csv_cell(record_dict["canonical_path"]),
        "bundle_id": _csv_cell(record_dict["bundle_id"]),
        "obtained_from": _csv_cell(record_dict["obtained_from"]),
        "parent_bundle_path": _csv_cell(record_dict["parent_bundle_path"]),
        "diagnostics": _csv_cell(record_dict["diagnostics"]),
        "classification": app.classification.bucket.value,
        "why": app.classification.why,
    }
    for group_name, _evidence_cls in _EVIDENCE_GROUPS:
        for field_name, value in record_dict[group_name].items():
            row[f"{group_name}_{field_name}"] = _csv_cell(value)
    return row


def render_csv(result: AuditResult) -> str:
    """One row per application, one column per evidence field, prefixed by group.

    E.g. app_store_status, homebrew_installed_version, .... No standard
    place for schema_version in CSV -- the column list itself is the
    contract.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_csv_fieldnames())
    writer.writeheader()
    for app in result.applications:
        writer.writerow(_flatten_application(app))
    return output.getvalue()


def _render_compact_table(applications: Sequence[ClassifiedApplication]) -> str:
    rows = [
        [
            app.record.name,
            app.record.version,
            app.record.app_store.status.value,
            app.record.homebrew.status.value,
            app.record.auto_update.status.value,
            app.classification.why,
        ]
        for app in applications
    ]
    return str(
        tabulate(
            rows, headers=["Application", "Version", "App Store", "Homebrew", "Auto-update", "Why"], tablefmt="pretty"
        )
    )


def _render_explain_block(app: ClassifiedApplication) -> str:
    record = app.record
    lines = [f"{record.name} ({record.version}) -- {app.classification.bucket.value}: {app.classification.why}"]
    for label, evidence in (
        ("App Store", record.app_store),
        ("Homebrew", record.homebrew),
        ("Auto-update", record.auto_update),
        ("Blocklist", record.blocklist),
    ):
        lines.append(
            f"  {label}: {evidence.status.value} -- {evidence.reason} "
            f"[source={evidence.source.value}, confidence={evidence.confidence.value}]"
        )
    return "\n".join(lines)


def _render_section(title: str, applications: Sequence[ClassifiedApplication], *, explain: bool) -> str:
    if explain:
        body = "\n".join(_render_explain_block(app) for app in applications)
    else:
        body = _render_compact_table(applications)
    return f"{title}\n{body}"


def _render_summary(summary: dict[str, int]) -> str:
    return (
        "Summary\n"
        f"  Total: {summary['total']}  Attention: {summary['attention']}  "
        f"Unknown: {summary['unknown']}  Managed: {summary['managed']}"
    )


def render_terminal(result: AuditResult, *, explain: bool) -> str:
    """Render sections: attention / unknown / managed / summary.

    Each section is shown exactly when `result` (already filtered by
    service.py::filter_result) contains an application for it. This
    function only groups whatever it's given by each application's own
    classification; it never re-applies filtering itself, so e.g.
    `--status managed` correctly shows every managed application without
    also needing `--all`.
    """
    attention = [app for app in result.applications if app.classification.bucket == AuditBucket.ATTENTION]
    unknown = [app for app in result.applications if app.classification.bucket == AuditBucket.UNKNOWN]
    managed = [app for app in result.applications if app.classification.bucket == AuditBucket.MANAGED]

    sections: list[str] = []
    if attention:
        sections.append(_render_section("Needs manual management", attention, explain=explain))
    if unknown:
        sections.append(_render_section("Needs review (unknown evidence)", unknown, explain=explain))
    if managed:
        sections.append(_render_section("Managed", managed, explain=explain))
    sections.append(_render_summary(result.summary))

    return "\n\n".join(sections)
