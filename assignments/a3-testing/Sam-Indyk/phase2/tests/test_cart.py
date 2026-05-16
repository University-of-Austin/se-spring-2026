"""Tests for cart, organized clause-by-clause against the spec."""
import pytest

from cart import Cart


# =========================================================================
# C1: add_item validation
# =========================================================================

def test_c1_qty_zero_raises():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("a", 0, 100)


def test_c1_qty_negative_raises():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("a", -1, 100)


def test_c1_negative_price_raises():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("a", 1, -1)


def test_c1_zero_price_allowed():
    # unit_price_cents must be non-negative — zero is allowed.
    cart = Cart()
    cart.add_item("freebie", 1, 0)
    assert cart.total_cents() == 500  # 0 + shipping


def test_c1_duplicate_sku_raises():
    cart = Cart()
    cart.add_item("a", 1, 100)
    with pytest.raises(ValueError):
        cart.add_item("a", 2, 200)


def test_c1_qty_one_allowed():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.total_cents() == 1000 + 500


# =========================================================================
# C2: apply_code return value
# =========================================================================

def test_c2_unknown_code_returns_false():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("NOT_A_CODE") is False


def test_c2_known_code_returns_true():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("SAVE10") is True


def test_c2_duplicate_application_returns_false():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FLAT5") is False


def test_c2_case_sensitive_lower():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("save10") is False


def test_c2_case_sensitive_mixed():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("Save10") is False


def test_c2_empty_string_unknown():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("") is False


@pytest.mark.parametrize(
    "code", ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"]
)
def test_c2_each_known_code_returns_true(code):
    cart = Cart()
    cart.add_item("bagel", 1, 1000)
    assert cart.apply_code(code) is True


@pytest.mark.parametrize(
    "code", ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"]
)
def test_c2_each_known_code_duplicate_returns_false(code):
    cart = Cart()
    cart.add_item("bagel", 1, 1000)
    cart.apply_code(code)
    assert cart.apply_code(code) is False


# =========================================================================
# C3: Each code's effect
# =========================================================================

def test_c3_save10_effect():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    cart.apply_code("SAVE10")
    # 10000 - 10% = 9000, + 500 shipping = 9500
    assert cart.total_cents() == 9500


def test_c3_save20_effect():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    cart.apply_code("SAVE20")
    # 10000 - 20% = 8000, + 500 shipping = 8500
    assert cart.total_cents() == 8500


def test_c3_flat5_effect():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("FLAT5")
    # 1000 - 500 = 500, + 500 shipping = 1000
    assert cart.total_cents() == 1000


def test_c3_bogo_bagel_effect():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    # 600 subtotal - 1 free (300) = 300 + 500 ship = 800
    assert cart.total_cents() == 800


def test_c3_bogo_bagel_qty_3_one_free():
    cart = Cart()
    cart.add_item("bagel", 3, 300)
    cart.apply_code("BOGO_BAGEL")
    # 3 // 2 = 1 free. Subtotal 900 - 300 = 600 + 500 ship = 1100
    assert cart.total_cents() == 1100


def test_c3_bogo_bagel_qty_4_two_free():
    cart = Cart()
    cart.add_item("bagel", 4, 300)
    cart.apply_code("BOGO_BAGEL")
    # 4 // 2 = 2 free. Subtotal 1200 - 600 = 600 + 500 ship = 1100
    assert cart.total_cents() == 1100


def test_c3_bogo_bagel_qty_5_two_free():
    cart = Cart()
    cart.add_item("bagel", 5, 300)
    cart.apply_code("BOGO_BAGEL")
    # 5 // 2 = 2 free. Subtotal 1500 - 600 = 900 + 500 ship = 1400
    assert cart.total_cents() == 1400


def test_c3_bogo_bagel_qty_1_zero_free():
    cart = Cart()
    cart.add_item("bagel", 1, 300)
    cart.apply_code("BOGO_BAGEL")
    # 1 // 2 = 0 free. Subtotal 300 + 500 ship = 800
    assert cart.total_cents() == 800


def test_c3_bogo_bagel_no_bagel_line_item_no_effect():
    # Spec: "If no bagel line item exists when total_cents is computed,
    # the code has no effect but is still considered 'applied'."
    cart = Cart()
    cart.add_item("muffin", 5, 200)
    cart.apply_code("BOGO_BAGEL")
    # No bagel → no discount. Subtotal 1000 + 500 ship = 1500
    assert cart.total_cents() == 1500


