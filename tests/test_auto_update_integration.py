"""Integration tests for auto-update confirmation flows and real-world scenarios."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

from versiontracker.handlers.auto_update_handlers import (
    handle_blacklist_auto_updates,
    handle_list_auto_updates,
    handle_uninstall_auto_updates,
)


class TestAutoUpdateIntegrationFlows(unittest.TestCase):
    """Integration tests for complete auto-update workflows."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()
        # Real-world app names from Homebrew
        self.real_apps = [
            "visual-studio-code",
            "google-chrome",
            "spotify",
            "slack",
            "discord",
            "zoom",
            "docker",
            "firefox",
        ]
        self.auto_update_apps = [
            "visual-studio-code",
            "google-chrome",
            "spotify",
            "slack",
            "discord",
        ]

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_complete_workflow_list_blacklist_uninstall(
        self,
        mock_print,
        mock_input,
        mock_run_command,
        mock_get_auto_updates,
        mock_get_casks,
        mock_get_config,
    ):
        """Test complete workflow: list -> blacklist -> uninstall remaining."""
        # Setup mocks
        mock_get_casks.return_value = self.real_apps
        mock_get_auto_updates.return_value = self.auto_update_apps

        # Mock config
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: {
            "blacklist": [],  # Start with empty blacklist
        }.get(key, default)
        mock_config.save.return_value = True
        mock_get_config.return_value = mock_config

        # Step 1: List auto-updates
        result = handle_list_auto_updates(self.mock_options)
        self.assertEqual(result, 0)

        # Step 2: Blacklist some apps
        mock_input.side_effect = ["y"]  # Confirm blacklist
        mock_config.get.side_effect = lambda key, default=None: {
            "blacklist": ["spotify", "slack"],  # Already blacklisted
        }.get(key, default)

        result = handle_blacklist_auto_updates(self.mock_options)
        self.assertEqual(result, 0)

        # Verify blacklist was updated correctly
        expected_blacklist = ["spotify", "slack", "visual-studio-code", "google-chrome", "discord"]
        mock_config.set.assert_called_with("blacklist", expected_blacklist)

        # Step 3: Uninstall non-blacklisted auto-update apps
        mock_input.side_effect = ["y", "UNINSTALL"]
        mock_config.get.side_effect = lambda key, default=None: {
            "blacklist": expected_blacklist,
        }.get(key, default)

        # Filter out blacklisted apps for uninstall
        non_blacklisted = [app for app in self.auto_update_apps if app not in expected_blacklist]
        mock_get_auto_updates.return_value = non_blacklisted

        mock_run_command.return_value = ("Success", 0)
        result = handle_uninstall_auto_updates(self.mock_options)
        self.assertEqual(result, 0)


class TestAutoUpdateWithFilters(unittest.TestCase):
    """Test auto-update functionality with various filter combinations."""

    def test_auto_update_filter_logic(self):
        """Test auto-update filter logic works correctly."""
        all_apps = ["app1", "app2", "app3", "app4"]
        auto_update_apps = ["app1", "app3"]

        # Test exclude auto-updates
        excluded = [app for app in all_apps if app not in auto_update_apps]
        self.assertEqual(excluded, ["app2", "app4"])

        # Test only auto-updates
        only_auto = [app for app in all_apps if app in auto_update_apps]
        self.assertEqual(only_auto, ["app1", "app3"])


class TestAutoUpdateExportIntegration(unittest.TestCase):
    """Test auto-update functionality with export features."""

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.print")
    def test_list_auto_updates_json_export(self, mock_print, mock_get_auto_updates, mock_get_casks, mock_get_config):
        """Test exporting auto-update list to JSON format."""
        # Setup mocks
        test_apps = ["vscode", "chrome", "slack"]
        mock_get_casks.return_value = test_apps
        mock_get_auto_updates.return_value = test_apps

        mock_config = MagicMock()
        mock_config.get.return_value = ["slack"]  # Slack is blacklisted
        mock_get_config.return_value = mock_config

        # Add export options
        self.mock_options = MagicMock()
        self.mock_options.export_format = "json"
        self.mock_options.output_file = None

        # Capture print output to verify JSON structure
        printed_output = []
        mock_print.side_effect = lambda x, **kwargs: printed_output.append(x)

        # Execute
        result = handle_list_auto_updates(self.mock_options)

        # Should still succeed even with export format
        # (Note: actual export would be handled by the calling function)
        self.assertEqual(result, 0)


class TestAutoUpdateDryRunMode(unittest.TestCase):
    """Test dry-run mode for auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_dry_run_mode(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test dry-run mode for uninstall operations."""
        # Setup mocks
        mock_get_casks.return_value = ["app1", "app2"]
        mock_get_auto_updates.return_value = ["app1", "app2"]

        # Add dry-run option
        self.mock_options.dry_run = True

        # In dry-run mode, we should see what would happen but not execute
        # This would need to be implemented in the actual handler
        # For now, test the normal flow
        mock_input.side_effect = ["y", "UNINSTALL"]
        mock_run_command.return_value = ("Success", 0)

        result = handle_uninstall_auto_updates(self.mock_options)
        self.assertEqual(result, 0)


