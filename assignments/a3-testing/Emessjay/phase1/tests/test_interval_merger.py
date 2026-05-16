"""Tests for the `interval_merger` module, organized by spec clause.

Spec reference: specs/interval_merger.md (clauses C1..C6).
"""
import pytest

from interval_merger import merge


# -----------------------------------------------------------------------------
# C1. Input validation: start > end raises ValueError; no silent swap
# -----------------------------------------------------------------------------

class TestC1Validation:
    def test_reversed_tuple_raises(self):
        with pytest.raises(ValueError):
            merge([(5, 1)])

    def test_reversed_does_not_silently_swap(self):
        # If a buggy impl silently swaps to (1, 5), this catches it.
        with pytest.raises(ValueError):
            merge([(5, 1)])

    def test_reversed_among_valid_raises(self):
        with pytest.raises(ValueError):
            merge([(1, 3), (10, 5), (20, 25)])

    def test_zero_length_does_not_raise(self):
        # (k, k) is start == end, not start > end. Valid.
        result = merge([(3, 3)])
        assert result == [(3, 3)]

    def test_negative_endpoints_valid(self):
        assert merge([(-5, -1)]) == [(-5, -1)]

    def test_reversed_negative_raises(self):
        with pytest.raises(ValueError):
            merge([(-1, -5)])


# -----------------------------------------------------------------------------
# C2. Output sorted ascending by start
# -----------------------------------------------------------------------------

class TestC2OutputOrder:
    def test_already_sorted_input(self):
        assert merge([(1, 3), (5, 7), (10, 12)]) == [(1, 3), (5, 7), (10, 12)]

    def test_reversed_input_is_sorted(self):
        assert merge([(10, 12), (5, 7), (1, 3)]) == [(1, 3), (5, 7), (10, 12)]

    def test_jumbled_input_is_sorted(self):
        # Independent intervals with a gap; just verify ordering.
        result = merge([(20, 25), (1, 3), (10, 15), (30, 32)])
        assert result == [(1, 3), (10, 15), (20, 25), (30, 32)]

    def test_overlapping_jumbled_input_sorted_after_merge(self):
        result = merge([(8, 10), (1, 6), (2, 3)])
        assert result == [(1, 6), (8, 10)]


# -----------------------------------------------------------------------------
# C3. Merge semantics for closed intervals
# -----------------------------------------------------------------------------

class TestC3MergeSemantics:
    def test_overlapping_intervals_merge(self):
        assert merge([(1, 3), (2, 6)]) == [(1, 6)]

    def test_touching_endpoints_merge(self):
        # Closed intervals that share an endpoint must merge.
        assert merge([(1, 3), (3, 5)]) == [(1, 5)]

    def test_adjacent_integers_stay_separate(self):
        # 3 and 4 are distinct integers; no shared int → stay separate.
        assert merge([(1, 3), (4, 5)]) == [(1, 3), (4, 5)]

    def test_chain_of_overlaps(self):
        assert merge([(1, 3), (3, 5), (5, 7)]) == [(1, 7)]

    def test_full_containment_collapses(self):
        assert merge([(1, 10), (3, 5)]) == [(1, 10)]

    def test_identical_intervals_collapse(self):
        assert merge([(1, 5), (1, 5)]) == [(1, 5)]

    def test_min_start_max_end(self):
        # All overlap; result spans min start to max end.
        assert merge([(5, 8), (3, 6), (7, 10)]) == [(3, 10)]

    def test_two_independent_groups_preserved(self):
        result = merge([(1, 3), (4, 6), (8, 10), (2, 5), (7, 9)])
        # (1,3), (2,5), (4,6) all touch/overlap → (1, 6).
        # (7,9), (8,10): (7,9) and (8,10) overlap → (7, 10).
        # (1,6) and (7,10): 6,7 adjacent ints, no merge.
        assert result == [(1, 6), (7, 10)]


# -----------------------------------------------------------------------------
# C4. Zero-length intervals (k, k) participate in merging
# -----------------------------------------------------------------------------

