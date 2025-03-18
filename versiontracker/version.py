"""Version comparison functionality for VersionTracker."""

import logging
import re
import subprocess
from enum import Enum
from typing import List, Optional, Tuple, Union, cast

from fuzzywuzzy import fuzz  # type: ignore

# Regular expression patterns for version extraction
VERSION_PATTERNS = [
    # Standard semantic versioning: 1.2.3
    r"(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?",
    # Two-component version: 1.2
    r"^(\d+)\.(\d+)$",
    # Mac-style version with build: 1.2 (345)
    r"(\d+)\.(\d+)(?:\.(\d+))?\s*(?:\(([a-zA-Z0-9.-]+)\))?",
    # Simple numeric version: 1
    r"^(\d+)$",
]


class VersionStatus(Enum):
    """Status of a version comparison."""

    UNKNOWN = "unknown"
    UP_TO_DATE = "up_to_date"
    OUTDATED = "outdated"
    NEWER = "newer"


class VersionInfo:
    """Information about a version, including its parsed components."""

    def __init__(
        self,
        name: str,
        version_string: str,
        parsed: Optional[Tuple[int, ...]] = None,
        latest_version: Optional[str] = None,
        latest_parsed: Optional[Tuple[int, ...]] = None,
        status: VersionStatus = VersionStatus.UNKNOWN,
        outdated_by: Optional[Tuple[int, ...]] = None,
    ):
        """Initialize a VersionInfo object."""
        self.name = name
        self.version_string = version_string
        self.parsed = parsed
        self.latest_version = latest_version
        self.latest_parsed = latest_parsed
        self.status = status
        self.outdated_by = outdated_by

        if self.version_string:
            self.parsed = parse_version(self.version_string)


def parse_version(version_string: Optional[str]) -> Optional[Tuple[int, ...]]:
    """Parse a version string into a tuple of integers for comparison.

    Args:
        version_string: The version string to parse

    Returns:
        Optional[Tuple[int, ...]]: A tuple of integers representing the version
        components, or None if the input is None or empty

    Examples:
        >>> parse_version("1.2.3")
        (1, 2, 3)
        >>> parse_version("2.0")
        (2, 0, 0)
        >>> parse_version("1.2 (345)")
        (1, 2, 345)
    """
    if version_string is None or not version_string.strip():
        return None

    # Clean up the version string
    version_string = version_string.strip().lower()

    # Remove non-alphanumeric characters except periods, spaces, parentheses, and hyphens
    version_string = re.sub(r"[^\w\s\.\(\)\-]", "", version_string)

    # Try each pattern until one works
    for pattern in VERSION_PATTERNS:
        match = re.search(pattern, version_string)
        if match:
            # Get all capture groups that are not None
            components = tuple(int(g) for g in match.groups() if g is not None and g.isdigit())
            if components:
                # Pad with zeros to ensure at least 3 components (major.minor.patch)
                if len(components) == 1:
                    return components + (0, 0)
                elif len(components) == 2:
                    return components + (0,)
                return components

    # Fallback: use any numbers found in the string
    numbers = re.findall(r"\d+", version_string)
    if numbers:
        components = tuple(int(n) for n in numbers)
        # Pad with zeros to ensure at least 3 components
        if len(components) == 1:
            return components + (0, 0)
        elif len(components) == 2:
            return components + (0,)
        return components

    # Last resort
    return None


def compare_versions(
    version1: Union[str, Tuple[int, ...], None], version2: Union[str, Tuple[int, ...], None]
) -> int:
    """Compare two version strings or tuples.

    Args:
        version1: First version
        version2: Second version

    Returns:
        int: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
    """
    # Parse strings to tuples if needed
    v1_parsed = parse_version(version1) if isinstance(version1, str) else version1
    v2_parsed = parse_version(version2) if isinstance(version2, str) else version2

    # Handle None cases
    if v1_parsed is None and v2_parsed is None:
        return 0
    if v1_parsed is None:
        return -1
    if v2_parsed is None:
        return 1

    # At this point, we know v1_parsed and v2_parsed are not None
    v1: Tuple[int, ...] = v1_parsed
    v2: Tuple[int, ...] = v2_parsed

    # Make sure both tuples have the same length
    max_len = max(len(v1), len(v2))
    v1_padded = v1 + (0,) * (max_len - len(v1))
    v2_padded = v2 + (0,) * (max_len - len(v2))

    # Compare tuples
    if v1_padded < v2_padded:
        return -1
    elif v1_padded > v2_padded:
        return 1
    else:
        return 0


