"""Interval merger.

Buggy implementation distributed to students at Phase 2.
"""
from __future__ import annotations


def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    # A10 fix (C5): empty input returns [], not None
    if not intervals:
        return []

    # A12 fix (C1): reversed tuple raises ValueError, no silent swap
    # A9 fix (C6): do not sort intervals in place — use a copy
    normalized: list[tuple[int, int]] = []
    for iv in intervals:
        s, e = iv
        if s > e:
            raise ValueError(f"interval start > end: {iv!r}")
        normalized.append((s, e))

    # A8 fix (C4): do NOT drop zero-length intervals — they participate
    # A9 fix (C6): sort a copy, not the original list
    ordered = sorted(normalized, key=lambda iv: iv[0])

    result: list[tuple[int, int]] = []
    for s, e in ordered:
        if not result:
            result.append((s, e))
            continue

        last_s, last_e = result[-1]
        # A7 fix (C3): touching endpoints merge (s <= last_e), subsumed merges
        if s <= last_e:
            result[-1] = (last_s, max(last_e, e))
        else:
            result.append((s, e))

    # A11 fix (C2): return sorted result directly, no re-ordering by input position
    return result
