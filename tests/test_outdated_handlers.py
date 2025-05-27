"""Comprehensive tests for outdated_handlers module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import time
from typing import Any, Dict, List, Tuple, Union

from versiontracker.handlers.outdated_handlers import (
    _update_config_from_options,
    _get_installed_applications,
    _get_homebrew_casks,
    _filter_applications,
    _check_outdated_apps,
    _process_outdated_info,
    _display_results,
    _export_data,
    handle_outdated_check,
)
from versiontracker.exceptions import ConfigError, ExportError, NetworkError


class TestUpdateConfigFromOptions:
    """Test _update_config_from_options function."""

    @patch('versiontracker.handlers.outdated_handlers.get_config')
    def test_update_config_with_no_progress_true(self, mock_get_config):
        """Test updating config when no_progress is True."""
        mock_config = Mock()
        mock_config.set = Mock()
        mock_get_config.return_value = mock_config
        
        options = Mock()
        options.no_progress = True
        
        _update_config_from_options(options)
        
        mock_config.set.assert_any_call("no_progress", True)
        mock_config.set.assert_any_call("show_progress", False)

    @patch('versiontracker.handlers.outdated_handlers.get_config')
    def test_update_config_with_no_progress_false(self, mock_get_config):
        """Test updating config when no_progress is False."""
        mock_config = Mock()
        mock_config.set = Mock()
        mock_get_config.return_value = mock_config
        
        options = Mock()
        options.no_progress = False
        
        _update_config_from_options(options)
        
        mock_config.set.assert_not_called()

    @patch('versiontracker.handlers.outdated_handlers.get_config')
    def test_update_config_without_no_progress_attribute(self, mock_get_config):
        """Test updating config when options doesn't have no_progress."""
        mock_config = Mock()
        mock_config.set = Mock()
        mock_get_config.return_value = mock_config
        
        options = Mock(spec=[])  # No attributes
        
        _update_config_from_options(options)
        
        mock_config.set.assert_not_called()

    @patch('versiontracker.handlers.outdated_handlers.get_config')
    def test_update_config_without_set_method(self, mock_get_config):
        """Test updating config when config doesn't have set method."""
        mock_config = Mock(spec=[])  # No set method
        mock_get_config.return_value = mock_config
        
        options = Mock()
        options.no_progress = True
        
        # Should not raise an exception
        _update_config_from_options(options)


class TestGetInstalledApplications:
    """Test _get_installed_applications function."""

    @patch('versiontracker.handlers.outdated_handlers.get_applications')
    @patch('versiontracker.handlers.outdated_handlers.get_json_data')
    @patch('versiontracker.handlers.outdated_handlers.get_config')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_get_installed_applications_success(self, mock_progress, mock_config, mock_json, mock_get_apps):
        """Test successful retrieval of installed applications."""
        mock_config.return_value.system_profiler_cmd = "system_profiler -json SPApplicationsDataType"
        mock_json.return_value = {"apps": "data"}
        mock_get_apps.return_value = [("App1", "1.0"), ("App2", "2.0")]
        mock_progress.return_value.color.return_value = lambda x: x
        
        result = _get_installed_applications()
        
        assert result == [("App1", "1.0"), ("App2", "2.0")]
        mock_json.assert_called_once_with("system_profiler -json SPApplicationsDataType")
        mock_get_apps.assert_called_once_with({"apps": "data"})

    @patch('versiontracker.handlers.outdated_handlers.get_applications')
    @patch('versiontracker.handlers.outdated_handlers.get_json_data')
    @patch('versiontracker.handlers.outdated_handlers.get_config')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_get_installed_applications_permission_error(self, mock_progress, mock_config, mock_json, mock_get_apps):
        """Test handling of permission error."""
        mock_config.return_value.system_profiler_cmd = "system_profiler -json SPApplicationsDataType"
        mock_json.side_effect = PermissionError("Permission denied")
        mock_progress.return_value.color.return_value = lambda x: x
        
        with pytest.raises(PermissionError):
            _get_installed_applications()

    @patch('versiontracker.handlers.outdated_handlers.get_applications')
    @patch('versiontracker.handlers.outdated_handlers.get_json_data')
    @patch('versiontracker.handlers.outdated_handlers.get_config')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_get_installed_applications_timeout_error(self, mock_progress, mock_config, mock_json, mock_get_apps):
        """Test handling of timeout error."""
        mock_config.return_value.system_profiler_cmd = "system_profiler -json SPApplicationsDataType"
        mock_json.side_effect = TimeoutError("Operation timed out")
        mock_progress.return_value.color.return_value = lambda x: x
        
        with pytest.raises(TimeoutError):
            _get_installed_applications()

    @patch('versiontracker.handlers.outdated_handlers.get_applications')
    @patch('versiontracker.handlers.outdated_handlers.get_json_data')
    @patch('versiontracker.handlers.outdated_handlers.get_config')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_get_installed_applications_config_without_cmd(self, mock_progress, mock_config, mock_json, mock_get_apps):
        """Test when config doesn't have system_profiler_cmd."""
        mock_config_obj = Mock()
        del mock_config_obj.system_profiler_cmd  # Remove attribute
        mock_config.return_value = mock_config_obj
        mock_json.return_value = {"apps": "data"}
        mock_get_apps.return_value = [("App1", "1.0")]
        mock_progress.return_value.color.return_value = lambda x: x
        
        result = _get_installed_applications()
        
        assert result == [("App1", "1.0")]
        mock_json.assert_called_once_with("system_profiler -json SPApplicationsDataType")


