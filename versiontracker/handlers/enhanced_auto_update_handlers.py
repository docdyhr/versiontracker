"""Enhanced handler functions for auto-update operations with improved error handling.

This module provides enhanced versions of auto-update handlers with:
- Better partial failure handling
- Detailed error reporting and recovery
- Transaction-like consistency
- Rollback mechanisms for critical failures
"""

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from versiontracker.apps import get_homebrew_casks
from versiontracker.config import get_config
from versiontracker.exceptions import ConfigError, HomebrewError
from versiontracker.homebrew import get_casks_with_auto_updates
from versiontracker.ui import create_progress_bar
from versiontracker.utils import run_command


class OperationResult(Enum):
    """Result types for operations."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"
    CANCELLED = "cancelled"
    CRITICAL_FAILURE = "critical_failure"


@dataclass
class UninstallResult:
    """Result of an individual uninstall operation."""

    app_name: str
    success: bool
    error_message: Optional[str] = None
    is_critical: bool = False


@dataclass
class BlacklistBackup:
    """Backup information for blacklist operations."""

    original_blacklist: List[str]
    backup_file: Optional[str] = None
    timestamp: float = 0.0


class EnhancedAutoUpdateHandler:
    """Enhanced auto-update handler with improved error handling."""

    def __init__(self):
        """Initialize the enhanced handler."""
        self.progress_bar = create_progress_bar()
        self.config = get_config()

    def _create_blacklist_backup(self, current_blacklist: List[str]) -> BlacklistBackup:
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

            backup_data = {"blacklist": current_blacklist, "timestamp": backup.timestamp, "version": "0.6.5"}

            with open(backup_file, "w") as f:
                json.dump(backup_data, f, indent=2)

            backup.backup_file = backup_file
            logging.info(f"Created blacklist backup at: {backup_file}")

        except Exception as e:
            logging.warning(f"Failed to create blacklist backup: {e}")
            # Continue without backup file

        return backup

    def _restore_blacklist_from_backup(self, backup: BlacklistBackup) -> bool:
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
            logging.error(f"Failed to restore blacklist from backup: {e}")
            return False

    def _cleanup_backup(self, backup: BlacklistBackup) -> None:
        """Clean up backup file.

        Args:
            backup: BlacklistBackup object
        """
        if backup.backup_file and os.path.exists(backup.backup_file):
            try:
                os.remove(backup.backup_file)
                logging.info(f"Cleaned up backup file: {backup.backup_file}")
            except Exception as e:
                logging.warning(f"Failed to clean up backup file: {e}")

    def handle_blacklist_auto_updates_enhanced(self, options: Any) -> int:
        """Enhanced version of blacklist auto-updates with better error handling.

        Args:
            options: Command line options

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        backup = None

        try:
            # Get all installed Homebrew casks
            print(self.progress_bar.color("green")("Getting installed Homebrew casks..."))
            all_casks = get_homebrew_casks()

            if not all_casks:
                print(self.progress_bar.color("yellow")("No Homebrew casks found."))
                return 0

            # Find casks with auto-updates
            print(self.progress_bar.color("green")("Checking for auto-updates..."))
            auto_update_casks = get_casks_with_auto_updates(all_casks)

            if not auto_update_casks:
                print(self.progress_bar.color("yellow")("No casks with auto-updates found."))
                return 0

            # Get current blacklist and create backup
            current_blacklist = self.config.get("blacklist", [])
            backup = self._create_blacklist_backup(current_blacklist)

            new_additions = []

            # Find which casks are not already blacklisted
            for cask in auto_update_casks:
                if cask not in current_blacklist:
                    new_additions.append(cask)

            if not new_additions:
                print(self.progress_bar.color("yellow")("All casks with auto-updates are already blacklisted."))
                self._cleanup_backup(backup)
                return 0

            # Show what will be added
            print(self.progress_bar.color("blue")(f"\nFound {len(auto_update_casks)} casks with auto-updates:"))
            for cask in auto_update_casks:
                status = " (already blacklisted)" if cask in current_blacklist else " (will be added)"
                color = "yellow" if cask in current_blacklist else "green"
                print(f"  - {self.progress_bar.color(color)(cask)}{status}")

            # Ask for confirmation
            print(self.progress_bar.color("yellow")(f"\nThis will add {len(new_additions)} casks to the blacklist."))
            print(self.progress_bar.color("blue")("A backup of your current blacklist has been created."))
            response = input("Do you want to continue? [y/N]: ").strip().lower()

            if response != "y":
                print(self.progress_bar.color("yellow")("Operation cancelled."))
                self._cleanup_backup(backup)
                return 0

            # Perform the blacklist update with transaction-like behavior
            try:
                updated_blacklist = current_blacklist + new_additions
                self.config.set("blacklist", updated_blacklist)

                # Attempt to save
                if self.config.save():
                    print(
                        self.progress_bar.color("green")(
                            f"\n✓ Successfully added {len(new_additions)} casks to the blacklist."
                        )
                    )
                    print(self.progress_bar.color("blue")(f"Total blacklisted items: {len(updated_blacklist)}"))
                    self._cleanup_backup(backup)
                    return 0
                else:
                    # Save failed - attempt rollback
                    print(self.progress_bar.color("red")("Failed to save configuration."))
                    print(self.progress_bar.color("yellow")("Attempting to restore original blacklist..."))

                    if self._restore_blacklist_from_backup(backup):
                        print(self.progress_bar.color("green")("Successfully restored original blacklist."))
                    else:
                        print(
                            self.progress_bar.color("red")(
                                "Failed to restore original blacklist. Manual intervention may be required."
                            )
                        )
                        print(self.progress_bar.color("blue")(f"Backup available at: {backup.backup_file}"))

                    return 1

            except Exception as e:
                # Config operation failed - attempt rollback
                logging.error(f"Config operation failed: {e}")
                print(self.progress_bar.color("red")(f"Configuration error: {e}"))
                print(self.progress_bar.color("yellow")("Attempting to restore original blacklist..."))

                if self._restore_blacklist_from_backup(backup):
                    print(self.progress_bar.color("green")("Successfully restored original blacklist."))
                else:
                    print(self.progress_bar.color("red")("Failed to restore original blacklist."))
                    if backup.backup_file:
                        print(self.progress_bar.color("blue")(f"Manual restore available from: {backup.backup_file}"))

                return 1

        except Exception as e:
            logging.error(f"Critical error in blacklist operation: {e}")
            print(self.progress_bar.color("red")(f"Critical error: {e}"))

            if backup and backup.backup_file:
                print(self.progress_bar.color("blue")(f"Backup available at: {backup.backup_file}"))

            return 1

    def _classify_uninstall_error(self, error_output: str, return_code: int) -> Tuple[bool, str]:
        """Classify uninstall error to determine if it's critical.

        Args:
            error_output: Error output from uninstall command
            return_code: Return code from command

        Returns:
            Tuple of (is_critical, categorized_error_message)
        """
        error_lower = error_output.lower()

        # Critical errors that might affect system stability
        critical_indicators = ["system integrity", "kernel", "critical system", "boot", "filesystem corruption"]

        # Dependency-related errors (usually not critical)
        dependency_indicators = ["required by", "depends on", "dependency"]

        # Permission errors (can usually be resolved)
        permission_indicators = ["permission denied", "operation not permitted", "insufficient privileges"]

        # App-specific errors (usually safe to continue)
        app_indicators = ["application is running", "app is open", "still running"]

        is_critical = any(indicator in error_lower for indicator in critical_indicators)

        if is_critical:
            return True, "Critical system error detected"
        elif any(indicator in error_lower for indicator in dependency_indicators):
            return False, "Dependency conflict"
        elif any(indicator in error_lower for indicator in permission_indicators):
            return False, "Permission error"
        elif any(indicator in error_lower for indicator in app_indicators):
            return False, "Application is currently running"
        else:
            return False, f"Uninstall failed (code: {return_code})"

    def handle_uninstall_auto_updates_enhanced(self, options: Any) -> int:
        """Enhanced version of uninstall auto-updates with detailed error handling.

        Args:
            options: Command line options

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Get all installed Homebrew casks
            print(self.progress_bar.color("green")("Getting installed Homebrew casks..."))
            all_casks = get_homebrew_casks()

            if not all_casks:
                print(self.progress_bar.color("yellow")("No Homebrew casks found."))
                return 0

            # Find casks with auto-updates
            print(self.progress_bar.color("green")("Checking for auto-updates..."))
            auto_update_casks = get_casks_with_auto_updates(all_casks)

            if not auto_update_casks:
                print(self.progress_bar.color("yellow")("No casks with auto-updates found."))
                return 0

            # Show what will be uninstalled
            print(self.progress_bar.color("blue")(f"\nFound {len(auto_update_casks)} casks with auto-updates:"))
            for i, cask in enumerate(auto_update_casks, 1):
                print(f"{i:3d}. {self.progress_bar.color('yellow')(cask)}")

            # Ask for confirmation
            print(self.progress_bar.color("red")(f"\n⚠️  This will UNINSTALL {len(auto_update_casks)} applications!"))
            print(self.progress_bar.color("yellow")("This action cannot be undone."))
            print(self.progress_bar.color("blue")("Detailed progress and error information will be provided."))
            response = input("Are you sure you want to continue? [y/N]: ").strip().lower()

            if response != "y":
                print(self.progress_bar.color("yellow")("Operation cancelled."))
                return 0

            # Double confirmation for safety
            print(
                self.progress_bar.color("red")(
                    "\nPlease type 'UNINSTALL' to confirm you want to remove these applications:"
                )
            )
            confirmation = input().strip()

            if confirmation != "UNINSTALL":
                print(self.progress_bar.color("yellow")("Operation cancelled."))
                return 0

            # Uninstall each cask with detailed tracking
            results: List[UninstallResult] = []
            critical_errors = []

            print(self.progress_bar.color("blue")("\nUninstalling casks with detailed progress..."))
            print(self.progress_bar.color("blue")("=" * 60))

            for i, cask in enumerate(auto_update_casks, 1):
                print(
                    f"[{i}/{len(auto_update_casks)}] Uninstalling {self.progress_bar.color('yellow')(cask)}...", end=" "
                )

                try:
                    # Run brew uninstall command with timeout
                    command = f"brew uninstall --cask {cask}"
                    stdout, returncode = run_command(command, timeout=60)

                    if returncode == 0:
                        print(self.progress_bar.color("green")("✓"))
                        results.append(UninstallResult(cask, True))
                    else:
                        is_critical, error_category = self._classify_uninstall_error(stdout, returncode)
                        print(self.progress_bar.color("red")("✗"))
                        print(f"    └─ {self.progress_bar.color('red')(error_category)}")

                        result = UninstallResult(cask, False, error_category, is_critical)
                        results.append(result)

                        if is_critical:
                            critical_errors.append((cask, error_category))
                            print(f"    └─ {self.progress_bar.color('red')('⚠️  CRITICAL ERROR DETECTED')}")

                except TimeoutError:
                    print(self.progress_bar.color("red")("✗ (timeout)"))
                    print(f"    └─ {self.progress_bar.color('yellow')('Operation timed out after 60 seconds')}")
                    results.append(UninstallResult(cask, False, "Timeout after 60 seconds", False))

                except Exception as e:
                    print(self.progress_bar.color("red")("✗ (error)"))
                    print(f"    └─ {self.progress_bar.color('red')(str(e))}")
                    is_critical = "system" in str(e).lower() or "critical" in str(e).lower()
                    result = UninstallResult(cask, False, str(e), is_critical)
                    results.append(result)

                    if is_critical:
                        critical_errors.append((cask, str(e)))

            # Generate detailed report
            successful = [r for r in results if r.success]
            failed = [r for r in results if not r.success]

            print(self.progress_bar.color("blue")("\n" + "=" * 60))
            print(self.progress_bar.color("blue")("UNINSTALL OPERATION SUMMARY"))
            print(self.progress_bar.color("blue")("=" * 60))

            print(self.progress_bar.color("green")(f"✓ Successfully uninstalled: {len(successful)}"))
            if successful:
                for result in successful:
                    print(f"  - {result.app_name}")

            if failed:
                print(self.progress_bar.color("red")(f"✗ Failed to uninstall: {len(failed)}"))

                # Group failures by error type
                error_groups: Dict[str, List[str]] = {}
                for result in failed:
                    error_msg = result.error_message or "Unknown error"
                    if error_msg not in error_groups:
                        error_groups[error_msg] = []
                    error_groups[error_msg].append(result.app_name)

                for error_msg, apps in error_groups.items():
                    print(f"\n  {self.progress_bar.color('red')(error_msg)}:")
                    for app in apps:
                        print(f"    - {app}")

            # Handle critical errors
            if critical_errors:
                print(self.progress_bar.color("red")("\n⚠️  CRITICAL ERRORS DETECTED:"))
                for app, error in critical_errors:
                    print(f"  - {app}: {error}")
                print(
                    self.progress_bar.color("yellow")(
                        "Please review system stability and consider manual intervention."
                    )
                )

            # Provide recommendations
            print(self.progress_bar.color("blue")("\nRECOMMENDATIONS:"))
            if failed:
                permission_failures = [r for r in failed if "permission" in (r.error_message or "").lower()]
                dependency_failures = [r for r in failed if "dependency" in (r.error_message or "").lower()]
                running_failures = [r for r in failed if "running" in (r.error_message or "").lower()]

                if permission_failures:
                    print(
                        f"  • Run with elevated privileges for: {', '.join([r.app_name for r in permission_failures])}"
                    )
                if dependency_failures:
                    dep_apps = ", ".join([r.app_name for r in dependency_failures])
                    print(f"  • Resolve dependencies before uninstalling: {dep_apps}")
                if running_failures:
                    running_apps = ", ".join([r.app_name for r in running_failures])
                    print(f"  • Close applications before uninstalling: {running_apps}")

            # Return appropriate exit code
            if critical_errors:
                return 2  # Critical failure
            elif failed:
                return 1  # Partial failure
            else:
                return 0  # Complete success

        except Exception as e:
            logging.error(f"Critical error in uninstall operation: {e}")
            print(self.progress_bar.color("red")(f"Critical error: {e}"))
            return 2


# Global instance for use by existing interface
_enhanced_handler = EnhancedAutoUpdateHandler()


def handle_blacklist_auto_updates_enhanced(options: Any) -> int:
    """Enhanced blacklist auto-updates handler (wrapper function)."""
    return _enhanced_handler.handle_blacklist_auto_updates_enhanced(options)


def handle_uninstall_auto_updates_enhanced(options: Any) -> int:
    """Enhanced uninstall auto-updates handler (wrapper function)."""
    return _enhanced_handler.handle_uninstall_auto_updates_enhanced(options)
