"""
Structured error codes system for VersionTracker.

This module provides a comprehensive error code system with structured
error reporting, categorization, and user-friendly messages.
"""

from enum import Enum
from typing import Any


class ErrorCategory(Enum):
    """Error categories for grouping related errors."""

    SYSTEM = "SYS"
    NETWORK = "NET"
    HOMEBREW = "HBW"
    APPLICATION = "APP"
    VERSION = "VER"
    CONFIG = "CFG"
    PERMISSION = "PRM"
    VALIDATION = "VAL"
    CACHE = "CHE"
    EXPORT = "EXP"


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCode(Enum):
    """Structured error codes for VersionTracker."""

    # System errors (SYS001-SYS099)
    SYS001 = ("SYS001", "System command execution failed", ErrorSeverity.HIGH)
    SYS002 = ("SYS002", "Platform not supported", ErrorSeverity.CRITICAL)
    SYS003 = ("SYS003", "Required system dependency missing", ErrorSeverity.HIGH)
    SYS004 = ("SYS004", "System resources exhausted", ErrorSeverity.MEDIUM)
    SYS005 = ("SYS005", "Process timeout", ErrorSeverity.MEDIUM)

    # Network errors (NET001-NET099)
    NET001 = ("NET001", "Network connection failed", ErrorSeverity.HIGH)
    NET002 = ("NET002", "Request timeout", ErrorSeverity.MEDIUM)
    NET003 = ("NET003", "Invalid response format", ErrorSeverity.MEDIUM)
    NET004 = ("NET004", "Rate limit exceeded", ErrorSeverity.MEDIUM)
    NET005 = ("NET005", "Authentication failed", ErrorSeverity.HIGH)
    NET006 = ("NET006", "Server error", ErrorSeverity.HIGH)
    NET007 = ("NET007", "DNS resolution failed", ErrorSeverity.HIGH)

    # Homebrew errors (HBW001-HBW099)
    HBW001 = ("HBW001", "Homebrew not installed", ErrorSeverity.CRITICAL)
    HBW002 = ("HBW002", "Homebrew command failed", ErrorSeverity.HIGH)
    HBW003 = ("HBW003", "Cask not found", ErrorSeverity.MEDIUM)
    HBW004 = ("HBW004", "Invalid cask information", ErrorSeverity.MEDIUM)
    HBW005 = ("HBW005", "Homebrew update required", ErrorSeverity.MEDIUM)
    HBW006 = ("HBW006", "Cask installation failed", ErrorSeverity.HIGH)
    HBW007 = ("HBW007", "Tap not available", ErrorSeverity.MEDIUM)

    # Application errors (APP001-APP099)
    APP001 = ("APP001", "Application not found", ErrorSeverity.MEDIUM)
    APP002 = ("APP002", "Invalid application bundle", ErrorSeverity.MEDIUM)
    APP003 = ("APP003", "Application version detection failed", ErrorSeverity.MEDIUM)
    APP004 = ("APP004", "Application metadata corrupted", ErrorSeverity.MEDIUM)
    APP005 = ("APP005", "Application directory access denied", ErrorSeverity.HIGH)
    APP006 = ("APP006", "Multiple applications with same name", ErrorSeverity.LOW)

    # Version errors (VER001-VER099)
    VER001 = ("VER001", "Version string parsing failed", ErrorSeverity.MEDIUM)
    VER002 = ("VER002", "Invalid version format", ErrorSeverity.MEDIUM)
    VER003 = ("VER003", "Version comparison failed", ErrorSeverity.MEDIUM)
    VER004 = ("VER004", "Unsupported version scheme", ErrorSeverity.LOW)

    # Configuration errors (CFG001-CFG099)
    CFG001 = ("CFG001", "Configuration file not found", ErrorSeverity.LOW)
    CFG002 = ("CFG002", "Invalid configuration format", ErrorSeverity.HIGH)
    CFG003 = ("CFG003", "Configuration validation failed", ErrorSeverity.HIGH)
    CFG004 = ("CFG004", "Configuration save failed", ErrorSeverity.MEDIUM)
    CFG005 = ("CFG005", "Environment variable invalid", ErrorSeverity.MEDIUM)

    # Permission errors (PRM001-PRM099)
    PRM001 = ("PRM001", "File access permission denied", ErrorSeverity.HIGH)
    PRM002 = ("PRM002", "Directory creation failed", ErrorSeverity.HIGH)
    PRM003 = ("PRM003", "File write permission denied", ErrorSeverity.HIGH)
    PRM004 = ("PRM004", "Elevated privileges required", ErrorSeverity.HIGH)

    # Validation errors (VAL001-VAL099)
    VAL001 = ("VAL001", "Invalid command line argument", ErrorSeverity.MEDIUM)
    VAL002 = ("VAL002", "Missing required parameter", ErrorSeverity.HIGH)
    VAL003 = ("VAL003", "Parameter validation failed", ErrorSeverity.MEDIUM)
    VAL004 = ("VAL004", "Incompatible options provided", ErrorSeverity.MEDIUM)

    # Cache errors (CHE001-CHE099)
    CHE001 = ("CHE001", "Cache file corrupted", ErrorSeverity.LOW)
    CHE002 = ("CHE002", "Cache directory access failed", ErrorSeverity.MEDIUM)
    CHE003 = ("CHE003", "Cache cleanup failed", ErrorSeverity.LOW)
    CHE004 = ("CHE004", "Cache size limit exceeded", ErrorSeverity.LOW)

    # Export errors (EXP001-EXP099)
    EXP001 = ("EXP001", "Export format not supported", ErrorSeverity.MEDIUM)
    EXP002 = ("EXP002", "Export file write failed", ErrorSeverity.HIGH)
    EXP003 = ("EXP003", "Export data serialization failed", ErrorSeverity.MEDIUM)
    EXP004 = ("EXP004", "Export template not found", ErrorSeverity.MEDIUM)

    def __init__(self, code: str, message: str, severity: ErrorSeverity):
        """Initialize error code with metadata."""
        self.code = code
        self.message = message
        self.severity = severity
        self.category = ErrorCategory(code[:3])


