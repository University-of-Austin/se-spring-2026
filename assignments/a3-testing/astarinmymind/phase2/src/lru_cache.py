"""LRU cache with optional per-entry TTL.

Fixed implementation — all seeded bugs resolved.
"""
from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any


class _Entry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, expires_at: float | None):
        self.value = value
        self.expires_at = expires_at


class LRUCache:
    def __init__(self, capacity: int) -> None:
        # A6 fix: validate capacity is a positive integer
        if capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {capacity}")
        self._capacity = capacity
        self._data: OrderedDict[Any, _Entry] = OrderedDict()

    def put(self, key: Any, value: Any, ttl: float | None = None) -> None:
        expires_at = None if ttl is None else time.monotonic() + ttl

        if key in self._data:
            # A4 fix: update expires_at too, not just value
            self._data[key].value = value
            self._data[key].expires_at = expires_at
            self._data.move_to_end(key)
            return

        # A5 fix: evict when at capacity, not capacity + 1
        while len(self._data) >= self._capacity:
            self._data.popitem(last=False)

        self._data[key] = _Entry(value, expires_at)

    def get(self, key: Any) -> Any:
        # A2 fix: raise KeyError instead of returning None for missing keys
        if key not in self._data:
            raise KeyError(key)

        entry = self._data[key]

        # A2 fix: check expiration on get
        if entry.expires_at is not None and time.monotonic() >= entry.expires_at:
            del self._data[key]
            raise KeyError(key)

        # A1 fix: promote to most-recently-used on get
        self._data.move_to_end(key)
        return entry.value

    def __len__(self) -> int:
        # A3 fix: exclude expired entries from count
        now = time.monotonic()
        return sum(
            1 for entry in self._data.values()
            if entry.expires_at is None or entry.expires_at > now
        )
