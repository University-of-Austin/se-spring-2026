"""Tests for cart.Cart, organized by spec clause (C1..C7).

Spec: starter/assignment3/specs/cart.md

All amounts are integer cents. Shipping is 500 cents. FREESHIP threshold is 5000.
"""
import pytest

from cart import Cart


SHIPPING = 500
FREESHIP_THRESHOLD = 5000


# =========================================================================
# C1. add_item validation
# =========================================================================

@pytest.mark.parametrize("bad_qty", [0, -1, -10])
def test_c1_qty_zero_or_negative_raises(bad_qty):
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("sku", bad_qty, 100)


@pytest.mark.parametrize("bad_price", [-1, -100])
def test_c1_negative_unit_price_raises(bad_price):
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("sku", 1, bad_price)


def test_c1_unit_price_zero_is_allowed():
    """unit_price_cents must be NON-NEGATIVE; 0 is allowed."""
    cart = Cart()
    cart.add_item("freebie", 1, 0)
    # No exception. And total reflects only shipping for non-empty cart.
    assert cart.total_cents() == 0 + SHIPPING


def test_c1_qty_one_is_allowed():
    cart = Cart()
    cart.add_item("sku", 1, 100)
    assert cart.total_cents() == 100 + SHIPPING


def test_c1_duplicate_sku_raises():
    cart = Cart()
    cart.add_item("sku", 1, 100)
    with pytest.raises(ValueError):
        cart.add_item("sku", 2, 200)


def test_c1_duplicate_sku_does_not_modify_existing_line():
    """Even though the duplicate raises, the original line item should be intact."""
    cart = Cart()
    cart.add_item("sku", 1, 100)
    with pytest.raises(ValueError):
        cart.add_item("sku", 5, 999)
    assert cart.total_cents() == 100 + SHIPPING


def test_c1_different_skus_can_coexist():
    cart = Cart()
    cart.add_item("a", 1, 100)
    cart.add_item("b", 2, 50)
    # 100 + 100 = 200, plus 500 shipping
    assert cart.total_cents() == 200 + SHIPPING


# =========================================================================
# C2. apply_code returns
# =========================================================================

def test_c2_known_code_returns_true():
    cart = Cart()
    cart.add_item("a", 1, 100)
    assert cart.apply_code("SAVE10") is True


def test_c2_unknown_code_returns_false():
    cart = Cart()
    assert cart.apply_code("BOGUS") is False


def test_c2_duplicate_application_returns_false():
    cart = Cart()
    cart.add_item("a", 1, 100)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE10") is False


@pytest.mark.parametrize("bad_case", ["save10", "Save10", "save20", "flat5",
                                       "freeship", "bogo_bagel", "FREEship"])
def test_c2_codes_are_case_sensitive(bad_case):
    cart = Cart()
    assert cart.apply_code(bad_case) is False


def test_c2_empty_string_is_unknown():
    cart = Cart()
    assert cart.apply_code("") is False


def test_c2_unknown_code_does_not_affect_total():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("BOGUS")
    assert cart.total_cents() == 1000 + SHIPPING


def test_c2_duplicate_application_does_not_double_apply():
    """Calling SAVE10 twice should NOT apply 10% twice."""
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("SAVE10")
    cart.apply_code("SAVE10")  # rejected
    # 1000 - 100 = 900, plus 500 shipping
    assert cart.total_cents() == 900 + SHIPPING


# =========================================================================
# C3. Known codes — basic effects
# =========================================================================

def test_c3_save10_takes_ten_percent():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("SAVE10")
    # 1000 - 100 = 900, plus shipping
    assert cart.total_cents() == 900 + SHIPPING


def test_c3_save20_takes_twenty_percent():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("SAVE20")
    # 1000 - 200 = 800, plus shipping
    assert cart.total_cents() == 800 + SHIPPING


def test_c3_flat5_takes_500_off():
    cart = Cart()
    cart.add_item("a", 1, 2000)
    cart.apply_code("FLAT5")
    # 2000 - 500 = 1500, plus shipping
    assert cart.total_cents() == 1500 + SHIPPING


def test_c3_bogo_bagel_one_free_per_pair():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    # 2*300 = 600, BOGO drops 1 = 300, plus shipping
    assert cart.total_cents() == 300 + SHIPPING


def test_c3_bogo_bagel_three_qty_one_free():
    """qty // 2 free: 3 // 2 = 1 free."""
    cart = Cart()
    cart.add_item("bagel", 3, 300)
    cart.apply_code("BOGO_BAGEL")
    # 3*300 = 900, 1 free = -300, post-BOGO = 600, plus shipping
    assert cart.total_cents() == 600 + SHIPPING


