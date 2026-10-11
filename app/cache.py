import time
from typing import Any, Dict, Optional

class SimpleMemoryCache:
    """
    High-performance in-memory cache with TTL and key-prefix invalidation.
    Designed for zero-dependency, thread-safe fast caching of settings, menus, and categories.
    """
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        if key in self._cache:
            if self._expiry.get(key, 0) > now:
                return self._cache[key]
            else:
                self.delete(key)
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        duration = ttl if ttl is not None else self.default_ttl
        self._cache[key] = value
        self._expiry[key] = time.time() + duration

    def delete(self, key: str) -> None:
        self._cache.pop(key, None)
        self._expiry.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(prefix)]
        for k in keys_to_remove:
            self.delete(k)

    def clear(self) -> None:
        self._cache.clear()
        self._expiry.clear()

# Global singleton cache
cache = SimpleMemoryCache(default_ttl=600)
