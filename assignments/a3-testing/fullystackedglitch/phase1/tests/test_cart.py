"""Tests for the cart module against its specification."""

import pytest

from cart import Cart


# C1: add_item validation

@pytest.mark.parametrize("bad_qty", [0, -1, -10])
def test_c1_non_positive_qty_value_error(bad_qty):
    """quantity must be a positive integer."""
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", bad_qty, 100)


def test_c1_negative_unit_price_value_error():
    """unit_price_cents must be zero or positive."""
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", 1, -1)


def test_c1_zero_unit_price_is_allowed():
    """unit_price_cents = 0 is non-negative, so it must be accepted."""
    cart = Cart()
    cart.add_item("freebie", 1, 0)
    # Subtotal is 0, cart is non-empty, so total is 0 + 500 shipping = 500.
    assert cart.total_cents() == 500


def test_c1_duplicate_sku_raises_value_error():
    """Adding a SKU already in the cart raises ValueError. one line item per SKU."""
    cart = Cart()
    cart.add_item("widget", 1, 500)
    with pytest.raises(ValueError):
        cart.add_item("widget", 2, 500)


def test_c1_qty_one_minimum_is_allowed():
    """qty = 1 is the minimum value."""
    cart = Cart()
    cart.add_item("widget", 1, 500)
    assert cart.total_cents() == 500 + 500


# C2: apply_code return values

def test_c2_unknown_code_returns_false():
    """An unrecognized code returns False from apply_code."""
    cart = Cart()
    assert cart.apply_code("NOTAREALCODE") is False


def test_c2_known_code_returns_true():
    """A valid known code returns True from apply_code."""
    cart = Cart()
    assert cart.apply_code("SAVE10") is True


def test_c2_re_applying_same_code_returns_false():
    """A code that has already been applied returns False on a second call."""
    cart = Cart()
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FLAT5") is False


def test_c2_codes_are_case_sensitive():
    """Code names are case-sensitive. 'save10' is unknown, 'SAVE10' is valid."""
    cart = Cart()
    assert cart.apply_code("save10") is False
    assert cart.apply_code("SAVE10") is True


