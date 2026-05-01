# Phase 2 Bug Hunt — Durp06

## What your tests caught vs. missed

**lru_cache** — Caught: A1, A2, A3, A5, A6. Missed: A4 (TTL replacement on
re-put). Two C3 tests passed on the buggy code because they did not exercise
the stale-expiry path after a re-put; A4 only became fully visible when
fixing the expired-entry path.

**interval_merger** — Caught: A7, A8, A9, A10, A12. Missed: A11 (re-order
output by input position). The buggy reordering produced correct results for
all sorted or near-sorted test inputs, so no test fired on it. It was caught
only during the spec re-read in Task 4.

**cart** — Caught: A13, A14, A15, A16, A17, A18, A19, A20. Missed: none.
All eight cart bugs triggered failing tests on the baseline run.

## Fix process

Fixes were applied one module at a time, spec-clause-by-clause, using the
plan table as the checklist. Each module's full test file was re-run after
every edit before moving on. The recommended `total_cents` structure from
the plan (empty-check, subtotal, BOGO, percent, FLAT5 clamp, shipping) was
followed exactly, making the ordering bugs A14 and A15 straightforward to
resolve without rework.

## Surprises

The spec re-read surfaced three corners the catalog wording skipped. For
the interval merger, fixing A9 (mutating `intervals.sort()`) also fixed A11
as a side effect, since removing the in-place sort forced rebuilding a fresh
sorted copy that rendered the input-position reorder block dead code. For
the LRU cache, the eviction loop correctly uses the physical dict `len`,
not the filtered `__len__`: expired entries occupy physical slots and count
toward capacity until freed. For the cart, the FREESHIP comparison naturally
operates on the already-mutated `subtotal` after FLAT5 and clamping, so the
post-FLAT5 threshold check was correct once the application order was fixed.
