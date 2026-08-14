"""Tests for macOS integration functionality."""

import plistlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Only run these tests on macOS
pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS integration tests only run on macOS")

# Import after pytest marker to avoid import errors on non-macOS systems
if sys.platform == "darwin":
    from versiontracker.macos_integration import (
        LaunchdService,
        MacOSNotifications,
        get_service_status,
        install_scheduled_checker,
        uninstall_scheduled_checker,
    )


class TestLaunchdService(unittest.TestCase):
    """Test cases for LaunchdService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.service = LaunchdService(interval_hours=12)
        # Override the plist path to use temp directory
        self.service.plist_path = self.temp_dir / "test.plist"
        self.service.log_dir = self.temp_dir / "logs"

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """Test LaunchdService initialization."""
        service = LaunchdService(interval_hours=6)
        self.assertEqual(service.interval_hours, 6)
        self.assertIsNotNone(service.plist_path)
        self.assertIsNotNone(service.log_dir)

    def test_create_plist(self):
        """Test plist configuration creation."""
        plist_config = self.service.create_plist(["--test"])

        self.assertEqual(plist_config["Label"], "com.versiontracker.updater")
        self.assertIn("--test", plist_config["ProgramArguments"])
        self.assertEqual(plist_config["StartInterval"], 12 * 3600)  # 12 hours in seconds
        self.assertFalse(plist_config["RunAtLoad"])

    def test_create_plist_default_command_args(self):
        """Default command_args must be real, valid CLI options.

        Regression coverage: the default used to be ["--outdated", "--no-progress"],
        and --outdated has never been a registered CLI flag (only --check-outdated
        is) -- every plist generated from the default would have failed on every
        scheduled run.
        """
        plist_config = self.service.create_plist()

        program_args = plist_config["ProgramArguments"]
        self.assertIn("--check-outdated", program_args)
        self.assertIn("--notify", program_args)
        self.assertNotIn("--outdated", program_args)

    @patch("subprocess.check_output")
    def test_create_plist_rejects_empty_python_path(self, mock_check_output):
        """An empty `which python3` result must fail clearly, not silently."""
        mock_check_output.return_value = "\n"

        with self.assertRaises(RuntimeError):
            self.service.create_plist(["--test"])

    @patch("subprocess.check_output")
    def test_create_plist_rejects_nonexistent_python_path(self, mock_check_output):
        """A `which python3` result that doesn't exist on disk must fail clearly."""
        mock_check_output.return_value = "/nonexistent/path/to/python3\n"

        with self.assertRaises(RuntimeError):
            self.service.create_plist(["--test"])

    def test_dict_to_plist_xml(self):
        """Test dictionary to plist XML conversion."""
        test_dict = {
            "Label": "test.label",
            "StartInterval": 3600,
            "RunAtLoad": True,
            "ProgramArguments": ["python", "--test"],
        }

        xml = self.service._dict_to_plist_xml(test_dict)

        self.assertIn('<?xml version="1.0" encoding="UTF-8"?>', xml)
        self.assertIn('<plist version="1.0">', xml)
        self.assertIn("<string>test.label</string>", xml)
        self.assertIn("<integer>3600</integer>", xml)
        self.assertIn("<true/>", xml)
        self.assertIn("<array>", xml)

    def test_dict_to_plist_xml_escapes_special_characters_and_round_trips(self):
        """XML-significant characters, quotes, spaces, and Unicode must survive intact.

        Regression coverage: the previous hand-rolled XML builder never escaped
        &, <, or > in string values or dict keys, so any environment variable,
        path, or argument containing them would produce invalid or
        semantically-wrong plist XML.
        """
        test_dict = {
            "Label": "com.versiontracker.updater",
            "StandardOutPath": "/tmp/A & B <weird> \"quoted\" 'path'/versiontracker.log",
            "EnvironmentVariables": {
                "HOME": "/Users/O'Brien & Cañón",
                "PATH": "/usr/bin:/bin",
            },
            "ProgramArguments": ["/usr/bin/python3", "-m", "versiontracker", "--check-outdated & --notify"],
        }

        xml = self.service._dict_to_plist_xml(test_dict)

        # Raw special characters must never appear unescaped in XML text content.
        self.assertNotIn("<weird>", xml)
        self.assertIn("&amp;", xml)
        self.assertIn("&lt;weird&gt;", xml)

        # The XML must be well-formed and round-trip back to the exact original dict.
        round_tripped = plistlib.loads(xml.encode("utf-8"))
        self.assertEqual(round_tripped, test_dict)

    def test_is_installed(self):
        """Test service installation check."""
        # Initially not installed
        self.assertFalse(self.service.is_installed())

        # Create plist file
        self.service.plist_path.parent.mkdir(parents=True, exist_ok=True)
        self.service.plist_path.write_text("test plist")

        # Now should be installed
        self.assertTrue(self.service.is_installed())

    @patch("subprocess.run")
    def test_get_status_loaded(self, mock_run):
        """Test getting service status when loaded."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "PID\tStatus\tLabel\n1234\t0\tcom.versiontracker.updater"

        status = self.service.get_status()

        self.assertEqual(status["status"], "loaded")
        self.assertEqual(status["pid"], "1234")

    @patch("subprocess.run")
    def test_get_status_not_loaded(self, mock_run):
        """Test getting service status when not loaded."""
        mock_run.return_value.returncode = 1

        status = self.service.get_status()

        self.assertEqual(status["status"], "not loaded")


class TestMacOSNotifications(unittest.TestCase):
    """Test cases for MacOSNotifications class."""

    @patch("subprocess.run")
    def test_send_notification_success(self, mock_run):
        """Test successful notification sending."""
        mock_run.return_value.returncode = 0

        success = MacOSNotifications.send_notification("Test Title", "Test Message", "Test Subtitle")

        self.assertTrue(success)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "osascript")

    @patch("subprocess.run")
    def test_send_notification_failure(self, mock_run):
        """Test notification sending failure."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Error"

        success = MacOSNotifications.send_notification("Test", "Test")

        self.assertFalse(success)

    @patch("subprocess.run")
    def test_notify_outdated_apps_empty(self, mock_run):
        """Test notification with no outdated apps."""
        mock_run.return_value.returncode = 0

        success = MacOSNotifications.notify_outdated_apps([])

        self.assertTrue(success)
        # Should send "all up to date" message, passed as argv data, never
        # embedded in the (static) AppleScript source text.
        args = mock_run.call_args[0][0]
        script = args[2]
        self.assertNotIn("All applications are up to date", script)
        self.assertIn("All applications are up to date! ✅", args[3:])

    @patch("subprocess.run")
    def test_notify_outdated_apps_with_apps(self, mock_run):
        """Test notification with outdated apps."""
        mock_run.return_value.returncode = 0

        outdated_apps = [
            {"name": "App1", "version": "1.0"},
            {"name": "App2", "version": "2.0"},
        ]

        success = MacOSNotifications.notify_outdated_apps(outdated_apps)

        self.assertTrue(success)
        args = mock_run.call_args[0][0]
        script = args[2]
        self.assertNotIn("App1, App2", script)
        self.assertTrue(any("App1, App2" in item for item in args[3:]))

    @patch("subprocess.run")
    def test_notify_service_status(self, mock_run):
        """Test service status notification."""
        mock_run.return_value.returncode = 0

        success = MacOSNotifications.notify_service_status("installed", True)

        self.assertTrue(success)
        args = mock_run.call_args[0][0]
        script = args[2]
        self.assertNotIn("installed successfully", script)
        self.assertTrue(any("installed successfully" in item for item in args[3:]))


