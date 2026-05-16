"""Tests for interval_merger.merge, organized by spec clause."""
import copy

import pytest

from interval_merger import merge


# ---------- C1: input validation ----------

def test_c1_reversed_positive_raises():
    """(5, 1): start > end with positive ints must raise ValueError."""
    with pytest.raises(ValueError):
        merge([(5, 1)])


def test_c1_reversed_off_by_one_raises():
    """(10, 9): start exactly one greater than end must raise ValueError."""
    with pytest.raises(ValueError):
        merge([(10, 9)])


def test_c1_reversed_negative_raises():
    """(-1, -5): start > end with both negative must raise ValueError."""
    with pytest.raises(ValueError):
        merge([(-1, -5)])


def test_c1_reversed_crosses_zero_raises():
    """(0, -1): start > end where the interval crosses zero must raise ValueError."""
    with pytest.raises(ValueError):
        merge([(0, -1)])


def test_c1_invalid_in_middle_raises():
    """Any invalid tuple in the list raises, even if others are valid."""
    with pytest.raises(ValueError):
        merge([(1, 3), (5, 4), (8, 10)])


def test_c1_invalid_first_raises():
    """An invalid tuple in the first position must still raise ValueError."""
    with pytest.raises(ValueError):
        merge([(5, 4), (1, 3), (8, 10)])


def test_c1_invalid_last_raises():
    """An invalid tuple in the last position must still raise ValueError."""
    with pytest.raises(ValueError):
        merge([(1, 3), (8, 10), (5, 4)])


def test_c1_all_invalid_raises():
    """If every tuple is reversed, merge still raises ValueError."""
    with pytest.raises(ValueError):
        merge([(3, 1), (10, 9), (0, -2)])


def test_c1_all_valid_with_min_max_passes():
    merge([(0, 0), (1, 1), (2, 3)])  # no exception


def test_c1_negative_interval_in_order_passes():
    """(-5, -1) is valid: start <= end even when both endpoints are negative."""
    assert merge([(-5, -1)]) == [(-5, -1)]


def test_c1_interval_crossing_zero_passes():
    """(-3, 4) is valid: start negative, end positive, start <= end across zero."""
    assert merge([(-3, 4)]) == [(-3, 4)]


# ---------- C2: output ordering ----------

def test_c2_unsorted_input_returns_sorted_output():
    assert merge([(8, 10), (1, 3), (5, 7)]) == [(1, 3), (5, 7), (8, 10)]


def test_c2_already_sorted_input_returns_sorted_output():
    assert merge([(1, 2), (4, 6), (8, 10)]) == [(1, 2), (4, 6), (8, 10)]


def test_c2_reverse_sorted_input_returns_sorted_output():
    assert merge([(8, 10), (5, 7), (1, 3)]) == [(1, 3), (5, 7), (8, 10)]


def test_c2_sort_across_negatives():
    """Output sorted ascending by start when starts span negative and positive."""
    assert merge([(5, 7), (-3, -1), (1, 3)]) == [(-3, -1), (1, 3), (5, 7)]


def test_c2_unsorted_with_overlaps_sorts_and_merges():
    """Unsorted input with overlaps: must sort globally before merging.

    A buggy impl that only merges adjacent-in-input pairs would leave (8,12)
    and (11,15) separate because (1,3) sits between them in input order.
    """
    assert merge([(8, 12), (1, 3), (11, 15), (2, 6)]) == [(1, 6), (8, 15)]


def test_c2_touching_after_sort_still_merges():
    """Touching intervals hidden by input order still merge after global sort."""
    assert merge([(5, 7), (1, 3), (3, 5)]) == [(1, 7)]


def test_c2_many_disjoint_intervals_shuffled_returns_sorted():
    """Six disjoint intervals in shuffled input return fully sorted."""
    assert merge([(20, 22), (1, 3), (15, 17), (5, 7), (25, 27), (10, 12)]) == [
        (1, 3), (5, 7), (10, 12), (15, 17), (20, 22), (25, 27)
    ]


# ---------- C3: merge semantics ----------

