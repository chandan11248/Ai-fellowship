"""
Retry mechanisms with exponential backoff and randomized jitter.
Protects against transient network failures, rate limit spikes (HTTP 429),
and upstream provider hiccups.
"""

import time
import random
import asyncio
import functools
import logging
from typing import Callable, Tuple, Type, Optional, Any

logger = logging.getLogger(__name__)


def compute_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True
) -> float:
    """Compute exponential backoff with optional full jitter."""
    delay = min(max_delay, base_delay * (2 ** attempt))
    if jitter:
        delay = random.uniform(0, delay)
    return delay


def retry_sync(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 20.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
):
    """Decorator for synchronous functions with exponential backoff."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_err = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_err = exc
                    if attempt >= max_retries:
                        logger.error(f"[Retry Exhausted] Function {func.__name__} failed after {max_retries} retries: {exc}")
                        raise

                    delay = compute_backoff(attempt, base_delay, max_delay)
                    logger.warning(
                        f"[Retry Attempt {attempt + 1}/{max_retries}] {func.__name__} failed with {type(exc).__name__}: {exc}. "
                        f"Backing off for {delay:.2f}s."
                    )
                    if on_retry:
                        on_retry(exc, attempt, delay)
                    time.sleep(delay)
            raise last_err
        return wrapper
    return decorator


def retry_async(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 20.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
):
    """Decorator for asynchronous coroutines with exponential backoff."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_err = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_err = exc
                    if attempt >= max_retries:
                        logger.error(f"[Async Retry Exhausted] Coroutine {func.__name__} failed after {max_retries} retries: {exc}")
                        raise

                    delay = compute_backoff(attempt, base_delay, max_delay)
                    logger.warning(
                        f"[Async Retry Attempt {attempt + 1}/{max_retries}] {func.__name__} failed with {type(exc).__name__}: {exc}. "
                        f"Backing off for {delay:.2f}s."
                    )
                    if on_retry:
                        on_retry(exc, attempt, delay)
                    await asyncio.sleep(delay)
            raise last_err
        return wrapper
    return decorator
