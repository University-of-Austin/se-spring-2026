"""Tests for the interval_merger module.

Organized clause by clause against the spec at
starter/assignment3/specs/interval_merger.md (C1-C6), with extra
baseline sanity checks and hidden-edge hunts.
"""
import copy

import pytest

from interval_merger import merge


# ---------------------------------------------------------------------------
# Baseline sanity: simple cases that confirm the function returns the
# right shape and contents at all.
# ---------------------------------------------------------------------------

def test_basic_single_interval_unchanged():
    assert merge([(1, 5)]) == [(1, 5)]


def test_basic_two_disjoint_intervals_stay_separate():
    assert merge([(1, 3), (10, 20)]) == [(1, 3), (10, 20)]


def test_basic_spec_canonical_example():
    # Directly from the spec: [(1, 3), (2, 6), (8, 10)] -> [(1, 6), (8, 10)].
    assert merge([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]


def test_basic_four_disjoint_intervals_all_returned():
    # Four disjoint intervals must all appear in output - none silently dropped.
    result = merge([(1, 2), (5, 6), (10, 11), (15, 16)])
    assert result == [(1, 2), (5, 6), (10, 11), (15, 16)]


def test_basic_mixed_four_intervals_partial_merge():
    # Two pairs that each merge, with a gap between the pairs.
    result = merge([(1, 3), (2, 5), (10, 12), (11, 15)])
    assert result == [(1, 5), (10, 15)]


# ---------------------------------------------------------------------------
# C1. Input validation: start > end raises ValueError; no silent swap.
# ---------------------------------------------------------------------------

def test_c1_reversed_tuple_raises_valueerror():
    with pytest.raises(ValueError):
        merge([(5, 1)])


def test_c1_reversed_does_not_silently_swap():
    # The spec explicitly forbids silent swap. Even (5, 3) (which would
    # be "valid" if swapped to (3, 5)) must raise.
    with pytest.raises(ValueError):
        merge([(5, 3)])


def test_c1_reversed_tuple_in_middle_of_valid_list_raises():
    # Validation must apply to every tuple, not just the first.
    with pytest.raises(ValueError):
        merge([(1, 2), (5, 1), (10, 12)])


# ---------------------------------------------------------------------------
# C2. Output ordering: result sorted ascending by start.
# ---------------------------------------------------------------------------

def test_c2_output_sorted_when_input_unsorted():
    assert merge([(8, 10), (1, 3)]) == [(1, 3), (8, 10)]


def test_c2_output_sorted_when_merging_required():
    # Even when merging happens, output is sorted by start.
    assert merge([(8, 10), (1, 3), (2, 6)]) == [(1, 6), (8, 10)]


# ---------------------------------------------------------------------------
# C3. Merge semantics: closed-interval overlap, touching endpoints merge,
# adjacent (gap of 1) stay separate.
# ---------------------------------------------------------------------------

def test_c3_overlapping_intervals_merge():
    assert merge([(1, 5), (3, 7)]) == [(1, 7)]


def test_c3_touching_endpoints_merge():
    # (1, 3) and (3, 5) share the integer 3 in closed-interval semantics.
    assert merge([(1, 3), (3, 5)]) == [(1, 5)]


def test_c3_adjacent_intervals_stay_separate():
    # (1, 3) and (4, 5): 3 and 4 are adjacent integers but no integer is
    # shared, so they must NOT merge.
    assert merge([(1, 3), (4, 5)]) == [(1, 3), (4, 5)]


def test_c3_full_containment_merges():
    # Inner interval (3, 5) is wholly inside (1, 10) - they collapse.
    assert merge([(1, 10), (3, 5)]) == [(1, 10)]


# ---------------------------------------------------------------------------
# C4. Zero-length intervals: (k, k) is valid and participates in merging
# the same way.
# ---------------------------------------------------------------------------

def test_c4_zero_length_interval_alone():
    assert merge([(3, 3)]) == [(3, 3)]


def test_c4_zero_length_merges_into_containing_range():
    assert merge([(1, 5), (3, 3)]) == [(1, 5)]


def test_c4_duplicate_zero_length_intervals_collapse():
    # Both intervals cover {3}, so they overlap and must collapse.
    assert merge([(3, 3), (3, 3)]) == [(3, 3)]


# ---------------------------------------------------------------------------
# C5. Empty input.
# ---------------------------------------------------------------------------

def test_c5_empty_input_returns_empty_list():
    assert merge([]) == []


# ---------------------------------------------------------------------------
# C6. No mutation: input list and its inner tuples must be unchanged.
# ---------------------------------------------------------------------------

def test_c6_input_list_not_mutated():
    inp = [(8, 10), (1, 3), (2, 6)]
    original = copy.deepcopy(inp)
    merge(inp)
    assert inp == original


def test_c6_input_list_length_unchanged():
    # Even on no-op input, merge must not append/remove from the list.
    inp = [(1, 3), (5, 7)]
    merge(inp)
    assert len(inp) == 2


# ---------------------------------------------------------------------------
# Hidden-edge hunts: properties the spec implies but does not name.
# ---------------------------------------------------------------------------

def test_hidden_returns_new_list_object_not_input():
    # No mutation (C6) is one thing; returning the same list is another.
    # If merge returned `intervals` directly, an in-place caller change
    # would surprise the user. Verify the returned list is a different
    # object.
    inp = [(1, 3)]
    out = merge(inp)
    assert out is not inp


def test_hidden_output_elements_are_tuples():
    out = merge([(1, 3), (5, 7)])
    for element in out:
        assert isinstance(element, tuple)
