"""Domain events for Circuit Breaker state transitions.

These events are emitted when circuit breakers change state, enabling
monitoring, alerting, and audit trails for system resilience patterns.

Circuit breaker events are NOT aggregate events (they don't belong to
an Aggregate Root). They are infrastructure events published directly
to the CloudEventBus for observability purposes.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent


class CircuitBreakerTransitionReason(str, Enum):
    """Reason for circuit breaker state transition."""

    FAILURE_THRESHOLD_REACHED = "failure_threshold_reached"  # Opened after too many failures
    RECOVERY_TIMEOUT_ELAPSED = "recovery_timeout_elapsed"  # Moved to half-open for testing
    TEST_CALL_SUCCEEDED = "test_call_succeeded"  # Closed after successful test
    TEST_CALL_FAILED = "test_call_failed"  # Reopened after failed test
    MANUAL_RESET = "manual_reset"  # Admin manually reset the circuit


@cloudevent("circuit_breaker.opened.v1")
@dataclass
class CircuitBreakerOpenedDomainEvent(DomainEvent):
    """Event raised when a circuit breaker opens (starts rejecting requests).

    This indicates that the protected service is experiencing failures and
    requests are being fast-failed to prevent cascade failures.
    """

    circuit_id: str
    """Unique identifier for the circuit breaker (e.g., 'keycloak', 'source:pizza-api')."""

    circuit_type: str
    """Type of circuit breaker: 'token_exchange' or 'tool_execution'."""

    source_id: str | None
    """Source ID for tool_execution circuits, None for token_exchange."""

    failure_count: int
    """Number of consecutive failures that triggered the opening."""

    failure_threshold: int
    """Threshold at which the circuit opens."""

    last_failure_time: datetime
    """Timestamp of the last failure that triggered opening."""

    reason: CircuitBreakerTransitionReason
    """Reason for the state transition."""

    def __init__(
        self,
        circuit_id: str,
        circuit_type: str,
        source_id: str | None,
        failure_count: int,
        failure_threshold: int,
        last_failure_time: datetime,
        reason: CircuitBreakerTransitionReason,
    ) -> None:
        super().__init__(circuit_id)
        self.circuit_id = circuit_id
        self.circuit_type = circuit_type
        self.source_id = source_id
        self.failure_count = failure_count
        self.failure_threshold = failure_threshold
        self.last_failure_time = last_failure_time
        self.reason = reason


@cloudevent("circuit_breaker.closed.v1")
@dataclass
class CircuitBreakerClosedDomainEvent(DomainEvent):
    """Event raised when a circuit breaker closes (resumes normal operation).

    This indicates that the protected service has recovered and requests
    are flowing through normally again.
    """

    circuit_id: str
    """Unique identifier for the circuit breaker."""

    circuit_type: str
    """Type of circuit breaker: 'token_exchange' or 'tool_execution'."""

    source_id: str | None
    """Source ID for tool_execution circuits, None for token_exchange."""

    reason: CircuitBreakerTransitionReason
    """Reason for the state transition."""

    closed_at: datetime
    """Timestamp when the circuit was closed."""

    was_manual: bool
    """True if closed by admin action, False if auto-closed after recovery."""

    closed_by: str | None
    """Username of admin who reset the circuit, if manual."""

    def __init__(
        self,
        circuit_id: str,
        circuit_type: str,
        source_id: str | None,
        reason: CircuitBreakerTransitionReason,
        closed_at: datetime,
        was_manual: bool,
        closed_by: str | None = None,
    ) -> None:
        super().__init__(circuit_id)
        self.circuit_id = circuit_id
        self.circuit_type = circuit_type
        self.source_id = source_id
        self.reason = reason
        self.closed_at = closed_at
        self.was_manual = was_manual
        self.closed_by = closed_by


@cloudevent("circuit_breaker.half_opened.v1")
@dataclass
class CircuitBreakerHalfOpenedDomainEvent(DomainEvent):
    """Event raised when a circuit breaker enters half-open state.

    This indicates the circuit is testing whether the protected service
    has recovered by allowing a limited number of test requests through.
    """

    circuit_id: str
    """Unique identifier for the circuit breaker."""

    circuit_type: str
    """Type of circuit breaker: 'token_exchange' or 'tool_execution'."""

    source_id: str | None
    """Source ID for tool_execution circuits, None for token_exchange."""

    recovery_timeout: float
    """Recovery timeout in seconds that elapsed before testing."""

    opened_at: datetime
    """Timestamp when the circuit entered half-open state."""

    def __init__(
        self,
        circuit_id: str,
        circuit_type: str,
        source_id: str | None,
        recovery_timeout: float,
        opened_at: datetime,
    ) -> None:
        super().__init__(circuit_id)
        self.circuit_id = circuit_id
        self.circuit_type = circuit_type
        self.source_id = source_id
        self.recovery_timeout = recovery_timeout
        self.opened_at = opened_at
