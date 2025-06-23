"""Tests for enhanced fuzzy matching functionality."""

from unittest.mock import Mock, patch

import pytest

from versiontracker.enhanced_matching import (
    EnhancedMatcher,
    enhanced_match,
    find_best_enhanced_match,
    get_enhanced_matcher,
)


class TestEnhancedMatcher:
    """Test the EnhancedMatcher class."""

    def test_init(self):
        """Test matcher initialization."""
        matcher = EnhancedMatcher(threshold=80)
        assert matcher.threshold == 80
        assert hasattr(matcher, "version_regex")
        assert hasattr(matcher, "suffix_regex")

    def test_normalize_advanced(self):
        """Test advanced name normalization."""
        matcher = EnhancedMatcher()

        # Test basic normalization
        assert matcher.normalize_advanced("Visual Studio Code") == "visual studio code"

        # Test file extension removal
        assert matcher.normalize_advanced("Firefox.app") == "firefox"
        assert matcher.normalize_advanced("Chrome.dmg") == "chrome"

        # Test version number removal
        assert matcher.normalize_advanced("Firefox 100.0.1") == "firefox"
        assert matcher.normalize_advanced("Chrome v95") == "chrome"

        # Test suffix removal
        assert matcher.normalize_advanced("Chrome Desktop") == "chrome"
        assert matcher.normalize_advanced("Firefox for Mac") == "firefox"

        # Test special character removal
        assert matcher.normalize_advanced("VLC@Media*Player!") == "vlc media player"

        # Test hyphen handling
        assert matcher.normalize_advanced("My-App-Name") == "my-app-name"
        assert matcher.normalize_advanced("-Leading-Trailing-") == "leading-trailing"

    def test_tokenize(self):
        """Test name tokenization."""
        matcher = EnhancedMatcher()

        # Test basic tokenization
        assert matcher.tokenize("Visual Studio Code") == ["visual", "studio", "code"]

        # Test hyphen splitting
        assert matcher.tokenize("My-App-Name") == ["my", "app", "name"]

        # Test mixed splitting
        assert matcher.tokenize("Docker Desktop for Mac") == ["docker", "desktop"]

        # Test filtering empty tokens (but keep single characters)
        assert matcher.tokenize("A B CD") == ["a", "b", "cd"]

    def test_calculate_token_similarity(self):
        """Test token-based similarity calculation."""
        matcher = EnhancedMatcher()

        # Test identical tokens
        tokens1 = ["visual", "studio", "code"]
        tokens2 = ["visual", "studio", "code"]
        assert matcher.calculate_token_similarity(tokens1, tokens2) == 100.0

        # Test subset relationship
        tokens1 = ["visual", "studio"]
        tokens2 = ["visual", "studio", "code"]
        score = matcher.calculate_token_similarity(tokens1, tokens2)
        assert score > 80  # Should get boost for subset

        # Test partial overlap
        tokens1 = ["visual", "studio"]
        tokens2 = ["studio", "code"]
        score = matcher.calculate_token_similarity(tokens1, tokens2)
        assert 30 < score < 70

        # Test no overlap
        tokens1 = ["firefox"]
        tokens2 = ["chrome"]
        assert matcher.calculate_token_similarity(tokens1, tokens2) == 0.0

        # Test empty tokens
        assert matcher.calculate_token_similarity([], ["test"]) == 0.0

    def test_check_known_aliases(self):
        """Test known alias checking."""
        matcher = EnhancedMatcher()

        # Test known aliases
        assert matcher.check_known_aliases("vscode", "visual studio code") == 100.0
        assert matcher.check_known_aliases("chrome", "google chrome") == 100.0
        assert matcher.check_known_aliases("docker", "docker desktop") == 100.0

        # Test case insensitive
        assert matcher.check_known_aliases("VSCODE", "Visual Studio Code") == 100.0

        # Test non-aliases
        assert matcher.check_known_aliases("firefox", "chrome") is None

    def test_calculate_similarity(self):
        """Test similarity calculation with multiple strategies."""
        matcher = EnhancedMatcher()

        # Test exact match
        assert matcher.calculate_similarity("test", "test") == 100.0
        assert matcher.calculate_similarity("Test", "test") == 100.0

        # Test known aliases
        assert matcher.calculate_similarity("vscode", "visual studio code") == 100.0

        # Test normalized exact match
        score = matcher.calculate_similarity("Visual Studio Code", "visual studio code")
        assert score >= 95.0

        # Test fuzzy matching (if available)
        score = matcher.calculate_similarity("chrome", "chromium")
        assert score > 60  # Should have some similarity

        # Test substring matching
        score = matcher.calculate_similarity("code", "visual studio code")
        assert score > 70  # Substring should score well

    def test_find_best_match(self):
        """Test finding best match from candidates."""
        matcher = EnhancedMatcher(threshold=70)

        candidates = ["firefox", "chrome", "visual-studio-code", "docker-desktop"]

        # Test exact match
        result = matcher.find_best_match("firefox", candidates)
        assert result is not None
        assert result[0] == "firefox"
        assert result[1] == 100.0

        # Test alias match
        result = matcher.find_best_match("docker", candidates)
        assert result is not None
        assert result[0] == "docker-desktop"
        # Should score high due to fuzzy matching but not necessarily 100
        assert result[1] > 85.0

        # Test fuzzy match
        result = matcher.find_best_match("docker", candidates)
        assert result is not None
        assert result[0] == "docker-desktop"

        # Test no match above threshold
        matcher.threshold = 90
        result = matcher.find_best_match("unknown-app", candidates)
        assert result is None

        # Test empty candidates
        assert matcher.find_best_match("test", []) is None

    def test_find_all_matches(self):
        """Test finding all matches above threshold."""
        matcher = EnhancedMatcher(threshold=60)

        candidates = ["firefox", "firefox-developer", "chrome", "chromium"]

        # Test multiple matches
        matches = matcher.find_all_matches("firefox", candidates)
        assert len(matches) >= 1
        assert matches[0][0] == "firefox"  # Best match first
        assert all(score >= 60 for _, score in matches)  # All above threshold

        # Test sorted by score
        scores = [score for _, score in matches]
        assert scores == sorted(scores, reverse=True)

    def test_explain_match(self):
        """Test match explanation functionality."""
        matcher = EnhancedMatcher()

        explanation = matcher.explain_match("vscode", "visual studio code")

        assert explanation["name1"] == "vscode"
        assert explanation["name2"] == "visual studio code"
        assert "normalized1" in explanation
        assert "normalized2" in explanation
        assert "tokens1" in explanation
        assert "tokens2" in explanation
        assert "scores" in explanation
        assert explanation["is_alias"] is True
        assert explanation["final_score"] == 100.0


