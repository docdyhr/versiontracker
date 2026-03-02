"""Tests for versiontracker.handlers.error_handlers — coverage improvement.

Covers all 8 functions: handle_permission_error, handle_timeout_error,
handle_network_error, handle_homebrew_not_found, handle_config_error,
handle_keyboard_interrupt, handle_generic_error, handle_top_level_exception.
"""

from unittest.mock import MagicMock, patch

from versiontracker.exceptions import ConfigError
from versiontracker.handlers.error_handlers import (
    handle_config_error,
    handle_generic_error,
    handle_homebrew_not_found,
    handle_keyboard_interrupt,
    handle_network_error,
    handle_permission_error,
    handle_timeout_error,
    handle_top_level_exception,
)


def _mock_progress_bar():
    """Create a mock progress_bar that returns identity for color calls."""
    pb = MagicMock()
    pb.color.return_value = lambda x: x
    return pb


# ---------------------------------------------------------------------------
# handle_permission_error
# ---------------------------------------------------------------------------


class TestHandlePermissionError:
    """Tests for handle_permission_error()."""

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_returns_exit_code_1(self, _pb):
        assert handle_permission_error() == 1

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_default_context(self, _pb, capsys):
        handle_permission_error()
        output = capsys.readouterr().out
        assert "application data" in output

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_custom_context(self, _pb, capsys):
        handle_permission_error("system preferences")
        output = capsys.readouterr().out
        assert "system preferences" in output

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_prints_suggestion(self, _pb, capsys):
        handle_permission_error()
        output = capsys.readouterr().out
        assert "sudo" in output or "permissions" in output


# ---------------------------------------------------------------------------
# handle_timeout_error
# ---------------------------------------------------------------------------


class TestHandleTimeoutError:
    """Tests for handle_timeout_error()."""

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_returns_exit_code_1(self, _pb):
        assert handle_timeout_error() == 1

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_default_context(self, _pb, capsys):
        handle_timeout_error()
        output = capsys.readouterr().out
        assert "application data" in output

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_custom_context(self, _pb, capsys):
        handle_timeout_error("brew database")
        output = capsys.readouterr().out
        assert "brew database" in output


# ---------------------------------------------------------------------------
# handle_network_error
# ---------------------------------------------------------------------------


class TestHandleNetworkError:
    """Tests for handle_network_error()."""

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_returns_exit_code_1(self, _pb):
        assert handle_network_error() == 1

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_default_context(self, _pb, capsys):
        handle_network_error()
        output = capsys.readouterr().out
        assert "checking for updates" in output

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_custom_context(self, _pb, capsys):
        handle_network_error("fetching cask info")
        output = capsys.readouterr().out
        assert "fetching cask info" in output

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_prints_connection_hint(self, _pb, capsys):
        handle_network_error()
        output = capsys.readouterr().out
        assert "internet connection" in output


# ---------------------------------------------------------------------------
# handle_homebrew_not_found
# ---------------------------------------------------------------------------


class TestHandleHomebrewNotFound:
    """Tests for handle_homebrew_not_found()."""

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_returns_exit_code_1(self, _pb):
        assert handle_homebrew_not_found() == 1

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_prints_not_found_message(self, _pb, capsys):
        handle_homebrew_not_found()
        output = capsys.readouterr().out
        assert "Homebrew" in output
        assert "not found" in output

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_prints_install_suggestion(self, _pb, capsys):
        handle_homebrew_not_found()
        output = capsys.readouterr().out
        assert "installed" in output or "configured" in output


# ---------------------------------------------------------------------------
# handle_config_error
# ---------------------------------------------------------------------------


class TestHandleConfigError:
    """Tests for handle_config_error()."""

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_returns_exit_code_1(self, _pb):
        err = ConfigError("bad yaml format")
        assert handle_config_error(err) == 1

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_prints_error_message(self, _pb, capsys):
        err = ConfigError("missing key")
        handle_config_error(err)
        output = capsys.readouterr().out
        assert "Configuration Error" in output
        assert "missing key" in output

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_prints_config_suggestion(self, _pb, capsys):
        err = ConfigError("parse failure")
        handle_config_error(err)
        output = capsys.readouterr().out
        assert "configuration file" in output


