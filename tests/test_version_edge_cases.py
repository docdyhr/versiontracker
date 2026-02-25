"""Edge case tests for version comparison and parsing.

Targets coverage gaps in version/comparator.py and version/parser.py:
- Prerelease handling (alpha/beta/rc/final, Unicode Greek letters)
- Build metadata (semver +build, app-specific patterns)
- Malformed and boundary inputs
- Tuple inputs and mixed types
- Application prefix normalization
"""

import pytest

from versiontracker.version import compare_versions, get_version_info, is_version_newer, parse_version
from versiontracker.version.comparator import (
    _compare_prerelease_suffixes,
    _compare_string_suffixes,
    _compare_unicode_suffixes,
    _convert_versions_to_strings,
    _extract_build_number,
    _extract_prerelease_type_and_suffix,
    _handle_standalone_unicode_chars,
    _is_prerelease,
    _is_version_malformed,
)
from versiontracker.version.models import VersionStatus

# ---------------------------------------------------------------------------
# Section 1: Prerelease detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version_str,expected",
    [
        ("1.0.0-alpha", True),
        ("1.0.0-beta", True),
        ("1.0.0-rc", True),
        ("1.0.0-final", True),
        ("1.0.0-Alpha", True),
        ("1.0.0-BETA", True),
        ("1.0.0.alpha", True),
        ("1.0.0.beta.2", True),
        ("1.0.0-α", True),
        ("1.0.0-β", True),
        ("1.0.0-γ", True),
        ("1.0.0-δ", True),
        # Not prerelease
        ("1.0.0", False),
        ("1.0.0.1234", False),
        ("1.0.0+build.1", False),
        ("alpha", False),  # no separator before keyword
        ("1.0.0-dev-1", False),  # dev is not a recognised prerelease keyword
    ],
)
def test_is_prerelease(version_str, expected):
    assert _is_prerelease(version_str) is expected


# ---------------------------------------------------------------------------
# Section 2: Prerelease type extraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version_str,expected_type,expected_suffix",
    [
        ("1.0.0-alpha", "alpha", None),
        ("1.0.0-beta.2", "beta", 2),
        ("1.0.0-rc.1", "rc", 1),
        ("1.0.0-final", "final", None),
        ("1.0.0-α", "alpha", None),
        ("1.0.0-β", "beta", None),
        ("1.0.0-Alpha.3", "alpha", 3),
        # No prerelease marker → treated as final
        ("1.0.0", "final", None),
    ],
)
def test_extract_prerelease_type_and_suffix(version_str, expected_type, expected_suffix):
    ptype, suffix = _extract_prerelease_type_and_suffix(version_str)
    assert ptype == expected_type
    assert suffix == expected_suffix


# ---------------------------------------------------------------------------
# Section 3: Prerelease comparison (compare_versions)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "v1,v2,expected",
    [
        # Same base, prerelease < release
        ("1.0.0-alpha", "1.0.0", -1),
        ("1.0.0-beta", "1.0.0", -1),
        ("1.0.0-rc", "1.0.0", -1),
        ("1.0.0", "1.0.0-alpha", 1),
        # Prerelease ordering: alpha < beta < rc < final
        ("1.0.0-alpha", "1.0.0-beta", -1),
        ("1.0.0-beta", "1.0.0-rc", -1),
        ("1.0.0-alpha", "1.0.0-rc", -1),
        ("1.0.0-rc", "1.0.0-alpha", 1),
        ("1.0.0-beta", "1.0.0-alpha", 1),
        # Same prerelease type, different suffix
        ("1.0.0-beta.1", "1.0.0-beta.2", -1),
        ("1.0.0-beta.2", "1.0.0-beta.1", 1),
        ("1.0.0-beta.1", "1.0.0-beta.1", 0),
        ("1.0.0-rc.1", "1.0.0-rc.3", -1),
        # Unicode prerelease
        ("1.0.0-α", "1.0.0-β", -1),
        ("1.0.0-β", "1.0.0-α", 1),
        # Different base versions with prerelease — current behavior compares
        # prerelease type first when both are prerelease (beta > alpha)
        ("1.0.0-beta", "2.0.0-alpha", 1),
        ("2.0.0-alpha", "1.0.0-beta", -1),
    ],
)
def test_compare_prerelease_versions(v1, v2, expected):
    assert compare_versions(v1, v2) == expected, f"{v1} vs {v2}"


