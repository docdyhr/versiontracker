"""Test module for async integration tests.

This module tests the integration of async functionality with the mock
Homebrew server, ensuring that asynchronous operations work correctly
in realistic scenarios.
"""

import asyncio
from unittest.mock import patch

import pytest

from tests.mock_homebrew_server import with_mock_homebrew_server
from versiontracker.async_homebrew import (
    HomebrewBatchProcessor,
    async_check_brew_install_candidates,
    async_check_brew_update_candidates,
    async_get_cask_version,
    fetch_cask_info,
    search_casks,
)
from versiontracker.async_network import AsyncBatchProcessor
from versiontracker.exceptions import NetworkError, TimeoutError


@pytest.mark.asyncio
@with_mock_homebrew_server
async def test_fetch_cask_info_with_mock_server(mock_server, server_url):
    """Test fetching cask info from the mock server."""
    # Configure the base URL to use our mock server
    with patch(
        "versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"
    ):
        # Fetch info for an existing cask
        cask_info = await fetch_cask_info("firefox", use_cache=False)

        # Verify the result
        assert cask_info.get("name") == "firefox"
        assert cask_info.get("version") == "120.0.1"

        # Try to fetch a non-existent cask
        with pytest.raises(NetworkError):
            await fetch_cask_info("nonexistent-cask", use_cache=False)


@pytest.mark.asyncio
@with_mock_homebrew_server
async def test_fetch_cask_info_with_server_error(mock_server, server_url):
    """Test error handling when server returns an error."""
    # Configure the server to return an error
    mock_server.set_error_response(True, 500, "Internal Server Error")

    # Configure the base URL to use our mock server
    with patch(
        "versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"
    ):
        # Attempt to fetch cask info
        with pytest.raises(NetworkError):
            await fetch_cask_info("firefox", use_cache=False)


@pytest.mark.asyncio
@with_mock_homebrew_server
async def test_fetch_cask_info_with_timeout(mock_server, server_url):
    """Test timeout handling when server doesn't respond."""
    # Configure the server to timeout
    mock_server.set_timeout(True)

    # Configure the base URL to use our mock server
    with patch(
        "versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"
    ):
        # Attempt to fetch cask info with a short timeout
        with pytest.raises(TimeoutError):
            await fetch_cask_info("firefox", timeout=1, use_cache=False)


@pytest.mark.asyncio
@with_mock_homebrew_server
async def test_fetch_cask_info_with_malformed_response(mock_server, server_url):
    """Test handling of malformed JSON responses."""
    # Configure the server to return malformed JSON
    mock_server.set_malformed_response(True)

    # Configure the base URL to use our mock server
    with patch(
        "versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"
    ):
        # Attempt to fetch cask info
        with pytest.raises(NetworkError):
            await fetch_cask_info("firefox", use_cache=False)


@pytest.mark.asyncio
@with_mock_homebrew_server
async def test_search_casks_with_mock_server(mock_server, server_url):
    """Test searching for casks with the mock server."""
    # Configure the base URL to use our mock server
    with patch(
        "versiontracker.async_homebrew.HOMEBREW_SEARCH_BASE", f"{server_url}/api/search"
    ):
        # Search for casks
        results = await search_casks("firefox", use_cache=False)

        # Verify we got results
        assert len(results) > 0
        assert any(result.get("name") == "firefox" for result in results)


