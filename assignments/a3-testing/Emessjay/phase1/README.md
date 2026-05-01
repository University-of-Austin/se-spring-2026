# A3 Phase 1 — Emessjay

## Approach

I read each spec strictly clause by clause (C1, C2, ...) before writing any
test. For every clause I wrote a dedicated `TestC<n>...` class so the test
names tie directly back to spec sections — that way, when the catalog drops,
mapping bug→clause→test is mechanical instead of archaeological.

I used the coding agent for two things: helping me re-read each clause out
loud and asking "what does this imply that it doesn't say?", and writing the
mechanical scaffolding (parametrize lists, repetitive structural assertions).
I deliberately did NOT let it look at the bytecode, decompile the `.pyc`, or
guess bug names — the whole pedagogical point of Phase 1 is that the tests
should be derived from the spec, not from the implementation. Where I caught
the agent leaning toward "let's enumerate the bug list", I redirected back to
the spec.

## Coverage map

**`cart`** (191 tests, clauses C1–C7):
- C1 add_item validation: qty/price ranges, duplicate-SKU rejection, partial-state-on-failure invariants.
- C2 apply_code semantics: unknown / duplicate / case-sensitive / whitespace-strict / near-miss codes.
- C3 each code's effect: SAVE10/20 percent, FLAT5 subtraction & zero-clamp, BOGO_BAGEL math (qty=1, odd qty, no-bagel, sku case-sensitivity), FREESHIP at/above/below the $50.00 threshold.
- C4 stacking: SAVE10⊥SAVE20 (both directions), FLAT5 stacks with both, BOGO/FREESHIP stack with everything; rejected stacks don't mutate; double-application doesn't double-discount; full triplet/quadruplet matrix.
- C5 application order: BOGO before percent; percent before FLAT5; FLAT5 not against shipping; percent not against shipping; FLAT5 clamp doesn't engage FREESHIP; threshold uses post-FLAT5 number.
- C6 banker's rounding: 20-point half-even sweep, dedicated truncate/half-up discriminators, half-even on post-BOGO subtotals.
- C7 empty cart: zero with any/all codes; no shipping.

**`lru_cache`** (94 tests, clauses C1–C7):
- C1 capacity: ValueError on 0/negative, cap=1 works, cap=1000 works.
- C2 put: default ttl=None, explicit None, int/float ttl values, value replacement.
- C3 TTL replacement: re-put with None clears expiry, re-put with new ttl resets the clock, re-put from no-ttl to ttl, re-put from longer to shorter.
- C4 eviction: LRU (not FIFO, not MRU); cap=1 evicts immediately; re-put never evicts; far-past-capacity keeps last N.
- C5 use tracking: get and put-on-existing both promote; new put doesn't reorder; long alternating get/put chains pinned step by step.
- C6 expiration: get-on-expired raises KeyError AND removes; get-on-missing raises KeyError; exact KeyError type contract; no silent None on miss.
- C7 length: excludes expired even before access; consistent across calls; never exceeds capacity.
- Cross-clause: TTL is anchored to put time (get doesn't refresh); per-entry TTL independent; expired entries don't force eviction of live ones; falsy values (`0`, `""`, `[]`, `None`, `False`) round-trip without being treated as missing.

**`interval_merger`** (114 tests, clauses C1–C6):
- C1 validation: reversed tuples raise ValueError, no silent swap, validation runs before any partial output.
- C2 sort: any input order yields ascending-by-start output.
- C3 merge semantics: overlap, touching endpoints, adjacent integers stay separate, chains, full containment, min-start/max-end.
- C4 zero-length: `(k, k)` valid, merges with overlapping, adjacent zero-lengths stay separate, two same-int zero-lengths collapse.
- C5 empty: `merge([])` returns `[]`.
- C6 no mutation: input list and tuple identity preserved across all paths (success, validation error, already-canonical input).
- Stress: 100-link touching chain, 50 disjoint pairs, deeply nested containment.
- Structural properties: output strictly disjoint, every input endpoint covered, output covers nothing the input didn't.

## Edge cases I invented

- **Cart**: half-even rounding sweep with a discriminator at every `.5` cent; `bagel×2@5500` → SAVE10 (rounds 555.5 → 556 because 556 is even) → land exactly at FREESHIP boundary `4999` (just under). `BOGO_BAGEL` is exactly `qty // 2` free, distinguishing `(qty-1)//2`, `qty//2 + 1`, and "half off bagel line" with qty=3. Apply-order symmetry across all 24 permutations of the four-code stack.
- **Cart**: rejected stacks don't mutate active state — `SAVE10 → SAVE10 (dup) → SAVE20 (conflict)` keeps SAVE10's effect.
- **Cart**: FREESHIP threshold strict-`>=`, with FLAT5-clamped-to-0 explicitly *not* engaging it.
- **lru_cache**: `get` is a use-tracker but doesn't refresh TTL (the spec ties expiration to put time); `get` on the MRU 100 times doesn't promote anyone else; falsy values (`0`, `None`, `False`) must round-trip rather than be confused with "missing"; expired entries don't trigger eviction of live ones because they don't count toward `len`.
- **interval_merger**: validation runs before any partial sort/output (input list order preserved on error); structural property "output intervals are strictly disjoint with `end[i] < start[i+1]`" catches whole categories of merge bugs at once; same-start tiebreaker collapses to the max end.

## What was easy, what was hard

The happy-path tests for each spec clause were straightforward — read the
clause, write the test, move on. The genuinely harder work was three things:

1. **Testing for the *absence* of behavior.** "This function doesn't mutate
   its input" is not something you can assert in one line — you need to
   snapshot, run, compare, and do it across every code path including the
   error path. Same for "rejected codes don't silently replace the active
   one" — you have to test the replacement *didn't* happen by checking
   downstream effects.
2. **Half-even rounding.** It's easy to write *a* test for banker's
   rounding; it's harder to write tests that distinguish half-even from
   truncate, ceil, half-up, and half-down. Each rounding mode disagrees
   with half-even at a specific subset of `.5` boundaries — the 20-point
   sweep is overkill but it pins all four wrong-mode bugs at once.
3. **Structural property tests for merge.** Writing "output intervals
   are strictly disjoint" as a single assertion took longer than the dozen
   case-by-case tests it replaces, but it catches bug categories the
   case tests don't.

The TTL timing tests were also fiddly — short enough to keep the suite
fast, long enough that machine jitter doesn't flake them. I settled on
30–50ms TTLs and 60–100ms sleeps, comfortably 2× the TTL.
