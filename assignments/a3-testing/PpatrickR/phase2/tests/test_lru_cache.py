"""Tests for lru_cache, organized by spec clause (C1..C7).

Spec: starter/assignment3/specs/lru_cache.md
"""
import time

import pytest

from lru_cache import LRUCache


SHORT_TTL = 0.05
WAIT_PAST = 0.12


# =========================================================================
# C1. Capacity validation
# =========================================================================

def test_c1_capacity_positive_one_is_allowed():
    cache = LRUCache(capacity=1)
    assert len(cache) == 0


def test_c1_capacity_large_positive_is_allowed():
    cache = LRUCache(capacity=1000)
    assert len(cache) == 0


@pytest.mark.parametrize("bad_capacity", [0, -1, -5, -100])
def test_c1_capacity_zero_or_negative_raises(bad_capacity):
    with pytest.raises(ValueError):
        LRUCache(capacity=bad_capacity)


# =========================================================================
# C2. put / get basics, TTL=None means no expiration
# =========================================================================

def test_c2_put_then_get_returns_value():
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    assert cache.get("a") == 1


def test_c2_put_replaces_existing_value():
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("a", 2)
    assert cache.get("a") == 2


def test_c2_ttl_none_does_not_expire():
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=None)
    time.sleep(WAIT_PAST)
    assert cache.get("a") == 1


def test_c2_ttl_default_is_none():
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    time.sleep(WAIT_PAST)
    assert cache.get("a") == 1


def test_c2_ttl_numeric_expires_after_duration():
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=SHORT_TTL)
    assert cache.get("a") == 1
    time.sleep(WAIT_PAST)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c2_ttl_int_value_works():
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=1)
    assert cache.get("a") == 1


def test_c2_value_may_be_none():
    cache = LRUCache(capacity=2)
    cache.put("a", None)
    assert cache.get("a") is None


def test_c2_value_may_be_arbitrary_object():
    cache = LRUCache(capacity=2)
    obj = {"nested": [1, 2, 3]}
    cache.put("a", obj)
    assert cache.get("a") is obj


# =========================================================================
# C3. TTL replacement on re-put
# =========================================================================

def test_c3_reput_with_none_ttl_clears_expiration():
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=SHORT_TTL)
    cache.put("a", 2, ttl=None)
    time.sleep(WAIT_PAST)
    assert cache.get("a") == 2


def test_c3_reput_default_ttl_clears_expiration():
    """put(key, value) with no ttl arg should clear a previously set TTL."""
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=SHORT_TTL)
    cache.put("a", 2)
    time.sleep(WAIT_PAST)
    assert cache.get("a") == 2


def test_c3_reput_replaces_value():
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=10)
    cache.put("a", 99, ttl=10)
    assert cache.get("a") == 99


def test_c3_reput_extends_ttl_window():
    """A fresh ttl on re-put supersedes the previous expiration time."""
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=SHORT_TTL)
    time.sleep(SHORT_TTL / 2)
    cache.put("a", 2, ttl=SHORT_TTL * 4)
    time.sleep(WAIT_PAST)
    assert cache.get("a") == 2


def test_c3_reput_shortens_ttl_window():
    """A shorter ttl on re-put supersedes the original longer ttl."""
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=10)
    cache.put("a", 2, ttl=SHORT_TTL)
    time.sleep(WAIT_PAST)
    with pytest.raises(KeyError):
        cache.get("a")


# =========================================================================
# C4. Capacity eviction
# =========================================================================

def test_c4_eviction_when_full_drops_lru():
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)  # evicts "a" (oldest)
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_c4_len_stays_at_capacity_after_eviction():
    cache = LRUCache(capacity=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert len(cache) == 2


def test_c4_reput_existing_key_when_full_does_not_evict():
    """Re-putting an existing key is not an insert and must not evict anything."""
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)  # already present — replace, not insert
    assert cache.get("a") == 99
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert len(cache) == 3


def test_c4_capacity_one_evicts_on_each_new_key():
    cache = LRUCache(capacity=1)
    cache.put("a", 1)
    cache.put("b", 2)
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert len(cache) == 1


def test_c4_eviction_chain():
    cache = LRUCache(capacity=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)  # evicts a
    cache.put("d", 4)  # evicts b
    with pytest.raises(KeyError):
        cache.get("a")
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("c") == 3
    assert cache.get("d") == 4


# =========================================================================
# C5. Use tracking — get and put-on-existing reset MRU; new-key insert does not
# =========================================================================

def test_c5_get_promotes_to_mru():
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")  # promotes "a"
    cache.put("d", 4)  # evicts "b" (oldest after promotion)
    assert cache.get("a") == 1
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_c5_put_on_existing_promotes_to_mru():
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)  # promotes "a"
    cache.put("d", 4)   # evicts "b"
    assert cache.get("a") == 99
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("c") == 3


