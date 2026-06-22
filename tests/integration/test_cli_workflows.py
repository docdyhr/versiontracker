"""Integration tests for CLI workflows.

Cross-platform tests that mock system-level calls (system_profiler, Homebrew)
and verify the full handler orchestration: argument parsing → handler → output.
Unlike the macOS-only end-to-end tests, these run in any CI environment.
"""

import json
from unittest import mock

import pytest

from versiontracker.__main__ import versiontracker_main

_FAKE_APPS = [
    ("Firefox", "110.0"),
    ("Google Chrome", "110.0.5481.177"),
    ("Visual Studio Code", "1.74.0"),
]

_FAKE_BREWS = ["firefox", "google-chrome", "visual-studio-code"]


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
