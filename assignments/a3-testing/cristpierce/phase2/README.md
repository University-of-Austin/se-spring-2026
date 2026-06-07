# A3 Phase 2 — cristpierce

Phase 1 tests copied forward unchanged. Buggy source from
`starter/assignment3/phase2/src/` rewritten to spec until **200 tests pass**.

## Workflow

Ran the unfixed source against my Phase 1 suite first to see the failure
shape: 107 passed, 93 failed. Walked the bug catalog clause by clause,
matched each failure to the buggy line, then rewrote each module against
the spec rather than patching in place — the buggy versions had multiple
issues per function and a clean rewrite was easier to verify.

## Fixes by labeled bug

**lru_cache**

- A1 (C5) — `get` now calls `self._data.move_to_end(key)` before returning.
- A2 (C6) — `get` checks `entry.expires_at` against `time.monotonic()` and raises `KeyError` on expiry, also deleting the entry.
- A3 (C7) — `__len__` filters out expired entries via a fresh `time.monotonic()` reading on each call.
- A4 (C3) — re-put now updates `entry.expires_at = expires_at` along with `value`.
- A5 (C4) — eviction loop runs while `len >= capacity`, not `len >= capacity + 1`.
- A6 (C1) — `__init__` raises `ValueError` when `capacity < 1`.

**interval_merger**

- A7 (C3) — merge predicate is `s <= last_e`, so `(1,3)` and `(3,5)` collapse.
- A8 (C4) — removed the zero-length filter; `(3,3)` participates in merging and survives alone.
- A9 (C6) — sort a copy via `sorted(intervals, …)`, never `intervals.sort()`.
- A10 (C5) — `merge([])` returns `[]`.
- A11 (C2) — return `result` directly; dropped the input-position re-sort.
- A12 (C1) — validate `s <= e` first; raise `ValueError` on reversed.

**cart**

- A13 (C4) — `apply_code` rejects a percent code if any other percent code is already in `_codes`.
- A14 (C5) — percent applied before FLAT5.
- A15 (C5) — FLAT5 clamps subtotal at 0.
- A16 (C5) — FREESHIP threshold uses `>=`.
- A17 (C3) — BOGO free units = `qty // 2`.
- A18 (C6) — `ROUND_HALF_EVEN` for percent rounding.
- A19 (C2) — case-sensitive code match; dropped `.upper()` canonicalization.
- A20 (C7) — empty cart returns 0 unconditionally.

## Hidden bugs caught

- **H1 (lru_cache)** — `get` on a missing key now raises `KeyError` rather than returning `None`. Caught by `test_c6_get_missing_key_raises_keyerror`.
- **H2 (interval_merger)** — fully-contained intervals merge into the larger one. The buggy `s < last_e and e > last_e` predicate was a bug-on-bug: it broke both touching and subsumption. Caught by `test_c3_fully_contained_interval_merges`.
- **H3 (cart)** — BOGO_BAGEL evaluated at `total_cents` time. The buggy version flagged BOGO as "applied-but-no-effect" if applied before the bagel was added, and never recovered. Caught by `test_edge_apply_bogo_before_adding_bagel_then_apply_at_total`.

## What was easy, what was hard

Easy: lru_cache and cart bugs were one-line-per-bug fixes once the catalog
was mapped to the source. Hard: the cart's BOGO sticky-flag (H3) required
deleting state, not adding it — the bug was a piece of bookkeeping that
shouldn't exist in a correct implementation. Easy to overlook on a first
read because the flag *looks* like it's doing something useful.
