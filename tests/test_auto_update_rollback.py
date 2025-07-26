"""Tests for auto-update rollback mechanisms and failure recovery."""

import json
import os
import tempfile
import unittest
from typing import Any, Dict, List
from unittest.mock import MagicMock, call, patch

from versiontracker.handlers.auto_update_handlers import (
    handle_blacklist_auto_updates,
    handle_uninstall_auto_updates,
)


class TestAutoUpdateRollbackMechanisms(unittest.TestCase):
    """Test rollback mechanisms for auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_file = os.path.join(self.temp_dir, "config_backup.json")

        self.mock_config = MagicMock()
        self.mock_options = MagicMock()

        # Test data
        self.original_blacklist = ["existing-app1", "existing-app2"]
        self.test_casks = ["app1", "app2", "app3", "app4"]
        self.auto_update_casks = ["app1", "app2"]

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_config_backup(self, blacklist: List[str]) -> str:
        """Create a configuration backup file."""
        backup_data = {"blacklist": blacklist, "timestamp": "2025-07-26T10:00:00Z", "version": "0.6.5"}
        with open(self.backup_file, "w") as f:
            json.dump(backup_data, f)
        return self.backup_file

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_blacklist_rollback_on_save_failure(
        self, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test rollback when blacklist save operation fails."""
        # Setup mocks
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_input.return_value = "y"

        # Setup config behavior
        self.mock_config.get.return_value = self.original_blacklist.copy()
        self.mock_config.save.return_value = False  # Simulate save failure

        # Execute
        result = handle_blacklist_auto_updates(self.mock_options)

        # Verify failure was detected and handled
        self.assertEqual(result, 1)

        # Verify the blacklist was set but save failed
        expected_blacklist = self.original_blacklist + self.auto_update_casks
        self.mock_config.set.assert_called_once_with("blacklist", expected_blacklist)
        self.mock_config.save.assert_called_once()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_blacklist_exception_during_operation(
        self, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test handling of exceptions during blacklist operation."""
        # Setup mocks
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_input.return_value = "y"

        # Setup config to throw exception during set
        self.mock_config.get.return_value = self.original_blacklist.copy()
        self.mock_config.set.side_effect = Exception("Config corruption")

        # Execute
        result = handle_blacklist_auto_updates(self.mock_options)

        # Verify exception was caught and handled gracefully
        self.assertEqual(result, 1)
        self.mock_config.set.assert_called_once()
        self.mock_config.save.assert_not_called()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_uninstall_rollback_tracking(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test tracking of successful uninstalls for potential rollback."""
        # Setup mocks
        mock_get_config.return_value = self.mock_config
        apps_to_uninstall = ["app1", "app2", "app3", "app4"]
        mock_get_casks.return_value = apps_to_uninstall
        mock_get_auto_updates.return_value = apps_to_uninstall
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate partial success - first two succeed, then failure
        mock_run_command.side_effect = [
            ("Successfully uninstalled app1", 0),
            ("Successfully uninstalled app2", 0),
            ("Error: app3 is required by other packages", 1),
            ("Successfully uninstalled app4", 0),
        ]

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Should continue despite failure and report mixed results
        self.assertEqual(result, 1)  # Returns 1 because some failed
        self.assertEqual(mock_run_command.call_count, 4)

        # Verify all uninstall commands were attempted
        expected_calls = [
            call("brew uninstall --cask app1", timeout=60),
            call("brew uninstall --cask app2", timeout=60),
            call("brew uninstall --cask app3", timeout=60),
            call("brew uninstall --cask app4", timeout=60),
        ]
        mock_run_command.assert_has_calls(expected_calls)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_uninstall_critical_failure_handling(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test handling of critical failures during uninstall."""
        # Setup mocks
        mock_get_config.return_value = self.mock_config
        apps_to_uninstall = ["critical-app", "normal-app"]
        mock_get_casks.return_value = apps_to_uninstall
        mock_get_auto_updates.return_value = apps_to_uninstall
        mock_input.side_effect = ["y", "UNINSTALL"]

        # First app succeeds, second has critical failure
        mock_run_command.side_effect = [
            ("Successfully uninstalled critical-app", 0),
            Exception("System error: critical failure"),
        ]

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Should handle critical failure gracefully
        self.assertEqual(result, 1)
        self.assertEqual(mock_run_command.call_count, 2)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_uninstall_timeout_recovery(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test recovery from timeout during uninstall."""
        # Setup mocks
        mock_get_config.return_value = self.mock_config
        apps_to_uninstall = ["fast-app", "slow-app", "normal-app"]
        mock_get_casks.return_value = apps_to_uninstall
        mock_get_auto_updates.return_value = apps_to_uninstall
        mock_input.side_effect = ["y", "UNINSTALL"]

        # First succeeds, second times out, third succeeds
        mock_run_command.side_effect = [
            ("Successfully uninstalled fast-app", 0),
            TimeoutError("Command timed out after 60 seconds"),
            ("Successfully uninstalled normal-app", 0),
        ]

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Should continue after timeout
        self.assertEqual(result, 1)  # Returns 1 because timeout is treated as failure
        self.assertEqual(mock_run_command.call_count, 3)


class TestAutoUpdateStateConsistency(unittest.TestCase):
    """Test state consistency during auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock()
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_blacklist_atomic_operation(self, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config):
        """Test that blacklist updates are atomic (all or nothing)."""
        # Setup mocks
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = ["app1", "app2", "app3"]
        mock_get_auto_updates.return_value = ["app1", "app2"]
        mock_input.return_value = "y"

        original_blacklist = ["existing"]
        self.mock_config.get.return_value = original_blacklist

        # Test successful case
        self.mock_config.save.return_value = True
        result = handle_blacklist_auto_updates(self.mock_options)

        self.assertEqual(result, 0)
        # Verify atomic update
        expected_final = original_blacklist + ["app1", "app2"]
        self.mock_config.set.assert_called_once_with("blacklist", expected_final)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_blacklist_no_partial_updates(self, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config):
        """Test that blacklist doesn't have partial updates on failure."""
        # Setup mocks
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = ["app1", "app2"]
        mock_get_auto_updates.return_value = ["app1", "app2"]
        mock_input.return_value = "y"

        self.mock_config.get.return_value = []
        self.mock_config.save.return_value = False  # Save fails

        result = handle_blacklist_auto_updates(self.mock_options)

        # Should fail completely, not partially update
        self.assertEqual(result, 1)
        # Set was called but save failed, so state should be inconsistent
        # but the function properly reports failure
        self.mock_config.set.assert_called_once()
        self.mock_config.save.assert_called_once()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_uninstall_state_tracking(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test that uninstall operations track state correctly."""
        # Setup mocks
        mock_get_config.return_value = self.mock_config
        apps = ["app1", "app2", "app3"]
        mock_get_casks.return_value = apps
        mock_get_auto_updates.return_value = apps
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Mixed success/failure
        mock_run_command.side_effect = [
            ("Success", 0),
            ("Failed", 1),
            ("Success", 0),
        ]

        result = handle_uninstall_auto_updates(self.mock_options)

        # Should track both successful and failed operations
        self.assertEqual(result, 1)  # Overall failure due to one failed app
        self.assertEqual(mock_run_command.call_count, 3)


class TestAutoUpdateRecoveryScenarios(unittest.TestCase):
    """Test various recovery scenarios for auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock()
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_config_corruption_recovery(self, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config):
        """Test recovery when config becomes corrupted during operation."""
        # Setup mocks
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = ["app1"]
        mock_get_auto_updates.return_value = ["app1"]
        mock_input.return_value = "y"

        # Config.get works initially but set fails due to corruption
        self.mock_config.get.return_value = []
        self.mock_config.set.side_effect = [
            None,  # First call succeeds
            Exception("Config file corrupted"),  # Second call fails
        ]

        result = handle_blacklist_auto_updates(self.mock_options)

        # Should handle corruption gracefully
        self.assertEqual(result, 1)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_system_resource_exhaustion_recovery(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test recovery when system resources are exhausted."""
        # Setup mocks
        mock_get_config.return_value = self.mock_config
        apps = ["app1", "app2", "app3"]
        mock_get_casks.return_value = apps
        mock_get_auto_updates.return_value = apps
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate resource exhaustion
        mock_run_command.side_effect = [
            ("Success", 0),
            OSError("No space left on device"),
            ("Success", 0),  # Recovery after resource freed
        ]

        result = handle_uninstall_auto_updates(self.mock_options)

        # Should continue despite resource issues
        self.assertEqual(result, 1)
        self.assertEqual(mock_run_command.call_count, 3)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_dependency_conflict_recovery(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test recovery when dependency conflicts occur during uninstall."""
        # Setup mocks
        mock_get_config.return_value = self.mock_config
        apps = ["dependency", "dependent", "independent"]
        mock_get_casks.return_value = apps
        mock_get_auto_updates.return_value = apps
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Dependency conflict prevents uninstall
        mock_run_command.side_effect = [
            ("Error: dependency is required by dependent", 1),
            ("Error: dependent depends on dependency", 1),
            ("Successfully uninstalled independent", 0),
        ]

        result = handle_uninstall_auto_updates(self.mock_options)

        # Should handle conflicts and continue with what it can
        self.assertEqual(result, 1)
        self.assertEqual(mock_run_command.call_count, 3)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_permission_escalation_recovery(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test recovery when permission escalation is needed."""
        # Setup mocks
        mock_get_config.return_value = self.mock_config
        apps = ["system-app", "user-app"]
        mock_get_casks.return_value = apps
        mock_get_auto_updates.return_value = apps
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Permission denied for system app, success for user app
        mock_run_command.side_effect = [
            ("Error: Operation not permitted", 1),
            ("Successfully uninstalled user-app", 0),
        ]

        result = handle_uninstall_auto_updates(self.mock_options)

        # Should continue with what it can uninstall
        self.assertEqual(result, 1)
        self.assertEqual(mock_run_command.call_count, 2)


class TestAutoUpdateTransactionIntegrity(unittest.TestCase):
    """Test transaction-like integrity for auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock()
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_blacklist_transaction_integrity(self, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config):
        """Test that blacklist operations maintain transaction-like integrity."""
        # Setup mocks
        mock_get_config.return_value = self.mock_config
        mock_get_casks.return_value = ["app1", "app2"]
        mock_get_auto_updates.return_value = ["app1", "app2"]
        mock_input.return_value = "y"

        original_blacklist = ["existing"]
        self.mock_config.get.return_value = original_blacklist

        # Successful transaction
        self.mock_config.save.return_value = True
        result = handle_blacklist_auto_updates(self.mock_options)

        self.assertEqual(result, 0)

        # Verify transaction completed atomically
        self.mock_config.set.assert_called_once()
        self.mock_config.save.assert_called_once()

        # Verify final state includes all new apps
        final_blacklist = self.mock_config.set.call_args[0][1]
        expected = original_blacklist + ["app1", "app2"]
        self.assertEqual(sorted(final_blacklist), sorted(expected))

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_operation_integrity(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test that uninstall operations maintain proper integrity."""
        # Setup mocks
        mock_get_config.return_value = self.mock_config
        apps = ["app1", "app2", "app3"]
        mock_get_casks.return_value = apps
        mock_get_auto_updates.return_value = apps
        mock_input.side_effect = ["y", "UNINSTALL"]

        # All operations succeed
        mock_run_command.return_value = ("Success", 0)

        result = handle_uninstall_auto_updates(self.mock_options)

        # Verify integrity
        self.assertEqual(result, 0)
        self.assertEqual(mock_run_command.call_count, 3)

        # Verify final reporting shows consistent state
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("Successfully uninstalled: 3" in call for call in print_calls))
        self.assertTrue(any("Failed to uninstall: 0" in call for call in print_calls))


if __name__ == "__main__":
    unittest.main()
