"""Phase 1 tests for `cart` module.

Tests are organized clause-by-clause against starter/assignment3/specs/cart.md.
Each test name encodes the clause it pins down (e.g. test_c5_order_bogo_before_percent).

All amounts are integer cents per spec.
"""
from decimal import Decimal, ROUND_HALF_EVEN
import pytest

from cart import Cart


def _half_even_percent(amount: int, percent: int) -> int:
    """Banker's-rounded percent discount amount, in cents.

    Mirrors C6's `decimal.ROUND_HALF_EVEN`. Used to compute expected values
    for percent-discount tests so we never eyeball a half-cent rounding.
    """
    raw = Decimal(amount) * Decimal(percent) / Decimal(100)
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


# ---------------------------------------------------------------------------
# C1. add_item validation.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_qty", [0, -1, -100])
def test_c1_qty_must_be_positive(bad_qty):
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", bad_qty, 1000)


@pytest.mark.parametrize("bad_price", [-1, -500])
def test_c1_unit_price_must_be_nonnegative(bad_price):
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", 1, bad_price)


def test_c1_zero_unit_price_accepted():
    # Non-negative includes 0 — a free promo item should be addable.
    cart = Cart()
    cart.add_item("freebie", 1, 0)
    assert cart.total_cents() == 500              # cart non-empty → shipping


def test_c1_empty_string_sku_is_still_a_line_item():
    # Spec constrains duplicate SKUs but does not impose SKU truthiness.
    cart = Cart()
    cart.add_item("", 1, 1000)
    assert cart.total_cents() == 1500
    with pytest.raises(ValueError):
        cart.add_item("", 1, 1000)


def test_c1_duplicate_sku_raises():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    with pytest.raises(ValueError):
        cart.add_item("widget", 2, 500)


def test_c1_invalid_qty_does_not_reserve_sku_or_add_line():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", 0, 1000)

    assert cart.total_cents() == 0
    cart.add_item("widget", 1, 1000)
    assert cart.total_cents() == 1500


def test_c1_invalid_price_does_not_reserve_sku_or_add_line():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", 1, -1)

    assert cart.total_cents() == 0
    cart.add_item("widget", 1, 1000)
    assert cart.total_cents() == 1500


def test_c1_duplicate_sku_does_not_replace_original_line():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    with pytest.raises(ValueError):
        cart.add_item("widget", 5, 1)

    assert cart.total_cents() == 1500


# ---------------------------------------------------------------------------
# C2. apply_code contract.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code", ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"])
def test_c2_known_code_returns_true(code):
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code(code) is True


@pytest.mark.parametrize("code", ["UNKNOWN", "SAVE15", "save10", "Save10", "SAVE_10", ""])
def test_c2_unknown_or_wrong_case_returns_false(code):
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code(code) is False


def test_c2_duplicate_application_returns_false():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FLAT5") is False


def test_c2_duplicate_bogo_returns_false_even_without_bagel():
    # Spec C3 makes this explicit: BOGO_BAGEL is "considered applied" even
    # when no bagel line item exists. So the second apply must return False.
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("BOGO_BAGEL") is False


@pytest.mark.parametrize("code", ["SAVE10", "SAVE20", "FREESHIP"])
def test_c2_duplicate_percent_or_freeship_returns_false(code):
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code(code) is True
    assert cart.apply_code(code) is False


def test_c2_unknown_code_does_not_block_later_valid_code():
    cart = Cart()
    cart.add_item("widget", 1, 10000)

    assert cart.apply_code("save10") is False
    assert cart.apply_code("SAVE10") is True
    assert cart.total_cents() == 9500


# ---------------------------------------------------------------------------
# C3. Each known code's individual effect.
# ---------------------------------------------------------------------------

def test_c3_save10_takes_ten_percent_off_subtotal():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("SAVE10")
    # 10000 - 1000 = 9000, plus 500 shipping = 9500
    assert cart.total_cents() == 9500


