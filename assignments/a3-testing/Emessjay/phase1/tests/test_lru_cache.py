"""Tests for the `lru_cache` module, organized by spec clause.

Spec reference: specs/lru_cache.md (clauses C1..C7).
"""
import time

import pytest

from lru_cache import LRUCache


# -----------------------------------------------------------------------------
# C1. Capacity must be a positive integer
# -----------------------------------------------------------------------------

class TestC1Capacity:
    @pytest.mark.parametrize("cap", [0, -1, -5, -100])
    def test_invalid_capacity_raises(self, cap):
        with pytest.raises(ValueError):
            LRUCache(cap)

    def test_capacity_one_works(self):
        cache = LRUCache(1)
        cache.put("a", 1)
        assert cache.get("a") == 1
        assert len(cache) == 1

    def test_large_capacity_works(self):
        cache = LRUCache(1000)
        for i in range(500):
            cache.put(i, i * 10)
        assert len(cache) == 500
        assert cache.get(0) == 0
        assert cache.get(499) == 4990


# -----------------------------------------------------------------------------
# C2. put inserts/replaces; ttl=None never expires; numeric ttl expires
# -----------------------------------------------------------------------------

class TestC2Put:
    def test_put_then_get_returns_value(self):
        cache = LRUCache(3)
        cache.put("a", 42)
        assert cache.get("a") == 42

    def test_put_with_default_ttl_does_not_expire(self):
        cache = LRUCache(3)
        cache.put("a", 1)  # default ttl=None
        time.sleep(0.05)
        assert cache.get("a") == 1

    def test_put_with_explicit_none_ttl_does_not_expire(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=None)
        time.sleep(0.05)
        assert cache.get("a") == 1

    def test_put_with_short_ttl_expires(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=0.03)
        time.sleep(0.06)
        with pytest.raises(KeyError):
            cache.get("a")

    def test_put_with_long_ttl_does_not_expire_quickly(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=10.0)
        assert cache.get("a") == 1

    def test_put_replaces_value_for_existing_key(self):
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("a", 2)
        assert cache.get("a") == 2

    def test_int_ttl_is_accepted(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=1)  # 1 second
        assert cache.get("a") == 1

    def test_float_ttl_is_accepted(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=0.5)
        assert cache.get("a") == 1


# -----------------------------------------------------------------------------
# C3. Re-put fully replaces value, TTL, and expiration time
# -----------------------------------------------------------------------------

class TestC3TTLReplacement:
    def test_re_put_with_none_clears_expiration(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=0.05)
        cache.put("a", 1, ttl=None)
        time.sleep(0.1)
        assert cache.get("a") == 1

    def test_re_put_with_default_clears_expiration(self):
        # Default arg is None per spec signature.
        cache = LRUCache(3)
        cache.put("a", 1, ttl=0.05)
        cache.put("a", 2)  # no ttl arg → defaults to None
        time.sleep(0.1)
        assert cache.get("a") == 2

    def test_re_put_with_new_ttl_resets_timer(self):
        # Was 50ms in; we reset to 100ms midway. Check we survive past original 50ms.
        cache = LRUCache(3)
        cache.put("a", 1, ttl=0.05)
        time.sleep(0.03)  # 60% through original
        cache.put("a", 1, ttl=0.1)  # reset
        time.sleep(0.04)  # original would be expired (70ms total), new not (40ms)
        assert cache.get("a") == 1

    def test_re_put_with_shorter_ttl_expires_per_new(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=10.0)
        cache.put("a", 1, ttl=0.03)
        time.sleep(0.06)
        with pytest.raises(KeyError):
            cache.get("a")

    def test_re_put_from_no_ttl_to_ttl_sets_expiration(self):
        cache = LRUCache(3)
        cache.put("a", 1)            # no expiration
        cache.put("a", 1, ttl=0.03)  # now expires
        time.sleep(0.06)
        with pytest.raises(KeyError):
            cache.get("a")

    def test_re_put_replaces_value_and_extends_ttl(self):
        cache = LRUCache(3)
        cache.put("a", "old", ttl=0.05)
        cache.put("a", "new", ttl=10.0)
        time.sleep(0.06)  # past old ttl
        assert cache.get("a") == "new"


