"""Test module for version comparison with parameterized tests.

This module contains parameterized tests for the version comparison
functionality in version.py, testing various version formats and
comparison scenarios with a data-driven approach.
"""

import pytest

from versiontracker.version import (
    VersionStatus,
    compare_versions,
    get_version_difference,
    get_version_info,
    parse_version,
)


@pytest.mark.parametrize(
    "version1,version2,expected_result",
    [
        # Basic semver comparisons
        ("1.0.0", "1.0.0", 0),
        ("1.0.0", "1.0.1", -1),
        ("1.0.1", "1.0.0", 1),
        ("1.1.0", "1.0.0", 1),
        ("1.0.0", "2.0.0", -1),
        ("2.0.0", "1.0.0", 1),
        
        # Comparing different length versions
        ("1.0", "1.0.0", 0),
        ("1", "1.0.0", 0),
        ("1.0.0", "1", 0),
        ("1.1", "1.0.0", 1),
        ("1.0.0", "1.1", -1),
        
        # Complex version formats
        ("1.0.0-beta", "1.0.0", -1),
        ("1.0.0", "1.0.0-beta", 1),
        ("1.0.0-alpha", "1.0.0-beta", -1),
        ("1.0.0-beta.2", "1.0.0-beta.1", 1),
        
        # Build metadata
        ("1.0.0+build.1", "1.0.0+build.2", 0),  # Build metadata should be ignored
        ("1.0.0+build.1", "1.0.0", 0),
        
        # Common macOS version formats
        ("12.3.1", "12.4", -1),
        ("10.15.7", "11.0", -1),
        ("11.2.3", "11.2.3", 0),
        
        # Application-specific formats
        ("Firefox 91.0.2", "Firefox 92.0", -1),
        ("Chrome 94.0.4606.71", "Chrome 94.0.4606.81", -1),
        ("Visual Studio Code 1.60.0", "Visual Studio Code 1.60.2", -1),
        
        # Non-standard formats
        ("2021.05", "2021.06", -1),
        ("v2.3.0", "v2.3.1", -1),
        ("Version 1.2", "Version 1.3", -1),
        
        # Edge cases
        ("", "", 0),
        ("0", "0", 0),
        ("0.0.0", "0.0.0", 0),
    ],
)
def test_compare_versions(version1, version2, expected_result):
    """Test version comparison with various version formats."""
    result = compare_versions(version1, version2)
    assert result == expected_result, f"Expected {expected_result} but got {result} for {version1} vs {version2}"


@pytest.mark.parametrize(
    "version_string,expected_tuple",
    [
        # Standard semantic versions
        ("1.0.0", (1, 0, 0)),
        ("2.3.4", (2, 3, 4)),
        ("0.1.0", (0, 1, 0)),
        
        # Partial versions
        ("1.0", (1, 0, 0)),
        ("1", (1, 0, 0)),
        
        # Versions with prefixes
        ("v1.0.0", (1, 0, 0)),
        ("Version 2.3.4", (2, 3, 4)),
        
        # Versions with build numbers
        ("1.0.0.1234", (1, 0, 0, 1234)),
        ("2.3.4-build.5678", (2, 3, 4, 5678)),
        
        # Versions with text
        ("1.0.0-beta", (1, 0, 0, 0)),
        ("2.3.4-alpha.1", (2, 3, 4, 1)),
        ("1.0.0-rc.2", (1, 0, 0, 2)),
        
        # Application names with versions
        ("Firefox 91.0.2", (91, 0, 2)),
        ("Chrome 94.0.4606.71", (94, 0, 4606, 71)),
        
        # Edge cases
        ("", (0, 0, 0)),
        ("no version", (0, 0, 0)),
        ("0", (0, 0, 0)),
    ],
)
def test_parse_version(version_string, expected_tuple):
    """Test version parsing with various version formats."""
    result = parse_version(version_string)
    assert result == expected_tuple, f"Expected {expected_tuple} but got {result} for '{version_string}'"


