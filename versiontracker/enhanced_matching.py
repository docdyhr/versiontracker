"""Enhanced fuzzy matching for improved application name matching accuracy.

This module provides advanced fuzzy matching algorithms and strategies to improve
the accuracy of matching application names with package manager entries.
"""

import logging
import re
from typing import Any

# Try to import fuzzy matching libraries
USE_RAPIDFUZZ = False
USE_FUZZYWUZZY = False
fuzz: Any = None

try:
    import rapidfuzz.fuzz as rapidfuzz_fuzz

    fuzz = rapidfuzz_fuzz
    USE_RAPIDFUZZ = True
except ImportError:
    try:
        import fuzzywuzzy.fuzz as fuzzywuzzy_fuzz

        fuzz = fuzzywuzzy_fuzz
        USE_FUZZYWUZZY = True
    except ImportError:
        pass

logger = logging.getLogger(__name__)


class EnhancedMatcher:
    """Enhanced fuzzy matching with multiple strategies for improved accuracy."""

    # Common application name variations and their mappings
    KNOWN_ALIASES = {
        # Common abbreviations
        "vscode": ["visual studio code", "code"],
        "intellij": ["intellij idea", "idea"],
        "pycharm": ["pycharm ce", "pycharm community", "pycharm professional"],
        "webstorm": ["webstorm ide"],
        "goland": ["goland ide"],
        "rubymine": ["rubymine ide"],
        "datagrip": ["datagrip ide"],
        "clion": ["clion ide"],
        "appcode": ["appcode ide"],
        "rider": ["rider ide"],
        # Version suffixes
        "firefox": ["firefox nightly", "firefox developer edition", "firefox esr"],
        "chrome": ["google chrome", "chrome canary", "chromium"],
        "edge": ["microsoft edge", "edge dev", "edge beta"],
        # Company names
        "slack": ["slack for desktop"],
        "teams": ["microsoft teams"],
        "zoom": ["zoom.us", "zoom client"],
        "discord": ["discord app"],
        "notion": ["notion enhanced", "notion desktop"],
        "obsidian": ["obsidian md"],
        # Developer tools
        "docker": ["docker desktop", "docker for mac"],
        "postman": ["postman api", "postman client"],
        "insomnia": ["insomnia rest", "insomnia api"],
        "sourcetree": ["sourcetree git"],
        "tower": ["tower git", "git tower"],
        "fork": ["fork git"],
        # Utilities
        "iterm": ["iterm2"],
        "alacritty": ["alacritty terminal"],
        "hyper": ["hyper terminal"],
        "rectangle": ["rectangle window manager"],
        "magnet": ["magnet window manager"],
        "spectacle": ["spectacle window manager"],
        # Media apps
        "vlc": ["vlc media player"],
        "mpv": ["mpv player"],
        "iina": ["iina player"],
        "spotify": ["spotify music", "spotify desktop"],
        # Office apps
        "word": ["microsoft word", "ms word"],
        "excel": ["microsoft excel", "ms excel"],
        "powerpoint": ["microsoft powerpoint", "ms powerpoint"],
        "outlook": ["microsoft outlook", "ms outlook"],
        "pages": ["apple pages"],
        "numbers": ["apple numbers"],
        "keynote": ["apple keynote"],
    }

    # Common suffixes to ignore during matching
    IGNORE_SUFFIXES = [
        "app",
        "application",
        "desktop",
        "for mac",
        "for macos",
        "mac",
        "macos",
        "osx",
        "client",
        "pro",
        "lite",
        "free",
        "premium",
        "plus",
        "ultimate",
        "community",
        "professional",
    ]

    # Patterns for version numbers
    VERSION_PATTERNS = [
        r"\d+\.\d+\.\d+",  # 1.2.3
        r"\d+\.\d+",  # 1.2
        r"v?\d+",  # v1 or 1
        r"\d{4}",  # Year versions like 2023
    ]

    def __init__(self, threshold: int = 75):
        """Initialize the enhanced matcher.

        Args:
            threshold: Minimum similarity score (0-100) for a match
        """
        self.threshold = threshold
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        self.version_regex = re.compile(r"|".join(self.VERSION_PATTERNS))
        # Only match suffixes at the end of the string or followed by whitespace
        self.suffix_regex = re.compile(
            r"\b(" + "|".join(re.escape(s) for s in self.IGNORE_SUFFIXES) + r")(?:\s|$)",
            re.IGNORECASE,
        )

    def normalize_advanced(self, name: str) -> str:
        """Advanced normalization of application names.

        Args:
            name: Application name to normalize

        Returns:
            Normalized name
        """
        # Basic cleanup
        normalized = name.lower().strip()

        # Remove file extensions
        normalized = re.sub(r"\.(app|exe|dmg|pkg)$", "", normalized, flags=re.IGNORECASE)

        # Remove version numbers
        normalized = self.version_regex.sub("", normalized)

        # Remove special characters but keep spaces and hyphens
        normalized = re.sub(r"[^\w\s-]", " ", normalized)

        # Normalize whitespace first
        normalized = " ".join(normalized.split())

        # Remove common suffixes at the end - iterate to handle multiple patterns
        for suffix in self.IGNORE_SUFFIXES:
            # Only remove if it's at the end of the string
            pattern = r"\b" + re.escape(suffix) + r"$"
            normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE).strip()

        # Clean up any extra whitespace again
        normalized = " ".join(normalized.split())

        # Remove trailing/leading hyphens
        normalized = normalized.strip("-")

        return normalized

    def tokenize(self, name: str) -> list[str]:
        """Tokenize name into meaningful parts.

        Args:
            name: Name to tokenize

        Returns:
            List of tokens
        """
        # First normalize
        normalized = self.normalize_advanced(name)

        # Split on spaces and hyphens
        tokens = re.split(r"[\s-]+", normalized)

        # Filter out empty tokens but keep all valid words
        tokens = [t for t in tokens if len(t) > 0]

        return tokens

    def calculate_token_similarity(self, tokens1: list[str], tokens2: list[str]) -> float:
        """Calculate similarity based on token overlap.

        Args:
            tokens1: First set of tokens
            tokens2: Second set of tokens

        Returns:
            Similarity score (0-100)
        """
        if not tokens1 or not tokens2:
            return 0.0

        set1 = set(tokens1)
        set2 = set(tokens2)

        # Calculate Jaccard similarity
        intersection = set1.intersection(set2)
        union = set1.union(set2)

        if not union:
            return 0.0

        jaccard = len(intersection) / len(union)

        # Boost score if all tokens from shorter name are in longer name
        if len(set1) < len(set2) and set1.issubset(set2):
            jaccard = min(jaccard * 1.5, 1.0)
        elif len(set2) < len(set1) and set2.issubset(set1):
            jaccard = min(jaccard * 1.5, 1.0)

        return jaccard * 100

    def check_known_aliases(self, name1: str, name2: str) -> float | None:
        """Check if names are known aliases of each other.

        Args:
            name1: First name
            name2: Second name

        Returns:
            100.0 if known aliases, None otherwise
        """
        normalized1 = self.normalize_advanced(name1).lower()
        normalized2 = self.normalize_advanced(name2).lower()

        for canonical, aliases in self.KNOWN_ALIASES.items():
            all_names = [canonical] + aliases
            normalized_names = [self.normalize_advanced(n).lower() for n in all_names]

            if normalized1 in normalized_names and normalized2 in normalized_names:
                return 100.0

        return None

    def calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names using multiple strategies.

        Args:
            name1: First name
            name2: Second name

        Returns:
            Similarity score (0-100)
        """
        # Check for exact match first
        if name1.lower() == name2.lower():
            return 100.0

        # Check known aliases
        alias_score = self.check_known_aliases(name1, name2)
        if alias_score is not None:
            return alias_score

        # Normalize names
        norm1 = self.normalize_advanced(name1)
        norm2 = self.normalize_advanced(name2)

        # Check normalized exact match
        if norm1 == norm2:
            return 95.0

        scores = []

        # Basic fuzzy matching if available
        if fuzz:
            # Standard ratio
            if hasattr(fuzz, "ratio"):
                scores.append(fuzz.ratio(norm1, norm2))

            # Partial ratio for substring matching
            if hasattr(fuzz, "partial_ratio"):
                scores.append(fuzz.partial_ratio(norm1, norm2) * 0.9)

            # Token sort ratio for word order independence
            if hasattr(fuzz, "token_sort_ratio"):
                scores.append(fuzz.token_sort_ratio(norm1, norm2) * 0.95)

            # Token set ratio for subset matching
            if hasattr(fuzz, "token_set_ratio"):
                scores.append(fuzz.token_set_ratio(norm1, norm2) * 0.9)

        # Token-based similarity
        tokens1 = self.tokenize(name1)
        tokens2 = self.tokenize(name2)
        token_score = self.calculate_token_similarity(tokens1, tokens2)
        scores.append(token_score)

        # Fallback substring matching
        if norm1 in norm2 or norm2 in norm1:
            # Calculate overlap percentage
            overlap = min(len(norm1), len(norm2)) / max(len(norm1), len(norm2))
            scores.append(overlap * 80)

        # Return the highest score
        return max(scores) if scores else 0.0

    def find_best_match(self, target: str, candidates: list[str]) -> tuple[str, float] | None:
        """Find the best matching candidate for a target name.

        Args:
            target: Target name to match
            candidates: List of candidate names

        Returns:
            Tuple of (best_match, score) or None if no match above threshold
        """
        if not candidates:
            return None

        best_match = None
        best_score = 0.0

        for candidate in candidates:
            score = self.calculate_similarity(target, candidate)

            if score > best_score:
                best_score = score
                best_match = candidate

            # Early exit on perfect match
            if score >= 100.0:
                break

        if best_score >= self.threshold and best_match is not None:
            return (best_match, best_score)

        return None

    def find_all_matches(self, target: str, candidates: list[str]) -> list[tuple[str, float]]:
        """Find all candidates matching above the threshold.

        Args:
            target: Target name to match
            candidates: List of candidate names

        Returns:
            List of (candidate, score) tuples sorted by score
        """
        matches = []

        for candidate in candidates:
            score = self.calculate_similarity(target, candidate)

            if score >= self.threshold:
                matches.append((candidate, score))

        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches

    def explain_match(self, name1: str, name2: str) -> dict[str, float | str | list[str] | bool | dict[str, float]]:
        """Explain why two names match or don't match.

        Args:
            name1: First name
            name2: Second name

        Returns:
            Dictionary with match explanation
        """
        result: dict[str, float | str | list[str] | bool | dict[str, float]] = {
            "name1": name1,
            "name2": name2,
            "normalized1": self.normalize_advanced(name1),
            "normalized2": self.normalize_advanced(name2),
            "tokens1": self.tokenize(name1),
            "tokens2": self.tokenize(name2),
            "scores": {},
            "is_alias": False,
            "final_score": 0.0,
        }

        # Check aliases
        alias_score = self.check_known_aliases(name1, name2)
        scores_dict = {}
        if alias_score:
            result["is_alias"] = True
            scores_dict["alias"] = alias_score

        # Calculate various scores
        if fuzz:
            norm1 = str(result["normalized1"])
            norm2 = str(result["normalized2"])
            if hasattr(fuzz, "ratio"):
                scores_dict["ratio"] = float(fuzz.ratio(norm1, norm2))
            if hasattr(fuzz, "partial_ratio"):
                scores_dict["partial_ratio"] = float(fuzz.partial_ratio(norm1, norm2))
            if hasattr(fuzz, "token_sort_ratio"):
                scores_dict["token_sort_ratio"] = float(fuzz.token_sort_ratio(norm1, norm2))
            if hasattr(fuzz, "token_set_ratio"):
                scores_dict["token_set_ratio"] = float(fuzz.token_set_ratio(norm1, norm2))

        # Token similarity
        tokens1_list = list(result["tokens1"]) if isinstance(result["tokens1"], list) else []
        tokens2_list = list(result["tokens2"]) if isinstance(result["tokens2"], list) else []
        scores_dict["token_similarity"] = self.calculate_token_similarity(tokens1_list, tokens2_list)

        result["scores"] = scores_dict

        # Final score
        result["final_score"] = self.calculate_similarity(name1, name2)

        return result


# Global instance for convenience
_default_matcher: EnhancedMatcher | None = None


def get_enhanced_matcher(threshold: int = 75) -> EnhancedMatcher:
    """Get or create the default enhanced matcher instance.

    Args:
        threshold: Minimum similarity threshold

    Returns:
        EnhancedMatcher instance
    """
    global _default_matcher

    if _default_matcher is None or _default_matcher.threshold != threshold:
        _default_matcher = EnhancedMatcher(threshold)

    return _default_matcher


def enhanced_match(name1: str, name2: str, threshold: int = 75) -> float:
    """Calculate enhanced similarity between two names.

    Args:
        name1: First name
        name2: Second name
        threshold: Minimum threshold (used for matcher initialization)

    Returns:
        Similarity score (0-100)
    """
    matcher = get_enhanced_matcher(threshold)
    return matcher.calculate_similarity(name1, name2)


def find_best_enhanced_match(target: str, candidates: list[str], threshold: int = 75) -> tuple[str, float] | None:
    """Find the best matching candidate using enhanced matching.

    Args:
        target: Target name to match
        candidates: List of candidate names
        threshold: Minimum similarity threshold

    Returns:
        Tuple of (best_match, score) or None
    """
    matcher = get_enhanced_matcher(threshold)
    return matcher.find_best_match(target, candidates)
