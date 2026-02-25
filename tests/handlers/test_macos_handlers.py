"""Tests for versiontracker.handlers.macos_handlers — coverage improvement.

Targets all 5 handler functions: handle_install_service, handle_uninstall_service,
handle_service_status, handle_test_notification, handle_menubar_app.
"""

from argparse import Namespace
from unittest.mock import MagicMock, patch

from versiontracker.handlers.macos_handlers import (
    handle_install_service,
    handle_menubar_app,
    handle_service_status,
    handle_test_notification,
    handle_uninstall_service,
)


def _mock_progress_bar():
    """Create a mock progress_bar that returns identity for color calls."""
    pb = MagicMock()
    pb.color.return_value = lambda x: x
    return pb


# ---------------------------------------------------------------------------
# handle_install_service
# ---------------------------------------------------------------------------


class TestHandleInstallService:
    """Tests for handle_install_service()."""

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "linux")
    def test_not_darwin_returns_1(self, _pb):
        assert handle_install_service(Namespace()) == 1

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.macos_handlers.install_scheduled_checker", return_value=True)
    @patch("sys.platform", "darwin")
    def test_success_returns_0(self, _install, _pb):
        assert handle_install_service(Namespace()) == 0

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.macos_handlers.install_scheduled_checker", return_value=False)
    @patch("sys.platform", "darwin")
    def test_failure_returns_1(self, _install, _pb):
        assert handle_install_service(Namespace()) == 1

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.macos_handlers.install_scheduled_checker", return_value=True)
    @patch("sys.platform", "darwin")
    def test_custom_interval(self, mock_install, _pb):
        handle_install_service(Namespace(service_interval=12))
        mock_install.assert_called_once_with(12, ["--outdated", "--no-progress"])

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch(
        "versiontracker.handlers.macos_handlers.install_scheduled_checker",
        side_effect=RuntimeError("boom"),
    )
    @patch("sys.platform", "darwin")
    def test_exception_returns_1(self, _install, _pb):
        assert handle_install_service(Namespace()) == 1


# ---------------------------------------------------------------------------
# handle_uninstall_service
# ---------------------------------------------------------------------------


class TestHandleUninstallService:
    """Tests for handle_uninstall_service()."""

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "linux")
    def test_not_darwin_returns_1(self, _pb):
        assert handle_uninstall_service(Namespace()) == 1

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.macos_handlers.uninstall_scheduled_checker", return_value=True)
    @patch("sys.platform", "darwin")
    def test_success_returns_0(self, _uninstall, _pb):
        assert handle_uninstall_service(Namespace()) == 0

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("versiontracker.handlers.macos_handlers.uninstall_scheduled_checker", return_value=False)
    @patch("sys.platform", "darwin")
    def test_failure_returns_1(self, _uninstall, _pb):
        assert handle_uninstall_service(Namespace()) == 1

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch(
        "versiontracker.handlers.macos_handlers.uninstall_scheduled_checker",
        side_effect=RuntimeError("boom"),
    )
    @patch("sys.platform", "darwin")
    def test_exception_returns_1(self, _uninstall, _pb):
        assert handle_uninstall_service(Namespace()) == 1


# ---------------------------------------------------------------------------
# handle_service_status
# ---------------------------------------------------------------------------