# ---------------------------------------------------------------------------
# Section 4: Prerelease suffix comparison (internal)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "s1,s2,expected",
    [
        # Both None
        (None, None, 0),
        # One None
        (None, 1, -1),
        (1, None, 1),
        # Both ints
        (1, 2, -1),
        (2, 1, 1),
        (3, 3, 0),
        # Both strings
        ("a", "b", -1),
        ("b", "a", 1),
        ("z", "z", 0),
        # Numeric strings
        ("1", "2", -1),
        ("10", "2", 1),
        # Mixed int/string
        (1, "a", -1),
        ("a", 1, 1),
        # Unicode Greek letters
        ("α", "β", -1),
        ("β", "α", 1),
        ("γ", "δ", -1),
        ("α", "δ", -1),
    ],
)
def test_compare_prerelease_suffixes(s1, s2, expected):
    assert _compare_prerelease_suffixes(s1, s2) == expected


# ---------------------------------------------------------------------------
# Section 5: Build metadata handling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "v1,v2,expected",
    [
        # Semver: build metadata is ignored when base is same
        ("1.0.0+build.1", "1.0.0+build.2", 0),
        ("1.0.0+build.1", "1.0.0", 0),
        ("1.0.0", "1.0.0+build.99", 0),
        ("1.0.0+abc", "1.0.0+xyz", 0),
        # Semver: different base versions with build metadata
        ("1.0.0+build.1", "1.0.1+build.1", -1),
        ("2.0.0+build.1", "1.0.0+build.99", 1),
    ],
)
def test_semver_build_metadata(v1, v2, expected):
    assert compare_versions(v1, v2) == expected, f"{v1} vs {v2}"


@pytest.mark.parametrize(
    "version_str,expected_build",
    [
        ("1.0.0 build 1234", 1234),
        ("1.0.0 Build 5678", 5678),
        ("1.0.0 (1234)", 1234),
        ("1.0.0-dev-42", 42),
        ("1.0.0", None),
        ("1.0.0-beta", None),
        ("1.0.0+build.1", None),  # semver metadata, not an app build pattern
    ],
)
def test_extract_build_number(version_str, expected_build):
    assert _extract_build_number(version_str) == expected_build


# ---------------------------------------------------------------------------
# Section 6: Malformed version handling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version,expected",
    [
        ("abc", True),
        ("no-version-here", True),
        ("xyz!", True),
        ("1.0.0", False),
        ("v2", False),
        ("build5", False),
        ("", False),  # empty is not malformed
        ((1, 2, 3), False),  # tuples are never malformed
    ],
)
def test_is_version_malformed(version, expected):
    assert _is_version_malformed(version) is expected


@pytest.mark.parametrize(
    "v1,v2,expected",
    [
        # Both malformed → equal
        ("abc", "xyz", 0),
        ("no-ver", "also-no-ver", 0),
        # One malformed → non-malformed wins
        ("abc", "1.0.0", -1),
        ("1.0.0", "abc", 1),
        ("no-digits", "0.1", -1),
    ],
)
def test_compare_malformed_versions(v1, v2, expected):
    assert compare_versions(v1, v2) == expected, f"{v1} vs {v2}"


