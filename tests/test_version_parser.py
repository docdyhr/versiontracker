"""Tests for versiontracker.version.parser."""

import pytest

from versiontracker.version.parser import (
    _build_final_version_tuple,
    _build_prerelease_tuple,
    _build_with_metadata,
    _clean_version_string,
    _extract_build_metadata,
    _extract_prerelease_info,
    _handle_mixed_format,
    _handle_special_beta_format,
    _is_mixed_format,
    _is_multi_component_version,
    _normalize_to_three_components,
    _parse_numeric_parts,
    parse_version,
)

# ---------------------------------------------------------------------------
# parse_version — main public API
# ---------------------------------------------------------------------------


class TestParseVersionNoneAndEmpty:
    def test_none_returns_none(self):
        assert parse_version(None) is None

    def test_empty_string_returns_zero_tuple(self):
        assert parse_version("") == (0, 0, 0)

    def test_whitespace_only_returns_zero_tuple(self):
        assert parse_version("   ") == (0, 0, 0)


class TestParseVersionNormal:
    @pytest.mark.parametrize(
        "version_str, expected",
        [
            ("1.2.3", (1, 2, 3)),
            ("1.0.0", (1, 0, 0)),
            ("0.0.1", (0, 0, 1)),
            ("10.20.30", (10, 20, 30)),
            ("100.200.300", (100, 200, 300)),
        ],
    )
    def test_three_component_versions(self, version_str, expected):
        assert parse_version(version_str) == expected

    @pytest.mark.parametrize(
        "version_str, expected",
        [
            ("1.2", (1, 2, 0)),
            ("1.0", (1, 0, 0)),
            ("10.5", (10, 5, 0)),
        ],
    )
    def test_two_component_versions_padded(self, version_str, expected):
        assert parse_version(version_str) == expected

    @pytest.mark.parametrize(
        "version_str, expected",
        [
            ("1", (1, 0, 0)),
            ("42", (42, 0, 0)),
        ],
    )
    def test_single_component_padded(self, version_str, expected):
        assert parse_version(version_str) == expected

    def test_four_component_version(self):
        result = parse_version("1.2.3.4")
        assert result == (1, 2, 3, 4)

    def test_five_component_version(self):
        result = parse_version("1.2.3.4.5")
        assert result == (1, 2, 3, 4, 5)


class TestParseVersionPrefixes:
    @pytest.mark.parametrize(
        "version_str, expected",
        [
            ("v1.2.3", (1, 2, 3)),
            ("V1.2.3", (1, 2, 3)),
            ("v2.0.0", (2, 0, 0)),
            ("Version 1.2.3", (1, 2, 3)),
            ("version 1.2.3", (1, 2, 3)),
            ("ver.1.2.3", (1, 2, 3)),
        ],
    )
    def test_version_prefix_stripped(self, version_str, expected):
        assert parse_version(version_str) == expected


class TestParseVersionPrerelease:
    @pytest.mark.parametrize(
        "version_str",
        [
            "1.2.3-alpha",
            "1.2.3-beta",
            "1.2.3-rc",
        ],
    )
    def test_prerelease_suffix_produces_valid_tuple(self, version_str):
        result = parse_version(version_str)
        assert result is not None
        assert result[0] == 1
        assert result[1] == 2
        assert result[2] == 3

    def test_beta_with_number(self):
        result = parse_version("1.2.3-beta2")
        assert result is not None
        assert result[:3] == (1, 2, 3)
        assert result[3] == 2

    def test_rc_with_number(self):
        result = parse_version("2.0.0-rc1")
        assert result is not None
        assert result[:3] == (2, 0, 0)

    def test_alpha_with_number(self):
        result = parse_version("1.0.0-alpha3")
        assert result is not None
        assert result[:3] == (1, 0, 0)


class TestParseVersionBuildMetadata:
    def test_semver_build_metadata(self):
        result = parse_version("1.2.3+build456")
        assert result is not None
        assert result[0] == 1
        assert result[1] == 2
        assert result[2] == 3

    def test_build_keyword(self):
        result = parse_version("1.2.3 build 100")
        assert result is not None
        assert result[:3] == (1, 2, 3)

    def test_parenthesised_build_number(self):
        result = parse_version("1.2.3 (456)")
        assert result is not None
        assert result[:3] == (1, 2, 3)


class TestParseVersionSpecialFormats:
    def test_special_beta_dot_format(self):
        result = parse_version("1.2.3.beta4")
        assert result is not None
        assert len(result) == 4
        assert result[0] == 1

    def test_mixed_format_1_beta_0(self):
        result = parse_version("1.beta.0")
        assert result is not None
        assert result[0] == 1

    def test_date_style_version(self):
        result = parse_version("2024.01.15")
        assert result == (2024, 1, 15)

    def test_application_name_prefix_chrome(self):
        result = parse_version("Chrome 120.0.6099.130")
        assert result is not None
        assert result[0] == 120

    def test_underscore_separator(self):
        result = parse_version("1_2_3")
        assert result is not None
        assert result[:3] == (1, 2, 3)


