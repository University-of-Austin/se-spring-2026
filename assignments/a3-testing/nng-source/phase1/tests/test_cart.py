"""Tests for cart.Cart.

Spec clauses:
  C1: add_item adds a line with (sku, qty, unit_price_cents). All prices are
      integer cents.
  C2: apply_code returns True if accepted, False if rejected.
  C3: total_cents returns an integer count of cents.
  C4: SAVE10 / SAVE20 are percent off subtotal; mutually exclusive.
  C5: FLAT5 takes 500 cents off; applied AFTER any percent discount.
  C6: BOGO_BAGEL: on the line with SKU "bagel", `qty // 2` bagels are free.
  C7: FREESHIP waives the flat $5.00 shipping charge, but ONLY when the
      pre-shipping total is at least $50.00 (5000 cents).
  C8: An empty cart has total 0 -- no shipping, no anything.
  C9: A non-empty cart has flat $5.00 shipping unless FREESHIP applies.
"""

import pytest
from cart import Cart


# -- C1: add_item validation ------------------------------------------------

def test_c1_qty_zero_raises_valueerror():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", 0, 1000)


def test_c1_qty_negative_raises_valueerror():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", -1, 1000)


def test_c1_negative_unit_price_raises_valueerror():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", 1, -100)


def test_c1_zero_unit_price_is_allowed():
    """Spec: unit_price_cents must be NON-NEGATIVE -- so 0 is fine."""
    cart = Cart()
    cart.add_item("freebie", 1, 0)
    # Free item, but cart is non-empty so shipping applies.
    assert cart.total_cents() == 500


def test_c1_duplicate_sku_raises_valueerror():
    """Spec C1: one line item per SKU."""
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    with pytest.raises(ValueError):
        cart.add_item("widget", 2, 500)


# -- C8: empty cart ----------------------------------------------------------

def test_c8_empty_cart_total_is_zero():
    cart = Cart()
    assert cart.total_cents() == 0


def test_c8_empty_cart_has_no_shipping():
    """An empty cart does not pay shipping."""
    cart = Cart()
    assert cart.total_cents() == 0


# -- C1/C9: basic add_item + shipping ----------------------------------------

def test_c1_single_item_adds_shipping():
    cart = Cart()
    cart.add_item("widget", 1, 1000)        # $10
    assert cart.total_cents() == 1500       # $10 + $5 shipping


def test_c1_quantity_multiplies_unit_price():
    cart = Cart()
    cart.add_item("widget", 3, 1000)        # 3 x $10 = $30
    assert cart.total_cents() == 3500       # + $5 shipping


def test_c1_multiple_skus_sum_to_subtotal_plus_shipping():
    cart = Cart()
    cart.add_item("a", 1, 1000)
    cart.add_item("b", 2, 500)              # 1000 each
    assert cart.total_cents() == 1000 + 1000 + 500


# -- C3: total_cents returns int --------------------------------------------

def test_c3_total_returns_integer():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert isinstance(cart.total_cents(), int)


def test_c3_total_with_percent_discount_is_int():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    cart.apply_code("SAVE10")
    assert isinstance(cart.total_cents(), int)


# -- C2: apply_code return type ---------------------------------------------

def test_c2_apply_code_returns_bool():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE10") is True


def test_c2_unknown_code_returns_false():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("NOPE") is False
    assert cart.apply_code("") is False


def test_c2_unknown_code_does_not_change_total():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    before = cart.total_cents()
    cart.apply_code("NOPE")
    assert cart.total_cents() == before


# -- C4: SAVE10 / SAVE20 percent off, mutually exclusive --------------------

def test_c4_save10_alone():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    # 10000 - 1000 = 9000, + 500 shipping = 9500
    assert cart.total_cents() == 9500


def test_c4_save20_alone():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    # 10000 - 2000 = 8000, + 500 shipping = 8500
    assert cart.total_cents() == 8500


