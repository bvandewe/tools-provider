"""WebSocket Connection State Machine.

Implements the connection lifecycle state machine for the Agent Host Protocol v1.0.0.

States:
    CONNECTING → CONNECTED → AUTHENTICATED → ACTIVE
    ACTIVE → PAUSED | RECONNECTING | CLOSING → CLOSED
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

log = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """Connection lifecycle states."""

    # Initial states
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"

    # Active states
    ACTIVE = "active"
    PAUSED = "paused"

    # Transitional states
    RECONNECTING = "reconnecting"
    CLOSING = "closing"

    # Terminal state
    CLOSED = "closed"


# Valid state transitions
_VALID_TRANSITIONS: dict[ConnectionState, set[ConnectionState]] = {
    ConnectionState.CONNECTING: {ConnectionState.CONNECTED, ConnectionState.CLOSED},
    ConnectionState.CONNECTED: {ConnectionState.AUTHENTICATED, ConnectionState.CLOSING, ConnectionState.CLOSED},
    ConnectionState.AUTHENTICATED: {ConnectionState.ACTIVE, ConnectionState.CLOSING, ConnectionState.CLOSED},
    ConnectionState.ACTIVE: {
        ConnectionState.PAUSED,
        ConnectionState.RECONNECTING,
        ConnectionState.CLOSING,
        ConnectionState.CLOSED,
    },
    ConnectionState.PAUSED: {ConnectionState.ACTIVE, ConnectionState.CLOSING, ConnectionState.CLOSED},
    ConnectionState.RECONNECTING: {ConnectionState.CONNECTING, ConnectionState.CLOSING, ConnectionState.CLOSED},
    ConnectionState.CLOSING: {ConnectionState.CLOSED},
    ConnectionState.CLOSED: set(),  # Terminal state - no transitions allowed
}


@dataclass
class StateTransition:
    """Record of a state transition."""

    from_state: ConnectionState
    to_state: ConnectionState
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    reason: str | None = None


class ConnectionStateMachine:
    """State machine for WebSocket connection lifecycle.

    Manages state transitions and maintains transition history for debugging.
    Thread-safe state transitions are not implemented here - the caller
    (ConnectionManager) should handle synchronization if needed.
    """

    def __init__(self, initial_state: ConnectionState = ConnectionState.CONNECTING):
        """Initialize the state machine.

        Args:
            initial_state: The starting state (default: CONNECTING)
        """
        self._state = initial_state
        self._history: list[StateTransition] = []
        self._created_at = datetime.now(UTC)
        log.debug(f"State machine initialized in state: {initial_state.value}")

    @property
    def state(self) -> ConnectionState:
        """Get the current state."""
        return self._state

    @property
    def history(self) -> list[StateTransition]:
        """Get the transition history."""
        return self._history.copy()

    @property
    def created_at(self) -> datetime:
        """Get the creation timestamp."""
        return self._created_at

    @property
    def is_terminal(self) -> bool:
        """Check if the current state is terminal (CLOSED)."""
        return self._state == ConnectionState.CLOSED

    @property
    def is_active(self) -> bool:
        """Check if the connection is in an active state."""
        return self._state in {ConnectionState.ACTIVE, ConnectionState.PAUSED}

    @property
    def can_receive_messages(self) -> bool:
        """Check if the connection can receive messages."""
        return self._state in {
            ConnectionState.AUTHENTICATED,
            ConnectionState.ACTIVE,
            ConnectionState.PAUSED,
        }

    @property
    def can_send_messages(self) -> bool:
        """Check if the connection can send messages."""
        return self._state in {
            ConnectionState.CONNECTED,
            ConnectionState.AUTHENTICATED,
            ConnectionState.ACTIVE,
            ConnectionState.PAUSED,
            ConnectionState.CLOSING,
        }

    def can_transition_to(self, new_state: ConnectionState) -> bool:
        """Check if a transition to the given state is valid.

        Args:
            new_state: The target state

        Returns:
            True if the transition is valid, False otherwise
        """
        valid_targets = _VALID_TRANSITIONS.get(self._state, set())
        return new_state in valid_targets

    def transition_to(self, new_state: ConnectionState, reason: str | None = None) -> bool:
        """Attempt to transition to a new state.

        Args:
            new_state: The target state
            reason: Optional reason for the transition

        Returns:
            True if the transition succeeded, False if it was invalid
        """
        if not self.can_transition_to(new_state):
            log.warning(f"Invalid state transition: {self._state.value} → {new_state.value} (valid targets: {[s.value for s in _VALID_TRANSITIONS.get(self._state, set())]})")
            return False

        old_state = self._state
        self._state = new_state
        transition = StateTransition(
            from_state=old_state,
            to_state=new_state,
            reason=reason,
        )
        self._history.append(transition)

        log.debug(f"State transition: {old_state.value} → {new_state.value}" + (f" (reason: {reason})" if reason else ""))
        return True

    def force_closed(self, reason: str | None = None) -> None:
        """Force transition to CLOSED state regardless of current state.

        This is used for error conditions where we need to close immediately.

        Args:
            reason: Optional reason for the forced close
        """
        old_state = self._state
        self._state = ConnectionState.CLOSED
        transition = StateTransition(
            from_state=old_state,
            to_state=ConnectionState.CLOSED,
            reason=reason or "forced_close",
        )
        self._history.append(transition)
        log.info(f"Forced state transition: {old_state.value} → CLOSED" + (f" (reason: {reason})" if reason else ""))

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"ConnectionStateMachine(state={self._state.value}, transitions={len(self._history)})"
