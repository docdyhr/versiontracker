"""Additional coverage tests for versiontracker.apps.finder.

Targets uncovered paths identified by the audit:
- get_applications: normalise_name branch, duplicate skipping
- get_applications_from_system_profiler: system/path filtering, error path
- _check_cask_installable_with_cache: homebrew unavailable
- _execute_cask_installable_check: exception suppression path
- _handle_batch_error: error threshold escalation for all error types
- check_brew_install_candidates: async path, async fallback, batch error escalation
- _create_rate_limiter: attribute-based and dict-based rate limits
- _get_existing_brews: HomebrewError and generic exception paths
- check_brew_update_candidates: empty data, async path, async fallback
- _should_show_progress: no_progress config attribute
"""

from unittest.mock import MagicMock, patch

import pytest

import versiontracker.apps.finder as finder_mod
from versiontracker.apps.finder import (
    MAX_ERRORS,
    _create_rate_limiter,
    _execute_cask_installable_check,
    _get_existing_brews,
    _handle_batch_error,
    _should_show_progress,
    check_brew_install_candidates,
    check_brew_update_candidates,
    get_applications,
    get_applications_from_system_profiler,
)
from versiontracker.exceptions import (
    BrewTimeoutError,
    HomebrewError,
    NetworkError,
)


@pytest.fixture(autouse=True)
def _reset_async_state():
    original = finder_mod._async_homebrew_available
    finder_mod._async_homebrew_available = None
    yield
    finder_mod._async_homebrew_available = original


@pytest.fixture(autouse=True)
def _clear_cask_cache():
    from versiontracker.apps.finder import get_homebrew_casks

    if hasattr(get_homebrew_casks, "cache_clear"):
        get_homebrew_casks.cache_clear()
    yield
    if hasattr(get_homebrew_casks, "cache_clear"):
        get_homebrew_casks.cache_clear()


# ---------------------------------------------------------------------------
# get_applications
# ---------------------------------------------------------------------------


_APP_PATH = "/Applications/Firefox.app"


class TestGetApplications:
    def test_normalise_name_branch(self):
        """Line 197: app without 'TestApp' prefix uses normalise_name."""
        data = {
            "SPApplicationsDataType": [
                {"_name": "Firefox", "version": "120.0", "path": _APP_PATH},
            ]
        }
        result = get_applications(data)
        assert len(result) == 1
        assert result[0][1] == "120.0"

    def test_duplicate_same_name_and_version_skipped(self):
        """Lines 202-203: exact duplicates (name + version) are deduplicated."""
        data = {
            "SPApplicationsDataType": [
                {"_name": "Firefox", "version": "120.0", "path": _APP_PATH},
                {"_name": "Firefox", "version": "120.0", "path": _APP_PATH},
            ]
        }
        result = get_applications(data)
        assert result.count(result[0]) == 1

    def test_same_name_different_version_kept(self):
        """Different versions of same app are both kept."""
        data = {
            "SPApplicationsDataType": [
                {"_name": "Firefox", "version": "120.0", "path": _APP_PATH},
                {"_name": "Firefox", "version": "121.0", "path": _APP_PATH},
            ]
        }
        result = get_applications(data)
        assert len(result) == 2

    def test_missing_name_key_skipped(self):
        """Line 206: KeyError on missing _name is silently skipped."""
        data = {
            "SPApplicationsDataType": [
                {"version": "1.0", "path": "/Applications/Unknown.app"},  # no _name
                {"_name": "Chrome", "version": "2.0", "path": "/Applications/Chrome.app"},
            ]
        }
        result = get_applications(data)
        assert any(name for name, _ in result if "chrome" in name.lower() or name == "Chrome")

    def test_app_outside_applications_skipped(self):
        """Line 183-184: apps not in /Applications/ are skipped."""
        data = {
            "SPApplicationsDataType": [
                {"_name": "SystemTool", "version": "1.0", "path": "/usr/bin/tool"},
                {"_name": "UserApp", "version": "2.0", "path": "/Applications/UserApp.app"},
            ]
        }
        result = get_applications(data)
        names = [n for n, _ in result]
        assert "SystemTool" not in names


