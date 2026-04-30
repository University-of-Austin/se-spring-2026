# A3 Phase 1 — Test-First Bug Hunt

## Approach

I read the assignment PDF first and brainstormed tests on my own before opening the
per-module specs. Then I worked through each spec **clause by clause**, naming tests `test_c<N>_<behavior>`. Andy had front-loaded a decent chunk of work here. The PDF's "things you'll want to test" guidance is already a near-checklist of the bug-rich surfaces (TTL replacement, eviction-when-full, input-mutation, percent rounding, etc.), and the numbered spec clauses are written so each claim is its own discrete bug-hunt target.

Workflow with the coding agent: I described in plain English which cases I thought
should be tested and why, and the agent wrote the actual test code. I then pushed back
on whether each proposed test was earning its keep, explicitly trying not to over-test
(redundant cases, gilded parametrize lists, smoke tests already covered elsewhere). The
agent was used as a sparring partner for brainstorming and clean implementation probing. `@pytest.mark.parametrize` was used where two tests differed only in input and kept separate when *intent* differed.

## Coverage map

### lru_cache (C1–C7 done)
- **C1**: cap=1 round-trip; parametrized rejection of `[0, -1, -5, -100]`.
- **C2**: insert/retrieve, value-replace, `ttl=None`, int/float TTL alive, float TTL expired, multiple keys, parametrized nonpositive ttl `[0, 0.0, -1, -0.001]`.
- **C3**: finite→longer, finite→None, None→finite, same-ttl clock reset.
- **C4**: full+new evicts oldest, re-put doesn't evict, cap=1 edge, multi-overflow.
- **C5**: `get` promotes, `put`-on-existing promotes, new-insert preserves survivor order, multi-use sequence.
- **C6**: missing raises, expired raises, expired-then-reput is fresh, get-on-expired doesn't revive (len stable), get-on-expired frees the capacity slot (Path B).
- **C7**: len excludes expired-unaccessed, mixed expired/alive count, all-expired→0, cap=1 cycle, re-put doesn't increment len.

### interval_merger (C1–C6 done)
- **C1**: valid intervals don't raise (incl. `(0, 0)` zero-length, negative-start), parametrized rejection of reversed tuples `[(5, 1), (10, -3), (0, -1)]`, mixed valid+invalid still raises.
- **C2**: parametrized over already-sorted, reverse-sorted, and random-order — all produce the same canonical sorted output.
- **C3**: overlap, touching endpoints merge, adjacent endpoints don't merge, contained absorbed, chain spans min→max, identical collapse.
- **C4**: parametrized zero-length alone-returned `[3, -3, 0]`, parametrized merging-positions (contained, left-touch, right-touch), adjacent zero-lengths stay separate.
- **C5**: empty input returns `[]`.
- **C6**: parametrized no-mutation over sort+merge / no-merge / zero-length paths.

### cart (C1–C7 done)
- **C1**: parametrized valid `add_item` (incl. unit_price=0 free items), parametrized invalid qty `[0, -1, -100]` and unit_price `[-1, -500]`, duplicate-sku raises, distinct skus coexist.
- **C2**: parametrized known codes return True (all 5), parametrized unknown/wrong-case return False `["BOGUS", "save10", "SAVE", ""]`, duplicate apply returns False.
- **C3**: parametrized SAVE10/SAVE20 percent, parametrized FLAT5 with clamp at 0, parametrized BOGO `qty // 2` floor-division (qty=1..4), BOGO with no bagel returns True (no effect), parametrized FREESHIP threshold at 4999/5000/5001.
- **C4**: parametrized save mutex both directions, first-save-takes-effect, parametrized 9 stacking pairs, parametrized 3-code combos, 4-code maximum stack.
- **C5**: BOGO before percent, percent before FLAT5 (PDF example), FREESHIP threshold uses post-FLAT5 total, full pipeline integration.
- **C6**: parametrized banker's rounding at 4 half-cent boundaries (25, 35, 45, 55).
- **C7**: parametrized empty-cart total=0 across no-codes / FLAT5-only / max-stack.

## Edge cases invented

- **`-1` capacity** as a parametrize case — catches off-by-one like `if cap < -1`.
- **Float TTL alive** (`ttl=0.5`, sleep `0.05`) — catches `int(ttl)` truncation.
- **Same-ttl clock reset** — pins "expiration time superseded" separately from "ttl superseded."
- **None → finite ttl re-put** — catches a sticky "never expires" flag.
- **Re-put on full does NOT evict** — diagnostic for the "every put evicts when full" shape.
- **Get-on-expired doesn't revive** — second get still raises; len stable across both.
- **Get-on-expired frees the capacity slot** — pins C6's "removes the entry" sub-clause via Path B in the C4×C7 narrative below.

## What was easy, what was hard

Clause-by-clause made breadth easy. The hardest tests were at clauses naming multiple
things in one sentence: C3's "value, TTL, and expiration time" required the same-ttl
clock-reset construction to distinguish ttl-supersedure from expiration-time-supersedure.

The most instructive moment was probing the **C4 × C7 cross-clause** behavior. C4 says
eviction triggers "when `len(cache) == capacity`" and C7 defines `len` as the non-expired
count — so strictly read, expired entries shouldn't fill slots toward the eviction
trigger. The clean impl violates this: `len()` filters correctly, but the eviction
trigger uses raw dict size.

Concrete demonstration at cap=2:

| Step                       | Path A (no pre-cleanup)              | Path B (get expired first)                      |
| -------------------------- | ------------------------------------ | ----------------------------------------------- |
| Initial state              | `{a alive, b expired}`, len=1, raw=2 | `{a alive, b expired}`, len=1, raw=2            |
| Optional cleanup           | (skipped)                            | `get("b")` → raises, **physically removes `b`** |
| State after cleanup        | `{a alive, b expired}`, raw=2        | `{a alive}`, raw=1                              |
| Put `c` triggers eviction? | yes (raw==2==cap) → evicts `a`       | no (raw==1 < cap) → just inserts                |
| Final state                | `{c alive}`, len=1                   | `{a alive, c alive}`, len=2                     |

Path B aligns with the strict spec reading; Path A doesn't. We can't assert "Path A is
buggy" (clean fails it), but Path B *can* be tested — pinning C6's "removes the entry"
sub-clause via the resulting eviction behavior. Lesson: use the clean module as a
validation oracle for spec-readings, not a source of truth for ambiguous behavior — and
probe carefully, because the workaround often pins what the strict version can't.
