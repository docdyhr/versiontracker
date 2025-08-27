"""Custom exception hierarchy for VersionTracker.

This module defines all custom exceptions used throughout the application,
following the established error handling patterns.
"""


class VersionTrackerError(Exception):
    """Base exception for all VersionTracker errors."""

    pass


class ConfigError(VersionTrackerError):
    """Raised when there's an error in configuration."""

    pass


class VersionError(VersionTrackerError):
    """Raised when there's an error parsing or comparing versions."""

    pass


class NetworkError(VersionTrackerError):
    """Raised when network operations fail."""

    pass


class TimeoutError(VersionTrackerError):
    """Raised when an operation times out."""

    pass


class HomebrewError(VersionTrackerError):
    """Raised when Homebrew operations fail."""

    pass


class ApplicationError(VersionTrackerError):
    """Raised when there's an error with application detection or processing."""

    pass


class CacheError(VersionTrackerError):
    """Raised when cache operations fail."""

    pass


class HandlerError(VersionTrackerError):
    """Raised when a command handler encounters an error."""

    pass
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
