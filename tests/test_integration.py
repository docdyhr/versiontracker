"""Integration tests for VersionTracker."""

import importlib.util

# Import the main function but avoid executing imports
import sys
import unittest
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location(
    "versiontracker.__main__",
    "/Users/thomas/Programming/versiontracker/versiontracker/__main__.py",
)
versiontracker_main_module = importlib.util.module_from_spec(spec)
sys.modules["versiontracker.__main__"] = versiontracker_main_module
spec.loader.exec_module(versiontracker_main_module)
main = versiontracker_main_module.versiontracker_main

# Import handler modules
from versiontracker.apps import get_applications, get_homebrew_casks, filter_out_brews, check_brew_install_candidates
from versiontracker.utils import get_json_data
from versiontracker.handlers.brew_handlers import handle_brew_recommendations
from versiontracker.handlers.app_handlers import handle_list_apps
from versiontracker.handlers.brew_handlers import handle_list_brews

# Override the handler functions in the main module for testing
versiontracker_main_module.handle_brew_recommendations = handle_brew_recommendations
versiontracker_main_module.handle_list_apps = handle_list_apps
versiontracker_main_module.handle_list_brews = handle_list_brews

# Also add the functions needed by the tests
versiontracker_main_module.get_applications = get_applications
versiontracker_main_module.get_homebrew_casks = get_homebrew_casks
versiontracker_main_module.filter_out_brews = filter_out_brews
versiontracker_main_module.check_brew_install_candidates = check_brew_install_candidates
versiontracker_main_module.get_json_data = get_json_data


