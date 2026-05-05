"""Tests for the interval_merger module against its specification."""

import pytest

from interval_merger import merge


# ---------- C1: Input validation ----------

def test_c1_start_greater_than_end_raises_value_error():
    """A tuple with start > end is invalid input."""
    with pytest.raises(ValueError):
        merge([(5, 1)])


def test_c1_invalid_tuple_among_valid_ones_still_raises():
    """Even one bad tuple in a list of valid ones must raise."""
    with pytest.raises(ValueError):
        merge([(1, 3), (10, 5), (20, 25)])


# ---------- C2: Output ordering ----------

@pytest.mark.parametrize("inputs,expected", [
    ([(10, 12), (5, 7), (1, 3)], [(1, 3), (5, 7), (10, 12)]),
    ([(20, 25), (1, 3), (10, 12), (5, 7)],
     [(1, 3), (5, 7), (10, 12), (20, 25)]),
    ([(4, 9)], [(4, 9)]),
])
def test_c2_output_sorted_ascending_by_start(inputs, expected):
    """Output is sorted ascending by start, regardless of input order."""
    assert merge(inputs) == expected


# ---------- C3: Merge semantics (closed intervals) ----------

def test_c3_overlapping_intervals_merge():
    """Overlap at any integer collapses two intervals into one spanning min..max."""
    assert merge([(1, 5), (3, 8)]) == [(1, 8)]


def test_c3_one_interval_fully_contained_in_another():
    """A wholly-contained interval is absorbed."""
    assert merge([(1, 10), (3, 5)]) == [(1, 10)]


def test_c3_touching_endpoints_merge():
    """Endpoints that touch (share an integer) merge: closed-interval semantics."""
    assert merge([(1, 3), (3, 5)]) == [(1, 5)]


def test_c3_adjacent_endpoints_do_not_merge():
    """Endpoints that are adjacent but distinct (gap of 1) stay separate."""
    assert merge([(1, 3), (4, 5)]) == [(1, 3), (4, 5)]


def test_c3_chain_of_three_collapses_to_one():
    """Multiple intervals that pairwise touch/overlap collapse to a single span."""
    assert merge([(1, 3), (2, 6), (5, 10)]) == [(1, 10)]


def test_c3_merged_span_uses_min_start_and_max_end():
    """Result spans from minimum start to maximum end across all merged inputs."""
    assert merge([(5, 7), (1, 6), (4, 9)]) == [(1, 9)]


# ---------- C4: Zero-length intervals ----------

def test_c4_zero_length_alone_returned_as_is():
    """A single point interval like (3, 3) is valid and survives unchanged."""
    assert merge([(3, 3)]) == [(3, 3)]


def test_c4_zero_length_inside_a_range_is_absorbed():
    """(3, 3) merges into (1, 5) because the integer 3 is shared."""
    assert merge([(1, 5), (3, 3)]) == [(1, 5)]


def test_c4_zero_length_at_endpoint_merges():
    """(5, 5) touches (1, 5) at the endpoint, so they merge."""
    assert merge([(1, 5), (5, 5)]) == [(1, 5)]


def test_c4_zero_length_disjoint_stays_separate():
    """A zero-length interval that shares no integer with the others stays separate."""
    assert merge([(1, 3), (10, 10)]) == [(1, 3), (10, 10)]


def test_c4_two_zero_length_at_same_point_collapse():
    """Two single-point intervals at the same integer collapse to one."""
    assert merge([(7, 7), (7, 7)]) == [(7, 7)]


# ---------- C5: Empty input ----------

def test_c5_empty_input_returns_empty_list():
    """merge([]) returns an empty list."""
    assert merge([]) == []


# ---------- C6: No mutation ----------

def test_c6_input_list_unchanged_after_merge():
    """The input list's contents and order are unchanged after merge."""
    inputs = [(2, 6), (1, 3), (8, 10)]
    snapshot = list(inputs)
    merge(inputs)
    assert inputs == snapshot


def test_c6_input_list_unchanged_when_merging_required():
    """Even when merge does heavy work, the input list is left intact."""
    inputs = [(1, 3), (3, 5), (10, 12), (11, 14)]
    snapshot = list(inputs)
    merge(inputs)
    assert inputs == snapshot
