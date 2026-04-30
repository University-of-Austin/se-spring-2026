"""Tests for cart.Cart, organized by spec clause.

Money is in integer cents throughout. Shipping is 500 cents. FREESHIP
threshold is 5000 cents on the post-discount pre-shipping subtotal.
"""
import pytest

from cart import Cart


@pytest.fixture
def cart():
    """Fresh empty Cart for tests that don't need pre-populated state.

    Pytest re-runs this fixture per test, so each test gets an isolated cart.
    Tests that need to compare two carts or build specific state should
    construct Cart() instances explicitly instead.
    """
    return Cart()


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


def test_c1_duplicate_sku_with_different_qty_raises(cart):
    """Dupe rule is sku-only, not (sku, qty): same sku at different qty still raises."""
    cart.add_item("widget", 1, 100)
    with pytest.raises(ValueError):
        cart.add_item("widget", 5, 100)


def test_c1_two_distinct_skus_both_accepted(cart):
    """Different SKUs are independent line items; both go into the cart."""
    cart.add_item("widget", 1, 100)
    cart.add_item("gadget", 1, 200)
    assert cart.total_cents() == 300 + 500


def test_c1_unit_price_negative_one_raises(cart):
    """Boundary: -1 is exactly one below the non-negative threshold and must raise."""
    with pytest.raises(ValueError):
        cart.add_item("widget", 1, -1)


def test_c1_separate_carts_have_independent_state():
    """Two Cart instances must not share items, codes, or any other state.

    Catches a bug where items/codes are class attributes instead of instance
    attributes (a classic Python gotcha that makes all Carts share one list).
    """
    cart_a = Cart()
    cart_b = Cart()
    cart_a.add_item("widget", 1, 100)
    cart_a.apply_code("SAVE10")
    assert cart_b.total_cents() == 0
    assert cart_b.apply_code("SAVE20") is True  # cart_b has no codes applied


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


def test_c2_already_applied_tracking_is_per_code(cart):
    """The 'already applied' check is per-code, not a global flag.

    Catches a bug like `if self.applied: return False` (single bool) instead of
    `if code in self.applied: return False` (per-code set).
    """
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FLAT5") is False  # same code: already applied
    assert cart.apply_code("SAVE10") is True  # different code: still fresh


def test_c2_apply_save10_returns_true(cart):
    """SAVE10 returns True on first apply."""
    assert cart.apply_code("SAVE10") is True


def test_c2_apply_save20_returns_true(cart):
    """SAVE20 returns True on first apply."""
    assert cart.apply_code("SAVE20") is True


def test_c2_apply_bogo_bagel_returns_true(cart):
    """BOGO_BAGEL returns True on first apply, even with no bagel in cart."""
    assert cart.apply_code("BOGO_BAGEL") is True


def test_c2_apply_freeship_returns_true(cart):
    """FREESHIP returns True on first apply."""
    assert cart.apply_code("FREESHIP") is True


def test_c2_apply_mixed_case_save10_is_unknown(cart):
    """Case sensitivity beyond all-lowercase: 'Save10' must not match 'SAVE10'."""
    assert cart.apply_code("Save10") is False


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


def test_c3_bogo_bagel_with_mixed_cart_discounts_only_bagel(cart):
    """BOGO discounts the bagel line only; non-bagel items in same cart pay full price."""
    cart.add_item("bagel", 2, 300)    # BOGO removes 1 -> 300
    cart.add_item("widget", 1, 1000)  # full price
    cart.apply_code("BOGO_BAGEL")
    # 300 (bagel) + 1000 (widget) + 500 shipping = 1800
    assert cart.total_cents() == 300 + 1000 + 500


def test_c3_bogo_bagel_qty_5_two_free(cart):
    """5 // 2 = 2 free; pay for 3 bagels."""
    cart.add_item("bagel", 5, 300)
    cart.apply_code("BOGO_BAGEL")
    # 5*300 = 1500, minus 2 free (600) = 900, + 500 shipping = 1400
    assert cart.total_cents() == 900 + 500


def test_c3_freeship_just_above_threshold_waives(cart):
    """5001 is above 5000; FREESHIP applies (>= boundary, just-above side)."""
    cart.add_item("widget", 1, 5001)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5001


