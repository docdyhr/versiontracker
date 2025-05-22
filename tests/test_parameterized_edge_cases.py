"""Test module for version comparison edge cases with parameterized tests.

This module tests version comparison functionality with a focus on edge cases,
using parameterized tests to improve coverage and reduce code duplication.
"""

import pytest

from versiontracker.version import (
    compare_versions,
    parse_version,
    get_version_difference,
    get_version_info,
    VersionStatus,
)


@pytest.mark.parametrize(
    "version1,version2,expected_result",
    [
        # Empty versions
        ("", "", 0),
        (None, None, 0),
        (None, "1.0", -1),
        ("1.0", None, 1),
        ("", "1.0", -1),
        ("1.0", "", 1),
        
        # Malformed versions
        ("not a version", "also not a version", 0),
        ("not a version", "1.0", -1),
        ("1.0", "not a version", 1),
        
        # Versions with text and whitespace
        ("version 1.0", "version 1.0", 0),
        ("version 1.0", "version 1.1", -1),
        ("version  1.0", "version 1.0", 0),  # Extra whitespace
        ("VERSION 1.0", "version 1.0", 0),  # Case insensitive
        
        # Versions with special characters
        ("1.0-alpha", "1.0-beta", -1),
        ("1.0+build.1", "1.0+build.2", 0),  # Build metadata should be ignored
        ("1.0-rc.1", "1.0-rc.2", -1),
        ("1.0-rc.1", "1.0", -1),
        
        # Complex version formats
        ("1.0.0-alpha.beta", "1.0.0-alpha.beta", 0),
        ("1.0.0-alpha.1", "1.0.0-alpha.beta", -1),
        ("1.0.0-beta.11", "1.0.0-beta.2", 1),  # Numeric comparison, not lexical
        ("1.0.0-beta.11", "1.0.0-rc.1", -1),
        
        # Dot-separated with varying components
        ("1", "1.0.0.0", 0),
        ("1.0", "1.0.0", 0),
        ("1.0.0", "1.0.0.0", 0),
        ("1.2", "1.2.0.0", 0),
        
        # Application-specific formats
        ("Firefox 91.0.2", "Firefox 91.0.2", 0),
        ("Firefox 91.0.2", "Firefox 92.0.0", -1),
        ("Chrome 94.0.4606.71", "Chrome 94.0.4606.81", -1),
        ("Google Chrome 94", "Google Chrome 94.0.4606.81", 0),
        
        # Extreme values
        ("999999.999999.999999", "999999.999999.999999", 0),
        ("0.0.0", "0.0.0", 0),
        ("0.0.0", "0.0.1", -1),
        
        # Version with varying separators
        ("1-0-0", "1.0.0", 0),
        ("1_0_0", "1.0.0", 0),
        ("1/0/0", "1.0.0", 0),
        
        # Unusual real-world version formats
        ("2021.05", "2021.06", -1),
        ("r20210501", "r20210601", -1),
        ("v2.3.0", "v2.3.1", -1),
        ("Version 1.2", "Version 1.3", -1),
        
        # Multiple numeric components
        ("1.2.3.4.5", "1.2.3.4.5", 0),
        ("1.2.3.4.5", "1.2.3.4.6", -1),
        ("1.2.3.4.5", "1.2.3.5.1", -1),
        
        # Leading zeros
        ("1.02.0", "1.2.0", 0),
        ("01.2.3", "1.2.3", 0),
        ("1.2.03", "1.2.3", 0),
        
        # Unicode characters
        ("1.0.0-α", "1.0.0-β", -1),
        ("1.0.0-α", "1.0.0-α", 0),
        
        # Versions with different sections that numerically compare the same
        ("1.10", "1.1.0", 1),  # 1.10 > 1.1.0
        ("1.1", "1.01", 0),
        ("1.0.0-final", "1.0.0", -1),
        
        # Edge cases with major.minor.patch vs year.month formats
        ("2021.1", "10.1", 1),  # Year-based versions are usually larger
        ("20.1", "2020.1", -1),
        
        # Mixed formats
        ("v1.0 build 1234", "v1.0 build 1235", -1),
        ("1.0 (1234)", "1.0 (1235)", -1),
        ("1.0-dev-1234", "1.0-dev-1235", -1),
        
        # Semver specific
        ("1.0.0-alpha", "1.0.0-alpha.1", -1),
        ("1.0.0-alpha.1", "1.0.0-alpha.beta", -1),
        ("1.0.0-alpha.beta", "1.0.0-beta", -1),
        ("1.0.0-beta", "1.0.0-beta.2", -1),
        ("1.0.0-beta.2", "1.0.0-beta.11", -1),
        ("1.0.0-beta.11", "1.0.0-rc.1", -1),
        ("1.0.0-rc.1", "1.0.0", -1),
    ],
)
def test_compare_versions_edge_cases(version1, version2, expected_result):
    """Test version comparison with various edge cases."""
    result = compare_versions(version1, version2)
    assert result == expected_result, f"Expected {expected_result} but got {result} for {version1} vs {version2}"


