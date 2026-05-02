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
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
            raise ValueError(f"capacity must be a positive integer, got {capacity!r}")
        self._capacity = capacity
        self._data: OrderedDict[Any, _Entry] = OrderedDict()

    def _is_expired(self, entry: _Entry) -> bool:
        return entry.expires_at is not None and time.monotonic() >= entry.expires_at

    def _purge_expired(self) -> None:
        for k in [k for k, e in self._data.items() if self._is_expired(e)]:
            del self._data[k]

    def put(self, key: Any, value: Any, ttl: float | None = None) -> None:
        expires_at = None if ttl is None else time.monotonic() + ttl

        if key in self._data:
            entry = self._data[key]
            entry.value = value
            entry.expires_at = expires_at
            self._data.move_to_end(key)
            return

        self._purge_expired()
        while len(self._data) >= self._capacity:
            self._data.popitem(last=False)

        self._data[key] = _Entry(value, expires_at)

    def get(self, key: Any) -> Any:
        if key not in self._data:
            raise KeyError(key)

        entry = self._data[key]
        if self._is_expired(entry):
            del self._data[key]
            raise KeyError(key)

        self._data.move_to_end(key)
        return entry.value

    def __len__(self) -> int:
        return sum(1 for e in self._data.values() if not self._is_expired(e))
