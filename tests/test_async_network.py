"""Test module for async_network functionality.

This module contains tests for the asynchronous network operations
provided by the async_network.py module.
"""

import asyncio
import json
from unittest.mock import MagicMock, patch

import aiohttp
import pytest
from aiohttp import ClientResponseError, ClientSession

from versiontracker.async_network import (
    AsyncBatchProcessor,
    async_to_sync,
    batch_fetch_json,
    fetch_json,
    run_async_in_thread,
)
from versiontracker.exceptions import NetworkError, TimeoutError


@pytest.fixture
def mock_aiohttp_session():
    """Create a mock aiohttp session."""
    session = MagicMock(spec=ClientSession)
    response = MagicMock()
    session.get.return_value.__aenter__.return_value = response
    response.raise_for_status = MagicMock()
    response.json.return_value = asyncio.Future()
    response.json.return_value.set_result({"key": "value"})
    return session, response


@pytest.mark.asyncio
async def test_fetch_json_success(mock_aiohttp_session):
    """Test successful JSON fetching."""
    session, response = mock_aiohttp_session
    
    with patch("aiohttp.ClientSession", return_value=session):
        with patch("versiontracker.async_network.read_cache", return_value=None):
            with patch("versiontracker.async_network.write_cache", return_value=True):
                result = await fetch_json("https://example.com/api", use_cache=True)
                
                # Verify the result
                assert result == {"key": "value"}
                
                # Verify the session was used correctly
                session.get.assert_called_once()
                response.raise_for_status.assert_called_once()
                response.json.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_json_from_cache():
    """Test fetching JSON from cache."""
    # Mock cached data
    cached_data = {"key": "cached_value"}
    
    with patch("versiontracker.async_network.read_cache", return_value=cached_data):
        result = await fetch_json("https://example.com/api", use_cache=True)
        
        # Verify the result is from cache
        assert result == cached_data


@pytest.mark.asyncio
async def test_fetch_json_network_error(mock_aiohttp_session):
    """Test handling of network errors."""
    session, response = mock_aiohttp_session
    
    # Make response.raise_for_status raise an error
    response.raise_for_status.side_effect = ClientResponseError(
        request_info=MagicMock(),
        history=(),
        status=404,
        message="Not Found",
    )
    
    with patch("aiohttp.ClientSession", return_value=session):
        with patch("versiontracker.async_network.read_cache", return_value=None):
            with pytest.raises(NetworkError):
                await fetch_json("https://example.com/api")


@pytest.mark.asyncio
async def test_fetch_json_timeout(mock_aiohttp_session):
    """Test handling of timeouts."""
    session, _ = mock_aiohttp_session
    
    # Make session.get raise a timeout
    session.get.side_effect = asyncio.TimeoutError("Timeout")
    
    with patch("aiohttp.ClientSession", return_value=session):
        with patch("versiontracker.async_network.read_cache", return_value=None):
            with pytest.raises(TimeoutError):
                await fetch_json("https://example.com/api")


@pytest.mark.asyncio
async def test_batch_fetch_json():
    """Test batch fetching of JSON."""
    # Create mock fetch function
    async def mock_fetch(url, cache_key, timeout, use_cache):
        return {"url": url}
    
    # Patch the fetch_json function
    with patch("versiontracker.async_network.fetch_json", side_effect=mock_fetch):
        urls = ["https://example.com/1", "https://example.com/2"]
        results = await batch_fetch_json(urls)
        
        # Verify the results
        assert len(results) == 2
        assert results[0]["url"] == urls[0]
        assert results[1]["url"] == urls[1]


@pytest.mark.asyncio
async def test_batch_fetch_json_error():
    """Test batch fetching with an error."""
    # Create mock fetch function that raises an error for the second URL
    async def mock_fetch(url, cache_key, timeout, use_cache):
        if url.endswith("/2"):
            raise NetworkError("Network error")
        return {"url": url}
    
    # Patch the fetch_json function
    with patch("versiontracker.async_network.fetch_json", side_effect=mock_fetch):
        urls = ["https://example.com/1", "https://example.com/2"]
        
        # Verify that the error is propagated
        with pytest.raises(NetworkError):
            await batch_fetch_json(urls)


def test_async_to_sync():
    """Test conversion of async function to sync."""
    async def async_func(x, y):
        return x + y
    
    # Convert to sync
    sync_func = async_to_sync(async_func)
    
    # Call the sync function
    result = sync_func(1, 2)
    
    # Verify the result
    assert result == 3


def test_run_async_in_thread():
    """Test running async function in a thread."""
    async def async_func(x, y):
        return x + y
    
    # Run in thread
    result = run_async_in_thread(async_func, 1, 2)
    
    # Verify the result
    assert result == 3


class TestAsyncBatchProcessor:
    """Tests for the AsyncBatchProcessor class."""
    
    class SimpleProcessor(AsyncBatchProcessor):
        """Simple implementation for testing."""
        
        async def process_item(self, item):
            """Process a test item by doubling it."""
            return item * 2
        
        def handle_error(self, item, error):
            """Handle errors by returning -1."""
            return -1
    
    def test_create_batches(self):
        """Test batch creation."""
        processor = self.SimpleProcessor(batch_size=2)
        
        # Create batches from a list
        batches = processor.create_batches([1, 2, 3, 4, 5])
        
        # Verify the batches
        assert len(batches) == 3
        assert batches[0] == [1, 2]
        assert batches[1] == [3, 4]
        assert batches[2] == [5]
    
    def test_process_all(self):
        """Test processing all items."""
        processor = self.SimpleProcessor(batch_size=2)
        
        # Process all items
        results = processor.process_all([1, 2, 3, 4, 5])
        
        # Verify the results
        assert results == [2, 4, 6, 8, 10]
    
    @pytest.mark.asyncio
    async def test_process_batch(self):
        """Test processing a batch."""
        processor = self.SimpleProcessor(batch_size=2)
        
        # Process a batch
        results = await processor.process_batch([1, 2, 3])
        
        # Verify the results
        assert results == [2, 4, 6]
    
    @pytest.mark.asyncio
    async def test_process_batch_with_error(self):
        """Test processing a batch with an error."""
        # Create a processor that raises an error for item 2
        class ErrorProcessor(self.SimpleProcessor):
            async def process_item(self, item):
                if item == 2:
                    raise ValueError("Test error")
                return item * 2
        
        processor = ErrorProcessor(batch_size=2)
        
        # Process a batch with an error
        results = await processor.process_batch([1, 2, 3])
        
        # Verify the results
        assert results == [2, -1, 6]