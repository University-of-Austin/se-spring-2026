"""Tests for cart module, organized by spec clause."""
import pytest
from cart import Cart


# --- C1: add_item validation ---

@pytest.mark.parametrize("qty,unit_price", [
    (1, 0),         # zero unit_price is valid (free items)
    (1, 1000),      # standard
    (10, 250),      # multiple qty
])
def test_c1_valid_add_item_does_not_raise(qty, unit_price):
    """Valid qty (>=1) and unit_price (>=0) must not raise. Boundary check on
    unit_price=0: catches a too-aggressive `if price <= 0: raise` that would
    incorrectly reject free items."""
    cart = Cart()
    cart.add_item("widget", qty, unit_price)


@pytest.mark.parametrize("bad_qty", [0, -1, -100])
def test_c1_invalid_qty_raises(bad_qty):
    """qty must be a positive integer (>=1). Zero or negative raises ValueError."""
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", bad_qty, 100)


@pytest.mark.parametrize("bad_price", [-1, -500])
def test_c1_invalid_unit_price_raises(bad_price):
    """unit_price_cents must be non-negative. Negative raises ValueError."""
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", 1, bad_price)


def test_c1_duplicate_sku_raises():
    """Adding the same sku twice raises — one line item per SKU. Catches a bug
    where the impl silently overwrites the first add or appends a duplicate
    line item that double-counts in the total."""
    cart = Cart()
    cart.add_item("widget", 1, 100)
    with pytest.raises(ValueError):
        cart.add_item("widget", 2, 200)


def test_c1_different_skus_coexist():
    """Two distinct SKUs are added independently and both contribute to total.
    Sanity check that the per-SKU restriction doesn't break multi-item carts."""
    cart = Cart()
    cart.add_item("widget", 1, 100)
    cart.add_item("gadget", 2, 200)
    # subtotal = 100 + 400 = 500; + 500 shipping = 1000
    assert cart.total_cents() == 1000


# --- C2: apply_code return values ---

