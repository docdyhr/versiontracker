"""UI handlers for displaying status information.

This module contains handler functions for UI-related operations in VersionTracker,
primarily focused on displaying status information with appropriate colors and icons.

Args:
    None: This is a module, not a function.

Returns:
    None: This module doesn't return anything directly.
"""

from collections.abc import Callable
from typing import Any

from versiontracker.ui import create_progress_bar


def get_status_icon(status: str) -> str:
    """Get a status icon for a version status.

    Provides a visual representation (emoji or text) for different application
    status types like up-to-date, outdated, not found, or error.

    Args:
        status: The version status (uptodate, outdated, not_found, error)

    Returns:
        str: An icon representing the status

    Raises:
        Exception: Falls back to text icons if colored icons are not available
    """
    try:
        if status == "uptodate":
            return str(create_progress_bar().color("green")("✅"))
        elif status == "outdated":
            return str(create_progress_bar().color("yellow")("🔄"))
        elif status == "not_found":
            return str(create_progress_bar().color("blue")("❓"))
        elif status == "error":
            return str(create_progress_bar().color("red")("❌"))
        return ""
    except Exception:
        # Fall back to text-based icons if colored package is not available
        if status == "uptodate":
            return "[OK]"
        elif status == "outdated":
            return "[OUTDATED]"
        elif status == "not_found":
            return "[NOT FOUND]"
        elif status == "error":
            return "[ERROR]"
        return ""


def get_status_color(status: str) -> Callable[[str], str | Any]:
    """Get a color function for the given version status.

    Returns a function that applies the appropriate color to text based on
    the status (green for up-to-date, red for outdated, etc.).

    Args:
        status: Version status (uptodate, outdated, newer, or any other status)

    Returns:
        function: Color function that takes a string and returns a colored string
            using the appropriate color based on status
    """
    if status == "uptodate":
        return lambda text: create_progress_bar().color("green")(text)
    elif status == "outdated":
        return lambda text: create_progress_bar().color("red")(text)
    elif status == "newer":
        return lambda text: create_progress_bar().color("cyan")(text)
    else:
        return lambda text: create_progress_bar().color("yellow")(text)
