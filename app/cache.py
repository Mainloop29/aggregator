import time
from typing import Any

from app.config import settings


class TTLCache:
    def __init__(self, ttl: int = 30) -> None:
        self.ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.monotonic() + self.ttl, value)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)


seats_cache = TTLCache(ttl=settings.seats_cache_ttl)
