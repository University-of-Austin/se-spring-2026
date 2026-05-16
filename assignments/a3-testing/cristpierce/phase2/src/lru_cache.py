"""LRU cache with optional per-entry TTL."""
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
        if capacity < 1:
            raise ValueError(f"capacity must be a positive integer, got {capacity!r}")
        self._capacity = capacity
        self._data: OrderedDict[Any, _Entry] = OrderedDict()

    def put(self, key: Any, value: Any, ttl: float | None = None) -> None:
        expires_at = None if ttl is None else time.monotonic() + ttl

        if key in self._data:
            entry = self._data[key]
            entry.value = value
            entry.expires_at = expires_at
            self._data.move_to_end(key)
            return

        # Expired entries don't consume a capacity slot.
        self._purge_expired()
        while len(self._data) >= self._capacity:
            self._data.popitem(last=False)

        self._data[key] = _Entry(value, expires_at)

    def get(self, key: Any) -> Any:
        if key not in self._data:
            raise KeyError(key)

        entry = self._data[key]
        if entry.expires_at is not None and time.monotonic() >= entry.expires_at:
            del self._data[key]
            raise KeyError(key)

        self._data.move_to_end(key)
        return entry.value

    def __len__(self) -> int:
        now = time.monotonic()
        return sum(
            1
            for e in self._data.values()
            if e.expires_at is None or now < e.expires_at
        )

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired = [
            k for k, e in self._data.items()
            if e.expires_at is not None and now >= e.expires_at
        ]
        for k in expired:
            del self._data[k]