def test_c3_save20_takes_twenty_percent_off_subtotal():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("SAVE20")
    # 10000 - 2000 = 8000, plus 500 shipping = 8500
    assert cart.total_cents() == 8500


def test_c3_flat5_takes_500_off():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("FLAT5")
    # 10000 - 500 = 9500, plus 500 shipping = 10000
    assert cart.total_cents() == 10000


def test_c3_bogo_bagel_frees_half_rounded_down():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    # qty // 2 = 1 free; 1 paid * 300 = 300, plus 500 shipping = 800
    assert cart.total_cents() == 800


def test_c3_bogo_bagel_qty1_zero_free():
    cart = Cart()
    cart.add_item("bagel", 1, 300)
    cart.apply_code("BOGO_BAGEL")
    # 1 // 2 = 0 free; 300 + 500 shipping = 800
    assert cart.total_cents() == 800


def test_c3_bogo_bagel_qty3_one_free():
    cart = Cart()
    cart.add_item("bagel", 3, 300)
    cart.apply_code("BOGO_BAGEL")
    # 3 // 2 = 1 free; 2 paid * 300 = 600, plus 500 = 1100
    assert cart.total_cents() == 1100


def test_c3_bogo_bagel_no_bagel_line_no_effect_but_applied():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    # No bagel → no discount; 1000 + 500 shipping = 1500
    assert cart.total_cents() == 1500


def test_c3_freeship_waives_shipping_when_above_threshold():
    cart = Cart()
    cart.add_item("widget", 1, 5000)              # exactly $50.00
    cart.apply_code("FREESHIP")
    # Pre-shipping = 5000, threshold met (>= 5000), shipping waived
    assert cart.total_cents() == 5000


def test_c3_freeship_does_not_waive_below_threshold():
    cart = Cart()
    cart.add_item("widget", 1, 4999)
    cart.apply_code("FREESHIP")
    # Pre-shipping = 4999, threshold NOT met, shipping still added
    assert cart.total_cents() == 4999 + 500


# ---------------------------------------------------------------------------
# C4. Stacking rules.
# ---------------------------------------------------------------------------

def test_c4_save10_and_save20_mutually_exclusive():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False
    # SAVE10 takes effect (the first one), not SAVE20
    assert cart.total_cents() == 9000 + 500


def test_c4_save20_then_save10_first_one_takes_effect():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("SAVE10") is False
    # SAVE20 first → takes effect: 10000 - 2000 = 8000, +500 = 8500
    assert cart.total_cents() == 8500


def test_c4_flat5_stacks_with_save10():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    # 10000 - 1000 (SAVE10) - 500 (FLAT5) = 8500, + 500 shipping = 9000
    assert cart.total_cents() == 9000


def test_c4_freeship_stacks_with_everything():
    cart = Cart()
    cart.add_item("bagel", 4, 2000)               # subtotal 8000
    assert cart.apply_code("BOGO_BAGEL") is True  # 2 free → 4000
    assert cart.apply_code("SAVE10") is True      # 4000 - 400 = 3600
    assert cart.apply_code("FLAT5") is True       # 3600 - 500 = 3100
    assert cart.apply_code("FREESHIP") is True
    # Pre-shipping = 3100 < 5000, FREESHIP applied but condition not met → shipping added
    assert cart.total_cents() == 3100 + 500


# ---------------------------------------------------------------------------
# C5. Application order in total_cents.
# ---------------------------------------------------------------------------

def test_c5_order_bogo_before_percent():
    # 4 bagels at 1000: subtotal=4000. BOGO frees 2 → 2000. SAVE10 → 1800. +500 = 2300.
    # If percent ran BEFORE BOGO: 4000 * 0.9 = 3600, then BOGO -2000 = 1600 + 500 = 2100.
    # Different total — this test pins down BOGO-then-percent.
    cart = Cart()
    cart.add_item("bagel", 4, 1000)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 2300