class TestGetHomebrewCasks:
    """Test _get_homebrew_casks function."""

    @patch('versiontracker.handlers.outdated_handlers.get_homebrew_casks')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_get_homebrew_casks_success(self, mock_progress, mock_get_casks):
        """Test successful retrieval of Homebrew casks."""
        mock_get_casks.return_value = ["firefox", "chrome", "vscode"]
        mock_progress.return_value.color.return_value = lambda x: x
        
        result = _get_homebrew_casks()
        
        assert result == ["firefox", "chrome", "vscode"]
        mock_get_casks.assert_called_once()

    @patch('versiontracker.handlers.outdated_handlers.get_homebrew_casks')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_get_homebrew_casks_file_not_found(self, mock_progress, mock_get_casks):
        """Test handling when Homebrew is not found."""
        mock_get_casks.side_effect = FileNotFoundError("Homebrew not found")
        mock_progress.return_value.color.return_value = lambda x: x
        
        with pytest.raises(FileNotFoundError):
            _get_homebrew_casks()

    @patch('versiontracker.handlers.outdated_handlers.get_homebrew_casks')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_get_homebrew_casks_permission_error(self, mock_progress, mock_get_casks):
        """Test handling of permission error."""
        mock_get_casks.side_effect = PermissionError("Permission denied")
        mock_progress.return_value.color.return_value = lambda x: x
        
        with pytest.raises(PermissionError):
            _get_homebrew_casks()


class TestFilterApplications:
    """Test _filter_applications function."""

    @patch('versiontracker.handlers.outdated_handlers.filter_out_brews')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_filter_applications_exclude_brews(self, mock_progress, mock_filter):
        """Test filtering out brew-managed applications."""
        apps = [("App1", "1.0"), ("App2", "2.0"), ("App3", "3.0")]
        brews = ["app1", "app2"]
        mock_filter.return_value = [("App3", "3.0")]
        mock_progress.return_value.color.return_value = lambda x: x
        
        result = _filter_applications(apps, brews, include_brews=False)
        
        assert result == [("App3", "3.0")]
        mock_filter.assert_called_once_with(apps, brews)

    def test_filter_applications_include_brews(self):
        """Test including brew-managed applications."""
        apps = [("App1", "1.0"), ("App2", "2.0"), ("App3", "3.0")]
        brews = ["app1", "app2"]
        
        result = _filter_applications(apps, brews, include_brews=True)
        
        assert result == apps

    @patch('versiontracker.handlers.outdated_handlers.filter_out_brews')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_filter_applications_filter_error(self, mock_progress, mock_filter):
        """Test handling error during filtering."""
        apps = [("App1", "1.0"), ("App2", "2.0")]
        brews = ["app1"]
        mock_filter.side_effect = Exception("Filter error")
        mock_progress.return_value.color.return_value = lambda x: x
        
        result = _filter_applications(apps, brews, include_brews=False)
        
        # Should return original apps on error
        assert result == apps


