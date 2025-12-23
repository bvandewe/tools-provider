"""Data Plane Message Handlers.

Handles data-level protocol messages for:
- Audit/telemetry events
- User message submission
- Widget response submission
- Content streaming (acknowledgments)
- Tool execution (notifications)

These handlers receive messages from clients and interact with the domain layer
to process user input and audit data.
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from application.protocol.audit import AuditAckPayload, AuditEventsPayload
from application.protocol.core import ProtocolMessage, create_message
from application.protocol.data import (
    ContentChunkPayload,
    MessageAckPayload,
    MessageSendPayload,
    ResponseSubmitPayload,
    ToolResultPayload,
)
from application.protocol.enums import AuditStatus
from application.websocket.connection import Connection
from application.websocket.handlers.base import BaseHandler

if TYPE_CHECKING:
    from application.websocket.manager import ConnectionManager

log = logging.getLogger(__name__)


# =============================================================================
# AUDIT HANDLERS
# =============================================================================


class AuditEventsHandler(BaseHandler[AuditEventsPayload]):
    """Handles data.audit.events messages.

    Client sends batched audit events (keystrokes, focus changes, clicks, etc.)
    for telemetry and analysis.

    Rate limiting:
    - Max 100 events per batch
    - Max 10 batches per minute per connection
    """

    payload_type = AuditEventsPayload

    # Rate limiting constants
    MAX_EVENTS_PER_BATCH = 100
    MAX_BATCHES_PER_MINUTE = 10

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for sending responses
        """
        super().__init__()
        self._manager = connection_manager
        # Track batch counts per connection for rate limiting
        self._batch_counts: dict[str, list[datetime]] = {}

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: AuditEventsPayload,
    ) -> None:
        """Process audit events batch.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated audit events payload
        """
        # Rate limiting check
        if not self._check_rate_limit(connection.connection_id):
            log.warning(f"⚠️ Rate limit exceeded for audit events from {connection.connection_id[:8]}...")
            await self._send_ack(
                connection,
                batch_id=payload.batch_id,
                received_count=0,
                status="rejected",
            )
            return

        # Validate batch size
        event_count = len(payload.events)
        if event_count > self.MAX_EVENTS_PER_BATCH:
            log.warning(f"⚠️ Batch too large: {event_count} events (max {self.MAX_EVENTS_PER_BATCH})")
            await self._send_ack(
                connection,
                batch_id=payload.batch_id,
                received_count=0,
                status="rejected",
            )
            return

        log.debug(f"📊 Received {event_count} audit events from {connection.connection_id[:8]}... (batch={payload.batch_id})")

        # TODO: Persist audit events to database
        # For now, just log and acknowledge
        for event in payload.events:
            log.debug(f"  - {event.event_type}: {event.event_id} at {event.timestamp}")

        # Send acknowledgment
        await self._send_ack(
            connection,
            batch_id=payload.batch_id,
            received_count=event_count,
            status="stored",
        )

    def _check_rate_limit(self, connection_id: str) -> bool:
        """Check if the connection is within rate limits.

        Args:
            connection_id: The connection to check

        Returns:
            True if within limits, False if rate limit exceeded
        """
        now = datetime.now(UTC)
        one_minute_ago = now.replace(second=now.second - 60) if now.second >= 60 else now.replace(minute=now.minute - 1)

        # Get or create batch history
        if connection_id not in self._batch_counts:
            self._batch_counts[connection_id] = []

        # Clean old entries
        self._batch_counts[connection_id] = [ts for ts in self._batch_counts[connection_id] if ts > one_minute_ago]

        # Check limit
        if len(self._batch_counts[connection_id]) >= self.MAX_BATCHES_PER_MINUTE:
            return False

        # Record this batch
        self._batch_counts[connection_id].append(now)
        return True

    async def _send_ack(
        self,
        connection: Connection,
        batch_id: str,
        received_count: int,
        status: AuditStatus,
    ) -> None:
        """Send acknowledgment for an audit batch.

        Args:
            connection: The connection to respond to
            batch_id: The batch being acknowledged
            received_count: Number of events received
            status: The acknowledgment status
        """
        ack_payload = AuditAckPayload(
            batchId=batch_id,
            receivedCount=received_count,
            status=status,
        )
        ack_message = create_message(
            message_type="data.audit.ack",
            payload=ack_payload.model_dump(by_alias=True),
            conversation_id=connection.conversation_id,
        )
        await self._manager.send_to_connection(connection.connection_id, ack_message)


# =============================================================================
# MESSAGE HANDLERS
# =============================================================================


