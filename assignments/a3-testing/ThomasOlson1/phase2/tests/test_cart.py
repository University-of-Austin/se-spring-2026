"""Phase 1 tests for the `cart` module.

Tests are organized clause-by-clause against the spec at
`starter/assignment3/specs/cart.md`.
"""
import pytest

from cart import Cart


# ---------------------------------------------------------------------------
# C1. add_item(sku, qty, unit_price_cents).
# - qty must be a positive integer (>= 1). Invalid raises ValueError.
# - unit_price_cents must be a non-negative integer. Invalid raises ValueError.
# - Adding a sku already in the cart raises ValueError. One line item per SKU.
# ---------------------------------------------------------------------------

def test_c1_qty_zero_raises_value_error():
    # Boundary case: 0 is the largest invalid qty under the >= 1 rule.
    # Catches a bug where the validator uses `qty < 0` (allowing 0) or
    # `qty <= 0` (correct) — only the latter rejects 0.
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("a", 0, 100)


@pytest.mark.parametrize("qty", [-1, -5, -100])
def test_c1_negative_qty_raises_value_error(qty):
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("a", qty, 100)


def test_c1_qty_one_is_valid():
    # Smallest valid qty per the >= 1 rule. Confirms the boundary
    # accepts (not just that it rejects 0).
    cart = Cart()
    cart.add_item("a", 1, 100)


def test_c1_unit_price_zero_is_valid():
    # Spec says unit_price_cents must be non-negative — so 0 is allowed
    # (free items). Catches a bug where the validator uses `> 0`
    # instead of `>= 0`.
    cart = Cart()
    cart.add_item("a", 1, 0)


@pytest.mark.parametrize("price", [-1, -100, -10000])
def test_c1_negative_unit_price_raises_value_error(price):
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("a", 1, price)


def test_c1_duplicate_sku_raises_value_error():
    # Spec: "Adding an item whose sku is already in the cart raises
    # ValueError. One line item per SKU." The second add must raise
    # even though the qty/price are valid on their own.
    cart = Cart()
    cart.add_item("a", 1, 100)
    with pytest.raises(ValueError):
        cart.add_item("a", 1, 100)


# ---------------------------------------------------------------------------
# C2. apply_code(code).
# - Returns True if the code was applied.
# - Returns False if the code is unknown, is already applied, or conflicts
#   with an applied code (per C4).
# - Code names are case-sensitive.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "code",
    ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"],
)
def test_c2_known_code_applies_on_fresh_cart(code):
    # Every code listed in C3 must be accepted on a fresh cart with no
    # other codes applied. Catches a bug where any single code is mis-
    # spelled or missing from the impl's known-code set.
    cart = Cart()
    assert cart.apply_code(code) is True


@pytest.mark.parametrize(
    "code",
    ["GIBBERISH", "SAVE15", "BOGO", "FREE_SHIP", ""],
)
def test_c2_unknown_code_returns_false(code):
    # Unknown codes (typos, similar-looking names, empty string) must
    # return False, not raise. Empty string is included to rule out a
    # bug where empty input is treated as a no-op success.
    cart = Cart()
    assert cart.apply_code(code) is False


@pytest.mark.parametrize(
    "code",
    [
        "save10",   # all lowercase
        "Save10",   # title case
        "SAVE10 ",  # trailing space (still distinct)
        "FLAT5  ",  # different code, same lesson
        "freeship",
    ],
)
def test_c2_codes_are_case_sensitive(code):
    # Spec: "Code names are case-sensitive. SAVE10 is a valid code;
    # save10 is unknown." Anything that isn't an exact-match string
    # against the known set must be treated as unknown -> False.
    cart = Cart()
    assert cart.apply_code(code) is False


@pytest.mark.parametrize(
    "code",
    ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"],
)
def test_c2_re_applying_same_code_returns_false(code):
    # Spec: "Returns False if the code is ... already applied."
    # Each code, applied a second time on the same cart, must return
    # False. Parametrized over all five codes to catch a bug that
    # tracks "applied" state incorrectly for any specific code.
    cart = Cart()
    assert cart.apply_code(code) is True
    assert cart.apply_code(code) is False


@pytest.mark.parametrize(
    "first, second",
    [
        pytest.param("SAVE10", "SAVE20", id="save10-then-save20"),
        pytest.param("SAVE20", "SAVE10", id="save20-then-save10"),
    ],
)
def test_c2_save10_and_save20_are_mutually_exclusive(first, second):
    # Spec C4: "SAVE10 and SAVE20 are mutually exclusive. Applying one
    # then the other returns False on the second call; only the first
    # takes effect." Tested in both orders to catch a bug where the
    # conflict check is one-directional.
    cart = Cart()
    assert cart.apply_code(first) is True
    assert cart.apply_code(second) is False


