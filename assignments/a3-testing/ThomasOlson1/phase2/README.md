My Phase 1 suite caught 19 of the 20 labeled bugs when running against the buggy source with all bugs on, and all 20 when you check them one by one. Every catalog entry had at least one test that would catch it under that bug alone. The three hidden bugs aren't in the catalog — those are still a question mark until grading.

For the fixes I went module by module and used Claude the way the assignment suggests — handed it a failing test plus the buggy source, had it propose a fix per the spec, ran the tests, moved on. interval_merger had six visible bugs, then lru_cache, then cart. After the rewrites all 140 tests passed.

The biggest surprise was bug masking. With every bug active at once, some bugs covered for each other — A11 (output in input order) never showed up as a failure because A9 had sorted the input in place first, so the output looked sorted by accident. The grading harness toggles bugs one at a time, so each still gets caught, but the all-on view was confusing at first.
