"""Integration tests for VersionTracker."""

import unittest
from unittest.mock import patch, MagicMock

# Import the main function but avoid executing imports
import sys
import importlib.util
spec = importlib.util.spec_from_file_location(
    "versiontracker.__main__", 
    "/Users/thomas/Programming/versiontracker/versiontracker/__main__.py"
)
versiontracker_main_module = importlib.util.module_from_spec(spec)
sys.modules["versiontracker.__main__"] = versiontracker_main_module
spec.loader.exec_module(versiontracker_main_module)
main = versiontracker_main_module.versiontracker_main

# Override the get_applications function for testing
versiontracker_main_module.get_applications = MagicMock()


class TestIntegration(unittest.TestCase):
    """Integration test cases for VersionTracker."""

    @patch("versiontracker.__main__.check_dependencies", return_value=True)
    @patch("versiontracker.__main__.get_applications")
    @patch("versiontracker.__main__.get_homebrew_casks")
    @patch("versiontracker.__main__.filter_out_brews")
    @patch("versiontracker.__main__.check_brew_install_candidates")
    @patch("versiontracker.__main__.get_json_data")
    @patch("versiontracker.__main__.setup_logging")
    @patch("versiontracker.__main__.config")
    def test_main_recommend_workflow(
        self,
        mock_config,
        mock_setup_logging,
        mock_json_data,
        mock_check_candidates,
        mock_filter_brews,
        mock_get_casks,
        mock_get_apps,
        mock_check_deps,
    ):
        """Test the main recommend workflow."""
        # Mock config methods
        mock_config.is_blacklisted.return_value = False
        mock_config.get.return_value = 10
        mock_config.rate_limit = 10  # Mock the rate_limit attribute

        # Mock the applications
        mock_get_apps.return_value = [
            ("Firefox", "100.0"),
            ("Chrome", "101.0"),
            ("Slack", "4.23.0"),
            ("VSCode", "1.67.0"),
        ]

        # Mock the brew casks
        mock_get_casks.return_value = ["firefox", "google-chrome"]

        # Mock the filtered apps
        mock_filter_brews.return_value = [("Slack", "4.23.0"), ("VSCode", "1.67.0")]

        # Mock brew candidates
        mock_check_candidates.return_value = ["slack", "visual-studio-code"]

        # Run the recommend handler directly with mocked options
        with patch("builtins.print"):  # Suppress output
            mock_json_data.return_value = {}  # Mock JSON data
            versiontracker_main_module.handle_brew_recommendations(MagicMock(
                recommend=True, 
                strict_recom=False,
                debug=False,
                strict_recommend=False,
                rate_limit=10
            ))

        # Verify the functions were called
        mock_get_apps.assert_called_once()
        mock_get_casks.assert_called_once()
        mock_filter_brews.assert_called_once()
        mock_check_candidates.assert_called_once_with(
            mock_filter_brews.return_value,
            10,  # Use an exact value instead of mock_config.get.return_value
            False,
        )

    @patch("versiontracker.__main__.check_dependencies", return_value=True)
    @patch("versiontracker.__main__.get_applications")
    @patch("versiontracker.__main__.get_homebrew_casks")
    @patch("versiontracker.__main__.filter_out_brews")
    @patch("versiontracker.__main__.check_brew_install_candidates")
    @patch("versiontracker.__main__.get_json_data")
    @patch("versiontracker.__main__.setup_logging")
    @patch("versiontracker.__main__.config")
    def test_main_strict_recommend_workflow(
        self,
        mock_config,
        mock_setup_logging,
        mock_json_data,
        mock_check_candidates,
        mock_filter_brews,
        mock_get_casks,
        mock_get_apps,
        mock_check_deps,
    ):
        """Test the main strict recommend workflow."""
        # Mock config methods
        mock_config.is_blacklisted.return_value = False
        mock_config.get.return_value = 10
        mock_config.rate_limit = 10  # Mock the rate_limit attribute

        # Mock the applications
        mock_get_apps.return_value = [
            ("Firefox", "100.0"),
            ("Chrome", "101.0"),
            ("Slack", "4.23.0"),
            ("VSCode", "1.67.0"),
        ]

        # Mock the brew casks
        mock_get_casks.return_value = ["firefox", "google-chrome"]

        # Mock the filtered apps
        mock_filter_brews.return_value = [("Slack", "4.23.0"), ("VSCode", "1.67.0")]

        # Mock brew candidates - fewer results than regular recommend due to strict filtering
        mock_check_candidates.return_value = ["visual-studio-code"]

        # Run the recommend handler directly with mocked options
        with patch("builtins.print"):  # Suppress output
            mock_json_data.return_value = {}  # Mock JSON data
            versiontracker_main_module.handle_brew_recommendations(MagicMock(
                recommend=False, 
                strict_recom=True,
                debug=False,
                strict_recommend=True,
                rate_limit=10
            ))

        # Verify the functions were called
        mock_get_apps.assert_called_once()
        mock_get_casks.assert_called_once()
        mock_filter_brews.assert_called_once()
        # Ensure strict param is True
        mock_check_candidates.assert_called_once_with(
            mock_filter_brews.return_value,
            10,  # Use an exact value instead of mock_config.get.return_value
            True,
        )

    @patch("versiontracker.__main__.check_dependencies", return_value=True)
    @patch("versiontracker.__main__.get_applications")
    @patch("versiontracker.__main__.get_json_data")
    @patch("versiontracker.__main__.setup_logging")
    @patch("versiontracker.__main__.config")
    def test_main_apps_workflow(
        self,
        mock_config,
        mock_setup_logging,
        mock_json_data,
        mock_get_apps,
        mock_check_deps,
    ):
        """Test the main apps workflow."""
        # Mock config method
        mock_config.is_blacklisted.return_value = False

        # Mock the applications
        mock_get_apps.return_value = [("Firefox", "100.0"), ("Chrome", "101.0")]

        # Run the apps handler directly with mocked options
        with patch("builtins.print"):  # Suppress output
            mock_json_data.return_value = {}  # Mock JSON data
            versiontracker_main_module.handle_list_apps(MagicMock(
                apps=True,
                debug=False,
                blacklist=None
            ))

        # Verify the function was called
        mock_get_apps.assert_called_once()

    @patch("versiontracker.__main__.check_dependencies", return_value=True)
    @patch("versiontracker.__main__.get_homebrew_casks")
    @patch("versiontracker.__main__.setup_logging")
    def test_main_brews_workflow(self, mock_setup_logging, mock_get_casks, mock_check_deps):
        """Test the main brews workflow."""
        # Mock the brew casks
        mock_get_casks.return_value = ["firefox", "google-chrome"]

        # Run the brews handler directly with mocked options
        with patch("builtins.print"):  # Suppress output
            versiontracker_main_module.handle_list_brews(MagicMock(
                brews=True,
                debug=False,
                export_format=None
            ))

        # Verify the function was called
        mock_get_casks.assert_called_once()


if __name__ == "__main__":
    unittest.main()