def test_c4_save10_then_save20_rejects_save20():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False


def test_c4_save20_then_save10_rejects_save10():
    """Mutually exclusive must be symmetric."""
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("SAVE10") is False


def test_c4_rejected_percent_code_does_not_change_total():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("SAVE10")
    cart.apply_code("SAVE20")  # rejected
    # Should reflect SAVE10 only: 10000 - 1000 + 500 = 9500
    assert cart.total_cents() == 9500


# -- C5: FLAT5 applied after percent ----------------------------------------

def test_c5_flat5_alone():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("FLAT5") is True
    # 10000 - 500 + 500 shipping = 10000
    assert cart.total_cents() == 10000


def test_c5_flat5_stacks_with_save10():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    # subtotal 10000, -10% = 9000, -500 = 8500, + 500 shipping = 9000
    assert cart.total_cents() == 9000


def test_c5_flat5_stacks_with_save20():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("FLAT5") is True
    # 10000 - 20% = 8000, -500 = 7500, + 500 shipping = 8000
    assert cart.total_cents() == 8000


def test_c5_flat5_applied_after_percent_order_independent():
    """Whether FLAT5 is applied first or second by the user, the math result
    must be 'percent then flat', not 'flat then percent'."""
    cart_a = Cart()
    cart_a.add_item("widget", 1, 10000)
    cart_a.apply_code("FLAT5")
    cart_a.apply_code("SAVE10")

    cart_b = Cart()
    cart_b.add_item("widget", 1, 10000)
    cart_b.apply_code("SAVE10")
    cart_b.apply_code("FLAT5")

    assert cart_a.total_cents() == cart_b.total_cents() == 9000


# -- C6: BOGO_BAGEL ---------------------------------------------------------

@pytest.mark.parametrize("qty,paid", [
    (1, 1),    # qty // 2 = 0 free, 1 paid
    (2, 1),    # 1 free, 1 paid (spec example)
    (3, 2),    # 1 free, 2 paid
    (4, 2),    # 2 free, 2 paid
    (5, 3),    # 2 free, 3 paid
    (6, 3),    # 3 free, 3 paid
])
def test_c6_bogo_bagel_qty_floor_div_two_free(qty, paid):
    """Spec C3: BOGO_BAGEL gives `qty // 2` units free."""
    cart = Cart()
    cart.add_item("bagel", qty, 300)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.total_cents() == paid * 300 + 500   # paid bagels + shipping


def test_c6_bogo_only_affects_bagel_line():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.add_item("widget", 1, 1000)
    cart.apply_code("BOGO_BAGEL")
    # bagels: 1 paid (300), widget 1000, shipping 500 = 1800
    assert cart.total_cents() == 1800


# -- C7: FREESHIP ------------------------------------------------------------

def test_c7_freeship_at_exactly_50_dollars():
    """Spec example: widget at exactly $50.00 qualifies."""
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    assert cart.apply_code("FREESHIP") is True
    assert cart.total_cents() == 5000


def test_c7_freeship_above_50_dollars():
    cart = Cart()
    cart.add_item("widget", 1, 6000)
    assert cart.apply_code("FREESHIP") is True
    assert cart.total_cents() == 6000


def test_c7_freeship_below_50_does_not_waive_shipping():
    """Whether apply_code returns True or False here, the SHIPPING must still
    appear in the total for a sub-$50 cart."""
    cart = Cart()
    cart.add_item("widget", 1, 4900)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 4900 + 500


def test_c7_freeship_just_below_boundary():
    """At $49.99 (4999 cents), FREESHIP must not waive shipping."""
    cart = Cart()
    cart.add_item("widget", 1, 4999)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 4999 + 500


def test_c7_freeship_just_at_boundary_5000_qualifies():
    """At exactly 5000 cents, FREESHIP qualifies (>= $50.00)."""
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5000