def test_c3_overlapping_intervals_merge():
    """Spec example: (1,3) and (2,6) overlap -> (1,6)."""
    assert merge([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]


def test_c3_touching_endpoints_merge():
    """Closed-interval touching: (1,3) and (3,5) share integer 3 -> (1,5)."""
    assert merge([(1, 3), (3, 5)]) == [(1, 5)]


def test_c3_adjacent_endpoints_stay_separate():
    """3 and 4 are distinct integers; intervals do not merge."""
    assert merge([(1, 3), (4, 5)]) == [(1, 3), (4, 5)]


def test_c3_chain_of_overlaps_collapses_to_one():
    assert merge([(1, 3), (2, 4), (3, 5), (4, 6)]) == [(1, 6)]


def test_c3_full_containment_returns_outer():
    assert merge([(1, 10), (3, 5)]) == [(1, 10)]
    assert merge([(3, 5), (1, 10)]) == [(1, 10)]


def test_c3_disjoint_chain_stays_separate():
    assert merge([(1, 2), (4, 5), (7, 8)]) == [(1, 2), (4, 5), (7, 8)]


def test_c3_merge_spans_min_start_to_max_end():
    """When N intervals merge, the result spans min(starts) to max(ends)."""
    assert merge([(2, 5), (1, 3), (4, 7)]) == [(1, 7)]


def test_c3_touching_at_zero_merges():
    """(-3, 0) and (0, 3) share integer 0 -> merge to (-3, 3)."""
    assert merge([(-3, 0), (0, 3)]) == [(-3, 3)]


def test_c3_adjacent_at_zero_stays_separate():
    """(-3, -1) and (0, 3): -1 and 0 are adjacent but distinct, stay separate."""
    assert merge([(-3, -1), (0, 3)]) == [(-3, -1), (0, 3)]


def test_c3_triple_touching_chain_collapses():
    """Three intervals touching at endpoints: (1,3),(3,5),(5,7) -> (1,7)."""
    assert merge([(1, 3), (3, 5), (5, 7)]) == [(1, 7)]


def test_c3_multiple_disjoint_merge_groups():
    """Two independent overlap clusters merge separately, not across."""
    assert merge([(1, 3), (2, 5), (10, 12), (11, 15)]) == [(1, 5), (10, 15)]


def test_c3_touching_among_negatives_merges():
    """(-5, -3) and (-3, -1) share integer -3 -> merge to (-5, -1)."""
    assert merge([(-5, -3), (-3, -1)]) == [(-5, -1)]


# ---------- C4: zero-length intervals ----------

def test_c4_zero_length_alone_stays():
    assert merge([(3, 3)]) == [(3, 3)]


def test_c4_zero_length_inside_larger_merges():
    assert merge([(1, 5), (3, 3)]) == [(1, 5)]


def test_c4_zero_length_at_left_endpoint_merges():
    assert merge([(3, 3), (3, 5)]) == [(3, 5)]


def test_c4_zero_length_at_right_endpoint_merges():
    assert merge([(1, 3), (3, 3)]) == [(1, 3)]


def test_c4_zero_length_adjacent_stays_separate():
    """(3,3) and (4,4) cover {3} and {4} -- no shared integer."""
    assert merge([(3, 3), (4, 4)]) == [(3, 3), (4, 4)]


def test_c4_two_zero_length_at_same_point_collapse():
    assert merge([(3, 3), (3, 3)]) == [(3, 3)]


def test_c4_zero_length_adjacent_to_larger_stays_separate():
    """(1,3) and (4,4): the zero-length is one integer past the larger -> stay separate."""
    assert merge([(1, 3), (4, 4)]) == [(1, 3), (4, 4)]


def test_c4_zero_length_at_integer_zero_stays():
    """(0, 0) is valid; the integer 0 must not be treated as falsy/empty."""
    assert merge([(0, 0)]) == [(0, 0)]


def test_c4_zero_length_negative_stays():
    """(-5, -5) is a valid zero-length interval at a negative integer."""
    assert merge([(-5, -5)]) == [(-5, -5)]


def test_c4_zero_length_inside_merge_group_absorbed():
    """A zero-length sitting inside a multi-interval merge doesn't break the merge."""
    assert merge([(1, 5), (3, 3), (2, 4)]) == [(1, 5)]


def test_c4_chain_of_zero_length_one_apart_stays_separate():
    """Four zero-length intervals each one integer apart stay as four."""
    assert merge([(1, 1), (2, 2), (3, 3), (4, 4)]) == [(1, 1), (2, 2), (3, 3), (4, 4)]


# ---------- C5: empty ----------

def test_c5_empty_returns_empty():
    assert merge([]) == []


# ---------- C6: no mutation ----------

def test_c6_unsorted_input_list_not_mutated():
    inp = [(8, 10), (1, 3), (5, 7)]
    snapshot = copy.deepcopy(inp)
    merge(inp)
    assert inp == snapshot


def test_c6_overlapping_input_list_not_mutated():
    inp = [(1, 3), (2, 6)]
    snapshot = copy.deepcopy(inp)
    merge(inp)
    assert inp == snapshot


def test_c6_input_list_identity_preserved():
    """The same list object should still be there after merge -- no in-place sort."""
    inp = [(8, 10), (1, 3)]
    merge(inp)
    assert inp == [(8, 10), (1, 3)]  # original order intact


def test_c6_empty_input_list_not_mutated():
    inp = []
    snapshot = copy.deepcopy(inp)
    merge(inp)
    assert inp == snapshot


def test_c6_unsorted_and_overlapping_input_not_mutated():
    """Input that triggers BOTH sort and merge paths is still left unchanged."""
    inp = [(8, 12), (1, 3), (11, 15), (2, 6)]
    snapshot = copy.deepcopy(inp)
    merge(inp)
    assert inp == snapshot


def test_c6_input_not_mutated_when_merge_raises():
    """When merge raises ValueError, the input list is still unchanged.

    Spec says callers can rely on the list being unchanged after the call;
    that should hold on the error path too, not just the success path.
    """
    inp = [(1, 3), (5, 7), (10, 5)]  # third tuple is reversed -> raises
    snapshot = copy.deepcopy(inp)
    with pytest.raises(ValueError):
        merge(inp)
    assert inp == snapshot


# ---------- Implied / edge cases ----------

def test_implied_single_interval_returns_unchanged():
    assert merge([(2, 7)]) == [(2, 7)]


def test_implied_negative_integer_intervals():
    assert merge([(-5, -2), (-3, 0), (5, 7)]) == [(-5, 0), (5, 7)]


def test_implied_large_gap_stays_separate():
    assert merge([(1, 2), (1_000_000, 2_000_000)]) == [(1, 2), (1_000_000, 2_000_000)]


def test_implied_all_overlapping_collapse_to_one():
    assert merge([(1, 100), (10, 50), (20, 80), (5, 60)]) == [(1, 100)]


def test_implied_returns_new_list_object():
    """merge should return a new list, not the same one (would imply mutation)."""
    inp = [(1, 2)]
    out = merge(inp)
    assert out is not inp


def test_implied_duplicate_intervals_collapse():
    """Identical duplicates share all integers and merge into one."""
    assert merge([(1, 3), (1, 3)]) == [(1, 3)]


def test_implied_same_start_different_ends_merges_to_max_end():
    """Two intervals with the same start: result keeps the larger end."""
    assert merge([(1, 5), (1, 3)]) == [(1, 5)]


def test_implied_same_end_different_starts_merges_to_min_start():
    """Two intervals with the same end: result keeps the smaller start."""
    assert merge([(1, 5), (3, 5)]) == [(1, 5)]


def test_implied_long_interval_contains_many_smaller():
    """A single long interval that contains several smaller ones collapses to itself."""
    assert merge([(1, 100), (5, 10), (20, 30), (50, 60), (90, 95)]) == [(1, 100)]


def test_implied_two_clusters_with_sort_and_merge():
    """Unsorted input with two separate overlap clusters: sort and merge per cluster."""
    assert merge([(20, 25), (1, 5), (3, 8), (22, 30)]) == [(1, 8), (20, 30)]
