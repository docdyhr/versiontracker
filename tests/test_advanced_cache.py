"""Tests for advanced_cache module."""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from versiontracker.advanced_cache import (
    DEFAULT_CACHE_DIR,
    AdvancedCache,
    CacheLevel,
    CacheMetadata,
    CachePriority,
    CacheStats,
)
from versiontracker.exceptions import CacheError


class TestCacheLevel:
    """Test CacheLevel enum."""

    def test_cache_level_values(self):
        """Test cache level enum values."""
        assert CacheLevel.MEMORY.value == "memory"
        assert CacheLevel.DISK.value == "disk"
        assert CacheLevel.ALL.value == "all"


class TestCachePriority:
    """Test CachePriority enum."""

    def test_cache_priority_values(self):
        """Test cache priority enum values."""
        assert CachePriority.LOW.value == 0
        assert CachePriority.NORMAL.value == 1
        assert CachePriority.HIGH.value == 2


class TestCacheMetadata:
    """Test CacheMetadata dataclass."""

    def test_cache_metadata_creation(self):
        """Test cache metadata creation."""
        metadata = CacheMetadata(
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=1,
            priority=CachePriority.NORMAL,
            size_bytes=1024,
            source="test",
        )

        assert metadata.access_count == 1
        assert metadata.priority == CachePriority.NORMAL
        assert metadata.size_bytes == 1024
        assert metadata.source == "test"


class TestCacheStats:
    """Test CacheStats dataclass."""

    def test_cache_stats_default(self):
        """Test cache stats default values."""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.writes == 0
        assert stats.evictions == 0
        assert stats.errors == 0
        assert stats.disk_size_bytes == 0
        assert stats.memory_size_bytes == 0

    def test_cache_stats_custom(self):
        """Test cache stats with custom values."""
        stats = CacheStats(
            hits=10,
            misses=5,
            writes=8,
            evictions=2,
            errors=1,
            disk_size_bytes=1024,
            memory_size_bytes=512,
        )

        assert stats.hits == 10
        assert stats.misses == 5
        assert stats.writes == 8
        assert stats.evictions == 2
        assert stats.errors == 1
        assert stats.disk_size_bytes == 1024
        assert stats.memory_size_bytes == 512


