"""Interval merger."""
from __future__ import annotations


def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    # Validate first (without mutating input). Raises before any work.
    for iv in intervals:
        s, e = iv
        if s > e:
            raise ValueError(f"interval {iv!r} has start > end")

    if not intervals:
        return []

    # Sort a copy so we don't mutate the caller's list.
    ordered = sorted(intervals, key=lambda iv: iv[0])

    result: list[tuple[int, int]] = []
    for s, e in ordered:
        if not result:
            result.append((s, e))
            continue

        last_s, last_e = result[-1]
        # Closed-interval semantics: touching endpoints (s == last_e) merge.
        # Subsumed intervals (e <= last_e) collapse into the existing one.
        if s <= last_e:
            result[-1] = (last_s, max(last_e, e))
        else:
            result.append((s, e))

    return result
