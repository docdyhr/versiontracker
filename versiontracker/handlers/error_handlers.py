"""Error handling utilities for VersionTracker handlers.

This module provides common error handling functions that can be reused
across different handlers for consistent error reporting and user feedback.
"""

import logging
import traceback

from versiontracker.config import get_config
from versiontracker.exceptions import ConfigError
from versiontracker.ui import create_progress_bar


def handle_permission_error(context: str = "application data") -> int:
    """Handle permission errors with user-friendly messaging.

    Args:
        context: Description of what was being accessed

    Returns:
        Exit code 1
    """
    print(create_progress_bar().color("red")(f"Error: Permission denied when reading {context}."))
    print(create_progress_bar().color("yellow")("Try running the command with sudo or check your file permissions."))
    return 1


def handle_timeout_error(context: str = "application data") -> int:
    """Handle timeout errors with user-friendly messaging.

    Args:
        context: Description of what was being accessed

    Returns:
        Exit code 1
    """
    print(create_progress_bar().color("red")(f"Error: Timed out while reading {context}."))
    print(create_progress_bar().color("yellow")("Check your system load and try again later."))
    return 1


def handle_network_error(context: str = "checking for updates") -> int:
    """Handle network errors with user-friendly messaging.

    Args:
        context: Description of what network operation was attempted

    Returns:
        Exit code 1
    """
    print(create_progress_bar().color("red")(f"Error: Network error while {context}."))
    print(create_progress_bar().color("yellow")("Check your internet connection and try again."))
    return 1


def handle_homebrew_not_found() -> int:
    """Handle Homebrew not found error.

    Returns:
        Exit code 1
    """
    print(create_progress_bar().color("red")("Error: Homebrew executable not found."))
    print(create_progress_bar().color("yellow")("Please make sure Homebrew is installed and properly configured."))
    return 1


def handle_config_error(error: ConfigError) -> int:
    """Handle configuration errors.

    Args:
        error: The ConfigError that occurred

    Returns:
        Exit code 1
    """
    print(create_progress_bar().color("red")(f"Configuration Error: {error}"))
    print(create_progress_bar().color("yellow")("Please check your configuration file and try again."))
    return 1


def handle_keyboard_interrupt() -> int:
    """Handle keyboard interrupt (Ctrl+C).

    Returns:
        Exit code 130 (standard for SIGINT)
    """
    print(create_progress_bar().color("yellow")("\nOperation canceled by user."))
    return 130


def handle_generic_error(error: Exception, context: str = "", debug: bool | None = None) -> int:
    """Handle generic errors with optional debug output.

    Args:
        error: The exception that occurred
        context: Optional context for the error message
        debug: Whether to show debug info (uses config if None)

    Returns:
        Exit code 1
    """
    if debug is None:
        debug = getattr(get_config(), "debug", False)

    error_msg = f"Error: {error}" if not context else f"Error {context}: {error}"
    logging.error(error_msg)
    print(create_progress_bar().color("red")(error_msg))

    if debug:
        traceback.print_exc()
    else:
        print(create_progress_bar().color("yellow")("Run with --debug for more information."))

    return 1


def handle_top_level_exception(e: BaseException) -> int:
    """Handle top-level exceptions with proper error reporting.

    This is a convenience function that routes to the appropriate
    specific handler based on exception type.

    Args:
        e: Exception that occurred

    Returns:
        Appropriate exit code
    """
    if isinstance(e, ConfigError):
        return handle_config_error(e)
    elif isinstance(e, KeyboardInterrupt):
        return handle_keyboard_interrupt()
    else:
        return handle_generic_error(e if isinstance(e, Exception) else Exception(str(e)))
