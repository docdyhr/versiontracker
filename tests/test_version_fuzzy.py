"""Tests for versiontracker.version.fuzzy module.

This module provides comprehensive tests for the fuzzy string matching
utilities used in version comparison. It tests:
- similarity_score: 0-100 scoring with None/empty handling
- partial_ratio: partial substring matching
- get_partial_ratio_scorer: scorer factory function
- compare_fuzzy: version string fuzzy comparison
- extract_best_match: best match extraction from a list
- get_fuzz / get_fuzz_process: module accessor functions
- _MinimalFuzz / _MinimalProcess: fallback implementations

Tests cover both the normal path (with whatever fuzzy library is installed)
and the minimal fallback path (via mocking).
"""

from unittest.mock import patch

import pytest

from versiontracker.version import fuzzy
from versiontracker.version.fuzzy import (
    _MinimalFuzz,
    _MinimalProcess,
    compare_fuzzy,
    extract_best_match,
    get_fuzz,
    get_fuzz_process,
    get_partial_ratio_scorer,
    partial_ratio,
    similarity_score,
)

# ---------------------------------------------------------------------------
# Helper: context manager to force the minimal fallback path
# ---------------------------------------------------------------------------


def _force_minimal_fallback():
    """Return a combined patch context that forces the minimal fallback path.

    This patches the module-level flags and the _fuzz/_fuzz_process references
    so that all functions use _MinimalFuzz / _MinimalProcess.
    """
    minimal_fuzz = _MinimalFuzz()
    minimal_process = _MinimalProcess()
    return (
        patch.object(fuzzy, "USE_RAPIDFUZZ", False),
        patch.object(fuzzy, "USE_FUZZYWUZZY", False),
        patch.object(fuzzy, "_fuzz", minimal_fuzz),
        patch.object(fuzzy, "_fuzz_process", minimal_process),
    )


# ===========================================================================
# Tests for _MinimalFuzz
# ===========================================================================


class TestMinimalFuzz:
    """Tests for the _MinimalFuzz fallback implementation."""

    def setup_method(self):
        self.fuzz = _MinimalFuzz()

    # -- ratio --

    def test_ratio_exact_match(self):
        assert self.fuzz.ratio("hello", "hello") == 100

    def test_ratio_case_insensitive_match(self):
        assert self.fuzz.ratio("Hello", "hello") == 100
        assert self.fuzz.ratio("FIREFOX", "firefox") == 100

    def test_ratio_no_match(self):
        assert self.fuzz.ratio("hello", "world") == 0

    def test_ratio_partial_no_match(self):
        """Minimal ratio does NOT do partial matching -- must be exact."""
        assert self.fuzz.ratio("fire", "firefox") == 0

    def test_ratio_empty_strings(self):
        assert self.fuzz.ratio("", "") == 100

    def test_ratio_one_empty(self):
        assert self.fuzz.ratio("", "hello") == 0
        assert self.fuzz.ratio("hello", "") == 0

    # -- partial_ratio --

    def test_partial_ratio_exact_match(self):
        assert self.fuzz.partial_ratio("hello", "hello") == 100

    def test_partial_ratio_substring_match(self):
        assert self.fuzz.partial_ratio("Chrome", "Google Chrome") == 100
        assert self.fuzz.partial_ratio("Google Chrome", "Chrome") == 100

    def test_partial_ratio_case_insensitive(self):
        assert self.fuzz.partial_ratio("chrome", "GOOGLE CHROME") == 100

    def test_partial_ratio_no_match(self):
        assert self.fuzz.partial_ratio("Firefox", "Safari") == 0

    def test_partial_ratio_empty_strings(self):
        """Empty string is a substring of everything."""
        assert self.fuzz.partial_ratio("", "") == 100
        assert self.fuzz.partial_ratio("", "hello") == 100
        assert self.fuzz.partial_ratio("hello", "") == 100


