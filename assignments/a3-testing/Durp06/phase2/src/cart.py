"""Shopping cart with promo codes.

Buggy implementation distributed to students at Phase 2.
"""
from __future__ import annotations

# A18 fix (C6): use ROUND_HALF_EVEN (banker's rounding) instead of ROUND_HALF_UP
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
        # A19 fix (C2): do NOT normalize to uppercase; compare raw code string
        if code not in KNOWN_CODES:
            return False

        if code in self._codes:
            return False

        # A13 fix (C4): SAVE10 and SAVE20 are mutually exclusive
        if code in PERCENT_CODES and any(c in PERCENT_CODES for c in self._codes):
            return False

        self._codes.add(code)
        return True

    def total_cents(self) -> int:
        # A20 fix (C7): empty cart returns 0 unconditionally, before any logic
        if not self._items:
            return 0

        subtotal = sum(qty * price for qty, price in self._items.values())

        # Step 1: BOGO
        # H3 fix (C3): bagel-presence check is anchored at total_cents() time,
        # NOT at apply_code() time. If apply_code(BOGO) was called before the
        # bagel was added but the bagel is in the cart now, BOGO applies.
        if "BOGO_BAGEL" in self._codes and "bagel" in self._items:
            qty, price = self._items["bagel"]
            # A17 fix (C3): free units = qty // 2, not (qty - 1) // 2
            free_units = qty // 2
            subtotal -= free_units * price

        # Step 2: percent discount (A14 fix C5: apply percent BEFORE FLAT5)
        percent_rates = [PERCENT_CODES[c] for c in self._codes if c in PERCENT_CODES]
        if percent_rates:
            percent = sum(percent_rates, Decimal(0))
            raw = Decimal(subtotal) * percent
            # A18 fix (C6): banker's rounding
            discount = int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
            subtotal = subtotal - discount

        # Step 3: FLAT5 discount then clamp at 0
        if "FLAT5" in self._codes:
            subtotal -= FLAT_DISCOUNT
            # A15 fix (C5): clamp pre-shipping total at 0
            if subtotal < 0:
                subtotal = 0

        # Step 4: shipping — A16 fix (C5): FREESHIP at >= threshold, not strictly >
        # H3 fix: compare against post-FLAT5/post-clamp subtotal
        if "FREESHIP" in self._codes:
            if subtotal < FREESHIP_THRESHOLD:
                subtotal += SHIPPING_FLAT
        else:
            subtotal += SHIPPING_FLAT

        return subtotal
