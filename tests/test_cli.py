"""Tests for the CLI module."""

import unittest
from io import StringIO
from unittest.mock import patch

from versiontracker.cli import get_arguments


class TestCLI(unittest.TestCase):
    """Test cases for the CLI module."""

    def test_default_args(self):
        """Test default command-line arguments."""
        with patch("sys.argv", ["versiontracker", "--apps"]):  # Need at least one arg to avoid printing help
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

    def test_audit_flag(self):
        """Test --audit flag."""
        with patch("sys.argv", ["versiontracker", "--audit"]):
            args = get_arguments()
            self.assertTrue(args.audit)
            self.assertFalse(args.apps)
            self.assertFalse(args.all)
            self.assertIsNone(args.status)
            self.assertFalse(args.explain)

    def test_audit_all_flag(self):
        """Test --audit --all flag."""
        with patch("sys.argv", ["versiontracker", "--audit", "--all"]):
            args = get_arguments()
            self.assertTrue(args.audit)
            self.assertTrue(args.all)
            self.assertIsNone(args.status)

    def test_audit_explain_flag(self):
        """Test --audit --explain flag."""
        with patch("sys.argv", ["versiontracker", "--audit", "--explain"]):
            args = get_arguments()
            self.assertTrue(args.audit)
            self.assertTrue(args.explain)

    def test_audit_status_choices(self):
        """Test --audit --status accepts only its defined choices."""
        for status in ("attention", "unknown", "managed"):
            with self.subTest(status=status):
                with patch("sys.argv", ["versiontracker", "--audit", "--status", status]):
                    args = get_arguments()
                    self.assertEqual(args.status, status)

        with patch("sys.argv", ["versiontracker", "--audit", "--status", "bogus"]):
            with self.assertRaises(SystemExit), patch("sys.stderr", new_callable=StringIO):
                get_arguments()

    def test_audit_all_and_status_mutually_exclusive(self):
        """Test --all and --status cannot be combined."""
        with patch("sys.argv", ["versiontracker", "--audit", "--all", "--status", "attention"]):
            with self.assertRaises(SystemExit), patch("sys.stderr", new_callable=StringIO):
                get_arguments()

    def test_audit_mutually_exclusive_with_apps(self):
        """Test --audit cannot be combined with other main action flags."""
        with patch("sys.argv", ["versiontracker", "--audit", "--apps"]):
            with self.assertRaises(SystemExit), patch("sys.stderr", new_callable=StringIO):
                get_arguments()


class TestRateLimitValidation(unittest.TestCase):
    """--rate-limit must be a positive, finite number of seconds.

    Regression coverage: the CLI previously accepted any float, which a
    downstream handler then truncated to int (0.5 -> 0), and a value of 0
    or a negative number would eventually crash deep inside
    ThreadPoolExecutor/asyncio with a confusing, unrelated error.
    """

    def _assert_rejected(self, raw_value: str) -> None:
        with patch("sys.argv", ["versiontracker", "--apps", "--rate-limit", raw_value]):
            with self.assertRaises(SystemExit), patch("sys.stderr", new_callable=StringIO):
                get_arguments()

    def test_rejects_zero(self):
        self._assert_rejected("0")

    def test_rejects_negative(self):
        self._assert_rejected("-1")

    def test_rejects_nan(self):
        self._assert_rejected("nan")

    def test_rejects_infinite(self):
        self._assert_rejected("inf")

    def test_rejects_non_numeric(self):
        self._assert_rejected("fast")

    def test_accepts_fractional_value(self):
        """A fractional --rate-limit is preserved exactly, not truncated."""
        with patch("sys.argv", ["versiontracker", "--apps", "--rate-limit", "0.5"]):
            args = get_arguments()
            self.assertEqual(args.rate_limit, 0.5)


class TestMaxWorkersValidation(unittest.TestCase):
    """--max-workers must be a positive integer.

    Regression coverage: --max-workers was previously fully dead (parsed,
    never read by any downstream code), so an invalid value like 0 or a
    negative number was silently accepted by argparse and simply ignored.
    Now that it's wired into Config (and Config.set() itself would reject
    a non-positive value), reject bad input at the CLI boundary too, with
    a clear argparse error instead of a downstream ConfigError.
    """

    def _assert_rejected(self, raw_value: str) -> None:
        with patch("sys.argv", ["versiontracker", "--apps", "--max-workers", raw_value]):
            with self.assertRaises(SystemExit), patch("sys.stderr", new_callable=StringIO):
                get_arguments()

    def test_rejects_zero(self):
        self._assert_rejected("0")

    def test_rejects_negative(self):
        self._assert_rejected("-1")

    def test_rejects_non_numeric(self):
        self._assert_rejected("fast")

    def test_rejects_fractional(self):
        self._assert_rejected("2.5")


if __name__ == "__main__":
    unittest.main()
