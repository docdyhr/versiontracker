"""Integration tests for CLI workflows.

Cross-platform tests that mock system-level calls (system_profiler, Homebrew)
and verify the full handler orchestration: argument parsing → handler → output.
Unlike the macOS-only end-to-end tests, these run in any CI environment.
"""

import json
from pathlib import Path
from unittest import mock

import pytest

from versiontracker.__main__ import versiontracker_main
from versiontracker.audit import AuditResult
from versiontracker.audit.models import (
    ApplicationRecord,
    AppStoreEvidence,
    AppStoreStatus,
    AuditBucket,
    AuditClassification,
    AutoUpdateEvidence,
    AutoUpdateStatus,
    BlocklistEvidence,
    BlocklistStatus,
    ClassifiedApplication,
    EvidenceSource,
    HomebrewEvidence,
    HomebrewStatus,
)
from versiontracker.cli import get_arguments
from versiontracker.deprecation import reset_deprecation_registry

_FAKE_APPS = [
    ("Firefox", "110.0"),
    ("Google Chrome", "110.0.5481.177"),
    ("Visual Studio Code", "1.74.0"),
]

_FAKE_BREWS = ["firefox", "google-chrome", "visual-studio-code"]


def _classified_app(name: str, bucket: AuditBucket) -> ClassifiedApplication:
    path = Path(f"/Applications/{name}.app")
    record = ApplicationRecord(
        name=name,
        version="1.0",
        path=path,
        canonical_path=path,
        bundle_id=f"com.example.{name.lower()}",
        obtained_from=None,
        parent_bundle_path=None,
        app_store=AppStoreEvidence(
            status=AppStoreStatus.NOT_APP_STORE, reason="test", source=EvidenceSource.FILESYSTEM
        ),
        homebrew=HomebrewEvidence(
            status=HomebrewStatus.NOT_AVAILABLE, reason="test", source=EvidenceSource.HOMEBREW_CLI
        ),
        auto_update=AutoUpdateEvidence(
            status=AutoUpdateStatus.NONE_DETECTED, reason="test", source=EvidenceSource.FILESYSTEM
        ),
        blocklist=BlocklistEvidence(status=BlocklistStatus.NOT_BLOCKED, reason="test", source=EvidenceSource.CONFIG),
    )
    return ClassifiedApplication(record=record, classification=AuditClassification(bucket=bucket, why=f"{name} why"))


