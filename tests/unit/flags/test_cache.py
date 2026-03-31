"""Tests for resolution cache and stats."""

from smplkit.flags.client import FlagStats, _ResolutionCache


class TestResolutionCache:
    def test_put_and_get(self):
        cache = _ResolutionCache()
        cache.put("key1", "value1")
        hit, value = cache.get("key1")
        assert hit is True
        assert value == "value1"

    def test_miss(self):
        cache = _ResolutionCache()
        hit, value = cache.get("nonexistent")
        assert hit is False
        assert value is None

    def test_hit_miss_counters(self):
        cache = _ResolutionCache()
        cache.put("k", "v")

        cache.get("k")  # hit
        cache.get("k")  # hit
        cache.get("missing")  # miss

        assert cache.cache_hits == 2
        assert cache.cache_misses == 1

    def test_clear(self):
        cache = _ResolutionCache()
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.clear()

        hit, _ = cache.get("k1")
        assert hit is False

    def test_lru_eviction(self):
        cache = _ResolutionCache(max_size=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("d", 4)  # evicts "a"

        hit_a, _ = cache.get("a")
        assert hit_a is False

        hit_b, _ = cache.get("b")
        assert hit_b is True

    def test_lru_access_refreshes(self):
        cache = _ResolutionCache(max_size=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.get("a")  # refreshes "a"
        cache.put("d", 4)  # evicts "b" (oldest untouched)

        hit_a, _ = cache.get("a")
        assert hit_a is True
        hit_b, _ = cache.get("b")
        assert hit_b is False

    def test_overwrite_existing(self):
        cache = _ResolutionCache()
        cache.put("k", "v1")
        cache.put("k", "v2")
        _, value = cache.get("k")
        assert value == "v2"


class TestFlagStats:
    def test_repr(self):
        stats = FlagStats(cache_hits=10, cache_misses=5)
        assert stats.cache_hits == 10
        assert stats.cache_misses == 5
        assert "10" in repr(stats)
