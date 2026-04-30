# Phase 1 — Sam-Indyk

## Approach

I worked clause-by-clause from each spec. For every numbered clause (C1, C2, ...) I first wrote the obvious-positive test that pins down the spec text, then asked "what would a buggy implementation do here that I haven't ruled out?" and added negative/boundary tests for each plausible deviation. Test names mirror clause numbers (`test_c4_eviction_happens_before_insert_not_after`) so the spec section being pinned is visible from the test name alone.

I used my coding agent to help me read the specs — paste a clause, ask what behaviors it implies, ask for half-cent boundaries that distinguish half-even from half-up — but I deliberately did **not** show it the `.pyc` files, the `phase2/` source tree, or `bug_catalog.md`, all of which were already in the repo. The point of Phase 1 is to write tests against the *spec*, not against the implementation, and peeking at any of those would have collapsed the distinction the assignment is trying to teach.

## Coverage map

**`lru_cache`** (37 tests): capacity validation (zero, negative, one, large); put/get round-trip; TTL acceptance for None/int/float; arbitrary hashable keys & arbitrary values; re-put replaces value, TTL, and expiration (including `ttl=None` clearing a prior TTL); LRU eviction when full; evict-before-insert ordering; overwrite doesn't trigger eviction; both `get` and `put`-on-existing promote to MRU; new inserts don't reorder others; expired-`get` raises and removes the entry; missing key also raises; `__len__` excludes expired-but-untouched entries; expired entries free their slot.

**`interval_merger`** (29 tests): `start > end` raises (no silent swap); equal endpoints valid; output sorted by start; overlapping merge; touching endpoints merge; adjacent endpoints stay separate; transitively-merging chains; nested intervals; identical/duplicate intervals; zero-length intervals at boundary, inside a range, alone, adjacent; empty input; **input list and tuples not mutated** (deepcopy snapshot, no reorder, no shrink); single interval; negatives; output element types are tuples.

**`cart`** (73 tests): qty/price validation, duplicate-SKU rejection, zero-price allowed; `apply_code` return semantics including case-sensitivity, empty string, and parametrized round-trip per code; each code's effect including BOGO at qty 1/2/3/4/5; FREESHIP threshold at the 4999/5000 boundary; SAVE10/SAVE20 mutual exclusion (only first takes effect); FLAT5 stacks with each percent code; BOGO and FREESHIP stack with everything; application order pinned (BOGO → percent → FLAT5 → shipping); FLAT5 clamps at 0 without removing shipping; FREESHIP threshold uses *post-discount* pre-shipping subtotal; banker's rounding at the half-cent (1245 vs 1255), explicitly distinguished from half-up; empty cart returns 0 with any subset of codes applied.

## Edge cases I invented

- **FREESHIP threshold gating on post-discount subtotal**: a $50 widget with FLAT5 lands at 4500 pre-shipping, so FREESHIP no longer fires (`test_c5_freeship_threshold_uses_post_discount_subtotal`). Same trick with SAVE10 on a 5500 cart and with BOGO on bagels.
- **Half-even vs half-up at the same input**: `test_c6_half_even_distinguishes_from_half_up` picks 1245 cents, where banker's rounds 124.5 → 124 but half-up would round → 125 — different totals, so the test would fail under a half-up impl.
- **Evict-before-insert** on a capacity=1 cache: if eviction happened *after* insert, the new key could be its own victim.
- **Expired entry frees its slot**: `test_expired_does_not_block_capacity_for_new_inserts` confirms an expired entry doesn't silently occupy a slot.
- **`merge` no-mutation in three flavors**: deep-equality snapshot, "didn't reorder," and "didn't shrink" — each catches a different mutation pattern.
- **Idempotent `total_cents`**: calling it three times must return the same number (catches "applied flag toggled inside the totaler").
- **Empty cart with codes applied**: combinations including FLAT5 (would otherwise go negative) and FREESHIP (would otherwise touch shipping).

## What was easy, what was hard

The clause-by-clause structure made the happy paths fall out almost mechanically. The hard part was testing for the *absence* of behavior — `merge` not mutating its input, `total_cents` not silently double-discounting on a re-call, eviction *not* triggering on overwrite. Those required imagining a wrong implementation and constructing a setup where the wrong behavior would leave a fingerprint. The other genuinely tricky one was the rounding clause: figuring out a subtotal where banker's and half-up actually disagree took some scratch arithmetic, since the disagreement only shows up at exactly the half-cent and only on certain parities.
