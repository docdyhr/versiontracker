"""Advanced test cases for auto-update functionality.

This module contains comprehensive tests for edge cases, error conditions,
integration scenarios, and performance testing for the auto-update feature.
"""

import unittest
from unittest.mock import MagicMock, patch

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
    """Test confirmation flow scenarios for auto-update operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()

    def _assert_command_execution(self, mock_run, should_proceed):
        """Helper to assert command execution based on expected outcome."""
        if should_proceed:
            mock_run.assert_called_once()
        else:
            mock_run.assert_not_called()

    def test_uninstall_with_various_confirmation_inputs(self):
        """Test various user inputs for confirmation prompts."""
        # Test valid confirmation sequence
        self._test_uninstall_confirmation(["y", "UNINSTALL"], should_proceed=True)

        # Test capital Y is accepted
        self._test_uninstall_confirmation(["Y", "UNINSTALL"], should_proceed=True)

        # Test valid with extra spaces
        self._test_uninstall_confirmation([" y ", "UNINSTALL"], should_proceed=True)

        # Test UNINSTALL with trailing space
        self._test_uninstall_confirmation(["y", "UNINSTALL "], should_proceed=True)

        # Test full "yes" not accepted
        self._test_uninstall_confirmation(["yes", "UNINSTALL"], should_proceed=False)

        # Test lowercase uninstall not accepted
        self._test_uninstall_confirmation(["y", "uninstall"], should_proceed=False)

        # Test empty confirmation
        self._test_uninstall_confirmation(["y", ""], should_proceed=False)

        # Test first prompt cancelled
        self._test_uninstall_confirmation(["n", "UNINSTALL"], should_proceed=False)

        # Test empty first prompt
        self._test_uninstall_confirmation(["", "UNINSTALL"], should_proceed=False)

    def _test_uninstall_confirmation(self, inputs, should_proceed):
        """Helper method to test uninstall confirmation scenarios."""
        auto_update_handlers = "versiontracker.handlers.auto_update_handlers"

        with patch(f"{auto_update_handlers}.get_homebrew_casks") as mock_casks:
            with patch(f"{auto_update_handlers}.get_casks_with_auto_updates") as mock_auto_updates:
                with patch("builtins.input") as mock_input:
                    with patch("builtins.print"):
                        with patch(f"{auto_update_handlers}.run_command") as mock_run:
                            # Setup mocks
                            mock_casks.return_value = ["app1"]
                            mock_auto_updates.return_value = ["app1"]
                            mock_input.side_effect = inputs
                            mock_run.return_value = ("Success", 0)

                            handle_uninstall_auto_updates(self.mock_options)

                            self._assert_command_execution(mock_run, should_proceed)

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
        # Generate 150 test apps and 75 auto-update apps
        large_app_list = self._generate_app_list(150)
        auto_update_apps = self._generate_auto_update_apps()

        # Setup mocks
        mock_get_casks.return_value = large_app_list
        mock_get_auto_updates.return_value = auto_update_apps
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Simulate mixed results using helper
        results = self._generate_mixed_uninstall_results()
        mock_run_command.side_effect = results

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Verify
        self.assertEqual(result, 1)  # Some failures
        # Should call run_command 75 times (one for each auto-update app)
        expected_call_count = 75
        self.assertEqual(mock_run_command.call_count, expected_call_count)

    def _generate_app_list(self, count: int) -> list[str]:
        """Generate a list of test app names."""
        return [f"app{i}" for i in range(count)]

    def _generate_auto_update_apps(self) -> list[str]:
        """Generate list of auto-update apps (every second app up to 150)."""
        return [f"app{i}" for i in range(0, 150, 2)]

    def _create_uninstall_result(self, index):
        """Helper to create a single uninstall result based on index."""
        if index % 10 == 0:  # Every 10th app fails
            return ("Error: Failed to uninstall", 1)
        else:
            return ("Success", 0)

    def _generate_mixed_uninstall_results(self) -> list[tuple[str, int]]:
        """Generate mixed success/failure results for uninstall operations."""
        # Generate 75 results (one for each auto-update app)
        return [self._create_uninstall_result(i) for i in range(75)]

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_blacklist_merge_with_large_existing_blacklist(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test adding to a blacklist that already has 500+ entries."""
        # Setup large existing blacklist and new apps using helpers
        existing_blacklist = self._generate_existing_blacklist()
        new_apps = self._generate_new_apps()

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

    def _generate_existing_blacklist(self) -> list[str]:
        """Generate large existing blacklist with 500 entries."""
        return [f"old-app{i}" for i in range(500)]

    def _generate_new_apps(self) -> list[str]:
        """Generate 50 new apps to add to blacklist."""
        return [f"new-app{i}" for i in range(50)]


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