# -----------------------------------------------------------------------------
# C4. Capacity eviction: new key on full cache evicts LRU
# -----------------------------------------------------------------------------

class TestC4Eviction:
    def test_eviction_removes_lru(self):
        cache = LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # evicts "a"
        with pytest.raises(KeyError):
            cache.get("a")
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_len_stays_at_capacity_after_many_inserts(self):
        cache = LRUCache(3)
        for i in range(10):
            cache.put(i, i)
        assert len(cache) == 3

    def test_capacity_one_evicts_immediately(self):
        cache = LRUCache(1)
        cache.put("a", 1)
        cache.put("b", 2)
        with pytest.raises(KeyError):
            cache.get("a")
        assert cache.get("b") == 2
        assert len(cache) == 1

    def test_re_put_existing_key_does_not_evict(self):
        # Re-put is not a "new key" insert per C4.
        cache = LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 100)  # re-put, no eviction
        assert cache.get("a") == 100
        assert cache.get("b") == 2
        assert len(cache) == 2

    def test_filling_to_capacity_does_not_evict(self):
        # Going up to cap shouldn't evict anyone.
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") == 3


# -----------------------------------------------------------------------------
# C5. get and put on existing key both count as uses; new put doesn't reorder
# -----------------------------------------------------------------------------

class TestC5UseTracking:
    def test_get_promotes_key_to_mru(self):
        # cap=3: order after a,b,c is: c, b, a (MRU..LRU).
        # get("a") → order: a, c, b. put("d") evicts b.
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.get("a")
        cache.put("d", 4)
        with pytest.raises(KeyError):
            cache.get("b")
        # a, c, d still present
        assert cache.get("a") == 1
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_re_put_promotes_key_to_mru(self):
        # cap=3: a,b,c → put("a", 100) → order: a, c, b. put("d") evicts b.
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("a", 100)
        cache.put("d", 4)
        with pytest.raises(KeyError):
            cache.get("b")
        assert cache.get("a") == 100
        assert cache.get("c") == 3

    def test_inserting_new_key_does_not_reorder_existing(self):
        # cap=4: a,b,c (cache not full, no eviction).
        # put d (still cap=3 → 4, no eviction needed). order should be d, c, b, a.
        # put e (now full → evict a, NOT b/c).
        cache = LRUCache(4)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("d", 4)
        cache.put("e", 5)  # evict a
        with pytest.raises(KeyError):
            cache.get("a")
        # b, c, d, e still present
        assert cache.get("b") == 2

    def test_long_lru_chain(self):
        # Stress-test the LRU ordering through gets and re-puts.
        cache = LRUCache(3)
        cache.put("a", 1)         # order: a
        cache.put("b", 2)         # order: b, a
        cache.put("c", 3)         # order: c, b, a
        cache.get("a")            # order: a, c, b
        cache.get("b")            # order: b, a, c
        cache.put("d", 4)         # full → evict c. order: d, b, a
        with pytest.raises(KeyError):
            cache.get("c")
        cache.put("a", 99)        # promote a. order: a, d, b
        cache.put("e", 5)         # evict b. order: e, a, d
        with pytest.raises(KeyError):
            cache.get("b")
        assert cache.get("a") == 99
        assert cache.get("d") == 4
        assert cache.get("e") == 5


# -----------------------------------------------------------------------------
# C6. Expiration on get
# -----------------------------------------------------------------------------

class TestC6Expiration:
    def test_get_on_expired_raises_keyerror(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=0.03)
        time.sleep(0.06)
        with pytest.raises(KeyError):
            cache.get("a")

    def test_get_on_missing_raises_keyerror(self):
        cache = LRUCache(3)
        with pytest.raises(KeyError):
            cache.get("nope")

    def test_get_on_expired_removes_entry(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=0.03)
        time.sleep(0.06)
        with pytest.raises(KeyError):
            cache.get("a")
        # second get is also a KeyError; len reflects removal.
        with pytest.raises(KeyError):
            cache.get("a")
        assert len(cache) == 0


# -----------------------------------------------------------------------------
# C7. Length excludes expired entries even before they're accessed
# -----------------------------------------------------------------------------