class TestModuleFunctions:
    """Test module-level convenience functions."""

    def test_get_enhanced_matcher(self):
        """Test getting the default matcher instance."""
        matcher1 = get_enhanced_matcher(75)
        matcher2 = get_enhanced_matcher(75)

        # Should return same instance for same threshold
        assert matcher1 is matcher2

        # Should create new instance for different threshold
        matcher3 = get_enhanced_matcher(80)
        assert matcher3 is not matcher1
        assert matcher3.threshold == 80

    def test_enhanced_match(self):
        """Test convenience function for enhanced matching."""
        score = enhanced_match("vscode", "visual studio code")
        assert score == 100.0

        score = enhanced_match("chrome", "firefox")
        assert score < 50

    def test_find_best_enhanced_match(self):
        """Test convenience function for finding best match."""
        candidates = ["firefox", "chrome", "visual-studio-code"]

        result = find_best_enhanced_match("firefox", candidates)
        assert result is not None
        assert result[0] == "firefox"
        assert result[1] == 100.0

        # Test with higher threshold
        result = find_best_enhanced_match("unknown", candidates, threshold=90)
        assert result is None


class TestRealWorldScenarios:
    """Test with real-world application name variations."""

    def test_common_app_variations(self):
        """Test matching common application name variations."""
        matcher = EnhancedMatcher(threshold=70)

        # Test IDE variations
        assert matcher.calculate_similarity("IntelliJ IDEA", "intellij") >= 90
        assert matcher.calculate_similarity("PyCharm CE", "pycharm") >= 90
        assert matcher.calculate_similarity("Visual Studio Code", "vscode") == 100.0

        # Test browser variations
        assert matcher.calculate_similarity("Google Chrome", "chrome") == 100.0
        assert (
            matcher.calculate_similarity("Firefox Developer Edition", "firefox")
            == 100.0
        )
        assert matcher.calculate_similarity("Microsoft Edge", "edge") == 100.0

        # Test utility variations
        assert matcher.calculate_similarity("Docker Desktop", "docker") == 100.0
        assert matcher.calculate_similarity("Slack for Desktop", "slack") == 100.0
        assert matcher.calculate_similarity("Zoom.us", "zoom") == 100.0

    def test_version_number_handling(self):
        """Test handling of version numbers in app names."""
        matcher = EnhancedMatcher()

        # Version numbers should be stripped
        assert matcher.normalize_advanced("Firefox 100.0.1") == "firefox"
        assert matcher.normalize_advanced("Chrome v95.0") == "chrome"
        assert matcher.normalize_advanced("IntelliJ IDEA 2023.1") == "intellij idea"

        # Similarity should be high despite version differences
        assert matcher.calculate_similarity("Firefox 100.0", "Firefox 101.0") >= 95

    def test_platform_suffix_handling(self):
        """Test handling of platform-specific suffixes."""
        matcher = EnhancedMatcher()

        # Platform suffixes should be removed
        assert matcher.normalize_advanced("Docker for Mac") == "docker"
        assert matcher.normalize_advanced("Slack Desktop") == "slack"
        assert matcher.normalize_advanced("Chrome App") == "chrome"

        # Should match well regardless of suffix
        assert matcher.calculate_similarity("Docker for Mac", "docker") >= 90
        assert matcher.calculate_similarity("Slack Desktop", "slack") >= 90

    def test_case_sensitivity(self):
        """Test case insensitive matching."""
        matcher = EnhancedMatcher()

        # Should be case insensitive
        assert matcher.calculate_similarity("FIREFOX", "firefox") == 100.0
        assert matcher.calculate_similarity("Chrome", "CHROME") == 100.0
        assert (
            matcher.calculate_similarity("Visual Studio Code", "VISUAL STUDIO CODE")
            == 100.0
        )


