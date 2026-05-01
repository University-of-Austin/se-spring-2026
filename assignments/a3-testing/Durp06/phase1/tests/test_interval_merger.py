"""Tests for interval_merger.merge, organized clause-by-clause against
starter/assignment3/specs/interval_merger.md."""
import copy

import pytest

from interval_merger import merge


# ---------------------------------------------------------------------------
# C1. Input validation: start > end is a hard error, no silent swap
# ---------------------------------------------------------------------------

def test_c1_reversed_tuple_raises_value_error():
    with pytest.raises(ValueError):
        merge([(5, 1)])


def test_c1_reversed_tuple_among_valid_raises_value_error():
    with pytest.raises(ValueError):
        merge([(1, 3), (5, 4)])


def test_c1_does_not_silently_swap_reversed_tuple():
    """Spec: 'The function does NOT silently swap the values.' Catch impls
    that just normalize start/end and return [(1, 5)]."""
    with pytest.raises(ValueError):
        result = merge([(5, 1)])
        # if we got here, also fail loudly so the impl is obviously wrong
        assert False, f"expected ValueError, got {result!r}"


# ---------------------------------------------------------------------------
# C2. Output ordering: ascending by start, even when input is unsorted
# ---------------------------------------------------------------------------

def test_c2_unsorted_input_produces_sorted_output():
    assert merge([(8, 10), (1, 6)]) == [(1, 6), (8, 10)]


def test_c2_unsorted_overlapping_input_sorted_after_merge():
    # input order shouldn't matter for either merging or final sort order
    assert merge([(8, 10), (2, 6), (1, 3)]) == [(1, 6), (8, 10)]


def test_c2_already_sorted_disjoint_passes_through_in_order():
    assert merge([(1, 2), (4, 5), (7, 8)]) == [(1, 2), (4, 5), (7, 8)]


# ---------------------------------------------------------------------------
# C3. Merge semantics: closed intervals — overlap or shared endpoint merges,
#                     adjacent (gap of 1) does not.
# ---------------------------------------------------------------------------

def test_c3_overlapping_intervals_merge():
    assert merge([(1, 3), (2, 6)]) == [(1, 6)]


def test_c3_touching_endpoints_merge():
    """Spec: '(1, 3) and (3, 5) merge into (1, 5).'"""
    assert merge([(1, 3), (3, 5)]) == [(1, 5)]


def test_c3_adjacent_with_gap_of_one_stays_separate():
    """Spec: '(1, 3) and (4, 5) stay separate — 3 and 4 are distinct.'"""
    assert merge([(1, 3), (4, 5)]) == [(1, 3), (4, 5)]


def test_c3_fully_contained_interval_merges():
    assert merge([(1, 10), (3, 5)]) == [(1, 10)]


def test_c3_chain_of_overlaps_merge_into_one():
    assert merge([(1, 3), (2, 6), (5, 10)]) == [(1, 10)]


def test_c3_three_way_touching_merge():
    assert merge([(1, 3), (3, 5), (5, 7)]) == [(1, 7)]


def test_c3_multiple_disjoint_groups():
    assert merge([(1, 3), (2, 4), (10, 12), (11, 15)]) == [(1, 4), (10, 15)]


def test_c3_negative_ranges_merge():
    assert merge([(-5, -1), (-2, 0)]) == [(-5, 0)]


# ---------------------------------------------------------------------------
# C4. Zero-length intervals: (k, k) is valid and participates in merging
# ---------------------------------------------------------------------------

def test_c4_zero_length_alone_passes_through():
    assert merge([(3, 3)]) == [(3, 3)]


def test_c4_zero_length_inside_other_merges():
    """Spec: '(3, 3) merges with (1, 5) into (1, 5).'"""
    assert merge([(1, 5), (3, 3)]) == [(1, 5)]


def test_c4_zero_length_at_endpoint_merges():
    assert merge([(1, 3), (3, 3)]) == [(1, 3)]


def test_c4_two_disjoint_zero_lengths_stay_separate():
    assert merge([(3, 3), (5, 5)]) == [(3, 3), (5, 5)]


def test_c4_two_touching_zero_lengths_merge():
    assert merge([(3, 3), (3, 3)]) == [(3, 3)]


# ---------------------------------------------------------------------------
# C5. Empty input
# ---------------------------------------------------------------------------

def test_c5_empty_returns_empty_list():
    assert merge([]) == []


def test_c5_empty_returns_a_list_type():
    result = merge([])
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# C6. No mutation of input
# ---------------------------------------------------------------------------

def test_c6_input_list_is_unchanged_after_merge():
    intervals = [(8, 10), (1, 3), (2, 6)]
    snapshot = copy.deepcopy(intervals)
    merge(intervals)
    assert intervals == snapshot


def test_c6_input_list_unchanged_when_already_sorted():
    intervals = [(1, 3), (2, 6), (8, 10)]
    snapshot = copy.deepcopy(intervals)
    merge(intervals)
    assert intervals == snapshot


def test_c6_input_list_unchanged_on_validation_error():
    """An invalid interval must not partially mutate the caller's list either."""
    intervals = [(1, 3), (5, 4)]
    snapshot = copy.deepcopy(intervals)
    with pytest.raises(ValueError):
        merge(intervals)
    assert intervals == snapshot


def test_c6_input_list_unchanged_on_empty():
    intervals = []
    merge(intervals)
    assert intervals == []


def test_c6_returned_list_is_not_the_input_list():
    """A 'no mutation' impl that returns the input list itself would let
    callers mutate the merged result and clobber the original. Result must
    be a separate list object."""
    intervals = [(1, 3)]
    result = merge(intervals)
    assert result is not intervals


# ---------------------------------------------------------------------------
# Cross-clause sanity: the published examples in the spec
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "given, expected",
    [
        ([(1, 3), (2, 6), (8, 10)], [(1, 6), (8, 10)]),
        ([(1, 3), (3, 5)], [(1, 5)]),
        ([(1, 3), (4, 5)], [(1, 3), (4, 5)]),
        ([], []),
    ],
)
def test_spec_examples(given, expected):
    assert merge(given) == expected


def test_single_valid_interval_passes_through():
    assert merge([(2, 7)]) == [(2, 7)]


def test_result_is_list_of_tuples():
    result = merge([(1, 3), (2, 6)])
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, tuple)
        assert len(item) == 2