class TestIntegration(unittest.TestCase):
    """Integration test cases for VersionTracker."""

    # Patch check_dependencies at its source
    @patch("versiontracker.config.check_dependencies", return_value=True)
    @patch("versiontracker.handlers.brew_handlers.get_applications")
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.brew_handlers.filter_out_brews")
    @patch("versiontracker.handlers.brew_handlers.check_brew_install_candidates")
    @patch("versiontracker.handlers.brew_handlers.get_json_data")
    @patch("versiontracker.__main__.setup_logging")
    @patch("versiontracker.config.Config")
    def test_main_recommend_workflow(
        self,
        MockConfig,
        mock_setup_logging,
        mock_json_data,
        mock_check_candidates,
        mock_filter_brews,
        mock_get_casks,
        mock_get_apps,
        mock_check_deps,
    ):
        """Test the main recommend workflow."""
        # Mock the instance returned by Config()
        mock_config_instance = MockConfig.return_value
        mock_config_instance.is_blacklisted.return_value = False
        mock_config_instance.get.return_value = 10
        mock_config_instance.rate_limit = 10
        mock_config_instance.debug = False

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
            versiontracker_main_module.handle_brew_recommendations(
                MagicMock(
                    recommend=True,
                    strict_recom=False,
                    debug=False,
                    strict_recommend=False,
                    rate_limit=10,
                )
            )

        # Verify the functions were called
        mock_get_apps.assert_called_once()
        mock_get_casks.assert_called_once()
        mock_filter_brews.assert_called_once()
        mock_check_candidates.assert_called_once_with(
            mock_filter_brews.return_value,
            10,
            False,
        )

    # Patch check_dependencies at its source
    @patch("versiontracker.config.check_dependencies", return_value=True)
    @patch("versiontracker.handlers.brew_handlers.get_applications")
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.brew_handlers.filter_out_brews")
    @patch("versiontracker.handlers.brew_handlers.check_brew_install_candidates")
    @patch("versiontracker.handlers.brew_handlers.get_json_data")
    @patch("versiontracker.__main__.setup_logging")
    @patch("versiontracker.handlers.brew_handlers.get_config")
    def test_main_strict_recommend_workflow(
        self,
        mock_get_config,
        mock_setup_logging,
        mock_json_data,
        mock_check_candidates,
        mock_filter_brews,
        mock_get_casks,
        mock_get_apps,
        mock_check_deps,
    ):
        """Test the main strict recommend workflow."""
        # Configure the mock instance returned by the patched get_config
        mock_config_instance = mock_get_config.return_value
        # Use configure_mock for clarity
        mock_config_instance.configure_mock(
            **{
                "is_blacklisted.return_value": False,
                "rate_limit": 5,  # Ensure this is an integer
                "debug": False,
            }
        )
        # Optional: Add assertions here to verify the mock state before calling main
        assert hasattr(mock_config_instance, "rate_limit")
        assert isinstance(mock_config_instance.rate_limit, int)
        assert mock_config_instance.rate_limit == 5

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

        # Mock the arguments that would normally come from argparse
        mock_args = MagicMock()
        mock_args.brews = False
        mock_args.recommend = False
        mock_args.strict_recommend = True
        mock_args.debug = False
        mock_args.additional_dirs = None
        mock_args.max_workers = 4
        mock_args.rate_limit = 5  # Set this explicitly to match rate_limit in config
        mock_args.no_progress = False
        mock_args.output_format = None
        mock_args.output_file = None

        # Run the recommend handler directly with mocked options
        with patch("builtins.print"):  # Suppress output
            mock_json_data.return_value = {}  # Mock JSON data
            versiontracker_main_module.handle_brew_recommendations(mock_args)

        # Verify the functions were called
        mock_get_apps.assert_called_once()
        mock_get_casks.assert_called_once()
        mock_filter_brews.assert_called_once()
        # Ensure strict param is True
        mock_check_candidates.assert_called_once_with(
            mock_filter_brews.return_value,
            5,
            True,
        )

    # Patch check_dependencies at its source
    @patch("versiontracker.config.check_dependencies", return_value=True)
    @patch("versiontracker.handlers.app_handlers.get_applications")
    @patch("versiontracker.handlers.app_handlers.get_json_data")
    @patch("versiontracker.__main__.setup_logging")
    @patch("versiontracker.config.Config")
    def test_main_apps_workflow(
        self,
        MockConfig,
        mock_setup_logging,
        mock_json_data,
        mock_get_apps,
        mock_check_deps,
    ):
        """Test the main apps workflow."""
        # Mock the instance returned by Config()
        mock_config_instance = MockConfig.return_value
        mock_config_instance.is_blacklisted.return_value = False
        mock_config_instance.get.return_value = 10
        mock_config_instance.rate_limit = 10
        mock_config_instance.debug = False

        # Mock the applications
        mock_get_apps.return_value = [("Firefox", "100.0"), ("Chrome", "101.0")]

        # Run the apps handler directly with mocked options
        with patch("builtins.print"):  # Suppress output
            mock_json_data.return_value = {}  # Mock JSON data
            versiontracker_main_module.handle_list_apps(
                MagicMock(apps=True, debug=False, blacklist=None)
            )

        # Verify the function was called
        mock_get_apps.assert_called_once()

    # Patch check_dependencies at its source
    @patch("versiontracker.config.check_dependencies", return_value=True)
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks")
    @patch("versiontracker.__main__.setup_logging")
    @patch("versiontracker.config.Config")
    def test_main_brews_workflow(
        self,
        MockConfig,
        mock_setup_logging,
        mock_get_casks,
        mock_check_deps,
    ):
        """Test the main brews workflow."""
        # Mock the instance returned by Config()
        mock_config_instance = MockConfig.return_value
        mock_config_instance.is_blacklisted.return_value = False
        mock_config_instance.get.return_value = 10
        mock_config_instance.rate_limit = 10
        mock_config_instance.debug = False

        # Mock the brew casks
        mock_get_casks.return_value = ["firefox", "google-chrome"]

        # Run the brews handler directly with mocked options
        with patch("builtins.print"):  # Suppress output
            versiontracker_main_module.handle_list_brews(
                MagicMock(brews=True, debug=False, export_format=None)
            )

        # Verify the function was called
        mock_get_casks.assert_called_once()


if __name__ == "__main__":
    unittest.main()
