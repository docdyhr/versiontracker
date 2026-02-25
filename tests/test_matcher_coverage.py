"""Tests for versiontracker.apps.matcher — coverage improvement.

Targets untested paths in search_brew_cask, _process_brew_search,
get_homebrew_cask_name, filter_brew_candidates, filter_out_brews,
_find_matching_cask, _process_single_app_search, _batch_process_brew_search,
_wait_for_rate_limit, and _normalize_and_validate_search_term.
"""

from unittest.mock import MagicMock, patch

from versiontracker.apps.matcher import (
    _batch_process_brew_search,
    _find_matching_cask,
    _normalize_and_validate_search_term,
    _process_brew_search,
    _process_single_app_search,
    _wait_for_rate_limit,
    filter_brew_candidates,
    filter_out_brews,
    get_homebrew_cask_name,
    search_brew_cask,
)

# ---------------------------------------------------------------------------
# search_brew_cask
# ---------------------------------------------------------------------------


class TestSearchBrewCask:
    """Tests for search_brew_cask()."""

    def test_empty_string_returns_empty(self):
        result = search_brew_cask("")
        assert result == []

    def test_whitespace_only_returns_empty(self):
        result = search_brew_cask("   ")
        assert result == []

    @patch("versiontracker.apps.matcher.get_config")
    @patch("versiontracker.apps.matcher.run_command")
    @patch("versiontracker.apps.finder.is_homebrew_available", return_value=False)
    def test_homebrew_unavailable(self, _mock_hb, _mock_run, _mock_cfg):
        result = search_brew_cask("firefox")
        assert result == []

    @patch("versiontracker.apps.matcher.get_config")
    @patch("versiontracker.apps.matcher.run_command", return_value=("firefox\ngoogle-chrome\n", 0))
    @patch("versiontracker.apps.finder.is_homebrew_available", return_value=True)
    def test_success_returns_cask_names(self, _hb, _run, _cfg):
        result = search_brew_cask("fire")
        assert "firefox" in result
        assert "google-chrome" in result

    @patch("versiontracker.apps.matcher.get_config")
    @patch(
        "versiontracker.apps.matcher.run_command",
        return_value=("==> Casks\nfirefox\n==> Formulae\n", 0),
    )
    @patch("versiontracker.apps.finder.is_homebrew_available", return_value=True)
    def test_filters_header_lines(self, _hb, _run, _cfg):
        result = search_brew_cask("firefox")
        assert result == ["firefox"]

    @patch("versiontracker.apps.matcher.get_config")
    @patch("versiontracker.apps.matcher.run_command", return_value=("No formulae found", 1))
    @patch("versiontracker.apps.finder.is_homebrew_available", return_value=True)
    def test_nonzero_return_code(self, _hb, _run, _cfg):
        result = search_brew_cask("nonexistent")
        assert result == []

    @patch("versiontracker.apps.matcher.get_config", side_effect=RuntimeError("boom"))
    @patch("versiontracker.apps.finder.is_homebrew_available", return_value=True)
    def test_exception_returns_empty(self, _hb, _cfg):
        result = search_brew_cask("firefox")
        assert result == []

    @patch("versiontracker.apps.matcher.get_config")
    @patch(
        "versiontracker.apps.matcher.run_command",
        return_value=("firefox   (cask)\ngoogle-chrome  (cask)\n", 0),
    )
    @patch("versiontracker.apps.finder.is_homebrew_available", return_value=True)
    def test_extracts_first_word_when_space(self, _hb, _run, _cfg):
        result = search_brew_cask("fire")
        assert result == ["firefox", "google-chrome"]


# ---------------------------------------------------------------------------
# _process_brew_search
# ---------------------------------------------------------------------------


class TestProcessBrewSearch:
    """Tests for _process_brew_search()."""

    @patch("versiontracker.apps.matcher.get_config")
    @patch("versiontracker.apps.matcher.run_command", return_value=("firefox\n", 0))
    def test_match_found(self, _run, _cfg):
        result = _process_brew_search(("Firefox", "100.0"))
        assert result == "Firefox"

    @patch("versiontracker.apps.matcher.get_config")
    @patch("versiontracker.apps.matcher.run_command", return_value=("firefox\n", 0))
    def test_with_rate_limiter(self, _run, _cfg):
        limiter = MagicMock()
        result = _process_brew_search(("Firefox", "100.0"), rate_limiter=limiter)
        limiter.wait.assert_called_once()
        assert result == "Firefox"

    @patch("versiontracker.apps.matcher.get_config")
    @patch("versiontracker.apps.matcher.run_command", return_value=("", 0))
    def test_no_match(self, _run, _cfg):
        result = _process_brew_search(("SomeObscureApp", "1.0"))
        assert result is None

    def test_empty_app_name(self):
        result = _process_brew_search(("", "1.0"))
        assert result is None

    @patch("versiontracker.apps.matcher.get_config")
    @patch("versiontracker.apps.matcher.run_command", return_value=("Error", 1))
    def test_nonzero_return_empty_response(self, _run, _cfg):
        result = _process_brew_search(("Firefox", "1.0"))
        assert result is None

    @patch("versiontracker.apps.matcher.get_config")
    @patch("versiontracker.apps.matcher.run_command", side_effect=OSError("fail"))
    @patch("versiontracker.apps.matcher.search_brew_cask", return_value=["firefox"])
    def test_command_failure_falls_back_to_search_brew_cask(self, _search, _run, _cfg):
        result = _process_brew_search(("Firefox", "1.0"))
        assert result == "Firefox"

    @patch("versiontracker.apps.matcher.normalise_name", side_effect=RuntimeError("boom"))
    def test_outer_exception(self, _norm):
        result = _process_brew_search(("Firefox", "1.0"))
        assert result is None


