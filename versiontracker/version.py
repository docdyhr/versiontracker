"""
Version parsing and comparison utilities.

This module provides functionality for parsing, comparing, and working with
semantic version strings according to the project's version handling standards.
"""

import re

from versiontracker.exceptions import VersionError


def parse_version(
    version_string: str,
) -> tuple[int, int, int] | tuple[int, int, int, str] | tuple[int, int, int, str, int]:
    """
    Parse a version string into its components.

    Supports various version formats:
    - Simple: "1.2.3"
    - With v prefix: "v1.2.3" or "V1.2.3"
    - With prerelease: "1.2.3-alpha", "1.2.3-beta.1", "1.2.3-rc.2"

    Args:
        version_string: The version string to parse.

    Returns:
        A tuple containing version components (major, minor, patch) and
        optionally prerelease identifiers.

    Raises:
        VersionError: If the version string cannot be parsed.
    """
    if not version_string:
        raise VersionError("Version string cannot be empty")

    # Remove 'v' or 'V' prefix if present
    cleaned = version_string.strip()
    if cleaned.lower().startswith("v"):
        cleaned = cleaned[1:]

    # Pattern for semantic versioning with optional prerelease
    pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z]+)(?:\.(\d+))?)?$"
    match = re.match(pattern, cleaned)

    if not match:
        raise VersionError(f"Invalid version format: {version_string}")

    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))

    prerelease_tag = match.group(4)
    prerelease_num = match.group(5)

    if prerelease_tag and prerelease_num:
        return (major, minor, patch, prerelease_tag, int(prerelease_num))
    elif prerelease_tag:
        return (major, minor, patch, prerelease_tag)
    else:
        return (major, minor, patch)


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two version strings.

    Args:
        version1: First version string to compare.
        version2: Second version string to compare.

    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2

    Raises:
        VersionError: If either version string cannot be parsed.
    """
    parsed1 = parse_version(version1)
    parsed2 = parse_version(version2)

    # Compare major, minor, patch
    for i in range(3):
        if parsed1[i] < parsed2[i]:
            return -1
        elif parsed1[i] > parsed2[i]:
            return 1

    # Both have same major.minor.patch, check prerelease
    len1, len2 = len(parsed1), len(parsed2)

    # Release version is greater than prerelease
    if len1 == 3 and len2 > 3:
        return 1
    elif len1 > 3 and len2 == 3:
        return -1
    elif len1 == 3 and len2 == 3:
        return 0

    # Both have prereleases, compare them
    if len1 > 3 and len2 > 3:
        # Compare prerelease tags alphabetically
        tag1 = parsed1[3] if len1 > 3 else ""
        tag2 = parsed2[3] if len2 > 3 else ""

        if tag1 < tag2:
            return -1
        elif tag1 > tag2:
            return 1

        # Same tags, compare numbers if present
        num1 = parsed1[4] if len1 > 4 else 0
        num2 = parsed2[4] if len2 > 4 else 0

        if num1 < num2:
            return -1
        elif num1 > num2:
            return 1

    return 0


def is_newer_version(current: str, available: str) -> bool:
    """
    Check if an available version is newer than the current version.

    Args:
        current: The current version string.
        available: The available version string to check.

    Returns:
        True if available version is newer than current version.

    Raises:
        VersionError: If either version string cannot be parsed.
    """
    return compare_versions(current, available) < 0


def format_version(
    major: int, minor: int, patch: int, prerelease: str | None = None, prerelease_num: int | None = None
) -> str:
    """
    Format version components into a version string.

    Args:
        major: Major version number.
        minor: Minor version number.
        patch: Patch version number.
        prerelease: Optional prerelease tag.
        prerelease_num: Optional prerelease number.

    Returns:
        Formatted version string.
    """
    version = f"{major}.{minor}.{patch}"

    if prerelease:
        version = f"{version}-{prerelease}"
        if prerelease_num is not None:
            version = f"{version}.{prerelease_num}"

    return version
