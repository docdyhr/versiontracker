"""Tests for versiontracker.audit.discovery.

All discovery calls pass an explicit `roots=` (directly, via `hermetic_roots`,
or by monkeypatching default_discovery_roots) so tests never touch the real
machine's /Applications or ~/Applications.
"""

from __future__ import annotations

import plistlib
from pathlib import Path

import versiontracker.audit.discovery as discovery
from versiontracker.audit.discovery import (
    configured_discovery_roots,
    default_discovery_roots,
    discover_applications,
    resolve_app_store_evidence,
    resolve_discovery_roots,
)
from versiontracker.audit.models import (
    AppStoreStatus,
    AutoUpdateStatus,
    BlocklistStatus,
    EvidenceConfidence,
    HomebrewStatus,
)
from versiontracker.config import get_config


class TestRootResolution:
    def test_default_roots_include_applications_and_home_applications(self, monkeypatch, tmp_path) -> None:
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        roots = default_discovery_roots()

        assert roots == [Path("/Applications"), fake_home / "Applications"]

    def test_configured_roots_reads_via_config_get(self, tmp_path) -> None:
        extra = tmp_path / "Extra"
        extra.mkdir()
        get_config().set("additional_app_dirs", [str(extra)])

        roots = configured_discovery_roots()

        assert roots == [extra]

    def test_configured_roots_empty_by_default(self) -> None:
        assert configured_discovery_roots() == []

    def test_resolve_discovery_roots_merges_default_configured_and_extra(self, monkeypatch, tmp_path) -> None:
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        configured_extra = tmp_path / "ConfiguredExtra"
        configured_extra.mkdir()
        get_config().set("additional_app_dirs", [str(configured_extra)])

        cli_extra = tmp_path / "CliExtra"
        cli_extra.mkdir()

        roots = resolve_discovery_roots(extra_roots=[str(cli_extra)])

        assert Path("/Applications").resolve() in roots
        assert (fake_home / "Applications").resolve() in roots
        assert configured_extra.resolve() in roots
        assert cli_extra.resolve() in roots

    def test_resolve_discovery_roots_deduplicates(self, tmp_path) -> None:
        extra = tmp_path / "Dup"
        extra.mkdir()

        roots = resolve_discovery_roots(extra_roots=[str(extra), str(extra)])

        assert roots.count(extra.resolve()) == 1


class TestTopLevelAndNestedDiscovery:
    def test_top_level_app_is_discovered(self, tmp_path, app_bundle_factory) -> None:
        app_bundle_factory(tmp_path, "Firefox")

        records = discover_applications(roots=[tmp_path])

        assert len(records) == 1
        assert records[0].name == "Firefox"
        assert records[0].parent_bundle_path is None

    def test_app_in_explicit_subdirectory_is_discovered(self, tmp_path, app_bundle_factory) -> None:
        suite_dir = tmp_path / "Python 3.12"
        app_bundle_factory(suite_dir, "IDLE")

        records = discover_applications(roots=[tmp_path])

        assert len(records) == 1
        assert records[0].name == "IDLE"
        assert records[0].parent_bundle_path is None

    def test_nested_helper_excluded_by_default(self, tmp_path, app_bundle_factory) -> None:
        main_app = app_bundle_factory(tmp_path, "MainApp")
        app_bundle_factory(main_app / "Contents" / "MacOS", "Helper")

        records = discover_applications(roots=[tmp_path])

        assert {r.name for r in records} == {"MainApp"}

    def test_nested_helper_included_with_flag(self, tmp_path, app_bundle_factory) -> None:
        main_app = app_bundle_factory(tmp_path, "MainApp")
        app_bundle_factory(main_app / "Contents" / "MacOS", "Helper")

        records = discover_applications(roots=[tmp_path], include_nested=True)

        by_name = {r.name: r for r in records}
        assert set(by_name) == {"MainApp", "Helper"}
        assert by_name["MainApp"].parent_bundle_path is None
        assert by_name["Helper"].parent_bundle_path == main_app.resolve()
        assert by_name["Helper"].is_nested_component is True


