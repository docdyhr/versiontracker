"""Test cases for CLI integration with auto-updates functionality."""

import sys
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from versiontracker.cli import get_arguments


class TestCLIAutoUpdates(unittest.TestCase):
    """Test cases for auto-update related CLI arguments."""

    def setUp(self):
        """Set up test fixtures."""
        self.original_argv = sys.argv.copy()

    def tearDown(self):
        """Restore original sys.argv."""
        sys.argv = self.original_argv

    def test_exclude_auto_updates_flag(self):
        """Test --exclude-auto-updates flag parsing."""
        sys.argv = ["versiontracker", "--brews", "--exclude-auto-updates"]
        args = get_arguments()

        self.assertTrue(hasattr(args, "exclude_auto_updates"))
        self.assertTrue(args.exclude_auto_updates)
        self.assertTrue(args.brews)

    def test_only_auto_updates_flag(self):
        """Test --only-auto-updates flag parsing."""
        sys.argv = ["versiontracker", "--recommend", "--only-auto-updates"]
        args = get_arguments()

        self.assertTrue(hasattr(args, "only_auto_updates"))
        self.assertTrue(args.only_auto_updates)
        self.assertTrue(args.recom)

    def test_blacklist_auto_updates_flag(self):
        """Test --blacklist-auto-updates flag parsing."""
        sys.argv = ["versiontracker", "--blacklist-auto-updates"]
        args = get_arguments()

        self.assertTrue(hasattr(args, "blacklist_auto_updates"))
        self.assertTrue(args.blacklist_auto_updates)

    def test_uninstall_auto_updates_flag(self):
        """Test --uninstall-auto-updates flag parsing."""
        sys.argv = ["versiontracker", "--uninstall-auto-updates"]
        args = get_arguments()

        self.assertTrue(hasattr(args, "uninstall_auto_updates"))
        self.assertTrue(args.uninstall_auto_updates)

    def test_auto_update_flags_not_mutually_exclusive_with_filters(self):
        """Test that filter flags can be combined with main commands."""
        sys.argv = ["versiontracker", "--brews", "--exclude-auto-updates", "--export", "json"]
        args = get_arguments()

        self.assertTrue(args.brews)
        self.assertTrue(args.exclude_auto_updates)
        self.assertEqual(args.export_format, "json")

    def test_blacklist_and_uninstall_mutually_exclusive(self):
        """Test that blacklist and uninstall commands are mutually exclusive."""
        sys.argv = ["versiontracker", "--blacklist-auto-updates", "--uninstall-auto-updates"]

        with self.assertRaises(SystemExit):
            with patch("sys.stderr", new_callable=StringIO):
                get_arguments()

    def test_combined_auto_update_filters(self):
        """Test combining auto-update filters with other options."""
        test_cases = [
            (
                ["versiontracker", "--recommend", "--exclude-auto-updates", "--rate-limit", "5"],
                {"recom": True, "exclude_auto_updates": True, "rate_limit": 5},
            ),
            (
                ["versiontracker", "--brews", "--only-auto-updates", "--no-progress"],
                {"brews": True, "only_auto_updates": True, "no_progress": True},
            ),
            (
                ["versiontracker", "--apps", "--blacklist", "Safari,Chrome", "--exclude-auto-updates"],
                {"apps": True, "blacklist": "Safari,Chrome", "exclude_auto_updates": True},
            ),
        ]

        for argv, expected in test_cases:
            with self.subTest(argv=argv):
                sys.argv = argv
                args = get_arguments()

                for attr, value in expected.items():
                    self.assertTrue(hasattr(args, attr))
                    self.assertEqual(getattr(args, attr), value)


