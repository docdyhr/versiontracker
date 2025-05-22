"""Version comparison and checking functionality for VersionTracker."""

# Standard library imports
import concurrent.futures
import logging
import multiprocessing
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple, Union, cast

# Internal imports
from versiontracker.config import get_config
from versiontracker.exceptions import (
    NetworkError,
    TimeoutError,
    VersionError,
)
from versiontracker.ui import smart_progress
from versiontracker.utils import normalise_name

# Optional dependency imports with fallbacks
# Import packaging version if available, otherwise create a stub
try:
    from packaging import version as packaging_version
except ImportError:
    # Handle case where packaging module is not available
    # Define a stub module type for type checking
    from types import ModuleType

    class _PackagingVersionStub(ModuleType):
        def parse(self, version_string):
            """Stub parse method."""
            return version_string

    packaging_version = _PackagingVersionStub("packaging.version")

# Try to import fuzzy matching libraries with fallbacks
USE_RAPIDFUZZ = False
USE_FUZZYWUZZY = False

try:
    from fuzzywuzzy import fuzz
    from fuzzywuzzy import process as fuzz_process
    from fuzzywuzzy.fuzz import partial_ratio as _partial_ratio

    USE_FUZZYWUZZY = True
except ImportError:
    try:
        from rapidfuzz import fuzz
        from rapidfuzz import process as fuzz_process
        from rapidfuzz.fuzz import partial_ratio as _partial_ratio

        USE_RAPIDFUZZ = True
    except ImportError:
        # Create minimal fallback implementations if neither library is available
        class MinimalFuzz:
            """Minimal implementation of fuzzy matching when no library is available."""

            @staticmethod
            def ratio(s1: str, s2: str, **kwargs) -> int:
                """Calculate the ratio of similarity between two strings.

                Args:
                    s1: First string
                    s2: Second string
                    **kwargs: Additional arguments (ignored)

                Returns:
                    Similarity score from 0-100
                """
                return 100 if s1 == s2 else 0

            @staticmethod
            def partial_ratio(s1: str, s2: str, **kwargs) -> int:
                """Calculate partial ratio between two strings.

                Args:
                    s1: First string
                    s2: Second string
                    **kwargs: Additional arguments (ignored)

                Returns:
                    Partial similarity score from 0-100
                """
                return 100 if s1 in s2 or s2 in s1 else 0

        class MinimalProcess:
            """Minimal implementation of fuzzy process matching when no library is available."""

            @staticmethod
            def extractOne(
                query: str, choices: List[str], **kwargs
            ) -> Optional[Tuple[str, int]]:
                """Find the best match for query among choices.

                Args:
                    query: The string to match
                    choices: List of possible matches
                    **kwargs: Additional arguments (ignored)

                Returns:
                    Tuple of (best_match, score) or None if no choices
                """
                if not choices:
                    return None

                best_score = 0
                best_match = None

                for choice in choices:
                    if query.lower() in choice.lower():
                        score = 90
                    elif choice.lower() in query.lower():
                        score = 70
                    else:
                        score = 0

                    if score > best_score:
                        best_score = score
                        best_match = choice

                return (best_match, best_score) if best_match else (choices[0], 0)

        fuzz = MinimalFuzz()
        fuzz_process = MinimalProcess()
        _partial_ratio = fuzz.partial_ratio

# Set up progress bar support

# Set up progress bar support
HAS_VERSION_PROGRESS = False
try:
    from tqdm.auto import tqdm

    HAS_VERSION_PROGRESS = True
except ImportError:
    # Create a minimal progress bar fallback
    class MinimalTqdm:
        """Minimal implementation of tqdm progress bar when the library is not available."""

        def __init__(self, iterable=None, **kwargs):
            """Initialize minimal progress bar.

            Args:
                iterable: Iterable to wrap with progress reporting
                **kwargs: Additional arguments like desc (description)
            """
            self.iterable = iterable
            self.total = len(iterable) if iterable is not None else None
            self.n = 0
            self.desc = kwargs.get("desc", "")

        def __iter__(self):
            """Iterate through items with progress updates.

            Yields:
                Items from the wrapped iterable
            """
            for item in self.iterable:
                self.n += 1
                if self.n % 10 == 0:
                    print(f"\r{self.desc}: {self.n}/{self.total}", end="", flush=True)
                yield item
            print("\rCompleted", " " * 30)

        def update(self, n=1):
            """Update progress by n steps.

            Args:
                n: Number of steps to increment
            """
            self.n += n

        def close(self):
            """Close the progress bar."""
            pass

    tqdm = MinimalTqdm
    HAS_VERSION_PROGRESS = True


