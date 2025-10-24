"""Custom exception hierarchy for VersionTracker.

This module defines all custom exceptions used throughout the application,
following the established error handling patterns with structured error support.
"""

from typing import Any

from versiontracker.error_codes import ErrorCode, StructuredError, create_error


class VersionTrackerError(Exception):
    """Base exception for all VersionTracker errors with structured error support."""

    def __init__(
        self,
        message: str = "",
        error_code: ErrorCode | None = None,
        details: str | None = None,
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        """Initialize VersionTracker error with structured error support.

        Args:
            message: Error message (fallback if no error_code provided)
            error_code: Structured error code
            details: Additional error details
            context: Context information
            original_exception: Original exception that caused this error
        """
        self.structured_error: StructuredError | None = None
        if error_code:
            self.structured_error = create_error(
                error_code=error_code,
                details=details,
                context=context,
                original_exception=original_exception,
            )
            super().__init__(self.structured_error.format_user_message())
        else:
            super().__init__(message)

    def get_error_code(self) -> str | None:
        """Get the error code if available."""
        return self.structured_error.code if self.structured_error else None

    def get_context(self) -> dict[str, Any]:
        """Get the error context."""
        return self.structured_error.context if self.structured_error else {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        if self.structured_error:
            return self.structured_error.to_dict()
        return {"message": str(self), "code": None}


class ConfigError(VersionTrackerError):
    """Raised when there's an error in configuration."""

    def __init__(
        self,
        message: str = "Configuration error",
        config_file: str | None = None,
        **kwargs: Any,
    ):
        """Initialize configuration error.

        Args:
            message: Error message
            config_file: Configuration file path that caused the error
            **kwargs: Additional arguments for VersionTrackerError
        """
        context = kwargs.get("context", {})
        if config_file:
            context["config_file"] = config_file
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class VersionError(VersionTrackerError):
    """Raised when there's an error parsing or comparing versions."""

    def __init__(
        self,
        message: str = "Version processing error",
        version_string: str | None = None,
        **kwargs: Any,
    ):
        """Initialize version error.

        Args:
            message: Error message
            version_string: Version string that caused the error
            **kwargs: Additional arguments for VersionTrackerError
        """
        context = kwargs.get("context", {})
        if version_string:
            context["version_string"] = version_string
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class NetworkError(VersionTrackerError):
    """Raised when network operations fail."""

    def __init__(
        self,
        message: str = "Network operation failed",
        url: str | None = None,
        status_code: int | None = None,
        **kwargs: Any,
    ):
        """Initialize network error.

        Args:
            message: Error message
            url: URL that caused the error
            status_code: HTTP status code if applicable
            **kwargs: Additional arguments for VersionTrackerError
        """
        context = kwargs.get("context", {})
        if url:
            context["url"] = url
        if status_code:
            context["status_code"] = status_code
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class TimeoutError(VersionTrackerError):
    """Raised when an operation times out."""

    def __init__(
        self,
        message: str = "Operation timed out",
        timeout_seconds: float | None = None,
        operation: str | None = None,
        **kwargs: Any,
    ):
        """Initialize timeout error.

        Args:
            message: Error message
            timeout_seconds: Timeout duration in seconds
            operation: Operation that timed out
            **kwargs: Additional arguments for VersionTrackerError
        """
        context = kwargs.get("context", {})
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds
        if operation:
            context["operation"] = operation
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class HomebrewError(VersionTrackerError):
    """Raised when Homebrew operations fail."""

    def __init__(
        self,
        message: str = "Homebrew operation failed",
        command: str | None = None,
        cask_name: str | None = None,
        **kwargs: Any,
    ):
        """Initialize Homebrew error.

        Args:
            message: Error message
            command: Homebrew command that failed
            cask_name: Cask name if applicable
            **kwargs: Additional arguments for VersionTrackerError
        """
        context = kwargs.get("context", {})
        if command:
            context["command"] = command
        if cask_name:
            context["cask_name"] = cask_name
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class ApplicationError(VersionTrackerError):
    """Raised when there's an error with application detection or processing."""

    def __init__(
        self,
        message: str = "Application processing error",
        app_name: str | None = None,
        app_path: str | None = None,
        **kwargs: Any,
    ):
        """Initialize application error.

        Args:
            message: Error message
            app_name: Application name that caused the error
            app_path: Application path if applicable
            **kwargs: Additional arguments for VersionTrackerError
        """
        context = kwargs.get("context", {})
        if app_name:
            context["app_name"] = app_name
        if app_path:
            context["app_path"] = app_path
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class CacheError(VersionTrackerError):
    """Raised when cache operations fail."""

    def __init__(
        self,
        message: str = "Cache operation failed",
        cache_key: str | None = None,
        cache_file: str | None = None,
        **kwargs: Any,
    ):
        """Initialize cache error.

        Args:
            message: Error message
            cache_key: Cache key that caused the error
            cache_file: Cache file path if applicable
            **kwargs: Additional arguments for VersionTrackerError
        """
        context = kwargs.get("context", {})
        if cache_key:
            context["cache_key"] = cache_key
        if cache_file:
            context["cache_file"] = cache_file
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class HandlerError(VersionTrackerError):
    """Raised when a command handler encounters an error."""

    def __init__(
        self,
        message: str = "Handler execution failed",
        handler_name: str | None = None,
        **kwargs: Any,
    ):
        """Initialize handler error.

        Args:
            message: Error message
            handler_name: Name of the handler that failed
            **kwargs: Additional arguments for VersionTrackerError
        """
        context = kwargs.get("context", {})
        if handler_name:
            context["handler_name"] = handler_name
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class DataParsingError(VersionTrackerError):
    """Data parsing errors.

    This exception is raised when parsing data from various sources fails, such as:
    - JSON parsing errors
    - Malformed data structures
    - Missing expected fields in data
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


# These exceptions are already defined above - no duplicates needed


# Validation exceptions
class ValidationError(VersionTrackerError):
    """Validation errors.

    This exception is raised when validation fails for any input data,
    such as command-line arguments, configuration values, or API responses.
    """

    pass
