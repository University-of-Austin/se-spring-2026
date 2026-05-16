"""Tests for interval_merger.merge, organized clause by clause against the spec.

Spec lives at starter/assignment3/specs/interval_merger.md. Every test name
references the clause(s) it pins down so the spec stays in the driver's seat.
"""
import copy

import pytest

from interval_merger import merge


# ---------------------------------------------------------------------------
# C1. Input validation — start <= end, no silent swap
# ---------------------------------------------------------------------------

def test_c1_reversed_tuple_raises_valueerror():
    with pytest.raises(ValueError):
        merge([(5, 1)])


def test_c1_does_not_silently_swap():
    # If the function silently swapped, this would return [(1, 5)] instead of
    # raising. The spec is explicit: it must NOT swap.
    with pytest.raises(ValueError):
        merge([(10, 3)])


def test_c1_reversed_inside_otherwise_valid_list_raises():
    with pytest.raises(ValueError):
        merge([(1, 2), (4, 3), (5, 6)])


def test_c1_valid_input_does_not_raise():
    merge([(1, 2), (3, 4)])  # should not raise


@pytest.mark.parametrize("bad", [(2, 1), (0, -1), (10, 9), (-3, -5)])
def test_c1_various_reversed_inputs_raise(bad):
    with pytest.raises(ValueError):
        merge([bad])


# ---------------------------------------------------------------------------
# C2. Output ordering
# ---------------------------------------------------------------------------

def test_c2_unsorted_input_returns_sorted_output():
    result = merge([(8, 10), (1, 3), (5, 7)])
    assert result == [(1, 3), (5, 7), (8, 10)]


def test_c2_already_sorted_input_returns_sorted_output():
    result = merge([(1, 3), (5, 7), (8, 10)])
    assert result == [(1, 3), (5, 7), (8, 10)]


def test_c2_reverse_sorted_input_returns_ascending_output():
    result = merge([(20, 25), (10, 15), (1, 5)])
    assert result == [(1, 5), (10, 15), (20, 25)]


# ---------------------------------------------------------------------------
# C3. Merge semantics — closed intervals
# ---------------------------------------------------------------------------

def test_c3_overlapping_intervals_merge():
    assert merge([(1, 3), (2, 6)]) == [(1, 6)]


def test_c3_touching_endpoints_merge():
    # Closed intervals touching at one integer share that integer.
    assert merge([(1, 3), (3, 5)]) == [(1, 5)]


def test_c3_adjacent_endpoints_stay_separate():
    # 3 and 4 are distinct integers; intervals share no integer.
    assert merge([(1, 3), (4, 5)]) == [(1, 3), (4, 5)]


def test_c3_fully_contained_interval_merges():
    assert merge([(1, 10), (3, 5)]) == [(1, 10)]


def test_c3_identical_intervals_collapse():
    assert merge([(1, 5), (1, 5)]) == [(1, 5)]


def test_c3_chain_of_overlaps_collapses_to_min_max():
    assert merge([(1, 3), (2, 5), (4, 7), (6, 9)]) == [(1, 9)]


def test_c3_chain_via_touching_endpoints():
    # Each pair touches the next at exactly one integer.
    assert merge([(1, 3), (3, 5), (5, 7)]) == [(1, 7)]


def test_c3_disjoint_intervals_remain_separate():
    assert merge([(1, 2), (10, 20), (30, 40)]) == [(1, 2), (10, 20), (30, 40)]


def test_c3_same_start_different_ends_collapse_to_widest():
    # Multiple intervals sharing the same start must collapse to the one
    # spanning to the maximum end. Tests sort/merge behavior when the
    # primary sort key is tied.
    assert merge([(1, 3), (1, 7), (1, 5)]) == [(1, 7)]


def test_c3_same_start_in_unsorted_input():
    # Same-start tuples in arbitrary order must still collapse correctly.
    assert merge([(1, 5), (1, 3), (1, 9), (1, 1)]) == [(1, 9)]


def test_c3_three_clusters():
    intervals = [(1, 3), (2, 4), (10, 12), (11, 15), (20, 22), (21, 25)]
    assert merge(intervals) == [(1, 4), (10, 15), (20, 25)]


