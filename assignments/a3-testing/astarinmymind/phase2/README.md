# A3 Phase 2 — Fix the Bugs

## What tests caught vs. missed

Against the bug catalog, the Phase 1 suite caught all 20 labeled bugs. Every clause has at least one test that directly exercises the specified behavior, so when the harness activates a single bug, something fails.

The one interesting case is A11 (output ordering) and A9 (input mutation) in `interval_merger`. My C2 test feeds in intervals in unsorted order like `[(8,10), (1,3), (5,7)]` and checks the output is sorted ascending. A11's bug returns results in input-appearance order instead of sorted — so that test should catch it. But when I ran all bugs at once, A9 was also active, which sorts the input list in place *before* A11 reads "input order." So the output came out sorted by accident, and the test passed. Tested individually by the harness (A11 on, A9 off), the input stays unsorted, A11 returns the wrong order, and my test catches it.

For hidden bugs (H1–H3), I suspect the nonpositive-TTL tests (lru_cache), the zero-length-bridges-chain test (interval_merger), and the apply-code-before-add-item test (cart) may catch one or two, but I won't know until the reference suite runs.

## Fix process

Claude one shot the changes and it passed my test suite... Claude knows to leave easily Angela-understandable comments for me to read and understand what Claude is doing.

## Surprises

The A9/A11 interaction was surprising — two bugs canceling each other out. A9 mutates the input list by sorting it, and A11 returns results in input order. With both active, the input is already sorted by A9 before A11 reads it, so the output looks correct. This is a good argument for the harness testing bugs individually rather than all at once.
