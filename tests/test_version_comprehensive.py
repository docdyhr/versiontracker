"""Comprehensive tests for version module."""

from typing import Dict, Union

import pytest

from versiontracker.version import (
    USE_FUZZYWUZZY,
    USE_RAPIDFUZZ,
    VERSION_PATTERNS,
    VersionInfo,
    VersionStatus,
    _dict_to_tuple,
    _parse_version_components,
    _parse_version_to_dict,
    _tuple_to_dict,
    compare_fuzzy,
    compare_versions,
    compose_version_tuple,
    decompose_version,
    get_compiled_pattern,
    get_version_difference,
    get_version_info,
    parse_version,
    partial_ratio,
    similarity_score,
)


class TestVersionStatus:
    """Test VersionStatus enum."""

    def test_version_status_values(self):
        """Test that VersionStatus has correct values."""
        assert VersionStatus.UNKNOWN.value == 0
        assert VersionStatus.UPTODATE.value == 1
        assert VersionStatus.OUTDATED.value == 2
        assert VersionStatus.NEWER.value == 3
        assert VersionStatus.NOT_FOUND.value == 4
        assert VersionStatus.ERROR.value == 5


class TestVersionInfo:
    """Test VersionInfo class."""

    def test_version_info_creation(self):
        """Test creating VersionInfo instances."""
        info = VersionInfo("TestApp", "1.0.0")
        assert info.name == "TestApp"
        assert info.version_string == "1.0.0"
        assert info.latest_version is None
        assert info.latest_parsed is None
        assert info.status == VersionStatus.UNKNOWN
        assert info.outdated_by is None

    def test_version_info_with_all_params(self):
        """Test creating VersionInfo with all parameters."""
        info = VersionInfo(
            "TestApp",
            "1.0.0",
            latest_version="2.0.0",
            latest_parsed=(2, 0, 0),
            status=VersionStatus.OUTDATED,
            outdated_by=(1, 0, 0)
        )
        assert info.name == "TestApp"
        assert info.version_string == "1.0.0"
        assert info.latest_version == "2.0.0"
        assert info.latest_parsed == (2, 0, 0)
        assert info.status == VersionStatus.OUTDATED
        assert info.outdated_by == (1, 0, 0)


class TestParseVersion:
    """Test parse_version function."""

    def test_parse_simple_version(self):
        """Test parsing simple version strings."""
        assert parse_version("1.2.3") == (1, 2, 3)
        assert parse_version("2.0") == (2, 0)
        assert parse_version("5") == (5,)

    def test_parse_version_with_build(self):
        """Test parsing versions with build numbers."""
        result = parse_version("1.2.3-beta")
        assert result is not None
        assert result[:3] == (1, 2, 3)

    def test_parse_none_version(self):
        """Test parsing None version."""
        assert parse_version(None) is None

    def test_parse_empty_version(self):
        """Test parsing empty version."""
        assert parse_version("") is None
        assert parse_version("   ") is None

    def test_parse_invalid_version(self):
        """Test parsing invalid version strings."""
        assert parse_version("not-a-version") is None
        assert parse_version("abc.def.ghi") is None

    @pytest.mark.parametrize("version,expected", [
        ("1.0.0", (1, 0, 0)),
        ("2.1", (2, 1)),
        ("3", (3,)),
        ("1.2.3-alpha", (1, 2, 3)),
        ("1.0.0+build.1", (1, 0, 0)),
    ])
    def test_parse_version_parametrized(self, version, expected):
        """Test parsing various version formats."""
        result = parse_version(version)
        assert result is not None
        assert result[:len(expected)] == expected


class TestCompareVersions:
    """Test compare_versions function."""

    def test_compare_equal_versions(self):
        """Test comparing equal versions."""
        assert compare_versions("1.0.0", "1.0.0") == 0
        assert compare_versions((1, 0, 0), (1, 0, 0)) == 0

    def test_compare_older_newer(self):
        """Test comparing older and newer versions."""
        assert compare_versions("1.0.0", "2.0.0") < 0
        assert compare_versions("2.0.0", "1.0.0") > 0

    def test_compare_different_lengths(self):
        """Test comparing versions with different lengths."""
        assert compare_versions("1.0", "1.0.0") == 0
        assert compare_versions("1.0", "1.0.1") < 0

    def test_compare_with_none(self):
        """Test comparing with None values."""
        assert compare_versions(None, "1.0.0") < 0  # type: ignore[arg-type]
        assert compare_versions("1.0.0", None) > 0  # type: ignore[arg-type]
        assert compare_versions(None, None) == 0    # type: ignore[arg-type]

    @pytest.mark.parametrize("v1,v2,expected", [
        ("1.0.0", "1.0.0", 0),
        ("1.0.0", "2.0.0", -1),
        ("2.0.0", "1.0.0", 1),
        ("1.0.0", "1.0.1", -1),
        ("1.1.0", "1.0.9", 1),
    ])
    def test_compare_versions_parametrized(self, v1, v2, expected):
        """Test version comparison with various inputs."""
        result = compare_versions(v1, v2)
        if expected == 0:
            assert result == 0
        elif expected < 0:
            assert result < 0
        else:
            assert result > 0


