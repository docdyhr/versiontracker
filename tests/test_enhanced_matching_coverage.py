"""Coverage tests for enhanced_matching — fuzz-fallback and Jaccard-boost paths."""

from unittest.mock import MagicMock

import versiontracker.enhanced_matching as em
from versiontracker.enhanced_matching import EnhancedMatcher

# ---------------------------------------------------------------------------
# Jaccard boost paths (lines 221-224)
# ---------------------------------------------------------------------------


class TestJaccardBoost:
    """Token similarity score is boosted when one token set is a subset."""

    def test_s1_subset_of_s2_boosts_score(self):
        matcher = EnhancedMatcher()
        # {"visual", "studio"} ⊂ {"visual", "studio", "code"}
        base = len({"visual", "studio"}) / len({"visual", "studio", "code"})
        score = matcher.calculate_token_similarity(
            ["visual", "studio"],
            ["visual", "studio", "code"],
        )
        boosted = min(base * 1.5, 1.0) * 100
        assert abs(score - boosted) < 0.01

    def test_s2_subset_of_s1_boosts_score(self):
        matcher = EnhancedMatcher()
        # reverse direction: s2 ⊂ s1
        score = matcher.calculate_token_similarity(
            ["visual", "studio", "code"],
            ["visual", "studio"],
        )
        assert score > 0

    def test_equal_sets_no_boost(self):
        matcher = EnhancedMatcher()
        score = matcher.calculate_token_similarity(["docker", "desktop"], ["docker", "desktop"])
        assert score == 100.0

    def test_disjoint_sets_zero(self):
        matcher = EnhancedMatcher()
        score = matcher.calculate_token_similarity(["alpha"], ["beta"])
        assert score == 0.0

    def test_empty_tokens_returns_zero(self):
        matcher = EnhancedMatcher()
        assert matcher.calculate_token_similarity([], ["a"]) == 0.0
        assert matcher.calculate_token_similarity(["a"], []) == 0.0


# ---------------------------------------------------------------------------
# SequenceMatcher fallback when fuzz is None (lines 298-308)
# ---------------------------------------------------------------------------


class TestNoFuzzFallback:
    """calculate_similarity falls back to SequenceMatcher when no fuzzy libs."""

    def test_returns_numeric_score(self, monkeypatch):
        monkeypatch.setattr(em, "fuzz", None)
        matcher = EnhancedMatcher()
        score = matcher.calculate_similarity("Microsoft Word", "MS Office Suite")
        assert 0.0 <= score <= 100.0

    def test_space_collapse_branch(self, monkeypatch):
        """Names with spaces vs collapsed form triggers the extra SequenceMatcher call."""
        monkeypatch.setattr(em, "fuzz", None)
        matcher = EnhancedMatcher()
        # "app name" normalises differently from "appname"
        score = matcher.calculate_similarity("app name", "appname")
        assert score > 0.0

    def test_high_similarity_similar_names(self, monkeypatch):
        monkeypatch.setattr(em, "fuzz", None)
        matcher = EnhancedMatcher()
        score = matcher.calculate_similarity("Firefox Browser", "Firefox Web Browser")
        assert score > 50.0

    def test_low_similarity_unrelated_names(self, monkeypatch):
        monkeypatch.setattr(em, "fuzz", None)
        matcher = EnhancedMatcher()
        score = matcher.calculate_similarity("Zoom", "Adobe Photoshop")
        assert score < 60.0


# ---------------------------------------------------------------------------
# explain_match fuzz paths (lines 407-417)
# ---------------------------------------------------------------------------


class TestExplainMatchWithFuzz:
    """explain_match populates fuzz scores when a fuzzy library is available."""

    def _make_mock_fuzz(self):
        mock = MagicMock()
        mock.ratio.return_value = 85.0
        mock.partial_ratio.return_value = 90.0
        mock.token_sort_ratio.return_value = 88.0
        mock.token_set_ratio.return_value = 92.0
        return mock

    def test_ratio_score_included(self, monkeypatch):
        monkeypatch.setattr(em, "fuzz", self._make_mock_fuzz())
        matcher = EnhancedMatcher()
        result = matcher.explain_match("Visual Studio Code", "VS Code")
        scores = dict(result["scores"])  # type: ignore[arg-type]
        assert "ratio" in scores

    def test_partial_ratio_included(self, monkeypatch):
        monkeypatch.setattr(em, "fuzz", self._make_mock_fuzz())
        matcher = EnhancedMatcher()
        result = matcher.explain_match("Visual Studio Code", "VS Code")
        scores = dict(result["scores"])  # type: ignore[arg-type]
        assert "partial_ratio" in scores

    def test_token_sort_ratio_included(self, monkeypatch):
        monkeypatch.setattr(em, "fuzz", self._make_mock_fuzz())
        matcher = EnhancedMatcher()
        result = matcher.explain_match("Code Studio", "Studio Code")
        scores = dict(result["scores"])  # type: ignore[arg-type]
        assert "token_sort_ratio" in scores

    def test_token_set_ratio_included(self, monkeypatch):
        monkeypatch.setattr(em, "fuzz", self._make_mock_fuzz())
        matcher = EnhancedMatcher()
        result = matcher.explain_match("Docker Desktop", "Docker")
        scores = dict(result["scores"])  # type: ignore[arg-type]
        assert "token_set_ratio" in scores

    def test_alias_path_with_fuzz(self, monkeypatch):
        """Alias match sets is_alias=True and alias score is in scores dict."""
        monkeypatch.setattr(em, "fuzz", self._make_mock_fuzz())
        matcher = EnhancedMatcher()
        result = matcher.explain_match("vscode", "visual studio code")
        assert result["is_alias"] is True
        scores = dict(result["scores"])  # type: ignore[arg-type]
        assert "alias" in scores
