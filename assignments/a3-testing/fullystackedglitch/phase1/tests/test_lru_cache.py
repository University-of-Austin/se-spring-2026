"""Tests for the lru_cache module against its specification."""

import time

import pytest

from lru_cache import LRUCache


# ---------- C1: Capacity validation ----------

@pytest.mark.parametrize("bad_capacity", [0, -1, -5, -100])
def test_c1_non_positive_capacity_raises_value_error(bad_capacity):
    """Capacity must be a positive integer; 0 or negative raises ValueError."""
    with pytest.raises(ValueError):
        LRUCache(bad_capacity)


def test_c1_capacity_one_is_valid():
    """The smallest legal capacity is 1."""
    cache = LRUCache(1)
    cache.put("a", 1)
    assert cache.get("a") == 1


# ---------- C2: put/get round-trip and TTL=None ----------

def test_c2_put_then_get_returns_value():
    """A value stored under a key is retrievable by that key."""
    cache = LRUCache(3)
    cache.put("a", 1)
    assert cache.get("a") == 1


def test_c2_put_replaces_existing_value():
    """Putting a key that already exists overwrites the value."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("a", 2)
    assert cache.get("a") == 2


def test_c2_ttl_none_does_not_expire():
    """An entry with ttl=None survives a real-time wait without expiring."""
    cache = LRUCache(3)
    cache.put("a", 1)
    time.sleep(0.05)
    assert cache.get("a") == 1


def test_c2_get_missing_key_raises_key_error():
    """get on a key never inserted raises KeyError."""
    cache = LRUCache(3)
    with pytest.raises(KeyError):
        cache.get("nope")


def test_c2_ttl_numeric_entry_retrievable_before_expiry():
    """An entry with a future TTL is gettable while still in its lifetime."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.5)
    assert cache.get("a") == 1


# ---------- C3: TTL replacement on re-put ----------

def test_c3_re_put_with_none_ttl_clears_prior_expiration():
    """Re-putting an existing key with no TTL clears any previously-set expiration."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("a", 2)
    time.sleep(0.1)
    assert cache.get("a") == 2


def test_c3_re_put_with_new_ttl_supersedes_old_ttl():
    """Re-putting an existing key with a fresh TTL replaces the prior expiration."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.02)
    cache.put("a", 2, ttl=0.5)
    time.sleep(0.1)
    assert cache.get("a") == 2


def test_c3_re_put_replaces_value_even_with_no_ttl_change():
    """A re-put with no TTL on either side still updates the value."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("a", 99)
    assert cache.get("a") == 99


def test_c3_re_put_with_short_ttl_after_no_ttl_does_expire():
    """An entry put with no TTL, then re-put with a short TTL, must now expire."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("a", 2, ttl=0.02)
    time.sleep(0.08)
    with pytest.raises(KeyError):
        cache.get("a")


# ---------- C4: Capacity eviction ----------

def test_c4_lru_entry_evicted_when_inserting_into_full_cache():
    """When at capacity, inserting a new key evicts the least-recently-used entry."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c4_other_entries_survive_eviction():
    """Eviction only removes the LRU entry; the rest stay."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_c4_length_stays_at_capacity_after_eviction():
    """After inserting into a full cache, length equals capacity, not capacity+1."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)
    assert len(cache) == 3


def test_c4_re_put_of_existing_key_does_not_evict():
    """Re-putting a key already in the cache does not trigger eviction."""
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 99)
    assert cache.get("a") == 99
    assert cache.get("b") == 2
    assert len(cache) == 2


# ---------- C5: Use tracking promotes to MRU ----------

def test_c5_get_promotes_key_so_it_is_not_evicted():
    """A get on an existing key resets its LRU position; it must not be the next to evict."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")
    cache.put("d", 4)
    assert cache.get("a") == 1
    with pytest.raises(KeyError):
        cache.get("b")


def test_c5_put_on_existing_key_promotes_to_mru():
    """put on an existing key counts as a use and promotes it."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)
    cache.put("d", 4)
    assert cache.get("a") == 99
    with pytest.raises(KeyError):
        cache.get("b")


def test_c5_inserting_new_key_does_not_promote_other_keys():
    """A new-key insert does not change the LRU order of existing keys."""
    cache = LRUCache(4)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)
    cache.put("e", 5)
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2


def test_c5_get_promotion_chain_protects_oldest_repeatedly():
    """Repeated gets keep promoting the oldest; another key is always the LRU victim."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")
    cache.get("a")
    cache.put("d", 4)
    assert cache.get("a") == 1
    assert cache.get("c") == 3
    assert cache.get("d") == 4
    with pytest.raises(KeyError):
        cache.get("b")


# ---------- C6: Expiration on get ----------

def test_c6_get_on_expired_entry_raises_key_error():
    """An entry whose TTL has passed raises KeyError when accessed."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.02)
    time.sleep(0.05)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c6_get_on_expired_entry_removes_it_from_cache():
    """After get on an expired entry raises, length reflects its removal."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.02)
    cache.put("b", 2)
    time.sleep(0.05)
    with pytest.raises(KeyError):
        cache.get("a")
    assert len(cache) == 1
    assert cache.get("b") == 2


def test_c6_get_on_never_inserted_key_raises_key_error():
    """get on a key that was never put raises KeyError (distinct from expiration)."""
    cache = LRUCache(3)
    cache.put("a", 1)
    with pytest.raises(KeyError):
        cache.get("zzz")


# Edge case beyond strict C6: validates that re-putting after expiration
# restores the key as a fresh live entry, not a stale corpse.
def test_c6_re_putting_an_expired_key_makes_it_live_again():
    """After expiration, putting the key again restores it as a fresh entry."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.02)
    time.sleep(0.05)
    cache.put("a", 99)
    assert cache.get("a") == 99


# ---------- C7: Length excludes expired entries ----------
#
# The C7 trap: a buggy impl might just return len(self._dict) and only purge
# expired entries inside get(). That would pass tests that touch the key
# first, but fail tests that check len() without ever calling get on the
# expired entry. Tests 2 and 3 deliberately never call get on the expired
# keys before asserting on len. Tests 1 and 4 are sanity coverage on basic
# counting behavior (insertion and post-eviction).

def test_c7_len_counts_live_entries():
    """len returns the number of currently-stored entries with no expiration in play."""
    cache = LRUCache(3)
    assert len(cache) == 0
    cache.put("a", 1)
    assert len(cache) == 1
    cache.put("b", 2)
    assert len(cache) == 2


def test_c7_len_excludes_expired_entries_without_access():
    """An expired entry is not counted by len, even if get has not been called on it."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.02)
    cache.put("b", 2)
    time.sleep(0.05)
    assert len(cache) == 1


def test_c7_len_zero_when_all_entries_expired():
    """If every entry has expired, len reports 0."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.02)
    cache.put("b", 2, ttl=0.02)
    time.sleep(0.05)
    assert len(cache) == 0


def test_c7_len_after_eviction_reflects_capacity():
    """After eviction caused by inserting into a full cache, len equals capacity."""
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert len(cache) == 2
