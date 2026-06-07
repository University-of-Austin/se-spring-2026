"""Tests for interval_merger module, organized by spec clause."""
import pytest
from interval_merger import merge


# --- C1: Input validation ---

def test_c1_valid_intervals_do_not_raise():
    """Valid intervals (start <= end) must not raise. Includes start == end
    (zero-length, valid per C4) and a negative-start range. Catches a too-aggressive
    validation bug like `if start >= end: raise` that would reject (3, 3)."""
    merge([(1, 5)])     # standard
    merge([(0, 0)])     # zero-length boundary
    merge([(-3, 7)])    # negative start, valid range


@pytest.mark.parametrize("bad_interval", [(5, 1), (10, -3), (0, -1)])
def test_c1_reversed_tuple_raises(bad_interval):
    """A tuple with start > end must raise ValueError. The function does NOT
    silently swap the values. Covers a positive-range reversal, a mixed-sign
    reversal, and a tight just-past-zero reversal."""
    with pytest.raises(ValueError):
        merge([bad_interval])


def test_c1_valid_plus_invalid_raises():
    """A list mixing one valid and one invalid interval must still raise.
    Catches a bug where validation only checks the first tuple."""
    with pytest.raises(ValueError):
        merge([(1, 5), (5, 1)])


# --- C2: Output ordering ---

@pytest.mark.parametrize("intervals", [
    [(1, 3), (4, 5), (8, 10)],   # already sorted (catches descending bugs)
    [(8, 10), (4, 5), (1, 3)],   # reverse sorted (catches "no sort")
    [(4, 5), (8, 10), (1, 3)],   # random (catches partial-sort bugs)
])
def test_c2_output_sorted_by_start_regardless_of_input_order(intervals):
    """Output is sorted ascending by start, regardless of input order. Same
    intervals in three orderings should all produce the same canonical output."""
    assert merge(intervals) == [(1, 3), (4, 5), (8, 10)]


# --- C3: Merge semantics ---

def test_c3_overlapping_intervals_merge():
    """Intervals whose ranges overlap merge into one spanning min start to max end.
    PDF's first canonical example."""
    assert merge([(1, 3), (2, 6)]) == [(1, 6)]


def test_c3_touching_endpoints_merge():
    """Closed-interval semantics: touching endpoints share an integer and merge.
    Catches the classic off-by-one where the impl uses strict `<` for overlap
    instead of `<=`. PDF spec example."""
    assert merge([(1, 3), (3, 5)]) == [(1, 5)]


def test_c3_adjacent_endpoints_do_not_merge():
    """Adjacent endpoints (3 and 4) don't share an integer, so the intervals stay
    separate. Catches the inverse off-by-one where the impl uses `<=` and treats
    `end_a + 1 == start_b` as overlap. PDF spec example."""
    assert merge([(1, 3), (4, 5)]) == [(1, 3), (4, 5)]


def test_c3_contained_interval_absorbed():
    """An interval fully contained in another must merge into the larger one.
    Catches a bug where the impl only compares pairs of adjacent intervals after
    sorting and misses the containment case."""
    assert merge([(1, 10), (3, 5)]) == [(1, 10)]


def test_c3_chain_merge_spans_min_to_max():
    """When 3+ intervals merge in a chain, the result spans the global min start
    to the global max end. Catches a bug where multi-merge uses the last pair's
    end instead of the maximum end across all merged intervals."""
    assert merge([(1, 3), (2, 5), (4, 7)]) == [(1, 7)]


def test_c3_identical_intervals_collapse():
    """Two identical intervals collapse into one — they overlap completely, so
    they're a degenerate case of merge. Catches a bug where the impl emits each
    input interval separately instead of deduping via overlap."""
    assert merge([(1, 3), (1, 3)]) == [(1, 3)]


def test_c3_chain_of_touching_intervals_merges():
    """A chain where each adjacent pair only touches at endpoints (no integer
    overlap beyond the touch point): (1,2), (2,3), (3,4). All three must collapse
    to (1, 4). Catches a bug where pairwise touch-merge works but the impl
    breaks on a chain where every link is a touch."""
    assert merge([(1, 2), (2, 3), (3, 4)]) == [(1, 4)]


# --- C4: Zero-length intervals ---

@pytest.mark.parametrize("k", [3, -3, 0])
def test_c4_zero_length_alone_returned(k):
    """A zero-length interval (k, k) alone must be returned unchanged. Covers
    positive, negative, and zero positions on the integer line — a bug that
    special-cases sign or filters out zero-length intervals would surface here."""
    assert merge([(k, k)]) == [(k, k)]


@pytest.mark.parametrize("intervals,expected", [
    ([(3, 3), (1, 5)], [(1, 5)]),       # contained inside a wider range (PDF example)
    ([(3, 3), (3, 5)], [(3, 5)]),       # touching at left endpoint
    ([(1, 3), (3, 3)], [(1, 3)]),       # touching at right endpoint
])
def test_c4_zero_length_merges_with_overlap(intervals, expected):
    """A zero-length interval participates in merging like any other range:
    contained inside, touching the left endpoint, or touching the right endpoint
    of a wider range. All three positions must merge correctly."""
    assert merge(intervals) == expected


def test_c4_adjacent_zero_lengths_stay_separate():
    """Two zero-length intervals at adjacent integers (3 and 4 don't share an
    integer) must NOT merge — applies C3's adjacency rule to the zero-length case.
    Catches a bug that wrongly collapses single-integer intervals one apart."""
    assert merge([(3, 3), (4, 4)]) == [(3, 3), (4, 4)]


def test_c4_zero_length_bridges_chain():
    """A zero-length interval in the middle of a chain: (1, 5), (5, 5), (5, 10).
    The (5, 5) touches both flanking intervals at endpoint 5, so all three must
    collapse to (1, 10). Catches a bug where the impl special-cases zero-length
    as a no-op rather than as a real interval that participates in merging."""
    assert merge([(1, 5), (5, 5), (5, 10)]) == [(1, 10)]


# --- C5: Empty input ---

def test_c5_empty_input_returns_empty_list():
    """merge([]) returns []. Catches bugs that return None, raise on empty, or
    return something pathological like [()]"""
    assert merge([]) == []


# --- C6: No mutation ---

@pytest.mark.parametrize("intervals", [
    [(8, 10), (1, 3), (2, 6)],         # unsorted + overlapping (sort + merge paths)
    [(1, 3), (4, 5), (8, 10)],         # already sorted, no overlap (minimal-work path)
    [(5, 5)],                           # single zero-length (edge path)
])
def test_c6_input_list_not_mutated(intervals):
    """merge must not mutate its input list across different processing paths.
    Catches a common bug where the impl uses `intervals.sort()` instead of
    `sorted(intervals)`, or pops/reassigns elements during processing."""
    snapshot = list(intervals)
    merge(intervals)
    assert intervals == snapshot


def test_c6_input_not_mutated_on_validation_error():
    """Cross-clause C1 × C6: even when merge raises ValueError due to an invalid
    tuple, the input list must remain unchanged. The spec's no-mutation guarantee
    applies on the error path too — but doesn't spell that out. Catches a bug
    where the impl pre-sorts the input list BEFORE validating, leaving the
    caller's list partially mutated when the error fires."""
    intervals = [(8, 10), (5, 1), (1, 3)]   # invalid in middle; list also unsorted
    snapshot = list(intervals)
    with pytest.raises(ValueError):
        merge(intervals)
    assert intervals == snapshot
