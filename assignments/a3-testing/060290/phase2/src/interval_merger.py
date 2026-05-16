"""Interval merger.

Buggy implementation distributed to students at Phase 2.
"""
from __future__ import annotations


def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not intervals:
        return []

    normalized: list[tuple[int, int]] = []
    for iv in intervals:
        s, e = iv
        if s > e:
            raise ValueError(f"Invalid interval {iv}: start must be <= end")
        normalized.append((s, e))

    ordered = sorted(normalized, key=lambda iv: iv[0])

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
