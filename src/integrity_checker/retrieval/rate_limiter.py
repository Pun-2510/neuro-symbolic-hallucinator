"""Async-safe token-bucket rate limiter với exponential backoff support."""

from __future__ import annotations

import asyncio
import random
import time


class RateLimiter:
    """Async-safe rate limiter với token-bucket và exponential backoff.

    Features:
        - Min interval spacing giữa các calls
        - Exponential backoff khi bị rate limited
        - Jitter để tránh thundering herd
        - Respect Retry-After header
    """

    def __init__(
        self,
        calls_per_second: float = 1.0,
        burst_size: int | None = None,
    ) -> None:
        if calls_per_second <= 0:
            raise ValueError("calls_per_second phải > 0")
        self._min_interval = 1.0 / calls_per_second
        self._burst_size = burst_size
        self._lock = asyncio.Lock()
        self._last_call = 0.0

        # Backoff state
        self._backoff_until: float = 0.0
        self._consecutive_failures: int = 0
        self._base_backoff: float = 5.0  # seconds
        self._max_backoff: float = 300.0  # 5 minutes max

    async def wait(self) -> None:
        """Wait until rate limit allows next request."""
        async with self._lock:
            now = time.monotonic()

            # Check backoff period
            if now < self._backoff_until:
                wait_time = self._backoff_until - now
                # Add jitter to prevent thundering herd
                jitter = random.uniform(0, wait_time * 0.2)
                total_wait = wait_time + jitter
                if total_wait > 0:
                    await asyncio.sleep(total_wait)
                now = time.monotonic()

            # Check min interval
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)

            self._last_call = time.monotonic()

    def report_rate_limited(self, retry_after: int | None = None) -> None:
        """Báo cáo bị rate limit - tăng backoff.

        Args:
            retry_after: Số giây server yêu cầu chờ (nếu có Retry-After header)
        """
        self._consecutive_failures += 1

        if retry_after and retry_after > 0:
            # Respect server's Retry-After header
            self._backoff_until = time.monotonic() + retry_after
        else:
            # Exponential backoff: 5, 10, 20, 40, 80... seconds
            backoff = min(
                self._base_backoff * (2 ** self._consecutive_failures),
                self._max_backoff
            )
            # Add jitter (0-30% of backoff time)
            jitter = random.uniform(0, backoff * 0.3)
            self._backoff_until = time.monotonic() + backoff + jitter

    def report_success(self) -> None:
        """Báo cáo request thành công - reset backoff."""
        self._consecutive_failures = 0
        self._backoff_until = 0.0

    def is_in_backoff(self) -> bool:
        """Kiểm tra đang trong period chờ backoff."""
        return time.monotonic() < self._backoff_until

    @property
    def consecutive_failures(self) -> int:
        """Số lần rate limit liên tiếp."""
        return self._consecutive_failures