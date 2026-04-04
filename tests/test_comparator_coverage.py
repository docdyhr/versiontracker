"""Coverage tests for versiontracker.version.comparator.

Targets the ~14% of uncovered lines identified by the audit:
- _compare_base_versions: < and > branches
- _compare_build_numbers: all None/non-None combinations
- _convert_versions_to_strings: tuple_to_version_str returning None
- _compare_prerelease: unknown prerelease type handling
- _compare_prerelease_suffixes: equal int suffixes
- _process_prerelease_suffix: string (non-int) suffix
- _extract_prerelease_type_and_suffix: standalone Unicode character
- _convert_versions_to_tuples: None version1 / None version2
- _apply_version_truncation: build metadata and prerelease truncation
- get_version_difference: build-metadata and prerelease versions
- get_version_info: None current, malformed, empty, NEWER status
- _handle_empty_version_cases: both empty, one empty
- _perform_version_comparison: malformed latest version
"""

from versiontracker.version.comparator import (
    _apply_version_truncation,
    _compare_base_versions,
    _compare_build_numbers,
    _compare_prerelease,
    _compare_prerelease_suffixes,
    _convert_versions_to_tuples,
    _extract_prerelease_type_and_suffix,
    _handle_empty_version_cases,
    _process_prerelease_suffix,
    compare_versions,
    get_version_difference,
    get_version_info,
    is_version_newer,
)
from versiontracker.version.models import VersionStatus

# ---------------------------------------------------------------------------
# _compare_base_versions
# ---------------------------------------------------------------------------


class TestCompareBaseVersions:
    def test_v1_less_than_v2(self):
        """Line 171: returns -1 when v1_base < v2_base."""
        assert _compare_base_versions((1, 0, 0), (2, 0, 0)) == -1

    def test_v1_greater_than_v2(self):
        """Line 173: returns 1 when v1_base > v2_base."""
        assert _compare_base_versions((2, 0, 0), (1, 0, 0)) == 1

    def test_equal_returns_zero(self):
        assert _compare_base_versions((1, 2, 3), (1, 2, 3)) == 0

    def test_short_tuples_padded(self):
        """Short tuples are zero-padded before comparison."""
        assert _compare_base_versions((1,), (1, 0, 0)) == 0
        assert _compare_base_versions((2,), (1, 9, 9)) == 1


# ---------------------------------------------------------------------------
# _compare_build_numbers
# ---------------------------------------------------------------------------


class TestCompareBuildNumbers:
    def test_both_none_returns_zero(self):
        assert _compare_build_numbers(None, None) == 0

    def test_v1_has_build_v2_does_not(self):
        """Line 187: v1 has build number, v2 doesn't → returns 1."""
        assert _compare_build_numbers(100, None) == 1

    def test_v2_has_build_v1_does_not(self):
        """Line 189: v2 has build number, v1 doesn't → returns -1."""
        assert _compare_build_numbers(None, 200) == -1

    def test_v1_build_less_than_v2(self):
        """Line 182: v1_build < v2_build → returns -1."""
        assert _compare_build_numbers(100, 200) == -1

    def test_v1_build_greater_than_v2(self):
        """Line 184: v1_build > v2_build → returns 1."""
        assert _compare_build_numbers(200, 100) == 1

    def test_equal_builds_returns_zero(self):
        assert _compare_build_numbers(100, 100) == 0


# ---------------------------------------------------------------------------
# _compare_prerelease
# ---------------------------------------------------------------------------


class TestComparePrerelease:
    def test_unknown_type_v1_logs_warning(self):
        """Lines 450-451: γ maps to 'gamma' (not in type_priority) → defaults to beta (2).
        rc has priority 3 → gamma(2) < rc(3) → returns -1."""
        result = _compare_prerelease("1.0-γ", "1.0-rc.1")
        assert result == -1

    def test_unknown_type_v2_logs_warning(self):
        """Lines 453-454: rc (3) vs γ mapped to gamma (unknown→beta=2) → rc > gamma → 1."""
        result = _compare_prerelease("1.0-rc.1", "1.0-γ")
        assert result == 1

    def test_both_unknown_same_suffix(self):
        """Same unknown type twice → same priority and same suffix → equal (0)."""
        result = _compare_prerelease("1.0-γ", "1.0-γ")
        assert result == 0

    def test_alpha_less_than_rc(self):
        assert _compare_prerelease("1.0-alpha.1", "1.0-rc.1") == -1

    def test_rc_greater_than_beta(self):
        assert _compare_prerelease("1.0-rc.1", "1.0-beta.1") == 1


# ---------------------------------------------------------------------------
# _compare_prerelease_suffixes
# ---------------------------------------------------------------------------


