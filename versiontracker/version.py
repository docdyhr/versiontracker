"""Version checking utility functions."""

import logging
import multiprocessing
import os
import re
import json
import subprocess
import functools
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union, NamedTuple, Set, cast
import warnings
import time
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

try:
    from rapidfuzz import fuzz as rapidfuzz
    from rapidfuzz import process
    USE_RAPIDFUZZ = True
except ImportError:
    from fuzzywuzzy import fuzz  # type: ignore
    USE_RAPIDFUZZ = False

# Import tqdm for progress bars
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    # Simple fallback if tqdm is not available
    def tqdm(iterable, **kwargs):
        return iterable
    HAS_TQDM = False

from versiontracker.config import config
from versiontracker.utils import normalise_name, run_command

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
    """Class representing version information for an application."""

    def __init__(self, name: str, version_string: str, 
                 latest_version: Optional[str] = None,
                 latest_parsed: Optional[Tuple[int, ...]] = None,
                 status: VersionStatus = VersionStatus.UNKNOWN,
                 outdated_by: Optional[Tuple[int, ...]] = None):
        """Initialize version information.

        Args:
            name: Name of the application
            version_string: Version string of the application
            latest_version: Latest version string, if available
            latest_parsed: Parsed latest version tuple, if available
            status: Version status (UNKNOWN, UP_TO_DATE, OUTDATED, etc.)
            outdated_by: Version difference tuple, if available
        """
        self.name = name
        self.version_string = version_string
        self.latest_version = latest_version
        self.status = status
        self._parsed = parse_version(version_string)
        self._parsed_dict = _parse_version_components(version_string)
        self._latest_parsed = latest_parsed if latest_parsed else parse_version(latest_version) if latest_version else None
        self._outdated_by = outdated_by
        
        # Calculate outdated_by if not provided and we have both versions
        if self._outdated_by is None and self._parsed and self._latest_parsed:
            self._outdated_by = get_version_difference(self._parsed, self._latest_parsed)

    @property
    def parsed(self) -> Optional[Tuple[int, ...]]:
        """Get the parsed version as a tuple.

        Returns:
            Optional[Tuple[int, ...]]: Parsed version tuple or None
        """
        return self._parsed

    @property
    def parsed_dict(self) -> Optional[Dict[str, Union[int, str]]]:
        """Get the parsed version as a dictionary.

        Returns:
            Optional[Dict[str, Union[int, str]]]: Parsed version dictionary or None
        """
        return self._parsed_dict
        
    @property
    def latest_parsed(self) -> Optional[Tuple[int, ...]]:
        """Get the latest parsed version as a tuple.

        Returns:
            Optional[Tuple[int, ...]]: Latest parsed version tuple or None
        """
        return self._latest_parsed
        
    @property
    def outdated_by(self) -> Optional[Tuple[int, ...]]:
        """Get the difference between current and latest version.

        Returns:
            Optional[Tuple[int, ...]]: Version difference or None
        """
        return self._outdated_by


# Add a precompiled regex pattern cache for better performance
@functools.lru_cache(maxsize=32)
def get_compiled_pattern(pattern: str) -> re.Pattern:
    """Get a compiled regular expression pattern.
    
    Args:
        pattern (str): The regex pattern string
        
    Returns:
        re.Pattern: The compiled pattern
    """
    return re.compile(pattern)


def decompose_version(version: str) -> Optional[Dict[str, Union[int, str]]]:
    """Decompose a version string into its components.

    Args:
        version: Version string to decompose

    Returns:
        Optional[Dict[str, Union[int, str]]]: Version components as a dictionary
    """
    if not version:
        return None

    # Normalize version string
    version = version.strip().lower()

    # Extract components using regex pattern
    for pattern in VERSION_PATTERNS:
        match = re.search(pattern, version)
        if match:
            groups = match.groupdict()
            version_parts: Dict[str, Union[int, str]] = {}
            
            # Convert numeric components to integers
            for key, value in groups.items():
                if value is not None:
                    if key in ["major", "minor", "patch"] and value.isdigit():
                        version_parts[key] = int(value)
                    else:
                        version_parts[key] = value

            # Ensure the standard components exist (with defaults)
            for component in ["major", "minor", "patch"]:
                if component not in version_parts:
                    version_parts[component] = 0

            return version_parts

    return None


