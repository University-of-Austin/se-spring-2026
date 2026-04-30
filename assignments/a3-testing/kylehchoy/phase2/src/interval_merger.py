"""Interval merger.

Phase 2 fix: implements clauses C1-C6 of the interval_merger spec.
"""
from __future__ import annotations


def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not intervals:
        return []

    # Validate before any other work so the input is never mutated and a bad
    # tuple raises before partial processing.
    validated: list[tuple[int, int]] = []
    for iv in intervals:
        if not isinstance(iv, tuple) or len(iv) != 2:
            raise ValueError(f"interval must be a 2-tuple, got {iv!r}")
        s, e = iv
        if isinstance(s, bool) or isinstance(e, bool) or not isinstance(s, int) or not isinstance(e, int):
            raise TypeError(f"interval bounds must be int, got {iv!r}")
        if s > e:
            raise ValueError(f"interval start must be <= end, got {iv!r}")
        validated.append((s, e))

    ordered = sorted(validated, key=lambda iv: iv[0])

    result: list[tuple[int, int]] = []
    for s, e in ordered:
        if result and s <= result[-1][1]:
            ls, le = result[-1]
            result[-1] = (ls, max(le, e))
        else:
            result.append((s, e))

    return result