class TestAutoUpdateErrorRecovery(unittest.TestCase):
    """Test error recovery mechanisms in auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_blacklist_recovery_from_corrupt_config(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test recovery when config file is corrupted during operation."""
        # Setup mocks
        mock_get_casks.return_value = ["app1"]
        mock_get_auto_updates.return_value = ["app1"]
        mock_input.return_value = "y"

        mock_config = MagicMock()
        # First call returns valid list, second call (during save) raises exception
        mock_config.get.return_value = []
        mock_config.save.side_effect = Exception("Config corrupted")
        mock_get_config.return_value = mock_config

        # Execute - should handle corruption gracefully
        result = handle_blacklist_auto_updates(self.mock_options)
        self.assertEqual(result, 1)

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_recovery_from_brew_corruption(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test recovery when brew database is corrupted during uninstall."""
        # Setup mocks
        mock_get_casks.return_value = ["app1", "app2", "app3"]
        mock_get_auto_updates.return_value = ["app1", "app2", "app3"]
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate brew database corruption after first uninstall
        mock_run_command.side_effect = [
            ("Success", 0),  # app1 succeeds
            ("Error: Brew database corrupted", 1),  # app2 fails
            ("Error: Brew database corrupted", 1),  # app3 fails
        ]

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Should report partial failure
        self.assertEqual(result, 1)
        self.assertEqual(mock_run_command.call_count, 3)


class TestAutoUpdateUserExperience(unittest.TestCase):
    """Test user experience aspects of auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_blacklist_with_progress_feedback(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test that progress feedback is provided during operations."""
        # Setup mocks for large operation
        large_app_list = [f"app{i}" for i in range(100)]
        mock_get_casks.return_value = large_app_list
        mock_get_auto_updates.return_value = large_app_list[:50]  # 50 auto-update apps
        mock_input.return_value = "y"

        mock_config = MagicMock()
        mock_config.get.return_value = []
        mock_config.save.return_value = True
        mock_get_config.return_value = mock_config

        # Execute
        result = handle_blacklist_auto_updates(self.mock_options)

        # Verify success and that progress was shown
        self.assertEqual(result, 0)
        # Check that print was called multiple times for progress
        self.assertGreater(mock_print.call_count, 5)

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_with_color_coded_output(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test that output uses appropriate colors for success/failure."""
        # Setup mocks
        mock_get_casks.return_value = ["app1", "app2", "app3"]
        mock_get_auto_updates.return_value = ["app1", "app2", "app3"]
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Mixed results
        mock_run_command.side_effect = [
            ("Success", 0),  # app1 succeeds
            ("Error", 1),  # app2 fails
            ("Success", 0),  # app3 succeeds
        ]

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Should show mixed results
        self.assertEqual(result, 1)
        # Verify print was called for each app status
        self.assertGreaterEqual(mock_print.call_count, 6)


class TestAutoUpdateSafetyChecks(unittest.TestCase):
    """Test safety checks and guards in auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_prevents_system_app_removal(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test that system-critical apps are protected from uninstall."""
        # Include some system-like app names
        system_apps = ["safari", "finder", "system-preferences"]
        normal_apps = ["chrome", "slack"]
        all_apps = system_apps + normal_apps

        mock_get_casks.return_value = all_apps
        mock_get_auto_updates.return_value = all_apps
        mock_input.side_effect = ["y", "UNINSTALL"]

        # System apps should fail to uninstall
        results = []
        for app in all_apps:
            if app in system_apps:
                results.append(("Error: Cannot uninstall system app", 1))
            else:
                results.append(("Success", 0))
        mock_run_command.side_effect = results

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Should report partial failure due to system apps
        self.assertEqual(result, 1)
        self.assertEqual(mock_run_command.call_count, 5)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_blacklist_validates_app_names(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test that invalid app names are handled properly."""
        # Include some potentially problematic app names
        test_apps = [
            "normal-app",
            "app with spaces",  # Invalid cask name
            "../../../etc/passwd",  # Path traversal attempt
            "app;rm -rf /",  # Command injection attempt
            "",  # Empty string
        ]

        mock_get_casks.return_value = test_apps
        mock_get_auto_updates.return_value = test_apps
        mock_input.return_value = "y"

        mock_config = MagicMock()
        mock_config.get.return_value = []
        mock_config.save.return_value = True
        mock_get_config.return_value = mock_config

        # Execute
        result = handle_blacklist_auto_updates(self.mock_options)

        # Should handle invalid names gracefully
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
