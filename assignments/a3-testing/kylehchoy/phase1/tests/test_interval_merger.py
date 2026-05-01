"""Phase 1 tests for `interval_merger` module.

Tests are organized clause-by-clause against
starter/assignment3/specs/interval_merger.md. Each test name encodes the
clause it pins down (e.g. test_c3_touching_endpoints_merge).
"""
import copy
import pytest

from interval_merger import merge


def _assert_canonical(intervals: list[tuple[int, int]]) -> None:
    """Assert intervals are sorted and fully merged for closed semantics."""
    for i in range(len(intervals) - 1):
        a_start, a_end = intervals[i]
        b_start, b_end = intervals[i + 1]
        assert a_start <= b_start
        assert a_end < b_start   # closed intervals: touching would be a_end == b_start and should merge


def _covered_in_any(x: int, intervals: list[tuple[int, int]]) -> bool:
    return any(start <= x <= end for start, end in intervals)


def _assert_same_integer_coverage(inp: list[tuple[int, int]], out: list[tuple[int, int]]) -> None:
    lo = min(start for start, _ in inp)
    hi = max(end for _, end in inp)
    for x in range(lo, hi + 1):
        assert _covered_in_any(x, inp) == _covered_in_any(x, out)


# ---------------------------------------------------------------------------
# C1. Input validation — start > end raises ValueError, no silent swap.
# ---------------------------------------------------------------------------

def test_c1_reversed_tuple_raises():
    with pytest.raises(ValueError):
        merge([(5, 1)])


def test_c1_invalid_in_middle_raises():
    with pytest.raises(ValueError):
        merge([(1, 3), (8, 5), (10, 12)])


def test_c1_invalid_in_last_position_raises():
    with pytest.raises(ValueError):
        merge([(1, 3), (5, 7), (10, 9)])


# ---------------------------------------------------------------------------
# C2. Output sorted ascending by start.
# ---------------------------------------------------------------------------

def test_c2_reversed_input_produces_sorted_output():
    out = merge([(8, 10), (1, 3)])
    assert out == [(1, 3), (8, 10)]


def test_c2_interleaved_input_produces_sorted_output():
    out = merge([(8, 10), (1, 3), (15, 20), (5, 6)])
    assert out == [(1, 3), (5, 6), (8, 10), (15, 20)]


# ---------------------------------------------------------------------------
# C3. Merge semantics — overlap, touching, adjacent.
# ---------------------------------------------------------------------------

