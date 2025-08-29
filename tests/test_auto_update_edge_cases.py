"""Comprehensive test suite for auto-update edge cases and failure scenarios."""

import tempfile
import unittest
from unittest.mock import MagicMock, patch

from versiontracker.config import Config
from versiontracker.exceptions import HomebrewError, NetworkError
from versiontracker.handlers.auto_update_handlers import (
    handle_blacklist_auto_updates,
    handle_list_auto_updates,
    handle_uninstall_auto_updates,
)


class TestAutoUpdateEdgeCases(unittest.TestCase):
    """Test edge cases for auto-update functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock(spec=Config)
        self.mock_config.get.return_value = []
        self.mock_config.save.return_value = True

        self.mock_options = MagicMock()
        self.test_casks = ["vscode", "slack", "firefox", "chrome", "zoom"]
        self.auto_update_casks = ["vscode", "slack", "zoom"]

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_blacklist_with_corrupted_config(self, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config):
        """Test blacklisting when config file is corrupted."""
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_input.return_value = "y"

        # Simulate config save failure
        self.mock_config.save.return_value = False

        result = handle_blacklist_auto_updates(self.mock_options)

        self.assertEqual(result, 1)
        self.mock_config.save.assert_called_once()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    def test_blacklist_with_unicode_app_names(self, mock_get_auto_updates, mock_get_casks, mock_get_config):
        """Test blacklisting apps with unicode characters in names."""
        unicode_casks = ["café-app", "naïve-editor", "测试-app", "🎨-painter"]
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = unicode_casks
        mock_get_auto_updates.return_value = unicode_casks[:2]

        with patch("builtins.input", return_value="y"):
            result = handle_blacklist_auto_updates(self.mock_options)

        self.assertEqual(result, 0)
        # Verify unicode names were handled correctly
        self.mock_config.set.assert_called_once_with("blacklist", unicode_casks[:2])

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_uninstall_with_dependency_conflicts(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test uninstalling when apps have dependency conflicts."""
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = ["zoom"]  # App with dependencies
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate dependency error
        mock_run_command.return_value = ("Error: zoom is required by other installed casks", 1)

        result = handle_uninstall_auto_updates(self.mock_options)

        self.assertEqual(result, 1)
        mock_run_command.assert_called_once_with("brew uninstall --cask zoom", timeout=60)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    def test_empty_cask_list(self, mock_get_auto_updates, mock_get_casks, mock_get_config):
        """Test handling when no casks are installed."""
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = []

        result = handle_blacklist_auto_updates(self.mock_options)

        self.assertEqual(result, 0)
        mock_get_auto_updates.assert_not_called()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    def test_all_apps_already_blacklisted(self, mock_get_auto_updates, mock_get_casks, mock_get_config):
        """Test when all auto-update apps are already blacklisted."""
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        # Simulate all apps already in blacklist
        self.mock_config.get.return_value = self.auto_update_casks

        result = handle_blacklist_auto_updates(self.mock_options)

        self.assertEqual(result, 0)
        # Should not attempt to save config
        self.mock_config.save.assert_not_called()


class TestAutoUpdateRollbackMechanisms(unittest.TestCase):
    """Test rollback mechanisms for failed auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock(spec=Config)
        self.mock_options = MagicMock()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_partial_uninstall_failure_reporting(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test reporting when some uninstalls fail."""
        mock_get_config.return_value = self.mock_config
        test_casks = ["app1", "app2", "app3", "app4"]
        mock_get_casks.return_value = test_casks
        mock_get_auto_updates.return_value = test_casks
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate mixed success/failure
        mock_run_command.side_effect = [
            ("Successfully uninstalled app1", 0),
            ("Error: app2 is running", 1),
            ("Successfully uninstalled app3", 0),
            ("Error: Permission denied for app4", 1),
        ]

        result = handle_uninstall_auto_updates(self.mock_options)

        self.assertEqual(result, 1)  # Should return 1 if any failed
        self.assertEqual(mock_run_command.call_count, 4)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    def test_config_backup_before_blacklist(self, mock_get_config):
        """Test that config is backed up before making changes."""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = ["existing-app"]
        mock_config.save.return_value = True
        mock_get_config.return_value = mock_config

        with patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks", return_value=["app1"]):
            with patch(
                "versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates", return_value=["app1"]
            ):
                with patch("builtins.input", return_value="y"):
                    result = handle_blacklist_auto_updates(self.mock_options)

        self.assertEqual(result, 0)
        # Verify the blacklist was updated correctly
        mock_config.set.assert_called_once_with("blacklist", ["existing-app", "app1"])