def _three_bucket_audit_result() -> AuditResult:
    """One app per bucket -- lets a single fixed AuditResult drive every
    --all/--status/--explain/--export observable-output test below."""
    applications = (
        _classified_app("AttentionApp", AuditBucket.ATTENTION),
        _classified_app("UnknownApp", AuditBucket.UNKNOWN),
        _classified_app("ManagedApp", AuditBucket.MANAGED),
    )
    return AuditResult(applications=applications, summary={"total": 3, "attention": 1, "unknown": 1, "managed": 1})


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear lru_cache between tests to prevent cross-test contamination."""
    from versiontracker.apps.finder import clear_homebrew_casks_cache

    clear_homebrew_casks_cache()
    yield
    clear_homebrew_casks_cache()


class TestCLIWorkflows:
    """Integration tests covering the full CLI dispatch → handler → output chain."""

    def test_apps_full_flow(self, capsys):
        """--apps discovers apps, sorts them, and prints a table."""
        with (
            mock.patch(
                "versiontracker.handlers.app_handlers._get_apps_data",
                return_value=_FAKE_APPS,
            ),
            mock.patch("sys.argv", ["versiontracker", "--apps"]),
        ):
            result = versiontracker_main()

        assert result == 0
        captured = capsys.readouterr()
        # At least one known app name should appear in the table
        assert any(name in captured.out for name in ("Firefox", "Google Chrome", "Visual Studio Code"))

    def test_apps_export_to_file(self, tmp_path):
        """--apps --export json --output-file writes valid JSON to the target path."""
        output_file = tmp_path / "apps_export.json"
        mock_cfg = mock.MagicMock()
        mock_cfg.is_blocklisted.return_value = False
        with (
            mock.patch(
                "versiontracker.handlers.app_handlers._get_apps_data",
                return_value=_FAKE_APPS,
            ),
            mock.patch(
                "versiontracker.handlers.app_handlers.get_config",
                return_value=mock_cfg,
            ),
            mock.patch(
                "sys.argv",
                [
                    "versiontracker",
                    "--apps",
                    "--export",
                    "json",
                    "--output-file",
                    str(output_file),
                ],
            ),
        ):
            result = versiontracker_main()

        assert result == 0
        assert output_file.exists(), "Export file was not created"
        with open(output_file) as f:
            data = json.load(f)
        assert isinstance(data, list | dict), "Export file does not contain valid JSON"
        # Each app should appear as an entry
        assert len(data) == len(_FAKE_APPS)

    def test_brews_list_flow(self, capsys):
        """--brews lists installed Homebrew casks without requiring a real brew binary."""
        with (
            mock.patch(
                "versiontracker.handlers.brew_handlers.get_homebrew_casks",
                return_value=_FAKE_BREWS,
            ),
            mock.patch("sys.argv", ["versiontracker", "--brews"]),
        ):
            result = versiontracker_main()

        assert result == 0
        captured = capsys.readouterr()
        assert "firefox" in captured.out.lower() or "homebrew" in captured.out.lower()

    def test_generate_config_flow(self, tmp_path, capsys):
        """--generate-config calls generate_default_config and reports the output path."""
        config_path = tmp_path / "versiontracker.yaml"

        with (
            mock.patch("versiontracker.handlers.config_handlers.get_config") as mock_get_config,
            mock.patch("sys.argv", ["versiontracker", "--generate-config"]),
        ):
            mock_cfg = mock.MagicMock()
            mock_cfg.generate_default_config.return_value = str(config_path)
            mock_get_config.return_value = mock_cfg

            result = versiontracker_main()

        assert result == 0
        captured = capsys.readouterr()
        assert str(config_path) in captured.out

    def test_check_outdated_flow(self):
        """--check-outdated exercises the full dispatch chain with no real network calls."""
        with (
            mock.patch(
                "versiontracker.handlers.outdated_handlers._get_applications_with_error_handling",
                return_value=(_FAKE_APPS, 0),
            ),
            mock.patch(
                "versiontracker.handlers.outdated_handlers._get_homebrew_casks_with_error_handling",
                return_value=([], 0),
            ),
            mock.patch(
                "versiontracker.handlers.outdated_handlers._check_outdated_with_error_handling",
                return_value=([], 0),
            ),
            mock.patch("sys.argv", ["versiontracker", "--check-outdated"]),
        ):
            result = versiontracker_main()

        # Handler may return 0 (up-to-date) or non-zero based on display logic;
        # the important thing is it completes without raising an unhandled exception.
        assert result in (0, 1)

    def test_audit_export_json_produces_clean_parseable_stdout(self, capsys):
        """--audit --export json must print *only* the JSON, even when combined
        with a deprecated flag -- this is the only test level that would catch a
        regression in __main__._emit_deprecation_warnings's emit_console_hint
        wiring, since handler-level unit tests mock straight past it."""
        reset_deprecation_registry()
        fake_result = AuditResult(applications=(), summary={"total": 0, "attention": 0, "unknown": 0, "managed": 0})
        with (
            mock.patch("versiontracker.handlers.audit_handlers.run_audit", return_value=fake_result),
            mock.patch(
                "sys.argv",
                ["versiontracker", "--audit", "--export", "json", "--blacklist", "Firefox"],
            ),
        ):
            result = versiontracker_main()

        assert result == 0
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)  # raises if a stray [DEPRECATION] line snuck in
        assert parsed["schema_version"] == 1
        assert parsed["applications"] == []

    def test_audit_default_view_hides_managed_app(self, capsys):
        """Default --audit shows attention/unknown, hides the managed app --
        the CLI-level proof that --all changes observable output at all."""
        with (
            mock.patch("versiontracker.handlers.audit_handlers.run_audit", return_value=_three_bucket_audit_result()),
            mock.patch("sys.argv", ["versiontracker", "--audit"]),
        ):
            result = versiontracker_main()

        assert result == 0
        captured = capsys.readouterr()
        assert "AttentionApp" in captured.out
        assert "UnknownApp" in captured.out
        assert "ManagedApp" not in captured.out

    def test_audit_all_flag_reveals_managed_app(self, capsys):
        """--all is the one flag whose whole purpose is revealing the
        otherwise-hidden managed app -- directly observable in stdout."""
        with (
            mock.patch("versiontracker.handlers.audit_handlers.run_audit", return_value=_three_bucket_audit_result()),
            mock.patch("sys.argv", ["versiontracker", "--audit", "--all"]),
        ):
            result = versiontracker_main()

        assert result == 0
        captured = capsys.readouterr()
        assert "ManagedApp" in captured.out

    def test_audit_status_flag_shows_only_that_bucket(self, capsys):
        """--status managed shows only the managed app, not the other two --
        proves --status actually filters, not just accepts the argument."""
        with (
            mock.patch("versiontracker.handlers.audit_handlers.run_audit", return_value=_three_bucket_audit_result()),
            mock.patch("sys.argv", ["versiontracker", "--audit", "--status", "managed"]),
        ):
            result = versiontracker_main()

        assert result == 0
        captured = capsys.readouterr()
        assert "ManagedApp" in captured.out
        assert "AttentionApp" not in captured.out
        assert "UnknownApp" not in captured.out

    def test_audit_explain_flag_shows_full_evidence(self, capsys):
        """--explain's whole purpose is exposing per-axis evidence
        (confidence=/source=) that the default compact table never prints."""
        with (
            mock.patch("versiontracker.handlers.audit_handlers.run_audit", return_value=_three_bucket_audit_result()),
            mock.patch("sys.argv", ["versiontracker", "--audit", "--all"]),
        ):
            versiontracker_main()
        compact_out = capsys.readouterr().out

        with (
            mock.patch("versiontracker.handlers.audit_handlers.run_audit", return_value=_three_bucket_audit_result()),
            mock.patch("sys.argv", ["versiontracker", "--audit", "--all", "--explain"]),
        ):
            result = versiontracker_main()
        explain_out = capsys.readouterr().out

        assert result == 0
        assert "confidence=" not in compact_out
        assert "confidence=" in explain_out

    def test_ask_audit_query_routes_through_to_audit_output(self, capsys):
        """--ask with an audit-style query must produce the same observable
        output as the equivalent literal --audit flag."""
        with (
            mock.patch("versiontracker.handlers.audit_handlers.run_audit", return_value=_three_bucket_audit_result()),
            mock.patch("sys.argv", ["versiontracker", "--ask", "which apps need manual updates"]),
        ):
            result = versiontracker_main()

        assert result == 0
        captured = capsys.readouterr()
        assert "AttentionApp" in captured.out
        assert "UnknownApp" in captured.out
        assert "ManagedApp" not in captured.out  # default view, same as bare --audit

    def test_ask_audit_query_combined_with_export_json(self, capsys):
        """--ask + --export json: proves --ask can be combined with modifier
        flags because they live in a separate argparse mutex group from
        action_group."""
        fake_result = AuditResult(applications=(), summary={"total": 0, "attention": 0, "unknown": 0, "managed": 0})
        with (
            mock.patch("versiontracker.handlers.audit_handlers.run_audit", return_value=fake_result),
            mock.patch(
                "sys.argv",
                ["versiontracker", "--ask", "which apps need manual updates", "--export", "json"],
            ),
        ):
            result = versiontracker_main()

        assert result == 0
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["schema_version"] == 1

    def test_ask_out_of_scope_query_no_crash(self, capsys):
        with mock.patch("sys.argv", ["versiontracker", "--ask", "install app named firefox"]):
            result = versiontracker_main()

        assert result == 1
        assert "not supported" in capsys.readouterr().out.lower()

    def test_ask_gibberish_query_asks_clarification_not_crash(self, capsys):
        with mock.patch("sys.argv", ["versiontracker", "--ask", "xyzzy plugh nonsense"]):
            result = versiontracker_main()

        assert result == 1
        assert "not sure" in capsys.readouterr().out.lower()

    def test_ask_mutually_exclusive_with_audit_flag(self):
        """--ask and --audit both live in action_group; argparse must reject
        combining them, proving the mutex placement actually took effect."""
        with (
            mock.patch("sys.argv", ["versiontracker", "--ask", "x", "--audit"]),
            pytest.raises(SystemExit),
        ):
            get_arguments()
