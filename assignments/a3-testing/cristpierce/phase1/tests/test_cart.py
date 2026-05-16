"""Tests for the cart module, organized clause by clause against the spec.

Spec lives at starter/assignment3/specs/cart.md. Test names reference the
clause(s) being pinned down so the spec drives coverage.

Reminders worth keeping in mind while reading these tests:
  - Cart shipping is a flat 500 cents added when the cart is non-empty,
    waived only if FREESHIP is applied AND post-discount pre-shipping >= 5000.
  - Application order (C5): subtotal -> BOGO -> percent -> FLAT5 -> shipping.
  - Percent discounts use banker's rounding (ROUND_HALF_EVEN) on the discount
    amount itself.
"""
import pytest

from cart import Cart


# ---------------------------------------------------------------------------
# C1. add_item validation
# ---------------------------------------------------------------------------

def test_c1_add_item_qty_zero_raises():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("a", 0, 100)


def test_c1_add_item_qty_negative_raises():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("a", -1, 100)


def test_c1_add_item_unit_price_negative_raises():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("a", 1, -1)


def test_c1_add_item_unit_price_zero_is_ok():
    cart = Cart()
    cart.add_item("a", 1, 0)
    assert cart.total_cents() == 500  # only shipping


def test_c1_add_item_qty_one_is_valid():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.total_cents() == 1500  # 1000 + 500 shipping


def test_c1_duplicate_sku_raises():
    cart = Cart()
    cart.add_item("a", 1, 100)
    with pytest.raises(ValueError):
        cart.add_item("a", 1, 200)


def test_c1_duplicate_sku_does_not_overwrite_first():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    with pytest.raises(ValueError):
        cart.add_item("a", 5, 9999)
    # First entry untouched: 1000 + 500 shipping = 1500.
    assert cart.total_cents() == 1500


# ---------------------------------------------------------------------------
# C2. apply_code return value
# ---------------------------------------------------------------------------

def test_c2_apply_known_code_returns_true():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("SAVE10") is True


def test_c2_apply_unknown_code_returns_false():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("NOPE") is False


def test_c2_apply_empty_code_returns_false():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("") is False


def test_c2_apply_code_case_sensitive_lower():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("save10") is False


def test_c2_apply_code_case_sensitive_mixed():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("Save10") is False


def test_c2_duplicate_apply_returns_false():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE10") is False


def test_c2_duplicate_apply_does_not_double_discount():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("SAVE10")
    cart.apply_code("SAVE10")  # rejected
    # 1000 - 100 = 900, +500 shipping = 1400
    assert cart.total_cents() == 1400


def test_c2_unknown_code_has_no_effect():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("BOGUS")
    assert cart.total_cents() == 1500


# ---------------------------------------------------------------------------
# C3. Known codes — basic effects
# ---------------------------------------------------------------------------

def test_c3_save10_applies_ten_percent():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("SAVE10")
    # 1000 - 100 = 900, +500 shipping
    assert cart.total_cents() == 1400


def test_c3_save20_applies_twenty_percent():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("SAVE20")
    # 1000 - 200 = 800, +500 shipping
    assert cart.total_cents() == 1300


def test_c3_flat5_subtracts_500():
    cart = Cart()
    cart.add_item("a", 1, 2000)
    cart.apply_code("FLAT5")
    # 2000 - 500 = 1500, +500 shipping = 2000
    assert cart.total_cents() == 2000


def test_c3_flat5_after_percent_discount():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    # 10000 - 1000 = 9000, -500 = 8500, +500 shipping = 9000
    assert cart.total_cents() == 9000


def test_c3_bogo_bagel_qty_two_one_free():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    # 1 paid * 300 = 300, +500 shipping = 800
    assert cart.total_cents() == 800


def test_c3_bogo_bagel_qty_three_one_free():
    cart = Cart()
    cart.add_item("bagel", 3, 300)
    cart.apply_code("BOGO_BAGEL")
    # qty // 2 = 1 free; 2 paid * 300 = 600, +500 shipping
    assert cart.total_cents() == 1100


def test_c3_bogo_bagel_qty_four_two_free():
    cart = Cart()
    cart.add_item("bagel", 4, 300)
    cart.apply_code("BOGO_BAGEL")
    # 4 // 2 = 2 free; 2 paid * 300 = 600, +500 shipping
    assert cart.total_cents() == 1100