class TestC4ZeroLength:
    def test_zero_length_alone(self):
        assert merge([(3, 3)]) == [(3, 3)]

    def test_zero_length_inside_other(self):
        # (3, 3) is just integer 3, which lives inside (1, 5).
        assert merge([(1, 5), (3, 3)]) == [(1, 5)]

    def test_zero_length_at_start_endpoint(self):
        assert merge([(1, 1), (1, 5)]) == [(1, 5)]

    def test_zero_length_at_end_endpoint(self):
        assert merge([(5, 5), (1, 5)]) == [(1, 5)]

    def test_zero_length_adjacent_to_other_stays_separate(self):
        # (2, 2) and (3, 5): integer 2 vs integers 3..5. No overlap.
        assert merge([(2, 2), (3, 5)]) == [(2, 2), (3, 5)]

    def test_two_zero_lengths_same_int_collapse(self):
        assert merge([(3, 3), (3, 3)]) == [(3, 3)]

    def test_two_zero_lengths_adjacent_stay_separate(self):
        # (1, 1) and (2, 2): adjacent ints, no shared integer.
        assert merge([(1, 1), (2, 2)]) == [(1, 1), (2, 2)]


# -----------------------------------------------------------------------------
# C5. Empty input
# -----------------------------------------------------------------------------

class TestC5Empty:
    def test_empty_returns_empty(self):
        assert merge([]) == []

    def test_empty_returns_list(self):
        assert isinstance(merge([]), list)


# -----------------------------------------------------------------------------
# C6. No mutation of input list or its tuples
# -----------------------------------------------------------------------------

class TestC6NoMutation:
    def test_input_list_contents_unchanged(self):
        original = [(1, 3), (2, 6), (8, 10)]
        snapshot = list(original)
        merge(original)
        assert original == snapshot

    def test_input_list_order_unchanged(self):
        original = [(8, 10), (1, 6), (2, 3)]
        snapshot = list(original)
        merge(original)
        assert original == snapshot
        # The first element must still be the first one we passed in.
        assert original[0] == (8, 10)

    def test_input_list_unchanged_when_input_invalid(self):
        original = [(1, 3), (5, 1)]
        snapshot = list(original)
        with pytest.raises(ValueError):
            merge(original)
        assert original == snapshot

    def test_input_list_length_unchanged(self):
        original = [(1, 3), (2, 6), (8, 10)]
        merge(original)
        assert len(original) == 3


# =============================================================================
# Adversarial probes — boundary semantics, mutation, output shape
# =============================================================================


class TestEndpointBoundary:
    """C3: closed intervals merge when they share an integer. The off-by-one
    in either direction is the prototypical bug here."""

    @pytest.mark.parametrize("a,b,expected", [
        # Touching endpoints: must merge.
        ((1, 3), (3, 5), [(1, 5)]),
        ((1, 3), (3, 3), [(1, 3)]),
        ((3, 3), (3, 5), [(3, 5)]),
        ((3, 3), (3, 3), [(3, 3)]),
        # Adjacent integers: must NOT merge.
        ((1, 3), (4, 5), [(1, 3), (4, 5)]),
        ((1, 1), (2, 2), [(1, 1), (2, 2)]),
        ((1, 1), (2, 5), [(1, 1), (2, 5)]),
        # Gap of 2: must NOT merge.
        ((1, 3), (5, 7), [(1, 3), (5, 7)]),
    ])
    def test_pairwise_boundary(self, a, b, expected):
        assert merge([a, b]) == expected

    def test_touching_with_gap_three_intervals(self):
        # First two touch, third is adjacent to merged result → stays separate.
        # (1,3) ∪ (3,5) = (1,5); (1,5) and (6,8) — 5 and 6 adjacent, no merge.
        assert merge([(1, 3), (3, 5), (6, 8)]) == [(1, 5), (6, 8)]

    def test_touching_with_overlap_three_intervals(self):
        # (1,3) ∪ (3,5) = (1,5); (1,5) and (5,7) touch at 5 → (1, 7).
        assert merge([(1, 3), (3, 5), (5, 7)]) == [(1, 7)]


class TestMergeOrderingIndependence:
    """C2 + C3: output is correct regardless of input ordering."""

    def test_same_intervals_any_order_same_result(self):
        from itertools import permutations
        intervals = [(8, 10), (1, 3), (2, 6), (15, 20), (12, 14)]
        # Reference result: (1,3) ∪ (2,6) = (1,6); (8,10) sep; (12,14) sep; (15,20) sep
        # 14 and 15 adjacent, no merge.
        expected = [(1, 6), (8, 10), (12, 14), (15, 20)]
        # Try a handful of permutations; all must give the same output.
        for perm in list(permutations(intervals))[:24]:  # cap at 24 to stay fast
            assert merge(list(perm)) == expected


