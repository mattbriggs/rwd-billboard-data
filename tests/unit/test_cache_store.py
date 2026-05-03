"""Unit tests for filesystem caching."""

from __future__ import annotations

from pathlib import Path

from study_system.infrastructure.persistence.cache_store import JsonCacheStore


def test_cache_store_round_trip(tmp_path: Path) -> None:
    cache = JsonCacheStore(tmp_path)
    cache.set("https://example.test", {"value": 1})
    assert cache.get("https://example.test") == {"value": 1}
    assert cache.get("missing") is None
