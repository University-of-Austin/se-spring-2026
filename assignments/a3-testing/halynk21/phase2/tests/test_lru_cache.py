import time
import pytest
from lru_cache import LRUCache

TTL_SHORT  = 0.020   # 20ms — entry expires after this
SLEEP_PAST = 0.060   # 60ms — 3x TTL_SHORT; guaranteed expired on any machine


# ---------------------------------------------------------------------------
# C1 — Capacity validation
# ---------------------------------------------------------------------------

def test_c1_capacity_zero_raises():
    with pytest.raises(ValueError):
        LRUCache(0)


def test_c1_capacity_negative_raises():
    with pytest.raises(ValueError):
        LRUCache(-5)


def test_c1_capacity_one_does_not_raise():
    cache = LRUCache(1)
    assert len(cache) == 0


# ---------------------------------------------------------------------------
# C2 — put basic behavior
# ---------------------------------------------------------------------------

def test_c2_put_get_basic():
    cache = LRUCache(2)
    cache.put("a", 42)
    assert cache.get("a") == 42


def test_c2_put_overwrites_value():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("a", 2)
    assert cache.get("a") == 2


def test_c2_ttl_none_never_expires():
    cache = LRUCache(2)
    cache.put("a", 99, ttl=None)
    time.sleep(SLEEP_PAST)
    assert cache.get("a") == 99


# ---------------------------------------------------------------------------
# C3 — TTL replacement on re-put
# ---------------------------------------------------------------------------

def test_c3_reput_clears_old_ttl():
    # First put has TTL; re-put with ttl=None should clear expiry
    cache = LRUCache(2)
    cache.put("a", 1, ttl=TTL_SHORT)
    cache.put("a", 2, ttl=None)   # clears the TTL
    time.sleep(SLEEP_PAST)
    assert cache.get("a") == 2    # should still be alive


def test_c3_reput_with_new_ttl_supersedes():
    # Re-put with a longer TTL should use the new expiry, not the old one
    cache = LRUCache(2)
    cache.put("a", 1, ttl=TTL_SHORT)
    cache.put("a", 2, ttl=TTL_SHORT * 50)  # 1 second — far future
    time.sleep(SLEEP_PAST)
    assert cache.get("a") == 2    # alive because new TTL is long


# ---------------------------------------------------------------------------
# C4 — Capacity eviction
# ---------------------------------------------------------------------------

def test_c4_evicts_lru_not_mru():
    # Fill to capacity, promote oldest via get, insert new key.
    # The second-oldest (not the one we promoted) should be evicted.
    cache = LRUCache(3)
    cache.put("a", 1)   # inserted first → LRU
    cache.put("b", 2)
    cache.put("c", 3)   # MRU
    cache.get("a")      # promotes "a" → now LRU is "b"
    cache.put("d", 4)   # should evict "b"
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("a") == 1
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_c4_evicted_key_raises_key_error():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)   # evicts "a"
    with pytest.raises(KeyError):
        cache.get("a")


def test_c4_len_equals_capacity_after_insert():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)   # triggers eviction
    assert len(cache) == 3


def test_c4_c5_reput_existing_at_capacity_does_not_evict():
    # C4: eviction triggers only on a new key that would exceed capacity.
    # Re-putting an existing key must not evict any other entry.
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 99)   # existing key re-put; no eviction should occur
    assert cache.get("a") == 99
    assert cache.get("b") == 2
    assert len(cache) == 2


def test_c4_c5_reput_after_intervening_get_does_not_evict():
    # Without an intervening get(), the re-put key happens to be the LRU,
    # so a buggy "always evict LRU then reinsert" produces the same state.
    # get("a") promotes "a" to MRU first, making "b" the LRU — now a buggy
    # impl evicts "b", while a correct impl leaves both entries alive.
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")        # promote "a"; "b" is now LRU
    cache.put("a", 99)    # re-put already-promoted key; no eviction
    assert cache.get("a") == 99
    assert cache.get("b") == 2   # "b" must still be alive
    assert len(cache) == 2


# ---------------------------------------------------------------------------
# C5 — Use tracking
# ---------------------------------------------------------------------------

def test_c5_get_promotes_to_mru():
    cache = LRUCache(2)
    cache.put("a", 1)   # LRU
    cache.put("b", 2)   # MRU
    cache.get("a")      # promotes "a" to MRU; "b" is now LRU
    cache.put("c", 3)   # should evict "b", not "a"
    assert cache.get("a") == 1
    with pytest.raises(KeyError):
        cache.get("b")


