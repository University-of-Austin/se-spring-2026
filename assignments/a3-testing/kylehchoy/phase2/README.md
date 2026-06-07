# A3 Phase 2 — Fixes

## What my tests caught vs. missed

All 20 labeled bugs (A1–A20) were caught by my Phase 1 suite, and the three
hidden bugs are caught too — at least under the buggy-source-against-spec
audit. Mapping at a glance:

- **lru_cache (6 labeled)**: A1–A6 covered by clause-tagged tests
  (`test_c5_get_promotes_to_mru`, `test_c6_get_expired_raises_keyerror`,
  `test_c7_len_excludes_expired_without_explicit_get`,
  `test_c3_reput_with_ttl_none_clears_expiration`,
  `test_c4_eviction_at_capacity_removes_lru`,
  `test_c1_nonpositive_capacity_raises_valueerror`). Hidden — `get` on a
  missing key returning `None` instead of raising `KeyError` — caught by
  `test_c6_get_missing_raises_keyerror`.
- **interval_merger (6 labeled)**: A7–A12 covered by C1–C6 clause tests.
  Hidden — subsumed intervals (`(1, 100)` containing `(20, 30)`) failing to
  merge — caught by `test_c3_one_interval_contains_another` and
  `test_max_end_appears_earlier_than_min_start_in_input`.
- **cart (8 labeled)**: A13–A20 covered. Hidden — `BOGO_BAGEL` permanently
  disabled when applied before the bagel line is added — caught by
  `test_bogo_applied_before_bagel_added_takes_effect`.

Baseline against the buggy source: 100 failures, 114 passes. After fixes:
214/214.

## Fix process

I rewrote each of the three modules from the spec rather than patching the
buggy source bug-by-bug. The buggy implementations had bugs woven into the
control flow (e.g. cart's `_bogo_applied_before_bagel` flag, interval_merger's
post-merge re-ordering pass) where surgically extracting the bug would have
left dead state in the file. A clean rewrite from the C1–C7 clauses produced
shorter, more obviously-correct code, and the test suite was the verification
loop. One iteration cycle per module — write, run, all green.

## Surprises

The interval_merger H bug is broader than the catalog labels suggest. The
buggy `if s < last_e and e > last_e` rejects merging in three shapes:
subsumed intervals, equal-end overlaps, and identical duplicates. A single
clause-driven test on subsumption tripped all of them — clause-first beat
example-first.