# ===========================================================================
# Tests for _MinimalProcess
# ===========================================================================


class TestMinimalProcess:
    """Tests for the _MinimalProcess fallback implementation."""

    def setup_method(self):
        self.process = _MinimalProcess()

    def test_extract_one_empty_choices(self):
        assert self.process.extractOne("query", []) is None

    def test_extract_one_exact_match(self):
        result = self.process.extractOne("Firefox", ["Firefox", "Chrome", "Safari"])
        assert result is not None
        assert result[0] == "Firefox"
        assert result[1] == 100

    def test_extract_one_case_insensitive_exact(self):
        result = self.process.extractOne("firefox", ["Firefox", "Chrome", "Safari"])
        assert result is not None
        assert result[0] == "Firefox"
        assert result[1] == 100

    def test_extract_one_query_in_choice(self):
        """query.lower() in choice.lower() => score 80."""
        result = self.process.extractOne("Chrome", ["Google Chrome Browser", "Safari", "Edge"])
        assert result is not None
        assert result[0] == "Google Chrome Browser"
        assert result[1] == 80

    def test_extract_one_choice_in_query(self):
        """choice.lower() in query.lower() => score 70."""
        result = self.process.extractOne("Google Chrome Browser", ["Chrome", "Safari", "Edge"])
        assert result is not None
        assert result[0] == "Chrome"
        assert result[1] == 70

    def test_extract_one_no_match_returns_first_choice(self):
        """When no match is found, returns (first_choice, 0)."""
        result = self.process.extractOne("XYZ", ["Alpha", "Beta", "Gamma"])
        assert result is not None
        assert result[0] == "Alpha"
        assert result[1] == 0

    def test_extract_one_prefers_higher_score(self):
        """Exact match (100) should beat substring match (80)."""
        result = self.process.extractOne("Chrome", ["Google Chrome", "Chrome", "Chromium"])
        assert result is not None
        assert result[0] == "Chrome"
        assert result[1] == 100


# ===========================================================================
# Tests for similarity_score
# ===========================================================================


class TestSimilarityScore:
    """Tests for the similarity_score function."""

    # -- None handling --

    def test_both_none(self):
        assert similarity_score(None, None) == 0

    def test_first_none(self):
        assert similarity_score(None, "hello") == 0

    def test_second_none(self):
        assert similarity_score("hello", None) == 0

    # -- Empty string handling --

    def test_both_empty(self):
        assert similarity_score("", "") == 100

    def test_first_empty(self):
        assert similarity_score("", "hello") == 0

    def test_second_empty(self):
        assert similarity_score("hello", "") == 0

    # -- Normal matching --

    def test_identical_strings(self):
        score = similarity_score("Firefox", "Firefox")
        assert score == 100

    def test_case_insensitive_equal(self):
        score = similarity_score("Firefox", "firefox")
        # With rapidfuzz/fuzzywuzzy this may not be exactly 100,
        # but the minimal fallback returns 100. We just check high.
        assert score >= 70

    def test_completely_different(self):
        score = similarity_score("abcdef", "zyxwvu")
        assert score < 50

    def test_returns_int(self):
        result = similarity_score("test", "test")
        assert isinstance(result, int)

    def test_score_range(self):
        """Score should always be in [0, 100]."""
        pairs = [
            ("hello", "hello"),
            ("abc", "xyz"),
            ("short", "a very long string that is different"),
            ("", "non-empty"),
            ("same", "same"),
        ]
        for s1, s2 in pairs:
            score = similarity_score(s1, s2)
            assert 0 <= score <= 100, f"Score {score} out of range for ({s1!r}, {s2!r})"

    # -- Fallback path via mocking --

    def test_minimal_fallback_identical(self):
        patches = _force_minimal_fallback()
        with patches[0], patches[1], patches[2], patches[3]:
            assert similarity_score("Firefox", "Firefox") == 100

    def test_minimal_fallback_case_insensitive(self):
        patches = _force_minimal_fallback()
        with patches[0], patches[1], patches[2], patches[3]:
            assert similarity_score("Firefox", "firefox") == 100

    def test_minimal_fallback_no_match(self):
        patches = _force_minimal_fallback()
        with patches[0], patches[1], patches[2], patches[3]:
            assert similarity_score("Firefox", "Chrome") == 0

    # -- Error handling --

    def test_fuzz_raises_exception_falls_back(self):
        """If _fuzz.ratio raises, the function falls back gracefully."""

        class BrokenFuzz:
            def ratio(self, s1, s2):
                raise TypeError("broken")

        with patch.object(fuzzy, "_fuzz", BrokenFuzz()):
            # Should not raise; uses inline fallback
            score = similarity_score("test", "test")
            assert score == 100

    def test_fuzz_raises_falls_back_different_strings(self):
        class BrokenFuzz:
            def ratio(self, s1, s2):
                raise ValueError("broken")

        with patch.object(fuzzy, "_fuzz", BrokenFuzz()):
            score = similarity_score("abc", "xyz")
            assert score == 0

    def test_fuzz_raises_falls_back_substring(self):
        class BrokenFuzz:
            def ratio(self, s1, s2):
                raise AttributeError("broken")

        with patch.object(fuzzy, "_fuzz", BrokenFuzz()):
            score = similarity_score("Chrome", "Google Chrome")
            assert score == 70


