"""Test cases for auto-update management handlers."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from versiontracker.handlers.auto_update_handlers import (
    handle_blacklist_auto_updates,
    handle_list_auto_updates,
    handle_uninstall_auto_updates,
)


class TestAutoUpdateHandlers(unittest.TestCase):
    """Test cases for auto-update management handler functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_options = MagicMock()
        self.test_casks = ["visual-studio-code", "slack", "firefox", "iterm2"]
        self.auto_update_casks = ["visual-studio-code", "slack"]

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_blacklist_auto_updates_success(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test successful blacklisting of auto-update casks."""
        # Setup mocks
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_input.return_value = "y"

        mock_config = MagicMock()
        mock_config.get.return_value = ["firefox"]  # Existing blacklist
        mock_config.save.return_value = True
        mock_get_config.return_value = mock_config

        # Execute
        result = handle_blacklist_auto_updates(self.mock_options)

        # Verify
        self.assertEqual(result, 0)
        mock_get_casks.assert_called_once()
        mock_get_auto_updates.assert_called_once_with(self.test_casks)

        # Verify that set was called with the updated blacklist
        mock_config.set.assert_called_once_with("blacklist", ["firefox", "visual-studio-code", "slack"])
        mock_config.save.assert_called_once()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_blacklist_auto_updates_cancelled(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test cancelling blacklist operation."""
        # Setup mocks
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_input.return_value = "n"  # User cancels

        mock_config = MagicMock()
        mock_config.get.return_value = []
        mock_get_config.return_value = mock_config

        # Execute
        result = handle_blacklist_auto_updates(self.mock_options)

        # Verify
        self.assertEqual(result, 0)
        mock_config.set.assert_not_called()
        mock_config.save.assert_not_called()

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_auto_updates_success(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test successful uninstallation of auto-update casks."""
        # Setup mocks
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_input.side_effect = ["y", "UNINSTALL"]  # User confirms twice
        mock_run_command.return_value = ("Success", 0)  # Successful uninstall

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Verify
        self.assertEqual(result, 0)
        self.assertEqual(mock_run_command.call_count, 2)  # Two casks uninstalled

        # Verify the correct brew commands were called
        expected_calls = [
            call("brew uninstall --cask visual-studio-code", timeout=60),
            call("brew uninstall --cask slack", timeout=60),
        ]
        mock_run_command.assert_has_calls(expected_calls)

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_auto_updates_cancelled_first_prompt(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks
    ):
        """Test cancelling uninstall at first confirmation."""
        # Setup mocks
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_input.return_value = "n"  # User cancels at first prompt

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Verify
        self.assertEqual(result, 0)
        # Verify that only one input was requested
        mock_input.assert_called_once()

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_auto_updates_cancelled_second_prompt(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks
    ):
        """Test cancelling uninstall at second confirmation."""
        # Setup mocks
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_input.side_effect = ["y", "cancel"]  # User cancels at second prompt

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Verify
        self.assertEqual(result, 0)
        self.assertEqual(mock_input.call_count, 2)

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_uninstall_auto_updates_partial_failure(
        self, mock_print, mock_input, mock_run_command, mock_get_auto_updates, mock_get_casks
    ):
        """Test partial failure during uninstallation."""
        # Setup mocks
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks
        mock_input.side_effect = ["y", "UNINSTALL"]
        # First uninstall succeeds, second fails
        mock_run_command.side_effect = [
            ("Success", 0),
            ("Error: Cask not installed", 1),
        ]

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Verify
        self.assertEqual(result, 1)  # Non-zero exit due to failure
        self.assertEqual(mock_run_command.call_count, 2)

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.print")
    def test_list_auto_updates(self, mock_print, mock_get_auto_updates, mock_get_casks, mock_get_config):
        """Test listing auto-update casks with blacklist info."""
        # Setup mocks
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks

        mock_config = MagicMock()
        mock_config.get.return_value = ["slack"]  # Slack is blacklisted
        mock_get_config.return_value = mock_config

        # Execute
        result = handle_list_auto_updates(self.mock_options)

        # Verify
        self.assertEqual(result, 0)
        mock_get_casks.assert_called_once()
        mock_get_auto_updates.assert_called_once_with(self.test_casks)

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("builtins.print")
    def test_no_homebrew_casks_found(self, mock_print, mock_get_casks):
        """Test when no Homebrew casks are found."""
        # Setup mocks
        mock_get_casks.return_value = []

        # Execute
        result = handle_blacklist_auto_updates(self.mock_options)

        # Verify
        self.assertEqual(result, 0)
        mock_get_casks.assert_called_once()

    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.print")
    def test_no_auto_update_casks_found(self, mock_print, mock_get_auto_updates, mock_get_casks):
        """Test when no casks with auto-updates are found."""
        # Setup mocks
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = []  # No auto-update casks

        # Execute
        result = handle_uninstall_auto_updates(self.mock_options)

        # Verify
        self.assertEqual(result, 0)
        mock_get_casks.assert_called_once()
        mock_get_auto_updates.assert_called_once()

    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_blacklist_all_already_blacklisted(
        self, mock_print, mock_input, mock_get_auto_updates, mock_get_casks, mock_get_config
    ):
        """Test when all auto-update casks are already blacklisted."""
        # Setup mocks
        mock_get_casks.return_value = self.test_casks
        mock_get_auto_updates.return_value = self.auto_update_casks

        mock_config = MagicMock()
        # All auto-update casks already in blacklist
        mock_config.get.return_value = ["visual-studio-code", "slack", "firefox"]
        mock_get_config.return_value = mock_config

        # Execute
        result = handle_blacklist_auto_updates(self.mock_options)

        # Verify
        self.assertEqual(result, 0)
        mock_config.set.assert_not_called()
        mock_config.save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
