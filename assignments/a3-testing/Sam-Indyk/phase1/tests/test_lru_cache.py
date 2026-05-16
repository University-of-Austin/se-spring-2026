"""Tests for lru_cache, organized clause-by-clause against the spec."""
import time

import pytest

from lru_cache import LRUCache


# -------------------- C1: Capacity validation --------------------

def test_c1_capacity_zero_raises():
    with pytest.raises(ValueError):
        LRUCache(0)


def test_c1_capacity_negative_raises():
    with pytest.raises(ValueError):
        LRUCache(-5)


def test_c1_capacity_one_is_allowed():
    cache = LRUCache(1)
    cache.put("a", 1)
    assert cache.get("a") == 1


def test_c1_large_capacity_allowed():
    cache = LRUCache(1000)
    for i in range(500):
        cache.put(i, i * 2)
    assert len(cache) == 500
    assert cache.get(0) == 0
    assert cache.get(499) == 998


# -------------------- C2: put / get round trip & TTL acceptance --------------------

def test_c2_put_then_get_returns_value():
    cache = LRUCache(3)
    cache.put("a", 1)
    assert cache.get("a") == 1


def test_c2_put_overwrites_value():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("a", 2)
    assert cache.get("a") == 2


def test_c2_ttl_none_never_expires():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=None)
    time.sleep(0.05)
    assert cache.get("a") == 1


def test_c2_ttl_default_is_none():
    cache = LRUCache(3)
    cache.put("a", 1)  # no ttl arg
    time.sleep(0.05)
    assert cache.get("a") == 1


def test_c2_ttl_float_accepted():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.5)
    assert cache.get("a") == 1


def test_c2_ttl_int_accepted():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=1)
    assert cache.get("a") == 1


def test_c2_value_can_be_any_object():
    cache = LRUCache(3)
    sentinel = object()
    cache.put("a", sentinel)
    cache.put("b", None)
    cache.put("c", [1, 2, 3])
    assert cache.get("a") is sentinel
    assert cache.get("b") is None
    assert cache.get("c") == [1, 2, 3]


def test_c2_keys_can_be_any_hashable():
    cache = LRUCache(3)
    cache.put(1, "int")
    cache.put((1, 2), "tuple")
    cache.put("s", "string")
    assert cache.get(1) == "int"
    assert cache.get((1, 2)) == "tuple"
    assert cache.get("s") == "string"


# -------------------- C3: TTL replacement on re-put --------------------

def test_c3_reput_with_none_clears_prior_ttl():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("a", 2, ttl=None)
    time.sleep(0.10)
    # Prior TTL should be cleared; entry must still be retrievable.
    assert cache.get("a") == 2


def test_c3_reput_with_no_ttl_arg_clears_prior_ttl():
    # Default ttl arg is None per the signature, so an explicit-default
    # re-put clears prior TTL the same way ttl=None does.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("a", 2)
    time.sleep(0.10)
    assert cache.get("a") == 2


def test_c3_reput_replaces_value_and_extends_ttl():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.02)
    cache.put("a", 2, ttl=1.0)  # supersede expiration
    time.sleep(0.10)  # original would have expired by now
    assert cache.get("a") == 2


def test_c3_reput_with_shorter_ttl_supersedes_longer():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=10.0)
    cache.put("a", 2, ttl=0.05)
    time.sleep(0.10)
    with pytest.raises(KeyError):
        cache.get("a")


# -------------------- C4: Capacity eviction --------------------

def test_c4_evicts_lru_when_full():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)  # evicts "a", the LRU
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_c4_len_stays_at_capacity_after_evict():
    cache = LRUCache(3)
    for k in ["a", "b", "c", "d", "e"]:
        cache.put(k, 0)
    assert len(cache) == 3


def test_c4_eviction_happens_before_insert_not_after():
    # If eviction happened AFTER insert, the new key could itself be
    # evicted on a capacity=1 cache. Spec says evict-then-insert.
    cache = LRUCache(1)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("b") == 2
    with pytest.raises(KeyError):
        cache.get("a")


