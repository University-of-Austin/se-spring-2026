"""Tests for lru_cache.LRUCache, organized by spec clause.

Test names encode the clause they pin down (e.g. test_c4_*). Tests for
behavior the spec implies but does not call out explicitly are prefixed
test_implied_*.
"""
import time

import pytest

from lru_cache import LRUCache


# ---------- C1: capacity ----------

def test_c1_capacity_zero_raises():
    """0 is the rejection threshold: capacity must be >= 1."""
    with pytest.raises(ValueError):
        LRUCache(0)


def test_c1_capacity_negative_one_raises():
    """Just below the threshold."""
    with pytest.raises(ValueError):
        LRUCache(-1)


def test_c1_capacity_negative_large_raises():
    """Far below the threshold; any negative is invalid."""
    with pytest.raises(ValueError):
        LRUCache(-100)


def test_c1_capacity_one_works():
    """1 is the smallest legal capacity (one above the rejection threshold)."""
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


def test_c2_ttl_zero_expires_immediately():
    """ttl is a number; 0 is a number, so the entry expires at monotonic() + 0."""
    c = LRUCache(3)
    c.put("a", 1, ttl=0)
    with pytest.raises(KeyError):
        c.get("a")


def test_c2_ttl_negative_expires_immediately():
    """Negative ttl yields an expiration time in the past."""
    c = LRUCache(3)
    c.put("a", 1, ttl=-0.01)
    with pytest.raises(KeyError):
        c.get("a")


def test_c2_put_default_ttl_does_not_expire():
    """The default ttl arg (omitted entirely) must behave like ttl=None."""
    c = LRUCache(3)
    c.put("a", 1)  # ttl arg omitted
    time.sleep(0.05)
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


def test_c3_reput_long_ttl_extends_short_ttl():
    """Symmetric to short-supersedes-long: re-put with longer TTL must extend life past the original."""
    c = LRUCache(3)
    c.put("a", 1, ttl=0.05)
    c.put("a", 2, ttl=1.0)
    time.sleep(0.12)  # past the original short TTL
    assert c.get("a") == 2


def test_c3_reput_with_ttl_overrides_no_ttl():
    """Symmetric to ttl=None-clears: adding a TTL to a previously-untimed entry must expire it."""
    c = LRUCache(3)
    c.put("a", 1)  # no TTL initially
    c.put("a", 2, ttl=0.05)
    time.sleep(0.12)
    with pytest.raises(KeyError):
        c.get("a")


def test_c3_reput_after_silent_expiration_works():
    """Re-put on a key whose TTL has lapsed (no get-cleanup yet) must yield a working entry."""
    c = LRUCache(3)
    c.put("a", 1, ttl=0.05)
    time.sleep(0.12)  # 'a' expired but nothing has touched it
    c.put("a", 99)  # re-put without any prior get
    assert c.get("a") == 99


def test_c3_reput_resets_expiration_clock_from_latest_put():
    """Re-put must restart expiration timing from the re-put moment, not original put time."""
    c = LRUCache(3)
    c.put("a", 1, ttl=0.10)
    time.sleep(0.06)
    c.put("a", 2, ttl=0.10)  # new expiration should be ~now+0.10
    time.sleep(0.06)  # now ~0.12 from first put, ~0.06 from second put
    assert c.get("a") == 2  # alive only if clock was reset
    time.sleep(0.06)  # now ~0.12 from second put
    with pytest.raises(KeyError):
        c.get("a")


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


def test_c4_below_capacity_insert_does_not_evict():
    """Putting into a non-full cache must not evict any prior entry."""
    c = LRUCache(3)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    assert c.get("b") == 2


def test_c4_expired_entry_does_not_count_toward_capacity():
    """Expired entries must not trigger eviction of alive entries on a new insert.

    cap=2 with one expired + one alive: putting a third key fills the expired slot,
    leaving the alive entry untouched. Catches a bug where eviction uses raw size
    instead of effective len() (per C7).
    """
    c = LRUCache(2)
    c.put("a", 1, ttl=0.05)
    c.put("b", 2)
    time.sleep(0.12)  # 'a' expires silently
    c.put("c", 3)
    assert c.get("b") == 2
    assert c.get("c") == 3
    with pytest.raises(KeyError):
        c.get("a")


def test_c4_alive_ttl_entry_evicts_normally_when_lru():
    """LRU is by access order, not TTL: an alive TTL'd LRU entry still gets evicted."""
    c = LRUCache(2)
    c.put("a", 1, ttl=10.0)  # plenty of TTL
    c.put("b", 2)
    c.put("c", 3)  # full at cap=2; evicts a (LRU)
    with pytest.raises(KeyError):
        c.get("a")
    assert c.get("b") == 2
    assert c.get("c") == 3


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


