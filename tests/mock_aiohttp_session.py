"""Mock aiohttp session context manager for testing.

This module provides a comprehensive mock for aiohttp.ClientSession
that can be used as a context manager in async tests.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, Union
from unittest.mock import AsyncMock, MagicMock

import aiohttp


class MockResponse:
    """Mock aiohttp response object."""

    def __init__(
        self,
        json_data: Optional[Dict[str, Any]] = None,
        text_data: Optional[str] = None,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        raise_for_status_exception: Optional[Exception] = None,
    ):
        self.json_data = json_data or {}
        self.text_data = text_data or ""
        self.status = status
        self.headers = headers or {}
        self._raise_for_status_exception = raise_for_status_exception

        # Mock methods
        self.json = AsyncMock(return_value=self.json_data)
        self.text = AsyncMock(return_value=self.text_data)
        self.raise_for_status = MagicMock()

        if self._raise_for_status_exception:
            self.raise_for_status.side_effect = self._raise_for_status_exception

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockSession:
    """Mock aiohttp session object."""

    def __init__(self):
        self.responses = {}
        self.default_response = MockResponse()
        self.call_history = []

        # Mock methods
        self.get = MagicMock(side_effect=self._mock_get)
        self.post = MagicMock(side_effect=self._mock_post)
        self.put = MagicMock(side_effect=self._mock_put)
        self.delete = MagicMock(side_effect=self._mock_delete)
        self.close = AsyncMock()

    def add_response(
        self,
        url: str,
        method: str = "GET",
        json_data: Optional[Dict[str, Any]] = None,
        text_data: Optional[str] = None,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        raise_for_status_exception: Optional[Exception] = None,
    ):
        """Add a mock response for a specific URL and method."""
        key = f"{method.upper()}:{url}"
        self.responses[key] = MockResponse(
            json_data=json_data,
            text_data=text_data,
            status=status,
            headers=headers,
            raise_for_status_exception=raise_for_status_exception,
        )

    def _get_response(self, method: str, url: str) -> MockResponse:
        """Get the appropriate response for a URL and method."""
        key = f"{method.upper()}:{url}"
        return self.responses.get(key, self.default_response)

    def _mock_get(self, url: str, **kwargs) -> MockResponse:
        """Mock GET request."""
        self.call_history.append(("GET", url, kwargs))
        response = self._get_response("GET", url)
        return response

    def _mock_post(self, url: str, **kwargs) -> MockResponse:
        """Mock POST request."""
        self.call_history.append(("POST", url, kwargs))
        response = self._get_response("POST", url)
        return response

    def _mock_put(self, url: str, **kwargs) -> MockResponse:
        """Mock PUT request."""
        self.call_history.append(("PUT", url, kwargs))
        response = self._get_response("PUT", url)
        return response

    def _mock_delete(self, url: str, **kwargs) -> MockResponse:
        """Mock DELETE request."""
        self.call_history.append(("DELETE", url, kwargs))
        response = self._get_response("DELETE", url)
        return response


@asynccontextmanager
async def mock_aiohttp_session():
    """Async context manager for mocking aiohttp.ClientSession.

    Usage:
        async with mock_aiohttp_session() as mock_session:
            mock_session.add_response("http://example.com", json_data={"key": "value"})
            # Your async code that uses aiohttp here
    """
    session = MockSession()
    try:
        yield session
    finally:
        await session.close()


class MockClientSession:
    """Mock aiohttp.ClientSession that can be used as a context manager."""

    def __init__(self, mock_session: MockSession):
        self.mock_session = mock_session

    async def __aenter__(self):
        return self.mock_session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.mock_session.close()


def create_mock_session_factory(mock_session: MockSession):
    """Create a factory function that returns a MockClientSession."""

    def factory(*args, **kwargs):
        return MockClientSession(mock_session)

    return factory