class MessageSendHandler(BaseHandler[MessageSendPayload]):
    """Handles data.message.send messages.

    Client sends a free-text chat message. This handler delegates to the
    Orchestrator which dispatches domain commands via Mediator.
    """

    payload_type = MessageSendPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for sending responses
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: MessageSendPayload,
    ) -> None:
        """Process user message.

        Delegates to the Orchestrator which:
        1. Validates the message against current conversation state
        2. Dispatches ProcessUserMessageCommand via Mediator
        3. Streams agent response back to client

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated message payload
        """
        log.info(f"💬 Message received from {connection.user_id}: {payload.content[:50]}...")

        # Delegate to orchestrator for CQRS-based processing
        orchestrator = getattr(self._manager, "_orchestrator", None)
        if orchestrator:
            # Extract metadata from payload if present
            metadata = {
                "messageId": message.id,
                "timestamp": message.timestamp,
            }
            await orchestrator.handle_user_message(
                connection=connection,
                content=payload.content,
                metadata=metadata,
            )
        else:
            # Fallback: just acknowledge (orchestrator not configured)
            log.warning("No orchestrator configured - message will not be processed")
            ack_payload = MessageAckPayload(messageId=message.id)
            ack_message = create_message(
                message_type="data.message.ack",
                payload=ack_payload.model_dump(by_alias=True),
                conversation_id=connection.conversation_id,
            )
            await self._manager.send_to_connection(connection.connection_id, ack_message)


# =============================================================================
# RESPONSE HANDLERS
# =============================================================================


class ResponseSubmitHandler(BaseHandler[ResponseSubmitPayload]):
    """Handles data.response.submit messages.

    Client submits a widget response (e.g., form field value, selection, etc.)
    Delegates to Orchestrator for CQRS-based processing.

    Supports batch submissions for confirmation mode:
    When `responses` is provided, all widget responses are processed together
    before advancing the conversation.
    """

    payload_type = ResponseSubmitPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for sending responses
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: ResponseSubmitPayload,
    ) -> None:
        """Process widget response submission.

        Delegates to Orchestrator which:
        1. Validates the response
        2. Dispatches ProcessWidgetResponseCommand via Mediator
        3. Advances conversation flow if needed

        For batch submissions (confirmation mode):
        - Process all widget responses from `responses` dict first
        - Then process the confirmation button click

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated response payload
        """
        orchestrator = getattr(self._manager, "_orchestrator", None)
        if not orchestrator:
            log.warning("No orchestrator configured - widget response will not be processed")
            return

        # Check if this is a batch submission (confirmation mode)
        if payload.responses:
            log.info(f"📝 Batch response submitted: item={payload.item_id}, widgets={list(payload.responses.keys())}")

            # Process each widget response in the batch (without advancing)
            for widget_id, response_item in payload.responses.items():
                log.debug(f"  Processing batch widget: {widget_id}, type={response_item.widget_type}")
                await orchestrator.handle_widget_response(
                    connection=connection,
                    widget_id=widget_id,
                    item_id=payload.item_id,
                    value=response_item.value,
                    metadata=None,
                    # Don't advance on individual batch items - wait for confirmation
                    batch_mode=True,
                )

            # Now process the confirmation button click (this triggers advancement)
            log.info(f"📝 Processing batch confirmation: item={payload.item_id}, widget={payload.widget_id}")
            await orchestrator.handle_widget_response(
                connection=connection,
                widget_id=payload.widget_id,
                item_id=payload.item_id,
                value=payload.value,
                metadata=None,
                batch_mode=False,
            )
        else:
            # Single widget response (original behavior)
            log.info(f"📝 Response submitted: item={payload.item_id}, widget={payload.widget_id}, type={payload.widget_type}, value={str(payload.value)[:50]}...")

            metadata = None
            if payload.metadata:
                metadata = {
                    "timeSpentMs": payload.metadata.time_spent_ms,
                    "changeCount": payload.metadata.change_count,
                }
                log.debug(f"  Metadata: time_spent={payload.metadata.time_spent_ms}ms")

            await orchestrator.handle_widget_response(
                connection=connection,
                widget_id=payload.widget_id,
                item_id=payload.item_id,
                value=payload.value,
                metadata=metadata,
            )

        # Acknowledgment will come through data.response.ack when domain processes it


# =============================================================================
# TOOL EXECUTION HANDLERS (Phase 3)
# =============================================================================


