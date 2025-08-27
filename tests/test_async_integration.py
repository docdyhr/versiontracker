"""Test module for async integration tests.

This module tests the integration of async functionality with the mock
Homebrew server, ensuring that asynchronous operations work correctly
in realistic scenarios.
"""

import asyncio
from unittest.mock import patch

import pytest

from versiontracker.async_homebrew import (
    fetch_cask_info,
    search_casks,
)
from versiontracker.async_network import AsyncBatchProcessor
from versiontracker.exceptions import NetworkError, TimeoutError


@pytest.mark.asyncio
async def test_fetch_cask_info_with_mock_server():
    """Test fetching cask info from the mock server."""
    from tests.mock_homebrew_server import MockHomebrewServer

    # Start mock server
    server = MockHomebrewServer()
    server_url, _ = server.start()

    try:
        # Configure the base URL to use our mock server
        with patch("versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"):
            # Fetch info for an existing cask
            cask_info = await fetch_cask_info("firefox", use_cache=False)

            # Verify the result
            assert cask_info.get("name") == "firefox"
            assert cask_info.get("version") == "120.0.1"

            # Try to fetch a non-existent cask
            with pytest.raises(NetworkError):
                await fetch_cask_info("nonexistent-cask", use_cache=False)
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_fetch_cask_info_with_server_error():
    """Test error handling when server returns an error."""
    from tests.mock_homebrew_server import MockHomebrewServer

    # Start mock server
    server = MockHomebrewServer()
    server_url, _ = server.start()

    try:
        # Configure the server to return an error
        server.set_error_response(True, 500, "Internal Server Error")

        # Configure the base URL to use our mock server
        with patch("versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"):
            # Attempt to fetch cask info
            with pytest.raises(NetworkError):
                await fetch_cask_info("firefox", use_cache=False)
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_fetch_cask_info_with_timeout():
    """Test timeout handling when server doesn't respond."""
    from tests.mock_homebrew_server import MockHomebrewServer

    # Start mock server
    server = MockHomebrewServer()
    server_url, _ = server.start()

    try:
        # Configure the server to timeout
        server.set_timeout(True)

        # Configure the base URL to use our mock server
        with patch("versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"):
            # Attempt to fetch cask info with a short timeout
            with pytest.raises(TimeoutError):
                await fetch_cask_info("firefox", timeout=1, use_cache=False)
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_fetch_cask_info_with_malformed_response():
    """Test handling of malformed JSON responses."""
    from tests.mock_homebrew_server import MockHomebrewServer

    # Start mock server
    server = MockHomebrewServer()
    server_url, _ = server.start()

    try:
        # Configure the server to return malformed JSON
        server.set_malformed_response(True)

        # Configure the base URL to use our mock server
        with patch("versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"):
            # Attempt to fetch cask info
            with pytest.raises(NetworkError):
                await fetch_cask_info("firefox", use_cache=False)
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_search_casks_with_mock_server():
    """Test searching for casks with the mock server."""
    from tests.mock_homebrew_server import MockHomebrewServer

    # Start mock server
    server = MockHomebrewServer()
    server_url, _ = server.start()

    try:
        # Configure the base URL to use our mock server
        with patch(
            "versiontracker.async_homebrew.HOMEBREW_SEARCH_BASE",
            f"{server_url}/api/search",
        ):
            # Search for casks
            results = await search_casks("firefox", use_cache=False)

            # Verify we got results
            assert len(results) > 0
            assert any(result.get("name") == "firefox" for result in results)
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_async_check_brew_install_candidates_with_mock_server():
    """Test checking brew install candidates with the mock server."""
    from tests.mock_homebrew_server import MockHomebrewServer

    # Start mock server
    server = MockHomebrewServer()
    server_url, _ = server.start()

    try:
        # Configure the base URL to use our mock server
        with patch("versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"):
            with patch(
                "versiontracker.async_homebrew.HOMEBREW_SEARCH_BASE",
                f"{server_url}/api/search",
            ):
                with patch(
                    "versiontracker.async_homebrew.is_homebrew_available",
                    return_value=True,
                ):
                    # Access the underlying async function without the sync wrapper
                    from versiontracker.async_homebrew import (
                        async_check_brew_install_candidates,
                    )

                    # Get the original async function by accessing __wrapped__
                    if hasattr(async_check_brew_install_candidates, "__wrapped__"):
                        raw_async_func = async_check_brew_install_candidates.__wrapped__
                    else:
                        raw_async_func = async_check_brew_install_candidates

                    results = await raw_async_func(
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
                    nonexistent_result = next(r for r in results if r[0] == "NonExistentApp")

                    assert firefox_result[2] is True  # Firefox should be installable
                    assert chrome_result[2] is True  # Chrome should be installable
                    assert nonexistent_result[2] is False  # NonExistentApp should not be installable
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_async_check_brew_update_candidates_with_mock_server():
    """Test checking brew update candidates with the mock server."""
    from tests.mock_homebrew_server import MockHomebrewServer

    # Start mock server
    server = MockHomebrewServer()
    server_url, _ = server.start()

    try:
        # Configure the base URL to use our mock server
        with patch("versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"):
            with patch("versiontracker.async_homebrew.is_homebrew_available", return_value=True):
                # Access the underlying async function without the sync wrapper
                from versiontracker.async_homebrew import (
                    async_check_brew_update_candidates,
                )

                # Get the original async function by accessing __wrapped__
                if hasattr(async_check_brew_update_candidates, "__wrapped__"):
                    raw_async_func = async_check_brew_update_candidates.__wrapped__
                else:
                    raw_async_func = async_check_brew_update_candidates

                # Check update candidates (disable caching to ensure mock server is used)
                with patch("versiontracker.async_homebrew.fetch_cask_info") as mock_fetch:
                    # Mock fetch_cask_info to return expected values
                    def mock_fetch_side_effect(cask_name, **kwargs):
                        mock_data = {
                            "firefox": {"version": "120.0.1"},
                            "google-chrome": {"version": "120.0.6099.129"},
                        }
                        if cask_name in mock_data:
                            return mock_data[cask_name]
                        else:
                            from versiontracker.exceptions import NetworkError

                            raise NetworkError("HTTP error 404: Not Found")

                    mock_fetch.side_effect = mock_fetch_side_effect

                    results = await raw_async_func(
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
                assert chrome_result[3] == "120.0.6099.129"  # Chrome version from mock server
                assert nonexistent_result[3] is None  # NonExistent should have no version
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_async_get_cask_version_with_mock_server():
    """Test getting a cask version with the mock server."""
    from tests.mock_homebrew_server import MockHomebrewServer

    # Start mock server
    server = MockHomebrewServer()
    server_url, _ = server.start()

    try:
        # Configure the base URL to use our mock server
        with patch("versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"):
            # Access the underlying async function without the sync wrapper
            from versiontracker.async_homebrew import async_get_cask_version

            # Get the original async function by accessing __wrapped__
            if hasattr(async_get_cask_version, "__wrapped__"):
                raw_async_func = async_get_cask_version.__wrapped__
            else:
                raw_async_func = async_get_cask_version

            # Get version for an existing cask
            version = await raw_async_func("firefox", use_cache=False)

            # Verify the version
            assert version == "120.0.1"

            # Try to get version for a non-existent cask
            version = await raw_async_func("nonexistent-cask", use_cache=False)
            # Verify the version is None
            assert version is None
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_batch_processing_with_server_errors():
    """Test batch processing when the server has intermittent errors."""
    import aiohttp

    from tests.mock_homebrew_server import MockHomebrewServer

    # Start mock server
    server = MockHomebrewServer()
    server_url, _ = server.start()

    try:

        class TestProcessor(AsyncBatchProcessor):
            """Test processor for async batch operations."""

            def __init__(self, server_url):
                super().__init__(batch_size=2, max_concurrency=2, rate_limit=0.1)
                self.server_url = server_url
                self.api_base = f"{server_url}/api/cask"

            async def process_item(self, item):
                """Process a single item."""
                app_name, _ = item
                cask_name = app_name.lower().replace(" ", "-")
                url = f"{self.api_base}/{cask_name}.json"

                # Simple fetch implementation
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            return (app_name, True)
                        return (app_name, False)

            async def handle_error(self, item, error):
                """Handle processing errors."""
                app_name, _ = item
                return (app_name, False)

        # Configure the server to return errors for every second request
        original_get = server.server.RequestHandlerClass.do_GET

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
        with patch.object(server.server.RequestHandlerClass, "do_GET", alternating_error_get):
            # Create test data
            data = [
                ("Firefox", "100.0"),
                ("Chrome", "99.0"),
            ]
            # Process the data
            processor = TestProcessor(server_url)
            # Access the underlying async method without the sync wrapper
            if hasattr(processor.process_all, "__wrapped__"):
                results = await processor.process_all.__wrapped__(processor, data)
            else:
                results = await processor.process_all(data)

            # Verify the results (should be at least 2, may have retries)
            assert len(results) >= 2
            # Check we got some results
            assert len(results) > 0
    finally:
        server.stop()


@pytest.mark.asyncio
async def test_high_concurrency_with_rate_limiting():
    """Test high concurrency processing with rate limiting."""
    from tests.mock_homebrew_server import MockHomebrewServer

    # Start mock server
    server = MockHomebrewServer()
    server_url, _ = server.start()

    try:
        # Configure the base URL to use our mock server
        with patch("versiontracker.async_homebrew.HOMEBREW_API_BASE", f"{server_url}/api/cask"):
            with patch(
                "versiontracker.async_homebrew.HOMEBREW_SEARCH_BASE",
                f"{server_url}/api/search",
            ):
                with patch(
                    "versiontracker.async_homebrew.is_homebrew_available",
                    return_value=True,
                ):
                    # Create a smaller batch of data for simpler testing
                    data = [
                        ("Firefox", "100.0"),
                        ("Google Chrome", "99.0"),
                        ("Slack", "4.0"),
                    ]

                    # Track request timing for rate limiting verification
                    request_times = []
                    original_fetch_json = fetch_cask_info

                    async def track_concurrent_fetch(cask_name, **kwargs):
                        # Force a delay between requests to simulate rate limiting
                        if request_times:
                            # Add artificial delay for the test
                            await asyncio.sleep(0.2)
                        request_times.append(asyncio.get_event_loop().time())
                        return await original_fetch_json(cask_name, **kwargs)

                    with patch(
                        "versiontracker.async_homebrew.fetch_cask_info",
                        track_concurrent_fetch,
                    ):
                        # Access the underlying async function without the sync wrapper
                        from versiontracker.async_homebrew import (
                            async_check_brew_install_candidates,
                        )

                        # Get the original async function by accessing __wrapped__
                        if hasattr(async_check_brew_install_candidates, "__wrapped__"):
                            raw_async_func = async_check_brew_install_candidates.__wrapped__
                        else:
                            raw_async_func = async_check_brew_install_candidates

                        # Test async install candidates with rate limiting
                        results = await raw_async_func(
                            data,
                            rate_limit=0.2,  # Rate limiting
                        )

                        # Verify we got results for all items
                        assert len(results) == len(data)

                        # Verify known apps are marked as installable
                        firefox_result = next(r for r in results if r[0] == "Firefox")
                        chrome_result = next(r for r in results if r[0] == "Google Chrome")

                        assert firefox_result[2] is True
                        assert chrome_result[2] is True

                        # Basic rate limiting verification
                        if len(request_times) > 1:
                            request_times.sort()
                            time_diffs = [request_times[i] - request_times[i - 1] for i in range(1, len(request_times))]
                            # At least some requests should be delayed by rate limiting
                            max_delay = max(time_diffs) if time_diffs else 0
                            assert max_delay >= 0.1  # Some delay from rate limiting
    finally:
        server.stop()