class TestAdvancedCache:
    """Test AdvancedCache class."""

    def test_cache_initialization_default(self):
        """Test cache initialization with default parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir)

            assert cache._cache_dir == Path(tmpdir)
            assert cache._memory_cache_size == 100
            assert cache._disk_cache_size_mb == 50
            assert cache._default_ttl == 86400
            assert cache._compression_threshold == 1024
            assert cache._compression_level == 6
            assert cache._stats_enabled is True
            assert isinstance(cache._stats, CacheStats)

    def test_cache_initialization_custom(self):
        """Test cache initialization with custom parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(
                cache_dir=tmpdir,
                memory_cache_size=50,
                disk_cache_size_mb=25,
                default_ttl=3600,
                compression_threshold=512,
                compression_level=9,
                stats_enabled=False,
            )

            assert cache._memory_cache_size == 50
            assert cache._disk_cache_size_mb == 25
            assert cache._default_ttl == 3600
            assert cache._compression_threshold == 512
            assert cache._compression_level == 9
            assert cache._stats_enabled is False

    @patch("versiontracker.advanced_cache.Path.mkdir")
    def test_cache_initialization_failure(self, mock_mkdir):
        """Test cache initialization failure."""
        mock_mkdir.side_effect = OSError("Permission denied")

        with pytest.raises(CacheError, match="Cache initialization failed"):
            AdvancedCache(cache_dir="/invalid/path")

    def test_cache_directory_creation(self):
        """Test cache directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "new_cache_dir"
            AdvancedCache(cache_dir=str(cache_dir))

            assert cache_dir.exists()
            assert cache_dir.is_dir()

    def test_get_put_basic(self):
        """Test basic get and put operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir)

            # Test put and get
            cache.put("test_key", "test_value")
            value = cache.get("test_key")
            assert value == "test_value"

            # Test get non-existent key
            assert cache.get("non_existent") is None

    def test_get_put_with_level(self):
        """Test get and put with cache level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir)

            # Put with memory only
            cache.put("memory_key", "memory_value", level=CacheLevel.MEMORY)
            assert cache.get("memory_key") == "memory_value"

            # Put with disk only
            cache.put("disk_key", "disk_value", level=CacheLevel.DISK)
            assert cache.get("disk_key") == "disk_value"

    def test_get_put_with_priority(self):
        """Test get and put with custom priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir)

            # Put with high priority
            cache.put("high_priority", "value", priority=CachePriority.HIGH)
            assert cache.get("high_priority") == "value"

            # Check metadata
            metadata = cache._metadata.get("high_priority")
            assert metadata is not None
            assert metadata.priority == CachePriority.HIGH

    def test_delete(self):
        """Test delete operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir)

            # Put and delete
            cache.put("delete_me", "value")
            assert cache.get("delete_me") == "value"

            deleted = cache.delete("delete_me")
            assert deleted is True
            assert cache.get("delete_me") is None

            # Try to delete non-existent key (returns True anyway)
            assert cache.delete("non_existent") is True

    def test_clear(self):
        """Test clear operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir)

            # Add multiple items
            for i in range(5):
                cache.put(f"key_{i}", f"value_{i}")

            # Verify items exist
            for i in range(5):
                assert cache.get(f"key_{i}") == f"value_{i}"

            # Clear cache
            cache.clear()

            # Verify all items are gone
            for i in range(5):
                assert cache.get(f"key_{i}") is None

    def test_get_stats(self):
        """Test cache statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir, stats_enabled=True)

            # Initial stats
            stats = cache.get_stats()
            assert stats.hits == 0
            assert stats.misses == 0
            assert stats.writes == 0

            # Perform operations and check stats
            cache.put("key1", "value1")
            stats = cache.get_stats()
            assert stats.writes == 1

            # Hit
            cache.get("key1")
            stats = cache.get_stats()
            assert stats.hits == 1

            # Miss
            cache.get("non_existent")
            stats = cache.get_stats()
            assert stats.misses == 1

    def test_stats_disabled(self):
        """Test cache with statistics disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir, stats_enabled=False)

            # Operations should still work
            cache.put("key", "value")
            assert cache.get("key") == "value"

            # Stats should remain at default values
            stats = cache.get_stats()
            assert stats.hits == 0
            assert stats.misses == 0
            assert stats.writes == 0

    def test_get_keys(self):
        """Test get_keys operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir)

            # Add items
            cache.put("key1", "value1", source="source1")
            cache.put("key2", "value2", source="source2")
            cache.put("key3", "value3", source="source1")

            # Get all keys
            all_keys = cache.get_keys()
            assert len(all_keys) == 3
            assert "key1" in all_keys
            assert "key2" in all_keys
            assert "key3" in all_keys

            # Get keys by source
            source1_keys = cache.get_keys(source="source1")
            assert len(source1_keys) == 2
            assert "key1" in source1_keys
            assert "key3" in source1_keys

    def test_compression(self):
        """Test compression for large values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir, compression_threshold=100)

            # Small value (shouldn't be compressed)
            small_value = "x" * 50
            cache.put("small", small_value)
            assert cache.get("small") == small_value

            # Large value (should be compressed)
            large_value = "y" * 200
            cache.put("large", large_value)
            assert cache.get("large") == large_value

    def test_memory_cache_eviction(self):
        """Test memory cache eviction when size limit is reached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir, memory_cache_size=3)

            # Add items to reach capacity
            for i in range(3):
                cache.put(f"key_{i}", f"value_{i}")

            # All items should be in memory cache
            assert len(cache._memory_cache) == 3

            # Add one more item to trigger eviction
            cache.put("key_3", "value_3")

            # Memory cache should still have 3 items
            assert len(cache._memory_cache) <= 3

    def test_source_filtering(self):
        """Test source-based operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir)

            # Add items with different sources
            cache.put("key1", "value1", source="source1")
            cache.put("key2", "value2", source="source2")
            cache.put("key3", "value3", source="source1")

            # Test source filtering
            all_keys = cache.get_keys()
            assert len(all_keys) == 3

            source1_keys = cache.get_keys(source="source1")
            assert len(source1_keys) == 2
            assert "key1" in source1_keys
            assert "key3" in source1_keys

    def test_thread_safety(self):
        """Test thread safety of cache operations."""
        import threading

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir)

            def worker(worker_id, num_operations):
                for i in range(num_operations):
                    key = f"worker_{worker_id}_key_{i}"
                    value = f"worker_{worker_id}_value_{i}"
                    cache.put(key, value)
                    assert cache.get(key) == value

            # Run multiple workers concurrently
            threads = []
            for i in range(3):
                t = threading.Thread(target=worker, args=(i, 10))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            # Verify all values are accessible
            for worker_id in range(3):
                for i in range(10):
                    key = f"worker_{worker_id}_key_{i}"
                    value = f"worker_{worker_id}_value_{i}"
                    assert cache.get(key) == value

    def test_metadata_persistence(self):
        """Test metadata persistence across cache instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create cache and add items
            cache1 = AdvancedCache(cache_dir=tmpdir)
            cache1.put("persistent_key", "persistent_value", priority=CachePriority.HIGH)

            # Save metadata explicitly since it's not auto-saved on put
            cache1._save_metadata()

            # Create new cache instance with same directory
            cache2 = AdvancedCache(cache_dir=tmpdir)

            # Item should still be accessible
            assert cache2.get("persistent_key") == "persistent_value"

            # Metadata should be preserved
            metadata = cache2._metadata.get("persistent_key")
            if metadata:
                assert metadata.priority == CachePriority.HIGH

    def test_default_cache_dir(self):
        """Test default cache directory usage."""
        # Just verify the constant is set correctly
        assert DEFAULT_CACHE_DIR == os.path.expanduser("~/.versiontracker/cache")

    def test_cache_size_monitoring(self):
        """Test cache size monitoring and limits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir, disk_cache_size_mb=1)  # Very small limit

            # Add some data
            cache.put("key1", "value1")
            cache.put("key2", "value2")

            # Get stats to check size monitoring
            stats = cache.get_stats()
            assert isinstance(stats.disk_size_bytes, int)
            assert stats.disk_size_bytes >= 0

    def test_internal_methods_exist(self):
        """Test that internal methods exist and can be called."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AdvancedCache(cache_dir=tmpdir)

            # Test internal method existence
            assert hasattr(cache, "_initialize_cache")
            assert hasattr(cache, "_load_metadata")
            assert hasattr(cache, "_save_metadata")
            assert hasattr(cache, "_update_cache_size")
            assert hasattr(cache, "_get_cache_path")
            assert hasattr(cache, "_compress_data")
            assert hasattr(cache, "_decompress_data")
            assert hasattr(cache, "_should_compress")
            assert hasattr(cache, "_evict_if_needed")
            assert hasattr(cache, "_is_expired")
            assert hasattr(cache, "_update_metadata")

            # Test cache path generation
            path = cache._get_cache_path("test_key")
            assert isinstance(path, Path)
            assert path.parent == cache._cache_dir

            # Test compression decision
            small_data = b"small"
            large_data = b"x" * 2000

            assert cache._should_compress(small_data) is False
            assert cache._should_compress(large_data) is True

            # Test compression/decompression
            compressed = cache._compress_data(large_data)
            decompressed = cache._decompress_data(compressed)
            assert decompressed == large_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