def test_c5_order_flat5_after_percent():
    # 1 shirt at 10000. SAVE10 → 9000. FLAT5 → 8500. +500 = 9000.
    # If FLAT5 ran BEFORE percent: 9500 * 0.9 = 8550 + 500 = 9050. Different.
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 9000


def test_c5_flat5_clamps_at_zero_when_exceeds_subtotal():
    cart = Cart()
    cart.add_item("cheap", 1, 100)                # subtotal 100
    cart.apply_code("FLAT5")                      # 100 - 500 → clamp at 0
    # Pre-shipping = 0, < 5000, no FREESHIP, cart non-empty → shipping 500
    assert cart.total_cents() == 500


def test_c5_freeship_threshold_uses_post_discount_subtotal():
    # FREESHIP threshold is "post-discount pre-shipping subtotal >= 5000".
    # If percent puts pre-shipping below 5000, FREESHIP must NOT waive.
    cart = Cart()
    cart.add_item("widget", 1, 5500)              # raw subtotal 5500 (>= 5000)
    cart.apply_code("SAVE20")                     # 5500 - 1100 = 4400 (< 5000)
    cart.apply_code("FREESHIP")
    # Pre-shipping = 4400, FREESHIP threshold not met → shipping added
    assert cart.total_cents() == 4400 + 500


def test_c5_full_stack_order_check():
    # All four discount codes stacked, on a bagel-line cart.
    # subtotal = 6 * 1500 = 9000
    # BOGO: 6 // 2 = 3 free → 3 paid * 1500 = 4500
    # SAVE20: 4500 * 0.80 = 3600 (no rounding needed; exact)
    # FLAT5: 3600 - 500 = 3100
    # Pre-shipping = 3100 < 5000, FREESHIP applied but not effective → shipping 500
    # Total = 3600
    cart = Cart()
    cart.add_item("bagel", 6, 1500)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE20")
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 3600


# ---------------------------------------------------------------------------
# C6. Banker's rounding (ROUND_HALF_EVEN) on percent discounts.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("subtotal,percent_code,percent", [
    (125, "SAVE10", 10),     # 12.5 → 12 (even); post-percent 113
    (175, "SAVE10", 10),     # 17.5 → 18 (even); post-percent 157
    (225, "SAVE10", 10),     # 22.5 → 22 (even); post-percent 203
    (275, "SAVE10", 10),     # 27.5 → 28 (even); post-percent 247
    (125, "SAVE20", 20),     # 25.0 → 25 (exact); post-percent 100
    (375, "SAVE20", 20),     # 75.0 → 75 (exact); post-percent 300
    (62,  "SAVE20", 20),     # 12.4 → 12 (not half); post-percent 50
    (63,  "SAVE20", 20),     # 12.6 → 13 (not half); post-percent 50
])
def test_c6_banker_rounding_on_percent(subtotal, percent_code, percent):
    cart = Cart()
    cart.add_item("widget", 1, subtotal)
    cart.apply_code(percent_code)
    expected_discount = _half_even_percent(subtotal, percent)
    expected_total = (subtotal - expected_discount) + 500   # plus shipping
    assert cart.total_cents() == expected_total


# ---------------------------------------------------------------------------
# C7. Empty cart total is 0 regardless of codes.
# ---------------------------------------------------------------------------

def test_c7_empty_cart_total_zero():
    assert Cart().total_cents() == 0


def test_c7_empty_cart_with_codes_still_zero():
    cart = Cart()
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 0


def test_c7_empty_cart_no_shipping_added():
    # Distinct from "total is 0" — pin down that no shipping is added even
    # though shipping is the default for non-empty carts.
    cart = Cart()
    assert cart.total_cents() == 0


# ===========================================================================
# Implication pass — spec-implied edge cases.
# ===========================================================================

# Boundary lens -------------------------------------------------------------

def test_freeship_threshold_just_above_5000():
    # Symmetric to the at-5000 test: 5001 must waive too.
    cart = Cart()
    cart.add_item("widget", 1, 5001)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5001


