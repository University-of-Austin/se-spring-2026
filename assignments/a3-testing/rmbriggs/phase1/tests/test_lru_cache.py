"""Tests for lru_cache.LRUCache, organized by spec clause.

Test names encode the clause they pin down (e.g. test_c4_*). Tests for
behavior the spec implies but does not call out explicitly are prefixed
test_implied_*.
"""
import time

import pytest

from lru_cache import LRUCache


# ---------- C1: capacity ----------

@pytest.mark.parametrize("cap", [-100, -1, 0])
def test_c1_capacity_non_positive_raises(cap):
    with pytest.raises(ValueError):
        LRUCache(cap)


def test_c1_capacity_one_works():
    c = LRUCache(1)
    c.put("a", 1)
    assert c.get("a") == 1
    assert len(c) == 1


# ---------- C2: put / ttl ----------

def test_c2_put_then_get_returns_value():
    c = LRUCache(3)
    c.put("a", 1)
    assert c.get("a") == 1


def test_c2_put_replaces_existing_value():
    c = LRUCache(3)
    c.put("a", 1)
    c.put("a", 2)
    assert c.get("a") == 2
    assert len(c) == 1


def test_c2_put_with_ttl_none_does_not_expire():
    c = LRUCache(3)
    c.put("a", 1, ttl=None)
    time.sleep(0.05)
    assert c.get("a") == 1


def test_c2_put_with_ttl_expires_after_window():
    c = LRUCache(3)
    c.put("a", 1, ttl=0.05)
    time.sleep(0.12)
    with pytest.raises(KeyError):
        c.get("a")


def test_c2_put_with_int_ttl_alive_within_window():
    """Spec: ttl can be int or float. Both behave the same way."""
    c = LRUCache(3)
    c.put("a", 1, ttl=1)
    assert c.get("a") == 1


def test_c2_put_with_float_ttl_alive_within_window():
    c = LRUCache(3)
    c.put("a", 1, ttl=1.0)
    assert c.get("a") == 1


# ---------- C3: TTL replacement on re-put ----------

def test_c3_reput_with_ttl_none_clears_old_ttl():
    """Re-putting with ttl=None must clear a previously-set expiration."""
    c = LRUCache(3)
    c.put("a", 1, ttl=0.1)
    c.put("a", 2)  # ttl=None implicit; clears expiration
    time.sleep(0.15)
    assert c.get("a") == 2  # would have expired if ttl wasn't cleared


def test_c3_reput_short_ttl_supersedes_long_ttl():
    c = LRUCache(3)
    c.put("a", 1, ttl=2.0)
    c.put("a", 2, ttl=0.05)
    time.sleep(0.12)
    with pytest.raises(KeyError):
        c.get("a")


def test_c3_reput_replaces_value_completely():
    c = LRUCache(3)
    c.put("a", 1, ttl=0.5)
    c.put("a", 999, ttl=0.5)
    assert c.get("a") == 999


# ---------- C4: capacity eviction ----------

def test_c4_eviction_when_full_evicts_lru():
    """Canonical example from the spec PDF."""
    c = LRUCache(3)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    c.get("a")  # promotes a; b is now LRU
    c.put("d", 4)  # evicts b
    with pytest.raises(KeyError):
        c.get("b")
    assert c.get("a") == 1
    assert c.get("c") == 3
    assert c.get("d") == 4


def test_c4_size_stays_at_capacity_after_eviction():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)  # evicts a
    assert len(c) == 2


def test_c4_replace_existing_when_full_does_not_evict():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 99)  # replace, not insert; no eviction
    assert len(c) == 2
    assert c.get("a") == 99
    assert c.get("b") == 2


# ---------- C5: use tracking ----------

def test_c5_get_promotes_to_mru():
    c = LRUCache(3)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    c.get("a")  # promotes a; b is LRU
    c.put("d", 4)
    with pytest.raises(KeyError):
        c.get("b")