def test_c3_bogo_bagel_qty_one_zero_free():
    cart = Cart()
    cart.add_item("bagel", 1, 300)
    cart.apply_code("BOGO_BAGEL")
    # 1 // 2 = 0 free; full price 300 + 500 shipping
    assert cart.total_cents() == 800


def test_c3_bogo_bagel_no_bagel_line_item_no_effect_but_applied():
    cart = Cart()
    cart.add_item("muffin", 4, 300)
    assert cart.apply_code("BOGO_BAGEL") is True
    # No discount: 4 * 300 + 500 = 1700
    assert cart.total_cents() == 1700
    # Counts as applied: re-applying must return False.
    assert cart.apply_code("BOGO_BAGEL") is False


def test_c3_bogo_bagel_only_affects_bagel_line():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.add_item("muffin", 2, 400)
    cart.apply_code("BOGO_BAGEL")
    # bagel: 1 free -> 300; muffin untouched -> 800; +500 shipping = 1600
    assert cart.total_cents() == 1600


def test_c3_freeship_waives_shipping_at_threshold():
    cart = Cart()
    cart.add_item("a", 1, 5000)  # exactly $50.00
    cart.apply_code("FREESHIP")
    # >=5000 pre-shipping subtotal, shipping waived
    assert cart.total_cents() == 5000


def test_c3_freeship_does_not_waive_below_threshold():
    cart = Cart()
    cart.add_item("a", 1, 4999)  # just under
    cart.apply_code("FREESHIP")
    # shipping not waived
    assert cart.total_cents() == 4999 + 500


def test_c3_freeship_no_effect_below_threshold_but_applied():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("FREESHIP") is True
    # Already applied — second attempt must fail.
    assert cart.apply_code("FREESHIP") is False


# ---------------------------------------------------------------------------
# C4. Stacking rules
# ---------------------------------------------------------------------------

def test_c4_save10_then_save20_rejects_save20():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False
    # SAVE10 took effect: 10000 - 1000 + 500 = 9500
    assert cart.total_cents() == 9500


def test_c4_save20_then_save10_rejects_save10():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("SAVE10") is False
    # SAVE20 took effect: 10000 - 2000 + 500 = 8500
    assert cart.total_cents() == 8500


def test_c4_flat5_stacks_with_save10():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    # 10000 - 1000 - 500 + 500 = 9000
    assert cart.total_cents() == 9000


