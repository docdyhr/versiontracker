"""macOS integration utilities for VersionTracker.

This module provides macOS-specific integration features including:
- launchd service management for scheduled checks
- Native notifications for update alerts
- System integration utilities
"""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from versiontracker.exceptions import HomebrewError

logger = logging.getLogger(__name__)

# macOS paths and constants
LAUNCHD_USER_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
VERSIONTRACKER_PLIST = "com.versiontracker.updater.plist"
VERSIONTRACKER_LOG_DIR = Path.home() / "Library" / "Logs" / "VersionTracker"


class LaunchdService:
    """Manages launchd service for scheduled VersionTracker runs."""

    def __init__(self, interval_hours: int = 24):
        """Initialize the launchd service manager.

        Args:
            interval_hours: How often to run the check (in hours)
        """
        self.interval_hours = interval_hours
        self.plist_path = LAUNCHD_USER_AGENTS_DIR / VERSIONTRACKER_PLIST
        self.log_dir = VERSIONTRACKER_LOG_DIR

    def create_plist(self, command_args: Optional[List[str]] = None) -> Dict:
        """Create the launchd plist configuration.

        Args:
            command_args: Additional command arguments for versiontracker

        Returns:
            Dict: The plist configuration
        """
        if command_args is None:
            command_args = ["--outdated", "--no-progress"]

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Get the python executable and versiontracker path
        # Using which with subprocess is safe here as we control the command
        python_path = subprocess.check_output(  # nosec B603 B607
            ["which", "python3"], text=True
        ).strip()

        plist_config = {
            "Label": "com.versiontracker.updater",
            "ProgramArguments": [python_path, "-m", "versiontracker"] + command_args,
            "StartInterval": self.interval_hours * 3600,  # Convert hours to seconds
            "RunAtLoad": False,
            "StandardOutPath": str(self.log_dir / "versiontracker.log"),
            "StandardErrorPath": str(self.log_dir / "versiontracker-error.log"),
            "ProcessType": "Background",
            "EnvironmentVariables": {
                "PATH": os.environ.get("PATH", ""),
                "HOME": str(Path.home()),
            },
        }

        return plist_config

    def install_service(self, command_args: Optional[List[str]] = None) -> bool:
        """Install the launchd service.

        Args:
            command_args: Additional command arguments for versiontracker

        Returns:
            bool: True if installation succeeded
        """
        try:
            # Ensure LaunchAgents directory exists
            LAUNCHD_USER_AGENTS_DIR.mkdir(parents=True, exist_ok=True)

            # Create plist content
            plist_config = self.create_plist(command_args)

            # Write plist file in XML format
            plist_content = self._dict_to_plist_xml(plist_config)

            with open(self.plist_path, "w") as f:
                f.write(plist_content)

            logger.info(f"Created launchd plist at {self.plist_path}")

            # Load the service
            # launchctl is a system command, using list of args is safe
            result = subprocess.run(  # nosec B603 B607
                ["launchctl", "load", str(self.plist_path)],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.info("Successfully installed VersionTracker launchd service")
                return True
            else:
                logger.error(f"Failed to load launchd service: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to install launchd service: {e}")
            return False

    def uninstall_service(self) -> bool:
        """Uninstall the launchd service.

        Returns:
            bool: True if uninstallation succeeded
        """
        try:
            # Unload the service if it's loaded
            # launchctl is a system command, using list of args is safe
            subprocess.run(  # nosec B603 B607
                ["launchctl", "unload", str(self.plist_path)],
                capture_output=True,
                text=True,
            )

            # Remove the plist file
            if self.plist_path.exists():
                self.plist_path.unlink()
                logger.info("Removed VersionTracker launchd service")
                return True
            else:
                logger.info("VersionTracker launchd service was not installed")
                return True

        except Exception as e:
            logger.error(f"Failed to uninstall launchd service: {e}")
            return False

    def is_installed(self) -> bool:
        """Check if the launchd service is installed.

        Returns:
            bool: True if the service is installed
        """
        return self.plist_path.exists()

    def get_status(self) -> Dict[str, str]:
        """Get the status of the launchd service.

        Returns:
            Dict: Service status information
        """
        try:
            # launchctl is a system command, using list of args is safe
            result = subprocess.run(  # nosec B603 B607
                ["launchctl", "list", "com.versiontracker.updater"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                # Parse the output to get status
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    status_line = lines[1].split()
                    return {
                        "status": "loaded",
                        "pid": status_line[0] if status_line[0] != "-" else "not running",
                        "last_exit_code": status_line[1] if len(status_line) > 1 else "unknown",
                    }

            return {"status": "not loaded"}

        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {"status": "error", "error": str(e)}

    def _dict_to_plist_xml(self, data: Dict) -> str:
        """Convert a dictionary to plist XML format.

        Args:
            data: Dictionary to convert

        Returns:
            str: XML plist content
        """

        def _convert_value(value):
            if isinstance(value, bool):
                return "<true/>" if value else "<false/>"
            elif isinstance(value, int):
                return f"<integer>{value}</integer>"
            elif isinstance(value, str):
                return f"<string>{value}</string>"
            elif isinstance(value, list):
                items = "".join(_convert_value(item) for item in value)
                return f"<array>{items}</array>"
            elif isinstance(value, dict):
                items = "".join(f"<key>{k}</key>{_convert_value(v)}" for k, v in value.items())
                return f"<dict>{items}</dict>"
            else:
                return f"<string>{str(value)}</string>"

        xml_content = _convert_value(data)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
{xml_content}
</plist>
"""


class MacOSNotifications:
    """Handle macOS native notifications for VersionTracker."""

    @staticmethod
    def send_notification(title: str, message: str, subtitle: str = "") -> bool:
        """Send a native macOS notification.

        Args:
            title: Notification title
            message: Notification message
            subtitle: Optional subtitle

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            cmd = [
                "osascript",
                "-e",
                f'display notification "{message}" with title "{title}"',
            ]

            if subtitle:
                cmd[-1] += f' subtitle "{subtitle}"'

            # nosec B603 - osascript with controlled arguments
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.debug(f"Sent notification: {title}")
                return True
            else:
                logger.error(f"Failed to send notification: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    @staticmethod
    def notify_outdated_apps(outdated_apps: List[Dict[str, str]]) -> bool:
        """Send notification about outdated applications.

        Args:
            outdated_apps: List of outdated application info

        Returns:
            bool: True if notification was sent successfully
        """
        if not outdated_apps:
            return MacOSNotifications.send_notification("VersionTracker", "All applications are up to date! ✅")

        count = len(outdated_apps)
        app_names = ", ".join(app.get("name", "Unknown") for app in outdated_apps[:3])

        if count > 3:
            app_names += f" and {count - 3} more"

        message = f"{count} app{'s' if count != 1 else ''} need updating: {app_names}"

        return MacOSNotifications.send_notification("VersionTracker", message, subtitle="Application Updates Available")

    @staticmethod
    def notify_service_status(action: str, success: bool) -> bool:
        """Send notification about service status.

        Args:
            action: The action performed (installed, uninstalled, etc.)
            success: Whether the action succeeded

        Returns:
            bool: True if notification was sent successfully
        """
        if success:
            message = f"VersionTracker service {action} successfully"
            return MacOSNotifications.send_notification("VersionTracker", message)
        else:
            message = f"Failed to {action.replace('ed', '')} VersionTracker service"
            return MacOSNotifications.send_notification("VersionTracker", message)


def install_scheduled_checker(interval_hours: int = 24, command_args: Optional[List[str]] = None) -> bool:
    """Install the scheduled application checker service.

    Args:
        interval_hours: How often to run the check (in hours)
        command_args: Additional command arguments for versiontracker

    Returns:
        bool: True if installation succeeded
    """
    service = LaunchdService(interval_hours)
    success = service.install_service(command_args)

    # Send notification about the installation
    MacOSNotifications.notify_service_status("installed", success)

    return success


def uninstall_scheduled_checker() -> bool:
    """Uninstall the scheduled application checker service.

    Returns:
        bool: True if uninstallation succeeded
    """
    service = LaunchdService()
    success = service.uninstall_service()

    # Send notification about the uninstallation
    MacOSNotifications.notify_service_status("uninstalled", success)

    return success


def get_service_status() -> Dict[str, Union[str, bool]]:
    """Get the status of the scheduled checker service.

    Returns:
        Dict: Service status information
    """
    service = LaunchdService()
    status = dict(service.get_status())  # Create a new dict to allow mixed types
    status["installed"] = service.is_installed()  # type: ignore
    return status  # type: ignore


def check_and_notify() -> None:
    """Check for outdated applications and send notifications.

    This is the main function called by the scheduled service.
    """
    try:
        from versiontracker.app_finder import get_applications
        from versiontracker.homebrew import get_installed_homebrew_casks
        from versiontracker.version import check_outdated_apps

        logger.info("Starting scheduled application check")

        # Get applications not in App Store
        apps = get_applications({})  # Pass empty dict for options

        if not apps:
            logger.info("No applications found to check")
            return

        # Check for outdated apps
        outdated_data = check_outdated_apps(apps)

        # Convert to format expected by notifications
        outdated_apps = []
        for app_name, version_info, status in outdated_data:
            if str(status) == "outdated":
                outdated_apps.append(
                    {
                        "name": app_name,
                        "installed": version_info.get("installed", "Unknown"),
                        "latest": version_info.get("latest", "Unknown"),
                    }
                )

        # Send notification
        MacOSNotifications.notify_outdated_apps(outdated_apps)

        logger.info(f"Checked {len(apps)} applications, found {len(outdated_apps)} outdated")

    except Exception as e:
        logger.error(f"Error during scheduled check: {e}")
        MacOSNotifications.send_notification("VersionTracker", f"Error during scheduled check: {str(e)}")
