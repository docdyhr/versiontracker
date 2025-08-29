"""Tests for the apps module."""

from unittest.mock import patch

from versiontracker.app_finder import (
    filter_out_brews,
    get_applications,
)


def test_get_applications():
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
    assert ("TestApp", "1.0.0") in result


@patch("versiontracker.apps.partial_ratio")
def test_filter_out_brews(mock_partial_ratio):
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
        ("Firefox", "100.0.0"),
        ("Chrome", "101.0.0"),
        ("Slack", "4.23.0"),
        ("VSCode", "1.67.0"),
    ]
    brews = ["firefox", "google-chrome", "visual-studio-code"]

    # Call the function
    result = filter_out_brews(applications, brews)

    # Check the result
    assert len(result) == 1  # Only Slack should remain
    assert ("Slack", "4.23.0") in result
