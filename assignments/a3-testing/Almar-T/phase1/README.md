# A3 Phase 1 — Almar-T

92 tests across the three modules, organized clause by clause. All 92
pass under `pytest tests/ -v` against the clean implementation
(`BUGS=""`).

## Approach

I read each spec end-to-end before writing anything, then walked
clause by clause and wrote down the behaviors each numbered clause
implies. Test names follow `test_c<N>_<behavior>` so the spec clause
being pinned is always visible — `test_c5_get_promotes_to_mru` forces
me back to "what does C5 actually say" instead of "did this trip the
bug." I used my coding agent to brainstorm edge cases off the clause
wording, never to peek at the `.pyc` or guess at the implementation.

## Coverage map

**lru_cache** — capacity validation (0, negatives, cap=1 boundary);
basic put/get/len; TTL=None never expires; numeric TTL expires; re-put
replaces value, ttl, and clears expiration on `ttl=None`; re-put
resets the expiration clock; eviction order on full insert; re-put on
existing does NOT evict; both get and put-on-existing promote to MRU;
new-key insert does not reorder existing; KeyError on missing and
expired; expired entries actually removed; len ignores expired
entries even before access.

**interval_merger** — single, two-disjoint, four-disjoint inputs all
returned intact; spec's canonical example; ValueError on `(5,1)`,
`(5,3)`, and reversed buried in a valid list; output sort with and
without merging; overlap, touching endpoints, gap-of-one adjacency,
full containment; zero-length alone, contained, duplicated; empty
input; no input-list mutation; returned list is a new object; output
elements are tuples.

**cart** — qty/price/duplicate-SKU validation; case-sensitive codes;
duplicate apply returns False; each code isolated; SAVE10/20 mutex
both orders; seven stacking pairs plus all-four-stackable; FLAT5
clamp at 0; FREESHIP boundary at 4999/5000; banker's rounding hitting
`.5` (5→0, 15→2, 25→2); empty cart with and without codes; four spec
worked examples verbatim.

## Edge cases I invented

The hidden hunts: a cache full of expired entries should accept new
inserts without evicting (C4 × C7 interaction); FLAT5 clamping to 0
disqualifies FREESHIP (threshold checked AFTER clamp); `BOGO_BAGEL`
with no bagel still counts as applied; `BOGO_BAGEL` with qty=1 grants
0 free; reversed `(5,3)` raises even though it would be "valid" if
silently swapped.

## What was easy, what was hard

Easy: clause-by-clause behavior tests and parametrize for validation.
Hard: testing the *absence* of behavior — "does not mutate" and
"does not trigger eviction" — required imagining a buggy
implementation and constructing the assertion that catches it.
Banker's rounding was the fiddliest: half-cent subtotals depend on
the neighbour's parity for tie-breaking.
