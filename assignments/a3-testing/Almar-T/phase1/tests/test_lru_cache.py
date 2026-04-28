"""Tests for the lru_cache module.

Organized clause by clause against the spec at
starter/assignment3/specs/lru_cache.md (C1-C7), with extra baseline
sanity checks and one hidden-edge hunt.
"""
import time

import pytest

from lru_cache import LRUCache


# ---------------------------------------------------------------------------
# Baseline sanity: the most basic operations must work before anything else
# is meaningful.
# ---------------------------------------------------------------------------

def test_basic_put_then_get_returns_value():
    cache = LRUCache(2)
    cache.put("a", 1)
    assert cache.get("a") == 1


def test_basic_len_with_items():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    assert len(cache) == 2


# ---------------------------------------------------------------------------
# C1. Capacity validation: positive integer required.
# ---------------------------------------------------------------------------

def test_c1_capacity_zero_raises():
    with pytest.raises(ValueError):
        LRUCache(0)


@pytest.mark.parametrize("bad_capacity", [-1, -5, -100])
def test_c1_capacity_negative_raises(bad_capacity):
    with pytest.raises(ValueError):
        LRUCache(bad_capacity)


def test_c1_capacity_one_works():
    cache = LRUCache(1)
    cache.put("a", 1)
    assert cache.get("a") == 1


# ---------------------------------------------------------------------------
# C2. put(key, value, ttl): TTL=None never expires; numeric TTL expires
# at time.monotonic() + ttl.
# ---------------------------------------------------------------------------

def test_c2_ttl_none_never_expires():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=None)
    time.sleep(0.05)
    assert cache.get("a") == 1


def test_c2_ttl_expires_after_sleep():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c2_ttl_default_argument_never_expires():
    # No ttl passed at all - default is None per signature.
    cache = LRUCache(2)
    cache.put("a", 1)
    time.sleep(0.05)
    assert cache.get("a") == 1


# ---------------------------------------------------------------------------
# C3. TTL replacement on re-put: re-put completely supersedes value, ttl,
# and expiration of the prior entry.
# ---------------------------------------------------------------------------

def test_c3_reput_replaces_value():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("a", 2)
    assert cache.get("a") == 2


def test_c3_reput_with_none_ttl_clears_prior_ttl():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    cache.put("a", 2, ttl=None)
    time.sleep(0.1)
    # Old ttl should be cleared; new entry has no expiration.
    assert cache.get("a") == 2


def test_c3_reput_resets_expiration_clock():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.08)
    time.sleep(0.05)
    # Re-put with a fresh, longer ttl. The original 0.08s ttl should
    # be entirely superseded by the new one.
    cache.put("a", 2, ttl=0.2)
    time.sleep(0.06)  # past the original 0.08s, well within new 0.2s
    assert cache.get("a") == 2


# ---------------------------------------------------------------------------
# C4. Capacity eviction: evict LRU BEFORE inserting new key when full;
# len stays at capacity afterwards.
# ---------------------------------------------------------------------------

def test_c4_eviction_when_full_drops_lru():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)  # cache full, "a" is LRU and gets evicted
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_c4_len_stays_at_capacity_after_eviction():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)
    assert len(cache) == 3


def test_c4_reput_existing_does_not_evict():
    # Re-put on an already-present key is NOT an insertion of a new key,
    # so it should not trigger eviction even when len == capacity.
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)  # re-put existing; nothing should be evicted
    assert cache.get("a") == 99
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert len(cache) == 3


# ---------------------------------------------------------------------------
# C5. Use tracking: get and put-on-existing both promote to MRU.
# Inserting a new key does not reorder existing keys.
# ---------------------------------------------------------------------------

def test_c5_get_promotes_to_mru():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")  # promote "a"
    cache.put("d", 4)  # now "b" is LRU and should be evicted
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("a") == 1


def test_c5_put_on_existing_promotes_to_mru():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)  # re-put on existing should count as use
    cache.put("d", 4)  # "b" should be LRU now, get evicted
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("a") == 99


def test_c5_put_new_key_does_not_reorder_existing():
    # Inserting a new key fills the cache, but the relative ordering
    # of the surviving keys must be preserved.
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)  # "a" evicted; remaining order: b (oldest), c, d
    cache.put("e", 5)  # "b" should now be LRU and evicted
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("c") == 3
    assert cache.get("d") == 4
    assert cache.get("e") == 5


# ---------------------------------------------------------------------------
# C6. get(): missing key raises KeyError; expired entry raises KeyError
# AND is removed from the cache.
# ---------------------------------------------------------------------------

def test_c6_get_missing_key_raises_keyerror():
    cache = LRUCache(2)
    with pytest.raises(KeyError):
        cache.get("nope")


def test_c6_get_expired_entry_raises_keyerror():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c6_get_expired_entry_removes_it():
    # After get raises on expired, the entry should be gone - inserting
    # a new key under the same name should be a fresh insertion.
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")
    cache.put("a", 99)
    assert cache.get("a") == 99


# ---------------------------------------------------------------------------
# C7. len() counts only non-expired entries, even before they have been
# accessed since their expiration.
# ---------------------------------------------------------------------------

def test_c7_len_excludes_expired_without_access():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2)  # never expires
    time.sleep(0.1)
    # "a" has expired but has not been accessed since. It must not
    # be counted in len().
    assert len(cache) == 1


# ---------------------------------------------------------------------------
# Hidden-edge hunt: expired entries must not occupy capacity for the
# purposes of new insertions. C7 says they aren't counted by len(); C4
# evicts only when len == capacity. Implication: a cache full of
# expired entries should accept new inserts without evicting anything.
# ---------------------------------------------------------------------------

def test_hidden_expired_entries_do_not_occupy_capacity():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2, ttl=0.05)
    time.sleep(0.1)
    # Both expired; len should be 0 per C7.
    assert len(cache) == 0
    # Inserting two new keys should succeed without evicting them as
    # though they were live.
    cache.put("c", 3)
    cache.put("d", 4)
    assert cache.get("c") == 3
    assert cache.get("d") == 4
    assert len(cache) == 2
