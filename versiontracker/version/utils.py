"""Version utility functions for composition and decomposition.

This module provides utility functions for working with version strings,
including composition, decomposition, and pattern matching.

Typical usage:
    from versiontracker.version.utils import decompose_version, compose_version_tuple

    components = decompose_version("1.2.3")
    # {'major': 1, 'minor': 2, 'patch': 3, 'build': 0}

    version_tuple = compose_version_tuple(1, 2, 3)
    # (1, 2, 3)
"""

import re
from typing import Any

from versiontracker.version.parser import parse_version

# Version patterns for different formats
VERSION_PATTERNS = [
    re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?$"),  # semantic
    re.compile(r"^(\d+)\.(\d+)$"),  # simple
    re.compile(r"^(\d+)$"),  # single
    re.compile(r"^(\d+)\.(\d+)\.(\d+)\.(\d+)$"),  # build
]

# Keep the dictionary version for backward compatibility
VERSION_PATTERN_DICT = {
    "semantic": re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?$"),
    "simple": re.compile(r"^(\d+)\.(\d+)$"),
    "single": re.compile(r"^(\d+)$"),
    "build": re.compile(r"^(\d+)\.(\d+)\.(\d+)\.(\d+)$"),
}


def compose_version_tuple(*components: int) -> tuple[int, ...]:
    """Compose a version tuple from individual components.

    Args:
        components: Version number components (major, minor, patch, build, etc.)

    Returns:
        Tuple of version numbers

    Examples:
        >>> compose_version_tuple(1, 2, 3)
        (1, 2, 3)
        >>> compose_version_tuple(1, 0, 0, 456)
        (1, 0, 0, 456)
    """
    return tuple(components)


def decompose_version(version_string: str | None) -> dict[str, int] | None:
    """Decompose a version string into components.

    Parses a version string and returns a dictionary with major, minor,
    patch, and build components.

    Args:
        version_string: Version string to decompose (e.g., "1.2.3")

    Returns:
        Dictionary with version components:
            - major: First version number
            - minor: Second version number
            - patch: Third version number
            - build: Fourth version number (or 0)
        Returns None if version_string is None or cannot be parsed.

    Examples:
        >>> decompose_version("1.2.3")
        {'major': 1, 'minor': 2, 'patch': 3, 'build': 0}
        >>> decompose_version("1.0")
        {'major': 1, 'minor': 0, 'patch': 0, 'build': 0}
        >>> decompose_version("")
        {'major': 0, 'minor': 0, 'patch': 0, 'build': 0}
        >>> decompose_version(None)
        None
    """
    if version_string is None:
        return None

    # Handle empty string
    if version_string == "":
        return {
            "major": 0,
            "minor": 0,
            "patch": 0,
            "build": 0,
        }

    parsed = parse_version(version_string)
    if parsed is None:
        return None

    return {
        "major": parsed[0] if len(parsed) > 0 else 0,
        "minor": parsed[1] if len(parsed) > 1 else 0,
        "patch": parsed[2] if len(parsed) > 2 else 0,
        "build": parsed[3] if len(parsed) > 3 else 0,
    }


def get_compiled_pattern(pattern: str) -> re.Pattern[str] | None:
    r"""Get a compiled regex pattern from a pattern string.

    Safely compiles a regex pattern, returning None if compilation fails.

    Args:
        pattern: Regex pattern string to compile

    Returns:
        Compiled regex pattern or None if compilation fails

    Examples:
        >>> pattern = get_compiled_pattern(r"^(\d+)\.(\d+)$")
        >>> pattern.match("1.2")
        <re.Match object; ...>
        >>> get_compiled_pattern("[invalid")
        None
    """
    try:
        return re.compile(pattern)
    except re.error:
        return None


def version_tuple_to_dict(version_tuple: tuple[int, ...]) -> dict[str, int]:
    """Convert a version tuple to a dictionary.

    Args:
        version_tuple: Tuple of version numbers

    Returns:
        Dictionary with major, minor, patch, build keys

    Examples:
        >>> version_tuple_to_dict((1, 2, 3))
        {'major': 1, 'minor': 2, 'patch': 3, 'build': 0}
    """
    return {
        "major": version_tuple[0] if len(version_tuple) > 0 else 0,
        "minor": version_tuple[1] if len(version_tuple) > 1 else 0,
        "patch": version_tuple[2] if len(version_tuple) > 2 else 0,
        "build": version_tuple[3] if len(version_tuple) > 3 else 0,
    }


def dict_to_version_tuple(version_dict: dict[str, Any]) -> tuple[int, ...]:
    """Convert a version dictionary to a tuple.

    Args:
        version_dict: Dictionary with major, minor, patch, build keys

    Returns:
        Tuple of version numbers

    Examples:
        >>> dict_to_version_tuple({'major': 1, 'minor': 2, 'patch': 3})
        (1, 2, 3, 0)
    """
    return (
        int(version_dict.get("major", 0)),
        int(version_dict.get("minor", 0)),
        int(version_dict.get("patch", 0)),
        int(version_dict.get("build", 0)),
    )


def normalize_version_string(version: str) -> str:
    """Normalize a version string by removing common prefixes.

    Removes common prefixes like 'v', 'version', and application names
    from version strings.

    Args:
        version: Version string to normalize

    Returns:
        Normalized version string

    Examples:
        >>> normalize_version_string("v1.2.3")
        "1.2.3"
        >>> normalize_version_string("Version 1.2.3")
        "1.2.3"
        >>> normalize_version_string("Firefox 100.0")
        "100.0"
    """
    # Remove common prefixes like "v" or "Version "
    cleaned = re.sub(r"^[vV]ersion\s+", "", version)
    cleaned = re.sub(r"^[vV](?:er\.?\s*)?", "", cleaned)

    # Handle application names at the beginning
    cleaned = re.sub(
        r"^(?:Google\s+)?(?:Chrome|Firefox|Safari)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^[a-zA-Z]+\s+(?=\d)", "", cleaned)

    return cleaned.strip()


def format_version_tuple(version_tuple: tuple[int, ...], separator: str = ".") -> str:
    """Format a version tuple as a string.

    Args:
        version_tuple: Tuple of version numbers
        separator: Separator between version components

    Returns:
        Formatted version string

    Examples:
        >>> format_version_tuple((1, 2, 3))
        "1.2.3"
        >>> format_version_tuple((1, 0, 0, 123), ".")
        "1.0.0.123"
    """
    return separator.join(str(n) for n in version_tuple)


def pad_version_tuple(version_tuple: tuple[int, ...], length: int = 3, pad_value: int = 0) -> tuple[int, ...]:
    """Pad a version tuple to a specified length.

    Args:
        version_tuple: Original version tuple
        length: Desired length of the tuple
        pad_value: Value to use for padding

    Returns:
        Padded version tuple

    Examples:
        >>> pad_version_tuple((1,), 3)
        (1, 0, 0)
        >>> pad_version_tuple((1, 2), 4)
        (1, 2, 0, 0)
    """
    if len(version_tuple) >= length:
        return version_tuple[:length]
    return version_tuple + (pad_value,) * (length - len(version_tuple))
