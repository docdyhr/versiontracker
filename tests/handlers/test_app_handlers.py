"""Test module for app_handlers module."""

import unittest
from io import StringIO
from unittest.mock import Mock, patch

# Import the modules that will be patched
# Import the function being tested
from versiontracker.handlers.app_handlers import handle_list_apps


class TestAppHandlers(unittest.TestCase):
    """Tests for the application handlers."""

    @patch("versiontracker.handlers.app_handlers.get_json_data")
    @patch("versiontracker.handlers.app_handlers.get_applications")
    @patch("versiontracker.handlers.app_handlers.get_config")
    @patch("sys.stdout", new_callable=StringIO)
    def test_handle_list_apps_success(self, mock_stdout, mock_get_config, mock_get_applications, mock_get_json_data):
        """Test handle_list_apps with successful execution."""
        # Setup mocks
        mock_get_json_data.return_value = {"items": []}
        mock_get_applications.return_value = [("App1", "1.0.0"), ("App2", "2.0.0")]

        mock_config = Mock()
        mock_config.is_blacklisted.return_value = False
        mock_get_config.return_value = mock_config

        # Create test options
        options = Mock()
        options.debug = False
        options.blacklist = None
        options.brew_filter = False
        options.export_format = None
        options.additional_dirs = None

        # Call the function
        result = handle_list_apps(options)

        # Check results
        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("Found 2 applications", output)
        self.assertIn("App1", output)
        self.assertIn("App2", output)
        mock_get_applications.assert_called_once()

    @patch("versiontracker.handlers.app_handlers.get_json_data")
    @patch("versiontracker.handlers.app_handlers.get_applications")
    @patch("versiontracker.handlers.app_handlers.get_config")
    @patch("versiontracker.handlers.app_handlers.filter_out_brews")
    @patch("versiontracker.handlers.app_handlers.get_homebrew_casks")
    @patch("sys.stdout", new_callable=StringIO)
    def test_handle_list_apps_with_brew_filter(
        self,
        mock_stdout,
        mock_get_homebrew_casks,
        mock_filter_out_brews,
        mock_get_config,
        mock_get_applications,
        mock_get_json_data,
    ):
        """Test handle_list_apps with brew filtering enabled."""
        # Setup mocks
        mock_get_json_data.return_value = {"items": []}
        mock_get_applications.return_value = [
            ("App1", "1.0.0"),
            ("App2", "2.0.0"),
            ("BrewApp", "3.0.0"),
        ]

        mock_config = Mock()
        mock_config.is_blacklisted.return_value = False
        mock_get_config.return_value = mock_config

        mock_get_homebrew_casks.return_value = ["BrewApp"]

        # Mock the filter to remove BrewApp
        mock_filter_out_brews.return_value = [("App1", "1.0.0"), ("App2", "2.0.0")]

        # Create test options
        options = Mock()
        options.debug = False
        options.blacklist = None
        options.brew_filter = True
        options.include_brews = False
        options.export_format = None
        options.additional_dirs = None

        # Call the function
        result = handle_list_apps(options)

        # Check results
        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("Found 2 applications", output)
        mock_get_homebrew_casks.assert_called_once()
        mock_filter_out_brews.assert_called_once()

    @patch("versiontracker.handlers.app_handlers.get_json_data")
    @patch("versiontracker.handlers.app_handlers.get_applications")
    @patch("versiontracker.handlers.app_handlers.Config")
    @patch("versiontracker.handlers.app_handlers.get_config")
    @patch("sys.stdout", new_callable=StringIO)
    def test_handle_list_apps_with_blacklist(
        self,
        mock_stdout,
        mock_get_config,
        mock_Config,
        mock_get_applications,
        mock_get_json_data,
    ):
        """Test handle_list_apps with blacklist filtering."""
        # Setup mocks
        mock_get_json_data.return_value = {"items": []}
        mock_get_applications.return_value = [
            ("App1", "1.0.0"),
            ("App2", "2.0.0"),
            ("BlacklistedApp", "3.0.0"),
        ]

        mock_temp_config = Mock()
        mock_temp_config.is_blacklisted.side_effect = lambda app: app == "BlacklistedApp"
        mock_temp_config.is_blocklisted.side_effect = lambda app: app == "BlacklistedApp"
        mock_Config.return_value = mock_temp_config

        # Create test options
        options = Mock()
        options.debug = False
        options.blacklist = "BlacklistedApp"
        options.brew_filter = False
        options.export_format = None
        options.additional_dirs = None

        # Call the function
        result = handle_list_apps(options)

        # Check results
        self.assertEqual(result, 0)
        output = mock_stdout.getvalue()
        self.assertIn("Found 2 applications", output)
        self.assertNotIn("BlacklistedApp", output)

    @patch("versiontracker.handlers.app_handlers.get_json_data")
    @patch("versiontracker.handlers.app_handlers.get_applications")
    @patch("versiontracker.handlers.app_handlers.get_config")
    @patch("sys.stderr", new_callable=StringIO)
    @patch("sys.stdout", new_callable=StringIO)
    def test_handle_list_apps_additional_dirs_warns_and_is_ignored(
        self,
        mock_stdout,
        mock_stderr,
        mock_get_config,
        mock_get_applications,
        mock_get_json_data,
    ):
        """Regression: --additional-dirs previously computed a comma-split
        of the value and discarded the result -- a silent no-op, and the
        wrong separator vs. the flag's own "colon-separated" help text.
        Now it's removed entirely and replaced with a clear warning (to
        stderr, since it's diagnostic, not data) instead of a silent
        no-op; --apps discovery is otherwise unaffected."""
        mock_get_json_data.return_value = {"items": []}
        mock_get_applications.return_value = [("App1", "1.0.0")]

        mock_config = Mock()
        mock_config.is_blacklisted.return_value = False
        mock_get_config.return_value = mock_config

        options = Mock()
        options.debug = False
        options.blacklist = None
        options.brew_filter = False
        options.export_format = None
        options.additional_dirs = "/extra/one:/extra/two"

        result = handle_list_apps(options)

        self.assertEqual(result, 0)
        stderr_output = mock_stderr.getvalue()
        self.assertIn("--additional-dirs", stderr_output)
        self.assertIn("not supported", stderr_output)
        self.assertIn("--audit", stderr_output)
        # The warning is diagnostic, not data -- it must not appear on stdout.
        self.assertNotIn("--additional-dirs", mock_stdout.getvalue())
        self.assertIn("App1", mock_stdout.getvalue())

    @patch("versiontracker.handlers.app_handlers.get_json_data")
    @patch("versiontracker.handlers.app_handlers.handle_export")
    @patch("versiontracker.handlers.app_handlers.get_applications")
    @patch("versiontracker.handlers.app_handlers.get_config")
    @patch("sys.stdout", new_callable=StringIO)
    def test_handle_list_apps_with_export(
        self,
        mock_stdout,
        mock_get_config,
        mock_get_applications,
        mock_handle_export,
        mock_get_json_data,
    ):
        """Test handle_list_apps with export option."""
        # Setup mocks
        mock_get_json_data.return_value = {"items": []}
        mock_get_applications.return_value = [("App1", "1.0.0"), ("App2", "2.0.0")]

        mock_config = Mock()
        mock_config.is_blacklisted.return_value = False
        mock_get_config.return_value = mock_config

        mock_handle_export.return_value = 0

        # Create test options
        options = Mock()
        options.debug = False
        options.blacklist = None
        options.brew_filter = False
        options.export_format = "json"
        options.output_file = None
        options.additional_dirs = None

        # Call the function
        result = handle_list_apps(options)

        # Check results
        self.assertEqual(result, 0)
        mock_handle_export.assert_called_once()
        expected_data = [
            {"name": "App1", "version": "1.0.0"},
            {"name": "App2", "version": "2.0.0"},
        ]
        self.assertEqual(mock_handle_export.call_args[0][0], expected_data)
        self.assertEqual(mock_handle_export.call_args[0][1], "json")

        # Regression: exporting must not also print the human-readable
        # preamble/table -- stdout should carry only the export string.
        output = mock_stdout.getvalue()
        self.assertNotIn("Getting application data", output)
        self.assertNotIn("Found 2 applications", output)

    @patch(
        "versiontracker.handlers.app_handlers.get_json_data",
        side_effect=OSError("Test error"),
    )
    @patch("versiontracker.handlers.app_handlers.get_config")
    @patch("sys.stdout", new_callable=StringIO)
    def test_handle_list_apps_error(self, mock_stdout, mock_get_config, mock_get_json_data):
        """Test handle_list_apps with error condition."""
        # Setup mocks
        mock_config = Mock()
        mock_get_config.return_value = mock_config

        # Create test options
        options = Mock()
        options.debug = False

        # Call the function
        result = handle_list_apps(options)

        # Check results
        self.assertEqual(result, 1)  # Should return error code


if __name__ == "__main__":
    unittest.main()
