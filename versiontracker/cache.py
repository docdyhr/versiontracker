"""Cache utilities for VersionTracker."""

import json
import logging
import os
import time
from typing import Any, Dict, Optional, cast

from versiontracker.exceptions import CacheError

# Define cache directory
CACHE_DIR = os.path.expanduser("~/.versiontracker/cache")


def _ensure_cache_dir():
    """Ensure cache directory exists."""
    try:
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR, exist_ok=True)
    except Exception as e:
        logging.error(f"Error creating cache directory: {e}")
        raise CacheError(f"Failed to create cache directory: {e}")


def read_cache(cache_name: str, max_age_seconds: int = 86400) -> Optional[Dict[str, Any]]:
    """Read data from cache.

    Args:
        cache_name: Name of the cache file
        max_age_seconds: Maximum age of cache in seconds (default: 1 day)

    Returns:
        Optional[Dict[str, Any]]: Cache data or None if not found or expired

    Raises:
        CacheError: If there's an error reading from cache
    """
    try:
        _ensure_cache_dir()

        cache_file = os.path.join(CACHE_DIR, f"{cache_name}.json")

        # Check if cache file exists
        if not os.path.exists(cache_file):
            return None

        # Check if cache is expired
        file_age = time.time() - os.path.getmtime(cache_file)
        if file_age > max_age_seconds:
            logging.debug(f"Cache {cache_name} expired (age: {file_age:.1f}s)")
            return None

        # Read cache
        with open(cache_file, "r") as f:
            data = json.load(f)

        return cast(Dict[str, Any], data)
    except json.JSONDecodeError as e:
        logging.warning(f"Invalid JSON in cache {cache_name}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error reading cache {cache_name}: {e}")
        return None


def write_cache(cache_name: str, data: Dict[str, Any]) -> bool:
    """Write data to cache.

    Args:
        cache_name: Name of the cache file
        data: Data to write

    Returns:
        bool: True if successful, False otherwise

    Raises:
        CacheError: If there's an error writing to cache
    """
    try:
        _ensure_cache_dir()

        cache_file = os.path.join(CACHE_DIR, f"{cache_name}.json")

        # Write cache
        with open(cache_file, "w") as f:
            json.dump(data, f)

        return True
    except Exception as e:
        logging.error(f"Error writing cache {cache_name}: {e}")
        raise CacheError(f"Failed to write to cache {cache_name}: {e}")


def clear_cache(cache_name: Optional[str] = None) -> bool:
    """Clear cache.

    Args:
        cache_name: Optional name of cache to clear, or None to clear all

    Returns:
        bool: True if successful, False otherwise

    Raises:
        CacheError: If there's an error clearing the cache
    """
    try:
        _ensure_cache_dir()

        if cache_name:
            # Clear specific cache
            cache_file = os.path.join(CACHE_DIR, f"{cache_name}.json")
            if os.path.exists(cache_file):
                os.remove(cache_file)
        else:
            # Clear all caches
            for filename in os.listdir(CACHE_DIR):
                if filename.endswith(".json"):
                    os.remove(os.path.join(CACHE_DIR, filename))

        return True
    except Exception as e:
        logging.error(f"Error clearing cache: {e}")
        raise CacheError(f"Failed to clear cache: {e}")