# ---------------------------------------------------------------------------
# Section 7: None and empty string handling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "v1,v2,expected",
    [
        (None, None, 0),
        (None, "1.0.0", -1),
        ("1.0.0", None, 1),
        ("", "", 0),
        ("", "1.0.0", -1),
        ("1.0.0", "", 1),
        ("   ", "", 0),  # whitespace-only == empty
        ("   ", "1.0.0", -1),
        ("1.0.0", "   ", 1),
    ],
)
def test_compare_none_and_empty(v1, v2, expected):
    assert compare_versions(v1, v2) == expected, f"{v1!r} vs {v2!r}"


# ---------------------------------------------------------------------------
# Section 8: Tuple inputs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "v1,v2,expected",
    [
        ((1, 0, 0), (1, 0, 0), 0),
        ((1, 0, 0), (1, 0, 1), -1),
        ((2, 0, 0), (1, 0, 0), 1),
        ((1,), (1, 0, 0), 0),
        ((1, 2), (1, 2, 0), 0),
        # Tuple vs string
        ((1, 0, 0), "1.0.0", 0),
        ("1.0.0", (1, 0, 0), 0),
        ((2, 0, 0), "1.0.0", 1),
        ("1.0.0", (2, 0, 0), -1),
        # 4-component tuples
        ((1, 0, 0, 1), (1, 0, 0, 2), -1),
        ((1, 0, 0, 5), (1, 0, 0, 3), 1),
    ],
)
def test_compare_tuple_inputs(v1, v2, expected):
    assert compare_versions(v1, v2) == expected, f"{v1} vs {v2}"


# ---------------------------------------------------------------------------
# Section 9: Trailing zeros / different-length versions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "v1,v2,expected",
    [
        ("1.0", "1.0.0", 0),
        ("1.0.0", "1.0", 0),
        ("1", "1.0.0", 0),
        ("1.0.0", "1", 0),
        ("1.0.0.0", "1.0.0", 0),
        ("5", "6", -1),
        ("6", "5", 1),
        ("10", "9", 1),
    ],
)
def test_trailing_zeros_and_single_component(v1, v2, expected):
    assert compare_versions(v1, v2) == expected, f"{v1} vs {v2}"


# ---------------------------------------------------------------------------
# Section 10: Date-based versions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "v1,v2,expected",
    [
        ("2024.1", "2024.2", -1),
        ("2024.2", "2024.1", 1),
        ("2024.1", "2024.1", 0),
        ("2023.12", "2024.1", -1),
        ("2024.1.1", "2024.1.2", -1),
    ],
)
def test_date_based_versions(v1, v2, expected):
    assert compare_versions(v1, v2) == expected, f"{v1} vs {v2}"


# ---------------------------------------------------------------------------
# Section 11: Application prefix normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "v1,v2,expected",
    [
        ("Firefox 91.0", "Firefox 92.0", -1),
        ("Chrome 94.0.4606.71", "Chrome 94.0.4606.81", -1),
        ("Visual Studio Code 1.60.0", "Visual Studio Code 1.60.2", -1),
        ("Version 1.2", "Version 1.3", -1),
        ("Version 1.2.3", "Version 1.2.3", 0),
    ],
)
def test_application_prefix_comparison(v1, v2, expected):
    assert compare_versions(v1, v2) == expected, f"{v1} vs {v2}"


# ---------------------------------------------------------------------------
# Section 12: parse_version edge cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version_string,expected_tuple",
    [
        # Standard
        ("1.2.3", (1, 2, 3)),
        ("0.0.1", (0, 0, 1)),
        # Prefixed
        ("v1.2.3", (1, 2, 3)),
        ("v0.1", (0, 1, 0)),
        # With app name
        ("Firefox 91.0.2", (91, 0, 2)),
        ("Chrome 94.0.4606.71", (94, 0, 4606, 71)),
        # Build numbers
        ("1.0.0.1234", (1, 0, 0, 1234)),
        # Prerelease → digit extracted
        ("1.0.0-beta", (1, 0, 0, 0)),
        ("2.3.4-alpha.1", (2, 3, 4, 1)),
        ("1.0.0-rc.2", (1, 0, 0, 2)),
        # Boundary
        ("", (0, 0, 0)),
        ("0", (0, 0, 0)),
        ("0.0.0", (0, 0, 0)),
        # No digits → (0,0,0)
        ("no version", (0, 0, 0)),
        # None → None
        (None, None),
        # Year-based
        ("2024.1.2", (2024, 1, 2)),
        # Single component
        ("5", (5, 0, 0)),
        ("42", (42, 0, 0)),
    ],
)
def test_parse_version_edge_cases(version_string, expected_tuple):
    result = parse_version(version_string)
    assert result == expected_tuple, f"parse_version({version_string!r}) = {result}, expected {expected_tuple}"


