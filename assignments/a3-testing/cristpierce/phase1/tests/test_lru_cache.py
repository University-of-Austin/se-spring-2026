"""Tests for the lru_cache module, organized clause by clause against the spec.

Spec lives at starter/assignment3/specs/lru_cache.md. Each test name encodes the
clause it pins down so the spec is the source of truth, not the implementation.
"""
import time

import pytest

from lru_cache import LRUCache


# ---------------------------------------------------------------------------
# C1. Capacity validation
# ---------------------------------------------------------------------------

def test_c1_capacity_zero_raises():
    with pytest.raises(ValueError):
        LRUCache(0)


def test_c1_capacity_negative_raises():
    with pytest.raises(ValueError):
        LRUCache(-1)


def test_c1_capacity_large_negative_raises():
    with pytest.raises(ValueError):
        LRUCache(-1000)


def test_c1_capacity_one_is_valid():
    cache = LRUCache(1)
    cache.put("a", 1)
    assert cache.get("a") == 1


def test_c1_capacity_positive_ok():
    cache = LRUCache(10)
    assert len(cache) == 0


# ---------------------------------------------------------------------------
# C2. put / get basic behavior
# ---------------------------------------------------------------------------

def test_c2_put_then_get_returns_value():
    cache = LRUCache(2)
    cache.put("a", 1)
    assert cache.get("a") == 1


def test_c2_put_no_ttl_does_not_expire():
    cache = LRUCache(2)
    cache.put("a", 1)
    time.sleep(0.05)
    assert cache.get("a") == 1


def test_c2_put_with_ttl_returns_value_before_expiry():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.5)
    assert cache.get("a") == 1


def test_c2_put_with_ttl_expires_after_ttl():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c2_put_accepts_int_ttl():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=1)
    assert cache.get("a") == 1


def test_c2_put_replaces_value_for_existing_key():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("a", 2)
    assert cache.get("a") == 2


def test_c2_put_does_not_grow_beyond_capacity_on_replace():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("a", 2)
    cache.put("a", 3)
    assert len(cache) == 1


def test_c2_ttl_zero_expires_immediately():
    # Spec C2: "If `ttl` is a number ... the entry expires at
    # time.monotonic() + ttl". With ttl=0, the entry is already at/past
    # its expiration as soon as the next monotonic() reading happens.
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0)
    # A tiny sleep guarantees we're past the boundary on the next get.
    time.sleep(0.01)
    with pytest.raises(KeyError):
        cache.get("a")


# ---------------------------------------------------------------------------
# C3. TTL replacement on re-put
# ---------------------------------------------------------------------------

def test_c3_reput_clears_previous_ttl():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    cache.put("a", 2)  # ttl=None, should clear expiration
    time.sleep(0.1)
    assert cache.get("a") == 2


def test_c3_reput_replaces_old_ttl_with_new_ttl():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=10)  # long TTL
    cache.put("a", 2, ttl=0.05)  # new shorter TTL takes over
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c3_reput_extends_short_ttl():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    cache.put("a", 2, ttl=10)  # extend
    time.sleep(0.1)
    assert cache.get("a") == 2


def test_c3_reput_replaces_value_completely():
    cache = LRUCache(2)
    cache.put("a", "first", ttl=10)
    cache.put("a", "second", ttl=10)
    assert cache.get("a") == "second"


# ---------------------------------------------------------------------------
# C4. Capacity eviction
# ---------------------------------------------------------------------------

def test_c4_evicts_lru_when_full():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)  # should evict "a"
    with pytest.raises(KeyError):
        cache.get("a")


def test_c4_keeps_other_entries_after_eviction():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)  # evicts "a"
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_c4_len_stays_at_capacity_after_evict_and_insert():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)
    assert len(cache) == 3


def test_c4_replacing_existing_key_at_capacity_does_not_evict():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)  # not a new key, must not evict
    assert cache.get("a") == 99
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert len(cache) == 3


def test_c4_evicts_before_insert_so_capacity_holds():
    # If eviction happened AFTER insert, len would briefly be capacity+1.
    # We can't observe that mid-operation, but we can assert post-condition.
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert len(cache) == 2


def test_c4_capacity_one_evicts_each_new_key():
    cache = LRUCache(1)
    cache.put("a", 1)
    cache.put("b", 2)
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2


# ---------------------------------------------------------------------------
# C5. Use tracking (LRU ordering)
# ---------------------------------------------------------------------------

def test_c5_get_promotes_to_most_recently_used():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")  # promote "a"
    cache.put("d", 4)  # should evict "b" (now LRU), not "a"
    assert cache.get("a") == 1
    with pytest.raises(KeyError):
        cache.get("b")


def test_c5_put_existing_promotes_to_most_recently_used():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)  # promote "a" via re-put
    cache.put("d", 4)  # should evict "b"
    assert cache.get("a") == 99
    with pytest.raises(KeyError):
        cache.get("b")


