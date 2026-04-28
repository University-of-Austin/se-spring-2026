"""Tests for the cart module.

Organized clause by clause against the spec at
starter/assignment3/specs/cart.md (C1-C7), with extra baseline sanity
checks, stacking-pair coverage, the worked spec examples verbatim,
and hidden-edge hunts.
"""
import pytest

from cart import Cart


# ---------------------------------------------------------------------------
# Baseline sanity: confirm the basic add_item / total_cents flow without
# any promo code logic getting involved.
# ---------------------------------------------------------------------------

def test_basic_single_item_no_codes():
    cart = Cart()
    cart.add_item("shirt", 1, 2000)  # $20.00
    # subtotal 2000 + 500 shipping = 2500
    assert cart.total_cents() == 2500


def test_basic_multiple_items_no_codes():
    cart = Cart()
    cart.add_item("shirt", 1, 1000)
    cart.add_item("hat", 2, 500)
    # 1000 + 1000 + 500 shipping = 2500
    assert cart.total_cents() == 2500


def test_basic_quantity_arithmetic():
    cart = Cart()
    cart.add_item("widget", 3, 100)
    # 3 * 100 = 300, + 500 shipping = 800
    assert cart.total_cents() == 800


# ---------------------------------------------------------------------------
# C1. add_item validation: qty >= 1, unit_price >= 0, no duplicate SKUs.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_qty", [0, -1, -5])
def test_c1_qty_zero_or_negative_raises(bad_qty):
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("x", bad_qty, 100)


@pytest.mark.parametrize("bad_price", [-1, -100])
def test_c1_negative_unit_price_raises(bad_price):
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("x", 1, bad_price)


def test_c1_zero_price_is_allowed():
    cart = Cart()
    cart.add_item("freebie", 1, 0)
    # 0 + 500 shipping (cart non-empty) = 500
    assert cart.total_cents() == 500


def test_c1_duplicate_sku_raises():
    cart = Cart()
    cart.add_item("shirt", 1, 1000)
    with pytest.raises(ValueError):
        cart.add_item("shirt", 1, 1000)


# ---------------------------------------------------------------------------
# C2. apply_code: True/False return; case-sensitive; duplicate application
# returns False.
# ---------------------------------------------------------------------------

def test_c2_unknown_code_returns_false():
    cart = Cart()
    cart.add_item("shirt", 1, 1000)
    assert cart.apply_code("BOGUS_CODE") is False


def test_c2_apply_code_returns_true_for_known_code():
    cart = Cart()
    cart.add_item("shirt", 1, 1000)
    assert cart.apply_code("SAVE10") is True


def test_c2_lowercase_code_is_unknown():
    # Code names are case-sensitive per spec.
    cart = Cart()
    cart.add_item("shirt", 1, 1000)
    assert cart.apply_code("save10") is False


def test_c2_duplicate_application_returns_false():
    cart = Cart()
    cart.add_item("shirt", 1, 1000)
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FLAT5") is False


# ---------------------------------------------------------------------------
# C3. Each known code's behavior in isolation.
# ---------------------------------------------------------------------------

def test_c3_save10_applies_10_percent():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    cart.apply_code("SAVE10")
    # 10000 - 10% = 9000, + 500 shipping = 9500
    assert cart.total_cents() == 9500


def test_c3_save20_applies_20_percent():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    cart.apply_code("SAVE20")
    # 10000 - 20% = 8000, + 500 shipping = 8500
    assert cart.total_cents() == 8500


def test_c3_flat5_subtracts_500_cents():
    cart = Cart()
    cart.add_item("shirt", 1, 2000)
    cart.apply_code("FLAT5")
    # 2000 - 500 = 1500, + 500 shipping = 2000
    assert cart.total_cents() == 2000


def test_c3_bogo_bagel_makes_half_free():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    # 2 bagels: qty // 2 = 1 free. subtotal: 300, + 500 shipping = 800
    assert cart.total_cents() == 800


def test_c3_freeship_waives_shipping_when_eligible():
    cart = Cart()
    cart.add_item("widget", 1, 5000)  # exactly $50, threshold met
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5000


