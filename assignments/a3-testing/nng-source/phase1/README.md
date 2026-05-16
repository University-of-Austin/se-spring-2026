# Phase 1 — Test-First Bug Hunt

128 tests, all passing against the clean implementation.

## Approach

Clause by clause. Tests are named after the clause they pin — `test_c1_capacity_zero_raises_valueerror`, `test_c5_freeship_uses_post_flat5_total` — so a failure points at the clause directly. I used the coding agent to re-read clauses and surface implications I'd glossed over, and to brainstorm "what about..." cases. I did not ask it to look at the bytecode or guess implementations.

## Coverage map

**lru_cache (42)** — capacity validation, put/get round-trip, KeyError on missing/evicted/empty, `__len__` (empty/growing/capped/expired-aware), LRU promotion on `get` and `put`-existing, eviction order, new-key insert doesn't reorder others, TTL with int/float/None, `__len__` excludes expired without `get`, `get`-on-expired raises *and* removes, re-put replaces value+TTL (clear/extend/shorten), expired entries don't occupy slots.

**interval_merger (31)** — single/disjoint/overlap/contained, touching endpoints merge, adjacent-but-not-touching stay separate, reversed tuple raises (alone/mixed/anywhere) and isn't silently swapped, empty input, output sorted, zero-length intervals merge correctly, input list and inner tuples not mutated, negatives, output type.

**cart (55)** — `add_item` validation (qty≥1, price≥0, no duplicate SKU), empty-cart-no-shipping, multi-line subtotals, `apply_code` returns bool, case-sensitive, same-code-twice rejected, percent codes mutually exclusive both ways, FLAT5 stacks regardless of apply order, BOGO `qty // 2` for 1/2/3/4 bagels, BOGO with no bagel returns True no effect, BOGO before bagel-add still applies (lazy per C3), FREESHIP at exact 5000 boundary and 4999, FREESHIP threshold uses post-FLAT5, FLAT5 clamps at 0, banker's rounding at half-cent.

## Edge cases I invented

`__len__` reflects expiry without `get`. Re-put with `ttl=None` clears a previous TTL; re-put with shorter TTL must shorten. Expired entries don't count toward capacity. `merge` doesn't mutate input or inner tuples. FREESHIP threshold uses *post-FLAT5* — pinned with a $54-with-FLAT5 cart that drops pre-shipping below $50. BOGO applied before bagels exist still applies at compute time. Banker's rounding pinned with subtotals where 10% lands on `.5` for both even and odd integers (25→2.5→2; 35→3.5→4), so naive `round()` and `floor()` bugs both fail visibly.

## What was easy, what was hard

Easy: pinning LRU order with eviction-triggering puts. Hard: testing the *absence* of behavior. `merge` not-mutating looks redundant when the return value is already correct, but it's a separate guarantee — deepcopy in, compare out. Distinguishing "FREESHIP threshold pre-FLAT5" from "post-FLAT5" took a specific $54-with-FLAT5 case; both readings agree on naive carts. And picking banker's-rounding subtotals took working backwards from the rule rather than forwards from arbitrary values.