class TestParseVersionEdgeCases:
    def test_whitespace_stripped(self):
        assert parse_version("  1.2.3  ") == (1, 2, 3)

    def test_very_large_numbers(self):
        result = parse_version("999999.888888.777777")
        assert result == (999999, 888888, 777777)

    def test_leading_zeros_in_parts(self):
        result = parse_version("1.02.003")
        assert result is not None
        assert result[0] == 1

    def test_string_with_only_letters_returns_zero_tuple(self):
        result = parse_version("notaversion")
        assert result == (0, 0, 0)

    def test_dash_separator(self):
        result = parse_version("1-2-3")
        assert result is not None
        assert result[0] == 1


# ---------------------------------------------------------------------------
# _clean_version_string
# ---------------------------------------------------------------------------


class TestCleanVersionString:
    @pytest.mark.parametrize(
        "raw, expected_start",
        [
            ("v1.2.3", "1.2.3"),
            ("V1.2.3", "1.2.3"),
            ("Version 1.2.3", "1.2.3"),
            ("ver.1.2.3", "1.2.3"),
            ("1.2.3", "1.2.3"),
        ],
    )
    def test_removes_prefix(self, raw, expected_start):
        assert _clean_version_string(raw).startswith(expected_start)

    def test_chrome_prefix_removed(self):
        cleaned = _clean_version_string("Chrome 120.0.1")
        assert "Chrome" not in cleaned

    def test_firefox_prefix_removed(self):
        cleaned = _clean_version_string("Firefox 120.0")
        assert "Firefox" not in cleaned

    def test_plain_version_unchanged(self):
        assert _clean_version_string("1.2.3") == "1.2.3"


# ---------------------------------------------------------------------------
# _extract_build_metadata
# ---------------------------------------------------------------------------


class TestExtractBuildMetadata:
    def test_semver_plus_notation(self):
        metadata, cleaned = _extract_build_metadata("1.2.3+456")
        assert metadata == 456
        assert "+" not in cleaned

    def test_build_keyword(self):
        metadata, cleaned = _extract_build_metadata("1.2.3 build 789")
        assert metadata == 789

    def test_parenthesised_number(self):
        metadata, cleaned = _extract_build_metadata("1.2.3 (100)")
        assert metadata == 100

    def test_dev_build(self):
        metadata, cleaned = _extract_build_metadata("1.2.3-dev-42")
        assert metadata == 42

    def test_no_metadata(self):
        metadata, cleaned = _extract_build_metadata("1.2.3")
        assert metadata is None
        assert cleaned == "1.2.3"


# ---------------------------------------------------------------------------
# _handle_special_beta_format
# ---------------------------------------------------------------------------


class TestHandleSpecialBetaFormat:
    def test_dot_beta_format(self):
        result = _handle_special_beta_format("1.2.3.beta4")
        assert result is not None
        assert result[0] == 1

    def test_no_special_format_returns_none(self):
        assert _handle_special_beta_format("1.2.3") is None
        assert _handle_special_beta_format("1.2.3-beta4") is None

    def test_too_few_numbers_returns_none(self):
        assert _handle_special_beta_format("1.2.beta3") is None


# ---------------------------------------------------------------------------
# _extract_prerelease_info
# ---------------------------------------------------------------------------


class TestExtractPrereleaseInfo:
    def test_beta_suffix(self):
        has_pre, pre_num, has_text, cleaned = _extract_prerelease_info("1.2.3-beta", "1.2.3-beta")
        assert has_pre is True

    def test_alpha_with_number(self):
        has_pre, pre_num, has_text, cleaned = _extract_prerelease_info("1.2.3-alpha2", "1.2.3-alpha2")
        assert has_pre is True
        assert pre_num == 2

    def test_rc_suffix(self):
        has_pre, pre_num, has_text, cleaned = _extract_prerelease_info("1.2.3-rc", "1.2.3-rc")
        assert has_pre is True

    def test_no_prerelease(self):
        has_pre, pre_num, has_text, cleaned = _extract_prerelease_info("1.2.3", "1.2.3")
        assert has_pre is False
        assert pre_num is None

    def test_prerelease_removed_from_cleaned(self):
        _, _, _, cleaned = _extract_prerelease_info("1.2.3-beta", "1.2.3-beta")
        assert "beta" not in cleaned


# ---------------------------------------------------------------------------
# _parse_numeric_parts
# ---------------------------------------------------------------------------


class TestParseNumericParts:
    def test_standard_version(self):
        assert _parse_numeric_parts("1.2.3") == [1, 2, 3]

    def test_dash_separator_normalised(self):
        assert _parse_numeric_parts("1-2-3") == [1, 2, 3]

    def test_underscore_separator_normalised(self):
        assert _parse_numeric_parts("1_2_3") == [1, 2, 3]

    def test_empty_string_returns_empty(self):
        assert _parse_numeric_parts("") == []

    def test_no_digits_returns_empty(self):
        assert _parse_numeric_parts("abc") == []

    def test_mixed_content(self):
        parts = _parse_numeric_parts("1.2.3.extra")
        assert 1 in parts and 2 in parts and 3 in parts


