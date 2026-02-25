"""Backup and restore handlers for configuration operations.

This module provides backup and restore functionality for configuration
changes, particularly for blacklist operations that need rollback capability.
"""

import json
import logging
import os
import tempfile
import time

from versiontracker.config import Config
from versiontracker.handlers.auto_update_types import BlacklistBackup
from versiontracker.ui import create_progress_bar


class BackupManager:
    """Manages backup and restore operations for configuration."""

    def __init__(self, config: Config | None = None) -> None:
        """Initialize the backup manager.

        Args:
            config: Configuration object to use for restore operations
        """
        from versiontracker.config import get_config

        self.config = config or get_config()
        self.progress_bar = create_progress_bar()

    def create_blacklist_backup(self, current_blacklist: list[str]) -> BlacklistBackup:
        """Create a backup of the current blacklist configuration.

        Args:
            current_blacklist: Current blacklist items

        Returns:
            BlacklistBackup object with backup information
        """
        backup = BlacklistBackup(original_blacklist=current_blacklist.copy(), timestamp=time.time())

        try:
            # Create temporary backup file
            temp_dir = tempfile.gettempdir()
            backup_file = os.path.join(temp_dir, f"versiontracker_blacklist_backup_{int(backup.timestamp)}.json")

            backup_data = {
                "blacklist": current_blacklist,
                "timestamp": backup.timestamp,
                "version": "0.6.5",
            }

            with open(backup_file, "w") as f:
                json.dump(backup_data, f, indent=2)

            backup.backup_file = backup_file
            logging.info("Created blacklist backup at: %s", backup_file)

        except Exception as e:
            logging.warning("Failed to create blacklist backup: %s", e)
            # Continue without backup file

        return backup

    def restore_blacklist_from_backup(self, backup: BlacklistBackup) -> bool:
        """Restore blacklist from backup.

        Args:
            backup: BlacklistBackup object

        Returns:
            True if restore was successful
        """
        try:
            self.config.set("blacklist", backup.original_blacklist)
            if self.config.save():
                logging.info("Successfully restored blacklist from backup")
                return True
            else:
                logging.error("Failed to save restored blacklist")
                return False
        except Exception as e:
            logging.error("Failed to restore blacklist from backup: %s", e)
            return False

    def cleanup_backup(self, backup: BlacklistBackup) -> None:
        """Clean up backup file.

        Args:
            backup: BlacklistBackup object
        """
        if backup.backup_file and os.path.exists(backup.backup_file):
            try:
                os.remove(backup.backup_file)
                logging.info("Cleaned up backup file: %s", backup.backup_file)
            except Exception as e:
                logging.warning("Failed to clean up backup file: %s", e)

    def handle_save_failure(self, backup: BlacklistBackup) -> int:
        """Handle configuration save failure with rollback.

        Args:
            backup: Backup information

        Returns:
            Exit code 1
        """
        print(self.progress_bar.color("red")("Failed to save configuration."))
        print(self.progress_bar.color("yellow")("Attempting to restore original blacklist..."))

        if self.restore_blacklist_from_backup(backup):
            print(self.progress_bar.color("green")("Successfully restored original blacklist."))
        else:
            print(
                self.progress_bar.color("red")(
                    "Failed to restore original blacklist. Manual intervention may be required."
                )
            )
            print(self.progress_bar.color("blue")(f"Backup available at: {backup.backup_file}"))

        return 1

    def handle_config_error(self, error: Exception, backup: BlacklistBackup) -> int:
        """Handle configuration error with rollback.

        Args:
            error: The exception that occurred
            backup: Backup information

        Returns:
            Exit code 1
        """
        logging.error("Config operation failed: %s", error)
        print(self.progress_bar.color("red")(f"Configuration error: {error}"))
        print(self.progress_bar.color("yellow")("Attempting to restore original blacklist..."))

        if self.restore_blacklist_from_backup(backup):
            print(self.progress_bar.color("green")("Successfully restored original blacklist."))
        else:
            print(self.progress_bar.color("red")("Failed to restore original blacklist."))
            if backup.backup_file:
                print(self.progress_bar.color("blue")(f"Manual restore available from: {backup.backup_file}"))

        return 1
