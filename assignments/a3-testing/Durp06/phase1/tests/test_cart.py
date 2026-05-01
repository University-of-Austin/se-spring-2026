"""Tests for cart.Cart, organized clause-by-clause against
starter/assignment3/specs/cart.md.

Conventions used in the spec:
  * subtotal       — sum of qty * unit_price_cents over all line items
  * post-BOGO      — subtotal after BOGO_BAGEL discount (if applied)
  * post-percent   — post-BOGO after SAVE10/SAVE20 (if applied)
  * pre-shipping   — post-percent after FLAT5 (if applied), clamped to >= 0
  * shipping       — flat 500 cents on non-empty carts unless FREESHIP applies
                     and pre-shipping >= 5000.

Application order is BOGO -> percent -> FLAT5 -> shipping (C5).
Rounding for percent discounts is half-even / banker's (C6).
"""
import pytest

from cart import Cart


# ---------------------------------------------------------------------------
# C1. add_item validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_qty", [0, -1, -100])
def test_c1_qty_must_be_positive(bad_qty):
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", bad_qty, 100)


def test_c1_qty_one_is_valid():
    cart = Cart()
    cart.add_item("widget", 1, 100)
    assert cart.total_cents() == 100 + 500  # +shipping


@pytest.mark.parametrize("bad_price", [-1, -500])
def test_c1_unit_price_must_be_non_negative(bad_price):
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", 1, bad_price)


def test_c1_zero_price_is_allowed():
    cart = Cart()
    cart.add_item("freebie", 3, 0)
    # cart non-empty -> shipping still applies
    assert cart.total_cents() == 500


def test_c1_duplicate_sku_raises_value_error():
    cart = Cart()
    cart.add_item("widget", 1, 100)
    with pytest.raises(ValueError):
        cart.add_item("widget", 2, 200)


# ---------------------------------------------------------------------------
# C2. apply_code return values
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "code", ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"]
)
def test_c2_known_codes_accepted_first_time(code):
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code(code) is True


def test_c2_unknown_code_rejected():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("NOPE") is False


def test_c2_codes_are_case_sensitive():
    """Spec: '"SAVE10" is a valid code; "save10" is unknown.'"""
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("save10") is False
    assert cart.apply_code("Save10") is False
    assert cart.apply_code("SAVE10") is True


@pytest.mark.parametrize(
    "code", ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"]
)
def test_c2_duplicate_apply_returns_false(code):
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code(code) is True
    assert cart.apply_code(code) is False


# ---------------------------------------------------------------------------
# C3. Known codes — independent effects
# ---------------------------------------------------------------------------

def test_c3_save10_takes_ten_percent_off():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("SAVE10")
    # 10000 - 1000 = 9000 + 500 shipping = 9500
    assert cart.total_cents() == 9500


def test_c3_save20_takes_twenty_percent_off():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("SAVE20")
    # 10000 - 2000 = 8000 + 500 shipping = 8500
    assert cart.total_cents() == 8500


def test_c3_flat5_subtracts_500_cents():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("FLAT5")
    # 10000 - 500 = 9500 + 500 shipping = 10000
    assert cart.total_cents() == 10000


def test_c3_bogo_bagel_makes_half_qty_free():
    """Spec example: 2 bagels @ 300 with BOGO -> 300 + 500 ship = 800."""
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 800


def test_c3_bogo_bagel_qty_three_one_free():
    """qty // 2 = 1 free, 2 paid."""
    cart = Cart()
    cart.add_item("bagel", 3, 300)
    cart.apply_code("BOGO_BAGEL")
    # 600 paid + 500 shipping = 1100
    assert cart.total_cents() == 1100