# ===========================================================================
# Tests for partial_ratio
# ===========================================================================


class TestPartialRatio:
    """Tests for the partial_ratio function."""

    def test_empty_first_string(self):
        assert partial_ratio("", "hello") == 0

    def test_empty_second_string(self):
        assert partial_ratio("hello", "") == 0

    def test_both_empty(self):
        assert partial_ratio("", "") == 0

    def test_identical_strings(self):
        score = partial_ratio("Firefox", "Firefox")
        assert score == 100

    def test_substring_match_high_score(self):
        score = partial_ratio("Chrome", "Google Chrome")
        assert score >= 70

    def test_no_match_low_score(self):
        score = partial_ratio("Firefox", "Safari")
        assert score < 50

    def test_score_cutoff_ignored(self):
        """score_cutoff is accepted but currently unused."""
        score1 = partial_ratio("hello", "hello", score_cutoff=None)
        score2 = partial_ratio("hello", "hello", score_cutoff=90)
        assert score1 == score2

    def test_returns_int(self):
        result = partial_ratio("a", "b")
        assert isinstance(result, int)

    # -- Fallback path --

    def test_minimal_fallback_exact(self):
        patches = _force_minimal_fallback()
        with patches[0], patches[1], patches[2], patches[3]:
            assert partial_ratio("hello", "hello") == 100

    def test_minimal_fallback_substring(self):
        patches = _force_minimal_fallback()
        with patches[0], patches[1], patches[2], patches[3]:
            assert partial_ratio("Chrome", "Google Chrome") == 100

    def test_minimal_fallback_no_match(self):
        patches = _force_minimal_fallback()
        with patches[0], patches[1], patches[2], patches[3]:
            assert partial_ratio("Firefox", "Safari") == 0

    # -- Error handling --

    def test_fuzz_raises_exception_falls_back(self):
        class BrokenFuzz:
            def partial_ratio(self, s1, s2):
                raise TypeError("broken")

        with patch.object(fuzzy, "_fuzz", BrokenFuzz()):
            score = partial_ratio("test", "test")
            assert score == 100

    def test_fuzz_raises_falls_back_substring(self):
        class BrokenFuzz:
            def partial_ratio(self, s1, s2):
                raise ValueError("broken")

        with patch.object(fuzzy, "_fuzz", BrokenFuzz()):
            score = partial_ratio("fire", "firefox")
            assert score == 70