# Create a compatibility function for partial_ratio
def partial_ratio(s1: str, s2: str, score_cutoff: Optional[int] = None) -> int:
    """Get the partial ratio between two strings.

    Provides compatibility between rapidfuzz and fuzzywuzzy, with fallbacks.
    Uses the appropriate function based on which library is available.

    Args:
        s1: First string to compare
        s2: Second string to compare
        score_cutoff: Optional score cutoff (only used with rapidfuzz)

    Returns:
        int: Similarity score (0-100) where 100 means identical
    """
    if not s1 or not s2:
        return 0

    try:
        if USE_RAPIDFUZZ:
            if score_cutoff is not None:
                score = float(
                    fuzz.partial_ratio(s1, s2, score_cutoff=float(score_cutoff))
                )
            else:
                score = float(fuzz.partial_ratio(s1, s2))
            return int(score)
        elif USE_FUZZYWUZZY:
            score = float(fuzz.partial_ratio(s1, s2))
            return int(score)
        else:
            # Use our minimal implementation
            return int(fuzz.partial_ratio(s1, s2))
    except Exception as e:
        logging.warning(f"Error calculating string similarity: {e}")
        # Simple fallback if all else fails
        return 100 if s1 == s2 else (70 if s1 in s2 or s2 in s1 else 0)


# Define progress bar functionality
def version_progress_bar(iterable, **kwargs):
    """Wrapper for tqdm to use in version module."""
    if HAS_VERSION_PROGRESS:
        return tqdm(iterable, **kwargs)
    # Simple fallback if tqdm is not available
    return iterable


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

    UNKNOWN = 0
    UPTODATE = 1
    OUTDATED = 2
    NEWER = 3
    NOT_FOUND = 4
    ERROR = 5


class VersionInfo:
    """Class representing version information for an application."""

    def __init__(
        self,
        name: str,
        version_string: str,
        latest_version: Optional[str] = None,
        latest_parsed: Optional[Tuple[int, ...]] = None,
        status: VersionStatus = VersionStatus.UNKNOWN,
        outdated_by: Optional[Tuple[int, ...]] = None,
    ):
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
        self._latest_parsed = (
            latest_parsed
            if latest_parsed
            else parse_version(latest_version)
            if latest_version
            else None
        )
        self._outdated_by = outdated_by

        # Calculate outdated_by if not provided and we have both versions
        if self._outdated_by is None and self._parsed and self._latest_parsed:
            self._outdated_by = get_version_difference(
                self._parsed, self._latest_parsed
            )

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

    @latest_parsed.setter
    def latest_parsed(self, value: Optional[Tuple[int, ...]]) -> None:
        """Set the latest parsed version.

        Args:
            value: Latest parsed version tuple
        """
        self._latest_parsed = value

    @property
    def outdated_by(self) -> Optional[Tuple[int, ...]]:
        """Get the difference between current and latest version.

        Returns:
            Optional[Tuple[int, ...]]: Version difference or None
        """
        return self._outdated_by

    @outdated_by.setter
    def outdated_by(self, value: Optional[Tuple[int, ...]]) -> None:
        """Set the version difference.

        Args:
            value: Version difference tuple
        """
        self._outdated_by = value


# Add a precompiled regex pattern cache for better performance


@lru_cache(maxsize=256)
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


def _parse_version_to_dict(
    version_str: Optional[str],
) -> Optional[Dict[str, Union[int, str]]]:
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
                "minor": (
                    int(groups[1])
                    if len(groups) > 1 and groups[1] and groups[1].isdigit()
                    else 0
                ),
                "patch": (
                    int(groups[2])
                    if len(groups) > 2 and groups[2] and groups[2].isdigit()
                    else 0
                ),
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
            "patch": int(numbers[2]) if len(numbers) > 2 else 0,
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
    simple_pattern = (
        r"(?:v|version\s+)?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?(?:[^\d].*)?$"
    )
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


def _dict_to_tuple(
    version_dict: Optional[Dict[str, Union[int, str]]],
) -> Optional[Tuple[int, ...]]:
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


