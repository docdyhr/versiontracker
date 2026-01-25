"""Enhanced handler functions for auto-update operations with improved error handling.

This module provides enhanced versions of auto-update handlers with:
- Better partial failure handling
- Detailed error reporting and recovery
- Transaction-like consistency
- Rollback mechanisms for critical failures

The functionality is organized into focused submodules:
- auto_update_types: Data classes and enums (OperationResult, UninstallResult, BlacklistBackup)
- backup_handlers: Backup and restore operations (BackupManager)
"""

import logging
from typing import Any

from versiontracker.app_finder import get_homebrew_casks
from versiontracker.config import get_config

# Import types from dedicated module
from versiontracker.handlers.auto_update_types import (
    BlacklistBackup,
    OperationResult,
    UninstallResult,
)
from versiontracker.handlers.backup_handlers import BackupManager
from versiontracker.homebrew import get_casks_with_auto_updates
from versiontracker.ui import create_progress_bar
from versiontracker.utils import run_command

# Re-export for backward compatibility
__all__ = [
    "OperationResult",
    "UninstallResult",
    "BlacklistBackup",
    "EnhancedAutoUpdateHandler",
    "handle_blacklist_auto_updates_enhanced",
    "handle_uninstall_auto_updates_enhanced",
]


class EnhancedAutoUpdateHandler:
    """Enhanced auto-update handler with improved error handling."""

    def __init__(self) -> None:
        """Initialize the enhanced handler."""
        self.progress_bar = create_progress_bar()
        self.config = get_config()
        self.backup_manager = BackupManager(self.config)

    def _create_blacklist_backup(self, current_blacklist: list[str]) -> BlacklistBackup:
        """Create a backup of the current blacklist configuration.

        Args:
            current_blacklist: Current blacklist items

        Returns:
            BlacklistBackup object with backup information
        """
        return self.backup_manager.create_blacklist_backup(current_blacklist)

    def _restore_blacklist_from_backup(self, backup: BlacklistBackup) -> bool:
        """Restore blacklist from backup.

        Args:
            backup: BlacklistBackup object

        Returns:
            True if restore was successful
        """
        return self.backup_manager.restore_blacklist_from_backup(backup)

    def _cleanup_backup(self, backup: BlacklistBackup) -> None:
        """Clean up backup file.

        Args:
            backup: BlacklistBackup object
        """
        self.backup_manager.cleanup_backup(backup)

    def _get_auto_update_casks_info(self) -> tuple[list[str] | None, list[str] | None]:
        """Get installed casks and those with auto-updates.

        Returns:
            Tuple of (all_casks, auto_update_casks) or (None, None) if error
        """
        # Get all installed Homebrew casks
        print(self.progress_bar.color("green")("Getting installed Homebrew casks..."))
        all_casks = get_homebrew_casks()

        if not all_casks:
            print(self.progress_bar.color("yellow")("No Homebrew casks found."))
            return None, None

        # Find casks with auto-updates
        print(self.progress_bar.color("green")("Checking for auto-updates..."))
        auto_update_casks = get_casks_with_auto_updates(all_casks)

        if not auto_update_casks:
            print(self.progress_bar.color("yellow")("No casks with auto-updates found."))
            return None, None

        return all_casks, auto_update_casks

    def _calculate_new_additions(self, auto_update_casks: list[str], current_blacklist: list[str]) -> list[str]:
        """Calculate which casks need to be added to blacklist.

        Args:
            auto_update_casks: List of casks with auto-updates
            current_blacklist: Current blacklisted casks

        Returns:
            List of casks to be added to blacklist
        """
        new_additions = []
        for cask in auto_update_casks:
            if cask not in current_blacklist:
                new_additions.append(cask)
        return new_additions

    def _display_blacklist_preview(
        self, auto_update_casks: list[str], current_blacklist: list[str], new_additions: list[str]
    ) -> None:
        """Display preview of what will be blacklisted.

        Args:
            auto_update_casks: All casks with auto-updates
            current_blacklist: Current blacklisted casks
            new_additions: Casks to be added
        """
        print(self.progress_bar.color("blue")(f"\nFound {len(auto_update_casks)} casks with auto-updates:"))
        for cask in auto_update_casks:
            status = " (already blacklisted)" if cask in current_blacklist else " (will be added)"
            color = "yellow" if cask in current_blacklist else "green"
            print(f"  - {self.progress_bar.color(color)(cask)}{status}")

    def _get_user_confirmation(self, new_additions_count: int) -> bool:
        """Get user confirmation for blacklist operation.

        Args:
            new_additions_count: Number of casks to be added

        Returns:
            True if user confirms, False otherwise
        """
        print(self.progress_bar.color("yellow")(f"\nThis will add {new_additions_count} casks to the blacklist."))
        print(self.progress_bar.color("blue")("A backup of your current blacklist has been created."))
        response = input("Do you want to continue? [y/N]: ").strip().lower()
        return response == "y"

    def _perform_blacklist_update(
        self, current_blacklist: list[str], new_additions: list[str], backup: BlacklistBackup
    ) -> int:
        """Perform the actual blacklist update with rollback capability.

        Args:
            current_blacklist: Current blacklisted casks
            new_additions: Casks to add
            backup: Backup information

        Returns:
            Exit code (0 for success, 1 for failure)
        """
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
                return self._handle_save_failure(backup)

        except Exception as e:
            return self._handle_config_error(e, backup)

    def _handle_save_failure(self, backup: BlacklistBackup) -> int:
        """Handle configuration save failure with rollback.

        Args:
            backup: Backup information

        Returns:
            Exit code 1
        """
        return self.backup_manager.handle_save_failure(backup)

    def _handle_config_error(self, error: Exception, backup: BlacklistBackup) -> int:
        """Handle configuration error with rollback.

        Args:
            error: The exception that occurred
            backup: Backup information

        Returns:
            Exit code 1
        """
        return self.backup_manager.handle_config_error(error, backup)

    def handle_blacklist_auto_updates_enhanced(self, options: Any) -> int:
        """Enhanced version of blacklist auto-updates with better error handling.

        Args:
            options: Command line options

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        backup = None

        try:
            # Get casks information
            all_casks, auto_update_casks = self._get_auto_update_casks_info()
            if all_casks is None or auto_update_casks is None:
                return 0

            # Get current blacklist and create backup
            current_blacklist = self.config.get("blacklist", [])
            backup = self._create_blacklist_backup(current_blacklist)

            # Calculate what needs to be added
            new_additions = self._calculate_new_additions(auto_update_casks, current_blacklist)

            if not new_additions:
                print(self.progress_bar.color("yellow")("All casks with auto-updates are already blacklisted."))
                self._cleanup_backup(backup)
                return 0

            # Show preview and get confirmation
            self._display_blacklist_preview(auto_update_casks, current_blacklist, new_additions)

            if not self._get_user_confirmation(len(new_additions)):
                print(self.progress_bar.color("yellow")("Operation cancelled."))
                self._cleanup_backup(backup)
                return 0

            # Perform the update
            return self._perform_blacklist_update(current_blacklist, new_additions, backup)

        except Exception as e:
            logging.error(f"Critical error in blacklist operation: {e}")
            print(self.progress_bar.color("red")(f"Critical error: {e}"))

            if backup and backup.backup_file:
                print(self.progress_bar.color("blue")(f"Backup available at: {backup.backup_file}"))

            return 1

    def _classify_uninstall_error(self, error_output: str, return_code: int) -> tuple[bool, str]:
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

    def _display_uninstall_preview(self, auto_update_casks: list[str]) -> None:
        """Display preview of casks to be uninstalled.

        Args:
            auto_update_casks: List of casks with auto-updates
        """
        print(self.progress_bar.color("blue")(f"\nFound {len(auto_update_casks)} casks with auto-updates:"))
        for i, cask in enumerate(auto_update_casks, 1):
            print(f"{i:3d}. {self.progress_bar.color('yellow')(cask)}")

    def _get_uninstall_confirmation(self, cask_count: int) -> bool:
        """Get double confirmation from user for uninstall operation.

        Args:
            cask_count: Number of casks to be uninstalled

        Returns:
            True if user confirms twice, False otherwise
        """
        # First confirmation
        print(self.progress_bar.color("red")(f"\n⚠️  This will UNINSTALL {cask_count} applications!"))
        print(self.progress_bar.color("yellow")("This action cannot be undone."))
        print(self.progress_bar.color("blue")("Detailed progress and error information will be provided."))
        response = input("Are you sure you want to continue? [y/N]: ").strip().lower()

        if response != "y":
            print(self.progress_bar.color("yellow")("Operation cancelled."))
            return False

        # Double confirmation for safety
        print(
            self.progress_bar.color("red")(
                "\nPlease type 'UNINSTALL' to confirm you want to remove these applications:"
            )
        )
        confirmation = input().strip()

        if confirmation != "UNINSTALL":
            print(self.progress_bar.color("yellow")("Operation cancelled."))
            return False

        return True

    def _uninstall_single_cask(self, cask: str) -> UninstallResult:
        """Uninstall a single cask and return the result.

        Args:
            cask: Name of the cask to uninstall

        Returns:
            UninstallResult with the operation outcome
        """
        try:
            # Run brew uninstall command with timeout
            command = f"brew uninstall --cask {cask}"
            stdout, returncode = run_command(command, timeout=60)

            if returncode == 0:
                print(self.progress_bar.color("green")("✓"))
                return UninstallResult(cask, True)
            else:
                is_critical, error_category = self._classify_uninstall_error(stdout, returncode)
                print(self.progress_bar.color("red")("✗"))
                print(f"    └─ {self.progress_bar.color('red')(error_category)}")

                result = UninstallResult(cask, False, error_category, is_critical)

                if is_critical:
                    print(f"    └─ {self.progress_bar.color('red')('⚠️  CRITICAL ERROR DETECTED')}")

                return result

        except TimeoutError:
            print(self.progress_bar.color("red")("✗ (timeout)"))
            print(f"    └─ {self.progress_bar.color('yellow')('Operation timed out after 60 seconds')}")
            return UninstallResult(cask, False, "Timeout after 60 seconds", False)

        except Exception as e:
            print(self.progress_bar.color("red")("✗ (error)"))
            print(f"    └─ {self.progress_bar.color('red')(str(e))}")
            is_critical = "system" in str(e).lower() or "critical" in str(e).lower()
            return UninstallResult(cask, False, str(e), is_critical)

    def _perform_uninstalls(self, auto_update_casks: list[str]) -> tuple[list[UninstallResult], list[tuple[str, str]]]:
        """Perform the actual uninstall operations.

        Args:
            auto_update_casks: List of casks to uninstall

        Returns:
            Tuple of (all_results, critical_errors)
        """
        results: list[UninstallResult] = []
        critical_errors = []

        print(self.progress_bar.color("blue")("\nUninstalling casks with detailed progress..."))
        print(self.progress_bar.color("blue")("=" * 60))

        for i, cask in enumerate(auto_update_casks, 1):
            print(f"[{i}/{len(auto_update_casks)}] Uninstalling {self.progress_bar.color('yellow')(cask)}...", end=" ")

            result = self._uninstall_single_cask(cask)
            results.append(result)

            if result.is_critical:
                critical_errors.append((cask, result.error_message or "Unknown critical error"))

        return results, critical_errors

    def _display_summary_header(self) -> None:
        """Display the summary section header."""
        print(self.progress_bar.color("blue")("\n" + "=" * 60))
        print(self.progress_bar.color("blue")("UNINSTALL OPERATION SUMMARY"))
        print(self.progress_bar.color("blue")("=" * 60))

    def _display_successful_results(self, successful: list[UninstallResult]) -> None:
        """Display successful uninstall results.

        Args:
            successful: List of successful uninstall results
        """
        print(self.progress_bar.color("green")(f"✓ Successfully uninstalled: {len(successful)}"))
        if successful:
            for result in successful:
                print(f"  - {result.app_name}")

    def _group_and_display_failures(self, failed: list[UninstallResult]) -> None:
        """Group failures by error type and display them.

        Args:
            failed: List of failed uninstall results
        """
        if not failed:
            return

        print(self.progress_bar.color("red")(f"✗ Failed to uninstall: {len(failed)}"))

        # Group failures by error type
        error_groups: dict[str, list[str]] = {}
        for result in failed:
            error_msg = result.error_message or "Unknown error"
            if error_msg not in error_groups:
                error_groups[error_msg] = []
            error_groups[error_msg].append(result.app_name)

        for error_msg, apps in error_groups.items():
            print(f"\n  {self.progress_bar.color('red')(error_msg)}:")
            for app in apps:
                print(f"    - {app}")

    def _display_critical_errors(self, critical_errors: list[tuple[str, str]]) -> None:
        """Display critical error information.

        Args:
            critical_errors: List of (app_name, error_message) tuples
        """
        if critical_errors:
            print(self.progress_bar.color("red")("\n⚠️  CRITICAL ERRORS DETECTED:"))
            for app, error in critical_errors:
                print(f"  - {app}: {error}")
            print(self.progress_bar.color("yellow")("Please review system stability and consider manual intervention."))

    def _provide_failure_recommendations(self, failed: list[UninstallResult]) -> None:
        """Provide recommendations based on failure types.

        Args:
            failed: List of failed uninstall results
        """
        print(self.progress_bar.color("blue")("\nRECOMMENDATIONS:"))
        if not failed:
            return

        permission_failures = [r for r in failed if "permission" in (r.error_message or "").lower()]
        dependency_failures = [r for r in failed if "dependency" in (r.error_message or "").lower()]
        running_failures = [r for r in failed if "running" in (r.error_message or "").lower()]

        if permission_failures:
            print(f"  • Run with elevated privileges for: {', '.join([r.app_name for r in permission_failures])}")
        if dependency_failures:
            dep_apps = ", ".join([r.app_name for r in dependency_failures])
            print(f"  • Resolve dependencies before uninstalling: {dep_apps}")
        if running_failures:
            running_apps = ", ".join([r.app_name for r in running_failures])
            print(f"  • Close applications before uninstalling: {running_apps}")

    def _determine_exit_code(self, critical_errors: list[tuple[str, str]], failed: list[UninstallResult]) -> int:
        """Determine appropriate exit code based on results.

        Args:
            critical_errors: List of critical errors
            failed: List of failed results

        Returns:
            Exit code (0=success, 1=partial failure, 2=critical failure)
        """
        if critical_errors:
            return 2  # Critical failure
        elif failed:
            return 1  # Partial failure
        else:
            return 0  # Complete success

    def handle_uninstall_auto_updates_enhanced(self, options: Any) -> int:
        """Enhanced version of uninstall auto-updates with detailed error handling.

        Args:
            options: Command line options

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Get casks information (reuse from blacklist function)
            all_casks, auto_update_casks = self._get_auto_update_casks_info()
            if all_casks is None or auto_update_casks is None:
                return 0

            # Show what will be uninstalled and get confirmation
            self._display_uninstall_preview(auto_update_casks)

            if not self._get_uninstall_confirmation(len(auto_update_casks)):
                return 0

            # Perform the uninstalls
            results, critical_errors = self._perform_uninstalls(auto_update_casks)

            # Analyze results
            successful = [r for r in results if r.success]
            failed = [r for r in results if not r.success]

            # Display comprehensive report
            self._display_summary_header()
            self._display_successful_results(successful)
            self._group_and_display_failures(failed)
            self._display_critical_errors(critical_errors)
            self._provide_failure_recommendations(failed)

            return self._determine_exit_code(critical_errors, failed)

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
