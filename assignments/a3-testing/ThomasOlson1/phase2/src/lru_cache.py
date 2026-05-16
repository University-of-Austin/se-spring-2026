"""LRU cache with optional per-entry TTL.

Phase 2 fix.
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
        # C1: capacity must be a positive integer (>= 1).
        if capacity < 1:
            raise ValueError(f"capacity must be a positive integer, got {capacity!r}")
        self._capacity = capacity
        self._data: OrderedDict[Any, _Entry] = OrderedDict()

    def put(self, key: Any, value: Any, ttl: float | None = None) -> None:
        expires_at = None if ttl is None else time.monotonic() + ttl

        if key in self._data:
            # C3: re-put completely replaces value, TTL, and expiration time.
            entry = self._data[key]
            entry.value = value
            entry.expires_at = expires_at
            self._data.move_to_end(key)
            return

        # C7: expired entries don't count toward capacity. Drop them first
        # so we don't unnecessarily evict a live LRU entry to make room
        # for a new key when an expired ghost is occupying internal state.
        now = time.monotonic()
        expired_keys = [
            k for k, e in self._data.items()
            if e.expires_at is not None and e.expires_at <= now
        ]
        for k in expired_keys:
            del self._data[k]

        # C4: evict LRU if at capacity, BEFORE inserting the new key.
        while len(self._data) >= self._capacity:
            self._data.popitem(last=False)

        self._data[key] = _Entry(value, expires_at)

    def get(self, key: Any) -> Any:
        # C6: missing key raises KeyError.
        if key not in self._data:
            raise KeyError(key)

        entry = self._data[key]

        # C6: expired entries raise KeyError and are removed.
        if entry.expires_at is not None and entry.expires_at <= time.monotonic():
            del self._data[key]
            raise KeyError(key)

        # C5: get on an existing live entry promotes it to most-recently-used.
        self._data.move_to_end(key)
        return entry.value

    def __len__(self) -> int:
        # C7: count only non-expired entries.
        now = time.monotonic()
        return sum(
            1 for e in self._data.values()
            if e.expires_at is None or e.expires_at > now
        )