def test_c5_put_existing_promotes_to_mru():
    cache = LRUCache(2)
    cache.put("a", 1)   # LRU
    cache.put("b", 2)   # MRU
    cache.put("a", 9)   # re-put "a" promotes it to MRU; "b" becomes LRU
    cache.put("c", 3)   # should evict "b", not "a"
    assert cache.get("a") == 9
    with pytest.raises(KeyError):
        cache.get("b")


def test_c5_eviction_order_respects_put_existing():
    # Full sequence: confirm put-on-existing changes who gets evicted next
    cache = LRUCache(3)
    cache.put("x", 10)
    cache.put("y", 20)
    cache.put("z", 30)
    # LRU order: x(oldest) → y → z(MRU)
    cache.put("y", 99)  # re-put y → LRU order: x → z → y(MRU)
    cache.put("w", 40)  # evicts x (LRU)
    with pytest.raises(KeyError):
        cache.get("x")
    assert cache.get("y") == 99
    assert cache.get("z") == 30
    assert cache.get("w") == 40


# ---------------------------------------------------------------------------
# C6 — Expiration on get
# ---------------------------------------------------------------------------

def test_c6_expired_get_raises_key_error():
    cache = LRUCache(2)
    cache.put("a", 1, ttl=TTL_SHORT)
    time.sleep(SLEEP_PAST)
    with pytest.raises(KeyError):
        cache.get("a")


def test_c6_missing_key_raises_key_error():
    cache = LRUCache(2)
    with pytest.raises(KeyError):
        cache.get("nonexistent")


def test_c6_expired_get_then_len_already_zero():
    # C7 already excludes expired entries from len before the get fires.
    # Do NOT assert "len decreases" — it was already 0 per C7.
    cache = LRUCache(2)
    cache.put("a", 1, ttl=TTL_SHORT)
    time.sleep(SLEEP_PAST)
    assert len(cache) == 0          # C7: already excluded
    with pytest.raises(KeyError):
        cache.get("a")              # C6: raises on expired
    assert len(cache) == 0          # still 0 after removal


# ---------------------------------------------------------------------------
# C7 — Length
# ---------------------------------------------------------------------------

def test_c7_len_excludes_expired_entries():
    cache = LRUCache(3)
    cache.put("a", 1, ttl=TTL_SHORT)
    cache.put("b", 2)
    time.sleep(SLEEP_PAST)
    assert len(cache) == 1   # only "b" is alive


def test_c7_len_excludes_expired_even_without_access():
    # Entry expires and is never get()-ted — must still not appear in len()
    cache = LRUCache(2)
    cache.put("a", 1, ttl=TTL_SHORT)
    time.sleep(SLEEP_PAST)
    assert len(cache) == 0   # expired without any get() call


# ---------------------------------------------------------------------------
# Hidden tests
# ---------------------------------------------------------------------------

def test_hidden_ttl_zero_immediately_expired():
    # C2: "expires at time.monotonic() + ttl". ttl=0 means expiry == put_time.
    # Since monotonic never decreases, any get() fires at or after expiry.
    cache = LRUCache(2)
    cache.put("x", 42, ttl=0)
    with pytest.raises(KeyError):
        cache.get("x")
    assert len(cache) == 0


def test_hidden_reput_on_expired_key_is_fresh_insert():
    # C2: "inserts or replaces" with no expiry-state qualifier.
    cache = LRUCache(2)
    cache.put("x", 1, ttl=TTL_SHORT)
    time.sleep(SLEEP_PAST)
    cache.put("x", 2)
    assert cache.get("x") == 2


def test_hidden_expired_get_does_not_corrupt_lru_order():
    # After get() raises for an expired entry and removes it, the LRU ordering
    # of surviving live entries must still be correct for subsequent evictions.
    cache = LRUCache(3)
    cache.put("a", 1)                        # oldest, no TTL
    cache.put("b", 2)                        # middle, no TTL
    cache.put("d", 99, ttl=TTL_SHORT)        # MRU, will expire
    time.sleep(SLEEP_PAST)                   # d expires; len==2
    with pytest.raises(KeyError):
        cache.get("d")                       # C6: removes d
    cache.put("c", 3)                        # len was 2 < 3, no eviction; LRU: [a, b, c]
    assert len(cache) == 3
    cache.put("e", 5)                        # len==3==capacity; must evict "a" (LRU)
    with pytest.raises(KeyError):
        cache.get("a")                       # a correctly evicted
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.get("e") == 5
