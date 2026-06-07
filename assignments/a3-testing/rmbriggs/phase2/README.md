# Phase 2 — A3 Test-First Bug Hunt

## What my tests caught vs. missed

**Caught all 20 labeled bugs.** Mapping catalog → first failing test:

`lru_cache` — A1 `test_c5_get_promotes_to_mru` · A2 `test_c6_get_expired_raises_keyerror` · A3 `test_c7_len_excludes_expired_unaccessed` · A4 `test_c3_reput_short_ttl_supersedes_long_ttl` · A5 `test_c4_size_stays_at_capacity_after_eviction` · A6 `test_c1_capacity_zero_raises`.

`interval_merger` — A7 `test_c3_touching_endpoints_merge` · A8 `test_c4_zero_length_alone_stays` · A9 `test_c6_unsorted_input_list_not_mutated` · A10 `test_c5_empty_returns_empty` · A11 `test_c2_unsorted_input_returns_sorted_output` · A12 `test_c1_reversed_positive_raises`.

`cart` — A13 `test_c4_save10_then_save20_second_rejected` · A14 `test_c4_flat5_stacks_with_save10` · A15 `test_c5_flat5_clamps_at_zero` · A16 `test_c3_freeship_at_threshold_waives` · A17 `test_c3_bogo_bagel_qty_2_one_free` · A18 `test_c6_save10_rounds_half_even_subtotal_1005` · A19 `test_c2_apply_lowercase_save10_is_unknown` · A20 `test_c7_empty_cart_total_is_zero`.

Initial run on the buggy source: **96 failed, 109 passed** — every labeled bug surfaced, several with multiple failing tests.

## Fix process

Module by module, spec-driven, not test-by-test. For each file I held the catalog row + the spec clause + the buggy code side-by-side and rewrote against the spec rather than patching individual lines. Cleaner than chasing failures: most bugs in a module share an underlying assumption (e.g. cart application order), so a cohesive rewrite fixes a cluster at once.

Notable fixes: `lru_cache.put` now sweeps expired entries before the capacity check so they don't crowd live ones out; `interval_merger` validates before sorting (and copies the input — never `intervals.sort`); `cart` removes the `_bogo_applied_before_bagel` flag entirely (the spec evaluates BOGO lazily at `total_cents` time), reorders FLAT5 to come after the percent discount, clamps the post-FLAT5 subtotal at 0, and switches the rounding mode to `ROUND_HALF_EVEN`.

After rewrites: **205 passed, 0 failed.**

## Surprises

The cart rewrite collapsed faster than expected once I realized C5 and C7 were what tied most of the bugs together — the buggy code's `_bogo_applied_before_bagel` cache was the sneakiest piece, since it looks like state-tracking but is actually a clause violation in disguise. I'm curious which interval_merger case was the hidden bug; my "no mutation on raise" and "triple touching chain" tests felt like the candidates going into Phase 2.