def test_c3_bogo_bagel_no_bagel_still_applied_for_dup_rule():
    # Even with no bagel line, BOGO_BAGEL counts as "applied" so a second
    # call returns False (per C2 + C3).
    cart = Cart()
    cart.add_item("muffin", 5, 200)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("BOGO_BAGEL") is False


def test_c3_freeship_waives_shipping_at_threshold():
    # widget at exactly 5000 cents — pre-shipping subtotal == 5000.
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    cart.apply_code("FREESHIP")
    # Threshold met (>= 5000). Shipping waived.
    assert cart.total_cents() == 5000


def test_c3_freeship_does_not_waive_below_threshold():
    cart = Cart()
    cart.add_item("widget", 1, 4999)
    cart.apply_code("FREESHIP")
    # Pre-shipping subtotal 4999 < 5000. Shipping NOT waived.
    assert cart.total_cents() == 4999 + 500


def test_c3_freeship_above_threshold_waives():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 10000


def test_c3_freeship_no_code_no_effect_on_threshold():
    # Without FREESHIP applied, shipping is added regardless of subtotal.
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.total_cents() == 10500


# =========================================================================
# C4: Stacking rules
# =========================================================================

def test_c4_save10_then_save20_returns_false():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False


def test_c4_save20_then_save10_returns_false():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("SAVE10") is False


def test_c4_only_first_percent_takes_effect():
    # Apply SAVE10 first, then SAVE20 (rejected). Total reflects SAVE10 only.
    cart = Cart()
    cart.add_item("a", 1, 10000)
    cart.apply_code("SAVE10")
    cart.apply_code("SAVE20")  # rejected
    # 10000 - 10% = 9000 + 500 ship = 9500 (NOT 8500)
    assert cart.total_cents() == 9500


def test_c4_flat5_stacks_with_save10():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    # 10000 - 10% = 9000 - 500 = 8500 + 500 ship = 9000
    assert cart.total_cents() == 9000


def test_c4_flat5_stacks_with_save20():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("FLAT5") is True
    # 10000 - 20% = 8000 - 500 = 7500 + 500 ship = 8000
    assert cart.total_cents() == 8000


def test_c4_bogo_stacks_with_percent():
    cart = Cart()
    cart.add_item("bagel", 2, 1000)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    # subtotal 2000, BOGO -1000 = 1000, SAVE10 = 1000 - 100 = 900, + 500 = 1400
    assert cart.total_cents() == 1400


def test_c4_bogo_stacks_with_flat5():
    cart = Cart()
    cart.add_item("bagel", 2, 1000)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("FLAT5")
    # subtotal 2000, BOGO -1000 = 1000, FLAT5 -500 = 500, + 500 = 1000
    assert cart.total_cents() == 1000


def test_c4_freeship_stacks_with_percent():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    cart.apply_code("SAVE10")
    cart.apply_code("FREESHIP")
    # 10000 - 10% = 9000, FREESHIP triggers (9000 >= 5000), no shipping = 9000
    assert cart.total_cents() == 9000


def test_c4_freeship_stacks_with_flat5():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    # 10000 - 500 = 9500, FREESHIP (9500 >= 5000), no ship = 9500
    assert cart.total_cents() == 9500


def test_c4_freeship_stacks_with_bogo():
    cart = Cart()
    cart.add_item("bagel", 12, 1000)  # 12000 subtotal
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("FREESHIP")
    # 12 // 2 = 6 free. 12000 - 6000 = 6000. >= 5000, FREESHIP triggers.
    assert cart.total_cents() == 6000


def test_c4_all_stacking_codes_together():
    cart = Cart()
    cart.add_item("bagel", 2, 5000)  # subtotal 10000
    cart.apply_code("BOGO_BAGEL")  # -5000 = 5000
    cart.apply_code("SAVE10")      # -500 = 4500
    cart.apply_code("FLAT5")       # -500 = 4000
    cart.apply_code("FREESHIP")    # 4000 < 5000 → does NOT waive
    # + 500 ship = 4500
    assert cart.total_cents() == 4500


# =========================================================================
# C5: Application order
# =========================================================================

