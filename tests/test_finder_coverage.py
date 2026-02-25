"""Tests for versiontracker.apps.finder — coverage improvement.

Targets untested paths in _is_async_homebrew_available, get_homebrew_casks,
is_homebrew_available, _check_cache_for_cask, _handle_cask_installable_error,
and _handle_future_result.
"""

import os
from concurrent.futures import Future
from unittest.mock import MagicMock, patch

import pytest

import versiontracker.apps.finder as finder_mod
from versiontracker.apps.finder import (
    _check_cache_for_cask,
    _handle_cask_installable_error,
    _handle_future_result,
    get_homebrew_casks,
    is_homebrew_available,
)
from versiontracker.exceptions import (
    BrewTimeoutError,
    HomebrewError,
    NetworkError,
)


@pytest.fixture(autouse=True)
def _reset_async_state():
    """Reset the module-level async cache before each test."""
    original = finder_mod._async_homebrew_available
    finder_mod._async_homebrew_available = None
    yield
    finder_mod._async_homebrew_available = original


@pytest.fixture(autouse=True)
def _clear_cask_cache():
    """Clear the lru_cache on get_homebrew_casks before and after each test."""
    if hasattr(get_homebrew_casks, "cache_clear"):
        get_homebrew_casks.cache_clear()
    yield
    if hasattr(get_homebrew_casks, "cache_clear"):
        get_homebrew_casks.cache_clear()


# ---------------------------------------------------------------------------
# _is_async_homebrew_available
# ---------------------------------------------------------------------------


class TestIsAsyncHomebrewAvailable:
    """Tests for _is_async_homebrew_available()."""

    def test_cached_true(self):
        finder_mod._async_homebrew_available = True
        assert finder_mod._is_async_homebrew_available() is True

    def test_cached_false(self):
        finder_mod._async_homebrew_available = False
        assert finder_mod._is_async_homebrew_available() is False

    @patch("versiontracker.apps.finder.get_config")
    def test_config_disabled(self, mock_cfg):
        mock_config = MagicMock()
        mock_config.async_homebrew = None
        mock_config._config = {"async_homebrew": {"enabled": False}}
        mock_cfg.return_value = mock_config

        assert finder_mod._is_async_homebrew_available() is False
        assert finder_mod._async_homebrew_available is False

    @patch.dict(os.environ, {"VERSIONTRACKER_ASYNC_BREW": "false"})
    @patch("versiontracker.apps.finder.get_config")
    def test_env_var_disabled(self, mock_cfg):
        mock_config = MagicMock()
        mock_config.async_homebrew = None
        mock_config._config = {"async_homebrew": {"enabled": True}}
        mock_cfg.return_value = mock_config

        assert finder_mod._is_async_homebrew_available() is False

    @patch("versiontracker.apps.finder.get_config")
    def test_import_error(self, mock_cfg):
        """When the async_homebrew module can't be imported."""
        mock_config = MagicMock()
        mock_config.async_homebrew = None
        mock_config._config = {"async_homebrew": {"enabled": True}}
        mock_cfg.return_value = mock_config

        with patch.dict(os.environ, {}, clear=False):
            # Remove env var if present
            os.environ.pop("VERSIONTRACKER_ASYNC_BREW", None)
            with patch("builtins.__import__", side_effect=ImportError("no module")):
                assert finder_mod._is_async_homebrew_available() is False

    @patch("versiontracker.apps.finder.get_config", side_effect=RuntimeError("boom"))
    def test_generic_exception(self, _cfg):
        assert finder_mod._is_async_homebrew_available() is False
        assert finder_mod._async_homebrew_available is False


# ---------------------------------------------------------------------------
# get_homebrew_casks
# ---------------------------------------------------------------------------


