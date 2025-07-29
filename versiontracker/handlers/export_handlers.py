"""Export handlers for VersionTracker.

This module contains handler functions for exporting data in various formats
such as JSON and CSV. It provides functions to handle the export of application
data, recommendations, and other information gathered by VersionTracker.

Args:
    None: This is a module, not a function.

Returns:
    None: This module doesn't return anything directly.
"""

import logging
import traceback
from typing import Any, Optional, Union

from versiontracker.config import get_config
from versiontracker.exceptions import ExportError
from versiontracker.export import export_data
from versiontracker.ui import create_progress_bar


def handle_export(
    data: Any,
    format_type: str,
    filename: Optional[str] = None,
) -> Union[int, str]:
    """Handle exporting data in the specified format.

    Exports data to JSON or CSV format, either to a file or as a string.

    Args:
        data: The data to export (can be dictionary, list, or other serializable type)
        format_type: The format to export to ('json' or 'csv')
        filename: Optional filename to write to

    Returns:
        int: Exit code (0 for success, non-zero for failure) or
        str: The exported data as a string if no filename is provided

    Raises:
        ValueError: If an unsupported format is specified
        PermissionError: If there's an issue with file permissions
        ExportError: If there's an error during the export process
        Exception: For other unexpected errors
    """
    try:
        # Export data
        result = export_data(data, format_type, filename)

        # If we're exporting to a file, return success
        if filename:
            return 0

        # Otherwise return the result for further processing
        return result
    except ValueError as e:
        print(create_progress_bar().color("red")(f"Export Error: {e}"))
        print(create_progress_bar().color("yellow")("Supported formats are 'json' and 'csv'"))
        return 1
    except PermissionError as e:
        print(create_progress_bar().color("red")(f"Permission Error: {e}"))
        print(create_progress_bar().color("yellow")("Check your write permissions for the output file"))
        return 1
    except ExportError as e:
        print(create_progress_bar().color("red")(f"Export Error: {e}"))
        return 1
    except Exception as e:
        logging.error(f"Error exporting data: {e}")
        print(create_progress_bar().color("red")(f"Error: Failed to export data: {e}"))
        if get_config().debug:
            traceback.print_exc()
        return 1
