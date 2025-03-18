"""Integration tests for VersionTracker."""

import unittest
from unittest.mock import ANY, MagicMock, patch

from versiontracker.__main__ import main


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

        # Run the main function with --recommend flag
        with patch("sys.argv", ["versiontracker", "--recommend"]):
            with patch("builtins.print"):  # Suppress output
                main()

        # Verify the functions were called
        mock_get_apps.assert_called_once()
        mock_get_casks.assert_called_once()
        mock_filter_brews.assert_called_once()
        mock_check_candidates.assert_called_once_with(
            mock_filter_brews.return_value,
            mock_config.get.return_value,
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

        # Run the main function with --strict-recommend flag
        with patch("sys.argv", ["versiontracker", "--strict-recommend"]):
            with patch("builtins.print"):  # Suppress output
                main()

        # Verify the functions were called
        mock_get_apps.assert_called_once()
        mock_get_casks.assert_called_once()
        mock_filter_brews.assert_called_once()
        # Ensure strict param is True
        mock_check_candidates.assert_called_once_with(
            mock_filter_brews.return_value,
            mock_config.get.return_value,
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

        # Run the main function with --apps flag
        with patch("sys.argv", ["versiontracker", "--apps"]):
            with patch("builtins.print"):  # Suppress output
                main()

        # Verify the function was called
        mock_get_apps.assert_called_once()

    @patch("versiontracker.__main__.check_dependencies", return_value=True)
    @patch("versiontracker.__main__.get_homebrew_casks")
    @patch("versiontracker.__main__.setup_logging")
    def test_main_brews_workflow(self, mock_setup_logging, mock_get_casks, mock_check_deps):
        """Test the main brews workflow."""
        # Mock the brew casks
        mock_get_casks.return_value = ["firefox", "google-chrome"]

        # Run the main function with --brews flag
        with patch("sys.argv", ["versiontracker", "--brews"]):
            with patch("builtins.print"):  # Suppress output
                main()

        # Verify the function was called
        mock_get_casks.assert_called_once()


if __name__ == "__main__":
    unittest.main()
