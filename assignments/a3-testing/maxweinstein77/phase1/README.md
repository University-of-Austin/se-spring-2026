# Phase 1: Test-First Bug Hunt

## 1. Approach

I went through every single clause in each of the three files and for each clause, I reflected on the simple, obvious cases, and then spent some time thinking about potential "what if" cases that weren't so obvious. 

I used Claude as an intellectual sparring partner. Specifically, I would paste a clause, ask the behavioral implications regarding it, and prompted it to challenge me to think really deeply about what potential bugs could exist. I stayed strictly on the spec side, making sure to consider all possible edge cases upon forming my tests. 

## 2. Coverage map

**`lru_cache` (37 tests)**
- Capacity validation: positive (1, 3), zero, negative
- `put` accepts ttl as None, int, float, 0, negative, None as a value, integer keys, tuple keys
- TTL replacement on re-put: new value, shorter TTL, ttl=None clearing, after expiration, ttl=0 immediate expiry, same TTL resets timer
- Capacity eviction: full cache, capacity=1 boundary, re-put existing doesn't evict, len after eviction, put on previously evicted key, no eviction when all expired
- Use tracking: get promotes, put on existing promotes, new key doesn't disturb others
- Expiration on get: expired entry, non-existent key, ttl = 0, negative ttl, multiple TTLs aging in parallel
- Length: empty cache, lazy expiration, ttl =0  excluded, negative ttl excluded, mixed expired/fresh

**`interval_merger` (31 tests)**
- Input validation: single valid, reversed alone, reversed in middle, negative valid, negative reversed
- Output ordering: already sorted, reverse-sorted, mixed, negative + positive
- Merge semantics: basic overlap, touching, adjacent, contained, transitive chain, identical, negative + positive overlap, multiple separate groups, interleaved groups, long touching chain, outer consumes many, negative-only chain, mix of zero-length and regular in chain
- Zero-length intervals: alone, inside larger, far away, identical, touching from each side
- Empty input
- No mutation: after normal merge, even when raising

**`cart` (67 tests)**
- add_item validation: qty boundaries (1, 0, negative), price boundaries (0, negative), duplicate SKU, duplicate with items in between, atomicity on failure
- apply_code returns: known True, unknown False, duplicate False (for SAVE10, SAVE20, FLAT5, FREESHIP individually), mixed case False, lowercase False
- Individual codes: SAVE10, SAVE20, FLAT5, BOGO with bagels, BOGO without bagel still applied, FREESHIP at exactly 5000, just below, pre vs post-shipping
- Hidden-bug edges in C3: BOGO/FREESHIP applied before items added, BOGO with case-sensitive SKU, BOGO with prefix-match SKU
- Stacking: SAVE10/SAVE20 mutual exclusion both directions, FLAT5 + each percent, BOGO + each percent, FREESHIP + each percent, BOGO + FLAT5 (no percent), FLAT5 + FREESHIP (no percent), BOGO + FREESHIP (no percent), three-way no-percent stack, all four together
- Application order: FLAT5 clamping (negative and exactly 0), BOGO at qty 1, 3, 4, 5, 10, empty cart with codes, multi-item cart with each percent and FLAT5, BOGO only affects bagel line, FREESHIP uses post-discount subtotal, free item still pays shipping, apply order vs spec order in three configurations
- Banker's rounding: half-cent boundaries at 0.5, 2.5, 3.5, 4.5, 5.5, 6.5
- Empty cart with no codes and with SAVE20

## 3. Edge cases invented

I want to highlight a few of the more clever hidden-bug edge cases:

- **Cart**: applying BOGO_BAGEL or FREESHIP on an empty cart and adding qualifying items afterward. The spec says BOGO checks happen "when total_cents is computed" thus a buggy implementation locking in cart state at apply_code time would fail.
- **Cart**: BOGO with SKU "Bagel" (case-sensitive) or "bagel_cream_cheese" (prefix-match). Catches loose SKU matching.
- **Cart**: FREESHIP uses post-discount pre-shipping subtotal, not the original. Subtle order-of-operations bug.
- **Cart**: apply codes in chronological order that differs from spec computation order (FLAT5 before SAVE10, SAVE10 before BOGO, full reverse-spec). Catches implementations that respect chronological apply order rather than the spec's defined computation order.
- **Cart**: BOGO with even qty (4, 10) and odd qty (3, 5) verifies the `qty // 2` floor-division across multiple values, not just the canonical qty = 2.
- **LRU cache**: multiple entries with different TTLs aging in parallel; None as a value; put on a previously-evicted key; put with non-string key types (integer, tuple); re-put with same TTL value resetting the timer.
- **Interval merger**: chain of intervals all touching at endpoints, interleaved merge groups in random input order, negative-only chains, mix of zero-length and regular intervals chaining.

## 4. Easy vs hard parts of this assignment

What was easy was clauses with explicit examples in the spec. It wasn't super hard to come up with simple, straightforward tests to evaluate what was written down. 

It was more challenging to test for behavior absence. For example, "Merge doesn't mutate the input list" and "a failed add_item doesn't partially mutate the cart" required snapshot-comparing state before and after, which felt different from "call X, expect Y." The cart's banker's rounding was also tricky in the sense that the banker's only differs from half-up at exact half-cent boundaries, and I had to derive that SAVE20 can't hit those boundaries on integer cents (only SAVE10 can). The "apply order vs spec order" tests required carefully constructing scenarios where chronological-order-buggy implementation would give a different total than spec-order-correct so I needed to think through that one from first principles. 