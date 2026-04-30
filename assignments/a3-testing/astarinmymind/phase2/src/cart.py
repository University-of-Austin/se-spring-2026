"""Shopping cart with promo codes.

Fixed implementation — all seeded bugs resolved.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN

KNOWN_CODES = {"SAVE10", "SAVE20", "FLAT5", "BOGO_BAGEL", "FREESHIP"}
PERCENT_CODES = {"SAVE10": Decimal("0.10"), "SAVE20": Decimal("0.20")}
FLAT_DISCOUNT = 500
SHIPPING_FLAT = 500
FREESHIP_THRESHOLD = 5000


class Cart:
    def __init__(self) -> None:
        self._items: dict[str, tuple[int, int]] = {}
        self._codes: set[str] = set()

    def add_item(self, sku: str, qty: int, unit_price_cents: int) -> None:
        if not isinstance(qty, int) or qty < 1:
            raise ValueError(f"qty must be positive int, got {qty!r}")
        if not isinstance(unit_price_cents, int) or unit_price_cents < 0:
            raise ValueError(f"unit_price_cents must be non-negative int, got {unit_price_cents!r}")
        if sku in self._items:
            raise ValueError(f"sku {sku!r} already in cart")
        self._items[sku] = (qty, unit_price_cents)

    def apply_code(self, code: str) -> bool:
        # A19 fix: don't uppercase — codes are case-sensitive
        if code not in KNOWN_CODES:
            return False

        if code in self._codes:
            return False

        # A13 fix: SAVE10 and SAVE20 are mutually exclusive
        if code in PERCENT_CODES:
            for existing in self._codes:
                if existing in PERCENT_CODES:
                    return False

        self._codes.add(code)
        return True

    def total_cents(self) -> int:
        # A20 fix: empty cart returns 0, no shipping
        if not self._items:
            return 0

        subtotal = sum(qty * price for qty, price in self._items.values())

        # Step 2: BOGO_BAGEL discount
        # A17 fix: qty // 2, not (qty - 1) // 2
        if "BOGO_BAGEL" in self._codes and "bagel" in self._items:
            qty, price = self._items["bagel"]
            free_units = qty // 2
            subtotal -= free_units * price

        # Step 3: percent discount
        # A14 fix: apply percent BEFORE flat5
        percent_rates = [PERCENT_CODES[c] for c in self._codes if c in PERCENT_CODES]
        if percent_rates:
            percent = percent_rates[0]
            raw = Decimal(subtotal) * percent
            # A18 fix: ROUND_HALF_EVEN, not ROUND_HALF_UP
            discount = int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
            subtotal -= discount

        # Step 4: FLAT5
        if "FLAT5" in self._codes:
            subtotal -= FLAT_DISCOUNT
            # A15 fix: clamp at 0
            if subtotal < 0:
                subtotal = 0

        # Step 5: shipping
        # A16 fix: >= not >
        if "FREESHIP" in self._codes and subtotal >= FREESHIP_THRESHOLD:
            pass  # shipping waived
        else:
            subtotal += SHIPPING_FLAT

        return subtotal
