import pytest
from cart import Cart


# ---------------------------------------------------------------------------
# C6 — Rounding (WRITTEN FIRST — clean-run gate before rest of suite)
# If either test fails against the clean module, stop and flag to instructor.
# The spec explicitly names decimal.ROUND_HALF_EVEN; do NOT weaken these tests.
# ---------------------------------------------------------------------------

def test_c6_round_half_even_down():
    # 10% of 1005 = 100.5 → rounds to 100 (100 is even under ROUND_HALF_EVEN)
    # A floor impl gives 100 (passes). A round() impl gives 101 (fails).
    # A ceiling impl gives 101 (fails). Only ROUND_HALF_EVEN gives 100 here.
    cart = Cart()
    cart.add_item("item", 1, 1005)
    cart.apply_code("SAVE10")
    # subtotal 1005, minus 100 discount = 905, plus 500 shipping = 1405
    assert cart.total_cents() == 1405


def test_c6_round_half_even_up():
    # 10% of 1015 = 101.5 → rounds to 102 (102 is even under ROUND_HALF_EVEN)
    # A floor impl gives 101 (fails). A round() impl gives 102 (passes here
    # by coincidence). A ceiling impl gives 102 (passes). ROUND_HALF_EVEN gives 102.
    # Combined with the _down test, these two together pin ROUND_HALF_EVEN uniquely.
    cart = Cart()
    cart.add_item("item", 1, 1015)
    cart.apply_code("SAVE10")
    # subtotal 1015, minus 102 discount = 913, plus 500 shipping = 1413
    assert cart.total_cents() == 1413


# ---------------------------------------------------------------------------
# C1 — add_item validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("qty", [0, -1, -100])
def test_c1_invalid_qty_raises(qty):
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", qty, 100)


@pytest.mark.parametrize("price", [-1, -500])
def test_c1_negative_price_raises(price):
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", 1, price)


def test_c1_zero_price_valid():
    cart = Cart()
    cart.add_item("freebie", 1, 0)   # must not raise


def test_c1_duplicate_sku_raises():
    cart = Cart()
    cart.add_item("widget", 1, 100)
    with pytest.raises(ValueError):
        cart.add_item("widget", 2, 200)


# ---------------------------------------------------------------------------
# C2 — apply_code
# ---------------------------------------------------------------------------

def test_c2_unknown_code_returns_false():
    cart = Cart()
    assert cart.apply_code("BOGUS") is False


def test_c2_lowercase_code_returns_false():
    # Code names are case-sensitive per C2
    cart = Cart()
    assert cart.apply_code("save10") is False


