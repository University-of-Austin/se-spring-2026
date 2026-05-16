"""Interval merger."""


def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    # Validate before any other work so the input is never mutated and a bad
    # tuple raises before partial processing.
    for iv in intervals:
        if not isinstance(iv, tuple) or len(iv) != 2:
            raise ValueError(f"interval must be a 2-tuple, got {iv!r}")
        s, e = iv
        if type(s) is not int or type(e) is not int:
            raise ValueError(f"interval bounds must be int, got {iv!r}")
        if s > e:
            raise ValueError(f"interval start must be <= end, got {iv!r}")

    result: list[tuple[int, int]] = []
    for s, e in sorted(intervals):
        if result and s <= result[-1][1]:
            ls, le = result[-1]
            result[-1] = (ls, max(le, e))
        else:
            result.append((s, e))
    return result
