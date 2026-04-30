"""Interval merger.

Fixed implementation — all seeded bugs resolved.
"""
from __future__ import annotations


def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    # A10 fix: return empty list, not None
    if not intervals:
        return []

    # A12 fix: raise ValueError on reversed tuples instead of swapping
    for iv in intervals:
        s, e = iv
        if s > e:
            raise ValueError(f"Invalid interval ({s}, {e}): start > end")

    # A9 fix: sort a copy, don't mutate the input list
    ordered = sorted(intervals, key=lambda iv: iv[0])

    # A8 fix: don't filter out zero-length intervals

    result: list[tuple[int, int]] = []
    for s, e in ordered:
        if not result:
            result.append((s, e))
            continue

        last_s, last_e = result[-1]
        # A7 fix: use <= so touching endpoints merge (e.g. (1,3) and (3,5))
        if s <= last_e:
            result[-1] = (last_s, max(last_e, e))
        else:
            result.append((s, e))

    # A11 fix: result is already sorted ascending from the sorted input
    return result
