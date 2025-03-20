"""Custom exceptions for VersionTracker."""


class VersionTrackerError(Exception):
    """Base exception for all VersionTracker errors."""

    pass


class NetworkError(VersionTrackerError):
    """Raised when a network operation fails."""

    pass


class TimeoutError(NetworkError):
    """Raised when a network operation times out."""

    pass


class PermissionError(VersionTrackerError):
    """Raised when a permission-related operation fails."""

    pass


class ConfigError(VersionTrackerError):
    """Raised when there's an issue with the configuration."""

    pass


class DataParsingError(VersionTrackerError):
    """Raised when there's an issue parsing data."""

    pass


class VersionError(VersionTrackerError):
    """Raised when there's an issue with version comparison or parsing."""

    pass


class HomebrewError(VersionTrackerError):
    """Raised when there's an issue with Homebrew operations."""

    pass


class ExportError(VersionTrackerError):
    """Raised when there's an issue exporting data."""

    pass


class CacheError(VersionTrackerError):
    """Raised when there's an issue with the cache."""

    pass


class FileNotFoundError(VersionTrackerError):
    """Raised when a file or command is not found."""

    pass
