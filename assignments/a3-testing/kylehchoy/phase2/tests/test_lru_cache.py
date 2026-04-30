"""Phase 1 tests for `lru_cache` module.

Tests are organized clause-by-clause against starter/assignment3/specs/lru_cache.md.
Each test name encodes the clause it pins down (e.g. test_c4_eviction_before_insert).

TTL discipline: per-test waits use real time.sleep with tens-of-ms scale.
TTL = 0.10s, alive-check at sleep(0.02), expired-check at sleep(0.15).
"""
import time
import pytest

from lru_cache import LRUCache


class _CollidingKey:
    """Hashable key with controlled equality and intentional hash collision."""

    def __init__(self, label):
        self.label = label

    def __hash__(self):
        return 1

    def __eq__(self, other):
        return isinstance(other, _CollidingKey) and self.label == other.label


# ---------------------------------------------------------------------------
# C1. Capacity validation.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_cap", [0, -1, -5, -100])
def test_c1_nonpositive_capacity_raises_valueerror(bad_cap):
    with pytest.raises(ValueError):
        LRUCache(bad_cap)


@pytest.mark.parametrize("good_cap", [1, 2, 10, 1000])
def test_c1_positive_capacity_accepted(good_cap):
    cache = LRUCache(good_cap)
    assert len(cache) == 0


# ---------------------------------------------------------------------------
# C2. put inserts or replaces; ttl semantics.
# ---------------------------------------------------------------------------

def test_c2_put_then_get_returns_value():
    cache = LRUCache(3)
    cache.put("a", 1)
    assert cache.get("a") == 1


def test_c2_put_replaces_value():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("a", 2)
    assert cache.get("a") == 2


def test_c2_ttl_none_never_expires():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=None)
    time.sleep(0.05)
    assert cache.get("a") == 1


def test_c2_ttl_numeric_expires_after_window():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.10)
    time.sleep(0.15)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c2_ttl_alive_within_window():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.10)
    time.sleep(0.02)
    assert cache.get("a") == 1


# ---------------------------------------------------------------------------
# C3. Re-put fully replaces the entry (value, ttl, expiration).
# ---------------------------------------------------------------------------

def test_c3_reput_replaces_value():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("a", 999)
    assert cache.get("a") == 999


def test_c3_reput_with_longer_ttl_supersedes():
    # Old TTL would have expired; new TTL is fresh and longer.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.02)                       # still alive under old ttl
    cache.put("a", 2, ttl=0.20)            # new ttl supersedes
    time.sleep(0.08)                       # past old ttl, before new ttl
    assert cache.get("a") == 2


def test_c3_reput_with_ttl_none_clears_expiration():
    # Spec C3 calls this out explicitly: ttl=None on a re-put clears expiration.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("a", 2, ttl=None)            # clears the expiration
    time.sleep(0.10)                       # well past original ttl
    assert cache.get("a") == 2


# ---------------------------------------------------------------------------
# C4. Capacity eviction. LRU is evicted BEFORE new insert.
# ---------------------------------------------------------------------------

def test_c4_eviction_at_capacity_removes_lru():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)                      # "a" is LRU, gets evicted
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_c4_len_stays_at_capacity_after_evicting_insert():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)
    assert len(cache) == 3


def test_c4_eviction_before_insert_so_new_key_present():
    # Phrased as a sequence: when full, the eviction happens first, then the
    # new key is inserted. So after the put, the new key is definitely there.
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)                      # evicts "a", inserts "c"
    assert cache.get("c") == 3
    assert cache.get("b") == 2
    with pytest.raises(KeyError):
        cache.get("a")


# ---------------------------------------------------------------------------
# C5. Use tracking. get and put-on-existing both promote to MRU.
# ---------------------------------------------------------------------------

def test_c5_get_promotes_to_mru():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")                         # promotes "a"; "b" is now LRU
    cache.put("d", 4)                      # evicts "b"
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("a") == 1
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_c5_put_on_existing_promotes_to_mru():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 11)                     # promotes "a"; "b" is now LRU
    cache.put("d", 4)                      # evicts "b"
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("a") == 11


