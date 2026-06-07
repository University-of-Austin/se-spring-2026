"""Tests for interval_merger.merge.

Spec clauses:
  C1: merge takes a list of (int, int) tuples and returns the minimal set of
      non-overlapping closed intervals covering the same integers.
  C2: Intervals are closed on both ends -- (a, b) covers every integer a..b.
  C3: Endpoints that touch count as merging: (1, 3) + (3, 5) -> (1, 5).
  C4: Adjacent integers in separate intervals do NOT merge:
      (1, 3) + (4, 5) stays separate.
  C5: A reversed tuple (start > end) is a ValueError.
  C6: An empty input returns an empty list.
  C7: Output is sorted (regardless of input order).
  C8: Zero-length intervals (a, a) are valid (start == end).
"""

import copy
import pytest
from interval_merger import merge


# -- C1/C2: basic semantics --------------------------------------------------

def test_c1_single_interval_returned_as_is():
    assert merge([(1, 5)]) == [(1, 5)]


def test_c1_two_disjoint_intervals_kept_separate_in_order():
    assert merge([(1, 3), (8, 10)]) == [(1, 3), (8, 10)]


# -- C3: overlapping & touching merge ----------------------------------------

def test_c3_overlapping_intervals_merge():
    assert merge([(1, 3), (2, 6)]) == [(1, 6)]


def test_c3_touching_endpoints_merge():
    """Spec: endpoints touching at 3 counts as merging for closed intervals."""
    assert merge([(1, 3), (3, 5)]) == [(1, 5)]


def test_c3_chain_of_overlaps_collapses_to_one():
    assert merge([(1, 4), (3, 7), (6, 10)]) == [(1, 10)]


def test_c3_one_interval_fully_contains_another():
    assert merge([(1, 10), (3, 5)]) == [(1, 10)]


def test_c3_spec_example_overlap_plus_disjoint():
    assert merge([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]


# -- C4: adjacent integers do not merge --------------------------------------

def test_c4_adjacent_but_non_touching_stay_separate():
    """Spec: (1, 3) and (4, 5) -- 3 and 4 are adjacent but don't share an
    integer, so they remain separate."""
    assert merge([(1, 3), (4, 5)]) == [(1, 3), (4, 5)]


def test_c4_gap_of_one_stays_separate():
    assert merge([(0, 0), (2, 2)]) == [(0, 0), (2, 2)]


# -- C5: reversed tuple is a ValueError --------------------------------------

@pytest.mark.parametrize("intervals", [
    [(5, 1)],                                       # alone
    [(1, 3), (10, 5)],                              # one valid, one reversed
    [(1, 3), (4, 6), (20, 15), (30, 35)],           # reversed in middle
    [(0, 0), (-1, -3)],                             # negative, reversed
    [(5, 4)],                                       # off-by-one reversed
])
def test_c5_reversed_tuple_raises_valueerror(intervals):
    """Spec C1: start > end raises ValueError; never silently swapped."""
    with pytest.raises(ValueError):
        merge(intervals)


# -- C6: empty input ---------------------------------------------------------

def test_c6_empty_list_returns_empty_list():
    assert merge([]) == []


# -- C7: output is sorted ----------------------------------------------------

def test_c7_unsorted_input_produces_sorted_output():
    assert merge([(8, 10), (1, 3)]) == [(1, 3), (8, 10)]


def test_c7_unsorted_overlapping_input_produces_sorted_merged_output():
    assert merge([(8, 10), (1, 3), (2, 6)]) == [(1, 6), (8, 10)]


def test_c7_three_unsorted_intervals():
    assert merge([(20, 25), (1, 3), (10, 12)]) == [(1, 3), (10, 12), (20, 25)]


# -- C8: zero-length intervals -----------------------------------------------

def test_c8_zero_length_interval_alone():
    assert merge([(3, 3)]) == [(3, 3)]


def test_c8_zero_length_inside_another_interval_merges():
    assert merge([(1, 5), (3, 3)]) == [(1, 5)]


def test_c8_zero_length_touching_endpoint_merges():
    assert merge([(1, 5), (5, 5)]) == [(1, 5)]


def test_c8_zero_length_disjoint():
    assert merge([(0, 0), (5, 5), (10, 10)]) == [(0, 0), (5, 5), (10, 10)]


# -- Input mutation: merge MUST NOT mutate its input -------------------------

def test_input_list_not_mutated():
    inp = [(8, 10), (1, 3), (2, 6)]
    snapshot = copy.deepcopy(inp)
    merge(inp)
    assert inp == snapshot


def test_input_list_not_mutated_when_already_sorted():
    inp = [(1, 3), (5, 7)]
    snapshot = copy.deepcopy(inp)
    merge(inp)
    assert inp == snapshot


def test_input_list_not_mutated_when_empty():
    inp = []
    merge(inp)
    assert inp == []


# -- Negative numbers --------------------------------------------------------

def test_negative_intervals_merge_correctly():
    assert merge([(-5, -1), (-3, 2)]) == [(-5, 2)]


def test_negative_and_positive_disjoint():
    assert merge([(-5, -1), (1, 5)]) == [(-5, -1), (1, 5)]


def test_negative_touching_at_zero():
    assert merge([(-5, 0), (0, 5)]) == [(-5, 5)]


# -- Larger, mixed case ------------------------------------------------------

def test_many_intervals_some_merge_some_dont():
    inp = [(1, 2), (3, 4), (5, 6), (2, 3), (10, 12), (11, 15)]
    # (1,2)+(2,3)+(3,4) chain -> (1,4); (4,5) NOT adjacent? 4 and 5 share if (4,..) but here we have (3,4) and (5,6) -- 4 and 5 don't overlap
    # Actually (1,2)+(2,3) -> (1,3); (1,3)+(3,4) -> (1,4); (5,6) separate; (10,12)+(11,15) -> (10,15)
    assert merge(inp) == [(1, 4), (5, 6), (10, 15)]


def test_duplicate_intervals_collapse():
    assert merge([(1, 3), (1, 3), (1, 3)]) == [(1, 3)]


def test_all_same_zero_length_interval():
    assert merge([(5, 5), (5, 5)]) == [(5, 5)]


# -- Output type sanity ------------------------------------------------------

def test_output_is_a_list():
    result = merge([(1, 3)])
    assert isinstance(result, list)


def test_output_elements_are_tuples():
    result = merge([(1, 3), (5, 7)])
    for item in result:
        assert isinstance(item, tuple)
        assert len(item) == 2