def test_c7_freeship_uses_post_discount_total_for_threshold():
    """Pre-shipping means after item subtotal + percent + flat discounts,
    before the shipping line. If discounts drop the total below $50,
    FREESHIP must NOT waive shipping."""
    cart = Cart()
    cart.add_item("widget", 1, 5500)            # $55
    cart.apply_code("SAVE20")                    # -20% -> $44
    cart.apply_code("FREESHIP")
    # Pre-shipping is 4400; below $50; shipping must be charged.
    assert cart.total_cents() == 4400 + 500


def test_c7_freeship_post_discount_above_threshold():
    cart = Cart()
    cart.add_item("widget", 1, 6000)            # $60
    cart.apply_code("SAVE10")                    # -10% -> $54
    cart.apply_code("FREESHIP")                  # pre-shipping 5400 >= 5000
    assert cart.total_cents() == 5400


# -- Spec example: SAVE10 + SAVE20 reject + FLAT5 ---------------------------

def test_spec_example_two_shirt_save10_save20_flat5():
    """Reproduces the exact second example in the spec."""
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False
    assert cart.apply_code("FLAT5") is True
    # 10000 - 10% = 9000 - 500 = 8500 + 500 shipping = 9000
    assert cart.total_cents() == 9000


# -- Combination scenarios --------------------------------------------------

def test_bogo_and_save10_combine():
    cart = Cart()
    cart.add_item("bagel", 4, 1000)             # 4 x $10 = $40
    cart.apply_code("BOGO_BAGEL")                # 2 free -> $20 paid
    cart.apply_code("SAVE10")                    # -10% -> $18
    # 2000 - 200 = 1800, + 500 shipping = 2300
    assert cart.total_cents() == 2300


def test_save10_save20_freeship_flat5_freeship_above_threshold():
    cart = Cart()
    cart.add_item("widget", 1, 10000)            # $100
    cart.apply_code("SAVE10")                    # 9000
    cart.apply_code("FLAT5")                     # 8500
    cart.apply_code("FREESHIP")                  # pre-shipping 8500 >= 5000
    assert cart.total_cents() == 8500


# -- Idempotence / repeated codes (only for codes with clear spec) ----------

def test_c4_same_percent_code_twice_does_not_double_discount():
    """Spec C2: same code twice returns False (already applied)."""
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE10") is False
    # Must not be 8000 (double 10%); should be 9000 + 500 shipping = 9500.
    assert cart.total_cents() == 9500


def test_c2_flat5_already_applied_returns_false():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FLAT5") is False


def test_c2_bogo_already_applied_returns_false():
    cart = Cart()
    cart.add_item("bagel", 4, 300)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("BOGO_BAGEL") is False


def test_c2_freeship_already_applied_returns_false():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("FREESHIP") is True
    assert cart.apply_code("FREESHIP") is False


def test_c2_case_sensitive_code_rejected():
    """Spec C2: codes are case-sensitive."""
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("save10") is False
    assert cart.apply_code("Save10") is False
    assert cart.apply_code("SAVE10") is True       # exact case wins


# -- C3: BOGO with no bagel still counts as applied -------------------------

def test_c3_bogo_with_no_bagel_returns_true_no_effect():
    """Spec C3: if no bagel line item exists, code has no effect but is still
    'applied' for the duplicate-application rule."""
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    # Total unaffected: 1000 + 500 shipping
    assert cart.total_cents() == 1500


def test_c3_bogo_no_bagel_then_second_bogo_returns_false():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("BOGO_BAGEL") is False


def test_c3_bogo_applied_before_bagel_added_still_works():
    """Spec C3: 'if no bagel exists when total_cents is computed' --
    implying lazy evaluation. So applying BOGO before adding bagels still
    works at compute time."""
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    cart.apply_code("BOGO_BAGEL")
    cart.add_item("bagel", 2, 300)
    # Subtotal 1000 + 600 = 1600. BOGO: -300. Post-BOGO 1300. + shipping 500 = 1800.
    assert cart.total_cents() == 1800


