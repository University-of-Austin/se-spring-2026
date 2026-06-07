"""Tests for lru_cache.LRUCache.

Organized clause-by-clause from the spec:
  C1: capacity is fixed; cache holds at most `capacity` non-expired entries.
  C2: put(key, value, ttl=None) inserts an entry; ttl is optional.
  C3: get(key) returns the value, raises KeyError on missing or expired.
  C4: __len__ counts non-expired entries only.
  C5: get touches an entry (promotes to MRU).
  C6: put on an existing key touches that entry (promotes to MRU).
  C7: When full, the least-recently-used entry is evicted on put.
  C8: TTL: a put with ttl=N causes the entry to expire N seconds later.
  C9: Re-putting a key replaces the entry (and its TTL).
"""

import time
import pytest
from lru_cache import LRUCache


# -- C1: capacity ------------------------------------------------------------

@pytest.mark.parametrize("bad_capacity", [0, -1, -100])
def test_c1_non_positive_capacity_raises_valueerror(bad_capacity):
    with pytest.raises(ValueError):
        LRUCache(capacity=bad_capacity)


def test_c1_capacity_one_holds_single_entry():
    cache = LRUCache(capacity=1)
    cache.put("a", 1)
    assert cache.get("a") == 1
    assert len(cache) == 1


def test_c1_capacity_three_holds_three_distinct_keys():
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert len(cache) == 3
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("c") == 3


# -- C2: put inserts ---------------------------------------------------------

def test_c2_put_then_get_returns_value():
    cache = LRUCache(capacity=2)
    cache.put("k", "v")
    assert cache.get("k") == "v"


def test_c2_put_value_can_be_any_type():
    cache = LRUCache(capacity=3)
    cache.put("int", 42)
    cache.put("list", [1, 2, 3])
    cache.put("none", None)
    assert cache.get("int") == 42
    assert cache.get("list") == [1, 2, 3]
    assert cache.get("none") is None


# -- C3: get raises KeyError on missing --------------------------------------

def test_c3_get_missing_key_raises_keyerror():
    cache = LRUCache(capacity=2)
    with pytest.raises(KeyError):
        cache.get("missing")


def test_c3_get_after_eviction_raises_keyerror():
    cache = LRUCache(capacity=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)  # evicts "a"
    with pytest.raises(KeyError):
        cache.get("a")


def test_c3_get_on_empty_cache_raises_keyerror():
    cache = LRUCache(capacity=5)
    with pytest.raises(KeyError):
        cache.get("anything")


# -- C4: __len__ ------------------------------------------------------------

def test_c4_len_empty_is_zero():
    cache = LRUCache(capacity=5)
    assert len(cache) == 0


def test_c4_len_increases_with_puts():
    cache = LRUCache(capacity=5)
    assert len(cache) == 0
    cache.put("a", 1)
    assert len(cache) == 1
    cache.put("b", 2)
    assert len(cache) == 2


def test_c4_len_capped_at_capacity():
    cache = LRUCache(capacity=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert len(cache) == 2


def test_c4_len_unchanged_when_overwriting_existing_key():
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("a", 2)
    assert len(cache) == 1


# -- C5: get promotes to MRU -------------------------------------------------

def test_c5_get_promotes_to_mru():
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")          # promote "a" to MRU; LRU is now "b"
    cache.put("d", 4)       # should evict "b", not "a"
    assert cache.get("a") == 1
    with pytest.raises(KeyError):
        cache.get("b")


def test_c5_repeated_get_keeps_entry_alive():
    """Repeatedly getting 'a' must keep it MRU; an eviction should take 'b'."""
    cache = LRUCache(capacity=2)
    cache.put("a", 1)
    cache.put("b", 2)
    for _ in range(5):
        cache.get("a")          # touch "a" five times in a row
    cache.put("c", 3)           # cache is full; LRU is "b"
    assert cache.get("a") == 1
    with pytest.raises(KeyError):
        cache.get("b")


# -- C6: put on existing key touches -----------------------------------------

def test_c6_put_on_existing_key_promotes_to_mru():
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)      # touch "a"; LRU is now "b"
    cache.put("d", 4)       # should evict "b"
    assert cache.get("a") == 99
    with pytest.raises(KeyError):
        cache.get("b")


# -- C7: eviction when full --------------------------------------------------

def test_c7_eviction_evicts_least_recently_used():
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)       # "a" is LRU and should be evicted
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_c7_spec_example_exact():
    """Reproduces the example from the spec verbatim."""
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert cache.get("a") == 1
    cache.put("d", 4)
    with pytest.raises(KeyError):
        cache.get("b")
    assert len(cache) == 3


def test_c7_multiple_evictions_in_sequence():
    cache = LRUCache(capacity=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)       # evicts "a"
    cache.put("d", 4)       # evicts "b"
    with pytest.raises(KeyError):
        cache.get("a")
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("c") == 3
    assert cache.get("d") == 4


# -- C8: TTL expiration ------------------------------------------------------

