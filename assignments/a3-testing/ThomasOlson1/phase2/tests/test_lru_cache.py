"""Phase 1 tests for the `lru_cache` module.

Tests are organized clause-by-clause against the spec at
`starter/assignment3/specs/lru_cache.md`.
"""
import time

import pytest

from lru_cache import LRUCache


# ---------------------------------------------------------------------------
# C1. Capacity. `capacity` is a positive integer. `__init__(0)` or
# `__init__(-5)` raises ValueError. Any non-int type for `capacity` is
# outside the spec.
# ---------------------------------------------------------------------------

def test_c1_zero_capacity_raises_value_error():
    with pytest.raises(ValueError):
        LRUCache(0)


@pytest.mark.parametrize("capacity", [-1, -5, -100, -10**6])
def test_c1_negative_capacity_raises_value_error(capacity):
    with pytest.raises(ValueError):
        LRUCache(capacity)


def test_c1_capacity_one_constructs_empty_cache():
    cache = LRUCache(1)
    assert len(cache) == 0


def test_c1_large_positive_capacity_constructs_empty_cache():
    cache = LRUCache(10**9)
    assert len(cache) == 0

# ---------------------------------------------------------------------------
# C2. put(key, value, ttl). Inserts or replaces the entry for `key`.
# If `ttl` is None, the entry never expires. If `ttl` is a number (int or
# float), the entry expires at `time.monotonic() + ttl`.
# ---------------------------------------------------------------------------

def test_c2_put_then_get_returns_value():
    cache = LRUCache(3)
    cache.put("a", 1)
    assert cache.get("a") == 1


def test_c2_multiple_keys_independently_retrievable():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", "two")
    cache.put("c", [3, 3, 3])
    assert cache.get("a") == 1
    assert cache.get("b") == "two"
    assert cache.get("c") == [3, 3, 3]


def test_c2_re_put_replaces_value():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("a", 99)
    assert cache.get("a") == 99


def test_c2_re_put_does_not_grow_length():
    cache = LRUCache(5)
    cache.put("a", 1)
    cache.put("a", 2)
    cache.put("a", 3)
    assert len(cache) == 1


def test_c2_ttl_none_does_not_expire_in_test_window():
    # Spec: "If ttl is None, the entry never expires." We can't prove "never"
    # with a finite test, but we can rule out the obvious failure modes
    # (TTL=None treated as 0, or as a short default) by sleeping briefly and
    # confirming the entry is still retrievable.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=None)
    time.sleep(0.05)
    assert cache.get("a") == 1


def test_c2_default_ttl_does_not_expire_in_test_window():
    # The default `ttl` argument is None per the signature. Confirm the
    # default behaves the same as explicit `ttl=None`.
    cache = LRUCache(3)
    cache.put("a", 1)
    time.sleep(0.05)
    assert cache.get("a") == 1


@pytest.mark.parametrize(
    "ttl, wait",
    [
        pytest.param(0, 0.05, id="int-ttl-0"),
        pytest.param(0.05, 0.1, id="float-ttl-0.05"),
    ],
)
def test_c2_short_ttl_entry_expires_after_wait(ttl, wait):
    # Numeric-TTL branch: when the wait exceeds the TTL, the entry is
    # expired and `get` must raise `KeyError`. Parametrized across an int
    # TTL (`0`, expires immediately) and a float TTL (`0.05`, expires
    # within a 100ms wait) to exercise both spec-named numeric types.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=ttl)
    time.sleep(wait)
    with pytest.raises(KeyError):
        cache.get("a")


@pytest.mark.parametrize(
    "ttl",
    [
        pytest.param(1, id="int-ttl-1"),
        pytest.param(0.5, id="float-ttl-0.5"),
    ],
)
def test_c2_numeric_ttl_does_not_expire_when_wait_is_shorter(ttl):
    # Complement to the "expires after wait" test: when the wait is shorter
    # than the TTL, the entry must still be retrievable. This catches a
    # bug where the numeric branch always treats entries as expired.
    # Parametrized over int and float TTLs to cover both spec-named types.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=ttl)
    time.sleep(0.05)
    assert cache.get("a") == 1


# ---------------------------------------------------------------------------
# C3. TTL replacement on re-put. When `put` is called on a key that already
# exists, the old entry is completely replaced: its value, its TTL, and its
# expiration time are all superseded by the new arguments. Passing
# `ttl=None` to a re-put on a previously-TTL'd key clears the expiration.
# ---------------------------------------------------------------------------

def test_c3_re_put_with_longer_ttl_extends_lifetime():
    # Re-put with a far-future TTL must override the original short TTL.
    # After the original TTL would have expired, the entry must still be
    # retrievable. Catches a bug where re-put doesn't replace the TTL.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("a", 99, ttl=10)
    time.sleep(0.1)
    assert cache.get("a") == 99


