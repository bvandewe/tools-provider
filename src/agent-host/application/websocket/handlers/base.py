"""Base Handler for WebSocket Messages.

Abstract base class for all WebSocket message handlers.
Provides common functionality for message processing.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from application.protocol.core import ProtocolMessage
from application.websocket.connection import Connection

log = logging.getLogger(__name__)

TPayload = TypeVar("TPayload", bound=BaseModel)


class BaseHandler(ABC, Generic[TPayload]):
    """Abstract base class for WebSocket message handlers.

    Handlers process incoming messages and optionally send responses.
    Subclasses must implement the process() method with business logic.

    Type Parameters:
        TPayload: The Pydantic model for the message payload
    """

    # Subclasses should set this to the Pydantic model class for payload validation
    payload_type: type[TPayload] | None = None

    def __init__(self):
        """Initialize the handler."""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def handle(self, connection: Connection, message: ProtocolMessage[Any]) -> None:
        """Handle an incoming message.

        Validates the payload (if payload_type is set) and delegates to process().

        Args:
            connection: The connection that sent the message
            message: The protocol message to handle

        Raises:
            ValidationError: If payload validation fails
        """
        self._logger.debug(f"Handling {message.type} from {connection.connection_id[:8]}...")

        payload: TPayload | dict[str, Any]

        # Validate and parse payload if we have a payload type
        if self.payload_type is not None:
            try:
                payload = self.payload_type.model_validate(message.payload)
            except ValidationError as e:
                self._logger.error(f"Payload validation failed for {message.type}: {e}")
                raise
        else:
            # No typed payload - pass raw dict
            payload = message.payload if isinstance(message.payload, dict) else {}

        # Update connection activity
        connection.update_activity()
        connection.last_received_message_id = message.id

        # Delegate to concrete implementation
        await self.process(connection, message, payload)

    @abstractmethod
    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: TPayload | dict[str, Any],
    ) -> None:
        """Process the validated message.

        Subclasses must implement this method with the actual message handling logic.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated payload (typed if payload_type is set)
        """
        ...

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"{self.__class__.__name__}(payload_type={self.payload_type})"


class NoOpHandler(BaseHandler[BaseModel]):
    """Handler that does nothing - used for acknowledged but unhandled message types."""

    payload_type = None

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: dict[str, Any],
    ) -> None:
        """Do nothing - just log receipt."""
        log.debug(f"NoOp handler received {message.type}")
