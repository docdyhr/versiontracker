"""Homebrew query module for VersionTracker.

This module provides functions for querying Homebrew casks with advanced caching
to reduce network calls and improve performance. It implements batch operations,
rate limiting, and error handling for Homebrew-related operations.
"""

import json
import logging
import os
import re
import subprocess
import time
from typing import Any, Dict, List

from versiontracker.advanced_cache import (
    CacheLevel,
    CachePriority,
    get_cache,
)
from versiontracker.config import get_config
from versiontracker.exceptions import DataParsingError, HomebrewError, NetworkError
from versiontracker.ui import create_progress_bar
from versiontracker.utils import run_command

# Cache keys for different Homebrew operations
CACHE_KEY_ALL_CASKS = "homebrew:all_casks"
CACHE_KEY_CASK_PREFIX = "homebrew:cask:"
CACHE_KEY_SEARCH_PREFIX = "homebrew:search:"
CACHE_KEY_INFO_PREFIX = "homebrew:info:"

# Cache TTLs (in seconds)
CACHE_TTL_ALL_CASKS = 86400  # 1 day
CACHE_TTL_CASK_INFO = 43200  # 12 hours
CACHE_TTL_SEARCH = 86400  # 1 day

# Batch size for parallel operations
DEFAULT_BATCH_SIZE = 10


def is_homebrew_available() -> bool:
    """Check if Homebrew is available on the system.

    Returns:
        bool: True if Homebrew is available
    """
    try:
        # Try to run brew --version
        stdout, returncode = run_command("brew --version", timeout=5)
        return returncode == 0
    except Exception as e:
        logging.warning(f"Homebrew availability check failed: {e}")
        return False


def get_homebrew_path() -> str:
    """Get the path to the Homebrew executable.

    Returns:
        str: Path to Homebrew executable

    Raises:
        HomebrewError: If Homebrew is not found
    """
    try:
        # Check common locations
        common_paths = [
            "/usr/local/bin/brew",  # Intel Mac
            "/opt/homebrew/bin/brew",  # Apple Silicon Mac
            os.path.expanduser("~/.homebrew/bin/brew"),  # Custom install
        ]

        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path

        # Try to find using which
        stdout, returncode = run_command("which brew", timeout=5)
        if returncode == 0 and stdout.strip():
            return stdout.strip()

        raise HomebrewError("Homebrew not found in common locations")
    except Exception as e:
        logging.error(f"Failed to find Homebrew: {e}")
        raise HomebrewError(f"Homebrew not found: {e}")


def get_brew_command() -> str:
    """Return the Homebrew command path, using system detection and config if available.

    Returns:
        str: The path to the Homebrew executable
    Raises:
        HomebrewError: If Homebrew cannot be found
    """
    # Try config first
    config = get_config()
    brew_path = getattr(config, "brew_path", None)
    if isinstance(brew_path, str) and os.path.exists(brew_path):
        return str(brew_path)
    # Fallback to detection logic
    return get_homebrew_path()


