#!/usr/bin/env python3
"""Utility functions for VersionTracker."""

import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import functools

from versiontracker.exceptions import (
    NetworkError,
    TimeoutError,
    PermissionError,
    DataParsingError,
    FileNotFoundError
)

logger = logging.getLogger(__name__)

# Default paths and commands
SYSTEM_PROFILER_CMD = "/usr/sbin/system_profiler -json SPApplicationsDataType"
DESIRED_PATHS = ("/Applications/",)  # desired paths for app filtering tuple

# Set up Homebrew path based on architecture (Apple Silicon or Intel)
BREW_PATH = "/opt/homebrew/bin/brew"
BREW_CMD = f"{BREW_PATH} list --casks"
BREW_SEARCH = f"{BREW_PATH} search"

# Default rate limiting
DEFAULT_API_RATE_LIMIT = 3  # seconds

# Application data cache settings
APP_CACHE_FILE = os.path.expanduser("~/.cache/versiontracker/app_cache.json")
APP_CACHE_TTL = 3600  # Cache validity in seconds (1 hour)


# Setup logging
def setup_logging(debug: bool = False) -> None:
    """Set up logging for the application.

    Args:
        debug (bool, optional): Enable debug logging. Defaults to False.
    """
    log_level = logging.DEBUG if debug else logging.INFO

    # Create log directory in user's Library folder
    log_dir = Path.home() / "Library" / "Logs" / "Versiontracker"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "versiontracker.log"

    # Python 3.9+ supports encoding parameter
    if sys.version_info >= (3, 9):
        logging.basicConfig(
            filename=log_file,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            encoding="utf-8",
            filemode="w",
            level=log_level,
        )
    else:
        logging.basicConfig(
            filename=log_file,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            filemode="w",
            level=log_level,
        )


def normalise_name(name: str) -> str:
    """Return a normalised string.

    Args:
        name (str): The name to normalize

    Returns:
        str: The normalized name
    """
    name = name.strip()  # removing whitespace
    name = re.sub(r"\d+", "", name)  # get rid of numbers in name
    if not name.isprintable():  # remove non printables
        name = "".join(c for c in name if c.isprintable())
    return name


def _ensure_cache_dir() -> None:
    """Ensure the cache directory exists."""
    cache_dir = os.path.dirname(APP_CACHE_FILE)
    os.makedirs(cache_dir, exist_ok=True)


def _read_cache_file() -> Dict[str, Any]:
    """Read the application data cache file.

    Returns:
        Dict[str, Any]: The cached data or an empty dict if no cache exists
    """
    try:
        if os.path.exists(APP_CACHE_FILE):
            with open(APP_CACHE_FILE, "r") as f:
                cache_data = json.load(f)
                
            # Check if cache is still valid
            if time.time() - cache_data.get("timestamp", 0) <= APP_CACHE_TTL:
                return cache_data  # Removed cast
            
            logging.info("Cache expired, will refresh application data")
    except Exception as e:
        logging.warning(f"Failed to read application cache: {e}")
    
    return {}


def _write_cache_file(data: Dict[str, Any]) -> None:
    """Write data to the application cache file.

    Args:
        data (Dict[str, Any]): The data to cache
    """
    try:
        _ensure_cache_dir()
        
        # Add timestamp to the data
        cache_data = {
            "timestamp": time.time(),
            "data": data
        }
        
        with open(APP_CACHE_FILE, "w") as f:
            json.dump(cache_data, f)
            
        logging.info(f"Application data cached to {APP_CACHE_FILE}")
    except Exception as e:
        logging.warning(f"Failed to write application cache: {e}")


@functools.lru_cache(maxsize=4)
def get_json_data(command: str) -> Dict[str, Any]:
    """Execute a command and return the JSON output, with caching.

    Args:
        command (str): The command to execute

    Returns:
        Dict[str, Any]: The parsed JSON data

    Raises:
        RuntimeError: If the command fails
    """
    # For system_profiler, check the cache first
    if SYSTEM_PROFILER_CMD in command:
        cache = _read_cache_file()
        if cache and "data" in cache:
            logging.info("Using cached application data")
            return cache["data"]  # Removed cast
    
    try:
        # Split the command into arguments for security
        command_parts = command.split()

        # Use subprocess.run for more secure command execution
        result = subprocess.run(command_parts, capture_output=True, text=True, check=True)

        if not result.stdout:
            raise RuntimeError(f"Command '{command}' produced no output")

        parsed_data = json.loads(result.stdout)
        
        # Cache system_profiler results
        if SYSTEM_PROFILER_CMD in command:
            _write_cache_file(parsed_data)
            
        return parsed_data
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{command}' failed with error code {e.returncode}: {e.stderr}")
        raise RuntimeError(f"Command '{command}' failed: {e.stderr}")
    except json.JSONDecodeError:
        logging.error(f"Failed to parse JSON output from '{command}'")
        raise RuntimeError(f"Failed to parse JSON output from '{command}'")
    except Exception as e:
        logging.error(f"Failed to execute command '{command}': {e}")
        raise RuntimeError(f"Failed to execute command '{command}': {e}")