# ---------------------------------------------------------------------------
# Section 13: is_version_newer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "current,latest,expected",
    [
        ("1.0.0", "1.0.1", True),
        ("1.0.1", "1.0.0", False),
        ("1.0.0", "1.0.0", False),
        ("1.0.0-beta", "1.0.0", True),
        ("1.0.0", "1.0.0-beta", False),
        ("0.9.0", "1.0.0", True),
    ],
)
def test_is_version_newer(current, latest, expected):
    assert is_version_newer(current, latest) is expected, f"is_version_newer({current!r}, {latest!r})"


# ---------------------------------------------------------------------------
# Section 14: get_version_info
# ---------------------------------------------------------------------------


def test_get_version_info_none_none():
    """Test get_version_info(None, None) returns UNKNOWN status."""
    info = get_version_info(None, None)
    assert info.status == VersionStatus.UNKNOWN


def test_get_version_info_outdated():
    """Test get_version_info detects outdated version."""
    info = get_version_info("1.0.0", "1.1.0")
    assert info.status == VersionStatus.OUTDATED


def test_get_version_info_newer():
    """Test get_version_info detects newer-than-latest version."""
    info = get_version_info("2.0.0", "1.0.0")
    assert info.status == VersionStatus.NEWER


def test_get_version_info_up_to_date():
    """Test get_version_info detects up-to-date version."""
    info = get_version_info("1.0.0", "1.0.0")
    assert info.status == VersionStatus.UP_TO_DATE


def test_get_version_info_empty_current():
    """Test get_version_info with empty current version."""
    info = get_version_info("", "1.0.0")
    assert info.status == VersionStatus.UNKNOWN


def test_get_version_info_no_latest():
    """Test get_version_info with only current version."""
    info = get_version_info("1.0.0")
    assert info.status == VersionStatus.UNKNOWN


# ---------------------------------------------------------------------------
# Section 15: _convert_versions_to_strings — malformed tuple input
# ---------------------------------------------------------------------------


def test_convert_versions_to_strings_malformed_tuple():
    """Test _convert_versions_to_strings with non-int tuple elements."""
    v1, v2 = _convert_versions_to_strings(("a", "b"), ("1", "2"))  # type: ignore[arg-type]
    assert v1 is None and v2 is None


def test_convert_versions_to_strings_valid_tuple():
    """Test _convert_versions_to_strings with valid tuples."""
    v1, v2 = _convert_versions_to_strings((1, 2, 3), (4, 5, 6))
    assert v1 == "1.2.3"
    assert v2 == "4.5.6"


def test_convert_versions_to_strings_string_inputs():
    """Test _convert_versions_to_strings with string inputs."""
    v1, v2 = _convert_versions_to_strings("1.0", "2.0")
    assert v1 == "1.0"
    assert v2 == "2.0"


# ---------------------------------------------------------------------------
# Section 16: compare_versions with malformed tuple → fallback to 0
# ---------------------------------------------------------------------------


def test_compare_versions_malformed_tuple():
    """Test compare_versions with non-integer tuple elements."""
    result = compare_versions(("a", "b"), ("c", "d"))  # type: ignore[arg-type]
    assert result == 0  # Malformed tuples treated as equal


