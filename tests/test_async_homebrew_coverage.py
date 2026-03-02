"""Tests for versiontracker.async_homebrew — coverage improvement.

Targets uncovered exception paths in search_casks() and uncovered
methods in HomebrewBatchProcessor (fuzzy match, empty app, NetworkError).
"""

import builtins
from unittest.mock import MagicMock, patch

import pytest
from aiohttp import ClientError, ClientResponseError

from versiontracker.async_homebrew import (
    HomebrewBatchProcessor,
    search_casks,
)
from versiontracker.exceptions import HomebrewError, NetworkError
from versiontracker.exceptions import TimeoutError as VTTimeoutError

# ---------------------------------------------------------------------------
# Helper: create a session factory whose .get() raises the given exception
# ---------------------------------------------------------------------------


def _make_error_session_factory(error: Exception):
    """Return a factory for aiohttp.ClientSession that raises on .get()."""

    class _ErrorSession:
        """Session mock whose get() raises an error."""

        def get(self, url, **kwargs):
            raise error

        async def close(self):
            pass

    class _ErrorClientSession:
        def __init__(self, *args, **kwargs):
            self._session = _ErrorSession()

        async def __aenter__(self):
            return self._session

        async def __aexit__(self, *args):
            pass

    return _ErrorClientSession


# ---------------------------------------------------------------------------
# search_casks — exception paths
# ---------------------------------------------------------------------------


class TestSearchCasksExceptions:
    """Tests for search_casks() error handling branches."""

    @pytest.mark.asyncio
    async def test_builtin_timeout_error(self):
        """search_casks raises VT TimeoutError on builtins.TimeoutError (lines 102-104)."""
        factory = _make_error_session_factory(builtins.TimeoutError("connection timed out"))

        with patch("versiontracker.async_homebrew.read_cache", return_value=None):
            with patch("aiohttp.ClientSession", factory):
                with pytest.raises(VTTimeoutError, match="Search request timed out"):
                    await search_casks("firefox", use_cache=False)

    @pytest.mark.asyncio
    async def test_client_response_error(self):
        """search_casks raises NetworkError on ClientResponseError (lines 105-107)."""
        error = ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=503,
            message="Service Unavailable",
        )
        factory = _make_error_session_factory(error)

        with patch("versiontracker.async_homebrew.read_cache", return_value=None):
            with patch("aiohttp.ClientSession", factory):
                with pytest.raises(NetworkError, match="HTTP error 503"):
                    await search_casks("firefox", use_cache=False)

    @pytest.mark.asyncio
    async def test_client_error(self):
        """search_casks raises NetworkError on ClientError (lines 108-110)."""
        factory = _make_error_session_factory(ClientError("connection reset"))

        with patch("versiontracker.async_homebrew.read_cache", return_value=None):
            with patch("aiohttp.ClientSession", factory):
                with pytest.raises(NetworkError, match="Network error"):
                    await search_casks("firefox", use_cache=False)


# ---------------------------------------------------------------------------
# HomebrewBatchProcessor._check_fuzzy_match
# ---------------------------------------------------------------------------


class TestHomebrewBatchProcessorFuzzyMatch:
    """Tests for HomebrewBatchProcessor._check_fuzzy_match()."""

    @pytest.mark.asyncio
    async def test_fuzzy_match_with_matching_cask(self):
        """_check_fuzzy_match returns True when search returns a significant match (lines 208-213)."""
        processor = HomebrewBatchProcessor(use_cache=False, strict_match=False)
        # search_casks returns results with a token that significantly matches "Firefox"
        mock_results = [{"token": "firefox", "name": "Firefox"}]
        with patch("versiontracker.async_homebrew.search_casks", return_value=mock_results):
            result = await processor._check_fuzzy_match("Firefox")
            assert result is True

    @pytest.mark.asyncio
    async def test_fuzzy_match_with_empty_results(self):
        """_check_fuzzy_match returns False when search returns empty list."""
        processor = HomebrewBatchProcessor(use_cache=False, strict_match=False)
        with patch("versiontracker.async_homebrew.search_casks", return_value=[]):
            result = await processor._check_fuzzy_match("SomeObscureApp")
            assert result is False

    @pytest.mark.asyncio
    async def test_fuzzy_match_no_significant_match(self):
        """_check_fuzzy_match returns False when results don't significantly match."""
        processor = HomebrewBatchProcessor(use_cache=False, strict_match=False)
        # Token "completely-different-tool" does not significantly match "Firefox"
        mock_results = [{"token": "completely-different-tool", "name": "Other"}]
        with patch("versiontracker.async_homebrew.search_casks", return_value=mock_results):
            result = await processor._check_fuzzy_match("Firefox")
            assert result is False


