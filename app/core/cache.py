"""
Cache utility with Redis backend and in-process TTL fallback.
"""
from __future__ import annotations
import time
import threading
from typing import Any, Callable, Dict, Tuple
import json

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore

from .config import settings

class BaseCache:
    def get(self, key: str) -> Any:  # pragma: no cover - interface
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def get_or_set(self, key: str, ttl_seconds: int, loader: Callable[[], Any]) -> Any:
        val = self.get(key)
        if val is not None:
            return val
        result = loader()
        if result is not None:
            self.set(key, result, ttl_seconds)
        return result


class TTLCache(BaseCache):
    def __init__(self):
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            expire_at, value = item
            if expire_at and expire_at < now:
                # expired
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        expire_at = time.time() + max(1, int(ttl_seconds))
        with self._lock:
            self._store[key] = (expire_at, value)


class RedisCache(BaseCache):
    def __init__(self, url: str):
        assert redis is not None, "redis library not available"
        # decode_responses=True to store strings; we'll json serialize values
        self._r = redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> Any:
        try:
            s = self._r.get(key)
            if s is None:
                return None
            return json.loads(s)
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        try:
            s = json.dumps(value, default=str)
            self._r.setex(key, int(max(1, ttl_seconds)), s)
        except Exception:
            # best-effort; ignore
            pass


def _create_cache() -> BaseCache:
    # Decide backend based on settings
    backend = str(getattr(settings, 'CACHE_BACKEND', 'memory') or 'memory').lower()
    redis_url = getattr(settings, 'REDIS_URL', None)
    if backend == "redis" and redis_url and redis is not None:
        try:
            c = RedisCache(redis_url)
            # health check
            c.set("__cache_probe__", {"ok": True}, 5)
            return c
        except Exception:
            pass
    # Fallback
    return TTLCache()


# Global cache instance
cache: BaseCache = _create_cache()
