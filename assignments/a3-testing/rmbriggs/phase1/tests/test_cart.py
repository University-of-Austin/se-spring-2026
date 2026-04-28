"""Tests for cart.Cart, organized by spec clause.

Money is in integer cents throughout. Shipping is 500 cents. FREESHIP
threshold is 5000 cents on the post-discount pre-shipping subtotal.
"""
import pytest

from cart import Cart


# ---------- C1: add_item ----------

def test_c1_add_item_qty_zero_raises():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", 0, 100)


def test_c1_add_item_qty_negative_raises():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", -1, 100)


def test_c1_add_item_unit_price_negative_raises():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", 1, -50)


def test_c1_add_item_unit_price_zero_works():
    """Spec says non-negative; zero is allowed."""
    cart = Cart()
    cart.add_item("freebie", 1, 0)
    assert cart.total_cents() == 500  # just shipping


def test_c1_duplicate_sku_raises():
    cart = Cart()
    cart.add_item("widget", 1, 100)
    with pytest.raises(ValueError):
        cart.add_item("widget", 1, 200)


def test_c1_qty_one_minimum_works():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.total_cents() == 1500


# ---------- C2: apply_code basics ----------

def test_c2_apply_unknown_returns_false():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("BOGUS") is False


def test_c2_apply_lowercase_save10_is_unknown():
    """Spec: code names are case-sensitive."""
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("save10") is False


def test_c2_apply_lowercase_then_uppercase_works():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("save10") is False
    assert cart.apply_code("SAVE10") is True


def test_c2_apply_known_code_returns_true():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("FLAT5") is True


def test_c2_double_apply_returns_false_second_time():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FLAT5") is False


# ---------- C3: known codes -- basic effects ----------

def test_c3_save10_takes_10_pct_off():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("SAVE10")
    # 10000 - 10% (1000) = 9000 + 500 shipping = 9500
    assert cart.total_cents() == 9500


def test_c3_save20_takes_20_pct_off():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("SAVE20")
    # 10000 - 20% (2000) = 8000 + 500 = 8500
    assert cart.total_cents() == 8500


def test_c3_flat5_subtracts_500_cents():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("FLAT5")
    # 10000 - 500 = 9500 + 500 shipping = 10000
    assert cart.total_cents() == 10000


def test_c3_bogo_bagel_qty_2_one_free():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    # 600 - 300 (1 free) = 300 + 500 = 800
    assert cart.total_cents() == 800


def test_c3_bogo_bagel_qty_3_one_free():
    """3 // 2 = 1 free."""
    cart = Cart()
    cart.add_item("bagel", 3, 300)
    cart.apply_code("BOGO_BAGEL")
    # 900 - 300 = 600 + 500 = 1100
    assert cart.total_cents() == 1100


def test_c3_bogo_bagel_qty_4_two_free():
    cart = Cart()
    cart.add_item("bagel", 4, 300)
    cart.apply_code("BOGO_BAGEL")
    # 1200 - 600 = 600 + 500 = 1100
    assert cart.total_cents() == 1100


