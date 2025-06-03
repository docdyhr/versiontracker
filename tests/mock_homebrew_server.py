"""Mock server for testing Homebrew network operations.

This module provides mock server functionality for testing Homebrew-related
network operations without making actual network requests. It simulates
the behavior of the Homebrew API, including success responses, errors,
timeouts, and malformed data.
"""

import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Dict, Optional, Tuple

# Default cask data for testing
DEFAULT_CASKS = {
    "firefox": {
        "name": "firefox",
        "token": "firefox_cask",
        "version": "120.0.1",
        "desc": "Web browser",
        "homepage": "https://www.mozilla.org/firefox/",
    },
    "visual-studio-code": {
        "name": "visual-studio-code",
        "token": "visual-studio-code_cask",
        "version": "1.85.1",
        "desc": "Open-source code editor",
        "homepage": "https://code.visualstudio.com/",
    },
    "slack": {
        "name": "slack",
        "token": "slack_cask",
        "version": "4.35.131",
        "desc": "Team communication and collaboration software",
        "homepage": "https://slack.com/",
    },
    "google-chrome": {
        "name": "google-chrome",
        "token": "google-chrome_cask",
        "version": "120.0.6099.129",
        "desc": "Web browser",
        "homepage": "https://www.google.com/chrome/",
    },
    "iterm2": {
        "name": "iterm2",
        "token": "iterm2_cask",
        "version": "3.4.21",
        "desc": "Terminal emulator as alternative to Apple's Terminal app",
        "homepage": "https://iterm2.com/",
    },
}


class MockHomebrewError(Exception):
    """Exception raised for errors in the mock Homebrew server."""

    pass


