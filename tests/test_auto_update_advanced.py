"""Advanced test cases for auto-update functionality.

This module contains comprehensive tests for edge cases, error conditions,
integration scenarios, and performance testing for the auto-update feature.
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

from versiontracker.handlers.auto_update_handlers import (
    handle_blacklist_auto_updates,
    handle_list_auto_updates,
    handle_uninstall_auto_updates,
)


class TestAutoUpdateRollbackMechanisms(unittest.TestCase):
    """Test rollback mechanisms for failed auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()
        self.test_casks = ["app1", "app2", "app3", "app4", "app5"]
        self.auto_update_casks = ["app1", "app2", "app3"]

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_rollback_on_critical_app_failure(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test rollback when a critical system app fails to uninstall."""
        # Setup mocks
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = ["system-preferences", "finder", "app1"]
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate critical app protection
        mock_run_command.side_effect = [
            ("Error: Cannot uninstall system app", 1),  # system-preferences
            ("Error: Cannot uninstall system app", 1),  # finder
            ("Success", 0),  # app1
        ]

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Verify partial failure is handled
        self.assertEqual(result, 1)
        self.assertEqual(mock_run_command.call_count, 3)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_blacklist_config_save_failure_rollback(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test rollback when configuration save fails."""
        # Setup mocks
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_input.return_value = "y"

        mock_config = MagicMock()
        mock_config.get.return_value = []
        mock_config.save.return_value = False  # Simulate save failure
        mock_get_config.return_value = mock_config

        # Execute
        result = handle_blacklist_auto_updates(self.mock_options)

        # Verify failure is handled properly
        self.assertEqual(result, 1)
        mock_config.save.assert_called_once()


class TestAutoUpdatePartialFailures(unittest.TestCase):
    """Test handling of partial update failures."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_network_failure_during_operation(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test handling when network fails during uninstall operation."""
        # Setup mocks
        mock_get_casks.return_value = ["app1", "app2", "app3"]
        mock_get_auto_updates.return_value = ["app1", "app2", "app3"]
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate network failure after first successful uninstall
        mock_run_command.side_effect = [
            ("Success", 0),  # app1 succeeds
            ("Error: Network unreachable", 1),  # app2 fails due to network
            ("Error: Network unreachable", 1),  # app3 fails due to network
        ]

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Verify partial failure is reported
        self.assertEqual(result, 1)
        self.assertEqual(mock_run_command.call_count, 3)

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_permission_denied_errors(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test handling of permission denied errors during uninstall."""
        # Setup mocks
        mock_get_casks.return_value = ["app1", "app2"]
        mock_get_auto_updates.return_value = ["app1", "app2"]
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate permission errors
        mock_run_command.side_effect = [
            ("Error: Permission denied", 1),  # app1 fails
            ("Error: Operation not permitted", 1),  # app2 fails
        ]

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Verify all failures are tracked
        self.assertEqual(result, 1)


class TestAutoUpdateEdgeCases(unittest.TestCase):
    """Test edge cases for auto-update functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_blacklist_with_corrupted_config(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test blacklisting when config returns non-list value."""
        # Setup mocks
        mock_get_casks.return_value = ["app1", "app2"]
        mock_get_auto_updates.return_value = ["app1"]
        mock_input.return_value = "y"

        mock_config = MagicMock()
        # Simulate corrupted config returning string instead of list
        mock_config.get.return_value = "corrupted_value"
        mock_get_config.return_value = mock_config

        # Execute - should handle gracefully and return error code
        result = handle_blacklist_auto_updates(self.mock_options)
        self.assertEqual(result, 1)

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    def test_list_auto_updates_with_unicode_names(self, mock_get_auto_updates, mock_get_casks):
        """Test listing apps with unicode characters in names."""
        # Setup mocks with unicode app names
        unicode_apps = ["app-中文", "app-émojis-😀", "app-Ñoño"]
        mock_get_casks.return_value = unicode_apps
        mock_get_auto_updates.return_value = unicode_apps

        # Execute
        with patch("builtins.print"):
            result = handle_list_auto_updates(self.mock_options)

        # Should handle unicode without errors
        self.assertEqual(result, 0)

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_with_dependency_conflicts(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test uninstalling apps that have dependencies."""
        # Setup mocks
        mock_get_casks.return_value = ["parent-app", "dependency-app"]
        mock_get_auto_updates.return_value = ["parent-app", "dependency-app"]
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate dependency conflict
        mock_run_command.side_effect = [
            ("Error: Cannot uninstall, required by other apps", 1),  # parent-app
            ("Success", 0),  # dependency-app
        ]

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Verify partial success
        self.assertEqual(result, 1)


class TestAutoUpdateConfirmationFlows(unittest.TestCase):
    """Test various confirmation flow scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    def test_uninstall_with_various_confirmation_inputs(self):
        """Test various user inputs for confirmation prompts."""
        # Test various inputs
        test_cases = [
            (["y", "UNINSTALL"], True),  # Normal case
            (["Y", "UNINSTALL"], True),  # Capital Y is accepted (strip().lower() converts to "y")
            (["yes", "UNINSTALL"], False),  # Full "yes" not accepted
            (["y", "uninstall"], False),  # Lowercase uninstall
            (["y", "UNINSTALL "], True),  # Extra space is ok (strip() removes it)
            (["y", ""], False),  # Empty confirmation
            (["n", "UNINSTALL"], False),  # First prompt cancelled
            (["", "UNINSTALL"], False),  # Empty first prompt
            ([" y ", "UNINSTALL"], True),  # Spaces around y (strip() removes them)
        ]

        for inputs, should_proceed in test_cases:
            with self.subTest(inputs=inputs):
                with patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks") as mock_get_casks:
                    with patch(
                        "versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates"
                    ) as mock_get_auto_updates:
                        with patch("builtins.input") as mock_input:
                            with patch("builtins.print"):
                                with patch("versiontracker.handlers.auto_update_handlers.run_command") as mock_run:
                                    # Setup mocks
                                    mock_get_casks.return_value = ["app1"]
                                    mock_get_auto_updates.return_value = ["app1"]
                                    mock_input.side_effect = inputs
                                    mock_run.return_value = ("Success", 0)

                                    result = handle_uninstall_auto_updates(self.mock_options)

                                    if should_proceed:
                                        mock_run.assert_called_once()
                                    else:
                                        mock_run.assert_not_called()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_blacklist_interrupted_by_keyboard(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test handling of KeyboardInterrupt during confirmation."""
        # Setup mocks
        mock_get_casks.return_value = ["app1"]
        mock_get_auto_updates.return_value = ["app1"]
        mock_input.side_effect = KeyboardInterrupt()

        mock_config = MagicMock()
        mock_config.get.return_value = []
        mock_get_config.return_value = mock_config

        # Execute - should handle gracefully
        with self.assertRaises(KeyboardInterrupt):
            handle_blacklist_auto_updates(self.mock_options)


class TestAutoUpdateConcurrentOperations(unittest.TestCase):
    """Test concurrent auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_with_concurrent_brew_operations(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test handling when another brew process is running."""
        # Setup mocks
        mock_get_casks.return_value = ["app1", "app2"]
        mock_get_auto_updates.return_value = ["app1", "app2"]
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate brew lock error
        mock_run_command.side_effect = [
            ("Error: Another brew process is running", 1),  # app1
            ("Success", 0),  # app2 succeeds after lock clears
        ]

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Verify partial success
        self.assertEqual(result, 1)


class TestAutoUpdateExceptionHandling(unittest.TestCase):
    """Test exception handling in auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    def test_handle_exception_in_get_casks(self, mock_get_casks):
        """Test handling of exceptions from get_homebrew_casks."""
        # Simulate exception
        mock_get_casks.side_effect = Exception("Homebrew not installed")

        # Execute
        with patch("builtins.print"):
            result = handle_list_auto_updates(self.mock_options)

        # Should return error code
        self.assertEqual(result, 1)

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    def test_handle_exception_in_auto_update_detection(self, mock_get_auto_updates, mock_get_casks):
        """Test handling of exceptions during auto-update detection."""
        # Setup mocks
        mock_get_casks.return_value = ["app1", "app2"]
        mock_get_auto_updates.side_effect = Exception("Network error")

        # Execute
        with patch("builtins.print"):
            result = handle_list_auto_updates(self.mock_options)

        # Should return error code
        self.assertEqual(result, 1)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_handle_exception_during_config_operations(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test handling of exceptions during config operations."""
        # Setup mocks
        mock_get_casks.return_value = ["app1"]
        mock_get_auto_updates.return_value = ["app1"]
        mock_input.return_value = "y"

        mock_config = MagicMock()
        mock_config.get.return_value = []
        mock_config.set.side_effect = Exception("Config write error")
        mock_get_config.return_value = mock_config

        # Execute
        result = handle_blacklist_auto_updates(self.mock_options)

        # Should return error code
        self.assertEqual(result, 1)


class TestAutoUpdateLargeScaleOperations(unittest.TestCase):
    """Test auto-update operations with large numbers of apps."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_large_number_of_apps(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test uninstalling a large number of apps (100+)."""
        # Generate 150 test apps
        large_app_list = [f"app{i}" for i in range(150)]
        auto_update_apps = [f"app{i}" for i in range(0, 150, 2)]  # 75 apps

        # Setup mocks
        mock_get_casks.return_value = large_app_list
        mock_get_auto_updates.return_value = auto_update_apps
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate mixed results
        results = []
        for i, app in enumerate(auto_update_apps):
            if i % 10 == 0:  # Every 10th app fails
                results.append(("Error: Failed to uninstall", 1))
            else:
                results.append(("Success", 0))
        mock_run_command.side_effect = results

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Verify
        self.assertEqual(result, 1)  # Some failures
        self.assertEqual(mock_run_command.call_count, 75)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_blacklist_merge_with_large_existing_blacklist(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test adding to a blacklist that already has 500+ entries."""
        # Setup large existing blacklist
        existing_blacklist = [f"old-app{i}" for i in range(500)]
        new_apps = [f"new-app{i}" for i in range(50)]

        # Setup mocks
        mock_get_casks.return_value = new_apps
        mock_get_auto_updates.return_value = new_apps
        mock_input.return_value = "y"

        mock_config = MagicMock()
        mock_config.get.return_value = existing_blacklist
        mock_config.save.return_value = True
        mock_get_config.return_value = mock_config

        # Execute
        result = handle_blacklist_auto_updates(self.mock_options)

        # Verify
        self.assertEqual(result, 0)
        # Check that set was called with combined list
        expected_list = existing_blacklist + new_apps
        mock_config.set.assert_called_once_with("blacklist", expected_list)


class TestAutoUpdateTimeoutScenarios(unittest.TestCase):
    """Test timeout handling in auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_with_timeout_errors(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test handling of timeout errors during uninstall."""
        from subprocess import TimeoutExpired

        # Setup mocks
        mock_get_casks.return_value = ["slow-app1", "slow-app2"]
        mock_get_auto_updates.return_value = ["slow-app1", "slow-app2"]
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate timeout
        mock_run_command.side_effect = TimeoutExpired("brew uninstall", 60)

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Should handle timeout gracefully
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