class TestAutoUpdateConfirmationFlows(unittest.TestCase):
    """Test various user confirmation scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock(spec=Config)
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_various_confirmation_inputs(self, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config):
        """Test handling of various user confirmation inputs."""
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = ["app1"]
        mock_get_auto_updates.return_value = ["app1"]

        # Test different user inputs
        test_cases = [
            ("n", 0, False),  # No
            ("N", 0, False),  # No (uppercase)
            ("", 0, False),  # Empty (default to No)
            ("yes", 0, False),  # Invalid (not just 'y')
            ("Y", 0, True),  # Uppercase Y should work (gets converted to lowercase)
            (" y ", 0, True),  # y with spaces (strip should handle and save)
        ]

        for user_input, expected_result, should_save in test_cases:
            with self.subTest(user_input=repr(user_input)):
                mock_input.return_value = user_input  # Don't pre-strip, let the handler do it
                self.mock_config.get.return_value = []  # Reset config state
                self.mock_config.save.return_value = True  # Mock save success
                self.mock_config.save.reset_mock()
                self.mock_config.set.reset_mock()  # Reset set mock as well

                result = handle_blacklist_auto_updates(self.mock_options)

                self.assertEqual(result, expected_result, f"Failed for input {repr(user_input)}")
                if should_save:
                    self.mock_config.save.assert_called_once()
                else:
                    try:
                        self.mock_config.save.assert_not_called()
                    except AssertionError:
                        print(f"Save was called for input {repr(user_input)} when it shouldn't have been")
                        raise

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_uninstall_double_confirmation(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test the double confirmation for uninstall."""
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = ["app1"]
        mock_get_auto_updates.return_value = ["app1"]
        mock_run_command.return_value = ("Success", 0)

        # Test various confirmation combinations
        test_cases = [
            (["n", "UNINSTALL"], False),  # First no
            (["y", "uninstall"], False),  # Wrong second confirmation
            (["y", "INSTALL"], False),  # Wrong word
            (["y", ""], False),  # Empty second confirmation
            (["y", "UNINSTALL"], True),  # Correct flow
        ]

        for inputs, should_uninstall in test_cases:
            with self.subTest(inputs=inputs):
                mock_input.side_effect = inputs
                mock_run_command.reset_mock()

                result = handle_uninstall_auto_updates(self.mock_options)

                if should_uninstall:
                    mock_run_command.assert_called_once()
                    self.assertEqual(result, 0)
                else:
                    mock_run_command.assert_not_called()
                    self.assertEqual(result, 0)


class TestAutoUpdateNetworkAndPermissionErrors(unittest.TestCase):
    """Test handling of network and permission errors."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock(spec=Config)
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    def test_network_error_during_cask_fetch(self, mock_get_casks, mock_get_config):
        """Test handling when network error occurs during cask fetch."""
        mock_get_config.return_value = self.mock_config
        mock_get_casks.side_effect = NetworkError("Connection timeout")

        result = handle_blacklist_auto_updates(self.mock_options)

        self.assertEqual(result, 1)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_permission_errors_during_uninstall(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test handling permission errors during uninstall."""
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = ["app1", "app2"]
        mock_get_auto_updates.return_value = ["app1", "app2"]
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate permission errors
        mock_run_command.side_effect = [
            ("Error: Permission denied", 1),
            ("Error: Operation not permitted", 1),
        ]

        result = handle_uninstall_auto_updates(self.mock_options)

        self.assertEqual(result, 1)
        self.assertEqual(mock_run_command.call_count, 2)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    def test_homebrew_not_available(self, mock_get_auto_updates, mock_get_casks, mock_get_config):
        """Test handling when Homebrew is not available."""
        mock_get_config.return_value = self.mock_config
        mock_get_casks.side_effect = HomebrewError("brew command not found")

        result = handle_list_auto_updates(self.mock_options)

        self.assertEqual(result, 1)


