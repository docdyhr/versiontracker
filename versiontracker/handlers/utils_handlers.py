"""Utility handlers for VersionTracker.

This module contains utility functions for logging, error handling, and other
support functionality used by various handlers in VersionTracker.

Args:
    None: This is a module, not a function.

Returns:
    None: This module doesn't return anything directly.
"""

import logging
import sys
import warnings
from typing import Any, Callable, Optional


def setup_logging(
    level: int, log_file: Optional[str] = None, warnings_file: Optional[str] = None
) -> None:
    """Configure logging for the application.

    Sets up root logger, formatters, and handlers for console and file logging.

    Args:
        level: The logging level to use (e.g. logging.DEBUG)
        log_file: Optional path to a file for storing logs
        warnings_file: Optional path to a file for storing warnings

    Returns:
        None
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Setup file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Setup warnings file handler if specified
    if warnings_file:
        warnings_handler = logging.FileHandler(warnings_file)
        warnings_handler.setLevel(logging.WARNING)
        warnings_handler.setFormatter(formatter)
        root_logger.addHandler(warnings_handler)

    logging.debug("Logging setup complete")


def suppress_console_warnings() -> None:
    """Suppress specific warnings from being printed to the console.

    This does not affect logging to warning log files. Specifically targets
    DeprecationWarning, ResourceWarning, and UserWarning from external libraries.

    Args:
        None

    Returns:
        None
    """

    def warning_filter(message, category, filename, lineno, file=None, line=None):
        """Filter warning messages based on defined criteria.

        Args:
            message: Warning message
            category: Warning category
            filename: Source filename
            lineno: Line number in source file
            file: Optional file to write warning to
            line: Optional line content where warning occurred

        Returns:
            bool: True if the warning should be shown, False if it should be suppressed
        """
        _ = message, lineno, file, line  # Acknowledge unused parameters
        if filename and "versiontracker" in filename:
            # Don't suppress warnings from versiontracker code
            return True

        # Filter out selected warning types from other libraries and modules
        for warn_type in ["DeprecationWarning", "ResourceWarning", "UserWarning"]:
            if category.__name__ == warn_type:
                return False

        return True

    # Create warning filter class
    class WarningFilter:
        """Filter for logging.Handler to suppress certain warning types."""

        def filter(self, record):
            """Filter log records based on warning type.

            Args:
                record: The log record to check

            Returns:
                bool: True if the record should be processed, False otherwise
            """
            if record.levelno == logging.WARNING:
                return warning_filter(
                    record.getMessage(), UserWarning, record.filename, record.lineno
                )
            return True

    # Set warnings filter
    warnings.filterwarnings("default")
    for handler in logging.getLogger().handlers:
        if hasattr(handler, "stream") and handler.stream == sys.stderr:
            handler.addFilter(WarningFilter())


def safe_function_call(
    func: Callable,
    *args,
    default_value: Any = None,
    error_msg: str = "Error in function call",
    **kwargs,
) -> Any:
    """Safely call a function, catching and logging any exceptions.

    Wraps a function call in a try/except block to prevent failures from
    propagating, logging errors and returning a default value instead.

    Args:
        func: The function to call
        *args: Arguments to pass to the function
        default_value: Value to return if the function call fails
        error_msg: Message to log on error
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function call, or default_value if the call fails

    Raises:
        No exceptions are raised; all are caught and logged
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logging.error(f"{error_msg}: {e}")
        return default_value
