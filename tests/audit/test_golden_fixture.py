"""End-to-end golden fixture for versiontracker.audit (Phase 5).

Phases 1-4's own test files each prove one resolver's truth table in
isolation (with every other axis stubbed to NOT_EVALUATED/mocked away).
Nothing until now has proven the *composition*: one real `run_audit()` call,
over real on-disk bundles, exercising every resolver together and asserting
on the final classification -- the actual thing a user experiences. This is
the project's own "Required Test Matrix" made executable, plus one isolated
test for its most important exit criterion: a resolver failure must never
silently present as a negative signal.
"""

from __future__ import annotations

import json

import versiontracker.audit.homebrew as homebrew_module
from versiontracker.audit.models import (
    AuditBucket,
    AutoUpdateStatus,
    BlocklistMatchKind,
    HomebrewStatus,
)
from versiontracker.audit.service import run_audit


class TestGoldenFixtureCompleteIntersection:
    """One tmp_path, one run_audit() call, seven apps -- each landing in its
    bucket via a distinct signal (or combination of signals), proving the
    resolvers compose correctly rather than merely existing in isolation."""

    def test_complete_intersection(
        self,
        monkeypatch,
        tmp_path,
        app_bundle_factory,
        cask_factory,
        installed_casks_payload_factory,
        sparkle_framework_factory,
    ) -> None:
        # -- App Store: a real MASReceipt is enough on its own (Phase 1's
        # receipt-presence signal), no system_profiler enrichment needed.
        app_bundle_factory(tmp_path, "AppStoreApp", bundle_id="com.example.appstoreapp", has_mas_receipt=True)

        # -- Homebrew: cask artifact target matches this bundle's own path exactly.
        homebrew_bundle = app_bundle_factory(tmp_path, "HomebrewManagedApp", bundle_id="com.example.homebrewmanagedapp")

        # -- Auto-update: Sparkle framework + an explicit enabled preference.
        sparkle_bundle = app_bundle_factory(
            tmp_path,
            "SparkleEnabledApp",
            bundle_id="com.example.sparkleenabledapp",
            extra_plist_keys={"SUEnableAutomaticChecks": True},
        )
        sparkle_framework_factory(sparkle_bundle)

        # -- Blocklist: matched by display name (the weakest tier) -- no
        # path/bundle-id/cask-token entry given, so this exercises exactly
        # that fallback tier.
        app_bundle_factory(tmp_path, "BlocklistedApp", bundle_id="com.example.blocklistedapp")

        # -- Multiple simultaneous positive signals: Homebrew-managed *and*
        # Sparkle present with no preference key set (unset -> CAPABLE, not
        # ENABLED). `why` must name both, not just whichever was checked first.
        multi_bundle = app_bundle_factory(tmp_path, "MultiSignalApp", bundle_id="com.example.multisignalapp")
        sparkle_framework_factory(multi_bundle)

        # -- All four signals quiet: the actual default "needs attention" case.
        app_bundle_factory(tmp_path, "PlainAttentionApp", bundle_id="com.example.plainattentionapp")

        # -- A cask exists and even looks related by name, but its artifact
        # target points somewhere else -- this app was installed manually,
        # not by that cask. HomebrewStatus.AVAILABLE is never produced by any
        # resolver today (cask availability is a deliberately deferred later
        # enrichment -- see versiontracker/audit/homebrew.py's own module
        # docstring), so the honest current assertion is NOT_AVAILABLE, not
        # the spec's aspirational "available" remediation status.
        app_bundle_factory(tmp_path, "CaskInstalledButManualApp", bundle_id="com.example.caskinstalledbutmanualapp")

        payload = installed_casks_payload_factory(
            cask_factory("homebrewmanagedapp", app_name="HomebrewManagedApp.app", app_target=str(homebrew_bundle)),
            cask_factory("multisignalapp", app_name="MultiSignalApp.app", app_target=str(multi_bundle)),
            cask_factory(
                "caskinstalledbutmanualapp",
                app_name="CaskInstalledButManualApp.app",
                app_target=str(tmp_path / "SomeOtherLocation" / "CaskInstalledButManualApp.app"),
            ),
        )
        monkeypatch.setattr(homebrew_module, "run_command_secure", lambda *a, **k: (json.dumps(payload), 0))
        monkeypatch.setattr(homebrew_module, "get_brew_command", lambda: "/opt/homebrew/bin/brew")
        empty_launch_agent_dir = tmp_path / "EmptyLaunchAgents"
        empty_launch_agent_dir.mkdir()

        result = run_audit(
            roots=[tmp_path],
            system_profiler_data={"SPApplicationsDataType": []},
            launch_agent_dirs=[empty_launch_agent_dir],
            blocklist_entries=["BlocklistedApp"],
        )

        expected_buckets = {
            "AppStoreApp": AuditBucket.MANAGED,
            "HomebrewManagedApp": AuditBucket.MANAGED,
            "SparkleEnabledApp": AuditBucket.MANAGED,
            "BlocklistedApp": AuditBucket.MANAGED,
            "MultiSignalApp": AuditBucket.MANAGED,
            "PlainAttentionApp": AuditBucket.ATTENTION,
            "CaskInstalledButManualApp": AuditBucket.ATTENTION,
        }
        by_name = {a.record.name: a for a in result.applications}
        assert set(by_name) == set(expected_buckets)
        for name, expected in expected_buckets.items():
            app = by_name[name]
            assert app.classification.bucket == expected, (
                f"{name}: expected {expected}, got {app.classification.bucket} ({app.classification.why})"
            )

        # Summary is derived from the same table it's checked against, not a
        # separately hand-maintained literal, so it can't silently drift
        # when a row is added later.
        expected_summary = {"total": len(expected_buckets), "unknown": 0}
        for bucket in (AuditBucket.ATTENTION, AuditBucket.MANAGED):
            expected_summary[bucket.value] = sum(1 for b in expected_buckets.values() if b == bucket)
        assert result.summary == expected_summary

        # Per-axis spot checks: each app must reach its bucket via the
        # *intended* signal, not coincidentally.
        assert by_name["AppStoreApp"].record.app_store.status.value == "app_store"
        assert by_name["HomebrewManagedApp"].record.homebrew.status == HomebrewStatus.MANAGED
        assert by_name["HomebrewManagedApp"].record.homebrew.matched_identifier == "homebrewmanagedapp"
        assert by_name["SparkleEnabledApp"].record.auto_update.status == AutoUpdateStatus.ENABLED
        assert by_name["BlocklistedApp"].record.blocklist.matched_by == BlocklistMatchKind.DISPLAY_NAME
        assert by_name["CaskInstalledButManualApp"].record.homebrew.status == HomebrewStatus.NOT_AVAILABLE

        # MultiSignalApp: why must name *both* signals, not just one.
        multi_why = by_name["MultiSignalApp"].classification.why
        assert "Homebrew" in multi_why
        assert "auto-update mechanism" in multi_why
        assert by_name["MultiSignalApp"].record.auto_update.status == AutoUpdateStatus.CAPABLE

    def test_homebrew_failure_produces_unknown_not_false_end_to_end(
        self, monkeypatch, tmp_path, app_bundle_factory
    ) -> None:
        """The exit criterion stated by this project's own handoff spec:
        'The composite test fails if any resolver silently changes unknown
        to false.' Kept isolated from the larger matrix above so a
        regression here has an unambiguous failure signal: this one app has
        no auto-update artifacts and isn't blocklisted, so both of those
        axes cleanly resolve negative on their own -- ATTENTION is exactly
        what a silently-flipped-to-false Homebrew resolver would produce
        instead of the correct UNKNOWN."""
        app_bundle_factory(tmp_path, "SomeApp", bundle_id="com.example.someapp")
        monkeypatch.setattr(homebrew_module, "run_command_secure", lambda *a, **k: ("boom", 1))
        monkeypatch.setattr(homebrew_module, "get_brew_command", lambda: "/opt/homebrew/bin/brew")
        empty_launch_agent_dir = tmp_path / "EmptyLaunchAgents"
        empty_launch_agent_dir.mkdir()

        result = run_audit(
            roots=[tmp_path],
            system_profiler_data={"SPApplicationsDataType": []},
            launch_agent_dirs=[empty_launch_agent_dir],
        )

        assert len(result.applications) == 1
        app = result.applications[0]
        assert app.record.homebrew.status == HomebrewStatus.UNKNOWN
        assert app.record.homebrew.error is not None
        assert app.classification.bucket == AuditBucket.UNKNOWN