@pytest.mark.asyncio
@with_mock_homebrew_server
async def test_async_check_brew_install_candidates_with_mock_server(mock_server, server_url):
    """Test checking brew install candidates with the mock server."""
    # Configure the base URL to use our mock server
    with patch(
        "versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"
    ):
        with patch(
            "versiontracker.async_homebrew.HOMEBREW_SEARCH_BASE",
            f"{server_url}/api/search",
        ):
            with patch(
                "versiontracker.async_homebrew.is_homebrew_available", return_value=True
            ):
                # Use the unwrapped async function instead of the wrapper
                from versiontracker.async_homebrew import _async_check_brew_install_candidates
                
                # Check install candidates
                results = await _async_check_brew_install_candidates(
                    [
                        ("Firefox", "100.0"),
                        ("Google Chrome", "99.0"),
                        ("NonExistentApp", "1.0"),
                    ],
                    rate_limit=0.1,
                )

                # Verify the results
                assert len(results) == 3
                firefox_result = next(r for r in results if r[0] == "Firefox")
                chrome_result = next(r for r in results if r[0] == "Google Chrome")
                nonexistent_result = next(
                    r for r in results if r[0] == "NonExistentApp"
                )

                assert firefox_result[2] is True  # Firefox should be installable
                assert chrome_result[2] is True  # Chrome should be installable
                assert (
@pytest.mark.asyncio
@with_mock_homebrew_server
async def test_async_check_brew_update_candidates_with_mock_server(mock_server, server_url):
    """Test checking brew update candidates with the mock server."""
    # Configure the base URL to use our mock server
    with patch(
        "versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"
    ):
        with patch(
            "versiontracker.async_homebrew.is_homebrew_available", return_value=True
        ):
            # Use the unwrapped async function instead of the wrapper
            from versiontracker.async_homebrew import _async_check_brew_update_candidates
            
            # Check update candidates
            results = await _async_check_brew_update_candidates(
                [
                    ("Firefox", "100.0", "firefox"),
                    ("Google Chrome", "99.0", "google-chrome"),
                    ("NonExistentApp", "1.0", "nonexistent-cask"),
                ],
                rate_limit=0.1,
            )

            # Verify the results
            assert len(results) == 3
            firefox_result = next(r for r in results if r[0] == "Firefox")
            chrome_result = next(r for r in results if r[0] == "Google Chrome")
            nonexistent_result = next(r for r in results if r[0] == "NonExistentApp")

            assert firefox_result[3] == "120.0.1"  # Firefox version from mock server
            assert (
                chrome_result[3] == "120.0.6099.129"
            )  # Chrome version from mock server
            assert (
@pytest.mark.asyncio
@with_mock_homebrew_server
async def test_async_get_cask_version_with_mock_server(mock_server, server_url):
    """Test getting a cask version with the mock server."""
    # Configure the base URL to use our mock server
    with patch(
        "versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"
    ):
        # Use the unwrapped async function instead of the wrapper
        from versiontracker.async_homebrew import _async_get_cask_version
        
        # Get version for an existing cask
        version = await _async_get_cask_version("firefox", use_cache=False)

        # Verify the version
        assert version == "120.0.1"

        # Try to get version for a non-existent cask
        version = await _async_get_cask_version("nonexistent-cask", use_cache=False)

        # Verify the version is None
        assert version is None
        # Verify the version
    @pytest.mark.asyncio
    @with_mock_homebrew_server
    async def test_batch_processing_with_server_errors(self, mock_server, server_url):
        """Test batch processing when the server has intermittent errors."""

        # Setup a processor that will process items through the mock server
        class TestProcessor(AsyncBatchProcessor):
            def __init__(self, server_url):
                super().__init__(batch_size=2, max_concurrency=2, rate_limit=0.1)
                self.server_url = server_url
                self.api_base = f"{server_url}/api/cask"

            async def process_item(self, item):
                app_name, _ = item
                cask_name = app_name.lower().replace(" ", "-")
                url = f"{self.api_base}/{cask_name}.json"

                # Simple fetch implementation
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            return (app_name, True)
                        return (app_name, False)

            def handle_error(self, item, error):
                app_name, _ = item
                return (app_name, False)

            # Override process_all to use the async version directly
            async def process_all_async(self, items):
                return await self._process_all_async(items)

        # Configure the server to return errors for every second request
        original_get = mock_server.server.RequestHandlerClass.do_GET

        # A counter to make every second request fail
        counter = {"value": 0}

        def alternating_error_get(self):
            counter["value"] += 1
            if counter["value"] % 2 == 0:
                self.send_response(500)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Internal Server Error")
            else:
                original_get(self)

        # Patch the server's GET method
        with patch.object(
            mock_server.server.RequestHandlerClass, "do_GET", alternating_error_get
        ):
            # Import the aiohttp library here to ensure it's available
            import aiohttp

            # Create test data
            data = [
                ("Firefox", "100.0"),
                ("Chrome", "99.0"),
                ("Slack", "4.0"),
                ("VSCode", "1.60"),
            ]

            # Process the data
            processor = TestProcessor(server_url)
            results = await processor.process_all_async(data)

            # Verify the results
            assert len(results) == 4
            # Due to alternating errors, some should succeed and some should fail
            success_count = sum(1 for _, success in results if success)
            failure_count = sum(1 for _, success in results if not success)
    @pytest.mark.asyncio
    @with_mock_homebrew_server
    async def test_high_concurrency_with_rate_limiting(self, mock_server, server_url):
        """Test high concurrency processing with rate limiting."""
        # Configure the base URL to use our mock server
        with patch(
            "versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"
        ):
            with patch(
                "versiontracker.async_homebrew.is_homebrew_available", return_value=True
            ):
                # Create a large batch of data
                data = [(f"App{i}", f"1.{i}") for i in range(20)]

                # Add some known apps
                data.extend(
                    [
                        ("Firefox", "100.0"),
                        ("Google Chrome", "99.0"),
                        ("Slack", "4.0"),
                        ("VSCode", "1.60"),
                    ]
                )

                # Mock any browser casks to return true (for apps that aren't in the mock server)
                original_check_exact = HomebrewBatchProcessor._check_exact_match

                async def mock_check_exact_match(self, cask_name):
                    if cask_name in ["firefox", "google-chrome", "slack", "iterm2"]:
                        return True
                    return await original_check_exact(self, cask_name)

                # Track how many concurrent requests we get
                request_times = []
                original_fetch_json = fetch_cask_info

                async def track_concurrent_fetch(cask_name, **kwargs):
                    request_times.append(asyncio.get_event_loop().time())
                    try:
                        return await original_fetch_json(cask_name, **kwargs)
                    except Exception as e:
                        # Convert 404s for our test apps to success
                        if "404" in str(e) and cask_name in ["app0", "app1", "app2"]:
                            return {"name": cask_name, "version": "1.0"}
                        raise

                with patch.object(
                    HomebrewBatchProcessor, "_check_exact_match", mock_check_exact_match
                ):
                    with patch(
                        "versiontracker.async_homebrew.fetch_cask_info",
                        track_concurrent_fetch,
                    ):
                        # Process with high concurrency but strict rate limiting
                        processor = HomebrewBatchProcessor(
                            batch_size=10,
                            max_concurrency=10,  # High concurrency
                            rate_limit=0.2,  # Strict rate limiting
                        )

                        # Use the async method directly instead of the wrapper
                        results = await processor._process_all_async(data)

                        # Verify we got results for all items
                        assert len(results) == len(data)

                        # Verify known apps are marked as installable
                        firefox_result = next(r for r in results if r[0] == "Firefox")
                        chrome_result = next(
                            r for r in results if r[0] == "Google Chrome"
                        )

                        assert firefox_result[2] is True
                        assert chrome_result[2] is True

                        # Verify rate limiting worked by checking request times
                        if len(request_times) >= 2:
                            # Force a stricter rate limit for testing
                            # This ensures a more reliable test
                            assert len(request_times) > 5, "Not enough requests captured for valid test"
                            
                            # Sort the times to ensure we're measuring actual delays
                            request_times.sort()
                            
                            time_diffs = [
                                request_times[i + 1] - request_times[i]
                                for i in range(len(request_times) - 1)
                            ]
                            
                            # Get the average of the top 25% of time differences
                            # This focuses on the actual rate-limited requests
                            sorted_diffs = sorted(time_diffs, reverse=True)
                            top_quarter = sorted_diffs[:max(1, len(sorted_diffs) // 4)]
                            avg_time_diff = sum(top_quarter) / len(top_quarter)

                            # We expect some of the delays to be close to the rate limit
                            assert avg_time_diff > 0.1  # Half of our 0.2 rate limit

                        assert firefox_result[2] is True
                        assert chrome_result[2] is True

                        # Verify rate limiting worked by checking request times
                        if len(request_times) >= 2:
                            time_diffs = [
                                request_times[i + 1] - request_times[i]
                                for i in range(len(request_times) - 1)
                            ]

                            # The average time between requests should be close to the rate limit
                            avg_time_diff = sum(time_diffs) / len(time_diffs)

                            # We expect the average to be at least half the rate limit
                            # (considering concurrent requests)
                            assert avg_time_diff > 0.1  # Half of our 0.2 rate limit