def test_c4_flat5_stacks_with_save20():
    cart = Cart()
    cart.add_item("a", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("FLAT5") is True
    # 10000 - 2000 - 500 + 500 = 8000
    assert cart.total_cents() == 8000


def test_c4_bogo_stacks_with_save10():
    cart = Cart()
    cart.add_item("bagel", 2, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("SAVE10") is True
    # subtotal 2000, -BOGO 1000 = 1000, -10% = 900, +500 = 1400
    assert cart.total_cents() == 1400


def test_c4_freeship_stacks_with_save10():
    cart = Cart()
    cart.add_item("a", 1, 6000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FREESHIP") is True
    # 6000 - 600 = 5400, >=5000 -> shipping waived
    assert cart.total_cents() == 5400


def test_c4_bogo_stacks_with_save20():
    cart = Cart()
    cart.add_item("bagel", 2, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("SAVE20") is True
    # subtotal 2000, BOGO -> 1000, SAVE20 -> 800, +500 ship = 1300
    assert cart.total_cents() == 1300


def test_c4_bogo_stacks_with_flat5():
    cart = Cart()
    cart.add_item("bagel", 2, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("FLAT5") is True
    # subtotal 2000, BOGO -> 1000, FLAT5 -> 500, +500 ship = 1000
    assert cart.total_cents() == 1000


def test_c4_bogo_stacks_with_freeship():
    # BOGO discount is part of the post-discount subtotal that FREESHIP
    # checks against the 5000 threshold.
    cart = Cart()
    cart.add_item("bagel", 2, 6000)  # subtotal 12000, BOGO -> 6000
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("FREESHIP") is True
    # 6000 >= 5000 so shipping waived
    assert cart.total_cents() == 6000


def test_c4_bogo_freeship_below_threshold_after_bogo_does_not_waive():
    # BOGO can pull the post-discount value below the FREESHIP threshold.
    cart = Cart()
    cart.add_item("bagel", 2, 4000)  # subtotal 8000, BOGO -> 4000
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("FREESHIP")
    # 4000 < 5000, FREESHIP must NOT waive
    assert cart.total_cents() == 4000 + 500


def test_c4_freeship_stacks_with_save20():
    cart = Cart()
    cart.add_item("a", 1, 7000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("FREESHIP") is True
    # 7000 - 1400 = 5600; >=5000 -> shipping waived
    assert cart.total_cents() == 5600


def test_c4_freeship_stacks_with_flat5():
    cart = Cart()
    cart.add_item("a", 1, 6000)
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True
    # 6000 - 500 = 5500; >=5000 -> shipping waived
    assert cart.total_cents() == 5500


def test_c4_all_stackable_codes_together():
    cart = Cart()
    cart.add_item("bagel", 2, 1000)
    cart.add_item("widget", 1, 9000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True
    # subtotal = 11000; BOGO -1000 = 10000; -10% = 9000; -500 = 8500;
    # pre-shipping >=5000 so FREESHIP waives shipping. Total 8500.
    assert cart.total_cents() == 8500


# ---------------------------------------------------------------------------
# C5. Application order
# ---------------------------------------------------------------------------

def test_c5_percent_applied_after_bogo():
    # If percent were applied to the pre-BOGO subtotal, the total would differ.
    cart = Cart()
    cart.add_item("bagel", 2, 1000)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    # subtotal 2000, BOGO -> 1000, SAVE10 -> 900, +shipping 500 = 1400.
    # If SAVE10 came before BOGO: 2000-200=1800, -1000 = 800 + 500 = 1300.
    assert cart.total_cents() == 1400


def test_c5_flat5_applied_after_percent():
    # Spec C3: FLAT5 is "applied AFTER any percent discount."
    cart = Cart()
    cart.add_item("a", 1, 10000)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    # subtotal 10000, -10% = 9000, -500 = 8500, +500 shipping = 9000
    assert cart.total_cents() == 9000


def test_c5_flat5_clamps_at_zero():
    # FLAT5 making pre-shipping total negative should clamp at 0.
    cart = Cart()
    cart.add_item("a", 1, 100)  # 100 cents
    cart.apply_code("FLAT5")
    # 100 - 500 -> clamp to 0; cart non-empty so +500 shipping = 500.
    assert cart.total_cents() == 500


def test_c5_flat5_clamps_then_freeship_threshold_not_met():
    # After clamping to 0, pre-shipping is 0, so FREESHIP can't waive shipping.
    cart = Cart()
    cart.add_item("a", 1, 100)
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    # pre-shipping 0; FREESHIP doesn't waive (0 < 5000); +500 shipping
    assert cart.total_cents() == 500


def test_c5_freeship_threshold_uses_post_discount_value():
    # 6000 - 20% = 4800, which is BELOW 5000, so FREESHIP must NOT waive.
    cart = Cart()
    cart.add_item("a", 1, 6000)
    cart.apply_code("SAVE20")
    cart.apply_code("FREESHIP")
    # 6000 - 1200 = 4800; 4800 < 5000; shipping NOT waived
    assert cart.total_cents() == 4800 + 500


def test_c5_freeship_exact_threshold_5000_waives():
    cart = Cart()
    cart.add_item("a", 1, 5000)
    cart.apply_code("FREESHIP")
    # exactly 5000, threshold inclusive, shipping waived
    assert cart.total_cents() == 5000


def test_c5_freeship_one_under_threshold_does_not_waive():
    cart = Cart()
    cart.add_item("a", 1, 4999)
    cart.apply_code("FREESHIP")
    # 4999 < 5000, shipping not waived
    assert cart.total_cents() == 4999 + 500


def test_c5_shipping_500_added_to_non_empty_cart_no_codes():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.total_cents() == 1500


def test_c5_shipping_added_to_small_non_empty_cart():
    cart = Cart()
    cart.add_item("a", 1, 100)
    assert cart.total_cents() == 600


def test_c5_freeship_threshold_uses_post_flat5_value():
    # subtotal 6000, FLAT5 -> 5500. >= 5000 so FREESHIP waives. Total 5500.
    cart = Cart()
    cart.add_item("a", 1, 6000)
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5500


def test_c5_freeship_post_flat5_just_under_threshold_does_not_waive():
    # subtotal 5499, FLAT5 -> 4999. <5000 so shipping NOT waived.
    cart = Cart()
    cart.add_item("a", 1, 5499)
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 4999 + 500


# ---------------------------------------------------------------------------
# C6. Banker's rounding (ROUND_HALF_EVEN) on percent discounts
# ---------------------------------------------------------------------------

def test_c6_save10_rounds_half_to_even_down():
    # 10% of 5 cents = 0.5 cents -> round half to even -> 0 (even).
    # Total: 5 - 0 + 500 shipping = 505.
    cart = Cart()
    cart.add_item("a", 1, 5)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 505


def test_c6_save10_rounds_half_to_even_up():
    # 10% of 15 cents = 1.5 cents -> round half to even -> 2 (even).
    # Total: 15 - 2 + 500 = 513.
    cart = Cart()
    cart.add_item("a", 1, 15)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 513


def test_c6_save10_rounds_half_to_even_quarter_down():
    # 10% of 25 cents = 2.5 cents -> round half to even -> 2 (even).
    # Total: 25 - 2 + 500 = 523.
    cart = Cart()
    cart.add_item("a", 1, 25)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 523


def test_c6_save10_rounds_half_to_even_thirty_five_up():
    # 10% of 35 = 3.5 -> round half to even -> 4 (even).
    # Total: 35 - 4 + 500 = 531.
    cart = Cart()
    cart.add_item("a", 1, 35)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 531


def test_c6_save20_rounds_half_to_even():
    # 20% of 25 = 5.0 -> exactly 5, no rounding ambiguity.
    cart = Cart()
    cart.add_item("a", 1, 25)
    cart.apply_code("SAVE20")
    assert cart.total_cents() == 25 - 5 + 500


def test_c6_no_rounding_when_clean_division():
    # 10% of 100 = exactly 10, no rounding required.
    cart = Cart()
    cart.add_item("a", 1, 100)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 100 - 10 + 500


# ---------------------------------------------------------------------------
# C7. Empty cart behavior
# ---------------------------------------------------------------------------

def test_c7_empty_cart_total_is_zero():
    assert Cart().total_cents() == 0


def test_c7_empty_cart_no_shipping_added():
    cart = Cart()
    # No add_item calls. Even with no codes, no shipping should be added.
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_freeship_still_zero():
    cart = Cart()
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_save10_still_zero():
    cart = Cart()
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_flat5_still_zero():
    # Even FLAT5 must not push total negative or add shipping.
    cart = Cart()
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_all_codes_still_zero():
    cart = Cart()
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 0


# ---------------------------------------------------------------------------
# Edge cases the spec implies but doesn't spell out
# ---------------------------------------------------------------------------

def test_edge_total_after_no_codes_simple_addition():
    cart = Cart()
    cart.add_item("a", 2, 250)
    cart.add_item("b", 1, 1000)
    # subtotal 500 + 1000 = 1500, +500 shipping = 2000
    assert cart.total_cents() == 2000


def test_edge_total_idempotent_when_called_twice():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("SAVE10")
    first = cart.total_cents()
    second = cart.total_cents()
    assert first == second


def test_edge_total_with_no_shipping_path_stays_consistent():
    cart = Cart()
    cart.add_item("a", 1, 5000)
    cart.apply_code("FREESHIP")
    first = cart.total_cents()
    second = cart.total_cents()
    assert first == 5000
    assert first == second


def test_edge_bogo_bagel_with_save10():
    # subtotal 2*500=1000, BOGO -500 = 500, SAVE10 -50 = 450, +500 ship = 950.
    cart = Cart()
    cart.add_item("bagel", 2, 500)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 950


def test_edge_bogo_bagel_with_save10_flat5():
    # 2*500=1000, BOGO -500 = 500, SAVE10 -50 = 450, FLAT5 -500 -> clamp 0,
    # +500 ship = 500.
    cart = Cart()
    cart.add_item("bagel", 2, 500)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 500


def test_edge_bogo_alone_keeps_full_shipping():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    # 300 + 500 shipping = 800
    assert cart.total_cents() == 800


def test_edge_freeship_alone_below_threshold_pays_shipping():
    cart = Cart()
    cart.add_item("a", 1, 100)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 600


def test_edge_save10_twice_second_returns_false():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE10") is False


def test_edge_unknown_code_does_not_block_known_code():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("NOPE")
    assert cart.apply_code("SAVE10") is True
    # 1000 - 100 + 500 = 1400
    assert cart.total_cents() == 1400


def test_edge_apply_code_before_adding_items_still_works_when_items_added():
    cart = Cart()
    assert cart.apply_code("SAVE10") is True
    cart.add_item("a", 1, 1000)
    # Code applied earlier still applies: 1000 - 100 + 500 = 1400
    assert cart.total_cents() == 1400


def test_edge_apply_bogo_before_adding_bagel_then_apply_at_total():
    # BOGO_BAGEL applied while no bagel exists must still work once a
    # bagel is added afterward.
    cart = Cart()
    assert cart.apply_code("BOGO_BAGEL") is True
    cart.add_item("bagel", 2, 300)
    # 1 free; 300 + 500 shipping = 800
    assert cart.total_cents() == 800


def test_edge_apply_freeship_before_adding_items():
    cart = Cart()
    assert cart.apply_code("FREESHIP") is True
    cart.add_item("a", 1, 5000)
    # threshold met after items added; shipping waived
    assert cart.total_cents() == 5000


def test_edge_add_item_then_code_then_add_more():
    # Subtotal must be computed at total_cents time, not at code-apply time.
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.apply_code("SAVE10")
    cart.add_item("b", 1, 1000)
    # subtotal at total time = 2000; -10% = 1800; +500 = 2300
    assert cart.total_cents() == 2300


def test_edge_freeship_threshold_recomputed_when_items_added_after_apply():
    # FREESHIP applied early; threshold check uses the final subtotal.
    cart = Cart()
    cart.apply_code("FREESHIP")
    cart.add_item("a", 1, 5000)
    # post-discount pre-shipping = 5000, threshold met, shipping waived
    assert cart.total_cents() == 5000


def test_edge_bogo_freeship_combined_with_save10():
    # Three-way stack: BOGO + SAVE10 + FREESHIP. Tests that FREESHIP's
    # threshold is evaluated against the value after BOGO and SAVE10
    # both apply.
    cart = Cart()
    cart.add_item("bagel", 2, 6000)  # subtotal 12000
    cart.apply_code("BOGO_BAGEL")  # -> 6000
    cart.apply_code("SAVE10")  # -> 5400
    cart.apply_code("FREESHIP")
    # 5400 >= 5000 so shipping waived. Total 5400.
    assert cart.total_cents() == 5400


def test_edge_flat5_clamps_with_percent_already_applied():
    cart = Cart()
    cart.add_item("a", 1, 400)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    # 400 - 40 = 360, -500 -> clamp 0, +500 shipping = 500
    assert cart.total_cents() == 500


def test_edge_bogo_with_zero_priced_bagels():
    cart = Cart()
    cart.add_item("bagel", 4, 0)
    cart.apply_code("BOGO_BAGEL")
    # subtotal 0, BOGO discount 0, +500 shipping
    assert cart.total_cents() == 500


@pytest.mark.parametrize(
    "qty,unit,expected_paid",
    [
        (1, 100, 100),  # 0 free
        (2, 100, 100),  # 1 free
        (3, 100, 200),  # 1 free
        (4, 100, 200),  # 2 free
        (5, 100, 300),  # 2 free
        (6, 100, 300),  # 3 free
        (10, 100, 500),  # 5 free
    ],
)
def test_edge_bogo_parametrized_qty_div_2_free(qty, unit, expected_paid):
    cart = Cart()
    cart.add_item("bagel", qty, unit)
    cart.apply_code("BOGO_BAGEL")
    # paid amount + 500 shipping
    assert cart.total_cents() == expected_paid + 500


@pytest.mark.parametrize(
    "code,expected",
    [
        ("save10", False),
        ("SAVE10 ", False),
        (" SAVE10", False),
        ("SAVE_10", False),
        ("SAVE100", False),
        ("flat5", False),
        ("FLAT_5", False),
        ("bogo_bagel", False),
        ("freeship", False),
    ],
)
def test_edge_unknown_or_misspelled_codes_rejected(code, expected):
    cart = Cart()
    cart.add_item("a", 1, 1000)
    assert cart.apply_code(code) is expected


@pytest.mark.parametrize(
    "code",
    ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"],
)
def test_edge_each_known_code_accepted_first_time(code):
    cart = Cart()
    cart.add_item("a", 1, 10000)
    assert cart.apply_code(code) is True


@pytest.mark.parametrize(
    "code",
    ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"],
)
def test_edge_each_known_code_rejected_second_time(code):
    cart = Cart()
    cart.add_item("a", 1, 10000)
    assert cart.apply_code(code) is True
    assert cart.apply_code(code) is False
