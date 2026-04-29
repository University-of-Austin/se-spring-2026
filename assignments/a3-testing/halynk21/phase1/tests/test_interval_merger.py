import pytest
from interval_merger import merge


# ---------------------------------------------------------------------------
# C1 — Input validation
# ---------------------------------------------------------------------------

def test_c1_reversed_tuple_single_raises():
    with pytest.raises(ValueError):
        merge([(5, 1)])


def test_c1_reversed_in_multi_list_raises():
    with pytest.raises(ValueError):
        merge([(1, 3), (5, 1)])


def test_c1_equal_endpoints_valid():
    # start == end is NOT reversed; only start > end raises
    assert merge([(3, 3)]) == [(3, 3)]


# ---------------------------------------------------------------------------
# C2 — Output ordering
# ---------------------------------------------------------------------------

def test_c2_unsorted_input_produces_sorted_output():
    assert merge([(5, 7), (1, 3)]) == [(1, 3), (5, 7)]


# ---------------------------------------------------------------------------
# C3 — Merge semantics (parametrized; no standalone duplicates)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("intervals,expected", [
    ([(1, 3), (2, 6), (8, 10)], [(1, 6), (8, 10)]),   # overlap → merge; separate stays
    ([(1, 3), (3, 5)],          [(1, 5)]),              # touching endpoints → merge
    ([(1, 3), (4, 5)],          [(1, 3), (4, 5)]),      # adjacent (3,4) → stay separate
    ([(1, 10), (3, 5)],         [(1, 10)]),              # nested → absorbed
    ([(5, 7), (1, 3)],          [(1, 3), (5, 7)]),       # unsorted → sorted output (C2)
    ([(1, 3), (3, 5), (5, 7)],  [(1, 7)]),               # three-way chain merge
    ([(-5, -3), (-2, 0)],       [(-5, -3), (-2, 0)]),    # negatives, adjacent → separate
], ids=["overlap", "touching", "adjacent", "nested", "unsorted", "chain", "negatives"])
def test_c3_c2_merge_scenarios(intervals, expected):
    assert merge(intervals) == expected


# ---------------------------------------------------------------------------
# C4 — Zero-length intervals
# ---------------------------------------------------------------------------

def test_c4_zero_length_standalone():
    assert merge([(3, 3)]) == [(3, 3)]


def test_c4_zero_length_merges_into_overlapping():
    # Spec example: (3,3) merges with (1,5) into (1,5)
    assert merge([(3, 3), (1, 5)]) == [(1, 5)]


# ---------------------------------------------------------------------------
# C5 — Empty input
# ---------------------------------------------------------------------------

def test_c5_empty_input_returns_empty():
    assert merge([]) == []


# ---------------------------------------------------------------------------
# C6 — No mutation
# ---------------------------------------------------------------------------

def test_c6_input_list_not_mutated():
    intervals = [(3, 5), (1, 4)]
    original = [(3, 5), (1, 4)]
    merge(intervals)
    assert intervals == original


def test_c6_input_order_preserved():
    # Out-of-order input: list order (not just contents) must be unchanged.
    # This catches sort()-in-place, which reorders even if contents are same.
    intervals = [(5, 7), (1, 3), (8, 10)]
    before = list(intervals)
    merge(intervals)
    assert intervals == before


# ---------------------------------------------------------------------------
# Hidden tests
# ---------------------------------------------------------------------------

def test_hidden_duplicate_identical_intervals():
    # C3: (1,5) and (1,5) fully overlap (share every integer) → merge to [(1,5)].
    # A dedup-skipping impl might return [(1,5),(1,5)].
    assert merge([(1, 5), (1, 5)]) == [(1, 5)]


def test_hidden_adjacent_zero_length_intervals_stay_separate():
    # C3 adjacent rule + C4 zero-length rule combined.
    # Integers 2 and 3 are adjacent (no shared integer) → stay separate.
    # Neither clause individually demonstrates zero-length adjacent behavior.
    assert merge([(2, 2), (3, 3)]) == [(2, 2), (3, 3)]


def test_hidden_zero_length_at_boundary_of_range():
    # C3: touching endpoints merge. C4: zero-length participates the same way.
    # (5,5) touches (1,5) at endpoint 5 → should merge to (1,5).
    # Neither clause individually demonstrates this combination.
    assert merge([(1, 5), (5, 5)]) == [(1, 5)]
