from lru_cache import LRUCache
import pytest
import time

## C1. Capacity

# What if capacity = 1 (the smallest valid value)?
def test_c1_capacity_one_constructs_successfully():
    cache = LRUCache(1)

# What if I construct with a typical positive capacity?
def test_c1_positive_capacity_constructs_successfully():
    cache = LRUCache(3)

# What if capacity = 0?
def test_c1_zero_capacity_raises_value_error():
    with pytest.raises(ValueError):
        LRUCache(0)

# What if capacity is negative?
def test_c1_negative_capacity_raises_value_error():
    with pytest.raises(ValueError):
        LRUCache(-5)

## C2. put(key, value, ttl)

# What if I do a basic put then get?
def test_c2_basic_put_then_get_returns_value():
    cache = LRUCache(3)
    cache.put("a", 1)
    assert cache.get("a") == 1

# What if I put with explicit ttl = None?
def test_c2_put_with_ttl_none_stores_entry():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = None)
    assert cache.get("a") == 1

# What if I put with an integer ttl?
def test_c2_put_accepts_integer_ttl():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = 60)
    assert cache.get("a") == 1

# What if I put with a float ttl?
def test_c2_put_accepts_float_ttl():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = 60.5)
    assert cache.get("a") == 1

# What if I put with ttl = 0?
def test_c2_put_accepts_zero_ttl():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = 0)

# What if I put with a negative ttl?
def test_c2_put_accepts_negative_ttl():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = -1)

# What if I put with None as the value?
def test_c2_put_with_none_value_works():
    cache = LRUCache(3)
    cache.put("a", None)
    assert cache.get("a") is None

# What if I put with an integer key?
def test_c2_put_with_integer_key_works():
    cache = LRUCache(3)
    cache.put(42, "value")
    assert cache.get(42) == "value"

# What if I put with a tuple key (any hashable)?
def test_c2_put_with_tuple_key_works():
    cache = LRUCache(3)
    cache.put((1, 2), "value")
    assert cache.get((1, 2)) == "value"

## C3. TTL replacement on re-put

# What if I re-put an existing key with a new value?
def test_c3_reput_replaces_value():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("a", 2)
    assert cache.get("a") == 2

# What if I re-put an existing key with a shorter TTL?
def test_c3_reput_replaces_old_ttl_with_new():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = 60)
    cache.put("a", 1, ttl = 0.05)
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")

# What if I re-put an existing key with ttl = None to clear the old TTL?
def test_c3_reput_with_ttl_none_clears_old_expiration():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = 0.05)
    cache.put("a", 1, ttl = None)
    time.sleep(0.1)
    assert cache.get("a") == 1

# What if I re-put a key after its previous entry expired?
def test_c3_reput_after_expiration_works_as_fresh_insert():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = 0.05)
    time.sleep(0.1)
    cache.put("a", 99)
    assert cache.get("a") == 99

# What if I re-put an existing key with ttl = 0?
def test_c3_reput_with_ttl_zero_expires_immediately():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("a", 99, ttl = 0)
    with pytest.raises(KeyError):
        cache.get("a")

# What if I re-put an existing key with the SAME TTL value (does the timer reset)?
def test_c3_reput_with_same_ttl_resets_timer():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = 0.2)
    time.sleep(0.15)
    cache.put("a", 1, ttl = 0.2)
    time.sleep(0.15)
    assert cache.get("a") == 1

## C4. Capacity eviction

# What if I insert a new key when the cache is full?
def test_c4_eviction_removes_lru_when_full():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    with pytest.raises(KeyError):
        cache.get("a")

# What if eviction happens at capacity = 1?
def test_c4_eviction_at_capacity_one():
    cache = LRUCache(1)
    cache.put("a", 1)
    cache.put("b", 2)
    with pytest.raises(KeyError):
        cache.get("a")
    assert cache.get("b") == 2

# What if I re-put an existing key when the cache is full?
def test_c4_reput_existing_key_at_capacity_does_not_evict():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 99)
    assert cache.get("a") == 99
    assert cache.get("b") == 2

# What if I check len after an eviction?
def test_c4_len_equals_capacity_after_eviction():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert len(cache) == 2

# What if I put a key that was previously evicted?
def test_c4_put_previously_evicted_key_works():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)
    assert cache.get("a") == 99

# What if every entry in a full cache is expired and I add a new key?
def test_c4_no_eviction_when_all_entries_expired():
    cache = LRUCache(2)
    cache.put("a", 1, ttl = 0.05)
    cache.put("b", 2, ttl = 0.05)
    time.sleep(0.1)
    cache.put("c", 3)
    assert cache.get("c") == 3

## C5. Use tracking

# What if I get an existing key (does that promote it)?
def test_c5_get_promotes_key_to_most_recently_used():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("a")
    cache.put("d", 4)
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("a") == 1

# What if I re-put an existing key (does that promote it)?
def test_c5_put_on_existing_key_promotes_to_most_recently_used():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("a", 99)
    cache.put("d", 4)
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("a") == 99

# What if I insert a new key (does that disturb the order of existing keys)?
def test_c5_inserting_new_key_does_not_affect_order_of_existing():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)
    cache.put("e", 5)
    with pytest.raises(KeyError):
        cache.get("b")
    assert cache.get("c") == 3
    assert cache.get("d") == 4
    assert cache.get("e") == 5

## C6. Expiration on get

# What if I get an expired entry?
def test_c6_get_on_expired_entry_raises_key_error():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = 0.05)
    time.sleep(0.1)
    with pytest.raises(KeyError):
        cache.get("a")

# What if I get a non-existent key?
def test_c6_get_on_non_existent_key_raises_key_error():
    cache = LRUCache(3)
    with pytest.raises(KeyError):
        cache.get("nope")

# What if I get an entry that was put with ttl = 0?
def test_c6_get_on_zero_ttl_entry_raises_key_error():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = 0)
    with pytest.raises(KeyError):
        cache.get("a")

# What if I get an entry that was put with a negative ttl?
def test_c6_get_on_negative_ttl_entry_raises_key_error():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = -1)
    with pytest.raises(KeyError):
        cache.get("a")

# What if multiple entries have different TTLs aging in parallel?
def test_c6_multiple_ttls_age_independently():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = 0.5)
    cache.put("b", 2, ttl = 0.05)
    time.sleep(0.1)
    assert cache.get("a") == 1
    with pytest.raises(KeyError):
        cache.get("b")

## C7. Length

# What if I check len of an empty cache?
def test_c7_empty_cache_has_length_zero():
    cache = LRUCache(3)
    assert len(cache) == 0

# What if an entry expires but no one called get on it yet?
def test_c7_len_excludes_expired_even_without_get():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = 0.05)
    time.sleep(0.1)
    assert len(cache) == 0

# What if an entry was put with ttl = 0 (immediately expired)?
def test_c7_len_excludes_zero_ttl_entry():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = 0)
    assert len(cache) == 0

# What if an entry was put with a negative ttl (already expired)?
def test_c7_len_excludes_negative_ttl_entry():
    cache = LRUCache(3)
    cache.put("a", 1, ttl = -1)
    assert len(cache) == 0

# What if the cache has both expired and non-expired entries?
def test_c7_len_with_mixed_expired_and_fresh():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2, ttl = 60)
    cache.put("c", 3, ttl = 0.05)
    time.sleep(0.1)
    assert len(cache) == 2