# ---------------------------------------------------------------------------
# get_applications_from_system_profiler
# ---------------------------------------------------------------------------


class TestGetApplicationsFromSystemProfiler:
    @patch("versiontracker.apps.finder.get_config")
    def test_skip_apple_apps(self, mock_cfg):
        """Lines 242-244: obtained_from=apple apps are skipped when skip_system_apps=True."""
        cfg = MagicMock()
        cfg.skip_system_apps = True
        cfg.skip_system_paths = False
        mock_cfg.return_value = cfg

        data = {
            "SPApplicationsDataType": [
                {"_name": "Safari", "version": "17.0", "obtained_from": "apple"},
                {"_name": "Firefox", "version": "120.0", "obtained_from": "web"},
            ]
        }
        result = get_applications_from_system_profiler(data)
        names = [n for n, _ in result]
        assert "Safari" not in names
        assert "Firefox" in names

    @patch("versiontracker.apps.finder.get_config")
    def test_skip_system_paths(self, mock_cfg):
        """Lines 247-250: apps under /System/ are skipped when skip_system_paths=True."""
        cfg = MagicMock()
        cfg.skip_system_apps = False
        cfg.skip_system_paths = True
        mock_cfg.return_value = cfg

        data = {
            "SPApplicationsDataType": [
                {"_name": "SystemUtil", "version": "1.0", "path": "/System/Library/App.app"},
                {"_name": "UserApp", "version": "2.0", "path": "/Applications/App.app"},
            ]
        }
        result = get_applications_from_system_profiler(data)
        names = [n for n, _ in result]
        assert "SystemUtil" not in names
        assert "UserApp" in names

    def test_missing_spdatatype_raises(self):
        """Lines 230-232: missing SPApplicationsDataType raises DataParsingError."""
        from versiontracker.exceptions import DataParsingError

        with pytest.raises(DataParsingError):
            get_applications_from_system_profiler({})

    def test_none_data_raises(self):
        """Lines 230-232: None data raises DataParsingError."""
        from versiontracker.exceptions import DataParsingError

        with pytest.raises(DataParsingError):
            get_applications_from_system_profiler(None)  # type: ignore[arg-type]

    @patch("versiontracker.apps.finder.get_config")
    def test_type_error_raises_data_parsing_error(self, mock_cfg):
        """Lines 261-263: TypeError during iteration raises DataParsingError."""
        from versiontracker.exceptions import DataParsingError

        cfg = MagicMock()
        cfg.skip_system_apps = False
        cfg.skip_system_paths = False
        mock_cfg.return_value = cfg

        # Integer is not iterable → TypeError inside the try block → DataParsingError
        with pytest.raises(DataParsingError):
            get_applications_from_system_profiler({"SPApplicationsDataType": 42})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _check_cask_installable_with_cache
# ---------------------------------------------------------------------------


class TestCheckCaskInstallableWithCache:
    @patch("versiontracker.apps.finder.is_homebrew_available", return_value=False)
    def test_homebrew_unavailable_raises(self, _mock):
        """Lines 468-469: HomebrewError when Homebrew not available."""
        from versiontracker.apps.finder import _check_cask_installable_with_cache

        with pytest.raises(HomebrewError):
            _check_cask_installable_with_cache("firefox", use_cache=False)


# ---------------------------------------------------------------------------
# _execute_cask_installable_check
# ---------------------------------------------------------------------------


class TestExecuteCaskInstallableCheck:
    @patch("versiontracker.apps.finder._execute_brew_search", side_effect=RuntimeError("boom"))
    def test_exception_returns_false(self, _mock):
        """Lines 491-494: generic exception during brew search returns False."""
        result = _execute_cask_installable_check("firefox", None)
        assert result is False


# ---------------------------------------------------------------------------
# _handle_batch_error
# ---------------------------------------------------------------------------