@pytest.mark.parametrize("code", ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"])
def test_c2_known_code_returns_true(code):
    """Every spec-listed code must be accepted on first application. Strict bool
    check — an impl that returns truthy non-bool would slip past `assert result`."""
    cart = Cart()
    cart.add_item("widget", 1, 100)
    assert cart.apply_code(code) is True


@pytest.mark.parametrize("code", ["BOGUS", "save10", "SAVE", ""])
def test_c2_unknown_or_wrong_case_returns_false(code):
    """Unknown codes, wrong-case variants, partial matches, and the empty string
    all return False. Pins case-sensitivity along with unknown-rejection."""
    cart = Cart()
    cart.add_item("widget", 1, 100)
    assert cart.apply_code(code) is False


def test_c2_duplicate_application_returns_false():
    """Applying the same code twice: first returns True, second returns False.
    Catches a bug where the impl re-applies (or doesn't track applied codes)."""
    cart = Cart()
    cart.add_item("widget", 1, 100)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE10") is False


# --- C3: Known codes (each in isolation) ---

@pytest.mark.parametrize("code,percent", [("SAVE10", 10), ("SAVE20", 20)])
def test_c3_save_codes_apply_percent(code, percent):
    """SAVE10 / SAVE20 take their named percent off the subtotal. Subtotal 10000
    is evenly divisible to avoid rounding noise (rounding is C6's territory)."""
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code(code)
    discount = 10000 * percent // 100
    expected = (10000 - discount) + 500       # post-discount + shipping
    assert cart.total_cents() == expected


@pytest.mark.parametrize("subtotal,expected", [
    (1000, 1000),     # 1000 - 500 = 500 (pre-ship) + 500 ship = 1000
    (100,   500),     # 100  - 500 = -400 → clamp 0 + 500 ship = 500
])
def test_c3_flat5_subtracts_500_with_clamp(subtotal, expected):
    """FLAT5 subtracts 500 cents. If that would make the pre-shipping total
    negative, the spec mandates clamping at 0. The 100-cent case exercises the
    clamp; the 1000-cent case exercises the normal subtraction path."""
    cart = Cart()
    cart.add_item("widget", 1, subtotal)
    cart.apply_code("FLAT5")
    assert cart.total_cents() == expected


@pytest.mark.parametrize("qty,paid_qty", [
    (1, 1),   # 1//2 = 0 free, 1 paid
    (2, 1),   # 1 free, 1 paid (PDF example)
    (3, 2),   # 1 free, 2 paid (odd quantity)
    (4, 2),   # 2 free, 2 paid (even higher)
])
def test_c3_bogo_bagel_qty_floor_div_2_free(qty, paid_qty):
    """BOGO_BAGEL gives `qty // 2` bagels free. Catches a bug using float division
    (qty/2) or integer-off-by-one (qty - 1). Boundary cases at odd quantities
    are where the floor-division semantic actually matters."""
    cart = Cart()
    cart.add_item("bagel", qty, 300)
    cart.apply_code("BOGO_BAGEL")
    expected = paid_qty * 300 + 500           # paid bagels + shipping
    assert cart.total_cents() == expected


def test_c3_bogo_bagel_with_no_bagel_returns_true_no_effect():
    """When BOGO_BAGEL is applied to a cart without a bagel line item, the spec
    says the code is still 'applied' (for C2 duplicate-tracking) but has no
    effect on the total. Catches a bug returning False, and a bug discounting
    the wrong sku."""
    cart = Cart()
    cart.add_item("widget", 1, 100)
    assert cart.apply_code("BOGO_BAGEL") is True   # applied for tracking
    assert cart.apply_code("BOGO_BAGEL") is False  # second call rejected (C2)
    assert cart.total_cents() == 600               # unchanged: 100 + 500 shipping


def test_c3_bogo_bagel_only_discounts_bagel_in_mixed_cart():
    """BOGO_BAGEL applies ONLY to the 'bagel' sku, not to other line items in a
    mixed cart. Trace: 2 bagels @ 300 + 1 widget @ 1000.
    Subtotal: 600 + 1000 = 1600 → BOGO (-300 for 1 free bagel) = 1300 → +500 ship.
    Catches a bug where BOGO discounts the entire subtotal or the wrong sku."""
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.add_item("widget", 1, 1000)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 1800


@pytest.mark.parametrize("subtotal,expected", [
    (4999, 5499),     # < 5000: shipping NOT waived; 4999 + 500
    (5000, 5000),     # exactly at threshold: waived (>=)
    (5001, 5001),     # > 5000: waived
])
def test_c3_freeship_threshold(subtotal, expected):
    """FREESHIP waives shipping when post-discount pre-shipping is >= 5000.
    Pins the boundary at exactly 5000 — catches a strict `>` off-by-one."""
    cart = Cart()
    cart.add_item("widget", 1, subtotal)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == expected


# --- C4: Stacking rules ---

@pytest.mark.parametrize("first,second", [
    ("SAVE10", "SAVE20"),
    ("SAVE20", "SAVE10"),
])
def test_c4_save_codes_mutually_exclusive(first, second):
    """SAVE10 and SAVE20 are mutually exclusive in both directions: applying one
    then the other returns False on the second call."""
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code(first) is True
    assert cart.apply_code(second) is False


def test_c4_first_save_code_takes_effect():
    """When SAVE10 is applied and SAVE20 is rejected, only SAVE10's discount is
    visible in the total. Pins 'only the first takes effect' via observable
    consequence — catches a bug where the rejected SAVE20 silently overrides."""
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("SAVE10")          # True
    cart.apply_code("SAVE20")          # False — must not override
    # total reflects SAVE10 (10% off), not SAVE20 (20% off): 9000 + 500 ship
    assert cart.total_cents() == 9500


@pytest.mark.parametrize("first,second", [
    ("SAVE10", "FLAT5"),
    ("SAVE20", "FLAT5"),
    ("SAVE10", "BOGO_BAGEL"),
    ("SAVE20", "BOGO_BAGEL"),
    ("FLAT5", "BOGO_BAGEL"),
    ("BOGO_BAGEL", "FREESHIP"),
    ("SAVE10", "FREESHIP"),
    ("SAVE20", "FREESHIP"),
    ("FLAT5", "FREESHIP"),
])
def test_c4_stacking_pairs_both_return_true(first, second):
    """Every non-mutex pair of codes stacks: both applies return True. Covers
    all 9 stacking pairs the spec calls out (FLAT5 with either save, BOGO with
    everyone, FREESHIP with everyone)."""
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code(first) is True
    assert cart.apply_code(second) is True


def test_c4_maximum_stack_all_four_apply():
    """The maximum stack: one percent code + FLAT5 + BOGO + FREESHIP. All four
    apply_code calls return True, confirming the impl doesn't have an arbitrary
    cap on stacked codes — a bug pair-wise tests would miss."""
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("FREESHIP") is True


@pytest.mark.parametrize("codes", [
    ("SAVE20", "FLAT5", "BOGO_BAGEL"),         # SAVE20-anchored (4-code uses SAVE10)
    ("SAVE20", "FLAT5", "FREESHIP"),           # SAVE20 + non-BOGO codes
    ("FLAT5", "BOGO_BAGEL", "FREESHIP"),       # no percent code at all
])
def test_c4_three_code_stacks(codes):
    """Representative 3-code combinations all return True. Catches bugs the
    pair-wise tests might miss (e.g. impl caps at 2 codes) without overlapping
    with the 4-code maximum-stack test."""
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    for code in codes:
        assert cart.apply_code(code) is True


# --- C5: Application order for total_cents ---

def test_c5_bogo_applied_before_percent():
    """Pins step 2 → step 3 order. Trace: 2 bagels @ 1000 = 2000 subtotal.
    Correct: 2000 → BOGO (1 free, -1000) = 1000 → SAVE10 (10% off) = 900 → +500 ship.
    Bug (percent first): 2000 → SAVE10 = 1800 → BOGO -1000 = 800 → +500 = 1300."""
    cart = Cart()
    cart.add_item("bagel", 2, 1000)
    cart.apply_code("SAVE10")
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 1400      # 900 + 500 shipping


def test_c5_percent_applied_before_flat5():
    """Pins step 3 → step 4 order. PDF canonical example.
    Correct: 10000 → SAVE10 = 9000 → FLAT5 = 8500 → +500 ship = 9000.
    Bug (FLAT5 first): 10000 → FLAT5 = 9500 → SAVE10 = 8550 → +500 = 9050."""
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 9000


def test_c5_freeship_threshold_uses_post_flat5_total():
    """Pins step 4 → step 5 order. FREESHIP threshold compares against the
    post-FLAT5 (pre-shipping) total, NOT the pre-discount subtotal.
    Correct: 5500 → SAVE10 = 4950 → FLAT5 = 4450 → 4450 < 5000 so ship NOT
    waived → 4450 + 500 = 4950.
    Bug (uses subtotal): 5500 >= 5000 so ship waived → 4450."""
    cart = Cart()
    cart.add_item("widget", 1, 5500)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 4950


def test_c5_full_pipeline_integration():
    """All four stackable codes applied at once — exercises every step in order.
    Trace: 4 bagels @ 1000 = 4000 subtotal.
    → BOGO (2 free, -2000) = 2000
    → SAVE10 (10% off) = 1800
    → FLAT5 (-500) = 1300
    → 1300 < 5000 so FREESHIP doesn't waive; +500 ship = 1800.
    Catches accumulated order bugs that single-step tests might miss."""
    cart = Cart()
    cart.add_item("bagel", 4, 1000)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 1800


def test_c5_apply_code_before_add_item_still_takes_effect():
    """The spec's BOGO clause says 'when total_cents is computed' — implying
    apply_code is evaluated lazily at total_cents time, not eagerly at apply time.
    A buggy impl that snapshots cart state at apply_code time would skip the
    discount on items added afterward. Hidden bug: spec implies but doesn't spell out."""
    cart = Cart()
    cart.apply_code("BOGO_BAGEL")        # applied to empty cart, no effect yet
    cart.add_item("bagel", 2, 300)       # bagels added AFTER apply
    # Subtotal 600 → BOGO -300 (1 free) = 300 → +500 ship = 800
    assert cart.total_cents() == 800


def test_c5_flat5_lands_at_exactly_zero():
    """FLAT5 reducing pre-shipping to exactly 0 — the boundary of the clamp.
    A buggy impl using truthiness checks on 0 (e.g. `if not pre_shipping`) might
    treat exact-zero specially. Pure boundary test: subtotal 500, FLAT5 → 0
    (not negative, not clamped — exactly zero) → +500 ship = 500."""
    cart = Cart()
    cart.add_item("widget", 1, 500)
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 500


# --- C6: Banker's rounding (ROUND_HALF_EVEN) ---

@pytest.mark.parametrize("subtotal,expected_discount", [
    (25, 2),    # 2.5 → 2 (round half-even down to even)
    (35, 4),    # 3.5 → 4 (up to even)
    (45, 4),    # 4.5 → 4 (down to even)
    (55, 6),    # 5.5 → 6 (up to even)
])
def test_c6_save10_rounds_half_even(subtotal, expected_discount):
    """SAVE10 discount on subtotals ending in 5 lands at the half-cent boundary,
    where banker's rounding kicks in. Each case alternates whether banker's
    rounds down or up (to the nearest even). A half-up bug fails at 25 and 45;
    a half-down bug fails at 35 and 55; a truncating impl fails at 35 and 55."""
    cart = Cart()
    cart.add_item("widget", 1, subtotal)
    cart.apply_code("SAVE10")
    expected_total = (subtotal - expected_discount) + 500
    assert cart.total_cents() == expected_total


# --- C7: Empty cart ---

@pytest.mark.parametrize("codes", [
    [],                                              # no codes at all
    ["FLAT5"],                                       # would go negative without clamp
    ["SAVE10", "FLAT5", "BOGO_BAGEL", "FREESHIP"],   # max stack on empty cart
])
def test_c7_empty_cart_total_is_zero(codes):
    """An empty cart's total is 0 regardless of which codes are applied. No
    shipping, no negative from FLAT5, no math at all. Catches: always-add-
    shipping, no-clamp-on-empty, and any code-dependent state corruption."""
    cart = Cart()
    for code in codes:
        cart.apply_code(code)
    assert cart.total_cents() == 0