# ---------------------------------------------------------------------------
# HomebrewBatchProcessor.process_item
# ---------------------------------------------------------------------------


class TestHomebrewBatchProcessorProcessItem:
    """Tests for HomebrewBatchProcessor.process_item()."""

    @pytest.mark.asyncio
    async def test_empty_app_name_returns_false(self):
        """process_item returns (app_name, version, False) for empty app names."""
        processor = HomebrewBatchProcessor(use_cache=False)
        result = await processor.process_item(("", "1.0"))
        assert result == ("", "1.0", False)

    @pytest.mark.asyncio
    async def test_network_error_returns_false(self):
        """process_item catches NetworkError and returns False."""
        processor = HomebrewBatchProcessor(use_cache=False, strict_match=True)
        with patch.object(
            processor,
            "_check_exact_match",
            side_effect=NetworkError("connection refused"),
        ):
            result = await processor.process_item(("TestApp", "2.0"))
            assert result == ("TestApp", "2.0", False)

    @pytest.mark.asyncio
    async def test_timeout_error_returns_false(self):
        """process_item catches TimeoutError and returns False."""
        processor = HomebrewBatchProcessor(use_cache=False, strict_match=True)
        with patch.object(
            processor,
            "_check_exact_match",
            side_effect=VTTimeoutError("timed out"),
        ):
            result = await processor.process_item(("TestApp", "2.0"))
            assert result == ("TestApp", "2.0", False)

    @pytest.mark.asyncio
    async def test_homebrew_error_returns_false(self):
        """process_item catches HomebrewError and returns False."""
        processor = HomebrewBatchProcessor(use_cache=False, strict_match=True)
        with patch.object(
            processor,
            "_check_exact_match",
            side_effect=HomebrewError("brew failed"),
        ):
            result = await processor.process_item(("TestApp", "2.0"))
            assert result == ("TestApp", "2.0", False)

    @pytest.mark.asyncio
    async def test_exact_match_found(self):
        """process_item returns True when exact match succeeds."""
        processor = HomebrewBatchProcessor(use_cache=False, strict_match=True)
        with patch.object(processor, "_check_exact_match", return_value=True):
            result = await processor.process_item(("Firefox", "100.0"))
            assert result == ("Firefox", "100.0", True)

    @pytest.mark.asyncio
    async def test_no_exact_match_falls_through_to_fuzzy(self):
        """process_item tries fuzzy match when exact fails and strict_match=False."""
        processor = HomebrewBatchProcessor(use_cache=False, strict_match=False)
        with patch.object(processor, "_check_exact_match", return_value=False):
            with patch.object(processor, "_check_fuzzy_match", return_value=True):
                result = await processor.process_item(("Firefox", "100.0"))
                assert result == ("Firefox", "100.0", True)


# ---------------------------------------------------------------------------
# HomebrewBatchProcessor.handle_error
# ---------------------------------------------------------------------------


class TestHomebrewBatchProcessorHandleError:
    """Tests for HomebrewBatchProcessor.handle_error()."""

    def test_handle_error_returns_false(self):
        """handle_error returns (app_name, version, False) tuple."""
        processor = HomebrewBatchProcessor()
        result = processor.handle_error(("MyApp", "1.0"), RuntimeError("fail"))
        assert result == ("MyApp", "1.0", False)


# ---------------------------------------------------------------------------
# HomebrewBatchProcessor._is_significant_match
# ---------------------------------------------------------------------------


class TestIsSignificantMatch:
    """Tests for _is_significant_match()."""

    def test_exact_match(self):
        processor = HomebrewBatchProcessor()
        assert processor._is_significant_match("firefox", "firefox") is True

    def test_contained_with_low_ratio(self):
        processor = HomebrewBatchProcessor()
        # "firefox" (7 chars) vs "firefoxbrowser" (14 chars) — ratio 0.5 < 0.6
        assert processor._is_significant_match("firefox", "firefox-browser") is False

    def test_no_overlap(self):
        processor = HomebrewBatchProcessor()
        assert processor._is_significant_match("chrome", "firefox") is False

    def test_partial_contained_below_threshold(self):
        processor = HomebrewBatchProcessor()
        # "vlc" (3 chars) in "vlcmedia" (8 chars) — ratio 3/8 = 0.375 < 0.6
        assert processor._is_significant_match("vlc", "vlcmedia") is False

    def test_close_length_match(self):
        processor = HomebrewBatchProcessor()
        # "iterm2" vs "iterm" — contained, ratio 5/6 = 0.83 > 0.6
        assert processor._is_significant_match("iTerm2", "iterm") is True
