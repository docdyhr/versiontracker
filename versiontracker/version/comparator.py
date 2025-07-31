"""Version comparison functionality."""

import logging
import re
from typing import List, Optional, Tuple, Union

# Import parse_version from parser module
from .parser import parse_version


class _EarlyReturn:
    """Sentinel class to indicate early return with None."""

    pass


def _handle_none_and_empty_versions(
    version1: Union[str, Tuple[int, ...], None],
    version2: Union[str, Tuple[int, ...], None],
) -> Optional[int]:
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


def _is_version_malformed(version: Union[str, Tuple[int, ...], None]) -> bool:
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
    version1: Union[str, Tuple[int, ...], None],
    version2: Union[str, Tuple[int, ...], None],
) -> Optional[int]:
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
    version1: Union[str, Tuple[int, ...], None],
    version2: Union[str, Tuple[int, ...], None],
) -> Optional[int]:
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
    version1: Union[str, Tuple[int, ...], None],
    version2: Union[str, Tuple[int, ...], None],
) -> Optional[int]:
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
    version1: Union[str, Tuple[int, ...], None],
    version2: Union[str, Tuple[int, ...], None],
) -> bool:
    """Check if both versions have application build patterns."""
    v1_has = isinstance(version1, str) and _has_application_build_pattern(version1)
    v2_has = isinstance(version2, str) and _has_application_build_pattern(version2)
    return v1_has and v2_has


def _parse_or_default(version: Union[str, Tuple[int, ...], None]) -> Tuple[int, ...]:
    """Parse version string or return default tuple."""
    if isinstance(version, str):
        parsed = parse_version(version)
        return parsed if parsed is not None else (0, 0, 0)
    return (0, 0, 0)


def _compare_base_versions(v1_tuple: Tuple[int, ...], v2_tuple: Tuple[int, ...]) -> int:
    """Compare base version tuples (first 3 components)."""
    v1_base = v1_tuple[:3] if len(v1_tuple) >= 3 else v1_tuple + (0,) * (3 - len(v1_tuple))
    v2_base = v2_tuple[:3] if len(v2_tuple) >= 3 else v2_tuple + (0,) * (3 - len(v2_tuple))

    if v1_base < v2_base:
        return -1
    elif v1_base > v2_base:
        return 1
    return 0


def _compare_build_numbers(v1_build: Optional[int], v2_build: Optional[int]) -> int:
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


def _handle_application_prefixes(v1_str: str, v2_str: str) -> Optional[int]:
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
    version1: Union[str, Tuple[int, ...], None],
    version2: Union[str, Tuple[int, ...], None],
) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
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
    v1_tuple: Tuple[int, ...],
    v2_tuple: Tuple[int, ...],
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
    version1: Union[str, Tuple[int, ...], None],
    version2: Union[str, Tuple[int, ...], None],
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
    # Validate that all tuple elements are integers before joining
    def tuple_to_version_str(version_tuple):
        if not all(isinstance(x, int) for x in version_tuple):
            # Handle non-integer elements in version tuple
            # You may choose to raise an error, return a special value, or handle as malformed
            # Here, we return the malformed_result for consistency
            return None
        return ".".join(map(str, version_tuple))

    if isinstance(version1, tuple):
        v1_str = tuple_to_version_str(version1)
        if v1_str is None:
            # Handle malformed tuple - treat as comparison between malformed versions
            return _handle_malformed_versions(version1, version2) or 0
    else:
        v1_str = str(version1)

    if isinstance(version2, tuple):
        v2_str = tuple_to_version_str(version2)
        if v2_str is None:
            # Handle malformed tuple - treat as comparison between malformed versions
            return _handle_malformed_versions(version1, version2) or 0
    else:
        v2_str = str(version2)

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


def _extract_build_number(version_str: str) -> Optional[int]:
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
            version_str,
            re.IGNORECASE,
        )
    )


