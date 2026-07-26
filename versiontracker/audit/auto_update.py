"""Local automatic-update capability detection for the audit feature (Phase 3).

Five independent, local-only probes (Sparkle framework, Squirrel framework,
electron-updater's app-update.yml, Mozilla's updater.app, and vendor
LaunchAgents/Daemons tied to a bundle identifier or known vendor) each
contribute an internal _ProbeResult; one aggregation step combines them into
the public AutoUpdateEvidence. A Homebrew cask's `auto_updates` flag can
supplement the result afterward, but only when local probes found nothing at
all, and never toward ENABLED -- it reflects upstream capability, not the
user's current preference. No network access, no subprocess calls.
"""

from __future__ import annotations

import dataclasses
import logging
import plistlib
from collections.abc import Sequence
from pathlib import Path

import yaml

from versiontracker.audit.discovery import _read_info_plist
from versiontracker.audit.models import (
    ApplicationRecord,
    AutoUpdateEvidence,
    AutoUpdateMechanism,
    AutoUpdateStatus,
    EvidenceConfidence,
    EvidenceSource,
    HomebrewStatus,
)

_UPDATER_KEYWORD = "update"

# Independently-paired (agent-label-prefix, app-bundle-id-prefixes) tuples --
# NOT a single shared string. Confirmed live that some vendors' LaunchAgent
# label namespace and their own app's bundle-id namespace genuinely differ
# (Dropbox's agents are `com.dropbox.*` but Dropbox.app's own bundle id is
# `com.getdropbox.dropbox`). Comparisons are case-insensitive on both sides.
_VENDOR_UPDATER_TIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("com.google.keystone.", ("com.google.",)),
    ("com.google.googleupdater.", ("com.google.",)),
    ("com.microsoft.update.", ("com.microsoft.",)),
    ("com.microsoft.autoupdate.", ("com.microsoft.",)),
    ("com.adobe.", ("com.adobe.",)),  # spec-named vendor; unverified on this machine (no Adobe app installed)
    ("com.logi.", ("com.logi.",)),
    ("com.dropbox.", ("com.getdropbox.",)),
    ("us.zoom.updater.", ("us.zoom.",)),
    ("org.gpgtools.updater.", ("org.gpgtools.",)),
)

_CONFIDENCE_RANK = {
    EvidenceConfidence.HIGH: 3,
    EvidenceConfidence.MEDIUM: 2,
    EvidenceConfidence.LOW: 1,
    EvidenceConfidence.NONE: 0,
}


@dataclasses.dataclass(frozen=True)
class _ProbeResult:
    """Internal: one mechanism probe's finding for one application record."""

    mechanism: AutoUpdateMechanism
    found: bool
    confidence: EvidenceConfidence
    detail: str
    matched_identifier: str | None = None
    enabled: bool | None = None  # only Sparkle's preference read ever sets True/False
    error: str | None = None  # may coexist with found=True -- see _aggregate_probe_results


@dataclasses.dataclass(frozen=True)
class _LaunchAgentCandidate:
    """Internal: one *.plist file found while scanning LaunchAgent/Daemon dirs."""

    path: Path
    filename_stem: str
    label: str | None


def default_launch_agent_dirs() -> list[Path]:
    """Built-in LaunchAgent/LaunchDaemon scan locations.

    Computed per call (not at import time) so tests can patch Path.home().
    """
    return [
        Path("/Library/LaunchDaemons"),
        Path("/Library/LaunchAgents"),
        Path.home() / "Library" / "LaunchAgents",
    ]


def _read_launch_agent_label(path: Path) -> str | None:
    """Best-effort read of a LaunchAgent/Daemon plist's Label key.

    Returns None on any read/parse failure, missing key, or non-string
    value -- never raises. Confirmed live that some vendor LaunchDaemons are
    root-owned and mode 600 (unreadable by an unprivileged process); this is
    exactly the case that degrades gracefully here -- the candidate's
    filename_stem remains usable even when its content isn't. Deliberately
    catches Exception broadly, not a specific tuple: confirmed live on this
    real machine that a genuinely malformed plist (a real, unrelated
    LaunchAgent with corrupt XML content) raises xml.parsers.expat.ExpatError
    via plistlib's XML parser -- neither OSError, ValueError, nor
    plistlib.InvalidFileException, so a narrower tuple would have let a real
    LaunchAgent scan crash the whole audit.
    """
    try:
        with path.open("rb") as f:
            data = plistlib.load(f)
    except Exception as e:
        logging.debug("Could not read LaunchAgent/Daemon label for %s: %s", path, e)
        return None
    label = data.get("Label") if isinstance(data, dict) else None
    return label if isinstance(label, str) else None