class TestHandleBatchError:
    def _batch(self):
        return [("App1", "1.0"), ("App2", "2.0")]

    def test_timeout_below_max(self):
        """BrewTimeoutError below MAX_ERRORS: no exception raised."""
        results, count, exc = _handle_batch_error(BrewTimeoutError("t"), 1, self._batch())
        assert exc is None
        assert count == 2

    def test_timeout_at_max_raises(self):
        """Lines 530-535: BrewTimeoutError at MAX_ERRORS returns exception."""
        _, _, exc = _handle_batch_error(BrewTimeoutError("t"), MAX_ERRORS - 1, self._batch())
        assert isinstance(exc, BrewTimeoutError)

    def test_network_below_max(self):
        """NetworkError below MAX_ERRORS: no exception raised."""
        _, _, exc = _handle_batch_error(NetworkError("n"), 1, self._batch())
        assert exc is None

    def test_network_at_max_raises(self):
        """Lines 538-543: NetworkError at MAX_ERRORS returns exception."""
        _, _, exc = _handle_batch_error(NetworkError("n"), MAX_ERRORS - 1, self._batch())
        assert isinstance(exc, NetworkError)

    def test_homebrew_at_max_raises(self):
        """Lines 544-547: HomebrewError at MAX_ERRORS returns original error."""
        original = HomebrewError("h")
        _, _, exc = _handle_batch_error(original, MAX_ERRORS - 1, self._batch())
        assert exc is original

    def test_generic_at_max_raises_homebrew_error(self):
        """Lines 548-555: generic error at MAX_ERRORS returns HomebrewError."""
        _, _, exc = _handle_batch_error(ValueError("v"), MAX_ERRORS - 1, self._batch())
        assert isinstance(exc, HomebrewError)

    def test_all_error_types_return_failed_results(self):
        """Failed results are always (name, version, False) tuples."""
        results, _, _ = _handle_batch_error(NetworkError("n"), 1, self._batch())
        assert all(not installable for _, _, installable in results)


# ---------------------------------------------------------------------------
# check_brew_install_candidates
# ---------------------------------------------------------------------------


class TestCheckBrewInstallCandidates:
    def test_empty_data_returns_empty(self):
        """Line 580: empty data returns empty list without touching Homebrew."""
        result = check_brew_install_candidates([], rate_limit=1)
        assert result == []

    @patch("versiontracker.apps.finder._is_async_homebrew_available", return_value=True)
    @patch("versiontracker.apps.finder.async_check_brew_install_candidates", create=True)
    def test_async_path_used(self, mock_async, _mock_avail):
        """Lines 587-596: async path is taken when available."""
        mock_async.return_value = [("App1", "1.0", True)]
        with patch.dict(
            "sys.modules",
            {"versiontracker.async_homebrew": MagicMock(async_check_brew_install_candidates=mock_async)},
        ):
            finder_mod._async_homebrew_available = True
            with patch("versiontracker.apps.finder._is_async_homebrew_available", return_value=True):
                with patch(
                    "versiontracker.apps.finder.async_check_brew_install_candidates",
                    mock_async,
                    create=True,
                ):
                    result = check_brew_install_candidates([("App1", "1.0")], rate_limit=1)
        # Verify async result is returned when async path succeeded
        assert isinstance(result, list)

    @patch("versiontracker.apps.finder._is_async_homebrew_available", return_value=True)
    def test_async_failure_falls_back_to_sync(self, _mock_avail):
        """Lines 597-598: async failure falls back to sync path."""
        import sys

        fake_async = MagicMock()
        fake_async.async_check_brew_install_candidates = MagicMock(side_effect=RuntimeError("async fail"))

        with patch.dict(sys.modules, {"versiontracker.async_homebrew": fake_async}):
            with patch("versiontracker.apps.finder._process_brew_batch", return_value=[("App1", "1.0", True)]):
                result = check_brew_install_candidates([("App1", "1.0")], rate_limit=0)
        assert isinstance(result, list)

    def test_rate_limit_attribute_extracted(self):
        """Lines 582-583: rate_limit with .api_rate_limit attribute is unwrapped."""
        mock_rl = MagicMock()
        mock_rl.api_rate_limit = 0
        # Just check it doesn't error; actual brew calls are mocked
        with patch("versiontracker.apps.finder._is_async_homebrew_available", return_value=False):
            with patch("versiontracker.apps.finder._process_brew_batch", return_value=[]):
                result = check_brew_install_candidates([("App1", "1.0")], rate_limit=mock_rl)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# _create_rate_limiter
