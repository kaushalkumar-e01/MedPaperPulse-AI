"""In-memory caching layer with TTL support."""

import time
from typing import Any, Optional, Dict


class MemoryCache:
    def __init__(self, default_ttl_seconds: int = 3600):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if not entry:
            return None
        if time.time() > entry["expires_at"]:
            del self._store[key]
            return None
        return entry["data"]

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        self._store[key] = {
            "data": value,
            "expires_at": time.time() + ttl,
        }

    def clear(self) -> None:
        self._store.clear()


cache = MemoryCache()
