"""Utility functions for VersionTracker."""

import functools
import json
import logging
import os
import platform
import re
import shlex
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, Tuple, cast

from versiontracker import __version__
from versiontracker.exceptions import (
    DataParsingError,
    FileNotFoundError,
    NetworkError,
    PermissionError,
    TimeoutError,
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
    log_file = None
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "versiontracker.log"
    except OSError as e:
        logging.error(f"Failed to create log directory {log_dir}: {e}")
        # Continue without file logging if directory creation fails

    # Python 3.9+ supports encoding parameter
    try:
        if log_file and sys.version_info >= (3, 9):
            logging.basicConfig(
                filename=log_file,
                format="%(asctime)s %(levelname)s %(name)s %(message)s",
                encoding="utf-8",
                filemode="w",
                level=log_level,
            )
        elif log_file:
            logging.basicConfig(
                filename=log_file,
                format="%(asctime)s %(levelname)s %(name)s %(message)s",
                filemode="w",
                level=log_level,
            )
        else:
            # Fallback to console logging if file logging fails
            logging.basicConfig(
                format="%(asctime)s %(levelname)s %(name)s %(message)s",
                level=log_level,
            )
    except (OSError, PermissionError):
        # Fallback to console logging if file logging fails
        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
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
    try:
        cache_dir = os.path.dirname(APP_CACHE_FILE)
        os.makedirs(cache_dir, exist_ok=True)
    except OSError as e:
        logging.warning(f"Could not create cache directory: {e}")
        # Continue without caching if directory creation fails


def _read_cache_file() -> Dict[str, Any]:
    """Read the application data cache file.

    Returns:
        Dict[str, Any]: The cached data or an empty dict if no cache exists
    """
    try:
        if os.path.exists(APP_CACHE_FILE):
            with open(APP_CACHE_FILE, "r") as f:
                cache_data = json.load(f)

            # Check if cache has timestamp and is still valid
            if "timestamp" in cache_data and time.time() - cache_data["timestamp"] <= APP_CACHE_TTL:
                return cast(Dict[str, Any], cache_data)

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
        cache_data = {"timestamp": time.time(), "data": data}

        with open(APP_CACHE_FILE, "w") as f:
            json.dump(cache_data, f)

        logging.info(f"Application data cached to {APP_CACHE_FILE}")
    except Exception as e:
        logging.warning(f"Failed to write application cache: {e}")


@functools.lru_cache(maxsize=4)
def _check_system_profiler_cache(command: str) -> Optional[Dict[str, Any]]:
    """Check if system_profiler data is cached and return it if valid."""
    if SYSTEM_PROFILER_CMD in command:
        cache = _read_cache_file()
        if cache and "data" in cache:
            logging.info("Using cached application data")
            return cast(Dict[str, Any], cache["data"])
    return None


def _parse_json_output(stdout: str, command: str) -> Dict[str, Any]:
    """Parse JSON output from command stdout."""
    if not stdout:
        raise DataParsingError(f"Command '{command}' produced no output")

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON output from '{command}': {e}")
        raise DataParsingError(f"Failed to parse JSON from command output: {e}") from e


def _handle_command_execution_error(e: subprocess.CalledProcessError, command: str) -> NoReturn:
    """Handle errors from command execution and raise appropriate exceptions."""
    logging.error(f"Command '{command}' failed with error code {e.returncode}")
    error_output = str(e.output) if e.output else str(e)

    if "command not found" in error_output.lower():
        raise FileNotFoundError(f"Command not found: {command}") from e
    elif "permission denied" in error_output.lower():
        raise PermissionError(f"Permission denied when running: {command}") from e
    else:
        raise DataParsingError(f"Command execution failed: {e}") from e


def _handle_unexpected_error(e: Exception, command: str) -> NoReturn:
    """Handle unexpected errors and categorize them appropriately."""
    logging.error(f"Unexpected error executing command '{command}': {e}")

    # Check for network-related terms in the error message
    if any(term in str(e).lower() for term in ["network", "connection", "timeout"]):
        raise NetworkError(f"Network error executing command: {command}") from e
    # Fallback to DataParsingError for other cases
    raise DataParsingError(f"Error processing command output: {e}") from e


def get_json_data(command: str) -> Dict[str, Any]:
    """Execute a command and return the JSON output, with caching.

    Executes the given command, parses its JSON output, and optionally
    caches the results for future use (when using system_profiler).

    Args:
        command (str): The command to execute

    Returns:
        Dict[str, Any]: The parsed JSON data

    Raises:
        DataParsingError: If the JSON output cannot be parsed
        FileNotFoundError: If the command executable cannot be found
        PermissionError: If there's insufficient permission to run the command
        TimeoutError: If the command execution times out
        NetworkError: If a network-related error occurs during execution
    """
    # Check cache first for system_profiler commands
    cached_data = _check_system_profiler_cache(command)
    if cached_data is not None:
        return cached_data

    try:
        # Execute command securely
        stdout, return_code = run_command(command, timeout=60)

        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, command, stdout)

        # Parse JSON output
        parsed_data = _parse_json_output(stdout, command)

        # Cache system_profiler results
        if SYSTEM_PROFILER_CMD in command:
            _write_cache_file(parsed_data)

        return parsed_data

    except subprocess.CalledProcessError as e:
        _handle_command_execution_error(e, command)
    except (
        FileNotFoundError,
        PermissionError,
        TimeoutError,
        NetworkError,
        DataParsingError,
    ):
        # Re-raise specific exceptions for consistent error handling
        raise
    except Exception as e:
        _handle_unexpected_error(e, command)


