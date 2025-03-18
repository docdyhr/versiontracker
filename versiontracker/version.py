"""Version comparison functionality for VersionTracker."""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

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


@dataclass
class VersionInfo:
    """Information about a version, including its parsed components."""

    name: str
    version_string: str
    parsed: Optional[Tuple[int, ...]] = None
    latest_version: Optional[str] = None
    latest_parsed: Optional[Tuple[int, ...]] = None
    status: VersionStatus = VersionStatus.UNKNOWN
    outdated_by: Optional[Tuple[int, ...]] = None

    def __post_init__(self):
        """Parse version string after initialization."""
        if self.version_string:
            self.parsed = parse_version(self.version_string)


def parse_version(version_string: str) -> Optional[Tuple[int, ...]]:
    """Parse a version string into a tuple of integers for comparison.

    Args:
        version_string: The version string to parse

    Returns:
        Optional[Tuple[int, ...]]: Parsed version as a tuple of integers, or None if parsing fails
    """
    if not version_string or not version_string.strip():
        return None

    # Clean the version string
    cleaned = version_string.strip().lower()

    # Try each pattern in order
    for pattern in VERSION_PATTERNS:
        match = re.match(pattern, cleaned)
        if match:
            # Extract all numbered groups that are not None
            components = [int(g) for g in match.groups() if g and g.isdigit()]
            if components:
                # Pad with zeros to ensure at least 3 components (major.minor.patch)
                while len(components) < 3:
                    components.append(0)
                return tuple(components)

    # If no pattern matches, try to extract any numbers from the string
    numbers = re.findall(r"\d+", cleaned)
    if numbers:
        components = [int(n) for n in numbers[:3]]  # Take at most 3 components
        while len(components) < 3:
            components.append(0)
        return tuple(components)

    logging.debug(f"Failed to parse version string: {version_string}")
    return None


def compare_versions(version1: Union[str, Tuple[int, ...]], version2: Union[str, Tuple[int, ...]]) -> int:
    """Compare two version strings or tuples.

    Args:
        version1: First version string or tuple
        version2: Second version string or tuple

    Returns:
        int: -1 if version1 < version2, 0 if version1 == version2, 1 if version1 > version2
    """
    # Parse strings to tuples if needed
    v1 = parse_version(version1) if isinstance(version1, str) else version1
    v2 = parse_version(version2) if isinstance(version2, str) else version2

    # Handle None cases
    if v1 is None and v2 is None:
        return 0
    if v1 is None:
        return -1
    if v2 is None:
        return 1

    # Compare tuples
    if v1 < v2:
        return -1
    if v1 > v2:
        return 1
    return 0


def get_version_difference(v1: Optional[Tuple[int, ...]], v2: Optional[Tuple[int, ...]]) -> Optional[Tuple[int, ...]]:
    """Calculate the difference between two version tuples.

    Args:
        v1: First version tuple
        v2: Second version tuple

    Returns:
        Optional[Tuple[int, ...]]: Tuple representing the version difference, or None if calculation isn't possible
    """
    if v1 is None or v2 is None:
        return None

    # Calculate the difference for each component
    max_len = max(len(v1), len(v2))
    
    # Pad with zeros
    padded_v1 = v1 + (0,) * (max_len - len(v1))
    padded_v2 = v2 + (0,) * (max_len - len(v2))
    
    # Calculate absolute differences
    return tuple(abs(a - b) for a, b in zip(padded_v1, padded_v2))


def format_outdated_indicator(version_info: VersionInfo) -> str:
    """Format an indicator string showing how outdated a version is.

    Args:
        version_info: Version information to format

    Returns:
        str: A formatted indicator string, e.g. "⚠️ (1.2.3 → 2.0.0)"
    """
    if version_info.status == VersionStatus.UP_TO_DATE:
        return "✓ Up to date"
    elif version_info.status == VersionStatus.NEWER:
        return "⚠️ Newer than latest"
    elif version_info.status == VersionStatus.OUTDATED and version_info.latest_version:
        return f"⚠️ Update available ({version_info.version_string} → {version_info.latest_version})"
    else:
        return "? Unknown status"


def get_homebrew_version_info(cask_name: str) -> Optional[str]:
    """Get the latest version information for a Homebrew cask.

    Args:
        cask_name: The name of the Homebrew cask

    Returns:
        Optional[str]: The latest version string, or None if not found
    """
    from versiontracker.utils import run_command
    
    try:
        brew_info_cmd = f"brew info --cask {cask_name}"
        info_lines = run_command(brew_info_cmd)
        
        # Look for version information in the output
        for line in info_lines:
            if ":" in line and "version" in line.lower():
                parts = line.split(":", 1)
                if len(parts) == 2 and "version" in parts[0].lower():
                    return parts[1].strip()
        
        return None
    except Exception as e:
        logging.error(f"Error getting version info for cask {cask_name}: {e}")
        return None


def find_matching_cask(app_name: str) -> Optional[str]:
    """Find a matching Homebrew cask for an application.

    Args:
        app_name: The name of the application

    Returns:
        Optional[str]: The matching cask name, or None if not found
    """
    from versiontracker.utils import run_command, BREW_SEARCH
    
    try:
        # Search for casks matching the app name
        brew_search = f"{BREW_SEARCH} --cask '{app_name}'"
        response = run_command(brew_search)
        
        from fuzzywuzzy.fuzz import partial_ratio
        
        # Filter out header lines
        casks = [item for item in response if item and "==>" not in item]
        
        # Find the best match
        best_match = None
        best_score = 0
        
        for cask in casks:
            score = partial_ratio(app_name.lower(), cask.lower())
            if score > best_score and score > 75:  # Require at least 75% similarity
                best_score = score
                best_match = cask
        
        return best_match
    except Exception as e:
        logging.error(f"Error finding matching cask for {app_name}: {e}")
        return None


def enrich_app_with_version_info(app: Tuple[str, str]) -> VersionInfo:
    """Enrich an application with version comparison information.

    Args:
        app: Tuple of (app_name, version_string)

    Returns:
        VersionInfo: Enhanced version information
    """
    app_name, version_string = app
    
    # Create basic version info
    version_info = VersionInfo(
        name=app_name,
        version_string=version_string
    )
    
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
        apps: List of (app_name, version) tuples

    Returns:
        List[VersionInfo]: List of applications with version status information
    """
    from tqdm import tqdm
    import concurrent.futures
    from versiontracker.utils import RateLimiter

    # Create a rate limiter (1 call per 2 seconds)
    rate_limiter = RateLimiter(calls_per_period=1, period=2)
    
    # Process applications with progress bar
    result = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        # Wrap the function to handle rate limiting
        def process_app(app):
            rate_limiter.wait()
            return enrich_app_with_version_info(app)
            
        # Map the function over all apps
        futures = [executor.submit(process_app, app) for app in apps]
        
        # Process results as they complete
        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Checking for updates",
            unit="app",
            ncols=80,
        ):
            try:
                result.append(future.result())
            except Exception as e:
                logging.error(f"Error processing app: {e}")
    
    # Sort by status (OUTDATED first) and then by name
    result.sort(key=lambda x: (x.status != VersionStatus.OUTDATED, x.name.lower()))
    
    return result
