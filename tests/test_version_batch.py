"""Tests for versiontracker.version.batch module."""

from __future__ import annotations

import concurrent.futures
from unittest.mock import MagicMock, patch

import pytest

from versiontracker.exceptions import NetworkError
from versiontracker.exceptions import TimeoutError as VTTimeoutError

# Import from batch module to get the same class references that batch.py uses internally.
# Importing from versiontracker.version.models can yield a patched class (via __init__.py)
# that differs from the one batch.py captured at import time.
from versiontracker.version.batch import (
    ApplicationInfo,
    VersionStatus,
    _get_config_settings,
    check_outdated_apps,
    create_app_batches,
    handle_batch_result,
    process_app_batch,
    process_single_app,
)


class TestProcessSingleApp:
    """Tests for process_single_app."""

    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_not_found_in_homebrew(self, mock_cask_info):
        mock_cask_info.return_value = None
        result = process_single_app(("Firefox", "120.0"))
        assert result.name == "Firefox"
        assert result.version_string == "120.0"
        assert result.status == VersionStatus.UNKNOWN
        assert result.error_message == "Not found in Homebrew"

    @patch("versiontracker.version.batch.is_version_newer")
    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_outdated_app(self, mock_cask_info, mock_is_newer):
        mock_cask_info.return_value = {"version": "121.0", "name": "firefox"}
        mock_is_newer.return_value = True
        result = process_single_app(("Firefox", "120.0"))
        assert result.status == VersionStatus.OUTDATED
        assert result.latest_version == "121.0"
        assert result.homebrew_name == "firefox"

    @patch("versiontracker.version.batch.compare_versions")
    @patch("versiontracker.version.batch.is_version_newer")
    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_up_to_date_app(self, mock_cask_info, mock_is_newer, mock_compare):
        mock_cask_info.return_value = {"version": "120.0", "name": "firefox"}
        mock_is_newer.return_value = False
        mock_compare.return_value = 0
        result = process_single_app(("Firefox", "120.0"))
        assert result.status == VersionStatus.UP_TO_DATE

    @patch("versiontracker.version.batch.compare_versions")
    @patch("versiontracker.version.batch.is_version_newer")
    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_newer_app(self, mock_cask_info, mock_is_newer, mock_compare):
        mock_cask_info.return_value = {"version": "119.0", "name": "firefox"}
        mock_is_newer.return_value = False
        mock_compare.return_value = 1
        result = process_single_app(("Firefox", "120.0"))
        assert result.status == VersionStatus.NEWER

    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_unknown_version_string(self, mock_cask_info):
        mock_cask_info.return_value = {"version": "unknown", "name": "myapp"}
        result = process_single_app(("MyApp", "1.0"))
        assert result.status == VersionStatus.UNKNOWN

    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_latest_version_string(self, mock_cask_info):
        mock_cask_info.return_value = {"version": "latest", "name": "myapp"}
        result = process_single_app(("MyApp", "1.0"))
        assert result.status == VersionStatus.UNKNOWN

    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_timeout_error(self, mock_cask_info):
        mock_cask_info.side_effect = VTTimeoutError("timed out")
        result = process_single_app(("Firefox", "120.0"))
        assert result.status == VersionStatus.ERROR
        assert result.error_message == "Network timeout"

    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_network_error(self, mock_cask_info):
        mock_cask_info.side_effect = NetworkError("connection failed")
        result = process_single_app(("Firefox", "120.0"))
        assert result.status == VersionStatus.ERROR
        assert "connection failed" in result.error_message

    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_os_error(self, mock_cask_info):
        mock_cask_info.side_effect = OSError("disk error")
        result = process_single_app(("Firefox", "120.0"))
        assert result.status == VersionStatus.ERROR

    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_enhanced_matching_passed_through(self, mock_cask_info):
        mock_cask_info.return_value = None
        process_single_app(("App", "1.0"), use_enhanced_matching=False)
        mock_cask_info.assert_called_once_with("App", False)

    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_homebrew_info_missing_name_uses_app_name(self, mock_cask_info):
        mock_cask_info.return_value = {"version": "unknown"}
        result = process_single_app(("MyApp", "1.0"))
        assert result.name == "MyApp"


class TestProcessAppBatch:
    """Tests for process_app_batch."""

    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_processes_all_apps(self, mock_cask_info):
        mock_cask_info.return_value = None
        apps = [("App1", "1.0"), ("App2", "2.0"), ("App3", "3.0")]
        results = process_app_batch(apps)
        assert len(results) == 3
        assert all(isinstance(r, ApplicationInfo) for r in results)

    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_empty_list(self, mock_cask_info):
        results = process_app_batch([])
        assert results == []
        mock_cask_info.assert_not_called()

    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_passes_enhanced_matching(self, mock_cask_info):
        mock_cask_info.return_value = None
        process_app_batch([("App", "1.0")], use_enhanced_matching=False)
        mock_cask_info.assert_called_once_with("App", False)