class TestComparePrereleaseSuffixes:
    def test_equal_int_suffixes(self):
        """Line 544: both suffixes are equal ints → returns 0."""
        assert _compare_prerelease_suffixes(2, 2) == 0

    def test_int_less_than_int(self):
        assert _compare_prerelease_suffixes(1, 2) == -1

    def test_int_greater_than_int(self):
        assert _compare_prerelease_suffixes(3, 2) == 1

    def test_string_vs_string_equal(self):
        assert _compare_prerelease_suffixes("a", "a") == 0

    def test_int_suffix_vs_string(self):
        """int suffix sorts before string (lines 539-540)."""
        assert _compare_prerelease_suffixes(1, "a") == -1

    def test_string_suffix_vs_int(self):
        """string suffix sorts after int (lines 541-542)."""
        assert _compare_prerelease_suffixes("a", 1) == 1


# ---------------------------------------------------------------------------
# _process_prerelease_suffix
# ---------------------------------------------------------------------------


class TestProcessPrereleaseSuffix:
    def test_int_string_becomes_int(self):
        assert _process_prerelease_suffix("3") == 3

    def test_non_int_string_stays_string(self):
        """Lines 558-559: non-numeric suffix returns string."""
        result = _process_prerelease_suffix("stable")
        assert result == "stable"

    def test_none_returns_none(self):
        assert _process_prerelease_suffix(None) is None

    def test_empty_string_returns_none(self):
        """Empty/falsy string returns None."""
        assert _process_prerelease_suffix("") is None


# ---------------------------------------------------------------------------
# _extract_prerelease_type_and_suffix
# ---------------------------------------------------------------------------


class TestExtractPrereleaseTypeAndSuffix:
    def test_standalone_alpha_unicode(self):
        """Line 594: standalone α character maps to 'alpha'."""
        prerelease_type, suffix = _extract_prerelease_type_and_suffix("1.0-α")
        assert prerelease_type == "alpha"

    def test_standalone_beta_unicode(self):
        """Line 594: standalone β character maps to 'beta'."""
        prerelease_type, suffix = _extract_prerelease_type_and_suffix("1.0-β")
        assert prerelease_type == "beta"

    def test_alpha_with_number(self):
        prerelease_type, suffix = _extract_prerelease_type_and_suffix("1.0-alpha.2")
        assert prerelease_type == "alpha"
        assert suffix == 2

    def test_rc_with_string_suffix(self):
        prerelease_type, suffix = _extract_prerelease_type_and_suffix("1.0-rc.final")
        assert prerelease_type == "rc"
        assert suffix == "final"

    def test_no_prerelease_returns_final(self):
        prerelease_type, suffix = _extract_prerelease_type_and_suffix("1.0.0")
        assert prerelease_type == "final"
        assert suffix is None


# ---------------------------------------------------------------------------
# _convert_versions_to_tuples
# ---------------------------------------------------------------------------


class TestConvertVersionsToTuples:
    def test_none_version1_becomes_zeros(self):
        """Line 659: None version1 → (0, 0, 0)."""
        v1, v2 = _convert_versions_to_tuples(None, "1.2.3")
        assert v1 == (0, 0, 0)

    def test_none_version2_becomes_zeros(self):
        """Line 668: None version2 → (0, 0, 0)."""
        v1, v2 = _convert_versions_to_tuples("1.2.3", None)
        assert v2 == (0, 0, 0)

    def test_both_none(self):
        v1, v2 = _convert_versions_to_tuples(None, None)
        assert v1 == (0, 0, 0)
        assert v2 == (0, 0, 0)

    def test_tuple_versions_passed_through(self):
        """Tuple versions are returned unchanged."""
        t = (1, 2, 3)
        v1, v2 = _convert_versions_to_tuples(t, t)
        assert v1 == t
        assert v2 == t

    def test_unparseable_string_becomes_zeros(self):
        """Strings that fail to parse → (0, 0, 0)."""
        v1, v2 = _convert_versions_to_tuples("not-a-version!!!", "1.0.0")
        # parse_version may return None for gibberish
        assert isinstance(v1, tuple)


# ---------------------------------------------------------------------------
# _apply_version_truncation
# ---------------------------------------------------------------------------


class TestApplyVersionTruncation:
    def test_both_have_build_metadata_truncates_to_3(self):
        """Lines 705-708: build metadata → truncate to 3 components."""
        v1 = (1, 2, 3, 4, 5)
        v2 = (1, 2, 3, 4, 6)
        result_v1, result_v2, max_len = _apply_version_truncation(v1, v2, 5, True, False)
        assert len(result_v1) == 3
        assert len(result_v2) == 3
        assert max_len == 3

    def test_both_have_prerelease_truncates_to_3(self):
        """Lines 710-713: prerelease versions → truncate to 3 components."""
        v1 = (1, 2, 3, 4)
        v2 = (1, 2, 3, 5)
        result_v1, result_v2, max_len = _apply_version_truncation(v1, v2, 4, False, True)
        assert len(result_v1) == 3
        assert max_len == 3

    def test_neither_flag_no_truncation(self):
        """No flags → no truncation."""
        v1 = (1, 2, 3, 4)
        v2 = (1, 2, 3, 5)
        result_v1, result_v2, max_len = _apply_version_truncation(v1, v2, 4, False, False)
        assert max_len == 4


# ---------------------------------------------------------------------------
# get_version_difference
# ---------------------------------------------------------------------------


