"""
Circuit Breaker and Graceful Degradation pattern.
Prevents cascading failures by halting downstream requests to degraded upstream
services and returning cached or graceful fallback responses.
"""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"        # Normal operation: requests pass through
    OPEN = "OPEN"            # Tripped: fast-fail, execute fallback
    HALF_OPEN = "HALF_OPEN"  # Testing if upstream has recovered


class CircuitBreaker:
    """Stateful Circuit Breaker with automatic recovery trialing."""

    def __init__(
        self,
        name: str = "llm_circuit",
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        half_open_successes_required: int = 2
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_successes_required = half_open_successes_required

        self.state: CircuitState = CircuitState.CLOSED
        self.failure_count: int = 0
        self.success_count: int = 0
        self.last_state_change: float = time.monotonic()

    def _transition_to(self, new_state: CircuitState) -> None:
        logger.warning(f"[CircuitBreaker '{self.name}'] State transition: {self.state.value} -> {new_state.value}")
        self.state = new_state
        self.last_state_change = time.monotonic()
        if new_state == CircuitState.HALF_OPEN:
            self.success_count = 0
        elif new_state == CircuitState.CLOSED:
            self.failure_count = 0
            self.success_count = 0

    def can_execute(self) -> bool:
        """Check if request is allowed to execute."""
        now = time.monotonic()
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery cooldown period has elapsed
            if (now - self.last_state_change) >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # Allow limited probe requests in half-open state
            return True

        return False

    def record_success(self) -> None:
        """Record successful invocation."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_successes_required:
                self._transition_to(CircuitState.CLOSED)
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record failed invocation."""
        self.failure_count += 1
        if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            self._transition_to(CircuitState.OPEN)

    def call(
        self,
        func: Callable[..., Any],
        fallback_func: Optional[Callable[..., Any]] = None,
        *args,
        **kwargs
    ) -> Any:
        """Execute callable with circuit protection and graceful degradation."""
        if not self.can_execute():
            logger.warning(f"[CircuitBreaker '{self.name}'] Tripped OPEN. Routing to fallback.")
            if fallback_func:
                return fallback_func(*args, **kwargs)
            return self.default_degradation_response()

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            logger.error(f"[CircuitBreaker '{self.name}'] Call failed: {exc}")
            self.record_failure()
            if fallback_func:
                return fallback_func(*args, **kwargs)
            return self.default_degradation_response()

    def default_degradation_response(self) -> str:
        return (
            "ShopAssist AI is currently experiencing connectivity issues with the upstream service. "
            "Please retry in a moment or refer to the FAQ section."
        )