def get_version_difference(
    version1: Union[str, Tuple[int, ...], None], version2: Union[str, Tuple[int, ...], None]
) -> Optional[Tuple[int, ...]]:
    """Calculate the difference between two versions.

    Args:
        version1: First version as string or tuple
        version2: Second version as string or tuple

    Returns:
        Optional[Tuple[int, ...]]: The component-wise difference between the versions,
        or None if either input is None
    """
    # Handle None cases
    if version1 is None or version2 is None:
        return None

    # Parse strings to tuples if needed
    v1_parsed = parse_version(version1) if isinstance(version1, str) else version1
    v2_parsed = parse_version(version2) if isinstance(version2, str) else version2

    # Handle if parsing resulted in None
    if v1_parsed is None or v2_parsed is None:
        return None

    # Now we know both are valid tuples
    v1: Tuple[int, ...] = v1_parsed
    v2: Tuple[int, ...] = v2_parsed

    # Make sure both tuples have the same length
    max_len = max(len(v1), len(v2))
    v1_padded = v1 + (0,) * (max_len - len(v1))
    v2_padded = v2 + (0,) * (max_len - len(v2))

    # Calculate differences
    differences = tuple(abs(a - b) for a, b in zip(v1_padded, v2_padded))
    return differences


def get_version_info(
    old_version: Union[str, Tuple[int, ...], None], new_version: Union[str, Tuple[int, ...], None]
) -> str:
    """Get human-readable description of version change.

    Args:
        old_version: Original version as string or tuple
        new_version: New version as string or tuple

    Returns:
        str: A human-readable description of the version difference
    """
    # Parse strings to tuples if needed
    v1_parsed = parse_version(old_version) if isinstance(old_version, str) else old_version
    v2_parsed = parse_version(new_version) if isinstance(new_version, str) else new_version

    # Handle None cases
    if v1_parsed is None or v2_parsed is None:
        old_str = str(old_version) if old_version is not None else "unknown"
        new_str = str(new_version) if new_version is not None else "unknown"
        return f"Version changed ({old_str} → {new_str})"

    # Now we know both are valid tuples
    v1: Tuple[int, ...] = v1_parsed
    v2: Tuple[int, ...] = v2_parsed

    # Format as strings for display
    v1_str = ".".join(str(c) for c in v1)
    v2_str = ".".join(str(c) for c in v2)

    # Get component-wise differences
    diff = get_version_difference(v1, v2)

    # If diff is None, something went wrong
    if diff is None:
        return f"Version changed ({v1_str} → {v2_str})"

    # Major version change
    if diff[0] > 0:
        return f"Major version update ({v1_str} → {v2_str})"
    # Minor version change
    elif len(diff) > 1 and diff[1] > 0:
        return f"Minor version update ({v1_str} → {v2_str})"
    # Patch version change
    elif len(diff) > 2 and diff[2] > 0:
        return f"Patch update ({v1_str} → {v2_str})"
    # Other change
    else:
        return f"Version updated ({v1_str} → {v2_str})"


def format_version_difference(
    old_version: Union[str, Tuple[int, ...], None],
    new_version: Union[str, Tuple[int, ...], None],
) -> str:
    """Format version difference as a human-readable string.

    Args:
        old_version: Original version as string or tuple
        new_version: New version as string or tuple

    Returns:
        str: A human-readable description of the version difference
    """
    return get_version_info(old_version, new_version)


def find_matching_cask(app_name: str) -> Optional[str]:
    """Find a matching Homebrew cask for the given app name.

    Args:
        app_name: The name of the application

    Returns:
        Optional[str]: The name of the matching cask, or None if not found
    """
    try:
        # Search for the app in Homebrew casks
        brew_search = f"brew search --casks '{app_name}'"
        response = subprocess.run(
            brew_search.split(),
            capture_output=True,
            text=True,
            check=False,
        ).stdout.splitlines()

        # Filter out header lines
        casks = [item for item in response if item and "==>" not in item]

        # Find the best match
        best_match = None
        best_score = 0

        for cask in casks:
            score = fuzz.partial_ratio(app_name.lower(), cask.lower())
            if score > best_score and score > 75:  # Require at least 75% similarity
                best_score = score
                best_match = cask

        return best_match
    except Exception as e:
        logging.error(f"Error finding matching cask for {app_name}: {e}")
        return None