def test_c3_bogo_bagel_four_qty_two_free():
    cart = Cart()
    cart.add_item("bagel", 4, 300)
    cart.apply_code("BOGO_BAGEL")
    # 4*300 = 1200, 2 free = -600, post-BOGO = 600, plus shipping
    assert cart.total_cents() == 600 + SHIPPING


def test_c3_bogo_bagel_one_qty_no_discount():
    """qty // 2 = 0 free when qty is 1."""
    cart = Cart()
    cart.add_item("bagel", 1, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 300 + SHIPPING


def test_c3_bogo_bagel_no_bagel_in_cart_no_effect_but_applied():
    """BOGO_BAGEL with no bagel: no effect on total, but counts as applied."""
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.total_cents() == 1000 + SHIPPING
    # Second application is a duplicate.
    assert cart.apply_code("BOGO_BAGEL") is False


def test_c3_bogo_bagel_only_affects_bagel_sku():
    """BOGO_BAGEL is keyed to 'bagel' SKU specifically — case-sensitive."""
    cart = Cart()
    cart.add_item("Bagel", 4, 300)  # capital B - not "bagel"
    cart.apply_code("BOGO_BAGEL")
    # Should have no effect.
    assert cart.total_cents() == 1200 + SHIPPING


def test_c3_freeship_above_threshold_waives_shipping():
    cart = Cart()
    cart.add_item("a", 1, 6000)
    cart.apply_code("FREESHIP")
    # 6000 >= 5000, shipping waived
    assert cart.total_cents() == 6000


def test_c3_freeship_below_threshold_keeps_shipping():
    cart = Cart()
    cart.add_item("a", 1, 4999)
    cart.apply_code("FREESHIP")
    # 4999 < 5000, shipping kept
    assert cart.total_cents() == 4999 + SHIPPING


def test_c3_freeship_exactly_at_threshold_waives_shipping():
    """C3 spec: 'when ... pre-shipping subtotal is >= 5000'. 5000 itself is included."""
    cart = Cart()
    cart.add_item("a", 1, 5000)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5000


def test_c3_freeship_one_below_threshold_keeps_shipping():
    """Boundary: 4999 means shipping is NOT waived."""
    cart = Cart()
    cart.add_item("a", 1, 4999)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 4999 + SHIPPING


def test_c3_freeship_after_discount_below_threshold():
    """FREESHIP looks at POST-discount pre-shipping subtotal."""
    cart = Cart()
    cart.add_item("a", 1, 5500)
    cart.apply_code("SAVE10")  # 5500 - 550 = 4950
    cart.apply_code("FREESHIP")
    # 4950 < 5000 → shipping kept
    assert cart.total_cents() == 4950 + SHIPPING


def test_c3_freeship_after_discount_above_threshold():
    cart = Cart()
    cart.add_item("a", 1, 6000)
    cart.apply_code("SAVE10")  # 6000 - 600 = 5400
    cart.apply_code("FREESHIP")
    # 5400 >= 5000 → shipping waived
    assert cart.total_cents() == 5400


# =========================================================================
# C4. Stacking rules
# =========================================================================

def test_c4_save10_then_save20_rejects_save20():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False
    # SAVE20 ignored: total reflects SAVE10
    assert cart.total_cents() == 900 + SHIPPING


def test_c4_save20_then_save10_rejects_save10():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("SAVE10") is False
    # SAVE10 ignored: total reflects SAVE20
    assert cart.total_cents() == 800 + SHIPPING


def test_c4_flat5_stacks_with_save10():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    # 10000 - 1000 = 9000, then -500 = 8500, +500 shipping = 9000
    assert cart.total_cents() == 8500 + SHIPPING


def test_c4_flat5_stacks_with_save20():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("FLAT5") is True
    # 10000 - 2000 = 8000, then -500 = 7500, +500 shipping
    assert cart.total_cents() == 7500 + SHIPPING


def test_c4_bogo_stacks_with_percent():
    cart = Cart()
    cart.add_item("bagel", 4, 300)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("SAVE10") is True
    # 1200 subtotal, -600 BOGO = 600, -10% = 540, +500 shipping
    assert cart.total_cents() == 540 + SHIPPING


def test_c4_bogo_stacks_with_flat5():
    cart = Cart()
    cart.add_item("bagel", 4, 500)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("FLAT5") is True
    # 2000 subtotal, -1000 BOGO = 1000, -500 FLAT5 = 500, +500 shipping
    assert cart.total_cents() == 500 + SHIPPING


def test_c4_freeship_stacks_with_percent():
    cart = Cart()
    cart.add_item("a", 1, 6000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FREESHIP") is True
    # 6000 - 600 = 5400 >= 5000, shipping waived
    assert cart.total_cents() == 5400


def test_c4_freeship_stacks_with_flat5():
    cart = Cart()
    cart.add_item("a", 1, 6000)
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True
    # 6000 - 500 = 5500 >= 5000, shipping waived
    assert cart.total_cents() == 5500


def test_c4_all_compatible_codes_stack():
    """SAVE10 + FLAT5 + BOGO_BAGEL + FREESHIP should all apply together."""
    cart = Cart()
    cart.add_item("bagel", 4, 2000)  # 8000 subtotal
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True
    # Subtotal 8000, -BOGO 4000 = 4000, -10% = 3600, -FLAT5 = 3100, ship+ since 3100<5000 → +500
    assert cart.total_cents() == 3100 + SHIPPING


def test_c4_save20_rejected_does_not_apply_after_save10():
    """When SAVE20 is rejected, only SAVE10 effect remains."""
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("SAVE10")
    cart.apply_code("SAVE20")  # rejected
    # Confirm only 10% was applied, not 20% or both
    assert cart.total_cents() == 900 + SHIPPING


# =========================================================================
# C5. Application order
# =========================================================================

def test_c5_bogo_applied_before_percent():
    """C5 step 2: BOGO before step 3: percent."""
    cart = Cart()
    cart.add_item("bagel", 2, 1000)  # 2000 subtotal
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    # If percent applied first: 2000 - 200 = 1800, then BOGO -1000 = 800
    # If BOGO first: 2000 - 1000 = 1000, then -10% = 900
    # Spec says BOGO first → 900
    assert cart.total_cents() == 900 + SHIPPING


def test_c5_flat5_applied_after_percent():
    """C5 step 4: FLAT5 after step 3: percent."""
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    # If FLAT5 first: 1000 - 500 = 500, then -10% = 450
    # Spec says percent first: 1000 - 100 = 900, then -500 = 400
    assert cart.total_cents() == 400 + SHIPPING


def test_c5_flat5_clamps_at_zero():
    """Step 4: FLAT5 making pre-shipping negative clamps at 0."""
    cart = Cart()
    cart.add_item("a", 1, 300)
    cart.apply_code("FLAT5")
    # 300 - 500 = -200, clamp to 0; +500 shipping
    assert cart.total_cents() == 0 + SHIPPING


def test_c5_flat5_clamp_then_freeship_below_threshold():
    """After FLAT5 clamps to 0, FREESHIP cannot waive shipping (0 < 5000)."""
    cart = Cart()
    cart.add_item("a", 1, 300)
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    # pre-shipping = 0 (clamped), 0 < 5000, shipping NOT waived
    assert cart.total_cents() == 0 + SHIPPING


def test_c5_flat5_exact_zero_then_shipping():
    """500 - 500 = 0 exactly. Not negative — still clamps fine."""
    cart = Cart()
    cart.add_item("a", 1, 500)
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 0 + SHIPPING


def test_c5_full_pipeline_example():
    """End-to-end through every step."""
    cart = Cart()
    cart.add_item("bagel", 2, 5000)  # subtotal 10000
    cart.add_item("widget", 1, 5000)  # subtotal 15000 total
    cart.apply_code("BOGO_BAGEL")  # one bagel free: -5000 → 10000
    cart.apply_code("SAVE20")      # 20% off: -2000 → 8000
    cart.apply_code("FLAT5")       # -500 → 7500
    cart.apply_code("FREESHIP")    # 7500 >= 5000 → shipping waived
    assert cart.total_cents() == 7500


# =========================================================================
# C6. Rounding (banker's / half-even)
# =========================================================================

def test_c6_save10_half_even_rounds_to_even_lower():
    """10% of 1005 = 100.5 → rounds to 100 (even). Total = 1005 - 100 = 905."""
    cart = Cart()
    cart.add_item("a", 1, 1005)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 905 + SHIPPING


def test_c6_save10_half_even_rounds_to_even_upper():
    """10% of 1015 = 101.5 → rounds to 102 (even). Total = 1015 - 102 = 913."""
    cart = Cart()
    cart.add_item("a", 1, 1015)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 913 + SHIPPING


def test_c6_save10_half_even_rounds_to_even_lower_2():
    """10% of 1025 = 102.5 → rounds to 102 (even)."""
    cart = Cart()
    cart.add_item("a", 1, 1025)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 923 + SHIPPING


def test_c6_save10_half_even_rounds_to_even_upper_2():
    """10% of 1035 = 103.5 → rounds to 104 (even)."""
    cart = Cart()
    cart.add_item("a", 1, 1035)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 931 + SHIPPING


@pytest.mark.parametrize(
    "subtotal,expected_post_discount",
    [
        (1005, 905),  # discount 100.5 → 100 (even)
        (1015, 913),  # discount 101.5 → 102 (even)
        (1025, 923),  # discount 102.5 → 102 (even)
        (1035, 931),  # discount 103.5 → 104 (even)
        (1045, 941),  # discount 104.5 → 104 (even)
        (1055, 949),  # discount 105.5 → 106 (even)
        (2005, 1805), # discount 200.5 → 200 (even)
        (2015, 1813), # discount 201.5 → 202 (even)
    ],
)
def test_c6_save10_half_even_rounding_table(subtotal, expected_post_discount):
    cart = Cart()
    cart.add_item("a", 1, subtotal)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == expected_post_discount + SHIPPING


def test_c6_save10_no_rounding_needed():
    """10% of 1000 is exactly 100 — no rounding involved."""
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 900 + SHIPPING


# =========================================================================
# C7. Empty cart
# =========================================================================

def test_c7_empty_cart_total_is_zero():
    assert Cart().total_cents() == 0


def test_c7_empty_cart_with_save10_is_zero():
    cart = Cart()
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_freeship_is_zero():
    cart = Cart()
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_all_codes_is_zero():
    cart = Cart()
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 0


# =========================================================================
# Cross-clause edge cases
# =========================================================================

def test_total_with_no_codes_includes_shipping():
    cart = Cart()
    cart.add_item("a", 1, 100)
    assert cart.total_cents() == 100 + SHIPPING


def test_total_cents_is_callable_multiple_times_idempotent():
    """Calling total_cents twice should give the same answer (no internal mutation)."""
    cart = Cart()
    cart.add_item("a", 2, 500)
    cart.apply_code("SAVE10")
    first = cart.total_cents()
    second = cart.total_cents()
    assert first == second


def test_can_add_item_after_apply_code():
    """Adding items after a code is applied should still work and affect the total."""
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("SAVE10")
    cart.add_item("b", 1, 1000)
    # Subtotal 2000, -10% = 1800, +500 shipping
    assert cart.total_cents() == 1800 + SHIPPING


def test_returns_integer_type():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("SAVE10")
    assert isinstance(cart.total_cents(), int)


def test_freeship_with_only_flat5_at_exact_threshold():
    """Subtotal = 5500, FLAT5 brings to 5000 exactly, FREESHIP waives at boundary."""
    cart = Cart()
    cart.add_item("a", 1, 5500)
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    # 5500 - 500 = 5000, >= 5000 → shipping waived
    assert cart.total_cents() == 5000


def test_freeship_just_below_threshold_after_flat5():
    cart = Cart()
    cart.add_item("a", 1, 5499)
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    # 5499 - 500 = 4999, < 5000 → shipping kept
    assert cart.total_cents() == 4999 + SHIPPING


def test_bogo_bagel_with_other_items():
    """BOGO only discounts the bagel line, leaves other lines alone."""
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.add_item("coffee", 1, 500)
    cart.apply_code("BOGO_BAGEL")
    # Subtotal 1100, BOGO -300 = 800, +500 shipping
    assert cart.total_cents() == 800 + SHIPPING


def test_zero_priced_item_with_freeship():
    """Free item alone — non-empty cart, but pre-shipping total = 0."""
    cart = Cart()
    cart.add_item("freebie", 1, 0)
    cart.apply_code("FREESHIP")
    # 0 < 5000 → shipping NOT waived
    assert cart.total_cents() == 0 + SHIPPING


def test_save20_rejected_returns_false_consistently():
    """After applying SAVE10, every subsequent SAVE10 OR SAVE20 returns False."""
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("SAVE10")
    assert cart.apply_code("SAVE10") is False
    assert cart.apply_code("SAVE20") is False
    assert cart.apply_code("SAVE10") is False


def test_unknown_codes_can_be_called_repeatedly():
    """Unknown codes always return False and never get 'remembered'."""
    cart = Cart()
    assert cart.apply_code("BOGUS") is False
    assert cart.apply_code("BOGUS") is False


def test_pdf_example_bogo_only():
    """The assignment PDF's BOGO example."""
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 300 + 500


def test_pdf_example_save10_plus_flat5():
    """The assignment PDF's SAVE10/FLAT5 example."""
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False
    assert cart.apply_code("FLAT5") is True
    # 10000 -> 9000 (SAVE10) -> 8500 (FLAT5) -> 9000 with shipping
    assert cart.total_cents() == 9000


def test_pdf_example_freeship_at_threshold():
    """Exactly $50.00 — FREESHIP waives shipping."""
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    assert cart.apply_code("FREESHIP") is True
    assert cart.total_cents() == 5000


def test_pdf_example_empty_cart():
    cart = Cart()
    assert cart.total_cents() == 0
