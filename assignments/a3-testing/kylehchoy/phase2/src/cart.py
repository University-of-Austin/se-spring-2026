"""Shopping cart with promo codes.

Phase 2 fix: implements clauses C1-C7 of the cart spec.
"""
from __future__ import annotations

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
        if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1:
            raise ValueError(f"qty must be positive int, got {qty!r}")
        if isinstance(unit_price_cents, bool) or not isinstance(unit_price_cents, int) or unit_price_cents < 0:
            raise ValueError(f"unit_price_cents must be non-negative int, got {unit_price_cents!r}")
        if sku in self._items:
            raise ValueError(f"sku {sku!r} already in cart")
        self._items[sku] = (qty, unit_price_cents)

    def apply_code(self, code: str) -> bool:
        if code not in KNOWN_CODES:
            return False
        if code in self._codes:
            return False
        # SAVE10/SAVE20 mutual exclusion (C4).
        if code in PERCENT_RATES:
            other = "SAVE20" if code == "SAVE10" else "SAVE10"
            if other in self._codes:
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
            free_units = qty // 2
            subtotal -= free_units * price

        # C5 step 3: percent discount on post-BOGO subtotal, banker's rounded (C6).
        for code, rate in PERCENT_RATES.items():
            if code in self._codes:
                raw = Decimal(subtotal) * rate
                discount = int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
                subtotal -= discount
                break  # mutual exclusion enforced in apply_code

        # C5 step 4: FLAT5 with clamp at 0.
        if "FLAT5" in self._codes:
            subtotal = max(0, subtotal - FLAT_DISCOUNT)

        # C5 step 5: shipping unless FREESHIP and post-discount subtotal >= 5000.
        if not ("FREESHIP" in self._codes and subtotal >= FREESHIP_THRESHOLD):
            subtotal += SHIPPING_FLAT

        return subtotal