class TestNoMutationDeep:
    """C6 in detail: input list, its tuples, and the order of elements
    must all be unchanged after merge — even on inputs that trigger
    interesting code paths (overlap, sort, validation error)."""

    def test_input_list_object_identity_of_elements_preserved(self):
        # Tuples are immutable, so we just verify each element is still ==
        # to the original tuple at the same position.
        original = [(8, 10), (1, 6), (2, 3)]
        copies = [t for t in original]  # references
        merge(original)
        for i, t in enumerate(copies):
            assert original[i] == t
            assert original[i] is t  # not replaced

    def test_input_unchanged_after_chain_merge(self):
        original = [(1, 3), (3, 5), (5, 7)]
        snap = list(original)
        merge(original)
        assert original == snap

    def test_input_unchanged_after_overlap_collapse(self):
        original = [(1, 10), (3, 5), (4, 6)]
        snap = list(original)
        merge(original)
        assert original == snap

    def test_input_unchanged_when_already_merged(self):
        # An input that's already in canonical form shouldn't be touched.
        original = [(1, 3), (5, 7)]
        snap = list(original)
        merge(original)
        assert original == snap

    def test_repeated_calls_do_not_mutate(self):
        original = [(8, 10), (1, 3), (4, 6)]
        snap = list(original)
        for _ in range(5):
            merge(original)
        assert original == snap


class TestOutputShape:
    def test_output_is_list(self):
        assert isinstance(merge([(1, 3), (2, 6)]), list)

    def test_output_elements_are_tuples(self):
        result = merge([(1, 3), (2, 6)])
        for r in result:
            assert isinstance(r, tuple)
            assert len(r) == 2

    def test_output_endpoints_are_ints(self):
        result = merge([(1, 3), (2, 6)])
        for start, end in result:
            assert isinstance(start, int) and isinstance(end, int)

    def test_idempotence(self):
        # Output of merge fed back as input must be unchanged.
        intervals = [(1, 3), (2, 6), (8, 10), (15, 20)]
        once = merge(intervals)
        twice = merge(once)
        assert once == twice


class TestRangeBreadth:
    """The spec doesn't restrict integer magnitude — verify negatives,
    zero, and large values all work."""

    def test_negative_intervals(self):
        assert merge([(-5, -1), (-2, 0)]) == [(-5, 0)]

    def test_negative_and_positive_span(self):
        assert merge([(-5, 5), (3, 10)]) == [(-5, 10)]

    def test_zero_crossing_touch(self):
        assert merge([(-2, 0), (0, 2)]) == [(-2, 2)]

    def test_zero_crossing_adjacent(self):
        # -1 and 0 are adjacent ints; (-2, -1) and (0, 2) share no integer.
        assert merge([(-2, -1), (0, 2)]) == [(-2, -1), (0, 2)]

    def test_large_integers(self):
        assert merge([(1_000_000, 2_000_000), (1_500_000, 3_000_000)]) == \
               [(1_000_000, 3_000_000)]

    def test_zero_only(self):
        assert merge([(0, 0)]) == [(0, 0)]


class TestMergeCorrectness:
    """End-to-end checks of merge's spec-level behavior on richer inputs."""

    def test_messy_overlap_chain(self):
        # All overlap into one giant interval.
        intervals = [(1, 5), (4, 9), (8, 12), (11, 15), (14, 20)]
        assert merge(intervals) == [(1, 20)]

    def test_two_separate_chains(self):
        intervals = [(1, 3), (3, 5), (10, 12), (12, 14)]
        assert merge(intervals) == [(1, 5), (10, 14)]

    def test_dropped_zero_length_bug_visible(self):
        # If a buggy impl drops zero-length intervals, this fails.
        # (3, 3) alone should be preserved.
        assert merge([(3, 3)]) == [(3, 3)]
        assert merge([(1, 1), (3, 3), (5, 5)]) == [(1, 1), (3, 3), (5, 5)]

    def test_merge_does_not_lose_intervals(self):
        # 5 disjoint intervals → 5 disjoint outputs.
        intervals = [(1, 2), (4, 5), (7, 8), (10, 11), (13, 14)]
        result = merge(intervals)
        assert result == intervals  # already sorted, no overlaps

    def test_single_element_pass_through(self):
        assert merge([(1, 5)]) == [(1, 5)]

    def test_all_overlap_collapses_to_one(self):
        intervals = [(1, 100), (50, 60), (40, 70), (90, 95)]
        assert merge(intervals) == [(1, 100)]

    def test_same_start_different_end_collapses(self):
        assert merge([(1, 5), (1, 3)]) == [(1, 5)]

    def test_same_end_different_start_collapses(self):
        assert merge([(1, 5), (3, 5)]) == [(1, 5)]