class ToolResultHandler(BaseHandler[ToolResultPayload]):
    """Handles data.tool.result messages.

    Client sends the result of a client-side tool execution back to the server.
    The server validates the result and continues the AI conversation.

    Flow:
    1. Server sends data.tool.call to client
    2. Client executes tool (browser-side)
    3. Client sends data.tool.result back
    4. Server processes result and continues AI flow
    """

    payload_type = ToolResultPayload

    # Rate limiting constants
    MAX_RESULTS_PER_MINUTE = 20

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for sending responses
        """
        super().__init__()
        self._manager = connection_manager
        # Track pending tool calls for validation
        self._pending_calls: dict[str, dict[str, Any]] = {}
        # Track result counts per connection for rate limiting
        self._result_counts: dict[str, list[datetime]] = {}

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: ToolResultPayload,
    ) -> None:
        """Process tool execution result from client.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The validated tool result payload
        """
        log.info(f"🔧 Tool result received: call_id={payload.call_id}, tool={payload.tool_name}, success={payload.success}")

        # Rate limiting check
        if not self._check_rate_limit(connection.connection_id):
            log.warning(f"⚠️ Rate limit exceeded for tool results from {connection.connection_id[:8]}...")
            await self._send_error(
                connection,
                code="RATE_LIMIT_EXCEEDED",
                message="Too many tool results, please slow down",
            )
            return

        # Log execution details
        if payload.execution_time_ms:
            log.debug(f"  Execution time: {payload.execution_time_ms}ms")

        if payload.success:
            log.debug(f"  Result: {str(payload.result)[:100]}...")
        else:
            log.warning(f"  Tool failed: {payload.result}")

        # TODO: Dispatch domain command to process the tool result
        # This will continue the AI conversation with the tool result
        # Example: await self._mediator.execute_async(ProcessToolResultCommand(...))

        # Send acknowledgment
        ack_message = create_message(
            message_type="data.tool.ack",
            payload={
                "callId": payload.call_id,
                "received": True,
            },
            conversation_id=connection.conversation_id,
        )
        await self._manager.send_to_connection(connection.connection_id, ack_message)

    def _check_rate_limit(self, connection_id: str) -> bool:
        """Check if the connection is within rate limits.

        Args:
            connection_id: The connection to check

        Returns:
            True if within limits, False if rate limit exceeded
        """
        now = datetime.now(UTC)
        one_minute_ago = now.replace(second=now.second - 60) if now.second >= 60 else now.replace(minute=now.minute - 1)

        # Get or create result history
        if connection_id not in self._result_counts:
            self._result_counts[connection_id] = []

        # Clean old entries
        self._result_counts[connection_id] = [ts for ts in self._result_counts[connection_id] if ts > one_minute_ago]

        # Check limit
        if len(self._result_counts[connection_id]) >= self.MAX_RESULTS_PER_MINUTE:
            return False

        # Record this result
        self._result_counts[connection_id].append(now)
        return True

    async def _send_error(
        self,
        connection: Connection,
        code: str,
        message: str,
    ) -> None:
        """Send an error message to the connection.

        Args:
            connection: The target connection
            code: Error code
            message: Human-readable error message
        """
        from application.protocol.system import SystemErrorPayload

        error_payload = SystemErrorPayload(
            category="rate_limit",
            code=code,
            message=message,
            isRetryable=True,
            retryAfterMs=60000,  # Retry after 1 minute
        )
        error_message = create_message(
            message_type="system.error",
            payload=error_payload.model_dump(by_alias=True),
            conversation_id=connection.conversation_id,
        )
        await self._manager.send_to_connection(connection.connection_id, error_message)

    def register_pending_call(self, call_id: str, tool_name: str, connection_id: str, timeout_seconds: int = 30) -> None:
        """Register a pending tool call for tracking.

        Args:
            call_id: The unique tool call ID
            tool_name: Name of the tool
            connection_id: Connection that should respond
            timeout_seconds: Timeout for the call
        """
        self._pending_calls[call_id] = {
            "tool_name": tool_name,
            "connection_id": connection_id,
            "started_at": datetime.now(UTC),
            "timeout_seconds": timeout_seconds,
        }

    def complete_pending_call(self, call_id: str) -> dict[str, Any] | None:
        """Mark a pending tool call as complete.

        Args:
            call_id: The tool call ID

        Returns:
            The call info if found, None otherwise
        """
        return self._pending_calls.pop(call_id, None)


# =============================================================================
# CONTENT STREAMING HANDLERS (Phase 3)
# =============================================================================


class ContentChunkAckHandler(BaseHandler[ContentChunkPayload]):
    """Handles data.content.chunk.ack messages (if client acknowledges chunks).

    This is typically server-to-client, but client may acknowledge receipt
    for flow control in high-latency scenarios.

    Note: In most cases, content chunks are server → client only.
    This handler is for optional client acknowledgments.
    """

    payload_type = ContentChunkPayload

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize with reference to connection manager.

        Args:
            connection_manager: The ConnectionManager for sending responses
        """
        super().__init__()
        self._manager = connection_manager

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        payload: ContentChunkPayload,
    ) -> None:
        """Process content chunk acknowledgment.

        Args:
            connection: The connection that sent the message
            message: The full protocol message
            payload: The content chunk payload
        """
        log.debug(f"📨 Content chunk ack: message_id={payload.message_id}, final={payload.final}")
        # Optional: Track delivery confirmation for analytics
        # This is primarily for debugging and monitoring
