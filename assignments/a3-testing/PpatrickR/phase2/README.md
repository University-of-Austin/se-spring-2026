# A3 Phase 2 — PpatrickR

172 Phase 1 tests, copied unchanged into `phase2/tests/`, all passing
against the fixed source in `phase2/src/`.

## What my tests caught vs. missed

Cross-referencing the catalog against the 83 failures my Phase 1 suite
produced against the unfixed source, every one of the 20 labeled bugs
had at least one failing test:

- **lru_cache (A1–A6)** — C5 promotion tests caught A1; C6 expire-on-get
  caught A2; C7 partial-expiration tests caught A3; C3 shorten-window
  caught A4; C4 eviction tests caught A5; the parametrized C1 raises
  caught A6.
- **interval_merger (A7–A12)** — C3 touching-endpoint tests caught A7;
  the C4 zero-length set caught A8; C6 no-mutation tests caught A9; C5
  empty-input pair caught A10; C2 unsorted-input tests caught A11; C1
  parametrized raises caught A12.
- **cart (A13–A20)** — C4 mutual exclusion (A13); C5 percent-then-FLAT5
  (A14); C5 clamp-at-zero (A15); C3 FREESHIP-at-threshold (A16); C3
  BOGO `qty//2` (A17); the C6 half-even rounding table (A18); C2
  case-sensitivity (A19); C7 empty-cart-no-shipping (A20).

Hidden bug status I won't know until grading.

## Fix process

I rewrote each module from the spec rather than patching bug-by-bug —
the catalog made it clear the source was deliberate per-clause
sabotage, so re-deriving each function was cleaner than chasing
individual failures. That took 83 failures to 0 in three edits.

## Surprises

A9 (mutating sort) silently masked A11 (input-order output) when both
were active in the all-on source — sorting the input made the
"input-order" reordering produce sorted output anyway. My C2 tests
still catch A11 on its own toggle, which is the configuration that
actually counts.
