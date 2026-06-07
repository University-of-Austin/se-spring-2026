"""Shopping cart with promo codes.

Buggy implementation distributed to students at Phase 2.
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
        if code not in KNOWN_CODES:
            return False
        if code in self._codes:
            return False
        if code == "SAVE10" and "SAVE20" in self._codes:
            return False
        if code == "SAVE20" and "SAVE10" in self._codes:
            return False

        self._codes.add(code)
        return True

    def total_cents(self) -> int:
        if not self._items:
            return 0

        subtotal = sum(qty * price for qty, price in self._items.values())

        if "BOGO_BAGEL" in self._codes and "bagel" in self._items:
            qty, price = self._items["bagel"]
            free_units = qty // 2
            subtotal -= free_units * price

        percent_rates = [PERCENT_CODES[c] for c in self._codes if c in PERCENT_CODES]
        if percent_rates:
            percent = sum(percent_rates, Decimal(0))
            raw = Decimal(subtotal) * percent
            discount = int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
            subtotal -= discount

        if "FLAT5" in self._codes:
            subtotal -= FLAT_DISCOUNT

        if subtotal < 0:
            subtotal = 0

        if "FREESHIP" in self._codes and subtotal >= FREESHIP_THRESHOLD:
            return subtotal
        return subtotal + SHIPPING_FLAT
