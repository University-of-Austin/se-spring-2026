import pytest
from interval_merger import merge


def test_c1_reversed_tuple_raises():
    with pytest.raises(ValueError):
        merge([(5, 4)])

def test_c2_output_sorted_ascending():
    assert merge([(2, 3), (0, 1)]) == [(0, 1), (2, 3)]

def test_c3_overlapping_intervals_merge():
    assert merge([(1, 4), (2, 6)]) == [(1, 6)] 

def test_c3_touching_endpoints_merge():
    assert merge([(3, 6), (6, 9)]) == [(3, 9)]

def test_c3_adjacent_stays_separate():
    assert merge([(1, 10), (11, 20)]) == [(1, 10), (11, 20)]

def test_c3_multiple_intervals_merge_full_span():
    assert merge([(1, 3), (3, 5), (5, 7)]) == [(1, 7)]

def test_c4_zero_length_merges_with_larger():
    assert merge([(5, 5), (1, 10)]) == [(1, 10)]

def test_c4_zero_length_alone():
    assert merge([(10, 10)]) == [(10, 10)]

def test_c5_empty_input():
    assert merge([]) == []

def test_c6_no_mutation():
    intervals = [(3, 6), (1, 4)]
    original = list(intervals)
    merge(intervals)
    assert intervals == original

def test_c3_partial_merge_mixed_list():
    assert merge([(1, 5), (6, 10), (10, 20), (21, 40)]) == [(1, 5), (6, 20), (21, 40)]

def test_c3_duplicate_intervals():
    assert merge([(1, 5), (1, 5)]) == [(1, 5)]

def test_single_interval_returns_as_is():
    assert merge([(2, 8)]) == [(2, 8)]

def test_c3_negative_numbers_merge():
    assert merge([(-2, 0), (-2, 1)]) == [(-2, 1)]

def test_c1_negative_reversed_tuple_raises():
    with pytest.raises(ValueError):
        merge([(1, -5)])

def test_c2_negative_numbers_sorted_ascending():
    assert merge([(-1, 5), (-10, -3)]) == [(-10, -3), (-1, 5)]

def test_c3_large_numbers_merge():
    assert merge([(1000000, 2000000), (1500000, 3000000)]) == [(1000000, 3000000)]