# A3 — Phase 1 (Durp06)

## Approach

Clause by clause. One test section per spec clause, names like
`test_c5_bogo_applied_before_percent` so a failure points at the spec
line it defends. The agent helped me interrogate the spec — "what does
this rule out?", "what's the boundary?" — but never read the `.pyc`.
TTL tests use real sleeps (50–200 ms). For banker's rounding I picked
SAVE10 subtotals (5, 15, 25, 35, 45) where ROUND_HALF_EVEN diverges from
both half-up and trunc.

## Coverage map

**lru_cache.** C1 capacity validation; C2 put/get + ttl (None / numeric
/ int); C3 re-put replacement, `ttl=None` clearing a prior expiry,
shorter-supersedes-longer; C4 eviction on full-insert, re-put doesn't
evict; C5 get-promotes, re-put-promotes, new-key doesn't reorder
survivors; C6 `KeyError` on missing/expired plus the slot-freeing side
effect of an expired `get`; C7 len ignores expired entries and counts
re-puts after expiry as fresh.

**interval_merger.** C1 reversed-tuple raises with no silent swap; C2
sort order regardless of input order; C3 overlap, touching endpoints,
gap-of-one separation, contained, chains, three-way, negatives; C4 zero-
length intervals (alone, inside, on endpoint, disjoint, equal); C5
`merge([])`; C6 no mutation across success / error / empty paths.

**cart.** C1 qty/price validation and dup-SKU; C2 case sensitivity and
duplicate apply across all five codes; C3 each code in isolation; C4
SAVE10/SAVE20 mutual exclusion in both orders; C5 BOGO-before-percent,
FLAT5-after-percent, FLAT5 clamp at 0, FREESHIP threshold tested at
4999/5000/5001 and against a post-discount total; C6 banker-rounding
table; C7 empty-cart total.

## Edge cases I invented

- Expired `get` must free the slot; tested by filling around it.
- `len` should forget an expired entry without needing a prior `get`.
- After a new-key insert, survivors' relative order must hold — checked
  by triggering a *second* eviction and asserting the right next-oldest
  key falls.
- `merge` mustn't mutate its input on the error or empty paths, and
  must return a new list (not a reference to the input).
- FREESHIP threshold uses the post-discount total ($50 + SAVE10 → 4500
  < 5000 → ship still applies).
- FLAT5 clamp reached three ways: low subtotal, post-percent, post-BOGO.
- Rounding inputs chosen so half-up and trunc both fail.

## Easy / hard

Easy: C1/C2 validation is one-liners. Hard: absence-of-behaviour tests.
Snapshotting the list, asserting equality on exit, *and* on the error
path, takes more discipline than asserting a return value. Cart ordering
tests were tricky — "BOGO before percent" only catches the bug if the
two orderings yield different totals, so inputs had to be picked to
diverge.
