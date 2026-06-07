"""Tests for the `cart` module, organized by spec clause.

Spec reference: specs/cart.md (clauses C1..C7).
"""
import pytest

from cart import Cart


# -----------------------------------------------------------------------------
# C1. add_item validation
# -----------------------------------------------------------------------------

class TestC1AddItem:
    def test_basic_add_succeeds(self):
        cart = Cart()
        cart.add_item("widget", 1, 100)
        assert cart.total_cents() == 100 + 500  # plus shipping

    @pytest.mark.parametrize("qty", [0, -1, -100])
    def test_non_positive_qty_raises(self, qty):
        cart = Cart()
        with pytest.raises(ValueError):
            cart.add_item("widget", qty, 100)

    @pytest.mark.parametrize("price", [-1, -100])
    def test_negative_price_raises(self, price):
        cart = Cart()
        with pytest.raises(ValueError):
            cart.add_item("widget", 1, price)

    def test_zero_price_is_allowed(self):
        cart = Cart()
        cart.add_item("freebie", 1, 0)
        # non-empty cart, so shipping applies
        assert cart.total_cents() == 500

    def test_duplicate_sku_raises(self):
        cart = Cart()
        cart.add_item("widget", 1, 100)
        with pytest.raises(ValueError):
            cart.add_item("widget", 2, 200)

    def test_different_skus_ok(self):
        cart = Cart()
        cart.add_item("a", 1, 100)
        cart.add_item("b", 1, 200)
        assert cart.total_cents() == 100 + 200 + 500


# -----------------------------------------------------------------------------
# C2. apply_code return semantics
# -----------------------------------------------------------------------------

