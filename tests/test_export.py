"""Unit tests for the export functionality."""

import csv
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from versiontracker.export import export_data, export_to_csv, export_to_json


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
            with open(result_path, "r") as f:
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
        self.assertTrue("name" in header)

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
            with open(result_path, "r", newline="") as f:
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


if __name__ == "__main__":
    unittest.main()
