"""Fuzzy string matching utilities for version comparison.

This module provides fuzzy matching capabilities for comparing application names
and version strings. It uses rapidfuzz (preferred) or fuzzywuzzy (fallback)
libraries when available, with minimal fallback implementations otherwise.

Typical usage:
    from versiontracker.version.fuzzy import similarity_score, partial_ratio

    score = similarity_score("Firefox", "firefox")  # 100
    score = partial_ratio("Chrome", "Google Chrome")  # ~80
"""

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Fuzzy matching library imports with fallbacks
USE_RAPIDFUZZ = False
USE_FUZZYWUZZY = False
_fuzz: Any = None
_fuzz_process: Any = None

try:
    import rapidfuzz.fuzz as rapidfuzz_fuzz
    import rapidfuzz.process as rapidfuzz_process

    _fuzz = rapidfuzz_fuzz
    _fuzz_process = rapidfuzz_process
    USE_RAPIDFUZZ = True
except ImportError:
    try:
        import fuzzywuzzy.fuzz as fuzzywuzzy_fuzz
        import fuzzywuzzy.process as fuzzywuzzy_process

        _fuzz = fuzzywuzzy_fuzz
        _fuzz_process = fuzzywuzzy_process
        USE_FUZZYWUZZY = True
    except ImportError:
        pass


class _MinimalFuzz:
    """Minimal implementation of fuzzy matching when no library is available."""

    @staticmethod
    def ratio(s1: str, s2: str) -> int:
        """Calculate the ratio of similarity between two strings."""
        return 100 if s1.lower() == s2.lower() else 0

    @staticmethod
    def partial_ratio(s1: str, s2: str) -> int:
        """Calculate the partial ratio of similarity between two strings."""
        return 100 if s1.lower() in s2.lower() or s2.lower() in s1.lower() else 0


class _MinimalProcess:
    """Minimal implementation of fuzzy process matching."""

    @staticmethod
    def extractOne(query: str, choices: list[str]) -> tuple[str, int] | None:
        """Extract the best match from choices."""
        if not choices:
            return None

        best_match = None
        best_score = 0

        for choice in choices:
            if query.lower() == choice.lower():
                score = 100
            elif query.lower() in choice.lower():
                score = 80
            elif choice.lower() in query.lower():
                score = 70
            else:
                score = 0

            if score > best_score:
                best_score = score
                best_match = choice

        return (best_match, best_score) if best_match else (choices[0], 0)


# Set up fallback implementations if no library available
if not USE_RAPIDFUZZ and not USE_FUZZYWUZZY:
    _fuzz = _MinimalFuzz()
    _fuzz_process = _MinimalProcess()


def get_fuzz() -> Any:
    """Get the active fuzz module (rapidfuzz, fuzzywuzzy, or minimal fallback).

    Returns:
        The fuzz module or fallback class instance.
    """
    return _fuzz


def get_fuzz_process() -> Any:
    """Get the active fuzz process module.

    Returns:
        The fuzz process module or fallback class instance.
    """
    return _fuzz_process


def similarity_score(s1: str | None, s2: str | None) -> int:
    """Calculate similarity score between two strings.

    This function provides a similarity score between 0-100 for two strings,
    with special handling for None and empty string values.

    Args:
        s1: First string to compare (can be None)
        s2: Second string to compare (can be None)

    Returns:
        Similarity score from 0-100

    Examples:
        >>> similarity_score("Firefox", "firefox")
        100
        >>> similarity_score("Chrome", "Firefox")
        # Lower score due to different strings
        >>> similarity_score(None, "test")
        0
    """
    # Handle None cases
    if s1 is None or s2 is None:
        return 0

    # Handle empty string cases
    if s1 == "" and s2 == "":
        return 100
    if s1 == "" or s2 == "":
        return 0

    # Use the existing fuzzy matching logic
    try:
        if _fuzz and hasattr(_fuzz, "ratio"):
            return int(_fuzz.ratio(s1, s2))
    except (AttributeError, TypeError, ValueError) as e:
        logger.error("Error calculating similarity score for '%s' vs '%s': %s", s1, s2, e)

    # Simple fallback
    return 100 if s1.lower() == s2.lower() else (70 if s1.lower() in s2.lower() or s2.lower() in s1.lower() else 0)


