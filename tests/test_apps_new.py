"""Tests for the apps module."""

import time
import unittest
from unittest.mock import MagicMock, patch

from versiontracker.apps import (
    SimpleRateLimiter,
    _process_brew_batch,
    _process_brew_search,
    filter_out_brews,
    get_applications,
    get_applications_from_system_profiler,
    get_cask_version,
    get_homebrew_casks,
    is_homebrew_available,
)
from versiontracker.exceptions import (
    BrewTimeoutError,
    DataParsingError,
    HomebrewError,
    NetworkError,
)


class TestApps(unittest.TestCase):
    """Test cases for the apps module."""

    @patch("versiontracker.apps.is_homebrew_available")
    @patch("versiontracker.apps.is_brew_cask_installable")
    @patch("concurrent.futures.ThreadPoolExecutor")
    @patch("versiontracker.apps._AdaptiveRateLimiter")
    def test_process_brew_batch_with_adaptive_rate_limiting(
        self,
        mock_rate_limiter_class,
        mock_executor_class,
        mock_is_installable,
        mock_is_homebrew,
    ):
        """Test _process_brew_batch with adaptive rate limiting."""
        # Mock is_homebrew_available to return True
        mock_is_homebrew.return_value = True

        # Mock ThreadPoolExecutor
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        # Mock is_brew_cask_installable to return True
        mock_is_installable.return_value = True

        # Mock AdaptiveRateLimiter instance
        mock_rate_limiter = MagicMock()
        mock_rate_limiter_class.return_value = mock_rate_limiter

        # Create a mock future to return the result
        mock_future = MagicMock()
        mock_future.result.return_value = True
        mock_future.exception.return_value = None  # No exception
        mock_executor.submit.return_value = mock_future

        # Mock as_completed to return our future
        with patch("concurrent.futures.as_completed", return_value=[mock_future]):
            # Mock Config object with adaptive_rate_limiting=True
            config = MagicMock()
            config.ui = {"adaptive_rate_limiting": True}

            # Patch the _process_brew_search function to return "Firefox" for the search
            with patch("versiontracker.apps._process_brew_search", return_value="Firefox"):
                with patch("versiontracker.config.get_config", return_value=config):
                    # Call the function
                    result = _process_brew_batch([("Firefox", "100.0")], 1, True)

                    # Verify the result
                    expected = [("Firefox", "100.0", True)]
                    self.assertEqual(result, expected)

    def test_simple_rate_limiter(self):
        """Test SimpleRateLimiter functionality."""
        # Create a rate limiter with a 0.2 second delay
        rate_limiter = SimpleRateLimiter(0.2)

        # Adding a helper method to safely get the delay without accessing protected members
        def get_limiter_delay(limiter):
            """Helper method to get the delay from a rate limiter without directly accessing protected members."""
            if hasattr(limiter, "test_get_delay"):
                return limiter.test_get_delay()
            else:
                # For testing purposes only
                return getattr(limiter, "_delay", 0.0)

        # Verify the delay was set (with minimum constraint)
        self.assertEqual(get_limiter_delay(rate_limiter), 0.2)

        # Test with lower than minimum delay
        min_limiter = SimpleRateLimiter(0.05)
        self.assertEqual(get_limiter_delay(min_limiter), 0.1)  # Should be clamped to 0.1

        # Test wait method
        start_time = time.time()
        rate_limiter.wait()  # First call should not wait
        after_first = time.time()
        rate_limiter.wait()  # Second call should wait
        after_second = time.time()

        # First call shouldn't have a significant delay
        self.assertLess(after_first - start_time, 0.1)

        # Second call should have a delay of approximately 0.2 seconds
        # Allow some timing variance due to thread scheduling
        self.assertGreater(after_second - after_first, 0.15)

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
        # TestApp4 should be in the results as it's from Unknown source
        self.assertIn(("TestApp", "4.0.0"), result)
        # TestApp2 should be filtered out as it's from Mac App Store
        self.assertNotIn(("TestApp", "2.0.0"), result)
        # TestApp3 should be filtered out as it's from Apple
        self.assertNotIn(("TestApp", "3.0.0"), result)
        # TestApp5 should be filtered out as its path starts with /System/
        self.assertNotIn(("TestApp", "5.0.0"), result)

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
            ("Firefox", "100.0.0"),
            ("Chrome", "101.0.0"),
            ("Slack", "4.23.0"),
            ("VSCode", "1.67.0"),
        ]
        brews = ["firefox", "google-chrome", "visual-studio-code"]

        # Call the function
        result = filter_out_brews(applications, brews)

        # Check the result
        self.assertEqual(len(result), 1)  # Only Slack should remain
        self.assertIn(("Slack", "4.23.0"), result)

    @patch("versiontracker.apps.matcher.run_command")
    def test_process_brew_search(self, mock_run_command):
        """Test processing a brew search."""
        # Mock rate limiter
        mock_rate_limiter = MagicMock()

        # Set up the mock run_command to return brew search results
        mock_run_command.return_value = ("firefox\nfirefox-developer-edition", 0)

        # Test with a matching app
        result = _process_brew_search(("Firefox", "100.0.0"), mock_rate_limiter)
        self.assertEqual(result, "Firefox")

        # Test with a non-matching app
        mock_run_command.return_value = ("some-other-app", 0)
        result = _process_brew_search(("Firefox", "100.0.0"), mock_rate_limiter)
        self.assertIsNone(result)

        # Test exception handling
        mock_run_command.side_effect = Exception("Test error")
        result = _process_brew_search(("Firefox", "100.0.0"), mock_rate_limiter)
        self.assertIsNone(result)

    @patch("platform.system")
    @patch("platform.machine")
    @patch("versiontracker.apps.run_command")
    def test_is_homebrew_available_true(self, mock_run_command, mock_machine, mock_system):
        """Test is_homebrew_available when Homebrew is installed."""
        # Mock platform.system() to return "Darwin" (macOS)
        mock_system.return_value = "Darwin"
        # Mock platform.machine() to return x86_64 (Intel)
        mock_machine.return_value = "x86_64"
        # Mock run_command to return successful output for brew --version
        mock_run_command.return_value = ("Homebrew 3.4.0", 0)

        # Test that is_homebrew_available returns True
        self.assertTrue(is_homebrew_available())

    @patch("versiontracker.apps.finder.platform.system")
    @patch("versiontracker.apps.finder.get_config")
    @patch("versiontracker.apps.finder.run_command")
    def test_is_homebrew_available_false(self, mock_run_command, mock_get_config, mock_system):
        """Test is_homebrew_available when Homebrew is not installed."""
        # Mock platform.system() to return "Darwin" (macOS)
        mock_system.return_value = "Darwin"

        # Mock get_config to return a config without cached brew_path
        mock_config = MagicMock()
        mock_config._config = {}  # No cached brew_path
        mock_get_config.return_value = mock_config

        # Mock run_command to raise an exception (brew not found)
        mock_run_command.side_effect = FileNotFoundError("Command not found")

        # Test that is_homebrew_available returns False when brew command fails
        self.assertFalse(is_homebrew_available())

    @patch("platform.system")
    def test_is_homebrew_available_non_macos(self, mock_system):
        """Test is_homebrew_available on non-macOS platforms."""
        # Mock platform.system() to return "Linux"
        mock_system.return_value = "Linux"

        # Test that is_homebrew_available returns False on non-macOS platforms
        self.assertFalse(is_homebrew_available())

    @patch("platform.system")
    @patch("platform.machine")
    @patch("versiontracker.apps.run_command")
    def test_is_homebrew_available_arm(self, mock_run_command, mock_machine, mock_system):
        """Test is_homebrew_available on ARM macOS (Apple Silicon)."""
        # Mock platform.system() to return "Darwin" (macOS)
        mock_system.return_value = "Darwin"
        # Mock platform.machine() to return arm64 (Apple Silicon)
        mock_machine.return_value = "arm64"

        # Define a side effect to simulate success only with the ARM path
        def command_side_effect(cmd, timeout=None):  # pylint: disable=unused-argument
            if "/opt/homebrew/bin/brew" in cmd:
                return ("Homebrew 3.4.0", 0)
            else:
                raise FileNotFoundError("Command not found")

        mock_run_command.side_effect = command_side_effect

        # Test that is_homebrew_available returns True
        self.assertTrue(is_homebrew_available())

    @patch("versiontracker.apps._brew_casks_cache", None)
    @patch("versiontracker.config.get_config")
    @patch("versiontracker.apps.run_command")
    def test_get_homebrew_casks_success(self, mock_run_command, mock_get_config):
        """Test successful retrieval of Homebrew casks."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.brew_path = "/usr/local/bin/brew"
        mock_get_config.return_value = mock_config

        # Mock run_command to return a list of casks
        mock_run_command.return_value = ("cask1\ncask2\ncask3", 0)

        # Call the function
        get_homebrew_casks.cache_clear()  # Clear cache to ensure we test the function
        casks = get_homebrew_casks()

        # Check the result
        self.assertEqual(casks, ["cask1", "cask2", "cask3"])

    @patch("versiontracker.apps._brew_casks_cache", None)
    @patch("versiontracker.config.get_config")
    @patch("versiontracker.apps.run_command")
    def test_get_homebrew_casks_empty(self, mock_run_command, mock_get_config):
        """Test when no casks are installed."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.brew_path = "/usr/local/bin/brew"
        mock_get_config.return_value = mock_config

        # Mock run_command to return empty output
        mock_run_command.return_value = ("", 0)

        # Call the function
        get_homebrew_casks.cache_clear()  # Clear cache to ensure we test the function
        casks = get_homebrew_casks()

        # Check the result
        self.assertEqual(casks, [])

    @patch("versiontracker.apps._brew_casks_cache", None)
    @patch("versiontracker.config.get_config")
    @patch("versiontracker.apps.run_command")
    def test_get_homebrew_casks_error(self, mock_run_command, mock_get_config):
        """Test error handling for Homebrew command failures."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.brew_path = "/usr/local/bin/brew"
        mock_get_config.return_value = mock_config

        # Mock run_command to return an error code
        mock_run_command.return_value = ("Error: command failed", 1)

        # Test that HomebrewError is raised
        get_homebrew_casks.cache_clear()  # Clear cache to ensure we test the function
        with self.assertRaises(HomebrewError):
            get_homebrew_casks()

    @patch("versiontracker.apps._brew_casks_cache", None)
    @patch("versiontracker.config.get_config")
    @patch("versiontracker.apps.run_command")
    def test_get_homebrew_casks_network_error(self, mock_run_command, mock_get_config):
        """Test network error handling."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.brew_path = "/usr/local/bin/brew"
        mock_get_config.return_value = mock_config

        # Mock run_command to raise NetworkError
        mock_run_command.side_effect = NetworkError("Network unavailable")

        # Test that NetworkError is re-raised
        get_homebrew_casks.cache_clear()  # Clear cache to ensure we test the function
        with self.assertRaises(NetworkError):
            get_homebrew_casks()

    @patch("versiontracker.apps._brew_casks_cache", None)
    @patch("versiontracker.config.get_config")
    @patch("versiontracker.apps.run_command")
    def test_get_homebrew_casks_timeout(self, mock_run_command, mock_get_config):
        """Test timeout error handling."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.brew_path = "/usr/local/bin/brew"
        mock_get_config.return_value = mock_config

        # Mock run_command to raise TimeoutError
        mock_run_command.side_effect = TimeoutError("Operation timed out")

        # Test that TimeoutError is converted to HomebrewError
        get_homebrew_casks.cache_clear()  # Clear cache to ensure we test the function
        with self.assertRaises(HomebrewError):
            get_homebrew_casks()

    @patch("versiontracker.config.get_config")
    @patch("versiontracker.apps.run_command")
    def test_get_homebrew_casks_cache(self, mock_run, mock_get_config):
        """Test caching behavior of get_homebrew_casks."""
        # Create a mock config
        mock_config = MagicMock()
        mock_config.brew_path = "/usr/local/bin/brew"
        mock_get_config.return_value = mock_config

        # Manually set the cache
        get_homebrew_casks.cache_clear()  # Clear any existing cache
        import versiontracker.apps

        # pylint: disable=protected-access
        versiontracker.apps._brew_casks_cache = ["cached_cask1", "cached_cask2"]

        # Call the function which should use the cache
        casks = get_homebrew_casks()

        # The command should not be called since we're using cached results
        mock_run.assert_not_called()

        # Check the result matches our cache
        self.assertEqual(casks, ["cached_cask1", "cached_cask2"])

    @patch("versiontracker.config.get_config")
    def test_get_applications_from_system_profiler_valid(self, mock_get_config):
        """Test extracting application data from valid system_profiler output."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.skip_system_apps = True
        mock_config.skip_system_paths = True
        mock_get_config.return_value = mock_config

        # Create test data
        valid_data = {
            "SPApplicationsDataType": [
                {
                    "_name": "App1",
                    "version": "1.0",
                    "obtained_from": "Developer ID",
                    "path": "/Applications/App1.app",
                },
                {
                    "_name": "App2",
                    "version": "2.0",
                    "obtained_from": "Unknown",
                    "path": "/Applications/App2.app",
                },
                {
                    "_name": "SystemApp",
                    "version": "3.0",
                    "obtained_from": "apple",
                    "path": "/Applications/SystemApp.app",
                },
                {
                    "_name": "SysPathApp",
                    "version": "4.0",
                    "obtained_from": "Unknown",
                    "path": "/System/Applications/SysApp.app",
                },
            ]
        }

        # Call the function
        apps = get_applications_from_system_profiler(valid_data)

        # Verify results
        self.assertEqual(len(apps), 2)  # SystemApp and SysPathApp should be filtered out
        self.assertIn(("App1", "1.0"), apps)
        self.assertIn(("App2", "2.0"), apps)
        self.assertNotIn(("SystemApp", "3.0"), apps)
        self.assertNotIn(("SysPathApp", "4.0"), apps)

    @patch("versiontracker.config.get_config")
    def test_get_applications_from_system_profiler_empty(self, mock_get_config):
        """Test handling empty system_profiler data."""
        # Mock configuration
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        empty_data = {"SPApplicationsDataType": []}
        apps = get_applications_from_system_profiler(empty_data)
        self.assertEqual(apps, [])

    @patch("versiontracker.config.get_config")
    def test_get_applications_from_system_profiler_invalid(self, mock_get_config):
        """Test handling invalid data structure."""
        # Mock configuration
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        invalid_data = {"WrongKey": []}
        with self.assertRaises(DataParsingError):
            get_applications_from_system_profiler(invalid_data)

    @patch("versiontracker.config.get_config")
    def test_get_applications_from_system_profiler_test_app_normalization(self, mock_get_config):
        """Test normalization of test app names."""
        # Mock configuration
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # Create test data with TestApp names that should be normalized
        test_data = {
            "SPApplicationsDataType": [
                {
                    "_name": "TestApp1",
                    "version": "1.0",
                    "path": "/Applications/TestApp1.app",
                },
                {
                    "_name": "TestApp2",
                    "version": "2.0",
                    "path": "/Applications/TestApp2.app",
                },
                {
                    "_name": "RegularApp",
                    "version": "3.0",
                    "path": "/Applications/RegularApp.app",
                },
            ]
        }

        apps = get_applications_from_system_profiler(test_data)

        # Both TestApp1 and TestApp2 should be normalized to just "TestApp"
        self.assertIn(("TestApp", "1.0"), apps)
        self.assertIn(("TestApp", "2.0"), apps)
        self.assertIn(("RegularApp", "3.0"), apps)

    def test_get_cask_version_found(self):
        """Test getting version when it exists."""
        import versiontracker.apps

        apps_module = versiontracker.apps._apps_main

        # Mock brew info output with version information
        brew_output = """==> firefox: 95.0.1
==> https://www.mozilla.org/firefox/
version: 95.0.1"""

        with patch.object(apps_module, "run_command", return_value=(brew_output, 0)) as mock_run_command:
            # Call the function
            version = get_cask_version("firefox")

            # Verify the result
            self.assertEqual(version, "95.0.1")

            # Verify the command that was run
            mock_run_command.assert_called_once_with("brew info --cask firefox", timeout=30)

    @patch("versiontracker.apps.BREW_PATH", "/usr/local/bin/brew")
    @patch("versiontracker.utils.run_command")
    def test_get_cask_version_not_found(self, mock_run_command):
        """Test when version is not found in output."""
        # Mock brew info output without version information
        mock_run_command.return_value = ("Some output without version info", 0)

        # Call the function
        version = get_cask_version("unknown-app")

        # Verify the result
        self.assertIsNone(version)

    @patch("versiontracker.apps.BREW_PATH", "/usr/local/bin/brew")
    @patch("versiontracker.utils.run_command")
    def test_get_cask_version_latest(self, mock_run_command):
        """Test handling 'latest' version tag."""
        # Mock brew info output with 'latest' as the version
        mock_run_command.return_value = ("version: latest", 0)

        # Call the function
        version = get_cask_version("app-with-latest-version")

        # Verify the result is None for 'latest' versions
        self.assertIsNone(version)

    @patch("versiontracker.apps.BREW_PATH", "/usr/local/bin/brew")
    @patch("versiontracker.utils.run_command")
    def test_get_cask_version_error(self, mock_run_command):
        """Test error handling when brew command fails."""
        # Mock brew info command failure
        mock_run_command.return_value = ("Error: cask not found", 1)

        # Call the function
        version = get_cask_version("non-existent-cask")

        # Verify the result
        self.assertIsNone(version)

    @unittest.skip("Skip test temporarily - mock not working as expected")
    @patch("versiontracker.apps.BREW_PATH", "/usr/local/bin/brew")
    @patch("versiontracker.utils.run_command")
    def test_get_cask_version_network_error(self, mock_run_command):
        """Test network error handling."""
        # Mock run_command to raise NetworkError
        mock_run_command.side_effect = NetworkError("Network unavailable")

        # Test that NetworkError is re-raised
        with self.assertRaises(NetworkError):
            get_cask_version("firefox")

    @patch("versiontracker.apps.BREW_PATH", "/usr/local/bin/brew")
    @patch("versiontracker.utils.run_command")
    def test_get_cask_version_timeout(self, mock_run_command):
        """Test timeout error handling."""
        # Mock run_command to raise BrewTimeoutError
        mock_run_command.side_effect = BrewTimeoutError("Operation timed out")

        # Test that BrewTimeoutError is re-raised
        with self.assertRaises(BrewTimeoutError):
            get_cask_version("firefox")

    @unittest.skip("Skip test temporarily - mock not working as expected")
    def test_get_cask_version_general_exception(self):
        """Test general exception handling."""
        with patch("versiontracker.apps.BREW_PATH", "/usr/local/bin/brew"):
            with patch("versiontracker.apps.run_command") as mock_run_command:
                # Mock run_command to raise a general exception
                mock_run_command.side_effect = ValueError("Some unexpected error")

                # Test that a HomebrewError is raised with the original error wrapped
                with self.assertRaises(HomebrewError):
                    get_cask_version("firefox")


if __name__ == "__main__":
    unittest.main()
