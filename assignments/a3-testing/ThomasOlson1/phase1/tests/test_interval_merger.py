"""Phase 1 tests for the `interval_merger` module.

Tests are organized clause-by-clause against the spec at
`starter/assignment3/specs/interval_merger.md`.
"""
import pytest

from interval_merger import merge


# ---------------------------------------------------------------------------
# C1. Input validation. Each element of `intervals` must be a tuple
# `(start, end)` of two integers with `start <= end`. If any tuple has
# `start > end`, `merge` raises ValueError. The function does NOT silently
# swap the values.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "intervals",
    [
        pytest.param([(5, 1)],            id="spec-example-5-1"),
        pytest.param([(1, 3), (5, 4)],    id="bad-pair-among-valid"),
        pytest.param([(5, 1), (1, 3)],    id="bad-pair-first"),
        pytest.param([(-2, -5)],          id="negative-reversed"),
        pytest.param([(0, -1)],           id="crossing-zero-reversed"),
        pytest.param([(100, -100)],       id="far-spread-reversed"),
    ],
)
def test_c1_start_greater_than_end_raises_value_error(intervals):
    # Spec: "If any tuple has start > end, merge raises ValueError. The
    # function does NOT silently swap the values." Catches both a bug
    # where validation is missing entirely and a bug where the impl
    # normalizes (a, b) with a > b into (b, a). If silent-swap were
    # happening, these calls would return a valid-looking merged list
    # rather than raising — pytest.raises would then fail.
    with pytest.raises(ValueError):
        merge(intervals)


# ---------------------------------------------------------------------------
# C2. Output ordering. The returned list is sorted ascending by the
# interval's `start` value. Intervals in the input may be in any order.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "intervals",
    [
        pytest.param([(1, 2), (3, 4), (5, 6)],   id="already-sorted"),
        pytest.param([(3, 4), (1, 2), (5, 6)],   id="middle-first"),
        pytest.param([(5, 6), (1, 2), (3, 4)],   id="last-first"),
        pytest.param([(5, 6), (3, 4), (1, 2)],   id="fully-reversed"),
        pytest.param([(5, 6), (-3, -1), (1, 2)], id="with-negatives"),
        pytest.param([(5, 6), (1, 2)],            id="two-element-reversed"),
    ],
)
def test_c2_output_is_sorted_ascending_by_start(intervals):
    # Every ordering of the same non-overlapping intervals must produce
    # the same sorted-by-start output. Non-overlapping is deliberate so
    # this test pins ONLY the ordering behavior — no merging happens, so
    # this isn't entangled with C3.
    result = merge(intervals)
    starts = [start for start, _ in result]
    assert starts == sorted(starts)
    # And the set of intervals is preserved (none lost or invented).
    assert sorted(result) == sorted(intervals)


def test_c2_sort_does_not_silently_swap_reversed_pairs_during_validation():
    # C1/C2 interaction. If the impl sorts the input as part of merging
    # and uses something like `min(start, end)` as the sort key, a
    # reversed (start > end) tuple would be silently normalized — the
    # C1 violation suppressed. Mixing a bad interval into an out-of-
    # order input forces both behaviors at once: the function must
    # still raise ValueError, not return a merged-and-sorted list.
    with pytest.raises(ValueError):
        merge([(5, 7), (10, 1), (3, 4)])


# ---------------------------------------------------------------------------
# C3. Merge semantics. Intervals are CLOSED on both ends: (a, b) represents
# every integer from a to b inclusive. Two intervals merge if their ranges
# overlap or their endpoints touch (share an integer). Adjacent integers
# (gap of 1, no shared integer) stay separate. When multiple intervals
# merge, the result spans from the minimum start to the maximum end.
# ---------------------------------------------------------------------------

def test_c3_overlapping_intervals_merge():
    # Spec example: (1, 3) and (2, 6) share integers 2 and 3, must merge.
    assert merge([(1, 3), (2, 6)]) == [(1, 6)]


def test_c3_touching_endpoints_merge():
    # Spec example: (1, 3) and (3, 5) touch at 3 and merge to (1, 5).
    # Closed intervals include their endpoints, so 3 is in both — they
    # share an integer. This is the "exactly inclusive at the boundary"
    # case, complementary to the "off-by-one apart" case below.
    assert merge([(1, 3), (3, 5)]) == [(1, 5)]


def test_c3_adjacent_intervals_do_not_merge():
    # Spec example: (1, 3) and (4, 5). The integers 3 and 4 are distinct,
    # so no integer is shared and they stay separate. This is the
    # off-by-one trap: a buggy impl using `end + 1 >= next_start` (or
    # equivalent) as the merge condition would incorrectly merge these.
    assert merge([(1, 3), (4, 5)]) == [(1, 3), (4, 5)]


@pytest.mark.parametrize(
    "intervals, expected",
    [
        pytest.param([(1, 3), (2, 5), (4, 7)], [(1, 7)], id="chain-via-overlap"),
        pytest.param([(1, 3), (3, 5), (5, 7)], [(1, 7)], id="chain-via-touching"),
    ],
)
def test_c3_chain_of_three_intervals_merges_into_one(intervals, expected):
    # Three intervals connected in a chain (each merging with the next)
    # must collapse into one spanning interval. Parametrized over the
    # two ways neighbors can connect: overlap and endpoint-touching.
    # Catches a bug where merging only handles pairs.
    assert merge(intervals) == expected


