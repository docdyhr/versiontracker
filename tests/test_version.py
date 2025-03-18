"""Tests for the version comparison functionality."""

import unittest

from versiontracker.version import (
    VersionInfo,
    VersionStatus,
    compare_versions,
    get_version_difference,
    parse_version,
)


class TestVersionComparison(unittest.TestCase):
    """Tests for version parsing and comparison functions."""

    def test_parse_version(self):
        """Test parsing of various version formats."""
        test_cases = [
            # Input, Expected Output
            ("1.2.3", (1, 2, 3)),
            ("1.2", (1, 2, 0)),
            ("1", (1, 0, 0)),
            ("1.2.3-beta", (1, 2, 3)),
            ("1.2.3+build.123", (1, 2, 3)),
            ("1.2.3-beta+build.123", (1, 2, 3)),
            ("1.2.3 (456)", (1, 2, 3)),
            ("Version 1.2.3", (1, 2, 3)),
            ("v1.2.3", (1, 2, 3)),
            ("", None),
            (None, None),
            ("non-version-string", None),
        ]

        for version_string, expected in test_cases:
            with self.subTest(version_string=version_string):
                result = parse_version(version_string)
                self.assertEqual(result, expected)

    def test_compare_versions(self):
        """Test comparison of version strings and tuples."""
        test_cases = [
            # Version 1, Version 2, Expected Result (-1, 0, 1)
            ("1.2.3", "1.2.3", 0),  # Equal versions
            ("1.2.3", "1.2.4", -1),  # Lower version
            ("1.2.3", "1.2.2", 1),  # Higher version
            ("1.2.3", "1.3.0", -1),  # Lower minor version
            ("2.0.0", "1.9.9", 1),  # Higher major version
            ((1, 2, 3), (1, 2, 3), 0),  # Equal tuples
            ((1, 2, 3), (1, 2, 4), -1),  # Lower tuple
            ((1, 2, 3), (1, 2, 2), 1),  # Higher tuple
            ("1.2.3", (1, 2, 3), 0),  # String vs tuple (equal)
            ("1.2.3", (1, 2, 4), -1),  # String vs tuple (lower)
            ((1, 2, 3), "1.2.2", 1),  # Tuple vs string (higher)
            (None, "1.2.3", -1),  # None vs version
            ("1.2.3", None, 1),  # Version vs None
            (None, None, 0),  # None vs None
        ]

        for version1, version2, expected in test_cases:
            with self.subTest(version1=version1, version2=version2):
                result = compare_versions(version1, version2)
                self.assertEqual(result, expected)

    def test_version_difference(self):
        """Test calculation of version differences."""
        test_cases = [
            # Version 1, Version 2, Expected Difference
            ((1, 2, 3), (1, 2, 3), (0, 0, 0)),  # No difference
            ((1, 2, 3), (1, 2, 4), (0, 0, 1)),  # Patch difference
            ((1, 2, 3), (1, 3, 3), (0, 1, 0)),  # Minor difference
            ((1, 2, 3), (2, 2, 3), (1, 0, 0)),  # Major difference
            ((1, 2, 3), (2, 3, 4), (1, 1, 1)),  # All differences
            ((1, 2), (1, 2, 3), (0, 0, 3)),  # Different lengths
            (None, (1, 2, 3), None),  # None case 1
            ((1, 2, 3), None, None),  # None case 2
            (None, None, None),  # Both None
        ]

        for v1, v2, expected in test_cases:
            with self.subTest(v1=v1, v2=v2):
                result = get_version_difference(v1, v2)
                self.assertEqual(result, expected)

    def test_version_info(self):
        """Test VersionInfo class initialization and status determination."""
        # Test basic initialization and parsing
        info = VersionInfo(name="TestApp", version_string="1.2.3")
        self.assertEqual(info.name, "TestApp")
        self.assertEqual(info.version_string, "1.2.3")
        self.assertEqual(info.parsed, (1, 2, 3))
        self.assertEqual(info.status, VersionStatus.UNKNOWN)

        # Test with empty version
        info = VersionInfo(name="TestApp", version_string="")
        self.assertEqual(info.parsed, None)

        # Test with latest_version
        info = VersionInfo(
            name="TestApp",
            version_string="1.2.3",
            latest_version="1.2.4",
            latest_parsed=(1, 2, 4),
            status=VersionStatus.OUTDATED,
            outdated_by=(0, 0, 1),
        )
        self.assertEqual(info.status, VersionStatus.OUTDATED)
        self.assertEqual(info.outdated_by, (0, 0, 1))


if __name__ == "__main__":
    unittest.main()