def test_c5_inserting_new_key_does_not_reorder_others():
    # When we insert a brand-new key into a non-full cache, the LRU position
    # of OTHER keys must not change. Insert the new key, then fill to capacity,
    # then trigger an eviction — the original LRU should be the one evicted.
    cache = LRUCache(4)
    cache.put("a", 1)                      # oldest
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)                      # cache now full; "a" is LRU
    cache.put("e", 5)                      # evicts "a"
    with pytest.raises(KeyError):
        cache.get("a")
    # b/c/d/e all present
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.get("d") == 4
    assert cache.get("e") == 5


# ---------------------------------------------------------------------------
# C6. KeyError on missing or expired; expired entries are removed.
# ---------------------------------------------------------------------------

def test_c6_get_missing_raises_keyerror():
    cache = LRUCache(3)
    with pytest.raises(KeyError):
        cache.get("never_set")


def test_c6_get_expired_raises_keyerror():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.10)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c6_get_expired_removes_entry():
    # After get-on-expired, the entry is gone — len reflects it, and a
    # subsequent re-put behaves like an insert (occupies a fresh slot).
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.10)
    with pytest.raises(KeyError):
        cache.get("a")
    assert len(cache) == 0


# ---------------------------------------------------------------------------
# C7. len counts non-expired entries only, without requiring a prior get.
# ---------------------------------------------------------------------------

def test_c7_len_counts_live_entries():
    cache = LRUCache(5)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert len(cache) == 3


def test_c7_len_excludes_expired_without_explicit_get():
    # The clause is specific: entries whose TTL has passed are NOT counted,
    # even if no get has been called to surface the expiration.
    cache = LRUCache(5)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2)                      # no ttl
    cache.put("c", 3, ttl=0.05)
    time.sleep(0.10)
    assert len(cache) == 1                 # only "b" survives


def test_c7_len_zero_on_empty():
    cache = LRUCache(3)
    assert len(cache) == 0


# ===========================================================================
# Implication pass — spec-implied edge cases.
# ===========================================================================

# Boundary lens -------------------------------------------------------------

def test_capacity_one_single_slot_churn():
    # cap=1 is the smallest valid cache; every put should evict the prior key.
    cache = LRUCache(1)
    cache.put("a", 1)
    cache.put("b", 2)                         # evicts "a"
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    cache.put("c", 3)                         # evicts "b"
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("c") == 3
    assert len(cache) == 1


# Absence lens --------------------------------------------------------------

def test_get_on_expired_does_not_promote_other_live_entries():
    # If get-on-expired accidentally reorders other entries, the LRU after
    # this sequence would change. Construct: a (LRU), b, c with short TTL (MRU).
    # After c expires, a should still be LRU; an insert should evict a.
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3, ttl=0.05)
    time.sleep(0.10)
    with pytest.raises(KeyError):
        cache.get("c")                        # KeyError + remove c
    cache.put("d", 4)                         # len was 2 before; now 3 — no eviction needed
    # But to lock in LRU order on a/b: insert one more.
    cache.put("e", 5)                         # full now; should evict "a"
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert cache.get("d") == 4
    assert cache.get("e") == 5


def test_len_progressively_decreases_as_entries_expire():
    # Multiple entries with staggered TTLs — len reflects expirations without
    # any get calls.
    cache = LRUCache(5)
    cache.put("short1", 1, ttl=0.05)
    cache.put("short2", 2, ttl=0.05)
    cache.put("forever", 3)
    assert len(cache) == 3
    time.sleep(0.10)
    assert len(cache) == 1                    # only "forever" survives


# Interaction lens ----------------------------------------------------------

def test_reput_on_already_expired_key_works_as_fresh_entry():
    # Spec C3 says re-put fully replaces value, ttl, expiration. An expired
    # entry is logically gone (per C7's len semantics); a put on that key
    # should produce a live entry with the new ttl.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.10)                          # "a" is expired
    cache.put("a", 99, ttl=0.50)              # fresh ttl on the same key
    assert cache.get("a") == 99               # alive under new ttl
    assert len(cache) == 1


def test_get_then_expire_sequence():
    # Live, accessed, then aged out — all transitions on one key.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.10)
    time.sleep(0.02)
    assert cache.get("a") == 1                # alive
    time.sleep(0.15)                          # past 0.10s window
    with pytest.raises(KeyError):
        cache.get("a")


