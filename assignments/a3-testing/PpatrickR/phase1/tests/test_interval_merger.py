"""Tests for interval_merger.merge, organized by spec clause (C1..C6).

Spec: starter/assignment3/specs/interval_merger.md
"""
import copy

import pytest

from interval_merger import merge


# =========================================================================
# C1. Input validation — start > end raises ValueError, no silent swapping
# =========================================================================

def test_c1_reversed_single_tuple_raises():
    with pytest.raises(ValueError):
        merge([(5, 1)])


def test_c1_reversed_among_valid_raises():
    with pytest.raises(ValueError):
        merge([(1, 3), (10, 5), (20, 25)])


@pytest.mark.parametrize("bad", [(5, 1), (10, 0), (-1, -5), (100, 99)])
def test_c1_various_reversed_raise(bad):
    with pytest.raises(ValueError):
        merge([bad])


def test_c1_does_not_silently_swap():
    """If the function silently swapped (5, 1) -> (1, 5), this would not raise."""
    with pytest.raises(ValueError):
        merge([(5, 1)])


# =========================================================================
# C2. Output ordering — sorted ascending by start
# =========================================================================

def test_c2_unsorted_input_returns_sorted_output():
    result = merge([(8, 10), (1, 3)])
    assert result == [(1, 3), (8, 10)]


def test_c2_sorted_already_remains_sorted():
    result = merge([(1, 3), (5, 7), (10, 12)])
    assert result == [(1, 3), (5, 7), (10, 12)]


def test_c2_descending_input_returns_ascending_output():
    result = merge([(20, 25), (10, 15), (1, 5)])
    assert result == [(1, 5), (10, 15), (20, 25)]


def test_c2_negative_starts_sort_first():
    result = merge([(5, 7), (-10, -5), (0, 2)])
    assert result == [(-10, -5), (0, 2), (5, 7)]


# =========================================================================
# C3. Merge semantics — closed intervals
# =========================================================================

def test_c3_overlapping_intervals_merge():
    # (1, 3) and (2, 6) overlap at 2, 3 -> (1, 6)
    assert merge([(1, 3), (2, 6)]) == [(1, 6)]


def test_c3_three_chained_overlaps_merge():
    assert merge([(1, 3), (2, 5), (4, 8)]) == [(1, 8)]


def test_c3_touching_endpoints_merge():
    """(1, 3) and (3, 5) share the endpoint 3 — merge."""
    assert merge([(1, 3), (3, 5)]) == [(1, 5)]


def test_c3_adjacent_endpoints_stay_separate():
    """(1, 3) and (4, 5) share no integer — stay separate."""
    assert merge([(1, 3), (4, 5)]) == [(1, 3), (4, 5)]


def test_c3_fully_contained_interval():
    """A wholly-inside interval merges into the bigger one."""
    assert merge([(1, 10), (3, 5)]) == [(1, 10)]


def test_c3_identical_intervals_collapse_to_one():
    assert merge([(2, 4), (2, 4)]) == [(2, 4)]


def test_c3_merged_span_is_min_start_to_max_end():
    """C3: When multiple intervals merge, result spans min start to max end."""
    result = merge([(5, 6), (1, 2), (3, 4), (2, 5)])
    assert result == [(1, 6)]


def test_c3_three_islands():
    """Disjoint groups stay disjoint, overlapping groups collapse."""
    result = merge([(1, 3), (2, 4), (10, 12), (15, 20), (16, 18)])
    assert result == [(1, 4), (10, 12), (15, 20)]


def test_c3_negative_intervals_merge():
    assert merge([(-10, -5), (-7, -3)]) == [(-10, -3)]


def test_c3_negative_touching_endpoints_merge():
    assert merge([(-5, 0), (0, 5)]) == [(-5, 5)]