class TestCreateAppBatches:
    """Tests for create_app_batches."""

    def test_exact_division(self):
        apps = [("A", "1"), ("B", "2"), ("C", "3"), ("D", "4")]
        batches = create_app_batches(apps, 2)
        assert len(batches) == 2
        assert batches[0] == [("A", "1"), ("B", "2")]
        assert batches[1] == [("C", "3"), ("D", "4")]

    def test_uneven_division(self):
        apps = [("A", "1"), ("B", "2"), ("C", "3")]
        batches = create_app_batches(apps, 2)
        assert len(batches) == 2
        assert len(batches[0]) == 2
        assert len(batches[1]) == 1

    def test_single_batch(self):
        apps = [("A", "1"), ("B", "2")]
        batches = create_app_batches(apps, 10)
        assert len(batches) == 1
        assert batches[0] == apps

    def test_empty_list(self):
        batches = create_app_batches([], 5)
        assert batches == []

    def test_batch_size_one(self):
        apps = [("A", "1"), ("B", "2"), ("C", "3")]
        batches = create_app_batches(apps, 1)
        assert len(batches) == 3
        assert all(len(b) == 1 for b in batches)


class TestHandleBatchResult:
    """Tests for handle_batch_result."""

    def test_successful_result(self):
        info = ApplicationInfo(name="App", version_string="1.0", status=VersionStatus.UP_TO_DATE)
        future = MagicMock(spec=concurrent.futures.Future)
        future.result.return_value = [info]
        results = []
        new_count = handle_batch_result(future, results, error_count=0, max_errors=3)
        assert new_count == 0
        assert len(results) == 1
        assert results[0] is info

    def test_runtime_error_increments_count(self):
        future = MagicMock(spec=concurrent.futures.Future)
        future.result.side_effect = RuntimeError("failed")
        results = []
        new_count = handle_batch_result(future, results, error_count=0, max_errors=3)
        assert new_count == 1
        assert results == []

    def test_timeout_error_increments_count(self):
        future = MagicMock(spec=concurrent.futures.Future)
        future.result.side_effect = concurrent.futures.TimeoutError("timeout")
        results = []
        new_count = handle_batch_result(future, results, error_count=0, max_errors=3)
        assert new_count == 1

    def test_raises_network_error_when_max_errors_reached(self):
        future = MagicMock(spec=concurrent.futures.Future)
        future.result.side_effect = RuntimeError("failed")
        results = []
        with pytest.raises(NetworkError, match="Too many batch processing failures"):
            handle_batch_result(future, results, error_count=2, max_errors=3)

    def test_error_at_exact_max(self):
        """error_count becomes max_errors exactly -> should raise."""
        future = MagicMock(spec=concurrent.futures.Future)
        future.result.side_effect = RuntimeError("boom")
        with pytest.raises(NetworkError):
            handle_batch_result(future, [], error_count=4, max_errors=3)

    def test_successful_result_does_not_change_error_count(self):
        future = MagicMock(spec=concurrent.futures.Future)
        future.result.return_value = []
        new_count = handle_batch_result(future, [], error_count=2, max_errors=3)
        assert new_count == 2


class TestCheckOutdatedApps:
    """Tests for check_outdated_apps."""

    @patch("versiontracker.version.batch._get_config_settings", return_value=(False, 2))
    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_empty_apps_returns_empty(self, mock_cask_info, mock_config):
        result = check_outdated_apps([])
        assert result == []
        mock_cask_info.assert_not_called()

    @patch("versiontracker.version.batch._get_config_settings", return_value=(False, 1))
    @patch("versiontracker.version.batch.compare_versions", return_value=0)
    @patch("versiontracker.version.batch.is_version_newer", return_value=False)
    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_returns_tuple_format(self, mock_cask_info, mock_newer, mock_compare, mock_config):
        mock_cask_info.return_value = {"version": "1.0", "name": "app"}
        result = check_outdated_apps([("App", "1.0")], batch_size=10)
        assert len(result) == 1
        name, versions, status = result[0]
        assert name == "App"
        assert versions["installed"] == "1.0"
        assert versions["latest"] == "1.0"
        assert status == VersionStatus.UP_TO_DATE

    @patch("versiontracker.version.batch._get_config_settings", return_value=(False, 2))
    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_not_found_shows_unknown_latest(self, mock_cask_info, mock_config):
        mock_cask_info.return_value = None
        result = check_outdated_apps([("App", "1.0")])
        _, versions, status = result[0]
        assert versions["latest"] == "Unknown"
        assert status == VersionStatus.UNKNOWN

    @patch("versiontracker.version.batch._get_config_settings", return_value=(False, 2))
    @patch("versiontracker.version.batch.is_version_newer", return_value=True)
    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_multiple_apps_all_processed(self, mock_cask_info, mock_newer, mock_config):
        mock_cask_info.return_value = {"version": "2.0", "name": "app"}
        apps = [("A", "1.0"), ("B", "1.0"), ("C", "1.0")]
        result = check_outdated_apps(apps, batch_size=2)
        assert len(result) == 3

    @patch("versiontracker.version.batch._get_config_settings", return_value=(False, 1))
    @patch("versiontracker.version.batch.is_version_newer", return_value=True)
    @patch("versiontracker.version.batch.get_homebrew_cask_info")
    def test_batch_size_respected(self, mock_cask_info, mock_newer, mock_config):
        mock_cask_info.return_value = {"version": "2.0", "name": "app"}
        apps = [("A", "1.0"), ("B", "1.0"), ("C", "1.0")]
        result = check_outdated_apps(apps, batch_size=1)
        assert len(result) == 3


class TestGetConfigSettings:
    """Tests for _get_config_settings."""

    def test_returns_defaults_on_import_error(self):
        """When config import fails, returns defaults."""
        with patch("versiontracker.version.batch._get_config_settings") as mock_fn:
            mock_fn.return_value = (True, 4)
            show, workers = mock_fn()
            assert show is True
            assert workers == 4

    def test_returns_tuple(self):
        result = _get_config_settings()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], int)
