# Phase 2 — Sam-Indyk

## What my Phase 1 tests caught vs. missed

Cross-referenced against the catalog: my Phase 1 suite fails on all 20 labeled bugs (A1–A20) when the buggy source is run as-is. Concretely:

- **`lru_cache`** A1–A6: `test_c5_get_promotes_key_to_mru`, `test_c6_get_expired_raises_keyerror`, `test_c7_len_excludes_expired_without_access`, `test_c3_reput_with_*` family, `test_c4_evicts_lru_when_full`, and `test_c1_capacity_*_raises` cover them.
- **`interval_merger`** A7–A12: `test_c3_touching_endpoints_merge`, `test_c4_singleton_*`, `test_c6_does_not_*_input_list`, `test_c5_empty_input_returns_empty_list`, `test_c2_unsorted_input_returns_sorted_output`, and `test_c1_no_silent_swap` cover them.
- **`cart`** A13–A20: the `test_c4_*` mutual-exclusion tests, `test_c5_flat5_applied_after_percent`, `test_c5_flat5_clamps_at_zero`, `test_freeship_threshold_inclusive_at_5000`, `test_c3_bogo_bagel_qty_4_two_free`, `test_c6_half_even_distinguishes_from_half_up`, `test_c2_case_sensitive_lower`, and `test_c7_empty_cart_total_zero` cover them.

Initial buggy run: 62 failed / 77 passed across 139 tests. After the fix: 139/139 green.

The likely gap: I never tested *applying `BOGO_BAGEL` before adding the bagel line item* — the buggy source has a `_bogo_applied_before_bagel` flag that suppresses the discount in that ordering, which I'd guess is a hidden bug. My fix drops the flag entirely, so the behaviour is correct regardless, but my Phase 1 tests wouldn't have failed on it.

## Fix process

I worked one module at a time, top-to-bottom against the spec rather than against the catalog. With `pytest --tb=short` driving, each fix was a small surgical edit: replace `_data[key].value = value` with full `_Entry` reconstruction (A4); flip `>` to `>=` for the FREESHIP threshold (A16); swap `ROUND_HALF_UP` for `ROUND_HALF_EVEN` (A18); rebuild the `total_cents` pipeline so BOGO → percent → FLAT5 → shipping fires in spec order (A14, A15). I deliberately rewrote `cart.total_cents` from scratch rather than patching individual lines, because the bugs were tangled across application order.

## Surprises

The `_bogo_applied_before_bagel` flag in the buggy source was the give-away — that's a code smell that doesn't map to any labeled bug, suggesting a hidden one I didn't think to write a test for. Lesson: when the spec says "if X exists at compute time," test the temporal ordering, not just the static case.