def partial_ratio(s1: str, s2: str, score_cutoff: int | None = None) -> int:
    """Calculate partial ratio between two strings.

    Provides compatibility between rapidfuzz and fuzzywuzzy, with fallbacks.
    Partial ratio is useful for matching substrings within larger strings.

    Args:
        s1: First string to compare
        s2: Second string to compare
        score_cutoff: Optional score cutoff (for compatibility, currently unused)

    Returns:
        Similarity score from 0-100

    Examples:
        >>> partial_ratio("Chrome", "Google Chrome")
        # High score because "Chrome" is contained in "Google Chrome"
        >>> partial_ratio("Firefox", "Chrome")
        # Low score due to no substring match
    """
    # Silence unused parameter warning
    _ = score_cutoff

    if not s1 or not s2:
        return 0

    try:
        if _fuzz and hasattr(_fuzz, "partial_ratio"):
            return int(_fuzz.partial_ratio(s1, s2))
    except (AttributeError, TypeError, ValueError) as e:
        logger.error("Error calculating partial ratio for '%s' vs '%s': %s", s1, s2, e)

    # Simple fallback
    return 100 if s1.lower() == s2.lower() else (70 if s1.lower() in s2.lower() or s2.lower() in s1.lower() else 0)


def get_partial_ratio_scorer() -> Callable[[str, str], float]:
    """Return a scorer function compatible with rapidfuzz/fuzzywuzzy extractOne.

    Returns:
        A callable that takes two strings and returns a similarity score (0.0-100.0)

    Examples:
        >>> scorer = get_partial_ratio_scorer()
        >>> score = scorer("Firefox", "Mozilla Firefox")
    """
    if USE_RAPIDFUZZ and _fuzz and hasattr(_fuzz, "partial_ratio"):

        def rapidfuzz_scorer(s1: str, s2: str) -> float:
            return float(_fuzz.partial_ratio(s1, s2))

        return rapidfuzz_scorer
    elif USE_FUZZYWUZZY and _fuzz and hasattr(_fuzz, "partial_ratio"):

        def fuzzywuzzy_scorer(s1: str, s2: str) -> float:
            return float(_fuzz.partial_ratio(s1, s2))

        return fuzzywuzzy_scorer
    else:

        def fallback_scorer(s1: str, s2: str) -> float:
            return (
                100.0
                if s1.lower() == s2.lower()
                else (70.0 if s1.lower() in s2.lower() or s2.lower() in s1.lower() else 0.0)
            )

        return fallback_scorer


def compare_fuzzy(version1: str, version2: str, threshold: int = 80) -> float:
    """Compare two version strings using fuzzy matching.

    This is useful when version strings may have slight formatting differences
    but represent the same version.

    Args:
        version1: First version string
        version2: Second version string
        threshold: Minimum similarity threshold (not used in return value,
            kept for API compatibility)

    Returns:
        Similarity score between 0.0 and 100.0

    Examples:
        >>> compare_fuzzy("1.2.3", "1.2.3")
        100.0
        >>> compare_fuzzy("v1.2.3", "1.2.3")
        # High score due to similarity
    """
    _ = threshold  # Unused but kept for API compatibility

    if _fuzz:
        return float(_fuzz.ratio(version1, version2))
    # Fallback when no fuzzy library available
    return 100.0 if version1.lower() == version2.lower() else 0.0


def extract_best_match(query: str, choices: list[str], score_cutoff: int = 0) -> tuple[str, int] | None:
    """Extract the best matching string from a list of choices.

    Args:
        query: String to match against
        choices: List of candidate strings
        score_cutoff: Minimum score required for a match (0-100)

    Returns:
        Tuple of (best_match, score) or None if no match above cutoff

    Examples:
        >>> extract_best_match("firefox", ["Firefox", "Chrome", "Safari"])
        ('Firefox', 100)
    """
    if not choices:
        return None

    if _fuzz_process and hasattr(_fuzz_process, "extractOne"):
        try:
            result = _fuzz_process.extractOne(query, choices)
            if result and result[1] >= score_cutoff:
                # Cast to proper type - extractOne returns tuple[str, int] or None
                return (str(result[0]), int(result[1]))
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("Error in extractOne for '%s': %s", query, e)

    # Fallback implementation
    best_match = None
    best_score = 0

    for choice in choices:
        score = similarity_score(query, choice)
        if score > best_score:
            best_score = score
            best_match = choice

    if best_match and best_score >= score_cutoff:
        return (best_match, best_score)
    return None