class TestPathScoping:
    def test_app_outside_all_roots_excluded(self, tmp_path, app_bundle_factory) -> None:
        outside = tmp_path / "outside"
        app_bundle_factory(outside, "Ghost")
        inside = tmp_path / "inside"
        inside.mkdir()

        records = discover_applications(roots=[inside])

        assert records == []

    def test_configured_additional_app_dir_is_scanned(self, tmp_path, app_bundle_factory, monkeypatch) -> None:
        extra = tmp_path / "Extra"
        app_bundle_factory(extra, "SideloadedApp")
        get_config().set("additional_app_dirs", [str(extra)])
        monkeypatch.setattr(discovery, "default_discovery_roots", lambda: [])

        records = discover_applications()

        assert [r.name for r in records] == ["SideloadedApp"]

    def test_extra_roots_param_is_scanned(self, tmp_path, app_bundle_factory, monkeypatch) -> None:
        extra = tmp_path / "CliDir"
        app_bundle_factory(extra, "CliApp")
        monkeypatch.setattr(discovery, "default_discovery_roots", lambda: [])

        records = discover_applications(extra_roots=[str(extra)])

        assert [r.name for r in records] == ["CliApp"]

    def test_home_applications_style_root_is_scanned(self, tmp_path, app_bundle_factory, monkeypatch) -> None:
        fake_home_apps = tmp_path / "home" / "Applications"
        app_bundle_factory(fake_home_apps, "HomeApp")
        monkeypatch.setattr(discovery, "default_discovery_roots", lambda: [fake_home_apps])

        records = discover_applications()

        assert [r.name for r in records] == ["HomeApp"]

    def test_nonexistent_root_is_skipped_without_error(self, tmp_path) -> None:
        missing = tmp_path / "DoesNotExist"

        records = discover_applications(roots=[missing])

        assert records == []


class TestDeduplication:
    def test_same_display_name_different_bundle_id_stay_distinct(self, tmp_path, app_bundle_factory) -> None:
        app_bundle_factory(tmp_path / "A", "Editor", bundle_id="com.vendor.editor.stable")
        app_bundle_factory(tmp_path / "B", "Editor", bundle_id="com.vendor.editor.beta")

        records = discover_applications(roots=[tmp_path])

        assert len(records) == 2
        assert {r.bundle_id for r in records} == {"com.vendor.editor.stable", "com.vendor.editor.beta"}

    def test_identical_bundle_seen_twice_collapses_to_one(self, tmp_path, app_bundle_factory) -> None:
        app_bundle_factory(tmp_path, "Firefox", bundle_id="org.mozilla.firefox")

        records = discover_applications(roots=[tmp_path, tmp_path])

        assert len(records) == 1