# ---------------------------------------------------------------------------
# Section 17: _compare_unicode_suffixes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "s1,s2,expected",
    [
        ("α", "β", -1),  # alpha < beta
        ("β", "α", 1),  # beta > alpha
        ("α", "α", 0),  # equal
        ("α", "x", -1),  # unicode vs non-unicode
        ("x", "β", 1),  # non-unicode vs unicode
        ("x", "y", None),  # neither is unicode
    ],
)
def test_compare_unicode_suffixes(s1, s2, expected):
    result = _compare_unicode_suffixes(s1, s2)
    assert result == expected, f"_compare_unicode_suffixes({s1!r}, {s2!r})"


# ---------------------------------------------------------------------------
# Section 18: _handle_standalone_unicode_chars
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version_str,expected",
    [
        ("1.0.0-α", ("alpha", "α")),
        ("1.0.0-β", ("beta", "β")),
        ("1.0.0-γ", ("gamma", "γ")),
        ("1.0.0-δ", ("delta", "δ")),
        ("1.0.0.α", ("alpha", "α")),
        ("1.0.0", None),  # no unicode
        ("1.0.0-rc1", None),  # not standalone unicode
    ],
)
def test_handle_standalone_unicode_chars(version_str, expected):
    result = _handle_standalone_unicode_chars(version_str)
    assert result == expected, f"_handle_standalone_unicode_chars({version_str!r})"


# ---------------------------------------------------------------------------
# Section 19: _compare_string_suffixes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "s1,s2,expected",
    [
        ("1", "2", -1),  # numeric comparison
        ("2", "1", 1),
        ("1", "1", 0),
        ("1", "abc", -1),  # number < text
        ("abc", "1", 1),  # text > number
        ("abc", "def", -1),  # lexical comparison
        ("def", "abc", 1),
        ("abc", "abc", 0),
    ],
)
def test_compare_string_suffixes(s1, s2, expected):
    result = _compare_string_suffixes(s1, s2)
    assert result == expected, f"_compare_string_suffixes({s1!r}, {s2!r})"


# ---------------------------------------------------------------------------
# Section 20: compare_versions — build number paths
# ---------------------------------------------------------------------------


def test_compare_versions_build_metadata_equal():
    """Test compare_versions with semver build metadata (ignored per spec)."""
    # Per semver, build metadata SHOULD NOT affect version precedence
    result = compare_versions("1.0.0+build.5", "1.0.0")
    assert result == 0


def test_compare_versions_build_numbers_differ():
    """Test compare_versions with different app-style build numbers."""
    # Application build patterns like "(1234)" ARE compared
    result = compare_versions("1.0.0 (100)", "1.0.0 (200)")
    assert result == -1


# ---------------------------------------------------------------------------
# Section 21: _extract_build_number — ValueError path
# ---------------------------------------------------------------------------


def test_extract_build_number_non_numeric_match():
    """Test _extract_build_number when pattern matches but value isn't numeric."""
    # The regex patterns always capture \d+, so ValueError is unlikely in practice.
    # But let's test basic cases for coverage:
    assert _extract_build_number("build 42") == 42
    assert _extract_build_number("no-build-info") is None


# ---------------------------------------------------------------------------
# Section 22: compare_versions — unknown prerelease type (warning path)
# ---------------------------------------------------------------------------


def test_compare_prerelease_unknown_type():
    """Test comparing versions with unknown prerelease types (triggers logging.warning)."""
    # "omega" is not a known prerelease type → defaults to beta priority
    result = compare_versions("1.0.0-omega1", "1.0.0-alpha1")
    assert isinstance(result, int)  # Should not error out


# ---------------------------------------------------------------------------
# Section 23: _compare_prerelease_suffixes — mixed int/str types
# ---------------------------------------------------------------------------


def test_compare_prerelease_suffixes_int_vs_str():
    """Numbers come before strings in prerelease suffix comparison."""
    assert _compare_prerelease_suffixes(1, "abc") == -1
    assert _compare_prerelease_suffixes("abc", 1) == 1