def test_c5_failed_get_missing_does_not_reorder():
    """A failed get on a never-existed key must not reshuffle existing keys.

    Verified via two-step eviction: if the failed get reordered anything,
    the wrong key would be evicted on the next insert.
    """
    c = LRUCache(3)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    with pytest.raises(KeyError):
        c.get("nope")
    c.put("d", 4)  # should evict a (LRU)
    c.put("e", 5)  # should evict b (next LRU)
    with pytest.raises(KeyError):
        c.get("a")
    with pytest.raises(KeyError):
        c.get("b")
    assert c.get("c") == 3


def test_c5_failed_get_expired_does_not_reorder_survivors():
    """A failed get on an expired key must not reshuffle the alive entries' order."""
    c = LRUCache(3)
    c.put("a", 1, ttl=0.05)  # will expire
    c.put("b", 2)
    c.put("c", 3)
    time.sleep(0.12)  # 'a' expires
    with pytest.raises(KeyError):
        c.get("a")  # cleanup; must not touch b/c order
    # b is older than c; eviction order on a fresh insert should be b first.
    c.put("d", 4)  # cache now {b, c, d}, len=3
    c.put("e", 5)  # full; evict LRU = b
    with pytest.raises(KeyError):
        c.get("b")
    assert c.get("c") == 3


def test_c5_reput_existing_does_not_reorder_other_keys():
    """Re-putting an existing key must promote only that key; others keep relative order."""
    c = LRUCache(3)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    c.put("b", 99)  # b -> MRU; relative order of a/c unchanged (a older than c)
    c.put("d", 4)  # full; evict LRU = a
    with pytest.raises(KeyError):
        c.get("a")
    assert c.get("c") == 3


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


def test_c6_get_on_alive_ttl_entry_does_not_extend_ttl():
    """A get is a use for LRU ordering, but must not refresh expiration time."""
    c = LRUCache(3)
    c.put("a", 1, ttl=0.10)
    time.sleep(0.05)
    assert c.get("a") == 1  # still alive mid-window
    time.sleep(0.07)  # total > 0.10 from put
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


def test_c6_reput_after_expired_get_works():
    """After a get cleans up an expired entry, re-putting that key must act as a fresh insert."""
    c = LRUCache(3)
    c.put("a", 1, ttl=0.05)
    time.sleep(0.12)
    with pytest.raises(KeyError):
        c.get("a")  # explicit cleanup path
    c.put("a", 99)
    assert c.get("a") == 99
    assert len(c) == 1


def test_c6_expired_get_frees_capacity_for_new_insert():
    """A failed get-on-expired removes the entry; a subsequent insert must not need to evict.

    Pairs C6 cleanup with C4 capacity bookkeeping. Different code path from
    test_c4_expired_entry_does_not_count_toward_capacity (which uses silent expiration).
    """
    c = LRUCache(2)
    c.put("a", 1, ttl=0.05)
    c.put("b", 2)
    time.sleep(0.12)
    with pytest.raises(KeyError):
        c.get("a")  # explicit cleanup
    c.put("c", 3)  # cache size was 1; no eviction
    assert c.get("b") == 2
    assert c.get("c") == 3


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


def test_c7_len_zero_when_all_entries_expired():
    """If every entry has expired, len() must be exactly 0."""
    c = LRUCache(3)
    c.put("a", 1, ttl=0.05)
    c.put("b", 2, ttl=0.05)
    c.put("c", 3, ttl=0.05)
    time.sleep(0.12)
    assert len(c) == 0


def test_c7_len_unchanged_after_failed_get_on_missing():
    """A failed get on a never-existed key must not change len() (no side effect)."""
    c = LRUCache(3)
    c.put("a", 1)
    c.put("b", 2)
    n = len(c)
    with pytest.raises(KeyError):
        c.get("nope")
    assert len(c) == n


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


def test_implied_none_value_round_trips():
    """None is a legal value: get must return None, not raise KeyError.

    Catches a bug where the implementation uses `dict.get(key)` returning None as
    a missing-key sentinel, which would conflate legitimate None values with absence.
    """
    c = LRUCache(3)
    c.put("a", None)
    assert c.get("a") is None


def test_implied_separate_caches_have_independent_state():
    """Two LRUCache instances must not share storage, order, or any other state.

    Catches a bug where the internal dict/order list is a class attribute instead of
    an instance attribute (the classic Python mutable-default-at-class-scope gotcha).
    """
    cache_a = LRUCache(3)
    cache_b = LRUCache(3)
    cache_a.put("a", 1)
    assert len(cache_b) == 0
    with pytest.raises(KeyError):
        cache_b.get("a")


def test_implied_reput_after_eviction_works_as_fresh_insert():
    """Once a key is evicted, re-putting it must behave as a brand-new insert."""
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)  # evicts a (LRU)
    c.put("a", 99)  # fresh insert; full again -> evicts b (now LRU)
    assert c.get("a") == 99
    with pytest.raises(KeyError):
        c.get("b")
    assert c.get("c") == 3
