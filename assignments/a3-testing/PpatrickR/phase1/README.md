# A3 Phase 1 — PpatrickR

172 tests across the three modules, all passing against the clean compiled
bundle.

## Approach

I read each spec straight through once, then went back and treated every
numbered clause as its own pin-down target. Test names start with the clause
they're testing (`test_c4_eviction_when_full_drops_lru`, etc.) so going back
to the spec to ask "why does this test exist" is one click. I used my coding
agent for spec interpretation — pasting a clause and asking "what edge cases
does this imply that aren't called out" — and to scaffold parametrize tables.
I deliberately did not let it look at the .pyc files, decompile, or guess at
the implementation; I worked only from the spec.

## Coverage map

**lru_cache** (43 tests)
- C1 capacity validation (positive, zero, negative)
- C2 put/get/replace, ttl=None vs numeric, default ttl
- C3 re-put replaces value AND ttl AND expiration; ttl=None on re-put clears
- C4 eviction when full, len stays at capacity, re-put on existing doesn't evict
- C5 get and put-on-existing both promote to MRU; new-key insert doesn't reorder
- C6 KeyError on missing and on expired; expired entry removed
- C7 len excludes expired entries even without access

**interval_merger** (44 tests)
- C1 reversed tuples raise ValueError, no silent swap
- C2 output sorted by start, regardless of input order
- C3 overlap merge, touching-endpoint merge, adjacent-but-distinct stays separate
- C4 zero-length intervals: alone, merging in, two equal, two distinct, adjacent
- C5 empty input
- C6 input list/tuples not mutated, even on raise

**cart** (85 tests)
- C1 qty/unit_price validation, zero price allowed, duplicate-SKU raises
- C2 case-sensitive code names, duplicates and unknowns return False
- C3 each known code's basic effect, BOGO bagel quantities, FREESHIP threshold
- C4 SAVE10/SAVE20 mutual exclusion, FLAT5/BOGO/FREESHIP stack with everything
- C5 BOGO before percent, FLAT5 after percent, FLAT5 clamps at zero
- C6 banker's rounding (parametrized table at the .5-boundary subtotals)
- C7 empty cart returns 0, even with codes applied

## Edge cases I went looking for

- LRU re-put on a full cache must NOT trigger eviction (replace ≠ insert).
- Expired entry is invisible to eviction — putting a new key doesn't drop a
  live one if an expired one exists.
- `merge` not mutating its input even when it raises ValueError mid-list.
- Tuple identity preserved in input list (not just tuple equality).
- FREESHIP at exactly 5000 cents is the boundary — included, not excluded.
- FLAT5 clamps to 0; FREESHIP can't waive shipping if pre-shipping is 0.
- Banker's rounding: 102.5 → 102, but 103.5 → 104 (parametrized 8 values).
- BOGO with no bagel still counts as "applied" — duplicate returns False.
- BOGO is keyed to the literal SKU "bagel" — "Bagel" doesn't trigger it.
- Case-sensitive code names ("save10" → False).

## What was easy, what was hard

The trickiest tests were the negative ones — proving `merge` doesn't mutate,
proving a re-put doesn't evict. You can't observe the absence of an event
directly; you have to set up state where the event would be visible if it
happened, then check the state didn't change. The banker's rounding boundary
was the other place I had to think carefully — I made a parametrized table
at every odd .5-cent subtotal so the harness can't just trip a "round-up"
implementation; it has to round-half-to-even specifically. The straightforward
parts were the basic happy-path tests for each clause; the spec is clean
enough that those wrote themselves.