def test_c3_bogo_bagel_high_qty_arithmetic(cart):
    """100 // 2 = 50 free; pay for 50. Stress test of qty // 2 arithmetic at scale."""
    cart.add_item("bagel", 100, 300)
    cart.apply_code("BOGO_BAGEL")
    # 100*300 = 30000, 50 free (15000) = 15000, + 500 shipping = 15500
    assert cart.total_cents() == 15000 + 500


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


def test_c4_save20_stacks_with_bogo(cart):
    """SAVE20 + BOGO_BAGEL stack (the only pair previously uncovered)."""
    cart.add_item("bagel", 4, 500)   # subtotal 2000
    cart.apply_code("BOGO_BAGEL")    # 2000 -> 1000 (2 free)
    cart.apply_code("SAVE20")        # 1000 -> 800
    # 800 + 500 shipping = 1300
    assert cart.total_cents() == 1300


def test_c4_save20_then_save10_rejected_then_flat5_stacks(cart):
    """SAVE20 first, SAVE10 rejected as conflict, FLAT5 still stacks.

    Mirrors test_c4_flat5_stacks_with_save10 from the SAVE20 side, with explicit
    bool-return checks at every step.
    """
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("SAVE10") is False  # mutex with SAVE20
    assert cart.apply_code("FLAT5") is True    # stacks with SAVE20
    # 10000 -> 8000 (SAVE20) -> 7500 (FLAT5) + 500 shipping = 8000
    assert cart.total_cents() == 8000


def test_c4_bogo_stacks_with_freeship(cart):
    """BOGO + FREESHIP stack: both apply_code calls return True; both effects compute."""
    cart.add_item("bagel", 4, 2500)  # subtotal 10000
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("FREESHIP") is True
    # BOGO: 10000 -> 5000; FREESHIP: 5000 >= 5000 -> waived
    assert cart.total_cents() == 5000


def test_c4_all_four_non_conflicting_codes_stack(cart):
    """SAVE10 + FLAT5 + BOGO_BAGEL + FREESHIP all stack together.

    Kitchen-sink integration test: every code that's allowed to coexist does.
    """
    cart.add_item("bagel", 4, 3500)  # subtotal 14000
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True
    # BOGO: 14000 -> 7000; SAVE10: 7000 -> 6300; FLAT5: 6300 -> 5800
    # 5800 >= 5000 -> FREESHIP waives shipping
    assert cart.total_cents() == 5800


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


def test_c5_freeship_first_then_flat5_must_recheck_threshold(cart):
    """FREESHIP applied while subtotal qualifies; FLAT5 then drops below threshold.

    Threshold must be re-evaluated at total_cents() time, not at apply_code() time.
    Catches a buggy impl that decides FREESHIP eligibility eagerly when the code is applied.
    """
    cart.add_item("widget", 1, 5400)
    cart.apply_code("FREESHIP")  # eager-eval would see 5400 >= 5000 and waive
    cart.apply_code("FLAT5")     # post-FLAT5: 4900 < 5000, must NOT be waived
    assert cart.total_cents() == 4900 + 500


def test_c5_apply_call_order_does_not_change_total(cart):
    """Calling FLAT5 before SAVE10 must produce the same result as calling SAVE10 first.

    Spec order (SAVE10 step 3, FLAT5 step 4) runs at total_cents() time regardless
    of apply_code() call order.
    """
    cart.add_item("shirt", 1, 10000)
    cart.apply_code("FLAT5")     # called first
    cart.apply_code("SAVE10")    # called second
    # Spec order: SAVE10 (10000->9000), FLAT5 (9000->8500), +500 shipping = 9000
    assert cart.total_cents() == 9000


def test_c5_freeship_threshold_reached_via_bogo(cart):
    """BOGO reduces post-step-2 subtotal to exactly 5000; FREESHIP applies."""
    cart.add_item("bagel", 4, 2500)  # 10000 subtotal
    cart.apply_code("BOGO_BAGEL")    # 10000 -> 5000 (2 free)
    cart.apply_code("FREESHIP")      # 5000 >= 5000 -> waive
    assert cart.total_cents() == 5000


def test_c5_save10_with_freeship_just_above_threshold_waives(cart):
    """SAVE10 lowers subtotal but stays above threshold; FREESHIP applies."""
    cart.add_item("widget", 1, 6000)
    cart.apply_code("SAVE10")    # 6000 -> 5400
    cart.apply_code("FREESHIP")  # 5400 >= 5000 -> waive
    assert cart.total_cents() == 5400