def test_c3_bogo_bagel_qty_1_no_free():
    """1 // 2 = 0; no discount."""
    cart = Cart()
    cart.add_item("bagel", 1, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 300 + 500


def test_c3_bogo_bagel_no_bagel_still_applied():
    """Spec: applies vacuously, but is still considered 'applied' for C2."""
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("BOGO_BAGEL") is False
    assert cart.total_cents() == 1500


def test_c3_bogo_bagel_does_not_discount_other_skus():
    cart = Cart()
    cart.add_item("widget", 4, 300)
    cart.apply_code("BOGO_BAGEL")
    # No bagel; widget pays full price
    assert cart.total_cents() == 1200 + 500


def test_c3_freeship_at_threshold_waives():
    """Boundary: pre-shipping == 5000 means FREESHIP applies (>= comparison)."""
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5000


def test_c3_freeship_just_below_threshold_does_not_waive():
    cart = Cart()
    cart.add_item("widget", 1, 4999)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 4999 + 500


def test_c3_freeship_well_below_threshold_does_not_waive():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 1000 + 500


def test_c3_freeship_compares_post_discount_total():
    """Threshold is post-discount pre-shipping subtotal, not the raw subtotal."""
    cart = Cart()
    cart.add_item("widget", 1, 5500)
    cart.apply_code("SAVE10")  # 5500 -> 4950 (below 5000)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 4950 + 500


# ---------- C4: stacking rules ----------

def test_c4_save10_then_save20_second_rejected():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False
    assert cart.total_cents() == 9500  # SAVE10 took effect


def test_c4_save20_then_save10_second_rejected():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("SAVE10") is False
    assert cart.total_cents() == 8500  # SAVE20 took effect


def test_c4_flat5_stacks_with_save10():
    """Spec example: 10000 -> 9000 (SAVE10) -> 8500 (FLAT5) + 500 = 9000."""
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False
    assert cart.apply_code("FLAT5") is True
    assert cart.total_cents() == 9000


def test_c4_flat5_stacks_with_save20():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    cart.apply_code("SAVE20")
    cart.apply_code("FLAT5")
    # 10000 -> 8000 (SAVE20) -> 7500 (FLAT5) + 500 shipping = 8000
    assert cart.total_cents() == 8000


def test_c4_bogo_stacks_with_percent():
    cart = Cart()
    cart.add_item("bagel", 4, 500)  # subtotal 2000
    cart.apply_code("BOGO_BAGEL")  # -> 1000
    cart.apply_code("SAVE10")      # -> 900
    # 900 + 500 shipping = 1400
    assert cart.total_cents() == 1400


def test_c4_bogo_stacks_with_flat5():
    cart = Cart()
    cart.add_item("bagel", 4, 500)
    cart.apply_code("BOGO_BAGEL")  # 2000 -> 1000
    cart.apply_code("FLAT5")       # -> 500
    assert cart.total_cents() == 500 + 500


def test_c4_freeship_stacks_with_percent():
    cart = Cart()
    cart.add_item("widget", 1, 6000)
    cart.apply_code("SAVE10")     # 6000 -> 5400 (>= 5000)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5400


# ---------- C5: application order ----------

def test_c5_full_order_bogo_then_percent_then_flat5():
    """4 bagels @ $5: BOGO -> 1000, SAVE10 -> 900, FLAT5 -> 400, +shipping = 900."""
    cart = Cart()
    cart.add_item("bagel", 4, 500)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 400 + 500


def test_c5_flat5_clamps_at_zero():
    """Pre-shipping cannot go negative from FLAT5."""
    cart = Cart()
    cart.add_item("widget", 1, 100)
    cart.apply_code("FLAT5")
    # 100 - 500 = -400 -> clamp 0; + 500 shipping = 500
    assert cart.total_cents() == 500


def test_c5_flat5_clamp_then_freeship_threshold_check():
    """If FLAT5 clamps subtotal to 0, FREESHIP still uses 0 as the threshold check."""
    cart = Cart()
    cart.add_item("widget", 1, 100)
    cart.apply_code("FLAT5")     # 100 -> -400 -> clamp 0
    cart.apply_code("FREESHIP")  # 0 < 5000, no waive
    assert cart.total_cents() == 0 + 500


def test_c5_shipping_added_on_non_empty_cart():
    cart = Cart()
    cart.add_item("widget", 1, 100)
    assert cart.total_cents() == 100 + 500


def test_c5_bogo_applied_before_percent():
    """Order sensitivity: BOGO first vs percent first changes the result.

    4 bagels @ 500 = 2000.
      BOGO-then-percent: 2000 -> 1000 (BOGO) -> 900 (SAVE10).
      Percent-then-BOGO: 2000 -> 1800 (SAVE10) -> 800 (BOGO if it stayed at 1000 off).
    Spec says BOGO first, so we expect 900 + shipping.
    """
    cart = Cart()
    cart.add_item("bagel", 4, 500)
    cart.apply_code("SAVE10")     # apply order of calls is irrelevant per spec
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 900 + 500


# ---------- C6: rounding (banker's / HALF_EVEN) ----------

@pytest.mark.parametrize(
    "subtotal,expected_total",
    [
        # SAVE10 ties at 0.5 occur when subtotal % 10 == 5.
        # HALF_EVEN rounds 0.5 toward the nearest even integer.
        # 100.5 -> 100 (even); discount 100; 1005 - 100 + 500 shipping = 1405
        (1005, 1005 - 100 + 500),
        # 101.5 -> 102 (even); 1015 - 102 + 500 = 1413
        (1015, 1015 - 102 + 500),
        # 102.5 -> 102 (even); 1025 - 102 + 500 = 1423
        (1025, 1025 - 102 + 500),
        # 103.5 -> 104 (even); 1035 - 104 + 500 = 1431
        (1035, 1035 - 104 + 500),
    ],
)
def test_c6_save10_rounds_half_even(subtotal, expected_total):
    cart = Cart()
    cart.add_item("widget", 1, subtotal)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == expected_total


def test_c6_save10_no_rounding_when_clean_division():
    """10% of 1000 is exactly 100; no rounding involved."""
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 1000 - 100 + 500


# ---------- C7: empty cart ----------

def test_c7_empty_cart_total_is_zero():
    assert Cart().total_cents() == 0


def test_c7_empty_cart_no_shipping_charge():
    """Empty cart: no shipping is added, even though the cart is otherwise valid."""
    cart = Cart()
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_codes_total_zero():
    cart = Cart()
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 0


# ---------- Implied / edge cases ----------

def test_implied_multiple_skus_subtotal():
    cart = Cart()
    cart.add_item("a", 2, 100)  # 200
    cart.add_item("b", 3, 200)  # 600
    assert cart.total_cents() == 800 + 500


def test_implied_freeship_alone_high_subtotal_waives():
    cart = Cart()
    cart.add_item("widget", 1, 7500)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 7500


def test_implied_freeship_with_flat5_just_above_threshold():
    """FLAT5 lowers post-discount subtotal; FREESHIP threshold must use the lowered value."""
    cart = Cart()
    cart.add_item("widget", 1, 5499)
    cart.apply_code("FLAT5")     # 5499 - 500 = 4999
    cart.apply_code("FREESHIP")  # 4999 < 5000 -> not waived
    assert cart.total_cents() == 4999 + 500


def test_implied_freeship_with_flat5_at_threshold():
    cart = Cart()
    cart.add_item("widget", 1, 5500)
    cart.apply_code("FLAT5")     # 5500 - 500 = 5000
    cart.apply_code("FREESHIP")  # 5000 >= 5000 -> waived
    assert cart.total_cents() == 5000


def test_implied_unknown_code_does_not_block_known_code():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    cart.apply_code("BOGUS")  # rejected
    assert cart.apply_code("SAVE10") is True


def test_implied_apply_codes_before_adding_items():
    """Codes can be applied to an empty cart; effects show up when items are added."""
    cart = Cart()
    cart.apply_code("SAVE10")
    cart.add_item("widget", 1, 10000)
    assert cart.total_cents() == 9000 + 500