# ---------------------------------------------------------------------------
# get_homebrew_cask_name
# ---------------------------------------------------------------------------


class TestGetHomebrewCaskName:
    """Tests for get_homebrew_cask_name()."""

    def test_empty_name_returns_none(self):
        assert get_homebrew_cask_name("") is None

    @patch("versiontracker.apps.matcher.read_cache", return_value={"cask_name": "firefox"})
    def test_cache_hit(self, _cache):
        assert get_homebrew_cask_name("Firefox") == "firefox"

    @patch("versiontracker.apps.matcher.write_cache")
    @patch("versiontracker.apps.matcher._process_brew_search", return_value=None)
    @patch("versiontracker.apps.matcher.read_cache", return_value=None)
    def test_caches_none_result(self, _read, _search, mock_write):
        result = get_homebrew_cask_name("Unknown App")
        assert result is None
        mock_write.assert_called_once()
        args = mock_write.call_args
        assert args[0][1] == {"cask_name": None}

    @patch("versiontracker.apps.matcher.write_cache")
    @patch("versiontracker.apps.matcher._process_brew_search", return_value="Firefox")
    @patch("versiontracker.apps.matcher.read_cache", return_value=None)
    def test_search_and_cache(self, _read, _search, mock_write):
        result = get_homebrew_cask_name("Firefox")
        assert result == "Firefox"
        mock_write.assert_called_once()

    @patch("versiontracker.apps.matcher.read_cache", return_value={"cask_name": "firefox"})
    def test_unicode_normalization(self, _cache):
        """Test that Unicode variants resolve to the same cache key."""
        result = get_homebrew_cask_name("\ufb01refox")  # fi ligature
        # Should still hit cache since NFKC normalizes the ligature
        assert result == "firefox"


# ---------------------------------------------------------------------------
# filter_brew_candidates
# ---------------------------------------------------------------------------


class TestFilterBrewCandidates:
    """Tests for filter_brew_candidates()."""

    def test_none_returns_all(self):
        data = [("a", "1", True), ("b", "2", False)]
        assert filter_brew_candidates(data) == data

    def test_true_returns_installable(self):
        data = [("a", "1", True), ("b", "2", False)]
        assert filter_brew_candidates(data, installable=True) == [("a", "1", True)]

    def test_false_returns_non_installable(self):
        data = [("a", "1", True), ("b", "2", False)]
        assert filter_brew_candidates(data, installable=False) == [("b", "2", False)]

    def test_empty_list(self):
        assert filter_brew_candidates([], installable=True) == []


# ---------------------------------------------------------------------------
# filter_out_brews
# ---------------------------------------------------------------------------


class TestFilterOutBrews:
    """Tests for filter_out_brews()."""

    @patch("versiontracker.apps.matcher.partial_ratio", return_value=50)
    def test_no_matches_returns_all(self, _ratio):
        apps = [("SomeUnique", "1.0"), ("AnotherUnique", "2.0")]
        result = filter_out_brews(apps, ["firefox", "chrome"])
        assert len(result) == 2

    @patch("versiontracker.apps.matcher.partial_ratio", return_value=90)
    def test_all_match_returns_empty(self, _ratio):
        apps = [("Firefox", "1.0"), ("Chrome", "2.0")]
        result = filter_out_brews(apps, ["firefox", "chrome"])
        assert result == []

    @patch("versiontracker.apps.matcher.partial_ratio", return_value=90)
    def test_strict_mode_skips_matched(self, _ratio):
        apps = [("Firefox", "1.0"), ("SomeUnique", "2.0")]
        result = filter_out_brews(apps, ["firefox", "someunique"], strict_mode=True)
        # strict mode: matched apps are skipped (break without adding to candidates)
        # All match in strict mode → all skipped → empty search_list
        assert result == []

    @patch("versiontracker.apps.matcher.partial_ratio", return_value=80)
    def test_partial_fuzzy_match(self, _ratio):
        apps = [("Firefox Browser", "1.0")]
        result = filter_out_brews(apps, ["firefox"])
        # Match (ratio > 75) means it does NOT appear in search_list
        assert len(result) == 0


# ---------------------------------------------------------------------------
# _wait_for_rate_limit
# ---------------------------------------------------------------------------