def _compare_prerelease(version1: Union[str, Tuple[int, ...]], version2: Union[str, Tuple[int, ...]]) -> int:
    """Compare two pre-release versions."""
    v1_str = str(version1) if not isinstance(version1, str) else version1
    v2_str = str(version2) if not isinstance(version2, str) else version2

    # Extract pre-release type and number/suffix
    v1_type, v1_suffix = _extract_prerelease_type_and_suffix(v1_str)
    v2_type, v2_suffix = _extract_prerelease_type_and_suffix(v2_str)

    # Pre-release type priority: alpha < beta < rc < final
    type_priority = {"alpha": 1, "beta": 2, "rc": 3, "final": 4}

    # Handle unknown prerelease types with warning
    v1_priority = type_priority.get(v1_type)
    v2_priority = type_priority.get(v2_type)

    if v1_priority is None:
        logging.warning("Unknown prerelease type '%s' encountered, treating as beta", v1_type)
        v1_priority = 2  # default to beta with warning
    if v2_priority is None:
        logging.warning("Unknown prerelease type '%s' encountered, treating as beta", v2_type)
        v2_priority = 2  # default to beta with warning

    if v1_priority < v2_priority:
        return -1
    elif v1_priority > v2_priority:
        return 1
    else:
        # Same type, compare suffixes
        return _compare_prerelease_suffixes(v1_suffix, v2_suffix)


def _get_unicode_priority(suffix: Union[int, str, None]) -> Optional[int]:
    """Get priority value for Unicode Greek letters."""
    unicode_priority = {"α": 1, "β": 2, "γ": 3, "δ": 4}
    return unicode_priority.get(str(suffix)) if suffix is not None else None


def _compare_unicode_suffixes(suffix1: Union[int, str, None], suffix2: Union[int, str, None]) -> Optional[int]:
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


def _compare_none_suffixes(suffix1: Union[int, str, None], suffix2: Union[int, str, None]) -> Optional[int]:
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


def _compare_prerelease_suffixes(suffix1: Union[int, str, None], suffix2: Union[int, str, None]) -> int:
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


def _extract_prerelease_type_and_suffix(
    version_str: str,
) -> Tuple[str, Union[int, str, None]]:
    """Extract pre-release type and number/suffix from version string."""
    # Look for alpha, beta, rc, final with optional number or suffix, including Unicode
    match = re.search(
        r"[-.](?P<type>alpha|beta|rc|final|α|β)(?:\.(?P<suffix>\w+|\d+))?",
        version_str,
        re.IGNORECASE,
    )
    if match:
        prerelease_type = match.group("type").lower()

        # Map Unicode characters to English equivalents
        if prerelease_type == "α":
            prerelease_type = "alpha"
        elif prerelease_type == "β":
            prerelease_type = "beta"

        suffix = match.group("suffix")
        if suffix:
            # Try to convert to int, otherwise keep as string
            try:
                return prerelease_type, int(suffix)
            except ValueError:
                return prerelease_type, suffix
        else:
            # No suffix means it's the base pre-release (None to distinguish from 0)
            return prerelease_type, None

    # Check for standalone Unicode characters (1.0.0-α)
    unicode_match = re.search(r"[-.](?P<unicode>[αβγδ])", version_str)
    if unicode_match:
        unicode_char = unicode_match.group("unicode")
        if unicode_char == "α":
            return "alpha", unicode_char
        elif unicode_char == "β":
            return "beta", unicode_char
        elif unicode_char == "γ":
            return "gamma", unicode_char
        elif unicode_char == "δ":
            return "delta", unicode_char

    # No prerelease pattern found - return None to indicate stable release
    return "final", None  # Treat as stable/final release when no prerelease markers found


def is_version_newer(current: str, latest: str) -> bool:
    """Check if the latest version is newer than the current version.

    Args:
        current: Current version string
        latest: Latest version string

    Returns:
        True if latest is newer than current
    """
    return compare_versions(current, latest) < 0


# Helper functions for get_version_difference
def _handle_empty_and_malformed_versions(
    version1: Union[str, Tuple[int, ...], None],
    version2: Union[str, Tuple[int, ...], None],
) -> Union[Tuple[int, ...], _EarlyReturn, None]:
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
    version1: Union[str, Tuple[int, ...], None],
    version2: Union[str, Tuple[int, ...], None],
) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
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
    version1: Union[str, Tuple[int, ...], None],
    version2: Union[str, Tuple[int, ...], None],
) -> Tuple[bool, bool]:
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
    v1_padded: Tuple[int, ...],
    v2_padded: Tuple[int, ...],
    max_len: int,
    both_have_build_metadata: bool,
    both_have_prerelease: bool,
) -> Tuple[Tuple[int, ...], Tuple[int, ...], int]:
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
    version1: Union[str, Tuple[int, ...], None],
    version2: Union[str, Tuple[int, ...], None],
) -> Optional[Tuple[int, ...]]:
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