def test_freeship_threshold_at_5000_via_flat5_reduction():
    # Pre-shipping reaches exactly 5000 only after FLAT5 takes effect:
    # subtotal 5500 → FLAT5 → 5000. >= 5000, FREESHIP waives.
    cart = Cart()
    cart.add_item("widget", 1, 5500)
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5000


def test_flat5_clamp_to_zero_does_not_make_freeship_effective():
    # FREESHIP checks the clamped pre-shipping total from C5 step 4.
    # Zero is below 5000, so a non-empty cart still pays shipping.
    cart = Cart()
    cart.add_item("cheap", 1, 100)
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 500


def test_bogo_with_large_qty():
    # qty=10 → 5 free, 5 paid.
    cart = Cart()
    cart.add_item("bagel", 10, 200)            # 2000 subtotal
    cart.apply_code("BOGO_BAGEL")
    # 5 paid * 200 = 1000, +500 shipping = 1500
    assert cart.total_cents() == 1500


# Absence lens --------------------------------------------------------------

@pytest.mark.parametrize("code", ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"])
def test_apply_code_on_empty_cart_returns_true(code):
    # No items doesn't disqualify a known code from being "applied" — the
    # contract for apply_code is purely about code validity / duplicates /
    # conflicts (C2). Empty cart isn't a disqualifier.
    cart = Cart()
    assert cart.apply_code(code) is True


# Interaction lens ----------------------------------------------------------

def test_apply_order_independence_for_freeship_evaluation():
    # FREESHIP is applied FIRST, then percent + FLAT5 drop pre-shipping below
    # 5000. The waiver condition is evaluated at total_cents time on the
    # post-discount pre-shipping subtotal, not at apply_code time.
    cart = Cart()
    cart.add_item("widget", 1, 5500)
    cart.apply_code("FREESHIP")               # applied early
    cart.apply_code("SAVE20")                 # 5500 → 4400 (< 5000)
    # FREESHIP threshold not met at evaluation time → shipping added
    assert cart.total_cents() == 4400 + 500


def test_total_cents_is_idempotent():
    # Calling total_cents twice returns the same value. Catches an impl that
    # mutates state during calculation (e.g., consumes BOGO discount once).
    cart = Cart()
    cart.add_item("bagel", 4, 1000)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    first = cart.total_cents()
    second = cart.total_cents()
    assert first == second


def test_bogo_only_affects_bagel_line_other_items_full_price():
    # BOGO targets the bagel line specifically. Other line items pay full.
    cart = Cart()
    cart.add_item("bagel", 4, 500)            # 2000 — BOGO frees 2 → 1000
    cart.add_item("widget", 2, 1000)          # 2000 — full price
    cart.apply_code("BOGO_BAGEL")
    # Subtotal after BOGO: 1000 + 2000 = 3000, +500 shipping = 3500
    assert cart.total_cents() == 3500


def test_bogo_applied_before_bagel_added_takes_effect():
    # C3 says BOGO has no effect "when total_cents is computed" if no bagel
    # exists. Implication: the discount is evaluated at total_cents time, so
    # adding the bagel AFTER the apply_code still triggers the discount.
    cart = Cart()
    cart.apply_code("BOGO_BAGEL")             # applied to empty cart
    cart.add_item("bagel", 2, 300)            # bagel added afterwards
    # 2//2 = 1 free; 1 paid * 300 = 300, +500 shipping = 800
    assert cart.total_cents() == 800


def test_save10_then_flat5_then_freeship_with_threshold_not_met():
    # All four codes that *can* stack with SAVE10, in mixed apply order.
    # subtotal 4000 → SAVE10 = 400 off → 3600 → FLAT5 → 3100. <5000.
    # FREESHIP applied but threshold not met → shipping added.
    cart = Cart()
    cart.add_item("widget", 1, 4000)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 3100 + 500


@pytest.mark.parametrize("qty,expected_paid", [
    (5, 3),     # 5 // 2 = 2 free, 3 paid
    (7, 4),     # 7 // 2 = 3 free, 4 paid
    (8, 4),     # 8 // 2 = 4 free, 4 paid
])
def test_bogo_qty_floor_division(qty, expected_paid):
    cart = Cart()
    cart.add_item("bagel", qty, 200)
    cart.apply_code("BOGO_BAGEL")
    # paid * 200 + 500 shipping
    assert cart.total_cents() == expected_paid * 200 + 500


def test_freeship_threshold_uses_post_flat5_subtotal_not_post_percent():
    # Distinguishes the post-FLAT5 reading (correct per C5 step 5) from a bug
    # using the post-percent pre-FLAT5 reading.
    # subtotal=5600. SAVE10 → 5040. FLAT5 → 4540. Pre-shipping = 4540 < 5000.
    # Per spec: shipping added → 4540 + 500 = 5040.
    # Per "uses post-percent" bug: 5040 >= 5000, waive shipping → 4540.
    cart = Cart()
    cart.add_item("widget", 1, 5600)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5040


def test_percent_applies_to_full_post_bogo_subtotal_in_mixed_cart():
    # Multi-line cart: bagel + widget. BOGO frees 2 bagels. SAVE10 then
    # applies to the post-BOGO TOTAL (not just the bagel line, not just
    # the widget line).
    # bagel: 4 * 500 = 2000. widget: 1 * 1000 = 1000. subtotal = 3000.
    # BOGO: 2 bagels free → 2000 (1000 paid bagel + 1000 widget).
    # SAVE10: 200 off → 1800. +500 shipping = 2300.
    cart = Cart()
    cart.add_item("bagel", 4, 500)
    cart.add_item("widget", 1, 1000)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 2300


def test_apply_order_flat5_then_save10_same_as_save10_then_flat5():
    # Apply-order independence: total_cents evaluates per C5's fixed order
    # regardless of apply_code call order.
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    cart.apply_code("FLAT5")                  # applied first
    cart.apply_code("SAVE10")                 # applied second
    # Per C5: SAVE10 → 9000, FLAT5 → 8500, +500 = 9000 (same as reverse order).
    assert cart.total_cents() == 9000


def test_save10_on_zero_subtotal_cart():
    # Free-item cart: subtotal = 0. SAVE10 applies 0% off 0 = 0.
    # Cart non-empty → +500 shipping. Total = 500.
    cart = Cart()
    cart.add_item("freebie", 1, 0)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 500


@pytest.mark.parametrize("bad_qty", [1.5, "2", None])
def test_c1_qty_must_be_integer_not_bool_or_other_types(bad_qty):
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", bad_qty, 1000)


@pytest.mark.parametrize("bad_price", [9.99, "100", None])
def test_c1_unit_price_must_be_integer_not_bool_or_other_types(bad_price):
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", 1, bad_price)


@pytest.mark.parametrize(
    "subtotal, expected",
    [
        (4999, 5499),  # below threshold -> shipping charged
        (5000, 5000),  # threshold met -> shipping waived
        (5001, 5001),  # above threshold -> shipping waived
    ],
)
def test_freeship_threshold_boundary_table(subtotal, expected):
    cart = Cart()
    cart.add_item("widget", 1, subtotal)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == expected


def test_total_cents_stable_after_rejected_code_attempts():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False  # conflict
    assert cart.apply_code("SAVE20") is False  # still rejected
    assert cart.apply_code("UNKNOWN") is False

    first = cart.total_cents()
    second = cart.total_cents()
    assert first == second == 9500


def test_bogo_can_drop_below_freeship_threshold():
    cart = Cart()
    cart.add_item("bagel", 4, 2500)   # subtotal 10000
    cart.apply_code("BOGO_BAGEL")      # subtotal 5000
    cart.apply_code("SAVE10")          # subtotal 4500
    cart.apply_code("FREESHIP")
    # FREESHIP checks post-discount pre-shipping subtotal (4500), so shipping applies.
    assert cart.total_cents() == 5000


def test_rounding_can_affect_freeship_threshold_decision():
    cart = Cart()
    cart.add_item("widget", 1, 5555)
    cart.apply_code("SAVE10")          # 555.5 rounds half-even to 556 -> 4999
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5499


def test_sku_case_distinct_lines_allowed():
    cart = Cart()
    cart.add_item("bagel", 1, 300)
    cart.add_item("BAGEL", 1, 300)
    # BOGO targets exact sku "bagel" only; here we just assert distinct line acceptance.
    assert cart.total_cents() == 1100


def test_code_application_order_does_not_change_total_when_valid():
    c1 = Cart()
    c1.add_item("bagel", 6, 1000)
    for code in ["BOGO_BAGEL", "SAVE10", "FLAT5", "FREESHIP"]:
        c1.apply_code(code)

    c2 = Cart()
    c2.add_item("bagel", 6, 1000)
    for code in ["FREESHIP", "FLAT5", "SAVE10", "BOGO_BAGEL"]:
        c2.apply_code(code)

    assert c1.total_cents() == c2.total_cents()


def test_code_application_order_independence_non_bagel_stack():
    c1 = Cart()
    c1.add_item("widget", 1, 10000)
    for code in ["SAVE20", "FLAT5", "FREESHIP"]:
        c1.apply_code(code)

    c2 = Cart()
    c2.add_item("widget", 1, 10000)
    for code in ["FREESHIP", "FLAT5", "SAVE20"]:
        c2.apply_code(code)

    assert c1.total_cents() == c2.total_cents() == 7500


def test_rejected_conflicting_percent_codes_are_noop_on_total():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    baseline = cart.total_cents()

    # Rejected conflicts should not alter applied state or computed total.
    assert cart.apply_code("SAVE20") is False
    assert cart.apply_code("SAVE20") is False
    assert cart.total_cents() == baseline == 9500


def test_bogo_targets_exact_lowercase_bagel_sku_only():
    cart = Cart()
    cart.add_item("bagel", 2, 300)   # BOGO should discount this line
    cart.add_item("Bagel", 2, 300)   # should not be discounted by BOGO_BAGEL
    cart.apply_code("BOGO_BAGEL")
    # lowercase bagel: 2 -> 1 paid = 300
    # uppercase Bagel: full 600
    # pre-shipping 900, plus shipping 500
    assert cart.total_cents() == 1400


def test_total_cents_reflects_code_applied_after_first_total():
    # total_cents is a calculation, not a one-time cached total.
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.total_cents() == 10500

    assert cart.apply_code("SAVE10") is True
    assert cart.total_cents() == 9500


def test_total_cents_reflects_item_added_after_first_total():
    cart = Cart()
    assert cart.total_cents() == 0

    cart.add_item("widget", 1, 1000)
    assert cart.total_cents() == 1500


def test_codes_applied_before_items_affect_later_total():
    # C2 allows known codes on an empty cart; C5 computes total from current
    # items plus applied codes when total_cents is called.
    cart = Cart()
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True

    cart.add_item("shirt", 1, 10000)
    # 10000 -> SAVE10 = 9000 -> FLAT5 = 8500 -> FREESHIP waives shipping.
    assert cart.total_cents() == 8500


def test_duplicate_flat5_is_noop_for_total():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FLAT5") is False

    assert cart.total_cents() == 10000


def test_duplicate_bogo_is_noop_for_total():
    cart = Cart()
    cart.add_item("bagel", 4, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("BOGO_BAGEL") is False

    # One BOGO application: 4 bagels -> 2 paid, plus shipping.
    assert cart.total_cents() == 2500


def test_bogo_can_land_exactly_on_freeship_threshold():
    cart = Cart()
    cart.add_item("bagel", 4, 2500)   # raw subtotal 10000
    cart.apply_code("BOGO_BAGEL")     # 2 free -> pre-shipping 5000
    cart.apply_code("FREESHIP")

    assert cart.total_cents() == 5000
