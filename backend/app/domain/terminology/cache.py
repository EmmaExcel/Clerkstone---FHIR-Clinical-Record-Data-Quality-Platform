"""In-process TTL cache for terminology resolution.

The NHS England adapter makes network calls; caching (including negative
results) keeps repeated lookups cheap and bounds latency on a slow or
rate-limited terminology service. The local subset client already keeps its
index in memory and does not need this wrapper.
"""

from __future__ import annotations

import time
from typing import Any

from app.domain.quality.rules.base import TerminologyClient


class TTLCache:
    """A tiny dict-backed cache with per-entry expiry."""

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._store: dict[tuple[str, str], tuple[float, Any]] = {}

    def get(self, key: tuple[str, str]) -> tuple[bool, Any]:
        entry = self._store.get(key)
        if entry is None:
            return False, None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            del self._store[key]
            return False, None
        return True, value

    def put(self, key: tuple[str, str], value: Any) -> None:
        self._store[key] = (time.monotonic() + self._ttl, value)


class CachedTerminologyClient:
    """Wraps a ``TerminologyClient`` with a TTL cache (negative results included)."""

    def __init__(self, inner: TerminologyClient, ttl_seconds: float) -> None:
        self._inner = inner
        self._cache = TTLCache(ttl_seconds)

    def resolve(self, system: str, code: str) -> dict[str, Any] | None:
        key = (system, code)
        hit, value = self._cache.get(key)
        if hit:
            return value
        value = self._inner.resolve(system, code)
        self._cache.put(key, value)
        return value