# ---------------------------------------------------------------------------
# C4. Stacking rules:
#   - SAVE10 and SAVE20 mutually exclusive.
#   - FLAT5, BOGO_BAGEL, FREESHIP each stack with everything else.
# Pair coverage: ten possible code pairs; the SAVE10+SAVE20 mutex is
# tested explicitly. The remaining nine stacking pairs are sampled below
# (SAVE10 versions are tested; SAVE20 versions exercise the same
# stacking machinery, so I cover the SAVE-percent stacking once via SAVE10
# and the SAVE20 standalone behavior separately above).
# ---------------------------------------------------------------------------

def test_c4_save10_then_save20_returns_false():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False
    # Confirm SAVE10 (10%) actually took effect, not SAVE20.
    # 10000 - 1000 = 9000, + 500 shipping = 9500
    assert cart.total_cents() == 9500


def test_c4_save20_then_save10_returns_false():
    # The mutex applies symmetrically: whichever you apply first wins.
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("SAVE10") is False
    # 10000 - 2000 = 8000, + 500 shipping = 8500
    assert cart.total_cents() == 8500


def test_c4_save10_and_flat5_stack():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    # 10000 - 1000 = 9000 - 500 = 8500, + 500 shipping = 9000
    assert cart.total_cents() == 9000


def test_c4_save10_and_bogo_stack():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("BOGO_BAGEL") is True
    # subtotal 600, BOGO: 600 - 300 = 300, SAVE10: 300 - 30 = 270, + 500 = 770
    assert cart.total_cents() == 770


def test_c4_save10_and_freeship_stack():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FREESHIP") is True
    # 10000 - 1000 = 9000 >= 5000, shipping waived. Total = 9000
    assert cart.total_cents() == 9000


def test_c4_flat5_and_bogo_stack():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("BOGO_BAGEL") is True
    # subtotal 600, BOGO: 300, FLAT5: 300 - 500 = -200 -> clamped to 0
    # cart non-empty, FREESHIP not applied -> + 500 shipping
    assert cart.total_cents() == 500


def test_c4_flat5_and_freeship_stack():
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True
    # 5000 - 500 = 4500 < 5000 -> FREESHIP threshold NOT met,
    # so shipping IS still added: 4500 + 500 = 5000.
    assert cart.total_cents() == 5000


def test_c4_bogo_and_freeship_stack():
    cart = Cart()
    cart.add_item("bagel", 20, 500)  # 20 * $5 = $100 subtotal
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("FREESHIP") is True
    # subtotal 10000, BOGO: 10000 - 10*500 = 5000, threshold met, no shipping
    assert cart.total_cents() == 5000


def test_c4_all_four_stackable_codes_together():
    # Maximum possible stack: SAVE10, FLAT5, BOGO_BAGEL, FREESHIP
    # (SAVE10 and SAVE20 are mutex, so only one percent code can apply).
    cart = Cart()
    cart.add_item("bagel", 20, 1000)  # 20 * $10
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("FREESHIP") is True
    # subtotal: 20000
    # BOGO: 20000 - 10*1000 = 10000
    # SAVE10: 10000 * 0.9 = 9000
    # FLAT5: 9000 - 500 = 8500
    # 8500 >= 5000 + FREESHIP -> no shipping
    assert cart.total_cents() == 8500


# ---------------------------------------------------------------------------
# C5. Application order: subtotal -> BOGO -> percent -> FLAT5 (clamp 0)
# -> shipping (FREESHIP waives only at >= 5000 post-FLAT5).
# ---------------------------------------------------------------------------

def test_c5_application_order_full_chain():
    # Same scenario as the all-four-stackable test; this test exists to
    # name the application-order property explicitly.
    cart = Cart()
    cart.add_item("bagel", 20, 1000)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    # If any step happens out of order the total will not match 8500.
    assert cart.total_cents() == 8500


def test_c5_flat5_clamps_at_zero_not_negative():
    cart = Cart()
    cart.add_item("cheap", 1, 300)  # $3.00
    cart.apply_code("FLAT5")
    # 300 - 500 = -200 -> clamped to 0; cart non-empty -> + 500 shipping
    assert cart.total_cents() == 500


def test_c5_freeship_below_5000_does_not_waive_shipping():
    cart = Cart()
    cart.add_item("widget", 1, 4000)  # $40.00
    cart.apply_code("FREESHIP")
    # 4000 < 5000, threshold not met, shipping still added
    assert cart.total_cents() == 4500