class TestCheckOutdatedApps:
    """Test _check_outdated_apps function."""

    @patch('versiontracker.handlers.outdated_handlers.check_outdated_apps')
    @patch('versiontracker.handlers.outdated_handlers.get_config')
    def test_check_outdated_apps_success(self, mock_config, mock_check):
        """Test successful outdated check."""
        mock_config.return_value.batch_size = 50
        apps = [("App1", "1.0"), ("App2", "2.0")]
        expected = [("App1", {"installed": "1.0", "latest": "2.0"}, "outdated")]
        mock_check.return_value = expected
        
        result = _check_outdated_apps(apps)
        
        assert result == expected
        mock_check.assert_called_once_with(apps, batch_size=50)

    @patch('versiontracker.handlers.outdated_handlers.check_outdated_apps')
    @patch('versiontracker.handlers.outdated_handlers.get_config')
    def test_check_outdated_apps_default_batch_size(self, mock_config, mock_check):
        """Test with default batch size when not configured."""
        mock_config_obj = Mock()
        del mock_config_obj.batch_size  # Remove attribute
        mock_config.return_value = mock_config_obj
        apps = [("App1", "1.0")]
        expected = [("App1", {"installed": "1.0", "latest": "1.0"}, "uptodate")]
        mock_check.return_value = expected
        
        result = _check_outdated_apps(apps)
        
        assert result == expected
        mock_check.assert_called_once_with(apps, batch_size=50)

    @patch('versiontracker.handlers.outdated_handlers.check_outdated_apps')
    @patch('versiontracker.handlers.outdated_handlers.get_config')
    def test_check_outdated_apps_timeout_error(self, mock_config, mock_check):
        """Test handling of timeout error."""
        mock_config.return_value.batch_size = 50
        apps = [("App1", "1.0")]
        mock_check.side_effect = TimeoutError("Operation timed out")
        
        with pytest.raises(TimeoutError):
            _check_outdated_apps(apps)

    @patch('versiontracker.handlers.outdated_handlers.check_outdated_apps')
    @patch('versiontracker.handlers.outdated_handlers.get_config')
    def test_check_outdated_apps_network_error(self, mock_config, mock_check):
        """Test handling of network error."""
        mock_config.return_value.batch_size = 50
        apps = [("App1", "1.0")]
        mock_check.side_effect = NetworkError("Network error")
        
        with pytest.raises(NetworkError):
            _check_outdated_apps(apps)