def _parse_version_components(version_str: str) -> Optional[Dict[str, Union[int, str]]]:
    """Parse a version string into components using regular expressions.
    
    Args:
        version_str: Version string to parse
        
    Returns:
        Optional[Dict[str, Union[int, str]]]: Dictionary with version components
    """
    # Try each pattern in sequence
    for pattern in VERSION_PATTERNS:
        match = re.search(pattern, version_str)
        if match:
            version_dict: Dict[str, Union[int, str]] = {}
            
            # Process each named group in the match
            for component, value in match.groupdict().items():
                if value is not None:
                    # Convert major, minor, patch to integers if they're digits
                    if component in ["major", "minor", "patch"] and value.isdigit():
                        version_dict[component] = int(value)
                    else:
                        version_dict[component] = value
            
            # Fill in missing components with defaults
            for component in ["major", "minor", "patch"]:
                if component not in version_dict:
                    version_dict[component] = 0
                    
            # Add build number if present
            if "build" not in version_dict or not version_dict["build"]:
                version_dict["build"] = ""
                
            return version_dict
                
    return None


def _parse_version_to_dict(version_str: Optional[str]) -> Optional[Dict[str, Union[int, str]]]:
    """Parse a version string into a dictionary of components.

    Args:
        version_str (Optional[str]): The version string to parse

    Returns:
        Optional[Dict[str, Union[int, str]]]: A dictionary with the version components
    """
    if version_str is None or not version_str.strip():
        return None

    # Clean up the version string
    version_str = version_str.strip().lower()
    
    # Remove non-alphanumeric characters except periods, spaces, parentheses, and hyphens
    version_str = re.sub(r"[^\w\s\.\(\)\-]", "", version_str)

    for pattern in VERSION_PATTERNS:
        compiled_pattern = get_compiled_pattern(pattern)
        match = compiled_pattern.search(version_str)
        if match:
            groups = match.groups()
            result: Dict[str, Union[int, str]] = {
                "major": int(groups[0]) if groups[0] and groups[0].isdigit() else 0,
                "minor": int(groups[1]) if len(groups) > 1 and groups[1] and groups[1].isdigit() else 0,
                "patch": int(groups[2]) if len(groups) > 2 and groups[2] and groups[2].isdigit() else 0,
            }
            
            # Handle additional components if available
            if len(groups) > 3 and groups[3]:
                result["prerelease"] = groups[3]
            if len(groups) > 4 and groups[4]:
                result["build"] = groups[4]
                
            return result

    # Fallback: use any numbers found in the string
    numbers = re.findall(r"\d+", version_str)
    if numbers:
        return {
            "major": int(numbers[0]) if len(numbers) > 0 else 0,
            "minor": int(numbers[1]) if len(numbers) > 1 else 0,
            "patch": int(numbers[2]) if len(numbers) > 2 else 0
        }

    # If no pattern matches, use the string as-is
    return {"version": version_str}


def parse_version(version_str: Optional[str]) -> Optional[Tuple[int, ...]]:
    """Parse a version string into a tuple of integers.

    Args:
        version_str: The version string to parse

    Returns:
        Optional[Tuple[int, ...]]: A tuple of integers representing the version components,
        or None if parsing fails
    """
    if version_str is None or not version_str.strip():
        return None

    # Simple common patterns
    simple_pattern = r"(?:v|version\s+)?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?(?:[^\d].*)?$"
    match = re.search(simple_pattern, version_str.lower(), re.IGNORECASE)
    
    if match:
        components = []
        for group in match.groups():
            if group is not None:
                components.append(int(group))
            else:
                # Only add trailing zeros for major and minor, not for patch or build
                if len(components) < 2:
                    components.append(0)
                
        # Ensure we at least have major.minor.patch
        while len(components) < 3:
            components.append(0)
            
        return tuple(components)

    # Try dictionary-based parsing as a fallback
    version_dict = _parse_version_components(version_str)
    if version_dict:
        major = int(version_dict.get("major", 0))
        minor = int(version_dict.get("minor", 0))
        patch = int(version_dict.get("patch", 0))
        return (major, minor, patch)
    
    return None


def _dict_to_tuple(version_dict: Optional[Dict[str, Union[int, str]]]) -> Optional[Tuple[int, ...]]:
    """Convert a version dictionary to a version tuple.

    Args:
        version_dict: Version dictionary

    Returns:
        Optional[Tuple[int, ...]]: Version tuple
    """
    if not version_dict:
        return None
        
    # Extract components
    major = int(version_dict.get("major", 0))
    minor = int(version_dict.get("minor", 0))
    patch = int(version_dict.get("patch", 0))
    
    # Create a tuple with major, minor, patch
    version_tuple: Tuple[int, ...] = (major, minor, patch)
    
    # Add build number if it's numeric
    build = version_dict.get("build", "")
    if isinstance(build, str) and build.isdigit():
        version_tuple = version_tuple + (int(build),)
    
    return version_tuple