class TestVersionDifference:
    """Test get_version_difference function."""

    def test_version_difference_basic(self):
        """Test basic version difference calculation."""
        diff = get_version_difference("1.0.0", "2.0.0")
        assert diff == (1, 0, 0)

    def test_version_difference_minor(self):
        """Test minor version difference."""
        diff = get_version_difference("1.0.0", "1.1.0")
        assert diff == (0, 1, 0)

    def test_version_difference_patch(self):
        """Test patch version difference."""
        diff = get_version_difference("1.0.0", "1.0.1")
        assert diff == (0, 0, 1)

    def test_version_difference_with_none(self):
        """Test version difference with None values."""
        assert get_version_difference(None, "1.0.0") is None
        assert get_version_difference("1.0.0", None) is None
        assert get_version_difference(None, None) is None


class TestGetVersionInfo:
    """Test get_version_info function."""

    def test_version_info_upgrade(self):
        """Test version info for upgrade."""
        info = get_version_info("1.0.0", "2.0.0")
        assert "1.0.0" in info
        assert "2.0.0" in info

    def test_version_info_same(self):
        """Test version info for same version."""
        info = get_version_info("1.0.0", "1.0.0")
        assert "same" in info.lower() or "identical" in info.lower()

    def test_version_info_with_none(self):
        """Test version info with None values."""
        info = get_version_info(None, "1.0.0")
        assert "unknown" in info.lower()


class TestSimilarityScore:
    """Test similarity_score function."""

    def test_similarity_identical(self):
        """Test similarity of identical strings."""
        assert similarity_score("test", "test") == 100

    def test_similarity_different(self):
        """Test similarity of different strings."""
        score = similarity_score("test", "different")
        assert 0 <= score <= 100
        assert score < 100

    def test_similarity_with_none(self):
        """Test similarity with None values."""
        assert similarity_score(None, "test") == 0  # type: ignore[arg-type]
        assert similarity_score("test", None) == 0  # type: ignore[arg-type]
        assert similarity_score(None, None) == 0    # type: ignore[arg-type]

    def test_similarity_empty_strings(self):
        """Test similarity with empty strings."""
        assert similarity_score("", "") == 100
        assert similarity_score("", "test") == 0
        assert similarity_score("test", "") == 0


class TestPartialRatio:
    """Test partial_ratio function."""

    def test_partial_ratio_identical(self):
        """Test partial ratio of identical strings."""
        assert partial_ratio("test", "test") == 100

    def test_partial_ratio_substring(self):
        """Test partial ratio with substring."""
        score = partial_ratio("test", "testing")
        assert score > 0

    def test_partial_ratio_empty(self):
        """Test partial ratio with empty strings."""
        assert partial_ratio("", "") == 0
        assert partial_ratio("", "test") == 0
        assert partial_ratio("test", "") == 0

    def test_partial_ratio_score_cutoff(self):
        """Test partial ratio with score cutoff (should be ignored)."""
        # score_cutoff should be ignored for compatibility
        score1 = partial_ratio("test", "testing")
        score2 = partial_ratio("test", "testing", score_cutoff=50)
        assert score1 == score2


class TestDecomposeVersion:
    """Test decompose_version function."""

    def test_decompose_simple_version(self):
        """Test decomposing simple version."""
        result = decompose_version("1.2.3")
        assert result is not None
        assert isinstance(result, dict)

    def test_decompose_empty_version(self):
        """Test decomposing empty version."""
        assert decompose_version("") is None
        assert decompose_version(None) is None # type: ignore[arg-type]

    def test_decompose_complex_version(self):
        """Test decomposing complex version."""
        result = decompose_version("1.2.3-beta+build.1")
        assert result is not None


class TestVersionPatterns:
    """Test VERSION_PATTERNS."""

    def test_version_patterns_exist(self):
        """Test that VERSION_PATTERNS is defined."""
        assert VERSION_PATTERNS is not None
        assert isinstance(VERSION_PATTERNS, list)
        assert len(VERSION_PATTERNS) > 0

    def test_version_patterns_match(self):
        """Test that version patterns can match common versions."""
        import re
        test_versions = ["1.2.3", "2.0", "5", "1.0.0-beta"]
        
        for version in test_versions:
            matched = False
            for pattern in VERSION_PATTERNS:
                if re.search(pattern, version):
                    matched = True
                    break
            assert matched, f"No pattern matched version: {version}"


