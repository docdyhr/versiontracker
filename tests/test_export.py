"""Unit tests for the export functionality."""

import csv
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from versiontracker.exceptions import ExportError
from versiontracker.export import export_data, export_to_csv, export_to_json
from versiontracker.version import VersionStatus


class TestExport(unittest.TestCase):
    """Test the export functionality."""

    def setUp(self):
        """Set up the test case."""
        self.test_data = {
            "applications": [
                ("Firefox", "100.0"),
                ("Chrome", "101.0"),
                ("Slack", "4.23.0"),
            ],
            "homebrew_casks": ["firefox", "google-chrome"],
            "recommendations": ["slack"],
        }

        # Create more complex data with version status for testing
        self.version_data = [
            ("Firefox", {"installed": "100.0", "latest": "101.0"}, "outdated"),
            ("Chrome", {"installed": "101.0", "latest": "101.0"}, "uptodate"),
            ("Unknown", {"installed": "1.0"}, "not_found"),
        ]

        # Create data with VersionStatus enum
        self.enum_data = [
            (
                "Firefox",
                {"installed": "100.0", "latest": "101.0"},
                VersionStatus.OUTDATED,
            ),
            (
                "Chrome",
                {"installed": "101.0", "latest": "101.0"},
                VersionStatus.UP_TO_DATE,
            ),
        ]

    def test_export_to_json_string(self):
        """Test exporting to JSON string."""
        json_str = export_to_json(self.test_data)
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        self.assertEqual(len(parsed["applications"]), 3)
        self.assertEqual(len(parsed["homebrew_casks"]), 2)
        self.assertEqual(len(parsed["recommendations"]), 1)

    def test_export_to_json_file(self):
        """Test exporting to JSON file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Export to the temp file
            result_path = export_to_json(self.test_data, temp_path)

            # Check the file exists
            self.assertTrue(os.path.exists(result_path))

            # Check the file content
            with open(result_path) as f:
                data = json.load(f)
                self.assertEqual(len(data["applications"]), 3)
                self.assertEqual(len(data["homebrew_casks"]), 2)
                self.assertEqual(len(data["recommendations"]), 1)
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_to_csv_string(self):
        """Test exporting to CSV string."""
        csv_str = export_to_csv(self.test_data)

        # Split into lines and check structure
        lines = csv_str.strip().split("\n")
        self.assertTrue(len(lines) > 1)  # Header + data rows

        # Check header contains expected fields
        header = lines[0].split(",")
        self.assertTrue("name" in header[0])

    def test_export_to_csv_file(self):
        """Test exporting to CSV file."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Export to the temp file
            result_path = export_to_csv(self.test_data, temp_path)

            # Check the file exists
            self.assertTrue(os.path.exists(result_path))

            # Check the file content
            with open(result_path, newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
                self.assertTrue(len(rows) > 1)  # Header + data rows
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_data_json(self):
        """Test the export_data function with JSON format."""
        # Test with JSON format
        result = export_data(self.test_data, "json")
        self.assertTrue(isinstance(result, str))

        # Verify it's valid JSON
        parsed = json.loads(result)
        self.assertEqual(len(parsed["applications"]), 3)

    def test_export_data_csv(self):
        """Test the export_data function with CSV format."""
        # Test with CSV format
        result = export_data(self.test_data, "csv")
        self.assertTrue(isinstance(result, str))

        # Should have header and data rows
        lines = result.strip().split("\n")
        self.assertTrue(len(lines) > 1)

    def test_export_data_invalid_format(self):
        """Test the export_data function with an invalid format."""
        # Test with invalid format
        with self.assertRaises(ValueError):
            export_data(self.test_data, "invalid_format")

    def test_export_data_empty(self):
        """Test export with empty data."""
        with self.assertRaises(ExportError):
            export_data(None, "json")

        with self.assertRaises(ExportError):
            export_data([], "json")

    def test_export_data_with_filename(self):
        """Test export with a filename destination."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = export_data(self.test_data, "json", temp_path)
            self.assertEqual(result, temp_path)
            self.assertTrue(os.path.exists(temp_path))
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_export_data_permission_error(self, mock_open):
        """Test handling of permission error when writing to file."""
        with self.assertRaises(PermissionError):
            export_data(self.test_data, "json", "/path/to/file.json")

    @patch("builtins.open", side_effect=Exception("Unknown error"))
    def test_export_data_general_error(self, mock_open):
        """Test handling of general error when writing to file."""
        with self.assertRaises(ExportError):
            export_data(self.test_data, "json", "/path/to/file.json")

    def test_export_to_json_with_version_status(self):
        """Test exporting data with version status to JSON."""
        # Test with list of tuples containing version info
        result = export_to_json(self.version_data)
        parsed = json.loads(result)

        # Check that it correctly parsed the structure
        self.assertEqual(len(parsed["applications"]), 3)
        self.assertEqual(parsed["applications"][0]["name"], "Firefox")
        self.assertEqual(parsed["applications"][0]["installed_version"], "100.0")
        self.assertEqual(parsed["applications"][0]["latest_version"], "101.0")
        self.assertEqual(parsed["applications"][0]["status"], "outdated")

    def test_export_to_json_with_version_status_enum(self):
        """Test exporting data with VersionStatus enum to JSON."""
        result = export_to_json(self.enum_data)
        parsed = json.loads(result)

        # Check that it correctly handled the enum
        self.assertEqual(parsed["applications"][0]["status"], "OUTDATED")
        self.assertEqual(parsed["applications"][1]["status"], "UP_TO_DATE")

    def test_export_to_json_file_error(self):
        """Test error handling when exporting to JSON file."""
        with patch("builtins.open", side_effect=Exception("Error")):
            with self.assertRaises(ExportError):
                export_to_json(self.test_data, "test.json")

    def test_export_to_csv_with_version_status(self):
        """Test exporting data with version status to CSV."""
        result = export_to_csv(self.version_data)
        result.strip().split("\n")

        # Convert to list of rows for easier checking
        # Use csv module to handle carriage returns properly
        import io

        reader = csv.reader(io.StringIO(result))
        rows = list(reader)

        # Check headers and content
        self.assertEqual(rows[0][0], "name")
        self.assertEqual(rows[0][1], "installed_version")
        self.assertEqual(rows[0][2], "latest_version")
        self.assertEqual(rows[0][3], "status")

        # Check Firefox row
        self.assertEqual(rows[1][0], "Firefox")
        self.assertEqual(rows[1][1], "100.0")
        self.assertEqual(rows[1][2], "101.0")
        self.assertEqual(rows[1][3], "outdated")

    def test_export_to_csv_with_minimal_tuple(self):
        """Test exporting minimal tuples to CSV."""
        minimal_data = [("App1",), ("App2",)]
        result = export_to_csv(minimal_data)
        lines = result.strip().split("\n")

        # Should have header + 2 rows
        self.assertEqual(len(lines), 3)

        # Check that app names are in the first column
        self.assertIn("App1", lines[1])
        self.assertIn("App2", lines[2])

    def test_export_to_csv_with_dict_structure(self):
        """Test exporting dictionary structure to CSV."""
        dict_data = {
            "App1": {"installed": "1.0", "latest": "2.0", "status": "outdated"},
            "App2": {"installed": "2.0", "latest": "2.0", "status": "uptodate"},
        }
        result = export_to_csv(dict_data)

        # Check that both apps are in the output
        self.assertIn("App1", result)
        self.assertIn("App2", result)
        self.assertIn("1.0", result)
        self.assertIn("2.0", result)
        self.assertIn("outdated", result)
        self.assertIn("uptodate", result)

    def test_export_to_csv_file_error(self):
        """Test error handling when exporting to CSV file."""
        with patch("builtins.open", side_effect=Exception("Error")):
            with self.assertRaises(ExportError):
                export_to_csv(self.test_data, "test.csv")

    def test_export_to_json_error(self):
        """Test error handling during JSON export."""
        with patch("json.dumps", side_effect=Exception("JSON error")):
            with self.assertRaises(ExportError):
                export_to_json(self.test_data)

    @patch("csv.writer", side_effect=Exception("CSV error"))
    def test_export_to_csv_error(self, mock_writer):
        """Test error handling during CSV export."""
        with self.assertRaises(ExportError):
            export_to_csv(self.test_data)


if __name__ == "__main__":
    unittest.main()