class TestProcessOutdatedInfo:
    """Test _process_outdated_info function."""

    @patch('versiontracker.handlers.outdated_handlers.get_status_icon')
    @patch('versiontracker.handlers.outdated_handlers.get_status_color')
    def test_process_outdated_info_mixed_statuses(self, mock_color, mock_icon):
        """Test processing outdated info with mixed statuses."""
        mock_icon.side_effect = lambda x: f"icon_{x}"
        mock_color.side_effect = lambda x: lambda y: f"color_{x}({y})"
        
        outdated_info = [
            ("App1", {"installed": "1.0", "latest": "2.0"}, "outdated"),
            ("App2", {"installed": "2.0", "latest": "2.0"}, "uptodate"),
            ("App3", {"installed": "1.0"}, "not_found"),
            ("App4", {"installed": "1.0"}, "error"),
            ("App5", {"installed": "1.0"}, "unknown_status"),
        ]
        
        table, status_counts = _process_outdated_info(outdated_info)
        
        assert len(table) == 5
        assert status_counts == {
            "outdated": 1,
            "uptodate": 1,
            "not_found": 1,
            "error": 1,
            "unknown": 1,
        }
        
        # Check table structure and sorting
        assert table[0] == ["icon_outdated", "App1", "color_outdated(1.0)", "color_outdated(2.0)"]
        assert table[1] == ["icon_uptodate", "App2", "color_uptodate(2.0)", "color_uptodate(2.0)"]
        assert table[2] == ["icon_not_found", "App3", "color_not_found(1.0)", "color_not_found(Unknown)"]
        assert table[3] == ["icon_error", "App4", "color_error(1.0)", "color_error(Unknown)"]
        assert table[4] == ["icon_unknown_status", "App5", "color_unknown_status(1.0)", "color_unknown_status(Unknown)"]

    @patch('versiontracker.handlers.outdated_handlers.get_status_icon')
    @patch('versiontracker.handlers.outdated_handlers.get_status_color')
    def test_process_outdated_info_empty_list(self, mock_color, mock_icon):
        """Test processing empty outdated info."""
        table, status_counts = _process_outdated_info([])
        
        assert table == []
        assert status_counts == {
            "outdated": 0,
            "uptodate": 0,
            "not_found": 0,
            "error": 0,
            "unknown": 0,
        }

    @patch('versiontracker.handlers.outdated_handlers.get_status_icon')
    @patch('versiontracker.handlers.outdated_handlers.get_status_color')
    def test_process_outdated_info_missing_version_info(self, mock_color, mock_icon):
        """Test processing with missing version information."""
        mock_icon.return_value = "icon"
        mock_color.return_value = lambda x: f"colored({x})"
        
        outdated_info = [
            ("App1", {}, "outdated"),  # No version info
        ]
        
        table, status_counts = _process_outdated_info(outdated_info)
        
        assert len(table) == 1
        assert table[0] == ["icon", "App1", "colored(Unknown)", "colored(Unknown)"]

    @patch('versiontracker.handlers.outdated_handlers.get_status_icon')
    @patch('versiontracker.handlers.outdated_handlers.get_status_color')
    def test_process_outdated_info_sorting(self, mock_color, mock_icon):
        """Test table sorting by application name."""
        mock_icon.return_value = "icon"
        mock_color.return_value = lambda x: x
        
        outdated_info = [
            ("ZApp", {"installed": "1.0", "latest": "1.0"}, "uptodate"),
            ("AApp", {"installed": "1.0", "latest": "1.0"}, "uptodate"),
            ("MApp", {"installed": "1.0", "latest": "1.0"}, "uptodate"),
        ]
        
        table, _ = _process_outdated_info(outdated_info)
        
        # Should be sorted alphabetically by app name (case-insensitive)
        assert table[0][1] == "AApp"
        assert table[1][1] == "MApp"
        assert table[2][1] == "ZApp"


class TestDisplayResults:
    """Test _display_results function."""

    @patch('versiontracker.handlers.outdated_handlers.tabulate')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_display_results_with_data(self, mock_progress, mock_tabulate):
        """Test displaying results with data."""
        mock_progress.return_value.color.return_value = lambda x: x
        mock_tabulate.return_value = "formatted_table"
        
        table = [["icon", "App1", "1.0", "2.0"]]
        status_counts = {
            "outdated": 1,
            "uptodate": 0,
            "not_found": 0,
            "error": 0,
            "unknown": 0,
        }
        
        _display_results(table, status_counts, 1, 5.5)
        
        mock_tabulate.assert_called_once_with(
            table,
            headers=["", "Application", "Installed Version", "Latest Version"],
            tablefmt="pretty"
        )

    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_display_results_empty_table(self, mock_progress):
        """Test displaying results with empty table."""
        mock_progress.return_value.color.return_value = lambda x: x
        
        _display_results([], {}, 0, 0.0)
        
        # Should print "No applications found" message

    @patch('versiontracker.handlers.outdated_handlers.tabulate')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_display_results_all_up_to_date(self, mock_progress, mock_tabulate):
        """Test displaying results when all apps are up to date."""
        mock_progress.return_value.color.return_value = lambda x: x
        mock_tabulate.return_value = "formatted_table"
        
        table = [["icon", "App1", "1.0", "1.0"]]
        status_counts = {
            "outdated": 0,
            "uptodate": 1,
            "not_found": 0,
            "error": 0,
            "unknown": 0,
        }
        
        _display_results(table, status_counts, 1, 2.0)
        
        # Should print "All applications are up to date!" message

    @patch('versiontracker.handlers.outdated_handlers.tabulate')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_display_results_with_outdated(self, mock_progress, mock_tabulate):
        """Test displaying results with outdated applications."""
        mock_progress.return_value.color.return_value = lambda x: x
        mock_tabulate.return_value = "formatted_table"
        
        table = [["icon", "App1", "1.0", "2.0"]]
        status_counts = {
            "outdated": 1,
            "uptodate": 0,
            "not_found": 0,
            "error": 0,
            "unknown": 0,
        }
        
        _display_results(table, status_counts, 1, 3.0)
        
        # Should print "Found X outdated applications" message