def test_c3_assignment_pdf_example_three_intervals():
    assert merge([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]


# =========================================================================
# C4. Zero-length intervals
# =========================================================================

def test_c4_zero_length_alone_kept_as_is():
    assert merge([(3, 3)]) == [(3, 3)]


def test_c4_zero_length_merges_into_containing_interval():
    assert merge([(1, 5), (3, 3)]) == [(1, 5)]


def test_c4_zero_length_at_endpoint_merges():
    assert merge([(1, 5), (5, 5)]) == [(1, 5)]


def test_c4_zero_length_below_start_endpoint_merges():
    assert merge([(1, 5), (1, 1)]) == [(1, 5)]


def test_c4_zero_length_separate():
    """Two distinct zero-length points stay separate."""
    assert merge([(3, 3), (7, 7)]) == [(3, 3), (7, 7)]


def test_c4_two_equal_zero_length_collapse():
    assert merge([(3, 3), (3, 3)]) == [(3, 3)]


def test_c4_zero_length_adjacent_stays_separate():
    """(3, 3) and (4, 4) share no integer."""
    assert merge([(3, 3), (4, 4)]) == [(3, 3), (4, 4)]


# =========================================================================
# C5. Empty input
# =========================================================================

def test_c5_empty_input_returns_empty_list():
    assert merge([]) == []


def test_c5_empty_input_returns_list_type():
    assert isinstance(merge([]), list)


# =========================================================================
# C6. No mutation
# =========================================================================

def test_c6_input_list_not_mutated():
    original = [(8, 10), (1, 3), (2, 6)]
    snapshot = copy.deepcopy(original)
    merge(original)
    assert original == snapshot


def test_c6_input_tuples_not_replaced():
    """The same tuple objects should still be in the list afterward."""
    a = (8, 10)
    b = (1, 3)
    c = (2, 6)
    original = [a, b, c]
    merge(original)
    assert original[0] is a
    assert original[1] is b
    assert original[2] is c


def test_c6_input_length_unchanged():
    original = [(1, 3), (2, 6), (8, 10)]
    merge(original)
    assert len(original) == 3


def test_c6_no_mutation_on_empty():
    original = []
    merge(original)
    assert original == []


def test_c6_invalid_input_does_not_mutate():
    """Even when raising, the function should not have left the list rearranged."""
    original = [(1, 3), (10, 5), (20, 25)]
    snapshot = list(original)
    with pytest.raises(ValueError):
        merge(original)
    assert original == snapshot


# =========================================================================
# Cross-clause edge cases
# =========================================================================

def test_single_interval_returns_singleton_list():
    assert merge([(1, 5)]) == [(1, 5)]


def test_single_zero_length_returns_singleton():
    assert merge([(7, 7)]) == [(7, 7)]


def test_returned_tuples_have_two_ints():
    result = merge([(1, 3), (2, 6), (8, 10)])
    for item in result:
        assert isinstance(item, tuple)
        assert len(item) == 2
        assert isinstance(item[0], int)
        assert isinstance(item[1], int)


def test_returned_intervals_are_non_overlapping_and_non_touching():
    """No two distinct intervals in output should overlap or touch."""
    result = merge([(1, 3), (5, 7), (2, 6), (10, 12), (12, 15)])
    # After merge it should be [(1, 7), (10, 15)]
    assert result == [(1, 7), (10, 15)]
    # General invariant: result[i].end + 1 < result[i+1].start
    for prev, nxt in zip(result, result[1:]):
        assert prev[1] + 1 < nxt[0]


def test_complex_unsorted_overlapping_input():
    result = merge([(15, 18), (1, 4), (8, 10), (2, 6), (17, 22), (8, 9)])
    assert result == [(1, 6), (8, 10), (15, 22)]


def test_many_zero_length_distinct_points():
    result = merge([(5, 5), (1, 1), (3, 3), (7, 7)])
    assert result == [(1, 1), (3, 3), (5, 5), (7, 7)]


def test_zero_length_chain_of_touches():
    """(1, 2) (2, 2) (2, 3) all touch at 2."""
    assert merge([(1, 2), (2, 2), (2, 3)]) == [(1, 3)]


def test_large_input_no_crash():
    """Stress: many non-overlapping intervals come out as themselves."""
    intervals = [(i * 10, i * 10 + 3) for i in range(50)]
    result = merge(intervals)
    assert result == intervals