def get_all_homebrew_casks() -> List[Dict[str, Any]]:
    """Get a list of all available Homebrew casks with advanced caching.

    Returns:
        List[Dict[str, Any]]: List of cask data dictionaries

    Raises:
        HomebrewError: If there's an error retrieving casks
        NetworkError: If there's a network error
        DataParsingError: If there's an error parsing the response
    """
    cache = get_cache()

    # Try to get from cache first
    cached_casks = cache.get(CACHE_KEY_ALL_CASKS, ttl=CACHE_TTL_ALL_CASKS)
    if cached_casks is not None:
        return cached_casks

    try:
        brew_path = get_brew_command()
        command = f"{brew_path} info --json=v2 --cask $(ls $(brew --repository)/Library/Taps/homebrew/homebrew-cask/Casks/)"

        # Show progress message
        progress_bar = create_progress_bar()
        print(progress_bar.color("blue")("Fetching all Homebrew casks (this may take a while)..."))

        # Execute command with timeout
        stdout, returncode = run_command(command, timeout=120)  # 2 minute timeout

        if returncode != 0:
            error_msg = f"Failed to retrieve Homebrew casks: {stdout}"
            logging.error(error_msg)
            raise HomebrewError(error_msg)

        try:
            # Parse JSON response
            data = json.loads(stdout)
            casks = data.get("casks", [])

            # Store in cache
            cache.put(
                CACHE_KEY_ALL_CASKS,
                casks,
                level=CacheLevel.ALL,
                priority=CachePriority.HIGH,
                source="homebrew",
            )

            return casks
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse Homebrew casks JSON: {e}"
            logging.error(error_msg)
            raise DataParsingError(error_msg)
    except subprocess.TimeoutExpired as e:
        error_msg = f"Timeout while retrieving Homebrew casks: {e}"
        logging.error(error_msg)
        raise NetworkError(error_msg)
    except Exception as e:
        error_msg = f"Error retrieving Homebrew casks: {e}"
        logging.error(error_msg)
        raise HomebrewError(error_msg)


