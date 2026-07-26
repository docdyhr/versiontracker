"""Tests for versiontracker.audit.models."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from versiontracker.audit.models import (
    ApplicationRecord,
    AppStoreEvidence,
    AppStoreStatus,
    AutoUpdateEvidence,
    AutoUpdateMechanism,
    AutoUpdateStatus,
    BlocklistEvidence,
    BlocklistMatchKind,
    BlocklistStatus,
    EvidenceConfidence,
    EvidenceSource,
    HomebrewEvidence,
    HomebrewStatus,
)


def _make_app_store_evidence(status: AppStoreStatus = AppStoreStatus.NOT_APP_STORE) -> AppStoreEvidence:
    return AppStoreEvidence(status=status, reason="test reason", source=EvidenceSource.SYSTEM_PROFILER)


def _make_record(**overrides: object) -> ApplicationRecord:
    defaults: dict[str, object] = {
        "name": "Firefox",
        "version": "120.0",
        "path": Path("/Applications/Firefox.app"),
        "canonical_path": Path("/Applications/Firefox.app"),
        "bundle_id": "org.mozilla.firefox",
        "obtained_from": "identified_developer",
        "parent_bundle_path": None,
        "app_store": _make_app_store_evidence(),
    }
    defaults.update(overrides)
    return ApplicationRecord(**defaults)  # type: ignore[arg-type]


class TestFrozenness:
    def test_application_record_is_frozen(self) -> None:
        record = _make_record()
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.name = "Chrome"  # type: ignore[misc]

    def test_app_store_evidence_is_frozen(self) -> None:
        evidence = _make_app_store_evidence()
        with pytest.raises(dataclasses.FrozenInstanceError):
            evidence.status = AppStoreStatus.APP_STORE  # type: ignore[misc]

    def test_homebrew_evidence_is_frozen(self) -> None:
        evidence = HomebrewEvidence.not_evaluated()
        with pytest.raises(dataclasses.FrozenInstanceError):
            evidence.status = HomebrewStatus.MANAGED  # type: ignore[misc]

    def test_auto_update_evidence_is_frozen(self) -> None:
        evidence = AutoUpdateEvidence.not_evaluated()
        with pytest.raises(dataclasses.FrozenInstanceError):
            evidence.status = AutoUpdateStatus.ENABLED  # type: ignore[misc]

    def test_blocklist_evidence_is_frozen(self) -> None:
        evidence = BlocklistEvidence.not_evaluated()
        with pytest.raises(dataclasses.FrozenInstanceError):
            evidence.status = BlocklistStatus.BLOCKED  # type: ignore[misc]

    def test_homebrew_evidence_new_fields_are_frozen(self) -> None:
        evidence = HomebrewEvidence.not_evaluated()
        with pytest.raises(dataclasses.FrozenInstanceError):
            evidence.installed_version = "1.0"  # type: ignore[misc]

    def test_blocklist_evidence_matched_by_is_frozen(self) -> None:
        evidence = BlocklistEvidence.not_evaluated()
        with pytest.raises(dataclasses.FrozenInstanceError):
            evidence.matched_by = BlocklistMatchKind.DISPLAY_NAME  # type: ignore[misc]

    def test_homebrew_evidence_cask_auto_updates_is_frozen(self) -> None:
        evidence = HomebrewEvidence.not_evaluated()
        with pytest.raises(dataclasses.FrozenInstanceError):
            evidence.cask_auto_updates = True  # type: ignore[misc]

    def test_auto_update_evidence_mechanisms_is_frozen(self) -> None:
        evidence = AutoUpdateEvidence.not_evaluated()
        with pytest.raises(dataclasses.FrozenInstanceError):
            evidence.mechanisms = (AutoUpdateMechanism.SPARKLE_FRAMEWORK,)  # type: ignore[misc]


class TestPlaceholderDefaults:
    def test_homebrew_defaults_to_not_evaluated(self) -> None:
        record = _make_record()
        assert record.homebrew.status == HomebrewStatus.NOT_EVALUATED
        assert record.homebrew.source == EvidenceSource.NOT_EVALUATED
        assert record.homebrew.confidence == EvidenceConfidence.NONE

    def test_auto_update_defaults_to_not_evaluated(self) -> None:
        record = _make_record()
        assert record.auto_update.status == AutoUpdateStatus.NOT_EVALUATED
        assert record.auto_update.source == EvidenceSource.NOT_EVALUATED
        assert record.auto_update.confidence == EvidenceConfidence.NONE

    def test_blocklist_defaults_to_not_evaluated(self) -> None:
        record = _make_record()
        assert record.blocklist.status == BlocklistStatus.NOT_EVALUATED
        assert record.blocklist.source == EvidenceSource.NOT_EVALUATED
        assert record.blocklist.confidence == EvidenceConfidence.NONE

    def test_app_store_has_no_default(self) -> None:
        with pytest.raises(TypeError):
            ApplicationRecord(  # type: ignore[call-arg]
                name="Firefox",
                version="120.0",
                path=Path("/Applications/Firefox.app"),
                canonical_path=Path("/Applications/Firefox.app"),
                bundle_id=None,
                obtained_from=None,
                parent_bundle_path=None,
            )

    def test_diagnostics_defaults_to_empty_tuple(self) -> None:
        record = _make_record()
        assert record.diagnostics == ()


class TestNotEvaluatedFactories:
    def test_homebrew_not_evaluated(self) -> None:
        evidence = HomebrewEvidence.not_evaluated()
        assert evidence.status is HomebrewStatus.NOT_EVALUATED
        assert evidence.source is EvidenceSource.NOT_EVALUATED

    def test_auto_update_not_evaluated(self) -> None:
        evidence = AutoUpdateEvidence.not_evaluated()
        assert evidence.status is AutoUpdateStatus.NOT_EVALUATED
        assert evidence.source is EvidenceSource.NOT_EVALUATED

    def test_blocklist_not_evaluated(self) -> None:
        evidence = BlocklistEvidence.not_evaluated()
        assert evidence.status is BlocklistStatus.NOT_EVALUATED
        assert evidence.source is EvidenceSource.NOT_EVALUATED


class TestPhase2Fields:
    """New Phase 2 fields on HomebrewEvidence/BlocklistEvidence."""

    def test_homebrew_evidence_new_fields_default_to_none(self) -> None:
        evidence = HomebrewEvidence.not_evaluated()
        assert evidence.installed_version is None
        assert evidence.artifact_target is None

    def test_homebrew_evidence_new_fields_can_be_populated(self) -> None:
        evidence = HomebrewEvidence(
            status=HomebrewStatus.MANAGED,
            reason="test reason",
            source=EvidenceSource.HOMEBREW_CLI,
            matched_identifier="firefox",
            installed_version="120.0",
            artifact_target=Path("/Applications/Firefox.app"),
        )
        assert evidence.installed_version == "120.0"
        assert evidence.artifact_target == Path("/Applications/Firefox.app")

    def test_blocklist_evidence_matched_by_defaults_to_none(self) -> None:
        evidence = BlocklistEvidence.not_evaluated()
        assert evidence.matched_by is None

    def test_blocklist_evidence_matched_by_can_be_populated(self) -> None:
        evidence = BlocklistEvidence(
            status=BlocklistStatus.BLOCKED,
            reason="test reason",
            source=EvidenceSource.CONFIG,
            matched_identifier="Little Snitch",
            matched_by=BlocklistMatchKind.DISPLAY_NAME,
        )
        assert evidence.matched_by is BlocklistMatchKind.DISPLAY_NAME


class TestPhase3Fields:
    """New Phase 3 fields on HomebrewEvidence/AutoUpdateEvidence."""

    def test_homebrew_evidence_cask_auto_updates_defaults_to_none(self) -> None:
        evidence = HomebrewEvidence.not_evaluated()
        assert evidence.cask_auto_updates is None

    def test_homebrew_evidence_cask_auto_updates_can_be_populated(self) -> None:
        evidence = HomebrewEvidence(
            status=HomebrewStatus.MANAGED,
            reason="test reason",
            source=EvidenceSource.HOMEBREW_CLI,
            cask_auto_updates=True,
        )
        assert evidence.cask_auto_updates is True

    def test_auto_update_evidence_mechanisms_defaults_to_empty_tuple(self) -> None:
        evidence = AutoUpdateEvidence.not_evaluated()
        assert evidence.mechanisms == ()

    def test_auto_update_evidence_mechanisms_can_be_populated(self) -> None:
        evidence = AutoUpdateEvidence(
            status=AutoUpdateStatus.CAPABLE,
            reason="test reason",
            source=EvidenceSource.FILESYSTEM,
            mechanisms=(AutoUpdateMechanism.SPARKLE_FRAMEWORK, AutoUpdateMechanism.ELECTRON_UPDATER_YML),
        )
        assert evidence.mechanisms == (
            AutoUpdateMechanism.SPARKLE_FRAMEWORK,
            AutoUpdateMechanism.ELECTRON_UPDATER_YML,
        )


class TestIdentityAndEquality:
    def test_identity_key_matches_canonical_path_and_bundle_id(self) -> None:
        record = _make_record(bundle_id="org.mozilla.firefox")
        assert record.identity_key == (record.canonical_path, "org.mozilla.firefox")

    def test_equal_records_are_equal_and_hashable(self) -> None:
        record_a = _make_record()
        record_b = _make_record()
        assert record_a == record_b
        assert hash(record_a) == hash(record_b)
        assert len({record_a, record_b}) == 1

    def test_records_with_different_bundle_ids_are_not_equal(self) -> None:
        record_a = _make_record(bundle_id="org.mozilla.firefox")
        record_b = _make_record(bundle_id="org.mozilla.firefox.beta")
        assert record_a != record_b

    def test_is_nested_component_false_when_no_parent(self) -> None:
        record = _make_record(parent_bundle_path=None)
        assert record.is_nested_component is False

    def test_is_nested_component_true_when_parent_set(self) -> None:
        record = _make_record(parent_bundle_path=Path("/Applications/Suite.app"))
        assert record.is_nested_component is True


class TestEnumValueStability:
    """Pins literal enum string values -- guards the future JSON export contract."""

    def test_app_store_status_values(self) -> None:
        assert AppStoreStatus.APP_STORE.value == "app_store"
        assert AppStoreStatus.NOT_APP_STORE.value == "not_app_store"
        assert AppStoreStatus.UNKNOWN.value == "unknown"

    def test_homebrew_status_values(self) -> None:
        assert HomebrewStatus.MANAGED.value == "managed"
        assert HomebrewStatus.AVAILABLE.value == "available"
        assert HomebrewStatus.NOT_AVAILABLE.value == "not_available"
        assert HomebrewStatus.UNKNOWN.value == "unknown"
        assert HomebrewStatus.NOT_EVALUATED.value == "not_evaluated"

    def test_auto_update_status_values(self) -> None:
        assert AutoUpdateStatus.ENABLED.value == "enabled"
        assert AutoUpdateStatus.CAPABLE.value == "capable"
        assert AutoUpdateStatus.NONE_DETECTED.value == "none_detected"
        assert AutoUpdateStatus.UNKNOWN.value == "unknown"
        assert AutoUpdateStatus.NOT_EVALUATED.value == "not_evaluated"

    def test_blocklist_status_values(self) -> None:
        assert BlocklistStatus.BLOCKED.value == "blocked"
        assert BlocklistStatus.NOT_BLOCKED.value == "not_blocked"
        assert BlocklistStatus.UNKNOWN.value == "unknown"
        assert BlocklistStatus.NOT_EVALUATED.value == "not_evaluated"

    def test_blocklist_match_kind_values(self) -> None:
        assert BlocklistMatchKind.CANONICAL_PATH.value == "canonical_path"
        assert BlocklistMatchKind.BUNDLE_ID.value == "bundle_id"
        assert BlocklistMatchKind.HOMEBREW_TOKEN.value == "homebrew_token"
        assert BlocklistMatchKind.DISPLAY_NAME.value == "display_name"

    def test_auto_update_mechanism_values(self) -> None:
        assert AutoUpdateMechanism.SPARKLE_FRAMEWORK.value == "sparkle_framework"
        assert AutoUpdateMechanism.SQUIRREL_FRAMEWORK.value == "squirrel_framework"
        assert AutoUpdateMechanism.ELECTRON_UPDATER_YML.value == "electron_updater_yml"
        assert AutoUpdateMechanism.MOZILLA_UPDATER.value == "mozilla_updater"
        assert AutoUpdateMechanism.VENDOR_LAUNCH_AGENT.value == "vendor_launch_agent"
        assert AutoUpdateMechanism.HOMEBREW_CASK_AUTO_UPDATES.value == "homebrew_cask_auto_updates"

    def test_evidence_source_values(self) -> None:
        assert EvidenceSource.SYSTEM_PROFILER.value == "system_profiler"
        assert EvidenceSource.FILESYSTEM.value == "filesystem"
        assert EvidenceSource.HOMEBREW_CLI.value == "homebrew_cli"
        assert EvidenceSource.CONFIG.value == "config"
        assert EvidenceSource.NOT_EVALUATED.value == "not_evaluated"

    def test_evidence_confidence_values(self) -> None:
        assert EvidenceConfidence.HIGH.value == "high"
        assert EvidenceConfidence.MEDIUM.value == "medium"
        assert EvidenceConfidence.LOW.value == "low"
        assert EvidenceConfidence.NONE.value == "none"
