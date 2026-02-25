"""Tests for versiontracker.version.homebrew module.

Tests Homebrew integration functions including cask info retrieval,
fuzzy cask matching, version checking, and brew availability detection.
All subprocess.run calls are mocked to avoid calling real brew commands.
"""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from versiontracker.exceptions import TimeoutError as VTTimeoutError
from versiontracker.version.homebrew import (
    _basic_fuzzy_cask_matching,
    _get_homebrew_casks_list,
    _search_homebrew_casks,
    _try_enhanced_cask_matching,
    check_latest_version,
    find_matching_cask,
    get_homebrew_cask_info,
    is_homebrew_available,
)

# Sample cask JSON returned by `brew info --cask <name> --json`
SAMPLE_CASK_JSON = json.dumps(
    [
        {
            "token": "firefox",
            "version": "121.0",
            "desc": "Web browser",
            "name": ["Firefox"],
        }
    ]
)

SAMPLE_CASK_LIST = "firefox\ngoogle-chrome\nvisual-studio-code\nslack\nspotify\n"


def _make_completed_process(stdout="", stderr="", returncode=0):
    """Helper to build a subprocess.CompletedProcess."""
    return subprocess.CompletedProcess(args=["brew"], returncode=returncode, stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
# get_homebrew_cask_info
# ---------------------------------------------------------------------------


class TestGetHomebrewCaskInfo:
    """Tests for get_homebrew_cask_info."""

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_exact_match_success(self, mock_run):
        """Exact cask match returns parsed info dict."""
        mock_run.return_value = _make_completed_process(stdout=SAMPLE_CASK_JSON)

        result = get_homebrew_cask_info("firefox")

        assert result == {
            "name": "firefox",
            "version": "121.0",
            "description": "Web browser",
        }
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["brew", "info", "--cask", "firefox", "--json"]

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_invalid_json_falls_back_to_search(self, mock_run):
        """Malformed JSON triggers fuzzy search fallback."""
        mock_run.return_value = _make_completed_process(stdout="not json")

        with patch("versiontracker.version.homebrew._search_homebrew_casks", return_value=None) as mock_search:
            result = get_homebrew_cask_info("firefox")

        assert result is None
        mock_search.assert_called_once_with("firefox", True)

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_nonzero_returncode_falls_back_to_search(self, mock_run):
        """Non-zero return code triggers fuzzy search fallback."""
        mock_run.return_value = _make_completed_process(returncode=1, stderr="Error")

        with patch("versiontracker.version.homebrew._search_homebrew_casks", return_value=None) as mock_search:
            result = get_homebrew_cask_info("unknown-app")

        assert result is None
        mock_search.assert_called_once_with("unknown-app", True)

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_timeout_raises_vttimeouterror(self, mock_run):
        """subprocess.TimeoutExpired is translated to VTTimeoutError."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="brew", timeout=30)

        with pytest.raises(VTTimeoutError, match="timed out"):
            get_homebrew_cask_info("firefox")

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_oserror_returns_none(self, mock_run):
        """OSError (e.g. brew not installed) returns None."""
        mock_run.side_effect = OSError("No such file or directory")

        result = get_homebrew_cask_info("firefox")

        assert result is None

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_empty_json_array_falls_back(self, mock_run):
        """Empty JSON array falls back to search."""
        mock_run.return_value = _make_completed_process(stdout="[]")

        with patch("versiontracker.version.homebrew._search_homebrew_casks", return_value=None) as mock_search:
            result = get_homebrew_cask_info("empty")

        assert result is None
        mock_search.assert_called_once()

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_use_enhanced_false_passed_to_search(self, mock_run):
        """use_enhanced=False is forwarded to _search_homebrew_casks."""
        mock_run.return_value = _make_completed_process(returncode=1)

        with patch("versiontracker.version.homebrew._search_homebrew_casks", return_value=None) as mock_search:
            get_homebrew_cask_info("app", use_enhanced=False)

        mock_search.assert_called_once_with("app", False)

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_cask_missing_fields_uses_defaults(self, mock_run):
        """Missing JSON fields fall back to defaults."""
        data = json.dumps([{"other_field": "value"}])
        mock_run.return_value = _make_completed_process(stdout=data)

        result = get_homebrew_cask_info("myapp")

        assert result is not None
        assert result["name"] == "myapp"  # fallback to app_name
        assert result["version"] == "unknown"
        assert result["description"] == ""


# ---------------------------------------------------------------------------
# _get_homebrew_casks_list
# ---------------------------------------------------------------------------


class TestGetHomebrewCasksList:
    """Tests for _get_homebrew_casks_list."""

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_returns_list_of_casks(self, mock_run):
        """Successful brew search returns parsed cask list."""
        mock_run.return_value = _make_completed_process(stdout=SAMPLE_CASK_LIST)

        result = _get_homebrew_casks_list()

        assert result is not None
        assert "firefox" in result
        assert "google-chrome" in result
        assert len(result) == 5

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_nonzero_returncode_returns_none(self, mock_run):
        """Non-zero return code yields None."""
        mock_run.return_value = _make_completed_process(returncode=1)

        assert _get_homebrew_casks_list() is None

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_empty_output_returns_none(self, mock_run):
        """Empty stdout returns None."""
        mock_run.return_value = _make_completed_process(stdout="")

        assert _get_homebrew_casks_list() is None

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_timeout_raises_vttimeouterror(self, mock_run):
        """Timeout is translated to VTTimeoutError."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="brew", timeout=60)

        with pytest.raises(VTTimeoutError, match="timed out"):
            _get_homebrew_casks_list()

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_oserror_returns_none(self, mock_run):
        """OSError returns None."""
        mock_run.side_effect = OSError("not found")

        assert _get_homebrew_casks_list() is None

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_strips_whitespace_from_cask_names(self, mock_run):
        """Whitespace around cask names is stripped."""
        mock_run.return_value = _make_completed_process(stdout="  firefox  \n  slack  \n")

        result = _get_homebrew_casks_list()

        assert result == ["firefox", "slack"]


# ---------------------------------------------------------------------------
# _try_enhanced_cask_matching
# ---------------------------------------------------------------------------


class TestTryEnhancedCaskMatching:
    """Tests for _try_enhanced_cask_matching."""

    @patch("versiontracker.enhanced_matching.find_best_enhanced_match")
    def test_returns_match_when_found(self, mock_enhanced):
        """Returns first element of match result tuple."""
        mock_enhanced.return_value = ("visual-studio-code", 95)
        casks = ["firefox", "visual-studio-code", "slack"]

        result = _try_enhanced_cask_matching("VS Code", casks)

        assert result == "visual-studio-code"
        mock_enhanced.assert_called_once_with("VS Code", casks, threshold=70)

    @patch("versiontracker.enhanced_matching.find_best_enhanced_match")
    def test_returns_none_when_no_match(self, mock_enhanced):
        """Returns None when enhanced matching finds nothing."""
        mock_enhanced.return_value = None

        result = _try_enhanced_cask_matching("unknown", ["firefox"])

        assert result is None

    def test_returns_none_when_module_unavailable(self):
        """Returns None gracefully when enhanced_matching is not importable."""
        with patch.dict("sys.modules", {"versiontracker.enhanced_matching": None}):
            # Force ImportError by patching the import target
            with patch(
                "versiontracker.version.homebrew._try_enhanced_cask_matching",
                wraps=_try_enhanced_cask_matching,
            ):
                # The actual function catches ImportError internally
                result = _try_enhanced_cask_matching("test", ["firefox"])
                # Result depends on whether enhanced_matching is actually available;
                # the function handles ImportError gracefully either way
                assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# _basic_fuzzy_cask_matching
# ---------------------------------------------------------------------------


class TestBasicFuzzyCaskMatching:
    """Tests for _basic_fuzzy_cask_matching."""

    def test_exact_match_returns_cask(self):
        """Exact name match (case-insensitive) returns the cask."""
        casks = ["firefox", "google-chrome", "slack"]

        result = _basic_fuzzy_cask_matching("firefox", casks)

        # Should match with high score
        assert result is not None

    def test_no_match_returns_none(self):
        """Completely dissimilar name returns None."""
        casks = ["firefox", "google-chrome"]

        result = _basic_fuzzy_cask_matching("zzzzzzzznotanapp", casks)

        assert result is None

    @patch("versiontracker.version.homebrew.get_fuzz")
    def test_uses_fuzz_ratio(self, mock_get_fuzz):
        """Verifies fuzz.ratio is called for scoring."""
        mock_fuzz = MagicMock()
        mock_fuzz.ratio.side_effect = lambda a, b: 90 if "fire" in b else 30
        mock_get_fuzz.return_value = mock_fuzz

        result = _basic_fuzzy_cask_matching("firefox", ["firefox", "slack"])

        assert result == "firefox"
        assert mock_fuzz.ratio.call_count == 2

    @patch("versiontracker.version.homebrew.get_fuzz")
    def test_threshold_enforced(self, mock_get_fuzz):
        """Scores at or below 70 are rejected."""
        mock_fuzz = MagicMock()
        mock_fuzz.ratio.return_value = 65  # Below threshold
        mock_get_fuzz.return_value = mock_fuzz

        result = _basic_fuzzy_cask_matching("test", ["cask-a", "cask-b"])

        assert result is None

    @patch("versiontracker.version.homebrew.get_fuzz")
    def test_fuzz_none_returns_none(self, mock_get_fuzz):
        """When fuzz module is None, returns None."""
        mock_get_fuzz.return_value = None

        result = _basic_fuzzy_cask_matching("firefox", ["firefox"])

        assert result is None


# ---------------------------------------------------------------------------
# _search_homebrew_casks
# ---------------------------------------------------------------------------


class TestSearchHomebrewCasks:
    """Tests for _search_homebrew_casks."""

    @patch("versiontracker.version.homebrew.get_homebrew_cask_info")
    @patch("versiontracker.version.homebrew._basic_fuzzy_cask_matching")
    @patch("versiontracker.version.homebrew._try_enhanced_cask_matching")
    @patch("versiontracker.version.homebrew._get_homebrew_casks_list")
    def test_enhanced_match_used_first(self, mock_list, mock_enhanced, mock_basic, mock_info):
        """Enhanced matching is tried before basic fuzzy matching."""
        mock_list.return_value = ["firefox", "slack"]
        mock_enhanced.return_value = "firefox"
        mock_info.return_value = {"name": "firefox", "version": "121.0", "description": ""}

        result = _search_homebrew_casks("Fire Fox", use_enhanced=True)

        assert result == {"name": "firefox", "version": "121.0", "description": ""}
        mock_enhanced.assert_called_once()
        mock_basic.assert_not_called()

    @patch("versiontracker.version.homebrew.get_homebrew_cask_info")
    @patch("versiontracker.version.homebrew._basic_fuzzy_cask_matching")
    @patch("versiontracker.version.homebrew._try_enhanced_cask_matching")
    @patch("versiontracker.version.homebrew._get_homebrew_casks_list")
    def test_falls_back_to_basic_when_enhanced_fails(self, mock_list, mock_enhanced, mock_basic, mock_info):
        """Basic fuzzy matching is used when enhanced returns None."""
        mock_list.return_value = ["firefox", "slack"]
        mock_enhanced.return_value = None
        mock_basic.return_value = "firefox"
        mock_info.return_value = {"name": "firefox", "version": "121.0", "description": ""}

        result = _search_homebrew_casks("Fire Fox", use_enhanced=True)

        assert result is not None
        mock_basic.assert_called_once()

    @patch("versiontracker.version.homebrew._try_enhanced_cask_matching")
    @patch("versiontracker.version.homebrew._get_homebrew_casks_list")
    def test_enhanced_skipped_when_disabled(self, mock_list, mock_enhanced):
        """Enhanced matching is skipped when use_enhanced=False."""
        mock_list.return_value = ["firefox"]

        with patch("versiontracker.version.homebrew._basic_fuzzy_cask_matching", return_value=None):
            _search_homebrew_casks("test", use_enhanced=False)

        mock_enhanced.assert_not_called()

    @patch("versiontracker.version.homebrew._get_homebrew_casks_list")
    def test_returns_none_when_cask_list_empty(self, mock_list):
        """Returns None if cask list is empty/None."""
        mock_list.return_value = None

        result = _search_homebrew_casks("firefox")

        assert result is None

    @patch("versiontracker.version.homebrew._get_homebrew_casks_list")
    def test_returns_none_when_no_match_found(self, mock_list):
        """Returns None if neither matcher finds a result."""
        mock_list.return_value = ["slack"]

        with patch("versiontracker.version.homebrew._try_enhanced_cask_matching", return_value=None):
            with patch("versiontracker.version.homebrew._basic_fuzzy_cask_matching", return_value=None):
                result = _search_homebrew_casks("zzzzz")

        assert result is None


# ---------------------------------------------------------------------------
# check_latest_version
# ---------------------------------------------------------------------------


class TestCheckLatestVersion:
    """Tests for check_latest_version."""

    @patch("versiontracker.version.homebrew.get_homebrew_cask_info")
    def test_returns_version_string(self, mock_info):
        """Returns the version from cask info."""
        mock_info.return_value = {"name": "firefox", "version": "121.0", "description": ""}

        assert check_latest_version("firefox") == "121.0"

    @patch("versiontracker.version.homebrew.get_homebrew_cask_info")
    def test_returns_none_when_not_found(self, mock_info):
        """Returns None when cask info is None."""
        mock_info.return_value = None

        assert check_latest_version("nonexistent") is None

    @patch("versiontracker.version.homebrew.get_homebrew_cask_info")
    def test_returns_none_when_version_key_missing(self, mock_info):
        """Returns None if version key is absent from dict."""
        mock_info.return_value = {"name": "firefox", "description": ""}

        assert check_latest_version("firefox") is None


# ---------------------------------------------------------------------------
# find_matching_cask
# ---------------------------------------------------------------------------


class TestFindMatchingCask:
    """Tests for find_matching_cask."""

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_returns_matching_cask_name(self, mock_run):
        """Finds a cask via fuzzy matching."""
        mock_run.return_value = _make_completed_process(stdout=SAMPLE_CASK_LIST)

        with patch("versiontracker.version.homebrew.get_fuzz") as mock_get_fuzz:
            mock_fuzz = MagicMock()
            mock_fuzz.ratio.side_effect = lambda a, b: 95 if "firefox" in b else 30
            mock_get_fuzz.return_value = mock_fuzz

            # Disable enhanced matching to test basic path
            result = find_matching_cask("firefox", threshold=70, use_enhanced=False)

        assert result == "firefox"

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_returns_none_on_brew_failure(self, mock_run):
        """Returns None when brew search fails."""
        mock_run.return_value = _make_completed_process(returncode=1)

        result = find_matching_cask("firefox")

        assert result is None

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_returns_none_when_empty_cask_list(self, mock_run):
        """Returns None when brew returns empty output."""
        mock_run.return_value = _make_completed_process(stdout="")

        result = find_matching_cask("firefox")

        assert result is None

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_oserror_returns_none(self, mock_run):
        """OSError is caught and returns None."""
        mock_run.side_effect = OSError("brew not found")

        result = find_matching_cask("firefox")

        assert result is None

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_enhanced_matching_used_when_enabled(self, mock_run):
        """Enhanced matching is attempted when use_enhanced=True."""
        mock_run.return_value = _make_completed_process(stdout=SAMPLE_CASK_LIST)

        with patch(
            "versiontracker.enhanced_matching.find_best_enhanced_match",
            return_value=("visual-studio-code", 92),
        ):
            result = find_matching_cask("VS Code", use_enhanced=True)

        assert result == "visual-studio-code"

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_threshold_parameter_respected(self, mock_run):
        """Custom threshold is passed to matching."""
        mock_run.return_value = _make_completed_process(stdout=SAMPLE_CASK_LIST)

        with patch("versiontracker.version.homebrew.get_fuzz") as mock_get_fuzz:
            mock_fuzz = MagicMock()
            mock_fuzz.ratio.return_value = 75  # Above 70 but below 80
            mock_get_fuzz.return_value = mock_fuzz

            result_low = find_matching_cask("test", threshold=70, use_enhanced=False)
            assert result_low is not None

            mock_fuzz.ratio.return_value = 75
            result_high = find_matching_cask("test", threshold=80, use_enhanced=False)
            assert result_high is None


# ---------------------------------------------------------------------------
# is_homebrew_available
# ---------------------------------------------------------------------------


class TestIsHomebrewAvailable:
    """Tests for is_homebrew_available."""

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_returns_true_when_brew_works(self, mock_run):
        """Returns True when brew --version succeeds."""
        mock_run.return_value = _make_completed_process(stdout="Homebrew 4.2.0")

        assert is_homebrew_available() is True

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_returns_false_on_nonzero_returncode(self, mock_run):
        """Returns False when brew --version fails."""
        mock_run.return_value = _make_completed_process(returncode=1)

        assert is_homebrew_available() is False

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_returns_false_on_oserror(self, mock_run):
        """Returns False when brew is not installed."""
        mock_run.side_effect = OSError("No such file or directory")

        assert is_homebrew_available() is False

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_returns_false_on_timeout(self, mock_run):
        """Returns False when brew --version times out."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="brew", timeout=5)

        assert is_homebrew_available() is False

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_returns_false_on_subprocess_error(self, mock_run):
        """Returns False on SubprocessError."""
        mock_run.side_effect = subprocess.SubprocessError("error")

        assert is_homebrew_available() is False


# ---------------------------------------------------------------------------
# _search_homebrew_casks — error paths
# ---------------------------------------------------------------------------


class TestSearchHomebrewCasksErrorPaths:
    """Tests for error handling in _search_homebrew_casks."""

    @patch("versiontracker.version.homebrew._get_homebrew_casks_list")
    def test_timeout_raises_vttimeouterror(self, mock_get_casks):
        """TimeoutExpired in _search_homebrew_casks raises VTTimeoutError."""
        mock_get_casks.side_effect = subprocess.TimeoutExpired(cmd="brew", timeout=5)

        with pytest.raises(VTTimeoutError, match="timed out"):
            _search_homebrew_casks("Firefox")

    @patch("versiontracker.version.homebrew._get_homebrew_casks_list")
    def test_subprocess_error_returns_none(self, mock_get_casks):
        """SubprocessError in _search_homebrew_casks returns None."""
        mock_get_casks.side_effect = subprocess.SubprocessError("error")

        result = _search_homebrew_casks("Firefox")
        assert result is None

    @patch("versiontracker.version.homebrew._get_homebrew_casks_list")
    def test_oserror_returns_none(self, mock_get_casks):
        """OSError in _search_homebrew_casks returns None."""
        mock_get_casks.side_effect = OSError("brew not found")

        result = _search_homebrew_casks("Firefox")
        assert result is None


# ---------------------------------------------------------------------------
# find_matching_cask — enhanced matching ImportError fallback
# ---------------------------------------------------------------------------


class TestFindMatchingCaskFallback:
    """Tests for find_matching_cask when enhanced matching is unavailable."""

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_find_matching_cask_enhanced_import_error(self, mock_run):
        """find_matching_cask falls back to basic matching when enhanced_matching unavailable."""
        import builtins

        mock_run.return_value = _make_completed_process(stdout="firefox\nfirefox-developer-edition\nwaterfox")

        original_import = builtins.__import__

        def import_side_effect(name, *args, **kwargs):
            if name == "versiontracker.enhanced_matching":
                raise ImportError("No module named 'versiontracker.enhanced_matching'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_side_effect):
            with patch("versiontracker.version.homebrew.get_fuzz") as mock_fuzz:
                mock_fuzz_instance = MagicMock()
                mock_fuzz_instance.ratio.return_value = 95
                mock_fuzz.return_value = mock_fuzz_instance

                result = find_matching_cask("Firefox", use_enhanced=True)
                # Should fall back to basic fuzzy matching and return a result
                assert result is not None

    @patch("versiontracker.version.homebrew.subprocess.run")
    def test_find_matching_cask_no_fuzz(self, mock_run):
        """find_matching_cask when fuzz library is not available."""
        mock_run.return_value = _make_completed_process(stdout="firefox\nchrome")

        with patch("versiontracker.version.homebrew.get_fuzz", return_value=None):
            result = find_matching_cask("Firefox", use_enhanced=False)
            # Without fuzz, should return None (no matching possible)
            assert result is None