# ===========================================================================
# Tests for get_partial_ratio_scorer
# ===========================================================================


class TestGetPartialRatioScorer:
    """Tests for the get_partial_ratio_scorer factory function."""

    def test_returns_callable(self):
        scorer = get_partial_ratio_scorer()
        assert callable(scorer)

    def test_scorer_returns_float(self):
        scorer = get_partial_ratio_scorer()
        result = scorer("hello", "hello")
        assert isinstance(result, float)

    def test_scorer_identical_strings(self):
        scorer = get_partial_ratio_scorer()
        assert scorer("Firefox", "Firefox") == 100.0

    def test_scorer_different_strings(self):
        scorer = get_partial_ratio_scorer()
        score = scorer("abcdef", "zyxwvu")
        assert score < 50.0

    # -- Explicit rapidfuzz path --

    def test_rapidfuzz_scorer_path(self):
        """When USE_RAPIDFUZZ is True, the rapidfuzz scorer branch is used."""
        mock_fuzz = _MinimalFuzz()
        with (
            patch.object(fuzzy, "USE_RAPIDFUZZ", True),
            patch.object(fuzzy, "USE_FUZZYWUZZY", False),
            patch.object(fuzzy, "_fuzz", mock_fuzz),
        ):
            scorer = get_partial_ratio_scorer()
            assert scorer("hello", "hello") == 100.0
            assert scorer("abc", "xyz") == 0.0

    # -- Explicit fuzzywuzzy path --

    def test_fuzzywuzzy_scorer_path(self):
        """When USE_FUZZYWUZZY is True (and rapidfuzz False), fuzzywuzzy branch is used."""
        mock_fuzz = _MinimalFuzz()
        with (
            patch.object(fuzzy, "USE_RAPIDFUZZ", False),
            patch.object(fuzzy, "USE_FUZZYWUZZY", True),
            patch.object(fuzzy, "_fuzz", mock_fuzz),
        ):
            scorer = get_partial_ratio_scorer()
            assert scorer("hello", "hello") == 100.0
            assert scorer("abc", "xyz") == 0.0

    # -- Explicit fallback path --

    def test_fallback_scorer_path(self):
        """When both flags are False, the inline fallback scorer is returned."""
        patches = _force_minimal_fallback()
        with patches[0], patches[1], patches[2], patches[3]:
            scorer = get_partial_ratio_scorer()
            assert scorer("hello", "hello") == 100.0
            assert scorer("Chrome", "Google Chrome") == 70.0
            assert scorer("abc", "xyz") == 0.0


# ===========================================================================
# Tests for compare_fuzzy
# ===========================================================================


class TestCompareFuzzy:
    """Tests for the compare_fuzzy function."""

    def test_identical_versions(self):
        assert compare_fuzzy("1.2.3", "1.2.3") == 100.0

    def test_different_versions(self):
        score = compare_fuzzy("1.2.3", "4.5.6")
        assert score < 100.0

    def test_returns_float(self):
        result = compare_fuzzy("1.0", "1.0")
        assert isinstance(result, float)

    def test_threshold_parameter_accepted(self):
        """threshold is accepted but does not affect the return value."""
        score1 = compare_fuzzy("1.2.3", "1.2.4", threshold=80)
        score2 = compare_fuzzy("1.2.3", "1.2.4", threshold=50)
        assert score1 == score2

    def test_similar_versions_high_score(self):
        score = compare_fuzzy("1.2.3", "1.2.4")
        assert score > 50.0

    def test_v_prefix_similarity(self):
        score = compare_fuzzy("v1.2.3", "1.2.3")
        assert score > 50.0

    # -- Fallback when _fuzz is None --

    def test_no_fuzz_identical(self):
        with patch.object(fuzzy, "_fuzz", None):
            assert compare_fuzzy("1.2.3", "1.2.3") == 100.0

    def test_no_fuzz_different(self):
        with patch.object(fuzzy, "_fuzz", None):
            assert compare_fuzzy("1.2.3", "4.5.6") == 0.0

    def test_no_fuzz_case_insensitive(self):
        with patch.object(fuzzy, "_fuzz", None):
            assert compare_fuzzy("ABC", "abc") == 100.0

    # -- Minimal fallback path --

    def test_minimal_fallback_identical(self):
        patches = _force_minimal_fallback()
        with patches[0], patches[1], patches[2], patches[3]:
            assert compare_fuzzy("1.2.3", "1.2.3") == 100.0

    def test_minimal_fallback_different(self):
        patches = _force_minimal_fallback()
        with patches[0], patches[1], patches[2], patches[3]:
            assert compare_fuzzy("1.2.3", "4.5.6") == 0.0


