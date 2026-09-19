"""
Tests for Reliability Controls: Retries, Rate Limiting, Circuit Breaker, Fallbacks.
"""

import time
import pytest
import asyncio
from src.reliability.retry import retry_sync, retry_async
from src.reliability.rate_limiter import TokenBucketRateLimiter, SlidingWindowRateLimiter
from src.reliability.circuit_breaker import CircuitBreaker, CircuitState
from src.reliability.fallback import FallbackManager
from src.assistant.llm_client import MockLLMClient, BaseLLMClient, LLMResponse


def test_retry_sync_success_after_failure():
    attempts = 0

    @retry_sync(max_retries=3, base_delay=0.01)
    def flaky_function():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionResetError("Temporary socket reset")
        return "SUCCESS"

    res = flaky_function()
    assert res == "SUCCESS"
    assert attempts == 3


def test_retry_sync_exhaustion():
    @retry_sync(max_retries=2, base_delay=0.01)
    def always_failing():
        raise TimeoutError("Dead upstream")

    with pytest.raises(TimeoutError):
        always_failing()


@pytest.mark.asyncio
async def test_retry_async():
    attempts = 0

    @retry_async(max_retries=2, base_delay=0.01)
    async def async_flaky():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ValueError("Intermittent failure")
        return "ASYNC_SUCCESS"

    res = await async_flaky()
    assert res == "ASYNC_SUCCESS"
    assert attempts == 2


def test_token_bucket_rate_limiter():
    limiter = TokenBucketRateLimiter(capacity=3, refill_rate_per_sec=10.0)
    assert limiter.acquire_sync(1.0) is True
    assert limiter.acquire_sync(1.0) is True
    assert limiter.acquire_sync(1.0) is True
    # Now exhausted
    assert limiter.acquire_sync(1.0) is False

    # Wait for refill
    time.sleep(0.15)
    assert limiter.acquire_sync(1.0) is True


def test_sliding_window_rate_limiter():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=0.5)
    allowed1, _, _ = limiter.is_allowed_sync("client_a")
    allowed2, _, _ = limiter.is_allowed_sync("client_a")
    allowed3, _, retry_after = limiter.is_allowed_sync("client_a")

    assert allowed1 is True
    assert allowed2 is True
    assert allowed3 is False
    assert retry_after > 0.0

    # Different client not blocked
    allowed_b, _, _ = limiter.is_allowed_sync("client_b")
    assert allowed_b is True


def test_circuit_breaker_transitions():
    cb = CircuitBreaker(name="test_cb", failure_threshold=2, recovery_timeout=0.1)
    assert cb.state == CircuitState.CLOSED

    # Failure 1
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED

    # Failure 2 -> Trips OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # Wait for recovery timeout
    time.sleep(0.15)
    # Becomes HALF_OPEN on next check
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Record required successes to close
    cb.record_success()
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_fallback_manager_cascading():
    class FailingClient(BaseLLMClient):
        def generate(self, *args, **kwargs):
            raise ConnectionError("Primary provider is down")
        async def generate_async(self, *args, **kwargs):
            raise ConnectionError("Down")
        async def generate_stream(self, *args, **kwargs):
            yield ""

    failing = FailingClient()
    mock_fallback = MockLLMClient()

    mgr = FallbackManager(primary_client=failing, fallback_clients=[mock_fallback])
    resp = mgr.generate_with_fallback([{"role": "user", "content": "Hello"}])

    assert resp.provider == "mock"
    assert resp.content is not None
