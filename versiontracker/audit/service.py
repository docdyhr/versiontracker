"""Audit orchestration: discover once, resolve every evidence axis, classify.

`run_audit()` is the single entry point that wires Phases 1-3 together in
the order that matters: discovery (with real system_profiler enrichment)
first, then Homebrew ownership, then blocklist and auto-update -- both of
which read already-resolved Homebrew evidence off each record, so Homebrew
must land before either. Blocklist and auto-update don't read each other,
so their relative order doesn't matter.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from versiontracker.audit.auto_update import apply_auto_update_evidence
from versiontracker.audit.blocklist import apply_blocklist_evidence
from versiontracker.audit.discovery import discover_applications
from versiontracker.audit.homebrew import apply_homebrew_evidence
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
    HomebrewEvidence,
    HomebrewStatus,
)
from versiontracker.config import get_config
from versiontracker.utils import get_json_data

_UNKNOWN_STATUS_VALUES = frozenset({"unknown", "not_evaluated"})


def _fetch_system_profiler_data() -> dict[str, Any] | None:
    """Fetch real system_profiler data for App Store obtained_from enrichment.

    Never raises -- returns None on any failure, which discover_applications()
    already handles gracefully (App Store evidence falls back to the
    MASReceipt-only signal, per discovery.py's own resolve_app_store_evidence
    truth table). Deliberately catches Exception broadly rather than a
    curated tuple: the same lesson already learned for plistlib (a narrower
    guess at "every way this can fail" previously missed a real exception
    type) applies equally to a subprocess+JSON fetch.
    """
    try:
        command = get_config().get("system_profiler_cmd", "system_profiler -json SPApplicationsDataType")
        return get_json_data(command)
    except Exception as e:
        logging.warning("Could not fetch system_profiler data for App Store enrichment: %s", e)
        return None


def classify_record(record: ApplicationRecord) -> AuditClassification:
    """Classify one record into attention / unknown / managed.

    Any evidence axis with status "unknown" or "not_evaluated" (checking
    the string value works uniformly across all four distinct enums, each
    has a member literally valued "unknown") puts the record in UNKNOWN,
    unconditionally -- even alongside a confident BLOCKED on a different
    axis, per the spec's unqualified "applications with incomplete or
    failed evidence belong in a separate unknown/needs_review section."

    Otherwise ATTENTION requires all four signals to be quiet:
    app_store != APP_STORE, homebrew != MANAGED (not "== NOT_AVAILABLE" --
    a future AVAILABLE result must stay attention-eligible too, since only
    MANAGED denotes real ownership; AVAILABLE is a remediation suggestion,
    not exclusion), auto_update not in (ENABLED, CAPABLE), blocklist !=
    BLOCKED. Otherwise MANAGED, with `why` naming every excluding signal.
    """
    axes: dict[str, AppStoreEvidence | HomebrewEvidence | AutoUpdateEvidence | BlocklistEvidence] = {
        "app_store": record.app_store,
        "homebrew": record.homebrew,
        "auto_update": record.auto_update,
        "blocklist": record.blocklist,
    }
    unknown_axes = [name for name, evidence in axes.items() if evidence.status.value in _UNKNOWN_STATUS_VALUES]
    if unknown_axes:
        parts = []
        for name in unknown_axes:
            evidence = axes[name]
            detail = f"{name}: {evidence.status.value}"
            if evidence.error:
                detail += f" ({evidence.error})"
            parts.append(detail)
        return AuditClassification(bucket=AuditBucket.UNKNOWN, why="Evidence incomplete: " + "; ".join(parts))

    is_app_store = record.app_store.status == AppStoreStatus.APP_STORE
    is_homebrew_managed = record.homebrew.status == HomebrewStatus.MANAGED
    is_auto_updating = record.auto_update.status in (AutoUpdateStatus.ENABLED, AutoUpdateStatus.CAPABLE)
    is_blocklisted = record.blocklist.status == BlocklistStatus.BLOCKED

    if not (is_app_store or is_homebrew_managed or is_auto_updating or is_blocklisted):
        why = "Not managed by the App Store, Homebrew, a local auto-updater, or the blocklist"
        if record.homebrew.status == HomebrewStatus.AVAILABLE:
            why += f" (Homebrew: {record.homebrew.reason} -- remediation suggestion, not ownership)"
        return AuditClassification(bucket=AuditBucket.ATTENTION, why=why)

    reasons = []
    if is_app_store:
        reasons.append("managed by the App Store")
    if is_homebrew_managed:
        reasons.append(f"managed by Homebrew ({record.homebrew.matched_identifier})")
    if is_auto_updating:
        reasons.append(f"has a local auto-update mechanism ({record.auto_update.status.value})")
    if is_blocklisted:
        matched_by = record.blocklist.matched_by.value if record.blocklist.matched_by else "unknown signal"
        reasons.append(f"blocklisted (matched by {matched_by})")
    # Capitalize only the first character -- str.capitalize() would also
    # lowercase the rest of the string, destroying "App Store"'s and
    # "Homebrew"'s intentional capitalization.
    combined = "; ".join(reasons)
    why = combined[0].upper() + combined[1:] if combined else combined
    return AuditClassification(bucket=AuditBucket.MANAGED, why=why)


def _build_summary(applications: Sequence[ClassifiedApplication]) -> dict[str, int]:
    summary = {"total": len(applications), "attention": 0, "unknown": 0, "managed": 0}
    for app in applications:
        summary[app.classification.bucket.value] += 1
    return summary


def run_audit(
    *,
    roots: Sequence[Path] | None = None,
    extra_roots: Sequence[str | Path] | None = None,
    system_profiler_data: dict[str, Any] | None = None,
    launch_agent_dirs: Sequence[Path] | None = None,
    blocklist_entries: Sequence[str] | None = None,
) -> AuditResult:
    """Discover once, resolve every evidence axis, classify, return a structured result.

    `system_profiler_data=None` means "fetch the real thing" (via
    _fetch_system_profiler_data(), degrading to None on failure) -- tests
    that want to exercise the no-system-profiler-data path must patch
    _fetch_system_profiler_data itself, not rely on passing None, since None
    is now the "use the real default" sentinel, consistent with every other
    parameter here.
    """
    sp_data = system_profiler_data if system_profiler_data is not None else _fetch_system_profiler_data()
    records = discover_applications(roots=roots, extra_roots=extra_roots, system_profiler_data=sp_data)

    # Homebrew must resolve before BOTH blocklist (its cask-token tier reads
    # record.homebrew.matched_identifier) and auto-update
    # (_apply_homebrew_cask_supplement reads record.homebrew.status /
    # .cask_auto_updates / .matched_identifier). Blocklist and auto-update
    # don't read each other, so their relative order doesn't matter.
    records = apply_homebrew_evidence(records)
    records = apply_blocklist_evidence(records, blocklist_entries)
    records = apply_auto_update_evidence(records, launch_agent_dirs=launch_agent_dirs)

    applications = tuple(
        ClassifiedApplication(record=record, classification=classify_record(record))
        for record in sorted(records, key=lambda r: (r.name.lower(), r.canonical_path))
    )
    return AuditResult(applications=applications, summary=_build_summary(applications))


def filter_result(result: AuditResult, *, show_all: bool, status: AuditBucket | None) -> AuditResult:
    """Select which applications to show; `summary` always reflects the full set.

    show_all=True: no filtering. status=X: exactly that bucket. Neither:
    ATTENTION union UNKNOWN -- the spec's default 3-section terminal view
    (Needs manual management / Needs review / Summary).
    """
    if show_all:
        selected = result.applications
    elif status is not None:
        selected = tuple(app for app in result.applications if app.classification.bucket == status)
    else:
        selected = tuple(
            app
            for app in result.applications
            if app.classification.bucket in (AuditBucket.ATTENTION, AuditBucket.UNKNOWN)
        )
    return AuditResult(applications=selected, summary=result.summary)