class TestC7Length:
    def test_empty_cache_len_is_zero(self):
        assert len(LRUCache(5)) == 0

    def test_len_reflects_inserts(self):
        cache = LRUCache(5)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        assert len(cache) == 3

    def test_len_excludes_expired_without_access(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=0.03)
        cache.put("b", 2)  # no ttl
        time.sleep(0.06)
        # a expired, b not. len must be 1 even though we haven't called get().
        assert len(cache) == 1

    def test_len_excludes_all_expired(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=0.03)
        cache.put("b", 2, ttl=0.03)
        cache.put("c", 3, ttl=0.03)
        time.sleep(0.06)
        assert len(cache) == 0

    def test_len_after_eviction(self):
        cache = LRUCache(2)
        for i in range(10):
            cache.put(i, i)
        assert len(cache) == 2

    def test_len_after_re_put(self):
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("a", 2)
        cache.put("a", 3)
        assert len(cache) == 1


# =============================================================================
# Adversarial probes — spec implications, edge cases, "wait, what about..."
# =============================================================================

class TestEvictionAfterPromotion:
    """C5 + C4 interact: promotions affect what gets evicted."""

    def test_get_then_eviction_picks_correct_victim(self):
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.get("a")  # a → MRU; LRU is now b
        cache.put("d", 4)  # evict b
        with pytest.raises(KeyError):
            cache.get("b")
        # a, c, d remain
        assert {cache.get("a"), cache.get("c"), cache.get("d")} == {1, 3, 4}

    def test_put_then_eviction_picks_correct_victim(self):
        # Re-put promotes; then a new key evicts the one that's now LRU.
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("a", 100)  # a → MRU; LRU is now b
        cache.put("d", 4)
        with pytest.raises(KeyError):
            cache.get("b")
        assert cache.get("a") == 100

    def test_get_on_missing_does_not_disturb_lru_order(self):
        # KeyError on a missing key shouldn't reorder the live ones.
        cache = LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)  # order: b, a
        with pytest.raises(KeyError):
            cache.get("nonexistent")
        # order should still be b, a → put("c") evicts a, NOT b
        cache.put("c", 3)
        with pytest.raises(KeyError):
            cache.get("a")
        assert cache.get("b") == 2

    def test_get_on_expired_does_not_count_as_use(self):
        # An expired-and-removed entry can't have its "use" promote it
        # (it's gone). Verify by confirming len decreases and re-put works.
        cache = LRUCache(2)
        cache.put("a", 1, ttl=0.03)
        cache.put("b", 2)
        time.sleep(0.06)
        with pytest.raises(KeyError):
            cache.get("a")
        # a is gone; cache has just b.
        assert len(cache) == 1
        # Now we can insert a new key without eviction.
        cache.put("c", 3)
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert len(cache) == 2


class TestExpirationFreesSpace:
    """An expired entry doesn't count toward len (C7); inserting after
    expiration shouldn't need to evict a live entry."""

    def test_expired_entries_do_not_block_new_insert(self):
        cache = LRUCache(2)
        cache.put("a", 1, ttl=0.03)
        cache.put("b", 2, ttl=0.03)
        time.sleep(0.06)
        # Both expired; len=0.
        cache.put("c", 3)
        assert cache.get("c") == 3

    def test_re_put_expired_key_creates_fresh_entry(self):
        cache = LRUCache(2)
        cache.put("a", 1, ttl=0.03)
        time.sleep(0.06)
        cache.put("a", 100)
        assert cache.get("a") == 100
        assert len(cache) == 1


class TestReplaceVsInsert:
    """C3 + C4: re-put never triggers eviction, even at full capacity."""

    def test_re_put_at_full_capacity_keeps_all_keys(self):
        cache = LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 99)   # re-put, NOT insert
        cache.put("a", 999)  # re-put again
        assert cache.get("a") == 999
        assert cache.get("b") == 2
        assert len(cache) == 2

    def test_re_put_does_not_treat_self_as_lru_victim(self):
        # If a buggy impl evicted the key being re-put, this would explode.
        cache = LRUCache(1)
        cache.put("a", 1)
        cache.put("a", 2)
        assert cache.get("a") == 2
        assert len(cache) == 1


