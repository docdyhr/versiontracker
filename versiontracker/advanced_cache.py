"""Advanced caching mechanism for VersionTracker.

This module provides an enhanced caching system for Homebrew queries and other
network operations, with features like:

1. Tiered caching (memory and disk)
2. Automatic expiry based on access patterns
3. Cache statistics and monitoring
4. Thread-safe operations
5. Cache compression for large responses
6. Batch operations for efficient updates

These features help reduce network calls, improve performance, and provide
better user experience when working with Homebrew data.
"""

import gzip
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

from versiontracker.exceptions import CacheError

# Type variable for generic cache value type
T = TypeVar("T")

# Define cache directory
DEFAULT_CACHE_DIR = os.path.expanduser("~/.versiontracker/cache")


class CacheLevel(Enum):
    """Cache level enum for tiered caching."""

    MEMORY = "memory"  # Memory cache only
    DISK = "disk"  # Disk cache only
    ALL = "all"  # Both memory and disk cache


class CachePriority(Enum):
    """Cache priority enum for expiry policies."""

    LOW = 0  # Cached items with low priority will be expired first
    NORMAL = 1  # Normal priority
    HIGH = 2  # High priority items will be kept longer


@dataclass
class CacheMetadata:
    """Metadata for cached items."""

    created_at: float  # Timestamp when the item was created
    last_accessed: float  # Timestamp when the item was last accessed
    access_count: int  # Number of times the item was accessed
    priority: CachePriority  # Priority of the item
    size_bytes: int  # Size of the item in bytes
    source: str  # Source of the data (e.g., "homebrew", "app_store")


@dataclass
class CacheStats:
    """Statistics for cache operations."""

    hits: int = 0  # Number of cache hits
    misses: int = 0  # Number of cache misses
    writes: int = 0  # Number of cache writes
    evictions: int = 0  # Number of cache evictions
    errors: int = 0  # Number of cache errors
    disk_size_bytes: int = 0  # Total size of disk cache in bytes
    memory_size_bytes: int = 0  # Total size of memory cache in bytes


