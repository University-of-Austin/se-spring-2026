# A3 Phase 1 — PpatrickR

172 tests across the three modules, all passing against the clean compiled
bundle.

## Approach

I read each spec straight through, then went back and treated every numbered
clause as its own pin-down target. Test names start with the clause they're
testing (`test_c4_eviction_when_full_drops_lru`, etc.) so the link back to
the spec is one click. I used my coding agent for spec interpretation —
pasting a clause and asking what edge cases it implies — and to scaffold
parametrize tables. I did not let it look at the .pyc files, decompile, or
guess at the implementation.

## Coverage map

**lru_cache** (43 tests) — capacity validation (C1), put/get/ttl basics (C2),
re-put fully replaces value+ttl+expiration (C3), eviction-when-full and
re-put-doesn't-evict (C4), get and put-on-existing both promote to MRU (C5),
KeyError on missing/expired (C6), len excludes expired entries even without
access (C7).

**interval_merger** (44 tests) — reversed tuples raise (C1), output sorted
(C2), overlap/touch merge but adjacent stays separate (C3), zero-length
intervals (C4), empty input (C5), no input mutation even on raise (C6).

**cart** (85 tests) — qty/price validation, duplicate-SKU raises (C1),
case-sensitive codes (C2), each known code's effect (C3), SAVE10/SAVE20
mutual exclusion plus other stacking (C4), application order with FLAT5
clamp at zero (C5), banker's rounding parametrized at every odd .5-cent
subtotal (C6), empty cart (C7).

## Edge cases I went looking for

- LRU re-put on a full cache must NOT evict (replace ≠ insert).
- Expired entries invisible to eviction — putting a new key doesn't drop a
  live entry if an expired one exists.
- `merge` not mutating input, even on ValueError mid-list.
- FREESHIP at exactly 5000 cents — included, not excluded.
- FLAT5 clamps to 0; FREESHIP can't waive shipping when pre-shipping is 0.
- Banker's rounding: 102.5 → 102, but 103.5 → 104 (parametrized).
- BOGO with no bagel still counts as "applied"; keyed to the literal SKU
  "bagel" (not "Bagel").

## What was easy, what was hard

The trickiest tests were the negative ones — proving `merge` doesn't mutate,
proving a re-put doesn't evict. You can't observe the absence of an event;
you set up state where the event would be visible if it happened, then check
the state didn't change. Banker's rounding was the other careful spot — a
parametrized table at every odd .5-cent subtotal so a "round-up"
implementation can't pass. Happy-path tests for each clause were mechanical;
the spec is clean enough that those wrote themselves.
