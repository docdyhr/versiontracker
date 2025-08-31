"""Version comparison and checking functionality for VersionTracker."""

# Standard library imports
import concurrent.futures
import logging
import multiprocessing
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Any, Callable

# Internal imports (imported after optional libraries are set up below)
# These will be imported conditionally after the fuzzy library setup

# Third-party imports (optional with fallbacks)
# Progress bar library (optional)
HAS_VERSION_PROGRESS = False

# Fuzzy matching library imports with fallbacks
USE_RAPIDFUZZ = False
USE_FUZZYWUZZY = False
fuzz: Any = None
fuzz_process: Any = None

try:
    import rapidfuzz.fuzz as rapidfuzz_fuzz
    import rapidfuzz.process as rapidfuzz_process

    fuzz = rapidfuzz_fuzz
    fuzz_process = rapidfuzz_process
    USE_RAPIDFUZZ = True
except ImportError:
    try:
        import fuzzywuzzy.fuzz as fuzzywuzzy_fuzz  # type: ignore[import-untyped]
        import fuzzywuzzy.process as fuzzywuzzy_process  # type: ignore[import-untyped]

        fuzz = fuzzywuzzy_fuzz
        fuzz_process = fuzzywuzzy_process
        USE_FUZZYWUZZY = True
    except ImportError:
        pass  # Assuming the full block had this for fuzzywuzzy

# If no fuzzy matching library is available, create fallback implementations
if not USE_RAPIDFUZZ and not USE_FUZZYWUZZY:
    # Create minimal fallback implementations
    class MinimalFuzz:
        """Minimal implementation of fuzzy matching when no library is available."""

        @staticmethod
        def ratio(s1: str, s2: str) -> int:
            """Calculate the ratio of similarity between two strings."""
            return 100 if s1 == s2 else 0

        @staticmethod
        def partial_ratio(s1: str, s2: str) -> int:
            """Calculate the partial ratio of similarity between two strings."""
            return 100 if s1.lower() in s2.lower() or s2.lower() in s1.lower() else 0

    class MinimalProcess:
        """Minimal implementation of fuzzy process matching."""

        @staticmethod
        def extractOne(query: str, choices: list[str]) -> tuple[str, int] | None:
            """Extract the best match from choices."""
            if not choices:
                return None

            best_match = None
            best_score = 0

            for choice in choices:
                if query.lower() == choice.lower():
                    score = 100
                elif query.lower() in choice.lower():
                    score = 80
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

# Internal imports
from versiontracker.exceptions import NetworkError  # noqa: E402
from versiontracker.exceptions import TimeoutError as VTTimeoutError  # noqa: E402
from versiontracker.ui import smart_progress  # noqa: E402
from versiontracker.utils import normalise_name  # noqa: E402

# Set up logging
logger = logging.getLogger(__name__)


class VersionStatus(Enum):
    """Enumeration of version comparison results."""

    UNKNOWN = 0
    UP_TO_DATE = 1
    OUTDATED = 2
    NEWER = 3
    NOT_FOUND = 4
    ERROR = 5


@dataclass
class ApplicationInfo:
    """Information about an installed application."""

    name: str
    version_string: str
    bundle_id: str | None = None
    path: str | None = None
    homebrew_name: str | None = None
    latest_version: str | None = None
    latest_parsed: tuple[int, ...] | None = None
    status: VersionStatus = VersionStatus.UNKNOWN
    error_message: str | None = None
    outdated_by: tuple[int, ...] | None = None
    newer_by: tuple[int, ...] | None = None

    @property
    def parsed(self) -> tuple[int, ...] | None:
        """Get the parsed version tuple."""
        if not self.version_string or not self.version_string.strip():
            return None
        return parse_version(self.version_string)


# Compatibility aliases and additional functions for test compatibility
VersionInfo = ApplicationInfo  # Alias for backward compatibility

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


def _clean_version_string(version_str: str) -> str:
    """Clean version string by removing prefixes and app names."""
    # Remove common prefixes like "v" or "Version "
    cleaned = re.sub(r"^[vV]ersion\s+", "", version_str)
    cleaned = re.sub(r"^[vV](?:er\.?\s*)?", "", cleaned)

    # Handle application names at the beginning
    cleaned = re.sub(r"^(?:Google\s+)?(?:Chrome|Firefox|Safari)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^[a-zA-Z]+\s+(?=\d)", "", cleaned)

    return cleaned


def _extract_build_metadata(cleaned: str) -> tuple[int | None, str]:
    """Extract build metadata from version string."""
    build_metadata = None

    # Look for various build patterns
    build_match = re.search(r"\+.*?(\d+)", cleaned)
    if build_match:
        try:
            build_metadata = int(build_match.group(1))
        except ValueError:
            pass

    # Search for other build patterns if not found
    if build_metadata is None:
        other_build_patterns = [r"build\s+(\d+)", r"\((\d+)\)", r"-dev-(\d+)"]
        for pattern in other_build_patterns:
            match = re.search(pattern, cleaned, re.IGNORECASE)
            if match:
                try:
                    build_metadata = int(match.group(1))
                    cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
                    break
                except ValueError:
                    pass

    # Remove semver build metadata
    cleaned = re.sub(r"\+.*$", "", cleaned)
    return build_metadata, cleaned


def _handle_special_beta_format(version_str: str) -> tuple[int, ...] | None:
    """Handle special format like '1.2.3.beta4'."""
    special_beta_format = re.search(r"\d+\.\d+\.\d+\.[a-zA-Z]+\d+", version_str)
    if special_beta_format:
        all_numbers = re.findall(r"\d+", version_str)
        if len(all_numbers) >= 4:
            parts = [int(num) for num in all_numbers[:4]]
            return tuple(parts)
    return None