class TestWaitForRateLimit:
    """Tests for _wait_for_rate_limit()."""

    def test_none_does_nothing(self):
        _wait_for_rate_limit(None)  # should not raise

    def test_wrong_type_does_nothing(self):
        _wait_for_rate_limit("not a rate limiter")  # should not raise

    def test_simple_rate_limiter_calls_wait(self):
        from versiontracker.apps.cache import SimpleRateLimiter

        limiter = SimpleRateLimiter(0.0)
        with patch.object(limiter, "wait") as mock_wait:
            _wait_for_rate_limit(limiter)
            mock_wait.assert_called_once()

    def test_adaptive_rate_limiter_calls_wait(self):
        from versiontracker.apps.cache import _AdaptiveRateLimiter

        limiter = _AdaptiveRateLimiter(base_rate_limit_sec=0.0, min_rate_limit_sec=0.0, max_rate_limit_sec=0.0)
        with patch.object(limiter, "wait") as mock_wait:
            _wait_for_rate_limit(limiter)
            mock_wait.assert_called_once()


# ---------------------------------------------------------------------------
# _normalize_and_validate_search_term
# ---------------------------------------------------------------------------


class TestNormalizeAndValidateSearchTerm:
    """Tests for _normalize_and_validate_search_term()."""

    def test_valid_name(self):
        assert _normalize_and_validate_search_term("Firefox") is not None

    def test_empty_name(self):
        assert _normalize_and_validate_search_term("") is None


# ---------------------------------------------------------------------------
# _find_matching_cask
# ---------------------------------------------------------------------------


class TestFindMatchingCask:
    """Tests for _find_matching_cask()."""

    def test_exact_match(self):
        assert _find_matching_cask(["firefox"], "Firefox") == "firefox"

    def test_substring_app_in_result(self):
        result = _find_matching_cask(["firefox-developer-edition"], "Firefox")
        assert result == "firefox-developer-edition"

    def test_substring_result_in_app(self):
        result = _find_matching_cask(["chrome"], "Google Chrome Browser")
        assert result == "chrome"

    def test_fuzzy_match(self):
        # partial_ratio("firefox", "firefoxbrowser") >= 80
        result = _find_matching_cask(["firefoxbrowser"], "Firefox")
        assert result == "firefoxbrowser"

    def test_no_match(self):
        result = _find_matching_cask(["completely-different"], "Firefox")
        assert result is None

    def test_empty_results(self):
        assert _find_matching_cask([], "Firefox") is None

    def test_skips_empty_normalized(self):
        """Ensure results that normalize to empty strings are skipped."""
        result = _find_matching_cask(["", "firefox"], "Firefox")
        assert result == "firefox"


# ---------------------------------------------------------------------------
# _process_single_app_search
# ---------------------------------------------------------------------------


class TestProcessSingleAppSearch:
    """Tests for _process_single_app_search()."""

    @patch("versiontracker.apps.matcher.search_brew_cask", return_value=["firefox"])
    @patch("versiontracker.apps.matcher._wait_for_rate_limit")
    @patch("versiontracker.apps.finder.is_homebrew_available", return_value=True)
    def test_match_found(self, _hb, _wait, _search):
        result = _process_single_app_search("Firefox", None)
        assert result == "firefox"

    @patch("versiontracker.apps.matcher.search_brew_cask", return_value=[])
    @patch("versiontracker.apps.matcher._wait_for_rate_limit")
    @patch("versiontracker.apps.finder.is_homebrew_available", return_value=True)
    def test_no_results(self, _hb, _wait, _search):
        result = _process_single_app_search("SomeObscure", None)
        assert result is None

    @patch("versiontracker.apps.matcher._normalize_and_validate_search_term", return_value=None)
    @patch("versiontracker.apps.matcher._wait_for_rate_limit")
    def test_invalid_search_term(self, _wait, _norm):
        result = _process_single_app_search("", None)
        assert result is None

    @patch("versiontracker.apps.matcher.search_brew_cask", side_effect=RuntimeError("boom"))
    @patch("versiontracker.apps.matcher._wait_for_rate_limit")
    def test_exception_returns_none(self, _wait, _search):
        result = _process_single_app_search("Firefox", None)
        assert result is None


# ---------------------------------------------------------------------------
# _batch_process_brew_search
# ---------------------------------------------------------------------------


class TestBatchProcessBrewSearch:
    """Tests for _batch_process_brew_search()."""

    @patch("versiontracker.apps.matcher._process_single_app_search", return_value=None)
    def test_empty_batch(self, _search):
        result = _batch_process_brew_search([], None)
        assert result == []

    @patch("versiontracker.apps.matcher._process_single_app_search", side_effect=["firefox", None, "chrome"])
    def test_some_matches(self, _search):
        apps = [("Firefox", "1.0"), ("Unknown", "2.0"), ("Chrome", "3.0")]
        result = _batch_process_brew_search(apps, None)
        assert result == ["firefox", "chrome"]

    @patch("versiontracker.apps.matcher._process_single_app_search", return_value=None)
    def test_all_none(self, _search):
        apps = [("A", "1.0"), ("B", "2.0")]
        result = _batch_process_brew_search(apps, None)
        assert result == []