def get_homebrew_version_info(cask_name: str) -> str:
    """Get the latest version information for a Homebrew cask.

    Args:
        cask_name: The name of the Homebrew cask

    Returns:
        str: The latest version string
    """
    try:
        brew_info_cmd = f"brew info --cask {cask_name}"
        info_lines = subprocess.run(
            brew_info_cmd.split(),
            capture_output=True,
            text=True,
            check=False,
        ).stdout.splitlines()

        # Look for version information in the output
        for line in info_lines:
            if ":" in line and "version" in line.lower():
                parts = line.split(":", 1)
                if len(parts) == 2 and "version" in parts[0].lower():
                    return parts[1].strip()

        return ""
    except Exception as e:
        logging.error(f"Error getting version info for cask {cask_name}: {e}")
        return ""


def enrich_app_with_version_info(app: Tuple[str, str]) -> VersionInfo:
    """Enrich an application with version comparison information.

    Args:
        app (Tuple[str, str]): Tuple of (app_name, version_string)

    Returns:
        VersionInfo: Enhanced version information
    """
    app_name, version_string = app

    version_info = VersionInfo(name=app_name, version_string=version_string)

    # Find matching cask
    matching_cask = find_matching_cask(app_name)
    if matching_cask:
        # Get latest version from Homebrew
        latest_version = get_homebrew_version_info(matching_cask)
        if latest_version:
            version_info.latest_version = latest_version
            version_info.latest_parsed = parse_version(latest_version)

            # Determine version status
            if version_info.parsed and version_info.latest_parsed:
                comparison = compare_versions(version_info.parsed, version_info.latest_parsed)
                if comparison < 0:
                    version_info.status = VersionStatus.OUTDATED
                    version_info.outdated_by = get_version_difference(
                        version_info.parsed, version_info.latest_parsed
                    )
                elif comparison > 0:
                    version_info.status = VersionStatus.NEWER
                else:
                    version_info.status = VersionStatus.UP_TO_DATE

    return version_info


def check_outdated_apps(apps: List[Tuple[str, str]]) -> List[VersionInfo]:
    """Check which applications are outdated compared to their Homebrew versions.

    Args:
        apps (List[Tuple[str, str]]): List of (app_name, version_string) tuples

    Returns:
        List[VersionInfo]: List of applications with version status information
    """
    import concurrent.futures

    result = []
    total = len(apps)

    if total <= 0:
        logging.warning("No applications to check")
        return []

    logging.info(f"Checking {total} applications against Homebrew versions...")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for app in apps:
            if not app[0] or not app[1]:
                continue

            futures.append(executor.submit(enrich_app_with_version_info, app))

        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            try:
                version_info = future.result()
                result.append(version_info)
                # Log progress every 10 apps
                if (i + 1) % 10 == 0:
                    logging.info(f"Processed {i + 1}/{total} applications...")
            except Exception as e:
                logging.error(f"Error processing app: {e}")

    # Sort by status (OUTDATED first) and then by name
    result.sort(key=lambda x: (x.status != VersionStatus.OUTDATED, x.name.lower()))

    return result


def format_outdated_indicator(version_info: VersionInfo) -> str:
    """Format an indicator string showing how outdated a version is.

    Args:
        version_info: Version information

    Returns:
        str: A formatted indicator string, e.g. "⚠️ (1.2.3 → 2.0.0)"
    """
    if version_info.status == VersionStatus.UP_TO_DATE:
        return "✓ Up to date"
    elif version_info.status == VersionStatus.NEWER:
        return "⚠️ Newer than latest"
    elif version_info.status == VersionStatus.OUTDATED and version_info.latest_version:
        return (
            f"⚠️ Update available ({version_info.version_string} → "
            f"{version_info.latest_version})"
        )
    else:
        return "? Unknown status"
