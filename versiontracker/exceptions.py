"""Custom exceptions for VersionTracker.

This module defines the exception hierarchy used by VersionTracker.
All exceptions derive from VersionTrackerError, which is the base exception class.
Specific error types are organized into categories based on the component they relate to.
"""

from typing import Optional


class VersionTrackerError(Exception):
    """Base exception for all VersionTracker errors.

    All custom exceptions in VersionTracker should inherit from this class.
    This allows applications to catch all VersionTracker-specific errors with
    a single except clause.
    """

    def __init__(self, message: str = "", cause: Optional[Exception] = None) -> None:
        """Initialize the exception.

        Args:
            message: Description of the error
            cause: Optional underlying exception that caused this error
        """
        super().__init__(message)
        self.cause = cause


class NetworkError(VersionTrackerError):
    """Network-related errors.

    This exception is raised when network operations fail, such as:
    - Connection failures
    - DNS resolution errors
    - API request failures
    """

    pass


class HomebrewError(VersionTrackerError):
    """Homebrew-related errors.

    This exception is raised when operations involving Homebrew fail, such as:
    - Homebrew command execution failures
    - Homebrew not being installed or not found
    - Issues with Homebrew packages or casks
    """

    pass


class DataParsingError(VersionTrackerError):
    """Data parsing errors.

    This exception is raised when parsing data from various sources fails, such as:
    - JSON parsing errors
    - Malformed data structures
    - Missing expected fields in data
    """

    pass


class ConfigError(VersionTrackerError):
    """Configuration errors.

    This exception is raised when there are issues with the configuration, such as:
    - Invalid configuration values
    - Missing required configuration
    - Configuration file not found or inaccessible
    """

    pass


# Redefine built-in errors to avoid conflicts
class BrewPermissionError(HomebrewError):
    """Permission errors when accessing Homebrew.

    This exception is raised when the application doesn't have
    sufficient permissions to execute Homebrew commands.
    """

    pass


class BrewTimeoutError(NetworkError):
    """Timeout errors when accessing Homebrew.

    This exception is raised when Homebrew operations take too long to complete,
    such as when downloading packages or updating the repository.
    """

    pass


# Additional exception classes
class CacheError(VersionTrackerError):
    """Cache-related errors.

    This exception is raised when there are issues with the cache, such as:
    - Cache corruption
    - Cache file access problems
    - Cache validation failures
    """

    pass


class ExportError(VersionTrackerError):
    """Export-related errors.

    This exception is raised when exporting data fails, such as:
    - File writing errors
    - Format conversion errors
    - Invalid export formats
    """

    pass


# Custom versions of built-in exceptions that are used in utils.py
class FileNotFoundError(VersionTrackerError):
    """File not found errors.

    This exception is raised when a file cannot be found at the specified path.
    """

    pass


class PermissionError(VersionTrackerError):
    """Permission errors.

    This exception is raised when the application doesn't have
    sufficient permissions to access a file or directory.
    """

    pass


class TimeoutError(VersionTrackerError):
    """Timeout errors.

    This exception is raised when an operation takes too long to complete.
    """

    pass


# Version-related exceptions
class VersionError(VersionTrackerError):
    """Version-related errors.

    This exception is raised when there are issues with version parsing, comparison,
    or validation, such as:
    - Invalid version string format
    - Version comparison failures
    - Missing version information
    """

    pass


# Validation exceptions
class ValidationError(VersionTrackerError):
    """Validation errors.

    This exception is raised when validation fails for any input data,
    such as command-line arguments, configuration values, or API responses.
    """

    pass
