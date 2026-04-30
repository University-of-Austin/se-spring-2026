"""Interval merger."""
from __future__ import annotations


def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    for iv in intervals:
        s, e = iv
        if s > e:
            raise ValueError(f"interval {iv!r} has start > end")

    if not intervals:
        return []

    ordered = sorted(intervals, key=lambda iv: iv[0])

    result: list[tuple[int, int]] = []
    for s, e in ordered:
        if not result or s > result[-1][1]:
            result.append((s, e))
        else:
            last_s, last_e = result[-1]
            result[-1] = (last_s, max(last_e, e))
    return result