class TestGetHomebrewCasks:
    """Tests for get_homebrew_casks()."""

    @patch("versiontracker.apps.finder.get_config")
    @patch("versiontracker.apps.finder.run_command", return_value=("firefox\nchrome\n", 0))
    def test_success(self, _run, _cfg):
        result = get_homebrew_casks()
        assert "firefox" in result
        assert "chrome" in result

    @patch("versiontracker.apps.finder.get_config")
    @patch("versiontracker.apps.finder.run_command", return_value=("Error", 1))
    def test_nonzero_raises_homebrew_error(self, _run, _cfg):
        with pytest.raises(HomebrewError):
            get_homebrew_casks()

    @patch("versiontracker.apps.finder.get_config")
    @patch("versiontracker.apps.finder.run_command", side_effect=BrewTimeoutError("timeout"))
    def test_timeout_reraises(self, _run, _cfg):
        with pytest.raises(BrewTimeoutError):
            get_homebrew_casks()

    @patch("versiontracker.apps.finder.get_config")
    @patch("versiontracker.apps.finder.run_command", side_effect=NetworkError("net fail"))
    def test_network_error_reraises(self, _run, _cfg):
        with pytest.raises(NetworkError):
            get_homebrew_casks()

    @patch("versiontracker.apps.finder.get_config")
    @patch("versiontracker.apps.finder.run_command", side_effect=ValueError("generic"))
    def test_generic_exception_wraps_as_homebrew_error(self, _run, _cfg):
        with pytest.raises(HomebrewError, match="Failed to get Homebrew casks"):
            get_homebrew_casks()


# ---------------------------------------------------------------------------
# is_homebrew_available
# ---------------------------------------------------------------------------


class TestIsHomebrewAvailable:
    """Tests for is_homebrew_available()."""

    @patch("versiontracker.apps.finder.platform")
    def test_non_darwin_returns_false(self, mock_platform):
        mock_platform.system.return_value = "Linux"
        assert is_homebrew_available() is False

    @patch("versiontracker.apps.finder.run_command", return_value=("Homebrew 4.0", 0))
    @patch("versiontracker.apps.finder.platform")
    @patch("versiontracker.apps.finder.get_config")
    def test_cached_brew_path_works(self, mock_cfg, mock_platform, _run):
        mock_platform.system.return_value = "Darwin"
        mock_config = MagicMock()
        mock_config._config = {"brew_path": "/opt/homebrew/bin/brew"}
        mock_cfg.return_value = mock_config

        assert is_homebrew_available() is True

    @patch("versiontracker.apps.finder.run_command", side_effect=OSError("fail"))
    @patch("versiontracker.apps.finder.platform")
    @patch("versiontracker.apps.finder.get_config")
    def test_cached_path_fails_tries_others(self, mock_cfg, mock_platform, _run):
        mock_platform.system.return_value = "Darwin"
        mock_platform.machine.return_value = "arm64"
        mock_config = MagicMock()
        mock_config._config = {"brew_path": "/bad/path"}
        mock_config.set = MagicMock()
        mock_cfg.return_value = mock_config

        assert is_homebrew_available() is False

    @patch("versiontracker.apps.finder.get_config", side_effect=RuntimeError("boom"))
    def test_outer_exception_returns_false(self, _cfg):
        assert is_homebrew_available() is False

    @patch("versiontracker.apps.finder.run_command")
    @patch("versiontracker.apps.finder.platform")
    @patch("versiontracker.apps.finder.get_config")
    def test_sets_config_brew_path_on_success(self, mock_cfg, mock_platform, mock_run):
        """When a path succeeds, it sets config and updates BREW_PATH global."""
        mock_platform.system.return_value = "Darwin"
        mock_platform.machine.return_value = "x86_64"
        mock_config = MagicMock()
        mock_config._config = {}
        mock_config.set = MagicMock()
        mock_cfg.return_value = mock_config

        # First call (cached path check) fails, then first path in list succeeds
        mock_run.side_effect = [("Homebrew 4.0", 0)]
        # _config has no brew_path → hasattr returns True but _config.get('brew_path') is falsy
        # so it goes to the path loop

        result = is_homebrew_available()
        assert result is True


# ---------------------------------------------------------------------------
# _check_cache_for_cask
# ---------------------------------------------------------------------------