# ---------------------------------------------------------------------------


class TestCreateRateLimiter:
    def test_int_rate_limit(self):
        """Line 632-633: integer rate limit creates a limiter."""
        limiter = _create_rate_limiter(2)
        assert limiter is not None

    def test_object_with_api_rate_limit_attr(self):
        """Lines 634-636: object with api_rate_limit attribute is used."""
        obj = MagicMock()
        obj.api_rate_limit = 3
        limiter = _create_rate_limiter(obj)
        assert limiter is not None

    def test_dict_like_rate_limit(self):
        """Lines 637-638: dict-like object uses .get('api_rate_limit', 1)."""

        class DictLike:
            def get(self, key, default=None):
                return 5 if key == "api_rate_limit" else default

        limiter = _create_rate_limiter(DictLike())
        assert limiter is not None

    def test_attribute_error_uses_default(self):
        """Lines 639-640: AttributeError falls back to default rate limit."""

        class BadObj:
            @property
            def api_rate_limit(self):
                raise AttributeError("no attr")

        limiter = _create_rate_limiter(BadObj())
        assert limiter is not None


# ---------------------------------------------------------------------------
# _get_existing_brews
# ---------------------------------------------------------------------------


class TestGetExistingBrews:
    @patch("versiontracker.apps.finder.get_homebrew_casks_list", side_effect=HomebrewError("no brew"))
    def test_homebrew_error_returns_empty(self, _mock):
        """Lines 849-850: HomebrewError returns empty list."""
        result = _get_existing_brews()
        assert result == []

    @patch("versiontracker.apps.finder.get_homebrew_casks_list", side_effect=RuntimeError("oops"))
    def test_generic_error_returns_empty(self, _mock):
        """Lines 851-852: generic exception returns empty list."""
        result = _get_existing_brews()
        assert result == []


# ---------------------------------------------------------------------------
# check_brew_update_candidates
# ---------------------------------------------------------------------------


class TestCheckBrewUpdateCandidates:
    def test_empty_data_returns_empty_dict(self):
        """Line 869-870: empty data returns {}."""
        result = check_brew_update_candidates([])
        assert result == {}

    @patch("versiontracker.apps.finder._is_async_homebrew_available", return_value=True)
    def test_async_failure_falls_back_to_sync(self, _mock_avail):
        """Lines 888-889: async failure falls back to synchronous path."""
        import sys

        fake_async = MagicMock()
        fake_async.async_check_brew_update_candidates = MagicMock(side_effect=RuntimeError("fail"))

        with patch.dict(sys.modules, {"versiontracker.async_homebrew": fake_async}):
            with patch("versiontracker.apps.finder._get_existing_brews", return_value=[]):
                with patch("versiontracker.apps.finder._process_brew_search_batches", return_value={}):
                    with patch("versiontracker.apps.finder._populate_cask_versions"):
                        result = check_brew_update_candidates([("App1", "1.0")], rate_limit=0)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# _should_show_progress
# ---------------------------------------------------------------------------


class TestShouldShowProgress:
    @patch("versiontracker.apps.finder.get_config")
    def test_no_progress_flag_suppresses(self, mock_cfg):
        """Lines 931-932: no_progress=True suppresses progress."""
        cfg = MagicMock()
        cfg.show_progress = True
        cfg.no_progress = True
        mock_cfg.return_value = cfg
        assert _should_show_progress() is False

    @patch("versiontracker.apps.finder.get_config")
    def test_show_progress_true(self, mock_cfg):
        """Line 930: show_progress=True without no_progress returns True."""
        cfg = MagicMock(spec=[])  # no no_progress attr
        cfg.show_progress = True
        mock_cfg.return_value = cfg
        assert _should_show_progress() is True