def _tuple_to_dict(version_tuple: Optional[Tuple[int, ...]]) -> Dict[str, Union[int, str]]:
    """Convert a version tuple to a version dictionary.

    Args:
        version_tuple: Version tuple

    Returns:
        Dict[str, Union[int, str]]: Version dictionary
    """
    if not version_tuple:
        return {}
        
    # Create dictionary with standard components
    version_dict: Dict[str, Union[int, str]] = {
        "major": version_tuple[0] if len(version_tuple) > 0 else 0,
        "minor": version_tuple[1] if len(version_tuple) > 1 else 0,
        "patch": version_tuple[2] if len(version_tuple) > 2 else 0,
    }
    
    # Add build number if available
    if len(version_tuple) > 3:
        version_dict["build"] = str(version_tuple[3])
    else:
        version_dict["build"] = ""
        
    return version_dict


def compare_versions(
    version1: Union[str, Tuple[int, ...], Dict[str, Union[int, str]]], 
    version2: Union[str, Tuple[int, ...], Dict[str, Union[int, str]]]
) -> int:
    """Compare two version strings.

    Args:
        version1: First version string, tuple, or dictionary
        version2: Second version string, tuple, or dictionary

    Returns:
        int: -1 if version1 < version2, 0 if version1 == version2, 1 if version1 > version2
    """
    # Convert inputs to common format (both tuples)
    v1_tuple: Optional[Tuple[int, ...]] = None
    v2_tuple: Optional[Tuple[int, ...]] = None
    
    if isinstance(version1, str):
        v1_tuple = parse_version(version1)
    elif isinstance(version1, tuple):
        v1_tuple = version1
    else:
        # It's a dictionary
        v1_dict = version1
        v1_tuple = _dict_to_tuple(v1_dict)
        
    if isinstance(version2, str):
        v2_tuple = parse_version(version2)
    elif isinstance(version2, tuple):
        v2_tuple = version2
    else:
        # It's a dictionary
        v2_dict = version2
        v2_tuple = _dict_to_tuple(v2_dict)
    
    # Handle None cases
    if v1_tuple is None and v2_tuple is None:
        return 0
    if v1_tuple is None:
        return -1
    if v2_tuple is None:
        return 1
        
    # Make sure both tuples have the same length
    max_len = max(len(v1_tuple), len(v2_tuple))
    v1_padded = v1_tuple + (0,) * (max_len - len(v1_tuple))
    v2_padded = v2_tuple + (0,) * (max_len - len(v2_tuple))
    
    # Compare each component
    for i in range(max_len):
        if v1_padded[i] < v2_padded[i]:
            return -1
        elif v1_padded[i] > v2_padded[i]:
            return 1
            
    # Equal versions
    return 0