class TestExportData:
    """Test _export_data function."""

    @patch('versiontracker.handlers.outdated_handlers.handle_export')
    def test_export_data_success_with_output_file(self, mock_handle_export):
        """Test successful export with output file."""
        mock_handle_export.return_value = "Export successful"
        outdated_info = [("App1", {"installed": "1.0", "latest": "2.0"}, "outdated")]
        options = Mock()
        options.export_format = "json"
        options.output_file = "output.json"
        
        result = _export_data(outdated_info, options)
        
        assert result == 0
        mock_handle_export.assert_called_once_with(outdated_info, "json", "output.json")

    @patch('versiontracker.handlers.outdated_handlers.handle_export')
    def test_export_data_success_without_output_file(self, mock_handle_export):
        """Test successful export without output file."""
        mock_handle_export.return_value = "Export data string"
        outdated_info = [("App1", {"installed": "1.0", "latest": "2.0"}, "outdated")]
        options = Mock()
        options.export_format = "csv"
        options.output_file = None
        
        result = _export_data(outdated_info, options)
        
        assert result == 0
        mock_handle_export.assert_called_once_with(outdated_info, "csv", None)

    @patch('versiontracker.handlers.outdated_handlers.handle_export')
    def test_export_data_without_output_file_attribute(self, mock_handle_export):
        """Test export when options doesn't have output_file attribute."""
        mock_handle_export.return_value = "Export data string"
        outdated_info = [("App1", {"installed": "1.0", "latest": "2.0"}, "outdated")]
        options = Mock(spec=["export_format"])  # No output_file attribute
        options.export_format = "yaml"
        
        result = _export_data(outdated_info, options)
        
        assert result == 0
        mock_handle_export.assert_called_once_with(outdated_info, "yaml", None)

    @patch('versiontracker.handlers.outdated_handlers.handle_export')
    def test_export_data_export_error(self, mock_handle_export):
        """Test handling of export error."""
        mock_handle_export.side_effect = ExportError("Export failed")
        outdated_info = [("App1", {"installed": "1.0", "latest": "2.0"}, "outdated")]
        options = Mock()
        options.export_format = "json"
        options.output_file = "output.json"
        
        with pytest.raises(ExportError):
            _export_data(outdated_info, options)