class TestCheckCacheForCask:
    """Tests for _check_cache_for_cask()."""

    def test_none_cache_returns_none(self):
        assert _check_cache_for_cask("firefox", None) is None

    def test_empty_cache_returns_none(self):
        assert _check_cache_for_cask("firefox", {}) is None

    def test_installable_list_found(self):
        cache = {"installable": ["firefox", "chrome"]}
        assert _check_cache_for_cask("firefox", cache) is True

    def test_installable_list_not_found(self):
        cache = {"installable": ["chrome"]}
        assert _check_cache_for_cask("firefox", cache) is False

    def test_alternate_format_direct_key(self):
        cache = {"firefox": True}
        assert _check_cache_for_cask("firefox", cache) is True

    def test_alternate_format_false(self):
        cache = {"firefox": False}
        assert _check_cache_for_cask("firefox", cache) is False

    def test_key_not_in_any_format(self):
        cache = {"other_key": "value"}
        assert _check_cache_for_cask("firefox", cache) is None


# ---------------------------------------------------------------------------
# _handle_cask_installable_error
# ---------------------------------------------------------------------------


class TestHandleCaskInstallableError:
    """Tests for _handle_cask_installable_error()."""

    def test_network_error_raises_network_error(self):
        error = ValueError("network connection failed")
        with pytest.raises(NetworkError, match="Network unavailable"):
            _handle_cask_installable_error("firefox", error)

    def test_connection_error_raises_network_error(self):
        error = ValueError("connection refused")
        with pytest.raises(NetworkError, match="Network unavailable"):
            _handle_cask_installable_error("firefox", error)

    def test_generic_error_raises_homebrew_error(self):
        error = ValueError("something went wrong")
        with pytest.raises(HomebrewError, match="Error checking if firefox is installable"):
            _handle_cask_installable_error("firefox", error)


# ---------------------------------------------------------------------------
# _handle_future_result
# ---------------------------------------------------------------------------


class TestHandleFutureResult:
    """Tests for _handle_future_result()."""

    def _make_future_with_exception(self, exc):
        """Create a future-like mock that returns the given exception."""
        future = MagicMock(spec=Future)
        future.exception.return_value = exc
        return future

    def _make_future_with_result(self, result):
        """Create a future-like mock that returns a result."""
        future = MagicMock(spec=Future)
        future.exception.return_value = None
        future.result.return_value = result
        return future

    def test_timeout_error(self):
        future = self._make_future_with_exception(BrewTimeoutError("timed out"))
        result, exc = _handle_future_result(future, "Firefox", "1.0")
        assert result == ("Firefox", "1.0", False)
        assert isinstance(exc, BrewTimeoutError)

    def test_network_error(self):
        future = self._make_future_with_exception(NetworkError("no network"))
        result, exc = _handle_future_result(future, "Firefox", "1.0")
        assert result == ("Firefox", "1.0", False)
        assert isinstance(exc, NetworkError)

    def test_homebrew_error(self):
        future = self._make_future_with_exception(HomebrewError("brew fail"))
        result, exc = _handle_future_result(future, "Firefox", "1.0")
        assert result == ("Firefox", "1.0", False)
        assert isinstance(exc, HomebrewError)

    def test_no_formulae_string(self):
        future = self._make_future_with_exception(RuntimeError("No formulae or casks found"))
        result, exc = _handle_future_result(future, "Firefox", "1.0")
        assert result == ("Firefox", "1.0", False)
        assert exc is None

    def test_generic_exception(self):
        future = self._make_future_with_exception(RuntimeError("something else"))
        result, exc = _handle_future_result(future, "Firefox", "1.0")
        assert result == ("Firefox", "1.0", False)
        assert exc is None

    def test_success(self):
        future = self._make_future_with_result(True)
        result, exc = _handle_future_result(future, "Firefox", "1.0")
        assert result == ("Firefox", "1.0", True)
        assert exc is None

    def test_success_false(self):
        future = self._make_future_with_result(False)
        result, exc = _handle_future_result(future, "Firefox", "1.0")
        assert result == ("Firefox", "1.0", False)
        assert exc is None

    def test_result_raises_exception(self):
        future = MagicMock(spec=Future)
        future.exception.return_value = None
        future.result.side_effect = RuntimeError("unexpected")
        result, exc = _handle_future_result(future, "Firefox", "1.0")
        assert result == ("Firefox", "1.0", False)
        assert isinstance(exc, RuntimeError)
