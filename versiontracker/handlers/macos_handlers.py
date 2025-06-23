"""Handlers for macOS integration commands."""

import logging
import sys
from argparse import Namespace
from typing import Optional

from versiontracker.macos_integration import (
    LaunchdService,
    MacOSNotifications,
    get_service_status,
    install_scheduled_checker,
    uninstall_scheduled_checker,
)
from versiontracker.ui import create_progress_bar

logger = logging.getLogger(__name__)


def handle_install_service(options: Namespace) -> int:
    """Handle installation of the macOS scheduled checker service.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        progress_bar = create_progress_bar()

        # Check if we're on macOS
        if sys.platform != "darwin":
            print(
                progress_bar.color("red")(
                    "Error: macOS integration is only available on macOS"
                )
            )
            return 1

        print("Installing VersionTracker scheduled checker service...")

        # Get interval from options
        interval_hours = getattr(options, "service_interval", 24)

        # Prepare command arguments
        command_args = ["--outdated", "--no-progress"]

        # Install the service
        success = install_scheduled_checker(interval_hours, command_args)

        if success:
            print(
                progress_bar.color("green")(
                    f"✅ Successfully installed VersionTracker service (runs every {interval_hours} hours)"
                )
            )
            print(
                "The service will check for outdated applications and send notifications."
            )
            print("Logs are available at: ~/Library/Logs/VersionTracker/")
            return 0
        else:
            print(
                progress_bar.color("red")("❌ Failed to install VersionTracker service")
            )
            print("Check the logs for more details.")
            return 1

    except Exception as e:
        logger.error(f"Error installing service: {e}")
        print(progress_bar.color("red")(f"Error: {e}"))
        return 1


def handle_uninstall_service(options: Namespace) -> int:
    """Handle uninstallation of the macOS scheduled checker service.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        progress_bar = create_progress_bar()

        # Check if we're on macOS
        if sys.platform != "darwin":
            print(
                progress_bar.color("red")(
                    "Error: macOS integration is only available on macOS"
                )
            )
            return 1

        print("Uninstalling VersionTracker scheduled checker service...")

        # Uninstall the service
        success = uninstall_scheduled_checker()

        if success:
            print(
                progress_bar.color("green")(
                    "✅ Successfully uninstalled VersionTracker service"
                )
            )
            return 0
        else:
            print(
                progress_bar.color("red")(
                    "❌ Failed to uninstall VersionTracker service"
                )
            )
            print("The service may not have been installed or there was an error.")
            return 1

    except Exception as e:
        logger.error(f"Error uninstalling service: {e}")
        print(progress_bar.color("red")(f"Error: {e}"))
        return 1


def handle_service_status(options: Namespace) -> int:
    """Handle displaying the status of the macOS scheduled checker service.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        progress_bar = create_progress_bar()

        # Check if we're on macOS
        if sys.platform != "darwin":
            print(
                progress_bar.color("red")(
                    "Error: macOS integration is only available on macOS"
                )
            )
            return 1

        print("VersionTracker Service Status:")
        print("=" * 40)

        # Get service status
        status = get_service_status()

        # Display installation status
        installed = status.get("installed", False)
        if installed:
            print(progress_bar.color("green")("✅ Service: Installed"))
        else:
            print(progress_bar.color("yellow")("⚠️  Service: Not installed"))
            return 0

        # Display running status
        service_status = status.get("status", "unknown")
        if service_status == "loaded":
            pid = status.get("pid", "unknown")
            if pid == "not running":
                print(
                    progress_bar.color("yellow")(
                        "🔄 Status: Loaded but not currently running"
                    )
                )
            else:
                print(progress_bar.color("green")(f"✅ Status: Running (PID: {pid})"))
        elif service_status == "not loaded":
            print(progress_bar.color("red")("❌ Status: Not loaded"))
        else:
            print(progress_bar.color("yellow")(f"⚠️  Status: {service_status}"))

        # Display exit code if available
        exit_code = status.get("last_exit_code")
        if exit_code and exit_code != "unknown":
            if exit_code == "0":
                print(
                    progress_bar.color("green")(
                        f"✅ Last exit code: {exit_code} (success)"
                    )
                )
            else:
                print(
                    progress_bar.color("red")(f"❌ Last exit code: {exit_code} (error)")
                )

        # Display configuration info
        service = LaunchdService()
        if service.is_installed():
            print(f"📁 Configuration: {service.plist_path}")
            print(f"📋 Logs: {service.log_dir}")

        return 0

    except Exception as e:
        logger.error(f"Error checking service status: {e}")
        print(progress_bar.color("red")(f"Error: {e}"))
        return 1


def handle_test_notification(options: Namespace) -> int:
    """Handle sending a test notification.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        progress_bar = create_progress_bar()

        # Check if we're on macOS
        if sys.platform != "darwin":
            print(
                progress_bar.color("red")(
                    "Error: macOS notifications are only available on macOS"
                )
            )
            return 1

        print("Sending test notification...")

        # Send test notification
        success = MacOSNotifications.send_notification(
            "VersionTracker",
            "Test notification sent successfully! 🎉",
            subtitle="System Integration Test",
        )

        if success:
            print(progress_bar.color("green")("✅ Test notification sent successfully"))
            return 0
        else:
            print(progress_bar.color("red")("❌ Failed to send test notification"))
            return 1

    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        print(progress_bar.color("red")(f"Error: {e}"))
        return 1


def handle_menubar_app(options: Namespace) -> int:
    """Handle launching the macOS menubar application.

    Args:
        options: Command line options

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        progress_bar = create_progress_bar()

        # Check if we're on macOS
        if sys.platform != "darwin":
            print(
                progress_bar.color("red")(
                    "Error: menubar application is only available on macOS"
                )
            )
            return 1

        print("Launching VersionTracker menubar application...")

        # Import and start the menubar app
        from versiontracker.menubar_app import MenubarApp

        app = MenubarApp()
        app.start()

        return 0

    except KeyboardInterrupt:
        print(progress_bar.color("yellow")("\nMenubar application stopped by user"))
        return 0
    except Exception as e:
        logger.error(f"Error launching menubar app: {e}")
        print(progress_bar.color("red")(f"Error: {e}"))
        return 1
