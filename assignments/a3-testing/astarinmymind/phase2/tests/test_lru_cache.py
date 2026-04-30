"""Tests for lru_cache module, organized by spec clause."""
import time
import pytest
from lru_cache import LRUCache


# --- C1: Capacity validation ---

def test_c1_valid_capacity():
    """A positive integer capacity should create a cache without error."""
    cache = LRUCache(1)
    assert len(cache) == 0


@pytest.mark.parametrize("bad_cap", [0, -1, -5, -100])
def test_c1_invalid_capacity_raises(bad_cap):
    """Capacity must be a positive int. Zero and any negative value should raise ValueError.
    -1 catches off-by-one bugs like `if cap < -1` that would let -1 through."""
    with pytest.raises(ValueError):
        LRUCache(bad_cap)


def test_c1_capacity_of_one():
    """Capacity of 1 is valid — smallest possible cache."""
    cache = LRUCache(1)
    cache.put("a", 1)
    assert cache.get("a") == 1


# --- C2: put basics ---

def test_c2_put_then_get():
    """Put a key-value pair, then get it back."""
    cache = LRUCache(3)
    cache.put("a", 1)
    assert cache.get("a") == 1


def test_c2_put_replaces_value():
    """Putting the same key again overwrites the value."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("a", 2)
    assert cache.get("a") == 2



def test_c2_put_no_ttl_never_expires():
    """Default ttl=None means the entry stays indefinitely."""
    cache = LRUCache(3)
    cache.put("a", 1)
    time.sleep(0.05)
    assert cache.get("a") == 1


def test_c2_put_with_ttl_expires():
    """Entry with a short TTL should expire after that time."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c2_put_with_int_ttl():
    """TTL can be an int, not just a float."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=1)
    # Should still be alive — 1 second hasn't passed
    assert cache.get("a") == 1


def test_c2_put_with_float_ttl_alive():
    """Sub-second float TTL preserves fractional precision (not truncated to int).
    A buggy impl that coerces ttl to int would turn 0.5 into 0 and expire immediately."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.5)
    time.sleep(0.05)
    assert cache.get("a") == 1


def test_c2_put_multiple_keys():
    """Cache holds multiple distinct keys at once."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("c") == 3


@pytest.mark.parametrize("ttl", [0, 0.0, -1, -0.001])
def test_c2_nonpositive_ttl_expires_immediately(ttl):
    """Any ttl <= 0 (int or float) means the entry is expired at the moment of put.
    Covers the boundary (0, 0.0) and clearly-past (-1, -0.001) for both numeric types."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=ttl)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c2_put_none_value_roundtrips():
    """Storing None as a value must be distinguishable from a missing key.
    Catches the classic sentinel bug where the impl does `if entry is None` and
    conflates 'value happens to be None' with 'key not present'."""
    cache = LRUCache(3)
    cache.put("a", None)
    assert cache.get("a") is None      # not KeyError
    assert len(cache) == 1             # entry counts even though value is None


@pytest.mark.parametrize("value", [0, False, "", [], {}])
def test_c2_put_falsy_value_roundtrips(value):
    """Falsy values (0, False, '', [], {}) must round-trip correctly. Catches a
    bug where the impl uses `if value:` (truthiness) somewhere instead of
    `key in self.entries` (presence). Spec notes: 'values can be any hashable
    Python object.'"""
    cache = LRUCache(3)
    cache.put("a", value)
    assert cache.get("a") == value


@pytest.mark.parametrize("key", [1, 3.14, (1, 2), frozenset([1, 2])])
def test_c2_put_non_string_keys_roundtrip(key):
    """Spec notes say keys can be any hashable Python object. Verify int, float,
    tuple, and frozenset keys all round-trip correctly."""
    cache = LRUCache(5)
    cache.put(key, "value")
    assert cache.get(key) == "value"


def test_c2_distinct_key_types_dont_collide():
    """Different key types with similar string representations must NOT collide.
    Catches a bug where the impl does `str(key)` anywhere — e.g., `1` and `"1"`
    would be conflated into the same entry."""
    cache = LRUCache(5)
    cache.put(1, "int-1")
    cache.put("1", "str-1")
    cache.put((1,), "tuple-1")
    assert cache.get(1) == "int-1"
    assert cache.get("1") == "str-1"
    assert cache.get((1,)) == "tuple-1"
    assert len(cache) == 3


# --- C3: TTL replacement on re-put ---

def test_c3_reput_resets_ttl():
    """Re-putting a key with a new TTL resets the expiration clock."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("a", 2, ttl=0.5)
    time.sleep(0.1)
    # Old TTL (0.05s) has passed, but new TTL (0.5s) hasn't
    assert cache.get("a") == 2


def test_c3_reput_none_clears_ttl():
    """Re-putting with ttl=None clears a previously-set expiration."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("a", 2, ttl=None)
    time.sleep(0.1)
    # Original TTL has passed, but entry should still be alive
    assert cache.get("a") == 2