# Adversarial strings covering the classes of input that could previously break
# out of the naive `"` -> `\"` AppleScript string-literal escaping: double
# quotes, single quotes, bare backslashes, a trailing backslash-then-quote
# (the specific break-out sequence), newlines/tabs, AppleScript operators and
# comment markers, unicode text, and CLI-output-shaped hostile text. These are
# purely structural assertions (no command is ever actually executed).
HOSTILE_STRINGS = [
    'has "double quotes"',
    "has 'single quotes'",
    "has a \\ backslash",
    'ends with a backslash then quote \\"',
    "has\nnewline\tand\ttab",
    'operators & -- comment "quote" ¬ continuation',
    "Café México 日本語 应用 App",
    'display dialog "pwned" -- do shell script "touch /tmp/pwned"',
]


class TestAppleScriptInjectionSafety(unittest.TestCase):
    """Regression coverage: hostile input must stay data, never script structure."""

    @patch("subprocess.run")
    def test_send_notification_hostile_input_stays_data(self, mock_run):
        """Hostile title/message/subtitle never alter the AppleScript source."""
        mock_run.return_value.returncode = 0

        for hostile in HOSTILE_STRINGS:
            with self.subTest(hostile=hostile):
                mock_run.reset_mock()
                MacOSNotifications.send_notification(hostile, hostile, hostile)

                args = mock_run.call_args[0][0]
                script = args[2]

                # The AppleScript source is always the same static handler,
                # regardless of what the hostile input contains.
                self.assertNotIn(hostile, script)
                self.assertIn("on run argv", script)
                self.assertIn(MacOSNotifications._NOTIFICATION_HANDLER, script)

                # The hostile value reaches osascript unchanged, as separate
                # argv items -- proving it is treated as opaque data.
                self.assertEqual(args[3:], [hostile, hostile, hostile])

    @patch("subprocess.run")
    def test_notification_script_is_constant_across_calls(self, mock_run):
        """The generated script text never changes, no matter the input."""
        mock_run.return_value.returncode = 0

        MacOSNotifications.send_notification("Title A", "Message A")
        script_a = mock_run.call_args[0][0][2]

        MacOSNotifications.send_notification('Title "B"', "Message\nB", subtitle="Sub\\B")
        script_b = mock_run.call_args[0][0][2]

        self.assertEqual(script_a, script_b)


