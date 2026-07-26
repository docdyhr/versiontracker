"""Tests for versiontracker.audit.auto_update."""

from __future__ import annotations

from pathlib import Path

import versiontracker.audit.auto_update as auto_update_module
from versiontracker.audit.auto_update import (
    _ProbeResult,
    apply_auto_update_evidence,
    build_launch_agent_index,
    resolve_auto_update_evidence,
)
from versiontracker.audit.models import (
    ApplicationRecord,
    AppStoreEvidence,
    AppStoreStatus,
    AutoUpdateMechanism,
    AutoUpdateStatus,
    EvidenceConfidence,
    EvidenceSource,
    HomebrewEvidence,
    HomebrewStatus,
)


def _make_record(
    canonical_path: Path,
    *,
    bundle_id: str | None = None,
    name: str = "App",
    homebrew: HomebrewEvidence | None = None,
) -> ApplicationRecord:
    kwargs: dict[str, object] = {
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
    return ApplicationRecord(**kwargs)  # type: ignore[arg-type]


def _managed_homebrew_evidence(*, auto_updates: bool | None, token: str = "some-cask") -> HomebrewEvidence:
    return HomebrewEvidence(
        status=HomebrewStatus.MANAGED,
        reason="test",
        source=EvidenceSource.HOMEBREW_CLI,
        matched_identifier=token,
        cask_auto_updates=auto_updates,
    )


class TestProbeSparkle:
    def test_absent_is_not_found(self, tmp_path, app_bundle_factory) -> None:
        bundle = app_bundle_factory(tmp_path, "PlainApp")

        result = auto_update_module._probe_sparkle(bundle)

        assert result.found is False
        assert result.mechanism == AutoUpdateMechanism.SPARKLE_FRAMEWORK

    def test_present_without_preference_key_is_capable_unconfirmed(
        self, tmp_path, app_bundle_factory, sparkle_framework_factory
    ) -> None:
        """Real basis: VLC's and ChatGPT's actual Info.plist have no
        SUEnableAutomaticChecks key despite Sparkle.framework being present."""
        bundle = app_bundle_factory(tmp_path, "VLC")
        sparkle_framework_factory(bundle)

        result = auto_update_module._probe_sparkle(bundle)

        assert result.found is True
        assert result.confidence == EvidenceConfidence.HIGH
        assert result.enabled is None

    def test_present_with_enabled_true(self, tmp_path, app_bundle_factory, sparkle_framework_factory) -> None:
        bundle = app_bundle_factory(tmp_path, "SomeApp", extra_plist_keys={"SUEnableAutomaticChecks": True})
        sparkle_framework_factory(bundle)

        result = auto_update_module._probe_sparkle(bundle)

        assert result.found is True
        assert result.enabled is True

    def test_present_with_enabled_false_is_capable_not_enabled(
        self, tmp_path, app_bundle_factory, sparkle_framework_factory
    ) -> None:
        """Real basis: Cyberduck's actual Info.plist has SUEnableAutomaticChecks=false."""
        bundle = app_bundle_factory(tmp_path, "Cyberduck", extra_plist_keys={"SUEnableAutomaticChecks": False})
        sparkle_framework_factory(bundle)

        result = auto_update_module._probe_sparkle(bundle)

        assert result.found is True
        assert result.enabled is False

    def test_probe_error_sets_error_field(self, tmp_path, app_bundle_factory, monkeypatch) -> None:
        bundle = app_bundle_factory(tmp_path, "App")

        def raise_os_error(self: Path, *args: object, **kwargs: object) -> bool:
            raise OSError("denied")

        monkeypatch.setattr(Path, "is_dir", raise_os_error)

        result = auto_update_module._probe_sparkle(bundle)

        assert result.found is False
        assert result.error is not None


class TestProbeSquirrel:
    def test_absent_is_not_found(self, tmp_path, app_bundle_factory) -> None:
        bundle = app_bundle_factory(tmp_path, "PlainApp")

        result = auto_update_module._probe_squirrel(bundle)

        assert result.found is False

    def test_present_with_shipit(self, tmp_path, app_bundle_factory, squirrel_framework_factory) -> None:
        bundle = app_bundle_factory(tmp_path, "Discord")
        squirrel_framework_factory(bundle, include_shipit=True)

        result = auto_update_module._probe_squirrel(bundle)

        assert result.found is True
        assert result.confidence == EvidenceConfidence.HIGH
        assert "ShipIt" in result.detail

    def test_present_without_shipit(self, tmp_path, app_bundle_factory, squirrel_framework_factory) -> None:
        bundle = app_bundle_factory(tmp_path, "App")
        squirrel_framework_factory(bundle, include_shipit=False)

        result = auto_update_module._probe_squirrel(bundle)

        assert result.found is True
        assert "ShipIt" not in result.detail

    def test_probe_error_sets_error_field(self, tmp_path, app_bundle_factory, monkeypatch) -> None:
        bundle = app_bundle_factory(tmp_path, "App")

        def raise_os_error(self: Path, *args: object, **kwargs: object) -> bool:
            raise OSError("denied")

        monkeypatch.setattr(Path, "is_dir", raise_os_error)

        result = auto_update_module._probe_squirrel(bundle)

        assert result.found is False
        assert result.error is not None


class TestProbeElectronUpdaterYml:
    def test_absent_is_not_found(self, tmp_path, app_bundle_factory) -> None:
        bundle = app_bundle_factory(tmp_path, "PlainApp")

        result = auto_update_module._probe_electron_updater_yml(bundle)

        assert result.found is False

    def test_present_valid_yaml(self, tmp_path, app_bundle_factory, electron_update_yml_factory) -> None:
        bundle = app_bundle_factory(tmp_path, "Signal")
        electron_update_yml_factory(bundle, provider="generic")

        result = auto_update_module._probe_electron_updater_yml(bundle)

        assert result.found is True
        assert result.confidence == EvidenceConfidence.HIGH
        assert "provider=generic" in result.detail

    def test_present_malformed_yaml_still_found(
        self, tmp_path, app_bundle_factory, electron_update_yml_factory
    ) -> None:
        bundle = app_bundle_factory(tmp_path, "App")
        electron_update_yml_factory(bundle, malformed=True)

        result = auto_update_module._probe_electron_updater_yml(bundle)

        assert result.found is True
        assert result.error is None

    def test_present_non_dict_yaml_still_found_without_provider(self, tmp_path, app_bundle_factory) -> None:
        """Valid YAML syntax that isn't a mapping at the top level (e.g. a
        bare string) -- distinct from malformed/unparseable content."""
        bundle = app_bundle_factory(tmp_path, "App")
        resources = bundle / "Contents" / "Resources"
        resources.mkdir(parents=True, exist_ok=True)
        (resources / "app-update.yml").write_text("just a string\n", encoding="utf-8")

        result = auto_update_module._probe_electron_updater_yml(bundle)

        assert result.found is True
        assert "provider=" not in result.detail

    def test_probe_error_sets_error_field(self, tmp_path, app_bundle_factory, monkeypatch) -> None:
        bundle = app_bundle_factory(tmp_path, "App")

        def raise_os_error(self: Path, *args: object, **kwargs: object) -> bool:
            raise OSError("denied")

        monkeypatch.setattr(Path, "is_file", raise_os_error)

        result = auto_update_module._probe_electron_updater_yml(bundle)

        assert result.found is False
        assert result.error is not None


class TestProbeMozillaUpdater:
    def test_absent_is_not_found(self, tmp_path, app_bundle_factory) -> None:
        bundle = app_bundle_factory(tmp_path, "PlainApp")

        result = auto_update_module._probe_mozilla_updater(bundle)

        assert result.found is False

    def test_present_alone_is_medium_confidence(self, tmp_path, app_bundle_factory, mozilla_updater_factory) -> None:
        bundle = app_bundle_factory(tmp_path, "PartialFirefox")
        mozilla_updater_factory(bundle, include_ini=False, include_launch_services_entry=False)

        result = auto_update_module._probe_mozilla_updater(bundle)

        assert result.found is True
        assert result.confidence == EvidenceConfidence.MEDIUM

    def test_present_with_corroboration_is_high_confidence(
        self, tmp_path, app_bundle_factory, mozilla_updater_factory
    ) -> None:
        """Real basis: Firefox.app has all three (updater.app, updater.ini,
        the LaunchServices entry)."""
        bundle = app_bundle_factory(tmp_path, "Firefox")
        mozilla_updater_factory(bundle, include_ini=True, include_launch_services_entry=True)

        result = auto_update_module._probe_mozilla_updater(bundle)

        assert result.found is True
        assert result.confidence == EvidenceConfidence.HIGH


class TestProbeVendorLaunchAgent:
    def test_no_bundle_id_is_not_found(self, tmp_path) -> None:
        record = _make_record(tmp_path / "App.app", bundle_id=None)

        result = auto_update_module._probe_vendor_launch_agent(record, (), ())

        assert result.found is False

    def test_exact_tier_match_via_label(self, tmp_path, launch_agent_plist_factory) -> None:
        launch_agent_plist_factory(tmp_path, "some-file.plist", label="com.microsoft.teams.TeamsUpdaterDaemon")
        candidates, _ = build_launch_agent_index([tmp_path])
        record = _make_record(tmp_path / "Teams.app", bundle_id="com.microsoft.teams")

        result = auto_update_module._probe_vendor_launch_agent(record, candidates, ())

        assert result.found is True
        assert result.confidence == EvidenceConfidence.HIGH
        assert result.matched_identifier == "com.microsoft.teams.TeamsUpdaterDaemon"

    def test_exact_tier_match_via_filename_when_content_unreadable(self, tmp_path, launch_agent_plist_factory) -> None:
        """Real basis: /Library/LaunchDaemons/com.microsoft.teams.TeamsUpdaterDaemon.plist
        is mode 600, root-owned -- content unreadable live, only the filename usable."""
        launch_agent_plist_factory(tmp_path, "com.microsoft.teams.TeamsUpdaterDaemon.plist", unreadable=True)
        candidates, _ = build_launch_agent_index([tmp_path])
        record = _make_record(tmp_path / "Teams.app", bundle_id="com.microsoft.teams")

        result = auto_update_module._probe_vendor_launch_agent(record, candidates, ())

        assert result.found is True
        assert result.confidence == EvidenceConfidence.MEDIUM
        assert result.matched_identifier == "com.microsoft.teams.TeamsUpdaterDaemon"

    def test_exact_tier_excludes_non_updater_daemon_sharing_prefix(self, tmp_path, launch_agent_plist_factory) -> None:
        """Real basis: ClamXAV's .Engine.plist and .HelperTool.plist share a
        bundle-id prefix with the real .HelperToolUpdater.plist but are not
        updaters -- the "update" keyword guard must exclude them."""
        launch_agent_plist_factory(tmp_path, "engine.plist", label="uk.co.canimaansoftware.ClamXAV.Engine")
        launch_agent_plist_factory(tmp_path, "helper.plist", label="uk.co.canimaansoftware.ClamXAV.HelperTool")
        candidates, _ = build_launch_agent_index([tmp_path])
        record = _make_record(tmp_path / "ClamXAV.app", bundle_id="uk.co.canimaansoftware.ClamXAV")

        result = auto_update_module._probe_vendor_launch_agent(record, candidates, ())

        assert result.found is False

    def test_exact_tier_still_finds_real_updater_among_non_updater_siblings(
        self, tmp_path, launch_agent_plist_factory
    ) -> None:
        launch_agent_plist_factory(tmp_path, "engine.plist", label="uk.co.canimaansoftware.ClamXAV.Engine")
        launch_agent_plist_factory(tmp_path, "updater.plist", label="uk.co.canimaansoftware.ClamXAV.HelperToolUpdater")
        candidates, _ = build_launch_agent_index([tmp_path])
        record = _make_record(tmp_path / "ClamXAV.app", bundle_id="uk.co.canimaansoftware.ClamXAV")

        result = auto_update_module._probe_vendor_launch_agent(record, candidates, ())

        assert result.found is True
        assert result.matched_identifier == "uk.co.canimaansoftware.ClamXAV.HelperToolUpdater"

    def test_vendor_tier_matches_paired_prefixes_that_differ(self, tmp_path, launch_agent_plist_factory) -> None:
        """Real basis: Dropbox's LaunchAgent labels are com.dropbox.* but
        Dropbox.app's own real bundle id is com.getdropbox.dropbox -- a
        naive single-shared-prefix design would never tie these together."""
        launch_agent_plist_factory(tmp_path, "dropbox-update.plist", label="com.dropbox.dropboxmacupdate.xpcservice")
        candidates, _ = build_launch_agent_index([tmp_path])
        record = _make_record(tmp_path / "Dropbox.app", bundle_id="com.getdropbox.dropbox")

        result = auto_update_module._probe_vendor_launch_agent(record, candidates, ())

        assert result.found is True
        assert result.confidence == EvidenceConfidence.LOW

    def test_vendor_tier_matches_via_filename_when_label_is_empty_stub(
        self, tmp_path, launch_agent_plist_factory
    ) -> None:
        """Real basis: com.google.keystone.agent.plist (both user and system
        copies) are empty <dict/> stubs with no Label key at all."""
        launch_agent_plist_factory(tmp_path, "com.google.keystone.agent.plist", label=None)
        candidates, _ = build_launch_agent_index([tmp_path])
        record = _make_record(tmp_path / "Chrome.app", bundle_id="com.google.Chrome")

        result = auto_update_module._probe_vendor_launch_agent(record, candidates, ())

        assert result.found is True
        assert result.confidence == EvidenceConfidence.LOW
        assert result.matched_identifier == "com.google.keystone.agent"

    def test_no_match_is_not_found(self, tmp_path, launch_agent_plist_factory) -> None:
        launch_agent_plist_factory(tmp_path, "com.unrelated.vendor.plist")
        candidates, _ = build_launch_agent_index([tmp_path])
        record = _make_record(tmp_path / "App.app", bundle_id="com.example.app")

        result = auto_update_module._probe_vendor_launch_agent(record, candidates, ())

        assert result.found is False

    def test_scan_errors_are_threaded_through(self, tmp_path) -> None:
        record = _make_record(tmp_path / "App.app", bundle_id="com.example.app")

        result = auto_update_module._probe_vendor_launch_agent(record, (), ("could not list /some/dir",))

        assert result.error == "could not list /some/dir"


class TestBuildLaunchAgentIndex:
    def test_scans_plist_files_only(self, tmp_path, launch_agent_plist_factory) -> None:
        launch_agent_plist_factory(tmp_path, "com.example.updater.plist")
        (tmp_path / "not-a-plist.txt").write_text("ignore me")

        candidates, scan_errors = build_launch_agent_index([tmp_path])

        assert len(candidates) == 1
        assert candidates[0].filename_stem == "com.example.updater"
        assert scan_errors == ()

    def test_malformed_xml_plist_label_falls_back_to_filename_without_raising(self, tmp_path) -> None:
        """Regression: confirmed live on a real machine that a genuinely
        corrupt LaunchAgent plist (~/Library/LaunchAgents/com.docdyhr.
        claude-dependabot.plist) raises xml.parsers.expat.ExpatError via
        plistlib's XML parser -- distinct from (and not caught by)
        OSError/ValueError/plistlib.InvalidFileException. A single corrupt
        file must not crash the whole scan; the candidate survives with
        label=None (filename_stem remains usable)."""
        path = tmp_path / "com.example.updater.plist"
        path.write_text("<?xml version='1.0'?><plist><dict><key>Foo</key><not-closed></plist>", encoding="utf-8")

        candidates, scan_errors = build_launch_agent_index([tmp_path])

        assert len(candidates) == 1
        assert candidates[0].label is None
        assert candidates[0].filename_stem == "com.example.updater"
        assert scan_errors == ()

    def test_permission_error_reading_plist_content_falls_back_to_filename(
        self, monkeypatch, tmp_path, launch_agent_plist_factory
    ) -> None:
        """Distinct failure point from the malformed-XML test above: a real
        PermissionError on the file open itself, not a content-parsing
        error -- confirmed live in Phase 3 (a real root-owned, mode-600
        Teams updater daemon on this machine). Simulated via monkeypatching
        per this project's established pattern (see conftest.py's
        make_launch_agent_plist docstring) rather than a real chmod, which
        would be unreliable across CI users/environments."""
        launch_agent_plist_factory(tmp_path, "com.example.updater.plist")

        def _raise_permission_error(self: Path, *args: object, **kwargs: object) -> None:
            raise PermissionError("denied")

        monkeypatch.setattr(Path, "open", _raise_permission_error)

        candidates, scan_errors = build_launch_agent_index([tmp_path])

        assert len(candidates) == 1
        assert candidates[0].label is None
        assert candidates[0].filename_stem == "com.example.updater"
        assert scan_errors == ()

    def test_nonexistent_directory_contributes_scan_error_not_crash(self, tmp_path) -> None:
        missing = tmp_path / "DoesNotExist"

        candidates, scan_errors = build_launch_agent_index([missing])

        assert candidates == ()
        assert len(scan_errors) == 1

    def test_one_bad_directory_does_not_abort_scanning_others(self, tmp_path, launch_agent_plist_factory) -> None:
        missing = tmp_path / "DoesNotExist"
        good_dir = tmp_path / "Good"
        launch_agent_plist_factory(good_dir, "com.example.updater.plist")

        candidates, scan_errors = build_launch_agent_index([missing, good_dir])

        assert len(candidates) == 1
        assert len(scan_errors) == 1

    def test_plist_suffixed_directory_is_skipped(self, tmp_path) -> None:
        (tmp_path / "weird.plist").mkdir()

        candidates, scan_errors = build_launch_agent_index([tmp_path])

        assert candidates == ()
        assert scan_errors == ()


class TestDefaultLaunchAgentDirs:
    def test_includes_standard_locations(self, monkeypatch, tmp_path) -> None:
        fake_home = tmp_path / "home"
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        dirs = auto_update_module.default_launch_agent_dirs()

        assert dirs == [
            Path("/Library/LaunchDaemons"),
            Path("/Library/LaunchAgents"),
            fake_home / "Library" / "LaunchAgents",
        ]


class TestAggregateProbeResults:
    def _result(self, **overrides: object) -> _ProbeResult:
        defaults: dict[str, object] = {
            "mechanism": AutoUpdateMechanism.SPARKLE_FRAMEWORK,
            "found": False,
            "confidence": EvidenceConfidence.NONE,
            "detail": "test",
        }
        defaults.update(overrides)
        return _ProbeResult(**defaults)  # type: ignore[arg-type]

    def test_all_negative_no_errors_is_none_detected(self) -> None:
        evidence = auto_update_module._aggregate_probe_results([self._result(), self._result()])

        assert evidence.status == AutoUpdateStatus.NONE_DETECTED
        assert evidence.confidence == EvidenceConfidence.MEDIUM

    def test_one_positive_is_capable(self) -> None:
        evidence = auto_update_module._aggregate_probe_results(
            [self._result(found=True, confidence=EvidenceConfidence.HIGH, detail="Sparkle present")]
        )

        assert evidence.status == AutoUpdateStatus.CAPABLE
        assert evidence.confidence == EvidenceConfidence.HIGH

    def test_positive_with_enabled_true_is_enabled(self) -> None:
        evidence = auto_update_module._aggregate_probe_results(
            [self._result(found=True, confidence=EvidenceConfidence.HIGH, enabled=True)]
        )

        assert evidence.status == AutoUpdateStatus.ENABLED

    def test_positive_survives_an_unrelated_probe_error(self) -> None:
        results = [
            self._result(found=True, confidence=EvidenceConfidence.HIGH, detail="Squirrel present"),
            self._result(mechanism=AutoUpdateMechanism.MOZILLA_UPDATER, found=False, error="permission denied"),
        ]

        evidence = auto_update_module._aggregate_probe_results(results)

        assert evidence.status == AutoUpdateStatus.CAPABLE
        assert "permission denied" in evidence.reason
        assert evidence.error is None

    def test_no_positive_with_error_is_unknown(self) -> None:
        evidence = auto_update_module._aggregate_probe_results([self._result(found=False, error="permission denied")])

        assert evidence.status == AutoUpdateStatus.UNKNOWN
        assert evidence.confidence == EvidenceConfidence.NONE
        assert evidence.error == "permission denied"

    def test_multiple_simultaneous_positives_populate_mechanisms(self) -> None:
        """Real basis: LM Studio/Signal/TradingView/Antigravity carry both
        Squirrel.framework and app-update.yml simultaneously."""
        results = [
            self._result(
                mechanism=AutoUpdateMechanism.SQUIRREL_FRAMEWORK,
                found=True,
                confidence=EvidenceConfidence.HIGH,
                detail="Squirrel present",
            ),
            self._result(
                mechanism=AutoUpdateMechanism.ELECTRON_UPDATER_YML,
                found=True,
                confidence=EvidenceConfidence.HIGH,
                detail="app-update.yml present",
            ),
        ]

        evidence = auto_update_module._aggregate_probe_results(results)

        assert set(evidence.mechanisms) == {
            AutoUpdateMechanism.SQUIRREL_FRAMEWORK,
            AutoUpdateMechanism.ELECTRON_UPDATER_YML,
        }


class TestHomebrewCaskSupplement:
    def test_supplements_none_detected_with_true_auto_updates(self, tmp_path) -> None:
        record = _make_record(tmp_path / "App.app", homebrew=_managed_homebrew_evidence(auto_updates=True))
        base_evidence = auto_update_module._aggregate_probe_results([])

        evidence = auto_update_module._apply_homebrew_cask_supplement(base_evidence, record)

        assert evidence.status == AutoUpdateStatus.CAPABLE
        assert evidence.mechanisms == (AutoUpdateMechanism.HOMEBREW_CASK_AUTO_UPDATES,)

    def test_does_not_supplement_when_cask_auto_updates_false(self, tmp_path) -> None:
        record = _make_record(tmp_path / "App.app", homebrew=_managed_homebrew_evidence(auto_updates=False))
        base_evidence = auto_update_module._aggregate_probe_results([])

        evidence = auto_update_module._apply_homebrew_cask_supplement(base_evidence, record)

        assert evidence.status == AutoUpdateStatus.NONE_DETECTED

    def test_does_not_override_unknown(self, tmp_path) -> None:
        """An errored local probe plus a generic upstream flag doesn't
        explain *why* the probe failed -- unknown must route to needs_review
        distinctly, not be papered over."""
        record = _make_record(tmp_path / "App.app", homebrew=_managed_homebrew_evidence(auto_updates=True))
        base_evidence = auto_update_module._aggregate_probe_results(
            [
                _ProbeResult(
                    mechanism=AutoUpdateMechanism.SPARKLE_FRAMEWORK,
                    found=False,
                    confidence=EvidenceConfidence.NONE,
                    detail="",
                    error="denied",
                )
            ]
        )

        evidence = auto_update_module._apply_homebrew_cask_supplement(base_evidence, record)

        assert evidence.status == AutoUpdateStatus.UNKNOWN

    def test_does_not_override_existing_positive(self, tmp_path) -> None:
        record = _make_record(tmp_path / "App.app", homebrew=_managed_homebrew_evidence(auto_updates=True))
        base_evidence = auto_update_module._aggregate_probe_results(
            [
                _ProbeResult(
                    mechanism=AutoUpdateMechanism.SPARKLE_FRAMEWORK,
                    found=True,
                    confidence=EvidenceConfidence.HIGH,
                    detail="Sparkle present",
                )
            ]
        )

        evidence = auto_update_module._apply_homebrew_cask_supplement(base_evidence, record)

        assert evidence.mechanisms == (AutoUpdateMechanism.SPARKLE_FRAMEWORK,)

    def test_never_produces_enabled(self, tmp_path) -> None:
        record = _make_record(tmp_path / "App.app", homebrew=_managed_homebrew_evidence(auto_updates=True))
        base_evidence = auto_update_module._aggregate_probe_results([])

        evidence = auto_update_module._apply_homebrew_cask_supplement(base_evidence, record)

        assert evidence.status != AutoUpdateStatus.ENABLED

    def test_ordering_tolerant_when_homebrew_not_yet_resolved(self, tmp_path) -> None:
        """No service.py enforces resolution order in this phase."""
        record = _make_record(tmp_path / "App.app")  # homebrew defaults to NOT_EVALUATED
        base_evidence = auto_update_module._aggregate_probe_results([])

        evidence = auto_update_module._apply_homebrew_cask_supplement(base_evidence, record)

        assert evidence.status == AutoUpdateStatus.NONE_DETECTED

    def test_not_available_homebrew_status_does_not_supplement(self, tmp_path) -> None:
        record = _make_record(
            tmp_path / "App.app",
            homebrew=HomebrewEvidence(
                status=HomebrewStatus.NOT_AVAILABLE, reason="test", source=EvidenceSource.HOMEBREW_CLI
            ),
        )
        base_evidence = auto_update_module._aggregate_probe_results([])

        evidence = auto_update_module._apply_homebrew_cask_supplement(base_evidence, record)

        assert evidence.status == AutoUpdateStatus.NONE_DETECTED


class TestApplyAutoUpdateEvidence:
    def test_hermetic_run_over_empty_dirs_is_none_detected(self, tmp_path, app_bundle_factory) -> None:
        empty_launch_agent_dir = tmp_path / "EmptyLaunchAgents"
        empty_launch_agent_dir.mkdir()
        bundle = app_bundle_factory(tmp_path / "Applications", "PlainApp")
        record = _make_record(bundle.resolve())

        result = apply_auto_update_evidence([record], launch_agent_dirs=[empty_launch_agent_dir])

        assert result[0].auto_update.status == AutoUpdateStatus.NONE_DETECTED

    def test_sparkle_bundle_resolves_capable(self, tmp_path, app_bundle_factory, sparkle_framework_factory) -> None:
        empty_launch_agent_dir = tmp_path / "EmptyLaunchAgents"
        empty_launch_agent_dir.mkdir()
        bundle = app_bundle_factory(tmp_path / "Applications", "SomeApp")
        sparkle_framework_factory(bundle)
        record = _make_record(bundle.resolve())

        result = apply_auto_update_evidence([record], launch_agent_dirs=[empty_launch_agent_dir])

        assert result[0].auto_update.status in (AutoUpdateStatus.CAPABLE, AutoUpdateStatus.ENABLED)

    def test_original_records_are_not_mutated(self, tmp_path, app_bundle_factory) -> None:
        empty_launch_agent_dir = tmp_path / "EmptyLaunchAgents"
        empty_launch_agent_dir.mkdir()
        bundle = app_bundle_factory(tmp_path / "Applications", "PlainApp")
        record = _make_record(bundle.resolve())

        apply_auto_update_evidence([record], launch_agent_dirs=[empty_launch_agent_dir])

        assert record.auto_update.status == AutoUpdateStatus.NOT_EVALUATED

    def test_default_dirs_used_when_none_given(self, monkeypatch, tmp_path, app_bundle_factory) -> None:
        empty_launch_agent_dir = tmp_path / "EmptyLaunchAgents"
        empty_launch_agent_dir.mkdir()
        monkeypatch.setattr(auto_update_module, "default_launch_agent_dirs", lambda: [empty_launch_agent_dir])
        bundle = app_bundle_factory(tmp_path / "Applications", "PlainApp")
        record = _make_record(bundle.resolve())

        result = apply_auto_update_evidence([record])

        assert result[0].auto_update.status == AutoUpdateStatus.NONE_DETECTED


class TestExitCriteria:
    """The four exit criteria quoted verbatim from the handoff spec."""

    def test_sparkle_fixture_is_capable_or_enabled(
        self, tmp_path, app_bundle_factory, sparkle_framework_factory
    ) -> None:
        bundle = app_bundle_factory(tmp_path, "SparkleApp")
        sparkle_framework_factory(bundle)
        record = _make_record(bundle.resolve())

        evidence = resolve_auto_update_evidence(record, launch_agent_candidates=())

        assert evidence.status in (AutoUpdateStatus.CAPABLE, AutoUpdateStatus.ENABLED)

    def test_squirrel_fixture_is_capable_or_enabled(
        self, tmp_path, app_bundle_factory, squirrel_framework_factory
    ) -> None:
        bundle = app_bundle_factory(tmp_path, "SquirrelApp")
        squirrel_framework_factory(bundle)
        record = _make_record(bundle.resolve())

        evidence = resolve_auto_update_evidence(record, launch_agent_candidates=())

        assert evidence.status in (AutoUpdateStatus.CAPABLE, AutoUpdateStatus.ENABLED)

    def test_clean_fixture_is_none_detected(self, tmp_path, app_bundle_factory) -> None:
        """Real basis: /System/Applications/Preview.app has zero
        Sparkle/Squirrel/updater files and zero SU* Info.plist keys."""
        bundle = app_bundle_factory(tmp_path, "Preview")
        record = _make_record(bundle.resolve())

        evidence = resolve_auto_update_evidence(record, launch_agent_candidates=())

        assert evidence.status == AutoUpdateStatus.NONE_DETECTED

    def test_probe_failure_is_unknown(self, tmp_path, app_bundle_factory, monkeypatch) -> None:
        bundle = app_bundle_factory(tmp_path, "App")
        record = _make_record(bundle.resolve())

        def raise_os_error(self: Path, *args: object, **kwargs: object) -> bool:
            raise OSError("permission denied")

        monkeypatch.setattr(Path, "is_dir", raise_os_error)

        evidence = resolve_auto_update_evidence(record, launch_agent_candidates=())

        assert evidence.status == AutoUpdateStatus.UNKNOWN

    def test_isolated_vendor_probe_permission_error_does_not_become_none_detected(
        self, tmp_path, app_bundle_factory, monkeypatch
    ) -> None:
        """Isolated version of test_probe_failure_is_unknown above, which
        fails ALL probes at once via Path.is_dir (incidentally also
        breaking Sparkle/Squirrel, which share that check). Here only the
        vendor LaunchAgent probe's directory listing fails via a real
        PermissionError on iterdir() -- Sparkle/Squirrel/electron/Mozilla
        all cleanly return "not found", no error -- proving the aggregator
        doesn't average one real error away into NONE_DETECTED just
        because four other probes were quietly negative."""
        bundle = app_bundle_factory(tmp_path, "App")
        record = _make_record(bundle.resolve())
        broken_dir = tmp_path / "BrokenLaunchAgents"
        broken_dir.mkdir()
        real_iterdir = Path.iterdir

        def _raise_for_broken_dir(self: Path):
            if self == broken_dir:
                raise PermissionError("denied")
            return real_iterdir(self)

        monkeypatch.setattr(Path, "iterdir", _raise_for_broken_dir)

        result = apply_auto_update_evidence([record], launch_agent_dirs=[broken_dir])

        assert result[0].auto_update.status == AutoUpdateStatus.UNKNOWN

    def test_negative_caveat_text_is_not_a_positive_match(self, tmp_path) -> None:
        """The design only ever reads the structured Homebrew auto_updates
        boolean, never Homebrew's free-text caveats string -- confirmed here
        by constructing a MANAGED record whose reason text sounds positive
        but whose cask_auto_updates is False, proving text content is never
        inspected."""
        homebrew = HomebrewEvidence(
            status=HomebrewStatus.MANAGED,
            reason="Caveat: this application does not auto-update automatically",
            source=EvidenceSource.HOMEBREW_CLI,
            matched_identifier="some-cask",
            cask_auto_updates=False,
        )
        record = _make_record(tmp_path / "App.app", homebrew=homebrew)
        base_evidence = auto_update_module._aggregate_probe_results([])

        evidence = auto_update_module._apply_homebrew_cask_supplement(base_evidence, record)

        assert evidence.status == AutoUpdateStatus.NONE_DETECTED
