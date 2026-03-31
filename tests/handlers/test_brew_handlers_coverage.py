"""Tests for versiontracker.handlers.brew_handlers — coverage improvement.

Targets error paths in handle_list_brews, handle_brew_recommendations,
_get_rate_limit, and _get_and_filter_brews.
"""

import sys
from unittest.mock import MagicMock, patch

from versiontracker.exceptions import HomebrewError, NetworkError
from versiontracker.handlers.brew_handlers import (
    _determine_strict_mode,
    _get_and_filter_brews,
    _get_homebrew_casks,
    _get_rate_limit,
    _handle_export_if_requested,
    _log_debug_info,
    handle_brew_recommendations,
    handle_list_brews,
)


def _mock_progress_bar():
    """Create a mock progress_bar that returns identity for color calls."""
    pb = MagicMock()
    pb.color.return_value = lambda x: x
    return pb


# ---------------------------------------------------------------------------
# handle_list_brews — error paths
# ---------------------------------------------------------------------------


class TestHandleListBrewsErrors:
    """Tests for handle_list_brews() error handling."""

    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks", side_effect=HomebrewError("not installed"))
    def test_homebrew_error(self, _casks, _pb):
        opts = MagicMock(export_format=None, output_file=None, spec=[])
        assert handle_list_brews(opts) == 1

    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks", side_effect=RuntimeError("unexpected"))
    def test_generic_exception(self, _casks, _pb):
        opts = MagicMock(export_format=None, output_file=None, spec=[])
        assert handle_list_brews(opts) == 1

    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks", return_value=[])
    def test_empty_list(self, _casks, _pb):
        opts = MagicMock(spec=[])
        del opts.exclude_auto_updates
        del opts.only_auto_updates
        opts.export_format = None
        assert handle_list_brews(opts) == 0


# ---------------------------------------------------------------------------
# handle_brew_recommendations — error paths
# ---------------------------------------------------------------------------


class TestHandleBrewRecommendationsErrors:
    """Tests for handle_brew_recommendations() error handling."""

    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.brew_handlers.filter_out_brews", return_value=[("App1", "1.0")])
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks", return_value=[])
    @patch("versiontracker.handlers.brew_handlers.get_applications", return_value=[("App1", "1.0")])
    @patch("versiontracker.handlers.brew_handlers.get_json_data", return_value={})
    @patch("versiontracker.handlers.brew_handlers.get_config")
    @patch(
        "versiontracker.handlers.brew_handlers.check_brew_install_candidates",
        side_effect=HomebrewError("brew error"),
    )
    def test_homebrew_error(self, _candidates, _config, _json, _apps, _casks, _filter, _pb):
        opts = MagicMock(
            recommend=True,
            strict_recommend=False,
            strict_recom=False,
            debug=False,
            rate_limit=1,
            export_format=None,
            output_file=None,
        )
        assert handle_brew_recommendations(opts) == 1

    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.brew_handlers.filter_out_brews", return_value=[("App1", "1.0")])
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks", return_value=[])
    @patch("versiontracker.handlers.brew_handlers.get_applications", return_value=[("App1", "1.0")])
    @patch("versiontracker.handlers.brew_handlers.get_json_data", return_value={})
    @patch("versiontracker.handlers.brew_handlers.get_config")
    @patch(
        "versiontracker.handlers.brew_handlers.check_brew_install_candidates",
        side_effect=NetworkError("no internet"),
    )
    def test_network_error(self, _candidates, _config, _json, _apps, _casks, _filter, _pb):
        opts = MagicMock(
            recommend=True,
            strict_recommend=False,
            strict_recom=False,
            debug=False,
            rate_limit=1,
            export_format=None,
            output_file=None,
        )
        assert handle_brew_recommendations(opts) == 1

    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.brew_handlers.filter_out_brews", return_value=[("App1", "1.0")])
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks", return_value=[])
    @patch("versiontracker.handlers.brew_handlers.get_applications", return_value=[("App1", "1.0")])
    @patch("versiontracker.handlers.brew_handlers.get_json_data", return_value={})
    @patch("versiontracker.handlers.brew_handlers.get_config")
    @patch(
        "versiontracker.handlers.brew_handlers.check_brew_install_candidates",
        side_effect=TimeoutError("timed out"),
    )
    def test_timeout_error(self, _candidates, _config, _json, _apps, _casks, _filter, _pb):
        opts = MagicMock(
            recommend=True,
            strict_recommend=False,
            strict_recom=False,
            debug=False,
            rate_limit=1,
            export_format=None,
            output_file=None,
        )
        assert handle_brew_recommendations(opts) == 1

    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch(
        "versiontracker.handlers.brew_handlers.get_json_data",
        side_effect=RuntimeError("total failure"),
    )
    @patch("versiontracker.handlers.brew_handlers.get_config")
    def test_outer_generic_exception(self, _config, _json, _pb):
        opts = MagicMock(
            recommend=True,
            strict_recommend=False,
            strict_recom=False,
            debug=False,
            rate_limit=1,
            export_format=None,
            output_file=None,
        )
        assert handle_brew_recommendations(opts) == 1