class TestAppStoreEvidenceResolution:
    def test_mac_app_store_with_receipt_is_high_confidence(
        self, tmp_path, app_bundle_factory, sp_entry_factory, sp_data_factory
    ) -> None:
        bundle = app_bundle_factory(tmp_path, "StoreApp", has_mas_receipt=True)
        sp = sp_data_factory(sp_entry_factory(bundle, obtained_from="mac_app_store"))

        records = discover_applications(roots=[tmp_path], system_profiler_data=sp)

        evidence = records[0].app_store
        assert evidence.status == AppStoreStatus.APP_STORE
        assert evidence.confidence == EvidenceConfidence.HIGH

    def test_ios_app_store_with_receipt_is_app_store(
        self, tmp_path, app_bundle_factory, sp_entry_factory, sp_data_factory
    ) -> None:
        bundle = app_bundle_factory(tmp_path, "IOSApp", has_mas_receipt=True)
        sp = sp_data_factory(sp_entry_factory(bundle, obtained_from="ios_app_store"))

        records = discover_applications(roots=[tmp_path], system_profiler_data=sp)

        assert records[0].app_store.status == AppStoreStatus.APP_STORE

    def test_apple_obtained_from_without_receipt_is_not_app_store(
        self, tmp_path, app_bundle_factory, sp_entry_factory, sp_data_factory
    ) -> None:
        bundle = app_bundle_factory(tmp_path, "AppleUtility", has_mas_receipt=False)
        sp = sp_data_factory(sp_entry_factory(bundle, obtained_from="apple"))

        records = discover_applications(roots=[tmp_path], system_profiler_data=sp)

        evidence = records[0].app_store
        assert evidence.status == AppStoreStatus.NOT_APP_STORE
        assert evidence.confidence == EvidenceConfidence.HIGH

    def test_receipt_present_overrides_conflicting_obtained_from(
        self, tmp_path, app_bundle_factory, sp_entry_factory, sp_data_factory
    ) -> None:
        bundle = app_bundle_factory(tmp_path, "Weird", has_mas_receipt=True)
        sp = sp_data_factory(sp_entry_factory(bundle, obtained_from="identified_developer"))

        records = discover_applications(roots=[tmp_path], system_profiler_data=sp)

        evidence = records[0].app_store
        assert evidence.status == AppStoreStatus.APP_STORE
        assert evidence.confidence == EvidenceConfidence.MEDIUM

    def test_missing_obtained_from_resolved_from_receipt_alone(self, tmp_path, app_bundle_factory) -> None:
        app_bundle_factory(tmp_path, "NoMetadata", has_mas_receipt=True)

        records = discover_applications(roots=[tmp_path])

        evidence = records[0].app_store
        assert evidence.status == AppStoreStatus.APP_STORE
        assert evidence.confidence == EvidenceConfidence.MEDIUM

    def test_no_signals_at_all_is_not_app_store_medium_confidence(self, tmp_path, app_bundle_factory) -> None:
        app_bundle_factory(tmp_path, "PlainApp", has_mas_receipt=False)

        records = discover_applications(roots=[tmp_path])

        evidence = records[0].app_store
        assert evidence.status == AppStoreStatus.NOT_APP_STORE
        assert evidence.confidence == EvidenceConfidence.MEDIUM

    def test_app_store_apps_are_still_returned_not_dropped(
        self, tmp_path, app_bundle_factory, sp_entry_factory, sp_data_factory
    ) -> None:
        bundle = app_bundle_factory(tmp_path, "StoreApp", has_mas_receipt=True)
        sp = sp_data_factory(sp_entry_factory(bundle, obtained_from="mac_app_store"))

        records = discover_applications(roots=[tmp_path], system_profiler_data=sp)

        assert len(records) == 1
        assert records[0].app_store.status == AppStoreStatus.APP_STORE

    def test_mac_app_store_without_receipt_is_medium_confidence(
        self, tmp_path, app_bundle_factory, sp_entry_factory, sp_data_factory
    ) -> None:
        bundle = app_bundle_factory(tmp_path, "StaleReceiptApp", has_mas_receipt=False)
        sp = sp_data_factory(sp_entry_factory(bundle, obtained_from="mac_app_store"))

        records = discover_applications(roots=[tmp_path], system_profiler_data=sp)

        evidence = records[0].app_store
        assert evidence.status == AppStoreStatus.APP_STORE
        assert evidence.confidence == EvidenceConfidence.MEDIUM

    def test_receipt_probe_failure_yields_unknown(self, tmp_path, app_bundle_factory, monkeypatch) -> None:
        bundle = app_bundle_factory(tmp_path, "Locked", has_mas_receipt=True)

        def raise_os_error(self: Path, *args: object, **kwargs: object) -> bool:
            raise OSError("permission denied")

        monkeypatch.setattr(Path, "exists", raise_os_error)

        evidence = resolve_app_store_evidence(bundle, "apple")

        assert evidence.status == AppStoreStatus.UNKNOWN
        assert evidence.confidence == EvidenceConfidence.NONE
        assert evidence.error is not None


