"""Tests for versiontracker.version.utils module.

Covers compose_version_tuple, decompose_version, get_compiled_pattern,
version_tuple_to_dict, dict_to_version_tuple, normalize_version_string,
format_version_tuple, pad_version_tuple, and module-level pattern constants.
"""

import re

from versiontracker.version.utils import (
    VERSION_PATTERN_DICT,
    VERSION_PATTERNS,
    compose_version_tuple,
    decompose_version,
    dict_to_version_tuple,
    format_version_tuple,
    get_compiled_pattern,
    normalize_version_string,
    pad_version_tuple,
    version_tuple_to_dict,
)


class TestComposeVersionTuple:
    """Tests for compose_version_tuple."""

    def test_three_components(self):
        """Test composing a standard 3-part version tuple."""
        assert compose_version_tuple(1, 2, 3) == (1, 2, 3)

    def test_four_components(self):
        """Test composing a 4-part version tuple with build number."""
        assert compose_version_tuple(1, 0, 0, 456) == (1, 0, 0, 456)

    def test_single_component(self):
        """Test composing a single-component version tuple."""
        assert compose_version_tuple(5) == (5,)

    def test_no_components(self):
        """Test composing with no arguments returns an empty tuple."""
        assert compose_version_tuple() == ()

    def test_large_numbers(self):
        """Test composing with large version numbers."""
        assert compose_version_tuple(100, 200, 300) == (100, 200, 300)

    def test_zeros(self):
        """Test composing with all zero components."""
        assert compose_version_tuple(0, 0, 0) == (0, 0, 0)


class TestDecomposeVersion:
    """Tests for decompose_version."""

    def test_semantic_version(self):
        """Test decomposing a standard semantic version string."""
        result = decompose_version("1.2.3")
        assert result == {"major": 1, "minor": 2, "patch": 3, "build": 0}

    def test_two_part_version(self):
        """Test decomposing a two-part version string."""
        result = decompose_version("1.0")
        assert result is not None
        assert result["major"] == 1
        assert result["minor"] == 0
        assert result["patch"] == 0
        assert result["build"] == 0

    def test_single_number_version(self):
        """Test decomposing a single number version string."""
        result = decompose_version("5")
        assert result is not None
        assert result["major"] == 5

    def test_four_part_version(self):
        """Test decomposing a four-part version string with build number."""
        result = decompose_version("1.2.3.4")
        assert result is not None
        assert result["major"] == 1
        assert result["minor"] == 2
        assert result["patch"] == 3
        assert result["build"] == 4

    def test_none_input(self):
        """Test that None input returns None."""
        assert decompose_version(None) is None

    def test_empty_string(self):
        """Test that empty string returns all-zero dict."""
        result = decompose_version("")
        assert result == {"major": 0, "minor": 0, "patch": 0, "build": 0}

    def test_result_keys(self):
        """Test that the result contains exactly the expected keys."""
        result = decompose_version("1.2.3")
        assert result is not None
        assert set(result.keys()) == {"major", "minor", "patch", "build"}

    def test_version_with_v_prefix(self):
        """Test decomposing a version string with v prefix."""
        result = decompose_version("v1.2.3")
        assert result is not None
        assert result["major"] == 1
        assert result["minor"] == 2
        assert result["patch"] == 3