class TestC2ApplyCode:
    def test_known_code_returns_true(self):
        cart = Cart()
        cart.add_item("widget", 1, 1000)
        assert cart.apply_code("SAVE10") is True

    def test_unknown_code_returns_false(self):
        cart = Cart()
        cart.add_item("widget", 1, 1000)
        assert cart.apply_code("NOT_A_CODE") is False

    def test_codes_are_case_sensitive(self):
        cart = Cart()
        cart.add_item("widget", 1, 1000)
        assert cart.apply_code("save10") is False
        assert cart.apply_code("Save10") is False
        assert cart.apply_code("SAVE10") is True

    def test_duplicate_application_returns_false(self):
        cart = Cart()
        cart.add_item("widget", 1, 1000)
        assert cart.apply_code("SAVE10") is True
        assert cart.apply_code("SAVE10") is False

    @pytest.mark.parametrize("code", ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"])
    def test_each_known_code_accepted_first_time(self, code):
        cart = Cart()
        cart.add_item("bagel", 2, 300)
        assert cart.apply_code(code) is True

    @pytest.mark.parametrize("code", ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"])
    def test_each_known_code_duplicate_rejected(self, code):
        cart = Cart()
        cart.add_item("bagel", 4, 300)
        assert cart.apply_code(code) is True
        assert cart.apply_code(code) is False

    def test_empty_string_unknown(self):
        cart = Cart()
        assert cart.apply_code("") is False


# -----------------------------------------------------------------------------
# C3. Code semantics (in isolation where possible)
# -----------------------------------------------------------------------------

class TestC3SAVE10:
    def test_save10_applies_ten_percent(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)  # $100
        cart.apply_code("SAVE10")
        # 10000 - 1000 = 9000, + 500 shipping = 9500
        assert cart.total_cents() == 9500


class TestC3SAVE20:
    def test_save20_applies_twenty_percent(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        cart.apply_code("SAVE20")
        # 10000 - 2000 = 8000, + 500 shipping = 8500
        assert cart.total_cents() == 8500


class TestC3FLAT5:
    def test_flat5_subtracts_500(self):
        cart = Cart()
        cart.add_item("widget", 1, 2000)
        cart.apply_code("FLAT5")
        # 2000 - 500 = 1500, + 500 shipping = 2000
        assert cart.total_cents() == 2000

    def test_flat5_clamps_at_zero(self):
        # Subtotal less than 500 cents, FLAT5 should not produce negative.
        cart = Cart()
        cart.add_item("widget", 1, 200)
        cart.apply_code("FLAT5")
        # 200 - 500 -> clamp 0, + 500 shipping = 500
        assert cart.total_cents() == 500

    def test_flat5_after_percent(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        cart.apply_code("SAVE10")
        cart.apply_code("FLAT5")
        # 10000 - 10% = 9000 - 500 = 8500 + 500 shipping = 9000
        assert cart.total_cents() == 9000


class TestC3BOGOBagel:
    def test_bogo_one_pair(self):
        cart = Cart()
        cart.add_item("bagel", 2, 300)
        cart.apply_code("BOGO_BAGEL")
        # qty // 2 = 1 free; pay for 1 bagel = 300 + 500 shipping = 800
        assert cart.total_cents() == 800

    def test_bogo_odd_qty(self):
        cart = Cart()
        cart.add_item("bagel", 3, 300)
        cart.apply_code("BOGO_BAGEL")
        # qty // 2 = 1 free; pay for 2 bagels = 600 + 500 shipping = 1100
        assert cart.total_cents() == 1100

    def test_bogo_single_bagel_no_discount(self):
        cart = Cart()
        cart.add_item("bagel", 1, 300)
        cart.apply_code("BOGO_BAGEL")
        # 1 // 2 = 0 free; pay 300 + 500 shipping = 800
        assert cart.total_cents() == 800

    def test_bogo_without_bagel_line_item_accepted(self):
        # Per C3: code is still considered "applied" even with no bagel.
        cart = Cart()
        cart.add_item("widget", 1, 1000)
        assert cart.apply_code("BOGO_BAGEL") is True
        # No effect on total
        assert cart.total_cents() == 1000 + 500

    def test_bogo_without_bagel_blocks_reapplication(self):
        cart = Cart()
        cart.add_item("widget", 1, 1000)
        cart.apply_code("BOGO_BAGEL")
        assert cart.apply_code("BOGO_BAGEL") is False

    def test_bogo_only_affects_bagel_line(self):
        cart = Cart()
        cart.add_item("bagel", 2, 300)
        cart.add_item("widget", 1, 1000)
        cart.apply_code("BOGO_BAGEL")
        # bagel: 1 free => 300; widget 1000; subtotal 1300; +500 shipping = 1800
        assert cart.total_cents() == 1800


class TestC3FREESHIP:
    def test_freeship_at_exact_threshold(self):
        cart = Cart()
        cart.add_item("widget", 1, 5000)  # exactly $50.00
        cart.apply_code("FREESHIP")
        # pre-shipping = 5000, >= 5000 so shipping waived
        assert cart.total_cents() == 5000

    def test_freeship_just_below_threshold(self):
        cart = Cart()
        cart.add_item("widget", 1, 4999)
        cart.apply_code("FREESHIP")
        # pre-shipping = 4999, < 5000, so shipping still added
        assert cart.total_cents() == 4999 + 500

    def test_freeship_above_threshold(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        cart.apply_code("FREESHIP")
        assert cart.total_cents() == 10000

    def test_freeship_threshold_uses_post_discount_subtotal(self):
        # Subtotal $55, after SAVE10 -> $49.50 = 4950, below threshold => shipping applies.
        cart = Cart()
        cart.add_item("widget", 1, 5500)
        cart.apply_code("SAVE10")
        cart.apply_code("FREESHIP")
        # 5500 - 10% = 4950, < 5000, so shipping added
        assert cart.total_cents() == 4950 + 500

    def test_freeship_threshold_includes_flat5(self):
        # $55 - 10% = 4950 - FLAT5 = 4450 < 5000 => shipping still added.
        cart = Cart()
        cart.add_item("widget", 1, 5500)
        cart.apply_code("SAVE10")
        cart.apply_code("FLAT5")
        cart.apply_code("FREESHIP")
        assert cart.total_cents() == 4450 + 500

    def test_freeship_without_meeting_threshold_is_still_applied(self):
        # apply_code returns True even if threshold not met (it's just inactive).
        cart = Cart()
        cart.add_item("widget", 1, 100)
        assert cart.apply_code("FREESHIP") is True
        # and re-apply rejected
        assert cart.apply_code("FREESHIP") is False


# -----------------------------------------------------------------------------
# C4. Stacking rules
# -----------------------------------------------------------------------------

class TestC4Stacking:
    def test_save10_then_save20_rejected(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        assert cart.apply_code("SAVE10") is True
        assert cart.apply_code("SAVE20") is False
        # SAVE10 is what takes effect: 10000 - 10% = 9000 + 500 = 9500
        assert cart.total_cents() == 9500

    def test_save20_then_save10_rejected(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        assert cart.apply_code("SAVE20") is True
        assert cart.apply_code("SAVE10") is False
        # SAVE20 takes effect: 10000 - 20% = 8000 + 500 = 8500
        assert cart.total_cents() == 8500

    def test_flat5_stacks_with_save10(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        assert cart.apply_code("SAVE10") is True
        assert cart.apply_code("FLAT5") is True

    def test_flat5_stacks_with_save20(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        assert cart.apply_code("SAVE20") is True
        assert cart.apply_code("FLAT5") is True

    def test_bogo_stacks_with_everything(self):
        cart = Cart()
        cart.add_item("bagel", 2, 300)
        cart.add_item("widget", 1, 10000)
        assert cart.apply_code("BOGO_BAGEL") is True
        assert cart.apply_code("SAVE10") is True
        assert cart.apply_code("FLAT5") is True
        assert cart.apply_code("FREESHIP") is True

    def test_freeship_stacks_with_everything(self):
        cart = Cart()
        cart.add_item("bagel", 2, 300)
        cart.add_item("widget", 1, 10000)
        assert cart.apply_code("FREESHIP") is True
        assert cart.apply_code("BOGO_BAGEL") is True
        assert cart.apply_code("SAVE20") is True
        assert cart.apply_code("FLAT5") is True


# -----------------------------------------------------------------------------
# C5. Application order
# -----------------------------------------------------------------------------

class TestC5Order:
    def test_full_combo_order(self):
        # bagel x2 @ 500 = 1000; widget x1 @ 9000 = 9000; subtotal 10000
        # BOGO: -500 (one bagel free) -> 9500
        # SAVE10: -950 -> 8550
        # FLAT5: -500 -> 8050
        # >=5000 and FREESHIP: shipping waived
        # Total = 8050
        cart = Cart()
        cart.add_item("bagel", 2, 500)
        cart.add_item("widget", 1, 9000)
        cart.apply_code("BOGO_BAGEL")
        cart.apply_code("SAVE10")
        cart.apply_code("FLAT5")
        cart.apply_code("FREESHIP")
        assert cart.total_cents() == 8050

    def test_percent_applies_after_bogo(self):
        # If percent applied to subtotal-before-BOGO, total would differ.
        # bagel x2 @ 1000 = 2000; BOGO -> 1000; SAVE10 -> 900; +500 shipping = 1400
        cart = Cart()
        cart.add_item("bagel", 2, 1000)
        cart.apply_code("BOGO_BAGEL")
        cart.apply_code("SAVE10")
        assert cart.total_cents() == 1400

    def test_flat5_applies_after_percent(self):
        # 10000 - 20% = 8000 - 500 = 7500 + 500 shipping = 8000
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        cart.apply_code("SAVE20")
        cart.apply_code("FLAT5")
        assert cart.total_cents() == 8000

    def test_flat5_clamp_does_not_cause_negative_shipping(self):
        cart = Cart()
        cart.add_item("widget", 1, 100)
        cart.apply_code("FLAT5")
        # subtotal 100 - 500 -> 0 (clamp). Cart non-empty, so shipping = 500.
        assert cart.total_cents() == 500

    def test_application_order_independent_of_apply_code_order(self):
        # Whether you apply FLAT5 before SAVE10 or after, the total math is the same.
        cart_a = Cart()
        cart_a.add_item("widget", 1, 10000)
        cart_a.apply_code("FLAT5")
        cart_a.apply_code("SAVE10")

        cart_b = Cart()
        cart_b.add_item("widget", 1, 10000)
        cart_b.apply_code("SAVE10")
        cart_b.apply_code("FLAT5")

        assert cart_a.total_cents() == cart_b.total_cents()


# -----------------------------------------------------------------------------
# C6. Banker's rounding on percent discount
# -----------------------------------------------------------------------------

class TestC6Rounding:
    def test_half_cent_rounds_to_even_down(self):
        # 10% of 105 = 10.5 -> rounds to 10 (even).
        # subtotal 105 - 10 = 95 + 500 shipping = 595
        cart = Cart()
        cart.add_item("widget", 1, 105)
        cart.apply_code("SAVE10")
        assert cart.total_cents() == 95 + 500

    def test_half_cent_rounds_to_even_up(self):
        # 10% of 115 = 11.5 -> rounds to 12 (even).
        # subtotal 115 - 12 = 103 + 500 shipping = 603
        cart = Cart()
        cart.add_item("widget", 1, 115)
        cart.apply_code("SAVE10")
        assert cart.total_cents() == 103 + 500

    def test_non_half_rounds_normally(self):
        # 10% of 104 = 10.4 -> 10
        cart = Cart()
        cart.add_item("widget", 1, 104)
        cart.apply_code("SAVE10")
        assert cart.total_cents() == 94 + 500

    def test_save20_half_cent_boundary(self):
        # 20% of 25 = 5.0 (exact), so just check a half: 20% of 15 = 3.0 (exact).
        # Use subtotal 12: 20% of 12 = 2.4 -> 2 -> total 10 + shipping
        # Use subtotal 25: 20% = 5.0 exact -> 20 + shipping
        # For half-cent: 20% of 5 = 1.0 exact too. 20% of 12.5 not possible (cents are int).
        # Cleanest: subtotal 65 -> 20% = 13.0 exact. Pick subtotal 7 -> 20% = 1.4 -> 1
        cart = Cart()
        cart.add_item("widget", 1, 7)
        cart.apply_code("SAVE20")
        assert cart.total_cents() == (7 - 1) + 500


# -----------------------------------------------------------------------------
# C7. Empty cart
# -----------------------------------------------------------------------------

class TestC7EmptyCart:
    def test_empty_cart_total_is_zero(self):
        assert Cart().total_cents() == 0

    def test_empty_cart_no_shipping(self):
        # Even with FREESHIP not applied, no shipping should be added.
        cart = Cart()
        assert cart.total_cents() == 0

    @pytest.mark.parametrize("code", ["SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"])
    def test_empty_cart_with_any_code_is_zero(self, code):
        cart = Cart()
        cart.apply_code(code)
        assert cart.total_cents() == 0

    def test_empty_cart_with_all_codes_is_zero(self):
        cart = Cart()
        cart.apply_code("SAVE10")
        cart.apply_code("FLAT5")
        cart.apply_code("BOGO_BAGEL")
        cart.apply_code("FREESHIP")
        assert cart.total_cents() == 0


# -----------------------------------------------------------------------------
# Edge cases / implied behavior
# -----------------------------------------------------------------------------

class TestEdgeCases:
    def test_total_is_idempotent(self):
        # Calling total_cents() multiple times must not mutate state.
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        cart.apply_code("SAVE10")
        first = cart.total_cents()
        second = cart.total_cents()
        third = cart.total_cents()
        assert first == second == third

    def test_add_item_after_apply_code(self):
        # The spec doesn't forbid adding items after applying codes. Codes still apply.
        cart = Cart()
        cart.apply_code("SAVE10")
        cart.add_item("widget", 1, 10000)
        # 10000 - 10% = 9000 + shipping 500 = 9500
        assert cart.total_cents() == 9500

    def test_qty_multiplies_unit_price(self):
        cart = Cart()
        cart.add_item("widget", 5, 200)
        # 5 * 200 = 1000 + 500 shipping = 1500
        assert cart.total_cents() == 1500

    def test_freeship_threshold_uses_post_flat5_subtotal_at_boundary(self):
        # subtotal 5500, SAVE10 -> 4950, FLAT5 -> 4450 < 5000: shipping NOT waived.
        cart = Cart()
        cart.add_item("widget", 1, 5500)
        cart.apply_code("SAVE10")
        cart.apply_code("FLAT5")
        cart.apply_code("FREESHIP")
        assert cart.total_cents() == 4450 + 500

    def test_freeship_at_exact_5000_after_discounts(self):
        # subtotal 5556, SAVE10 -> 5000.4 -> rounds: 10% of 5556 = 555.6 -> 556 (banker)
        # 5556 - 556 = 5000. Then FREESHIP threshold met exactly.
        cart = Cart()
        cart.add_item("widget", 1, 5556)
        cart.apply_code("SAVE10")
        cart.apply_code("FREESHIP")
        # 10% of 5556 = 555.6 -> 556 (no half-even involved). 5556 - 556 = 5000
        assert cart.total_cents() == 5000

    def test_unknown_then_known_code_independent(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        assert cart.apply_code("MYSTERY") is False
        assert cart.apply_code("SAVE10") is True
        assert cart.total_cents() == 9000 + 500

    def test_bogo_qty_one_pays_full_price(self):
        cart = Cart()
        cart.add_item("bagel", 1, 300)
        cart.apply_code("BOGO_BAGEL")
        # 1 // 2 = 0 free, full 300 + 500 shipping
        assert cart.total_cents() == 800

    def test_bogo_large_qty(self):
        cart = Cart()
        cart.add_item("bagel", 10, 100)
        cart.apply_code("BOGO_BAGEL")
        # 10 // 2 = 5 free, pay for 5: 500 + 500 shipping = 1000
        assert cart.total_cents() == 1000

    def test_flat5_alone_on_small_cart(self):
        # subtotal 500 - 500 = 0 + shipping 500 = 500
        cart = Cart()
        cart.add_item("widget", 1, 500)
        cart.apply_code("FLAT5")
        assert cart.total_cents() == 500

    def test_percent_discount_on_zero_subtotal_does_not_explode(self):
        cart = Cart()
        cart.add_item("freebie", 1, 0)
        cart.apply_code("SAVE10")
        # 0 - 0% = 0; non-empty so shipping 500
        assert cart.total_cents() == 500


# -----------------------------------------------------------------------------
# Adversarial / "wait, what about..." cases — spec implications, not happy path
# -----------------------------------------------------------------------------

class TestC1FailedAddDoesNotMutate:
    """C1 says invalid args raise. The spec doesn't say "no partial state",
    but a failed add_item that leaves a half-formed line item violates the
    one-line-per-SKU invariant. Pin it down."""

    def test_duplicate_sku_does_not_overwrite(self):
        cart = Cart()
        cart.add_item("widget", 2, 100)
        with pytest.raises(ValueError):
            cart.add_item("widget", 99, 9999)
        # Original line item intact: 2 * 100 = 200 + 500 shipping
        assert cart.total_cents() == 200 + 500

    def test_bad_qty_does_not_register_sku(self):
        cart = Cart()
        with pytest.raises(ValueError):
            cart.add_item("widget", 0, 100)
        # SKU never made it in, so re-adding with valid qty must succeed
        cart.add_item("widget", 1, 100)
        assert cart.total_cents() == 100 + 500

    def test_bad_price_does_not_register_sku(self):
        cart = Cart()
        with pytest.raises(ValueError):
            cart.add_item("widget", 1, -50)
        cart.add_item("widget", 1, 100)
        assert cart.total_cents() == 100 + 500

    def test_bad_add_does_not_make_cart_non_empty(self):
        # If a failed add somehow flipped "is the cart empty?" state, shipping
        # would appear on a logically-empty cart.
        cart = Cart()
        with pytest.raises(ValueError):
            cart.add_item("widget", -1, 100)
        assert cart.total_cents() == 0


class TestC2CodeMatchingStrict:
    """C2: code names are case-sensitive. The spec's example only covers
    case; whitespace and partial matches are the obvious adjacent traps."""

    @pytest.mark.parametrize("code", [
        " SAVE10", "SAVE10 ", " SAVE10 ", "SAVE 10",
        "save10", "Save10", "sAvE10",
        "SAVE", "SAVE100", "SAVE1",
        "SAVE10\n", "\tSAVE10",
    ])
    def test_near_miss_codes_unknown(self, code):
        cart = Cart()
        cart.add_item("widget", 1, 1000)
        assert cart.apply_code(code) is False

    @pytest.mark.parametrize("code", ["bogo_bagel", "Bogo_Bagel", "BOGO BAGEL", "BOGOBAGEL"])
    def test_bogo_near_miss_unknown(self, code):
        cart = Cart()
        cart.add_item("bagel", 2, 300)
        assert cart.apply_code(code) is False


class TestC3BOGOSkuExact:
    """C3: BOGO is for sku exactly 'bagel'. Different-cased bagel SKUs are
    different line items, so BOGO should not discount them."""

    def test_capital_bagel_not_discounted(self):
        cart = Cart()
        cart.add_item("Bagel", 2, 300)
        cart.apply_code("BOGO_BAGEL")
        # No "bagel" line item, so BOGO is no-op (still applied per C3 note).
        # 2 * 300 = 600 + 500 shipping = 1100
        assert cart.total_cents() == 600 + 500

    def test_uppercase_bagel_not_discounted(self):
        cart = Cart()
        cart.add_item("BAGEL", 2, 300)
        cart.apply_code("BOGO_BAGEL")
        assert cart.total_cents() == 600 + 500

    def test_bagel_substring_sku_not_discounted(self):
        cart = Cart()
        cart.add_item("bagels", 2, 300)
        cart.apply_code("BOGO_BAGEL")
        assert cart.total_cents() == 600 + 500


class TestC3CodeFirstThenItems:
    """C3 says BOGO/FREESHIP are evaluated at total_cents time. Applying
    them before the relevant line items exist must still take effect once
    the items are added."""

    def test_bogo_applied_before_bagel_added(self):
        cart = Cart()
        cart.apply_code("BOGO_BAGEL")
        cart.add_item("bagel", 2, 300)
        # BOGO active at total time, so 1 free: 300 + 500 shipping = 800
        assert cart.total_cents() == 800

    def test_freeship_applied_before_threshold_met(self):
        cart = Cart()
        cart.apply_code("FREESHIP")
        cart.add_item("widget", 1, 5000)
        # threshold met now, shipping waived
        assert cart.total_cents() == 5000


class TestC4RejectedCodeDoesNotMutate:
    """C4: a rejected stack attempt must not silently replace the active
    code or count as 'applied'."""

    def test_save20_after_save10_does_not_replace(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        cart.apply_code("SAVE10")
        assert cart.apply_code("SAVE20") is False
        # SAVE10 still active: 10000 - 10% = 9000 + 500 = 9500
        assert cart.total_cents() == 9500

    def test_save10_after_save20_does_not_replace(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        cart.apply_code("SAVE20")
        assert cart.apply_code("SAVE10") is False
        # SAVE20 still active: 10000 - 20% = 8000 + 500 = 8500
        assert cart.total_cents() == 8500

    def test_rejected_save20_can_still_combine_with_flat5(self):
        # After SAVE10 then SAVE20 (rejected), FLAT5 should still apply normally.
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        cart.apply_code("SAVE10")
        cart.apply_code("SAVE20")  # rejected
        assert cart.apply_code("FLAT5") is True
        # 10000 - 10% = 9000 - 500 = 8500 + 500 shipping = 9000
        assert cart.total_cents() == 9000

    def test_double_apply_does_not_double_discount(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        cart.apply_code("FLAT5")
        cart.apply_code("FLAT5")  # rejected, no-op
        # Single FLAT5: 10000 - 500 + 500 = 10000
        assert cart.total_cents() == 10000


class TestC5OrderPinned:
    """C5: pin the application order with cases where the wrong order
    produces a different number."""

    def test_flat5_does_not_reduce_shipping_charge(self):
        # If FLAT5 mistakenly applied to (subtotal + shipping) or after shipping,
        # this test would fail.
        cart = Cart()
        cart.add_item("widget", 1, 1000)
        cart.apply_code("FLAT5")
        # spec: 1000 - 500 = 500 pre-shipping, + 500 shipping = 1000
        assert cart.total_cents() == 1000

    def test_percent_does_not_apply_to_shipping(self):
        # If SAVE10 mistakenly applied to (subtotal + shipping):
        #   (1000 + 500) - 10% = 1350. We expect 1000 - 100 + 500 = 1400.
        cart = Cart()
        cart.add_item("widget", 1, 1000)
        cart.apply_code("SAVE10")
        assert cart.total_cents() == 900 + 500

    def test_percent_applied_before_flat5_not_after(self):
        # If FLAT5 applied first: 10000 - 500 = 9500, then -10% = 8550, +500 = 9050.
        # Spec order: 10000 - 10% = 9000, -500 = 8500, +500 = 9000.
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        cart.apply_code("FLAT5")    # apply order shouldn't matter
        cart.apply_code("SAVE10")
        assert cart.total_cents() == 9000

    def test_bogo_uses_unit_price_not_post_percent_price(self):
        # BOGO discount is qty // 2 free units at unit price (i.e., subtracted
        # from subtotal BEFORE percent). If percent applied first then BOGO,
        # the free unit's discount would be smaller.
        # bagel x2 @ 1000: subtotal 2000, BOGO -1000 = 1000, SAVE10 -100 = 900
        # +500 shipping = 1400.
        cart = Cart()
        cart.add_item("bagel", 2, 1000)
        cart.apply_code("BOGO_BAGEL")
        cart.apply_code("SAVE10")
        assert cart.total_cents() == 1400

    def test_freeship_does_not_engage_when_flat5_drops_below_threshold(self):
        # subtotal 5400, SAVE10 -> 4860, FLAT5 -> 4360 (< 5000). FREESHIP no-op.
        cart = Cart()
        cart.add_item("widget", 1, 5400)
        cart.apply_code("SAVE10")
        cart.apply_code("FLAT5")
        cart.apply_code("FREESHIP")
        # 5400 - 540 = 4860 - 500 = 4360 + 500 shipping = 4860
        assert cart.total_cents() == 4860

    def test_freeship_engages_when_flat5_lands_at_threshold(self):
        # subtotal 5500 - 0% - 500 = 5000 exact. FREESHIP engages.
        cart = Cart()
        cart.add_item("widget", 1, 5500)
        cart.apply_code("FLAT5")
        cart.apply_code("FREESHIP")
        assert cart.total_cents() == 5000

    def test_flat5_clamp_then_freeship_no_engage(self):
        # After clamping to 0, pre-shipping is 0 (< 5000), FREESHIP no-op.
        cart = Cart()
        cart.add_item("widget", 1, 100)
        cart.apply_code("FLAT5")
        cart.apply_code("FREESHIP")
        # 100 - 500 -> 0 (clamp). 0 < 5000, so shipping still added.
        assert cart.total_cents() == 500


class TestC6BankerSweep:
    """C6: half-even rounding is the prototypical 'rounded the wrong way'
    bug. Sweep many .5 boundaries so a truncate, ceil, or half-up bug
    fails on at least one."""

    @pytest.mark.parametrize("subtotal,expected_discount", [
        (5,   0),   # 0.5 -> 0  (even)
        (15,  2),   # 1.5 -> 2
        (25,  2),   # 2.5 -> 2
        (35,  4),   # 3.5 -> 4
        (45,  4),   # 4.5 -> 4
        (55,  6),   # 5.5 -> 6
        (65,  6),   # 6.5 -> 6
        (75,  8),   # 7.5 -> 8
        (85,  8),   # 8.5 -> 8
        (95,  10),  # 9.5 -> 10
        (105, 10),  # 10.5 -> 10
        (115, 12),  # 11.5 -> 12
    ])
    def test_save10_half_even_sweep(self, subtotal, expected_discount):
        cart = Cart()
        cart.add_item("widget", 1, subtotal)
        cart.apply_code("SAVE10")
        # All non-empty so + 500 shipping
        assert cart.total_cents() == (subtotal - expected_discount) + 500

    def test_save10_truncation_bug_visible(self):
        # truncate-toward-zero would give 105 -> 10 (matches half-even),
        # but 95 -> 9 (truncating 9.5), while half-even gives 10. Catches truncate.
        cart = Cart()
        cart.add_item("widget", 1, 95)
        cart.apply_code("SAVE10")
        assert cart.total_cents() == (95 - 10) + 500

    def test_save10_half_up_bug_visible(self):
        # half-up gives 105 -> 11 (rounds .5 up), half-even gives 10. Catches half-up.
        cart = Cart()
        cart.add_item("widget", 1, 105)
        cart.apply_code("SAVE10")
        assert cart.total_cents() == (105 - 10) + 500


class TestApplyOrderSymmetry:
    """For any combination of compatible codes, apply_code call order shouldn't
    change the final total — only application order in C5 does."""

    def test_all_codes_any_order_same_total(self):
        codes = ["SAVE10", "FLAT5", "BOGO_BAGEL", "FREESHIP"]
        results = []
        # Try a few permutations
        for perm in [codes, list(reversed(codes)),
                     [codes[1], codes[3], codes[0], codes[2]]]:
            cart = Cart()
            cart.add_item("bagel", 2, 1000)
            cart.add_item("widget", 1, 9000)
            for c in perm:
                cart.apply_code(c)
            results.append(cart.total_cents())
        assert len(set(results)) == 1


class TestEmptySkuAndZeroPriceLines:
    """Spec doesn't forbid empty-string SKUs or all-zero-priced lines.
    Pin the implied behavior so the implementation can't quietly reject them."""

    def test_empty_string_sku_allowed(self):
        cart = Cart()
        cart.add_item("", 1, 100)
        assert cart.total_cents() == 100 + 500

    def test_only_zero_price_items_still_charges_shipping(self):
        # Cart is non-empty, so shipping applies even when subtotal is 0.
        cart = Cart()
        cart.add_item("a", 1, 0)
        cart.add_item("b", 1, 0)
        assert cart.total_cents() == 500

    def test_freeship_does_not_engage_on_zero_subtotal(self):
        cart = Cart()
        cart.add_item("a", 1, 0)
        cart.apply_code("FREESHIP")
        # 0 < 5000 so shipping still added
        assert cart.total_cents() == 500


# =============================================================================
# Deeper adversarial probes — the spec's named bug hotspots
# =============================================================================
#
# The spec explicitly calls out four areas as places bugs could hide:
#   "The stacking rules, the application order, the exact boundary at $50.00,
#    and the rounding behavior on percent discounts are all specified
#    precisely, and every one of them is a place a bug could be."
#
# Each section below picks a probe that distinguishes the spec from a
# plausible-looking wrong implementation by at least one cent.
# =============================================================================


class TestStackingProbes:
    """C4: every accept/reject permutation that a careless implementation
    might get wrong — including order-of-application, double-application
    propagation, and rejected-then-retried codes."""

    # ---- FLAT5 acceptance order (independent of percent code order) ---------

    def test_flat5_first_then_save10_accepted(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        assert cart.apply_code("FLAT5") is True
        assert cart.apply_code("SAVE10") is True

    def test_flat5_first_then_save20_accepted(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        assert cart.apply_code("FLAT5") is True
        assert cart.apply_code("SAVE20") is True

    # ---- Mutual exclusion is symmetric and persistent -----------------------

    def test_save20_still_rejected_after_save10_duplicate_attempt(self):
        # Sequence: SAVE10 (True), SAVE10 (False, duplicate), SAVE20 (False, conflict).
        # A buggy "remove on duplicate" impl might forget SAVE10 was active.
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        assert cart.apply_code("SAVE10") is True
        assert cart.apply_code("SAVE10") is False
        assert cart.apply_code("SAVE20") is False
        # SAVE10 still active: 10000 - 1000 + 500 = 9500
        assert cart.total_cents() == 9500

    def test_save10_still_rejected_after_save20_duplicate_attempt(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        assert cart.apply_code("SAVE20") is True
        assert cart.apply_code("SAVE20") is False
        assert cart.apply_code("SAVE10") is False
        # SAVE20 still active
        assert cart.total_cents() == 8000 + 500

    # ---- Re-attempting a rejected code stays rejected -----------------------

    def test_save20_repeatedly_rejected_after_save10(self):
        cart = Cart()
        cart.add_item("widget", 1, 10000)
        cart.apply_code("SAVE10")
        for _ in range(5):
            assert cart.apply_code("SAVE20") is False
        assert cart.total_cents() == 9500

    # ---- All triplets explicitly accepted ----------------------------------

    @pytest.mark.parametrize("percent", ["SAVE10", "SAVE20"])
    @pytest.mark.parametrize("other", ["FLAT5", "BOGO_BAGEL", "FREESHIP"])
    def test_percent_with_each_other_accepted(self, percent, other):
        cart = Cart()
        cart.add_item("bagel", 2, 300)
        cart.add_item("widget", 1, 10000)
        assert cart.apply_code(percent) is True
        assert cart.apply_code(other) is True

    @pytest.mark.parametrize("a,b", [
        ("FLAT5", "BOGO_BAGEL"),
        ("FLAT5", "FREESHIP"),
        ("BOGO_BAGEL", "FREESHIP"),
    ])
    def test_non_percent_pair_stacks(self, a, b):
        cart = Cart()
        cart.add_item("bagel", 2, 300)
        cart.add_item("widget", 1, 5000)
        assert cart.apply_code(a) is True
        assert cart.apply_code(b) is True

    # ---- Specific math when 4 codes stack ----------------------------------

    def test_four_code_stack_exact_math(self):
        # bagel x4 @ 1000 = 4000; widget x1 @ 7000 = 7000; subtotal 11000
        # BOGO: 4 // 2 = 2 free * 1000 = -2000 -> 9000
        # SAVE20: 9000 - 1800 = 7200
        # FLAT5: 7200 - 500 = 6700
        # FREESHIP: 6700 >= 5000, shipping waived
        # Total = 6700
        cart = Cart()
        cart.add_item("bagel", 4, 1000)
        cart.add_item("widget", 1, 7000)
        cart.apply_code("BOGO_BAGEL")
        cart.apply_code("SAVE20")
        cart.apply_code("FLAT5")
        cart.apply_code("FREESHIP")
        assert cart.total_cents() == 6700

    # ---- Apply-order matrix: any permutation gives same total --------------

    def test_full_combo_apply_order_invariant(self):
        from itertools import permutations
        codes = ["SAVE10", "FLAT5", "BOGO_BAGEL", "FREESHIP"]
        totals = set()
        for perm in permutations(codes):
            cart = Cart()
            cart.add_item("bagel", 4, 500)
            cart.add_item("widget", 1, 9000)
            for c in perm:
                cart.apply_code(c)
            totals.add(cart.total_cents())
        # All 24 permutations must produce the same total.
        assert len(totals) == 1


class TestApplicationOrderProbes:
    """C5: each step of the order pinned with numbers a wrong order can't hit."""

    def test_bogo_then_percent_then_flat5_explicit_math(self):
        # bagel x3 @ 700 = 2100. BOGO: 1 free -> 1400.
        # SAVE10: 10% of 1400 = 140 -> 1260.
        # FLAT5: -500 -> 760. Shipping +500 -> 1260.
        cart = Cart()
        cart.add_item("bagel", 3, 700)
        cart.apply_code("BOGO_BAGEL")
        cart.apply_code("SAVE10")
        cart.apply_code("FLAT5")
        assert cart.total_cents() == 1260

    def test_percent_does_not_apply_to_pre_bogo_subtotal(self):
        # bagel x2 @ 1000. Wrong (percent on pre-BOGO): 2000 - 200 = 1800, BOGO -1000 = 800.
        # Right (BOGO first): 2000 - 1000 = 1000, SAVE10 -100 = 900.
        # Difference: 100 cents. +500 shipping in either case.
        cart = Cart()
        cart.add_item("bagel", 2, 1000)
        cart.apply_code("BOGO_BAGEL")
        cart.apply_code("SAVE10")
        assert cart.total_cents() == 1400  # 900 + 500

    def test_flat5_clamp_does_not_underflow_into_shipping(self):
        # subtotal 100, FLAT5 -> 0 (clamp). Shipping is its own +500; not -400.
        cart = Cart()
        cart.add_item("widget", 1, 100)
        cart.apply_code("FLAT5")
        assert cart.total_cents() == 500  # not 100 - 500 + 500 = 100, not -400, etc.

    def test_clamped_flat5_does_not_consume_subsequent_percent_call(self):
        # If FLAT5 clamped to 0 and the implementation skipped the percent
        # discount on a clamped total, this would expose it. Here percent
        # comes before FLAT5 so clamp happens later — test pins the order.
        cart = Cart()
        cart.add_item("widget", 1, 600)
        cart.apply_code("SAVE10")  # 600 - 60 = 540
        cart.apply_code("FLAT5")   # 540 - 500 = 40
        # +500 shipping = 540
        assert cart.total_cents() == 540

    def test_bogo_discount_is_qty_div_two_not_floor_qty_div_two_minus_one(self):
        # qty=4: spec says 4 // 2 = 2 free. If buggy "(qty-1) // 2" it'd be 1 free.
        # bagel x4 @ 1000. Spec: 2 free, pay 2 = 2000 + 500 ship = 2500.
        # Buggy: 1 free, pay 3 = 3000 + 500 = 3500.
        cart = Cart()
        cart.add_item("bagel", 4, 1000)
        cart.apply_code("BOGO_BAGEL")
        assert cart.total_cents() == 2500

    def test_bogo_discount_is_qty_div_two_not_qty_div_two_plus_one(self):
        # qty=2: spec says 1 free. If buggy "qty // 2 + 1" gave 2 free, total would be 0+500.
        cart = Cart()
        cart.add_item("bagel", 2, 1000)
        cart.apply_code("BOGO_BAGEL")
        assert cart.total_cents() == 1000 + 500  # one paid + shipping

    def test_bogo_does_not_silently_act_as_half_off_bagel_line(self):
        # qty=3 @ 700. Spec: 1 free, pay 1400. Half-off would be 1050. +500 shipping.
        cart = Cart()
        cart.add_item("bagel", 3, 700)
        cart.apply_code("BOGO_BAGEL")
        assert cart.total_cents() == 1400 + 500

    def test_percent_rounds_on_post_bogo_subtotal(self):
        # bagel x2 @ 5: subtotal 10, BOGO -> 5. SAVE10 of 5 = 0.5 -> half-even 0.
        # Total = 5 + 500 shipping = 505. If percent applied to PRE-BOGO 10:
        # 10% of 10 = 1 -> 9 - 5 (BOGO) = 4 + 500 = 504. Different cent.
        cart = Cart()
        cart.add_item("bagel", 2, 5)
        cart.apply_code("BOGO_BAGEL")
        cart.apply_code("SAVE10")
        assert cart.total_cents() == 505


class TestFiftyDollarBoundary:
    """C3 + C5 step 5: FREESHIP threshold is `>= 5000` on the post-FLAT5
    pre-shipping number. Probe the exact boundary from multiple angles."""

    @pytest.mark.parametrize("pre_shipping_subtotal,expected_total", [
        (4998, 4998 + 500),   # below: shipping added
        (4999, 4999 + 500),   # below: shipping added
        (5000, 5000),         # at: shipping waived
        (5001, 5001),         # above: shipping waived
        (5002, 5002),         # above: shipping waived
    ])
    def test_freeship_boundary_sweep(self, pre_shipping_subtotal, expected_total):
        cart = Cart()
        cart.add_item("widget", 1, pre_shipping_subtotal)
        cart.apply_code("FREESHIP")
        assert cart.total_cents() == expected_total

    def test_freeship_boundary_via_bogo(self):
        # bagel x2 @ 5000: subtotal 10000, BOGO -> 5000. Threshold met.
        cart = Cart()
        cart.add_item("bagel", 2, 5000)
        cart.apply_code("BOGO_BAGEL")
        cart.apply_code("FREESHIP")
        assert cart.total_cents() == 5000

    def test_freeship_boundary_via_bogo_just_below(self):
        # bagel x2 @ 4999: BOGO -> 4999. Below threshold.
        cart = Cart()
        cart.add_item("bagel", 2, 4999)
        cart.apply_code("BOGO_BAGEL")
        cart.apply_code("FREESHIP")
        assert cart.total_cents() == 4999 + 500

    def test_freeship_boundary_via_percent(self):
        # subtotal 5556, SAVE10 -> 555.6 rounds to 556 (no half-cent).
        # 5556 - 556 = 5000. Threshold met exactly.
        cart = Cart()
        cart.add_item("widget", 1, 5556)
        cart.apply_code("SAVE10")
        cart.apply_code("FREESHIP")
        assert cart.total_cents() == 5000

    def test_freeship_boundary_via_percent_one_off(self):
        # subtotal 5555, SAVE10: 10% of 5555 = 555.5 -> half-even 556 (even).
        # 5555 - 556 = 4999. Just below.
        cart = Cart()
        cart.add_item("widget", 1, 5555)
        cart.apply_code("SAVE10")
        cart.apply_code("FREESHIP")
        assert cart.total_cents() == 4999 + 500

    def test_freeship_threshold_uses_post_flat5_not_post_percent(self):
        # subtotal 5500, SAVE10 -> 4950, FLAT5 -> 4450. Below threshold.
        # If buggy used post-PERCENT (4950) only, still below — same answer.
        # Construct one where the two diverge: subtotal 5500, FLAT5 only.
        # Post-percent doesn't exist (no percent applied). Post-FLAT5 = 5000. Met.
        # Now: subtotal 5500, SAVE10 (4950), FLAT5 (4450).
        #   post-percent = 4950 (below threshold either way — not discriminating).
        # Better: subtotal 5500, no percent, FLAT5 -> 5000 met.
        cart = Cart()
        cart.add_item("widget", 1, 5500)
        cart.apply_code("FLAT5")
        cart.apply_code("FREESHIP")
        assert cart.total_cents() == 5000

    def test_freeship_threshold_is_post_flat5_not_pre_flat5(self):
        # subtotal 5400. FLAT5 -> 4900 (below). FREESHIP must NOT engage.
        # If buggy compared pre-FLAT5 (5400 >= 5000), it would wrongly engage.
        cart = Cart()
        cart.add_item("widget", 1, 5400)
        cart.apply_code("FLAT5")
        cart.apply_code("FREESHIP")
        # 5400 - 500 = 4900, < 5000, shipping added: 4900 + 500 = 5400
        assert cart.total_cents() == 5400

    def test_freeship_threshold_strict_greater_or_equal(self):
        # The spec phrase ">= 5000" — confirm it's NOT strict ">".
        cart = Cart()
        cart.add_item("widget", 1, 5000)
        cart.apply_code("FREESHIP")
        # If buggy used "> 5000", shipping would be added: 5500.
        assert cart.total_cents() == 5000

    def test_freeship_threshold_not_strict_less(self):
        # The spec phrase ">= 5000" — confirm 4999 is NOT included.
        cart = Cart()
        cart.add_item("widget", 1, 4999)
        cart.apply_code("FREESHIP")
        # If buggy used ">= 4999" or ">", behavior would differ.
        assert cart.total_cents() == 4999 + 500


class TestRoundingProbes:
    """C6: ROUND_HALF_EVEN. Beyond the boundary sweep, probe rounding's
    *interaction* with the rest of the pipeline."""

    def test_rounding_only_on_percent_not_on_flat5(self):
        # FLAT5 is exactly 500; rounding should never apply to it.
        # subtotal 500, FLAT5 -> 0 -> +500 shipping = 500. If FLAT5 were rounded
        # weirdly, the result would shift.
        cart = Cart()
        cart.add_item("widget", 1, 500)
        cart.apply_code("FLAT5")
        assert cart.total_cents() == 500

    def test_rounding_only_on_percent_not_on_bogo(self):
        # BOGO discount = (qty // 2) * unit_price. Pure integer arithmetic,
        # rounding shouldn't apply. Pick a unit price where the BOGO discount
        # alone would be a "rounded" candidate if buggy: 5 cents. qty=2 BOGO=-5.
        cart = Cart()
        cart.add_item("bagel", 2, 5)
        cart.apply_code("BOGO_BAGEL")
        # subtotal 10, BOGO -5 = 5, + 500 ship = 505
        assert cart.total_cents() == 505

    def test_save20_no_half_cent_boundary_exists(self):
        # 20% of any integer X = X/5, which has fractional component in
        # {0, 0.2, 0.4, 0.6, 0.8} — never 0.5. Half-even can't be observed
        # in SAVE20 in isolation. Pin a few SAVE20 results to lock down
        # the (mathematically-unambiguous) rounding direction.
        for subtotal, discount in [(7, 1), (12, 2), (13, 3), (14, 3), (8, 2)]:
            # 7 -> 1.4 -> 1; 12 -> 2.4 -> 2; 13 -> 2.6 -> 3; 14 -> 2.8 -> 3; 8 -> 1.6 -> 2
            cart = Cart()
            cart.add_item("widget", 1, subtotal)
            cart.apply_code("SAVE20")
            assert cart.total_cents() == (subtotal - discount) + 500, \
                f"SAVE20 of {subtotal}: expected discount {discount}"

    def test_rounding_at_save10_on_post_bogo_half_cent(self):
        # bagel x2 @ 105: subtotal 210, BOGO -> 105. SAVE10 of 105 = 10.5 -> 10 (even).
        # 105 - 10 = 95 + 500 ship = 595.
        cart = Cart()
        cart.add_item("bagel", 2, 105)
        cart.apply_code("BOGO_BAGEL")
        cart.apply_code("SAVE10")
        assert cart.total_cents() == 595

    def test_rounding_at_save10_on_post_bogo_half_cent_other_parity(self):
        # bagel x2 @ 115: subtotal 230, BOGO -> 115. SAVE10 of 115 = 11.5 -> 12 (even).
        # 115 - 12 = 103 + 500 ship = 603.
        cart = Cart()
        cart.add_item("bagel", 2, 115)
        cart.apply_code("BOGO_BAGEL")
        cart.apply_code("SAVE10")
        assert cart.total_cents() == 603

    @pytest.mark.parametrize("subtotal,save10_discount", [
        # ROUND_HALF_EVEN-distinguishing: each is a .5 case. truncate, ceil,
        # half-up, half-down all disagree with half-even on at least one.
        (5,   0),
        (15,  2),
        (25,  2),
        (35,  4),
        (45,  4),
        (55,  6),
        (65,  6),
        (75,  8),
        (85,  8),
        (95,  10),
        (105, 10),
        (115, 12),
        (125, 12),
        (135, 14),
        (145, 14),
        (155, 16),
        (165, 16),
        (175, 18),
        (185, 18),
        (195, 20),
    ])
    def test_save10_extended_half_even_sweep(self, subtotal, save10_discount):
        cart = Cart()
        cart.add_item("widget", 1, subtotal)
        cart.apply_code("SAVE10")
        assert cart.total_cents() == (subtotal - save10_discount) + 500

    def test_rounding_does_not_compound_across_calls(self):
        # total_cents() called twice must give the same answer; rounding
        # should not accumulate or drift if the impl recomputes from scratch.
        cart = Cart()
        cart.add_item("widget", 1, 105)
        cart.apply_code("SAVE10")
        results = [cart.total_cents() for _ in range(10)]
        assert len(set(results)) == 1
        assert results[0] == 95 + 500