# =============================================================================
# Deeper adversarial probes — spec example replication, stress, duplicates,
# zero-length interactions, sort tiebreakers, validation edges
# =============================================================================


class TestSpecExamplesReproduced:
    """Re-test the exact examples from the spec — these are the canonical
    cases the spec author chose to publish."""

    def test_spec_example_overlap_and_disjoint(self):
        # merge([(1, 3), (2, 6), (8, 10)]) returns [(1, 6), (8, 10)]
        assert merge([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]

    def test_spec_example_touching(self):
        # merge([(1, 3), (3, 5)]) returns [(1, 5)] — endpoints touch at 3
        assert merge([(1, 3), (3, 5)]) == [(1, 5)]

    def test_spec_example_adjacent_stays_separate(self):
        # merge([(1, 3), (4, 5)]) returns [(1, 3), (4, 5)] — 3 and 4 distinct
        assert merge([(1, 3), (4, 5)]) == [(1, 3), (4, 5)]

    def test_spec_example_reversed_raises(self):
        # merge([(5, 1)]) raises ValueError — must NOT return [(1, 5)]
        with pytest.raises(ValueError):
            merge([(5, 1)])

    def test_spec_example_empty(self):
        # merge([]) returns []
        assert merge([]) == []


class TestStressManyIntervals:
    """Volume probes — many intervals at once."""

    def test_chain_of_100_touching(self):
        # (0,1), (1,2), ..., (99,100). Each pair shares an endpoint.
        intervals = [(i, i + 1) for i in range(100)]
        assert merge(intervals) == [(0, 100)]

    def test_chain_of_100_disjoint_zero_lengths(self):
        # (0,0), (2,2), (4,4), ..., (198,198). Each pair has gap of 1 int — separate.
        intervals = [(2 * i, 2 * i) for i in range(100)]
        assert merge(intervals) == intervals

    def test_alternating_groups(self):
        # 20 groups of 2 overlapping intervals each, separated by gaps.
        intervals = []
        for i in range(20):
            intervals.append((10 * i, 10 * i + 3))
            intervals.append((10 * i + 2, 10 * i + 5))
        # Each group merges to (10i, 10i+5). Between groups: 5 to 10 — 4-int gap.
        expected = [(10 * i, 10 * i + 5) for i in range(20)]
        assert merge(intervals) == expected

    def test_one_giant_interval_swallows_many(self):
        intervals = [(0, 1000)]
        intervals.extend([(i, i + 5) for i in range(10, 990, 10)])
        assert merge(intervals) == [(0, 1000)]

    def test_50_disjoint_pairs_jumbled(self):
        # Pairs at (k*100, k*100+10) and (k*100+5, k*100+15) → merge to (k*100, k*100+15).
        intervals = []
        for k in range(50):
            intervals.append((k * 100, k * 100 + 10))
            intervals.append((k * 100 + 5, k * 100 + 15))
        # Reverse the input to break any "input is already sorted" assumption.
        intervals.reverse()
        result = merge(intervals)
        expected = [(k * 100, k * 100 + 15) for k in range(50)]
        assert result == expected


class TestDuplicateHandling:
    """Identical-tuple handling — duplicates must collapse."""

    def test_n_copies_collapse_to_one(self):
        assert merge([(1, 5)] * 10) == [(1, 5)]

    def test_duplicate_zero_length_collapses(self):
        assert merge([(3, 3)] * 10) == [(3, 3)]

    def test_duplicates_with_distinct_intervals(self):
        intervals = [(1, 3), (1, 3), (5, 7), (5, 7), (5, 7)]
        assert merge(intervals) == [(1, 3), (5, 7)]

    def test_duplicates_after_merge_chain(self):
        # All collapse to (1, 7).
        intervals = [(1, 3), (1, 3), (3, 5), (5, 7), (5, 7)]
        assert merge(intervals) == [(1, 7)]


class TestSortTiebreakers:
    """Many intervals with the same start — verify ordering and merging."""

    def test_same_start_different_end_takes_max(self):
        intervals = [(1, 3), (1, 5), (1, 7)]
        assert merge(intervals) == [(1, 7)]

    def test_same_end_different_start_takes_min(self):
        intervals = [(1, 7), (3, 7), (5, 7)]
        assert merge(intervals) == [(1, 7)]

    def test_complex_same_start_groups(self):
        intervals = [(1, 5), (1, 3), (1, 4), (10, 12), (10, 11), (10, 15)]
        # All with start=1 → (1, 5). All with start=10 → (10, 15). 5 and 10: gap.
        assert merge(intervals) == [(1, 5), (10, 15)]

    def test_three_intervals_same_start_zero_length(self):
        # (1, 1), (1, 5), (1, 3) — all share start. Max end is 5.
        assert merge([(1, 1), (1, 5), (1, 3)]) == [(1, 5)]


class TestExtremeNesting:
    """Deeply nested containment and zero-length chains."""

    def test_full_containment_n_levels(self):
        # Five concentric intervals, all collapsing into the outermost.
        intervals = [(10 * i, 100 - 10 * i) for i in range(5)]
        assert merge(intervals) == [(0, 100)]

    def test_zero_length_inside_chain(self):
        # (1, 3), (3, 3), (3, 5) — all touch at 3.
        assert merge([(1, 3), (3, 3), (3, 5)]) == [(1, 5)]

    def test_zero_length_at_each_endpoint_chain(self):
        # Six intervals chaining via shared endpoints.
        intervals = [(1, 1), (1, 3), (3, 3), (3, 5), (5, 5), (5, 7)]
        assert merge(intervals) == [(1, 7)]

    def test_mixed_zero_and_nonzero_chain(self):
        # (0, 0), (0, 2), (2, 2), (2, 4): all share endpoints.
        assert merge([(0, 0), (0, 2), (2, 2), (2, 4)]) == [(0, 4)]


class TestZeroLengthInteractionDeeper:
    """Probe zero-length semantics from every angle."""

    def test_zero_length_only_at_distinct_ints(self):
        # Spaced by 2: each pair adjacent (no shared int) → all stay separate.
        assert merge([(1, 1), (3, 3), (5, 5), (7, 7)]) == [(1, 1), (3, 3), (5, 5), (7, 7)]

    def test_zero_length_between_two_overlapping(self):
        # (1, 5) absorbs (3, 3); (1, 5) overlaps (4, 7) → (1, 7).
        assert merge([(1, 5), (3, 3), (4, 7)]) == [(1, 7)]

    def test_zero_length_in_middle_of_other(self):
        assert merge([(1, 5), (3, 3)]) == [(1, 5)]

    def test_zero_length_at_negative(self):
        assert merge([(-5, -5), (-5, 0)]) == [(-5, 0)]

    def test_zero_length_outside_other_stays_separate(self):
        # (10, 10) outside (1, 5).
        assert merge([(1, 5), (10, 10)]) == [(1, 5), (10, 10)]

    def test_two_zero_lengths_at_same_int(self):
        assert merge([(3, 3), (3, 3), (3, 3)]) == [(3, 3)]


class TestValidationEdges:
    """C1: ValueError must be raised for any reversed tuple, regardless of
    where it lives in the input list."""

    def test_only_invalid_raises(self):
        with pytest.raises(ValueError):
            merge([(2, 1)])

    def test_first_element_invalid_raises(self):
        with pytest.raises(ValueError):
            merge([(10, 5), (1, 3)])

    def test_middle_element_invalid_raises(self):
        with pytest.raises(ValueError):
            merge([(1, 3), (10, 5), (15, 20)])

    def test_last_element_invalid_raises(self):
        with pytest.raises(ValueError):
            merge([(1, 3), (5, 7), (10, 5)])

    def test_zero_length_with_invalid_raises(self):
        with pytest.raises(ValueError):
            merge([(3, 3), (5, 1)])

    def test_invalid_with_otherwise_mergeable_raises(self):
        # If impl swallows invalid and merges the rest, this catches it.
        with pytest.raises(ValueError):
            merge([(1, 5), (3, 7), (100, 50)])

    def test_off_by_one_invalid_raises(self):
        # (5, 4) is reversed by exactly 1 — common off-by-one bug spot.
        with pytest.raises(ValueError):
            merge([(5, 4)])

    def test_negative_reversed_raises(self):
        with pytest.raises(ValueError):
            merge([(-1, -5)])


class TestNoMutationOnError:
    """C6: input list unchanged even when merge raises ValueError."""

    def test_input_unchanged_after_first_invalid(self):
        original = [(10, 5), (1, 3), (5, 7)]
        snapshot = list(original)
        with pytest.raises(ValueError):
            merge(original)
        assert original == snapshot

    def test_input_unchanged_after_middle_invalid(self):
        original = [(1, 3), (10, 5), (15, 20)]
        snapshot = list(original)
        with pytest.raises(ValueError):
            merge(original)
        assert original == snapshot

    def test_input_unchanged_after_last_invalid(self):
        # If impl partially-sorts the input before validating, this catches it.
        original = [(1, 3), (5, 7), (10, 5)]
        snapshot = list(original)
        with pytest.raises(ValueError):
            merge(original)
        assert original == snapshot


class TestOutputStructureStrict:
    """Beyond the basic 'is list of tuples' check — verify shape on richer inputs."""

    def test_output_is_list_for_single_interval(self):
        result = merge([(1, 5)])
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], tuple)

    def test_output_is_list_for_zero_length(self):
        result = merge([(3, 3)])
        assert isinstance(result, list)
        assert isinstance(result[0], tuple)

    def test_output_tuples_are_pairs(self):
        # Every element must be a 2-tuple, not a 3-tuple or 1-tuple.
        result = merge([(1, 3), (5, 7), (10, 12)])
        for r in result:
            assert isinstance(r, tuple)
            assert len(r) == 2

    def test_output_endpoints_preserve_int_type(self):
        # Don't accept the impl returning bools or floats accidentally.
        result = merge([(1, 5), (10, 15)])
        for start, end in result:
            assert type(start) is int and type(end) is int

    def test_output_contains_only_valid_intervals(self):
        # start <= end must hold for every output interval.
        intervals = [(1, 3), (5, 7), (3, 5), (10, 12)]
        result = merge(intervals)
        for start, end in result:
            assert start <= end

    def test_output_intervals_strictly_disjoint(self):
        # No two output intervals should overlap or touch.
        intervals = [(1, 3), (2, 5), (10, 15), (12, 20), (25, 30)]
        result = merge(intervals)
        for i in range(len(result) - 1):
            _, end_i = result[i]
            start_next, _ = result[i + 1]
            # Not touching, not overlapping. Adjacent ints are OK.
            assert end_i < start_next, \
                f"intervals {result[i]} and {result[i+1]} should not have merged"


class TestMergeNeverDropsCoverage:
    """Property: every integer covered by an input interval must be covered
    by some output interval."""

    def test_every_input_endpoint_covered(self):
        intervals = [(1, 3), (5, 8), (3, 4), (10, 10)]
        result = merge(intervals)

        def covers(point):
            return any(s <= point <= e for s, e in result)

        for s, e in intervals:
            assert covers(s), f"start {s} of {(s, e)} not covered by output"
            assert covers(e), f"end {e} of {(s, e)} not covered by output"

    def test_no_extraneous_coverage(self):
        # Output intervals shouldn't cover integers no input did.
        intervals = [(1, 3), (10, 12)]
        result = merge(intervals)
        # Integer 5 is not covered by any input.
        for s, e in result:
            assert not (s <= 5 <= e)


class TestRepeatedCallsConsistent:
    def test_same_input_same_output_across_calls(self):
        intervals = [(8, 10), (1, 6), (2, 3)]
        first = merge(list(intervals))
        second = merge(list(intervals))
        third = merge(list(intervals))
        assert first == second == third

    def test_idempotent_when_already_canonical(self):
        canonical = [(1, 6), (8, 10)]
        for _ in range(5):
            assert merge(canonical) == canonical