class StructuredError:
    """Structured error with detailed information and context."""

    def __init__(
        self,
        error_code: ErrorCode,
        details: str | None = None,
        context: dict[str, Any] | None = None,
        suggestions: list[str] | None = None,
        original_exception: Exception | None = None,
    ):
        """Initialize structured error.

        Args:
            error_code: The error code enum
            details: Additional error details
            context: Context information (file paths, values, etc.)
            suggestions: User-actionable suggestions to fix the error
            original_exception: Original exception that caused this error
        """
        self.error_code = error_code
        self.details = details or ""
        self.context = context or {}
        self.suggestions = suggestions or []
        self.original_exception = original_exception

    @property
    def code(self) -> str:
        """Get the error code string."""
        return self.error_code.code

    @property
    def message(self) -> str:
        """Get the error message."""
        return self.error_code.message

    @property
    def severity(self) -> ErrorSeverity:
        """Get the error severity."""
        return self.error_code.severity

    @property
    def category(self) -> ErrorCategory:
        """Get the error category."""
        return self.error_code.category

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "details": self.details,
            "context": self.context,
            "suggestions": self.suggestions,
            "original_exception": str(self.original_exception) if self.original_exception else None,
        }

    def format_user_message(self) -> str:
        """Format a user-friendly error message."""
        lines = [f"Error {self.code}: {self.message}"]

        if self.details:
            lines.append(f"Details: {self.details}")

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            lines.append(f"Context: {context_str}")

        if self.suggestions:
            lines.append("Suggestions:")
            for i, suggestion in enumerate(self.suggestions, 1):
                lines.append(f"  {i}. {suggestion}")

        return "\n".join(lines)

    def __str__(self) -> str:
        """String representation of the error."""
        return f"{self.code}: {self.message}"

    def __repr__(self) -> str:
        """Detailed representation of the error."""
        return (
            f"StructuredError(code={self.code}, message='{self.message}', "
            f"severity={self.severity.value}, category={self.category.value})"
        )


# Predefined error suggestions for common issues
ERROR_SUGGESTIONS = {
    ErrorCode.HBW001: [
        "Install Homebrew from https://brew.sh",
        "Ensure Homebrew is in your PATH",
        "Run 'which brew' to verify installation",
    ],
    ErrorCode.NET001: [
        "Check your internet connection",
        "Verify proxy settings if using a corporate network",
        "Try again after a few minutes",
    ],
    ErrorCode.CFG002: [
        "Check YAML syntax in configuration file",
        "Validate configuration against schema",
        "Use 'versiontracker --generate-config' to create a new config",
    ],
    ErrorCode.PRM001: [
        "Check file permissions with 'ls -la'",
        "Ensure you have read access to the file",
        "Run with appropriate user privileges",
    ],
    ErrorCode.VAL002: [
        "Check command syntax with 'versiontracker --help'",
        "Ensure all required parameters are provided",
        "Review command documentation",
    ],
}


def create_error(
    error_code: ErrorCode,
    details: str | None = None,
    context: dict[str, Any] | None = None,
    original_exception: Exception | None = None,
) -> StructuredError:
    """Create a structured error with automatic suggestions.

    Args:
        error_code: The error code enum
        details: Additional error details
        context: Context information
        original_exception: Original exception that caused this error

    Returns:
        StructuredError: Configured structured error
    """
    suggestions = ERROR_SUGGESTIONS.get(error_code, [])
    return StructuredError(
        error_code=error_code,
        details=details,
        context=context,
        suggestions=suggestions,
        original_exception=original_exception,
    )


def get_errors_by_category(category: ErrorCategory) -> list[ErrorCode]:
    """Get all error codes in a specific category.

    Args:
        category: Error category to filter by

    Returns:
        list[ErrorCode]: List of error codes in the category
    """
    return [error for error in ErrorCode if error.category == category]


def get_errors_by_severity(severity: ErrorSeverity) -> list[ErrorCode]:
    """Get all error codes with a specific severity.

    Args:
        severity: Error severity to filter by

    Returns:
        list[ErrorCode]: List of error codes with the severity
    """
    return [error for error in ErrorCode if error.severity == severity]
