"""In-memory sliding-window rate limits (single host, §25.1 H8)."""
from __future__ import annotations

import threading
import time
from collections import deque


class Limiter:
    """At most ``limit`` hits per ``window`` seconds for each key."""

    def __init__(self, limit: int, window: float = 60.0, *, max_keys: int = 10_000) -> None:
        self.limit = limit
        self.window = window
        self.max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def take(self, key: str, *, now: float | None = None) -> bool:
        t = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.get(key)
            if hits is None:
                if len(self._hits) >= self.max_keys:
                    self._sweep(t)
                hits = self._hits[key] = deque()
            while hits and hits[0] <= t - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(t)
            return True

    def _sweep(self, t: float) -> None:
        for k in [k for k, h in self._hits.items() if not h or h[-1] <= t - self.window]:
            del self._hits[k]
        if len(self._hits) >= self.max_keys:  # still full: drop the oldest keys
            for k in sorted(self._hits, key=lambda k: self._hits[k][-1])[: len(self._hits) // 2]:
                del self._hits[k]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