class TestPerformance:
    """Test performance characteristics of enhanced matching."""

    def test_large_candidate_list(self):
        """Test performance with large candidate lists."""
        matcher = EnhancedMatcher()

        # Create a large list of candidates
        candidates = [f"app-{i}" for i in range(1000)]
        candidates.append("target-app")

        # Should still find the match efficiently
        result = matcher.find_best_match("target-app", candidates)
        assert result is not None
        assert result[0] == "target-app"

    def test_caching_behavior(self):
        """Test that matcher instances are cached properly."""
        # Clear any existing cache
        import versiontracker.enhanced_matching

        versiontracker.enhanced_matching._default_matcher = None

        matcher1 = get_enhanced_matcher(75)
        matcher2 = get_enhanced_matcher(75)

        # Should reuse the same instance
        assert matcher1 is matcher2

        # Different threshold should create new instance
        matcher3 = get_enhanced_matcher(80)
        assert matcher3 is not matcher1


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_inputs(self):
        """Test handling of empty inputs."""
        matcher = EnhancedMatcher()

        # Empty strings
        assert matcher.calculate_similarity("", "") == 100.0
        assert matcher.calculate_similarity("test", "") < 50
        assert matcher.calculate_similarity("", "test") < 50

        # Empty candidate lists
        assert matcher.find_best_match("test", []) is None
        assert matcher.find_all_matches("test", []) == []

    def test_special_characters(self):
        """Test handling of special characters."""
        matcher = EnhancedMatcher()

        # Special characters should be normalized
        normalized = matcher.normalize_advanced("App@Name#123!")
        assert "@" not in normalized
        assert "#" not in normalized
        assert "!" not in normalized

        # Should still match well
        score = matcher.calculate_similarity("App@Name", "AppName")
        assert score > 80

    def test_unicode_handling(self):
        """Test handling of unicode characters."""
        matcher = EnhancedMatcher()

        # Should handle unicode gracefully
        score = matcher.calculate_similarity("Café", "Cafe")
        assert score > 70  # Should be similar despite accent

    def test_threshold_edge_cases(self):
        """Test threshold boundary conditions."""
        matcher = EnhancedMatcher(threshold=75)

        candidates = ["similar-app", "different-app"]

        # Mock similarity to return exactly threshold value
        with patch.object(matcher, "calculate_similarity") as mock_calc:
            mock_calc.return_value = 75.0
            result = matcher.find_best_match("test", candidates)
            assert result is not None  # Should include exact threshold match

            mock_calc.return_value = 74.9
            result = matcher.find_best_match("test", candidates)
            assert result is None  # Should exclude below threshold