def test_c4_overwrite_does_not_evict():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)  # not a new key — no eviction
    assert cache.get("a") == 99
    assert cache.get("b") == 2
    assert cache.get("c") == 3


# -------------------- C5: Use tracking (LRU ordering) --------------------

def test_c5_get_promotes_key_to_mru():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")  # promote "a"
    cache.put("d", 4)  # should now evict "b", not "a"
    assert cache.get("a") == 1
    with pytest.raises(KeyError):
        cache.get("b")


def test_c5_put_on_existing_promotes_to_mru():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)  # promote "a" via re-put
    cache.put("d", 4)  # evicts "b"
    assert cache.get("a") == 99
    with pytest.raises(KeyError):
        cache.get("b")


def test_c5_new_insert_does_not_reorder_others():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    # New key "d" must evict "a" (LRU) — order of b, c is preserved.
    cache.put("d", 4)
    with pytest.raises(KeyError):
        cache.get("a")
    # Now LRU is "b". Add "e" → "b" should evict.
    cache.put("e", 5)
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("c") == 3


def test_c5_oldest_after_get_is_correctly_tracked():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("b")  # order is now a (LRU), c, b (MRU)
    cache.get("a")  # order is now c (LRU), b, a (MRU)
    cache.put("d", 4)  # evicts "c"
    with pytest.raises(KeyError):
        cache.get("c")
    assert cache.get("a") == 1
    assert cache.get("b") == 2


# -------------------- C6: Expiration on get --------------------

def test_c6_get_missing_key_raises_keyerror():
    cache = LRUCache(3)
    with pytest.raises(KeyError):
        cache.get("missing")


def test_c6_get_expired_raises_keyerror():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.10)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c6_expired_get_removes_entry():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.10)
    with pytest.raises(KeyError):
        cache.get("a")
    # After expired-get removed it, cache slot is freed:
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)  # would evict an existing entry only if "a" still counted
    # We can confirm "a" is gone by verifying we can re-put "a" without evicting
    # any of the three live entries from a NEW cache scenario:
    cache2 = LRUCache(3)
    cache2.put("x", 1, ttl=0.05)
    time.sleep(0.10)
    with pytest.raises(KeyError):
        cache2.get("x")
    cache2.put("y", 2)
    cache2.put("z", 3)
    cache2.put("w", 4)  # if "x" were still there, this would evict "y"
    assert cache2.get("y") == 2


# -------------------- C7: __len__ excludes expired entries --------------------

def test_c7_len_excludes_expired_without_access():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2)
    time.sleep(0.10)
    # "a" is expired but has not been accessed since expiring.
    assert len(cache) == 1


def test_c7_len_initially_zero():
    cache = LRUCache(3)
    assert len(cache) == 0


def test_c7_len_counts_unexpired_entries():
    cache = LRUCache(5)
    cache.put("a", 1)
    cache.put("b", 2, ttl=10)
    cache.put("c", 3)
    assert len(cache) == 3


def test_c7_len_after_eviction_equals_capacity():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)
    assert len(cache) == 2


def test_c7_len_with_all_entries_expired():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2, ttl=0.05)
    cache.put("c", 3, ttl=0.05)
    time.sleep(0.10)
    assert len(cache) == 0


# -------------------- Mixed / cross-clause edges --------------------

def test_expired_does_not_block_capacity_for_new_inserts():
    # If an entry is expired, the cache should not behave as if it's still
    # occupying a slot when something else is inserted.
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2)
    time.sleep(0.10)
    # "a" is expired. len should reflect this.
    assert len(cache) == 1
    cache.put("c", 3)
    # "b" should still be alive — "a"'s expiration freed its slot.
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_get_does_not_resurrect_expired_entry():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.10)
    with pytest.raises(KeyError):
        cache.get("a")
    # A second get must also raise — expired entry must not linger.
    with pytest.raises(KeyError):
        cache.get("a")