# ===========================================================================
# Tests for extract_best_match
# ===========================================================================


class TestExtractBestMatch:
    """Tests for the extract_best_match function."""

    def test_empty_choices(self):
        assert extract_best_match("query", []) is None

    def test_exact_match(self):
        result = extract_best_match("Firefox", ["Firefox", "Chrome", "Safari"])
        assert result is not None
        assert result[0] == "Firefox"
        assert result[1] == 100

    def test_case_insensitive_match(self):
        result = extract_best_match("firefox", ["Firefox", "Chrome", "Safari"])
        assert result is not None
        assert result[0] == "Firefox"
        assert result[1] >= 70

    def test_returns_tuple_or_none(self):
        result = extract_best_match("test", ["test"])
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], int)

    def test_score_cutoff_filters(self):
        """With a very high cutoff, low-scoring matches are filtered out."""
        result = extract_best_match("zzzzz", ["Alpha", "Beta", "Gamma"], score_cutoff=90)
        assert result is None

    def test_score_cutoff_zero_allows_all(self):
        result = extract_best_match("anything", ["Alpha"], score_cutoff=0)
        # Should return something (score >= 0)
        assert result is not None

    def test_best_match_among_several(self):
        result = extract_best_match("Chrome", ["Firefox", "Google Chrome", "Safari"])
        assert result is not None
        # Should pick "Google Chrome" as best match (contains "Chrome")
        assert "Chrome" in result[0]

    # -- Minimal fallback path --

    def test_minimal_fallback_exact(self):
        patches = _force_minimal_fallback()
        with patches[0], patches[1], patches[2], patches[3]:
            result = extract_best_match("Firefox", ["Firefox", "Chrome"])
            assert result is not None
            assert result[0] == "Firefox"
            assert result[1] == 100

    def test_minimal_fallback_substring(self):
        patches = _force_minimal_fallback()
        with patches[0], patches[1], patches[2], patches[3]:
            result = extract_best_match("Chrome", ["Google Chrome", "Safari"])
            assert result is not None
            assert result[0] == "Google Chrome"
            assert result[1] >= 80

    def test_minimal_fallback_no_match_with_cutoff(self):
        patches = _force_minimal_fallback()
        with patches[0], patches[1], patches[2], patches[3]:
            result = extract_best_match("zzz", ["Alpha", "Beta"], score_cutoff=50)
            assert result is None

    # -- Error handling --

    def test_fuzz_process_raises_falls_back(self):
        """If _fuzz_process.extractOne raises, fallback logic is used."""

        class BrokenProcess:
            def extractOne(self, query, choices):
                raise TypeError("broken")

        with patch.object(fuzzy, "_fuzz_process", BrokenProcess()):
            result = extract_best_match("Firefox", ["Firefox", "Chrome"])
            assert result is not None
            assert result[0] == "Firefox"

    def test_fuzz_process_returns_low_score_below_cutoff(self):
        """If extractOne returns below score_cutoff, None is returned."""

        class LowScoreProcess:
            def extractOne(self, query, choices):
                return (choices[0], 10)

        with patch.object(fuzzy, "_fuzz_process", LowScoreProcess()):
            result = extract_best_match("query", ["choice"], score_cutoff=50)
            assert result is None