def test_c3_contained_interval_merges_into_outer():
    # When one interval is entirely inside another, they merge to the
    # outer interval. Catches a bug that only checks endpoint touching
    # (not full containment).
    assert merge([(1, 10), (3, 5)]) == [(1, 10)]


def test_c3_merge_spans_from_min_start_to_max_end():
    # Across a merge group, the result must span from the SMALLEST start
    # to the LARGEST end, regardless of input order. Catches a bug that
    # takes the first or last interval's bounds rather than the global
    # min/max of the group.
    assert merge([(5, 10), (1, 3), (2, 8)]) == [(1, 10)]


def test_c3_merge_does_not_bleed_into_isolated_interval():
    # Where some intervals merge and others don't, the merge must stop
    # at the boundary of the merging group. (1, 3) and (2, 5) merge to
    # (1, 5); (10, 12) is isolated and stays as is.
    assert merge([(1, 3), (2, 5), (10, 12)]) == [(1, 5), (10, 12)]


def test_c3_invalid_interval_among_mergers_still_raises_value_error():
    # C1/C3 interaction. If the impl uses min(start, end) / max(start,
    # end) during merging "for robustness," a reversed pair gets
    # silently normalized and the C1 violation is suppressed. With
    # (1, 5) and (10, 3): under silent normalization the second becomes
    # (3, 10), then merges with (1, 5) to give (1, 10). Must raise
    # instead.
    with pytest.raises(ValueError):
        merge([(1, 5), (10, 3)])


# ---------------------------------------------------------------------------
# C4. Zero-length intervals. (k, k) is a valid interval representing the
# single integer k. Zero-length intervals participate in merging the same
# way as normal intervals.
# ---------------------------------------------------------------------------

def test_c4_singular_zero_length_interval_round_trips():
    # The minimum case: a single (k, k) interval is valid input and
    # appears unchanged in the output. Catches a bug that rejects
    # zero-length intervals via `start < end` instead of `start <= end`.
    assert merge([(5, 5)]) == [(5, 5)]


def test_c4_zero_length_contained_in_interval_merges():
    # Spec example: (3, 3) merges with (1, 5) into (1, 5). The single
    # integer 3 is inside [1, 5], so they overlap and merge.
    assert merge([(1, 5), (3, 3)]) == [(1, 5)]


def test_c4_zero_length_isolated_stays_separate():
    # Spec example: (3, 3) alone in the output stays as (3, 3) when
    # there's no other interval covering it. Pinned alongside another
    # non-merging interval to confirm the zero-length isn't dropped.
    assert merge([(3, 3), (10, 12)]) == [(3, 3), (10, 12)]


def test_c4_zero_length_touching_endpoint_merges():
    # Spec: "Zero-length intervals participate in merging the same way."
    # (1, 3) and (3, 3) share the integer 3, so they merge under the
    # touching-endpoints rule from C3 — same as a normal touching pair.
    assert merge([(1, 3), (3, 3)]) == [(1, 3)]


def test_c4_zero_length_adjacent_does_not_merge():
    # Off-by-one boundary for zero-length intervals. (1, 3) and (5, 5)
    # share no integer (3 vs 5, gap of 1 at the integer 4), so they
    # stay separate — same as the normal-interval adjacency rule from
    # C3. Catches a bug that special-cases zero-length to always-merge.
    assert merge([(1, 3), (5, 5)]) == [(1, 3), (5, 5)]


# ---------------------------------------------------------------------------
# C5. Empty input. merge([]) returns [].
# ---------------------------------------------------------------------------

def test_c5_empty_input_returns_empty_list():
    assert merge([]) == []


# ---------------------------------------------------------------------------
# C6. No mutation. merge does not mutate its input list or any of the
# tuples inside it. Callers can rely on their list being unchanged after
# the call.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "intervals",
    [
        pytest.param([],                              id="empty"),
        pytest.param([(1, 5)],                        id="single"),
        pytest.param([(5, 6), (1, 2), (3, 4)],        id="non-merging-unsorted"),
        pytest.param([(8, 10), (1, 3), (2, 6)],       id="merging-unsorted"),
        pytest.param([(1, 3), (2, 6), (8, 10)],       id="merging-sorted"),
        pytest.param([(3, 3), (1, 5)],                id="zero-length-included"),
    ],
)
def test_c6_input_list_is_not_mutated(intervals):
    # Spec: "merge does not mutate its input list or any of the tuples
    # inside it." Snapshot the input before the call, then assert it's
    # unchanged after. The == check on lists compares both content and
    # order, so this catches:
    #   - intervals.sort() in place (would change order of unsorted
    #     inputs — the most likely real bug)
    #   - intervals.append() / .pop() (would change length)
    #   - Any tuple replacement (would change content)
    snapshot = list(intervals)
    merge(intervals)
    assert intervals == snapshot