def test_c3_re_put_with_shorter_ttl_shortens_lifetime():
    # Re-put with a short TTL must override the original long TTL. After
    # the new short TTL expires, the entry must be gone. Catches a bug
    # where re-put leaves the original (longer) TTL in place.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=10)
    cache.put("a", 99, ttl=0.05)
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c3_re_put_with_none_ttl_clears_expiration():
    # Spec: "Passing ttl=None to a re-put on a previously-TTL'd key clears
    # the expiration." After the original TTL would have expired, the
    # entry must still be retrievable because the re-put cleared it.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("a", 99, ttl=None)
    time.sleep(0.1)
    assert cache.get("a") == 99


def test_c3_re_put_resets_expiration_timer_with_same_ttl():
    # Spec: "expiration time... superseded by the new arguments." The new
    # expiration is `time.monotonic() at re-put + ttl`, NOT the original
    # expiration. Sleep most of the original TTL, re-put with the same
    # TTL, then sleep past where the ORIGINAL would have expired but
    # before where the NEW expiration lands. Entry must still be there.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.2)       # original expires at T0 + 0.2
    time.sleep(0.15)                  # at T0 + 0.15, still valid
    cache.put("a", 99, ttl=0.2)      # new expires at T0 + 0.35
    time.sleep(0.1)                   # at T0 + 0.25 — past T0+0.2, before T0+0.35
    assert cache.get("a") == 99


# ---------------------------------------------------------------------------
# C4. Capacity eviction. Inserting a new key when `len(cache) == capacity`
# evicts the least-recently-used entry BEFORE the new entry is inserted.
# After the insert, `len(cache) == capacity`.
# ---------------------------------------------------------------------------

def test_c4_capacity_one_second_put_evicts_first():
    # Smallest possible capacity: any second insert must evict the only
    # existing entry. This pins down that capacity is actually enforced
    # rather than being stored and ignored.
    cache = LRUCache(1)
    cache.put("a", 1)
    cache.put("b", 2)

    assert len(cache) == 1
    assert cache.get("b") == 2
    with pytest.raises(KeyError):
        cache.get("a")


def test_c4_no_eviction_below_or_at_capacity():
    # Eviction triggers only when an insert WOULD exceed capacity. Filling
    # exactly to capacity should leave every entry retrievable and len
    # incrementing 1, 2, 3. Catches an off-by-one where eviction triggers
    # at len == capacity rather than len == capacity + 1.
    cache = LRUCache(3)
    cache.put("a", 1)
    assert len(cache) == 1
    cache.put("b", 2)
    assert len(cache) == 2
    cache.put("c", 3)
    assert len(cache) == 3
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_c4_one_over_capacity_evicts_exactly_lru():
    # Filling capacity + 1 items must evict exactly the LRU entry (the
    # oldest untouched one), leaving all others intact and len at capacity.
    # Catches both "evicts too many" and "evicts the wrong one" bugs.
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)  # cache full; 'a' is LRU and must be evicted
    assert len(cache) == 3
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_c4_re_put_on_existing_key_does_not_evict():
    # Re-put on an already-present key is not "inserting a new key" per
    # C4, so no eviction should occur even when the cache is full. After
    # the re-put, every original key must still be retrievable.
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)  # re-put on existing key while full
    assert len(cache) == 3
    assert cache.get("a") == 99
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_c4_expired_entry_does_not_consume_capacity_slot():
    # Cross-clause check (C4 + C7). Once an entry expires, `len` no longer
    # counts it (C7), so an insert into a "full-looking" cache where one
    # entry has expired should NOT evict any live entry. After the put,
    # `len` must equal capacity, not capacity - 1 (which would mean the
    # impl over-evicted by treating the expired slot as an LRU candidate).
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2)
    cache.put("c", 3)
    time.sleep(0.1)               # 'a' expires; len drops to 2 per C7
    assert len(cache) == 2
    cache.put("d", 4)             # should NOT trigger eviction
    assert len(cache) == 3
    assert cache.get("d") == 4


# ---------------------------------------------------------------------------
# C5. Use tracking. Both get(key) and put(key, ...) on an existing key
# count as "uses" that reset that key's LRU position to most-recently-used.
# Inserting a new key does not affect the order of other keys.
# ---------------------------------------------------------------------------

def test_c5_get_promotes_key_to_most_recently_used():
    # After get('a'), 'a' is MRU. The next eviction-triggering put should
    # remove 'b' (the new LRU), not 'a'.
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")             # promote 'a'; LRU order is now b, c, a
    cache.put("d", 4)          # cache full; 'b' is the new LRU and must go
    assert len(cache) == 3
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("a") == 1
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_c5_re_put_promotes_key_to_most_recently_used():
    # Re-put on an existing key counts as a "use" — same promotion as get.
    # After re-put('a'), 'a' is MRU. Eviction should remove 'b', not 'a'.
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)         # re-put on 'a'; promotes 'a' to MRU
    cache.put("d", 4)          # cache full; 'b' is the new LRU
    assert len(cache) == 3
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("a") == 99
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_c5_expiration_preserves_lru_order_of_survivors():
    # When an entry expires, the LRU positions of the remaining live keys
    # must be unchanged. Catches a bug where expiration shuffles or resets
    # the order tracking for surviving entries.
    #
    # Setup live order LRU->MRU: a, c, d, b  (after get('b') promotes b).
    # 'a' expires; live order becomes: c, d, b. Putting 'e' doesn't evict
    # anyone (len=3, capacity=4); order: c, d, b, e. Putting 'f' triggers
    # eviction and the new LRU (c) must be the one removed.
    cache = LRUCache(4)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)
    cache.get("b")             # promote 'b'; live order: a, c, d, b
    time.sleep(0.1)             # 'a' expires; live order: c, d, b
    cache.put("e", 5)           # no eviction needed; order: c, d, b, e
    cache.put("f", 6)           # full; LRU is 'c' and must be evicted
    assert len(cache) == 4
    with pytest.raises(KeyError):
        cache.get("c")
    assert cache.get("d") == 4
    assert cache.get("b") == 2
    assert cache.get("e") == 5
    assert cache.get("f") == 6


