"""
List applications command implementation.

This module provides the ListAppsCommand for discovering and listing
applications installed on the system.
"""

import logging
from typing import Any

from versiontracker.commands import BaseCommand
from versiontracker.handlers import handle_list_apps


class ListAppsCommand(BaseCommand):
    """Command to list applications not managed by the App Store."""

    name = "list-apps"
    description = "List all applications not updated by App Store"

    def execute(self, options: Any) -> int:
        """Execute the list apps command.

        Args:
            options: Parsed command-line arguments

        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        try:
            return handle_list_apps(options)
        except Exception as e:
            logging.exception("Error executing list apps command: %s", str(e))
            return 1

    def validate_options(self, options: Any) -> bool:
        """Validate command-specific options.

        Args:
            options: Parsed command-line arguments

        Returns:
            bool: True if options are valid, False otherwise
        """
        # Basic validation - ensure apps flag is set
        if not hasattr(options, "apps") or not options.apps:
            return False

        # Additional validation can be added here
        return True
