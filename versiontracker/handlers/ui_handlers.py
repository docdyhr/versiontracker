"""UI handlers for displaying status information."""

from typing import Any, Callable, Union

from versiontracker.ui import create_progress_bar


def get_status_icon(status: str) -> str:
    """Get a status icon for a version status.

    Args:
        status: The version status

    Returns:
        str: An icon representing the status
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


def get_status_color(status: str) -> Callable[[str], Union[str, Any]]:
    """Get a color function for the given version status.

    Args:
        status: Version status

    Returns:
        function: Color function that takes a string and returns a colored string
    """
    if status == "uptodate":
        return lambda text: create_progress_bar().color("green")(text)
    elif status == "outdated":
        return lambda text: create_progress_bar().color("red")(text)
    elif status == "newer":
        return lambda text: create_progress_bar().color("cyan")(text)
    else:
        return lambda text: create_progress_bar().color("yellow")(text)