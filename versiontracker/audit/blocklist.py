"""Blocklist identity resolution for the audit feature (Phase 2).

Blocklist entries are matched by structured identity -- canonical path,
bundle identifier, associated Homebrew cask token, and (weakest) normalized
display name -- rather than versiontracker.config.Config.is_blocklisted()'s
pure display-name comparison, which cannot distinguish a cask token like
"visual-studio-code" (written into the same list by the existing
--blocklist-auto-updates flag) from the display name "Visual Studio Code"
it's meant to match.
"""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Iterable, Sequence
from pathlib import Path

from versiontracker.audit.models import (
    ApplicationRecord,
    BlocklistEvidence,
    BlocklistMatchKind,
    BlocklistStatus,
    EvidenceConfidence,
    EvidenceSource,
)
from versiontracker.config import get_config
from versiontracker.exceptions import ConfigError


def _try_resolve_path_entry(entry: str) -> Path | None:
    """Resolve a blocklist entry as a path, but only if it already looks like one.

    A bare relative fragment (e.g. a typo'd "Keynote.app" meant as a display
    name) must NOT be resolved against the process's cwd -- that would make
    the same config match or not match depending on where versiontracker
    happens to be launched from. Only entries already absolute or
    `~`-prefixed are eligible for canonical-path matching.
    """
    try:
        candidate = Path(entry).expanduser()
        if not candidate.is_absolute():
            return None
        return candidate.resolve()
    except (OSError, RuntimeError, ValueError) as e:
        logging.debug("Could not resolve blocklist entry as a path: %r (%s)", entry, e)
        return None


def _blocked(
    matched_entry: str,
    matched_by: BlocklistMatchKind,
    reason: str,
    *,
    confidence: EvidenceConfidence = EvidenceConfidence.HIGH,
) -> BlocklistEvidence:
    return BlocklistEvidence(
        status=BlocklistStatus.BLOCKED,
        reason=reason,
        source=EvidenceSource.CONFIG,
        matched_identifier=matched_entry,
        matched_by=matched_by,
        confidence=confidence,
    )


def resolve_blocklist_evidence(record: ApplicationRecord, blocklist_entries: Iterable[str]) -> BlocklistEvidence:
    """Resolve blocklist status for one record via structured identity matching.

    Checks, strongest first: canonical path, bundle identifier, Homebrew
    cask token, normalized display name. The cask-token tier reads
    record.homebrew.matched_identifier, which is None for every
    HomebrewStatus except MANAGED -- so this degrades gracefully (not a
    crash) whether or not Homebrew evidence has been resolved yet for this
    record; there is no service.py in this phase to enforce resolution
    order, so this function must tolerate either order on its own.
    """
    entries = [entry for entry in blocklist_entries if isinstance(entry, str)]

    for entry in entries:
        resolved_entry = _try_resolve_path_entry(entry)
        if resolved_entry is not None and resolved_entry == record.canonical_path:
            return _blocked(
                entry,
                BlocklistMatchKind.CANONICAL_PATH,
                f"Matches canonical path '{record.canonical_path}'",
            )

    if record.bundle_id:
        for entry in entries:
            if entry == record.bundle_id:
                return _blocked(
                    entry,
                    BlocklistMatchKind.BUNDLE_ID,
                    f"Matches bundle identifier '{record.bundle_id}'",
                )

    homebrew_token = record.homebrew.matched_identifier
    if homebrew_token:
        for entry in entries:
            if entry.strip().lower() == homebrew_token.strip().lower():
                return _blocked(
                    entry,
                    BlocklistMatchKind.HOMEBREW_TOKEN,
                    f"Matches Homebrew cask token '{homebrew_token}'",
                )

    normalized_name = record.name.strip().lower()
    for entry in entries:
        if entry.strip().lower() == normalized_name:
            return _blocked(
                entry,
                BlocklistMatchKind.DISPLAY_NAME,
                f"Matches display name '{record.name}'",
                confidence=EvidenceConfidence.MEDIUM,
            )

    return BlocklistEvidence(
        status=BlocklistStatus.NOT_BLOCKED,
        reason="No blocklist entry matches this application's path, bundle identifier, Homebrew token, or display name",
        source=EvidenceSource.CONFIG,
        confidence=EvidenceConfidence.HIGH,
    )


def apply_blocklist_evidence(
    records: Sequence[ApplicationRecord], blocklist_entries: Iterable[str] | None = None
) -> list[ApplicationRecord]:
    """Resolve and attach blocklist evidence to each record, returning new records.

    Defaults to get_config().get_blocklist() -- the existing, already-unified
    accessor that merges legacy `blacklist` with modern `blocklist` config
    keys -- when blocklist_entries isn't given explicitly. A malformed
    config file can raise ConfigError on that call; this degrades every
    record to BlocklistStatus.UNKNOWN rather than propagating and crashing
    the whole audit.
    """
    if blocklist_entries is not None:
        entries = list(blocklist_entries)
    else:
        try:
            entries = get_config().get_blocklist()
        except ConfigError as e:
            logging.warning("Blocklist resolution unavailable: %s", e)
            unknown = BlocklistEvidence(
                status=BlocklistStatus.UNKNOWN,
                reason="Could not load blocklist configuration",
                source=EvidenceSource.CONFIG,
                confidence=EvidenceConfidence.NONE,
                error=str(e),
            )
            return [dataclasses.replace(record, blocklist=unknown) for record in records]

    return [dataclasses.replace(record, blocklist=resolve_blocklist_evidence(record, entries)) for record in records]