def test_c5_save20_with_freeship_below_threshold_does_not_waive(cart):
    """SAVE20 cannot be used to dodge the shipping threshold.

    Even though raw subtotal 6000 >= 5000, the post-discount value 4800 is below
    threshold and shipping is NOT waived. Mirrors the SAVE10 case in C3.
    """
    cart.add_item("widget", 1, 6000)
    cart.apply_code("SAVE20")    # 6000 -> 4800
    cart.apply_code("FREESHIP")  # 4800 < 5000 -> NOT waived
    assert cart.total_cents() == 4800 + 500


def test_c5_save20_with_freeship_at_exact_threshold_waives(cart):
    """SAVE20 lands post-discount at exactly 5000; FREESHIP applies (>= boundary)."""
    cart.add_item("widget", 1, 6250)
    cart.apply_code("SAVE20")    # 6250 -> 5000
    cart.apply_code("FREESHIP")  # 5000 >= 5000 -> waive
    assert cart.total_cents() == 5000


def test_c5_save20_with_freeship_just_above_threshold_waives(cart):
    """SAVE20 stays above threshold; FREESHIP applies."""
    cart.add_item("widget", 1, 6500)
    cart.apply_code("SAVE20")    # 6500 -> 5200
    cart.apply_code("FREESHIP")  # 5200 >= 5000 -> waive
    assert cart.total_cents() == 5200


def test_c5_flat5_at_subtotal_500_no_clamp_needed(cart):
    """500 - 500 = 0 exactly; no clamp involved. Pre-shipping = 0; +500 shipping = 500."""
    cart.add_item("widget", 1, 500)
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 0 + 500


def test_c5_flat5_at_subtotal_499_clamps_from_negative_one(cart):
    """499 - 500 = -1; clamps to 0. Smallest negative case for the clamp clause."""
    cart.add_item("widget", 1, 499)
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 0 + 500


# ---------- C6: rounding (banker's / HALF_EVEN) ----------

def test_c6_save10_rounds_half_even_subtotal_1005():
    """100.5 rounds to 100 (nearest even). 1005 - 100 + 500 shipping = 1405."""
    cart = Cart()
    cart.add_item("widget", 1, 1005)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 1005 - 100 + 500


def test_c6_save10_rounds_half_even_subtotal_1015():
    """101.5 rounds to 102 (nearest even). 1015 - 102 + 500 shipping = 1413."""
    cart = Cart()
    cart.add_item("widget", 1, 1015)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 1015 - 102 + 500


def test_c6_save10_rounds_half_even_subtotal_1025():
    """102.5 rounds to 102 (nearest even). 1025 - 102 + 500 shipping = 1423."""
    cart = Cart()
    cart.add_item("widget", 1, 1025)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 1025 - 102 + 500


def test_c6_save10_rounds_half_even_subtotal_1035():
    """103.5 rounds to 104 (nearest even). 1035 - 104 + 500 shipping = 1431."""
    cart = Cart()
    cart.add_item("widget", 1, 1035)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 1035 - 104 + 500


def test_c6_save10_no_rounding_when_clean_division():
    """10% of 1000 is exactly 100; no rounding involved."""
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 1000 - 100 + 500


def test_c6_save20_rounds_non_integer_result(cart):
    """SAVE20 rounds a non-tie fractional result correctly.

    20% of 1003 = 200.6, which rounds to 201 under any reasonable rounding mode.
    Catches a buggy SAVE20 that truncates (would discount 200) instead of rounding.
    Note: 20% of integer cents never produces a HALF_EVEN tie; this is the
    closest test to 'percent discounts rounded' that SAVE20 admits.
    """
    cart.add_item("widget", 1, 1003)
    cart.apply_code("SAVE20")
    # 1003 - 201 + 500 shipping = 1302
    assert cart.total_cents() == 1302


def test_c6_save20_no_rounding_when_clean_division(cart):
    """20% of 1000 is exactly 200; no rounding involved. SAVE20 negative control."""
    cart.add_item("widget", 1, 1000)
    cart.apply_code("SAVE20")
    # 1000 - 200 + 500 shipping = 1300
    assert cart.total_cents() == 1300


def test_c6_save10_half_even_at_larger_scale(cart):
    """HALF_EVEN holds at larger values: 10% of 10005 = 1000.5 -> 1000 (even).

    Catches precision or overflow bugs that only show at higher amounts.
    """
    cart.add_item("widget", 1, 10005)
    cart.apply_code("SAVE10")
    # 10005 - 1000 + 500 shipping = 9505
    assert cart.total_cents() == 9505


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


