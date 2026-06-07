# Assignment 3 Phase 1: Test-First Bug Hunt

## Approach

Clause by clause through each spec, naming every test after the clause it
pins down (`test_c3_touching_endpoints_merge`) so the file reads as a
checklist. After clause coverage I did a second pass for implied
behaviors: input mutation, `len()` on expired-but-untouched entries, BOGO
with non-bagel items. I never decompiled the .pyc, never read phase 2
source or the bug catalog. My coding agent helped me think through what
each clause implied; every test was written from the spec.

I did phase 1 late. Neither I nor Claude saw the phase 2 files nor the bug catalog file.

## Coverage map

**`interval_merger`** (19 tests, all 6 clauses): 
- C1 validation
- C2 sort order
- C3 overlap, full containment, touching, adjacent (do not merge), chain collapse 
- C4 zero-length intervals in five positions
- C5 empty input 
- C6 input list not mutated, even when merging actually runs.

**`lru_cache`** (30 tests, all 7 clauses): 
- C1 capacity validation
- C2 put/get round-trip and ttl = None never expires
- C3 re-put TTL replacement in four directions
- C4 eviction picks LRU and length stays at capacity
- C5 use tracking on both get and put, with new-key inserts not promoting other keys
- C6 expiration on `get` plus removal
- C7 length excludes expired entries even without access.

**`cart`** (45 tests, all 7 clauses): 
- C1 validation including zero-price boundary
- C2 apply_code returns including case sensitivity 
- C3 each code in isolation including the FREESHIP 5000/4999 boundary 
- C4 stacking with both orderings of SAVE10/SAVE20
- C5 application order (BOGO before percent, FLAT5 after, clamp at 0, FREESHIP threshold on post-discount)
- C6 half-even rounding at 0.5, 1.5, 2.5, 3.5 cents
- C7 empty cart with and without codes

## Edge cases invented by Claude

- `lru_cache` C7 tests deliberately never call `get` on the expired key
  before checking `len`, catching the lazy-purge-on-access bug class.
- `interval_merger` C6 tests check input is unchanged after a real merge
  has run, not just the no-op case.
- `cart` half-cent rounding sweeps all four .5 cases (0.5, 1.5, 2.5, 3.5)
  to distinguish half-even from both half-up and half-down.
- FREESHIP threshold tested at exactly 5000 (waiver) and 4999 (no waiver)
  on both raw and post-discount pre-shipping totals.
- BOGO_BAGEL with no bagel SKU verifies the spec's "applied but no
  effect" rule against C2's duplicate-rejection.

## Easy vs hard

Easy: clauses that are equality assertions on a return value. C1
validation across all three modules wrote itself.

Hard: testing for the absence of behavior. Mutation tests need
snapshotting and comparing. The "length without access" tests required
imagining a buggy implementation and writing a test that only fails under
it. The half-even rounding sweep took longest because I had to reason
about which rounding modes a sloppy impl might produce, then pick
subtotals that distinguished all of them.