# ---------------------------------------------------------------------------
# _get_rate_limit
# ---------------------------------------------------------------------------


class TestGetRateLimit:
    """Tests for _get_rate_limit()."""

    def test_from_options(self):
        opts = MagicMock(rate_limit=5)
        assert _get_rate_limit(opts) == 5

    @patch("versiontracker.handlers.brew_handlers.get_config")
    def test_from_config(self, mock_config):
        mock_config.return_value.get.return_value = 7
        opts = MagicMock(spec=[])
        assert _get_rate_limit(opts) == 7

    @patch("versiontracker.handlers.brew_handlers.get_config")
    def test_default(self, mock_config):
        mock_config.return_value.get.side_effect = ValueError("bad")
        opts = MagicMock(spec=[])
        assert _get_rate_limit(opts) == 10


# ---------------------------------------------------------------------------
# _get_and_filter_brews
# ---------------------------------------------------------------------------


class TestGetAndFilterBrews:
    """Tests for _get_and_filter_brews()."""

    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.brew_handlers.get_casks_with_auto_updates", return_value=["firefox"])
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks", return_value=["firefox", "chrome"])
    def test_exclude_auto_updates(self, _casks, _auto, _pb):
        opts = MagicMock(exclude_auto_updates=True)
        brews, auto = _get_and_filter_brews(opts)
        assert "firefox" not in brews
        assert "chrome" in brews

    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.brew_handlers.get_casks_with_auto_updates", return_value=["firefox"])
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks", return_value=["firefox", "chrome"])
    def test_only_auto_updates(self, _casks, _auto, _pb):
        opts = MagicMock(only_auto_updates=True)
        del opts.exclude_auto_updates
        brews, auto = _get_and_filter_brews(opts)
        assert brews == ["firefox"]


# ---------------------------------------------------------------------------
# _display_brew_list — auto-update marker path (lines 114-115)
# ---------------------------------------------------------------------------


class TestDisplayBrewList:
    """Tests for _display_brew_list() auto-update marker path."""

    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    def test_auto_update_marker_shown(self, _pb, capsys):
        """Brew with auto-update shows the (auto-updates) marker."""
        from versiontracker.handlers.brew_handlers import _display_brew_list

        opts = MagicMock(show_auto_updates=True, exclude_auto_updates=False, only_auto_updates=False)
        _display_brew_list(["firefox"], ["firefox"], opts)
        out = capsys.readouterr().out
        assert "firefox" in out
        assert "auto-updates" in out

    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    def test_no_auto_update_marker_when_not_in_list(self, _pb, capsys):
        """Brew not in auto-update list shows no marker."""
        from versiontracker.handlers.brew_handlers import _display_brew_list

        opts = MagicMock(show_auto_updates=True, exclude_auto_updates=False, only_auto_updates=False)
        _display_brew_list(["chrome"], ["firefox"], opts)
        out = capsys.readouterr().out
        assert "chrome" in out
        assert "auto-updates" not in out


# ---------------------------------------------------------------------------
# _handle_export_if_requested — stdout print path (line 138)
# ---------------------------------------------------------------------------


