"""Tests for the CLI module."""

import unittest
from unittest.mock import patch

from versiontracker.cli import get_arguments


class TestCLI(unittest.TestCase):
    """Test cases for the CLI module."""

    def test_default_args(self):
        """Test default command-line arguments."""
        with patch(
            "sys.argv", ["versiontracker", "--apps"]
        ):  # Need at least one arg to avoid printing help
            args = get_arguments()
            self.assertTrue(args.apps)
            self.assertFalse(args.brews)
            self.assertFalse(args.recom)
            self.assertFalse(args.debug)
            self.assertEqual(args.rate_limit, None)
            self.assertEqual(args.max_workers, None)
            self.assertFalse(args.no_progress)
            self.assertEqual(args.blacklist, None)
            self.assertEqual(args.additional_dirs, None)
            self.assertEqual(args.similarity, None)

    def test_apps_flag(self):
        """Test --apps flag."""
        with patch("sys.argv", ["versiontracker", "--apps"]):
            args = get_arguments()
            self.assertTrue(args.apps)
            self.assertFalse(args.brews)
            self.assertFalse(args.recom)

    def test_brews_flag(self):
        """Test --brews flag."""
        with patch("sys.argv", ["versiontracker", "--brews"]):
            args = get_arguments()
            self.assertFalse(args.apps)
            self.assertTrue(args.brews)
            self.assertFalse(args.recom)

    def test_recommend_flag(self):
        """Test the --recommend flag."""
        with patch("sys.argv", ["versiontracker", "--recommend"]):
            args = get_arguments()
            self.assertTrue(args.recom)
            self.assertFalse(args.apps)
            self.assertFalse(args.brews)
            self.assertFalse(hasattr(args, "strict_recom") and args.strict_recom)

    def test_strict_recommend_flag(self):
        """Test the --strict-recommend flag."""
        with patch("sys.argv", ["versiontracker", "--strict-recommend"]):
            args = get_arguments()
            self.assertTrue(args.strict_recom)
            self.assertFalse(args.apps)
            self.assertFalse(args.brews)
            self.assertFalse(args.recom)

    def test_debug_option(self):
        """Test --debug option."""
        with patch("sys.argv", ["versiontracker", "--apps", "--debug"]):
            args = get_arguments()
            self.assertTrue(args.debug)

    def test_rate_limit_option(self):
        """Test --rate-limit option."""
        with patch("sys.argv", ["versiontracker", "--apps", "--rate-limit", "2"]):
            args = get_arguments()
            self.assertEqual(args.rate_limit, 2)

    def test_max_workers_option(self):
        """Test --max-workers option."""
        with patch("sys.argv", ["versiontracker", "--apps", "--max-workers", "8"]):
            args = get_arguments()
            self.assertEqual(args.max_workers, 8)

    def test_no_progress_flag(self):
        """Test --no-progress flag."""
        with patch("sys.argv", ["versiontracker", "--apps", "--no-progress"]):
            args = get_arguments()
            self.assertTrue(args.no_progress)

    def test_blacklist_option(self):
        """Test --blacklist option."""
        with patch("sys.argv", ["versiontracker", "--apps", "--blacklist", "Firefox,Chrome"]):
            args = get_arguments()
            self.assertEqual(args.blacklist, "Firefox,Chrome")

    def test_additional_dirs_option(self):
        """Test --additional-dirs option."""
        with patch(
            "sys.argv",
            ["versiontracker", "--apps", "--additional-dirs", "/path1:/path2"],
        ):
            args = get_arguments()
            self.assertEqual(args.additional_dirs, "/path1:/path2")

    def test_similarity_option(self):
        """Test --similarity option."""
        with patch("sys.argv", ["versiontracker", "--apps", "--similarity", "80"]):
            args = get_arguments()
            self.assertEqual(args.similarity, 80)

    def test_combined_options(self):
        """Test combining multiple options."""
        with patch(
            "sys.argv",
            [
                "versiontracker",
                "--recommend",
                "--max-workers",
                "8",
                "--rate-limit",
                "2",
                "--blacklist",
                "Firefox,Chrome",
                "--additional-dirs",
                "/path1:/path2",
                "--similarity",
                "80",
                "--no-progress",
            ],
        ):
            args = get_arguments()
            self.assertTrue(args.recom)
            self.assertEqual(args.max_workers, 8)
            self.assertEqual(args.rate_limit, 2)
            self.assertEqual(args.blacklist, "Firefox,Chrome")
            self.assertEqual(args.additional_dirs, "/path1:/path2")
            self.assertEqual(args.similarity, 80)
            self.assertTrue(args.no_progress)


if __name__ == "__main__":
    unittest.main()
