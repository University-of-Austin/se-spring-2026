"""Interval merger over closed integer intervals."""
from __future__ import annotations


def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    # Validate before doing any work so the input can't be mutated on the
    # error path (C6).
    for s, e in intervals:
        if s > e:
            raise ValueError(f"interval start must be <= end, got ({s}, {e})")

    if not intervals:
        return []

    # Sort a copy — never mutate the caller's list.
    ordered = sorted(intervals, key=lambda iv: iv[0])

    result: list[tuple[int, int]] = []
    for s, e in ordered:
        if not result:
            result.append((s, e))
            continue

        last_s, last_e = result[-1]
        # Closed intervals merge on overlap, touching, or full containment.
        if s <= last_e:
            result[-1] = (last_s, max(last_e, e))
        else:
            result.append((s, e))

    return result