# ---------------------------------------------------------------------------
# C4. Zero-length intervals
# ---------------------------------------------------------------------------

def test_c4_zero_length_alone():
    assert merge([(3, 3)]) == [(3, 3)]


def test_c4_zero_length_inside_larger_merges():
    assert merge([(1, 5), (3, 3)]) == [(1, 5)]


def test_c4_zero_length_at_boundary_merges():
    # (1, 3) ∪ {3} = (1, 3)
    assert merge([(1, 3), (3, 3)]) == [(1, 3)]


def test_c4_zero_length_touching_extends():
    # (3, 3) and (3, 5) touch at 3; closed-interval merge gives (3, 5).
    assert merge([(3, 3), (3, 5)]) == [(3, 5)]


def test_c4_two_distinct_zero_length_intervals_stay_separate():
    assert merge([(1, 1), (5, 5)]) == [(1, 1), (5, 5)]


def test_c4_two_zero_length_at_same_point_collapse():
    assert merge([(3, 3), (3, 3)]) == [(3, 3)]


# ---------------------------------------------------------------------------
# C5. Empty input
# ---------------------------------------------------------------------------

def test_c5_empty_input_returns_empty_list():
    assert merge([]) == []


def test_c5_empty_input_returns_a_list_type():
    result = merge([])
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# C6. No mutation of input
# ---------------------------------------------------------------------------

def test_c6_does_not_mutate_input_list_length():
    intervals = [(1, 3), (2, 6), (8, 10)]
    snapshot = copy.deepcopy(intervals)
    merge(intervals)
    assert intervals == snapshot


def test_c6_does_not_reorder_input_list():
    intervals = [(8, 10), (1, 3), (5, 7)]
    snapshot = copy.deepcopy(intervals)
    merge(intervals)
    assert intervals == snapshot


def test_c6_does_not_mutate_unsorted_with_overlap():
    intervals = [(5, 8), (1, 4), (3, 6)]
    snapshot = copy.deepcopy(intervals)
    merge(intervals)
    assert intervals == snapshot


def test_c6_no_mutation_on_invalid_input():
    # If the function raises, it should still not mutate the input.
    intervals = [(1, 2), (5, 3)]
    snapshot = copy.deepcopy(intervals)
    with pytest.raises(ValueError):
        merge(intervals)
    assert intervals == snapshot


def test_c6_returns_new_list_object():
    intervals = [(1, 3), (5, 7)]
    result = merge(intervals)
    assert result is not intervals


# ---------------------------------------------------------------------------
# Edge cases the spec implies but doesn't spell out
# ---------------------------------------------------------------------------

def test_edge_single_interval_unchanged():
    assert merge([(2, 7)]) == [(2, 7)]


def test_edge_negative_integers():
    assert merge([(-5, -3), (-4, -2)]) == [(-5, -2)]


def test_edge_negative_and_positive_merge():
    assert merge([(-3, 0), (0, 3)]) == [(-3, 3)]


def test_edge_negative_disjoint():
    assert merge([(-10, -5), (-3, -1)]) == [(-10, -5), (-3, -1)]


def test_edge_large_values():
    assert merge([(10**9, 10**9 + 5), (10**9 + 3, 10**9 + 10)]) == [
        (10**9, 10**9 + 10)
    ]


def test_edge_many_overlapping_intervals_collapse_to_one():
    intervals = [(i, i + 3) for i in range(0, 100, 2)]
    result = merge(intervals)
    assert result == [(0, 101)]


def test_edge_alternating_clusters():
    intervals = [(1, 2), (10, 11), (2, 3), (11, 12), (3, 4)]
    assert merge(intervals) == [(1, 4), (10, 12)]


def test_edge_unsorted_with_full_containment():
    assert merge([(3, 5), (1, 10), (4, 7)]) == [(1, 10)]


def test_edge_zero_in_interval():
    assert merge([(-2, 0), (0, 2)]) == [(-2, 2)]


def test_edge_returns_list_of_tuples():
    result = merge([(1, 3), (5, 7)])
    assert all(isinstance(x, tuple) and len(x) == 2 for x in result)
