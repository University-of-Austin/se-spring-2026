import pytest
from lru_cache import LRUCache


def test_c1_zero_capacity_raises():
    with pytest.raises(ValueError):
        LRUCache(0)


def test_c1_negative_capacity_raises():
    with pytest.raises(ValueError):
        LRUCache(-5)

def test_c2_put_and_get_basic():
    cache = LRUCache(5)
    cache.put("dog", "Bambi")
    assert cache.get("dog") == "Bambi"

def test_c2_ttl_none_never_expires():
    import time
    cache = LRUCache(5)
    cache.put("dog", "Bambi", ttl=None)
    time.sleep(0.2)
    assert cache.get("dog") == "Bambi"


def test_c6_get_missing_key_raises():
    cache = LRUCache(5)
    with pytest.raises(KeyError):
        cache.get("cat")

def test_c3_reput_replaces_value():
    cache = LRUCache(5)
    cache.put("dog", "Bambi")
    cache.put("dog", "Rex")
    assert cache.get("dog") == "Rex"

def test_c3_reput_clears_ttl():
    import time
    cache = LRUCache(5)
    cache.put("dog", "Bambi", ttl=0.1)
    cache.put("dog", "Rex", ttl=None)
    time.sleep(0.2)
    assert cache.get("dog") == "Rex"

def test_c3_reput_old_ttl_truly_gone():
    import time
    cache = LRUCache(5)
    cache.put("dog", "Bambi", ttl=0.1)
    cache.put("dog", "Rex", ttl=1.0)
    time.sleep(0.2)
    # old ttl of 0.1 would have expired, but new ttl of 1.0 should still be alive
    assert cache.get("dog") == "Rex"

def test_c4_evicts_least_recently_used():
    cache = LRUCache(3)
    cache.put("dog", "Bambi")
    cache.put("cat", "Grinch")
    cache.put("bird", "Kelly")
    cache.put("horse", "Forest")
    with pytest.raises(KeyError):
        cache.get("dog")

def test_c4_len_after_eviction():
    cache = LRUCache(3)
    cache.put("dog", "Bambi")
    cache.put("cat", "Grinch")
    cache.put("bird", "Kelly")
    cache.put("horse", "Forest")
    assert len(cache) == 3

def test_c4_new_entry_present_after_eviction():
    cache = LRUCache(3)
    cache.put("dog", "Bambi")
    cache.put("cat", "Grinch")
    cache.put("bird", "Kelly")
    cache.put("horse", "Forest")
    assert cache.get("horse") == "Forest"

def test_c5_get_refreshes_lru_position():
    cache = LRUCache(3)
    cache.put("dog", "Bambi")
    cache.put("cat", "Grinch")
    cache.put("bird", "Kelly")
    cache.get("dog")  # refreshes dog, now cat is least recently used
    cache.put("horse", "Forest")
    with pytest.raises(KeyError):
        cache.get("cat")

def test_c5_put_existing_refreshes_lru_position():
    cache = LRUCache(3)
    cache.put("dog", "Bambi")
    cache.put("cat", "Grinch")
    cache.put("bird", "Kelly")
    cache.put("dog", "Rex")  # refreshes dog, now cat is least recently used
    cache.put("horse", "Forest")
    with pytest.raises(KeyError):
        cache.get("cat")
def test_c5_lru_order_based_on_use_not_ttl():
    cache = LRUCache(2)
    cache.put("dog", "Bambi", ttl=0.5)
    cache.put("horse", "Forest")
    cache.get("dog")  # refreshes dog, horse is now least recently used
    cache.put("cat", "Grinch")
    with pytest.raises(KeyError):
        cache.get("horse")


def test_c6_expired_entry_raises():
    import time
    cache = LRUCache(5)
    cache.put("dog", "Bambi", ttl=0.1)
    time.sleep(0.2)
    with pytest.raises(KeyError):
        cache.get("dog")

def test_c6_expired_entry_removed_from_len():
    import time
    cache = LRUCache(5)
    cache.put("dog", "Bambi", ttl=0.1)
    time.sleep(0.2)
    try:
        cache.get("dog")
    except KeyError:
        pass
    assert len(cache) == 0

def test_c7_len_excludes_expired_entries():
    import time
    cache = LRUCache(5)
    cache.put("dog", "Bambi", ttl=0.1)
    cache.put("cat", "Grinch")
    time.sleep(0.2)
    assert len(cache) == 1

def test_c7_len_empty_cache():
    cache = LRUCache(5)
    assert len(cache) == 0

def test_c7_len_decreases_after_expiry():
    import time
    cache = LRUCache(5)
    cache.put("dog", "Bambi", ttl=0.1)
    cache.put("cat", "Grinch")
    assert len(cache) == 2
    time.sleep(0.2)
    assert len(cache) == 1


def test_c7_reput_does_not_increase_len():
    cache = LRUCache(5)
    cache.put("dog", "Bambi")
    cache.put("dog", "Rex")
    assert len(cache) == 1

