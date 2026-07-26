"""Async-safe token-bucket rate limiter."""

from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """Đơn giản: spacing min-interval giữa các call.

    # TODO(user): tuần 9 — nâng cấp thành sliding-window hoặc token-bucket
        chính xác hơn nếu cần.
    """

    def __init__(self, calls_per_second: float = 1.0) -> None:
        if calls_per_second <= 0:
            raise ValueError("calls_per_second phải > 0")
        self._min_interval = 1.0 / calls_per_second
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()