class MockHomebrewHandler(BaseHTTPRequestHandler):
    """Request handler for the mock Homebrew server."""

    # Class variables to control server behavior
    casks_data: Dict[str, Dict[str, str]] = DEFAULT_CASKS.copy()
    delay_seconds: float = 0.0
    should_timeout: bool = False
    should_return_malformed: bool = False
    should_return_error: bool = False
    error_code: int = 500
    error_message: str = "Internal Server Error"

    def log_message(self, format: str, *args) -> None:
        """Suppress logging unless in debug mode."""
        pass

    def do_GET(self) -> None:
        """Handle GET requests."""
        # Simulate a timeout if configured
        if self.should_timeout:
            time.sleep(10)  # Long delay to force timeout
            return

        # Apply configured delay
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

        # Return error if configured
        if self.should_return_error:
            self.send_response(self.error_code)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(self.error_message.encode("utf-8"))
            return

        # Parse the path to determine what to return
        if self.path.startswith("/api/cask"):
            # Extract cask name from path
            match = re.search(r"/api/cask/([^/]+)", self.path)
            if match:
                cask_name = match.group(1)
                # Remove .json extension if present
                if cask_name.endswith(".json"):
                    cask_name = cask_name[:-5]
                self.handle_cask_request(cask_name)
            else:
                self.handle_all_casks_request()
        elif self.path.startswith("/api/search"):
            # Handle search queries (both /api/search and /api/search.json)
            self.handle_search_request()
        else:
            # Handle unknown paths
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")

    def handle_cask_request(self, cask_name: str) -> None:
        """Handle request for a specific cask."""
        if cask_name in self.casks_data:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            if self.should_return_malformed:
                # Return malformed JSON
                self.wfile.write(b'{"name": "malformed')
            else:
                # Return valid cask data
                response = json.dumps(self.casks_data[cask_name])
                self.wfile.write(response.encode("utf-8"))
        else:
            # Cask not found
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Cask '{cask_name}' not found".encode("utf-8"))

    def handle_all_casks_request(self) -> None:
        """Handle request for all casks."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        if self.should_return_malformed:
            # Return malformed JSON
            self.wfile.write(b'[{"name": "malformed')
        else:
            # Return all cask data
            response = json.dumps(list(self.casks_data.values()))
            self.wfile.write(response.encode("utf-8"))

    def handle_search_request(self) -> None:
        """Handle search request."""
        # Parse query parameters
        query = ""
        if "?" in self.path:
            query_params = self.path.split("?")[1]
            params = query_params.split("&")
            for param in params:
                if param.startswith("q="):
                    query = param[2:]

        # Filter casks by query
        results = []
        if query:
            for cask_name, cask_data in self.casks_data.items():
                if (
                    query.lower() in cask_name.lower()
                    or query.lower() in cask_data["desc"].lower()
                ):
                    results.append(cask_data)
        else:
            # No query, return all casks
            results = list(self.casks_data.values())

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        if self.should_return_malformed:
            # Return malformed JSON
            self.wfile.write(b'[{"name": "malformed')
        else:
            # Return search results
            response = json.dumps(results)
            self.wfile.write(response.encode("utf-8"))


class MockHomebrewServer:
    """Mock server for Homebrew API testing."""

    def __init__(self, host: str = "localhost", port: int = 0) -> None:
        """Initialize the mock server.

        Args:
            host: Hostname to bind to
            port: Port number to bind to (0 means automatic port selection)
        """
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self._original_casks = MockHomebrewHandler.casks_data.copy()

    def start(self) -> Tuple[str, int]:
        """Start the mock server.

        Returns:
            Tuple containing the server URL and port number
        """
        if self.server:
            raise MockHomebrewError("Server already running")

        # Create and start the server
        self.server = HTTPServer((self.host, self.port), MockHomebrewHandler)
        self.port = self.server.server_port  # Get the actual port (if 0 was specified)

        # Start the server in a separate thread
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        return f"http://{self.host}:{self.port}", self.port

    def stop(self) -> None:
        """Stop the mock server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            self.server_thread = None
            # Reset server behavior
            self.reset()

    def reset(self) -> None:
        """Reset server behavior to defaults."""
        MockHomebrewHandler.casks_data = self._original_casks.copy()
        MockHomebrewHandler.delay_seconds = 0.0
        MockHomebrewHandler.should_timeout = False
        MockHomebrewHandler.should_return_malformed = False
        MockHomebrewHandler.should_return_error = False
        MockHomebrewHandler.error_code = 500
        MockHomebrewHandler.error_message = "Internal Server Error"

    def set_casks(self, casks: Dict[str, Dict[str, str]]) -> None:
        """Set custom cask data.

        Args:
            casks: Dictionary of cask data to use
        """
        MockHomebrewHandler.casks_data = casks

    def add_cask(
        self, name: str, version: str, desc: str = "", homepage: str = ""
    ) -> None:
        """Add a new cask to the mock server.

        Args:
            name: Name of the cask
            version: Version string
            desc: Description of the cask
            homepage: Homepage URL
        """
        MockHomebrewHandler.casks_data[name] = {
            "name": name,
            "version": version,
            "desc": desc,
            "homepage": homepage,
        }

    def remove_cask(self, name: str) -> None:
        """Remove a cask from the mock server.

        Args:
            name: Name of the cask to remove
        """
        if name in MockHomebrewHandler.casks_data:
            del MockHomebrewHandler.casks_data[name]

    def set_delay(self, seconds: float) -> None:
        """Set a delay for all responses.

        Args:
            seconds: Delay in seconds
        """
        MockHomebrewHandler.delay_seconds = seconds

    def set_timeout(self, should_timeout: bool = True) -> None:
        """Configure the server to timeout on requests.

        Args:
            should_timeout: Whether requests should timeout
        """
        MockHomebrewHandler.should_timeout = should_timeout

    def set_malformed_response(self, should_return_malformed: bool = True) -> None:
        """Configure the server to return malformed JSON.

        Args:
            should_return_malformed: Whether to return malformed JSON
        """
        MockHomebrewHandler.should_return_malformed = should_return_malformed

    def set_error_response(
        self,
        should_return_error: bool = True,
        code: int = 500,
        message: str = "Internal Server Error",
    ) -> None:
        """Configure the server to return an error response.

        Args:
            should_return_error: Whether to return an error
            code: HTTP status code
            message: Error message
        """
        MockHomebrewHandler.should_return_error = should_return_error
        MockHomebrewHandler.error_code = code
        MockHomebrewHandler.error_message = message


def with_mock_homebrew_server(func: Callable) -> Callable:
    """Decorator that starts a mock server before the test and stops it after.

    Args:
        func: Test function to decorate

    Returns:
        Decorated function
    """
    import asyncio
    from functools import wraps

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        # Start mock server
        server = MockHomebrewServer()
        server_url, port = server.start()

        # Add server to kwargs
        kwargs["mock_server"] = server
        kwargs["server_url"] = server_url

        try:
            # Run the test
            return await func(*args, **kwargs)
        finally:
            # Stop the server
            server.stop()

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        # Start mock server
        server = MockHomebrewServer()
        server_url, port = server.start()

        # Add server to kwargs
        kwargs["mock_server"] = server
        kwargs["server_url"] = server_url

        try:
            # Run the test
            return func(*args, **kwargs)
        finally:
            # Stop the server
            server.stop()

    # Check if the function is async
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