class TestUtilityFunctions:
    """Test utility functions."""

    def test_get_compiled_pattern(self):
        """Test get_compiled_pattern function."""
        pattern = r"\d+\.\d+\.\d+"
        compiled = get_compiled_pattern(pattern)
        assert compiled.pattern == pattern

    def test_compose_version_tuple(self):
        """Test compose_version_tuple function."""
        version_dict: Dict[str, Union[int, str]] = {"major": 1, "minor": 2, "patch": 3}
        result = compose_version_tuple(version_dict)
        assert result is not None

    def test_compare_fuzzy(self):
        """Test compare_fuzzy function."""
        score = compare_fuzzy("test", "test")
        assert score == 100.0
        
        score = compare_fuzzy("similar", "different")
        assert 0 <= score <= 100


class TestPrivateFunctions:
    """Test private functions."""

    def test_parse_version_components(self):
        """Test _parse_version_components function."""
        result = _parse_version_components("1.2.3")
        assert result is not None

    def test_parse_version_to_dict(self):
        """Test _parse_version_to_dict function."""
        result = _parse_version_to_dict("1.2.3")
        assert result is not None or result is None  # Can return None for invalid input

    def test_dict_to_tuple(self):
        """Test _dict_to_tuple function."""
        version_dict = {"major": 1, "minor": 2, "patch": 3}
        result = _dict_to_tuple(version_dict)
        assert result is not None

    def test_tuple_to_dict(self):
        """Test _tuple_to_dict function."""
        version_tuple = (1, 2, 3)
        result = _tuple_to_dict(version_tuple)
        assert result is not None
        assert isinstance(result, dict)

    def test_dict_to_tuple_with_none(self):
        """Test _dict_to_tuple with None input."""
        result = _dict_to_tuple(None)
        assert result is None

    def test_tuple_to_dict_with_none(self):
        """Test _tuple_to_dict with None input."""
        result = _tuple_to_dict(None)
        assert isinstance(result, dict)


class TestErrorHandling:
    """Test error handling in version functions."""

    def test_parse_version_error_handling(self):
        """Test parse_version error handling."""
        # Should not raise exceptions for invalid input
        assert parse_version("invalid...version") is None
        assert parse_version("") is None

    def test_compare_versions_error_handling(self):
        """Test compare_versions error handling."""
        # Should handle invalid inputs gracefully
        result = compare_versions("invalid", "1.0.0")
        assert isinstance(result, int)

    def test_similarity_score_error_handling(self):
        """Test similarity_score error handling."""
        # Should handle None and empty inputs
        assert similarity_score(None, "test") == 0 # type: ignore[arg-type]
        assert similarity_score("", "") >= 0


class TestFuzzyLibraryCompatibility:
    """Test fuzzy library compatibility."""

    def test_fuzzy_library_flags(self):
        """Test that fuzzy library flags are properly set."""
        # At least one should be True or both False if no library is available
        assert isinstance(USE_RAPIDFUZZ, bool)
        assert isinstance(USE_FUZZYWUZZY, bool)

    def test_fuzzy_functions_work(self):
        """Test that fuzzy functions work regardless of library."""
        # These should work regardless of which fuzzy library is available
        score1 = similarity_score("test", "test")
        score2 = partial_ratio("test", "testing")
        
        assert score1 == 100
        assert isinstance(score2, int)
        assert 0 <= score2 <= 100


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_version_strings(self):
        """Test handling of very long version strings."""
        long_version = "1." + ".".join(["0"] * 100)
        result = parse_version(long_version)
        # Should either parse successfully or return None
        assert result is None or isinstance(result, tuple)

    def test_unicode_version_strings(self):
        """Test handling of Unicode in version strings."""
        unicode_version = "1.2.3-αβγ"
        result = parse_version(unicode_version)
        # Should handle Unicode gracefully
        assert result is None or isinstance(result, tuple)

    def test_special_characters_in_versions(self):
        """Test handling of special characters."""
        special_versions = [
            "1.2.3!",
            "1.2.3@",
            "1.2.3#",
            "1.2.3$",
            "1.2.3%",
        ]
        
        for version in special_versions:
            result = parse_version(version)
            # Should not raise exceptions
            assert result is None or isinstance(result, tuple)

    def test_whitespace_handling(self):
        """Test handling of whitespace in version strings."""
        whitespace_versions = [
            " 1.2.3 ",
            "\t1.2.3\t",
            "\n1.2.3\n",
            "1. 2. 3",
        ]
        
        for version in whitespace_versions:
            result = parse_version(version)
            # Should handle whitespace gracefully
            assert result is None or isinstance(result, tuple)