def get_version_difference(
    version1: Union[str, Tuple[int, ...], Dict[str, Union[int, str]], None], 
    version2: Union[str, Tuple[int, ...], Dict[str, Union[int, str]], None]
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

    # Parse strings to dictionaries or tuples if needed
    if isinstance(version1, str):
        v1_tuple = parse_version(version1)
    elif isinstance(version1, tuple):
        v1_tuple = version1
    else:  # Dict
        v1_tuple = _dict_to_tuple(version1)
        
    if isinstance(version2, str):
        v2_tuple = parse_version(version2)
    elif isinstance(version2, tuple):
        v2_tuple = version2
    else:  # Dict
        v2_tuple = _dict_to_tuple(version2)
    
    # Handle None results from parsing
    if v1_tuple is None or v2_tuple is None:
        return None

    # Make sure both tuples have the same length
    max_len = max(len(v1_tuple), len(v2_tuple))
    v1_padded = v1_tuple + (0,) * (max_len - len(v1_tuple))
    v2_padded = v2_tuple + (0,) * (max_len - len(v2_tuple))

    # Calculate differences
    differences = tuple(abs(a - b) for a, b in zip(v1_padded, v2_padded))
    return differences


def get_version_info(
    old_version: Union[str, Tuple[int, ...], Dict[str, Union[int, str]], None], 
    new_version: Union[str, Tuple[int, ...], Dict[str, Union[int, str]], None]
) -> str:
    """Get human-readable description of version change.

    Args:
        old_version: Original version as string or tuple
        new_version: New version as string or tuple

    Returns:
        str: A human-readable description of the version difference
    """
    # Parse strings to dictionaries or tuples if needed
    if isinstance(old_version, str):
        v1_tuple = parse_version(old_version)
    elif isinstance(old_version, tuple):
        v1_tuple = old_version
    else:  # Dict
        v1_tuple = _dict_to_tuple(old_version)
        
    if isinstance(new_version, str):
        v2_tuple = parse_version(new_version)
    elif isinstance(new_version, tuple):
        v2_tuple = new_version
    else:  # Dict
        v2_tuple = _dict_to_tuple(new_version)

    # Handle None cases
    if v1_tuple is None or v2_tuple is None:
        old_str = str(old_version) if old_version is not None else "unknown"
        new_str = str(new_version) if new_version is not None else "unknown"
        return f"Version changed ({old_str} → {new_str})"

    # Format as strings for display
    v1_str = ".".join(str(c) for c in v1_tuple)
    v2_str = ".".join(str(c) for c in v2_tuple)

    # Get component-wise differences
    diff = get_version_difference(v1_tuple, v2_tuple)
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
        return f"Version changed ({v1_str} → {v2_str})"


def format_version_difference(
    old_version: Union[str, Tuple[int, ...], Dict[str, Union[int, str]], None],
    new_version: Union[str, Tuple[int, ...], Dict[str, Union[int, str]], None],
) -> str:
    """Format version difference as a human-readable string.

    Args:
        old_version: Original version as string or tuple
        new_version: New version as string or tuple

    Returns:
        str: A human-readable description of the version difference
    """
    return get_version_info(old_version, new_version)


def compose_version_tuple(version_dict: Dict[str, int]) -> Optional[Dict[str, Union[int, str]]]:
    """Compose a version tuple from a version dictionary.

    Args:
        version_dict: Version dictionary

    Returns:
        Optional[Dict[str, Union[int, str]]]: Version dictionary with composite versions
    """
    if not version_dict:
        return None

    return {
        "major": version_dict.get("major", 0),
        "minor": version_dict.get("minor", 0),
        "patch": version_dict.get("patch", 0),
        "build": str(version_dict.get("build", "")),
    }


def compare_fuzzy(name1: str, name2: str, threshold: int = 75) -> float:
    """Compare two names using fuzzy matching.

    Args:
        name1: First name
        name2: Second name
        threshold: Threshold for fuzzy matching

    Returns:
        float: Fuzzy match ratio
    """
    # Normalize names for comparison
    name1 = name1.lower()
    name2 = name2.lower()

    # Use rapidfuzz for better performance if available
    if USE_RAPIDFUZZ:
        ratio = float(rapidfuzz.partial_ratio(name1, name2))
    else:
        # Fall back to fuzzywuzzy if rapidfuzz is not available
        from fuzzywuzzy import fuzz
        ratio = float(fuzz.partial_ratio(name1, name2))

    # Only return the ratio if it meets the threshold
    if ratio >= threshold:
        return ratio
    
    return 0.0


def check_outdated_apps(apps: List[Tuple[str, str]], batch_size: int = 50) -> List[Tuple[str, Dict[str, str], VersionStatus]]:
    """Check which applications are outdated compared to their Homebrew versions.

    Args:
        apps: List of applications with name and version
        batch_size: How many applications to check in one batch (for parallelism)

    Returns:
        List of tuples with application name, version info and status
    """
    if not apps:
        return []

    # Skip progress bar if explicitly disabled in config
    show_progress = getattr(config, "show_progress", True)
    if hasattr(config, "no_progress") and config.no_progress:
        show_progress = False

    # Determine max workers - default to either CPU count or 4, whichever is lower
    max_workers = min(multiprocessing.cpu_count(), getattr(config, "max_workers", 4))
    
    # Create batches for parallel processing
    batches = [apps[i : i + batch_size] for i in range(0, len(apps), batch_size)]
    
    results = []
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit batch processing tasks
        futures = [executor.submit(_process_app_batch, batch) for batch in batches]
        
        # Process results as they complete with progress bar
        if HAS_TQDM and show_progress:
            # Use tqdm to show progress with time estimation
            for batch_results in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Checking for updates",
                unit="batch",
                ncols=80,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
            ):
                try:
                    for app_info in batch_results.result():
                        app_name = app_info.name
                        version_info = {
                            "installed": app_info.version_string,
                            "latest": app_info.latest_version or "Unknown",
                        }
                        results.append((app_name, version_info, app_info.status))
                except Exception as e:
                    logging.error(f"Error processing batch: {e}")
        else:
            # Process without progress bar
            for future in as_completed(futures):
                try:
                    for app_info in future.result():
                        app_name = app_info.name
                        version_info = {
                            "installed": app_info.version_string,
                            "latest": app_info.latest_version or "Unknown",
                        }
                        results.append((app_name, version_info, app_info.status))
                except Exception as e:
                    logging.error(f"Error processing batch: {e}")
                    
    # Sort results by application name
    return sorted(results, key=lambda x: x[0].lower())