def test_c5_freeship_at_exactly_5000_waives_shipping():
    cart = Cart()
    cart.add_item("widget", 1, 5000)  # exactly $50
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5000


def test_c5_freeship_just_below_5000_does_not_waive():
    cart = Cart()
    cart.add_item("widget", 1, 4999)  # $49.99
    cart.apply_code("FREESHIP")
    # 4999 < 5000, NOT waived
    assert cart.total_cents() == 5499


# ---------------------------------------------------------------------------
# C6. Banker's rounding (round half to even) on percent discount.
# ---------------------------------------------------------------------------

def test_c6_banker_rounding_half_rounds_down_to_even_zero():
    # subtotal 5, SAVE10 -> discount = 0.5 -> rounds to 0 (even).
    # After: 5 - 0 = 5, + 500 shipping = 505
    cart = Cart()
    cart.add_item("x", 1, 5)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 505


def test_c6_banker_rounding_half_rounds_up_to_even_two():
    # subtotal 15, SAVE10 -> discount = 1.5 -> rounds to 2 (even).
    # After: 15 - 2 = 13, + 500 shipping = 513
    cart = Cart()
    cart.add_item("x", 1, 15)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 513


def test_c6_banker_rounding_half_rounds_down_to_even_two():
    # subtotal 25, SAVE10 -> discount = 2.5 -> rounds to 2 (even, not 3).
    # After: 25 - 2 = 23, + 500 shipping = 523
    cart = Cart()
    cart.add_item("x", 1, 25)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 523


def test_c6_no_rounding_needed_baseline():
    # subtotal 100, SAVE10 -> discount = 10 exactly. After: 90, + 500 = 590
    cart = Cart()
    cart.add_item("x", 1, 100)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 590


# ---------------------------------------------------------------------------
# C7. Empty cart returns 0; no shipping; codes have no effect.
# ---------------------------------------------------------------------------

def test_c7_empty_cart_total_is_zero():
    cart = Cart()
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_codes_still_zero():
    cart = Cart()
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    # FLAT5 must NOT pull total below 0; shipping must NOT be added.
    assert cart.total_cents() == 0


# ---------------------------------------------------------------------------
# Worked spec examples (verbatim from starter/assignment3/specs/cart.md).
# ---------------------------------------------------------------------------

def test_spec_example_bogo_bagel():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.total_cents() == 800


def test_spec_example_save10_save20_flat5():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False
    assert cart.apply_code("FLAT5") is True
    assert cart.total_cents() == 9000


def test_spec_example_freeship_at_50_dollars():
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    assert cart.apply_code("FREESHIP") is True
    assert cart.total_cents() == 5000


def test_spec_example_empty_cart():
    cart = Cart()
    assert cart.total_cents() == 0


# ---------------------------------------------------------------------------
# Hidden-edge hunts: properties the spec implies but does not name explicitly.
# ---------------------------------------------------------------------------

def test_hidden_bogo_with_no_bagel_still_counts_as_applied():
    # Spec parenthetical: "If no bagel line item exists when total_cents
    # is computed, the code has no effect but is still considered
    # 'applied' for the purpose of C2's duplicate-application rule."
    cart = Cart()
    cart.add_item("shirt", 1, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    # Second application must be rejected as duplicate.
    assert cart.apply_code("BOGO_BAGEL") is False
    # Total should be unaffected: 1000 + 500 shipping = 1500
    assert cart.total_cents() == 1500


def test_hidden_bogo_with_single_bagel_grants_zero_free():
    # qty // 2 with qty=1 gives 0 free.
    cart = Cart()
    cart.add_item("bagel", 1, 300)
    cart.apply_code("BOGO_BAGEL")
    # 1 paid bagel + 500 shipping = 800
    assert cart.total_cents() == 800


def test_hidden_flat5_clamp_disqualifies_freeship():
    # FLAT5 brings pre-shipping to 0 (clamped). FREESHIP threshold is
    # measured AFTER the clamp, so 0 < 5000 -> shipping NOT waived.
    cart = Cart()
    cart.add_item("cheap", 1, 300)
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    # 300 - 500 = -200 -> 0 (clamped). FREESHIP gates at >= 5000 -> shipping added.
    assert cart.total_cents() == 500
