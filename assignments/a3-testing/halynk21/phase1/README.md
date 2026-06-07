# A3 Phase 1 — Test Suite README

## Approach

Clause by clause for each spec. For each clause I asked what the exact behavior was, what the boundary values were, and what a wrong implementation would do. I used an AI coding agent to reason through edge cases implied by each clause — not to look at the implementation. Every test derives from the spec text, not from observed module behavior.

Tests are named by clause (`test_c3_...`) and multi-case clauses are parametrized. I verified each file passes the clean module before moving on.

## Coverage Map

**lru_cache:** C1 capacity validation, C2 put/get/overwrite/ttl=None, C3 re-put clears and supersedes TTL, C4 eviction identity and len invariant / re-put at capacity does not evict, C5 get and put-existing both promote to MRU, C6 expired and missing both raise / len behavior around expired get, C7 len excludes expired with and without access

**interval_merger:** C1 reversed raises / equal endpoints valid, C2 unsorted → sorted, C3 overlap / touching / adjacent / nested / chain / negatives (parametrized), C4 zero-length standalone and merged, C5 empty input, C6 contents not mutated / order not mutated (two tests). Note: `test_c1_equal_endpoints_valid` and `test_c4_zero_length_standalone` both assert `merge([(3,3)]) == [(3,3)]` — intentional duplication; each frames the same input from a different clause perspective.

**cart:** C1 qty and price validation / duplicate SKU, C2 unknown / lowercase / all five duplicate-rejected (parametrized), C3 SAVE10/20 / BOGO qty 1–5 (parametrized) / BOGO no-bagel sku / FREESHIP at 4999/5000/6000, C4 percent mutual exclusion both orders, C5 FLAT5 after percent / BOGO before percent / shipping / FLAT5 clamped / FREESHIP threshold post-discount and post-FLAT5, C6 ROUND_HALF_EVEN in both rounding directions, C7 empty cart

## Edge Cases Invented

- **LRU ttl=0**: C2's formula means expiry equals put-time; entry is immediately expired.
- **LRU expired-get ordering**: after removing an expired entry via get(), subsequent evictions must still pick the correct oldest live entry.
- **LRU re-put on expired key**: C2 says "inserts or replaces" with no expiry qualifier.
- **interval_merger duplicate intervals**: `[(1,5),(1,5)]` → `[(1,5)]` per C3 overlap.
- **interval_merger adjacent zero-lengths**: `[(2,2),(3,3)]` stays separate — C3 adjacent applied to zero-length inputs.
- **interval_merger zero-length at boundary**: `[(1,5),(5,5)]` → `[(1,5)]` — C3 touching and C4 zero-length combined.
- **Cart BOGO before bagel added**: C3 says discount is evaluated "when total_cents is computed."
- **Cart zero-price item triggers shipping**: C1 allows price=0; C5 adds shipping for any non-empty cart.
- **Cart FREESHIP with zero subtotal**: 0 < 5000, so shipping still applies despite code being active.
- **Cart duplicate BOGO no bagel**: C3 says the code is "still considered applied for C2's duplicate rule."

## What Was Easy, What Was Hard

interval_merger was most direct — clauses map almost one-to-one to tests.

Hardest was testing absence of behavior. The mutation tests have no return value; you compare a copy of the input before and after, and correctness depends entirely on when the copy is made.

The rounding tests needed values in both rounding directions (1005→100, 1015→102) because either alone doesn't distinguish ROUND_HALF_EVEN from floor or ceiling.

Sharpest tradeoff: combining C4 ("evict when len == capacity") with C7 ("len excludes expired") implies expired entries shouldn't count toward the eviction trigger — but the clean module evicts on raw storage count, so a test pinning that interaction would have failed the clean-run gate. I kept a single-clause C2 boundary test (ttl=0) as the third hidden test instead.