def test_c7_empty_cart_with_save20_total_zero(cart):
    """Empty cart + SAVE20: total is 0. Symmetric to existing SAVE10 case."""
    cart.apply_code("SAVE20")
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_bogo_bagel_total_zero(cart):
    """Empty cart + BOGO_BAGEL: BOGO is 'applied' vacuously, total still 0."""
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_all_stackable_codes_total_zero(cart):
    """Empty cart + every non-conflicting code: total is 0 regardless."""
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("BOGO_BAGEL")
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


def test_implied_bogo_applied_then_bagel_added_discounts_correctly(cart):
    """BOGO is evaluated at total_cents() time, not at apply_code() time.

    Catches a buggy impl that snapshots the bagel line at apply time and
    misses bagels added after.
    """
    cart.apply_code("BOGO_BAGEL")
    cart.add_item("bagel", 2, 300)
    # 600 subtotal - 300 (1 free) + 500 shipping = 800
    assert cart.total_cents() == 800


def test_implied_total_cents_is_idempotent(cart):
    """Calling total_cents() twice produces the same result.

    Catches a buggy impl that mutates state inside total_cents (e.g., applies
    discounts destructively or accumulates in a counter).
    """
    cart.add_item("widget", 1, 1000)
    cart.apply_code("SAVE10")
    first = cart.total_cents()
    second = cart.total_cents()
    assert first == second


def test_implied_apply_code_after_total_cents_still_works(cart):
    """total_cents() does not freeze the cart; codes applied after still take effect."""
    cart.add_item("widget", 1, 10000)
    assert cart.total_cents() == 10000 + 500  # initial total, no codes
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 9000 + 500   # discount applies on next call


def test_implied_add_item_after_total_cents_still_works(cart):
    """total_cents() does not freeze the cart; items added after still count."""
    cart.add_item("widget", 1, 1000)
    assert cart.total_cents() == 1000 + 500   # initial total
    cart.add_item("gadget", 1, 500)
    assert cart.total_cents() == 1500 + 500   # both line items counted


def test_implied_save10_save20_rejected_save10_chain(cart):
    """SAVE10 -> SAVE20 (conflict) -> SAVE10 (already applied) all return correctly.

    Confirms 'already applied' state persists through a conflict-rejection event.
    """
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False  # conflict
    assert cart.apply_code("SAVE10") is False  # already applied


def test_implied_bogo_and_flat5_call_order_does_not_change_total(cart):
    """BOGO then FLAT5 order is fixed by spec, regardless of apply_code() call order."""
    cart.add_item("bagel", 4, 500)  # subtotal 2000
    cart.apply_code("FLAT5")        # intentionally called first
    cart.apply_code("BOGO_BAGEL")
    # Spec order: BOGO (2000->1000), then FLAT5 (1000->500), then shipping.
    assert cart.total_cents() == 500 + 500


def test_implied_all_non_conflicting_codes_ignore_apply_call_order(cart):
    """Non-conflicting codes stack by fixed spec order, not call order."""
    cart.add_item("bagel", 4, 3000)  # subtotal 12000
    cart.apply_code("FREESHIP")
    cart.apply_code("FLAT5")
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    # Spec order:
    # BOGO: 12000 -> 6000
    # SAVE10: 6000 -> 5400
    # FLAT5: 5400 -> 4900
    # FREESHIP check uses 4900, so shipping is not waived.
    assert cart.total_cents() == 4900 + 500


@pytest.mark.parametrize("sku", ["Bagel", "bagel ", "bagel-mini"])
def test_implied_bogo_matches_only_exact_lowercase_bagel_sku(cart, sku):
    """BOGO applies only to SKU exactly equal to 'bagel'."""
    cart.add_item(sku, 2, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 600 + 500


def test_implied_shipping_not_waived_without_freeship_even_at_threshold(cart):
    """Shipping remains charged at >=5000 unless FREESHIP code is applied."""
    cart.add_item("widget", 1, 5000)
    assert cart.total_cents() == 5000 + 500


def test_implied_save20_then_flat5_clamps_post_discount_subtotal_to_zero(cart):
    """FLAT5 clamp applies after percent discount in the spec's calculation order."""
    cart.add_item("widget", 1, 500)  # SAVE20 => 400
    cart.apply_code("SAVE20")
    cart.apply_code("FLAT5")         # 400 - 500 => clamp to 0
    assert cart.total_cents() == 0 + 500
