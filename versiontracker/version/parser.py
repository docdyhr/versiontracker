"""Version parsing functionality."""

import re
from typing import List, Optional, Tuple


def _clean_version_string(version_str: str) -> str:
    """Clean version string by removing prefixes and app names."""
    # Remove common prefixes like "v" or "Version "
    cleaned = re.sub(r"^[vV]ersion\s+", "", version_str)
    cleaned = re.sub(r"^[vV](?:er\.?\s*)?", "", cleaned)

    # Handle application names at the beginning
    cleaned = re.sub(r"^(?:Google\s+)?(?:Chrome|Firefox|Safari)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^[a-zA-Z]+\s+(?=\d)", "", cleaned)

    return cleaned


def _extract_build_metadata(cleaned: str) -> Tuple[Optional[int], str]:
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


def _handle_special_beta_format(version_str: str) -> Optional[Tuple[int, ...]]:
    """Handle special format like '1.2.3.beta4'."""
    special_beta_format = re.search(r"\d+\.\d+\.\d+\.[a-zA-Z]+\d+", version_str)
    if special_beta_format:
        all_numbers = re.findall(r"\d+", version_str)
        if len(all_numbers) >= 4:
            parts = [int(num) for num in all_numbers[:4]]
            return tuple(parts)
    return None


def _extract_prerelease_info(cleaned: str, version_str: str) -> Tuple[bool, Optional[int], bool, str]:
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


def _parse_numeric_parts(cleaned: str) -> List[int]:
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
    parts: List[int],
    has_prerelease: bool,
    prerelease_num: Optional[int],
    has_text_suffix: bool,
    build_metadata: Optional[int],
    version_str: str,
) -> Tuple[int, ...]:
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


def _is_multi_component_version(parts: List[int], has_prerelease: bool, build_metadata: Optional[int]) -> bool:
    """Check if this is a 4+ component version without special suffixes."""
    return len(parts) >= 4 and not has_prerelease and build_metadata is None


def _build_with_metadata(parts: List[int], build_metadata: int) -> Tuple[int, ...]:
    """Build version tuple with build metadata."""
    padded_parts = _normalize_to_three_components(parts)
    return padded_parts[:3] + (build_metadata,)


def _is_mixed_format(version_str: str, parts: List[int]) -> bool:
    """Check if version uses mixed format like '1.beta.0'."""
    original_str = version_str.lower()
    has_keywords = any(k in original_str for k in ["beta", "alpha", "rc"])
    has_pattern = re.search(r"\d+\.[a-zA-Z]+\.\d+", version_str)
    return has_keywords and len(parts) >= 2 and has_pattern is not None


def _handle_mixed_format(parts: List[int]) -> Tuple[int, ...]:
    """Handle mixed format versions."""
    return (parts[0], 0, parts[-1])


def _build_prerelease_tuple(
    parts: List[int],
    prerelease_num: Optional[int],
    has_text_suffix: bool,
    version_str: str,
) -> Tuple[int, ...]:
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


def _normalize_to_three_components(parts: List[int]) -> Tuple[int, ...]:
    """Ensure version has at least 3 components."""
    result = parts.copy()
    while len(result) < 3:
        result.append(0)
    return tuple(result)


def parse_version(version_string: Optional[str]) -> Optional[Tuple[int, ...]]:
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