def build_launch_agent_index(
    dirs: Sequence[Path],
) -> tuple[tuple[_LaunchAgentCandidate, ...], tuple[str, ...]]:
    """Enumerate *.plist files across the given directories once.

    Never raises. A directory that can't be listed (missing, permission
    denied) contributes a scan error but doesn't abort scanning the other
    directories.
    """
    candidates: list[_LaunchAgentCandidate] = []
    scan_errors: list[str] = []

    for directory in dirs:
        try:
            entries = list(directory.iterdir())
        except OSError as e:
            logging.debug("Could not list %s: %s", directory, e)
            scan_errors.append(f"Could not list {directory}: {e}")
            continue

        for entry in entries:
            if entry.suffix.lower() != ".plist":
                continue
            try:
                is_file = entry.is_file()
            except OSError:
                continue
            if not is_file:
                continue
            candidates.append(
                _LaunchAgentCandidate(path=entry, filename_stem=entry.stem, label=_read_launch_agent_label(entry))
            )

    return tuple(candidates), tuple(scan_errors)


def _probe_sparkle(bundle_path: Path) -> _ProbeResult:
    """Sparkle framework presence + SUEnableAutomaticChecks preference.

    Framework presence is the reliable signal -- confirmed against 14 real
    Sparkle apps, Info.plist SU* keys are sparse/inconsistent (some real
    apps have none at all despite the framework definitely being present).
    """
    framework_path = bundle_path / "Contents" / "Frameworks" / "Sparkle.framework"
    try:
        present = framework_path.is_dir()
    except OSError as e:
        return _ProbeResult(
            mechanism=AutoUpdateMechanism.SPARKLE_FRAMEWORK,
            found=False,
            confidence=EvidenceConfidence.NONE,
            detail="Could not check for Sparkle.framework",
            error=str(e),
        )
    if not present:
        return _ProbeResult(
            mechanism=AutoUpdateMechanism.SPARKLE_FRAMEWORK,
            found=False,
            confidence=EvidenceConfidence.NONE,
            detail="Sparkle.framework not found",
        )

    enabled = _read_info_plist(bundle_path).get("SUEnableAutomaticChecks")
    if enabled is True:
        detail = "Sparkle.framework present; SUEnableAutomaticChecks=true"
    elif enabled is False:
        detail = "Sparkle.framework present; SUEnableAutomaticChecks=false (explicitly disabled)"
    else:
        detail = "Sparkle.framework present; auto-check preference not set in Info.plist"

    return _ProbeResult(
        mechanism=AutoUpdateMechanism.SPARKLE_FRAMEWORK,
        found=True,
        confidence=EvidenceConfidence.HIGH,
        detail=detail,
        matched_identifier="Sparkle.framework",
        enabled=enabled if isinstance(enabled, bool) else None,
    )


def _probe_squirrel(bundle_path: Path) -> _ProbeResult:
    """Squirrel framework presence (ShipIt helper noted as corroboration).

    ShipIt (Sparkle's privileged-install helper) is nested inside Squirrel's
    own Resources -- confirmed live -- so it's folded into this probe's
    detail rather than treated as a separate probe.
    """
    framework_path = bundle_path / "Contents" / "Frameworks" / "Squirrel.framework"
    try:
        present = framework_path.is_dir()
    except OSError as e:
        return _ProbeResult(
            mechanism=AutoUpdateMechanism.SQUIRREL_FRAMEWORK,
            found=False,
            confidence=EvidenceConfidence.NONE,
            detail="Could not check for Squirrel.framework",
            error=str(e),
        )
    if not present:
        return _ProbeResult(
            mechanism=AutoUpdateMechanism.SQUIRREL_FRAMEWORK,
            found=False,
            confidence=EvidenceConfidence.NONE,
            detail="Squirrel.framework not found",
        )

    has_shipit = False
    try:
        has_shipit = (framework_path / "Resources" / "ShipIt").exists()
    except OSError:
        pass

    detail = "Squirrel.framework present" + (" (with ShipIt helper)" if has_shipit else "")
    return _ProbeResult(
        mechanism=AutoUpdateMechanism.SQUIRREL_FRAMEWORK,
        found=True,
        confidence=EvidenceConfidence.HIGH,
        detail=detail,
        matched_identifier="Squirrel.framework",
    )