class TestTTLPrecision:
    """The spec allows int or float ttl. Pin a few non-trivial cases."""

    def test_separate_ttls_per_entry(self):
        cache = LRUCache(3)
        cache.put("short", "s", ttl=0.03)
        cache.put("long", "l", ttl=10.0)
        time.sleep(0.06)
        with pytest.raises(KeyError):
            cache.get("short")
        assert cache.get("long") == "l"

    def test_ttl_does_not_affect_other_entries(self):
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2, ttl=0.03)
        cache.put("c", 3)
        time.sleep(0.06)
        assert cache.get("a") == 1
        assert cache.get("c") == 3
        with pytest.raises(KeyError):
            cache.get("b")

    def test_long_ttl_survives_many_operations(self):
        cache = LRUCache(5)
        cache.put("a", 1, ttl=10.0)
        for i in range(100):
            cache.put(f"k{i}", i)
            cache.put(f"k{i}", i + 1)  # re-put churn
        # "a" got evicted by capacity (cap=5, lots of new keys), not by TTL.
        # Pin: TTL alone wouldn't expire it.
        with pytest.raises(KeyError):
            cache.get("a")  # this is OK: eviction, not TTL

    def test_zero_capacity_eviction_is_consistent(self):
        # Smallest meaningful capacity — every put evicts.
        cache = LRUCache(1)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("d", 4)
        assert len(cache) == 1
        assert cache.get("d") == 4


class TestKeyAndValueGenerality:
    """C-notes: 'Values and keys can be any hashable Python object.'"""

    def test_int_keys(self):
        cache = LRUCache(3)
        cache.put(1, "a")
        cache.put(2, "b")
        assert cache.get(1) == "a"

    def test_tuple_keys(self):
        cache = LRUCache(3)
        cache.put(("x", 1), "value")
        assert cache.get(("x", 1)) == "value"

    def test_none_value_is_returned_not_treated_as_missing(self):
        # If the impl confuses None-value with missing, get would raise.
        cache = LRUCache(3)
        cache.put("a", None)
        assert cache.get("a") is None

    def test_complex_value(self):
        cache = LRUCache(3)
        cache.put("a", {"nested": [1, 2, 3]})
        assert cache.get("a") == {"nested": [1, 2, 3]}


class TestExpirationDuringPromotion:
    """Edge: getting a not-yet-expired entry should not trigger expiration."""

    def test_get_close_to_but_before_expiration_works(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=0.2)  # 200ms
        time.sleep(0.05)            # 50ms in, still 150ms left
        assert cache.get("a") == 1

    def test_get_promotes_then_expires_per_original_ttl(self):
        # get is a "use" that resets LRU order, but does NOT reset TTL.
        # Spec C2 ties expiration to put time + ttl, not last-get time.
        cache = LRUCache(3)
        cache.put("a", 1, ttl=0.05)
        time.sleep(0.03)
        cache.get("a")           # use, but does not refresh expiration
        time.sleep(0.04)         # total ~70ms past put → expired
        with pytest.raises(KeyError):
            cache.get("a")


class TestLenAtBoundary:
    def test_len_decreases_after_get_expired(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=0.03)
        cache.put("b", 2)
        time.sleep(0.06)
        with pytest.raises(KeyError):
            cache.get("a")
        assert len(cache) == 1

    def test_len_consistent_across_calls(self):
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        # Call len multiple times; must be stable.
        assert len(cache) == len(cache) == len(cache) == 2

    def test_len_does_not_count_expired_after_re_put_others(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=0.03)
        cache.put("b", 2)
        time.sleep(0.06)
        cache.put("b", 22)  # re-put unrelated key
        # a is still expired
        assert len(cache) == 1


# =============================================================================
# Deeper adversarial probes — pinpoint LRU semantics, TTL timing, capacity
# boundary, and replace-vs-insert distinctions
# =============================================================================


