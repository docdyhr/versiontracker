"""Test cases for auto-updates functionality."""

import unittest
from unittest.mock import MagicMock, patch

from versiontracker.homebrew import get_casks_with_auto_updates, has_auto_updates


class TestAutoUpdates(unittest.TestCase):
    """Test cases for auto-updates detection in Homebrew casks."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_cask_with_auto_updates = {
            "token": "visual-studio-code",
            "version": "1.85.0",
            "auto_updates": True,
            "caveats": None,
        }

        self.test_cask_with_auto_updates_in_caveats = {
            "token": "slack",
            "version": "4.36.134",
            "auto_updates": False,
            "caveats": "slack will automatically update itself.",
        }

        self.test_cask_without_auto_updates = {
            "token": "firefox",
            "version": "120.0.1",
            "auto_updates": False,
            "caveats": "Firefox requires manual updates through the app.",
        }

        self.test_cask_with_sparkle = {
            "token": "iterm2",
            "version": "3.4.23",
            "auto_updates": False,
            "caveats": "iterm2 uses Sparkle for updates.",
        }

    @patch("versiontracker.homebrew.get_cask_info")
    def test_has_auto_updates_true_field(self, mock_get_cask_info):
        """Test detection when auto_updates field is True."""
        mock_get_cask_info.return_value = self.test_cask_with_auto_updates

        result = has_auto_updates("visual-studio-code")

        self.assertTrue(result)
        mock_get_cask_info.assert_called_once_with("visual-studio-code")

    @patch("versiontracker.homebrew.get_cask_info")
    def test_has_auto_updates_in_caveats(self, mock_get_cask_info):
        """Test detection when auto-updates mentioned in caveats."""
        mock_get_cask_info.return_value = self.test_cask_with_auto_updates_in_caveats

        result = has_auto_updates("slack")

        self.assertTrue(result)
        mock_get_cask_info.assert_called_once_with("slack")

    @patch("versiontracker.homebrew.get_cask_info")
    def test_has_auto_updates_sparkle(self, mock_get_cask_info):
        """Test detection when Sparkle is mentioned (common auto-update framework)."""
        mock_get_cask_info.return_value = self.test_cask_with_sparkle

        result = has_auto_updates("iterm2")

        self.assertTrue(result)
        mock_get_cask_info.assert_called_once_with("iterm2")

    @patch("versiontracker.homebrew.get_cask_info")
    def test_has_auto_updates_false(self, mock_get_cask_info):
        """Test when cask doesn't have auto-updates."""
        mock_get_cask_info.return_value = self.test_cask_without_auto_updates

        result = has_auto_updates("firefox")

        self.assertFalse(result)
        mock_get_cask_info.assert_called_once_with("firefox")

    @patch("versiontracker.homebrew.get_cask_info")
    def test_has_auto_updates_error_handling(self, mock_get_cask_info):
        """Test error handling returns False."""
        mock_get_cask_info.side_effect = Exception("Network error")

        result = has_auto_updates("some-cask")

        self.assertFalse(result)

    @patch("versiontracker.homebrew.has_auto_updates")
    def test_get_casks_with_auto_updates(self, mock_has_auto_updates):
        """Test getting list of casks with auto-updates."""
        test_casks = ["visual-studio-code", "slack", "firefox", "iterm2"]
        # Mock that first two have auto-updates
        mock_has_auto_updates.side_effect = [True, True, False, True]

        result = get_casks_with_auto_updates(test_casks)

        self.assertEqual(result, ["visual-studio-code", "slack", "iterm2"])
        self.assertEqual(mock_has_auto_updates.call_count, 4)

    @patch("versiontracker.homebrew.has_auto_updates")
    def test_get_casks_with_auto_updates_empty_list(self, mock_has_auto_updates):
        """Test with empty list."""
        result = get_casks_with_auto_updates([])

        self.assertEqual(result, [])
        mock_has_auto_updates.assert_not_called()

    @patch("versiontracker.homebrew.get_cask_info")
    def test_various_auto_update_patterns(self, mock_get_cask_info):
        """Test various patterns that indicate auto-updates."""
        test_cases = [
            ("automatically update", True),
            ("self-update", True),
            ("self update", True),
            ("auto-update", True),
            ("auto update", True),
            ("update automatically", True),
            ("sparkle framework", True),
            ("manual updates only", False),
            ("", False),
            (None, False),
        ]

        for caveats_text, expected in test_cases:
            with self.subTest(caveats=caveats_text):
                mock_get_cask_info.return_value = {
                    "token": "test-cask",
                    "auto_updates": False,
                    "caveats": caveats_text,
                }

                result = has_auto_updates("test-cask")
                self.assertEqual(result, expected, f"Failed for caveats: {caveats_text}")