class TestMalformedEntries:
    def test_missing_info_plist_kept_with_diagnostics(self, tmp_path, app_bundle_factory) -> None:
        app_bundle_factory(tmp_path, "Broken", write_plist=False)

        records = discover_applications(roots=[tmp_path])

        assert len(records) == 1
        record = records[0]
        assert record.name == "Broken"  # falls back to the bundle's filename stem
        assert "missing or empty version" in record.diagnostics
        assert "missing bundle identifier" in record.diagnostics

    def test_info_plist_read_failure_returns_empty_and_does_not_raise(
        self, tmp_path, app_bundle_factory, monkeypatch
    ) -> None:
        bundle = app_bundle_factory(tmp_path, "Locked")

        def raise_permission_error(self: Path, *args: object, **kwargs: object) -> object:
            raise PermissionError("denied")

        monkeypatch.setattr(Path, "open", raise_permission_error)

        result = discovery._read_info_plist(bundle)

        assert result == {}

    def test_malformed_xml_plist_returns_empty_and_does_not_raise(self, tmp_path, app_bundle_factory) -> None:
        """Regression: confirmed live on a real machine that a genuinely
        corrupt plist raises xml.parsers.expat.ExpatError via plistlib's XML
        parser -- distinct from (and not caught by) OSError/ValueError/
        plistlib.InvalidFileException."""
        bundle = app_bundle_factory(tmp_path, "Corrupt", write_plist=False)
        contents = bundle / "Contents"
        contents.mkdir(parents=True, exist_ok=True)
        (contents / "Info.plist").write_text(
            "<?xml version='1.0'?><plist><dict><key>Foo</key><not-closed></plist>", encoding="utf-8"
        )

        result = discovery._read_info_plist(bundle)

        assert result == {}


class TestEnrichmentPriority:
    def test_system_profiler_name_and_version_take_priority_over_info_plist(
        self, tmp_path, app_bundle_factory, sp_entry_factory, sp_data_factory
    ) -> None:
        bundle = app_bundle_factory(tmp_path, "PlistName", version="1.0")
        sp = sp_data_factory(sp_entry_factory(bundle, name="SystemProfilerName", version="2.0"))

        records = discover_applications(roots=[tmp_path], system_profiler_data=sp)

        assert records[0].name == "SystemProfilerName"
        assert records[0].version == "2.0"

    def test_bundle_id_from_system_profiler_entry_is_used(
        self, tmp_path, app_bundle_factory, sp_entry_factory, sp_data_factory
    ) -> None:
        bundle = app_bundle_factory(tmp_path, "Editor", bundle_id="com.example.plist-id")
        sp = sp_data_factory(sp_entry_factory(bundle, bundle_id="com.example.sp-id"))

        records = discover_applications(roots=[tmp_path], system_profiler_data=sp)

        assert records[0].bundle_id == "com.example.sp-id"

    def test_cfbundleversion_used_when_short_version_string_missing(self, tmp_path) -> None:
        bundle_path = tmp_path / "LegacyApp.app"
        contents = bundle_path / "Contents"
        contents.mkdir(parents=True)
        with (contents / "Info.plist").open("wb") as f:
            plistlib.dump({"CFBundleName": "LegacyApp", "CFBundleVersion": "42"}, f)

        records = discover_applications(roots=[tmp_path])

        assert records[0].version == "42"


class TestPlaceholderEvidenceOnRecords:
    def test_discovered_record_has_not_evaluated_placeholders(self, tmp_path, app_bundle_factory) -> None:
        app_bundle_factory(tmp_path, "Firefox")

        records = discover_applications(roots=[tmp_path])

        record = records[0]
        assert record.homebrew.status == HomebrewStatus.NOT_EVALUATED
        assert record.auto_update.status == AutoUpdateStatus.NOT_EVALUATED
        assert record.blocklist.status == BlocklistStatus.NOT_EVALUATED


class TestNoLegacyRegressions:
    def test_testapp_prefixed_name_is_not_rewritten(self, tmp_path, app_bundle_factory) -> None:
        app_bundle_factory(tmp_path, "TestApp123", bundle_id="com.example.testapp123")

        records = discover_applications(roots=[tmp_path])

        assert records[0].name == "TestApp123"

    def test_digits_in_name_are_preserved(self, tmp_path, app_bundle_factory) -> None:
        app_bundle_factory(tmp_path, "Python 3.12", bundle_id="org.python.python312")

        records = discover_applications(roots=[tmp_path])

        assert records[0].name == "Python 3.12"


class TestInternalHelpers:
    """Direct tests for small private helpers whose defensive branches are
    impractical to trigger through a full discover_applications() run."""

    def test_nearest_parent_bundle_returns_none_for_unrelated_path(self, tmp_path) -> None:
        unrelated = Path("/some/unrelated/tree/App.app")

        assert discovery._nearest_parent_bundle(unrelated, tmp_path) is None

    def test_log_walk_error_does_not_raise(self) -> None:
        discovery._log_walk_error(OSError("simulated permission error"))