class TestExactLRUSequences:
    """Multi-step sequences where the wrong eviction victim signals a
    use-tracking or insertion-ordering bug."""

    def test_eviction_is_lru_not_fifo(self):
        # FIFO would evict the first-inserted; LRU evicts based on last use.
        cache = LRUCache(3)
        cache.put("first", 1)
        cache.put("second", 2)
        cache.put("third", 3)
        cache.get("first")          # promote "first" to MRU
        cache.put("fourth", 4)      # FIFO would evict "first"; LRU evicts "second"
        with pytest.raises(KeyError):
            cache.get("second")
        assert cache.get("first") == 1
        assert cache.get("third") == 3
        assert cache.get("fourth") == 4

    def test_eviction_is_lru_not_mru(self):
        # MRU eviction would evict the just-inserted key.
        cache = LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)  # MRU = b, LRU = a
        cache.put("c", 3)  # spec: evict a (LRU). Buggy MRU: would evict b.
        with pytest.raises(KeyError):
            cache.get("a")
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_re_put_mru_does_not_promote_anyone_else(self):
        # Re-put on an already-MRU key shouldn't change the order of others.
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)              # order: c b a
        cache.put("c", 30)             # c already MRU; order unchanged
        cache.put("d", 4)              # full → evict a
        with pytest.raises(KeyError):
            cache.get("a")
        assert cache.get("b") == 2
        assert cache.get("c") == 30
        assert cache.get("d") == 4

    def test_repeat_get_mru_keeps_lru_order(self):
        # Calling get on the MRU key 100 times must not promote anyone else.
        cache = LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        for _ in range(100):
            cache.get("b")
        cache.put("c", 3)              # evict a (still LRU)
        with pytest.raises(KeyError):
            cache.get("a")
        assert cache.get("b") == 2

    def test_alternating_get_put_chain(self):
        cache = LRUCache(2)
        cache.put("a", 1)         # [a]
        cache.put("b", 2)         # [b, a]
        cache.get("a")            # [a, b]
        cache.put("c", 3)         # full → evict b. [c, a]
        cache.get("a")            # [a, c]
        cache.put("d", 4)         # full → evict c. [d, a]
        cache.put("a", 100)       # re-put. [a, d]
        cache.put("e", 5)         # full → evict d. [e, a]
        with pytest.raises(KeyError):
            cache.get("d")
        with pytest.raises(KeyError):
            cache.get("c")
        assert cache.get("a") == 100
        assert cache.get("e") == 5
        assert len(cache) == 2

    def test_each_use_promotes_one_step(self):
        # cap=4 sequence with two gets between four inserts.
        cache = LRUCache(4)
        for k, v in [("a", 1), ("b", 2), ("c", 3), ("d", 4)]:
            cache.put(k, v)
        # order: d c b a
        cache.get("a")             # → [a, d, c, b]
        cache.get("b")             # → [b, a, d, c]
        cache.put("e", 5)          # full → evict c
        with pytest.raises(KeyError):
            cache.get("c")
        # a, b, d, e remain
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("d") == 4
        assert cache.get("e") == 5


class TestTTLTimingBoundary:
    """C2: 'expires at time.monotonic() + ttl'. Pin pre-expiry vs post-expiry."""

    def test_get_well_before_expiry_returns_value(self):
        cache = LRUCache(2)
        cache.put("a", 1, ttl=0.5)
        time.sleep(0.05)               # 10% in
        assert cache.get("a") == 1

    def test_get_well_after_expiry_raises(self):
        cache = LRUCache(2)
        cache.put("a", 1, ttl=0.05)
        time.sleep(0.15)               # 3x past
        with pytest.raises(KeyError):
            cache.get("a")

    def test_get_does_not_extend_ttl(self):
        # get is a "use" but does NOT refresh expiration. TTL anchors to put time.
        cache = LRUCache(2)
        cache.put("a", 1, ttl=0.1)
        time.sleep(0.05)               # 50% through
        cache.get("a")                 # use, but does not reset clock
        time.sleep(0.08)               # total ~130ms past put → expired
        with pytest.raises(KeyError):
            cache.get("a")

    def test_re_put_resets_ttl_clock(self):
        cache = LRUCache(2)
        cache.put("a", 1, ttl=0.05)
        time.sleep(0.03)               # 60% through original
        cache.put("a", 2, ttl=0.15)    # reset to 150ms timer
        time.sleep(0.08)               # original would be 110ms past (expired);
                                       # new is 80ms in (alive)
        assert cache.get("a") == 2

    def test_per_entry_ttl_independent(self):
        cache = LRUCache(3)
        cache.put("short", "s", ttl=0.05)
        cache.put("med", "m", ttl=0.3)
        cache.put("long", "l", ttl=10.0)
        time.sleep(0.1)
        with pytest.raises(KeyError):
            cache.get("short")
        # med still alive (300ms TTL, 100ms elapsed)
        assert cache.get("med") == "m"
        assert cache.get("long") == "l"

    def test_re_put_with_none_after_almost_expired(self):
        # Almost expired → re-put with None → must survive past original TTL.
        cache = LRUCache(2)
        cache.put("a", 1, ttl=0.05)
        time.sleep(0.04)               # 80% through
        cache.put("a", 2)              # default ttl=None → never expires
        time.sleep(0.05)               # past original (90ms total)
        assert cache.get("a") == 2