def _probe_electron_updater_yml(bundle_path: Path) -> _ProbeResult:
    """electron-updater's app-update.yml.

    Distinct from Squirrel -- confirmed live that a single Electron app can
    carry both an old Squirrel.framework build and newer app-update.yml
    metadata simultaneously, so this probe never treats Squirrel presence as
    a reason to skip this check. File content has no enabled/disabled
    toggle (confirmed against real files) -- presence is capability-only.
    """
    yml_path = bundle_path / "Contents" / "Resources" / "app-update.yml"
    try:
        present = yml_path.is_file()
    except OSError as e:
        return _ProbeResult(
            mechanism=AutoUpdateMechanism.ELECTRON_UPDATER_YML,
            found=False,
            confidence=EvidenceConfidence.NONE,
            detail="Could not check for app-update.yml",
            error=str(e),
        )
    if not present:
        return _ProbeResult(
            mechanism=AutoUpdateMechanism.ELECTRON_UPDATER_YML,
            found=False,
            confidence=EvidenceConfidence.NONE,
            detail="app-update.yml not found",
        )

    provider: str | None = None
    try:
        with yml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            provider_value = data.get("provider")
            provider = provider_value if isinstance(provider_value, str) else None
    except (OSError, yaml.YAMLError) as e:
        # Secondary-detail failure only (a malformed/unreadable body) --
        # existence itself was already confirmed above, so this stays found=True.
        logging.debug("Could not parse app-update.yml at %s: %s", yml_path, e)

    detail = "app-update.yml present" + (f" (provider={provider})" if provider else "")
    return _ProbeResult(
        mechanism=AutoUpdateMechanism.ELECTRON_UPDATER_YML,
        found=True,
        confidence=EvidenceConfidence.HIGH,
        detail=detail,
        matched_identifier="app-update.yml",
    )


def _probe_mozilla_updater(bundle_path: Path) -> _ProbeResult:
    """Mozilla-style updater probe: Contents/MacOS/updater.app.

    A corroborating updater.ini / org.mozilla.updater LaunchServices entry
    bumps confidence. Multiplicity affects confidence, not inclusion -- a
    stricter all-three-required gate would risk false negatives on a
    legitimate partial build for no real gain, since a coincidental
    unrelated updater.app directory would still be a correct positive, not
    a false one.
    """
    updater_app = bundle_path / "Contents" / "MacOS" / "updater.app"
    try:
        present = updater_app.is_dir()
    except OSError as e:
        return _ProbeResult(
            mechanism=AutoUpdateMechanism.MOZILLA_UPDATER,
            found=False,
            confidence=EvidenceConfidence.NONE,
            detail="Could not check for Contents/MacOS/updater.app",
            error=str(e),
        )
    if not present:
        return _ProbeResult(
            mechanism=AutoUpdateMechanism.MOZILLA_UPDATER,
            found=False,
            confidence=EvidenceConfidence.NONE,
            detail="Contents/MacOS/updater.app not found",
        )

    corroborating = 0
    for candidate in (
        bundle_path / "Contents" / "Resources" / "updater.ini",
        bundle_path / "Contents" / "Library" / "LaunchServices" / "org.mozilla.updater",
    ):
        try:
            if candidate.is_file():
                corroborating += 1
        except OSError:
            pass

    confidence = EvidenceConfidence.HIGH if corroborating > 0 else EvidenceConfidence.MEDIUM
    return _ProbeResult(
        mechanism=AutoUpdateMechanism.MOZILLA_UPDATER,
        found=True,
        confidence=confidence,
        detail=f"Contents/MacOS/updater.app present ({corroborating} corroborating file(s))",
        matched_identifier="Contents/MacOS/updater.app",
    )


def _candidate_identifiers(candidate: _LaunchAgentCandidate) -> list[tuple[str, EvidenceConfidence]]:
    """Return every identifier worth testing for this candidate, in priority order.

    Label and filename stem are checked independently, not one-with-a-
    fallback -- confirmed live that they can diverge in both directions: a
    real, root-owned, mode-600 vendor updater daemon's content is
    unreadable (Label unavailable, filename still usable), and a real
    LaunchAgent's filename doesn't always match its own internal Label even
    when both ARE readable. Relying on only one would miss real matches the
    other would have caught. Label (when present) is checked first and
    reported preferentially when both match, since it's the more
    authoritative identifier when readable.
    """
    identifiers: list[tuple[str, EvidenceConfidence]] = []
    if candidate.label:
        identifiers.append((candidate.label, EvidenceConfidence.HIGH))
    identifiers.append((candidate.filename_stem, EvidenceConfidence.MEDIUM))
    return identifiers


