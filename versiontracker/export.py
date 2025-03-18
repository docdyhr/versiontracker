import csv
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

from versiontracker.version import VersionStatus
from versiontracker.exceptions import ExportError

def export_data(
    data: Union[Dict[str, Any], List[Tuple[str, Dict[str, str], VersionStatus]]],
    format_type: str,
    filename: Optional[str] = None,
) -> str:
    """Export data to a file or return as string.

    Args:
        data: The data to export
        format_type: The format to export to ('json' or 'csv')
        filename: Optional filename to write to

    Returns:
        str: The filename or the exported data as a string

    Raises:
        ValueError: If the format is not supported
        ExportError: If there's an error during export
        PermissionError: If there's a permission error writing to file
    """
    if not data:
        raise ExportError("No data to export")

    # Convert format to lowercase
    format_type = format_type.lower()

    # Determine export format
    if format_type == "json":
        content = export_to_json(data)
    elif format_type == "csv":
        content = export_to_csv(data)
    else:
        raise ValueError(f"Unsupported export format: {format_type}")

    if filename:
        try:
            with open(filename, "w") as f:
                f.write(content)
            return filename
        except PermissionError as e:
            logging.error(f"Permission error writing to {filename}: {e}")
            raise PermissionError(f"Permission denied writing to {filename}") from e
        except Exception as e:
            logging.error(f"Error writing to {filename}: {e}")
            raise ExportError(f"Failed to write to {filename}: {e}") from e
    else:
        return content


def _export_to_json(data: Union[Dict[str, Any], List[Tuple[str, Dict[str, str], VersionStatus]]]) -> str:
    """Export data to JSON format.
    
    Args:
        data: The data to export
        
    Returns:
        str: The exported data as a JSON string
    """
    try:
        # For app version info list, convert to a more JSON-friendly format
        if isinstance(data, list) and data and isinstance(data[0], tuple):
            output_data = {
                "applications": [
                    {
                        "name": app[0],
                        "installed_version": app[1].get("installed", ""),
                        "latest_version": app[1].get("latest", "Unknown"),
                        "status": app[2].name if hasattr(app[2], "name") else str(app[2]),
                    }
                    for app in data
                ]
            }
        else:
            output_data = data
            
        return json.dumps(output_data, indent=2)
    except Exception as e:
        logging.error(f"Error exporting to JSON: {e}")
        raise ExportError(f"Failed to export to JSON: {e}") from e


def _export_to_csv(data: Union[Dict[str, Any], List[Tuple[str, Dict[str, str], VersionStatus]]]) -> str:
    """Export data to CSV format.
    
    Args:
        data: The data to export
        
    Returns:
        str: The exported data as a CSV string
    """
    try:
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header with expected field names from tests
        writer.writerow(["name", "installed_version", "latest_version", "status"])
        
        # For app version info list
        if isinstance(data, list) and data and isinstance(data[0], tuple):
            for app in data:
                writer.writerow([
                    app[0],
                    app[1].get("installed", ""),
                    app[1].get("latest", "Unknown"),
                    app[2].name if hasattr(app[2], "name") else str(app[2]),
                ])
        # For dictionary format
        elif isinstance(data, dict) and "applications" in data:
            applications = data["applications"]
            for app in applications:
                if isinstance(app, tuple):
                    writer.writerow([app[0], app[1], "", ""])
                elif isinstance(app, dict):
                    writer.writerow([
                        app.get("name", ""),
                        app.get("installed_version", ""),
                        app.get("latest_version", "Unknown"),
                        app.get("status", ""),
                    ])
                    
        return output.getvalue()
    except Exception as e:
        logging.error(f"Error exporting to CSV: {e}")
        raise ExportError(f"Failed to export to CSV: {e}") from e


def export_to_json(data, filename=None):
    """Export data to JSON format.
    
    Args:
        data: The data to export
        filename: Optional filename to write to
        
    Returns:
        str: The exported data as a JSON string or filename
    """
    content = _export_to_json(data)
    
    if filename:
        try:
            with open(filename, "w") as f:
                f.write(content)
            return filename
        except Exception as e:
            logging.error(f"Error writing to {filename}: {e}")
            raise ExportError(f"Failed to write to {filename}: {e}")
            
    return content


def export_to_csv(data, filename=None):
    """Export data to CSV format.
    
    Args:
        data: The data to export
        filename: Optional filename to write to
        
    Returns:
        str: The exported data as a CSV string or filename
    """
    content = _export_to_csv(data)
    
    if filename:
        try:
            with open(filename, "w") as f:
                f.write(content)
            return filename
        except Exception as e:
            logging.error(f"Error writing to {filename}: {e}")
            raise ExportError(f"Failed to write to {filename}: {e}")
            
    return content
