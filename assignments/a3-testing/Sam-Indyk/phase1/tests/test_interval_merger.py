"""Tests for interval_merger, organized clause-by-clause against the spec."""
import copy

import pytest

from interval_merger import merge


# -------------------- C1: Input validation --------------------

def test_c1_reversed_tuple_raises_valueerror():
    with pytest.raises(ValueError):
        merge([(5, 1)])


def test_c1_no_silent_swap():
    # If merge silently swapped (5, 1) -> (1, 5), this would return [(1, 5)]
    # instead of raising.
    with pytest.raises(ValueError):
        merge([(5, 1)])


def test_c1_reversed_among_valid_raises():
    with pytest.raises(ValueError):
        merge([(1, 3), (10, 5), (20, 25)])


def test_c1_equal_endpoints_are_valid():
    # (k, k) has start == end which satisfies start <= end.
    assert merge([(3, 3)]) == [(3, 3)]


# -------------------- C2: Output ordering --------------------

def test_c2_unsorted_input_returns_sorted_output():
    result = merge([(8, 10), (1, 3), (5, 6)])
    assert result == [(1, 3), (5, 6), (8, 10)]


def test_c2_already_sorted_input_stays_sorted():
    result = merge([(1, 2), (4, 5), (7, 8)])
    assert result == [(1, 2), (4, 5), (7, 8)]


def test_c2_output_is_sorted_by_start():
    # Even after merging, output is sorted by start.
    result = merge([(20, 25), (1, 3), (10, 15), (2, 5)])
    starts = [start for start, _ in result]
    assert starts == sorted(starts)


# -------------------- C3: Merge semantics --------------------

def test_c3_overlapping_intervals_merge():
    assert merge([(1, 3), (2, 6)]) == [(1, 6)]


def test_c3_overlapping_with_separate_third():
    assert merge([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]


def test_c3_touching_endpoints_merge():
    # (1, 3) and (3, 5) share the integer 3 — closed intervals merge.
    assert merge([(1, 3), (3, 5)]) == [(1, 5)]


def test_c3_adjacent_endpoints_stay_separate():
    # (1, 3) and (4, 5) share no integer — stay separate.
    assert merge([(1, 3), (4, 5)]) == [(1, 3), (4, 5)]


def test_c3_one_fully_contains_other():
    assert merge([(1, 10), (3, 5)]) == [(1, 10)]


def test_c3_chain_merge_via_transitivity():
    # (1,3) merges with (3,5) merges with (5,7) -> (1,7) overall.
    assert merge([(1, 3), (3, 5), (5, 7)]) == [(1, 7)]


def test_c3_chain_merge_unsorted_input():
    assert merge([(5, 7), (1, 3), (3, 5)]) == [(1, 7)]


def test_c3_merge_spans_min_start_to_max_end():
    # Output of a merge group covers [min start, max end].
    result = merge([(2, 4), (1, 3), (3, 7), (5, 6)])
    assert result == [(1, 7)]


def test_c3_identical_intervals_merge():
    assert merge([(1, 5), (1, 5)]) == [(1, 5)]


# -------------------- C4: Zero-length intervals --------------------

def test_c4_singleton_alone_stays():
    assert merge([(3, 3)]) == [(3, 3)]


def test_c4_singleton_inside_range_merges():
    # (3, 3) is the integer 3, which is in [1, 5].
    assert merge([(1, 5), (3, 3)]) == [(1, 5)]


def test_c4_singleton_at_boundary_merges():
    # (1, 1) touches (1, 5) at start.
    assert merge([(1, 1), (1, 5)]) == [(1, 5)]
    # (5, 5) touches (1, 5) at end.
    assert merge([(1, 5), (5, 5)]) == [(1, 5)]


def test_c4_singleton_adjacent_stays_separate():
    # (3, 3) is the integer 3; (4, 4) is the integer 4. Adjacent, not touching.
    assert merge([(3, 3), (4, 4)]) == [(3, 3), (4, 4)]


def test_c4_two_singletons_at_same_value_merge():
    assert merge([(3, 3), (3, 3)]) == [(3, 3)]


# -------------------- C5: Empty input --------------------

def test_c5_empty_input_returns_empty_list():
    assert merge([]) == []


# -------------------- C6: No mutation of input --------------------

def test_c6_does_not_mutate_input_list():
    original = [(8, 10), (1, 3), (2, 6)]
    snapshot = copy.deepcopy(original)
    merge(original)
    assert original == snapshot


def test_c6_does_not_reorder_input_list():
    # An implementation that sorts in-place would reorder the caller's list.
    original = [(8, 10), (1, 3), (2, 6)]
    merge(original)
    assert original == [(8, 10), (1, 3), (2, 6)]


def test_c6_does_not_mutate_with_only_one_interval():
    original = [(1, 5)]
    merge(original)
    assert original == [(1, 5)]


def test_c6_does_not_remove_elements_from_input():
    # If merge popped/removed during iteration, caller's list would shrink.
    original = [(1, 3), (2, 4), (10, 12)]
    merge(original)
    assert len(original) == 3


# -------------------- Edge cases / single-interval --------------------

def test_single_interval_returned_unchanged():
    assert merge([(1, 5)]) == [(1, 5)]


def test_negative_values_supported():
    assert merge([(-5, -1), (-3, 2)]) == [(-5, 2)]


def test_zero_in_range():
    assert merge([(-2, 0), (0, 2)]) == [(-2, 2)]


def test_large_disjoint_set():
    intervals = [(i, i + 1) for i in range(0, 20, 4)]  # (0,1),(4,5),(8,9),...
    expected = sorted(intervals)
    assert merge(intervals) == expected


def test_output_elements_are_tuples():
    result = merge([(1, 3), (5, 7)])
    for item in result:
        assert isinstance(item, tuple)
        assert len(item) == 2
