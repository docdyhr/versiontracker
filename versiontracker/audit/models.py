"""Data models for the unmanaged macOS application audit feature.

Shared evidence vocabulary and the ApplicationRecord shape. AppStoreEvidence
is resolved during discovery (see discovery.py::resolve_app_store_evidence);
HomebrewEvidence, AutoUpdateEvidence, and BlocklistEvidence are resolved by
homebrew.py, auto_update.py, and blocklist.py respectively. Each Evidence
type ships its own `.not_evaluated()` default so a record can be partially
resolved (e.g. by a fresh discover_applications() call, before any resolver
has run) without ApplicationRecord's shape changing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class EvidenceSource(Enum):
    """Where a piece of evidence was derived from."""

    SYSTEM_PROFILER = "system_profiler"
    FILESYSTEM = "filesystem"
    HOMEBREW_CLI = "homebrew_cli"
    CONFIG = "config"
    NOT_EVALUATED = "not_evaluated"


class EvidenceConfidence(Enum):
    """Confidence attached to a resolved piece of evidence."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class AppStoreStatus(Enum):
    """App Store management status for an application bundle."""

    APP_STORE = "app_store"
    NOT_APP_STORE = "not_app_store"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AppStoreEvidence:
    """Evidence for whether an application is App Store-managed."""

    status: AppStoreStatus
    reason: str
    source: EvidenceSource
    matched_identifier: str | None = None
    confidence: EvidenceConfidence = EvidenceConfidence.NONE
    error: str | None = None


class HomebrewStatus(Enum):
    """Homebrew ownership status for an application bundle.

    Resolved starting in a later phase; Phase 1 records only carry
    NOT_EVALUATED (see HomebrewEvidence.not_evaluated).
    """

    MANAGED = "managed"
    AVAILABLE = "available"
    NOT_AVAILABLE = "not_available"
    UNKNOWN = "unknown"
    NOT_EVALUATED = "not_evaluated"


@dataclass(frozen=True)
class HomebrewEvidence:
    """Evidence for Homebrew ownership/availability of an application."""

    status: HomebrewStatus
    reason: str
    source: EvidenceSource
    matched_identifier: str | None = None
    confidence: EvidenceConfidence = EvidenceConfidence.NONE
    error: str | None = None
    installed_version: str | None = None
    artifact_target: Path | None = None
    cask_auto_updates: bool | None = None

    @classmethod
    def not_evaluated(cls) -> HomebrewEvidence:
        """Return the Phase 1 placeholder: Homebrew resolution hasn't run yet."""
        return cls(
            status=HomebrewStatus.NOT_EVALUATED,
            reason="Homebrew ownership resolution runs in a later phase",
            source=EvidenceSource.NOT_EVALUATED,
        )


class AutoUpdateStatus(Enum):
    """Auto-update capability status for an application bundle.

    Resolved starting in a later phase; Phase 1 records only carry
    NOT_EVALUATED (see AutoUpdateEvidence.not_evaluated).
    """

    ENABLED = "enabled"
    CAPABLE = "capable"
    NONE_DETECTED = "none_detected"
    UNKNOWN = "unknown"
    NOT_EVALUATED = "not_evaluated"


class AutoUpdateMechanism(Enum):
    """Which local mechanism contributed positive auto-update evidence."""

    SPARKLE_FRAMEWORK = "sparkle_framework"
    SQUIRREL_FRAMEWORK = "squirrel_framework"
    ELECTRON_UPDATER_YML = "electron_updater_yml"
    MOZILLA_UPDATER = "mozilla_updater"
    VENDOR_LAUNCH_AGENT = "vendor_launch_agent"
    HOMEBREW_CASK_AUTO_UPDATES = "homebrew_cask_auto_updates"