@pytest.mark.parametrize("code", ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"])
def test_c2_duplicate_any_code_returns_false(code):
    # C2: returns False if already applied. Test all five codes.
    # Only assert apply_code return values — this test pins C2, not discount amounts.
    cart = Cart()
    cart.add_item("widget", 1, 10000)
    first  = cart.apply_code(code)
    second = cart.apply_code(code)
    assert first  is True
    assert second is False


# ---------------------------------------------------------------------------
# C3 — Known codes (percent discounts)
# ---------------------------------------------------------------------------

def test_c3_save10_ten_percent_off():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    cart.apply_code("SAVE10")
    # 10000 * 10% = 1000; subtotal after = 9000; + 500 shipping = 9500
    assert cart.total_cents() == 9500


def test_c3_save20_twenty_percent_off():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    cart.apply_code("SAVE20")
    # 10000 * 20% = 2000; subtotal after = 8000; + 500 shipping = 8500
    assert cart.total_cents() == 8500


# ---------------------------------------------------------------------------
# C3 — Known codes (BOGO_BAGEL)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("qty,free_units", [(1, 0), (2, 1), (3, 1), (4, 2), (5, 2)])
def test_c3_bogo_bagel_qty_floor_division(qty, free_units):
    cart = Cart()
    cart.add_item("bagel", qty, 300)
    cart.apply_code("BOGO_BAGEL")
    paid_units = qty - free_units
    # paid bagels + 500 shipping
    assert cart.total_cents() == paid_units * 300 + 500


def test_c3_bogo_bagel_no_bagel_sku_no_effect():
    # BOGO applied but no "bagel" SKU: code accepted (True), no discount
    cart = Cart()
    cart.add_item("muffin", 2, 300)
    assert cart.apply_code("BOGO_BAGEL") is True
    # no BOGO discount, just 2 * 300 + 500 shipping
    assert cart.total_cents() == 1100


# ---------------------------------------------------------------------------
# C3 — Known codes (FREESHIP)
# ---------------------------------------------------------------------------

def test_c3_freeship_exactly_5000_waived():
    # >= 5000 qualifies; exactly 5000 must waive shipping
    cart = Cart()
    cart.add_item("item", 1, 5000)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5000


def test_c3_freeship_4999_not_waived():
    cart = Cart()
    cart.add_item("item", 1, 4999)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5499  # 4999 + 500 shipping


def test_c3_freeship_above_5000_waived():
    cart = Cart()
    cart.add_item("item", 1, 6000)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 6000


# ---------------------------------------------------------------------------
# C4 — Stacking rules
# ---------------------------------------------------------------------------

def test_c4_save10_then_save20_second_rejected():
    cart = Cart()
    cart.add_item("item", 1, 10000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False


def test_c4_save20_then_save10_second_rejected():
    cart = Cart()
    cart.add_item("item", 1, 10000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("SAVE10") is False


def test_c4_only_first_percent_affects_total():
    # Only SAVE10 should apply; SAVE20 was rejected
    cart = Cart()
    cart.add_item("item", 1, 10000)
    cart.apply_code("SAVE10")
    cart.apply_code("SAVE20")   # rejected
    # 10000 - 1000 = 9000 + 500 = 9500 (not 8500 which would be 20%)
    assert cart.total_cents() == 9500


# ---------------------------------------------------------------------------
# C5 — Application order
# ---------------------------------------------------------------------------

def test_c5_flat5_applied_after_percent():
    # Verify order: percent discount first, FLAT5 second
    # If FLAT5 applied first: 10000 - 500 = 9500; then 10% of 9500 = 950 off → 8550 + 500 = 9050
    # If percent first (correct): 10000 - 1000 = 9000; then - 500 = 8500 + 500 = 9000
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 9000


def test_c5_bogo_applied_before_percent():
    # C5: BOGO subtracted before percent discount applied
    # 4 bagels at 300 each = 1200; BOGO frees 2 → 600; SAVE10 of 600 = 60 off → 540; + 500 = 1040
    # If percent applied first (wrong): 1200 * 90% = 1080; BOGO frees 2 at 300 = -600 → 480 + 500 = 980
    cart = Cart()
    cart.add_item("bagel", 4, 300)
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 1040


def test_c5_shipping_500_added_nonempty():
    # Non-empty cart, no FREESHIP: shipping always added
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.total_cents() == 1500


def test_c5_flat5_clamp_at_zero():
    # C5 step 4: if FLAT5 would make pre-shipping total negative, clamp at 0
    cart = Cart()
    cart.add_item("cheap", 1, 200)   # subtotal 200
    cart.apply_code("FLAT5")         # would give 200 - 500 = -300 → clamp to 0
    # pre-shipping = 0; cart non-empty → shipping added; total = 500
    assert cart.total_cents() == 500


def test_c5_freeship_threshold_uses_post_discount_total():
    # FREESHIP checks pre-shipping total AFTER discounts (C5 step 5: "from step 4")
    # SAVE20 on 6000 = 1200 off → 4800 post-discount; 4800 < 5000 → FREESHIP not waived
    cart = Cart()
    cart.add_item("item", 1, 6000)
    cart.apply_code("SAVE20")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5300   # 4800 + 500 shipping


def test_c5_freeship_not_waived_when_below_threshold_after_flat5():
    # FLAT5 drops pre-shipping below 5000 → FREESHIP threshold not met
    cart = Cart()
    cart.add_item("item", 1, 5300)    # subtotal 5300
    cart.apply_code("FLAT5")          # 5300 - 500 = 4800 pre-shipping
    cart.apply_code("FREESHIP")       # 4800 < 5000 → not waived
    assert cart.total_cents() == 5300  # 4800 + 500 shipping


# ---------------------------------------------------------------------------
# C7 — Empty cart
# ---------------------------------------------------------------------------

def test_c7_empty_cart_returns_zero():
    assert Cart().total_cents() == 0


def test_c7_empty_cart_with_codes_returns_zero():
    cart = Cart()
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 0


# ---------------------------------------------------------------------------
# Hidden tests
# ---------------------------------------------------------------------------

def test_hidden_bogo_applied_before_bagel_added():
    # C3: "when total_cents is computed" — BOGO evaluates at compute-time,
    # so the bagel item doesn't need to exist when the code is applied.
    cart = Cart()
    cart.apply_code("BOGO_BAGEL")      # applied before bagel exists
    cart.add_item("bagel", 2, 300)     # added after
    # BOGO: 1 free; 1 paid * 300 = 300; + 500 shipping = 800
    assert cart.total_cents() == 800


def test_hidden_nonempty_cart_zero_subtotal_shipping_added():
    # C1 allows unit_price_cents=0. C5 adds shipping for any non-empty cart.
    cart = Cart()
    cart.add_item("freebie", 1, 0)
    assert cart.total_cents() == 500   # cart non-empty → shipping added


def test_hidden_freeship_zero_subtotal_threshold_not_waived():
    # Pre-shipping total of 0 is below the 5000 threshold, so FREESHIP
    # does not waive shipping even though the code is applied.
    cart = Cart()
    cart.add_item("freebie", 1, 0)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 500   # 0 < 5000 threshold → shipping not waived


def test_hidden_duplicate_bogo_no_bagel_returns_false():
    # C3: the code is "still considered applied for the purpose of C2's
    # duplicate-application rule" even without a bagel item in the cart.
    cart = Cart()
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("BOGO_BAGEL") is False
