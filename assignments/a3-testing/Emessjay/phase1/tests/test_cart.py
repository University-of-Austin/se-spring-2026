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