def test_c3_bogo_bagel_qty_one_zero_free():
    """qty // 2 = 0 free, 1 paid."""
    cart = Cart()
    cart.add_item("bagel", 1, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 300 + 500


def test_c3_bogo_only_affects_bagel_sku():
    """A BOGO with no bagel line item has no effect — but is still applied."""
    cart = Cart()
    cart.add_item("widget", 4, 100)
    cart.apply_code("BOGO_BAGEL")
    # subtotal 400, no BOGO effect, + 500 ship = 900
    assert cart.total_cents() == 900


def test_c3_bogo_with_no_bagel_is_still_applied_for_duplicate_rule():
    """Spec: 'no bagel line item ... still considered "applied" for ...
    duplicate-application rule.'"""
    cart = Cart()
    cart.add_item("widget", 1, 100)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("BOGO_BAGEL") is False


def test_c3_freeship_waives_shipping_at_or_above_5000():
    cart = Cart()
    cart.add_item("widget", 1, 5000)  # exactly $50.00
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5000


# ---------------------------------------------------------------------------
# C4. Stacking rules
# ---------------------------------------------------------------------------

def test_c4_save10_then_save20_rejects_second():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False
    # Only SAVE10 took effect: 10000 - 1000 = 9000 + 500 = 9500
    assert cart.total_cents() == 9500


def test_c4_save20_then_save10_rejects_second():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("SAVE10") is False
    # Only SAVE20 took effect: 10000 - 2000 = 8000 + 500 = 8500
    assert cart.total_cents() == 8500


def test_c4_flat5_stacks_with_save10():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("SAVE10")
    assert cart.apply_code("FLAT5") is True
    # 10000 - 1000 = 9000, then -500 = 8500, + 500 ship = 9000
    assert cart.total_cents() == 9000


def test_c4_flat5_stacks_with_save20():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("SAVE20")
    assert cart.apply_code("FLAT5") is True
    # 10000 - 2000 = 8000, -500 = 7500, +500 ship = 8000
    assert cart.total_cents() == 8000


def test_c4_bogo_stacks_with_percent():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("SAVE10") is True


def test_c4_freeship_stacks_with_save10():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("SAVE10")
    assert cart.apply_code("FREESHIP") is True


def test_c4_all_compatible_codes_can_stack():
    cart = Cart()
    cart.add_item("bagel", 4, 300)        # 1200 subtotal
    cart.add_item("widget", 1, 5000)      # +5000 = 6200 subtotal
    assert cart.apply_code("BOGO_BAGEL") is True   # 1200 -> 600 (2 free)
    assert cart.apply_code("SAVE10") is True       # subtotal post-BOGO 5600, -560 = 5040
    assert cart.apply_code("FLAT5") is True        # 5040 - 500 = 4540
    assert cart.apply_code("FREESHIP") is True     # 4540 < 5000, ship still applies
    assert cart.total_cents() == 4540 + 500


# ---------------------------------------------------------------------------
# C5. Application order
# ---------------------------------------------------------------------------

def test_c5_bogo_applied_before_percent():
    """2 bagels @ 300 + BOGO + SAVE10:
        subtotal 600 -> BOGO -300 = 300 -> SAVE10 -30 = 270 -> +500 ship = 770.
    If percent were applied before BOGO: 600 - 60 = 540 -> BOGO -300 = 240 ->
    + 500 = 740. Different number, so this nails down ordering."""
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 770


def test_c5_flat5_applied_after_percent():
    """$100 + SAVE10 + FLAT5:
       10000 -> -1000 = 9000 -> -500 = 8500 -> + 500 ship = 9000.
    If FLAT5 were before percent: 10000 - 500 = 9500 -> -950 = 8550 -> + 500
    = 9050. Different number, pins the order."""
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 9000


def test_c5_flat5_clamps_pre_shipping_at_zero():
    """Spec: 'If this would make the pre-shipping total negative, clamp at 0.'"""
    cart = Cart()
    cart.add_item("widget", 1, 200)  # subtotal 200, < 500
    cart.apply_code("FLAT5")
    # pre-shipping = max(0, 200 - 500) = 0; cart non-empty -> + 500 ship
    assert cart.total_cents() == 500


def test_c5_bogo_then_flat5_clamps_to_zero():
    """2 bagels @ 300 + BOGO + FLAT5: subtotal 600 -> BOGO -300 = 300 ->
    FLAT5 -500 -> clamp 0 pre-shipping -> + 500 ship = 500. Exercises the
    clamp through a different combination of codes than the percent path."""
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 500


def test_c5_flat5_with_percent_then_clamp():
    """Tests clamp lands on 0 even when reached via percent + FLAT5."""
    cart = Cart()
    cart.add_item("widget", 1, 400)
    cart.apply_code("SAVE10")          # 400 - 40 = 360
    cart.apply_code("FLAT5")           # 360 - 500 -> clamp 0
    assert cart.total_cents() == 500   # 0 pre-shipping + 500 ship


def test_c5_shipping_added_to_non_empty_cart_when_no_freeship():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.total_cents() == 1500  # 1000 + 500 shipping


def test_c5_apply_order_in_code_calls_does_not_change_total():
    """Codes apply per the spec's fixed order regardless of the order they
    were called in apply_code."""
    cart_a = Cart()
    cart_a.add_item("bagel", 2, 300)
    cart_a.apply_code("SAVE10")
    cart_a.apply_code("BOGO_BAGEL")

    cart_b = Cart()
    cart_b.add_item("bagel", 2, 300)
    cart_b.apply_code("BOGO_BAGEL")
    cart_b.apply_code("SAVE10")

    assert cart_a.total_cents() == cart_b.total_cents()


# ---- FREESHIP boundary --------------------------------------------------

def test_c5_freeship_threshold_exactly_at_5000_waives():
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5000


def test_c5_freeship_threshold_just_below_does_not_waive():
    cart = Cart()
    cart.add_item("widget", 1, 4999)
    cart.apply_code("FREESHIP")
    # 4999 < 5000 -> shipping still applies
    assert cart.total_cents() == 4999 + 500


def test_c5_freeship_threshold_just_above_waives():
    cart = Cart()
    cart.add_item("widget", 1, 5001)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5001


def test_c5_freeship_uses_post_discount_threshold_not_subtotal():
    """$50 with SAVE10 -> 5000 - 500 = 4500 pre-shipping, < 5000, so shipping
    is NOT waived. If FREESHIP looked at the raw subtotal (5000), it would
    incorrectly waive."""
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    cart.apply_code("SAVE10")
    cart.apply_code("FREESHIP")
    # post-percent 4500, +500 ship = 5000
    assert cart.total_cents() == 5000


def test_c5_freeship_threshold_uses_post_flat5_total():
    """$54.99 with FLAT5 -> 5499 - 500 = 4999 < 5000 -> shipping still added.
    Pin that FREESHIP looks at the post-FLAT5 number, not pre-FLAT5."""
    cart = Cart()
    cart.add_item("widget", 1, 5499)
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    # pre-shipping = 4999, < 5000 -> shipping added
    assert cart.total_cents() == 4999 + 500


def test_c5_freeship_alone_with_low_total_does_not_waive():
    cart = Cart()
    cart.add_item("widget", 1, 100)
    cart.apply_code("FREESHIP")
    # 100 < 5000 -> shipping still applies
    assert cart.total_cents() == 600


# ---------------------------------------------------------------------------
# C6. Banker's rounding (ROUND_HALF_EVEN) on percent discounts.
#
# SAVE10 hits the half-cent boundary at subtotals 5, 15, 25, 35, 45, ...
# Banker's rounds 0.5 toward the nearest even integer:
#   0.5 -> 0,  1.5 -> 2,  2.5 -> 2,  3.5 -> 4,  4.5 -> 4
# These values disagree with both ROUND_HALF_UP and ROUND_DOWN at different
# points, so the table below catches several rounding-bug shapes.
# Each row is (subtotal, expected discount).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "subtotal, expected_discount",
    [
        (5,  0),   # 0.5 -> 0      (half-up would give 1)
        (15, 2),   # 1.5 -> 2      (half-down/trunc would give 1)
        (25, 2),   # 2.5 -> 2      (half-up would give 3)
        (35, 4),   # 3.5 -> 4      (half-down/trunc would give 3)
        (45, 4),   # 4.5 -> 4      (half-up would give 5)
    ],
)
def test_c6_save10_banker_rounding_at_half_cent(subtotal, expected_discount):
    cart = Cart()
    cart.add_item("widget", 1, subtotal)
    cart.apply_code("SAVE10")
    expected_pre_shipping = subtotal - expected_discount
    expected_total = expected_pre_shipping + 500   # + shipping (cart non-empty)
    assert cart.total_cents() == expected_total