@pytest.mark.parametrize(
    "version_string,expected_tuple",
    [
        # Empty versions
        ("", (0, 0, 0)),
        (None, (0, 0, 0)),
        
        # Malformed versions
        ("not a version", (0, 0, 0)),
        ("version without numbers", (0, 0, 0)),
        
        # Versions with text and whitespace
        ("version 1.0", (1, 0, 0)),
        ("version  1.0", (1, 0, 0)),  # Extra whitespace
        ("VERSION 1.0", (1, 0, 0)),  # Case insensitive
        ("ver. 1.0", (1, 0, 0)),
        
        # Versions with special characters
        ("1.0-alpha", (1, 0, 0)),
        ("1.0+build.1", (1, 0, 0, 1)),
        ("1.0-rc.1", (1, 0, 0, 1)),
        
        # Complex version formats
        ("1.0.0-alpha.beta", (1, 0, 0)),
        ("1.0.0-alpha.1", (1, 0, 0, 1)),
        ("1.0.0-beta.11", (1, 0, 0, 11)),
        
        # Dot-separated with varying components
        ("1", (1, 0, 0)),
        ("1.0", (1, 0, 0)),
        ("1.0.0", (1, 0, 0)),
        ("1.0.0.0", (1, 0, 0, 0)),
        ("1.2", (1, 2, 0)),
        ("1.2.0", (1, 2, 0)),
        
        # Application-specific formats
        ("Firefox 91.0.2", (91, 0, 2)),
        ("Chrome 94.0.4606.71", (94, 0, 4606, 71)),
        ("Google Chrome 94", (94, 0, 0)),
        
        # Extreme values
        ("999999.999999.999999", (999999, 999999, 999999)),
        ("0.0.0", (0, 0, 0)),
        
        # Version with varying separators
        ("1-0-0", (1, 0, 0)),
        ("1_0_0", (1, 0, 0)),
        ("1/0/0", (1, 0, 0)),
        
        # Unusual real-world version formats
        ("2021.05", (2021, 5, 0)),
        ("r20210501", (20210501, 0, 0)),
        ("v2.3.0", (2, 3, 0)),
        ("Version 1.2", (1, 2, 0)),
        
        # Multiple numeric components
        ("1.2.3.4.5", (1, 2, 3, 4, 5)),
        
        # Leading zeros
        ("1.02.0", (1, 2, 0)),
        ("01.2.3", (1, 2, 3)),
        ("1.2.03", (1, 2, 3)),
        
        # Unicode characters
        ("1.0.0-α", (1, 0, 0)),
        
        # Mixed formats
        ("v1.0 build 1234", (1, 0, 0, 1234)),
        ("1.0 (1234)", (1, 0, 0, 1234)),
        ("1.0-dev-1234", (1, 0, 0, 1234)),
        
        # Large numeric components
        ("1.9999999999.3", (1, 9999999999, 3)),
        
        # Versions with dashes
        ("1.0.0-20210501", (1, 0, 0, 20210501)),
        
        # Versions with words inside
        ("1.beta.0", (1, 0, 0)),
        ("1.0.beta", (1, 0, 0)),
        
        # Very large components
        ("9".ljust(100, "9") + ".0.0", (int("9".ljust(100, "9")), 0, 0)),
    ],
)
def test_parse_version_edge_cases(version_string, expected_tuple):
    """Test version parsing with various edge cases."""
    result = parse_version(version_string)
    assert result == expected_tuple, f"Expected {expected_tuple} but got {result} for '{version_string}'"


