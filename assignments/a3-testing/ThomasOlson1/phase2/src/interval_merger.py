"""Interval merger.

Phase 2 fix.
"""
from __future__ import annotations


def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    # C5: empty input returns []
    if not intervals:
        return []

    # C1: validate each interval — start > end raises ValueError, no silent swap.
    # C6: snapshot first so we don't mutate caller's list.
    validated: list[tuple[int, int]] = []
    for iv in intervals:
        s, e = iv
        if s > e:
            raise ValueError(f"invalid interval ({s}, {e}): start > end")
        validated.append((s, e))

    # C2: output sorted ascending by start. sorted() returns a new list,
    # so the caller's input list is untouched.
    ordered = sorted(validated, key=lambda iv: iv[0])

    # C3 + C4: merge overlapping or touching intervals, including zero-length.
    # Closed intervals (a, b) and (c, d) merge if c <= b (they share an integer).
    result: list[tuple[int, int]] = []
    for s, e in ordered:
        if not result:
            result.append((s, e))
            continue
        last_s, last_e = result[-1]
        if s <= last_e:
            result[-1] = (last_s, max(last_e, e))
        else:
            result.append((s, e))

    return result