class TestHandleExportIfRequested:
    """Tests for _handle_export_if_requested() stdout print path."""

    @patch("versiontracker.handlers.brew_handlers.handle_export", return_value='[{"name":"firefox"}]')
    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    def test_prints_to_stdout_when_no_output_file(self, _pb, mock_export, capsys):
        """When output_file is None, export result is printed to stdout."""
        opts = MagicMock(export_format="json", output_file=None)
        _handle_export_if_requested(["firefox"], opts)
        captured = capsys.readouterr()
        assert "firefox" in captured.out

    @patch("versiontracker.handlers.brew_handlers.handle_export", return_value=0)
    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    def test_no_print_when_output_file_set(self, _pb, mock_export, capsys):
        """When output_file is set, nothing is printed."""
        opts = MagicMock(export_format="json", output_file="/tmp/out.json")
        _handle_export_if_requested(["firefox"], opts)
        captured = capsys.readouterr()
        assert captured.out == ""


# ---------------------------------------------------------------------------
# handle_list_brews — outer exception handler (lines 179-182)
# ---------------------------------------------------------------------------


class TestHandleListBrewsOuterException:
    """Tests for the outer try/except in handle_list_brews."""

    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    def test_outer_exception_returns_1(self, _pb):
        """An exception raised before the inner try returns exit code 1."""
        with patch(
            "versiontracker.handlers.brew_handlers.create_progress_bar",
            side_effect=RuntimeError("boom"),
        ):
            result = handle_list_brews(MagicMock())
        assert result == 1


# ---------------------------------------------------------------------------
# _get_homebrew_casks — generic exception path (lines 257-260)
# ---------------------------------------------------------------------------


class TestGetHomebrewCasksHandler:
    """Tests for _get_homebrew_casks() generic exception fallback."""

    @patch("versiontracker.handlers.brew_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks", side_effect=OSError("disk error"))
    def test_generic_exception_returns_empty(self, _casks, _pb):
        """A non-HomebrewError exception returns [] and doesn't raise."""
        result = _get_homebrew_casks()
        assert result == []


# ---------------------------------------------------------------------------
# _log_debug_info — debug logging paths (lines 273-283)
# ---------------------------------------------------------------------------


class TestLogDebugInfo:
    """Tests for _log_debug_info() debug logging branches."""

    def test_no_debug_does_nothing(self):
        """No logging when debug is False/0."""
        opts = MagicMock(debug=False)
        _log_debug_info(opts, [("App", "1.0")], ["brew"], [("App", "1.0")])
        # No exception means pass

    def test_debug_logs_items(self):
        """All three loops execute when debug is True."""
        opts = MagicMock(debug=True)
        with patch("versiontracker.handlers.brew_handlers.logging") as mock_log:
            _log_debug_info(
                opts,
                [("App", "1.0"), ("App2", "2.0")],
                ["brew1", "brew2"],
                [("App", "1.0")],
            )
        assert mock_log.debug.call_count >= 6  # 3 headers + at least 3 items


# ---------------------------------------------------------------------------
# _determine_strict_mode — test-detection and strict_recommend paths
# ---------------------------------------------------------------------------


class TestDetermineStrictMode:
    """Tests for _determine_strict_mode() branches."""

    def test_strict_recom_returns_true(self):
        opts = MagicMock(strict_recom=True)
        assert _determine_strict_mode(opts) is True

    def test_test_detection_sets_mock_test(self):
        """When sys.argv has ≤1 elements, mock_test is set and False is returned."""
        opts = MagicMock(spec=["strict_recommend", "recommend"])
        with patch.object(sys, "argv", ["pytest"]):
            result = _determine_strict_mode(opts)
        assert result is False
        assert opts.mock_test is True

    def test_strict_recommend_returns_true(self):
        """strict_recommend attribute triggers True when argv has entries."""
        opts = MagicMock(strict_recom=False, strict_recommend=True)
        with patch.object(sys, "argv", ["versiontracker", "--strict-recom"]):
            result = _determine_strict_mode(opts)
        assert result is True
