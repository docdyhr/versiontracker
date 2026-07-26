"""Unmanaged macOS application audit package.

Phase 1: identity-preserving discovery with App Store evidence. Phase 2:
exact Homebrew ownership + blocklist identity resolution. Phase 3: local
auto-update capability detection. Phase 4: audit orchestration
(service.py), terminal rendering, and JSON/YAML/CSV export (rendering.py).
CLI wiring lives in versiontracker/handlers/audit_handlers.py and
versiontracker/cli.py -- see
.claude/plans/versiontracker-unmanaged-apps-handoff.md.
"""

from .auto_update import (
    apply_auto_update_evidence,
    build_launch_agent_index,
    default_launch_agent_dirs,
    resolve_auto_update_evidence,
)
from .blocklist import apply_blocklist_evidence, resolve_blocklist_evidence
from .discovery import (
    configured_discovery_roots,
    default_discovery_roots,
    discover_applications,
    resolve_app_store_evidence,
    resolve_discovery_roots,
)
from .homebrew import apply_homebrew_evidence, build_artifact_index, resolve_homebrew_evidence
from .models import (
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
    EvidenceConfidence,
    EvidenceSource,
    HomebrewEvidence,
    HomebrewStatus,
)
from .rendering import render_csv, render_json, render_terminal, render_yaml
from .service import classify_record, filter_result, run_audit

__all__ = [
    "ApplicationRecord",
    "AppStoreEvidence",
    "AppStoreStatus",
    "AuditBucket",
    "AuditClassification",
    "AuditResult",
    "AutoUpdateEvidence",
    "AutoUpdateMechanism",
    "AutoUpdateStatus",
    "BlocklistEvidence",
    "BlocklistMatchKind",
    "BlocklistStatus",
    "ClassifiedApplication",
    "EvidenceConfidence",
    "EvidenceSource",
    "HomebrewEvidence",
    "HomebrewStatus",
    "apply_auto_update_evidence",
    "apply_blocklist_evidence",
    "apply_homebrew_evidence",
    "build_artifact_index",
    "build_launch_agent_index",
    "classify_record",
    "configured_discovery_roots",
    "default_discovery_roots",
    "default_launch_agent_dirs",
    "discover_applications",
    "filter_result",
    "render_csv",
    "render_json",
    "render_terminal",
    "render_yaml",
    "resolve_app_store_evidence",
    "resolve_auto_update_evidence",
    "resolve_blocklist_evidence",
    "resolve_discovery_roots",
    "resolve_homebrew_evidence",
    "run_audit",
]