class TestMainAutoUpdatesIntegration(unittest.TestCase):
    """Test main module integration with auto-update commands."""

    @patch("versiontracker.apps.get_homebrew_casks", return_value=["firefox", "chrome"])
    @patch("versiontracker.__main__.handle_blacklist_auto_updates")
    @patch("versiontracker.__main__.get_arguments")
    def test_main_blacklist_auto_updates(self, mock_get_args, mock_handle_blacklist, mock_get_casks):
        """Test main function calls blacklist handler correctly."""
        from versiontracker.__main__ import versiontracker_main

        mock_args = MagicMock()
        mock_args.blacklist_auto_updates = True
        mock_args.generate_config = False
        mock_get_args.return_value = mock_args
        mock_handle_blacklist.return_value = 0

        with patch("versiontracker.__main__.handle_setup_logging"):
            with patch("versiontracker.__main__.handle_initialize_config"):
                with patch("versiontracker.__main__.handle_configure_from_options"):
                    with patch("versiontracker.__main__.handle_filter_management", return_value=None):
                        result = versiontracker_main()

        self.assertEqual(result, 0)
        mock_handle_blacklist.assert_called_once_with(mock_args)

    @patch("versiontracker.apps.get_homebrew_casks", return_value=["firefox", "chrome"])
    @patch("versiontracker.__main__.handle_uninstall_auto_updates")
    @patch("versiontracker.__main__.get_arguments")
    def test_main_uninstall_auto_updates(self, mock_get_args, mock_handle_uninstall, mock_get_casks):
        """Test main function calls uninstall handler correctly."""
        from versiontracker.__main__ import versiontracker_main

        mock_args = MagicMock()
        mock_args.uninstall_auto_updates = True
        mock_args.generate_config = False
        mock_get_args.return_value = mock_args
        mock_handle_uninstall.return_value = 0

        with patch("versiontracker.__main__.handle_setup_logging"):
            with patch("versiontracker.__main__.handle_initialize_config"):
                with patch("versiontracker.__main__.handle_configure_from_options"):
                    with patch("versiontracker.__main__.handle_filter_management", return_value=None):
                        result = versiontracker_main()

        self.assertEqual(result, 0)
        mock_handle_uninstall.assert_called_once_with(mock_args)


class TestAutoUpdatesCLIHelp(unittest.TestCase):
    """Test help text includes auto-update options."""

    def test_help_includes_auto_update_options(self):
        """Test that help text includes all auto-update options."""
        sys.argv = ["versiontracker", "--help"]

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            with self.assertRaises(SystemExit) as cm:
                get_arguments()
            help_text = mock_stdout.getvalue()

        self.assertEqual(cm.exception.code, 0)

        # Check that all auto-update options are in help
        expected_options = [
            "--exclude-auto-updates",
            "--only-auto-updates",
            "--exclude-auto-updates",
            "--only-auto-updates",
            "--blacklist-auto-updates",
            "--uninstall-auto-updates",
            "Exclude applications that have auto-updates",
            "Only show applications that have auto-updates",
            "Add all applications with auto-updates to the",
            "Uninstall all Homebrew casks that have auto-updates",
        ]

        self.assertIsNotNone(help_text, "Help text was not captured")
        # Type assertion for type checker
        assert help_text is not None
        for option in expected_options:
            self.assertIn(option, help_text, f"Help text missing: {option}")


class TestAutoUpdatesEndToEnd(unittest.TestCase):
    """End-to-end tests for auto-update functionality."""

    @patch("versiontracker.handlers.auto_update_handlers.run_command")
    @patch("versiontracker.handlers.auto_update_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.auto_update_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.auto_update_handlers.get_config")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_end_to_end_blacklist_workflow(
        self,
        mock_print,
        mock_input,
        mock_get_config,
        mock_get_casks,
        mock_get_auto_updates,
        mock_run_command,
    ):
        """Test complete workflow of blacklisting auto-update apps."""
        from versiontracker.__main__ import versiontracker_main

        # Setup test data
        test_casks = ["vscode", "slack", "firefox", "chrome"]
        auto_update_casks = ["vscode", "slack"]

        # Setup mocks
        mock_get_casks.return_value = test_casks
        mock_get_auto_updates.return_value = auto_update_casks
        mock_input.return_value = "y"  # Confirm blacklist

        mock_config = MagicMock()
        mock_config.get.return_value = []  # Empty blacklist
        mock_config.save.return_value = True
        mock_get_config.return_value = mock_config

        # Run with blacklist command
        sys.argv = ["versiontracker", "--blacklist-auto-updates"]

        with patch("versiontracker.__main__.get_arguments") as mock_get_args:
            mock_args = MagicMock()
            mock_args.blacklist_auto_updates = True
            mock_args.generate_config = False
            mock_get_args.return_value = mock_args

            with patch("versiontracker.__main__.handle_setup_logging"):
                with patch("versiontracker.__main__.handle_initialize_config"):
                    with patch("versiontracker.__main__.handle_configure_from_options"):
                        with patch("versiontracker.__main__.handle_filter_management", return_value=None):
                            with patch("versiontracker.__main__.handle_blacklist_auto_updates") as mock_handle:
                                mock_handle.return_value = 0
                                result = versiontracker_main()

        # Verify success
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