class TestGlobalFunctions(unittest.TestCase):
    """Test cases for global integration functions."""

    @patch("versiontracker.macos_integration.LaunchdService")
    @patch("versiontracker.macos_integration.MacOSNotifications")
    def test_install_scheduled_checker(self, mock_notifications, mock_service_class):
        """Test installing scheduled checker."""
        mock_service = MagicMock()
        mock_service.install_service.return_value = True
        mock_service_class.return_value = mock_service
        mock_notifications.notify_service_status.return_value = True

        result = install_scheduled_checker(24, ["--test"])

        self.assertTrue(result)
        mock_service.install_service.assert_called_once_with(["--test"])
        mock_notifications.notify_service_status.assert_called_once_with("installed", True)

    @patch("versiontracker.macos_integration.LaunchdService")
    @patch("versiontracker.macos_integration.MacOSNotifications")
    def test_uninstall_scheduled_checker(self, mock_notifications, mock_service_class):
        """Test uninstalling scheduled checker."""
        mock_service = MagicMock()
        mock_service.uninstall_service.return_value = True
        mock_service_class.return_value = mock_service
        mock_notifications.notify_service_status.return_value = True

        result = uninstall_scheduled_checker()

        self.assertTrue(result)
        mock_service.uninstall_service.assert_called_once()
        mock_notifications.notify_service_status.assert_called_once_with("uninstalled", True)

    @patch("versiontracker.macos_integration.LaunchdService")
    def test_get_service_status(self, mock_service_class):
        """Test getting service status."""
        mock_service = MagicMock()
        mock_service.get_status.return_value = {"status": "loaded"}
        mock_service.is_installed.return_value = True
        mock_service_class.return_value = mock_service

        status = get_service_status()

        self.assertEqual(status["status"], "loaded")
        self.assertTrue(status["installed"])


if __name__ == "__main__":
    unittest.main()
