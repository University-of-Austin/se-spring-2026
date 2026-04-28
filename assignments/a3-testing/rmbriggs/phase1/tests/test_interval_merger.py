"""Tests for interval_merger.merge, organized by spec clause."""
import copy

import pytest

from interval_merger import merge


# ---------- C1: input validation ----------

def test_c1_reversed_tuple_raises():
    with pytest.raises(ValueError):
        merge([(5, 1)])


def test_c1_invalid_in_middle_raises():
    """Any invalid tuple in the list raises, even if others are valid."""
    with pytest.raises(ValueError):
        merge([(1, 3), (5, 4), (8, 10)])


def test_c1_all_valid_with_min_max_passes():
    merge([(0, 0), (1, 1), (2, 3)])  # no exception


# ---------- C2: output ordering ----------

def test_c2_unsorted_input_returns_sorted_output():
    assert merge([(8, 10), (1, 3), (5, 7)]) == [(1, 3), (5, 7), (8, 10)]


def test_c2_already_sorted_input_returns_sorted_output():
    assert merge([(1, 2), (4, 6), (8, 10)]) == [(1, 2), (4, 6), (8, 10)]


def test_c2_reverse_sorted_input_returns_sorted_output():
    assert merge([(8, 10), (5, 7), (1, 3)]) == [(1, 3), (5, 7), (8, 10)]


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