def test_c6_save10_no_rounding_needed():
    """A subtotal where SAVE10 yields an integer discount — sanity check."""
    cart = Cart()
    cart.add_item("widget", 1, 200)   # 10% = 20.0, no rounding ambiguity
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 200 - 20 + 500


def test_c6_save20_exact_when_subtotal_divisible_by_5():
    cart = Cart()
    cart.add_item("widget", 1, 100)   # 20% = 20.0
    cart.apply_code("SAVE20")
    assert cart.total_cents() == 100 - 20 + 500


# ---------------------------------------------------------------------------
# C7. Empty cart
# ---------------------------------------------------------------------------

def test_c7_empty_cart_total_is_zero():
    cart = Cart()
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_codes_still_zero():
    """Spec: 'returns 0 regardless of which codes have been applied.'"""
    cart = Cart()
    # Some codes may legitimately reject on an empty cart; apply_code's return
    # value isn't what we're testing here. The total must be 0 either way.
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 0


def test_c7_empty_cart_no_shipping():
    """Spec: 'If cart is empty, shipping is not added regardless of codes.'"""
    cart = Cart()
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 0


# ---------------------------------------------------------------------------
# Cross-cutting: the spec's worked examples
# ---------------------------------------------------------------------------

def test_spec_example_bagels_bogo():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.total_cents() == 800


def test_spec_example_shirt_save10_save20_flat5():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False
    assert cart.apply_code("FLAT5") is True
    assert cart.total_cents() == 9000


def test_spec_example_widget_freeship_at_threshold():
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    assert cart.apply_code("FREESHIP") is True
    assert cart.total_cents() == 5000


def test_spec_example_empty_cart_zero():
    assert Cart().total_cents() == 0