@dataclass(frozen=True)
class AutoUpdateEvidence:
    """Evidence for an application's automatic-update capability."""

    status: AutoUpdateStatus
    reason: str
    source: EvidenceSource
    matched_identifier: str | None = None
    confidence: EvidenceConfidence = EvidenceConfidence.NONE
    error: str | None = None
    mechanisms: tuple[AutoUpdateMechanism, ...] = ()

    @classmethod
    def not_evaluated(cls) -> AutoUpdateEvidence:
        """Return the Phase 1 placeholder: auto-update resolution hasn't run yet."""
        return cls(
            status=AutoUpdateStatus.NOT_EVALUATED,
            reason="Auto-update capability resolution runs in a later phase",
            source=EvidenceSource.NOT_EVALUATED,
        )


class BlocklistStatus(Enum):
    """Blocklist status for an application bundle.

    Resolved starting in a later phase; Phase 1 records only carry
    NOT_EVALUATED (see BlocklistEvidence.not_evaluated).
    """

    BLOCKED = "blocked"
    NOT_BLOCKED = "not_blocked"
    UNKNOWN = "unknown"
    NOT_EVALUATED = "not_evaluated"


class BlocklistMatchKind(Enum):
    """Which identity signal a blocklist match was decided by."""

    CANONICAL_PATH = "canonical_path"
    BUNDLE_ID = "bundle_id"
    HOMEBREW_TOKEN = "homebrew_token"
    DISPLAY_NAME = "display_name"


@dataclass(frozen=True)
class BlocklistEvidence:
    """Evidence for whether an application is blocklisted."""

    status: BlocklistStatus
    reason: str
    source: EvidenceSource
    matched_identifier: str | None = None
    confidence: EvidenceConfidence = EvidenceConfidence.NONE
    error: str | None = None
    matched_by: BlocklistMatchKind | None = None

    @classmethod
    def not_evaluated(cls) -> BlocklistEvidence:
        """Return the Phase 1 placeholder: blocklist resolution hasn't run yet."""
        return cls(
            status=BlocklistStatus.NOT_EVALUATED,
            reason="Blocklist resolution runs in a later phase",
            source=EvidenceSource.NOT_EVALUATED,
        )


@dataclass(frozen=True)
class ApplicationRecord:
    """Identity-preserving record for one discovered application bundle."""

    name: str
    version: str
    path: Path
    canonical_path: Path
    bundle_id: str | None
    obtained_from: str | None
    parent_bundle_path: Path | None

    app_store: AppStoreEvidence
    homebrew: HomebrewEvidence = field(default_factory=HomebrewEvidence.not_evaluated)
    auto_update: AutoUpdateEvidence = field(default_factory=AutoUpdateEvidence.not_evaluated)
    blocklist: BlocklistEvidence = field(default_factory=BlocklistEvidence.not_evaluated)

    diagnostics: tuple[str, ...] = ()

    @property
    def identity_key(self) -> tuple[Path, str | None]:
        """Stable identity used for de-duplication and future cross-resolver joins."""
        return (self.canonical_path, self.bundle_id)

    @property
    def is_nested_component(self) -> bool:
        """True if this bundle was found nested inside another bundle's Contents/."""
        return self.parent_bundle_path is not None


class AuditBucket(Enum):
    """Which section of the audit output an application belongs to."""

    ATTENTION = "attention"
    UNKNOWN = "unknown"
    MANAGED = "managed"


@dataclass(frozen=True)
class AuditClassification:
    """The bucket a record was sorted into, and a human-readable explanation."""

    bucket: AuditBucket
    why: str


@dataclass(frozen=True)
class ClassifiedApplication:
    """One application paired with its audit classification."""

    record: ApplicationRecord
    classification: AuditClassification


@dataclass(frozen=True)
class AuditResult:
    """The full output of one audit run.

    `summary` always reflects the entire discovered set, regardless of any
    filtering later applied to `applications` (see service.py::filter_result)
    -- a filtered view should still be able to report how many applications
    exist in the buckets it isn't showing.
    """

    applications: tuple[ClassifiedApplication, ...]
    summary: dict[str, int]