# ---------------------------------------------------------------------------
# handle_keyboard_interrupt
# ---------------------------------------------------------------------------


class TestHandleKeyboardInterrupt:
    """Tests for handle_keyboard_interrupt()."""

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_returns_exit_code_130(self, _pb):
        assert handle_keyboard_interrupt() == 130

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_prints_cancel_message(self, _pb, capsys):
        handle_keyboard_interrupt()
        output = capsys.readouterr().out
        assert "canceled" in output or "cancelled" in output


# ---------------------------------------------------------------------------
# handle_generic_error
# ---------------------------------------------------------------------------


class TestHandleGenericError:
    """Tests for handle_generic_error()."""

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_returns_exit_code_1(self, _pb):
        assert handle_generic_error(RuntimeError("fail")) == 1

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_without_context(self, _pb, capsys):
        handle_generic_error(ValueError("oops"), debug=False)
        output = capsys.readouterr().out
        assert "Error: oops" in output

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_with_context(self, _pb, capsys):
        handle_generic_error(ValueError("oops"), context="loading apps", debug=False)
        output = capsys.readouterr().out
        assert "Error loading apps" in output

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    @patch("versiontracker.handlers.error_handlers.traceback")
    def test_debug_true_shows_traceback(self, mock_tb, _pb):
        handle_generic_error(RuntimeError("boom"), debug=True)
        mock_tb.print_exc.assert_called_once()

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_debug_false_shows_hint(self, _pb, capsys):
        handle_generic_error(RuntimeError("boom"), debug=False)
        output = capsys.readouterr().out
        assert "--debug" in output

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    @patch("versiontracker.handlers.error_handlers.get_config")
    def test_debug_none_uses_config_true(self, mock_config, _pb):
        mock_config.return_value = MagicMock(debug=True)
        with patch("versiontracker.handlers.error_handlers.traceback") as mock_tb:
            handle_generic_error(RuntimeError("boom"), debug=None)
            mock_tb.print_exc.assert_called_once()

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    @patch("versiontracker.handlers.error_handlers.get_config")
    def test_debug_none_uses_config_false(self, mock_config, _pb, capsys):
        mock_config.return_value = MagicMock(debug=False)
        handle_generic_error(RuntimeError("boom"), debug=None)
        output = capsys.readouterr().out
        assert "--debug" in output


# ---------------------------------------------------------------------------
# handle_top_level_exception
# ---------------------------------------------------------------------------


class TestHandleTopLevelException:
    """Tests for handle_top_level_exception()."""

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_config_error_routes_to_handle_config_error(self, _pb):
        err = ConfigError("bad config")
        result = handle_top_level_exception(err)
        assert result == 1

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    def test_keyboard_interrupt_routes_to_handle_keyboard_interrupt(self, _pb):
        result = handle_top_level_exception(KeyboardInterrupt())
        assert result == 130

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    @patch("versiontracker.handlers.error_handlers.get_config")
    def test_runtime_error_routes_to_handle_generic_error(self, mock_config, _pb):
        mock_config.return_value = MagicMock(debug=False)
        result = handle_top_level_exception(RuntimeError("unexpected"))
        assert result == 1

    @patch(
        "versiontracker.handlers.error_handlers.create_progress_bar",
        return_value=_mock_progress_bar(),
    )
    @patch("versiontracker.handlers.error_handlers.get_config")
    def test_base_exception_wraps_as_exception(self, mock_config, _pb):
        """Non-Exception BaseException gets wrapped via Exception(str(e))."""
        mock_config.return_value = MagicMock(debug=False)
        result = handle_top_level_exception(SystemExit(42))
        assert result == 1