class AdvancedCache:
    """Advanced caching system with tiered storage and expiry policies."""

    def __init__(
        self,
        cache_dir: str = DEFAULT_CACHE_DIR,
        memory_cache_size: int = 100,  # Max number of items in memory cache
        disk_cache_size_mb: int = 50,  # Max size of disk cache in MB
        default_ttl: int = 86400,  # Default TTL in seconds (1 day)
        compression_threshold: int = 1024,  # Compress items larger than this (bytes)
        compression_level: int = 6,  # Compression level (1-9, higher = more compression)
        stats_enabled: bool = True,  # Enable cache statistics
    ):
        """Initialize the cache.

        Args:
            cache_dir: Directory for disk cache
            memory_cache_size: Maximum number of items in memory cache
            disk_cache_size_mb: Maximum size of disk cache in MB
            default_ttl: Default time-to-live for cache items in seconds
            compression_threshold: Size threshold for compression in bytes
            compression_level: Compression level (1-9)
            stats_enabled: Whether to collect cache statistics

        Raises:
            CacheError: If cache initialization fails
        """
        self._cache_dir = Path(cache_dir)
        self._memory_cache: Dict[str, Any] = {}
        self._metadata: Dict[str, CacheMetadata] = {}
        self._memory_cache_size = memory_cache_size
        self._disk_cache_size_mb = disk_cache_size_mb
        self._default_ttl = default_ttl
        self._compression_threshold = compression_threshold
        self._compression_level = compression_level
        self._stats_enabled = stats_enabled
        self._stats = CacheStats()
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._initialize_cache()

    def _initialize_cache(self) -> None:
        """Initialize the cache directory and load metadata.

        Raises:
            CacheError: If cache initialization fails
        """
        try:
            # Create cache directory if it doesn't exist
            self._cache_dir.mkdir(parents=True, exist_ok=True)

            # Load metadata for existing cache files
            self._load_metadata()

            # Calculate initial cache size
            self._update_cache_size()
        except Exception as e:
            logging.error(f"Failed to initialize cache: {e}")
            raise CacheError(f"Cache initialization failed: {e}")

    def _load_metadata(self) -> None:
        """Load metadata for existing cache files.

        This loads metadata for all files in the cache directory.
        """
        metadata_file = self._cache_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, "r") as f:
                    metadata_dict = json.load(f)

                # Convert the dictionary back to CacheMetadata objects
                for key, meta in metadata_dict.items():
                    self._metadata[key] = CacheMetadata(
                        created_at=meta["created_at"],
                        last_accessed=meta["last_accessed"],
                        access_count=meta["access_count"],
                        priority=CachePriority(meta["priority"]),
                        size_bytes=meta["size_bytes"],
                        source=meta["source"],
                    )
            except Exception as e:
                logging.warning(f"Failed to load cache metadata: {e}")
                # Continue without metadata, it will be rebuilt as items are accessed

    def _save_metadata(self) -> None:
        """Save metadata for cache files."""
        metadata_file = self._cache_dir / "metadata.json"
        try:
            # Convert CacheMetadata objects to dictionaries
            metadata_dict = {}
            for key, meta in self._metadata.items():
                metadata_dict[key] = {
                    "created_at": meta.created_at,
                    "last_accessed": meta.last_accessed,
                    "access_count": meta.access_count,
                    "priority": meta.priority.value,
                    "size_bytes": meta.size_bytes,
                    "source": meta.source,
                }

            with open(metadata_file, "w") as f:
                json.dump(metadata_dict, f)
        except Exception as e:
            logging.warning(f"Failed to save cache metadata: {e}")

    def _update_cache_size(self) -> None:
        """Update cache size statistics."""
        if not self._stats_enabled:
            return

        disk_size = 0
        for file_path in self._cache_dir.glob("*.cache"):
            try:
                disk_size += file_path.stat().st_size
            except (FileNotFoundError, PermissionError):
                pass

        memory_size = sum(len(json.dumps(v).encode()) for v in self._memory_cache.values())

        self._stats.disk_size_bytes = disk_size
        self._stats.memory_size_bytes = memory_size

    def _get_cache_path(self, key: str) -> Path:
        """Get the path for a cache file.

        Args:
            key: Cache key

        Returns:
            Path: Path to the cache file
        """
        # Sanitize key for use as a filename
        safe_key = "".join(c if c.isalnum() else "_" for c in key)
        return self._cache_dir / f"{safe_key}.cache"

    def _compress_data(self, data: bytes) -> bytes:
        """Compress data using gzip.

        Args:
            data: Data to compress

        Returns:
            bytes: Compressed data
        """
        return gzip.compress(data, compresslevel=self._compression_level)

    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress data using gzip.

        Args:
            data: Data to decompress

        Returns:
            bytes: Decompressed data
        """
        return gzip.decompress(data)

    def _should_compress(self, data: bytes) -> bool:
        """Determine if data should be compressed.

        Args:
            data: Data to check

        Returns:
            bool: True if data should be compressed
        """
        return len(data) > self._compression_threshold

    def _evict_if_needed(self) -> None:
        """Evict items from cache if it exceeds size limits."""
        with self._lock:
            # Check memory cache size
            if len(self._memory_cache) > self._memory_cache_size:
                self._evict_from_memory(len(self._memory_cache) - self._memory_cache_size)

            # Check disk cache size
            disk_size_mb = self._stats.disk_size_bytes / (1024 * 1024)
            if disk_size_mb > self._disk_cache_size_mb:
                # Calculate how many MB to free
                mb_to_free = disk_size_mb - self._disk_cache_size_mb
                # Roughly estimate how many items to evict (assume average 100KB per item)
                items_to_evict = int((mb_to_free * 1024) / 100) + 1
                self._evict_from_disk(items_to_evict)

    def _evict_from_memory(self, count: int) -> None:
        """Evict items from memory cache.

        Args:
            count: Number of items to evict
        """
        if not self._memory_cache:
            return

        # Sort items by priority (ascending), then by last accessed (ascending)
        items_to_evict = sorted(
            self._memory_cache.keys(),
            key=lambda k: (
                self._metadata.get(k, CacheMetadata(0, 0, 0, CachePriority.LOW, 0, "")).priority.value,
                self._metadata.get(k, CacheMetadata(0, 0, 0, CachePriority.LOW, 0, "")).last_accessed,
            ),
        )

        # Evict the specified number of items
        for key in items_to_evict[:count]:
            if key in self._memory_cache:
                del self._memory_cache[key]
                if self._stats_enabled:
                    self._stats.evictions += 1

    def _evict_from_disk(self, count: int) -> None:
        """Evict items from disk cache.

        Args:
            count: Number of items to evict
        """
        # Get all cache files
        cache_files = list(self._cache_dir.glob("*.cache"))
        if not cache_files:
            return

        # Sort by priority and last accessed time
        items_to_evict = sorted(
            [f.stem for f in cache_files],
            key=lambda k: (
                self._metadata.get(k, CacheMetadata(0, 0, 0, CachePriority.LOW, 0, "")).priority.value,
                self._metadata.get(k, CacheMetadata(0, 0, 0, CachePriority.LOW, 0, "")).last_accessed,
            ),
        )

        # Evict the specified number of items
        for key in items_to_evict[:count]:
            cache_path = self._get_cache_path(key)
            try:
                if cache_path.exists():
                    cache_path.unlink()
                    if key in self._metadata:
                        del self._metadata[key]
                    if self._stats_enabled:
                        self._stats.evictions += 1
            except (FileNotFoundError, PermissionError) as e:
                logging.warning(f"Failed to evict cache item {key}: {e}")

    def _is_expired(self, key: str, ttl: int) -> bool:
        """Check if a cache item is expired.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            bool: True if the item is expired
        """
        if key not in self._metadata:
            return True

        metadata = self._metadata[key]
        current_time = time.time()
        return current_time - metadata.created_at > ttl

    def _update_metadata(
        self,
        key: str,
        size_bytes: int,
        source: str,
        priority: CachePriority,
        is_access: bool = False,
    ) -> None:
        """Update metadata for a cache item.

        Args:
            key: Cache key
            size_bytes: Size of the item in bytes
            source: Source of the data
            priority: Priority of the item
            is_access: Whether this is an access operation
        """
        current_time = time.time()

        if key in self._metadata:
            metadata = self._metadata[key]
            if is_access:
                metadata.last_accessed = current_time
                metadata.access_count += 1
            else:
                metadata.created_at = current_time
                metadata.last_accessed = current_time
                metadata.size_bytes = size_bytes
                metadata.source = source
                metadata.priority = priority
        else:
            self._metadata[key] = CacheMetadata(
                created_at=current_time,
                last_accessed=current_time,
                access_count=1 if is_access else 0,
                priority=priority,
                size_bytes=size_bytes,
                source=source,
            )

    def get(self, key: str, level: CacheLevel = CacheLevel.ALL, ttl: Optional[int] = None) -> Optional[T]:
        """Get item from cache.

        Args:
            key: Cache key
            level: Cache level to check
            ttl: Time-to-live in seconds (None to use default)

        Returns:
            Optional[T]: Cached value or None if not found or expired

        Raises:
            CacheError: If there's an error reading from cache
        """
        ttl = ttl if ttl is not None else self._default_ttl

        with self._lock:
            # Check memory cache first if requested
            if level in (CacheLevel.MEMORY, CacheLevel.ALL) and key in self._memory_cache:
                if self._is_expired(key, ttl):
                    # Item is expired, remove it
                    del self._memory_cache[key]
                    if self._stats_enabled:
                        self._stats.misses += 1
                    return None

                # Update access metadata
                self._update_metadata(key, 0, "", CachePriority.NORMAL, is_access=True)

                if self._stats_enabled:
                    self._stats.hits += 1

                return cast(T, self._memory_cache[key])

            # Check disk cache if requested
            if level in (CacheLevel.DISK, CacheLevel.ALL):
                cache_path = self._get_cache_path(key)
                try:
                    if cache_path.exists():
                        if self._is_expired(key, ttl):
                            # Item is expired, remove it
                            cache_path.unlink()
                            if key in self._metadata:
                                del self._metadata[key]
                            if self._stats_enabled:
                                self._stats.misses += 1
                            return None

                        # Read data from disk
                        with open(cache_path, "rb") as f:
                            data = f.read()

                        # Check if data is compressed
                        try:
                            if data[:2] == b"\x1f\x8b":  # gzip magic number
                                data = self._decompress_data(data)
                            value = json.loads(data.decode("utf-8"))
                        except (json.JSONDecodeError, UnicodeDecodeError) as e:
                            logging.warning(f"Invalid data in cache {key}: {e}")
                            if self._stats_enabled:
                                self._stats.errors += 1
                            return None

                        # Update access metadata
                        self._update_metadata(key, len(data), "", CachePriority.NORMAL, is_access=True)

                        # Store in memory cache for faster access next time
                        if level == CacheLevel.ALL:
                            self._memory_cache[key] = value
                            self._evict_if_needed()

                        if self._stats_enabled:
                            self._stats.hits += 1

                        return cast(T, value)
                except Exception as e:
                    logging.error(f"Error reading cache {key}: {e}")
                    if self._stats_enabled:
                        self._stats.errors += 1
                    raise CacheError(f"Failed to read from cache {key}: {e}")

            if self._stats_enabled:
                self._stats.misses += 1

            return None

    def put(
        self,
        key: str,
        value: T,
        level: CacheLevel = CacheLevel.ALL,
        priority: CachePriority = CachePriority.NORMAL,
        source: str = "",
    ) -> bool:
        """Put item in cache.

        Args:
            key: Cache key
            value: Value to cache
            level: Cache level to store in
            priority: Priority of the item
            source: Source of the data

        Returns:
            bool: True if successful

        Raises:
            CacheError: If there's an error writing to cache
        """
        with self._lock:
            try:
                # Convert value to JSON string
                json_data = json.dumps(value)
                data = json_data.encode("utf-8")
                data_size = len(data)

                # Compress if needed
                if self._should_compress(data):
                    data = self._compress_data(data)

                # Store in memory cache if requested
                if level in (CacheLevel.MEMORY, CacheLevel.ALL):
                    self._memory_cache[key] = value

                # Store on disk if requested
                if level in (CacheLevel.DISK, CacheLevel.ALL):
                    cache_path = self._get_cache_path(key)
                    with open(cache_path, "wb") as f:
                        f.write(data)

                # Update metadata
                self._update_metadata(key, data_size, source, priority)

                # Evict items if cache is full
                self._evict_if_needed()

                if self._stats_enabled:
                    self._stats.writes += 1
                    self._update_cache_size()

                return True
            except Exception as e:
                logging.error(f"Error writing cache {key}: {e}")
                if self._stats_enabled:
                    self._stats.errors += 1
                raise CacheError(f"Failed to write to cache {key}: {e}")

    def delete(self, key: str) -> bool:
        """Delete item from cache.

        Args:
            key: Cache key

        Returns:
            bool: True if successful

        Raises:
            CacheError: If there's an error deleting from cache
        """
        with self._lock:
            try:
                # Remove from memory cache
                if key in self._memory_cache:
                    del self._memory_cache[key]

                # Remove from disk cache
                cache_path = self._get_cache_path(key)
                if cache_path.exists():
                    cache_path.unlink()

                # Remove metadata
                if key in self._metadata:
                    del self._metadata[key]

                if self._stats_enabled:
                    self._update_cache_size()

                return True
            except Exception as e:
                logging.error(f"Error deleting cache {key}: {e}")
                if self._stats_enabled:
                    self._stats.errors += 1
                raise CacheError(f"Failed to delete from cache {key}: {e}")

    def clear(self, source: Optional[str] = None) -> bool:
        """Clear cache.

        Args:
            source: Optional source to clear (only items from this source)

        Returns:
            bool: True if successful

        Raises:
            CacheError: If there's an error clearing the cache
        """
        with self._lock:
            try:
                if source:
                    # Clear only items from the specified source
                    keys_to_delete = [key for key, meta in self._metadata.items() if meta.source == source]

                    # Delete each item
                    for key in keys_to_delete:
                        self.delete(key)
                else:
                    # Clear memory cache
                    self._memory_cache.clear()

                    # Clear disk cache
                    for cache_path in self._cache_dir.glob("*.cache"):
                        try:
                            cache_path.unlink()
                        except (FileNotFoundError, PermissionError):
                            pass

                    # Clear metadata
                    self._metadata.clear()

                if self._stats_enabled:
                    self._update_cache_size()

                return True
            except Exception as e:
                logging.error(f"Error clearing cache: {e}")
                if self._stats_enabled:
                    self._stats.errors += 1
                raise CacheError(f"Failed to clear cache: {e}")

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            CacheStats: Cache statistics
        """
        if self._stats_enabled:
            self._update_cache_size()
        return self._stats

    def get_keys(self, source: Optional[str] = None) -> List[str]:
        """Get all cache keys.

        Args:
            source: Optional source to filter by

        Returns:
            List[str]: List of cache keys
        """
        with self._lock:
            if source:
                return [key for key, meta in self._metadata.items() if meta.source == source]
            return list(self._metadata.keys())

    def get_size_mb(self) -> float:
        """Get total cache size in MB.

        Returns:
            float: Cache size in MB
        """
        if self._stats_enabled:
            self._update_cache_size()
        total_bytes = self._stats.disk_size_bytes + self._stats.memory_size_bytes
        return total_bytes / (1024 * 1024)

    def exists(self, key: str, level: CacheLevel = CacheLevel.ALL) -> bool:
        """Check if item exists in cache.

        Args:
            key: Cache key
            level: Cache level to check

        Returns:
            bool: True if item exists in cache
        """
        with self._lock:
            # Check memory cache
            if level in (CacheLevel.MEMORY, CacheLevel.ALL) and key in self._memory_cache:
                return True

            # Check disk cache
            if level in (CacheLevel.DISK, CacheLevel.ALL):
                cache_path = self._get_cache_path(key)
                return cache_path.exists()

            return False

    def get_or_set(
        self,
        key: str,
        getter_func: Callable[[], T],
        level: CacheLevel = CacheLevel.ALL,
        ttl: Optional[int] = None,
        priority: CachePriority = CachePriority.NORMAL,
        source: str = "",
    ) -> T:
        """Get item from cache or set it if not found.

        Args:
            key: Cache key
            getter_func: Function to call if item is not in cache
            level: Cache level to check/store
            ttl: Time-to-live in seconds (None to use default)
            priority: Priority of the item
            source: Source of the data

        Returns:
            T: Cached or new value

        Raises:
            CacheError: If there's an error accessing the cache
        """
        # Try to get from cache
        cached_value = self.get(key, level, ttl)
        if cached_value is not None:
            return cached_value  # type: ignore

        # Not in cache, call getter function and store it
        value = getter_func()
        self.put(key, value, level, priority, source)
        return value

    def batch_get(
        self,
        keys: List[str],
        level: CacheLevel = CacheLevel.ALL,
        ttl: Optional[int] = None,
    ) -> Dict[str, Optional[T]]:
        """Get multiple items from cache.

        Args:
            keys: List of cache keys
            level: Cache level to check
            ttl: Time-to-live in seconds (None to use default)

        Returns:
            Dict[str, Optional[T]]: Dictionary of cache keys to values
        """
        result: Dict[str, Optional[T]] = {}
        for key in keys:
            result[key] = self.get(key, level, ttl)
        return result

    def batch_put(
        self,
        items: Dict[str, T],
        level: CacheLevel = CacheLevel.ALL,
        priority: CachePriority = CachePriority.NORMAL,
        source: str = "",
    ) -> bool:
        """Put multiple items in cache.

        Args:
            items: Dictionary of cache keys to values
            level: Cache level to store in
            priority: Priority of the items
            source: Source of the data

        Returns:
            bool: True if all operations were successful
        """
        success = True
        for key, value in items.items():
            try:
                self.put(key, value, level, priority, source)
            except Exception as e:
                logging.error(f"Error in batch put for key {key}: {e}")
                success = False
        return success

    def save_metadata_to_disk(self) -> bool:
        """Save metadata to disk.

        Returns:
            bool: True if successful
        """
        try:
            self._save_metadata()
            return True
        except Exception as e:
            logging.error(f"Error saving metadata: {e}")
            return False

    def load_metadata_from_disk(self) -> bool:
        """Load metadata from disk.

        Returns:
            bool: True if successful
        """
        try:
            self._load_metadata()
            return True
        except Exception as e:
            logging.error(f"Error loading metadata: {e}")
            return False


# Create a global cache instance
_cache_instance: Optional[AdvancedCache] = None


def get_cache() -> AdvancedCache:
    """Get the global cache instance.

    Returns:
        AdvancedCache: Global cache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = AdvancedCache()
    return _cache_instance


def set_cache_instance(cache: AdvancedCache) -> None:
    """Set the global cache instance.

    Args:
        cache: Cache instance to use
    """
    global _cache_instance
    _cache_instance = cache