def test_c5_inserting_new_key_does_not_promote_others():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    # No gets; "a" is still LRU. Inserting "d" should evict "a".
    cache.put("d", 4)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c5_repeated_get_keeps_key_alive():
    # Repeatedly touching "a" should keep it as MRU so a single new insert
    # evicts "b" instead.
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    for _ in range(5):
        cache.get("a")
    cache.put("c", 3)  # should evict "b"
    assert cache.get("a") == 1
    with pytest.raises(KeyError):
        cache.get("b")


def test_c5_get_on_ttld_alive_entry_promotes_to_mru():
    # A get on a TTL'd entry that is still alive should both return the
    # value AND count as a "use" for LRU ordering — TTL'd entries are not
    # second-class with respect to use-tracking.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=10)  # long, still alive
    cache.put("b", 2)
    cache.put("c", 3)
    # Touch "a" so it becomes MRU; "b" is now LRU.
    assert cache.get("a") == 1
    cache.put("d", 4)  # should evict "b"
    assert cache.get("a") == 1
    with pytest.raises(KeyError):
        cache.get("b")


def test_c5_lru_order_with_mixed_get_and_put():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")  # order: b, c, a
    cache.get("b")  # order: c, a, b
    cache.put("d", 4)  # evicts c
    with pytest.raises(KeyError):
        cache.get("c")
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("d") == 4


# ---------------------------------------------------------------------------
# C6. Expiration on get / missing key
# ---------------------------------------------------------------------------

def test_c6_get_missing_key_raises_keyerror():
    cache = LRUCache(2)
    with pytest.raises(KeyError):
        cache.get("nope")


def test_c6_get_expired_raises_keyerror():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c6_get_expired_removes_entry():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")
    # After the failed get, entry must be gone — re-putting and the slot
    # behaves like a fresh insert.
    cache.put("a", 2)
    assert cache.get("a") == 2


def test_c6_expired_get_does_not_crash_then_works_for_other_keys():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2)
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2


# ---------------------------------------------------------------------------
# C7. Length excludes expired entries
# ---------------------------------------------------------------------------

def test_c7_len_starts_at_zero():
    cache = LRUCache(5)
    assert len(cache) == 0


def test_c7_len_counts_live_entries():
    cache = LRUCache(5)
    cache.put("a", 1)
    cache.put("b", 2)
    assert len(cache) == 2


def test_c7_len_excludes_expired_without_access():
    # Entry must drop out of len even though we never called get on it.
    cache = LRUCache(5)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2)
    time.sleep(0.1)
    assert len(cache) == 1


def test_c7_len_excludes_all_expired():
    cache = LRUCache(5)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2, ttl=0.05)
    time.sleep(0.1)
    assert len(cache) == 0


def test_c7_len_unaffected_by_no_ttl():
    cache = LRUCache(5)
    cache.put("a", 1)
    cache.put("b", 2)
    time.sleep(0.05)
    assert len(cache) == 2


# ---------------------------------------------------------------------------
# Edge cases the spec implies but doesn't spell out
# ---------------------------------------------------------------------------

def test_edge_eviction_targets_lru_after_long_chain():
    cache = LRUCache(3)
    for k, v in [("a", 1), ("b", 2), ("c", 3)]:
        cache.put(k, v)
    # Touch a, b, c in that order so c is most recent, a is least.
    cache.get("a")
    cache.get("b")
    cache.get("c")
    # Now "a" is LRU again (got pushed back when we touched b and c).
    cache.put("d", 4)  # evicts "a"
    with pytest.raises(KeyError):
        cache.get("a")


def test_edge_value_can_be_none():
    cache = LRUCache(2)
    cache.put("a", None)
    assert cache.get("a") is None


def test_edge_non_string_keys():
    cache = LRUCache(3)
    cache.put((1, 2), "tuple")
    cache.put(42, "int")
    cache.put(frozenset([1, 2]), "fs")
    assert cache.get((1, 2)) == "tuple"
    assert cache.get(42) == "int"
    assert cache.get(frozenset([1, 2])) == "fs"


def test_edge_expired_entry_does_not_block_new_put_at_capacity():
    # An expired entry should not consume a capacity slot.
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2)
    time.sleep(0.1)
    # "a" is expired; len(cache) should be 1, so adding "c" should not
    # evict "b".
    cache.put("c", 3)
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_edge_reput_same_key_at_capacity_does_not_evict():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 100)  # re-put existing key, not a new insertion
    # Both keys should still be present.
    assert cache.get("a") == 100
    assert cache.get("b") == 2


def test_edge_get_after_replacement_returns_new_value_not_old():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("a", 2)
    cache.put("a", 3)
    assert cache.get("a") == 3


def test_edge_ttl_isolated_per_entry():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=10)  # long
    cache.put("b", 2, ttl=0.05)  # short
    time.sleep(0.1)
    assert cache.get("a") == 1
    with pytest.raises(KeyError):
        cache.get("b")


@pytest.mark.parametrize("bad_capacity", [0, -1, -100])
def test_edge_invalid_capacity_parametrized(bad_capacity):
    with pytest.raises(ValueError):
        LRUCache(bad_capacity)