class TestAutoUpdatesIntegration(unittest.TestCase):
    """Integration tests for auto-updates functionality with handlers."""

    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.brew_handlers.get_casks_with_auto_updates")
    def test_list_brews_with_exclude_auto_updates(self, mock_get_auto_updates, mock_get_casks):
        """Test list brews command with exclude auto-updates flag."""
        from versiontracker.handlers.brew_handlers import handle_list_brews

        mock_get_casks.return_value = ["visual-studio-code", "slack", "firefox", "iterm2"]
        mock_get_auto_updates.return_value = ["visual-studio-code", "slack"]

        options = MagicMock()
        options.exclude_auto_updates = True
        options.only_auto_updates = False
        options.export_format = None
        options.output_file = None

        with patch("builtins.print"):
            result = handle_list_brews(options)

        self.assertEqual(result, 0)
        mock_get_auto_updates.assert_called_once()

    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.brew_handlers.get_casks_with_auto_updates")
    def test_list_brews_with_only_auto_updates(self, mock_get_auto_updates, mock_get_casks):
        """Test list brews command with only auto-updates flag."""
        from versiontracker.handlers.brew_handlers import handle_list_brews

        mock_get_casks.return_value = ["visual-studio-code", "slack", "firefox", "iterm2"]
        mock_get_auto_updates.return_value = ["visual-studio-code", "slack"]

        options = MagicMock()
        options.exclude_auto_updates = False
        options.only_auto_updates = True
        options.export_format = None
        options.output_file = None

        with patch("builtins.print"):
            result = handle_list_brews(options)

        self.assertEqual(result, 0)
        mock_get_auto_updates.assert_called_once()


class TestAutoUpdatesEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions for auto-updates functionality."""

    @patch("versiontracker.homebrew.get_cask_info")
    def test_has_auto_updates_with_none_caveats(self, mock_get_cask_info):
        """Test when caveats field is None."""
        mock_get_cask_info.return_value = {
            "token": "test-app",
            "auto_updates": False,
            "caveats": None,
        }

        result = has_auto_updates("test-app")
        self.assertFalse(result)

    @patch("versiontracker.homebrew.get_cask_info")
    def test_has_auto_updates_with_dict_caveats(self, mock_get_cask_info):
        """Test when caveats field is not a string (dict)."""
        mock_get_cask_info.return_value = {
            "token": "test-app",
            "auto_updates": False,
            "caveats": {"warning": "some warning"},
        }

        result = has_auto_updates("test-app")
        self.assertFalse(result)

    @patch("versiontracker.homebrew.get_cask_info")
    def test_has_auto_updates_missing_fields(self, mock_get_cask_info):
        """Test when cask info is missing expected fields."""
        mock_get_cask_info.return_value = {
            "token": "test-app",
            # Missing auto_updates and caveats fields
        }

        result = has_auto_updates("test-app")
        self.assertFalse(result)

    @patch("versiontracker.homebrew.get_cask_info")
    def test_has_auto_updates_case_insensitive(self, mock_get_cask_info):
        """Test that auto-update detection is case insensitive."""
        test_cases = [
            "App will AUTO-UPDATE itself",
            "Uses SPARKLE framework",
            "Automatically Updates",
            "SELF-UPDATE enabled",
        ]

        for caveats in test_cases:
            with self.subTest(caveats=caveats):
                mock_get_cask_info.return_value = {
                    "token": "test-app",
                    "auto_updates": False,
                    "caveats": caveats,
                }
                result = has_auto_updates("test-app")
                self.assertTrue(result, f"Failed to detect auto-updates in: {caveats}")

    @patch("versiontracker.homebrew.get_cask_info")
    def test_has_auto_updates_empty_cask_info(self, mock_get_cask_info):
        """Test with empty cask info dict."""
        mock_get_cask_info.return_value = {}
        result = has_auto_updates("test-app")
        self.assertFalse(result)

    @patch("versiontracker.homebrew.has_auto_updates")
    def test_get_casks_with_auto_updates_mixed_results(self, mock_has_auto_updates):
        """Test with mixed auto-update results and errors."""
        test_casks = ["app1", "app2", "app3", "app4", "app5"]
        # app1: True, app2: False, app3: True, app4: Error (returns False), app5: True
        mock_has_auto_updates.side_effect = [True, False, True, False, True]

        result = get_casks_with_auto_updates(test_casks)

        self.assertEqual(result, ["app1", "app3", "app5"])
        self.assertEqual(mock_has_auto_updates.call_count, 5)


class TestAutoUpdatesBrewHandlerIntegration(unittest.TestCase):
    """Integration tests for auto-updates with brew handlers."""

    @patch("versiontracker.handlers.brew_handlers.check_brew_install_candidates")
    @patch("versiontracker.handlers.brew_handlers.filter_out_brews")
    @patch("versiontracker.handlers.brew_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.brew_handlers.get_applications")
    @patch("versiontracker.handlers.brew_handlers.get_json_data")
    def test_brew_recommendations_with_exclude_auto_updates(
        self,
        mock_get_json_data,
        mock_get_applications,
        mock_get_homebrew_casks,
        mock_get_auto_updates,
        mock_filter_out_brews,
        mock_check_candidates,
    ):
        """Test brew recommendations with exclude auto-updates flag."""
        from versiontracker.handlers.brew_handlers import handle_brew_recommendations

        # Setup mocks
        mock_get_json_data.return_value = {}
        mock_get_applications.return_value = [("App1", "1.0"), ("App2", "2.0")]
        mock_get_homebrew_casks.return_value = []
        mock_filter_out_brews.return_value = [("App1", "1.0"), ("App2", "2.0")]
        mock_check_candidates.return_value = [("App1", "1.0", True), ("App2", "2.0", True)]
        mock_get_auto_updates.return_value = ["App1"]

        options = MagicMock()
        options.exclude_auto_updates = True
        options.rate_limit = 1
        options.debug = False
        options.export_format = None

        with patch("builtins.print"):
            result = handle_brew_recommendations(options)

        self.assertEqual(result, 0)
        mock_get_auto_updates.assert_called_once()

    @patch("versiontracker.handlers.brew_handlers.check_brew_install_candidates")
    @patch("versiontracker.handlers.brew_handlers.filter_out_brews")
    @patch("versiontracker.handlers.brew_handlers.get_casks_with_auto_updates")
    @patch("versiontracker.handlers.brew_handlers.get_homebrew_casks")
    @patch("versiontracker.handlers.brew_handlers.get_applications")
    @patch("versiontracker.handlers.brew_handlers.get_json_data")
    def test_brew_recommendations_with_only_auto_updates(
        self,
        mock_get_json_data,
        mock_get_applications,
        mock_get_homebrew_casks,
        mock_get_auto_updates,
        mock_filter_out_brews,
        mock_check_candidates,
    ):
        """Test brew recommendations with only auto-updates flag."""
        from versiontracker.handlers.brew_handlers import handle_brew_recommendations

        # Setup mocks
        mock_get_json_data.return_value = {}
        mock_get_applications.return_value = [("App1", "1.0"), ("App2", "2.0"), ("App3", "3.0")]
        mock_get_homebrew_casks.return_value = []
        mock_filter_out_brews.return_value = [("App1", "1.0"), ("App2", "2.0"), ("App3", "3.0")]
        mock_check_candidates.return_value = [
            ("App1", "1.0", True),
            ("App2", "2.0", True),
            ("App3", "3.0", True),
        ]
        mock_get_auto_updates.return_value = ["App2", "App3"]

        options = MagicMock()
        options.only_auto_updates = True
        options.rate_limit = 1
        options.debug = False
        options.export_format = None

        with patch("builtins.print"):
            result = handle_brew_recommendations(options)

        self.assertEqual(result, 0)
        mock_get_auto_updates.assert_called_once()


class TestAutoUpdatesPerformance(unittest.TestCase):
    """Performance tests for auto-updates functionality."""

    @patch("versiontracker.homebrew.get_cask_info")
    def test_has_auto_updates_performance_with_large_caveats(self, mock_get_cask_info):
        """Test performance with very large caveats text."""
        large_text = "This is a very long caveat text. " * 1000
        large_text += "This app uses sparkle for updates."

        mock_get_cask_info.return_value = {
            "token": "test-app",
            "auto_updates": False,
            "caveats": large_text,
        }

        import time

        start_time = time.time()
        result = has_auto_updates("test-app")
        end_time = time.time()

        self.assertTrue(result)
        # Should complete in less than 0.1 seconds even with large text
        self.assertLess(end_time - start_time, 0.1)

    @patch("versiontracker.homebrew.has_auto_updates")
    def test_get_casks_with_auto_updates_performance(self, mock_has_auto_updates):
        """Test performance with large number of casks."""
        # Test with 1000 casks
        test_casks = [f"app{i}" for i in range(1000)]
        # Every third app has auto-updates
        mock_has_auto_updates.side_effect = [(i % 3 == 0) for i in range(1000)]

        import time

        start_time = time.time()
        result = get_casks_with_auto_updates(test_casks)
        end_time = time.time()

        # Should have ~333 apps with auto-updates
        self.assertEqual(len(result), 334)  # 0, 3, 6, ... 999
        # Should complete in reasonable time
        self.assertLess(end_time - start_time, 1.0)


if __name__ == "__main__":
    unittest.main()