class TestHandleOutdatedCheck:
    """Test handle_outdated_check function."""

    @patch('versiontracker.handlers.outdated_handlers._export_data')
    @patch('versiontracker.handlers.outdated_handlers._display_results')
    @patch('versiontracker.handlers.outdated_handlers._process_outdated_info')
    @patch('versiontracker.handlers.outdated_handlers._check_outdated_apps')
    @patch('versiontracker.handlers.outdated_handlers._filter_applications')
    @patch('versiontracker.handlers.outdated_handlers._get_homebrew_casks')
    @patch('versiontracker.handlers.outdated_handlers._get_installed_applications')
    @patch('versiontracker.handlers.outdated_handlers._update_config_from_options')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    @patch('time.time')
    def test_handle_outdated_check_success_without_export(
        self,
        mock_time,
        mock_progress,
        mock_update_config,
        mock_get_apps,
        mock_get_casks,
        mock_filter,
        mock_check,
        mock_process,
        mock_display,
        mock_export,
    ):
        """Test successful outdated check without export."""
        # Setup mocks
        mock_time.side_effect = [1000.0, 1005.0]  # start and end times
        mock_progress.return_value.color.return_value = lambda x: x
        mock_get_apps.return_value = [("App1", "1.0"), ("App2", "2.0")]
        mock_get_casks.return_value = ["cask1", "cask2"]
        mock_filter.return_value = [("App1", "1.0"), ("App2", "2.0")]
        mock_check.return_value = [("App1", {"installed": "1.0", "latest": "2.0"}, "outdated")]
        mock_process.return_value = (
            [["icon", "App1", "1.0", "2.0"]],
            {"outdated": 1, "uptodate": 0, "not_found": 0, "error": 0, "unknown": 0}
        )
        
        options = Mock(spec=["include_brews"])
        options.include_brews = False
        
        result = handle_outdated_check(options)
        
        assert result == 0
        mock_update_config.assert_called_once_with(options)
        mock_get_apps.assert_called_once()
        mock_get_casks.assert_called_once()
        mock_filter.assert_called_once_with([("App1", "1.0"), ("App2", "2.0")], ["cask1", "cask2"], False)
        mock_check.assert_called_once_with([("App1", "1.0"), ("App2", "2.0")])
        mock_process.assert_called_once()
        mock_display.assert_called_once()
        mock_export.assert_not_called()

    @patch('versiontracker.handlers.outdated_handlers._export_data')
    @patch('versiontracker.handlers.outdated_handlers._display_results')
    @patch('versiontracker.handlers.outdated_handlers._process_outdated_info')
    @patch('versiontracker.handlers.outdated_handlers._check_outdated_apps')
    @patch('versiontracker.handlers.outdated_handlers._filter_applications')
    @patch('versiontracker.handlers.outdated_handlers._get_homebrew_casks')
    @patch('versiontracker.handlers.outdated_handlers._get_installed_applications')
    @patch('versiontracker.handlers.outdated_handlers._update_config_from_options')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    @patch('time.time')
    def test_handle_outdated_check_success_with_export(
        self,
        mock_time,
        mock_progress,
        mock_update_config,
        mock_get_apps,
        mock_get_casks,
        mock_filter,
        mock_check,
        mock_process,
        mock_display,
        mock_export,
    ):
        """Test successful outdated check with export."""
        # Setup mocks
        mock_time.side_effect = [1000.0, 1005.0]
        mock_progress.return_value.color.return_value = lambda x: x
        mock_get_apps.return_value = [("App1", "1.0")]
        mock_get_casks.return_value = ["cask1"]
        mock_filter.return_value = [("App1", "1.0")]
        mock_check.return_value = [("App1", {"installed": "1.0", "latest": "1.0"}, "uptodate")]
        mock_process.return_value = ([], {})
        mock_export.return_value = 0
        
        options = Mock()
        options.include_brews = True
        options.export_format = "json"
        options.output_file = "output.json"
        
        result = handle_outdated_check(options)
        
        assert result == 0
        mock_export.assert_called_once()

    @patch('versiontracker.handlers.outdated_handlers._get_installed_applications')
    @patch('versiontracker.handlers.outdated_handlers._update_config_from_options')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_handle_outdated_check_permission_error_apps(
        self,
        mock_progress,
        mock_update_config,
        mock_get_apps,
    ):
        """Test handling permission error when getting applications."""
        mock_progress.return_value.color.return_value = lambda x: x
        mock_get_apps.side_effect = PermissionError("Permission denied")
        
        options = Mock()
        
        result = handle_outdated_check(options)
        
        assert result == 1

    @patch('versiontracker.handlers.outdated_handlers._get_homebrew_casks')
    @patch('versiontracker.handlers.outdated_handlers._get_installed_applications')
    @patch('versiontracker.handlers.outdated_handlers._update_config_from_options')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_handle_outdated_check_file_not_found_homebrew(
        self,
        mock_progress,
        mock_update_config,
        mock_get_apps,
        mock_get_casks,
    ):
        """Test handling when Homebrew is not found."""
        mock_progress.return_value.color.return_value = lambda x: x
        mock_get_apps.return_value = [("App1", "1.0")]
        mock_get_casks.side_effect = FileNotFoundError("Homebrew not found")
        
        options = Mock()
        
        result = handle_outdated_check(options)
        
        assert result == 1

    @patch('versiontracker.handlers.outdated_handlers._check_outdated_apps')
    @patch('versiontracker.handlers.outdated_handlers._filter_applications')
    @patch('versiontracker.handlers.outdated_handlers._get_homebrew_casks')
    @patch('versiontracker.handlers.outdated_handlers._get_installed_applications')
    @patch('versiontracker.handlers.outdated_handlers._update_config_from_options')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    @patch('time.time')
    def test_handle_outdated_check_timeout_error_check(
        self,
        mock_time,
        mock_progress,
        mock_update_config,
        mock_get_apps,
        mock_get_casks,
        mock_filter,
        mock_check,
    ):
        """Test handling timeout error during outdated check."""
        mock_time.return_value = 1000.0
        mock_progress.return_value.color.return_value = lambda x: x
        mock_get_apps.return_value = [("App1", "1.0")]
        mock_get_casks.return_value = ["cask1"]
        mock_filter.return_value = [("App1", "1.0")]
        mock_check.side_effect = TimeoutError("Network timeout")
        
        options = Mock()
        options.include_brews = False
        
        result = handle_outdated_check(options)
        
        assert result == 1

    @patch('versiontracker.handlers.outdated_handlers._export_data')
    @patch('versiontracker.handlers.outdated_handlers._display_results')
    @patch('versiontracker.handlers.outdated_handlers._process_outdated_info')
    @patch('versiontracker.handlers.outdated_handlers._check_outdated_apps')
    @patch('versiontracker.handlers.outdated_handlers._filter_applications')
    @patch('versiontracker.handlers.outdated_handlers._get_homebrew_casks')
    @patch('versiontracker.handlers.outdated_handlers._get_installed_applications')
    @patch('versiontracker.handlers.outdated_handlers._update_config_from_options')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    @patch('time.time')
    def test_handle_outdated_check_export_error(
        self,
        mock_time,
        mock_progress,
        mock_update_config,
        mock_get_apps,
        mock_get_casks,
        mock_filter,
        mock_check,
        mock_process,
        mock_display,
        mock_export,
    ):
        """Test handling export error."""
        mock_time.side_effect = [1000.0, 1005.0]
        mock_progress.return_value.color.return_value = lambda x: x
        mock_get_apps.return_value = [("App1", "1.0")]
        mock_get_casks.return_value = ["cask1"]
        mock_filter.return_value = [("App1", "1.0")]
        mock_check.return_value = [("App1", {"installed": "1.0", "latest": "1.0"}, "uptodate")]
        mock_process.return_value = ([], {})
        mock_export.side_effect = ExportError("Export failed")
        
        options = Mock()
        options.include_brews = False
        options.export_format = "json"
        
        result = handle_outdated_check(options)
        
        assert result == 1

    @patch('versiontracker.handlers.outdated_handlers._update_config_from_options')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_handle_outdated_check_config_error(
        self,
        mock_progress,
        mock_update_config,
    ):
        """Test handling configuration error."""
        mock_progress.return_value.color.return_value = lambda x: x
        mock_update_config.side_effect = ConfigError("Config error")
        
        options = Mock()
        
        result = handle_outdated_check(options)
        
        assert result == 1

    @patch('versiontracker.handlers.outdated_handlers._update_config_from_options')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_handle_outdated_check_keyboard_interrupt(
        self,
        mock_progress,
        mock_update_config,
    ):
        """Test handling keyboard interrupt."""
        mock_progress.return_value.color.return_value = lambda x: x
        mock_update_config.side_effect = KeyboardInterrupt()
        
        options = Mock()
        
        result = handle_outdated_check(options)
        
        assert result == 130

    @patch('versiontracker.handlers.outdated_handlers._update_config_from_options')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    @patch('versiontracker.handlers.outdated_handlers.get_config')
    @patch('logging.error')
    def test_handle_outdated_check_unexpected_error_debug_mode(
        self,
        mock_logging,
        mock_get_config,
        mock_progress,
        mock_update_config,
    ):
        """Test handling unexpected error in debug mode."""
        mock_progress.return_value.color.return_value = lambda x: x
        mock_update_config.side_effect = Exception("Unexpected error")
        mock_config = Mock()
        mock_config.debug = True
        mock_get_config.return_value = mock_config
        
        options = Mock()
        
        with patch('traceback.print_exc') as mock_traceback:
            result = handle_outdated_check(options)
        
        assert result == 1
        mock_logging.assert_called_once()
        mock_traceback.assert_called_once()

    @patch('versiontracker.handlers.outdated_handlers._update_config_from_options')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    @patch('versiontracker.handlers.outdated_handlers.get_config')
    @patch('logging.error')
    def test_handle_outdated_check_unexpected_error_no_debug(
        self,
        mock_logging,
        mock_get_config,
        mock_progress,
        mock_update_config,
    ):
        """Test handling unexpected error without debug mode."""
        mock_progress.return_value.color.return_value = lambda x: x
        mock_update_config.side_effect = Exception("Unexpected error")
        mock_config = Mock()
        mock_config.debug = False
        mock_get_config.return_value = mock_config
        
        options = Mock()
        
        result = handle_outdated_check(options)
        
        assert result == 1
        mock_logging.assert_called_once()