# ===========================================================================
# Tests for get_fuzz / get_fuzz_process
# ===========================================================================


class TestGetFuzzAccessors:
    """Tests for the get_fuzz and get_fuzz_process accessor functions."""

    def test_get_fuzz_returns_something(self):
        result = get_fuzz()
        assert result is not None

    def test_get_fuzz_has_ratio(self):
        fuzz_mod = get_fuzz()
        assert hasattr(fuzz_mod, "ratio")

    def test_get_fuzz_has_partial_ratio(self):
        fuzz_mod = get_fuzz()
        assert hasattr(fuzz_mod, "partial_ratio")

    def test_get_fuzz_process_returns_something(self):
        result = get_fuzz_process()
        assert result is not None

    def test_get_fuzz_process_has_extract_one(self):
        proc = get_fuzz_process()
        assert hasattr(proc, "extractOne")

    def test_get_fuzz_returns_module_reference(self):
        """get_fuzz should return the module-level _fuzz reference."""
        assert get_fuzz() is fuzzy._fuzz

    def test_get_fuzz_process_returns_module_reference(self):
        """get_fuzz_process should return the module-level _fuzz_process reference."""
        assert get_fuzz_process() is fuzzy._fuzz_process


# ===========================================================================
# Tests for library detection flags
# ===========================================================================


class TestLibraryDetection:
    """Tests verifying the library detection flags are consistent."""

    def test_flags_are_mutually_exclusive_or_both_false(self):
        """At most one of USE_RAPIDFUZZ / USE_FUZZYWUZZY should be True."""
        assert not (fuzzy.USE_RAPIDFUZZ and fuzzy.USE_FUZZYWUZZY)

    def test_at_least_one_backend_available(self):
        """_fuzz and _fuzz_process should always be set (library or fallback)."""
        assert fuzzy._fuzz is not None
        assert fuzzy._fuzz_process is not None


# ===========================================================================
# Integration-style tests (use whatever library is installed)
# ===========================================================================


class TestIntegration:
    """Integration tests exercising the public API end-to-end."""

    def test_similarity_and_partial_ratio_consistent(self):
        """For identical strings, both functions should return 100."""
        assert similarity_score("Firefox", "Firefox") == 100
        assert partial_ratio("Firefox", "Firefox") == 100

    def test_extract_best_match_uses_similarity(self):
        """extract_best_match should find the closest match."""
        result = extract_best_match("Firefox", ["Chrome", "Firefox", "Safari"])
        assert result is not None
        assert result[0] == "Firefox"
        assert result[1] == 100

    def test_compare_fuzzy_identical_is_perfect(self):
        assert compare_fuzzy("2.0.1", "2.0.1") == 100.0

    def test_full_pipeline_scorer(self):
        """Get a scorer, use it, and verify results make sense."""
        scorer = get_partial_ratio_scorer()
        assert scorer("Firefox", "Firefox") == 100.0
        assert scorer("Firefox", "Mozilla Firefox") > 0.0

    @pytest.mark.parametrize(
        "s1, s2, expected_min",
        [
            ("Firefox", "Firefox", 100),
            ("Chrome", "Google Chrome", 50),
            ("Safari", "Microsoft Edge", 0),
        ],
    )
    def test_similarity_score_parametrized(self, s1, s2, expected_min):
        score = similarity_score(s1, s2)
        assert score >= expected_min

    @pytest.mark.parametrize(
        "query, choices, expected_match",
        [
            ("Firefox", ["Firefox", "Chrome"], "Firefox"),
            ("chrome", ["Firefox", "Chrome", "Safari"], "Chrome"),
        ],
    )
    def test_extract_best_match_parametrized(self, query, choices, expected_match):
        result = extract_best_match(query, choices)
        assert result is not None
        assert result[0] == expected_match