def test_c8_get_after_ttl_expires_raises_keyerror():
    cache = LRUCache(capacity=3)
    cache.put("x", 99, ttl=0.03)
    time.sleep(0.08)
    with pytest.raises(KeyError):
        cache.get("x")


def test_c8_get_before_ttl_expires_returns_value():
    cache = LRUCache(capacity=3)
    cache.put("x", 99, ttl=1.0)
    assert cache.get("x") == 99


def test_c8_no_ttl_means_no_expiration():
    cache = LRUCache(capacity=3)
    cache.put("x", 99)        # no ttl
    time.sleep(0.1)
    assert cache.get("x") == 99


def test_c8_none_ttl_means_no_expiration():
    cache = LRUCache(capacity=3)
    cache.put("x", 99, ttl=None)
    time.sleep(0.1)
    assert cache.get("x") == 99


def test_c8_spec_example_exact():
    """Reproduces the TTL example from the spec."""
    cache = LRUCache(capacity=3)
    cache.put("x", 99, ttl=0.5)
    time.sleep(1.0)
    with pytest.raises(KeyError):
        cache.get("x")


# -- C4 + C8: len excludes expired entries -----------------------------------

def test_c4_len_excludes_expired_entries():
    cache = LRUCache(capacity=5)
    cache.put("a", 1)
    cache.put("b", 2, ttl=0.03)
    time.sleep(0.08)
    assert len(cache) == 1


def test_c4_len_excludes_expired_even_without_get():
    """Spec note: len() must reflect expiry without anyone touching the key."""
    cache = LRUCache(capacity=5)
    cache.put("a", 1, ttl=0.03)
    cache.put("b", 2, ttl=0.03)
    time.sleep(0.08)
    assert len(cache) == 0


def test_c4_len_mixed_ttl_and_no_ttl():
    cache = LRUCache(capacity=5)
    cache.put("perm", 1)
    cache.put("temp", 2, ttl=0.03)
    assert len(cache) == 2
    time.sleep(0.08)
    assert len(cache) == 1


# -- C9: re-put replaces entry and its TTL ----------------------------------

def test_c9_reput_replaces_value():
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("a", 2)
    assert cache.get("a") == 2


def test_c9_reput_without_ttl_clears_previous_ttl():
    """If you re-put a key with no ttl, the previous TTL must not still apply."""
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=0.03)
    cache.put("a", 2)         # no ttl on the re-put
    time.sleep(0.08)
    assert cache.get("a") == 2


def test_c9_reput_with_new_ttl_uses_new_ttl():
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=0.03)
    cache.put("a", 2, ttl=1.0)  # extend
    time.sleep(0.08)
    assert cache.get("a") == 2


def test_c9_reput_shortens_ttl():
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=10.0)
    cache.put("a", 2, ttl=0.03)
    time.sleep(0.08)
    with pytest.raises(KeyError):
        cache.get("a")


# -- Edge: expired entry should not be returned even if not yet evicted ------

def test_expired_then_get_raises_not_returns():
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=0.03)
    time.sleep(0.08)
    with pytest.raises(KeyError):
        cache.get("a")


def test_expired_entry_does_not_count_toward_capacity():
    """If 'a' has expired, putting two new entries shouldn't evict a non-expired one."""
    cache = LRUCache(capacity=2)
    cache.put("a", 1, ttl=0.03)
    cache.put("b", 2)
    time.sleep(0.08)
    # "a" expired; cache effectively holds 1 entry.
    cache.put("c", 3)
    assert cache.get("b") == 2
    assert cache.get("c") == 3


# -- LRU ordering interaction with TTL --------------------------------------

def test_c6_get_on_expired_removes_entry():
    """Spec C6: get on expired raises KeyError AND removes the entry."""
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=0.03)
    cache.put("b", 2)
    time.sleep(0.08)
    assert len(cache) == 1  # b only
    with pytest.raises(KeyError):
        cache.get("a")
    # After the failed get, "a" must still be gone (and len still 1).
    assert len(cache) == 1


def test_c5_inserting_new_key_does_not_reorder_others():
    """Spec C5: inserting a new key does not affect the LRU order of others."""
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("b", 2)
    # Now add a third key. "a" was the LRU before; it must stay LRU.
    cache.put("c", 3)
    cache.put("d", 4)   # should evict "a" (still LRU)
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_c2_ttl_int_works():
    """Spec C2: ttl can be int or float."""
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=1)        # int ttl
    assert cache.get("a") == 1


def test_get_on_expired_key_does_not_promote():
    """If a get raises KeyError due to expiry, eviction order should still
    treat that slot as gone, not as freshly-touched."""
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("b", 2, ttl=0.03)
    cache.put("c", 3)
    time.sleep(0.08)
    with pytest.raises(KeyError):
        cache.get("b")
    # adding a fourth entry should not evict "a" or "c"
    cache.put("d", 4)
    assert cache.get("a") == 1
    assert cache.get("c") == 3
    assert cache.get("d") == 4
