"""Test module for async_homebrew functionality.

This module contains tests for the asynchronous Homebrew operations
provided by the async_homebrew.py module.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.mock_aiohttp_session import create_mock_session_factory, mock_aiohttp_session
from versiontracker.async_homebrew import (
    HomebrewBatchProcessor,
    HomebrewVersionChecker,
    async_check_brew_install_candidates,
    async_check_brew_update_candidates,
    async_get_cask_version,
    fetch_cask_info,
    search_casks,
)
from versiontracker.exceptions import NetworkError


@pytest.mark.asyncio
async def test_fetch_cask_info_success():
    """Test successful cask info fetching."""
    with patch(
        "versiontracker.async_homebrew.fetch_json",
        return_value={"name": "firefox", "version": "100.0"},
    ):
        result = await fetch_cask_info("firefox", use_cache=True)

        # Verify the result
        assert result == {"name": "firefox", "version": "100.0"}


@pytest.mark.asyncio
async def test_fetch_cask_info_not_found():
    """Test fetching info for a non-existent cask."""
    # Mock fetch_json to raise a 404 error
    mock_error = NetworkError("HTTP error 404: Not Found")

    with patch("versiontracker.async_homebrew.fetch_json", side_effect=mock_error):
        with pytest.raises(NetworkError):
            await fetch_cask_info("nonexistent-cask")


@pytest.mark.asyncio
async def test_search_casks_success():
    """Test successful cask searching."""
    # Mock search results
    mock_results = [
        {"token": "firefox-cask", "name": "Firefox"},
        {"token": "another-cask", "name": "Another App"},
    ]

    async with mock_aiohttp_session() as mock_session:
        # Setup mock response
        mock_session.add_response(
            "https://formulae.brew.sh/api/search.json?q=firefox", json_data=mock_results
        )

        session_factory = create_mock_session_factory(mock_session)

        with patch("versiontracker.async_homebrew.read_cache", return_value=None):
            with patch("versiontracker.async_homebrew.write_cache", return_value=True):
                with patch("aiohttp.ClientSession", session_factory):
                    results = await search_casks("firefox", use_cache=False)

                    # Verify the results
                    assert len(results) == 2
                    assert results[0]["token"] == "firefox-cask"
                    assert results[1]["token"] == "another-cask"


@pytest.mark.asyncio
async def test_search_casks_from_cache():
    """Test fetching search results from cache."""
    # Mock cached data
    cached_data = [{"token": "firefox-cask", "name": "Firefox"}]

    with patch("versiontracker.async_homebrew.read_cache", return_value=cached_data):
        results = await search_casks("firefox", use_cache=True)

        # Verify the results are from cache
        assert results == cached_data


class TestHomebrewBatchProcessor:
    """Tests for the HomebrewBatchProcessor class."""

    @pytest.mark.asyncio
    async def test_process_item_exact_match(self):
        """Test processing an item with an exact match."""
        processor = HomebrewBatchProcessor(rate_limit=0.01)  # Fast for testing

        # Mock the _check_exact_match method
        processor._check_exact_match = AsyncMock(return_value=True)

        # Process an item
        result = await processor.process_item(("Firefox", "100.0"))

        # Verify the result
        assert result == ("Firefox", "100.0", True)
        processor._check_exact_match.assert_called_once_with("firefox")

    @pytest.mark.asyncio
    async def test_process_item_fuzzy_match(self):
        """Test processing an item with a fuzzy match."""
        processor = HomebrewBatchProcessor(rate_limit=0.01, strict_match=False)

        # Mock the methods
        processor._check_exact_match = AsyncMock(return_value=False)
        processor._check_fuzzy_match = AsyncMock(return_value=True)

        # Process an item
        result = await processor.process_item(("Firefox", "100.0"))

        # Verify the result
        assert result == ("Firefox", "100.0", True)
        processor._check_exact_match.assert_called_once_with("firefox")
        processor._check_fuzzy_match.assert_called_once_with("Firefox")

    @pytest.mark.asyncio
    async def test_process_item_no_match(self):
        """Test processing an item with no match."""
        processor = HomebrewBatchProcessor(rate_limit=0.01)

        # Mock the methods
        processor._check_exact_match = AsyncMock(return_value=False)
        processor._check_fuzzy_match = AsyncMock(return_value=False)

        # Process an item
        result = await processor.process_item(("Firefox", "100.0"))

        # Verify the result
        assert result == ("Firefox", "100.0", False)

    @pytest.mark.asyncio
    async def test_process_item_error(self):
        """Test processing an item with an error."""
        processor = HomebrewBatchProcessor(rate_limit=0.01)

        # Mock the _check_exact_match method to raise an error
        processor._check_exact_match = AsyncMock(side_effect=NetworkError("Test error"))

        # Process an item
        result = await processor.process_item(("Firefox", "100.0"))

        # Verify the result
        assert result == ("Firefox", "100.0", False)

    def test_is_significant_match(self):
        """Test significant match detection."""
        processor = HomebrewBatchProcessor()

        # Test cases that should match
        assert processor._is_significant_match("Firefox", "firefox")
        assert processor._is_significant_match("Google Chrome", "google-chrome")
        assert (
            processor._is_significant_match("VSCode", "visual-studio-code") is False
        )  # Too short
        assert processor._is_significant_match(
            "Visual Studio Code", "visual-studio-code"
        )

        # Test cases that should not match
        assert processor._is_significant_match("Firefox", "chrome") is False
        assert processor._is_significant_match("A", "verylongname") is False


def test_async_get_cask_version():
    """Test getting a cask version."""
    # Mock the fetch_cask_info function to return a coroutine
    with patch(
        "versiontracker.async_homebrew.fetch_cask_info",
        new_callable=AsyncMock,
        return_value={"version": "100.0"},
    ):
        version = async_get_cask_version("firefox")

        # Verify the version
        assert version == "100.0"


def test_async_get_cask_version_not_found():
    """Test getting a version for a non-existent cask."""
    # Mock fetch_cask_info to raise a 404 error
    mock_error = NetworkError("HTTP error 404: Not Found")

    with patch(
        "versiontracker.async_homebrew.fetch_cask_info",
        new_callable=AsyncMock,
        side_effect=mock_error,
    ):
        version = async_get_cask_version("nonexistent-cask")

        # Verify the version is None
        assert version is None


class TestHomebrewVersionChecker:
    """Tests for the HomebrewVersionChecker class."""

    @pytest.mark.asyncio
    async def test_process_item(self):
        """Test processing an item."""
        checker = HomebrewVersionChecker(rate_limit=0.01)

        # Mock the async_get_cask_version function
        with patch(
            "versiontracker.async_homebrew.async_get_cask_version",
            new_callable=AsyncMock,
            return_value="101.0",
        ):
            result = await checker.process_item(("Firefox", "100.0", "firefox"))

            # Verify the result
            assert result == ("Firefox", "100.0", "firefox", "101.0")

    @pytest.mark.asyncio
    async def test_process_item_error(self):
        """Test processing an item with an error."""
        checker = HomebrewVersionChecker(rate_limit=0.01)

        # Mock async_get_cask_version to raise an error
        with patch(
            "versiontracker.async_homebrew.async_get_cask_version",
            side_effect=NetworkError("Test error"),
        ):
            result = await checker.process_item(("Firefox", "100.0", "firefox"))

            # Verify the result
            assert result == ("Firefox", "100.0", "firefox", None)


@pytest.mark.asyncio
async def test_async_check_brew_install_candidates():
    """Test checking brew install candidates."""
    # Mock the process_all method
    with patch(
        "versiontracker.async_homebrew.is_homebrew_available", return_value=True
    ):
        with patch.object(
            HomebrewBatchProcessor,
            "process_all",
            new_callable=AsyncMock,
            return_value=[("Firefox", "100.0", True)],
        ):
            # Access the underlying async function without the sync wrapper
            if hasattr(async_check_brew_install_candidates, "__wrapped__"):
                results = await async_check_brew_install_candidates.__wrapped__(
                    [("Firefox", "100.0")]
                )
            else:
                results = await async_check_brew_install_candidates(
                    [("Firefox", "100.0")]
                )

            # Verify the results
            assert results == [("Firefox", "100.0", True)]


@pytest.mark.asyncio
async def test_async_check_brew_install_candidates_no_homebrew():
    """Test checking brew install candidates when Homebrew is not available."""
    with patch(
        "versiontracker.async_homebrew.is_homebrew_available", return_value=False
    ):
        # Access the underlying async function without the sync wrapper
        if hasattr(async_check_brew_install_candidates, "__wrapped__"):
            results = await async_check_brew_install_candidates.__wrapped__(
                [("Firefox", "100.0")]
            )
        else:
            results = await async_check_brew_install_candidates([("Firefox", "100.0")])

        # Verify the results
        assert results == [("Firefox", "100.0", False)]
        # Verify the results


@pytest.mark.asyncio
async def test_async_check_brew_update_candidates():
    """Test checking brew update candidates."""
    # Mock the process_all method
    with patch(
        "versiontracker.async_homebrew.is_homebrew_available", return_value=True
    ):
        with patch.object(
            HomebrewVersionChecker,
            "process_all",
            new_callable=AsyncMock,
            return_value=[("Firefox", "100.0", "firefox", "101.0")],
        ):
            # Access the underlying async function without the sync wrapper
            if hasattr(async_check_brew_update_candidates, "__wrapped__"):
                results = await async_check_brew_update_candidates.__wrapped__(
                    [("Firefox", "100.0", "firefox")]
                )
            else:
                results = await async_check_brew_update_candidates(
                    [("Firefox", "100.0", "firefox")]
                )

            # Verify the results
            assert results == [("Firefox", "100.0", "firefox", "101.0")]


@pytest.mark.asyncio
async def test_async_check_brew_update_candidates_no_homebrew():
    """Test checking brew update candidates when Homebrew is not available."""
    with patch(
        "versiontracker.async_homebrew.is_homebrew_available", return_value=False
    ):
        # Access the underlying async function without the sync wrapper
        if hasattr(async_check_brew_update_candidates, "__wrapped__"):
            results = await async_check_brew_update_candidates.__wrapped__(
                [("Firefox", "100.0", "firefox")]
            )
        else:
            results = await async_check_brew_update_candidates(
                [("Firefox", "100.0", "firefox")]
            )

        # Verify the results
        assert results == [("Firefox", "100.0", "firefox", None)]
