"""Simple in-memory cache with TTL for API responses."""
import time
from typing import Any, Dict, Optional


class SimpleCache:
    """Thread-safe in-memory cache with Time-To-Live (TTL) support."""

    def __init__(self, default_ttl: int = 600):
        """Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 600 = 10 minutes)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value if exists and not expired, None otherwise
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if time.time() > entry["expires_at"]:
            # Expired, remove from cache
            del self._cache[key]
            return None

        return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        if ttl is None:
            ttl = self._default_ttl

        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
            "created_at": time.time()
        }

    def delete(self, key: str) -> None:
        """Delete key from cache.

        Args:
            key: Cache key to delete
        """
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time > entry["expires_at"]
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache stats
        """
        current_time = time.time()
        active_entries = sum(
            1 for entry in self._cache.values()
            if current_time <= entry["expires_at"]
        )

        return {
            "total_entries": len(self._cache),
            "active_entries": active_entries,
            "expired_entries": len(self._cache) - active_entries
        }


# Global cache instance
_global_cache = SimpleCache(default_ttl=600)  # 10 minutes default


def get_cache() -> SimpleCache:
    """Get the global cache instance.

    Returns:
        Global SimpleCache instance
    """
    return _global_cache
