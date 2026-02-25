"""Tests for versiontracker.handlers.brew_handlers — coverage improvement.

Targets error paths in handle_list_brews, handle_brew_recommendations,
_get_rate_limit, and _get_and_filter_brews.
"""

from unittest.mock import MagicMock, patch

from versiontracker.exceptions import HomebrewError, NetworkError
from versiontracker.handlers.brew_handlers import (
    _get_and_filter_brews,
    _get_rate_limit,
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