def _tuple_to_dict(
    version_tuple: Optional[Tuple[int, ...]],
) -> Dict[str, Union[int, str]]:
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
    version2: Union[str, Tuple[int, ...], Dict[str, Union[int, str]]],
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
    version2: Union[str, Tuple[int, ...], Dict[str, Union[int, str]], None],
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
    new_version: Union[str, Tuple[int, ...], Dict[str, Union[int, str]], None],
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


def compose_version_tuple(
    version_dict: Dict[str, int],
) -> Optional[Dict[str, Union[int, str]]]:
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


def similarity_score(s1: str, s2: str, score_cutoff: Optional[int] = None) -> int:
    """Calculate similarity score between two strings.

    Args:
        s1: First string
        s2: Second string
        score_cutoff: Minimum score cutoff (0-100)

    Returns:
        int: Similarity score between 0 and 100
    """
    # Handle None inputs gracefully
    if (s1 is None) or (s2 is None):
        return 0
    # Special case for exact match
    if s1 == s2:
        return 100

    # Use fuzz.ratio or rapidfuzz equivalent
    if USE_RAPIDFUZZ:
        return int(fuzz.ratio(s1, s2, score_cutoff=score_cutoff if score_cutoff else 0))
    else:
        return int(fuzz.ratio(s1, s2))


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

    # Use our compatibility wrapper function
    ratio = float(similarity_score(name1, name2))

    # Only return the ratio if it meets the threshold
    if ratio >= threshold:
        return ratio

    return 0.0


def _get_config_settings() -> Tuple[bool, int]:
    """Get configuration settings for progress display and worker count.

    Returns:
        Tuple of (show_progress, max_workers)
    """
    # Check if progress display is enabled
    show_progress = getattr(get_config(), "show_progress", True)
    if hasattr(get_config(), "no_progress") and get_config().no_progress:
        show_progress = False

    # Determine max workers - default to either CPU count or 4, whichever is lower
    max_workers = min(
        multiprocessing.cpu_count(), getattr(get_config(), "max_workers", 4)
    )

    return show_progress, max_workers


def _create_app_batches(
    apps: List[Tuple[str, str]], batch_size: int
) -> List[List[Tuple[str, str]]]:
    """Split applications into batches for parallel processing.

    Args:
        apps: List of applications with name and version
        batch_size: Size of each batch

    Returns:
        List of application batches
    """
    return [apps[i : i + batch_size] for i in range(0, len(apps), batch_size)]


def check_outdated_apps(
    apps: List[Tuple[str, str]], batch_size: int = 50
) -> List[Tuple[str, Dict[str, str], VersionStatus]]:
    """Check which applications are outdated compared to their Homebrew versions.

    Args:
        apps: List of applications with name and version
        batch_size: How many applications to check in one batch (for parallelism)

    Returns:
        List of tuples with application name, version info and status

    Raises:
        NetworkError: If there's a persistent network-related issue
        TimeoutError: If operations consistently time out
        RuntimeError: For other critical errors
    """
    if not apps:
        return []

    # Get configuration settings
    show_progress, max_workers = _get_config_settings()

    # Create batches for parallel processing
    batches = _create_app_batches(apps, batch_size)

    results = []
    error_count = 0
    max_errors = 3  # Maximum number of consecutive errors to tolerate

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit batch processing tasks
        futures = [executor.submit(_process_app_batch, batch) for batch in batches]

        # Process results as they complete with progress bar
        if HAS_VERSION_PROGRESS and show_progress:
            # Use smart progress to show progress with time estimation and system resources
            for future in smart_progress(
                concurrent.futures.as_completed(futures),
                total=len(futures),
                desc="Checking for updates",
                unit="batch",
                monitor_resources=True,
                ncols=80,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
            ):
                try:
                    for app_info in future.result():
                        app_name = app_info.name
                        version_info = {
                            "installed": app_info.version_string,
                            "latest": app_info.latest_version or "Unknown",
                        }
                        results.append((app_name, version_info, app_info.status))
                    # Reset error counter on success
                    error_count = 0
                except (NetworkError, TimeoutError) as e:
                    error_count += 1
                    logging.error(f"Network error processing batch: {e}")
                    # If we've had too many consecutive errors, propagate the error
                    if error_count >= max_errors:
                        logging.critical(
                            f"Too many consecutive network errors, aborting: {e}"
                        )
                        raise
                except Exception as e:
                    logging.error(f"Error processing batch: {e}")
                    error_count += 1
                    # If we've had too many consecutive errors, propagate the error
                    if error_count >= max_errors:
                        logging.critical(f"Too many consecutive errors, aborting: {e}")
                        raise RuntimeError(
                            f"Multiple errors occurred while checking applications: {e}"
                        )
        else:
            # Process without progress bar
            for future in concurrent.futures.as_completed(futures):
                try:
                    for app_info in future.result():
                        app_name = app_info.name
                        version_info = {
                            "installed": app_info.version_string,
                            "latest": app_info.latest_version or "Unknown",
                        }
                        results.append((app_name, version_info, app_info.status))
                    # Reset error counter on success
                    error_count = 0
                except (NetworkError, TimeoutError) as e:
                    error_count += 1
                    logging.error(f"Network error processing batch: {e}")
                    # If we've had too many consecutive errors, propagate the error
                    if error_count >= max_errors:
                        logging.critical(
                            f"Too many consecutive network errors, aborting: {e}"
                        )
                        raise
                except Exception as e:
                    logging.error(f"Error processing batch: {e}")
                    error_count += 1
                    # If we've had too many consecutive errors, propagate the error
                    if error_count >= max_errors:
                        logging.critical(f"Too many consecutive errors, aborting: {e}")
                        raise RuntimeError(
                            f"Multiple errors occurred while checking applications: {e}"
                        )

    return results


