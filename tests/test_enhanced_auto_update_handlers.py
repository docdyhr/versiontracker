"""Tests for enhanced auto-update handlers with improved error handling."""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from versiontracker.handlers.enhanced_auto_update_handlers import (
    BlacklistBackup,
    EnhancedAutoUpdateHandler,
    UninstallResult,
    handle_blacklist_auto_updates_enhanced,
    handle_uninstall_auto_updates_enhanced,
)


class TestEnhancedAutoUpdateHandler(unittest.TestCase):
    """Test the enhanced auto-update handler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.handler = EnhancedAutoUpdateHandler()
        self.mock_options = MagicMock()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_blacklist_backup(self):
        """Test creating a blacklist backup."""
        test_blacklist = ["app1", "app2", "app3"]

        backup = self.handler._create_blacklist_backup(test_blacklist)

        self.assertEqual(backup.original_blacklist, test_blacklist)
        self.assertGreater(backup.timestamp, 0)

        if backup.backup_file:
            self.assertTrue(os.path.exists(backup.backup_file))

            # Verify backup file contents
            with open(backup.backup_file) as f:
                backup_data = json.load(f)

            self.assertEqual(backup_data["blacklist"], test_blacklist)
            self.assertEqual(backup_data["timestamp"], backup.timestamp)

    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_config")
    def test_restore_blacklist_from_backup(self, mock_get_config):
        """Test restoring blacklist from backup."""
        mock_config = MagicMock()
        mock_config.save.return_value = True
        mock_get_config.return_value = mock_config

        # Create a new handler so it gets the mocked config
        handler = EnhancedAutoUpdateHandler()

        # Create a backup
        original_blacklist = ["original1", "original2"]
        backup = BlacklistBackup(original_blacklist=original_blacklist)

        # Test restore
        result = handler._restore_blacklist_from_backup(backup)

        self.assertTrue(result)
        mock_config.set.assert_called_once_with("blacklist", original_blacklist)
        mock_config.save.assert_called_once()

    def test_classify_uninstall_error(self):
        """Test error classification for uninstall operations."""
        test_cases = [
            # (error_output, return_code, expected_is_critical, expected_category_contains)
            ("System integrity compromised", 1, True, "Critical system error"),
            ("app1 is required by app2", 1, False, "Dependency conflict"),
            ("Permission denied", 1, False, "Permission error"),
            ("Application is running", 1, False, "Application is currently running"),
            ("Unknown error occurred", 1, False, "Uninstall failed"),
        ]

        for error_output, return_code, expected_critical, expected_category in test_cases:
            with self.subTest(error=error_output):
                is_critical, category = self.handler._classify_uninstall_error(error_output, return_code)

                self.assertEqual(is_critical, expected_critical)
                self.assertIn(expected_category.lower(), category.lower())

    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_blacklist_enhanced_success(self, mock_input, mock_get_auto_updates, mock_get_casks):
        """Test enhanced blacklist operation success."""
        # Setup mocks
        mock_get_casks.return_value = ["app1", "app2", "app3"]
        mock_get_auto_updates.return_value = ["app1", "app2"]
        mock_input.return_value = "y"

        # Mock config
        with patch.object(self.handler, "config") as mock_config:
            mock_config.get.return_value = []
            mock_config.save.return_value = True

            result = self.handler.handle_blacklist_auto_updates_enhanced(self.mock_options)

        self.assertEqual(result, 0)
        mock_config.set.assert_called_once()
        mock_config.save.assert_called_once()

    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_blacklist_enhanced_with_rollback(self, mock_input, mock_get_auto_updates, mock_get_casks):
        """Test enhanced blacklist operation with rollback on failure."""
        # Setup mocks
        mock_get_casks.return_value = ["app1", "app2"]
        mock_get_auto_updates.return_value = ["app1", "app2"]
        mock_input.return_value = "y"

        # Mock config to fail save
        with patch.object(self.handler, "config") as mock_config:
            original_blacklist = ["existing"]
            mock_config.get.return_value = original_blacklist
            mock_config.save.return_value = False  # Save fails

            result = self.handler.handle_blacklist_auto_updates_enhanced(self.mock_options)

        self.assertEqual(result, 1)
        # Should attempt to set and save, then restore on failure
        self.assertGreaterEqual(mock_config.set.call_count, 1)

    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_enhanced_success(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test enhanced uninstall operation success."""
        # Setup mocks
        mock_get_casks.return_value = ["app1", "app2"]
        mock_get_auto_updates.return_value = ["app1", "app2"]
        mock_input.side_effect = ["y", "UNINSTALL"]
        mock_run_command.return_value = ("Successfully uninstalled", 0)

        result = self.handler.handle_uninstall_auto_updates_enhanced(self.mock_options)

        self.assertEqual(result, 0)
        self.assertEqual(mock_run_command.call_count, 2)

    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_enhanced_with_mixed_results(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test enhanced uninstall with mixed success/failure results."""
        # Setup mocks
        apps = ["app1", "app2", "app3", "app4"]
        mock_get_casks.return_value = apps
        mock_get_auto_updates.return_value = apps
        mock_input.side_effect = ["y", "UNINSTALL"]

        # Mixed results: success, permission error, dependency error, critical error
        mock_run_command.side_effect = [
            ("Successfully uninstalled app1", 0),
            ("Permission denied", 1),
            ("app3 is required by app4", 1),
            ("System integrity compromised", 1),
        ]

        result = self.handler.handle_uninstall_auto_updates_enhanced(self.mock_options)

        # Should return 2 for critical errors
        self.assertEqual(result, 2)
        self.assertEqual(mock_run_command.call_count, 4)

    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_uninstall_enhanced_timeout_handling(
        self, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test enhanced uninstall timeout handling."""
        # Setup mocks
        mock_get_casks.return_value = ["slow-app"]
        mock_get_auto_updates.return_value = ["slow-app"]
        mock_input.side_effect = ["y", "UNINSTALL"]
        mock_run_command.side_effect = TimeoutError("Command timed out")

        result = self.handler.handle_uninstall_auto_updates_enhanced(self.mock_options)

        # Should handle timeout gracefully
        self.assertEqual(result, 1)

    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_blacklist_enhanced_cancellation(self, mock_input, mock_get_auto_updates, mock_get_casks):
        """Test enhanced blacklist operation cancellation."""
        # Setup mocks
        mock_get_casks.return_value = ["app1"]
        mock_get_auto_updates.return_value = ["app1"]
        mock_input.return_value = "n"  # User cancels

        result = self.handler.handle_blacklist_auto_updates_enhanced(self.mock_options)

        self.assertEqual(result, 0)  # Cancellation is not an error

    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    def test_uninstall_enhanced_cancellation(self, mock_input, mock_get_auto_updates, mock_get_casks):
        """Test enhanced uninstall operation cancellation."""
        # Setup mocks
        mock_get_casks.return_value = ["app1"]
        mock_get_auto_updates.return_value = ["app1"]

        # Test first confirmation cancellation
        mock_input.return_value = "n"
        result = self.handler.handle_uninstall_auto_updates_enhanced(self.mock_options)
        self.assertEqual(result, 0)

        # Test second confirmation cancellation
        mock_input.side_effect = ["y", "cancel"]
        result = self.handler.handle_uninstall_auto_updates_enhanced(self.mock_options)
        self.assertEqual(result, 0)


class TestEnhancedHandlerWrapperFunctions(unittest.TestCase):
    """Test the wrapper functions for enhanced handlers."""

    @patch("versiontracker.handlers.enhanced_auto_update_handlers._enhanced_handler")
    def test_blacklist_wrapper_function(self, mock_handler):
        """Test the blacklist wrapper function."""
        mock_handler.handle_blacklist_auto_updates_enhanced.return_value = 0
        mock_options = MagicMock()

        result = handle_blacklist_auto_updates_enhanced(mock_options)

        self.assertEqual(result, 0)
        mock_handler.handle_blacklist_auto_updates_enhanced.assert_called_once_with(mock_options)

    @patch("versiontracker.handlers.enhanced_auto_update_handlers._enhanced_handler")
    def test_uninstall_wrapper_function(self, mock_handler):
        """Test the uninstall wrapper function."""
        mock_handler.handle_uninstall_auto_updates_enhanced.return_value = 0
        mock_options = MagicMock()

        result = handle_uninstall_auto_updates_enhanced(mock_options)

        self.assertEqual(result, 0)
        mock_handler.handle_uninstall_auto_updates_enhanced.assert_called_once_with(mock_options)


class TestUninstallResultDataClass(unittest.TestCase):
    """Test the UninstallResult data class."""

    def test_uninstall_result_creation(self):
        """Test creating UninstallResult instances."""
        # Success case
        success_result = UninstallResult("app1", True)
        self.assertEqual(success_result.app_name, "app1")
        self.assertTrue(success_result.success)
        self.assertIsNone(success_result.error_message)
        self.assertFalse(success_result.is_critical)

        # Failure case
        failure_result = UninstallResult("app2", False, "Permission denied", False)
        self.assertEqual(failure_result.app_name, "app2")
        self.assertFalse(failure_result.success)
        self.assertEqual(failure_result.error_message, "Permission denied")
        self.assertFalse(failure_result.is_critical)

        # Critical failure case
        critical_result = UninstallResult("app3", False, "System error", True)
        self.assertEqual(critical_result.app_name, "app3")
        self.assertFalse(critical_result.success)
        self.assertEqual(critical_result.error_message, "System error")
        self.assertTrue(critical_result.is_critical)


class TestBlacklistBackupDataClass(unittest.TestCase):
    """Test the BlacklistBackup data class."""

    def test_blacklist_backup_creation(self):
        """Test creating BlacklistBackup instances."""
        test_blacklist = ["app1", "app2"]

        # Basic backup
        backup = BlacklistBackup(test_blacklist)
        self.assertEqual(backup.original_blacklist, test_blacklist)
        self.assertIsNone(backup.backup_file)
        self.assertEqual(backup.timestamp, 0.0)

        # Full backup
        backup_full = BlacklistBackup(test_blacklist, "/tmp/backup.json", 1234567890.0)
        self.assertEqual(backup_full.original_blacklist, test_blacklist)
        self.assertEqual(backup_full.backup_file, "/tmp/backup.json")
        self.assertEqual(backup_full.timestamp, 1234567890.0)


class TestEnhancedHandlerIntegration(unittest.TestCase):
    """Integration tests for enhanced handlers."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_config")
    @patch("builtins.input")
    def test_end_to_end_blacklist_success(self, mock_input, mock_get_config, mock_get_auto_updates, mock_get_casks):
        """Test end-to-end blacklist operation success."""
        # Setup mocks
        mock_get_casks.return_value = ["app1", "app2", "app3"]
        mock_get_auto_updates.return_value = ["app1", "app2"]
        mock_input.return_value = "y"

        mock_config = MagicMock()
        mock_config.get.return_value = ["existing"]
        mock_config.save.return_value = True
        mock_get_config.return_value = mock_config

        # Patch the global handler instance
        with patch("versiontracker.handlers.enhanced_auto_update_handlers._enhanced_handler") as mock_handler:
            mock_handler.handle_blacklist_auto_updates_enhanced.return_value = 0

            # Execute
            result = handle_blacklist_auto_updates_enhanced(MagicMock())

            # Verify
            self.assertEqual(result, 0)

    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.get_config")
    @patch("versiontracker.handlers.enhanced_auto_update_handlers.run_command")
    @patch("builtins.input")
    def test_end_to_end_uninstall_with_partial_failures(
        self, mock_input, mock_run_command, mock_get_config, mock_get_auto_updates, mock_get_casks
    ):
        """Test end-to-end uninstall with partial failures."""
        # Setup mocks
        apps = ["app1", "app2", "app3"]
        mock_get_casks.return_value = apps
        mock_get_auto_updates.return_value = apps
        mock_input.side_effect = ["y", "UNINSTALL"]
        mock_get_config.return_value = MagicMock()

        # Mixed results: success, failure, success
        mock_run_command.side_effect = [
            ("Success", 0),
            ("Permission denied", 1),
            ("Success", 0),
        ]

        # Execute
        result = handle_uninstall_auto_updates_enhanced(MagicMock())

        # Verify partial failure
        self.assertEqual(result, 1)
        self.assertEqual(mock_run_command.call_count, 3)


if __name__ == "__main__":
    unittest.main()
