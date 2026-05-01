"""Tests for lru_cache.LRUCache, organized clause-by-clause against
starter/assignment3/specs/lru_cache.md."""
import time

import pytest

from lru_cache import LRUCache


# ---------------------------------------------------------------------------
# C1. Capacity validation
# ---------------------------------------------------------------------------

def test_c1_capacity_zero_raises_value_error():
    with pytest.raises(ValueError):
        LRUCache(0)


def test_c1_capacity_negative_raises_value_error():
    with pytest.raises(ValueError):
        LRUCache(-5)


def test_c1_capacity_one_is_valid():
    cache = LRUCache(1)
    cache.put("a", 1)
    assert cache.get("a") == 1


# ---------------------------------------------------------------------------
# C2. put inserts/replaces; ttl=None means never expires; numeric ttl expires
# ---------------------------------------------------------------------------

def test_c2_put_then_get_returns_value():
    cache = LRUCache(2)
    cache.put("a", 1)
    assert cache.get("a") == 1


def test_c2_put_replaces_value_for_existing_key():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("a", 99)
    assert cache.get("a") == 99


def test_c2_ttl_none_never_expires():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=None)
    time.sleep(0.10)
    # explicit None — entry should still be present
    assert cache.get("a") == 1


def test_c2_default_ttl_argument_means_no_expiry():
    # ttl defaults to None per signature — same behavior as explicit None
    cache = LRUCache(2)
    cache.put("a", 1)
    time.sleep(0.10)
    assert cache.get("a") == 1


def test_c2_numeric_ttl_expires_entry():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.15)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c2_int_ttl_accepted():
    # ttl: float | None — the spec says int or float
    cache = LRUCache(2)
    cache.put("a", 1, ttl=1)
    # well within ttl
    assert cache.get("a") == 1


# ---------------------------------------------------------------------------
# C3. TTL replacement on re-put
# ---------------------------------------------------------------------------

def test_c3_reput_replaces_value():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=10)
    cache.put("a", 2, ttl=10)
    assert cache.get("a") == 2


def test_c3_reput_with_none_clears_prior_ttl():
    """Spec: 're-put on a previously-TTL'd key clears the expiration.'"""
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    # immediately re-put with no ttl — old expiration must be discarded
    cache.put("a", 99, ttl=None)
    time.sleep(0.15)
    assert cache.get("a") == 99


def test_c3_reput_with_new_ttl_supersedes_old():
    """A short-then-long re-put must honor the longer ttl."""
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    cache.put("a", 2, ttl=2.0)
    time.sleep(0.15)
    # old ttl=0.05 would have expired; new ttl=2.0 keeps it alive
    assert cache.get("a") == 2


def test_c3_reput_with_shorter_ttl_supersedes_old():
    """A long-then-short re-put must honor the shorter ttl, not the older one."""
    cache = LRUCache(2)
    cache.put("a", 1, ttl=10)
    cache.put("a", 2, ttl=0.05)
    time.sleep(0.15)
    with pytest.raises(KeyError):
        cache.get("a")


# ---------------------------------------------------------------------------
# C4. Capacity eviction
# ---------------------------------------------------------------------------

def test_c4_eviction_when_inserting_new_key_into_full_cache():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)  # evicts "a" (least-recently-used)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c4_size_remains_capacity_after_eviction():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)
    assert len(cache) == 3


def test_c4_new_key_present_after_eviction():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    # eviction happens BEFORE the insert, so "c" must fit and be retrievable
    assert cache.get("c") == 3


def test_c4_reput_on_existing_key_does_not_evict():
    """Re-put is not 'a new key', so no eviction is required."""
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 99)  # not new — no one should be evicted
    assert cache.get("a") == 99
    assert cache.get("b") == 2


# ---------------------------------------------------------------------------
# C5. Use tracking (get and put-on-existing both promote to MRU)
# ---------------------------------------------------------------------------

def test_c5_get_promotes_key_to_mru():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")          # "a" is now MRU; "b" is now LRU
    cache.put("d", 4)       # should evict "b", not "a"
    assert cache.get("a") == 1
    with pytest.raises(KeyError):
        cache.get("b")


def test_c5_reput_on_existing_promotes_key_to_mru():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)      # touching "a" promotes it; "b" is now LRU
    cache.put("d", 4)
    assert cache.get("a") == 99
    with pytest.raises(KeyError):
        cache.get("b")


def test_c5_inserting_new_key_does_not_reorder_others():
    """C5: 'Inserting a new key does not affect the order of other keys.'"""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    # When we add "d" the cache is full; "a" (oldest) should be evicted.
    cache.put("d", 4)
    with pytest.raises(KeyError):
        cache.get("a")
    # "b" and "c" should still be present and in their original relative order
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_c5_relative_order_of_survivors_preserved_after_eviction():
    """After a new-key insert evicts the LRU, the remaining keys must keep
    their relative LRU/MRU order so the *next* eviction picks the correct
    next-oldest key. Catches a bug where new-key insert subtly reorders the
    survivors."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)            # evicts "a"; order should be b(LRU), c, d(MRU)
    cache.put("e", 5)            # should evict "b" next
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("c") == 3
    assert cache.get("d") == 4
    assert cache.get("e") == 5


def test_c5_lru_after_long_access_pattern():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")          # order: b, c, a
    cache.get("b")          # order: c, b, a
    cache.put("d", 4)       # evict "c"
    with pytest.raises(KeyError):
        cache.get("c")
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("d") == 4


# ---------------------------------------------------------------------------
# C6. get behavior on missing/expired
# ---------------------------------------------------------------------------

def test_c6_get_missing_raises_key_error():
    cache = LRUCache(2)
    with pytest.raises(KeyError):
        cache.get("nope")


def test_c6_get_expired_raises_key_error():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.15)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c6_expired_get_removes_entry():
    """Spec: 'get(key) on an expired entry raises KeyError and removes the
    entry from the cache.' After the failed get, the slot should be free and
    not counted by len."""
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2)
    time.sleep(0.15)
    with pytest.raises(KeyError):
        cache.get("a")
    # "a" was removed by the failed get
    assert len(cache) == 1
    # the freed slot is reusable: adding a new key shouldn't evict "b"
    cache.put("c", 3)
    assert cache.get("b") == 2
    assert cache.get("c") == 3


# ---------------------------------------------------------------------------
# C7. len() counts non-expired entries only
# ---------------------------------------------------------------------------

def test_c7_len_zero_initially():
    cache = LRUCache(3)
    assert len(cache) == 0


def test_c7_len_grows_with_puts():
    cache = LRUCache(3)
    cache.put("a", 1)
    assert len(cache) == 1
    cache.put("b", 2)
    assert len(cache) == 2


def test_c7_len_does_not_count_expired_unaccessed_entries():
    """Spec: 'Entries whose TTL has passed are not counted, even if they have
    not yet been accessed since expiring.'"""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2)
    cache.put("c", 3)
    time.sleep(0.15)
    # "a" expired but never accessed; len must not count it
    assert len(cache) == 2


def test_c7_len_counts_non_expired_ttl_entries_normally():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=10)
    cache.put("b", 2)
    assert len(cache) == 2


def test_c7_reput_after_expiry_then_len_counts_new_entry():
    """Sanity: a re-put after expiry should count as a fresh entry."""
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.15)
    # at this point "a" is expired and uncounted by len
    cache.put("a", 2)
    assert len(cache) == 1
    assert cache.get("a") == 2
