"""Type definitions for auto-update operations.

This module provides data classes and enums used by auto-update handlers
for consistent type handling across blacklist and uninstall operations.
"""

from dataclasses import dataclass
from enum import Enum


class OperationResult(Enum):
    """Result types for operations."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"
    CANCELLED = "cancelled"
    CRITICAL_FAILURE = "critical_failure"


@dataclass
class UninstallResult:
    """Result of an individual uninstall operation.

    Attributes:
        app_name: Name of the application that was uninstalled
        success: Whether the uninstall was successful
        error_message: Error message if the operation failed
        is_critical: Whether the error is critical (affects system stability)
    """

    app_name: str
    success: bool
    error_message: str | None = None
    is_critical: bool = False


@dataclass
class BlacklistBackup:
    """Backup information for blacklist operations.

    Attributes:
        original_blacklist: Original list of blacklisted items before changes
        backup_file: Path to the backup file on disk
        timestamp: Unix timestamp when the backup was created
    """

    original_blacklist: list[str]
    backup_file: str | None = None
    timestamp: float = 0.0