class TestCapacityBoundary:
    """C4: eviction triggers when len(cache) == capacity. Off-by-one
    territory."""

    def test_filling_exactly_to_capacity_no_eviction(self):
        cache = LRUCache(5)
        for i in range(5):
            cache.put(f"k{i}", i)
        assert len(cache) == 5
        # Every key still retrievable.
        for i in range(5):
            assert cache.get(f"k{i}") == i

    def test_one_past_capacity_evicts_exactly_one(self):
        cache = LRUCache(5)
        for i in range(6):
            cache.put(f"k{i}", i)
        assert len(cache) == 5
        # k0 was LRU before any gets, so k0 should be evicted.
        with pytest.raises(KeyError):
            cache.get("k0")
        for i in range(1, 6):
            assert cache.get(f"k{i}") == i

    def test_far_past_capacity_keeps_only_recent(self):
        cache = LRUCache(3)
        for i in range(100):
            cache.put(i, i * 10)
        assert len(cache) == 3
        # Last 3 inserted should remain.
        for i in range(97):
            with pytest.raises(KeyError):
                cache.get(i)
        for i in range(97, 100):
            assert cache.get(i) == i * 10


class TestErrorContract:
    """C1, C6: exact error TYPE matters — not just 'something raised'."""

    def test_get_missing_raises_keyerror_specifically(self):
        cache = LRUCache(2)
        # pytest.raises(KeyError) accepts only KeyError (and subclasses).
        # If impl returns None or raises a different exception, fails.
        with pytest.raises(KeyError):
            cache.get("nope")

    def test_get_expired_raises_keyerror_specifically(self):
        cache = LRUCache(2)
        cache.put("a", 1, ttl=0.03)
        time.sleep(0.06)
        with pytest.raises(KeyError):
            cache.get("a")

    def test_zero_capacity_raises_valueerror_specifically(self):
        with pytest.raises(ValueError):
            LRUCache(0)

    def test_get_missing_does_not_silently_return_none(self):
        # An impl that returns None on miss would not raise — assert that
        # the call raises rather than returning a sentinel.
        cache = LRUCache(2)
        try:
            value = cache.get("missing")
        except KeyError:
            return
        pytest.fail(f"Expected KeyError, got returned value: {value!r}")


class TestRePutAtCapacityNoEviction:
    """C3 + C4: re-put never causes eviction, even at capacity 1."""

    def test_re_put_at_cap_one_keeps_only_key(self):
        cache = LRUCache(1)
        cache.put("a", 1)
        cache.put("a", 2)
        cache.put("a", 3)
        assert cache.get("a") == 3
        assert len(cache) == 1

    def test_re_put_does_not_double_count_in_len(self):
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("a", 2)
        cache.put("a", 3)
        assert len(cache) == 1

    def test_repeated_re_put_full_cache_no_evictions(self):
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        # Re-put each key 5 times — no key should ever get evicted.
        for _ in range(5):
            for k in ["a", "b", "c"]:
                cache.put(k, ord(k))
        assert len(cache) == 3
        assert cache.get("a") == ord("a")
        assert cache.get("b") == ord("b")
        assert cache.get("c") == ord("c")