def test_get_promotes_lru_but_does_not_renew_ttl():
    # C5 says get refreshes LRU position; C2 says expiration is fixed at
    # put-time. This catches a sliding-TTL implementation that renews on get.
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.20)
    cache.put("b", 2)

    time.sleep(0.08)
    assert cache.get("a") == 1  # promotes "a", but should not extend ttl

    cache.put("c", 3)  # get promotion means "b" is the LRU victim
    with pytest.raises(KeyError):
        cache.get("b")

    time.sleep(0.16)  # beyond original a-expiration; before sliding expiry
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("c") == 3


def test_c2_ttl_zero_expires_essentially_immediately():
    # Spec C2: "If ttl is a number (int or float)" — 0 is a number.
    # Expiration is at monotonic() + 0; any subsequent get sees now > expiry.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0)
    time.sleep(0.01)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c3_reput_with_shorter_ttl_supersedes():
    # Inverse of test_c3_reput_with_longer_ttl_supersedes: original TTL would
    # still be alive, but the re-put's shorter TTL takes over.
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.50)               # would survive long
    cache.put("a", 2, ttl=0.05)               # but new shorter TTL supersedes
    time.sleep(0.10)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c6_get_on_expired_only_removes_the_expired_entry():
    # When get raises KeyError on an expired entry, neighbors must remain.
    # C6 says the expired entry is removed; C7 says len counts non-expired.
    # Implication: only the expired one goes away.
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2, ttl=0.05)
    cache.put("c", 3)
    time.sleep(0.10)
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("a") == 1
    assert cache.get("c") == 3


def test_c5_promotion_order_across_multiple_gets():
    # Sequence of gets shifts the LRU-MRU ordering predictably.
    # Start: a(LRU), b, c(MRU). get a → b(LRU), c, a(MRU). get b → c(LRU), a, b(MRU).
    # Insert d → evicts c.
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")
    cache.get("b")
    cache.put("d", 4)                         # evicts "c"
    with pytest.raises(KeyError):
        cache.get("c")
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("d") == 4


def test_negative_ttl_expires_immediately():
    # C2 implies expiration at monotonic() + ttl; negative ttl means expired now.
    cache = LRUCache(2)
    cache.put("a", 1, ttl=-0.01)
    with pytest.raises(KeyError):
        cache.get("a")


def test_insert_when_one_entry_already_expired_keeps_live_entry():
    # C7 says expired entries are not counted by len(); inserting with an expired
    # resident should not evict a live key.
    cache = LRUCache(2)
    cache.put("old", 1, ttl=0.05)
    cache.put("live", 2)
    time.sleep(0.10)  # "old" now expired
    cache.put("new", 3)

    assert cache.get("live") == 2
    assert cache.get("new") == 3
    with pytest.raises(KeyError):
        cache.get("old")


def test_hashable_non_string_keys_round_trip():
    cache = LRUCache(3)
    tuple_key = ("user", 42)
    int_key = 7
    cache.put(tuple_key, "tuple-value")
    cache.put(int_key, "int-value")
    assert cache.get(tuple_key) == "tuple-value"
    assert cache.get(int_key) == "int-value"


def test_hash_collision_keys_remain_distinct():
    # "Any hashable" means full Python key semantics, not using hash(key)
    # alone. These two keys collide but are not equal.
    cache = LRUCache(3)
    left = _CollidingKey("left")
    right = _CollidingKey("right")

    cache.put(left, "left-value")
    cache.put(right, "right-value")

    assert cache.get(left) == "left-value"
    assert cache.get(right) == "right-value"


def test_equal_distinct_key_objects_address_same_entry_and_promote():
    cache = LRUCache(2)
    first = _CollidingKey("same")
    equivalent = _CollidingKey("same")

    cache.put(first, "old")
    cache.put("other", "value")
    cache.put(equivalent, "new")  # replaces/promotes the existing equal key
    cache.put("third", "value")   # should evict "other", not the equal key

    assert cache.get(first) == "new"
    assert cache.get(equivalent) == "new"
    with pytest.raises(KeyError):
        cache.get("other")


def test_object_value_round_trips_without_coercion():
    cache = LRUCache(2)
    payload = {"name": "kyle", "scores": [1, 2, 3]}
    cache.put("obj", payload)
    assert cache.get("obj") is payload


def test_expired_entry_not_chosen_as_live_eviction_competitor():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2)
    time.sleep(0.10)
    cache.put("c", 3)
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    with pytest.raises(KeyError):
        cache.get("a")


