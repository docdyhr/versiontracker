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

# Adversarial strings covering the input classes that could previously break out
# of the naive `"` -> `\"` AppleScript string-literal escaping used by
# `show_result_dialog()`: double quotes, single quotes, bare backslashes, a
# trailing backslash-then-quote (the specific break-out sequence),
# newlines/tabs, AppleScript operators/comment markers, unicode text, and
# CLI-output-shaped hostile text. Purely structural assertions -- no command is
# ever actually executed.
HOSTILE_STRINGS = [
    'has "double quotes"',
    "has 'single quotes'",
    "has a \\ backslash",
    'ends with a backslash then quote \\"',
    "has\nnewline\tand\ttab",
    'operators & -- comment "quote" ¬ continuation',
    "Café México 日本語 应用 App",
    'display dialog "pwned" -- do shell script "touch /tmp/pwned"',
]


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


class TestShowMenu:
    """`show_menu()` must build a static AppleScript script and pass menu
    items only as separate osascript arguments -- never interpolate them
    into the script source. `menu_items` is a hardcoded list today, but the
    call site should not rely on that for safety."""

    @patch("subprocess.run")
    def test_menu_items_are_argv_not_script_text(self, mock_run) -> None:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "cancelled"

        app = MenubarApp()
        with patch.object(app, "handle_menu_choice") as mock_handle:
            app.show_menu()

        args = mock_run.call_args[0][0]
        assert args[0] == "osascript"
        script = args[2]
        # Menu items reach osascript only via argv -- not embedded in the
        # script source, unlike "Check for Updates", which is intentionally a
        # static default-item literal in the script itself.
        assert "Show Homebrew Casks" not in script
        assert "Uninstall Service" not in script
        assert args[3:] == [
            "VersionTracker",
            "─────────────────",
            "Check for Updates",
            "Show Outdated Apps",
            "Show All Apps",
            "Show Homebrew Casks",
            "─────────────────",
            "Install Service",
            "Uninstall Service",
            "Service Status",
            "─────────────────",
            "Quit",
        ]
        mock_handle.assert_called_once_with("cancelled")

    @patch("subprocess.run")
    def test_script_is_constant_across_calls(self, mock_run) -> None:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "cancelled"

        app = MenubarApp()
        with patch.object(app, "handle_menu_choice"):
            app.show_menu()
            script_a = mock_run.call_args[0][0][2]
            app.show_menu()
            script_b = mock_run.call_args[0][0][2]

        assert script_a == script_b


class TestShowResultDialog:
    """`show_result_dialog()` must never let title/message alter the
    AppleScript source, regardless of what a `versiontracker` subprocess's
    stdout/stderr (the real caller) contains."""

    @patch("subprocess.run")
    def test_hostile_input_stays_data(self, mock_run) -> None:
        mock_run.return_value.returncode = 0

        app = MenubarApp()
        for hostile in HOSTILE_STRINGS:
            mock_run.reset_mock()
            app.show_result_dialog(hostile, hostile)

            args = mock_run.call_args[0][0]
            script = args[2]
            assert hostile not in script
            assert args[3:] == [hostile, hostile]

    @patch("subprocess.run")
    def test_truncates_long_messages_before_passing_as_argv(self, mock_run) -> None:
        mock_run.return_value.returncode = 0

        app = MenubarApp()
        long_message = "x" * 2000
        app.show_result_dialog("Title", long_message)

        args = mock_run.call_args[0][0]
        passed_message = args[4]
        assert len(passed_message) < len(long_message)
        assert passed_message.endswith("(truncated)")
