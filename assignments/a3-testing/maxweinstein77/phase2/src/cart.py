"""Shopping cart with promo codes."""
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
        # Codes are case-sensitive: only the exact uppercase form is accepted.
        if code not in KNOWN_CODES:
            return False

        if code in self._codes:
            return False

        # SAVE10 and SAVE20 are mutually exclusive.
        if code == "SAVE10" and "SAVE20" in self._codes:
            return False
        if code == "SAVE20" and "SAVE10" in self._codes:
            return False

        self._codes.add(code)
        return True

    def total_cents(self) -> int:
        # Empty cart: total is 0 regardless of codes; no shipping.
        if not self._items:
            return 0

        # Step 1: subtotal from line items.
        subtotal = sum(qty * price for qty, price in self._items.values())

        # Step 2: subtract BOGO_BAGEL discount if applied AND a bagel line exists
        # at the time total_cents is computed (per spec C3).
        if "BOGO_BAGEL" in self._codes and "bagel" in self._items:
            qty, price = self._items["bagel"]
            free_units = qty // 2
            subtotal -= free_units * price

        # Step 3: percent discount on the post-BOGO subtotal.
        percent: Decimal | None = None
        if "SAVE10" in self._codes:
            percent = PERCENT_CODES["SAVE10"]
        elif "SAVE20" in self._codes:
            percent = PERCENT_CODES["SAVE20"]

        if percent is not None:
            raw = Decimal(subtotal) * percent
            discount = int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
            subtotal = subtotal - discount

        # Step 4: subtract FLAT5, clamp at 0.
        if "FLAT5" in self._codes:
            subtotal -= FLAT_DISCOUNT
            if subtotal < 0:
                subtotal = 0

        # Step 5: shipping. Non-empty cart adds 500 cents UNLESS FREESHIP applied
        # AND post-discount pre-shipping subtotal >= 5000.
        if "FREESHIP" in self._codes and subtotal >= FREESHIP_THRESHOLD:
            pass  # shipping waived
        else:
            subtotal += SHIPPING_FLAT

        return subtotal
