# A3 Phase 1 — cristpierce

185 tests across the three modules, all passing against the clean
implementation with `BUGS` unset.

## Approach

Clause by clause. For each module I listed the numbered clauses and wrote
a section of tests for each before moving on. Test names mirror the clause
they pin down (`test_c4_evicts_lru_when_full`) so a failure maps back to a
sentence in the spec. After clause coverage I added an `edge` section for
behaviors the spec implies but doesn't spell out.

I used my coding agent to read the spec back to me ("what does C5 imply if
FLAT5 makes the post-discount value negative and FREESHIP is also
applied?") but never let it touch the `.pyc` modules or guess at the
implementation. Every test was derived from the spec, then validated
against the clean module.

## Coverage map

**lru_cache** — capacity validation (C1), put/get with and without TTL
(C2), re-put fully replaces value/TTL/expiration (C3), eviction-before-
insert (C4), LRU promotion via both `get` and re-put (C5), `KeyError` on
missing and expired (C6), `len` excluding passively-expired (C7).

**interval_merger** — reversed tuples raise without silent swap (C1),
output sort (C2), overlap/touching/adjacent semantics on closed intervals
(C3), zero-length intervals (C4), empty input (C5), no input mutation even
on the error path (C6).

**cart** — `add_item` validation incl. duplicate-SKU (C1), `apply_code`
truthiness, case-sensitivity, duplicates (C2), each of the five codes
(C3), stacking and mutex rules (C4), application order incl.
FLAT5-clamps-at-0 and the exact $50 FREESHIP boundary (C5), banker's
rounding at the half-cent (C6), empty-cart no-shipping (C7).

## Edge cases I invented

Input mutation on the error path (`merge` raising shouldn't stomp the
caller's list); expired entries not consuming a capacity slot;
`BOGO_BAGEL` accepted-but-no-effect when no bagel exists; FREESHIP
threshold against the post-FLAT5 value (5499 - 500 = 4999 must NOT waive);
banker's rounding on 0.5 / 1.5 / 2.5 / 3.5 cents to verify both half-even
directions; parametrized BOGO across odd and even quantities.

## What was easy, what was hard

Easy: anywhere the spec gave a worked example — the cart stacking rules
basically wrote themselves. Hard: testing for the *absence* of behavior.
"`merge` does not mutate its input" needs a deepcopy snapshot and a check
on both the list and the tuples. "Inserting a new key does not promote
others" required staging a state where the wrong promotion would only be
visible later. The half-even rounding took the most thinking — I had to
build subtotals where the discount landed exactly on a half-cent so the
rounding direction actually mattered.