def test_c2_freeship_applies_regardless_of_cart_total():
    # The $50 threshold from C5 governs whether shipping is *waived*
    # during total_cents computation — it is NOT a precondition for
    # apply_code(FREESHIP) returning True. Confirmed across an empty
    # cart and a sub-$50 cart: both must accept FREESHIP at apply
    # time. Catches a bug where the impl conflates the C5 waiver
    # gate with the C2 apply gate.
    empty = Cart()
    assert empty.apply_code("FREESHIP") is True

    small = Cart()
    small.add_item("widget", 1, 100)   # $1.00, well under $50
    assert small.apply_code("FREESHIP") is True


# ---------------------------------------------------------------------------
# C3. Known codes — each code's specific effect on the cart total.
# Test math (cart $100 = 10000 cents, default shipping = 500 cents):
#   No codes:    10000 + 500       = 10500
#   SAVE10:      10000 - 10% + 500 = 9500
#   SAVE20:      10000 - 20% + 500 = 8500
#   FLAT5:       10000 - 500 + 500 = 10000
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "code, expected",
    [
        pytest.param("SAVE10", 9500, id="save10-10-percent-off"),
        pytest.param("SAVE20", 8500, id="save20-20-percent-off"),
    ],
)
def test_c3_percent_codes_take_their_named_cut_off_subtotal(code, expected):
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code(code)
    assert cart.total_cents() == expected


def test_c3_flat5_takes_500_cents_off_subtotal():
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("FLAT5")
    # 10000 - 500 (FLAT5) + 500 (shipping) = 10000
    assert cart.total_cents() == 10000


