"""Tests for the version comparison functionality."""

import pytest

from versiontracker.version import (
    VersionInfo,
    VersionStatus,
    compare_versions,
    get_version_difference,
    parse_version,
)


@pytest.mark.parametrize(
    "version_string,expected",
    [
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
        ("1.2.3.4", (1, 2, 3)),  # Extra version components
        ("2021.1.2", (2021, 1, 2)),  # Year-based versioning
        ("1.2.3-rc1", (1, 2, 3)),  # Release candidate
        ("1.2.3.beta4", (1, 2, 3)),  # Beta with number
        ("10.15.7", (10, 15, 7)),  # macOS version format
        ("1.2.3d", (1, 2, 3)),  # Version with suffix
        ("1.2.3rev2", (1, 2, 3)),  # Revision suffix
        ("App v2.3.0 (build 1234)", (2, 3, 0)),  # Complex format
        ("", (0, 0, 0)),
        (None, (0, 0, 0)),
        ("non-version-string", None),
    ],
)
def test_parse_version(version_string, expected):
    """Test parsing of various version formats."""
    result = parse_version(version_string)
    assert result == expected


@pytest.mark.parametrize(
    "version1,version2,expected",
    [
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
    ],
)
def test_compare_versions(version1, version2, expected):
    """Test comparison of version strings and tuples."""
    result = compare_versions(version1, version2)
    assert result == expected


@pytest.mark.parametrize(
    "v1,v2,expected",
    [
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
    ],
)
def test_version_difference(v1, v2, expected):
    """Test calculation of version differences."""
    result = get_version_difference(v1, v2)
    assert result == expected


def test_version_info():
    """Test VersionInfo class initialization and status determination."""
    # Test basic initialization and parsing
    info = VersionInfo(name="TestApp", version_string="1.2.3")
    assert info.name == "TestApp"
    assert info.version_string == "1.2.3"
    assert info.parsed == (1, 2, 3)
    assert info.status == VersionStatus.UNKNOWN

    # Test with empty version
    info = VersionInfo(name="TestApp", version_string="")
    assert info.parsed is None

    # Test with latest_version
    info = VersionInfo(
        name="TestApp",
        version_string="1.2.3",
        latest_version="1.2.4",
        latest_parsed=(1, 2, 4),
        status=VersionStatus.OUTDATED,
        outdated_by=(0, 0, 1),
    )
    assert info.status == VersionStatus.OUTDATED
    assert info.outdated_by == (0, 0, 1)
