import pytest
from cart import Cart


def test_c1_invalid_qty_raises():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("dog", 0, 100)

def test_c1_negative_price_raises():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add_item("dog", 1, -100)
    
def test_c1_duplicate_sku_raises():
    cart = Cart()
    cart.add_item("dog", 1, 100)
    with pytest.raises(ValueError):
        cart.add_item("dog", 1, 200)

def test_c2_valid_code_returns_true():
    cart = Cart()
    assert cart.apply_code("SAVE10") == True

def test_c2_unknown_code_returns_false():
    cart = Cart()
    assert cart.apply_code("INVALID") == False

def test_c2_duplicate_code_returns_false():
    cart = Cart()
    cart.apply_code("SAVE10")
    assert cart.apply_code("SAVE10") == False

def test_c2_case_sensitive_code():
    cart = Cart()
    assert cart.apply_code("save10") == False

def test_c3_save10_discount():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)  # $100 shirt
    cart.apply_code("SAVE10")
    # 10000 - 10% = 9000, plus 500 shipping = 9500
    assert cart.total_cents() == 9500

def test_c3_save20_discount():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)  # $100 shirt
    cart.apply_code("SAVE20")
    # 10000 - 20% = 8000, plus 500 shipping = 8500
    assert cart.total_cents() == 8500

def test_c3_flat5_discount():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)  # $100 shirt
    cart.apply_code("FLAT5")
    # 10000 - 500 = 9500, plus 500 shipping = 10000
    assert cart.total_cents() == 10000

def test_c3_bogo_bagel():
    cart = Cart()
    cart.add_item("bagel", 2, 300)  # 2 bagels at $3.00 each
    cart.apply_code("BOGO_BAGEL")
    # 1 free bagel, so pay for 1: 300, plus 500 shipping = 800
    assert cart.total_cents() == 800

def test_c3_freeship():
    cart = Cart()
    cart.add_item("widget", 1, 5000)  # exactly $50.00
    cart.apply_code("FREESHIP")
    # 5000 >= 5000 so shipping waived, total = 5000
    assert cart.total_cents() == 5000

def test_c3_bogo_bagel_no_bagel_in_cart():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    assert cart.apply_code("BOGO_BAGEL") == True
    # no bagel so no discount, 10000 + 500 shipping = 10500
    assert cart.total_cents() == 10500


def test_c3_bogo_bagel_odd_quantity():
    cart = Cart()
    cart.add_item("bagel", 3, 400)  # 3 bagels at $4.00 each
    cart.apply_code("BOGO_BAGEL")
    # 3 // 2 = 1 free, pay for 2: 800, + 500 shipping = 1300
    assert cart.total_cents() == 1300

def test_c3_bogo_no_flat5_without_code():
    cart = Cart()
    cart.add_item("bagel", 2, 500)  # 2 bagels at $5.00 each
    cart.apply_code("BOGO_BAGEL")
    # 1 free, pay for 1: 500, + 500 shipping = 1000
    # FLAT5 not applied so no extra 500 off
    assert cart.total_cents() == 1000

def test_c3_no_codes_just_subtotal_and_shipping():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    # no codes applied, 10000 + 500 shipping = 10500
    assert cart.total_cents() == 10500

def test_c3_bogo_bagel_only_applies_to_bagels():
    cart = Cart()
    cart.add_item("bagel", 2, 500)
    cart.add_item("apple", 2, 300)
    cart.apply_code("BOGO_BAGEL")
    # 1 bagel free: 500, apples full price: 600, + 500 shipping = 1600
    assert cart.total_cents() == 1600

def test_c4_save10_and_save20_mutually_exclusive():
    cart = Cart()
    cart.apply_code("SAVE10")
    assert cart.apply_code("SAVE20") == False

def test_c4_save20_and_save10_mutually_exclusive():
    cart = Cart()
    cart.apply_code("SAVE20")
    assert cart.apply_code("SAVE10") == False

def test_c4_flat5_stacks_with_save10():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    # 10000 - 10% = 9000, - 500 = 8500, + 500 shipping = 9000
    assert cart.total_cents() == 9000

def test_c4_flat5_stacks_with_save10():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    # 10000 - 10% = 9000, - 500 = 8500, + 500 shipping = 9000
    assert cart.total_cents() == 9000

def test_c4_flat5_stacks_with_save20():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    cart.apply_code("SAVE20")
    cart.apply_code("FLAT5")
    # 10000 - 20% = 8000, - 500 = 7500, + 500 shipping = 8000
    assert cart.total_cents() == 8000

