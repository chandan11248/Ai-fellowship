"""
Rate Limiting implementations: Token Bucket & Sliding Window Log.
Prevents API abuse, protects upstream quota limits, and enforces fair usage.
"""

import time
import asyncio
from typing import Dict, Tuple
from collections import deque


class TokenBucketRateLimiter:
    """
    Token Bucket Rate Limiter with thread-safe async locks.
    Tokens refill continuously at `refill_rate` tokens/sec up to `capacity`.
    """

    def __init__(self, capacity: int = 60, refill_rate_per_sec: float = 1.0):
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.refill_rate = refill_rate_per_sec
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def acquire_sync(self, cost: float = 1.0) -> bool:
        """Non-blocking synchronous check."""
        self._refill()
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False

    async def acquire(self, cost: float = 1.0) -> bool:
        """Asynchronous token acquisition check."""
        async with self._lock:
            self._refill()
            if self.tokens >= cost:
                self.tokens -= cost
                return True
            return False

    async def wait_and_acquire(self, cost: float = 1.0, max_wait: float = 5.0) -> bool:
        """Wait until a token becomes available or timeout expires."""
        deadline = time.monotonic() + max_wait
        while time.monotonic() < deadline:
            async with self._lock:
                self._refill()
                if self.tokens >= cost:
                    self.tokens -= cost
                    return True
                deficit = cost - self.tokens
                wait_time = min(deficit / self.refill_rate, 0.1)
            await asyncio.sleep(wait_time)
        return False


class SlidingWindowRateLimiter:
    """
    Sliding Window Log Rate Limiter per client identifier (IP / API Key).
    Tracks exact request timestamps within a rolling time window.
    """

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.client_windows: Dict[str, deque] = {}
        self._lock = asyncio.Lock()

    def is_allowed_sync(self, client_id: str) -> Tuple[bool, int, float]:
        """
        Check if request is allowed.
        Returns: (allowed, remaining_quota, retry_after_seconds)
        """
        now = time.monotonic()
        if client_id not in self.client_windows:
            self.client_windows[client_id] = deque()

        q = self.client_windows[client_id]
        # Discard expired timestamps
        while q and (now - q[0]) > self.window_seconds:
            q.popleft()

        if len(q) < self.max_requests:
            q.append(now)
            remaining = self.max_requests - len(q)
            return True, remaining, 0.0

        # Rate limited: time until the oldest request falls out of window
        oldest = q[0]
        retry_after = max(0.1, (oldest + self.window_seconds) - now)
        return False, 0, retry_after

    async def is_allowed(self, client_id: str) -> Tuple[bool, int, float]:
        """Async thread-safe check."""
        async with self._lock:
            return self.is_allowed_sync(client_id)
