"""Shopping cart with promo codes. All monetary values are integer cents."""
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
        # Case-sensitive (C2): "SAVE10" valid, "save10" unknown.
        if code not in KNOWN_CODES:
            return False
        if code in self._codes:
            return False
        # Percent codes are mutually exclusive (C4).
        if code in PERCENT_CODES and any(c in self._codes for c in PERCENT_CODES):
            return False
        self._codes.add(code)
        return True

    def total_cents(self) -> int:
        # C7: empty cart returns 0 regardless of codes (no shipping).
        if not self._items:
            return 0

        # C5 step 1: subtotal from line items.
        subtotal = sum(qty * price for qty, price in self._items.values())

        # C5 step 2: BOGO_BAGEL — evaluated at total time so a bagel added
        # AFTER the code was applied still gets the discount.
        if "BOGO_BAGEL" in self._codes and "bagel" in self._items:
            qty, price = self._items["bagel"]
            subtotal -= (qty // 2) * price

        # C5 step 3: percent discount (banker's rounding per C6). Mutex on
        # SAVE10/SAVE20 is enforced at apply_code time, so at most one is
        # in self._codes here.
        for code, rate in PERCENT_CODES.items():
            if code in self._codes:
                raw = Decimal(subtotal) * rate
                discount = int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
                subtotal -= discount
                break

        # C5 step 4: FLAT5 (after percent), then clamp at 0.
        if "FLAT5" in self._codes:
            subtotal -= FLAT_DISCOUNT
            if subtotal < 0:
                subtotal = 0

        # C5 step 5: shipping unless FREESHIP applied AND pre-shipping >= 5000.
        if "FREESHIP" in self._codes and subtotal >= FREESHIP_THRESHOLD:
            return subtotal
        return subtotal + SHIPPING_FLAT
