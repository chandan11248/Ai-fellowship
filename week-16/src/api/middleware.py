"""
Middleware for request timing, rate limiting, and response caching.
"""

import time
import hashlib
import json
from typing import Dict, Any, Tuple, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.config import settings
from src.reliability.rate_limiter import SlidingWindowRateLimiter


class AppRateLimiterMiddleware(BaseHTTPMiddleware):
    """Enforces sliding window rate limits per client IP."""

    def __init__(self, app, max_requests_per_minute: int = settings.RATE_LIMIT_REQUESTS_PER_MINUTE):
        super().__init__(app)
        self.limiter = SlidingWindowRateLimiter(
            max_requests=max_requests_per_minute,
            window_seconds=60.0
        )

    async def dispatch(self, request: Request, call_next):
        # Exclude health check and metrics from rate limiting
        if request.url.path in ("/health", "/metrics", "/docs", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        allowed, remaining, retry_after = await self.limiter.is_allowed(client_ip)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after_seconds": round(retry_after, 2),
                    "message": f"Maximum of {settings.RATE_LIMIT_REQUESTS_PER_MINUTE} req/min allowed per client."
                },
                headers={"Retry-After": str(int(retry_after) + 1)}
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Measures total request processing time."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        process_time = (time.perf_counter() - start) * 1000.0
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        return response


class SimpleResponseCache:
    """In-memory key-value cache with TTL expiration."""

    def __init__(self, ttl_seconds: int = settings.CACHE_TTL_SECONDS, max_entries: int = settings.MAX_CACHE_ENTRIES):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.hits = 0
        self.misses = 0

    def _make_key(self, query: str, config_dict: Dict[str, Any]) -> str:
        payload = f"{query.strip()}||{json.dumps(config_dict, sort_keys=True)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, query: str, config_dict: Dict[str, Any]) -> Optional[Any]:
        key = self._make_key(query, config_dict)
        now = time.monotonic()

        if key in self.cache:
            val, expiry = self.cache[key]
            if now < expiry:
                self.hits += 1
                return val
            else:
                del self.cache[key]

        self.misses += 1
        return None

    def set(self, query: str, config_dict: Dict[str, Any], val: Any) -> None:
        if len(self.cache) >= self.max_entries:
            # Purge oldest 20%
            oldest = sorted(self.cache.keys(), key=lambda k: self.cache[k][1])[:int(self.max_entries * 0.2)]
            for k in oldest:
                self.cache.pop(k, None)

        key = self._make_key(query, config_dict)
        self.cache[key] = (val, time.monotonic() + self.ttl)

    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        ratio = (self.hits / total * 100.0) if total > 0 else 0.0
        return {
            "entries": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio_pct": round(ratio, 2)
        }


# Global application cache instance
response_cache = SimpleResponseCache()
