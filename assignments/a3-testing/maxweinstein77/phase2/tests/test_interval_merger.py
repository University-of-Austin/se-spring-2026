from interval_merger import merge
import pytest

## C1. Input validation

# What if I pass a single valid interval?
def test_c1_single_valid_interval_works():
    result = merge([(1, 3)])
    assert result == [(1, 3)]

# What if a tuple is reversed (start > end)?
def test_c1_reversed_tuple_raises_value_error():
    with pytest.raises(ValueError):
        merge([(5, 1)])

# What if a reversed tuple is mixed in with valid ones (catches lazy validation)?
def test_c1_reversed_tuple_in_middle_of_list_raises():
    with pytest.raises(ValueError):
        merge([(1, 3), (5, 1), (10, 12)])

# What if I pass a valid interval with negative numbers?
def test_c1_valid_negative_interval_works():
    result = merge([(-5, -1)])
    assert result == [(-5, -1)]

# What if a negative tuple is reversed (catches abs comparison bugs)?
def test_c1_reversed_negative_tuple_raises():
    with pytest.raises(ValueError):
        merge([(-1, -5)])

## C2. Output ordering

# What if the input is already sorted?
def test_c2_already_sorted_input_returns_sorted():
    result = merge([(1, 2), (5, 6), (9, 10)])
    assert result == [(1, 2), (5, 6), (9, 10)]

# What if the input is reverse-sorted?
def test_c2_reverse_sorted_input_returns_sorted():
    result = merge([(9, 10), (5, 6), (1, 2)])
    assert result == [(1, 2), (5, 6), (9, 10)]

# What if the input is in random order?
def test_c2_mixed_order_input_returns_sorted():
    result = merge([(5, 6), (1, 2), (9, 10)])
    assert result == [(1, 2), (5, 6), (9, 10)]

# What if some intervals have negative starts and some positive (sort handles signs correctly)?
def test_c2_negative_and_positive_starts_sort_correctly():
    result = merge([(1, 2), (-5, -3), (-10, -8)])
    assert result == [(-10, -8), (-5, -3), (1, 2)]

## C3. Merge semantics

# What if two intervals overlap?
def test_c3_basic_overlap_merges():
    result = merge([(1, 3), (2, 6)])
    assert result == [(1, 6)]

# What if two intervals only touch at a single integer endpoint?
def test_c3_touching_endpoints_merge():
    result = merge([(1, 3), (3, 5)])
    assert result == [(1, 5)]

# What if two intervals are next to each other but share no integer (adjacent, not touching)?
def test_c3_adjacent_intervals_stay_separate():
    result = merge([(1, 3), (4, 5)])
    assert result == [(1, 3), (4, 5)]

# What if one interval is fully contained within another?
def test_c3_contained_interval_collapses_to_larger():
    result = merge([(1, 10), (3, 5)])
    assert result == [(1, 10)]

# What if three intervals chain transitively (the middle one bridges the other two)?
def test_c3_indirect_chain_merges_transitively():
    result = merge([(1, 3), (5, 8), (3, 5)])
    assert result == [(1, 8)]

# What if I have two identical intervals?
def test_c3_identical_intervals_collapse():
    result = merge([(1, 3), (1, 3)])
    assert result == [(1, 3)]

# What if overlapping intervals span across zero (negative + positive)?
def test_c3_negative_and_positive_overlap_merges():
    result = merge([(-3, 0), (-1, 2)])
    assert result == [(-3, 2)]

# What if there are multiple separate merge groups in the same call?
def test_c3_multiple_separate_merge_groups():
    result = merge([(1, 3), (2, 5), (10, 15), (12, 18)])
    assert result == [(1, 5), (10, 18)]

# What if multiple separate merge groups are interleaved (not sorted) in the input?
def test_c3_interleaved_merge_groups():
    result = merge([(10, 12), (1, 3), (11, 14), (2, 5)])
    assert result == [(1, 5), (10, 14)]

# What if a long chain of intervals all touch endpoint to endpoint?
def test_c3_chain_of_touching_intervals_all_merge():
    result = merge([(1, 3), (3, 5), (5, 7), (7, 9)])
    assert result == [(1, 9)]

# What if one big interval contains many smaller intervals inside it?
def test_c3_one_outer_interval_consumes_many_inner():
    result = merge([(1, 100), (5, 10), (50, 60), (90, 95)])
    assert result == [(1, 100)]

# What if I have a chain of negative-only intervals all touching at endpoints?
def test_c3_negative_only_chain_merges_through_touching():
    result = merge([(-10, -7), (-7, -4), (-4, -1)])
    assert result == [(-10, -1)]

# What if I have a chain mixing zero-length and regular intervals?
def test_c3_mix_of_zero_length_and_regular_chain_merges():
    result = merge([(1, 1), (1, 3), (3, 3)])
    assert result == [(1, 3)]

## C4. Zero-length intervals

# What if I pass a single zero-length interval?
def test_c4_single_zero_length_interval_returns_as_is():
    result = merge([(3, 3)])
    assert result == [(3, 3)]

# What if a zero-length interval sits inside a larger interval?
def test_c4_zero_length_inside_larger_interval_merges():
    result = merge([(3, 3), (1, 5)])
    assert result == [(1, 5)]

# What if a zero-length interval shares no integers with a far-away interval?
def test_c4_zero_length_and_far_interval_stay_separate():
    result = merge([(3, 3), (7, 9)])
    assert result == [(3, 3), (7, 9)]

# What if I have two identical zero-length intervals?
def test_c4_identical_zero_length_intervals_collapse():
    result = merge([(3, 3), (3, 3)])
    assert result == [(3, 3)]

# What if a zero-length interval touches another from the left?
def test_c4_zero_length_touching_from_left_merges():
    result = merge([(3, 3), (2, 3)])
    assert result == [(2, 3)]

# What if a zero-length interval touches another from the right?
def test_c4_zero_length_touching_from_right_merges():
    result = merge([(3, 3), (3, 5)])
    assert result == [(3, 5)]

## C5. Empty input

# What if the input is an empty list?
def test_c5_empty_input_returns_empty_list():
    result = merge([])
    assert result == []

## C6. No mutation

# What if I check the input list after a normal merge call (sorting + merging)?
def test_c6_input_list_unchanged_after_normal_merge():
    intervals = [(9, 10), (1, 3), (2, 5)]
    merge(intervals)
    assert intervals == [(9, 10), (1, 3), (2, 5)]

# What if merge raises ValueError partway through (does it still leave the input untouched)?
def test_c6_input_list_unchanged_when_merge_raises():
    intervals = [(1, 3), (5, 1), (10, 12)]
    with pytest.raises(ValueError):
        merge(intervals)
    assert intervals == [(1, 3), (5, 1), (10, 12)]