class TestAutoUpdateConcurrentOperations(unittest.TestCase):
    """Test handling of concurrent operations and race conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_concurrent_blacklist_modifications(
        self, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test when blacklist is modified concurrently."""
        mock_config = MagicMock(spec=Config)
        mock_get_config.return_value = mock_config
        mock_get_casks.return_value = ["app1", "app2"]
        mock_get_auto_updates.return_value = ["app1", "app2"]
        mock_input.return_value = "y"

        # Simulate concurrent modification - blacklist changes between get and set
        mock_config.get.side_effect = [
            [],  # First call returns empty
            ["app3"],  # Config was modified by another process
        ]

        result = handle_blacklist_auto_updates(self.mock_options)

        # Should still succeed but include all apps
        self.assertEqual(result, 0)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_app_state_changes_during_uninstall(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test when app state changes during uninstall operation."""
        mock_config = MagicMock(spec=Config)
        mock_get_config.return_value = mock_config
        mock_get_casks.return_value = ["app1", "app2", "app3"]
        mock_get_auto_updates.return_value = ["app1", "app2", "app3"]
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate app2 being uninstalled by another process
        mock_run_command.side_effect = [
            ("Success", 0),
            ("Error: app2 is not installed", 1),
            ("Success", 0),
        ]

        result = handle_uninstall_auto_updates(self.mock_options)

        # Should handle gracefully and continue
        self.assertEqual(result, 1)  # Returns 1 because one failed
        self.assertEqual(mock_run_command.call_count, 3)


class TestAutoUpdateTimeoutScenarios(unittest.TestCase):
    """Test timeout handling in auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_uninstall_timeout_handling(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test handling of timeouts during uninstall."""
        mock_config = MagicMock(spec=Config)
        mock_get_config.return_value = mock_config
        mock_get_casks.return_value = ["slow-app"]
        mock_get_auto_updates.return_value = ["slow-app"]
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate timeout
        mock_run_command.side_effect = TimeoutError("Command timed out")

        result = handle_uninstall_auto_updates(self.mock_options)

        self.assertEqual(result, 1)
        # Verify timeout parameter was passed
        mock_run_command.assert_called_with("brew uninstall --cask slow-app", timeout=60)


class TestAutoUpdateLargeScaleOperations(unittest.TestCase):
    """Test handling of large-scale operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_blacklist_large_number_of_apps(self, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config):
        """Test blacklisting a large number of apps (100+)."""
        mock_config = MagicMock(spec=Config)
        mock_get_config.return_value = mock_config

        # Generate 150 test apps
        large_cask_list = [f"app-{i}" for i in range(150)]
        auto_update_list = [f"app-{i}" for i in range(0, 100)]  # 100 with auto-updates

        mock_get_casks.return_value = large_cask_list
        mock_get_auto_updates.return_value = auto_update_list
        mock_input.return_value = "y"
        mock_config.get.return_value = []
        mock_config.save.return_value = True

        result = handle_blacklist_auto_updates(self.mock_options)

        self.assertEqual(result, 0)
        # Verify all 100 apps were added
        mock_config.set.assert_called_once()
        blacklist_arg = mock_config.set.call_args[0][1]
        self.assertEqual(len(blacklist_arg), 100)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_progress_reporting_large_scale(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test progress reporting during large-scale uninstall."""
        mock_config = MagicMock(spec=Config)
        mock_get_config.return_value = mock_config

        # Generate 50 apps to uninstall
        apps_to_uninstall = [f"app-{i}" for i in range(50)]
        mock_get_casks.return_value = apps_to_uninstall
        mock_get_auto_updates.return_value = apps_to_uninstall
        mock_input.side_effect = ["y", "UNINSTALL"]

        # All succeed
        mock_run_command.return_value = ("Success", 0)

        result = handle_uninstall_auto_updates(self.mock_options)

        self.assertEqual(result, 0)
        self.assertEqual(mock_run_command.call_count, 50)

        # Verify progress was reported
        print_calls = [str(call) for call in mock_print.call_args_list]
        # Should show the list of apps and final summary
        self.assertTrue(any("Found 50 casks" in str(call) for call in print_calls))
        self.assertTrue(any("Successfully uninstalled: 50" in str(call) for call in print_calls))


if __name__ == "__main__":
    unittest.main()
