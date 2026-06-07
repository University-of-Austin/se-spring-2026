# Phase 2 — Assignment 3

## 1. Bugs I caught

My Phase 1 test suite caught **all 20 seeded bugs** across the three modules. After fixing each one in `phase2/src/`, every test in my suite passes (17 in `test_interval_merger.py`, 20 in `test_lru_cache.py`, 36 in `test_cart.py` — 73 total).

Of the 20 bugs, only 5 were called out by comments in the buggy source (4 in `interval_merger.py`, 1 in `cart.py`). The other 15 had no comments warning about them — my tests caught them purely from the spec.

### `interval_merger.py` — 5 bugs

1. Reversed tuples were silently corrected (swapped) instead of raising a `ValueError`, which was caught by `test_c1_reversed_tuple_raises` and `test_c1_negative_reversed_tuple_raises`.

2. Intervals that touched at endpoints (e.g., `(3,6)` and `(6,9)`) were not merged, and intervals fully contained within others were incorrectly re-added instead of absorbed, which was caught by `test_c3_touching_endpoints_merge` and `test_c3_multiple_intervals_merge_full_span`.

3. Zero-length intervals like `(10,10)` were incorrectly discarded instead of being treated as valid intervals, which was caught by `test_c4_zero_length_alone`.

4. An empty input returned `None` instead of an empty list `[]`, which was caught by `test_c5_empty_input`.

5. The function mutated the original input list by sorting it in place instead of leaving it unchanged, which was caught by `test_c6_no_mutation`.

### `lru_cache.py` — 6 bugs

None of these had comments calling them out — all caught from the spec.

1. The `__init__` method did not validate that `capacity > 0`, allowing zero or negative capacities, which was caught by `test_c1_zero_capacity_raises` and `test_c1_negative_capacity_raises`.

2. Re-inserting an existing key updated the value but incorrectly preserved the old TTL instead of resetting it, which was caught by `test_c3_reput_clears_ttl` and `test_c3_reput_old_ttl_truly_gone`.

3. The eviction condition used an off-by-one check (`>= capacity + 1`), allowing the cache to exceed its intended capacity, which was caught by `test_c4_evicts_least_recently_used` and `test_c4_len_after_eviction`.

4. The `get(key)` operation did not refresh the LRU ordering, so accesses were not treated as usage, which was caught by `test_c5_get_refreshes_lru_position` and `test_c5_lru_order_based_on_use_not_ttl`.

5. The `get` method returned `None` for missing or expired keys instead of raising `KeyError`, and also failed to remove expired entries, which was caught by `test_c6_get_missing_key_raises`, `test_c6_expired_entry_raises`, and `test_c6_expired_entry_removed_from_len`.

6. The `__len__` method returned the raw dictionary size, including expired entries, instead of only counting valid ones, which was caught by `test_c7_len_excludes_expired_entries` and `test_c7_len_decreases_after_expiry`.
### `cart.py` — 9 bugs


1. `apply_code` was not case-sensitive and actually upper-cased the input, so `"save10"` was treated as `"SAVE10"` was caught by the `test_c2_case_sensitive_code` 
2. `SAVE10` and `SAVE20` were both allowed to apply even though the spec says they're mutually exclusive and it was caught by the `test_c4_save10_and_save20_mutually_exclusive`, `test_c4_save20_and_save10_mutually_exclusive`.
3. The BOGO_BAGEL formula was implemented as (qty - 1) // 2 instead of qty // 2, so buying 2 bagels resulted in 0 free instead of 1, which was caught by test_c3_bogo_bagel.
4.A `_bogo_applied_before_bagel` flag forced the discount order incorrectly, causing the BOGO logic to run at the wrong stage instead of being applied consistently with the pricing rules, which was caught by its corresponding ordering test.
5.FLAT5 was subtracted before applying the percent discount instead of after, inflating the discount base, which was caught by `test_c5_flat5_applies_after_percent_discount` and `test_c5_flat5_applies_after_bogo_and_percent`.
6.The pre-shipping subtotal was not clamped at 0, so applying FLAT5 to a cart under $5 could produce a negative total, which was caught by `test_c5_flat5_clamps_at_zero`.
7.The FREESHIP threshold used a strict > comparison instead of >=, so a subtotal of exactly 5000 did not qualify, which was caught by `test_c5_freeship_exact_boundary` and `test_c3_freeship`.
8.Percent discounts used ROUND_HALF_UP instead of `ROUND_HALF_EVEN`, so values like 100.5 rounded to 101 instead of 100, which was caught by `test_c6_rounding_half_even`.
9.An empty cart without FREESHIP returned a 500 shipping charge instead of 0, even though the spec requires empty carts to total 0, which was caught by `test_c7_empty_cart_returns_zero` and `test_c7_empty_cart_with_codes_returns_zero`.


## 2. Fixing Pattern 

To fix the bugs I began with telling Claude Code to fix the tests one by one on what the output is and what it was supposed to be, however as time went on, I noticed that the the process could be going twice as fast and just told Claude Code to fix the bugs that showed up in each program. This went by faster and had all of the bugs fixed at the end. 


## 3. Suprises

### Cart Program 
I was suprised that alot of the tests had to do with the specific math constrictions. This includes the incorrect rounded that caused a bug with the the Round half up instead of Round Half even which made the amount just that one extra cent bigger. Then also the small errors of > sign which made the freeshipping code not activate when the price was 5000, had to be changed to >= so that it included 5000. Also I thought it was interesting that the shipping cost was applied reguardless of the items in the cart, when it was completely empty the Freeship had to be applied to get it to 0, and so one of the bugs that had to be fixed was that the shipping cost was not charged on an empty cart. 
### Interval Merger
With the Interval Merger had almost a similar bug with the inclusion and declusion of the intervals when comparing the start and end numbers in the intervals, it was > instead of >=, just like the bug in the Cart program with the Free Shipping code. It was very funny to see how most of the bugs were dilberately going against the spec, code mutated the interval order by putting it in inverse order, and even swapped the start and end numbers when they were out of order, behaviors that the spec wanted to avoid. 

### Lru Cache 
Lru Cache had a similar situation with the bugs of the Cart and Interval Merger programs were the bugs were specifically designed to go agianst the behavior the spec wanted. One of the bugs specifically was due to the lack of specificity where the init accepted any value, negative and 0 despite the necessity of positve integers in this circumstance of capacity. One of the other bugs that surprised me was that capcity was overflowing instead of capping off at the capacity like it should. I was very suprised that the program didn't account for the amount of times the key-value pair was visited which was the main functionality of the program. 