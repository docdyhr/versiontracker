"""Tests for the apps module."""

import unittest
from unittest.mock import MagicMock, patch

from versiontracker.apps import _process_brew_search, filter_out_brews, get_applications


class TestApps(unittest.TestCase):
    """Test cases for the apps module."""

    def test_get_applications(self):
        """Test getting applications."""
        # Mock system_profiler data
        mock_data = {
            "SPApplicationsDataType": [
                {
                    "_name": "TestApp1",
                    "path": "/Applications/TestApp1.app",
                    "version": "1.0.0",
                    "obtained_from": "Developer ID",
                },
                {
                    "_name": "TestApp2",
                    "path": "/Applications/TestApp2.app",
                    "version": "2.0.0",
                    "obtained_from": "mac_app_store",  # Should be filtered out
                },
                {
                    "_name": "TestApp3",
                    "path": "/Applications/TestApp3.app",
                    "version": "3.0.0",
                    "obtained_from": "apple",  # Should be filtered out
                },
                {
                    "_name": "TestApp4",
                    "path": "/Applications/TestApp4.app",
                    "version": "4.0.0",
                    "obtained_from": "Unknown",
                },
                {
                    "_name": "TestApp5",
                    "path": "/System/Applications/TestApp5.app",  # Should be filtered out by path
                    "version": "5.0.0",
                    "obtained_from": "Unknown",
                },
            ]
        }

        # Call the function with our mock data
        result = get_applications(mock_data)

        # TestApp1 should be in the results, normalized to TestApp
        self.assertIn(("TestApp", "1.0.0"), result)

    @patch("versiontracker.apps.partial_ratio")
    def test_filter_out_brews(self, mock_partial_ratio):
        """Test filtering out applications already installed via Homebrew."""

        # Set up the mock partial_ratio to match our expectations
        def side_effect(app, brew):
            # Return high similarity for Firefox/firefox, Chrome/google-chrome,
            # VSCode/visual-studio-code
            if app == "firefox" and brew == "firefox":
                return 100
            elif app == "chrome" and brew == "google-chrome":
                return 80
            elif app == "vscode" and brew == "visual-studio-code":
                return 85
            return 30  # Return low similarity for everything else

        mock_partial_ratio.side_effect = side_effect

        # Mock applications and brews
        applications = [
            ["Firefox", "100.0.0"],
            ["Chrome", "101.0.0"],
            ["Slack", "4.23.0"],
            ["VSCode", "1.67.0"],
        ]
        brews = ["firefox", "google-chrome", "visual-studio-code"]

        # Call the function
        result = filter_out_brews(applications, brews)

        # Check the result
        self.assertEqual(len(result), 1)  # Only Slack should remain
        self.assertIn(["Slack", "4.23.0"], result)

    @patch("versiontracker.apps.run_command")
    def test_process_brew_search(self, mock_run_command):
        """Test processing a brew search."""
        # Mock rate limiter
        mock_rate_limiter = MagicMock()

        # Set up the mock run_command to return brew search results
        mock_run_command.return_value = ["firefox", "firefox-developer-edition"]

        # Test with a matching app
        result = _process_brew_search(["Firefox", "100.0.0"], mock_rate_limiter)
        self.assertEqual(result, "Firefox")

        # Test with a non-matching app
        mock_run_command.return_value = ["some-other-app"]
        result = _process_brew_search(["Firefox", "100.0.0"], mock_rate_limiter)
        self.assertIsNone(result)

        # Test exception handling
        mock_run_command.side_effect = Exception("Test error")
        result = _process_brew_search(["Firefox", "100.0.0"], mock_rate_limiter)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