def test_c5_put_existing_promotes_to_mru():
    c = LRUCache(3)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    c.put("a", 99)  # promotes a; b is LRU
    c.put("d", 4)
    with pytest.raises(KeyError):
        c.get("b")
    assert c.get("a") == 99


def test_c5_new_insert_does_not_disturb_order_of_others():
    """Inserting a new key must not reshuffle the order of existing keys."""
    c = LRUCache(3)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    c.put("d", 4)  # at capacity; evicts a (LRU). Should NOT promote b or c.
    # If b/c got promoted by insertion of d, the next eviction would be wrong.
    c.put("e", 5)  # should evict b (the new LRU after a)
    with pytest.raises(KeyError):
        c.get("b")
    assert c.get("c") == 3
    assert c.get("d") == 4
    assert c.get("e") == 5


# ---------- C6: get raises ----------

def test_c6_get_missing_raises_keyerror():
    c = LRUCache(3)
    with pytest.raises(KeyError):
        c.get("nope")


def test_c6_get_expired_raises_keyerror():
    c = LRUCache(3)
    c.put("a", 1, ttl=0.05)
    time.sleep(0.12)
    with pytest.raises(KeyError):
        c.get("a")


def test_c6_get_expired_removes_entry():
    c = LRUCache(3)
    c.put("a", 1, ttl=0.05)
    c.put("b", 2)
    time.sleep(0.12)
    with pytest.raises(KeyError):
        c.get("a")
    # 'a' should be gone from the cache after the failed get
    assert len(c) == 1


# ---------- C7: length ----------

def test_c7_len_starts_zero():
    assert len(LRUCache(3)) == 0


def test_c7_len_counts_entries():
    c = LRUCache(5)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    assert len(c) == 3


def test_c7_len_after_replace_not_doubled():
    c = LRUCache(3)
    c.put("a", 1)
    c.put("a", 2)
    assert len(c) == 1


def test_c7_len_excludes_expired_unaccessed():
    """Expired entries are excluded from len() even before any get() touches them."""
    c = LRUCache(3)
    c.put("a", 1, ttl=0.05)
    c.put("b", 2)
    time.sleep(0.12)
    assert len(c) == 1


# ---------- Implied / edge cases ----------

def test_implied_capacity_one_replace_then_evict():
    c = LRUCache(1)
    c.put("a", 1)
    c.put("a", 2)  # replace, no eviction
    assert len(c) == 1
    c.put("b", 3)  # evicts a
    with pytest.raises(KeyError):
        c.get("a")
    assert c.get("b") == 3


def test_implied_eviction_evicts_only_one():
    c = LRUCache(3)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    c.put("d", 4)  # evicts a
    assert len(c) == 3


def test_implied_get_does_not_change_size():
    c = LRUCache(3)
    c.put("a", 1)
    c.put("b", 2)
    n = len(c)
    c.get("a")
    assert len(c) == n


def test_implied_keys_can_be_any_hashable():
    """Spec note: keys and values can be any hashable Python object."""
    c = LRUCache(3)
    c.put((1, 2), "tuple-key")
    c.put(42, "int-key")
    c.put("s", "str-key")
    assert c.get((1, 2)) == "tuple-key"
    assert c.get(42) == "int-key"
    assert c.get("s") == "str-key"


def test_implied_get_after_partial_expiration_promotes_survivor():
    """A surviving entry's LRU position should still update via get."""
    c = LRUCache(3)
    c.put("a", 1, ttl=0.05)
    c.put("b", 2)
    c.put("c", 3)
    time.sleep(0.12)  # 'a' expires
    c.get("b")  # promotes b; with a expired, c is now LRU
    c.put("d", 4)  # cache holds b, c, d -- 'a' was already expired-evicted
    # c should still be present (LRU but not yet evicted; len was 2 before put d)
    assert c.get("c") == 3
    assert c.get("d") == 4
    assert c.get("b") == 2
