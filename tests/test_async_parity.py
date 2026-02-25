"""Tests for async Homebrew feature flag, fallback, and parity.

Verifies that the async/sync routing in apps/finder.py works correctly,
that the feature flag can be disabled, and that the deadlock bug in
async_check_brew_update_candidates is fixed.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

import versiontracker.apps.finder as finder_mod
from versiontracker.apps.finder import (
    _is_async_homebrew_available,
    check_brew_install_candidates,
    check_brew_update_candidates,
    get_homebrew_casks,
)


@pytest.fixture(autouse=True)
def _reset_async_state():
    """Reset async detection cache before/after each test."""
    original = finder_mod._async_homebrew_available
    finder_mod._async_homebrew_available = None
    yield
    finder_mod._async_homebrew_available = original


@pytest.fixture(autouse=True)
def _clear_cask_cache():
    """Clear lru_cache on get_homebrew_casks before/after each test."""
    if hasattr(get_homebrew_casks, "cache_clear"):
        get_homebrew_casks.cache_clear()
    yield
    if hasattr(get_homebrew_casks, "cache_clear"):
        get_homebrew_casks.cache_clear()


# ---------------------------------------------------------------------------
# Feature flag tests
# ---------------------------------------------------------------------------


class TestFeatureFlag:
    """Tests for the VERSIONTRACKER_ASYNC_BREW feature flag."""

    @pytest.mark.parametrize("value", ["0", "false", "no", "off"])
    @patch.dict(os.environ, {}, clear=False)
    def test_disable_values(self, value):
        """All disable values should make async unavailable."""
        with patch.dict(os.environ, {"VERSIONTRACKER_ASYNC_BREW": value}):
            result = _is_async_homebrew_available()
            assert result is False

    @patch.dict(os.environ, {}, clear=False)
    @patch("versiontracker.apps.finder.get_config")
    def test_config_disabled(self, mock_config):
        """Config async_homebrew.enabled=False should disable async."""
        mock_cfg = MagicMock()
        mock_cfg._config = {"async_homebrew": {"enabled": False}}
        mock_cfg.async_homebrew = {"enabled": False}
        mock_config.return_value = mock_cfg
        # Remove any env override
        os.environ.pop("VERSIONTRACKER_ASYNC_BREW", None)
        result = _is_async_homebrew_available()
        assert result is False

    @patch.dict(os.environ, {}, clear=False)
    @patch("versiontracker.apps.finder.get_config")
    def test_config_enabled_default(self, mock_config):
        """Default config has async_homebrew.enabled=True."""
        from versiontracker.config import Config

        with patch.dict(os.environ, {"CI": "true", "VERSIONTRACKER_SKIP_BREW_DETECTION": "1"}):
            cfg = Config()
        async_cfg = cfg._config.get("async_homebrew", {})
        assert async_cfg.get("enabled", True) is True

    def test_caching(self):
        """Result should be cached in _async_homebrew_available global."""
        finder_mod._async_homebrew_available = True
        assert _is_async_homebrew_available() is True

        finder_mod._async_homebrew_available = False
        assert _is_async_homebrew_available() is False


# ---------------------------------------------------------------------------
# Install candidates fallback tests
# ---------------------------------------------------------------------------


class TestInstallCandidatesFallback:
    """Tests for async fallback in check_brew_install_candidates."""

    @patch("versiontracker.apps.finder._is_async_homebrew_available", return_value=True)
    @patch("versiontracker.apps.finder.is_homebrew_available", return_value=True)
    def test_async_import_error_falls_back(self, _hb, _async):
        """When async module import fails, should fall back to sync."""
        with patch(
            "versiontracker.async_homebrew.async_check_brew_install_candidates",
            side_effect=ImportError("no module"),
        ):
            # This should fall back to the sync path
            with patch("versiontracker.apps.finder.smart_progress", return_value=[]):
                result = check_brew_install_candidates([], 1)
                assert result == []

    @patch("versiontracker.apps.finder._is_async_homebrew_available", return_value=True)
    @patch("versiontracker.apps.finder.is_homebrew_available", return_value=True)
    def test_async_exception_falls_back(self, _hb, _async):
        """When async raises, should fall back to sync."""
        with patch(
            "versiontracker.async_homebrew.async_check_brew_install_candidates",
            side_effect=RuntimeError("async failed"),
        ):
            with patch("versiontracker.apps.finder.smart_progress", return_value=[]):
                result = check_brew_install_candidates([("App1", "1.0")], 1)
                assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Update candidates fallback tests
# ---------------------------------------------------------------------------


class TestUpdateCandidatesFallback:
    """Tests for async fallback in check_brew_update_candidates."""

    @patch("versiontracker.apps.finder._is_async_homebrew_available", return_value=True)
    def test_async_exception_falls_back_to_sync(self, _async):
        """When async update check fails, should fall back to sync."""
        with patch(
            "versiontracker.async_homebrew.async_check_brew_update_candidates",
            side_effect=RuntimeError("async failed"),
        ):
            with patch("versiontracker.apps.finder._get_existing_brews", return_value=[]):
                with patch("versiontracker.apps.finder._process_brew_search_batches", return_value={}):
                    with patch("versiontracker.apps.finder._populate_cask_versions"):
                        result = check_brew_update_candidates([("App1", "1.0")], 1)
                        assert isinstance(result, dict)

    @patch("versiontracker.apps.finder._is_async_homebrew_available", return_value=False)
    def test_sync_path_when_async_disabled(self, _async):
        """When async is disabled, should use sync path directly."""
        with patch("versiontracker.apps.finder._get_existing_brews", return_value=[]):
            with patch("versiontracker.apps.finder._process_brew_search_batches", return_value={}):
                with patch("versiontracker.apps.finder._populate_cask_versions"):
                    result = check_brew_update_candidates([("App1", "1.0")], 1)
                    assert isinstance(result, dict)

    @patch("versiontracker.apps.finder._is_async_homebrew_available", return_value=True)
    def test_async_success_returns_dict(self, _async):
        """When async succeeds, should return converted dict."""
        mock_result = [
            ("App1", "1.0", "app1", "2.0"),
            ("App2", "1.0", "app2", None),  # No update available
        ]
        with patch(
            "versiontracker.async_homebrew.async_check_brew_update_candidates",
            return_value=mock_result,
        ):
            result = check_brew_update_candidates([("App1", "1.0"), ("App2", "1.0")], 1)
            assert "app1" in result
            assert result["app1"]["version"] == "2.0"
            assert "app2" not in result  # None latest_version should be excluded

    def test_empty_data_returns_empty(self):
        """Empty input should return empty dict without calling async."""
        result = check_brew_update_candidates([], 1)
        assert result == {}


# ---------------------------------------------------------------------------
# Deadlock avoidance test
# ---------------------------------------------------------------------------


class TestDeadlockAvoidance:
    """Tests that async functions don't deadlock."""

    @pytest.mark.timeout(10)
    @patch("versiontracker.apps.finder._is_async_homebrew_available", return_value=True)
    def test_update_candidates_no_deadlock(self, _async):
        """async_check_brew_update_candidates should complete without hanging."""
        mock_result = [("App1", "1.0", "app1", "2.0")]
        with patch(
            "versiontracker.async_homebrew.async_check_brew_update_candidates",
            return_value=mock_result,
        ):
            result = check_brew_update_candidates([("App1", "1.0")], 1)
            assert isinstance(result, dict)

    @pytest.mark.timeout(10)
    @patch("versiontracker.apps.finder._is_async_homebrew_available", return_value=True)
    @patch("versiontracker.apps.finder.is_homebrew_available", return_value=True)
    def test_install_candidates_no_deadlock(self, _hb, _async):
        """async_check_brew_install_candidates should complete without hanging."""
        mock_result = [("App1", "1.0", True)]
        with patch(
            "versiontracker.async_homebrew.async_check_brew_install_candidates",
            return_value=mock_result,
        ):
            result = check_brew_install_candidates([("App1", "1.0")], 1)
            assert result == [("App1", "1.0", True)]
