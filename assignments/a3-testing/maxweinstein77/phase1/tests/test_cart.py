from cart import Cart
import pytest

## C1. add_item validation

# What if I do a typical valid add_item call?
def test_c1_valid_add_item_works():
    cart = Cart()
    cart.add_item("widget", 2, 500)

# What if qty = 1 (the smallest valid quantity)?
def test_c1_qty_one_works():
    cart = Cart()
    cart.add_item("widget", 1, 500)

# What if qty = 0?
def test_c1_qty_zero_raises_value_error():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", 0, 500)

# What if qty is negative?
def test_c1_negative_qty_raises_value_error():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", -5, 500)

# What if unit_price_cents = 0 (a free item)?
def test_c1_zero_unit_price_works():
    cart = Cart()
    cart.add_item("freebie", 1, 0)

# What if unit_price_cents is negative?
def test_c1_negative_unit_price_raises_value_error():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("widget", 1, -1)

# What if I add the same SKU twice?
def test_c1_duplicate_sku_raises_value_error():
    cart = Cart()
    cart.add_item("widget", 1, 500)
    with pytest.raises(ValueError):
        cart.add_item("widget", 2, 600)

# What if I add a duplicate SKU but with other items in between?
def test_c1_duplicate_sku_with_other_items_in_between_still_raises():
    cart = Cart()
    cart.add_item("widget", 1, 500)
    cart.add_item("bagel", 2, 300)
    cart.add_item("shirt", 1, 1000)
    with pytest.raises(ValueError):
        cart.add_item("widget", 1, 500)

# What if a successful add is followed by a failed add (does the cart stay clean)?
def test_c1_failed_add_does_not_partially_mutate_cart():
    cart = Cart()
    cart.add_item("widget", 1, 500)
    with pytest.raises(ValueError):
        cart.add_item("bagel", 0, 300)
    assert cart.total_cents() == 1000

## C2. apply_code return values

# What if I apply a known code?
def test_c2_apply_known_code_returns_true():
    cart = Cart()
    assert cart.apply_code("SAVE10") is True

# What if I apply an unknown code?
def test_c2_apply_unknown_code_returns_false():
    cart = Cart()
    assert cart.apply_code("BLAHBLAH") is False

# What if I apply the same code twice?
def test_c2_apply_same_code_twice_returns_false_on_second():
    cart = Cart()
    cart.apply_code("SAVE10")
    assert cart.apply_code("SAVE10") is False

# What if I apply a mixed-case version of a valid code?
def test_c2_apply_mixed_case_code_returns_false():
    cart = Cart()
    assert cart.apply_code("Save10") is False

# What if I apply an all-lowercase version of a valid code?
def test_c2_apply_lowercase_code_returns_false():
    cart = Cart()
    assert cart.apply_code("save10") is False

# What if I apply SAVE20 twice?
def test_c2_apply_save20_twice_returns_false_on_second():
    cart = Cart()
    cart.apply_code("SAVE20")
    assert cart.apply_code("SAVE20") is False

# What if I apply FLAT5 twice?
def test_c2_apply_flat5_twice_returns_false_on_second():
    cart = Cart()
    cart.apply_code("FLAT5")
    assert cart.apply_code("FLAT5") is False

# What if I apply FREESHIP twice?
def test_c2_apply_freeship_twice_returns_false_on_second():
    cart = Cart()
    cart.apply_code("FREESHIP")
    assert cart.apply_code("FREESHIP") is False

## C3. Known codes and their effects

# What if a basic cart has no codes applied?
def test_c3_baseline_no_codes():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.total_cents() == 1500

# What if SAVE10 is applied?
def test_c3_save10_applies_ten_percent_off():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 1400

# What if SAVE20 is applied?
def test_c3_save20_applies_twenty_percent_off():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    cart.apply_code("SAVE20")
    assert cart.total_cents() == 1300

# What if FLAT5 is applied?
def test_c3_flat5_takes_500_cents_off():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 1000

# What if BOGO_BAGEL is applied with bagels in the cart?
def test_c3_bogo_bagel_makes_half_free():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 800

# What if BOGO_BAGEL is applied but no bagel exists?
def test_c3_bogo_bagel_with_no_bagel_has_no_effect_but_is_applied():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.total_cents() == 1500
    assert cart.apply_code("BOGO_BAGEL") is False

# What if FREESHIP is applied with pre-shipping subtotal exactly at 5000?
def test_c3_freeship_at_exactly_5000_waives_shipping():
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5000

# What if FREESHIP is applied with pre-shipping subtotal just below 5000?
def test_c3_freeship_just_below_5000_does_not_waive():
    cart = Cart()
    cart.add_item("widget", 1, 4999)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5499

# What if pre-shipping is below 5000 but post-shipping would be at 5000?
def test_c3_freeship_uses_pre_shipping_not_post_shipping_for_threshold():
    cart = Cart()
    cart.add_item("widget", 1, 4500)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 5000

