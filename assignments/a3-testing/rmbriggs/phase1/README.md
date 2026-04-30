# Phase 1 — A3 Test-First Bug Hunt

## Approach

Clause by clause. For each module I read the spec end-to-end, then walked C1 → CN asking: literal behavior, implied boundaries, and what the prose doesn't spell out. Tests are named after the clauses they pin down so the files read like an annotated spec.

The agent helped paraphrase clauses, surface boundary inputs (HALF_EVEN ties, post-discount FREESHIP thresholds), and check stacked-discount arithmetic. I kept it away from the `.pyc` files and stayed in-spec — testing unspecified behavior (tuple length, malformed inputs) risks failing the clean run without catching any seeded clause-bug.

## Coverage map

**`lru_cache` (52 tests):** capacity validation; put/get round-trip; TTL variants (None, positive, zero, negative); re-put clearing/shortening/extending TTL; LRU eviction with promotion via `get` and re-`put`; failed-get doesn't reorder; expired excluded from `len`; expiration frees capacity; non-string keys; per-instance state isolation.

**`interval_merger` (58 tests):** reversed tuples raise across every sign config and list position; sort across negatives + overlaps; touching merges (positives, negatives, zero-crossing, triple chains); adjacency rules; containment; multiple independent merge groups; zero-length variants; empty input; non-mutation **including the raise path**; same-start/end ties.

**`cart` (95 tests):** add_item validation + per-Cart state isolation; case-sensitive matching; per-code dedupe; bool-return per code; SAVE10/SAVE20 mutex both directions; full stacking matrix; BOGO at qty 1/2/3/4/5/100 + mixed cart; **FREESHIP threshold across every reduction path** (BOGO, SAVE10, SAVE20, FLAT5); FLAT5 clamp at 499/500; HALF_EVEN ties + SAVE20 + at scale; empty cart with every code; `total_cents` idempotence; lazy code evaluation.

## Edge cases I invented

- **FREESHIP eager-eval bug** — apply FREESHIP first while subtotal qualifies, then FLAT5 drops below; spec re-evaluates at total time, not at apply time.
- **`merge` input untouched on raise** — error-path mutation guarantee.
- **`total_cents` idempotent and non-freezing** — repeat calls match; later operations still take effect.
- **BOGO applied before bagel added** — proves BOGO evaluates lazily.
- **Cart instance isolation** — the class-vs-instance attribute trap.
- **Triple touching chain** and **multiple independent merge groups** in interval_merger.

## What was easy, what was hard

`interval_merger` was fastest — six clauses, self-contained math. `cart` was hardest: application order, FREESHIP threshold, and FLAT5 clamp interact across every reduction path. Testing the *absence* of behavior was the recurring step up — `merge` doesn't mutate on raise, `total_cents` doesn't accumulate state, LRU insertion doesn't reshuffle untouched keys, BOGO is "applied" with no bagel. The hardest single test to reason about was FREESHIP eager-evaluation — the spec implies lazy threshold-checking but never states it directly.