def test_c3_overlapping_intervals_merge():
    assert merge([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]


def test_c3_touching_endpoints_merge():
    # (1, 3) and (3, 5) share the integer 3 — closed-interval merge.
    assert merge([(1, 3), (3, 5)]) == [(1, 5)]


def test_c3_adjacent_intervals_stay_separate():
    # (1, 3) and (4, 5) are adjacent integers but share no integer — stay separate.
    assert merge([(1, 3), (4, 5)]) == [(1, 3), (4, 5)]


def test_c3_chain_merge_spans_min_to_max():
    # Many intervals collapsing to one — the result spans from minimum start
    # to maximum end.
    assert merge([(1, 4), (3, 7), (6, 10), (9, 12)]) == [(1, 12)]


def test_c3_one_interval_contains_another():
    # (1, 100) fully contains (20, 30) — merge to the larger interval.
    assert merge([(1, 100), (20, 30)]) == [(1, 100)]


# ---------------------------------------------------------------------------
# C4. Zero-length intervals (k, k).
# ---------------------------------------------------------------------------

def test_c4_zero_length_alone_in_output():
    assert merge([(3, 3)]) == [(3, 3)]


def test_c4_zero_length_merges_into_containing_interval():
    # (3, 3) is the integer 3, which is inside (1, 5) — merge to (1, 5).
    assert merge([(1, 5), (3, 3)]) == [(1, 5)]


def test_c4_zero_length_touching_endpoint_merges():
    # (5, 5) shares endpoint 5 with (1, 5) — merge.
    assert merge([(1, 5), (5, 5)]) == [(1, 5)]


def test_c4_two_zero_length_at_same_point_merge():
    assert merge([(3, 3), (3, 3)]) == [(3, 3)]


# ---------------------------------------------------------------------------
# C5. Empty input.
# ---------------------------------------------------------------------------

def test_c5_empty_input_returns_empty_list():
    assert merge([]) == []


# ---------------------------------------------------------------------------
# C6. No mutation of input list.
# ---------------------------------------------------------------------------

def test_c6_input_list_not_mutated():
    original = [(8, 10), (1, 3), (2, 6)]
    snapshot = copy.deepcopy(original)
    merge(original)
    assert original == snapshot


def test_c6_input_list_length_preserved():
    original = [(1, 3), (2, 6), (8, 10), (15, 20)]
    pre_len = len(original)
    merge(original)
    assert len(original) == pre_len


def test_c6_input_tuples_identity_preserved():
    # Stronger form: not only is the list equal, but the same tuple objects
    # are still in the same positions. Catches an implementation that builds
    # a new list with reordered or copied tuples in the input.
    t1, t2, t3 = (8, 10), (1, 3), (2, 6)
    original = [t1, t2, t3]
    merge(original)
    assert original[0] is t1
    assert original[1] is t2
    assert original[2] is t3


# ===========================================================================
# Implication pass — spec-implied edge cases.
# ===========================================================================

# Boundary lens -------------------------------------------------------------

def test_zero_length_at_start_endpoint_merges():
    # Symmetric to the existing end-endpoint test: (1, 1) at the START of
    # (1, 5) shares endpoint 1 — must merge.
    assert merge([(1, 1), (1, 5)]) == [(1, 5)]


def test_zero_length_chain_all_distinct_points():
    # Several zero-length intervals at distinct points stay separate AND
    # come back sorted.
    assert merge([(5, 5), (1, 1), (3, 3)]) == [(1, 1), (3, 3), (5, 5)]


# Absence lens --------------------------------------------------------------

def test_input_not_mutated_on_error_path():
    # DM-borderline: spec C6 says no mutation. Defensible reading is that
    # this is unconditional, not just on the success path. An impl that
    # sorts in place and then validates would mutate before raising.
    original = [(1, 3), (5, 7), (10, 9), (15, 20)]
    snapshot = copy.deepcopy(original)
    with pytest.raises(ValueError):
        merge(original)
    assert original == snapshot


# Interaction lens ----------------------------------------------------------

def test_combined_unsorted_overlapping_and_zero_length():
    # Stress combo: out-of-order input, overlap chains, zero-lengths inside
    # ranges, zero-lengths at boundaries.
    inp = [(8, 10), (1, 3), (2, 5), (3, 3), (10, 12), (20, 20)]
    # (1,3)+(2,5) → (1,5); (3,3) inside → still (1,5); (8,10)+(10,12) → (8,12)
    # (20,20) standalone.
    assert merge(inp) == [(1, 5), (8, 12), (20, 20)]


def test_long_chain_collapses_to_one_interval():
    # A long chain of touching/overlapping intervals collapses to a single
    # span from min start to max end.
    inp = [(i, i + 2) for i in range(0, 20, 2)]   # (0,2),(2,4),(4,6),...,(18,20)
    assert merge(inp) == [(0, 20)]


def test_singleton_non_zero_input():
    # Single interval, no merging possible — should round-trip unchanged.
    assert merge([(1, 5)]) == [(1, 5)]


def test_negative_integers_handled():
    # Spec says "integers"; doesn't restrict to non-negative. A bug using
    # abs() or unsigned arithmetic on bounds would slip through without this.
    assert merge([(-5, -1), (-3, 0)]) == [(-5, 0)]


def test_already_sorted_non_overlapping_passes_through():
    # Already-sorted, no merges — output equals input.
    assert merge([(1, 3), (5, 7), (10, 12)]) == [(1, 3), (5, 7), (10, 12)]


def test_duplicate_identical_intervals_merge():
    # Two identical non-zero intervals share every integer — must merge per C3.
    assert merge([(1, 5), (1, 5)]) == [(1, 5)]


def test_max_end_appears_earlier_than_min_start_in_input():
    # Stress for "running max" tracking: the largest-end interval is first
    # in input, then smaller-end intervals follow. Result must span min→max.
    assert merge([(1, 100), (2, 5), (3, 4)]) == [(1, 100)]


def test_returns_new_list_object_not_input_reference():
    data = [(1, 3), (2, 4)]
    out = merge(data)
    assert out == [(1, 4)]
    assert out is not data


def test_large_magnitude_bounds_merge_correctly():
    intervals = [(-10**9, -5), (-7, 3), (3, 10**9)]
    assert merge(intervals) == [(-10**9, 10**9)]


def test_duplicates_out_of_order_and_touching_collapse():
    intervals = [(5, 7), (1, 3), (3, 5), (1, 3), (7, 9)]
    # (1,3)+(3,5)+(5,7)+(7,9) all connect under closed-interval touching.
    assert merge(intervals) == [(1, 9)]


@pytest.mark.parametrize("bad_interval", [(1,), (1, 2, 3), "1,2", 123, None])
def test_c1_invalid_interval_shape_or_type_raises(bad_interval):
    with pytest.raises((TypeError, ValueError)):
        merge([bad_interval])


def test_output_has_no_touching_pairs_left():
    out = merge([(1, 3), (3, 5), (5, 7), (10, 12)])
    assert out == [(1, 7), (10, 12)]


def test_union_coverage_preserved_simple_case():
    inp = [(1, 2), (2, 4), (7, 7)]
    out = merge(inp)
    assert out == [(1, 4), (7, 7)]


def test_malformed_interval_among_valid_raises():
    with pytest.raises((TypeError, ValueError)):
        merge([(1, 3), (2,), (4, 5)])


def test_nested_touching_duplicate_chain():
    assert merge([(1, 10), (2, 3), (10, 12), (1, 10)]) == [(1, 12)]


def test_canonical_input_returns_equal_intervals():
    inp = [(-5, -3), (0, 0), (2, 4)]
    out = merge(inp)
    assert out == inp


@pytest.mark.parametrize(
    "inp",
    [
        [(8, 10), (1, 3), (2, 6), (10, 12), (20, 21)],
        [(20, 21), (10, 12), (2, 6), (1, 3), (8, 10)],
        [(1, 3), (20, 21), (8, 10), (2, 6), (10, 12)],
    ],
)
def test_permutation_invariance_for_same_interval_set(inp):
    assert merge(inp) == [(1, 6), (8, 12), (20, 21)]


def test_output_is_canonical_on_complex_input():
    out = merge([(1, 3), (3, 5), (8, 10), (9, 12), (20, 22)])
    assert out == [(1, 5), (8, 12), (20, 22)]
    _assert_canonical(out)


def test_integer_coverage_equivalence_on_crafted_case():
    inp = [(-3, -1), (-1, 2), (5, 5), (6, 8), (8, 9)]
    out = merge(inp)
    assert out == [(-3, 2), (5, 5), (6, 9)]
    _assert_canonical(out)
    _assert_same_integer_coverage(inp, out)


def test_same_start_different_ends_merge_to_largest_end():
    # Same-start intervals stress both sorting ties and max-end tracking.
    assert merge([(5, 7), (5, 10), (1, 5)]) == [(1, 10)]


def test_negative_adjacent_intervals_stay_separate():
    # Closed intervals merge when they share an integer; -1 and 0 are adjacent
    # but distinct, so these ranges must remain separate.
    assert merge([(-3, -1), (0, 2)]) == [(-3, -1), (0, 2)]


def test_touching_negative_to_zero_endpoint_merges():
    assert merge([(-3, 0), (0, 2)]) == [(-3, 2)]