# What if I apply BOGO_BAGEL on an empty cart and then add bagels?
def test_c3_bogo_applied_first_then_bagel_added_still_discounts():
    cart = Cart()
    assert cart.apply_code("BOGO_BAGEL") is True
    cart.add_item("bagel", 2, 300)
    assert cart.total_cents() == 800

# What if I apply FREESHIP on an empty cart and then add an expensive item?
def test_c3_freeship_applied_first_then_expensive_item_still_waives():
    cart = Cart()
    assert cart.apply_code("FREESHIP") is True
    cart.add_item("widget", 1, 6000)
    assert cart.total_cents() == 6000

# What if I have items with SKU "Bagel" (capitalized) and apply BOGO_BAGEL?
def test_c3_bogo_does_not_match_capitalized_bagel_sku():
    cart = Cart()
    cart.add_item("Bagel", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 1100

# What if I have items with SKU "bagel_cream_cheese" and apply BOGO_BAGEL?
def test_c3_bogo_does_not_match_bagel_prefix_sku():
    cart = Cart()
    cart.add_item("bagel_cream_cheese", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 1100

## C4. Stacking rules

# What if I apply SAVE10 and then SAVE20?
def test_c4_save10_then_save20_rejects_save20():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("SAVE20") is False
    assert cart.total_cents() == 1400

# What if I apply SAVE20 and then SAVE10 (reverse direction)?
def test_c4_save20_then_save10_rejects_save10():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("SAVE10") is False
    assert cart.total_cents() == 1300

# What if I stack FLAT5 with SAVE10?
def test_c4_flat5_stacks_with_save10():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.total_cents() == 900

# What if I stack FLAT5 with SAVE20?
def test_c4_flat5_stacks_with_save20():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.total_cents() == 800

# What if I stack BOGO_BAGEL with SAVE10?
def test_c4_bogo_bagel_stacks_with_save10():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("SAVE10") is True
    assert cart.total_cents() == 770

# What if I stack BOGO_BAGEL with SAVE20?
def test_c4_bogo_bagel_stacks_with_save20():
    cart = Cart()
    cart.add_item("bagel", 2, 500)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("SAVE20") is True
    assert cart.total_cents() == 900

# What if I stack FREESHIP with SAVE10?
def test_c4_freeship_stacks_with_save10():
    cart = Cart()
    cart.add_item("widget", 1, 6000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FREESHIP") is True
    assert cart.total_cents() == 5400

# What if I stack FREESHIP with SAVE20?
def test_c4_freeship_stacks_with_save20():
    cart = Cart()
    cart.add_item("widget", 1, 7000)
    assert cart.apply_code("SAVE20") is True
    assert cart.apply_code("FREESHIP") is True
    assert cart.total_cents() == 5600

# What if I stack BOGO with FLAT5 (no percent)?
def test_c4_bogo_stacks_with_flat5_no_percent():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.total_cents() == 500

# What if I stack FLAT5 with FREESHIP (no percent)?
def test_c4_flat5_stacks_with_freeship_no_percent():
    cart = Cart()
    cart.add_item("widget", 1, 6000)
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True
    assert cart.total_cents() == 5500

# What if I stack BOGO with FREESHIP (no percent)?
def test_c4_bogo_stacks_with_freeship_no_percent():
    cart = Cart()
    cart.add_item("bagel", 4, 3000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("FREESHIP") is True
    assert cart.total_cents() == 6000

# What if I stack BOGO + FLAT5 + FREESHIP (three way, no percent)?
def test_c4_bogo_flat5_freeship_three_way_stack_no_percent():
    cart = Cart()
    cart.add_item("bagel", 4, 3000)
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("FREESHIP") is True
    assert cart.total_cents() == 5500

# What if all four compatible codes (SAVE10, FLAT5, BOGO_BAGEL, FREESHIP) are stacked?
def test_c4_all_four_compatible_codes_stack():
    cart = Cart()
    cart.add_item("bagel", 4, 4000)
    assert cart.apply_code("SAVE10") is True
    assert cart.apply_code("FLAT5") is True
    assert cart.apply_code("BOGO_BAGEL") is True
    assert cart.apply_code("FREESHIP") is True
    assert cart.total_cents() == 6700

## C5. Application order

# What if FLAT5 alone would take the pre-shipping total below 0?
def test_c5_flat5_clamps_to_zero_when_subtotal_below_500():
    cart = Cart()
    cart.add_item("widget", 1, 200)
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 500

# What if SAVE10 + FLAT5 combined would take the pre-shipping total below 0?
def test_c5_flat5_plus_save10_clamps_to_zero():
    cart = Cart()
    cart.add_item("widget", 1, 400)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 500

# What if FLAT5 reduces the subtotal to exactly 0 (boundary, not clamping)?
def test_c5_flat5_reduces_subtotal_to_exactly_zero():
    cart = Cart()
    cart.add_item("widget", 1, 500)
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 500

# What if BOGO is applied with qty = 1 (qty // 2 = 0)?
def test_c5_bogo_qty_one_has_no_effect():
    cart = Cart()
    cart.add_item("bagel", 1, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 800

# What if BOGO is applied with an odd qty = 3?
def test_c5_bogo_qty_three_makes_one_free_two_paid():
    cart = Cart()
    cart.add_item("bagel", 3, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 1100

# What if BOGO is applied with an even qty = 4?
def test_c5_bogo_qty_four_makes_two_free_two_paid():
    cart = Cart()
    cart.add_item("bagel", 4, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 1100

# What if BOGO is applied with an odd qty = 5?
def test_c5_bogo_qty_five_makes_two_free_three_paid():
    cart = Cart()
    cart.add_item("bagel", 5, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 1400

# What if BOGO is applied with a larger qty = 10?
def test_c5_bogo_qty_ten_makes_five_free_five_paid():
    cart = Cart()
    cart.add_item("bagel", 10, 300)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 2000

# What if I apply multiple codes to an empty cart?
def test_c5_empty_cart_with_multiple_codes_returns_zero():
    cart = Cart()
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 0

# What if a cart has multiple different items with SAVE10 applied?
def test_c5_multi_item_cart_with_save10():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    cart.add_item("shirt", 1, 2000)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 3200

# What if a cart has multiple different items with SAVE20 applied?
def test_c5_multi_item_cart_with_save20():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    cart.add_item("shirt", 1, 2000)
    cart.apply_code("SAVE20")
    assert cart.total_cents() == 2900

# What if a cart has multiple different items with FLAT5 applied?
def test_c5_multi_item_cart_with_flat5():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    cart.add_item("shirt", 1, 2000)
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 3000

# What if a cart has bagels and other items with BOGO applied?
def test_c5_bogo_bagel_only_affects_bagel_line():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.add_item("widget", 1, 500)
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 1300

# What if FREESHIP is checked against the original subtotal vs the post-discount subtotal?
def test_c5_freeship_uses_post_discount_pre_shipping_subtotal():
    cart = Cart()
    cart.add_item("widget", 1, 5500)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 4950

# What if my cart only has a free item and I apply FREESHIP?
def test_c5_free_item_with_freeship_still_pays_shipping():
    cart = Cart()
    cart.add_item("freebie", 1, 0)
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 500

# What if I apply FLAT5 chronologically before SAVE10 (does spec order still win)?
def test_c5_apply_flat5_before_save10_still_uses_spec_order():
    cart = Cart()
    cart.add_item("widget", 1, 1000)
    cart.apply_code("FLAT5")
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 900

# What if I apply SAVE10 chronologically before BOGO (does spec order still win)?
def test_c5_apply_save10_before_bogo_still_uses_spec_order():
    cart = Cart()
    cart.add_item("bagel", 2, 300)
    cart.apply_code("SAVE10")
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 770

# What if I apply codes in fully reverse-spec order (FREESHIP, FLAT5, SAVE10, BOGO)?
def test_c5_apply_codes_in_reverse_spec_order():
    cart = Cart()
    cart.add_item("bagel", 4, 4000)
    cart.apply_code("FREESHIP")
    cart.apply_code("FLAT5")
    cart.apply_code("SAVE10")
    cart.apply_code("BOGO_BAGEL")
    assert cart.total_cents() == 6700

## C6. Rounding (banker's rounding / half-even)

# What if SAVE10 produces 0.5 cents (banker's: rounds to 0 because 0 is even)?
def test_c6_save10_rounds_half_to_zero():
    cart = Cart()
    cart.add_item("widget", 1, 5)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 505

# What if SAVE10 produces 2.5 cents (banker's: rounds to 2 because 2 is even)?
def test_c6_save10_rounds_half_down_to_even():
    cart = Cart()
    cart.add_item("widget", 1, 25)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 523

# What if SAVE10 produces 3.5 cents (banker's: rounds to 4 because 4 is even)?
def test_c6_save10_rounds_half_up_to_even():
    cart = Cart()
    cart.add_item("widget", 1, 35)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 531

# What if SAVE10 produces 4.5 cents (banker's: rounds to 4 because 4 is even)?
def test_c6_save10_rounds_4_5_down_to_even():
    cart = Cart()
    cart.add_item("widget", 1, 45)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 541

# What if SAVE10 produces 5.5 cents (banker's: rounds to 6 because 6 is even)?
def test_c6_save10_rounds_5_5_up_to_even():
    cart = Cart()
    cart.add_item("widget", 1, 55)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 549

# What if SAVE10 produces 6.5 cents (banker's: rounds to 6 because 6 is even)?
def test_c6_save10_rounds_6_5_down_to_even():
    cart = Cart()
    cart.add_item("widget", 1, 65)
    cart.apply_code("SAVE10")
    assert cart.total_cents() == 559

## C7. Empty cart

# What if the cart is empty and no codes are applied?
def test_c7_empty_cart_with_no_codes_returns_zero():
    cart = Cart()
    assert cart.total_cents() == 0

# What if the cart is empty and SAVE20 is applied?
def test_c7_empty_cart_with_save20_returns_zero():
    cart = Cart()
    cart.apply_code("SAVE20")
    assert cart.total_cents() == 0