def _probe_vendor_launch_agent(
    record: ApplicationRecord,
    candidates: Sequence[_LaunchAgentCandidate],
    scan_errors: Sequence[str],
) -> _ProbeResult:
    """Tie a LaunchAgent/Daemon to this record via its bundle_id (exact tier) or a known vendor (vendor tier).

    Exact-prefix matching on structured reverse-DNS identifiers, not
    similarity scoring -- deterministic and does not fall under the
    "do not use fuzzy matching to prove ownership" guardrail. Confirmed
    live this needs an "update" keyword guard on the exact tier (ClamXAV's
    .Engine.plist/.HelperTool.plist share a bundle-id prefix with the real
    .HelperToolUpdater.plist but aren't updaters) and independently-paired
    vendor prefixes on the vendor tier (see _VENDOR_UPDATER_TIES).
    """
    error = "; ".join(scan_errors) if scan_errors else None

    if not record.bundle_id:
        return _ProbeResult(
            mechanism=AutoUpdateMechanism.VENDOR_LAUNCH_AGENT,
            found=False,
            confidence=EvidenceConfidence.NONE,
            detail="No bundle identifier to tie a LaunchAgent/Daemon to",
            error=error,
        )

    bundle_id_lower = record.bundle_id.lower()

    for candidate in candidates:
        for identifier, confidence in _candidate_identifiers(candidate):
            identifier_lower = identifier.lower()
            if identifier_lower.startswith(bundle_id_lower) and _UPDATER_KEYWORD in identifier_lower:
                return _ProbeResult(
                    mechanism=AutoUpdateMechanism.VENDOR_LAUNCH_AGENT,
                    found=True,
                    confidence=confidence,
                    detail=f"LaunchAgent/Daemon '{identifier}' is tied to this app's own bundle identifier",
                    matched_identifier=identifier,
                    error=error,
                )

    for candidate in candidates:
        for identifier, _confidence in _candidate_identifiers(candidate):
            identifier_lower = identifier.lower()
            for agent_prefix, app_prefixes in _VENDOR_UPDATER_TIES:
                if identifier_lower.startswith(agent_prefix) and any(
                    bundle_id_lower.startswith(app_prefix) for app_prefix in app_prefixes
                ):
                    return _ProbeResult(
                        mechanism=AutoUpdateMechanism.VENDOR_LAUNCH_AGENT,
                        found=True,
                        confidence=EvidenceConfidence.LOW,
                        detail=f"LaunchAgent/Daemon '{identifier}' belongs to a known vendor's suite-wide updater",
                        matched_identifier=identifier,
                        error=error,
                    )

    return _ProbeResult(
        mechanism=AutoUpdateMechanism.VENDOR_LAUNCH_AGENT,
        found=False,
        confidence=EvidenceConfidence.NONE,
        detail="No LaunchAgent/Daemon tied to this app's bundle identifier or a known vendor",
        error=error,
    )