class TestExpiredEvictionInteraction:
    """C7 + C4: expired entries don't count toward len, so a put that
    finds the cache 'full of expired entries' shouldn't evict live ones."""

    def test_expired_does_not_force_eviction_of_live_when_under_capacity(self):
        cache = LRUCache(2)
        cache.put("expired", "x", ttl=0.03)
        cache.put("live", "v")
        time.sleep(0.06)
        # 'expired' is expired; per C7, len excludes it.
        assert len(cache) == 1
        # New put: cache is not "full" by spec, no eviction needed.
        cache.put("new", "n")
        assert cache.get("live") == "v"
        assert cache.get("new") == "n"

    def test_all_expired_then_burst_of_inserts(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=0.03)
        cache.put("b", 2, ttl=0.03)
        cache.put("c", 3, ttl=0.03)
        time.sleep(0.06)
        assert len(cache) == 0
        cache.put("x", 100)
        cache.put("y", 200)
        cache.put("z", 300)
        assert cache.get("x") == 100
        assert cache.get("y") == 200
        assert cache.get("z") == 300
        assert len(cache) == 3


class TestValueIntegrity:
    """get must return what was last put — never stale, never wrapped."""

    def test_value_is_what_was_put_no_wrapping(self):
        # If the impl stores a wrapper (e.g., (value, expiry)), and
        # forgets to unpack on get, this catches it.
        cache = LRUCache(3)
        cache.put("a", "raw_string")
        assert cache.get("a") == "raw_string"

    def test_value_after_re_put_is_latest(self):
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("a", 2)
        cache.put("a", 3)
        assert cache.get("a") == 3

    def test_distinct_values_per_key(self):
        cache = LRUCache(3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_get_does_not_consume_value(self):
        # get is not "pop" — repeated gets return the same value.
        cache = LRUCache(2)
        cache.put("a", 42)
        for _ in range(10):
            assert cache.get("a") == 42

    def test_falsy_values_round_trip(self):
        # Values like 0, "", [], None must all round-trip without being
        # interpreted as "missing".
        cache = LRUCache(5)
        cache.put("zero", 0)
        cache.put("empty_str", "")
        cache.put("empty_list", [])
        cache.put("none", None)
        cache.put("false", False)
        assert cache.get("zero") == 0
        assert cache.get("empty_str") == ""
        assert cache.get("empty_list") == []
        assert cache.get("none") is None
        assert cache.get("false") is False


class TestFreshInsertAfterExpiredAccess:
    """Once an expired entry's get raises, the slot should be freed for a
    fresh insert without disrupting other live entries."""

    def test_get_expired_then_insert_no_eviction_of_live(self):
        cache = LRUCache(2)
        cache.put("a", 1, ttl=0.03)
        cache.put("b", 2)
        time.sleep(0.06)
        with pytest.raises(KeyError):
            cache.get("a")  # removes a
        cache.put("c", 3)   # should fit without evicting b
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        with pytest.raises(KeyError):
            cache.get("a")
        assert len(cache) == 2

    def test_re_put_expired_creates_fresh_entry(self):
        cache = LRUCache(2)
        cache.put("a", 1, ttl=0.03)
        time.sleep(0.06)
        cache.put("a", 100)   # re-put after expiration
        time.sleep(0.05)
        assert cache.get("a") == 100  # the fresh put has no TTL, alive forever


class TestSequenceInvariants:
    """Properties that must hold across any sequence of operations."""

    def test_len_never_exceeds_capacity(self):
        cache = LRUCache(3)
        for i in range(50):
            cache.put(i, i)
            assert len(cache) <= 3

    def test_len_never_negative(self):
        cache = LRUCache(3)
        for i in range(20):
            cache.put(i, i)
            assert len(cache) >= 0
        time.sleep(0.01)
        for i in range(10):
            try:
                cache.get(i)
            except KeyError:
                pass
            assert len(cache) >= 0

    def test_get_after_put_same_session_returns_value(self):
        cache = LRUCache(3)
        for i in range(3):
            cache.put(i, i * 10)
        for i in range(3):
            assert cache.get(i) == i * 10

    def test_idempotent_len_call(self):
        cache = LRUCache(3)
        cache.put("a", 1, ttl=10.0)
        cache.put("b", 2)
        # Calling len repeatedly must not change the cache.
        before = (len(cache), len(cache), len(cache))
        cache.get("a")
        cache.get("b")
        after = (len(cache), len(cache), len(cache))
        assert before == after == (2, 2, 2)
