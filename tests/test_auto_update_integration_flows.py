"""Integration tests for auto-update confirmation flows and complete workflows."""

import os
import sys
import tempfile
import unittest
from io import StringIO
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, call, patch

from versiontracker.__main__ import versiontracker_main
from versiontracker.cli import get_arguments
from versiontracker.handlers.auto_update_handlers import (
    handle_blacklist_auto_updates,
    handle_list_auto_updates,
    handle_uninstall_auto_updates,
)


class TestAutoUpdateIntegrationFlows(unittest.TestCase):
    """Integration tests for complete auto-update workflows."""

    def setUp(self):
        """Set up test fixtures."""
        self.original_argv = sys.argv.copy()
        self.temp_dir = tempfile.mkdtemp()

        # Common test data
        self.test_casks = ["vscode", "slack", "firefox", "chrome", "zoom", "docker"]
        self.auto_update_casks = ["vscode", "slack", "zoom"]  # Apps with auto-updates
        self.blacklisted_casks = ["firefox"]  # Already blacklisted

    def tearDown(self):
        """Clean up test fixtures."""
        sys.argv = self.original_argv
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("versiontracker.__main__.handle_setup_logging")
    @patch("versiontracker.__main__.handle_initialize_config")
    @patch("versiontracker.__main__.handle_configure_from_options")
    @patch("versiontracker.__main__.handle_filter_management")
    @patch("versiontracker.__main__.handle_save_filter")
    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_complete_blacklist_workflow_success(
        self,
        mock_print,
        mock_input,
        mock_get_auto_updates,
        mock_get_casks,
        mock_get_config,
        mock_save_filter,
        mock_filter_mgmt,
        mock_configure,
        mock_init_config,
        mock_setup_logging,
    ):
        """Test complete successful blacklist workflow from CLI to completion."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.get.return_value = self.blacklisted_casks
        mock_config.save.return_value = True
        mock_get_config.return_value = mock_config
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_input.return_value = "y"  # User confirms
        mock_filter_mgmt.return_value = None

        # Set up command line arguments
        sys.argv = ["versiontracker", "--blacklist-auto-updates"]

        # Run main function
        result = versiontracker_main()

        # Verify success
        self.assertEqual(result, 0)

        # Verify the workflow was executed correctly
        mock_get_casks.assert_called_once()
        mock_get_auto_updates.assert_called_once_with(self.test_casks)
        mock_config.get.assert_called_with("blacklist", [])

        # Verify blacklist was updated with new apps (excluding already blacklisted)
        expected_new_apps = ["vscode", "slack", "zoom"]  # Firefox already blacklisted
        expected_final_blacklist = self.blacklisted_casks + expected_new_apps
        mock_config.set.assert_called_once_with("blacklist", expected_final_blacklist)
        mock_config.save.assert_called_once()

    @patch("versiontracker.__main__.handle_setup_logging")
    @patch("versiontracker.__main__.handle_initialize_config")
    @patch("versiontracker.__main__.handle_configure_from_options")
    @patch("versiontracker.__main__.handle_filter_management")
    @patch("versiontracker.__main__.handle_save_filter")
    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_blacklist_workflow_user_cancellation(
        self,
        mock_input,
        mock_get_auto_updates,
        mock_get_casks,
        mock_get_config,
        mock_save_filter,
        mock_filter_mgmt,
        mock_configure,
        mock_init_config,
        mock_setup_logging,
    ):
        """Test blacklist workflow when user cancels."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.get.return_value = []
        mock_get_config.return_value = mock_config
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_input.return_value = "n"  # User cancels
        mock_filter_mgmt.return_value = None

        # Set up command line arguments
        sys.argv = ["versiontracker", "--blacklist-auto-updates"]

        # Run main function
        result = versiontracker_main()

        # Verify cancellation was handled correctly
        self.assertEqual(result, 0)
        mock_config.set.assert_not_called()
        mock_config.save.assert_not_called()

    @patch("versiontracker.__main__.handle_setup_logging")
    @patch("versiontracker.__main__.handle_initialize_config")
    @patch("versiontracker.__main__.handle_configure_from_options")
    @patch("versiontracker.__main__.handle_filter_management")
    @patch("versiontracker.__main__.handle_save_filter")
    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_complete_uninstall_workflow_success(
        self,
        mock_print,
        mock_input,
        mock_run_command,
        mock_get_auto_updates,
        mock_get_casks,
        mock_get_config,
        mock_save_filter,
        mock_filter_mgmt,
        mock_configure,
        mock_init_config,
        mock_setup_logging,
    ):
        """Test complete successful uninstall workflow."""
        # Setup mocks
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_input.side_effect = ["y", "UNINSTALL"]  # User confirms both steps
        mock_run_command.return_value = ("Successfully uninstalled", 0)
        mock_filter_mgmt.return_value = None

        # Set up command line arguments
        sys.argv = ["versiontracker", "--uninstall-auto-updates"]

        # Run main function
        result = versiontracker_main()

        # Verify success
        self.assertEqual(result, 0)

        # Verify uninstall commands were executed for each app
        expected_calls = [call(f"brew uninstall --cask {app}", timeout=60) for app in self.auto_update_casks]
        mock_run_command.assert_has_calls(expected_calls, any_order=False)

    @patch("versiontracker.__main__.handle_setup_logging")
    @patch("versiontracker.__main__.handle_initialize_config")
    @patch("versiontracker.__main__.handle_configure_from_options")
    @patch("versiontracker.__main__.handle_filter_management")
    @patch("versiontracker.__main__.handle_save_filter")
    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_uninstall_workflow_double_confirmation_failure(
        self,
        mock_input,
        mock_run_command,
        mock_get_auto_updates,
        mock_get_casks,
        mock_get_config,
        mock_save_filter,
        mock_filter_mgmt,
        mock_configure,
        mock_init_config,
        mock_setup_logging,
    ):
        """Test uninstall workflow when second confirmation fails."""
        # Setup mocks
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_input.side_effect = ["y", "uninstall"]  # Wrong second confirmation
        mock_filter_mgmt.return_value = None

        # Set up command line arguments
        sys.argv = ["versiontracker", "--uninstall-auto-updates"]

        # Run main function
        result = versiontracker_main()

        # Verify cancellation was handled correctly
        self.assertEqual(result, 0)
        mock_run_command.assert_not_called()

    @patch("versiontracker.__main__.handle_setup_logging")
    @patch("versiontracker.__main__.handle_initialize_config")
    @patch("versiontracker.__main__.handle_configure_from_options")
    @patch("versiontracker.__main__.handle_filter_management")
    @patch("versiontracker.__main__.handle_save_filter")
    @patch("versiontracker.handlers.brew_handlers.get_config")
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.brew_handlers.get_casks_with_auto_updates")
    @patch("builtins.print")
    def test_list_auto_updates_workflow(
        self,
        mock_print,
        mock_get_auto_updates,
        mock_get_casks,
        mock_get_config,
        mock_save_filter,
        mock_filter_mgmt,
        mock_configure,
        mock_init_config,
        mock_setup_logging,
    ):
        """Test list auto-updates workflow."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.get.return_value = self.blacklisted_casks
        mock_get_config.return_value = mock_config
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_filter_mgmt.return_value = None

        # Set up command line arguments - use --brews --only-auto-updates to list auto-update casks
        sys.argv = ["versiontracker", "--brews", "--only-auto-updates", "--no-progress"]

        # Run main function
        result = versiontracker_main()

        # Verify success
        self.assertEqual(result, 0)

        # Verify listing was performed
        mock_get_casks.assert_called_once()
        mock_get_auto_updates.assert_called_once_with(self.test_casks)


class TestAutoUpdateConfirmationVariations(unittest.TestCase):
    """Test various user input scenarios for confirmations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock()
        self.mock_config.get.return_value = []
        self.mock_config.save.return_value = True
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_blacklist_confirmation_edge_cases(
        self, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test edge cases for blacklist confirmation."""
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = ["app1"]
        mock_get_auto_updates.return_value = ["app1"]

        # Test various invalid confirmations
        invalid_inputs = [
            "yes",  # Full word not accepted
            "Y",  # Uppercase not accepted
            " y ",  # Spaces (should be stripped and work)
            "n",  # Explicit no
            "",  # Empty input (default no)
            "maybe",  # Invalid input
            "1",  # Number
            "true",  # Boolean-like
        ]

        for user_input in invalid_inputs:
            with self.subTest(user_input=repr(user_input)):
                mock_input.return_value = user_input
                self.mock_config.save.reset_mock()

                result = handle_blacklist_auto_updates(self.mock_options)

                if user_input.strip().lower() == "y":
                    # Only "y" should trigger save
                    self.assertEqual(result, 0)
                    self.mock_config.save.assert_called_once()
                else:
                    # All others should cancel
                    self.assertEqual(result, 0)
                    self.mock_config.save.assert_not_called()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_uninstall_confirmation_edge_cases(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test edge cases for uninstall double confirmation."""
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = ["app1"]
        mock_get_auto_updates.return_value = ["app1"]
        mock_run_command.return_value = ("Success", 0)

        # Test combinations of first and second confirmations
        test_cases = [
            # First confirmation variations
            (["n", "UNINSTALL"], False, "First confirmation declined"),
            (["N", "UNINSTALL"], False, "First confirmation declined (uppercase)"),
            (["", "UNINSTALL"], False, "First confirmation empty"),
            (["no", "UNINSTALL"], False, "First confirmation 'no'"),
            # Second confirmation variations (first is 'y')
            (["y", "uninstall"], False, "Second confirmation lowercase"),
            (["y", "INSTALL"], False, "Second confirmation wrong word"),
            (["y", ""], False, "Second confirmation empty"),
            (["y", "delete"], False, "Second confirmation different word"),
            (["y", "UNINSTALL "], True, "Second confirmation with trailing space (stripped)"),
            (["y", " UNINSTALL"], True, "Second confirmation with leading space (stripped)"),
            # Valid combination
            (["y", "UNINSTALL"], True, "Valid confirmation sequence"),
        ]

        for inputs, should_proceed, description in test_cases:
            with self.subTest(inputs=inputs, description=description):
                mock_input.side_effect = inputs
                mock_run_command.reset_mock()

                result = handle_uninstall_auto_updates(self.mock_options)

                self.assertEqual(result, 0)  # Should always return 0 for cancellations

                if should_proceed:
                    mock_run_command.assert_called_once()
                else:
                    mock_run_command.assert_not_called()


class TestAutoUpdateInterruptionHandling(unittest.TestCase):
    """Test handling of interruptions during auto-update operations."""

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_keyboard_interrupt_during_confirmation(
        self, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test handling KeyboardInterrupt during confirmation."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        mock_get_casks.return_value = ["app1"]
        mock_get_auto_updates.return_value = ["app1"]
        mock_input.side_effect = KeyboardInterrupt()

        with self.assertRaises(KeyboardInterrupt):
            handle_blacklist_auto_updates(MagicMock())

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_keyboard_interrupt_during_uninstall(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test handling KeyboardInterrupt during uninstall process."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        mock_get_casks.return_value = ["app1", "app2", "app3"]
        mock_get_auto_updates.return_value = ["app1", "app2", "app3"]
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate interruption on second app
        mock_run_command.side_effect = [
            ("Success", 0),  # First app succeeds
            KeyboardInterrupt(),  # User interrupts
        ]

        with self.assertRaises(KeyboardInterrupt):
            handle_uninstall_auto_updates(MagicMock())


class TestAutoUpdateProgressReporting(unittest.TestCase):
    """Test progress reporting during auto-update operations."""

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_progress_detailed_reporting(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test detailed progress reporting during uninstall."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        apps = ["app1", "app2", "app3", "app4", "app5"]
        mock_get_casks.return_value = apps
        mock_get_auto_updates.return_value = apps
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Mix of success and failure
        mock_run_command.side_effect = [
            ("Success", 0),
            ("Error: App is running", 1),
            ("Success", 0),
            ("Error: Permission denied", 1),
            ("Success", 0),
        ]

        result = handle_uninstall_auto_updates(MagicMock())

        self.assertEqual(result, 1)  # Should return 1 because some failed

        # Verify all apps were processed
        self.assertEqual(mock_run_command.call_count, 5)

        # Check that progress was reported
        print_calls = [str(call) for call in mock_print.call_args_list]

        # Should show initial count
        self.assertTrue(any("Found 5 casks" in call for call in print_calls))

        # Should show final summary
        self.assertTrue(any("Successfully uninstalled: 3" in call for call in print_calls))
        self.assertTrue(any("Failed to uninstall: 2" in call for call in print_calls))

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_blacklist_progress_reporting(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test progress reporting during blacklist operation."""
        mock_config = MagicMock()
        mock_config.get.return_value = ["existing-app"]
        mock_config.save.return_value = True
        mock_get_config.return_value = mock_config

        all_apps = ["app1", "app2", "app3", "existing-app"]
        auto_apps = ["app1", "app2", "existing-app"]
        mock_get_casks.return_value = all_apps
        mock_get_auto_updates.return_value = auto_apps
        mock_input.return_value = "y"

        result = handle_blacklist_auto_updates(MagicMock())

        self.assertEqual(result, 0)

        # Check progress reporting
        print_calls = [str(call) for call in mock_print.call_args_list]

        # Should show count of apps with auto-updates
        self.assertTrue(any("Found 3 casks with auto-updates" in call for call in print_calls))

        # Should show how many will be added (excluding already blacklisted)
        self.assertTrue(any("add 2 casks to the blacklist" in call for call in print_calls))

        # Should show final success message
        self.assertTrue(any("Successfully added 2 casks" in call for call in print_calls))


class TestAutoUpdateErrorRecovery(unittest.TestCase):
    """Test error recovery and graceful degradation."""

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    def test_config_error_recovery(self, mock_get_auto_updates, mock_get_casks, mock_get_config):
        """Test recovery when config operations fail."""
        mock_get_casks.return_value = ["app1"]
        mock_get_auto_updates.return_value = ["app1"]

        # Simulate config.get() failure
        mock_config = MagicMock()
        mock_config.get.side_effect = Exception("Config read error")
        mock_get_config.return_value = mock_config

        result = handle_blacklist_auto_updates(MagicMock())

        self.assertEqual(result, 1)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    def test_homebrew_error_recovery(self, mock_get_casks, mock_get_config):
        """Test recovery when Homebrew operations fail."""
        mock_get_config.return_value = MagicMock()
        mock_get_casks.side_effect = Exception("Homebrew not found")

        result = handle_list_auto_updates(MagicMock())

        self.assertEqual(result, 1)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_partial_uninstall_error_recovery(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test recovery from partial uninstall failures."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        mock_get_casks.return_value = ["app1", "app2", "app3"]
        mock_get_auto_updates.return_value = ["app1", "app2", "app3"]
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate failure on second app, but continue with third
        mock_run_command.side_effect = [
            ("Success", 0),
            Exception("Unexpected error"),
            ("Success", 0),
        ]

        result = handle_uninstall_auto_updates(MagicMock())

        # Should complete operation despite error
        self.assertEqual(result, 1)
        self.assertEqual(mock_run_command.call_count, 3)


if __name__ == "__main__":
    unittest.main()
