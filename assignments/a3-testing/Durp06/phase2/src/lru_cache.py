"""LRU cache with optional per-entry TTL.

Buggy implementation distributed to students at Phase 2. All seeded bugs are
active. Students use their Phase 1 test suite to discover and fix them.
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
        # A6 fix (C1): raise ValueError when capacity <= 0
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity!r}")
        self._capacity = capacity
        self._data: OrderedDict[Any, _Entry] = OrderedDict()

    def put(self, key: Any, value: Any, ttl: float | None = None) -> None:
        now = time.monotonic()
        expires_at = None if ttl is None else now + ttl

        if key in self._data:
            # A4 fix (C3): replace both value AND expires_at on re-put
            self._data[key].value = value
            self._data[key].expires_at = expires_at
            self._data.move_to_end(key)
            return

        # H1 fix (C4 + C7): spec C4 references len(cache) which per C7 excludes
        # expired entries. Reap expired entries first so eviction picks the
        # genuine LRU among still-valid entries, not a still-valid LRU that
        # happens to sit in front of an older expired one.
        for k in [
            k for k, e in self._data.items()
            if e.expires_at is not None and e.expires_at <= now
        ]:
            del self._data[k]

        # A5 fix (C4): evict BEFORE insert so len never exceeds capacity
        while len(self._data) >= self._capacity:
            self._data.popitem(last=False)

        self._data[key] = _Entry(value, expires_at)

    def get(self, key: Any) -> Any:
        # A2 fix (C6): raise KeyError on missing key
        if key not in self._data:
            raise KeyError(key)

        entry = self._data[key]

        # A2 fix (C6): raise KeyError on expired entry, delete it first
        now = time.monotonic()
        if entry.expires_at is not None and entry.expires_at <= now:
            del self._data[key]
            raise KeyError(key)

        # A1 fix (C5): promote to MRU on successful get
        self._data.move_to_end(key)
        return entry.value

    def __len__(self) -> int:
        # A3 fix (C7): count only non-expired entries; do not mutate
        now = time.monotonic()
        return sum(
            1 for entry in self._data.values()
            if entry.expires_at is None or entry.expires_at > now
        )
