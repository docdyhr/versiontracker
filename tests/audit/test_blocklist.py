"""Tests for versiontracker.audit.blocklist."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import versiontracker.audit.blocklist as blocklist_module
from versiontracker.audit.blocklist import apply_blocklist_evidence, resolve_blocklist_evidence
from versiontracker.audit.models import (
    ApplicationRecord,
    AppStoreEvidence,
    AppStoreStatus,
    BlocklistMatchKind,
    BlocklistStatus,
    EvidenceSource,
    HomebrewEvidence,
    HomebrewStatus,
)
from versiontracker.config import get_config
from versiontracker.exceptions import ConfigError


def _make_record(
    *,
    name: str = "Little Snitch",
    canonical_path: Path = Path("/Applications/Little Snitch.app"),
    bundle_id: str | None = None,
    homebrew: HomebrewEvidence | None = None,
) -> ApplicationRecord:
    kwargs: dict[str, Any] = {
        "name": name,
        "version": "1.0",
        "path": canonical_path,
        "canonical_path": canonical_path,
        "bundle_id": bundle_id,
        "obtained_from": None,
        "parent_bundle_path": None,
        "app_store": AppStoreEvidence(
            status=AppStoreStatus.NOT_APP_STORE, reason="test", source=EvidenceSource.SYSTEM_PROFILER
        ),
    }
    if homebrew is not None:
        kwargs["homebrew"] = homebrew
    return ApplicationRecord(**kwargs)


def _managed_homebrew_evidence(token: str) -> HomebrewEvidence:
    return HomebrewEvidence(
        status=HomebrewStatus.MANAGED,
        reason="test",
        source=EvidenceSource.HOMEBREW_CLI,
        matched_identifier=token,
    )


class TestResolveBlocklistEvidenceMatrixRows:
    """The three required-test-matrix rows, plus the path row from Acceptance Criteria."""

    def test_blocklist_by_display_name(self) -> None:
        record = _make_record(name="Little Snitch")

        evidence = resolve_blocklist_evidence(record, ["Little Snitch"])

        assert evidence.status == BlocklistStatus.BLOCKED
        assert evidence.matched_by == BlocklistMatchKind.DISPLAY_NAME
        assert evidence.matched_identifier == "Little Snitch"

    def test_blocklist_by_bundle_id(self) -> None:
        record = _make_record(name="Little Snitch", bundle_id="at.obdev.littlesnitch")

        evidence = resolve_blocklist_evidence(record, ["at.obdev.littlesnitch"])

        assert evidence.status == BlocklistStatus.BLOCKED
        assert evidence.matched_by == BlocklistMatchKind.BUNDLE_ID

    def test_blocklist_by_cask_token(self) -> None:
        record = _make_record(name="Visual Studio Code", homebrew=_managed_homebrew_evidence("visual-studio-code"))

        evidence = resolve_blocklist_evidence(record, ["visual-studio-code"])

        assert evidence.status == BlocklistStatus.BLOCKED
        assert evidence.matched_by == BlocklistMatchKind.HOMEBREW_TOKEN

    def test_blocklist_by_canonical_path(self) -> None:
        record = _make_record(canonical_path=Path("/Applications/Little Snitch.app").resolve())

        evidence = resolve_blocklist_evidence(record, ["/Applications/Little Snitch.app"])

        assert evidence.status == BlocklistStatus.BLOCKED
        assert evidence.matched_by == BlocklistMatchKind.CANONICAL_PATH


class TestResolveBlocklistEvidenceNoMatch:
    def test_no_match_is_not_blocked(self) -> None:
        record = _make_record(name="Firefox")

        evidence = resolve_blocklist_evidence(record, ["Little Snitch", "Microsoft Defender"])

        assert evidence.status == BlocklistStatus.NOT_BLOCKED

    def test_empty_blocklist_is_not_blocked(self) -> None:
        record = _make_record()

        evidence = resolve_blocklist_evidence(record, [])

        assert evidence.status == BlocklistStatus.NOT_BLOCKED

    def test_non_string_entries_are_skipped_defensively(self) -> None:
        record = _make_record(name="Firefox")

        evidence = resolve_blocklist_evidence(record, [123, None, {"a": 1}, "Little Snitch"])  # type: ignore[list-item]

        assert evidence.status == BlocklistStatus.NOT_BLOCKED


class TestResolveBlocklistEvidenceTierPriority:
    def test_bundle_id_wins_over_display_name(self) -> None:
        record = _make_record(name="Firefox", bundle_id="Firefox")

        evidence = resolve_blocklist_evidence(record, ["Firefox"])

        assert evidence.matched_by == BlocklistMatchKind.BUNDLE_ID

    def test_canonical_path_wins_over_bundle_id(self) -> None:
        path = Path("/Applications/App.app").resolve()
        record = _make_record(canonical_path=path, bundle_id=str(path))

        evidence = resolve_blocklist_evidence(record, [str(path)])

        assert evidence.matched_by == BlocklistMatchKind.CANONICAL_PATH

    def test_falls_through_non_matching_tiers_to_display_name(self) -> None:
        """bundle_id and Homebrew token are both present but don't match any
        entry -- must fall all the way through to the weakest (display name)
        tier rather than stopping at the first non-empty tier it checks."""
        record = _make_record(
            name="Little Snitch",
            bundle_id="at.obdev.littlesnitch",
            homebrew=_managed_homebrew_evidence("little-snitch"),
        )

        evidence = resolve_blocklist_evidence(record, ["some-other-token", "Little Snitch"])

        assert evidence.status == BlocklistStatus.BLOCKED
        assert evidence.matched_by == BlocklistMatchKind.DISPLAY_NAME


class TestResolveBlocklistEvidenceCwdRegression:
    def test_relative_entry_does_not_match_via_cwd(self, monkeypatch, tmp_path) -> None:
        """Regression: a bare relative blocklist entry must never be resolved
        against the process's cwd -- otherwise the same config could match or
        not match depending on where versiontracker happens to be launched
        from. cwd is set to the app's own parent directory, so a naive
        Path(entry).resolve() would accidentally match if the guard were
        missing."""
        app_dir = tmp_path / "Applications"
        app_dir.mkdir()
        canonical_path = (app_dir / "Keynote.app").resolve()
        monkeypatch.chdir(app_dir)
        record = _make_record(name="Keynote App", canonical_path=canonical_path)

        # "Keynote.app" is a bare relative fragment -- meant as a (wrong)
        # display-name typo, not a path -- and must NOT match via
        # cwd-relative resolution.
        evidence = resolve_blocklist_evidence(record, ["Keynote.app"])

        assert evidence.status == BlocklistStatus.NOT_BLOCKED

    def test_absolute_entry_still_matches_regardless_of_cwd(self, monkeypatch, tmp_path) -> None:
        app_dir = tmp_path / "Applications"
        app_dir.mkdir()
        canonical_path = (app_dir / "Keynote.app").resolve()
        monkeypatch.chdir(tmp_path)  # deliberately not the app's own directory
        record = _make_record(name="Keynote App", canonical_path=canonical_path)

        evidence = resolve_blocklist_evidence(record, [str(canonical_path)])

        assert evidence.status == BlocklistStatus.BLOCKED
        assert evidence.matched_by == BlocklistMatchKind.CANONICAL_PATH


class TestPathEntryPermissionErrorGracefulDegradation:
    """_try_resolve_path_entry() catches (OSError, RuntimeError, ValueError)
    around Path.resolve() -- PermissionError is a real OSError subtype a
    user-controlled config entry can trigger (e.g. an unreadable mount
    point), but nothing exercised that except-clause until now."""

    def test_permission_error_falls_through_to_next_tier(self, monkeypatch) -> None:
        def _raise_permission_error(self: Path) -> Path:
            raise PermissionError("denied")

        monkeypatch.setattr(Path, "resolve", _raise_permission_error)
        record = _make_record(name="Test App", bundle_id="com.example.testapp")

        evidence = resolve_blocklist_evidence(record, ["/Applications/Unreadable Mount/App.app", "com.example.testapp"])

        assert evidence.status == BlocklistStatus.BLOCKED
        assert evidence.matched_by == BlocklistMatchKind.BUNDLE_ID


class TestHomebrewTokenTierGracefulDegradation:
    """No service.py enforces resolution order in this phase -- blocklist
    resolution must tolerate running before Homebrew resolution."""

    def test_unresolved_homebrew_evidence_does_not_crash_and_skips_to_next_tier(self) -> None:
        record = _make_record(name="Visual Studio Code")  # homebrew defaults to NOT_EVALUATED

        evidence = resolve_blocklist_evidence(record, ["visual-studio-code"])

        assert evidence.status == BlocklistStatus.NOT_BLOCKED

    def test_matches_once_homebrew_evidence_is_resolved(self) -> None:
        record = _make_record(name="Visual Studio Code", homebrew=_managed_homebrew_evidence("visual-studio-code"))

        evidence = resolve_blocklist_evidence(record, ["visual-studio-code"])

        assert evidence.status == BlocklistStatus.BLOCKED
        assert evidence.matched_by == BlocklistMatchKind.HOMEBREW_TOKEN


class TestApplyBlocklistEvidence:
    def test_explicit_entries_used_when_given(self) -> None:
        record = _make_record(name="Firefox")

        result = apply_blocklist_evidence([record], ["Firefox"])

        assert result[0].blocklist.status == BlocklistStatus.BLOCKED

    def test_defaults_to_config_get_blocklist(self) -> None:
        get_config().set("blocklist", ["Firefox"])
        record = _make_record(name="Firefox")

        result = apply_blocklist_evidence([record])

        assert result[0].blocklist.status == BlocklistStatus.BLOCKED

    def test_config_error_degrades_every_record_to_unknown(self, monkeypatch) -> None:
        def raise_config_error() -> None:
            raise ConfigError("malformed config")

        monkeypatch.setattr(blocklist_module, "get_config", raise_config_error)
        records = [_make_record(name="A"), _make_record(name="B")]

        result = apply_blocklist_evidence(records)

        assert all(r.blocklist.status == BlocklistStatus.UNKNOWN for r in result)
        assert all(r.blocklist.error is not None for r in result)

    def test_original_records_are_not_mutated(self) -> None:
        record = _make_record(name="Firefox")

        apply_blocklist_evidence([record], ["Firefox"])

        assert record.blocklist.status == BlocklistStatus.NOT_EVALUATED
