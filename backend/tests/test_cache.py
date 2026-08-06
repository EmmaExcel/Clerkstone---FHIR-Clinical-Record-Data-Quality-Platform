from __future__ import annotations

from app.domain.terminology.cache import CachedTerminologyClient, TTLCache


class _CountingClient:
    def __init__(self) -> None:
        self.calls = 0

    def resolve(self, system: str, code: str):
        self.calls += 1
        if code == "missing":
            return None
        return {"display": "Hypertension", "active": True}


def test_cache_hits_and_negative_caching():
    inner = _CountingClient()
    client = CachedTerminologyClient(inner, ttl_seconds=60)

    first = client.resolve("http://snomed.info/sct", "38341003")
    second = client.resolve("http://snomed.info/sct", "38341003")
    assert first == {"display": "Hypertension", "active": True}
    assert second == first
    assert inner.calls == 1  # second call served from cache

    # Negative results are cached too.
    assert client.resolve("http://snomed.info/sct", "missing") is None
    assert client.resolve("http://snomed.info/sct", "missing") is None
    assert inner.calls == 2  # only one additional upstream call for the miss


def test_ttl_expiry_refetches():
    inner = _CountingClient()
    client = CachedTerminologyClient(inner, ttl_seconds=0)  # expires immediately
    client.resolve("s", "c")
    client.resolve("s", "c")
    assert inner.calls == 2


def test_ttl_cache_get_put_roundtrip():
    cache = TTLCache(ttl_seconds=60)
    assert cache.get(("s", "c")) == (False, None)
    cache.put(("s", "c"), {"display": "X"})
    assert cache.get(("s", "c")) == (True, {"display": "X"})
