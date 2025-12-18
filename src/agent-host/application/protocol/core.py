"""
Agent Host WebSocket Protocol v1.0.0 - Core Types

Base types for the protocol message envelope and utilities.
"""

import random
import uuid
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from .enums import MessageSource, ProtocolVersion

T = TypeVar("T")


# =============================================================================
# COMMON PRIMITIVES
# =============================================================================


class Position(BaseModel):
    """2D position coordinates."""

    x: float
    y: float


class Dimensions(BaseModel):
    """Size constraints for widgets."""

    width: float | None = None
    height: float | None = None
    min_width: float | None = Field(default=None, alias="minWidth")
    min_height: float | None = Field(default=None, alias="minHeight")
    max_width: float | None = Field(default=None, alias="maxWidth")
    max_height: float | None = Field(default=None, alias="maxHeight")

    model_config = {"populate_by_name": True}


class Region(BaseModel):
    """Rectangular region on canvas."""

    x: float
    y: float
    width: float
    height: float


# =============================================================================
# MESSAGE ENVELOPE
# =============================================================================


class ProtocolMessage(BaseModel, Generic[T]):
    """
    Base message envelope - all messages wrap their payload in this structure.
    Inspired by CloudEvents specification.
    """

    id: str = Field(..., description="Unique message identifier (UUID or nanoid)")
    type: str = Field(..., description="Hierarchical message type: plane.category.action")
    version: ProtocolVersion = Field(..., description="Protocol version (semver format)")
    timestamp: str = Field(..., description="ISO 8601 timestamp with milliseconds")
    source: MessageSource = Field(..., description="Origin: client or server")
    conversation_id: str | None = Field(default=None, alias="conversationId", description="Conversation context (null for connection-level messages)")
    payload: T = Field(..., description="Message-specific data")

    model_config = {"populate_by_name": True}


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================


def create_message(
    message_type: str,
    payload: Any,
    conversation_id: str | None = None,
    source: MessageSource = "server",
) -> ProtocolMessage[Any]:
    """
    Create a protocol message with proper envelope structure.

    Args:
        message_type: The hierarchical message type (e.g., "control.widget.state")
        payload: The message payload
        conversation_id: Optional conversation context
        source: Origin of the message ("client" or "server")

    Returns:
        A properly structured ProtocolMessage
    """
    return ProtocolMessage(
        id=str(uuid.uuid4()),
        type=message_type,
        version="1.0",
        timestamp=datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        source=source,
        conversationId=conversation_id,
        payload=payload,
    )


def calculate_reconnect_backoff(attempt: int) -> float:
    """
    Calculate exponential backoff delay for reconnection.

    Args:
        attempt: The reconnection attempt number (0-indexed)

    Returns:
        Delay in milliseconds before next reconnection attempt
    """
    base_delay = 1000  # 1 second
    max_delay = 30000  # 30 seconds
    jitter = random.random() * 1000  # 0-1 second jitter

    delay = min(base_delay * (2**attempt) + jitter, max_delay)
    return delay