class TestGetCompiledPattern:
    """Tests for get_compiled_pattern."""

    def test_valid_pattern(self):
        """Test compiling a valid regex pattern."""
        pattern = get_compiled_pattern(r"^(\d+)\.(\d+)$")
        assert pattern is not None
        assert isinstance(pattern, re.Pattern)

    def test_valid_pattern_matches(self):
        """Test that compiled pattern actually works for matching."""
        pattern = get_compiled_pattern(r"^(\d+)\.(\d+)$")
        assert pattern is not None
        match = pattern.match("1.2")
        assert match is not None
        assert match.group(1) == "1"
        assert match.group(2) == "2"

    def test_invalid_pattern_returns_none(self):
        """Test that an invalid regex returns None."""
        result = get_compiled_pattern("[invalid")
        assert result is None

    def test_another_invalid_pattern(self):
        """Test another invalid regex pattern returns None."""
        result = get_compiled_pattern("(unclosed")
        assert result is None

    def test_empty_pattern(self):
        """Test compiling an empty string pattern succeeds."""
        pattern = get_compiled_pattern("")
        assert pattern is not None

    def test_complex_pattern(self):
        """Test compiling a complex version regex."""
        pattern = get_compiled_pattern(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?$")
        assert pattern is not None
        assert pattern.match("1.2.3") is not None
        assert pattern.match("1.2.3-beta.1") is not None


class TestVersionTupleToDict:
    """Tests for version_tuple_to_dict."""

    def test_three_element_tuple(self):
        """Test converting a 3-element tuple to dict."""
        result = version_tuple_to_dict((1, 2, 3))
        assert result == {"major": 1, "minor": 2, "patch": 3, "build": 0}

    def test_four_element_tuple(self):
        """Test converting a 4-element tuple to dict."""
        result = version_tuple_to_dict((1, 2, 3, 4))
        assert result == {"major": 1, "minor": 2, "patch": 3, "build": 4}

    def test_single_element_tuple(self):
        """Test converting a single-element tuple to dict."""
        result = version_tuple_to_dict((5,))
        assert result == {"major": 5, "minor": 0, "patch": 0, "build": 0}

    def test_empty_tuple(self):
        """Test converting an empty tuple to dict."""
        result = version_tuple_to_dict(())
        assert result == {"major": 0, "minor": 0, "patch": 0, "build": 0}

    def test_two_element_tuple(self):
        """Test converting a 2-element tuple to dict."""
        result = version_tuple_to_dict((3, 7))
        assert result == {"major": 3, "minor": 7, "patch": 0, "build": 0}

    def test_result_has_expected_keys(self):
        """Test that result always has exactly four keys."""
        result = version_tuple_to_dict((1,))
        assert set(result.keys()) == {"major", "minor", "patch", "build"}


class TestDictToVersionTuple:
    """Tests for dict_to_version_tuple."""

    def test_full_dict(self):
        """Test converting a full version dict to tuple."""
        result = dict_to_version_tuple({"major": 1, "minor": 2, "patch": 3, "build": 4})
        assert result == (1, 2, 3, 4)

    def test_partial_dict_missing_build(self):
        """Test converting a dict without build key."""
        result = dict_to_version_tuple({"major": 1, "minor": 2, "patch": 3})
        assert result == (1, 2, 3, 0)

    def test_empty_dict(self):
        """Test converting an empty dict defaults to all zeros."""
        result = dict_to_version_tuple({})
        assert result == (0, 0, 0, 0)

    def test_always_returns_four_elements(self):
        """Test that the result always has exactly four elements."""
        result = dict_to_version_tuple({"major": 5})
        assert len(result) == 4
        assert result == (5, 0, 0, 0)

    def test_string_values_converted_to_int(self):
        """Test that string values in the dict are converted to int."""
        result = dict_to_version_tuple({"major": "2", "minor": "5", "patch": "1", "build": "0"})
        assert result == (2, 5, 1, 0)

    def test_roundtrip_with_version_tuple_to_dict(self):
        """Test roundtrip conversion tuple -> dict -> tuple."""
        original = (1, 2, 3, 0)
        d = version_tuple_to_dict(original)
        result = dict_to_version_tuple(d)
        assert result == original


class TestNormalizeVersionString:
    """Tests for normalize_version_string."""

    def test_strip_lowercase_v(self):
        """Test stripping lowercase v prefix."""
        assert normalize_version_string("v1.2.3") == "1.2.3"

    def test_strip_uppercase_v(self):
        """Test stripping uppercase V prefix."""
        assert normalize_version_string("V1.2.3") == "1.2.3"

    def test_strip_version_prefix(self):
        """Test stripping 'Version ' prefix."""
        assert normalize_version_string("Version 1.2.3") == "1.2.3"

    def test_strip_version_prefix_lowercase(self):
        """Test stripping 'version ' prefix."""
        assert normalize_version_string("version 1.2.3") == "1.2.3"

    def test_strip_app_name_firefox(self):
        """Test stripping Firefox application name."""
        assert normalize_version_string("Firefox 100.0") == "100.0"

    def test_strip_app_name_chrome(self):
        """Test stripping Chrome application name."""
        assert normalize_version_string("Chrome 120.0.1") == "120.0.1"

    def test_strip_app_name_google_chrome(self):
        """Test stripping Google Chrome application name."""
        assert normalize_version_string("Google Chrome 120.0.1") == "120.0.1"

    def test_strip_generic_app_name(self):
        """Test stripping a generic application name prefix."""
        assert normalize_version_string("MyApp 2.0.0") == "2.0.0"

    def test_plain_version_unchanged(self):
        """Test that a plain version string is returned unchanged."""
        assert normalize_version_string("1.2.3") == "1.2.3"

    def test_whitespace_stripped(self):
        """Test that leading/trailing whitespace is stripped."""
        result = normalize_version_string("  1.2.3  ")
        assert result == "1.2.3"


class TestFormatVersionTuple:
    """Tests for format_version_tuple."""

    def test_default_separator(self):
        """Test formatting with default dot separator."""
        assert format_version_tuple((1, 2, 3)) == "1.2.3"

    def test_four_part_version(self):
        """Test formatting a 4-part version tuple."""
        assert format_version_tuple((1, 0, 0, 123)) == "1.0.0.123"

    def test_custom_separator(self):
        """Test formatting with a custom separator."""
        assert format_version_tuple((1, 2, 3), separator="-") == "1-2-3"

    def test_single_element(self):
        """Test formatting a single-element tuple."""
        assert format_version_tuple((5,)) == "5"

    def test_empty_tuple(self):
        """Test formatting an empty tuple returns empty string."""
        assert format_version_tuple(()) == ""

    def test_underscore_separator(self):
        """Test formatting with underscore separator."""
        assert format_version_tuple((2, 0, 1), separator="_") == "2_0_1"


class TestPadVersionTuple:
    """Tests for pad_version_tuple."""

    def test_pad_single_to_three(self):
        """Test padding a single-element tuple to length 3."""
        assert pad_version_tuple((1,), 3) == (1, 0, 0)

    def test_pad_two_to_four(self):
        """Test padding a two-element tuple to length 4."""
        assert pad_version_tuple((1, 2), 4) == (1, 2, 0, 0)

    def test_no_padding_needed(self):
        """Test that a tuple of exact length is unchanged."""
        assert pad_version_tuple((1, 2, 3), 3) == (1, 2, 3)

    def test_truncate_longer_tuple(self):
        """Test that a longer tuple is truncated to the specified length."""
        assert pad_version_tuple((1, 2, 3, 4), 3) == (1, 2, 3)

    def test_default_length_is_three(self):
        """Test that default padding length is 3."""
        assert pad_version_tuple((1,)) == (1, 0, 0)

    def test_custom_pad_value(self):
        """Test padding with a custom pad value."""
        assert pad_version_tuple((1,), 3, pad_value=9) == (1, 9, 9)

    def test_pad_empty_tuple(self):
        """Test padding an empty tuple."""
        assert pad_version_tuple((), 3) == (0, 0, 0)

    def test_pad_to_length_one(self):
        """Test padding/truncating to length 1."""
        assert pad_version_tuple((5, 6, 7), 1) == (5,)

    def test_pad_to_zero_length(self):
        """Test truncating to length 0 returns empty tuple."""
        assert pad_version_tuple((1, 2, 3), 0) == ()


class TestModuleLevelPatterns:
    """Tests for VERSION_PATTERNS and VERSION_PATTERN_DICT module-level constants."""

    def test_version_patterns_is_list(self):
        """Test that VERSION_PATTERNS is a list."""
        assert isinstance(VERSION_PATTERNS, list)

    def test_version_patterns_contains_compiled_regexes(self):
        """Test that all items in VERSION_PATTERNS are compiled regex patterns."""
        for pattern in VERSION_PATTERNS:
            assert isinstance(pattern, re.Pattern)

    def test_version_patterns_not_empty(self):
        """Test that VERSION_PATTERNS has at least one pattern."""
        assert len(VERSION_PATTERNS) > 0

    def test_version_pattern_dict_is_dict(self):
        """Test that VERSION_PATTERN_DICT is a dict."""
        assert isinstance(VERSION_PATTERN_DICT, dict)

    def test_version_pattern_dict_has_expected_keys(self):
        """Test that VERSION_PATTERN_DICT has the known named patterns."""
        assert "semantic" in VERSION_PATTERN_DICT
        assert "simple" in VERSION_PATTERN_DICT
        assert "single" in VERSION_PATTERN_DICT
        assert "build" in VERSION_PATTERN_DICT

    def test_version_pattern_dict_values_are_compiled(self):
        """Test that all values in VERSION_PATTERN_DICT are compiled patterns."""
        for value in VERSION_PATTERN_DICT.values():
            assert isinstance(value, re.Pattern)

    def test_semantic_pattern_matches(self):
        """Test that the semantic pattern matches a standard semver string."""
        pattern = VERSION_PATTERN_DICT["semantic"]
        assert pattern.match("1.2.3") is not None
        assert pattern.match("1.2.3-beta.1") is not None

    def test_simple_pattern_matches(self):
        """Test that the simple pattern matches a two-part version."""
        pattern = VERSION_PATTERN_DICT["simple"]
        assert pattern.match("1.2") is not None
        assert pattern.match("1.2.3") is None

    def test_single_pattern_matches(self):
        """Test that the single pattern matches a standalone number."""
        pattern = VERSION_PATTERN_DICT["single"]
        assert pattern.match("5") is not None
        assert pattern.match("1.2") is None

    def test_build_pattern_matches(self):
        """Test that the build pattern matches a four-part version."""
        pattern = VERSION_PATTERN_DICT["build"]
        assert pattern.match("1.2.3.4") is not None
        assert pattern.match("1.2.3") is None