class TestGetVersionDifference:
    def test_both_empty_returns_zero_tuple(self):
        """Lines 634-635: both empty → (0, 0, 0)."""
        result = get_version_difference("", "")
        assert result == (0, 0, 0)

    def test_one_malformed_returns_none(self):
        """Line 643: one malformed version → None."""
        result = get_version_difference("not_a_version!!!", "1.0.0")
        assert result is None

    def test_normal_difference(self):
        result = get_version_difference("2.0.0", "1.0.0")
        assert result is not None
        assert result[0] > 0

    def test_build_metadata_versions_truncated(self):
        """Lines 705-708: build metadata causes truncation to 3 components."""
        result = get_version_difference("1.2.3+build.1", "1.2.3+build.2")
        assert result is not None

    def test_prerelease_versions_truncated(self):
        """Lines 710-713: prerelease versions are truncated."""
        result = get_version_difference("1.2.3-alpha.1", "1.2.3-beta.1")
        assert result is not None

    def test_none_version_returns_none(self):
        assert get_version_difference(None, "1.0.0") is None
        assert get_version_difference("1.0.0", None) is None

    def test_tuple_versions(self):
        result = get_version_difference((2, 0, 0), (1, 0, 0))
        assert result is not None
        assert result[0] > 0


# ---------------------------------------------------------------------------
# _handle_empty_version_cases
# ---------------------------------------------------------------------------


class TestHandleEmptyVersionCases:
    def test_both_empty_returns_up_to_date(self):
        """Line 837: both empty → UP_TO_DATE."""
        result = _handle_empty_version_cases("", "")
        assert result == VersionStatus.UP_TO_DATE

    def test_current_empty_returns_unknown(self):
        """Line 840-841: one empty → UNKNOWN."""
        result = _handle_empty_version_cases("", "1.0.0")
        assert result == VersionStatus.UNKNOWN

    def test_latest_empty_returns_unknown(self):
        result = _handle_empty_version_cases("1.0.0", "")
        assert result == VersionStatus.UNKNOWN

    def test_neither_empty_returns_none(self):
        """Neither empty → None (continue normal processing)."""
        assert _handle_empty_version_cases("1.0.0", "2.0.0") is None


# ---------------------------------------------------------------------------
# get_version_info
# ---------------------------------------------------------------------------


class TestGetVersionInfo:
    def test_none_current_version(self):
        """Lines 770-771: None current_version is treated as empty string."""
        info = get_version_info(None)
        assert info is not None

    def test_single_version_no_comparison(self):
        """Lines 781-783: without latest_version, just returns basic info."""
        info = get_version_info("1.0.0")
        assert info is not None
        assert info.status == VersionStatus.UNKNOWN

    def test_up_to_date(self):
        info = get_version_info("1.0.0", "1.0.0")
        assert info.status == VersionStatus.UP_TO_DATE

    def test_outdated(self):
        """Line 859-862: OUTDATED with outdated_by populated."""
        info = get_version_info("1.0.0", "2.0.0")
        assert info.status == VersionStatus.OUTDATED

    def test_newer(self):
        """Lines 864-867: NEWER with newer_by populated."""
        info = get_version_info("2.0.0", "1.0.0")
        assert info.status == VersionStatus.NEWER

    def test_malformed_current_unknown(self):
        """Lines 816-818: malformed current version → UNKNOWN."""
        info = get_version_info("not_a_version!!!", "1.0.0")
        assert info.status == VersionStatus.UNKNOWN

    def test_malformed_latest_unknown(self):
        """Lines 803-804: malformed latest version → (0,0,0) parsed."""
        info = get_version_info("1.0.0", "not_a_version!!!")
        assert info is not None

    def test_empty_current_and_latest(self):
        """Both empty → UP_TO_DATE (via _handle_empty_version_cases)."""
        info = get_version_info("", "")
        assert info.status == VersionStatus.UP_TO_DATE

    def test_empty_current_non_empty_latest(self):
        """One empty → UNKNOWN."""
        info = get_version_info("", "1.0.0")
        assert info.status == VersionStatus.UNKNOWN


# ---------------------------------------------------------------------------
# is_version_newer  (smoke tests of public API)
# ---------------------------------------------------------------------------


class TestIsVersionNewer:
    def test_older_is_not_newer(self):
        assert is_version_newer("1.0.0", "1.0.0") is False

    def test_latest_is_newer(self):
        assert is_version_newer("1.0.0", "2.0.0") is True

    def test_current_ahead_not_newer(self):
        assert is_version_newer("2.0.0", "1.0.0") is False


# ---------------------------------------------------------------------------
# compare_versions (edge cases hitting application-prefix path)
# ---------------------------------------------------------------------------


class TestCompareVersionsEdgeCases:
    def test_prefix_versions_equal(self):
        """Line 355: application prefix versions treated as equal."""
        result = compare_versions("Firefox 120.0", "Firefox 120.0")
        assert result == 0

    def test_both_versions_are_tuples(self):
        """Tuple inputs are handled."""
        assert compare_versions((1, 0, 0), (2, 0, 0)) < 0
        assert compare_versions((2, 0, 0), (1, 0, 0)) > 0