def test_c3_reput_adds_ttl_to_untimed_entry():
    """An entry put without ttl, then re-put with one, must honor the new ttl.
    Catches an impl that stores a 'never expires' flag and forgets to clear it on re-put."""
    cache = LRUCache(3)
    cache.put("a", 1)              # no ttl
    cache.put("a", 2, ttl=0.05)    # now has ttl
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c3_reput_resets_expiration_clock():
    """Re-put with the same ttl must restart the expiration clock from the new put time,
    not preserve the original expiration timestamp. Pins the spec's 'expiration time
    superseded' clause separately from 'ttl superseded'."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.1)
    time.sleep(0.07)               # most of original ttl elapsed
    cache.put("a", 2, ttl=0.1)     # same ttl — clock should restart from now
    time.sleep(0.07)               # past original deadline, but new clock has ~0.03 left
    assert cache.get("a") == 2


# --- C4: Capacity eviction ---

def test_c4_full_insert_evicts_oldest():
    """When the cache is full, inserting a NEW key evicts the least-recently-used
    entry — which, with no get/put-on-existing in play, is the first one inserted."""
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)              # full → must evict "a"
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert len(cache) == 2


def test_c4_reput_existing_does_not_evict_when_full():
    """Re-putting an existing key on a full cache is an update, not an insert.
    No eviction should happen — both keys remain, len stays at capacity."""
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 99)             # update, not insert — must not evict "b"
    assert cache.get("a") == 99
    assert cache.get("b") == 2
    assert len(cache) == 2


def test_c4_capacity_one_evicts_on_every_new_insert():
    """Smallest-cache edge case: capacity 1 means each new key evicts the previous."""
    cache = LRUCache(1)
    cache.put("a", 1)
    cache.put("b", 2)
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2
    assert len(cache) == 1


def test_c4_multiple_overflows_keep_evicting():
    """Eviction must keep working across multiple overflows — catches an impl that
    succeeds once but corrupts internal bookkeeping for subsequent inserts."""
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)              # evicts "a"
    cache.put("d", 4)              # evicts "b"
    with pytest.raises(KeyError):
        cache.get("a")
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("c") == 3
    assert cache.get("d") == 4
    assert len(cache) == 2


# --- C5: Use tracking (LRU promotion) ---

def test_c5_get_promotes_to_mru():
    """get(key) is a 'use' — it must reset that key's position to most-recently-used.
    With cap=3 filled by [a, b, c] (a is LRU), getting 'a' makes 'b' the new LRU.
    A subsequent put of a new key must therefore evict 'b', not 'a'."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")                 # promote "a" to MRU; "b" now LRU
    cache.put("d", 4)              # cache full, new key → evict LRU which is "b"
    assert cache.get("a") == 1
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("c") == 3
    assert cache.get("d") == 4
    assert len(cache) == 3


def test_c5_put_on_existing_promotes_to_mru():
    """put(key, ...) on an EXISTING key is also a 'use' — must promote to MRU.
    Same shape as the get test, but the promoter is a re-put. Catches an impl that
    treats re-put as a pure value update without touching LRU position."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)             # re-put: promotes "a" to MRU; "b" now LRU
    cache.put("d", 4)              # evicts "b"
    assert cache.get("a") == 99
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("c") == 3
    assert cache.get("d") == 4
    assert len(cache) == 3


def test_c5_new_key_insert_does_not_promote_others():
    """Inserting a NEW key must not change the relative order of existing keys.
    After [a, b, c] then put d (evicts a), the surviving order must still be b<c.
    A subsequent put of e must therefore evict b, not c. This pins the third C5
    claim — only observable with ≥2 survivors after the first overflow, hence cap=3."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)              # evicts "a"; b/c relative order must stay (b<c)
    cache.put("e", 5)              # evicts "b" (next LRU), NOT "c"
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("c") == 3
    assert cache.get("d") == 4
    assert cache.get("e") == 5
    assert len(cache) == 3