@pytest.mark.parametrize(
    "version1,version2,expected_difference",
    [
        # Empty versions
        ("", "", (0, 0, 0)),
        (None, None, None),
        (None, "1.0", None),
        ("1.0", None, None),
        
        # Malformed versions
        ("not a version", "also not a version", (0, 0, 0)),
        ("not a version", "1.0", None),
        ("1.0", "not a version", None),
        
        # Same versions with different formats
        ("1.0", "1.0.0", (0, 0, 0)),
        ("v1.0", "1.0", (0, 0, 0)),
        ("Version 1.0", "v1.0", (0, 0, 0)),
        
        # Simple differences
        ("1.0.0", "1.0.1", (0, 0, -1)),
        ("1.0.0", "1.1.0", (0, -1, 0)),
        ("1.0.0", "2.0.0", (-1, 0, 0)),
        
        # Complex differences
        ("1.2.3", "3.2.1", (-2, 0, 2)),
        ("1.2.3", "1.3.2", (0, -1, 1)),
        
        # Multiple component differences
        ("1.2.3.4", "1.2.3.5", (0, 0, 0, -1)),
        ("1.2.3.4", "1.2.4.4", (0, 0, -1, 0)),
        
        # Large differences
        ("1.0.0", "999.0.0", (-998, 0, 0)),
        ("1.0.0", "1.999.0", (0, -999, 0)),
        
        # Special versions
        ("1.0.0-alpha", "1.0.0-beta", (0, 0, 0)),  # Ignores pre-release tags
        ("1.0.0+build.1", "1.0.0+build.2", (0, 0, 0)),  # Ignores build metadata
        
        # Unusual formats
        ("2021.05", "2021.06", (0, -1, 0)),
        ("r20210501", "r20210601", (-100, 0, 0)),
    ],
)
def test_version_difference_edge_cases(version1, version2, expected_difference):
    """Test version difference calculation with various edge cases."""
    result = get_version_difference(version1, version2)
    assert result == expected_difference, f"Expected {expected_difference} but got {result} for {version1} vs {version2}"


@pytest.mark.parametrize(
    "current_version,latest_version,expected_status",
    [
        # Edge cases for version status
        (None, None, VersionStatus.UNKNOWN),
        ("", "", VersionStatus.UP_TO_DATE),
        (None, "1.0", VersionStatus.UNKNOWN),
        ("1.0", None, VersionStatus.UNKNOWN),
        
        # Malformed versions
        ("not a version", "also not a version", VersionStatus.UNKNOWN),
        ("not a version", "1.0", VersionStatus.UNKNOWN),
        
        # Various comparison scenarios
        ("1.0", "1.0", VersionStatus.UP_TO_DATE),
        ("1.0", "1.1", VersionStatus.OUTDATED),
        ("1.1", "1.0", VersionStatus.NEWER),
        
        # Different formats
        ("v1.0", "1.0", VersionStatus.UP_TO_DATE),
        ("Version 1.0", "v1.0", VersionStatus.UP_TO_DATE),
        
        # Pre-release versions
        ("1.0.0-alpha", "1.0.0", VersionStatus.OUTDATED),
        ("1.0.0", "1.0.0-alpha", VersionStatus.NEWER),
        ("1.0.0-alpha", "1.0.0-beta", VersionStatus.OUTDATED),
        
        # Build metadata (should be ignored)
        ("1.0.0+build.1", "1.0.0+build.2", VersionStatus.UP_TO_DATE),
        
        # Complex versions
        ("Firefox 91.0.2", "Firefox 92.0.0", VersionStatus.OUTDATED),
        ("Chrome 94.0.4606.71", "Chrome 94.0.4606.81", VersionStatus.OUTDATED),
        
        # Unusual formats
        ("2021.05", "2021.06", VersionStatus.OUTDATED),
        ("r20210501", "r20210601", VersionStatus.OUTDATED),
        ("v2.3.0", "v2.3.1", VersionStatus.OUTDATED),
    ],
)
def test_version_status_edge_cases(current_version, latest_version, expected_status):
    """Test version status determination with various edge cases."""
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
        
        # Extreme differences
        ("1.0.0", "999.0.0", -998, 0, 0),
        ("1.0.0", "1.999.0", 0, -999, 0),
        ("1.0.0", "1.0.999", 0, 0, -999),
        
        # Different formats
        ("v1.0.0", "1.0.0", 0, 0, 0),
        ("Version 1.0.0", "v1.0.0", 0, 0, 0),
        
        # Different component lengths
        ("1", "2.0.0", -1, 0, 0),
        ("1.0", "1.1.0", 0, -1, 0),
    ],
)
def test_version_difference_components_edge_cases(
    version1, version2, expected_major, expected_minor, expected_patch
):
    """Test individual component differences in versions with edge cases."""
    version_info = get_version_info(version1, version2)
    if version_info.status != VersionStatus.UNKNOWN:
        diff = version_info.newer_by if version_info.status == VersionStatus.NEWER else version_info.outdated_by
        
        # Check only the first three components (major, minor, patch)
        if len(diff) >= 3:
            assert diff[0] == expected_major, f"Expected major diff {expected_major} but got {diff[0]}"
            assert diff[1] == expected_minor, f"Expected minor diff {expected_minor} but got {diff[1]}"
            assert diff[2] == expected_patch, f"Expected patch diff {expected_patch} but got {diff[2]}"