class TestHandleServiceStatus:
    """Tests for handle_service_status()."""

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "linux")
    def test_not_darwin_returns_1(self, _pb):
        assert handle_service_status(Namespace()) == 1

    @patch("versiontracker.handlers.macos_handlers.LaunchdService")
    @patch(
        "versiontracker.handlers.macos_handlers.get_service_status",
        return_value={"installed": False},
    )
    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "darwin")
    def test_not_installed(self, _pb, _status, _service):
        assert handle_service_status(Namespace()) == 0

    @patch("versiontracker.handlers.macos_handlers.LaunchdService")
    @patch(
        "versiontracker.handlers.macos_handlers.get_service_status",
        return_value={"installed": True, "status": "loaded", "pid": "1234"},
    )
    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "darwin")
    def test_loaded_running(self, _pb, _status, _service):
        assert handle_service_status(Namespace()) == 0

    @patch("versiontracker.handlers.macos_handlers.LaunchdService")
    @patch(
        "versiontracker.handlers.macos_handlers.get_service_status",
        return_value={"installed": True, "status": "loaded", "pid": "not running"},
    )
    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "darwin")
    def test_loaded_not_running(self, _pb, _status, _service):
        assert handle_service_status(Namespace()) == 0

    @patch("versiontracker.handlers.macos_handlers.LaunchdService")
    @patch(
        "versiontracker.handlers.macos_handlers.get_service_status",
        return_value={"installed": True, "status": "not loaded"},
    )
    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "darwin")
    def test_not_loaded(self, _pb, _status, _service):
        assert handle_service_status(Namespace()) == 0

    @patch("versiontracker.handlers.macos_handlers.LaunchdService")
    @patch(
        "versiontracker.handlers.macos_handlers.get_service_status",
        return_value={"installed": True, "status": "something_else"},
    )
    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "darwin")
    def test_unknown_status(self, _pb, _status, _service):
        assert handle_service_status(Namespace()) == 0

    @patch("versiontracker.handlers.macos_handlers.LaunchdService")
    @patch(
        "versiontracker.handlers.macos_handlers.get_service_status",
        return_value={"installed": True, "status": "loaded", "pid": "1234", "last_exit_code": "0"},
    )
    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "darwin")
    def test_exit_code_success(self, _pb, _status, _service):
        assert handle_service_status(Namespace()) == 0

    @patch("versiontracker.handlers.macos_handlers.LaunchdService")
    @patch(
        "versiontracker.handlers.macos_handlers.get_service_status",
        return_value={"installed": True, "status": "loaded", "pid": "1234", "last_exit_code": "1"},
    )
    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "darwin")
    def test_exit_code_error(self, _pb, _status, _service):
        assert handle_service_status(Namespace()) == 0

    @patch(
        "versiontracker.handlers.macos_handlers.get_service_status",
        side_effect=RuntimeError("boom"),
    )
    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "darwin")
    def test_exception_returns_1(self, _pb, _status):
        assert handle_service_status(Namespace()) == 1


# ---------------------------------------------------------------------------
# handle_test_notification
# ---------------------------------------------------------------------------


class TestHandleTestNotification:
    """Tests for handle_test_notification()."""

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "linux")
    def test_not_darwin_returns_1(self, _pb):
        assert handle_test_notification(Namespace()) == 1

    @patch("versiontracker.handlers.macos_handlers.MacOSNotifications")
    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "darwin")
    def test_success_returns_0(self, _pb, mock_notif):
        mock_notif.send_notification.return_value = True
        assert handle_test_notification(Namespace()) == 0

    @patch("versiontracker.handlers.macos_handlers.MacOSNotifications")
    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "darwin")
    def test_failure_returns_1(self, _pb, mock_notif):
        mock_notif.send_notification.return_value = False
        assert handle_test_notification(Namespace()) == 1

    @patch(
        "versiontracker.handlers.macos_handlers.MacOSNotifications",
        **{"send_notification.side_effect": RuntimeError("boom")},
    )
    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "darwin")
    def test_exception_returns_1(self, _pb, _notif):
        assert handle_test_notification(Namespace()) == 1


# ---------------------------------------------------------------------------
# handle_menubar_app
# ---------------------------------------------------------------------------


class TestHandleMenubarApp:
    """Tests for handle_menubar_app()."""

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "linux")
    def test_not_darwin_returns_1(self, _pb):
        assert handle_menubar_app(Namespace()) == 1

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "darwin")
    def test_success_returns_0(self, _pb):
        mock_module = MagicMock()
        mock_module.MenubarApp.return_value = MagicMock()
        with patch.dict("sys.modules", {"versiontracker.menubar_app": mock_module}):
            assert handle_menubar_app(Namespace()) == 0

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "darwin")
    def test_keyboard_interrupt_returns_0(self, _pb):
        mock_module = MagicMock()
        mock_module.MenubarApp.return_value.start.side_effect = KeyboardInterrupt
        with patch.dict("sys.modules", {"versiontracker.menubar_app": mock_module}):
            assert handle_menubar_app(Namespace()) == 0

    @patch("versiontracker.handlers.macos_handlers.create_progress_bar", return_value=_mock_progress_bar())
    @patch("sys.platform", "darwin")
    def test_exception_returns_1(self, _pb):
        mock_module = MagicMock()
        mock_module.MenubarApp.return_value.start.side_effect = RuntimeError("boom")
        with patch.dict("sys.modules", {"versiontracker.menubar_app": mock_module}):
            assert handle_menubar_app(Namespace()) == 1