def get_json_data(cmd: str, timeout: int = 30) -> Dict[str, Any]:
    """Run a command and parse the output as JSON.
    
    Args:
        cmd: Command to run
        timeout: Timeout in seconds
        
    Returns:
        Dict[str, Any]: Parsed JSON data
        
    Raises:
        TimeoutError: If the command times out
        PermissionError: If there's a permission error
        DataParsingError: If the data cannot be parsed as JSON
    """
    try:
        output, returncode = run_command(cmd, timeout=timeout)
        
        if returncode != 0:
            logging.error(f"Command failed with return code {returncode}: {output}")
            raise DataParsingError(f"Command failed with return code {returncode}: {output}")
            
        # Parse JSON data
        try:
            data = json.loads(output)
            return data
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON data: {e}")
            raise DataParsingError(f"Invalid JSON data: {e}")
    except TimeoutError:
        logging.error(f"Command timed out: {cmd}")
        raise
    except PermissionError:
        logging.error(f"Permission denied: {cmd}")
        raise
    except Exception as e:
        logging.error(f"Error getting JSON data: {e}")
        raise Exception(f"Failed to get JSON data: {e}")


def run_command(cmd: str, timeout: Optional[int] = None) -> Tuple[str, int]:
    """Run a command and return the output.
    
    Args:
        cmd: Command to run
        timeout: Optional timeout in seconds
        
    Returns:
        Tuple[str, int]: Command output and return code
        
    Raises:
        TimeoutError: If the command times out
        PermissionError: If there's a permission error running the command
        Exception: If there's a network-related error
    """
    try:
        # Run the command
        logging.debug(f"Running command: {cmd}")
        process = subprocess.Popen(
            cmd, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        # Wait for the command to complete with timeout
        stdout, stderr = process.communicate(timeout=timeout)
        
        # Check return code
        if process.returncode != 0:
            logging.warning(f"Command failed with return code {process.returncode}: {stderr}")
            
            # Check for common errors
            if "command not found" in stderr:
                raise FileNotFoundError(f"Command not found: {cmd}")
            elif "permission denied" in stderr.lower():
                raise PermissionError(f"Permission denied: {cmd}")
            elif "network is unreachable" in stderr.lower() or "no route to host" in stderr.lower():
                raise NetworkError(f"Network error: {stderr}")
            
        return stdout, process.returncode
    except subprocess.TimeoutExpired as e:
        # Kill the process if it timed out
        process.kill()
        logging.error(f"Command timed out after {timeout} seconds: {cmd}")
        raise TimeoutError(f"Command timed out after {timeout} seconds: {cmd}") from e
    except PermissionError as e:
        logging.error(f"Permission error running command: {e}")
        raise
    except Exception as e:
        logging.error(f"Error running command: {e}")
        if "network" in str(e).lower():
            raise NetworkError(f"Network error running command: {e}")
        raise


def run_command_original(command: str, timeout: int = 30) -> List[str]:
    """Execute a command and return the output as a list of lines.

    Args:
        command (str): The command to execute
        timeout (int, optional): Timeout in seconds for the command. Defaults to 30.

    Returns:
        List[str]: The output as a list of lines

    Raises:
        PermissionError: If the command fails due to permission issues
        TimeoutError: If the command times out
        RuntimeError: For other command execution failures
    """
    try:
        # Execute the command using a shell for complex commands with pipes
        result = subprocess.run(
            command,
            shell=True,  # Using shell=True for compatibility with complex commands
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
        return [line for line in result.stdout.splitlines() if line]
    except subprocess.TimeoutExpired as e:
        error_msg = f"Command '{command}' timed out after {timeout} seconds"
        logging.error(error_msg)
        raise TimeoutError(error_msg) from e
    except subprocess.CalledProcessError as e:
        error_msg = f"Command '{command}' failed with error code {e.returncode}"
        
        # Check for common error patterns to provide better messages
        if e.returncode == 13 or "Permission denied" in e.stderr:
            logging.error(f"{error_msg}: Permission denied. Try running with sudo or check file permissions.")
            raise PermissionError(f"Permission denied while executing '{command}'") from e
        elif "command not found" in e.stderr:
            logging.error(f"{error_msg}: Command not found. Check if the required program is installed.")
            raise Exception(f"Command not found: '{command}'") from e
        elif "No such file or directory" in e.stderr:
            logging.error(f"{error_msg}: File or directory not found. Check if the path exists.")
            raise Exception(f"File or directory not found in command: '{command}'") from e
        else:
            # Generic error message with stderr output
            detailed_error = e.stderr.strip() if e.stderr else "Unknown error"
            logging.error(f"{error_msg}: {detailed_error}")
            raise RuntimeError(f"Command '{command}' failed: {detailed_error}") from e
    except Exception as e:
        logging.error(f"Failed to execute command '{command}': {e}")
        raise RuntimeError(f"Failed to execute command '{command}': {e}") from e


class RateLimiter:
    """Rate limiter for API calls that is thread-safe."""

    def __init__(self, calls_per_period: int = 1, period: float = 1.0):
        """Initialize the rate limiter.

        Args:
            calls_per_period (int): Number of calls allowed in the period
            period (float): Time period in seconds
        """
        self.calls_per_period = calls_per_period
        self.period = period
        self.timestamps: List[float] = []
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Wait if necessary to comply with the rate limit."""
        with self._lock:  # Use a lock to make the method thread-safe
            current_time = time.time()

            # Remove timestamps older than the period
            self.timestamps = [t for t in self.timestamps if current_time - t < self.period]

            # If we've reached the limit, wait until we can make another call
            if len(self.timestamps) >= self.calls_per_period:
                sleep_time = self.period - (current_time - self.timestamps[0])
                if sleep_time > 0:
                    logging.debug(f"Rate limiting: waiting for {sleep_time:.2f} seconds")
                    # Release the lock while sleeping to avoid blocking other threads
                    self._lock.release()
                    try:
                        time.sleep(sleep_time)
                    finally:
                        # Reacquire the lock after sleeping
                        self._lock.acquire()
                    current_time = time.time()  # Update current time after sleeping

            # Record the timestamp for this call
            self.timestamps.append(current_time)