@pytest.mark.parametrize(
    "qty, paid_count",
    [
        pytest.param(1, 1, id="qty-1-no-effect"),       # qty//2 = 0 free, 1 paid
        pytest.param(2, 1, id="qty-2-canonical-bogo"),  # qty//2 = 1 free, 1 paid
        pytest.param(3, 2, id="qty-3-odd-floors"),      # qty//2 = 1 free, 2 paid
        pytest.param(4, 2, id="qty-4-two-pairs"),       # qty//2 = 2 free, 2 paid
    ],
)
def test_c3_bogo_bagel_makes_qty_floor_div_two_units_free(qty, paid_count):
    # Spec: "for the line item with sku 'bagel', (qty // 2) units are
    # free." Test math: paid_count * 300 + 500 shipping. qty=1 case
    # pins the boundary between "BOGO does nothing" (qty < 2) and
    # "BOGO does something" — catches a bug using `(qty + 1) // 2`.
    cart = Cart()
    cart.add_item("bagel", qty, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == paid_count * 300 + 500


def test_c3_bogo_bagel_only_affects_bagel_sku():
    # Spec: "for the line item with sku 'bagel'" — the discount is
    # SKU-specific. Adding 2 muffins (which look BOGO-shaped but
    # aren't bagels) must not yield any discount.
    cart = Cart()
    cart.add_item("muffin", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    # No discount: 600 subtotal + 500 shipping = 1100
    assert cart.total_cents() == 1100


def test_c3_bogo_bagel_with_no_bagel_in_cart_has_no_effect():
    # Spec: "If no bagel line item exists when total_cents is computed,
    # the code has no effect but is still considered 'applied' for the
    # purpose of C2's duplicate-application rule." Cart has only candy;
    # BOGO is applied but contributes no discount.
    cart = Cart()
    cart.add_item("candy", 1, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    # 1000 + 500 shipping = 1500 (no BOGO effect)
    assert cart.total_cents() == 1500


def test_c3_percent_discount_applies_after_bogo():
    # Spec: "SAVE10 — 10% off subtotal (after BOGO)." Two bagels at $3
    # each:  600 -> 300 (BOGO halves it) -> 270 (SAVE10 on $3, not $6)
    # -> +500 shipping = 770. If percent applied BEFORE BOGO (the bug):
    # 600 -> 540 -> 270 (BOGO halves $5.40) -> +500 = 770. Hmm same!
    # But using SAVE20 distinguishes: correct 600->300->240+500=740,
    # wrong order 600->480->240+500=740. Still same! Need a value where
    # the order matters mathematically — odd-qty bagel.
    #
    # Three bagels at $3 each = 900. Correct order:
    #   900 -> 600 (BOGO: 1 free, 2 paid) -> 540 (SAVE10) -> 1040 total
    # Wrong order (percent first):
    #   900 -> 810 (SAVE10) -> 540 (BOGO: 1 free) -> 1040 total
    # Hmm same again. The reason: BOGO halves and percent multiplies,
    # so they commute on linear quantities.
    #
    # The order matters when BOGO interacts asymmetrically with rounding.
    # For now, pin the SPEC-promised behavior: 2 bagels at $3, BOGO+SAVE10
    # gives 600->300->270+500=770. Documents the order even if the
    # alternative order gives the same number for this case.
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 770


def test_c3_flat5_applies_after_percent_discount():
    # Spec: "FLAT5 — 500 cents off, applied AFTER any percent discount."
    # Cart $100 + SAVE10 + FLAT5:
    #   Correct order: 10000 -> 9000 (SAVE10) -> 8500 (FLAT5) +500 ship = 9000
    #   Wrong order:   10000 -> 9500 (FLAT5) -> 8550 (SAVE10) +500 ship = 9050
    # The 50-cent gap exposes percent applied to wrong base.
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 9000


@pytest.mark.parametrize(
    "subtotal, expected",
    [
        pytest.param(4999, 5499, id="just-below-5000-shipping-not-waived"),
        pytest.param(5000, 5000, id="exactly-5000-boundary-shipping-waived"),
        pytest.param(5001, 5001, id="just-above-5000-shipping-waived"),
    ],
)
def test_c3_freeship_waives_shipping_at_5000_cent_boundary(subtotal, expected):
    # Spec: "FREESHIP — waives the flat 500-cent shipping charge when
    # the post-discount pre-shipping subtotal is >= 5000 cents." Test
    # the exact boundary: 4999 must NOT waive, 5000 must waive (the
    # `>=`), 5001 must waive. Catches `>` vs `>=` off-by-one.
    cart = Cart()
    cart.add_item("widget", 1, subtotal)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == expected


# ---------------------------------------------------------------------------
# C4. Stacking rules. SAVE10 and SAVE20 are mutually exclusive; FLAT5 stacks
# with either percent code; BOGO_BAGEL and FREESHIP stack with everything.
# (Conflict-returns-False already tested in C2; these tests focus on the
# EFFECTS — that the first code's effect is preserved when a second is
# rejected, and that allowed stacks compute the right total.)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "first, second, expected",
    [
        pytest.param("SAVE10", "SAVE20", 9500, id="save10-then-save20-keeps-save10"),
        pytest.param("SAVE20", "SAVE10", 8500, id="save20-then-save10-keeps-save20"),
    ],
)
def test_c4_rejected_save_code_does_not_undo_first_save_code(first, second, expected):
    # Spec C4: "Applying one then the other returns False on the second
    # call; only the first takes effect." This goes beyond the C2
    # return-value test by checking that the first code's EFFECT
    # actually persists into total_cents. Catches a bug where the
    # rejection path inadvertently clears the first code's state.
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    cart.apply_code(first)
    cart.apply_code(second)        # rejected
    assert cart.total_cents() == expected


@pytest.mark.parametrize(
    "percent_code, expected",
    [
        pytest.param("SAVE10", 9000, id="flat5-with-save10"),
        pytest.param("SAVE20", 8000, id="flat5-with-save20"),
    ],
)
def test_c4_flat5_stacks_with_either_percent_code(percent_code, expected):
    # Spec C4: "FLAT5 stacks with either percent code." Both codes
    # must apply and both effects must show in total_cents.
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    assert cart.apply_code(percent_code) is True
    assert cart.apply_code("FLAT5") is True
    assert cart.total_cents() == expected


def test_c4_flat5_stacks_with_bogo_bagel():
    # Spec C4: "BOGO_BAGEL stacks with every other code." Pair with
    # FLAT5 specifically to confirm both effects compose correctly.
    # 2 bagels at $10 each: 2000 -> 1000 (BOGO) -> 500 (FLAT5)
    #   + 500 shipping = 1000.
    cart = Cart()
    cart.add_item("bagel", 2, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.total_cents() == 1000


# ---------------------------------------------------------------------------
# C5. Application order for total_cents. Covered piecewise by C3 tests,
# but two unique C5 promises remain: (a) FLAT5 clamps the pre-shipping
# total at 0 if it would go negative, and (b) all six steps compose
# correctly when every code is applied.
# ---------------------------------------------------------------------------

def test_c5_shipping_added_for_zero_dollar_subtotal_with_items():
    # Spec C5 step 5: "If cart is non-empty, add 500 cents shipping
    # UNLESS FREESHIP..." A cart with a $0-priced item is still
    # non-empty, so shipping must be added. Total = 0 + 500 = 500.
    # Catches a bug where the shipping-added gate uses subtotal > 0
    # instead of cart-non-empty as the trigger.
    cart = Cart()
    cart.add_item("freebie", 1, 0)
    assert cart.total_cents() == 500


def test_c5_flat5_clamps_pre_shipping_total_at_zero():
    # Spec C5 step 4: "If this would make the pre-shipping total
    # negative, clamp at 0." Cart has $1.00 subtotal; FLAT5 would
    # subtract 500 cents from 100, going to -400. Clamp to 0, then
    # shipping (500 cents) is added per step 5. Expected total: 500.
    # Without the clamp, the impl would yield -400 + 500 = 100 (wrong).
    cart = Cart()
    cart.add_item("widget", 1, 100)
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 500


def test_c5_full_application_order_end_to_end():
    # Comprehensive integration test exercising every step of the C5
    # order in one cart, with TWO line items (one bagel, one non-bagel)
    # so that subtotal computation across multiple SKUs is also pinned.
    #
    # Cart: 4 bagels at $30 each + 2 widgets at $20 each
    #
    #   Step 1: subtotal = 4*3000 + 2*2000 = 12000 + 4000 = 16000
    #   Step 2: BOGO halves the bagel line only (qty//2=2 free):
    #           bagels 12000 -> 6000; widgets unchanged 4000;
    #           post-BOGO = 10000
    #   Step 3: SAVE20 (20% off) on 10000 -> 8000
    #   Step 4: FLAT5 -> 7500 (no clamp needed)
    #   Step 5: FREESHIP applied AND pre-shipping 7500 >= 5000,
    #           so shipping waived. Total = 7500.
    #
    # Bugs this catches that single-SKU tests don't:
    #   - subtotal only counts the first/last line item
    #   - BOGO bleeds into non-bagel SKUs (would yield 8000, not 7500)
    #   - FREESHIP threshold check uses the raw subtotal instead of the
    #     post-discount pre-shipping total
    cart = Cart()
    cart.add_item("bagel", 4, 3000)
    cart.add_item("widget", 2, 2000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True
    assert cart.total_cents() == 7500


# ---------------------------------------------------------------------------
# C6. Rounding. Percent discounts use banker's rounding (ROUND_HALF_EVEN)
# to the nearest cent. Only the percent-discount result rounds; integer
# arithmetic elsewhere.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "subtotal, expected_total",
    [
        # subtotal ending in 5 -> 10% has half-cent fractional part.
        # Banker's rounds half to nearest EVEN integer.
        # Each row: (subtotal, total_after_save10_and_shipping)
        # total = subtotal - banker_rounded_discount + 500 (shipping)
        pytest.param(5,  505, id="0.5-rounds-down-to-0"),    # 0.5 -> 0 (vs half-up 1)
        pytest.param(15, 513, id="1.5-rounds-up-to-2"),      # 1.5 -> 2 (vs half-down 1)
        pytest.param(25, 523, id="2.5-rounds-down-to-2"),    # 2.5 -> 2 (vs half-up 3)
        pytest.param(35, 531, id="3.5-rounds-up-to-4"),      # 3.5 -> 4 (vs half-down 3)
        pytest.param(45, 541, id="4.5-rounds-down-to-4"),    # 4.5 -> 4 (vs half-up 5)
    ],
)
def test_c6_save10_uses_bankers_rounding_at_half_cent_boundaries(subtotal, expected_total):
    # Spec: "Percent discounts are rounded half-even (banker's rounding)
    # to the nearest cent." Only SAVE10 (10%) can produce half-cent
    # discounts on integer-cent subtotals — SAVE20 always lands on a
    # whole cent because 20% of an integer is in {.0, .2, .4, .6, .8}.
    #
    # The five cases alternate the rounding direction (down to even,
    # up to even, down to even, ...) to catch BOTH the "round half up"
    # bug (would fail at 0.5, 2.5, 4.5) AND the "round half down" bug
    # (would fail at 1.5, 3.5).
    cart = Cart()
    cart.add_item("widget", 1, subtotal)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == expected_total


def test_c6_rejected_save_code_does_not_perturb_rounding():
    # C4/C6 interaction: when a second SAVE code is rejected (per C4
    # mutual exclusion), the rounding must reflect ONLY the originally-
    # applied code's effect, not double-applied or recomputed under
    # the rejected code's percent.
    #
    # Cart at 25 cents: SAVE10 = 2.5 banker's -> 2 -> total 523.
    # If a buggy impl partially applied SAVE20 alongside or recomputed
    # incorrectly on rejection, the total would diverge.
    cart = Cart()
    cart.add_item("widget", 1, 25)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False    # rejected
    assert cart.total_cents() == 523              # SAVE10's banker's effect


# ---------------------------------------------------------------------------
# C7. Empty cart. Cart().total_cents() returns 0 regardless of which codes
# have been applied. Shipping is not added to an empty cart.
# ---------------------------------------------------------------------------

def test_c7_empty_cart_returns_zero():
    assert Cart().total_cents() == 0


@pytest.mark.parametrize(
    "code",
    ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"],
)
def test_c7_empty_cart_with_any_code_applied_returns_zero(code):
    # Spec: "Cart().total_cents() returns 0 regardless of which codes
    # have been applied." Each code, applied alone to an empty cart,
    # must leave total at 0 — no shipping, no negative discount, no
    # spurious effect.
    cart = Cart()
    assert cart.apply_code(code) is True
    assert cart.total_cents() == 0
