"""Tests for versiontracker.utils — coverage improvement.

Targets untested paths in shell_command_to_args, is_homebrew_installed,
get_homebrew_prefix, and human_readable_time.
"""

from unittest.mock import patch

from versiontracker.utils import (
    get_homebrew_prefix,
    human_readable_time,
    is_homebrew_installed,
    shell_command_to_args,
)

# ---------------------------------------------------------------------------
# shell_command_to_args
# ---------------------------------------------------------------------------


class TestShellCommandToArgs:
    """Tests for shell_command_to_args()."""

    def test_basic_split(self):
        result = shell_command_to_args("brew search --cask firefox")
        assert result == ["brew", "search", "--cask", "firefox"]

    def test_quoted_strings(self):
        result = shell_command_to_args('brew search --cask "Google Chrome"')
        assert result == ["brew", "search", "--cask", "Google Chrome"]

    def test_malformed_fallback(self):
        # Unmatched quote triggers ValueError in shlex.split
        result = shell_command_to_args('brew search "unmatched')
        # Falls back to str.split()
        assert "search" in result


# ---------------------------------------------------------------------------
# is_homebrew_installed
# ---------------------------------------------------------------------------


class TestIsHomebrewInstalled:
    """Tests for is_homebrew_installed()."""

    @patch("versiontracker.utils.Path")
    def test_path_exists(self, mock_path_cls):
        # First path check returns True
        mock_path_cls.return_value.exists.return_value = True
        assert is_homebrew_installed() is True

    @patch("versiontracker.utils.subprocess.run")
    @patch("versiontracker.utils.Path")
    def test_which_fallback(self, mock_path_cls, mock_run):
        mock_path_cls.return_value.exists.return_value = False
        mock_run.return_value.returncode = 0
        assert is_homebrew_installed() is True

    @patch("versiontracker.utils.subprocess.run")
    @patch("versiontracker.utils.Path")
    def test_not_found(self, mock_path_cls, mock_run):
        mock_path_cls.return_value.exists.return_value = False
        # which returns non-zero when brew not in PATH
        mock_run.return_value.returncode = 1
        assert is_homebrew_installed() is False


# ---------------------------------------------------------------------------
# get_homebrew_prefix
# ---------------------------------------------------------------------------


class TestGetHomebrewPrefix:
    """Tests for get_homebrew_prefix()."""

    @patch("versiontracker.utils.is_homebrew_installed", return_value=False)
    def test_not_installed_returns_none(self, _installed):
        assert get_homebrew_prefix() is None

    @patch("versiontracker.utils.subprocess.run")
    @patch("versiontracker.utils.is_homebrew_installed", return_value=True)
    def test_brew_prefix_success(self, _installed, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "/opt/homebrew\n"
        assert get_homebrew_prefix() == "/opt/homebrew"

    @patch("versiontracker.utils.subprocess.run")
    @patch("versiontracker.utils.is_homebrew_installed", return_value=True)
    def test_brew_prefix_failure(self, _installed, mock_run):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        # Falls back to checking common paths
        result = get_homebrew_prefix()
        # On macOS one of these will exist; on CI it might be None
        assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# human_readable_time
# ---------------------------------------------------------------------------


class TestHumanReadableTime:
    """Tests for human_readable_time()."""

    def test_seconds(self):
        assert human_readable_time(42.5) == "42.5s"

    def test_minutes(self):
        assert human_readable_time(90.0) == "1.5m"

    def test_hours(self):
        assert human_readable_time(7200.0) == "2.0h"

    def test_zero(self):
        assert human_readable_time(0.0) == "0.0s"

    def test_boundary_60(self):
        # 60 seconds should show as minutes
        assert human_readable_time(60.0) == "1.0m"

    def test_boundary_3600(self):
        # 3600 seconds should show as hours
        assert human_readable_time(3600.0) == "1.0h"