def test_c5_percent_applied_to_post_bogo_subtotal():
    # If percent applied to pre-BOGO subtotal, result would differ.
    cart = Cart()
    cart.add_item("bagel", 2, 1000)  # subtotal 2000
    cart.apply_code("BOGO_BAGEL")    # -1000 = 1000 (post-BOGO)
    cart.apply_code("SAVE10")        # 10% of 1000 = 100 → 900
    # If wrongly applied to 2000: 200 off → 800. Spec says: 900.
    # + 500 ship = 1400
    assert cart.total_cents() == 1400


def test_c5_flat5_applied_after_percent():
    # If FLAT5 applied first then percent, result differs.
    cart = Cart()
    cart.add_item("a", 1, 10000)
    cart.apply_code("SAVE10")        # 10000 - 1000 = 9000
    cart.apply_code("FLAT5")         # 9000 - 500 = 8500
    # If wrongly: 10000 - 500 = 9500, then 10% off = 8550. Spec: 8500.
    # + 500 ship = 9000
    assert cart.total_cents() == 9000


def test_c5_flat5_clamps_at_zero():
    # FLAT5 (500) on a tiny cart should clamp pre-shipping to 0, not go negative.
    cart = Cart()
    cart.add_item("cheap", 1, 100)
    cart.apply_code("FLAT5")
    # 100 - 500 → clamped at 0. + 500 ship = 500.
    assert cart.total_cents() == 500


def test_c5_flat5_clamp_then_shipping_added():
    # Clamping at 0 from FLAT5 doesn't remove the shipping line.
    cart = Cart()
    cart.add_item("cheap", 1, 1)
    cart.apply_code("FLAT5")
    # 1 - 500 → 0. + 500 ship = 500.
    assert cart.total_cents() == 500


def test_c5_freeship_threshold_uses_post_discount_subtotal():
    # Subtotal exactly at 5000 with FLAT5 → post-discount 4500 → below threshold.
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    cart.apply_code("FLAT5")     # 5000 - 500 = 4500
    cart.apply_code("FREESHIP")  # 4500 < 5000 → shipping NOT waived
    # 4500 + 500 ship = 5000
    assert cart.total_cents() == 5000


def test_c5_freeship_threshold_uses_post_percent_subtotal():
    # Subtotal 5500 - 10% = 4950 < 5000 → FREESHIP doesn't trigger.
    cart = Cart()
    cart.add_item("widget", 1, 5500)
    cart.apply_code("SAVE10")    # 5500 - 550 = 4950
    cart.apply_code("FREESHIP")  # 4950 < 5000 → shipping NOT waived
    # 4950 + 500 ship = 5450
    assert cart.total_cents() == 5450


def test_c5_freeship_post_bogo_below_threshold():
    # BOGO brings post-discount below threshold.
    cart = Cart()
    cart.add_item("bagel", 2, 5000)  # subtotal 10000
    cart.apply_code("BOGO_BAGEL")    # -5000 = 5000
    cart.apply_code("SAVE10")        # -500 = 4500
    cart.apply_code("FREESHIP")      # 4500 < 5000 → shipping NOT waived
    # 4500 + 500 = 5000
    assert cart.total_cents() == 5000


def test_c5_freeship_post_bogo_at_threshold():
    cart = Cart()
    cart.add_item("bagel", 2, 5000)  # subtotal 10000
    cart.apply_code("BOGO_BAGEL")    # -5000 = 5000
    cart.apply_code("FREESHIP")      # 5000 >= 5000 → ship WAIVED
    assert cart.total_cents() == 5000


# =========================================================================
# C6: Banker's (half-even) rounding for percent discounts
# =========================================================================

def test_c6_no_rounding_needed_when_exact():
    # 10% of 10000 = 1000 exactly.
    cart = Cart()
    cart.add_item("a", 1, 10000)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 9000 + 500


def test_c6_half_cent_rounds_to_even_up():
    # Subtotal 1255: 10% = 125.5 cents. Banker's round → 126 (6 is even).
    # Post-discount = 1255 - 126 = 1129. + 500 ship = 1629.
    cart = Cart()
    cart.add_item("a", 1, 1255)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 1629


def test_c6_half_cent_rounds_to_even_down():
    # Subtotal 1245: 10% = 124.5 cents. Banker's round → 124 (4 is even).
    # Post-discount = 1245 - 124 = 1121. + 500 ship = 1621.
    cart = Cart()
    cart.add_item("a", 1, 1245)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 1621


