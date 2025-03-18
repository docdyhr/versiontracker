"""Utility functions for VersionTracker."""

import json
import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from fuzzywuzzy.fuzz import partial_ratio

# Default paths and commands
SYSTEM_PROFILER_CMD = "/usr/sbin/system_profiler -json SPApplicationsDataType"
DESIRED_PATHS = ("/Applications/",)  # desired paths for app filtering tuple

# Set up Homebrew path based on architecture (Apple Silicon or Intel)
BREW_PATH = (
    "/opt/homebrew/bin/brew" if Path("/opt/homebrew/bin/brew").exists() else "/usr/local/bin/brew"
)
BREW_CMD = f"{BREW_PATH} list --casks"
BREW_SEARCH = f"{BREW_PATH} search"

# Default rate limiting
DEFAULT_API_RATE_LIMIT = 3  # seconds


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

    logging.basicConfig(
        filename=log_file,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        encoding="utf-8",
        filemode="w",
        level=log_level,
    )


def check_dependencies() -> bool:
    """Check if all required system dependencies are available.

    Returns:
        bool: True if all dependencies are available, False otherwise
    """
    # Check system_profiler
    if not shutil.which("/usr/sbin/system_profiler"):
        logging.error("system_profiler not found. This tool requires macOS.")
        return False

    # Check brew
    if not os.path.exists(BREW_PATH):
        logging.error(f"Homebrew not found at {BREW_PATH}. Please install Homebrew.")
        return False

    # Check for required Python packages
    try:
        import fuzzywuzzy
        import Levenshtein
    except ImportError as e:
        logging.error(f"Required Python package not found: {e}")
        return False

    return True


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


def get_json_data(command: str) -> Dict[str, Any]:
    """Execute a command and return the JSON output.

    Args:
        command (str): The command to execute

    Returns:
        Dict[str, Any]: The parsed JSON data

    Raises:
        RuntimeError: If the command fails
    """
    try:
        # Split the command into arguments for security
        command_parts = command.split()

        # Use subprocess.run for more secure command execution
        result = subprocess.run(command_parts, capture_output=True, text=True, check=True)

        if not result.stdout:
            raise RuntimeError(f"Command '{command}' produced no output")

        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{command}' failed with error code {e.returncode}: {e.stderr}")
        raise RuntimeError(f"Command '{command}' failed: {e.stderr}")
    except json.JSONDecodeError:
        logging.error(f"Failed to parse JSON output from '{command}'")
        raise RuntimeError(f"Failed to parse JSON output from '{command}'")
    except Exception as e:
        logging.error(f"Failed to execute command '{command}': {e}")
        raise RuntimeError(f"Failed to execute command '{command}': {e}")


def run_command(command: str) -> List[str]:
    """Execute a command and return the output as a list of lines.

    Args:
        command (str): The command to execute

    Returns:
        List[str]: The output as a list of lines

    Raises:
        RuntimeError: If the command fails
    """
    try:
        # Execute the command using a shell for complex commands with pipes
        result = subprocess.run(
            command,
            shell=True,  # Using shell=True for compatibility with complex commands
            capture_output=True,
            text=True,
            check=True,
        )
        return [line for line in result.stdout.splitlines() if line]
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{command}' failed with error code {e.returncode}: {e.stderr}")
        raise RuntimeError(f"Command '{command}' failed: {e.stderr}")
    except Exception as e:
        logging.error(f"Failed to execute command '{command}': {e}")
        raise RuntimeError(f"Failed to execute command '{command}': {e}")


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, calls_per_period: int = 1, period: float = 1.0):
        """Initialize the rate limiter.

        Args:
            calls_per_period (int): Number of calls allowed in the period
            period (float): Time period in seconds
        """
        self.calls_per_period = calls_per_period
        self.period = period
        self.timestamps: List[float] = []

    def wait(self) -> None:
        """Wait if necessary to comply with the rate limit."""
        current_time = time.time()

        # Remove timestamps older than the period
        self.timestamps = [t for t in self.timestamps if current_time - t < self.period]

        # If we've reached the limit, wait until we can make another call
        if len(self.timestamps) >= self.calls_per_period:
            sleep_time = self.period - (current_time - self.timestamps[0])
            if sleep_time > 0:
                logging.debug(f"Rate limiting: waiting for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                current_time = time.time()  # Update current time after sleeping

        # Record the timestamp for this call
        self.timestamps.append(current_time)
