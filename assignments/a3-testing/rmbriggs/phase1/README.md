# Phase 1 — A3 Test-First Bug Hunt

## Approach

Clause by clause. For each module I read the spec end-to-end, then walked C1 → CN asking: literal behavior, implied boundaries, what the prose doesn't spell out. Tests are named after the clause they pin down (`test_c4_eviction_when_full_evicts_lru`, `test_c6_save10_rounds_half_even`) so the files read like an annotated spec.

Used the agent to paraphrase clauses, surface half-cent inputs that distinguish HALF_EVEN from HALF_UP, and double-check stacked-discount arithmetic. Did not use it on the `.pyc` files — the point is a spec-driven suite, not an implementation-shaped one.

## Coverage map

**`lru_cache`:** capacity validation; put/get round-trip; replacement keeps `len` constant; TTL=None vs positive TTL; re-put clearing/shortening TTL; LRU eviction at capacity; `get` and re-`put` promote to MRU; new insert doesn't disturb existing order; `get` on missing/expired raises and removes; `len()` excludes expired-but-unaccessed; capacity=1; non-string hashable keys.

**`interval_merger`:** reversed tuple → `ValueError`; sort order; touching endpoints merge; adjacent endpoints stay separate; overlap chains; full containment; zero-length intervals (alone, inside, at endpoints, coincident, adjacent); empty input; input non-mutation via deep-copy snapshot; negatives; large gaps.

**`cart`:** invalid qty/price; duplicate SKU; case-sensitive codes; double-application rejected; SAVE10/SAVE20 mutually exclusive both orderings; FLAT5 stacks with each percent code; BOGO_BAGEL at qty 1/2/3/4 and with no bagel; FREESHIP at exactly 5000, at 4999, and across the threshold via SAVE10/FLAT5; FLAT5 clamp at zero; banker's-rounding parametrize at 1005/1015/1025/1035; empty-cart with/without codes.

## Edge cases I invented

- `merge` mutation check uses a deep-copy snapshot, so even an in-place re-sort gets caught.
- Banker's-rounding parametrize at four subtotals where HALF_UP and HALF_EVEN diverge on every row.
- FREESHIP boundary tested directly (`subtotal=5000`) and indirectly via FLAT5 (`5500 → 5000` waives; `5499 → 4999` does not).
- LRU re-put with `ttl=None` after a previous TTL was set, then sleeping past the old TTL — pins down "passing ttl=None clears the expiration."
- "New insert doesn't reshuffle order" tested via two-step eviction: put d evicts a, put e must evict b.

## What was easy, what was hard

`interval_merger` went fastest. `cart` was hardest — application order and the FREESHIP threshold interact, since FREESHIP looks at the post-FLAT5 subtotal and the boundary itself is moveable. Testing for the *absence* of behavior was a step up: that `merge` doesn't mutate, that LRU insertion doesn't reshuffle others, that BOGO_BAGEL is "applied" with no bagel. Each needed sequences that fail loudly when the invariant is violated. Banker's rounding was unintuitive until I worked out which subtotals produce a half-cent tie.
