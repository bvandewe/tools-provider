"""WebSocket Connection Representation.

Represents a single WebSocket connection with its associated state and metadata.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from starlette.websockets import WebSocket

from application.websocket.state import ConnectionState, ConnectionStateMachine

log = logging.getLogger(__name__)


@dataclass
class Connection:
    """Represents a single WebSocket connection.

    Encapsulates the WebSocket, user information, conversation context,
    and the connection state machine.
    """

    # Core connection info
    websocket: WebSocket
    user_id: str

    # Connection identifiers
    connection_id: str = field(default_factory=lambda: str(uuid4()))

    # Optional conversation context
    conversation_id: str | None = None
    definition_id: str | None = None

    # Authentication token for external API calls (e.g., Tools Provider)
    access_token: str | None = None

    # State machine for lifecycle management
    state_machine: ConnectionStateMachine = field(default_factory=ConnectionStateMachine)

    # Timing info
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Message tracking
    message_sequence: int = 0
    last_received_message_id: str | None = None
    last_sent_message_id: str | None = None

    # Heartbeat tracking
    last_ping_sent: datetime | None = None
    last_pong_received: datetime | None = None
    missed_pongs: int = 0

    @property
    def state(self) -> ConnectionState:
        """Get the current connection state."""
        return self.state_machine.state

    @property
    def is_active(self) -> bool:
        """Check if connection is in an active state."""
        return self.state_machine.is_active

    @property
    def can_receive(self) -> bool:
        """Check if connection can receive messages."""
        return self.state_machine.can_receive_messages

    @property
    def can_send(self) -> bool:
        """Check if connection can send messages."""
        return self.state_machine.can_send_messages

    @property
    def age_seconds(self) -> float:
        """Get the connection age in seconds."""
        return (datetime.now(UTC) - self.created_at).total_seconds()

    @property
    def idle_seconds(self) -> float:
        """Get seconds since last activity."""
        return (datetime.now(UTC) - self.last_activity).total_seconds()

    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.now(UTC)

    def increment_sequence(self) -> int:
        """Increment and return the message sequence number."""
        self.message_sequence += 1
        return self.message_sequence

    def record_ping_sent(self) -> None:
        """Record that a ping was sent."""
        self.last_ping_sent = datetime.now(UTC)

    def record_pong_received(self) -> None:
        """Record that a pong was received."""
        self.last_pong_received = datetime.now(UTC)
        self.missed_pongs = 0
        self.update_activity()

    def record_missed_pong(self) -> None:
        """Record a missed pong response."""
        self.missed_pongs += 1

    def transition_to(self, new_state: ConnectionState, reason: str | None = None) -> bool:
        """Attempt to transition to a new connection state.

        Args:
            new_state: The target state
            reason: Optional reason for the transition

        Returns:
            True if the transition succeeded
        """
        return self.state_machine.transition_to(new_state, reason)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Connection(id={self.connection_id[:8]}..., user={self.user_id}, conv={self.conversation_id or 'None'}, state={self.state.value}, seq={self.message_sequence})"

    def __hash__(self) -> int:
        """Hash by connection ID for use in sets/dicts."""
        return hash(self.connection_id)

    def __eq__(self, other: object) -> bool:
        """Equality by connection ID."""
        if not isinstance(other, Connection):
            return NotImplemented
        return self.connection_id == other.connection_id
