"""Custom exceptions for VersionTracker."""

class VersionTrackerError(Exception):
    """Base exception for all VersionTracker errors."""
    pass

class NetworkError(VersionTrackerError):
    """Network-related errors."""
    pass

class HomebrewError(VersionTrackerError):
    """Homebrew-related errors."""
    pass

class DataParsingError(VersionTrackerError):
    """Data parsing errors."""
    pass

class ConfigError(VersionTrackerError):
    """Configuration errors."""
    pass

# Redefine built-in errors to avoid conflicts
class BrewPermissionError(HomebrewError):
    """Permission errors when accessing Homebrew."""
    pass

class BrewTimeoutError(NetworkError):
    """Timeout errors when accessing Homebrew."""
    pass

# Add missing exception classes
class CacheError(VersionTrackerError):
    """Cache-related errors."""
    pass

class ExportError(VersionTrackerError):
    """Export-related errors."""
    pass

# Add custom versions of built-in exceptions that are used in utils.py
class FileNotFoundError(VersionTrackerError):
    """File not found errors."""
    pass

class PermissionError(VersionTrackerError):
    """Permission errors."""
    pass

class TimeoutError(VersionTrackerError):
    """Timeout errors."""
    pass

# Add VersionError for version.py
class VersionError(VersionTrackerError):
    """Version-related errors."""
    pass
