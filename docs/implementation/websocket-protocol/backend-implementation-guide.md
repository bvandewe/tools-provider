# Backend Implementation Guide

**Document Version:** 1.1.0
**Last Updated:** December 18, 2025
**Target:** Python 3.12+ / FastAPI / Starlette WebSockets

---

## ⚠️ CRITICAL: Before Using This Document

> **This document contains architectural patterns and code examples.**
> **Some code examples use UNVERIFIED imports that must be validated against the codebase.**
>
> **BEFORE implementing any code from this document:**
>
> 1. Read [Pattern Discovery Reference](./pattern-discovery-reference.md) for verified imports
> 2. Read [Implementation Prompt Template](./implementation-prompt-template.md) for safe implementation workflow
> 3. Search the existing codebase to confirm patterns
>
> **Code blocks marked with `⚠️ PATTERN: VERIFY BEFORE USE` require validation.**

---

## Table of Contents

1. [Overview](#1-overview)
2. [Project Structure](#2-project-structure)
3. [Core Components](#3-core-components)
4. [Message Handling](#4-message-handling)
5. [Domain Integration](#5-domain-integration)
6. [State Management](#6-state-management)
7. [Scaling & Infrastructure](#7-scaling--infrastructure)
8. [Error Handling](#8-error-handling)
9. [Security](#9-security)
10. [Implementation Recipes](#10-implementation-recipes)

---

## 1. Overview

### Architecture Principles

1. **Clean Architecture**: WebSocket layer is an infrastructure concern, not domain
2. **CQRS Alignment**: WebSocket messages trigger commands, domain events broadcast responses
3. **Stateless Handlers**: Each message handler is stateless; state lives in connection manager
4. **Protocol-First**: All messages validated against Pydantic models before processing

### Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| WebSocket Server | Starlette (via FastAPI) | Native async, production-ready |
| Message Serialization | Pydantic v2 | Already implemented protocol models |
| State Store | Redis | Cross-instance state sharing |
| Message Broker | Redis PubSub | Simple, sufficient for scale |
| Authentication | JWT + Session cookies | Existing Keycloak integration |

---

## 2. Project Structure

```
src/agent-host/
├── application/
│   ├── protocol/                    # ✅ COMPLETE
│   │   ├── __init__.py
│   │   ├── enums.py
│   │   ├── core.py
│   │   ├── system.py
│   │   ├── control.py
│   │   ├── data.py
│   │   ├── canvas.py
│   │   ├── iframe.py
│   │   ├── audit.py
│   │   └── widgets/
│   │
│   ├── websocket/                   # 🔲 TO BUILD
│   │   ├── __init__.py
│   │   ├── manager.py               # ConnectionManager class
│   │   ├── router.py                # MessageRouter class
│   │   ├── state.py                 # ConnectionState enum + machine
│   │   ├── broadcast.py             # Broadcasting utilities
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # BaseHandler abstract class
│   │   │   ├── system_handlers.py   # System message handlers
│   │   │   ├── control_handlers.py  # Control plane handlers
│   │   │   ├── data_handlers.py     # Data plane handlers
│   │   │   └── canvas_handlers.py   # Canvas message handlers
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py              # Authentication middleware
│   │       ├── rate_limit.py        # Rate limiting
│   │       └── logging.py           # Message logging
│   │
│   ├── commands/
│   │   └── websocket/               # WebSocket-triggered commands
│   │       ├── process_message_command.py
│   │       ├── submit_response_command.py
│   │       └── execute_tool_command.py
│   │
│   └── events/
│       └── websocket/               # Domain → WebSocket event handlers
│           ├── content_generated_handler.py
│           ├── widget_rendered_handler.py
│           └── conversation_updated_handler.py
│
├── api/
│   └── controllers/
│       └── websocket_controller.py  # WebSocket endpoint
│
├── infrastructure/
│   └── websocket/
│       ├── __init__.py
│       ├── redis_pubsub.py          # Cross-instance messaging
│       └── connection_store.py      # Connection registry
│
└── domain/
    └── events/
        └── websocket_events.py      # WebSocket-related domain events
```

---

## 3. Core Components

### 3.1 ConnectionManager

Manages WebSocket connection lifecycle.

```python
# src/agent-host/application/websocket/manager.py

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from application.protocol import (
    ProtocolMessage,
    MessageTypes,
    SystemConnectionEstablishedPayload,
    SystemConnectionClosePayload,
    StandardCloseCode,
    AppCloseCode,
    create_message,
)
from application.websocket.state import ConnectionState, ConnectionStateMachine
from application.websocket.router import MessageRouter


class Connection:
    """Represents an active WebSocket connection."""

    def __init__(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: str,
        conversation_id: str | None = None,
    ):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.state_machine = ConnectionStateMachine()
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = self.created_at
        self.message_sequence = 0
        self.pending_acks: dict[str, asyncio.Future] = {}

    @property
    def state(self) -> ConnectionState:
        return self.state_machine.state

    async def send(self, message: ProtocolMessage) -> None:
        """Send a message to the client."""
        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.send_json(
                message.model_dump(by_alias=True, exclude_none=True)
            )
            self.last_activity = datetime.now(timezone.utc)

    async def close(self, code: int, reason: str) -> None:
        """Close the connection."""
        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.close(code=code, reason=reason)


class ConnectionManager:
    """Manages all active WebSocket connections."""

    def __init__(
        self,
        router: MessageRouter,
        heartbeat_interval: int = 30,
        connection_timeout: int = 300,
    ):
        self.router = router
        self.heartbeat_interval = heartbeat_interval
        self.connection_timeout = connection_timeout

        # Connection registries
        self._connections: dict[str, Connection] = {}
        self._user_connections: dict[str, set[str]] = {}  # user_id → connection_ids
        self._conversation_connections: dict[str, set[str]] = {}  # conv_id → connection_ids

        # Background tasks
        self._heartbeat_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start background tasks."""
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop background tasks and close all connections."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()

        # Close all connections gracefully
        close_tasks = [
            conn.close(
                StandardCloseCode.GOING_AWAY,
                "Server shutting down"
            )
            for conn in self._connections.values()
        ]
        await asyncio.gather(*close_tasks, return_exceptions=True)
        self._connections.clear()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        conversation_id: str | None = None,
    ) -> Connection:
        """Accept a new WebSocket connection."""
        await websocket.accept()

        connection_id = str(uuid.uuid4())
        connection = Connection(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        # Register connection
        self._connections[connection_id] = connection

        if user_id not in self._user_connections:
            self._user_connections[user_id] = set()
        self._user_connections[user_id].add(connection_id)

        if conversation_id:
            if conversation_id not in self._conversation_connections:
                self._conversation_connections[conversation_id] = set()
            self._conversation_connections[conversation_id].add(connection_id)

        # Transition state
        connection.state_machine.transition_to(ConnectionState.CONNECTED)

        # Send connection established message
        await self._send_connection_established(connection)

        return connection

    async def disconnect(self, connection_id: str) -> None:
        """Remove a connection from the manager."""
        connection = self._connections.pop(connection_id, None)
        if not connection:
            return

        # Remove from registries
        user_conns = self._user_connections.get(connection.user_id)
        if user_conns:
            user_conns.discard(connection_id)
            if not user_conns:
                del self._user_connections[connection.user_id]

        if connection.conversation_id:
            conv_conns = self._conversation_connections.get(connection.conversation_id)
            if conv_conns:
                conv_conns.discard(connection_id)
                if not conv_conns:
                    del self._conversation_connections[connection.conversation_id]

    async def handle_connection(self, connection: Connection) -> None:
        """Main message loop for a connection."""
        try:
            while True:
                data = await connection.websocket.receive_json()
                await self._process_message(connection, data)
        except WebSocketDisconnect:
            pass
        finally:
            await self.disconnect(connection.connection_id)

    async def broadcast_to_conversation(
        self,
        conversation_id: str,
        message: ProtocolMessage,
        exclude: str | None = None,
    ) -> None:
        """Broadcast a message to all connections in a conversation."""
        connection_ids = self._conversation_connections.get(conversation_id, set())
        tasks = []
        for conn_id in connection_ids:
            if conn_id == exclude:
                continue
            connection = self._connections.get(conn_id)
            if connection:
                tasks.append(connection.send(message))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def send_to_user(
        self,
        user_id: str,
        message: ProtocolMessage,
    ) -> None:
        """Send a message to all connections for a user."""
        connection_ids = self._user_connections.get(user_id, set())
        tasks = [
            self._connections[conn_id].send(message)
            for conn_id in connection_ids
            if conn_id in self._connections
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_connection_established(self, connection: Connection) -> None:
        """Send the connection established message."""
        payload = SystemConnectionEstablishedPayload(
            connection_id=connection.connection_id,
            server_time=datetime.now(timezone.utc).isoformat(),
            protocol_version="1.0",
            heartbeat_interval=self.heartbeat_interval,
            features=["streaming", "canvas", "widgets", "audit"],
        )
        message = create_message(
            msg_type=MessageTypes.SYSTEM_CONNECTION_ESTABLISHED,
            payload=payload,
            source="server",
        )
        await connection.send(message)

    async def _process_message(
        self,
        connection: Connection,
        data: dict[str, Any],
    ) -> None:
        """Process an incoming message."""
        connection.last_activity = datetime.now(timezone.utc)

        try:
            # Parse and validate message
            message = ProtocolMessage.model_validate(data)

            # Route to appropriate handler
            await self.router.route(connection, message)

        except Exception as e:
            # Send error response
            await self._send_error(connection, str(e))

    async def _send_error(
        self,
        connection: Connection,
        error: str,
        recoverable: bool = True,
    ) -> None:
        """Send an error message to the client."""
        from application.protocol import SystemErrorPayload

        payload = SystemErrorPayload(
            code="PROCESSING_ERROR",
            message=error,
            category="validation",
            recoverable=recoverable,
        )
        message = create_message(
            msg_type=MessageTypes.SYSTEM_ERROR,
            payload=payload,
            source="server",
        )
        await connection.send(message)

    async def _heartbeat_loop(self) -> None:
        """Send periodic ping messages to all connections."""
        while True:
            await asyncio.sleep(self.heartbeat_interval)

            from application.protocol import SystemPingPongPayload

            now = datetime.now(timezone.utc)
            payload = SystemPingPongPayload(timestamp=now.isoformat())
            message = create_message(
                msg_type=MessageTypes.SYSTEM_PING,
                payload=payload,
                source="server",
            )

            tasks = [
                conn.send(message)
                for conn in self._connections.values()
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _cleanup_loop(self) -> None:
        """Clean up stale connections."""
        while True:
            await asyncio.sleep(60)  # Check every minute

            now = datetime.now(timezone.utc)
            stale_connections = [
                conn_id
                for conn_id, conn in self._connections.items()
                if (now - conn.last_activity).total_seconds() > self.connection_timeout
            ]

            for conn_id in stale_connections:
                connection = self._connections.get(conn_id)
                if connection:
                    await connection.close(
                        AppCloseCode.IDLE_TIMEOUT,
                        "Connection timed out due to inactivity"
                    )
                    await self.disconnect(conn_id)
```

### 3.2 MessageRouter

Routes incoming messages to appropriate handlers.

```python
# src/agent-host/application/websocket/router.py

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Awaitable

from application.protocol import ProtocolMessage, MessageTypes
from application.websocket.handlers.base import BaseHandler

if TYPE_CHECKING:
    from application.websocket.manager import Connection

logger = logging.getLogger(__name__)


class MessageRouter:
    """Routes WebSocket messages to appropriate handlers."""

    def __init__(self):
        self._handlers: dict[str, BaseHandler] = {}
        self._middleware: list[Callable] = []

    def register_handler(self, message_type: str, handler: BaseHandler) -> None:
        """Register a handler for a message type."""
        self._handlers[message_type] = handler
        logger.debug(f"Registered handler for {message_type}: {handler.__class__.__name__}")

    def register_handlers(self, handlers: dict[str, BaseHandler]) -> None:
        """Register multiple handlers at once."""
        for msg_type, handler in handlers.items():
            self.register_handler(msg_type, handler)

    def add_middleware(
        self,
        middleware: Callable[[Connection, ProtocolMessage, Callable], Awaitable[None]],
    ) -> None:
        """Add middleware to the routing pipeline."""
        self._middleware.append(middleware)

    async def route(self, connection: Connection, message: ProtocolMessage) -> None:
        """Route a message to its handler."""
        msg_type = message.type

        # Check for handler
        handler = self._handlers.get(msg_type)
        if not handler:
            logger.warning(f"No handler registered for message type: {msg_type}")
            return

        # Build middleware chain
        async def call_handler():
            await handler.handle(connection, message)

        # Apply middleware in reverse order
        next_handler = call_handler
        for middleware in reversed(self._middleware):
            next_handler = self._wrap_middleware(middleware, connection, message, next_handler)

        # Execute chain
        await next_handler()

    def _wrap_middleware(
        self,
        middleware: Callable,
        connection: Connection,
        message: ProtocolMessage,
        next_handler: Callable,
    ) -> Callable:
        """Wrap a middleware function."""
        async def wrapped():
            await middleware(connection, message, next_handler)
        return wrapped


# Pre-configured router factory
def create_router() -> MessageRouter:
    """Create a pre-configured message router with all handlers."""
    from application.websocket.handlers import (
        system_handlers,
        control_handlers,
        data_handlers,
        canvas_handlers,
    )

    router = MessageRouter()

    # System handlers
    router.register_handlers({
        MessageTypes.SYSTEM_CONNECTION_RESUME: system_handlers.ConnectionResumeHandler(),
        MessageTypes.SYSTEM_PONG: system_handlers.PongHandler(),
    })

    # Control handlers
    router.register_handlers({
        MessageTypes.CONTROL_CONVERSATION_CONFIG: control_handlers.ConversationConfigHandler(),
        MessageTypes.CONTROL_WIDGET_STATE: control_handlers.WidgetStateHandler(),
        MessageTypes.CONTROL_WIDGET_MOVED: control_handlers.WidgetMovedHandler(),
        MessageTypes.CONTROL_WIDGET_RESIZED: control_handlers.WidgetResizedHandler(),
        MessageTypes.CONTROL_FLOW_START: control_handlers.FlowStartHandler(),
        MessageTypes.CONTROL_FLOW_PAUSE: control_handlers.FlowPauseHandler(),
        MessageTypes.CONTROL_FLOW_CANCEL: control_handlers.FlowCancelHandler(),
        MessageTypes.CONTROL_NAVIGATION_NEXT: control_handlers.NavigationHandler(),
        MessageTypes.CONTROL_NAVIGATION_PREVIOUS: control_handlers.NavigationHandler(),
        MessageTypes.CONTROL_NAVIGATION_SKIP: control_handlers.NavigationHandler(),
    })

    # Data handlers
    router.register_handlers({
        MessageTypes.DATA_MESSAGE_SEND: data_handlers.MessageSendHandler(),
        MessageTypes.DATA_RESPONSE_SUBMIT: data_handlers.ResponseSubmitHandler(),
        MessageTypes.DATA_TOOL_RESULT: data_handlers.ToolResultHandler(),
        MessageTypes.DATA_AUDIT_EVENTS: data_handlers.AuditEventsHandler(),
    })

    # Canvas handlers
    router.register_handlers({
        MessageTypes.CONTROL_CANVAS_CONNECTION_CREATED: canvas_handlers.ConnectionCreatedHandler(),
        MessageTypes.CONTROL_CANVAS_GROUP_TOGGLED: canvas_handlers.GroupToggledHandler(),
        MessageTypes.CONTROL_CANVAS_LAYER_TOGGLED: canvas_handlers.LayerToggledHandler(),
        MessageTypes.CONTROL_CANVAS_SELECTION_CHANGED: canvas_handlers.SelectionChangedHandler(),
        MessageTypes.CONTROL_CANVAS_BOOKMARK_NAVIGATE: canvas_handlers.BookmarkNavigateHandler(),
        MessageTypes.CONTROL_CANVAS_PRESENTATION_NAVIGATED: canvas_handlers.PresentationNavigatedHandler(),
    })

    return router
```

### 3.3 BaseHandler

Abstract base class for message handlers.

```python
# src/agent-host/application/websocket/handlers/base.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel

from application.protocol import ProtocolMessage

if TYPE_CHECKING:
    from application.websocket.manager import Connection

TPayload = TypeVar("TPayload", bound=BaseModel)


class BaseHandler(ABC, Generic[TPayload]):
    """Base class for WebSocket message handlers."""

    payload_type: type[TPayload] | None = None

    async def handle(self, connection: Connection, message: ProtocolMessage) -> None:
        """Handle an incoming message."""
        # Validate payload if type is specified
        payload = None
        if self.payload_type and message.payload:
            payload = self.payload_type.model_validate(message.payload)

        # Call implementation
        await self.process(connection, message, payload)

    @abstractmethod
    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage,
        payload: TPayload | None,
    ) -> None:
        """Process the message. Override in subclasses."""
        pass
```

---

## 4. Message Handling

### 4.1 System Handlers

```python
# src/agent-host/application/websocket/handlers/system_handlers.py

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from application.protocol import (
    ProtocolMessage,
    MessageTypes,
    SystemConnectionResumePayload,
    SystemConnectionResumedPayload,
    SystemPingPongPayload,
    create_message,
)
from application.websocket.handlers.base import BaseHandler

if TYPE_CHECKING:
    from application.websocket.manager import Connection


class ConnectionResumeHandler(BaseHandler[SystemConnectionResumePayload]):
    """Handle connection resume requests."""

    payload_type = SystemConnectionResumePayload

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage,
        payload: SystemConnectionResumePayload | None,
    ) -> None:
        if not payload:
            return

        # Validate the previous connection
        # In production, check Redis for the old connection state

        # For now, just acknowledge the resume
        response_payload = SystemConnectionResumedPayload(
            previous_connection_id=payload.previous_connection_id,
            new_connection_id=connection.connection_id,
            messages_replayed=0,  # Would replay missed messages
            state_restored=True,
        )

        response = create_message(
            msg_type=MessageTypes.SYSTEM_CONNECTION_RESUMED,
            payload=response_payload,
            source="server",
        )
        await connection.send(response)


class PongHandler(BaseHandler[SystemPingPongPayload]):
    """Handle pong responses from clients."""

    payload_type = SystemPingPongPayload

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage,
        payload: SystemPingPongPayload | None,
    ) -> None:
        # Just update last activity (already done in manager)
        # Could calculate latency from timestamp
        pass
```

### 4.2 Data Handlers

```python
# src/agent-host/application/websocket/handlers/data_handlers.py
# ⚠️ PATTERN: VERIFY BEFORE USE - Check pattern-discovery-reference.md

from __future__ import annotations

from typing import TYPE_CHECKING

# ✅ VERIFIED: This import is correct
from neuroglia.mediation import Mediator

from application.protocol import (
    ProtocolMessage,
    MessageTypes,
    MessageSendPayload,
    ResponseSubmitPayload,
    ToolResultPayload,
    AuditEventsPayload,
    MessageAckPayload,
    create_message,
)
from application.websocket.handlers.base import BaseHandler
from application.commands.websocket import (
    ProcessMessageCommand,
    SubmitResponseCommand,
    ProcessToolResultCommand,
    StoreAuditEventsCommand,
)

if TYPE_CHECKING:
    from application.websocket.manager import Connection


class MessageSendHandler(BaseHandler[MessageSendPayload]):
    """Handle user messages."""

    payload_type = MessageSendPayload

    def __init__(self, mediator: Mediator):
        self.mediator = mediator

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage,
        payload: MessageSendPayload | None,
    ) -> None:
        if not payload:
            return

        # Dispatch to domain via command
        command = ProcessMessageCommand(
            conversation_id=connection.conversation_id,
            user_id=connection.user_id,
            content=payload.content,
            content_type=payload.content_type,
            metadata=payload.metadata,
        )

        result = await self.mediator.execute_async(command)

        # Send acknowledgment
        ack_payload = MessageAckPayload(
            client_message_id=payload.client_message_id,
            server_message_id=result.message_id,
            status="accepted",
        )

        ack = create_message(
            msg_type=MessageTypes.DATA_MESSAGE_ACK,
            payload=ack_payload,
            source="server",
        )
        await connection.send(ack)


class ResponseSubmitHandler(BaseHandler[ResponseSubmitPayload]):
    """Handle widget response submissions."""

    payload_type = ResponseSubmitPayload

    def __init__(self, mediator: Mediator):
        self.mediator = mediator

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage,
        payload: ResponseSubmitPayload | None,
    ) -> None:
        if not payload:
            return

        # Dispatch to domain
        command = SubmitResponseCommand(
            conversation_id=connection.conversation_id,
            widget_id=payload.widget_id,
            response_id=payload.response_id,
            value=payload.value,
            metadata=payload.metadata,
        )

        await self.mediator.execute_async(command)


class ToolResultHandler(BaseHandler[ToolResultPayload]):
    """Handle tool execution results from client-side tools."""

    payload_type = ToolResultPayload

    def __init__(self, mediator: Mediator):
        self.mediator = mediator

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage,
        payload: ToolResultPayload | None,
    ) -> None:
        if not payload:
            return

        command = ProcessToolResultCommand(
            conversation_id=connection.conversation_id,
            tool_call_id=payload.tool_call_id,
            result=payload.result,
            success=payload.success,
            error=payload.error,
        )

        await self.mediator.execute_async(command)


class AuditEventsHandler(BaseHandler[AuditEventsPayload]):
    """Handle audit telemetry events."""

    payload_type = AuditEventsPayload

    def __init__(self, mediator: Mediator):
        self.mediator = mediator

    async def process(
        self,
        connection: Connection,
        message: ProtocolMessage,
        payload: AuditEventsPayload | None,
    ) -> None:
        if not payload:
            return

        command = StoreAuditEventsCommand(
            conversation_id=connection.conversation_id,
            widget_id=payload.widget_id,
            events=payload.events,
        )

        await self.mediator.execute_async(command)
```

---

## 5. Domain Integration

### 5.1 How Domain Events Work in This Codebase

**Critical Understanding:**

1. **Repository auto-publishes events**: The `neuroglia.data.infrastructure.abstractions.Repository`
   base class automatically calls `mediator.publish_async(event)` after `add_async()` and `update_async()`.

2. **Mediator auto-discovers handlers**: The Mediator finds all `DomainEventHandler[TEvent]` classes
   in packages registered via `Mediator.configure(builder, ["application.events.domain", ...])`.

3. **No decorators needed**: Just extend `DomainEventHandler[TEvent]` and implement `handle_async()`.

**Reference implementation:** `src/tools-provider/application/events/domain/task_projection_handlers.py`

### 5.2 Domain Event → WebSocket Broadcasting (Verified Pattern)

```python
# src/agent-host/application/events/websocket/content_generated_handler.py
# ✅ VERIFIED PATTERN - Based on task_projection_handlers.py

import logging

from neuroglia.mediation import DomainEventHandler  # ✅ Correct import

from domain.events import ContentGeneratedEvent
from application.protocol import (
    MessageTypes,
    ContentChunkPayload,
    ContentCompletePayload,
    create_message,
)
from application.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


class ContentGeneratedEventHandler(DomainEventHandler[ContentGeneratedEvent]):
    """Broadcasts content generation events to WebSocket clients.

    This handler is automatically discovered by the Mediator when the
    'application.events.websocket' package is registered in main.py.

    The Repository automatically publishes ContentGeneratedEvent after
    persisting the content entity.
    """

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()  # ✅ Call parent __init__
        self.connection_manager = connection_manager

    async def handle_async(self, event: ContentGeneratedEvent) -> None:  # ✅ Correct method name
        """Handle content generated domain event."""
        logger.info(f"📤 Broadcasting content event: {event.content_id}")

        if event.is_complete:
            # Send completion message
            payload = ContentCompletePayload(
                content_id=event.content_id,
                total_length=event.total_length,
                role=event.role,
            )
            message = create_message(
                msg_type=MessageTypes.DATA_CONTENT_COMPLETE,
                payload=payload,
                source="server",
            )
        else:
            # Send chunk
            payload = ContentChunkPayload(
                content_id=event.content_id,
                chunk=event.chunk,
                sequence=event.sequence,
                is_final=event.is_final,
                role=event.role,
            )
            message = create_message(
                msg_type=MessageTypes.DATA_CONTENT_CHUNK,
                payload=payload,
                source="server",
            )

        # Broadcast to conversation
        await self.connection_manager.broadcast_to_conversation(
            conversation_id=event.conversation_id,
            message=message,
        )

        logger.info(f"✅ Broadcasted content event: {event.content_id}")
```

### 5.3 Widget Rendering Event Handler (Verified Pattern)

```python
# src/agent-host/application/events/websocket/widget_rendered_handler.py
# ✅ VERIFIED PATTERN - Based on task_projection_handlers.py

import logging

from neuroglia.mediation import DomainEventHandler  # ✅ Correct import

from domain.events import WidgetRenderedEvent
from application.protocol import (
    MessageTypes,
    create_message,
)
from application.protocol.widgets import WidgetRenderPayload
from application.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


class WidgetRenderedEventHandler(DomainEventHandler[WidgetRenderedEvent]):
    """Broadcasts widget render events to WebSocket clients.

    Auto-discovered by Mediator when package is registered in main.py.
    """

    def __init__(self, connection_manager: ConnectionManager):
        super().__init__()  # ✅ Call parent __init__
        self.connection_manager = connection_manager

    async def handle_async(self, event: WidgetRenderedEvent) -> None:  # ✅ Correct method name
        """Handle widget rendered domain event."""
        logger.info(f"📤 Broadcasting widget render: {event.widget_id}")

        payload = WidgetRenderPayload(
            widget_id=event.widget_id,
            widget_type=event.widget_type,
            config=event.config,
            layout=event.layout,
            constraints=event.constraints,
            state=event.state,
        )

        message = create_message(
            msg_type=MessageTypes.DATA_WIDGET_RENDER,
            payload=payload,
            source="server",
        )

        await self.connection_manager.broadcast_to_conversation(
            conversation_id=event.conversation_id,
            message=message,
        )

        logger.info(f"✅ Broadcasted widget render: {event.widget_id}")
```

### 5.4 Registering Event Handler Packages in main.py

```python
# In main.py - ensure websocket event handlers are discovered
Mediator.configure(builder, [
    "application.commands",
    "application.queries",
    "application.events",
    "application.events.domain",
    "application.events.websocket",  # ✅ Add this for WebSocket event handlers
])
```

---

## 6. State Management

### 6.1 Connection State Machine

```python
# src/agent-host/application/websocket/state.py

from enum import Enum, auto
from typing import Set


class ConnectionState(Enum):
    """WebSocket connection states."""

    CONNECTING = auto()
    CONNECTED = auto()
    AUTHENTICATED = auto()
    ACTIVE = auto()
    PAUSED = auto()
    RECONNECTING = auto()
    CLOSING = auto()
    CLOSED = auto()


# Valid state transitions
STATE_TRANSITIONS: dict[ConnectionState, Set[ConnectionState]] = {
    ConnectionState.CONNECTING: {ConnectionState.CONNECTED, ConnectionState.CLOSED},
    ConnectionState.CONNECTED: {ConnectionState.AUTHENTICATED, ConnectionState.CLOSING, ConnectionState.CLOSED},
    ConnectionState.AUTHENTICATED: {ConnectionState.ACTIVE, ConnectionState.CLOSING, ConnectionState.CLOSED},
    ConnectionState.ACTIVE: {ConnectionState.PAUSED, ConnectionState.RECONNECTING, ConnectionState.CLOSING, ConnectionState.CLOSED},
    ConnectionState.PAUSED: {ConnectionState.ACTIVE, ConnectionState.CLOSING, ConnectionState.CLOSED},
    ConnectionState.RECONNECTING: {ConnectionState.ACTIVE, ConnectionState.CLOSED},
    ConnectionState.CLOSING: {ConnectionState.CLOSED},
    ConnectionState.CLOSED: set(),
}


class ConnectionStateMachine:
    """State machine for WebSocket connection lifecycle."""

    def __init__(self, initial_state: ConnectionState = ConnectionState.CONNECTING):
        self._state = initial_state
        self._history: list[tuple[ConnectionState, ConnectionState]] = []

    @property
    def state(self) -> ConnectionState:
        return self._state

    def can_transition_to(self, new_state: ConnectionState) -> bool:
        """Check if transition to new state is valid."""
        valid_transitions = STATE_TRANSITIONS.get(self._state, set())
        return new_state in valid_transitions

    def transition_to(self, new_state: ConnectionState) -> bool:
        """Attempt to transition to a new state."""
        if not self.can_transition_to(new_state):
            return False

        old_state = self._state
        self._state = new_state
        self._history.append((old_state, new_state))
        return True

    @property
    def history(self) -> list[tuple[ConnectionState, ConnectionState]]:
        return self._history.copy()
```

---

## 7. Scaling & Infrastructure

### 7.1 Redis PubSub for Cross-Instance Messaging

```python
# src/agent-host/infrastructure/websocket/redis_pubsub.py

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Awaitable

import redis.asyncio as redis

from application.protocol import ProtocolMessage

logger = logging.getLogger(__name__)


class RedisPubSub:
    """Redis PubSub for cross-instance WebSocket messaging."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None
        self._listener_task: asyncio.Task | None = None
        self._handlers: dict[str, Callable[[dict], Awaitable[None]]] = {}

    async def connect(self) -> None:
        """Connect to Redis."""
        self._redis = redis.from_url(self.redis_url)
        self._pubsub = self._redis.pubsub()

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._listener_task:
            self._listener_task.cancel()
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()

    async def subscribe(
        self,
        channel: str,
        handler: Callable[[dict], Awaitable[None]],
    ) -> None:
        """Subscribe to a channel."""
        if not self._pubsub:
            raise RuntimeError("Not connected to Redis")

        await self._pubsub.subscribe(channel)
        self._handlers[channel] = handler

        # Start listener if not running
        if not self._listener_task:
            self._listener_task = asyncio.create_task(self._listen())

    async def publish(
        self,
        channel: str,
        message: dict[str, Any],
    ) -> None:
        """Publish a message to a channel."""
        if not self._redis:
            raise RuntimeError("Not connected to Redis")

        await self._redis.publish(channel, json.dumps(message))

    async def publish_to_conversation(
        self,
        conversation_id: str,
        message: ProtocolMessage,
    ) -> None:
        """Publish a protocol message to a conversation channel."""
        channel = f"conversation:{conversation_id}"
        await self.publish(channel, message.model_dump(by_alias=True))

    async def _listen(self) -> None:
        """Listen for messages on subscribed channels."""
        if not self._pubsub:
            return

        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode()

                    data = json.loads(message["data"])
                    handler = self._handlers.get(channel)
                    if handler:
                        await handler(data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
```

### 7.2 Connection Store

```python
# src/agent-host/infrastructure/websocket/connection_store.py

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis


class ConnectionStore:
    """Redis-backed connection registry for cross-instance state."""

    def __init__(self, redis_url: str, ttl_seconds: int = 3600):
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self._redis: redis.Redis | None = None

    async def connect(self) -> None:
        self._redis = redis.from_url(self.redis_url)

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.close()

    async def register_connection(
        self,
        connection_id: str,
        user_id: str,
        conversation_id: str | None,
        instance_id: str,
    ) -> None:
        """Register a connection in the store."""
        if not self._redis:
            raise RuntimeError("Not connected to Redis")

        key = f"connection:{connection_id}"
        data = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "instance_id": instance_id,
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }

        await self._redis.setex(key, self.ttl_seconds, json.dumps(data))

        # Add to user's connection set
        user_key = f"user_connections:{user_id}"
        await self._redis.sadd(user_key, connection_id)
        await self._redis.expire(user_key, self.ttl_seconds)

        # Add to conversation's connection set
        if conversation_id:
            conv_key = f"conversation_connections:{conversation_id}"
            await self._redis.sadd(conv_key, connection_id)
            await self._redis.expire(conv_key, self.ttl_seconds)

    async def unregister_connection(self, connection_id: str) -> None:
        """Remove a connection from the store."""
        if not self._redis:
            return

        key = f"connection:{connection_id}"
        data = await self._redis.get(key)

        if data:
            info = json.loads(data)

            # Remove from user's set
            user_key = f"user_connections:{info['user_id']}"
            await self._redis.srem(user_key, connection_id)

            # Remove from conversation's set
            if info.get("conversation_id"):
                conv_key = f"conversation_connections:{info['conversation_id']}"
                await self._redis.srem(conv_key, connection_id)

        await self._redis.delete(key)

    async def get_connection(self, connection_id: str) -> dict[str, Any] | None:
        """Get connection info."""
        if not self._redis:
            return None

        key = f"connection:{connection_id}"
        data = await self._redis.get(key)
        return json.loads(data) if data else None

    async def get_conversation_connections(
        self,
        conversation_id: str,
    ) -> list[str]:
        """Get all connection IDs for a conversation."""
        if not self._redis:
            return []

        key = f"conversation_connections:{conversation_id}"
        members = await self._redis.smembers(key)
        return [m.decode() if isinstance(m, bytes) else m for m in members]
```

---

## 8. Error Handling

### 8.1 Error Categories

```python
# src/agent-host/application/websocket/errors.py

from enum import Enum
from typing import Any

from application.protocol import SystemErrorPayload, AppCloseCode


class ErrorCategory(Enum):
    TRANSPORT = "transport"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    BUSINESS = "business"
    SERVER = "server"
    RATE_LIMIT = "rate_limit"


class WebSocketError(Exception):
    """Base WebSocket error."""

    def __init__(
        self,
        code: str,
        message: str,
        category: ErrorCategory = ErrorCategory.SERVER,
        recoverable: bool = True,
        details: dict[str, Any] | None = None,
        close_code: int | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.category = category
        self.recoverable = recoverable
        self.details = details or {}
        self.close_code = close_code

    def to_payload(self) -> SystemErrorPayload:
        return SystemErrorPayload(
            code=self.code,
            message=self.message,
            category=self.category.value,
            recoverable=self.recoverable,
            details=self.details if self.details else None,
        )


class AuthenticationError(WebSocketError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            code="AUTH_FAILED",
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            recoverable=False,
            close_code=AppCloseCode.AUTHENTICATION_INVALID,
        )


class ValidationError(WebSocketError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            category=ErrorCategory.VALIDATION,
            recoverable=True,
            details=details,
        )


class RateLimitError(WebSocketError):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            code="RATE_LIMITED",
            message=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            category=ErrorCategory.RATE_LIMIT,
            recoverable=True,
            details={"retryAfter": retry_after},
            close_code=AppCloseCode.RATE_LIMITED,
        )
```

---

## 9. Security

### 9.1 Authentication Middleware

```python
# src/agent-host/application/websocket/middleware/auth.py

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Awaitable

from application.protocol import ProtocolMessage
from application.websocket.errors import AuthenticationError

if TYPE_CHECKING:
    from application.websocket.manager import Connection


async def auth_middleware(
    connection: Connection,
    message: ProtocolMessage,
    next_handler: Callable[[], Awaitable[None]],
) -> None:
    """Verify connection is authenticated before processing messages."""

    # System messages are always allowed
    if message.type.startswith("system."):
        await next_handler()
        return

    # Check authentication
    if not connection.user_id:
        raise AuthenticationError("Connection not authenticated")

    await next_handler()
```

### 9.2 Rate Limiting Middleware

```python
# src/agent-host/application/websocket/middleware/rate_limit.py

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING, Callable, Awaitable

from application.protocol import ProtocolMessage
from application.websocket.errors import RateLimitError

if TYPE_CHECKING:
    from application.websocket.manager import Connection


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(
        self,
        rate: int = 100,  # messages per window
        window: int = 60,  # seconds
    ):
        self.rate = rate
        self.window = window
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        bucket = self._buckets[key]

        # Remove old entries
        bucket[:] = [t for t in bucket if now - t < self.window]

        if len(bucket) >= self.rate:
            return False

        bucket.append(now)
        return True


_rate_limiter = RateLimiter()


async def rate_limit_middleware(
    connection: Connection,
    message: ProtocolMessage,
    next_handler: Callable[[], Awaitable[None]],
) -> None:
    """Apply rate limiting to messages."""

    # Don't rate limit system messages
    if message.type.startswith("system."):
        await next_handler()
        return

    # Check rate limit by user
    if not _rate_limiter.check(connection.user_id):
        raise RateLimitError()

    await next_handler()
```

---

## 10. Implementation Recipes

### 10.1 Setting Up the WebSocket Endpoint

```python
# src/agent-host/api/controllers/websocket_controller.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from starlette.websockets import WebSocketState

from api.dependencies import get_current_user_ws
from application.websocket.manager import ConnectionManager
from application.websocket.router import create_router


router = APIRouter()

# Global connection manager (initialized on startup)
connection_manager: ConnectionManager | None = None


@router.on_event("startup")
async def startup():
    global connection_manager
    message_router = create_router()
    connection_manager = ConnectionManager(router=message_router)
    await connection_manager.start()


@router.on_event("shutdown")
async def shutdown():
    if connection_manager:
        await connection_manager.stop()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: str | None = Query(default=None),
    token: str | None = Query(default=None),
):
    """WebSocket endpoint for real-time communication."""

    # Authenticate
    user = await get_current_user_ws(websocket, token)
    if not user:
        await websocket.close(code=4000, reason="Authentication required")
        return

    # Accept and handle connection
    connection = await connection_manager.connect(
        websocket=websocket,
        user_id=user["sub"],
        conversation_id=conversation_id,
    )

    try:
        await connection_manager.handle_connection(connection)
    except WebSocketDisconnect:
        pass
    finally:
        await connection_manager.disconnect(connection.connection_id)
```

### 10.2 Dependency Injection Setup (Verified Pattern)

```python
# src/agent-host/application/websocket/manager.py
# ✅ VERIFIED PATTERN - Based on ToolProviderClient.configure() and MotorRepository.configure()

import logging

from neuroglia.hosting.abstractions import ApplicationBuilderBase  # ✅ Correct import

from application.websocket.router import create_router

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(
        self,
        router,
        heartbeat_interval: int = 30,
        connection_timeout: int = 300,
    ):
        self.router = router
        self.heartbeat_interval = heartbeat_interval
        self.connection_timeout = connection_timeout
        # ... rest of implementation

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> None:
        """
        Configure ConnectionManager in the service collection.

        Follows Neuroglia framework pattern for service registration.
        Uses the builder.services API, NOT ServiceCollection directly.

        Args:
            builder: The application builder (WebApplicationBuilder)
        """
        # Get settings from builder services
        from application.settings import Settings

        settings = next(
            (d.singleton for d in builder.services if d.service_type is Settings),
            None,
        )

        if settings is None:
            logger.warning("Settings not found, using defaults")
            settings = Settings()

        # Create router with registered handlers
        router = create_router()

        # Create singleton instance
        manager = ConnectionManager(
            router=router,
            heartbeat_interval=getattr(settings, 'websocket_heartbeat_interval', 30),
            connection_timeout=getattr(settings, 'websocket_connection_timeout', 300),
        )

        # Register as singleton
        builder.services.add_singleton(ConnectionManager, singleton=manager)
        logger.info("Configured ConnectionManager")
```

### 10.3 Registering in main.py

```python
# src/agent-host/main.py
# ✅ VERIFIED PATTERN - Based on existing main.py structure

from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mediation import Mediator
from neuroglia.mapping import Mapper
from neuroglia.serialization.json import JsonSerializer

from application.websocket.manager import ConnectionManager


def create_app() -> FastAPI:
    builder = WebApplicationBuilder(app_settings=app_settings)

    # Configure core Neuroglia services
    Mediator.configure(builder, [
        "application.commands",
        "application.queries",
        "application.events",
        "application.events.domain",
        "application.events.websocket",  # ✅ Add for WebSocket event handlers
    ])
    Mapper.configure(builder, ["application.mapping", "integration.models"])
    JsonSerializer.configure(builder, ["domain.entities", "domain.models"])

    # Configure WebSocket services
    ConnectionManager.configure(builder)

    # ... rest of app configuration
```

---

## Related Documents

- [Implementation Plan](./websocket-protocol-implementation-plan.md)
- [Frontend Implementation Guide](./frontend-implementation-guide.md)
- [Testing Strategy](./testing-strategy.md)
- [Protocol Specification](../specs/websocket-protocol-v1.md)

---

_Document maintained by: Development Team_
_Last review: December 18, 2025_