def test_c4_freeship_and_flat5_independent():
    cart = Cart()
    cart.add_item("widget", 1, 4000)
    cart.apply_code("FREESHIP")
    cart.apply_code("FLAT5")
    # 4000 - 500 FLAT5 = 3500, 3500 < 5000 so shipping NOT waived
    # 3500 + 500 shipping = 4000
    assert cart.total_cents() == 4000

def test_c4_freeship_and_flat5_both_applied():
    cart = Cart()
    cart.add_item("widget", 1, 6000)
    cart.apply_code("FREESHIP")
    cart.apply_code("FLAT5")
    # 6000 - 500 FLAT5 = 5500, 5500 >= 5000 so shipping waived
    # total = 5500
    assert cart.total_cents() == 5500

def test_c5_bogo_applies_before_percent_discount():
    cart = Cart()
    cart.add_item("bagel", 2, 1000)  # 2 bagels at $10 each
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    # subtotal 2000, BOGO makes 1 free: 1000, then 10% off: 900, + 500 shipping = 1400
    assert cart.total_cents() == 1400

def test_c5_flat5_applies_after_percent_discount():
    cart = Cart()
    cart.add_item("shirt", 1, 10000)
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    # 10000 - 10% = 9000, - 500 FLAT5 = 8500, + 500 shipping = 9000
    assert cart.total_cents() == 9000

def test_c5_flat5_clamps_at_zero():
    cart = Cart()
    cart.add_item("thing", 1, 300)  # $3.00
    cart.apply_code("FLAT5")
    # 300 - 500 would be -200, clamp to 0, + 500 shipping = 500
    assert cart.total_cents() == 500    

def test_c5_freeship_exact_boundary():
    cart = Cart()
    cart.add_item("widget", 1, 5000)  # exactly $50.00
    cart.apply_code("FREESHIP")
    # 5000 >= 5000 so shipping waived, total = 5000
    assert cart.total_cents() == 5000

def test_c5_freeship_below_boundary():
    cart = Cart()
    cart.add_item("widget", 1, 4999)  # one cent below $50.00
    cart.apply_code("FREESHIP")
    # 4999 < 5000 so shipping NOT waived, total = 4999 + 500 = 5499
    assert cart.total_cents() == 5499

def test_c5_freeship_not_waived_when_discounts_drop_below_boundary():
    cart = Cart()
    cart.add_item("widget", 1, 5500)
    cart.apply_code("SAVE10")
    cart.apply_code("FREESHIP")
    # 5500 - 10% = 4950, which is < 5000, so shipping NOT waived
    # 4950 + 500 shipping = 5450
    assert cart.total_cents() == 5450    


def test_c5_freeship_not_waived_when_discounts_drop_below_boundary():
    cart = Cart()
    cart.add_item("widget", 1, 5500)
    cart.apply_code("SAVE10")
    cart.apply_code("FREESHIP")
    # 5500 - 10% = 4950, which is < 5000, so shipping NOT waived
    # 4950 + 500 shipping = 5450
    assert cart.total_cents() == 5450

def test_c5_flat5_applies_after_bogo_and_percent():
    cart = Cart()
    cart.add_item("bagel", 4, 500)  # 4 bagels at $5.00 each
    cart.apply_code("BOGO_BAGEL")
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    # subtotal 2000, BOGO makes 2 free: 1000, 10% off: 900, - 500 FLAT5: 400, + 500 shipping = 900
    assert cart.total_cents() == 900

def test_c5_freeship_not_applied_below_boundary():
    cart = Cart()
    cart.add_item("widget", 1, 4500)
    cart.apply_code("FREESHIP")
    # 4500 < 5000 so shipping NOT waived, total = 4500 + 500 = 5000
    assert cart.total_cents() == 5000

def test_c5_no_freeship_code_shipping_always_added():
    cart = Cart()
    cart.add_item("widget", 1, 5000)
    # FREESHIP not applied, so shipping always added regardless of total
    assert cart.total_cents() == 5500

def test_c6_rounding_half_even():
    cart = Cart()
    cart.add_item("thing", 1, 1005)  # $10.05
    cart.apply_code("SAVE10")
    # 10% of 1005 = 100.5, rounds half-even to 100
    # 1005 - 100 = 905, + 500 shipping = 1405
    assert cart.total_cents() == 1405


def test_c7_empty_cart_returns_zero():
    cart = Cart()
    assert cart.total_cents() == 0


def test_c7_empty_cart_with_codes_returns_zero():
    cart = Cart()
    cart.apply_code("SAVE10")
    cart.apply_code("FLAT5")
    assert cart.total_cents() == 0

def test_c7_empty_cart_no_shipping_with_freeship():
    cart = Cart()
    cart.apply_code("FREESHIP")
    assert cart.total_cents() == 0

