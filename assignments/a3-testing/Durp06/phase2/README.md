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

Two hidden corners surfaced on spec re-read. Cart C3 anchors the
bagel-presence check at `total_cents()` time, but the buggy starter
latched state at `apply_code()` via a `_bogo_applied_before_bagel`
flag — apply BOGO before adding the bagel and the discount stayed
zeroed. Removing the flag fixed it. LRU `put()` originally evicted by
physical dict size, but spec C4 references `len(cache)` which per C7
excludes expired entries — so a still-valid LRU could be evicted while
an older expired entry kept its slot. Reaping expired entries before
the eviction loop fixed it. For the merger, dropping the in-place
`intervals.sort()` (A9) made the input-position reorder (A11) dead.
