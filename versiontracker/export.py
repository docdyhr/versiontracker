"""Export utilities for VersionTracker."""

import csv
import json
import logging
import os
from typing import Any, Dict, List, Optional


def export_to_json(data: Dict[str, Any], filename: Optional[str] = None) -> str:
    """Export data to JSON format.

    Args:
        data: The data to export
        filename: Optional filename to write to (if None, returns string)

    Returns:
        str: JSON string if no filename provided, otherwise path to the file
    """
    json_data = json.dumps(data, indent=2)

    if filename:
        output_path = os.path.abspath(filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_data)
        logging.info(f"Exported data to JSON file: {output_path}")
        return output_path

    return json_data


def export_to_csv(data: Dict[str, List[Any]], filename: Optional[str] = None) -> str:
    """Export data to CSV format.

    Args:
        data: The data to export, must contain lists under keys
        filename: Optional filename to write to (if None, returns string)

    Returns:
        str: CSV string if no filename provided, otherwise path to the file
    """
    # Determine all headers from the data
    headers = []
    for key, items in data.items():
        if isinstance(items, list) and len(items) > 0:
            if isinstance(items[0], dict):
                # For list of dictionaries, use keys as headers
                headers.extend(items[0].keys())
            elif isinstance(items[0], (list, tuple)) and len(items[0]) > 1:
                # For list of lists/tuples, use first row as keys
                if hasattr(items[0], "__dict__"):
                    headers.extend(items[0].__dict__.keys())
                else:
                    # For tuples in apps data structure
                    headers.extend(["name", "version"])

    # Remove duplicates while preserving order
    unique_headers = []
    for header in headers:
        if header not in unique_headers:
            unique_headers.append(header)

    # Prepare data for CSV
    csv_data = []
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
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    row = {"name": item[0], "version": item[1]}
                    csv_data.append(row)
            elif isinstance(item, str):
                # For simple string lists (brew names)
                row = {"name": item}
                csv_data.append(row)

    # Create CSV output
    if not csv_data:
        return "No data to export"

    # Determine the actual headers available in the data
    available_headers = set()
    for row in csv_data:
        available_headers.update(row.keys())

    # Filter headers to those actually in the data
    final_headers = [h for h in unique_headers if h in available_headers]
    if not final_headers and csv_data:
        final_headers = list(csv_data[0].keys())

    if filename:
        output_path = os.path.abspath(filename)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=final_headers)
            writer.writeheader()
            writer.writerows(csv_data)
        logging.info(f"Exported data to CSV file: {output_path}")
        return output_path

    # Return as string if no filename provided
    result = []
    result.append(",".join(final_headers))
    for row in csv_data:
        csv_row = [str(row.get(header, "")) for header in final_headers]
        result.append(",".join(csv_row))

    return "\n".join(result)


def export_data(data: Dict[str, Any], format_type: str, filename: Optional[str] = None) -> str:
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
