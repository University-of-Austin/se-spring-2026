"""Shopping cart with promo codes.

Phase 2 fix.
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
        # C2: codes are case-sensitive — exact-match against the known set.
        if code not in KNOWN_CODES:
            return False
        # C2: already-applied returns False.
        if code in self._codes:
            return False
        # C4: SAVE10 and SAVE20 are mutually exclusive.
        if code == "SAVE10" and "SAVE20" in self._codes:
            return False
        if code == "SAVE20" and "SAVE10" in self._codes:
            return False
        self._codes.add(code)
        return True

    def total_cents(self) -> int:
        # C7: empty cart returns 0 regardless of which codes have been applied.
        if not self._items:
            return 0

        # C5 step 1: subtotal across all line items.
        subtotal = sum(qty * price for qty, price in self._items.values())

        # C5 step 2: BOGO_BAGEL — qty // 2 free bagel units, only if a bagel
        # line item exists at total_cents time (per C3).
        if "BOGO_BAGEL" in self._codes and "bagel" in self._items:
            qty, price = self._items["bagel"]
            free_units = qty // 2
            subtotal -= free_units * price

        # C5 step 3: percent discount on post-BOGO subtotal.
        # C6: banker's rounding (ROUND_HALF_EVEN) on the discount cents.
        percent_code = next(
            (c for c in self._codes if c in PERCENT_CODES), None
        )
        if percent_code is not None:
            rate = PERCENT_CODES[percent_code]
            raw_discount = Decimal(subtotal) * rate
            discount = int(raw_discount.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
            subtotal -= discount

        # C5 step 4: FLAT5 after percent. Clamp pre-shipping at 0 if negative.
        if "FLAT5" in self._codes:
            subtotal -= FLAT_DISCOUNT
            if subtotal < 0:
                subtotal = 0

        # C5 step 5: shipping is added unless FREESHIP is applied AND the
        # post-discount pre-shipping subtotal is >= 5000.
        if "FREESHIP" in self._codes and subtotal >= FREESHIP_THRESHOLD:
            pass  # shipping waived
        else:
            subtotal += SHIPPING_FLAT

        return subtotal