@pytest.mark.parametrize("code", ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"])
def test_c2_each_known_code_accepted_on_a_fresh_cart(code):
    """Every documented code is recognized on a fresh cart."""
    cart = Cart()
    assert cart.apply_code(code) is True


# C3: Per-code behavior

def test_c3_save10_takes_ten_percent_off_total():
    """SAVE10 reduces the subtotal by 10% before shipping."""
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    # 10000 - 10% = 9000 + 500 shipping = 9500
    assert cart.total_cents() == 9500


def test_c3_save20_takes_twenty_percent_off_subtotal():
    """SAVE20 reduces the subtotal by 20% before shipping."""
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    # 10000 - 20% = 8000, + 500 shipping = 8500
    assert cart.total_cents() == 8500


def test_c3_flat5_subtracts_500_cents_from_pre_shipping_total():
    """FLAT5 subtracts 500 cents from the pre-shipping total."""
    cart = Cart()
    cart.add_item("shirt", 1, 2000)
    assert cart.apply_code("FLAT5") is True
    # 2000 - 500 = 1500, + 500 shipping = 2000
    assert cart.total_cents() == 2000


def test_c3_bogo_bagel_makes_half_the_bagels_free():
    """BOGO_BAGEL: (qty // 2) bagels are free on the bagel line item."""
    cart = Cart()
    cart.add_item("bagel", 4, 300)
    assert cart.apply_code("BOGO_BAGEL") is True
    # 4 // 2 = 2 free, 2 paid * 300 = 600, + 500 shipping = 1100
    assert cart.total_cents() == 1100


def test_c3_bogo_bagel_with_odd_qty_floor_divides():
    """An odd qty: (qty // 2) is floor division. 5 bagels => 2 free, 3 paid."""
    cart = Cart()
    cart.add_item("bagel", 5, 300)
    assert cart.apply_code("BOGO_BAGEL") is True
    # 5 // 2 = 2 free, 3 paid * 300 = 900, + 500 shipping = 1400
    assert cart.total_cents() == 1400


def test_c3_bogo_bagel_with_no_bagel_line_item_has_no_effect_but_is_applied():
    """BOGO_BAGEL with no bagel SKU: no discount, but the code still counts as applied."""
    cart = Cart()
    cart.add_item("shirt", 1, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    # No bagels, subtotal unchanged: 1000 + 500 shipping = 1500
    assert cart.total_cents() == 1500
    # C2: re-applying an already-applied code returns False, even if it had no effect.
    assert cart.apply_code("BOGO_BAGEL") is False


def test_c3_freeship_waives_shipping_at_exact_threshold():
    """FREESHIP at exactly 5000 cents pre-shipping: shipping is waived."""
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    assert cart.apply_code("FREESHIP") is True
    # subtotal 5000, FREESHIP waives shipping at the >= 5000 boundary
    assert cart.total_cents() == 5000


def test_c3_freeship_does_not_waive_shipping_below_threshold():
    """FREESHIP under 5000 cents pre-shipping: shipping is NOT waived."""
    cart = Cart()
    cart.add_item("widget", 1, 4999)
    assert cart.apply_code("FREESHIP") is True
    # subtotal 4999, code accepted but shipping still added: 4999 + 500 = 5499
    assert cart.total_cents() == 5499


# C4: Stacking rules 

def test_c4_save10_then_save20_rejects_save20():
    """SAVE10 first, then SAVE20: second one rejected; SAVE10 takes effect."""
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False
    # Only SAVE10: 10000 -10% = 9000, + 500 shipping = 9500
    assert cart.total_cents() == 9500


def test_c4_save20_then_save10_rejects_save10():
    """SAVE20 first, then SAVE10: second one rejected; SAVE20 takes effect."""
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("SAVE10") is False
    # Only SAVE20: 10000 -20% = 8000, + 500 shipping = 8500
    assert cart.total_cents() == 8500


def test_c4_flat5_stacks_with_save10():
    """FLAT5 stacks with SAVE10."""
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    # 10000 -10% = 9000, -500 = 8500, + 500 shipping = 9000
    assert cart.total_cents() == 9000


def test_c4_flat5_stacks_with_save20():
    """FLAT5 stacks with SAVE20."""
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("FLAT5") is True
    # 10000 -20% = 8000, -500 = 7500, + 500 shipping = 8000
    assert cart.total_cents() == 8000


def test_c4_bogo_stacks_with_save10():
    """BOGO_BAGEL applies before percent: SAVE10 sees the post-BOGO subtotal."""
    cart = Cart()
    cart.add_item("bagel", 4, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("SAVE10") is True
    # 4 // 2 = 2 free. Paid 2 * 1000 = 2000 post-BOGO.
    # SAVE10: 2000 -10% = 1800. + 500 shipping = 2300.
    assert cart.total_cents() == 2300


def test_c4_freeship_stacks_with_other_codes():
    """FREESHIP stacks with SAVE10, FLAT5, etc."""
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True
    # 10000 -10% = 9000, -500 = 8500. 8500 >= 5000, FREESHIP waives shipping.
    assert cart.total_cents() == 8500


#  C5: Application order 

def test_c5_bogo_applies_before_percent_discount():
    """C5 step 2 vs 3: BOGO reduces subtotal before percent is computed."""
    cart = Cart()
    cart.add_item("bagel", 2, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("SAVE20") is True
    # post-BOGO: 1 free, 1 paid * 1000 = 1000.
    # SAVE20: 1000 -20% = 800. + 500 shipping = 1300.
    # If percent applied first: 2000 -20% = 1600 then BOGO would give different result.
    assert cart.total_cents() == 1300


def test_c5_flat5_applies_after_percent_discount():
    """C5 step 3 vs 4: FLAT5 subtracts after percent is computed."""
    cart = Cart()
    cart.add_item("shirt", 1, 1000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    # 1000 -10% = 900; -500 = 400; +500 shipping = 900
    # If FLAT5 first: 1000-500=500; -10%=450; +500=950. Different.
    assert cart.total_cents() == 900


def test_c5_flat5_clamps_at_zero_when_pre_shipping_total_would_go_negative():
    """C5 step 4 clamp: FLAT5 cannot drive the pre-shipping total below zero."""
    cart = Cart()
    cart.add_item("widget", 1, 100)
    assert cart.apply_code("FLAT5") is True
    # 100 - 500 would be -400, clamp at 0; +500 shipping = 500
    assert cart.total_cents() == 500


def test_c5_freeship_threshold_uses_post_discount_pre_shipping_total():
    """FREESHIP threshold is checked on the pre-shipping total AFTER discounts (step 4)."""
    cart = Cart()
    cart.add_item("widget", 1, 5500)
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True
    # 5500 - 500 FLAT5 = 5000 pre-shipping. >= 5000, FREESHIP waives. Total = 5000.
    assert cart.total_cents() == 5000


def test_c5_freeship_does_not_apply_when_discount_drops_total_below_threshold():
    """If a discount drops pre-shipping below 5000, FREESHIP does not waive."""
    cart = Cart()
    cart.add_item("widget", 1, 5499)
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True
    # 5499 - 500 = 4999 pre-shipping. < 5000, shipping NOT waived. Total = 4999 + 500 = 5499.
    assert cart.total_cents() == 5499


#  C6: Half-even (banker's) rounding on percent discounts 
#
# Half-even rounding rounds .5 cases toward the nearest EVEN integer:
#   0.5 -> 0, 1.5 -> 2, 2.5 -> 2, 3.5 -> 4
# Half-up would give 1, 2, 3, 4 (catches 0.5 and 2.5 cases).
# Half-down would give 0, 1, 2, 3 (catches 1.5 and 3.5 cases).
# All four cases are needed to distinguish half-even from both alternatives.

def test_c6_half_cent_0_5_rounds_to_even_zero():
    """0.5 cent discount rounds half-even to 0 (zero is even)."""
    cart = Cart()
    cart.add_item("widget", 1, 5)
    assert cart.apply_code("SAVE10") is True
    # 5 * 0.10 = 0.5; banker's -> 0. 5 - 0 + 500 = 505.
    assert cart.total_cents() == 505


def test_c6_half_cent_1_5_rounds_to_even_two():
    """1.5 cent discount rounds half-even to 2."""
    cart = Cart()
    cart.add_item("widget", 1, 15)
    assert cart.apply_code("SAVE10") is True
    # 15 * 0.10 = 1.5; banker's -> 2. 15 - 2 + 500 = 513.
    assert cart.total_cents() == 513


def test_c6_half_cent_2_5_rounds_to_even_two():
    """2.5 cent discount rounds half-even to 2 (down to even); half-up would give 3."""
    cart = Cart()
    cart.add_item("widget", 1, 25)
    assert cart.apply_code("SAVE10") is True
    # 25 * 0.10 = 2.5; banker's -> 2. 25 - 2 + 500 = 523.
    assert cart.total_cents() == 523


def test_c6_half_cent_3_5_rounds_to_even_four():
    """3.5 cent discount rounds half-even to 4; half-down would give 3."""
    cart = Cart()
    cart.add_item("widget", 1, 35)
    assert cart.apply_code("SAVE10") is True
    # 35 * 0.10 = 3.5; banker's -> 4. 35 - 4 + 500 = 531.
    assert cart.total_cents() == 531


#  C7: Empty cart 

def test_c7_empty_cart_total_is_zero():
    """An empty cart has total 0; no shipping is added."""
    cart = Cart()
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_codes_applied_still_zero():
    """Even with codes applied, an empty cart returns 0."""
    cart = Cart()
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True
    assert cart.total_cents() == 0


# ---------- Implied / edge cases beyond explicit clauses (Claude) ----------

def test_subtotal_across_multiple_line_items():
    """Subtotal correctly sums across distinct line items."""
    cart = Cart()
    cart.add_item("a", 2, 100)   # 200
    cart.add_item("b", 3, 50)    # 150
    cart.add_item("c", 1, 1000)  # 1000
    # subtotal 1350, + 500 shipping = 1850
    assert cart.total_cents() == 1850


def test_bogo_does_not_discount_non_bagel_items():
    """BOGO_BAGEL only affects the bagel line; other items pay full price."""
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.add_item("shirt", 1, 5000)
    assert cart.apply_code("BOGO_BAGEL") is True
    # 1 free bagel: paid 1 * 300 = 300. Shirt full price 5000. Subtotal post-BOGO 5300.
    # + 500 shipping = 5800.
    assert cart.total_cents() == 5800


def test_bogo_qty_one_no_free_bagels():
    """qty=1 bagel: 1 // 2 = 0 free. Single bagel pays full."""
    cart = Cart()
    cart.add_item("bagel", 1, 300)
    assert cart.apply_code("BOGO_BAGEL") is True
    # 0 free, 1 paid = 300; + 500 shipping = 800
    assert cart.total_cents() == 800


def test_all_compatible_codes_stack_together():
    """SAVE10, FLAT5, BOGO_BAGEL, FREESHIP all stack on the same cart."""
    cart = Cart()
    cart.add_item("bagel", 4, 1000)   # 4000 raw subtotal on bagels
    cart.add_item("shirt", 1, 5000)   # +5000 = 9000 raw subtotal
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True
    # BOGO: 4 // 2 = 2 free bagels at 1000 = -2000 -> post-BOGO 7000
    # SAVE10: 7000 - 700 = 6300
    # FLAT5: 6300 - 500 = 5800 pre-shipping
    # FREESHIP: 5800 >= 5000 -> shipping waived. Total = 5800.
    assert cart.total_cents() == 5800