def test_c5_multi_use_sequence():
    """Multi-step LRU sequence — promotion must remain consistent across multiple uses.
    Catches an impl where promotion works once but corrupts state for subsequent uses."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)              # order: a < b < c
    cache.get("a")                 # order: b < c < a
    cache.get("b")                 # order: c < a < b
    cache.put("d", 4)              # evicts "c" (now LRU)
    with pytest.raises(KeyError):
        cache.get("c")
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("d") == 4
    assert len(cache) == 3


# --- C6: get raises KeyError on missing/expired ---

def test_c6_get_missing_key_raises():
    """get on a never-inserted key raises KeyError. Pinned explicitly here even though
    eviction tests cover it implicitly — makes the spec mapping unambiguous."""
    cache = LRUCache(3)
    with pytest.raises(KeyError):
        cache.get("nonexistent")


def test_c6_get_expired_raises():
    """get on an expired entry raises KeyError. C6's first claim, mapped explicitly."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c6_get_expired_then_reput_works():
    """After get-on-expired raises, the entry must be cleared enough that a fresh put
    to the same key works as a new insert. Smoke test for the spec's 'removes the
    entry from the cache' clause — not fully pinning it (the lingering-expired bug
    is invisible from outside without cross-clause C4×C7 setup), but verifying the
    user-facing behavior holds."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")             # expired and removed
    cache.put("a", 2)              # fresh put — no ttl this time
    assert cache.get("a") == 2     # new value alive, no expiration carryover
    time.sleep(0.1)
    assert cache.get("a") == 2     # still alive after sleep (no inherited ttl)


def test_c6_get_expired_does_not_revive():
    """A get on an expired entry raises but must NOT 'revive' it. A second get on
    the same key must still raise — the entry is gone, not extended. len must stay
    constant across the gets, confirming no observable state change from the expired
    entry being touched. Catches bugs where get-on-expired silently extends the TTL,
    re-marks the entry as alive, or re-adds it to the live-count tracking."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2)              # baseline live entry
    time.sleep(0.1)                # "a" is now expired but unaccessed
    assert len(cache) == 1         # before any get: only "b" counted
    with pytest.raises(KeyError):
        cache.get("a")             # first get on expired
    assert len(cache) == 1         # unchanged — "a" was not revived
    with pytest.raises(KeyError):
        cache.get("a")             # second get on (still-)expired
    assert len(cache) == 1         # unchanged — second get also didn't revive


def test_c6_get_on_expired_frees_capacity_slot():
    """C6 says get-on-expired 'removes the entry from the cache.' This is observable
    via the eviction trigger: after the cleanup, the freed slot means a subsequent
    put doesn't need to evict an alive entry.

    Path B in the README's C4×C7 narrative: starting from {a alive, b expired} at
    cap=2, calling get('b') first physically removes b (raw size drops from 2 to 1),
    so the next put('c') has room and inserts without eviction — both 'a' and 'c'
    survive. Without the pre-cleanup (Path A), 'a' would have been evicted.

    Pins C6's 'removes' sub-clause through its observable consequence on capacity
    accounting. Catches a bug where get-on-expired raises but doesn't actually
    unlink the entry from internal storage."""
    cache = LRUCache(2)
    cache.put("a", 1)              # alive, no ttl
    cache.put("b", 2, ttl=0.05)    # will expire
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("b")             # forces C6 cleanup of expired "b"
    cache.put("c", 3)              # raw size now 1 < cap; no eviction needed
    assert cache.get("a") == 1     # "a" survived (would have been evicted in Path A)
    assert cache.get("c") == 3
    assert len(cache) == 2


# --- C7: Length ---

def test_c7_len_excludes_expired_unaccessed():
    """The core C7 claim: an entry whose TTL has passed must NOT be counted by len,
    even if no one has called get on it since it expired. Pins the spec's specific
    'even if they have not yet been accessed since expiring' phrase."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2)              # no ttl
    time.sleep(0.1)                # "a" has expired but no get called on it
    assert len(cache) == 1         # only "b" should count


def test_c7_len_with_mixed_expired_alive():
    """Multi-entry mix: some expired, some no-ttl, some with future ttl. len must
    accurately reflect only the non-expired ones across a varied state."""
    cache = LRUCache(5)
    cache.put("a", 1, ttl=0.05)    # will expire
    cache.put("b", 2)              # no ttl, alive
    cache.put("c", 3, ttl=0.05)    # will expire
    cache.put("d", 4)              # no ttl, alive
    cache.put("e", 5, ttl=1.0)     # ttl far enough out to stay alive
    time.sleep(0.1)
    assert len(cache) == 3         # b, d, e — a and c expired


def test_c7_all_expired_len_zero():
    """When every entry has expired, len must be 0 — the strongest version of the
    'expired entries don't count' claim. Catches off-by-one or 'minimum 1' bugs."""
    cache = LRUCache(3)
    cache.put("a", 1, ttl=0.05)
    cache.put("b", 2, ttl=0.05)
    cache.put("c", 3, ttl=0.05)
    time.sleep(0.1)
    assert len(cache) == 0


def test_c7_capacity_one_len_cycles_with_ttl():
    """The smallest cache (cap=1) must accurately track len through a fresh →
    populated → expired → repopulated cycle. Catches state corruption in
    minimum-size caches when entries come and go via TTL."""
    cache = LRUCache(1)
    assert len(cache) == 0         # fresh
    cache.put("a", 1, ttl=0.05)
    assert len(cache) == 1         # populated
    time.sleep(0.1)
    assert len(cache) == 0         # all expired
    cache.put("b", 2)
    assert len(cache) == 1         # repopulated


def test_c7_reput_does_not_increment_len():
    """Re-putting an existing key is an update, not an insert — len must not change.
    Catches a bug where re-put adds a duplicate entry instead of replacing."""
    cache = LRUCache(3)
    cache.put("a", 1)
    assert len(cache) == 1
    cache.put("a", 99)
    assert len(cache) == 1         # still 1, not 2
    cache.put("a", 7, ttl=10)
    assert len(cache) == 1         # still 1, even with ttl change