@dataclass
class AppVersionInfo:
    """Simple dataclass for application version information."""

    name: str
    version_string: str
    latest_version: Optional[str] = None
    status: VersionStatus = VersionStatus.UNKNOWN


def _process_app_batch(batch: List[Tuple[str, str]]) -> List[AppVersionInfo]:
    """Process a batch of applications to check their outdated status.

    Args:
        batch: Batch of applications to check

    Returns:
        List of AppVersionInfo objects with update status

    Raises:
        NetworkError: If there's a network-related error while checking versions
        TimeoutError: If the operation times out
        DataParsingError: If there's an error parsing version data
    """
    results = []

    for app_name, installed_version in batch:
        try:
            # Skip empty app names
            if not app_name:
                continue

            # Get latest version and status using existing function
            brew_version, status = _check_app_version(app_name, installed_version)
            results.append(
                AppVersionInfo(
                    name=app_name,
                    version_string=installed_version,
                    latest_version=brew_version or "Unknown",
                    status=status,
                )
            )

        except Exception as e:
            logging.error(f"Unexpected error processing {app_name}: {e}")
            # Still add the app to the results with UNKNOWN status
            results.append(
                AppVersionInfo(app_name, installed_version, None, VersionStatus.UNKNOWN)
            )

    return results


def _check_app_version(
    app_name: str, installed_version: str
) -> Tuple[Optional[str], VersionStatus]:
    """Check the version status of an application.

    Args:
        app_name: Name of the application
        installed_version: Installed version of the application

    Returns:
        Tuple of (latest version, status)
    """
    try:
        # Try to get a corresponding cask first
        normalized_name = normalise_name(app_name)
        cask = find_corresponding_cask(normalized_name)

        if not cask:
            # No matching cask found
            return None, VersionStatus.NOT_FOUND

        # Get latest version
        latest_version = check_latest_version(app_name, installed_version)

        # If we couldn't get the latest version, mark as unknown
        if not latest_version:
            return None, VersionStatus.UNKNOWN

        # If there's no installed version, we can't compare
        if not installed_version:
            return latest_version, VersionStatus.UNKNOWN

        # Compare versions
        result = compare_versions(installed_version, latest_version)

        if result < 0:
            return latest_version, VersionStatus.OUTDATED
        elif result == 0:
            return latest_version, VersionStatus.UPTODATE
        else:
            return latest_version, VersionStatus.NEWER
    except Exception as e:
        logging.error(f"Error checking version for {app_name}: {e}")
        return None, VersionStatus.ERROR


