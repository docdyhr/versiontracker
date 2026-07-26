"""Exact Homebrew ownership resolution for the audit feature (Phase 2).

Ownership is decided by joining each discovered bundle's canonical path
against installed casks' `app` artifact targets -- never by fuzzy name
matching (see versiontracker/apps/matcher.py:filter_out_brews for the
fuzzy-matching approach this deliberately does not reuse). Cask
"availability" (a matching cask exists but wasn't used to install this
bundle) is a separate, later enrichment -- this module only ever produces
MANAGED, NOT_AVAILABLE, or UNKNOWN, never AVAILABLE.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from versiontracker.audit.models import (
    ApplicationRecord,
    EvidenceConfidence,
    EvidenceSource,
    HomebrewEvidence,
    HomebrewStatus,
)
from versiontracker.exceptions import DataParsingError, HomebrewError, NetworkError
from versiontracker.exceptions import TimeoutError as VtTimeoutError
from versiontracker.homebrew import get_brew_command
from versiontracker.utils import run_command_secure

_APP_ARTIFACT_KEY = "app"
_TARGET_KEY = "target"


@dataclasses.dataclass(frozen=True)
class _InstalledCaskAppTarget:
    """Internal: one installed cask's app-artifact ownership record."""

    token: str
    installed_version: str | None
    artifact_target: Path
    tap: str | None
    auto_updates: bool


def fetch_installed_casks(*, timeout: int = 60) -> list[dict[str, Any]]:
    """Run `brew info --json=v2 --cask --installed` once and return the casks list.

    `--cask` is added to the handoff spec's literal example command: it
    skips formula data (confirmed identical `casks` shape either way, ~40%
    smaller/faster on this machine) that this audit never looks at.

    Raises HomebrewError/NetworkError/DataParsingError on any failure --
    never returns a sentinel. apply_homebrew_evidence() is the single place
    that catches these and degrades every record to UNKNOWN.
    """
    brew_path = get_brew_command()
    cmd_args = [brew_path, "info", "--json=v2", "--cask", "--installed"]

    try:
        stdout, returncode = run_command_secure(cmd_args, timeout=timeout)
    except VtTimeoutError as e:
        raise NetworkError(f"Timed out running brew info --json=v2 --cask --installed: {e}") from e
    except Exception as e:
        # run_command_secure can surface a bare builtins.Exception when brew
        # itself is missing/misconfigured: its own FileNotFoundError/
        # PermissionError except clauses are bound to versiontracker's
        # custom exception subclasses, not the plain builtins subprocess.Popen
        # actually raises, so that case falls through to a bare Exception.
        raise HomebrewError(f"Error running brew info --json=v2 --cask --installed: {e}") from e

    if returncode != 0:
        raise HomebrewError(f"brew info --json=v2 --cask --installed failed: {stdout}")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise DataParsingError(f"Could not parse installed casks JSON: {e}") from e

    casks = data.get("casks", [])
    return casks if isinstance(casks, list) else []


def _canonicalize_target(target: str) -> Path | None:
    try:
        return Path(target).expanduser().resolve()
    except OSError as e:
        logging.debug("Could not canonicalize cask artifact target %r: %s", target, e)
        return None


def build_artifact_index(casks: Sequence[dict[str, Any]]) -> dict[Path, _InstalledCaskAppTarget]:
    """Map canonical app-artifact target path -> owning cask.

    Only casks with at least one `app` artifact contribute -- casks without
    one (fonts, CLI tools, pkg-only installers) are recorded nowhere, per
    "record casks without an app artifact without guessing ownership".
    Multi-app casks produce multiple separate artifact entries in Homebrew's
    own JSON (never one entry listing multiple app names), so iterating
    `artifacts` and reading each app-keyed entry's own `target` handles that
    case with no special-casing.
    """
    index: dict[Path, _InstalledCaskAppTarget] = {}
    for cask in casks:
        token = cask.get("token")
        if not token:
            continue
        for artifact in cask.get("artifacts", []):
            if not isinstance(artifact, dict) or _APP_ARTIFACT_KEY not in artifact:
                continue
            target = artifact.get(_TARGET_KEY)
            if not target:
                continue
            canonical = _canonicalize_target(target)
            if canonical is None:
                continue
            if canonical in index:
                logging.debug(
                    "Cask '%s' artifact target %s collides with already-indexed cask '%s'; keeping first-seen",
                    token,
                    canonical,
                    index[canonical].token,
                )
                continue
            index[canonical] = _InstalledCaskAppTarget(
                token=token,
                installed_version=cask.get("installed"),
                artifact_target=canonical,
                tap=cask.get("tap"),
                auto_updates=bool(cask.get("auto_updates", False)),
            )
    return index


def resolve_homebrew_evidence(
    record: ApplicationRecord, artifact_index: dict[Path, _InstalledCaskAppTarget]
) -> HomebrewEvidence:
    """Resolve Homebrew ownership for one record against a pre-built artifact index.

    Only decides exact ownership (MANAGED) versus "not managed by an
    installed cask" (NOT_AVAILABLE) -- it never claims a suitable cask
    exists in the wider catalog when none is installed; that "availability"
    check is a deliberately separate, later enrichment. This function never
    sees a fetch failure (apply_homebrew_evidence() handles that upstream),
    so it has no UNKNOWN branch of its own.
    """
    match = artifact_index.get(record.canonical_path)
    if match is not None:
        return HomebrewEvidence(
            status=HomebrewStatus.MANAGED,
            reason=f"Homebrew cask '{match.token}' owns this bundle via its app artifact target",
            source=EvidenceSource.HOMEBREW_CLI,
            matched_identifier=match.token,
            confidence=EvidenceConfidence.HIGH,
            installed_version=match.installed_version,
            artifact_target=match.artifact_target,
            cask_auto_updates=match.auto_updates,
        )

    return HomebrewEvidence(
        status=HomebrewStatus.NOT_AVAILABLE,
        reason=("No installed cask's app artifact targets this bundle path (the wider cask catalog was not searched)"),
        source=EvidenceSource.HOMEBREW_CLI,
        confidence=EvidenceConfidence.HIGH,
    )


def apply_homebrew_evidence(records: Sequence[ApplicationRecord]) -> list[ApplicationRecord]:
    """Resolve and attach Homebrew evidence to each record, returning new records.

    Fetches the installed-cask list and builds the artifact index once. If
    that fails for any reason (Homebrew missing, command failure, malformed
    JSON), every record gets HomebrewStatus.UNKNOWN -- never NOT_AVAILABLE,
    per "if Homebrew is missing or the command fails, set unknown, not
    not_managed."
    """
    try:
        casks = fetch_installed_casks()
        artifact_index = build_artifact_index(casks)
    except (HomebrewError, NetworkError, DataParsingError) as e:
        logging.warning("Homebrew ownership resolution unavailable: %s", e)
        unknown = HomebrewEvidence(
            status=HomebrewStatus.UNKNOWN,
            reason="Could not determine installed Homebrew casks",
            source=EvidenceSource.HOMEBREW_CLI,
            confidence=EvidenceConfidence.NONE,
            error=str(e),
        )
        return [dataclasses.replace(record, homebrew=unknown) for record in records]

    return [
        dataclasses.replace(record, homebrew=resolve_homebrew_evidence(record, artifact_index)) for record in records
    ]
