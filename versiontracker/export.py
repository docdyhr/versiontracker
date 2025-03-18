"""Export functionality for VersionTracker."""

import csv
import json
import logging
import os

# Type for path-like objects
from os import PathLike
from typing import Any, Dict, List, Optional, Set, Union


def export_to_json(data: Dict[str, Any], filename: Optional[str] = None) -> Union[str, PathLike]:
    """Export data to JSON format.

    Args:
        data: The data to export
        filename: Optional filename to write to

    Returns:
        str: JSON string or path to output file
    """
    json_str = json.dumps(data, indent=2)

    if filename:
        output_path = os.path.abspath(filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_str)
        logging.info(f"Exported data to JSON file: {output_path}")
        return output_path
    else:
        return json_str


def export_to_csv(data: Dict[str, Any], filename: Optional[str] = None) -> Union[str, PathLike]:
    """Export data to CSV format.

    Args:
        data: The data to export
        filename: Optional filename to write to

    Returns:
        str: CSV string or path to output file
    """
    # Determine headers from all data items
    headers: List[str] = ["name"]  # Always include name

    # Extract all potential headers from dictionaries
    for key, items in data.items():
        if not isinstance(items, list) or not items:
            continue

        # Look at the first item to determine structure
        if isinstance(items[0], dict):
            headers.extend(items[0].keys())
        elif hasattr(items[0], "__dict__"):
            headers.extend(items[0].__dict__.keys())
        else:
            # For tuples in apps data structure
            headers.extend(["name", "version"])

    # Remove duplicates while preserving order
    unique_headers: List[str] = []
    for header in headers:
        if header not in unique_headers:
            unique_headers.append(header)

    # Prepare data for CSV
    csv_data: List[Dict[str, str]] = []
    for key, items in data.items():
        if not isinstance(items, list):
            continue

        for item in items:
            if isinstance(item, dict):
                # Add dictionary items as a row
                row = {header: item.get(header, "") for header in unique_headers}
                csv_data.append(row)
            elif isinstance(item, (list, tuple)) and len(item) > 1:
                # For list of lists/tuples (app names and versions), create rows
                row = {"name": item[0], "version": item[1]}
                csv_data.append(row)
            elif isinstance(item, str):
                # For simple string lists (brew names)
                row = {"name": item}
                csv_data.append(row)

    if not csv_data:
        return ""

    # Write to file or return as string
    output = ""
    if filename:
        output_path = os.path.abspath(filename)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=unique_headers)
            writer.writeheader()
            writer.writerows(csv_data)
        logging.info(f"Exported data to CSV file: {output_path}")
        return output_path
    else:
        # Create CSV string
        lines = []
        lines.append(",".join(unique_headers))
        for row in csv_data:
            lines.append(",".join(f'"{str(row.get(header, ""))}"' for header in unique_headers))
        output = "\n".join(lines)
        return output


def export_data(
    data: Dict[str, Any], format_type: str, filename: Optional[str] = None
) -> Union[str, PathLike]:
    """Export data in the specified format.

    Args:
        data: The data to export
        format_type: Format to export to ('json' or 'csv')
        filename: Optional filename to write to

    Returns:
        str: Exported data as string or path to output file

    Raises:
        ValueError: If an unsupported format is specified
    """
    if format_type.lower() == "json":
        return export_to_json(data, filename)
    elif format_type.lower() == "csv":
        return export_to_csv(data, filename)
    else:
        raise ValueError(f"Unsupported export format: {format_type}")
