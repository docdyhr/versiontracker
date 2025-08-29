"""VersionTracker menubar application for macOS.

This module provides a simple menubar application that gives quick access to
VersionTracker functionality directly from the macOS menubar.
"""

import logging
import subprocess
import sys
import threading
import time

logger = logging.getLogger(__name__)


class MenubarApp:
    """Simple menubar application for VersionTracker."""

    def __init__(self):
        """Initialize the menubar application."""
        self.running = False
        self.last_check_time: float | None = None
        self.outdated_count = 0

    def show_menu(self) -> None:
        """Show the menubar menu using osascript."""
        try:
            # Create menu items
            menu_items = [
                "VersionTracker",
                "─────────────────",
                "Check for Updates",
                "Show Outdated Apps",
                "Show All Apps",
                "Show Homebrew Casks",
                "─────────────────",
                "Install Service",
                "Uninstall Service",
                "Service Status",
                "─────────────────",
                "Quit",
            ]

            # Create AppleScript for menu
            script = f'''
            set menuItems to {{"{'", "'.join(menu_items)}"}}
            set selectedItem to (choose from list menuItems with title "VersionTracker" \\
                with prompt "Choose an action:" default items {{"Check for Updates"}})

            if selectedItem is not false then
                return item 1 of selectedItem
            else
                return "cancelled"
            end if
            '''

            # osascript is a system command, using list of args is safe
            result = subprocess.run(  # nosec B603 B607
                ["osascript", "-e", script], capture_output=True, text=True
            )

            if result.returncode == 0:
                choice = result.stdout.strip()
                self.handle_menu_choice(choice)
            else:
                logger.error(f"Failed to show menu: {result.stderr}")

        except Exception as e:
            logger.error(f"Error showing menu: {e}")

    def handle_menu_choice(self, choice: str) -> None:
        """Handle menu selection.

        Args:
            choice: The selected menu item
        """
        if choice == "cancelled" or choice == "Quit":
            self.quit()
            return

        # Map menu choices to versiontracker commands
        commands = {
            "Check for Updates": ["--outdated", "--notify"],
            "Show Outdated Apps": ["--outdated"],
            "Show All Apps": ["--apps"],
            "Show Homebrew Casks": ["--brews"],
            "Install Service": ["--install-service"],
            "Uninstall Service": ["--uninstall-service"],
            "Service Status": ["--service-status"],
        }

        if choice in commands:
            self.run_versiontracker_command(commands[choice])
        elif choice not in ["VersionTracker", "─────────────────"]:
            logger.warning(f"Unknown menu choice: {choice}")

    def run_versiontracker_command(self, args: list) -> None:
        """Run a versiontracker command in a separate thread.

        Args:
            args: Command line arguments for versiontracker
        """

        def run_command():
            try:
                # Run versiontracker command
                cmd = [sys.executable, "-m", "versiontracker"] + args
                # System executable is safe, using list of args
                result = subprocess.run(  # nosec B603
                    cmd, capture_output=True, text=True
                )

                if result.returncode == 0:
                    if result.stdout:
                        # Show output in a dialog if there's output
                        self.show_result_dialog("VersionTracker", result.stdout)
                else:
                    # Show error in a dialog
                    error_msg = result.stderr or "Command failed"
                    self.show_result_dialog("VersionTracker Error", error_msg)

            except Exception as e:
                logger.error(f"Error running command: {e}")
                self.show_result_dialog("VersionTracker Error", f"Failed to run command: {e}")

        # Run in background thread
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()

    def show_result_dialog(self, title: str, message: str) -> None:
        """Show a result dialog.

        Args:
            title: Dialog title
            message: Dialog message
        """
        try:
            # Limit message length for dialog
            if len(message) > 1000:
                message = message[:1000] + "\\n\\n... (truncated)"

            # Escape quotes in message
            message = message.replace('"', '\\"').replace("'", "\\'")

            script = f'''
            display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK"
            '''

            # osascript is a system command, using list of args is safe
            subprocess.run(  # nosec B603 B607
                ["osascript", "-e", script], capture_output=True, text=True
            )

        except Exception as e:
            logger.error(f"Error showing result dialog: {e}")

    def create_status_item(self) -> bool:
        """Create a status bar item using SwiftBar-style script.

        Returns:
            bool: True if status item was created successfully
        """
        try:
            # Create a simple status bar script that shows the menu when clicked

            # For now, just show the menu directly since we don't have SwiftBar
            # In a real implementation, this would integrate with a menubar framework
            return True

        except Exception as e:
            logger.error(f"Error creating status item: {e}")
            return False

    def start(self) -> None:
        """Start the menubar application."""
        if sys.platform != "darwin":
            print("VersionTracker menubar app is only available on macOS")
            return

        print("Starting VersionTracker menubar application...")  # type: ignore[unreachable]
        print("Click the menu to access VersionTracker features.")

        self.running = True

        try:
            # Show menu immediately
            self.show_menu()

            # Keep the app running and show menu periodically or on demand
            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\\nShutting down menubar application...")
            self.quit()

    def quit(self) -> None:
        """Quit the menubar application."""
        self.running = False
        print("VersionTracker menubar application stopped.")


def main() -> None:
    """Main entry point for the menubar application."""
    app = MenubarApp()
    app.start()


if __name__ == "__main__":
    main()