# -- C6: banker's rounding (ROUND_HALF_EVEN) on percent discounts -----------

@pytest.mark.parametrize("subtotal,code,paid_after_discount,note", [
    # No rounding needed -- baseline sanity.
    (100,  "SAVE10",  90, "exact 10%"),
    (125,  "SAVE20", 100, "exact 20%"),
    # Banker's rounding at .5 -- four pinning cases.
    # 10% of 25 = 2.5  -> rounds to 2 (even)   round-up bug fails here
    ( 25,  "SAVE10",  23, "2.5 -> 2"),
    # 10% of 35 = 3.5  -> rounds to 4 (even)   floor-rounding bug fails here
    ( 35,  "SAVE10",  31, "3.5 -> 4"),
    # 10% of 105 = 10.5 -> rounds to 10 (even)
    (105,  "SAVE10",  95, "10.5 -> 10"),
    # 10% of 115 = 11.5 -> rounds to 12 (even)
    (115,  "SAVE10", 103, "11.5 -> 12"),
])
def test_c6_percent_uses_banker_rounding(subtotal, code, paid_after_discount, note):
    """Spec C6: percent discounts round half-even (ROUND_HALF_EVEN)."""
    cart = Cart()
    cart.add_item("widget", 1, subtotal)
    cart.apply_code(code)
    assert cart.total_cents() == paid_after_discount + 500


# -- C5: precise application order ------------------------------------------

def test_c5_bogo_then_save_then_flat_then_freeship_order():
    """Subtotal 4 bagels at $20 = 8000. BOGO: -4000 = 4000. SAVE10: 3600.
    FLAT5: 3100. Pre-shipping 3100 < 5000, so FREESHIP cannot waive.
    Total = 3100 + 500 = 3600."""
    cart = Cart()
    cart.add_item("bagel", 4, 2000)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 3600


def test_c5_flat5_clamps_at_zero():
    """Spec C5 step 4: clamp at 0. Subtotal 100, FLAT5 -> max(0, 100-500) = 0.
    + shipping 500 = 500."""
    cart = Cart()
    cart.add_item("widget", 1, 100)
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 0 + 500


def test_c5_freeship_uses_post_flat5_total():
    """Pre-shipping for FREESHIP threshold is post-FLAT5.
    Subtotal 5400, FLAT5 -> 4900 (below 5000). FREESHIP cannot waive.
    Total = 4900 + 500 = 5400."""
    cart = Cart()
    cart.add_item("widget", 1, 5400)
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5400


def test_c5_freeship_post_flat5_at_exact_5000_qualifies():
    """Subtotal 5500, FLAT5 -> 5000 (exactly). FREESHIP qualifies (>= 5000)."""
    cart = Cart()
    cart.add_item("widget", 1, 5500)
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5000


# -- Adding items after applying code ---------------------------------------

def test_add_item_after_apply_code_still_discounted():
    """Spec doesn't say discount applies only to items present at apply time;
    most natural reading is total_cents recomputes from current state."""
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    cart.apply_code("SAVE10")
    cart.add_item("gadget", 1, 5000)
    # Subtotal 10000, -10% = 9000, + 500 shipping = 9500
    assert cart.total_cents() == 9500


# -- Boundary on FLAT5: cart smaller than $5 --------------------------------

def test_flat5_does_not_make_total_negative_for_pre_shipping():
    """If items total $1 and FLAT5 is applied, the line discount can't
    create a negative subtotal. Total should be no less than the shipping
    portion (or zero)."""
    cart = Cart()
    cart.add_item("widget", 1, 100)             # $1
    cart.apply_code("FLAT5")
    # Either: (max(0, 100 - 500)) + shipping = 0 + 500 = 500
    # or: subtotal can't go negative, treated as 0.
    assert cart.total_cents() >= 0
    assert cart.total_cents() <= 500