# ---------------------------------------------------------------------------
# _normalize_to_three_components
# ---------------------------------------------------------------------------


class TestNormalizeToThreeComponents:
    def test_already_three(self):
        assert _normalize_to_three_components([1, 2, 3]) == (1, 2, 3)

    def test_two_components_padded(self):
        assert _normalize_to_three_components([1, 2]) == (1, 2, 0)

    def test_one_component_padded(self):
        assert _normalize_to_three_components([5]) == (5, 0, 0)

    def test_more_than_three_kept(self):
        result = _normalize_to_three_components([1, 2, 3, 4])
        assert result == (1, 2, 3, 4)

    def test_empty_padded(self):
        assert _normalize_to_three_components([]) == (0, 0, 0)


# ---------------------------------------------------------------------------
# _is_multi_component_version
# ---------------------------------------------------------------------------


class TestIsMultiComponentVersion:
    def test_four_parts_no_prerelease_no_metadata(self):
        assert _is_multi_component_version([1, 2, 3, 4], False, None) is True

    def test_three_parts_is_not_multi(self):
        assert _is_multi_component_version([1, 2, 3], False, None) is False

    def test_four_parts_with_prerelease_is_not_multi(self):
        assert _is_multi_component_version([1, 2, 3, 4], True, None) is False

    def test_four_parts_with_metadata_is_not_multi(self):
        assert _is_multi_component_version([1, 2, 3, 4], False, 42) is False


# ---------------------------------------------------------------------------
# _build_with_metadata
# ---------------------------------------------------------------------------


class TestBuildWithMetadata:
    def test_appends_metadata_as_fourth_element(self):
        result = _build_with_metadata([1, 2, 3], 99)
        assert result == (1, 2, 3, 99)

    def test_short_parts_padded_first(self):
        result = _build_with_metadata([1, 2], 50)
        assert result == (1, 2, 0, 50)


# ---------------------------------------------------------------------------
# _is_mixed_format
# ---------------------------------------------------------------------------


class TestIsMixedFormat:
    def test_1_beta_0_is_mixed(self):
        assert _is_mixed_format("1.beta.0", [1, 0]) is True

    def test_plain_version_is_not_mixed(self):
        assert _is_mixed_format("1.2.3", [1, 2, 3]) is False

    def test_beta_without_surrounding_dots_not_mixed(self):
        assert _is_mixed_format("1.2.3-beta", [1, 2, 3]) is False


# ---------------------------------------------------------------------------
# _handle_mixed_format
# ---------------------------------------------------------------------------


class TestHandleMixedFormat:
    def test_two_parts(self):
        assert _handle_mixed_format([1, 0]) == (1, 0, 0)

    def test_three_parts_uses_first_and_last(self):
        result = _handle_mixed_format([2, 99, 1])
        assert result == (2, 0, 1)


# ---------------------------------------------------------------------------
# _build_prerelease_tuple
# ---------------------------------------------------------------------------


class TestBuildPrereleaseTuple:
    def test_with_prerelease_number(self):
        result = _build_prerelease_tuple([1, 2, 3], 2, False, "1.2.3-beta2")
        assert result == (1, 2, 3, 2)

    def test_with_text_suffix(self):
        result = _build_prerelease_tuple([1, 2, 3], None, True, "1.2.3-beta")
        assert result == (1, 2, 3)

    def test_without_prerelease_num_three_original_components(self):
        result = _build_prerelease_tuple([1, 2, 3], None, False, "1.2.3-rc")
        assert result == (1, 2, 3, 0)

    def test_without_prerelease_num_two_original_components(self):
        result = _build_prerelease_tuple([1, 2], None, False, "1.2-rc")
        assert result == (1, 2, 0)


# ---------------------------------------------------------------------------
# _build_final_version_tuple
# ---------------------------------------------------------------------------


class TestBuildFinalVersionTuple:
    def test_empty_parts_returns_zero(self):
        assert _build_final_version_tuple([], False, None, False, None, "") == (0, 0, 0)

    def test_normal_three_parts(self):
        assert _build_final_version_tuple([1, 2, 3], False, None, False, None, "1.2.3") == (1, 2, 3)

    def test_four_parts_no_extras(self):
        result = _build_final_version_tuple([1, 2, 3, 4], False, None, False, None, "1.2.3.4")
        assert result == (1, 2, 3, 4)

    def test_with_build_metadata(self):
        result = _build_final_version_tuple([1, 2, 3], False, None, False, 99, "1.2.3+99")
        assert result[:3] == (1, 2, 3)
        assert result[3] == 99

    def test_with_prerelease_number(self):
        result = _build_final_version_tuple([1, 2, 3], True, 2, False, None, "1.2.3-beta2")
        assert result[:3] == (1, 2, 3)
        assert result[3] == 2