def get_shell_json_data(cmd: str, timeout: int = 30) -> Dict[str, Any]:
    """Run a shell command and parse the output as JSON.

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
            return cast(Dict[str, Any], data)
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON data: {e}")
            raise DataParsingError(f"Invalid JSON data: {e}")
    except TimeoutError:
        logging.error(f"Command timed out: {cmd}")
        raise
    except PermissionError:
        logging.error(f"Permission denied: {cmd}")
        raise
    except DataParsingError:
        # Re-raise DataParsingError as-is
        raise
    except Exception as e:
        logging.error(f"Error getting JSON data: {e}")
        raise DataParsingError(f"Failed to get JSON data: {e}") from e


def run_command_secure(command_parts: List[str], timeout: Optional[int] = None) -> Tuple[str, int]:
    """Run a command securely without shell=True.

    This function executes commands without using shell=True, which eliminates
    shell injection vulnerabilities. Commands are passed as a list of arguments.

    Args:
        command_parts: List of command arguments (e.g., ['brew', 'list', '--cask'])
        timeout: Optional timeout in seconds

    Returns:
        Tuple[str, int]: Command output and return code

    Raises:
        TimeoutError: If the command execution exceeds the specified timeout
        PermissionError: If there's insufficient permissions to run the command
        FileNotFoundError: If the command executable cannot be found
        NetworkError: If a network-related error occurs during execution
        subprocess.SubprocessError: For other subprocess-related errors
    """
    process = None
    try:
        # Run the command without shell=True for security
        logging.debug(f"Running secure command: {' '.join(command_parts)}")
        process = subprocess.Popen(
            command_parts,
            shell=False,  # Security: No shell interpretation
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for the command to complete with timeout
        stdout, stderr = process.communicate(timeout=timeout)

        # Check return code
        if process.returncode != 0:
            # Check for expected "failures" that shouldn't be logged as warnings
            if "Error: No formulae or casks found" in stderr:
                # This is an expected case for non-existent brews, don't log it as a warning
                pass
            else:
                # Log other failures as warnings
                logging.warning(
                    f"Command {' '.join(command_parts)} failed with return code {process.returncode}: {stderr}"
                )

        return stdout, process.returncode

    except subprocess.TimeoutExpired:
        if process:
            process.kill()
            process.wait()
        error_msg = f"Command {' '.join(command_parts)} timed out after {timeout} seconds"
        logging.error(error_msg)
        raise TimeoutError(error_msg)

    except FileNotFoundError as e:
        error_msg = f"Command not found: {command_parts[0] if command_parts else 'unknown'}"
        logging.error(error_msg)
        raise FileNotFoundError(error_msg) from e

    except PermissionError as e:
        error_msg = f"Permission denied executing command: {' '.join(command_parts)}"
        logging.error(error_msg)
        raise PermissionError(error_msg) from e

    except Exception as e:
        # Check if this looks like a network error
        error_str = str(e).lower()
        if any(
            keyword in error_str
            for keyword in [
                "network",
                "connection",
                "host",
                "resolve",
                "timeout",
            ]
        ):
            raise NetworkError(f"Network error running command: {' '.join(command_parts)}") from e
        # Re-raise with more context
        raise Exception(f"Error executing command {' '.join(command_parts)}: {e}") from e


def shell_command_to_args(cmd: str) -> List[str]:
    """Convert a shell command string to a secure argument list.

    This function uses shlex.split() to properly parse shell commands into
    individual arguments, which can then be used with subprocess without shell=True.

    Args:
        cmd: Shell command string to convert

    Returns:
        List[str]: Command arguments that can be used with subprocess

    Example:
        >>> shell_command_to_args('brew search --cask "Google Chrome"')
        ['brew', 'search', '--cask', 'Google Chrome']
    """
    try:
        return shlex.split(cmd)
    except ValueError as e:
        # If shlex.split fails due to unmatched quotes or other issues,
        # fall back to simple split but log a warning
        logging.warning(f"Failed to parse command with shlex.split: {cmd}. Error: {e}")
        return cmd.split()


def _execute_subprocess(cmd_list: List[str], timeout: Optional[int]) -> subprocess.Popen:
    """Execute subprocess and return the process object."""
    return subprocess.Popen(
        cmd_list,
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _is_expected_homebrew_failure(stderr: str) -> bool:
    """Check if stderr contains expected Homebrew failure messages."""
    return "Error: No formulae or casks found" in stderr


def _classify_command_error(stderr: str, cmd: str) -> None:
    """Classify and raise appropriate exception based on stderr content."""
    if "command not found" in stderr:
        raise FileNotFoundError(f"Command not found: {cmd}")
    elif "permission denied" in stderr.lower():
        raise PermissionError(f"Permission denied: {cmd}")
    elif any(
        network_err in stderr.lower()
        for network_err in [
            "network is unreachable",
            "no route to host",
            "connection refused",
            "temporary failure in name resolution",
        ]
    ):
        raise NetworkError(f"Network error: {stderr}")


def _handle_process_output(stdout: str, stderr: str, return_code: int, cmd: str) -> Tuple[str, int]:
    """Handle process output and return appropriate result."""
    if return_code != 0:
        if _is_expected_homebrew_failure(stderr):
            # This is an expected case for non-existent brews, don't log it as a warning
            pass
        else:
            # Log other failures as warnings
            logging.warning(f"Command failed with return code {return_code}: {stderr}")
            # Check for specific errors that should raise exceptions
            _classify_command_error(stderr, cmd)

        # Return appropriate output based on content
        if not stdout.strip() and stderr.strip():
            if "No formulae or casks found" in stderr:
                return "No formulae or casks found", return_code
            return stderr, return_code

    return stdout, return_code


def _handle_timeout_error(process: Optional[subprocess.Popen], timeout: Optional[int], cmd: str) -> NoReturn:
    """Handle timeout errors and cleanup process."""
    if process:
        try:
            process.kill()
        except Exception as kill_error:
            logging.debug(f"Error killing timed out process: {kill_error}")

    logging.error(f"Command timed out after {timeout} seconds: {cmd}")
    raise TimeoutError(f"Command timed out after {timeout} seconds: {cmd}")


def _handle_network_error_check(e: Exception, cmd: str) -> None:
    """Check if exception indicates network error and raise NetworkError if so."""
    if any(
        network_term in str(e).lower()
        for network_term in [
            "network",
            "socket",
            "connection",
            "host",
            "resolve",
            "timeout",
        ]
    ):
        raise NetworkError(f"Network error running command: {cmd}") from e


def run_command(cmd: str, timeout: Optional[int] = None) -> Tuple[str, int]:
    """Run a command and return the output.

    ⚠️  SECURITY WARNING: This function uses shell=True which can be vulnerable
    to command injection if user input is not properly sanitized. Consider using
    run_command_secure() instead for better security.

    Executes a shell command and captures its output and return code.
    Handles various error conditions including timeouts, permission issues,
    and network-related problems.

    Args:
        cmd: Command to run
        timeout: Optional timeout in seconds

    Returns:
        Tuple[str, int]: Command output and return code

    Raises:
        TimeoutError: If the command execution exceeds the specified timeout
        PermissionError: If there's insufficient permissions to run the command
        FileNotFoundError: If the command executable cannot be found
        NetworkError: If a network-related error occurs during execution
        subprocess.SubprocessError: For other subprocess-related errors
    """
    process = None
    try:
        # Run the command
        logging.debug(f"Running command: {cmd}")
        # Parse command safely to avoid shell injection
        cmd_list = shlex.split(cmd)
        process = _execute_subprocess(cmd_list, timeout)

        # Wait for the command to complete with timeout
        stdout, stderr = process.communicate(timeout=timeout)

        # Handle the output based on return code and content
        return _handle_process_output(stdout, stderr, process.returncode, cmd)

    except subprocess.TimeoutExpired:
        _handle_timeout_error(process, timeout, cmd)
    except FileNotFoundError as e:
        logging.error(f"Command not found: {cmd}")
        raise FileNotFoundError(f"Command not found: {cmd}") from e
    except PermissionError as e:
        logging.error(f"Permission error running command: {cmd}")
        raise PermissionError(f"Permission denied when running: {cmd}") from e
    except subprocess.SubprocessError as e:
        logging.error(f"Subprocess error running command: {cmd} - {e}")
        raise
    except Exception as e:
        logging.error(f"Error running command '{cmd}': {e}")
        # Check for network-related errors in the exception message
        _handle_network_error_check(e, cmd)
        # Re-raise with more context
        raise Exception(f"Error executing command '{cmd}': {e}") from e


def run_command_original(command: str, timeout: int = 30) -> List[str]:
    """Execute a command and return the output as a list of lines.

    ⚠️  SECURITY WARNING: This function uses shell=True which can be vulnerable
    to command injection if user input is not properly sanitized. Consider using
    run_command_secure() instead for better security.

    Args:
        command (str): The command to execute
        timeout (int, optional): Timeout in seconds for the command. Defaults to 30.

    Returns:
        List[str]: The output as a list of lines

    Raises:
        PermissionError: If the command fails due to permission issues
        TimeoutError: If the command times out
        FileNotFoundError: If the command is not found
        NetworkError: For network-related command failures
        RuntimeError: For other command execution failures
    """
    try:
        result = subprocess.run(
            command,
            shell=True,  # nosec B602 - Intentionally using shell=True for legacy compatibility
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
        stderr = e.stderr or ""
        # Check for common error patterns to provide better messages
        if e.returncode == 13 or "permission denied" in stderr.lower():
            logging.error(f"{error_msg}: Permission denied. Try running with sudo or check file permissions.")
            raise PermissionError(f"Permission denied while executing '{command}'") from e
        elif "command not found" in stderr.lower():
            logging.error(f"{error_msg}: Command not found. Check if the required program is installed.")
            raise FileNotFoundError(f"Command not found: '{command}'") from e
        elif "no such file or directory" in stderr.lower():
            logging.error(f"{error_msg}: File or directory not found. Check if the path exists.")
            raise FileNotFoundError(f"File or directory not found in command: '{command}'") from e
        elif any(
            network_err in stderr.lower()
            for network_err in [
                "network is unreachable",
                "no route to host",
                "connection refused",
                "temporary failure in name resolution",
                "could not resolve host",
                "connection timed out",
                "timed out",
            ]
        ):
            logging.error(f"{error_msg}: Network error: {stderr}")
            raise NetworkError(f"Network error while executing '{command}': {stderr}") from e
        else:
            detailed_error = stderr.strip() if stderr else "Unknown error"
            logging.error(f"{error_msg}: {detailed_error}")
            raise RuntimeError(f"Command '{command}' failed: {detailed_error}") from e
    except Exception as e:
        logging.error(f"Failed to execute command '{command}': {e}")
        raise RuntimeError(f"Failed to execute command '{command}': {e}") from e


def get_user_agent() -> str:
    """Return the default User-Agent string for VersionTracker network requests.

    Returns:
        str: The User-Agent string identifying VersionTracker and Python version.
    """
    python_version = platform.python_version()
    system = platform.system()
    return f"VersionTracker/{__version__} (Python/{python_version}; {system})"


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
            self.timestamps = [t for t in self.timestamps if current_time - t <= self.period]

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

                    # Remove timestamps older than the period after sleeping
                    self.timestamps = [t for t in self.timestamps if current_time - t <= self.period]

            # Record the timestamp for this call
            self.timestamps.append(current_time)