def _aggregate_probe_results(results: Sequence[_ProbeResult]) -> AutoUpdateEvidence:
    """Combine independent probe results into one AutoUpdateEvidence.

    A probe error never suppresses a positive finding from a different
    probe -- CAPABLE/ENABLED is decided from `positives` first, independent
    of `errors`; an error alongside a positive becomes a reason caveat, not
    `.error` (matching existing precedent: `.error` is only populated on the
    evidence's own failed status). `mechanisms` records every contributing
    positive probe, not just the deciding one -- some real apps genuinely
    have two simultaneously-true mechanisms (e.g. Squirrel.framework AND
    app-update.yml).
    """
    positives = [r for r in results if r.found]
    errors = [r for r in results if r.error]
    mechanisms = tuple(r.mechanism for r in positives)
    matched_identifier = next((r.matched_identifier for r in positives if r.matched_identifier), None)

    if any(r.enabled is True for r in positives):
        return AutoUpdateEvidence(
            status=AutoUpdateStatus.ENABLED,
            reason="; ".join(r.detail for r in positives),
            source=EvidenceSource.FILESYSTEM,
            matched_identifier=matched_identifier,
            confidence=EvidenceConfidence.HIGH,
            mechanisms=mechanisms,
        )

    if positives:
        confidence = max((r.confidence for r in positives), key=lambda c: _CONFIDENCE_RANK[c])
        reason = "; ".join(r.detail for r in positives)
        if errors:
            error_detail = "; ".join(e.error for e in errors if e.error)
            reason += f"; {len(errors)} probe(s) could not complete: {error_detail}"
        return AutoUpdateEvidence(
            status=AutoUpdateStatus.CAPABLE,
            reason=reason,
            source=EvidenceSource.FILESYSTEM,
            matched_identifier=matched_identifier,
            confidence=confidence,
            mechanisms=mechanisms,
        )

    if errors:
        error_detail = "; ".join(e.error for e in errors if e.error)
        return AutoUpdateEvidence(
            status=AutoUpdateStatus.UNKNOWN,
            reason=f"Could not complete all local auto-update probes: {error_detail}",
            source=EvidenceSource.FILESYSTEM,
            confidence=EvidenceConfidence.NONE,
            error=error_detail,
        )

    return AutoUpdateEvidence(
        status=AutoUpdateStatus.NONE_DETECTED,
        reason="All local auto-update probes completed without evidence",
        source=EvidenceSource.FILESYSTEM,
        confidence=EvidenceConfidence.MEDIUM,
    )


def _apply_homebrew_cask_supplement(evidence: AutoUpdateEvidence, record: ApplicationRecord) -> AutoUpdateEvidence:
    """Supplement with the owning cask's auto_updates flag.

    Only applied when local probes found nothing at all (never overriding
    a positive or an unknown), and never toward ENABLED, since the cask
    flag indicates upstream capability, not the user's current preference.
    """
    if record.homebrew.status is not HomebrewStatus.MANAGED:
        return evidence
    if record.homebrew.cask_auto_updates is not True:
        return evidence
    if evidence.status is not AutoUpdateStatus.NONE_DETECTED:
        return evidence

    return dataclasses.replace(
        evidence,
        status=AutoUpdateStatus.CAPABLE,
        reason=(
            "No local probe found evidence, but the owning Homebrew cask "
            f"'{record.homebrew.matched_identifier}' declares auto_updates=true"
        ),
        confidence=EvidenceConfidence.LOW,
        matched_identifier=record.homebrew.matched_identifier,
        mechanisms=(AutoUpdateMechanism.HOMEBREW_CASK_AUTO_UPDATES,),
    )


def resolve_auto_update_evidence(
    record: ApplicationRecord,
    *,
    launch_agent_candidates: Sequence[_LaunchAgentCandidate],
    launch_agent_scan_errors: Sequence[str] = (),
) -> AutoUpdateEvidence:
    """Run all local probes for one record, aggregate, then apply the Homebrew cask auto_updates supplement."""
    results = [
        _probe_sparkle(record.canonical_path),
        _probe_squirrel(record.canonical_path),
        _probe_electron_updater_yml(record.canonical_path),
        _probe_mozilla_updater(record.canonical_path),
        _probe_vendor_launch_agent(record, launch_agent_candidates, launch_agent_scan_errors),
    ]
    evidence = _aggregate_probe_results(results)
    return _apply_homebrew_cask_supplement(evidence, record)


def apply_auto_update_evidence(
    records: Sequence[ApplicationRecord], *, launch_agent_dirs: Sequence[Path] | None = None
) -> list[ApplicationRecord]:
    """Resolve and attach auto-update evidence to each record, returning new records.

    Builds the LaunchAgent/Daemon index once, shared across all records.
    `launch_agent_dirs`, when given, fully replaces the default scan
    locations -- the same hermetic escape hatch `discover_applications(roots=...)`
    established; tests must never enumerate the real machine's actual
    LaunchAgents/Daemons.
    """
    dirs = list(launch_agent_dirs) if launch_agent_dirs is not None else default_launch_agent_dirs()
    candidates, scan_errors = build_launch_agent_index(dirs)

    return [
        dataclasses.replace(
            record,
            auto_update=resolve_auto_update_evidence(
                record, launch_agent_candidates=candidates, launch_agent_scan_errors=scan_errors
            ),
        )
        for record in records
    ]