def get_cask_info(cask_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific Homebrew cask.

    Args:
        cask_name: Name of the cask

    Returns:
        Dict[str, Any]: Cask information

    Raises:
        HomebrewError: If there's an error retrieving cask info
        NetworkError: If there's a network error
        DataParsingError: If there's an error parsing the response
    """
    cache = get_cache()
    cache_key = f"{CACHE_KEY_CASK_PREFIX}{cask_name}"

    # Try to get from cache first
    cached_info = cache.get(cache_key, ttl=CACHE_TTL_CASK_INFO)
    if cached_info is not None:
        return cached_info

    try:
        brew_path = get_brew_command()
        command = f"{brew_path} info --json=v2 --cask {cask_name}"

        # Execute command with timeout
        stdout, returncode = run_command(command, timeout=30)

        if returncode != 0:
            error_msg = f"Failed to retrieve info for cask {cask_name}: {stdout}"
            logging.error(error_msg)
            raise HomebrewError(error_msg)

        try:
            # Parse JSON response
            data = json.loads(stdout)
            casks = data.get("casks", [])

            if not casks:
                error_msg = f"No information found for cask {cask_name}"
                logging.warning(error_msg)
                return {}

            cask_info = casks[0]

            # Store in cache
            cache.put(
                cache_key,
                cask_info,
                level=CacheLevel.ALL,
                priority=CachePriority.NORMAL,
                source="homebrew",
            )

            return cask_info
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse cask info JSON for {cask_name}: {e}"
            logging.error(error_msg)
            raise DataParsingError(error_msg)
    except subprocess.TimeoutExpired as e:
        error_msg = f"Timeout while retrieving info for cask {cask_name}: {e}"
        logging.error(error_msg)
        raise NetworkError(error_msg)
    except Exception as e:
        error_msg = f"Error retrieving info for cask {cask_name}: {e}"
        logging.error(error_msg)
        raise HomebrewError(error_msg)


def search_casks(query: str) -> List[Dict[str, Any]]:
    """Search for Homebrew casks matching a query.

    Args:
        query: Search query

    Returns:
        List[Dict[str, Any]]: List of matching cask data dictionaries

    Raises:
        HomebrewError: If there's an error searching for casks
        NetworkError: If there's a network error
        DataParsingError: If there's an error parsing the response
    """
    cache = get_cache()
    cache_key = f"{CACHE_KEY_SEARCH_PREFIX}{query}"

    # Try to get from cache first
    cached_results = cache.get(cache_key, ttl=CACHE_TTL_SEARCH)
    if cached_results is not None:
        return cached_results

    try:
        brew_path = get_brew_command()
        # Escape special characters in query
        safe_query = re.sub(r'([^\w\s-])', r'\\\1', query)
        command = f"{brew_path} search --cask --json=v2 {safe_query}"

        # Execute command with timeout
        stdout, returncode = run_command(command, timeout=30)

        if returncode != 0:
            error_msg = f"Failed to search for casks with query '{query}': {stdout}"
            logging.error(error_msg)
            raise HomebrewError(error_msg)

        try:
            # Parse JSON response
            data = json.loads(stdout)
            casks = data.get("casks", [])

            # Store in cache
            cache.put(
                cache_key,
                casks,
                level=CacheLevel.ALL,
                priority=CachePriority.NORMAL,
                source="homebrew",
            )

            return casks
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse search results JSON for '{query}': {e}"
            logging.error(error_msg)
            raise DataParsingError(error_msg)
    except subprocess.TimeoutExpired as e:
        error_msg = f"Timeout while searching for casks with query '{query}': {e}"
        logging.error(error_msg)
        raise NetworkError(error_msg)
    except Exception as e:
        error_msg = f"Error searching for casks with query '{query}': {e}"
        logging.error(error_msg)
        raise HomebrewError(error_msg)


def batch_get_cask_info(cask_names: List[str]) -> Dict[str, Dict[str, Any]]:
    """Get information for multiple casks in a batch operation.

    Args:
        cask_names: List of cask names

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary mapping cask names to their info

    Raises:
        HomebrewError: If there's an error retrieving cask info
    """
    if not cask_names:
        return {}

    cache = get_cache()
    result: Dict[str, Dict[str, Any]] = {}
    casks_to_fetch: List[str] = []

    # Check cache first for all casks
    for cask_name in cask_names:
        cache_key = f"{CACHE_KEY_CASK_PREFIX}{cask_name}"
        cached_info = cache.get(cache_key, ttl=CACHE_TTL_CASK_INFO)

        if cached_info is not None:
            result[cask_name] = cached_info
        else:
            casks_to_fetch.append(cask_name)

    # If all casks were in cache, return early
    if not casks_to_fetch:
        return result

    # Process remaining casks in batches
    config = get_config()
    batch_size = getattr(config, "homebrew_batch_size", DEFAULT_BATCH_SIZE)
    progress_bar = create_progress_bar()

    print(progress_bar.color("blue")(f"Fetching info for {len(casks_to_fetch)} casks..."))

    for i in range(0, len(casks_to_fetch), batch_size):
        batch = casks_to_fetch[i:i + batch_size]

        try:
            # Construct a command to get info for multiple casks at once
            brew_path = get_brew_command()
            casks_arg = " ".join(batch)
            command = f"{brew_path} info --json=v2 --cask {casks_arg}"

            # Execute command with timeout
            stdout, returncode = run_command(command, timeout=60)

            if returncode != 0:
                logging.warning(f"Failed to retrieve info for cask batch: {stdout}")
                # Continue with next batch rather than failing completely
                continue

            try:
                # Parse JSON response
                data = json.loads(stdout)
                casks = data.get("casks", [])

                # Process each cask in the response
                for cask in casks:
                    cask_name = cask.get("token")
                    if cask_name:
                        # Store in result
                        result[cask_name] = cask

                        # Store in cache
                        cache_key = f"{CACHE_KEY_CASK_PREFIX}{cask_name}"
                        cache.put(
                            cache_key,
                            cask,
                            level=CacheLevel.ALL,
                            priority=CachePriority.NORMAL,
                            source="homebrew",
                        )
            except json.JSONDecodeError as e:
                logging.warning(f"Failed to parse cask info JSON for batch: {e}")
                # Continue with next batch
                continue

            # Rate limiting to avoid overloading Homebrew
            rate_limit = getattr(config, "api_rate_limit", 0.5)
            if rate_limit > 0 and i + batch_size < len(casks_to_fetch):
                time.sleep(rate_limit)

        except Exception as e:
            logging.warning(f"Error retrieving info for cask batch: {e}")
            # Continue with next batch
            continue

    return result


def get_installed_homebrew_casks() -> List[Dict[str, Any]]:
    """Get a list of all installed Homebrew casks.

    Returns:
        List[Dict[str, Any]]: List of installed cask data dictionaries

    Raises:
        HomebrewError: If there's an error retrieving installed casks
        NetworkError: If there's a network error
        DataParsingError: If there's an error parsing the response
    """
    try:
        brew_path = get_brew_command()
        command = f"{brew_path} list --cask --json=v2"

        # Execute command with timeout
        stdout, returncode = run_command(command, timeout=30)

        if returncode != 0:
            error_msg = f"Failed to retrieve installed Homebrew casks: {stdout}"
            logging.error(error_msg)
            raise HomebrewError(error_msg)

        try:
            # Parse JSON response
            data = json.loads(stdout)
            casks = data.get("casks", [])

            return casks
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse installed casks JSON: {e}"
            logging.error(error_msg)
            raise DataParsingError(error_msg)
    except subprocess.TimeoutExpired as e:
        error_msg = f"Timeout while retrieving installed casks: {e}"
        logging.error(error_msg)
        raise NetworkError(error_msg)
    except Exception as e:
        error_msg = f"Error retrieving installed casks: {e}"
        logging.error(error_msg)
        raise HomebrewError(error_msg)


def clear_homebrew_cache() -> bool:
    """Clear all Homebrew-related cache.

    Returns:
        bool: True if cache was cleared successfully
    """
    cache = get_cache()
    return cache.clear(source="homebrew")


def get_outdated_homebrew_casks() -> List[Dict[str, Any]]:
    """Get a list of outdated Homebrew casks.

    Returns:
        List[Dict[str, Any]]: List of outdated cask data dictionaries

    Raises:
        HomebrewError: If there's an error retrieving outdated casks
        NetworkError: If there's a network error
        DataParsingError: If there's an error parsing the response
    """
    try:
        brew_path = get_brew_command()
        command = f"{brew_path} outdated --cask --json=v2"

        # Execute command with timeout
        stdout, returncode = run_command(command, timeout=30)

        if returncode != 0:
            error_msg = f"Failed to retrieve outdated Homebrew casks: {stdout}"
            logging.error(error_msg)
            raise HomebrewError(error_msg)

        try:
            # Parse JSON response
            data = json.loads(stdout)
            casks = data.get("casks", [])

            return casks
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse outdated casks JSON: {e}"
            logging.error(error_msg)
            raise DataParsingError(error_msg)
    except subprocess.TimeoutExpired as e:
        error_msg = f"Timeout while retrieving outdated casks: {e}"
        logging.error(error_msg)
        raise NetworkError(error_msg)
    except Exception as e:
        error_msg = f"Error retrieving outdated casks: {e}"
        logging.error(error_msg)
        raise HomebrewError(error_msg)


def get_cask_version(cask_name: str) -> str:
    """Get the current version of a Homebrew cask.

    Args:
        cask_name: Name of the cask

    Returns:
        str: Current version of the cask

    Raises:
        HomebrewError: If there's an error retrieving the cask version
    """
    try:
        cask_info = get_cask_info(cask_name)
        return str(cask_info.get("version", ""))
    except Exception as e:
        error_msg = f"Error retrieving version for cask {cask_name}: {e}"
        logging.error(error_msg)
        raise HomebrewError(error_msg)


def get_caskroom_path() -> str:
    """Return the default Homebrew Caskroom path used for cask installations.

    Returns:
        str: The path to the Homebrew Caskroom directory
    """
    # Standard Homebrew Caskroom location
    paths = [
        "/usr/local/Caskroom",  # Intel Macs
        "/opt/homebrew/Caskroom",  # Apple Silicon Macs
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    # Fallback to the first path if none exist
    return paths[0]