def check_latest_version(app_name: str, installed_version: str) -> Optional[str]:
    """Check the latest version of an application available via Homebrew.

    Args:
        app_name: Name of the application
        installed_version: Currently installed version

    Returns:
        Optional[str]: Latest version string if found, None otherwise

    Raises:
        NetworkError: If there's a network issue connecting to Homebrew
        TimeoutError: If the operation times out
    """
    from versiontracker.apps import get_cask_version

    try:
        # First normalize the app name for better matching
        normalized_name = normalise_name(app_name)

        # Find corresponding Homebrew cask
        cask = find_corresponding_cask(normalized_name)

        if not cask:
            logging.debug(f"No cask found for {app_name}")
            return None

        # Get the latest version from Homebrew
        latest_version = get_cask_version(cask)

        if not latest_version:
            logging.debug(f"No version information found for {cask}")
            return None

        return latest_version
    except (NetworkError, TimeoutError):
        # Re-raise these specific exceptions for proper handling upstream
        raise
    except Exception as e:
        logging.error(f"Error checking latest version for {app_name}: {e}")
        return None


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
        cask
        for cask in casks
        if lower_app_name in cask.lower() or cask.lower() in lower_app_name
    ]

    # If we have potential matches, use fuzzy matching to find the best one
    if target_casks:
        # If rapidfuzz is available, use it for faster matching
        if USE_RAPIDFUZZ:
            try:
                # Use imported fuzz_process from module import rather than direct reference
                match = fuzz_process.extractOne(
                    lower_app_name,
                    target_casks,
                    scorer=partial_ratio,
                    score_cutoff=75,  # Require at least 75% similarity
                )

                if match:
                    return cast(Optional[str], match[0])
            except Exception as e:
                logging.warning(
                    f"Error using rapidfuzz: {e}, falling back to manual matching"
                )
                # Fall through to manual matching
        else:
            # Use fuzzywuzzy as fallback
            try:
                match = fuzz_process.extractOne(
                    lower_app_name,
                    target_casks,
                    scorer=fuzz.partial_ratio,
                    score_cutoff=75,
                )

                if match:
                    return cast(Optional[str], match[0])
            except Exception as e:
                logging.warning(
                    f"Error using fuzzywuzzy: {e}, falling back to manual matching"
                )

        # Manual matching as a fallback
        best_match = None
        best_score = 0

        for cask in target_casks:
            score = partial_ratio(lower_app_name, cask.lower())
            if score > best_score and score >= 75:
                best_score = score
                best_match = cask

        return best_match

    return None


def find_corresponding_cask(app_name: str) -> Optional[str]:
    """Find a corresponding Homebrew cask for the given app name.
    This is a wrapper around find_matching_cask with better error handling.

    Args:
        app_name: The name of the application

    Returns:
        Optional[str]: The name of the matching cask, or None if not found

    Raises:
        NetworkError: If there's a network issue
        TimeoutError: If the operation times out
    """
    try:
        from versiontracker.apps import get_homebrew_casks

        # Get cached list of casks if possible
        casks = get_homebrew_casks()

        # Use the existing matching function
        return _find_matching_cask(app_name, casks)
    except NetworkError:
        logging.error(f"Network error finding cask for {app_name}")
        raise
    except TimeoutError:
        logging.error(f"Timeout finding cask for {app_name}")
        raise
    except Exception as e:
        logging.error(f"Error finding corresponding cask for {app_name}: {e}")
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
                comparison = compare_versions(
                    version_info.parsed, version_info.latest_parsed
                )
                if comparison < 0:
                    version_info.status = VersionStatus.OUTDATED
                    version_info.outdated_by = get_version_difference(
                        version_info.parsed, version_info.latest_parsed
                    )
                elif comparison > 0:
                    version_info.status = VersionStatus.NEWER
                else:
                    version_info.status = VersionStatus.UPTODATE

    return version_info


def format_outdated_indicator(version_info: VersionInfo) -> str:
    """Format an indicator string showing how outdated a version is.

    Args:
        version_info: Version information

    Returns:
        str: A formatted indicator string, e.g. "⚠️ (1.2.3 → 2.0.0)"
    """
    if version_info.status == VersionStatus.UPTODATE:
        return "✓ Up to date"
    elif version_info.status == VersionStatus.NEWER:
        return "⚠️ Newer than latest"
    elif version_info.status == VersionStatus.OUTDATED and version_info.latest_version:
        return (
            f"⚠️ Update available ({version_info.version_string} → "
            f"{version_info.latest_version})"
        )
    elif version_info.status == VersionStatus.NOT_FOUND:
        return "🔍 Not found"
    elif version_info.status == VersionStatus.ERROR:
        return "⚠️ Error checking version"
    else:
        return "? Unknown status"
