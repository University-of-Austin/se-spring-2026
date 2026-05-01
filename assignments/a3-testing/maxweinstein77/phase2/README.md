# Phase 2: Fix the Bugs

## 1. What I caught vs. missed

Initial run against the buggy source: **62 failures, 76 passing** out of 138 tests. After fixing all the bugs, the entire suite is now good. 

It looks like my Phase 1 suite caught all 20 labeled bugs (A1 through A20), broken down by module:
- **`lru_cache`**: A1 (get not promoting), A2 (stale TTL on get), A3 (len includes expired), A4 (re-put keeps old TTL), A5 (capacity+1 off-by-one), A6 (no validation on capacity).
- **`interval_merger`**: A7 (touching no merge), A8 (zero-length filtered), A9 (input mutated), A10 (empty returns None), A11 (output not sorted), A12 (silent swap on reversed).
- **`cart`**: A13 (SAVE10/20 both apply), A14 (FLAT5 before percent), A15 (no clamp), A16 (FREESHIP strict >), A17 (BOGO `(qty-1)//2`), A18 (HALF_UP not HALF_EVEN), A19 (case-insensitive codes), A20 (empty cart charged shipping).

For hidden bugs, I'm fairly confident about two: `get` on a missing key returning `None` rather than raising `KeyError` (lru), and BOGO_BAGEL applied before the bagel line was added permanently suppressing the discount even after the fact that the bagel got added (cart). The third I'm less confident on.

## 2. Fix process

I had Claude go through it module by module, reading each buggy source against the spec and the bug catalog side by side. Most fixes were very subtle changes: swap `>` to `>=`, add a `move_to_end`, change `(qty - 1) // 2` to `qty // 2`, swap `ROUND_HALF_UP` for `ROUND_HALF_EVEN`. The interval merger needed the most work though because the buggy version had a clever output-reordering hack that I had replaced with the straightforward sort-then-sweep approach.

## 3. Surprises

The cart bug where the BOGO_BAGEL flag silently suppressed the discount forever after being applied to an empty cart was kind of hard to detect if you were just skimming it. The code that was buggy would pass as fine if you weren't reading the spec very carefully. The interval merger's output-reordering hack was also kind of crazy in that it quite literally masked the contained-interval bug by accident, so my contained-interval test passed against the buggy code even though the merge logic was entirely off. 