@pytest.mark.parametrize(
    "version1,version2,expected_difference",
    [
        # Same versions
        ("1.0.0", "1.0.0", (0, 0, 0)),
        
        # Simple differences
        ("1.0.0", "1.0.1", (0, 0, -1)),
        ("1.0.0", "1.1.0", (0, -1, 0)),
        ("1.0.0", "2.0.0", (-1, 0, 0)),
        
        # Multiple component differences
        ("1.2.3", "2.3.4", (-1, -1, -1)),
        ("3.2.1", "1.2.3", (2, 0, -2)),
        
        # Different length versions
        ("1.0", "1.0.1", (0, 0, -1)),
        ("1", "1.1.0", (0, -1, 0)),
        
        # Edge cases
        (None, "1.0.0", None),
        ("1.0.0", None, None),
        (None, None, None),
    ],
)
def test_get_version_difference(version1, version2, expected_difference):
    """Test version difference calculation with various version formats."""
    result = get_version_difference(version1, version2)
    assert result == expected_difference, f"Expected {expected_difference} but got {result} for {version1} vs {version2}"


@pytest.mark.parametrize(
    "current_version,latest_version,expected_status",
    [
        # Exact same versions
        ("1.0.0", "1.0.0", VersionStatus.UPTODATE),
        
        # Outdated versions
        ("1.0.0", "1.0.1", VersionStatus.OUTDATED),
        ("1.0.0", "1.1.0", VersionStatus.OUTDATED),
        ("1.0.0", "2.0.0", VersionStatus.OUTDATED),
        
        # Newer versions (unusual but possible)
        ("1.0.1", "1.0.0", VersionStatus.NEWER),
        ("1.1.0", "1.0.0", VersionStatus.NEWER),
        ("2.0.0", "1.0.0", VersionStatus.NEWER),
        
        # Unknown status
        (None, "1.0.0", VersionStatus.UNKNOWN),
        ("1.0.0", None, VersionStatus.UNKNOWN),
        (None, None, VersionStatus.UNKNOWN),
        ("", "1.0.0", VersionStatus.UNKNOWN),
        ("1.0.0", "", VersionStatus.UNKNOWN),
    ],
)
def test_version_status(current_version, latest_version, expected_status):
    """Test version status determination with various version scenarios."""
    version_info = get_version_info(current_version, latest_version)
    assert version_info.status == expected_status, (
        f"Expected status {expected_status} but got {version_info.status} "
        f"for current={current_version}, latest={latest_version}"
    )


@pytest.mark.parametrize(
    "version1,version2,expected_major,expected_minor,expected_patch",
    [
        # No differences
        ("1.0.0", "1.0.0", 0, 0, 0),
        
        # Major differences
        ("1.0.0", "2.0.0", -1, 0, 0),
        ("2.0.0", "1.0.0", 1, 0, 0),
        
        # Minor differences
        ("1.0.0", "1.1.0", 0, -1, 0),
        ("1.1.0", "1.0.0", 0, 1, 0),
        
        # Patch differences
        ("1.0.0", "1.0.1", 0, 0, -1),
        ("1.0.1", "1.0.0", 0, 0, 1),
        
        # Combined differences
        ("1.2.3", "2.3.4", -1, -1, -1),
        ("2.3.4", "1.2.3", 1, 1, 1),
    ],
)
def test_version_difference_components(
    version1, version2, expected_major, expected_minor, expected_patch
):
    """Test individual component differences in versions."""
    version_info = get_version_info(version1, version2)
    if version_info.status != VersionStatus.UNKNOWN:
        diff = version_info.outdated_by if version_info.status == VersionStatus.OUTDATED else version_info.newer_by
        assert diff[0] == expected_major, f"Expected major diff {expected_major} but got {diff[0]}"
        assert diff[1] == expected_minor, f"Expected minor diff {expected_minor} but got {diff[1]}"
        assert diff[2] == expected_patch, f"Expected patch diff {expected_patch} but got {diff[2]}"