def test_len_does_not_affect_lru_order():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    _ = len(cache)
    cache.put("c", 3)
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_len_cleanup_of_expired_entry_does_not_reorder_live_entries():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("expired", 2, ttl=0.05)
    cache.put("c", 3)
    time.sleep(0.10)

    assert len(cache) == 2
    cache.put("d", 4)  # fills the expired slot; no live eviction
    cache.put("e", 5)  # now evicts live LRU "a"

    with pytest.raises(KeyError):
        cache.get("a")
    with pytest.raises(KeyError):
        cache.get("expired")
    assert cache.get("c") == 3
    assert cache.get("d") == 4
    assert cache.get("e") == 5


def test_reput_existing_at_capacity_never_evicts_other_key():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 10)
    assert cache.get("a") == 10
    assert cache.get("b") == 2
    assert len(cache) == 2


def test_reput_after_expiry_creates_fresh_live_entry():
    cache = LRUCache(1)
    cache.put("x", 1, ttl=0.05)
    time.sleep(0.10)
    cache.put("x", 2, ttl=None)
    assert cache.get("x") == 2
    assert len(cache) == 1


def test_tuple_key_with_ttl_expires_normally():
    cache = LRUCache(2)
    key = ("u", 1)
    cache.put(key, "v", ttl=0.05)
    time.sleep(0.10)
    with pytest.raises(KeyError):
        cache.get(key)


def test_ttl_boundary_triad_before_and_after_expiry():
    cache = LRUCache(2)
    cache.put("k", 1, ttl=0.10)

    time.sleep(0.02)  # clearly alive
    assert cache.get("k") == 1

    time.sleep(0.05)  # still before expiry in this test window
    assert cache.get("k") == 1

    time.sleep(0.10)  # clearly after total ttl window
    with pytest.raises(KeyError):
        cache.get("k")


def test_get_expired_key_does_not_change_live_eviction_victim():
    # a(LRU), b(MRU), e(expiring). After probing expired e, inserting d/e2 should
    # still evict a first among live keys.
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("e", 3, ttl=0.05)
    time.sleep(0.10)

    with pytest.raises(KeyError):
        cache.get("e")  # remove expired key only

    cache.put("d", 4)   # fill to capacity
    cache.put("e2", 5)  # force eviction of live LRU ("a")
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert cache.get("d") == 4
    assert cache.get("e2") == 5


def test_long_mixed_sequence_eviction_victim_is_precise():
    cache = LRUCache(3)
    cache.put("a", 1)        # a
    cache.put("b", 2)        # a,b
    cache.put("c", 3)        # a,b,c
    cache.get("a")           # b,c,a
    cache.put("b", 20)       # c,a,b
    cache.get("a")           # c,b,a
    cache.put("d", 4)        # evict c -> b,a,d

    with pytest.raises(KeyError):
        cache.get("c")
    assert cache.get("a") == 1
    assert cache.get("b") == 20
    assert cache.get("d") == 4


@pytest.mark.parametrize("key", [0, "", None, False])
def test_falsey_hashable_keys_round_trip(key):
    # Notes say keys can be any hashable object. Falsey-but-hashable keys
    # catch implementations that treat "missing" as truthiness.
    cache = LRUCache(2)
    cache.put(key, "value")
    assert cache.get(key) == "value"


@pytest.mark.parametrize("value", [0, "", None, False, []])
def test_falsey_values_round_trip_without_becoming_missing(value):
    # Values can be any object, including values that are false in boolean
    # context. Missing is signaled by KeyError, not by value truthiness.
    cache = LRUCache(2)
    cache.put("key", value)
    assert cache.get("key") is value


def test_get_missing_does_not_change_lru_order():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)

    with pytest.raises(KeyError):
        cache.get("missing")

    cache.put("c", 3)
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_reput_expired_key_at_capacity_keeps_other_live_key():
    # len(cache) excludes expired entries. Replacing an expired key should not
    # evict another live key just because stale storage still exists.
    cache = LRUCache(2)
    cache.put("expired", 1, ttl=0.05)
    cache.put("live", 2)
    time.sleep(0.10)

    cache.put("expired", 3)

    assert cache.get("expired") == 3
    assert cache.get("live") == 2
    assert len(cache) == 2