def test_c5_eviction_preserves_lru_order_of_survivors():
    # When an entry is evicted, the LRU positions of the remaining keys
    # must be unchanged. Catches a bug where eviction renumbers or resets
    # the order tracking for surviving entries.
    #
    # Setup order LRU->MRU: a, b, c. get('a') promotes a -> b, c, a.
    # put('d') evicts b -> c, a, d. put('e') triggers next eviction; LRU
    # is now 'c' and must be the one removed.
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")             # promote 'a'; order: b, c, a
    cache.put("d", 4)           # evict 'b'; order: c, a, d
    cache.put("e", 5)           # full; LRU is 'c' and must be evicted
    assert len(cache) == 3
    with pytest.raises(KeyError):
        cache.get("c")
    assert cache.get("a") == 1
    assert cache.get("d") == 4
    assert cache.get("e") == 5


# ---------------------------------------------------------------------------
# C6. Expiration on get. get(key) on an expired entry raises KeyError and
# removes the entry from the cache. get(key) on a non-existent key also
# raises KeyError.
# ---------------------------------------------------------------------------

def test_c6_get_on_never_put_key_raises_key_error():
    # The non-existent-key branch of C6, distinct from the expired branch.
    cache = LRUCache(3)
    cache.put("a", 1)
    with pytest.raises(KeyError):
        cache.get("never_put")


def test_c6_repeated_get_on_expired_entry_consistently_raises_key_error():
    # Spec: get on an expired entry "raises KeyError and removes the entry
    # from the cache." A second get on the same key must therefore also
    # raise KeyError (entry was removed). Catches a bug where the first
    # get raises but leaves the entry behind, so a subsequent get could
    # somehow re-find or re-deliver it.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")
    with pytest.raises(KeyError):
        cache.get("a")


def test_c6_re_put_on_expired_entry_yields_only_new_entry():
    # If an entry expires but is never accessed, a re-put on that key must
    # produce exactly one live entry (the new one), not coexist as both an
    # expired ghost and a fresh entry. Verifies via `len == 1` and the new
    # value being returned.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.1)               # 'a' expires without ever being accessed
    cache.put("a", 99)             # re-put on the expired ghost
    assert len(cache) == 1
    assert cache.get("a") == 99


# ---------------------------------------------------------------------------
# C7. Length. len(cache) returns the number of non-expired entries
# currently stored. Entries whose TTL has passed are not counted, even if
# they have not yet been accessed since expiring.
# ---------------------------------------------------------------------------

def test_c7_silently_expired_entries_not_counted_in_len():
    # Multiple entries with TTLs expire without being accessed by any get.
    # `len` must return the count of live entries only — ignoring all the
    # expired ones, even though no get has triggered their cleanup.
    cache = LRUCache(5)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2, ttl=0.05)
    cache.put("c", 3, ttl=0.05)
    cache.put("d", 4)               # no TTL; never expires
    time.sleep(0.1)                  # a, b, c silently expire
    assert len(cache) == 1


def test_c7_len_is_zero_when_all_entries_have_expired():
    # Every entry has expired without being accessed. `len` returns 0,
    # not the original count. Boundary case of the silent-expiry rule.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2, ttl=0.05)
    cache.put("c", 3, ttl=0.05)
    time.sleep(0.1)
    assert len(cache) == 0


# ---------------------------------------------------------------------------
# Cross-cutting edge cases. These follow from spec notes that don't sit in
# a single numbered clause but apply across the public API.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "key",
    [
        pytest.param(42, id="int-key"),
        pytest.param(("a", "b"), id="tuple-key"),
        pytest.param(None, id="none-key"),
    ],
)
def test_keys_can_be_any_hashable_type(key):
    # Spec notes: "Values and keys can be any hashable Python object. The
    # cache does not restrict their type." Round-trip put/get with int,
    # tuple, and None as keys verifies the impl isn't quietly assuming
    # strings.
    cache = LRUCache(3)
    cache.put(key, "value")
    assert cache.get(key) == "value"


def test_negative_ttl_entry_is_born_expired():
    # Spec: "the entry expires at time.monotonic() + ttl." With ttl < 0,
    # the expiration time is in the past, so the entry is expired the
    # instant it's put. `len` must therefore be 0 immediately, and `get`
    # must raise KeyError.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=-1)
    assert len(cache) == 0
    with pytest.raises(KeyError):
        cache.get("a")


