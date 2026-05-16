"""Interval merger."""
from __future__ import annotations


def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    for s, e in intervals:
        if s > e:
            raise ValueError(f"start > end: ({s}, {e})")

    if not intervals:
        return []

    sorted_intervals = sorted(intervals, key=lambda iv: iv[0])

    result: list[tuple[int, int]] = []
    for s, e in sorted_intervals:
        if not result:
            result.append((s, e))
            continue

        last_s, last_e = result[-1]
        if s <= last_e:
            result[-1] = (last_s, max(last_e, e))
        else:
            result.append((s, e))

    return result