@dataclass
class AppVersionInfo:
    """Class to hold application version information."""
    name: str
    version_string: str
    latest_version: Optional[str] = None
    status: str = VersionStatus.UNKNOWN


def _process_app_batch(batch: List[Tuple[str, str]]) -> List[AppVersionInfo]:
    """Process a batch of applications to check for updates.
    
    Args:
        batch: List of applications with name and version
        
    Returns:
        List of AppVersionInfo objects
    """
    results = []
    for app_name, app_version in batch:
        try:
            brew_version, status = _check_app_version(app_name, app_version)
            results.append(
                AppVersionInfo(
                    name=app_name,
                    version_string=app_version,
                    latest_version=brew_version or "Unknown",
                    status=status
                )
            )
        except Exception as e:
            logging.error(f"Error checking version for {app_name}: {e}")
            results.append(
                AppVersionInfo(
                    name=app_name,
                    version_string=app_version,
                    latest_version=None,
                    status=VersionStatus.UNKNOWN
                )
            )
    return results


def _check_app_version(app_name: str, app_version: str) -> Tuple[str, VersionStatus]:
    """Check the version of a single application.

    Args:
        app_name: Name of the application
        app_version: Version of the application

    Returns:
        Tuple[str, VersionStatus]: Latest version and status
    """
    # Find matching cask
    matching_cask = find_matching_cask(app_name)
    if matching_cask:
        # Get latest version from Homebrew
        latest_version = get_homebrew_version_info(matching_cask)
        if latest_version:
            # Determine version status
            if app_version and latest_version:
                comparison = compare_versions(app_version, latest_version)
                if comparison < 0:
                    return latest_version, VersionStatus.OUTDATED
                elif comparison > 0:
                    return latest_version, VersionStatus.NEWER
                else:
                    return latest_version, VersionStatus.UP_TO_DATE

    return "", VersionStatus.UNKNOWN


def find_matching_cask(app_name: str) -> Optional[str]:
    """Find a matching Homebrew cask for the given app name.

    Args:
        app_name (str): The name of the application

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

        return _find_matching_cask(app_name, casks)
    except Exception as e:
        logging.error(f"Error finding matching cask for {app_name}: {e}")
        return None


def _find_matching_cask(app_name: str, casks: List[str]) -> Optional[str]:
    """Find a matching Homebrew cask for an application.

    Args:
        app_name: Application name to match
        casks: List of Homebrew casks to search

    Returns:
        Optional[str]: The matching cask name or None if no match found
    """
    # Return None if no casks are available
    if not casks:
        return None
        
    lower_app_name = app_name.lower()
    
    # First, look for exact matches
    for cask in casks:
        if cask.lower() == lower_app_name:
            return cask
    
    # Next, look for casks that contain the app name
    target_casks = [
        cask for cask in casks 
        if lower_app_name in cask.lower() or cask.lower() in lower_app_name
    ]
    
    # If we have potential matches, use fuzzy matching to find the best one
    if target_casks:
        # Use rapidfuzz's process.extractOne for faster matching if available
        if USE_RAPIDFUZZ:
            match = process.extractOne(
                lower_app_name, 
                target_casks, 
                scorer=rapidfuzz.partial_ratio,
                score_cutoff=75  # Require at least 75% similarity
            )
            
            if match:
                return match[0]
        else:
            # Fallback to fuzzywuzzy
            best_match = None
            best_score = 0
            
            for cask in target_casks:
                score = fuzz.partial_ratio(lower_app_name, cask.lower())
                if score > best_score and score >= 75:
                    best_score = score
                    best_match = cask
                    
            return best_match
            
    return None


def get_homebrew_version_info(cask_name: str) -> str:
    """Get the latest version information for a Homebrew cask.

    Args:
        cask_name (str): The name of the Homebrew cask

    Returns:
        str: The latest version string
    """
    try:
        # Get version info from Homebrew
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
