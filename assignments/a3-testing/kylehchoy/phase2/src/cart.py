"""Shopping cart with promo codes."""
from decimal import Decimal, ROUND_HALF_EVEN

KNOWN_CODES = {"SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"}
PERCENT_RATES = {"SAVE10": Decimal("0.10"), "SAVE20": Decimal("0.20")}
FLAT_DISCOUNT = 500
SHIPPING_FLAT = 500
FREESHIP_THRESHOLD = 5000


class Cart:
    def __init__(self) -> None:
        self._items: dict[str, tuple[int, int]] = {}
        self._codes: set[str] = set()

    def add_item(self, sku: str, qty: int, unit_price_cents: int) -> None:
        if type(qty) is not int or qty < 1:
            raise ValueError(f"qty must be positive int, got {qty!r}")
        if type(unit_price_cents) is not int or unit_price_cents < 0:
            raise ValueError(f"unit_price_cents must be non-negative int, got {unit_price_cents!r}")
        if sku in self._items:
            raise ValueError(f"sku {sku!r} already in cart")
        self._items[sku] = (qty, unit_price_cents)

    def apply_code(self, code: str) -> bool:
        if code not in KNOWN_CODES:
            return False
        if code in self._codes:
            return False
        # C4: SAVE10/SAVE20 mutually exclusive — reject if any percent code already applied.
        if code in PERCENT_RATES and self._codes & PERCENT_RATES.keys():
            return False
        self._codes.add(code)
        return True

    def total_cents(self) -> int:
        # C7: empty cart total is 0 regardless of codes.
        if not self._items:
            return 0

        # C5 step 1: subtotal from line items.
        subtotal = sum(qty * price for qty, price in self._items.values())

        # C5 step 2: BOGO_BAGEL discount, evaluated against current items.
        if "BOGO_BAGEL" in self._codes and "bagel" in self._items:
            qty, price = self._items["bagel"]
            subtotal -= (qty // 2) * price

        # C5 step 3: percent discount on post-BOGO subtotal, banker's rounded (C6).
        for code, rate in PERCENT_RATES.items():
            if code in self._codes:
                raw = Decimal(subtotal) * rate
                subtotal -= int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
                break  # mutual exclusion enforced in apply_code

        # C5 step 4: FLAT5 with clamp at 0.
        if "FLAT5" in self._codes:
            subtotal = max(0, subtotal - FLAT_DISCOUNT)

        # C5 step 5: shipping unless FREESHIP and post-discount subtotal >= 5000.
        if "FREESHIP" not in self._codes or subtotal < FREESHIP_THRESHOLD:
            subtotal += SHIPPING_FLAT

        return subtotal
