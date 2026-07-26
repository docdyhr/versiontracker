"""Tests for versiontracker.menubar_app.

Regression coverage: `MenubarApp.handle_menu_choice()`'s `commands` dict
previously hard-coded `--outdated` and `--notify`, neither of which exist as
real CLI flags -- every real click of "Check for Updates" or "Show Outdated
Apps" would fail argparse parsing and show an error dialog instead of
working. Zero test coverage existed for this file before this addition.
"""

from __future__ import annotations

from unittest.mock import patch

from versiontracker.cli import get_arguments
from versiontracker.menubar_app import MenubarApp


class TestMenubarCommandsAreValidFlags:
    """Validated against the real argparse parser, not a hand-maintained
    list of "known good" flags -- so a future flag rename can't silently
    reintroduce this bug without this test catching it."""

    def test_every_menu_command_parses_cleanly(self) -> None:
        app = MenubarApp()
        captured_args: list[list[str]] = []
        with patch.object(app, "run_versiontracker_command", side_effect=captured_args.append):
            for choice in (
                "Check for Updates",
                "Show Outdated Apps",
                "Show All Apps",
                "Show Homebrew Casks",
                "Install Service",
                "Uninstall Service",
                "Service Status",
            ):
                app.handle_menu_choice(choice)

        assert len(captured_args) == 7
        for args in captured_args:
            with patch("sys.argv", ["versiontracker", *args]):
                get_arguments()  # raises SystemExit(2) if any flag is unrecognized

    def test_check_for_updates_and_show_outdated_use_check_outdated_flag(self) -> None:
        app = MenubarApp()
        captured_args: list[list[str]] = []
        with patch.object(app, "run_versiontracker_command", side_effect=captured_args.append):
            app.handle_menu_choice("Check for Updates")
            app.handle_menu_choice("Show Outdated Apps")

        assert captured_args == [["--check-outdated"], ["--check-outdated"]]

    def test_unknown_choice_does_not_run_a_command(self) -> None:
        app = MenubarApp()
        with patch.object(app, "run_versiontracker_command") as mock_run:
            app.handle_menu_choice("Some Unrecognized Choice")

        mock_run.assert_not_called()