def test_c5_inserting_new_key_does_not_reorder_others():
    """Inserting a brand-new key does not touch the LRU position of others."""
    cache = LRUCache(capacity=4)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)
    # a is the oldest; insert e and capacity overflow should evict a.
    cache.put("e", 5)
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.get("d") == 4
    assert cache.get("e") == 5


def test_c5_get_on_existing_key_under_capacity_does_not_evict_anything():
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")
    assert cache.get("b") == 2
    assert len(cache) == 2


def test_c5_repeated_get_keeps_key_alive_through_evictions():
    cache = LRUCache(capacity=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")  # a is MRU now
    cache.put("c", 3)  # evicts b
    cache.get("a")  # still alive
    cache.put("d", 4)  # evicts c
    assert cache.get("a") == 1


# =========================================================================
# C6. Expiration on get
# =========================================================================

def test_c6_get_missing_key_raises_keyerror():
    cache = LRUCache(capacity=3)
    with pytest.raises(KeyError):
        cache.get("nope")


def test_c6_get_expired_raises_keyerror():
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=SHORT_TTL)
    time.sleep(WAIT_PAST)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c6_get_expired_removes_entry():
    """After get raises on expired, len drops accordingly."""
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=SHORT_TTL)
    cache.put("b", 2)
    time.sleep(WAIT_PAST)
    with pytest.raises(KeyError):
        cache.get("a")
    # Now a should be gone — len reflects only b.
    assert len(cache) == 1
    # And re-putting "a" must not cause the cache to evict "b".
    cache.put("a", 99)
    assert cache.get("b") == 2
    assert cache.get("a") == 99


# =========================================================================
# C7. Length
# =========================================================================

def test_c7_len_empty_cache_is_zero():
    cache = LRUCache(capacity=3)
    assert len(cache) == 0


def test_c7_len_after_puts():
    cache = LRUCache(capacity=5)
    cache.put("a", 1)
    cache.put("b", 2)
    assert len(cache) == 2


def test_c7_len_does_not_count_expired_entries_even_without_access():
    """Entries whose TTL passed are NOT counted by len, even without get."""
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=SHORT_TTL)
    cache.put("b", 2)
    assert len(cache) == 2
    time.sleep(WAIT_PAST)
    assert len(cache) == 1


def test_c7_len_after_expiration_and_replacement():
    cache = LRUCache(capacity=3)
    cache.put("a", 1, ttl=SHORT_TTL)
    cache.put("b", 2, ttl=SHORT_TTL)
    cache.put("c", 3)
    time.sleep(WAIT_PAST)
    assert len(cache) == 1


def test_c7_len_does_not_count_partial_expiration():
    """Mix of expired and live entries reports only live count."""
    cache = LRUCache(capacity=5)
    cache.put("expire1", 1, ttl=SHORT_TTL)
    cache.put("expire2", 2, ttl=SHORT_TTL)
    cache.put("alive1", 10)
    cache.put("alive2", 20, ttl=10)
    time.sleep(WAIT_PAST)
    assert len(cache) == 2


# =========================================================================
# Cross-clause edge cases
# =========================================================================

def test_capacity_invariant_after_mixed_ops():
    """len <= capacity at all times."""
    cache = LRUCache(capacity=3)
    for i in range(20):
        cache.put(f"k{i}", i)
        assert len(cache) <= 3


def test_get_after_replacement_returns_new_value():
    cache = LRUCache(capacity=3)
    cache.put("a", 1)
    cache.put("a", 2)
    cache.put("a", 3)
    assert cache.get("a") == 3


def test_eviction_does_not_drop_recently_put_existing_key():
    """A re-put refreshes recency just like get."""
    cache = LRUCache(capacity=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 99)  # a is now MRU
    cache.put("c", 3)   # should evict b
    assert cache.get("a") == 99
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("c") == 3


def test_expired_entry_does_not_count_as_present_for_eviction():
    """If an entry has expired, putting a new key should not require evicting a live one."""
    cache = LRUCache(capacity=2)
    cache.put("a", 1, ttl=SHORT_TTL)
    cache.put("b", 2)
    time.sleep(WAIT_PAST)
    cache.put("c", 3)  # a is expired, b should survive
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_integer_keys_and_values():
    cache = LRUCache(capacity=3)
    cache.put(1, "one")
    cache.put(2, "two")
    assert cache.get(1) == "one"
    assert cache.get(2) == "two"


def test_tuple_key_works():
    cache = LRUCache(capacity=2)
    cache.put((1, 2), "pair")
    assert cache.get((1, 2)) == "pair"
