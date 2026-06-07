# A3 Phase 1 - Kyle Choy

## Approach

I read the three specs clause by clause, then made a second pass through three lenses: boundaries, absence/no-op behavior, and interactions between rules. I used my coding agent only to reason from the written specs and brainstorm spec-implied cases. I did not inspect bytecode, probe bug names, or tune tests against observed buggy behavior. Every test is meant to trace to a clause or to a defensible implication of one.

## Coverage Map

- **LRU (64 collected tests):** capacity validation, put/get/replace, ttl=None vs numeric TTLs, re-put replacement of value and expiration, eviction at capacity, get/put promotion, missing and expired KeyError behavior, len excluding expired entries, cap=1 churn, expired-entry cleanup, falsey keys/values, tuple/hash-colliding/equal-distinct keys, object values, fixed TTL windows, and long promotion sequences.
- **Interval merger (49 collected tests):** reversed intervals, malformed entries, output ordering, overlap/touching/adjacent semantics, zero-length intervals, empty input, input non-mutation, nested/duplicate intervals, negative ranges, large bounds, same-start intervals, permutation invariance, and canonical output shape.
- **Cart (101 collected tests):** item validation, invalid-add no-ops, duplicate SKUs, known/unknown/case-sensitive codes, duplicate and conflicting code rejection, each promo's individual effect, stacking, fixed application order, FLAT5 clamp, FREESHIP threshold boundaries, banker rounding, empty carts, mixed carts, BOGO floor division, exact lowercase bagel targeting, empty-string SKUs, code-order independence, and rejected-code no-ops.

## Edge Cases I Invented

- Falsey LRU keys and values (`0`, `""`, `None`, `False`) still round-trip; missing is represented by `KeyError`, not truthiness.
- Hash-colliding LRU keys remain distinct, while equal-but-distinct key objects address the same cache entry.
- Missing LRU lookups do not perturb the live eviction order.
- LRU `get` promotes recency but does not renew the original TTL window.
- LRU `len()` cleanup of expired entries does not reorder live entries.
- Merger non-mutation applies on error paths too, catching implementations that sort before validating.
- Same-start intervals with different ends merge to the largest end.
- Empty-string cart SKUs are still valid line items and still participate in duplicate detection.
- Promo codes applied before items still affect later totals, because `total_cents` evaluates current cart state.
- `total_cents` is not cached: later item additions and later code applications must change subsequent totals.
- `FLAT5` clamping a non-empty cart to zero does not make `FREESHIP` effective.
- Invalid item additions and duplicate SKU attempts do not reserve or replace lines.
- Duplicate FLAT5, BOGO, percent, and FREESHIP applications are no-ops, not just `False` return values.

## What Was Easy / Hard

The easy part was translating direct clauses into assertions. The hard part was finding absence tests: "does not mutate," "does not disturb LRU order," "does not double-apply," and "does not cache stale totals" require setups where the wrong implementation would visibly diverge. Rounding also needed care, so percent expectations use `Decimal` with `ROUND_HALF_EVEN` instead of hand math.