def _extract_prerelease_info(cleaned: str, version_str: str) -> tuple[bool, int | None, bool, str]:
    """Extract prerelease information from version string."""
    has_prerelease = False
    prerelease_num = None
    has_text_suffix = False

    prerelease_match = re.search(
        r"[-.](?P<type>alpha|beta|rc|final|[αβγδ])(?:\.?(?P<suffix>\w*\d*))?$",
        cleaned,
        re.IGNORECASE,
    )
    is_mixed_format = re.search(r"\d+\.[a-zA-Z]+\.\d+", version_str)

    if prerelease_match and not is_mixed_format:
        has_prerelease = True
        prerelease_type = prerelease_match.group("type")
        suffix = prerelease_match.group("suffix")

        if prerelease_type in ["α", "β", "γ", "δ"]:
            has_text_suffix = True
        elif suffix and suffix.strip():
            try:
                prerelease_num = int(suffix)
            except ValueError:
                has_text_suffix = True
        else:
            has_text_suffix = False

        # Remove prerelease part for main version parsing
        cleaned = re.sub(
            r"[-.](?:alpha|beta|rc|final|[αβγδ])(?:\.\w+|\.\d+)?.*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

    return has_prerelease, prerelease_num, has_text_suffix, cleaned


def _parse_numeric_parts(cleaned: str) -> list[int]:
    """Parse numeric parts from cleaned version string."""
    cleaned = re.sub(r"[-_/]", ".", cleaned)
    all_numbers = re.findall(r"\d+", cleaned)

    if not all_numbers:
        return []

    parts = []
    for num_str in all_numbers:
        try:
            parts.append(int(num_str))
        except ValueError:
            continue

    return parts


def _build_final_version_tuple(
    parts: list[int],
    has_prerelease: bool,
    prerelease_num: int | None,
    has_text_suffix: bool,
    build_metadata: int | None,
    version_str: str,
) -> tuple[int, ...]:
    """Build the final version tuple based on all extracted information."""
    if not parts:
        return (0, 0, 0)

    # Handle special version formats
    if _is_multi_component_version(parts, has_prerelease, build_metadata):
        return tuple(parts)

    if build_metadata is not None:
        return _build_with_metadata(parts, build_metadata)

    if _is_mixed_format(version_str, parts):
        return _handle_mixed_format(parts)

    if has_prerelease:
        return _build_prerelease_tuple(parts, prerelease_num, has_text_suffix, version_str)

    # For normal versions, ensure 3 components
    return _normalize_to_three_components(parts)


def _is_multi_component_version(parts: list[int], has_prerelease: bool, build_metadata: int | None) -> bool:
    """Check if this is a 4+ component version without special suffixes."""
    return len(parts) >= 4 and not has_prerelease and build_metadata is None


def _build_with_metadata(parts: list[int], build_metadata: int) -> tuple[int, ...]:
    """Build version tuple with build metadata."""
    padded_parts = _normalize_to_three_components(parts)
    return padded_parts[:3] + (build_metadata,)


def _is_mixed_format(version_str: str, parts: list[int]) -> bool:
    """Check if version uses mixed format like '1.beta.0'."""
    original_str = version_str.lower()
    has_keywords = any(k in original_str for k in ["beta", "alpha", "rc"])
    has_pattern = re.search(r"\d+\.[a-zA-Z]+\.\d+", version_str)
    return has_keywords and len(parts) >= 2 and has_pattern is not None


def _handle_mixed_format(parts: list[int]) -> tuple[int, ...]:
    """Handle mixed format versions."""
    return (parts[0], 0, parts[-1])


def _build_prerelease_tuple(
    parts: list[int],
    prerelease_num: int | None,
    has_text_suffix: bool,
    version_str: str,
) -> tuple[int, ...]:
    """Build version tuple for prerelease versions."""
    padded_parts = _normalize_to_three_components(parts)

    if prerelease_num is not None:
        return padded_parts[:3] + (prerelease_num,)
    elif has_text_suffix:
        return padded_parts[:3]
    else:
        # Check original component count
        clean_version = version_str.split("-")[0].split("+")[0]
        original_components = len(re.findall(r"\d+", clean_version))

        if original_components >= 3:
            return padded_parts[:3] + (0,)
        return padded_parts[:3]


def _normalize_to_three_components(parts: list[int]) -> tuple[int, ...]:
    """Ensure version has at least 3 components."""
    result = parts.copy()
    while len(result) < 3:
        result.append(0)
    return tuple(result)


def parse_version(version_string: str | None) -> tuple[int, ...] | None:
    """Parse a version string into a tuple of integers for comparison.

    Args:
        version_string: The version string to parse

    Returns:
        Tuple of integers representing the version, or None for invalid inputs

    Examples:
        >>> parse_version("1.2.3")
        (1, 2, 3)
        >>> parse_version("2.0.1-beta")
        (2, 0, 1)
        >>> parse_version("1.2")
        (1, 2, 0)
        >>> parse_version("")
        (0, 0, 0)
    """
    # Handle None and empty inputs
    if version_string is None:
        return None
    if not version_string.strip():
        return (0, 0, 0)

    version_str = str(version_string).strip()

    # Step 1: Clean the version string
    cleaned = _clean_version_string(version_str)

    # Step 2: Handle special beta format early
    special_result = _handle_special_beta_format(version_str)
    if special_result is not None:
        return special_result

    # Step 3: Extract build metadata
    build_metadata, cleaned = _extract_build_metadata(cleaned)

    # Step 4: Extract prerelease information
    has_prerelease, prerelease_num, has_text_suffix, cleaned = _extract_prerelease_info(cleaned, version_str)

    # Step 5: Parse numeric parts
    parts = _parse_numeric_parts(cleaned)

    # Step 6: Build final version tuple
    return _build_final_version_tuple(
        parts,
        has_prerelease,
        prerelease_num,
        has_text_suffix,
        build_metadata,
        version_str,
    )


def _handle_none_and_empty_versions(
    version1: str | tuple[int, ...] | None,
    version2: str | tuple[int, ...] | None,
) -> int | None:
    """Handle None and empty version cases.

    Returns:
        Comparison result if handled, None if further processing needed
    """
    # Handle None cases
    if version1 is None and version2 is None:
        return 0
    if version1 is None:
        return -1
    if version2 is None:
        return 1

    # Handle empty strings
    if isinstance(version1, str) and not version1.strip():
        version1 = ""
    if isinstance(version2, str) and not version2.strip():
        version2 = ""

    if version1 == "" and version2 == "":
        return 0
    if version1 == "":
        return -1
    if version2 == "":
        return 1

    return None


def _is_version_malformed(version: str | tuple[int, ...] | None) -> bool:
    """Check if a version is malformed (no digits found)."""
    if isinstance(version, tuple):
        return False
    v_str = str(version).strip()
    # Empty strings are not malformed, they're just empty
    if not v_str:
        return False
    # If no digits found at all, it's malformed
    return not re.search(r"\d", v_str)


def _handle_malformed_versions(
    version1: str | tuple[int, ...] | None,
    version2: str | tuple[int, ...] | None,
) -> int | None:
    """Handle malformed version comparisons.

    Returns:
        Comparison result if handled, None if further processing needed
    """
    v1_malformed = _is_version_malformed(version1)
    v2_malformed = _is_version_malformed(version2)

    # If both are malformed, they're equal
    if v1_malformed and v2_malformed:
        return 0
    # If only one is malformed, the non-malformed one is greater
    if v1_malformed:
        return -1
    if v2_malformed:
        return 1

    return None


def _has_application_build_pattern(version_str: str) -> bool:
    """Check if version string has application-specific build patterns."""
    return bool(
        re.search(r"build\s+\d+", version_str, re.IGNORECASE)
        or re.search(r"\(\d+\)", version_str)
        or re.search(r"-dev-\d+", version_str)
    )


def _handle_semver_build_metadata(
    v1_str: str,
    v2_str: str,
    version1: str | tuple[int, ...] | None,
    version2: str | tuple[int, ...] | None,
) -> int | None:
    """Handle semantic versioning build metadata (+build.X)."""
    v1_has_semver_build = isinstance(version1, str) and "+" in version1
    v2_has_semver_build = isinstance(version2, str) and "+" in version2

    if not (v1_has_semver_build or v2_has_semver_build):
        return None

    v1_base = re.sub(r"\+.*$", "", v1_str) if v1_has_semver_build else v1_str
    v2_base = re.sub(r"\+.*$", "", v2_str) if v2_has_semver_build else v2_str

    # If the base versions are the same, build metadata is ignored (semver rule)
    if v1_base == v2_base:
        return 0

    # Otherwise compare the base versions
    return compare_versions(v1_base, v2_base)


def _compare_application_builds(
    v1_str: str,
    v2_str: str,
    version1: str | tuple[int, ...] | None,
    version2: str | tuple[int, ...] | None,
) -> int | None:
    """Compare versions with application-specific build patterns."""
    # Check if both versions have application build patterns
    if not _both_have_app_builds(version1, version2):
        return None

    # Parse version tuples
    v1_tuple = _parse_or_default(version1)
    v2_tuple = _parse_or_default(version2)

    # Extract build numbers
    v1_build = _extract_build_number(v1_str)
    v2_build = _extract_build_number(v2_str)

    # Compare base versions
    base_comparison = _compare_base_versions(v1_tuple, v2_tuple)
    if base_comparison != 0:
        return base_comparison

    # Base versions are equal, compare build numbers
    return _compare_build_numbers(v1_build, v2_build)


def _both_have_app_builds(
    version1: str | tuple[int, ...] | None,
    version2: str | tuple[int, ...] | None,
) -> bool:
    """Check if both versions have application build patterns."""
    v1_has = isinstance(version1, str) and _has_application_build_pattern(version1)
    v2_has = isinstance(version2, str) and _has_application_build_pattern(version2)
    return v1_has and v2_has


def _parse_or_default(version: str | tuple[int, ...] | None) -> tuple[int, ...]:
    """Parse version string or return default tuple."""
    if isinstance(version, str):
        parsed = parse_version(version)
        return parsed if parsed is not None else (0, 0, 0)
    return (0, 0, 0)


def _compare_base_versions(v1_tuple: tuple[int, ...], v2_tuple: tuple[int, ...]) -> int:
    """Compare base version tuples (first 3 components)."""
    v1_base = v1_tuple[:3] if len(v1_tuple) >= 3 else v1_tuple + (0,) * (3 - len(v1_tuple))
    v2_base = v2_tuple[:3] if len(v2_tuple) >= 3 else v2_tuple + (0,) * (3 - len(v2_tuple))

    if v1_base < v2_base:
        return -1
    elif v1_base > v2_base:
        return 1
    return 0


def _compare_build_numbers(v1_build: int | None, v2_build: int | None) -> int:
    """Compare build numbers, handling None values."""
    if v1_build is not None and v2_build is not None:
        if v1_build < v2_build:
            return -1
        elif v1_build > v2_build:
            return 1
        return 0
    elif v1_build is not None:
        return 1  # v1 has build number, v2 doesn't
    elif v2_build is not None:
        return -1  # v2 has build number, v1 doesn't
    return 0  # Neither has build number


def _normalize_app_version_string(v_str: str) -> str:
    """Remove application names but keep version info."""
    cleaned = re.sub(
        r"^(?:Google\s+)?(?:Chrome|Firefox|Safari)\s+",
        "",
        v_str,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^[a-zA-Z]+\s+(?=\d)", "", cleaned)
    return cleaned.strip()


def _handle_application_prefixes(v1_str: str, v2_str: str) -> int | None:
    """Handle versions with application name prefixes."""
    # Only apply app name prefix logic if the versions actually contain application names
    has_app_name_v1 = bool(
        re.search(r"^(?:Google\s+)?(?:Chrome|Firefox|Safari)\s+", v1_str, re.IGNORECASE)
        or re.search(r"^[a-zA-Z]+\s+(?=\d)", v1_str)
    )
    has_app_name_v2 = bool(
        re.search(r"^(?:Google\s+)?(?:Chrome|Firefox|Safari)\s+", v2_str, re.IGNORECASE)
        or re.search(r"^[a-zA-Z]+\s+(?=\d)", v2_str)
    )

    if not (has_app_name_v1 or has_app_name_v2):
        return None

    v1_norm = _normalize_app_version_string(v1_str)
    v2_norm = _normalize_app_version_string(v2_str)

    # If one version is a prefix of another (e.g., "Google Chrome 94" vs "Google Chrome 94.0.4606.81")
    # But exclude pre-release versions from this logic (they should be compared semantically)
    if v1_norm != v2_norm and not (_is_prerelease(v1_str) or _is_prerelease(v2_str)):
        v1_parts = v1_norm.split(".")
        v2_parts = v2_norm.split(".")

        # Check if one is a prefix of the other
        min_len = min(len(v1_parts), len(v2_parts))
        if v1_parts[:min_len] == v2_parts[:min_len] and len(v1_parts) != len(v2_parts):
            # The shorter version is considered equal (both point to same app)
            return 0

    return None


def _convert_to_version_tuples(
    version1: str | tuple[int, ...] | None,
    version2: str | tuple[int, ...] | None,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Convert versions to tuples for comparison."""
    # Convert to tuples if needed
    if isinstance(version1, str):
        v1_tuple = parse_version(version1)
        if v1_tuple is None:
            v1_tuple = (0, 0, 0)
    else:  # isinstance(version1, tuple) - since None was handled earlier
        v1_tuple = version1 or (0, 0, 0)

    if isinstance(version2, str):
        v2_tuple = parse_version(version2)
        if v2_tuple is None:
            v2_tuple = (0, 0, 0)
    else:  # isinstance(version2, tuple) - since None was handled earlier
        v2_tuple = version2 or (0, 0, 0)

    return v1_tuple, v2_tuple


def _compare_base_and_prerelease_versions(
    v1_tuple: tuple[int, ...],
    v2_tuple: tuple[int, ...],
    v1_str: str,
    v2_str: str,
) -> int:
    """Compare base versions and handle prerelease logic."""
    # Normalize tuples to same length for comparison
    max_len = max(len(v1_tuple), len(v2_tuple))
    v1_padded = v1_tuple + (0,) * (max_len - len(v1_tuple))
    v2_padded = v2_tuple + (0,) * (max_len - len(v2_tuple))

    # Check for pre-release versions
    v1_prerelease = _is_prerelease(v1_str)
    v2_prerelease = _is_prerelease(v2_str)

    # For pre-release vs pre-release comparisons, use special logic
    if v1_prerelease and v2_prerelease:
        return _compare_prerelease(v1_str, v2_str)

    # Compare base versions (first 3 components for consistency with most apps)
    v1_base_tuple = v1_padded[:3] if len(v1_padded) >= 3 else v1_padded + (0,) * (3 - len(v1_padded))
    v2_base_tuple = v2_padded[:3] if len(v2_padded) >= 3 else v2_padded + (0,) * (3 - len(v2_padded))

    if v1_base_tuple < v2_base_tuple:
        return -1
    elif v1_base_tuple > v2_base_tuple:
        return 1
    else:
        # Base versions are equal

        # Handle pre-release vs release
        if v1_prerelease and not v2_prerelease:
            return -1  # pre-release < release
        elif not v1_prerelease and v2_prerelease:
            return 1  # release > pre-release

        # Both are release versions with same base - compare remaining components
        if max_len > 3:
            v1_remaining = v1_padded[3:]
            v2_remaining = v2_padded[3:]
            if v1_remaining < v2_remaining:
                return -1
            elif v1_remaining > v2_remaining:
                return 1

        return 0


def compare_versions(
    version1: str | tuple[int, ...] | None,
    version2: str | tuple[int, ...] | None,
) -> int:
    """Compare two version strings or tuples.

    Args:
        version1: First version string or tuple
        version2: Second version string or tuple

    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2
    """
    # Handle None and empty cases first
    none_result = _handle_none_and_empty_versions(version1, version2)
    if none_result is not None:
        return none_result

    # Handle malformed versions
    malformed_result = _handle_malformed_versions(version1, version2)
    if malformed_result is not None:
        return malformed_result

    # Convert to string representations for further processing
    v1_str = str(version1) if not isinstance(version1, tuple) else ".".join(map(str, version1))
    v2_str = str(version2) if not isinstance(version2, tuple) else ".".join(map(str, version2))

    # Handle semver build metadata
    semver_result = _handle_semver_build_metadata(v1_str, v2_str, version1, version2)
    if semver_result is not None:
        return semver_result

    # Handle application-specific build patterns
    app_build_result = _compare_application_builds(v1_str, v2_str, version1, version2)
    if app_build_result is not None:
        return app_build_result

    # Convert to tuples for comparison
    v1_tuple, v2_tuple = _convert_to_version_tuples(version1, version2)

    # Handle special application formats
    if isinstance(version1, str) and isinstance(version2, str):
        app_prefix_result = _handle_application_prefixes(v1_str, v2_str)
        if app_prefix_result is not None:
            return app_prefix_result

    # Final comparison of base versions and prerelease logic
    return _compare_base_and_prerelease_versions(v1_tuple, v2_tuple, v1_str, v2_str)


def _extract_build_number(version_str: str) -> int | None:
    """Extract build number from version string with application-specific patterns."""
    # Look for patterns like "build 1234", "(1234)", "-dev-1234"
    patterns = [
        r"build\s+(\d+)",
        r"\((\d+)\)",
        r"-dev-(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, version_str, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue

    return None


def _is_prerelease(version_str: str) -> bool:
    """Check if a version string indicates a pre-release."""
    return bool(
        re.search(
            r"[-.](?:alpha|beta|rc|final|[αβγδ])(?:\W|$)",
            str(version_str),
            re.IGNORECASE,
        )
    )


def _compare_prerelease(version1: str | tuple[int, ...], version2: str | tuple[int, ...]) -> int:
    """Compare two pre-release versions."""
    v1_str = str(version1) if not isinstance(version1, str) else version1
    v2_str = str(version2) if not isinstance(version2, str) else version2

    # Extract pre-release type and number/suffix
    v1_type, v1_suffix = _extract_prerelease_type_and_suffix(v1_str)
    v2_type, v2_suffix = _extract_prerelease_type_and_suffix(v2_str)

    # Pre-release type priority: alpha < beta < rc < final
    type_priority = {"alpha": 1, "beta": 2, "rc": 3, "final": 4}

    v1_priority = type_priority.get(v1_type, 2)  # default to beta
    v2_priority = type_priority.get(v2_type, 2)

    if v1_priority < v2_priority:
        return -1
    elif v1_priority > v2_priority:
        return 1
    else:
        # Same type, compare suffixes
        return _compare_prerelease_suffixes(v1_suffix, v2_suffix)


def _get_unicode_priority(suffix: int | str | None) -> int | None:
    """Get priority value for Unicode Greek letters."""
    unicode_priority = {"α": 1, "β": 2, "γ": 3, "δ": 4}
    return unicode_priority.get(str(suffix)) if suffix is not None else None


def _compare_unicode_suffixes(suffix1: int | str | None, suffix2: int | str | None) -> int | None:
    """Compare Unicode Greek letter suffixes. Returns None if not applicable."""
    p1 = _get_unicode_priority(suffix1)
    p2 = _get_unicode_priority(suffix2)

    # Both are Unicode characters
    if p1 is not None and p2 is not None:
        return -1 if p1 < p2 else (1 if p1 > p2 else 0)

    # One is Unicode and one is not
    if p1 is not None and p2 is None:
        return -1
    if p2 is not None and p1 is None:
        return 1

    return None  # Neither is Unicode


def _compare_none_suffixes(suffix1: int | str | None, suffix2: int | str | None) -> int | None:
    """Compare None values. Returns None if not applicable."""
    if suffix1 is None and suffix2 is not None:
        return -1
    if suffix2 is None and suffix1 is not None:
        return 1
    if suffix1 is None and suffix2 is None:
        return 0
    return None  # Neither is None


def _compare_string_suffixes(suffix1: str, suffix2: str) -> int:
    """Compare string suffixes, handling numeric strings."""
    try:
        num1 = int(suffix1)
        try:
            num2 = int(suffix2)
            return -1 if num1 < num2 else (1 if num1 > num2 else 0)
        except ValueError:
            return -1  # number < text
    except ValueError:
        try:
            int(suffix2)
            return 1  # text > number
        except ValueError:
            # Both are text, do lexical comparison
            return -1 if suffix1 < suffix2 else (1 if suffix1 > suffix2 else 0)


def _compare_prerelease_suffixes(suffix1: int | str | None, suffix2: int | str | None) -> int:
    """Compare pre-release suffixes (numbers, strings, or None)."""
    # Handle Unicode Greek letters
    unicode_result = _compare_unicode_suffixes(suffix1, suffix2)
    if unicode_result is not None:
        return unicode_result

    # Handle None values
    none_result = _compare_none_suffixes(suffix1, suffix2)
    if none_result is not None:
        return none_result

    # Both are numbers
    if isinstance(suffix1, int) and isinstance(suffix2, int):
        return -1 if suffix1 < suffix2 else (1 if suffix1 > suffix2 else 0)

    # Both are strings (not Unicode)
    if isinstance(suffix1, str) and isinstance(suffix2, str):
        return _compare_string_suffixes(suffix1, suffix2)

    # Mixed types: numbers come before strings
    if isinstance(suffix1, int) and isinstance(suffix2, str):
        return -1
    if isinstance(suffix1, str) and isinstance(suffix2, int):
        return 1

    return 0


def _normalize_unicode_prerelease_type(prerelease_type: str) -> str:
    """Normalize Unicode prerelease types to English equivalents."""
    unicode_mapping = {"α": "alpha", "β": "beta"}
    return unicode_mapping.get(prerelease_type, prerelease_type)


def _parse_prerelease_suffix(suffix: str | None) -> int | str | None:
    """Parse prerelease suffix, converting to int if possible."""
    if not suffix:
        return None

    try:
        return int(suffix)
    except ValueError:
        return suffix


def _extract_standalone_unicode_prerelease(version_str: str) -> tuple[str, str] | None:
    """Extract standalone Unicode prerelease characters."""
    unicode_match = re.search(r"[-.](?P<unicode>[αβγδ])", version_str)
    if not unicode_match:
        return None

    unicode_char = unicode_match.group("unicode")
    unicode_to_type = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta"}

    prerelease_type = unicode_to_type.get(unicode_char, "beta")
    return prerelease_type, unicode_char


def _extract_prerelease_type_and_suffix(
    version_str: str,
) -> tuple[str, int | str | None]:
    """Extract pre-release type and number/suffix from version string."""
    # Look for alpha, beta, rc, final with optional number or suffix, including Unicode
    match = re.search(
        r"[-.](?P<type>alpha|beta|rc|final|α|β)(?:\.(?P<suffix>\w+|\d+))?",
        version_str,
        re.IGNORECASE,
    )

    if match:
        prerelease_type = _normalize_unicode_prerelease_type(match.group("type").lower())
        suffix = _parse_prerelease_suffix(match.group("suffix"))
        return prerelease_type, suffix

    # Check for standalone Unicode characters (1.0.0-α)
    unicode_result = _extract_standalone_unicode_prerelease(version_str)
    if unicode_result:
        return unicode_result

    return "beta", None  # default


def is_version_newer(current: str, latest: str) -> bool:
    """Check if the latest version is newer than the current version.

    Args:
        current: Current version string
        latest: Latest version string

    Returns:
        True if latest is newer than current
    """
    return compare_versions(current, latest) < 0


@lru_cache(maxsize=128)
def get_homebrew_cask_info(app_name: str, use_enhanced: bool = True) -> dict[str, str] | None:
    """Get Homebrew cask information for an application.

    Args:
        app_name: Name of the application
        use_enhanced: Whether to use enhanced matching (default: True)

    Returns:
        Dictionary with cask information or None if not found
    """
    try:
        # First try exact match
        # brew is a known system command, using list args is safe
        result = subprocess.run(  # nosec B603 B607
            ["brew", "info", "--cask", app_name, "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0:
            import json

            try:
                cask_data = json.loads(result.stdout)
                if cask_data and isinstance(cask_data, list) and len(cask_data) > 0:
                    cask = cask_data[0]
                    return {
                        "name": cask.get("token", app_name),
                        "version": cask.get("version", "unknown"),
                        "description": cask.get("desc", ""),
                    }
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON for cask %s", app_name)

        # If exact match fails, try fuzzy search
        return _search_homebrew_casks(app_name, use_enhanced)

    except subprocess.TimeoutExpired:
        logger.warning("Timeout while checking Homebrew cask for %s", app_name)
        raise VTTimeoutError(f"Homebrew operation timed out for {app_name}") from None
    except (OSError, subprocess.SubprocessError) as e:
        logger.error("Error checking Homebrew cask for %s: %s", app_name, e)
        return None


def _get_homebrew_casks_list() -> list[str] | None:
    """Get list of all available Homebrew casks."""
    try:
        # brew is a known system command, using list args is safe (enhanced search)
        result = subprocess.run(  # nosec B603 B607
            ["brew", "search", "--cask"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if result.returncode != 0:
            return None

        casks = result.stdout.strip().split("\n")
        casks = [cask.strip() for cask in casks if cask.strip()]

        return casks if casks else None

    except subprocess.TimeoutExpired:
        logger.warning("Timeout while fetching Homebrew casks list")
        raise VTTimeoutError("Homebrew search timed out") from None
    except (OSError, subprocess.SubprocessError) as e:
        logger.error("Error fetching Homebrew casks list: %s", e)
        return None


def _try_enhanced_cask_matching(app_name: str, casks: list[str]) -> str | None:
    """Try enhanced matching for cask search."""
    try:
        from versiontracker.enhanced_matching import find_best_enhanced_match

        match_result = find_best_enhanced_match(app_name, casks, threshold=70)
        if match_result:
            return match_result[0]
    except ImportError:
        logger.debug("Enhanced matching not available, falling back to basic matching")

    return None


def _basic_fuzzy_cask_matching(app_name: str, casks: list[str]) -> str | None:
    """Perform basic fuzzy matching for cask search."""
    normalized_app_name = normalise_name(app_name)
    best_match: str | None = None
    best_score = 0

    for cask in casks:
        normalized_cask = normalise_name(cask)

        # Calculate similarity score
        if fuzz:
            score = fuzz.ratio(normalized_app_name, normalized_cask)
            if score > best_score and score > 70:  # Minimum threshold
                best_score = score
                best_match = cask

    return best_match


def _search_homebrew_casks(app_name: str, use_enhanced: bool = True) -> dict[str, str] | None:
    """Search for Homebrew casks using fuzzy matching.

    Args:
        app_name: Name of the application to search for
        use_enhanced: Whether to use enhanced matching (default: True)

    Returns:
        Dictionary with cask information or None if not found
    """
    try:
        casks = _get_homebrew_casks_list()
        if not casks:
            return None

        # Try enhanced matching first if enabled
        best_match = None
        if use_enhanced:
            best_match = _try_enhanced_cask_matching(app_name, casks)

        # Fallback to basic fuzzy matching if enhanced didn't work
        if not best_match:
            best_match = _basic_fuzzy_cask_matching(app_name, casks)

        if best_match:
            return get_homebrew_cask_info(best_match)

        return None

    except subprocess.TimeoutExpired:
        logger.warning("Timeout while searching Homebrew casks for %s", app_name)
        raise VTTimeoutError(f"Homebrew search timed out for {app_name}") from None
    except (OSError, subprocess.SubprocessError) as e:
        logger.error("Error searching Homebrew casks for %s: %s", app_name, e)
        return None


def _get_config_settings() -> tuple[bool, int]:
    """Get configuration settings for version checking.

    Returns:
        Tuple of (show_progress, max_workers)
    """
    try:
        from versiontracker.config import get_config

        config = get_config()
        show_progress = getattr(getattr(config, "ui", None), "progress", True)
        max_workers = min(
            getattr(getattr(config, "performance", None), "max_workers", 4),
            multiprocessing.cpu_count(),
        )
        return show_progress, max_workers
    except (AttributeError, TypeError, ImportError):
        # Fallback to default values
        return True, min(4, multiprocessing.cpu_count())


def _process_single_app(app_info: tuple[str, str], use_enhanced_matching: bool = True) -> ApplicationInfo:
    """Process a single application to check its version status.

    Args:
        app_info: Tuple of (app_name, current_version)
        use_enhanced_matching: Whether to use enhanced fuzzy matching

    Returns:
        ApplicationInfo object with version status
    """
    app_name, current_version = app_info

    try:
        # Get Homebrew cask information
        homebrew_info = get_homebrew_cask_info(app_name, use_enhanced_matching)

        if not homebrew_info:
            return ApplicationInfo(
                name=app_name,
                version_string=current_version,
                status=VersionStatus.UNKNOWN,
                error_message="Not found in Homebrew",
            )

        latest_version = homebrew_info.get("version", "unknown")
        homebrew_name = homebrew_info.get("name", app_name)

        # Compare versions
        if latest_version == "unknown" or latest_version == "latest":
            status = VersionStatus.UNKNOWN
        elif is_version_newer(current_version, latest_version):
            status = VersionStatus.OUTDATED
        elif compare_versions(current_version, latest_version) == 0:
            status = VersionStatus.UP_TO_DATE
        else:
            status = VersionStatus.NEWER

        return ApplicationInfo(
            name=app_name,
            version_string=current_version,
            homebrew_name=homebrew_name,
            latest_version=latest_version,
            status=status,
        )

    except VTTimeoutError:
        return ApplicationInfo(
            name=app_name,
            version_string=current_version,
            status=VersionStatus.ERROR,
            error_message="Network timeout",
        )
    except (OSError, subprocess.SubprocessError, NetworkError) as e:
        logger.error("Error processing %s: %s", app_name, e)
        return ApplicationInfo(
            name=app_name,
            version_string=current_version,
            status=VersionStatus.ERROR,
            error_message=str(e),
        )


def _process_app_batch(apps: list[tuple[str, str]], use_enhanced_matching: bool = True) -> list[ApplicationInfo]:
    """Process a batch of applications.

    Args:
        apps: List of application tuples (name, version)
        use_enhanced_matching: Whether to use enhanced fuzzy matching

    Returns:
        List of ApplicationInfo objects
    """
    return [_process_single_app(app, use_enhanced_matching) for app in apps]


def _create_app_batches(apps: list[tuple[str, str]], batch_size: int) -> list[list[tuple[str, str]]]:
    """Create batches of applications for parallel processing.

    Args:
        apps: List of applications
        batch_size: Size of each batch

    Returns:
        List of application batches
    """
    return [apps[i : i + batch_size] for i in range(0, len(apps), batch_size)]


def _handle_batch_result(future: concurrent.futures.Future[list[ApplicationInfo]], results: list[ApplicationInfo], error_count: int, max_errors: int) -> int:
    """Handle the result of a batch processing future.

    Args:
        future: The completed future
        results: List to append successful results to
        error_count: Current error count
        max_errors: Maximum allowed errors

    Returns:
        Updated error count

    Raises:
        NetworkError: If too many errors occur
    """
    try:
        batch_results = future.result()
        results.extend(batch_results)
        return error_count
    except (RuntimeError, concurrent.futures.TimeoutError) as e:
        logger.error("Batch processing failed: %s", e)
        error_count += 1
        if error_count >= max_errors:
            raise NetworkError(f"Too many batch processing failures: {e}") from e
        return error_count


def check_outdated_apps(
    apps: list[tuple[str, str]],
    batch_size: int = 50,
    use_enhanced_matching: bool = True,
) -> list[tuple[str, dict[str, str], VersionStatus]]:
    """Check which applications are outdated compared to their Homebrew versions.

    Args:
        apps: List of applications with name and version
        batch_size: How many applications to check in one batch
        use_enhanced_matching: Whether to use enhanced fuzzy matching

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

    results: list[ApplicationInfo] = []
    error_count = 0
    max_errors = 3

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit batch processing tasks
        futures = [executor.submit(_process_app_batch, batch, use_enhanced_matching) for batch in batches]

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
                error_count = _handle_batch_result(future, results, error_count, max_errors)
        else:
            # Process without progress bar
            for future in concurrent.futures.as_completed(futures):
                error_count = _handle_batch_result(future, results, error_count, max_errors)

    # Convert results to expected format
    return [
        (
            app_info.name,
            {
                "installed": app_info.version_string,
                "latest": app_info.latest_version or "Unknown",
            },
            app_info.status,
        )
        for app_info in results
    ]


def similarity_score(s1: str | None, s2: str | None) -> int:
    """Calculate similarity score between two strings.

    This function provides a similarity score between 0-100 for two strings,
    with special handling for None and empty string values.

    Args:
        s1: First string to compare (can be None)
        s2: Second string to compare (can be None)

    Returns:
        Similarity score from 0-100
    """
    # Handle None cases
    if s1 is None or s2 is None:
        return 0

    # Handle empty string cases
    if s1 == "" and s2 == "":
        return 100
    if s1 == "" or s2 == "":
        return 0

    # Use the existing fuzzy matching logic
    try:
        if fuzz and hasattr(fuzz, "ratio"):
            return int(fuzz.ratio(s1, s2))
    except (AttributeError, TypeError, ValueError) as e:
        logger.error("Error calculating similarity score for '%s' vs '%s': %s", s1, s2, e)

    # Simple fallback
    return 100 if s1.lower() == s2.lower() else (70 if s1.lower() in s2.lower() or s2.lower() in s1.lower() else 0)


def partial_ratio(s1: str, s2: str, score_cutoff: int | None = None) -> int:
    """Calculate partial ratio between two strings.

    Provides compatibility between rapidfuzz and fuzzywuzzy, with fallbacks.

    Args:
        s1: First string to compare
        s2: Second string to compare
        score_cutoff: Optional score cutoff (for compatibility, currently unused)

    Returns:
        Similarity score from 0-100
    """
    # Silence unused parameter warning
    _ = score_cutoff

    if not s1 or not s2:
        return 0

    try:
        if fuzz and hasattr(fuzz, "partial_ratio"):
            return int(fuzz.partial_ratio(s1, s2))
    except (AttributeError, TypeError, ValueError) as e:
        logger.error("Error calculating partial ratio for '%s' vs '%s': %s", s1, s2, e)

    # Simple fallback
    return 100 if s1.lower() == s2.lower() else (70 if s1.lower() in s2.lower() or s2.lower() in s1.lower() else 0)


def get_partial_ratio_scorer() -> Callable[[str, str], float]:
    """Return a scorer function compatible with rapidfuzz/fuzzywuzzy extractOne."""
    if USE_RAPIDFUZZ and fuzz and hasattr(fuzz, "partial_ratio"):

        def rapidfuzz_scorer(s1: str, s2: str) -> float:
            # fuzz is not None here due to the checks above
            return float(fuzz.partial_ratio(s1, s2))

        return rapidfuzz_scorer
    elif USE_FUZZYWUZZY and fuzz and hasattr(fuzz, "partial_ratio"):

        def fuzzywuzzy_scorer(s1: str, s2: str) -> float:
            # fuzz is not None here due to the checks above
            return float(fuzz.partial_ratio(s1, s2))

        return fuzzywuzzy_scorer
    else:

        def fallback_scorer(s1: str, s2: str) -> float:
            # Fallback implementation
            return (
                100.0
                if s1.lower() == s2.lower()
                else (70.0 if s1.lower() in s2.lower() or s2.lower() in s1.lower() else 0.0)
            )

        return fallback_scorer


class _EarlyReturn:
    """Sentinel class to indicate early return with None."""

    pass


def _handle_empty_and_malformed_versions(
    version1: str | tuple[int, ...] | None,
    version2: str | tuple[int, ...] | None,
) -> tuple[int, ...] | _EarlyReturn | None:
    """Handle empty and malformed version cases.

    Returns _EarlyReturn() if should return None, None if should continue processing.
    """
    # Handle None cases - should return None from get_version_difference
    if version1 is None or version2 is None:
        return _EarlyReturn()

    v1_malformed = _is_version_malformed(version1)
    v2_malformed = _is_version_malformed(version2)

    # Handle empty strings specially - they should be treated as (0, 0, 0)
    v1_empty = isinstance(version1, str) and not version1.strip()
    v2_empty = isinstance(version2, str) and not version2.strip()

    # If both are empty, return zero difference
    if v1_empty and v2_empty:
        return (0, 0, 0)

    # If both are malformed (but not empty), return zero difference
    if v1_malformed and v2_malformed:
        return (0, 0, 0)

    # If either version is malformed (but not empty), return None from get_version_difference
    if v1_malformed or v2_malformed:
        return _EarlyReturn()

    # Continue with normal processing
    return None


def _convert_versions_to_tuples(
    version1: str | tuple[int, ...] | None,
    version2: str | tuple[int, ...] | None,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Convert versions to tuples for comparison."""
    if isinstance(version1, str):
        v1_tuple = parse_version(version1)
        if v1_tuple is None:
            v1_tuple = (0, 0, 0)
    elif version1 is None:
        v1_tuple = (0, 0, 0)
    else:
        v1_tuple = version1

    if isinstance(version2, str):
        v2_tuple = parse_version(version2)
        if v2_tuple is None:
            v2_tuple = (0, 0, 0)
    elif version2 is None:
        v2_tuple = (0, 0, 0)
    else:
        v2_tuple = version2

    return v1_tuple, v2_tuple


def _check_version_metadata(
    version1: str | tuple[int, ...] | None,
    version2: str | tuple[int, ...] | None,
) -> tuple[bool, bool]:
    """Check if versions have build metadata or prerelease patterns."""
    v1_has_build_metadata = isinstance(version1, str) and (
        "+build." in version1 or bool(re.search(r"\+.*\d+", version1))
    )
    v2_has_build_metadata = isinstance(version2, str) and (
        "+build." in version2 or bool(re.search(r"\+.*\d+", version2))
    )

    v1_has_prerelease = isinstance(version1, str) and _is_prerelease(version1)
    v2_has_prerelease = isinstance(version2, str) and _is_prerelease(version2)

    return (
        v1_has_build_metadata and v2_has_build_metadata,
        v1_has_prerelease and v2_has_prerelease,
    )


def _apply_version_truncation(
    v1_padded: tuple[int, ...],
    v2_padded: tuple[int, ...],
    max_len: int,
    both_have_build_metadata: bool,
    both_have_prerelease: bool,
) -> tuple[tuple[int, ...], tuple[int, ...], int]:
    """Apply truncation rules for build metadata and prerelease versions."""
    # If both versions have build metadata, compare only first 3 components
    if both_have_build_metadata:
        max_len = min(max_len, 3)
        v1_padded = v1_padded[:3]
        v2_padded = v2_padded[:3]
    # If both versions have pre-release tags, ignore pre-release components
    elif both_have_prerelease:
        max_len = min(max_len, 3)
        v1_padded = v1_padded[:3]
        v2_padded = v2_padded[:3]

    return v1_padded, v2_padded, max_len


def get_version_difference(
    version1: str | tuple[int, ...] | None,
    version2: str | tuple[int, ...] | None,
) -> tuple[int, ...] | None:
    """Get the signed difference between two versions (v1 - v2).

    Args:
        version1: First version string or tuple
        version2: Second version string or tuple

    Returns:
        Tuple containing signed version difference (v1 - v2), or None if either version is None or malformed
    """
    # Handle empty and malformed versions
    early_result = _handle_empty_and_malformed_versions(version1, version2)
    if isinstance(early_result, _EarlyReturn):
        return None
    elif early_result is not None:
        return early_result

    # Convert to tuples
    v1_tuple, v2_tuple = _convert_versions_to_tuples(version1, version2)

    # Pad to same length
    max_len = max(len(v1_tuple), len(v2_tuple))
    v1_padded = v1_tuple + (0,) * (max_len - len(v1_tuple))
    v2_padded = v2_tuple + (0,) * (max_len - len(v2_tuple))

    # Check for metadata patterns
    both_have_build_metadata, both_have_prerelease = _check_version_metadata(version1, version2)

    # Apply truncation rules
    v1_padded, v2_padded, max_len = _apply_version_truncation(
        v1_padded, v2_padded, max_len, both_have_build_metadata, both_have_prerelease
    )

    # Calculate signed differences (v1 - v2)
    differences = tuple(v1_padded[i] - v2_padded[i] for i in range(max_len))

    return differences


def get_version_info(current_version: str | None, latest_version: str | None = None) -> ApplicationInfo:
    """Get information about version(s) and comparison.

    Args:
        current_version: Current version string to analyze
        latest_version: Optional latest version for comparison

    Returns:
        ApplicationInfo object with version information and status
    """
    if current_version is None:
        current_version = ""

    # Parse current version
    current_parsed = parse_version(current_version)
    if current_parsed is None:
        current_parsed = (0, 0, 0)

    # Create base ApplicationInfo object
    app_info = ApplicationInfo(name="Unknown", version_string=current_version, status=VersionStatus.UNKNOWN)

    if latest_version is None:
        # Single version analysis - just return basic info
        return app_info

    # Two version comparison
    return _perform_version_comparison(app_info, current_version, latest_version)


def _perform_version_comparison(
    app_info: ApplicationInfo, current_version: str, latest_version: str
) -> ApplicationInfo:
    """Perform comparison between current and latest versions.

    Args:
        app_info: Base ApplicationInfo object to update
        current_version: Current version string (already normalized from None to "")
        latest_version: Latest version string

    Returns:
        Updated ApplicationInfo object with comparison results
    """
    latest_parsed = parse_version(latest_version)
    if latest_parsed is None:
        latest_parsed = (0, 0, 0)

    app_info.latest_version = latest_version
    app_info.latest_parsed = latest_parsed

    # Check for empty string cases
    status = _handle_empty_version_cases(current_version, latest_version)
    if status is not None:
        app_info.status = status
        return app_info

    # Check for malformed versions
    if _is_version_malformed(current_version) or _is_version_malformed(latest_version):
        app_info.status = VersionStatus.UNKNOWN
        return app_info

    # Perform version comparison and set status
    _set_version_comparison_status(app_info, current_version, latest_version)
    return app_info


def _handle_empty_version_cases(current_version: str, latest_version: str) -> VersionStatus | None:
    """Handle cases where one or both versions are empty strings.

    Args:
        current_version: Current version string
        latest_version: Latest version string

    Returns:
        VersionStatus if a special case is detected, None otherwise
    """
    # Both empty strings should be considered equal
    if current_version == "" and latest_version == "":
        return VersionStatus.UP_TO_DATE

    # One empty string but not both - return UNKNOWN
    if current_version == "" or latest_version == "":
        return VersionStatus.UNKNOWN

    return None


def _set_version_comparison_status(app_info: ApplicationInfo, current_version: str, latest_version: str) -> None:
    """Set the version comparison status and difference information.

    Args:
        app_info: ApplicationInfo object to update
        current_version: Current version string
        latest_version: Latest version string
    """
    comparison = compare_versions(current_version, latest_version)

    if comparison == 0:
        app_info.status = VersionStatus.UP_TO_DATE
    elif comparison < 0:
        app_info.status = VersionStatus.OUTDATED
        diff = get_version_difference(current_version, latest_version)
        if diff is not None:
            app_info.outdated_by = tuple(abs(x) for x in diff)
    else:
        app_info.status = VersionStatus.NEWER
        diff = get_version_difference(latest_version, current_version)
        if diff is not None:
            app_info.newer_by = tuple(abs(x) for x in diff)


def check_latest_version(app_name: str) -> str | None:
    """Check the latest version available for an application.

    Args:
        app_name: Name of the application

    Returns:
        Latest version string or None if not found
    """
    homebrew_info = get_homebrew_cask_info(app_name)
    if homebrew_info:
        return homebrew_info.get("version", None)
    return None


def find_matching_cask(app_name: str, threshold: int = 70, use_enhanced: bool = True) -> str | None:
    """Find a matching Homebrew cask for an application.

    Args:
        app_name: Name of the application
        threshold: Minimum similarity threshold (0-100)
        use_enhanced: Whether to use enhanced matching (default: True)

    Returns:
        Name of matching cask or None if not found
    """
    try:
        # Get list of all casks
        # brew is a known system command, using list args is safe (find matching)
        result = subprocess.run(  # nosec B603 B607
            ["brew", "search", "--cask"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if result.returncode != 0:
            return None

        casks = result.stdout.strip().split("\n")
        casks = [cask.strip() for cask in casks if cask.strip()]

        if not casks:
            return None

        # Use enhanced matching if available and enabled
        if use_enhanced:
            try:
                from versiontracker.enhanced_matching import find_best_enhanced_match

                match_result = find_best_enhanced_match(app_name, casks, threshold)
                if match_result:
                    return match_result[0]
            except ImportError:
                logger.debug("Enhanced matching not available, falling back to basic matching")

        # Fallback to basic fuzzy matching
        normalized_app_name = normalise_name(app_name)
        fallback_best_match: str | None = None
        best_score = 0

        for cask in casks:
            normalized_cask = normalise_name(cask)

            # Calculate similarity score
            if fuzz:
                score = fuzz.ratio(normalized_app_name, normalized_cask)
                if score > best_score and score >= threshold:
                    best_score = score
                    fallback_best_match = cask

        return fallback_best_match

    except (OSError, subprocess.SubprocessError, AttributeError) as e:
        logger.error("Error finding matching cask for %s: %s", app_name, e)
        return None


# Additional internal functions that tests might expect
def _parse_version_components(version_string: str) -> dict[str, int]:
    """Parse version string into components dictionary.

    Args:
        version_string: Version string to parse

    Returns:
        Dictionary with version components
    """
    parsed = parse_version(version_string)
    if parsed is None:
        parsed = (0, 0, 0)
    return {
        "major": parsed[0] if len(parsed) > 0 else 0,
        "minor": parsed[1] if len(parsed) > 1 else 0,
        "patch": parsed[2] if len(parsed) > 2 else 0,
        "build": parsed[3] if len(parsed) > 3 else 0,
    }


def _parse_version_to_dict(
    version_string: str,
) -> dict[str, str | int | tuple[int, ...] | None]:
    """Parse version string to dictionary format.

    Args:
        version_string: Version string to parse

    Returns:
        Dictionary representation of version
    """
    info = get_version_info(version_string)
    parsed = info.parsed

    # Extract version components
    if parsed is not None:
        major = parsed[0] if len(parsed) > 0 else 0
        minor = parsed[1] if len(parsed) > 1 else 0
        patch = parsed[2] if len(parsed) > 2 else 0
        build = parsed[3] if len(parsed) > 3 else 0
    else:
        major = minor = patch = build = 0

    return {
        "original": version_string,
        "parsed": parsed,
        "pattern_type": "semantic" if parsed and len(parsed) >= 3 else "unknown",
        "major": major,
        "minor": minor,
        "patch": patch,
        "build": build,
    }


def _dict_to_tuple(version_dict: dict[str, int] | None) -> tuple[int, ...] | None:
    """Convert version dictionary to tuple.

    Args:
        version_dict: Dictionary with version components

    Returns:
        Tuple of version numbers or None if input is None
    """
    if version_dict is None:
        return None

    return (
        version_dict.get("major", 0),
        version_dict.get("minor", 0),
        version_dict.get("patch", 0),
        version_dict.get("build", 0),
    )


def _tuple_to_dict(version_tuple: tuple[int, ...] | None) -> dict[str, int]:
    """Convert version tuple to dictionary.

    Args:
        version_tuple: Tuple of version numbers

    Returns:
        Dictionary with version components
    """
    if version_tuple is None:
        return {
            "major": 0,
            "minor": 0,
            "patch": 0,
            "build": 0,
        }

    return {
        "major": version_tuple[0] if len(version_tuple) > 0 else 0,
        "minor": version_tuple[1] if len(version_tuple) > 1 else 0,
        "patch": version_tuple[2] if len(version_tuple) > 2 else 0,
        "build": version_tuple[3] if len(version_tuple) > 3 else 0,
    }


def compare_fuzzy(version1: str, version2: str, threshold: int = 80) -> float:
    """Compare two version strings using fuzzy matching.

    Args:
        version1: First version string
        version2: Second version string
        threshold: Minimum similarity threshold (not used in return value)

    Returns:
        Similarity score between 0.0 and 100.0
    """
    if fuzz:
        return float(fuzz.ratio(version1, version2))
    # Fallback when no fuzzy library available
    return 100.0 if version1.lower() == version2.lower() else 0.0


def compose_version_tuple(*components: int) -> tuple[int, ...]:
    """Compose a version tuple from individual components.

    Args:
        components: Version number components

    Returns:
        Tuple of version numbers
    """
    return tuple(components)


def decompose_version(version_string: str | None) -> dict[str, int] | None:
    """Decompose a version string into components.

    Args:
        version_string: Version string to decompose

    Returns:
        Dictionary with version components or None if invalid
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


def get_compiled_pattern(pattern: str) -> re.Pattern | None:
    """Get a compiled regex pattern from a pattern string.

    Args:
        pattern: Regex pattern string to compile

    Returns:
        Compiled regex pattern or None if compilation fails
    """
    try:
        return re.compile(pattern)
    except re.error:
        return None


# Update the __all__ export list to include new functions
__all__ = [
    "VersionStatus",
    "ApplicationInfo",
    "VersionInfo",  # Alias
    "parse_version",
    "compare_versions",
    "is_version_newer",
    "get_homebrew_cask_info",
    "check_outdated_apps",
    "get_partial_ratio_scorer",
    "partial_ratio",
    "get_version_difference",
    "get_version_info",
    "check_latest_version",
    "find_matching_cask",
    "VERSION_PATTERNS",
    "compare_fuzzy",
    "compose_version_tuple",
    "decompose_version",
    "get_compiled_pattern",
    "_parse_version_components",
    "_parse_version_to_dict",
    "_dict_to_tuple",
    "_tuple_to_dict",
    "USE_RAPIDFUZZ",
    "USE_FUZZYWUZZY",
]