def test_c6_half_even_distinguishes_from_half_up():
    # If implementation uses half-up instead of half-even, 124.5 rounds to 125.
    # Banker's says 124. Total would differ: 1120 + 500 = 1620 (half-up)
    # vs 1121 + 500 = 1621 (banker's).
    cart = Cart()
    cart.add_item("a", 1, 1245)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 1621  # banker's, not half-up


def test_c6_save20_rounding_at_half_cent():
    # Subtotal 1235: 20% = 247.0 (exact). Post = 988. + 500 = 1488.
    # Use a half-cent case: subtotal 1252 → 20% = 250.4 → 250 (round down, not at half)
    # Try subtotal 1235: 20% = 247.0 exact.
    # For half-even at 0.5: subtotal 1255 → 20% = 251.0 (exact, no rounding).
    # Actually 20% needs subtotal s.t. 2*s/10 has fractional .5: never with int s.
    # So pick a non-half case to verify SAVE20 rounding doesn't go wrong.
    cart = Cart()
    cart.add_item("a", 1, 1234)  # 20% = 246.8 → 247 (banker's)
    cart.apply_code("SAVE20")
    # 1234 - 247 = 987. + 500 = 1487.
    assert cart.total_cents() == 1487


# =========================================================================
# C7: Empty cart
# =========================================================================

def test_c7_empty_cart_total_zero():
    cart = Cart()
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_save10_total_zero():
    cart = Cart()
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_flat5_does_not_go_negative():
    cart = Cart()
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_freeship_total_zero():
    cart = Cart()
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 0


def test_c7_empty_cart_no_shipping_added():
    # Spec C5.6 + C7: empty cart never has shipping added.
    cart = Cart()
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_all_codes_total_zero():
    cart = Cart()
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 0


# =========================================================================
# Cross-clause / integration / edge cases
# =========================================================================

def test_multi_item_subtotal():
    cart = Cart()
    cart.add_item("a", 2, 100)  # 200
    cart.add_item("b", 1, 300)  # 300
    cart.add_item("c", 3, 50)   # 150
    # subtotal 650 + 500 ship = 1150
    assert cart.total_cents() == 1150


def test_bagel_alongside_other_items_only_bagel_gets_bogo():
    cart = Cart()
    cart.add_item("bagel", 2, 300)  # 600
    cart.add_item("muffin", 2, 400)  # 800
    cart.apply_code("BOGO_BAGEL")
    # bagel BOGO: -300. Other items unaffected.
    # subtotal post-BOGO: 600 - 300 + 800 = 1100. + 500 ship = 1600.
    assert cart.total_cents() == 1600


def test_apply_code_before_adding_items_then_compute():
    # Codes can be applied before items; total computed lazily.
    cart = Cart()
    cart.apply_code("SAVE10")
    cart.add_item("a", 1, 10000)
    assert cart.total_cents() == 9000 + 500


def test_total_cents_is_idempotent():
    # Calling total_cents multiple times returns the same value (no
    # silent state change like applying discount twice).
    cart = Cart()
    cart.add_item("a", 1, 10000)
    cart.apply_code("SAVE10")
    first = cart.total_cents()
    second = cart.total_cents()
    third = cart.total_cents()
    assert first == second == third == 9500


def test_adding_after_total_still_works():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.total_cents()
    cart.add_item("b", 1, 2000)
    assert cart.total_cents() == 3000 + 500


def test_freeship_threshold_inclusive_at_5000():
    # Spec: shipping waived when pre-shipping total >= 5000.
    # Test the boundary explicitly.
    cart = Cart()
    cart.add_item("a", 1, 5000)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5000  # waived at exactly 5000


def test_bogo_bagel_qty_2_one_paid_unit():
    # Common business case: buy 2, get 1 free → only 1 unit paid.
    cart = Cart()
    cart.add_item("bagel", 2, 500)  # 1000
    cart.apply_code("BOGO_BAGEL")
    # 1000 - 500 = 500. + 500 ship = 1000
    assert cart.total_cents() == 1000


def test_complex_full_stack():
    cart = Cart()
    cart.add_item("bagel", 4, 250)   # 1000
    cart.add_item("widget", 1, 9000)  # 9000
    # subtotal = 10000
    cart.apply_code("BOGO_BAGEL")    # 4//2 = 2 free; -500. Now 9500.
    cart.apply_code("SAVE10")        # 9500 - 950 = 8550
    cart.apply_code("FLAT5")         # 8550 - 500 = 8050
    cart.apply_code("FREESHIP")      # 8050 >= 5000 → ship waived
    assert cart.total_cents() == 8050
