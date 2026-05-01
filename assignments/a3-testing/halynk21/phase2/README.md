# A3 Phase 2 — Fix-Up README

## What my tests caught vs. missed

All 20 labeled bugs from the catalog map to clauses I tested in Phase 1, with at least one test per bug that fires when only that bug is active.

For hidden bugs (one per module): `test_hidden_bogo_applied_before_bagel_added` catches the cart hidden bug — the buggy source uses an `_bogo_applied_before_bagel` flag that disables BOGO if BOGO is applied before bagel is added. For lru_cache, the buggy `get` returns `None` for missing keys instead of raising `KeyError`; `test_c6_missing_key_raises_key_error` catches this. For interval_merger, my hidden tests trip on labeled bugs in the all-bugs baseline, so I can't isolate which one catches a hidden bug.

## Fix process

I read each source file clause by clause against the spec, then rewrote each module rather than patch in place — the buggy versions had structural choices (cart's `_bogo_applied_before_bagel` flag, interval_merger's broken reorder-by-input-position pass) that were cleaner to remove than to surgically correct.

Order: cart first (most surface area, densest coverage), then lru_cache, then interval_merger. After each module I ran the full test suite to confirm no regression. No fix turned a passing test red.

## Surprises

The cart hidden bug is the most spec-faithful trap. The spec says "if no bagel line item exists when total_cents is computed" — note "when computed", not "when apply_code is called". The buggy code violates this with a flag set at apply_code time. My Phase 1 hidden test caught it because I asked "what does 'when computed' mean?" rather than testing only the obvious BOGO-with-bagel scenarios.

Pre-submission prediction: I expect the reference suite to pass on all 20 labeled and 2 of 3 hidden; interval_merger is my most plausible miss given uncertain attribution there.