class TestErrorHandling:
    """Test error handling scenarios."""

    @patch('versiontracker.handlers.outdated_handlers._get_installed_applications')
    @patch('versiontracker.handlers.outdated_handlers._update_config_from_options')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_handle_timeout_error_apps(self, mock_progress, mock_update_config, mock_get_apps):
        """Test handling timeout error when getting applications."""
        mock_progress.return_value.color.return_value = lambda x: x
        mock_get_apps.side_effect = TimeoutError("Operation timed out")
        
        options = Mock()
        
        result = handle_outdated_check(options)
        
        assert result == 1

    @patch('versiontracker.handlers.outdated_handlers._get_homebrew_casks')
    @patch('versiontracker.handlers.outdated_handlers._get_installed_applications')
    @patch('versiontracker.handlers.outdated_handlers._update_config_from_options')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    def test_handle_permission_error_homebrew(
        self, mock_progress, mock_update_config, mock_get_apps, mock_get_casks
    ):
        """Test handling permission error when accessing Homebrew."""
        mock_progress.return_value.color.return_value = lambda x: x
        mock_get_apps.return_value = [("App1", "1.0")]
        mock_get_casks.side_effect = PermissionError("Permission denied")
        
        options = Mock()
        
        result = handle_outdated_check(options)
        
        assert result == 1

    @patch('versiontracker.handlers.outdated_handlers._check_outdated_apps')
    @patch('versiontracker.handlers.outdated_handlers._filter_applications')
    @patch('versiontracker.handlers.outdated_handlers._get_homebrew_casks')
    @patch('versiontracker.handlers.outdated_handlers._get_installed_applications')
    @patch('versiontracker.handlers.outdated_handlers._update_config_from_options')
    @patch('versiontracker.handlers.outdated_handlers.create_progress_bar')
    @patch('time.time')
    def test_handle_network_error_check(
        self,
        mock_time,
        mock_progress,
        mock_update_config,
        mock_get_apps,
        mock_get_casks,
        mock_filter,
        mock_check,
    ):
        """Test handling network error during outdated check."""
        mock_time.return_value = 1000.0
        mock_progress.return_value.color.return_value = lambda x: x
        mock_get_apps.return_value = [("App1", "1.0")]
        mock_get_casks.return_value = ["cask1"]
        mock_filter.return_value = [("App1", "1.0")]
        mock_check.side_effect = NetworkError("Network error")
        
        options = Mock()
        options.include_brews = False
        
        result = handle_outdated_check(options)
        
        assert result == 1