# Phase 1: Core Infrastructure - Detailed Tasks

**Document Version:** 1.0.0
**Last Updated:** December 18, 2025
**Duration:** Weeks 1-3

---

## Objective

Establish reliable WebSocket communication foundation with authentication, reconnection, and message routing.

---

## Deliverables

1. Working WebSocket connection with authentication
2. Ping/pong keepalive mechanism
3. Automatic reconnection with exponential backoff
4. Error handling and reporting
5. Unit and integration tests

---

## Backend Tasks

### B1.1 WebSocket Endpoint in FastAPI

**File:** `src/agent-host/api/controllers/websocket_controller.py`

**Steps:**

1. Create FastAPI router with WebSocket endpoint at `/ws`
2. Accept query parameters: `token`, `conversation_id`
3. Validate token using existing Keycloak integration
4. Initialize connection via ConnectionManager
5. Handle WebSocket lifecycle (accept, receive loop, disconnect)

**Key Code Points:**

- Use `@router.websocket("/ws")` decorator
- Extract token from query string or cookie
- Call `await websocket.accept()` after validation
- Wrap receive loop in try/except for `WebSocketDisconnect`

---

### B1.2 Connection Lifecycle Manager

**File:** `src/agent-host/application/websocket/manager.py`

**Classes:**

- `Connection`: Represents single WebSocket connection
- `ConnectionManager`: Manages all connections

**Connection Properties:**

- `connection_id: str` - UUID
- `websocket: WebSocket` - Starlette WebSocket
- `user_id: str` - Authenticated user
- `conversation_id: str | None` - Optional conversation context
- `state_machine: ConnectionStateMachine` - Current state
- `created_at: datetime`
- `last_activity: datetime`
- `message_sequence: int` - For ordering

**ConnectionManager Methods:**

- `connect(websocket, user_id, conversation_id) -> Connection`
- `disconnect(connection_id) -> None`
- `handle_connection(connection) -> None` - Main receive loop
- `broadcast_to_conversation(conversation_id, message) -> None`
- `send_to_user(user_id, message) -> None`

**Background Tasks:**

- Heartbeat loop: Send `system.ping` every N seconds
- Cleanup loop: Remove stale connections

---

### B1.3 Message Router

**File:** `src/agent-host/application/websocket/router.py`

**Class:** `MessageRouter`

**Responsibilities:**

- Map message type strings to handler instances
- Support middleware chain (auth, rate limit, logging)
- Route incoming messages to appropriate handler

**Methods:**

- `register_handler(message_type, handler) -> None`
- `register_handlers(dict) -> None` - Bulk registration
- `add_middleware(middleware) -> None`
- `route(connection, message) -> None`

**Factory Function:**

- `create_router() -> MessageRouter` - Pre-configured with all handlers

---

### B1.4 System Message Handlers

**Files:**

- `src/agent-host/application/websocket/handlers/base.py`
- `src/agent-host/application/websocket/handlers/system_handlers.py`

**BaseHandler:**

```python
class BaseHandler(ABC, Generic[TPayload]):
    payload_type: type[TPayload] | None = None

    async def handle(connection, message) -> None
    @abstractmethod
    async def process(connection, message, payload) -> None
```

**System Handlers:**

- `ConnectionResumeHandler`: Handle `system.connection.resume`
- `PongHandler`: Handle `system.pong` (update last_activity)

---

### B1.5 Connection State Machine

**File:** `src/agent-host/application/websocket/state.py`

**States:**

```
CONNECTING → CONNECTED → AUTHENTICATED → ACTIVE
ACTIVE → PAUSED | RECONNECTING | CLOSING → CLOSED
```

**Class:** `ConnectionStateMachine`

- `state: ConnectionState`
- `can_transition_to(new_state) -> bool`
- `transition_to(new_state) -> bool`
- `history: list[tuple[old, new]]`

---

### B1.6 Redis PubSub (P1)

**File:** `src/agent-host/infrastructure/websocket/redis_pubsub.py`

**Purpose:** Enable cross-instance message broadcasting when running multiple server instances.

**Class:** `RedisPubSub`

- `connect() -> None`
- `disconnect() -> None`
- `subscribe(channel, handler) -> None`
- `publish(channel, message) -> None`
- `publish_to_conversation(conversation_id, message) -> None`

**Channels:**

- `conversation:{conversation_id}` - Per-conversation messages
- `user:{user_id}` - Per-user messages
- `broadcast` - Global broadcasts

---

### B1.7 Authentication Integration

**File:** `src/agent-host/api/dependencies.py`

**Function:** `get_current_user_ws(websocket, token) -> dict | None`

**Steps:**

1. Check for token in query string
2. If not present, check for session cookie
3. Validate token with existing Keycloak service
4. Return user claims or None

**Integration:**

- Reuse existing `get_current_user` logic
- Support both JWT bearer and session cookies
- Return `None` to trigger 4000 close code

---

### B1.8 Graceful Shutdown

**Location:** `src/agent-host/main.py` (lifespan)

**Steps:**

1. Register shutdown handler in FastAPI lifespan
2. Call `connection_manager.stop()`
3. Stop heartbeat/cleanup tasks
4. Send `system.connection.close` to all connections with reason "server_shutdown"
5. Close all WebSockets with code 1012 (SERVICE_RESTART)

---

## Frontend Tasks

### F1.1 WebSocket Client Class

**File:** `src/agent-host/ui/src/protocol/client.ts`

**Class:** `WebSocketClient`

**Constructor Options:**

```typescript
interface WebSocketClientOptions {
  url: string;
  token?: string;
  conversationId?: string;
  reconnect?: boolean;
  heartbeatInterval?: number;
}
```

**Public API:**

- `connect(): Promise<void>` - Establish connection
- `disconnect(code?, reason?): void` - Close connection
- `send<T>(type: string, payload: T): void` - Send message
- `state: ConnectionState` - Current state (getter)
- `connectionId: string | null` - Connection ID (getter)
- `on(event, handler): void` - Add event listener
- `off(event, handler): void` - Remove event listener

**Events:**

- `connected` - Connection established
- `disconnected` - Connection closed
- `error` - Error occurred
- `message` - Any message received

**Implementation Notes:**

- Build URL with query params: `?token=X&conversationId=Y`
- Auto-respond to `system.ping` with `system.pong`
- Store connection ID from `system.connection.established`
- Emit typed events using CustomEvent or EventEmitter pattern

---

### F1.2 Reconnection with Backoff

**File:** `src/agent-host/ui/src/protocol/reconnect.ts`

**Class:** `ReconnectionManager`

**Configuration:**

```typescript
interface ReconnectionConfig {
  baseDelay: number;      // 1000ms
  maxDelay: number;       // 30000ms
  maxAttempts: number;    // 10
  jitterFactor: number;   // 0.1
}
```

**Methods:**

- `start(): void` - Begin reconnection attempts
- `stop(): void` - Cancel reconnection
- `reset(): void` - Reset attempt counter
- `attempt: number` - Current attempt (getter)
- `nextDelay: number` - Delay before next attempt (getter)

**Algorithm:**

```typescript
calculateDelay(attempt: number): number {
  const delay = Math.min(
    this.config.baseDelay * Math.pow(2, attempt),
    this.config.maxDelay
  );
  const jitter = delay * this.config.jitterFactor * (Math.random() * 2 - 1);
  return Math.floor(delay + jitter);
}
```

**State Persistence:**

- Store `connectionId` in sessionStorage for resume
- Store `lastMessageSequence` for replay

---

### F1.3 Connection State Machine

**File:** `src/agent-host/ui/src/protocol/state-machine.ts`

**States:**

```typescript
type ConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'active'
  | 'reconnecting'
  | 'closed';
```

**Transitions:**

```
disconnected → connecting → connected → active
active → reconnecting → connecting
any → closed (terminal)
```

**Events:**

- Emit `statechange` event on transition
- Include `previousState` and `newState` in event

---

### F1.4 Message Bus

**File:** `src/agent-host/ui/src/protocol/message-bus.ts`

**Class:** `MessageBus`

**Methods:**

```typescript
subscribe<T>(type: string, handler: MessageHandler<T>): () => void;
subscribeOnce<T>(type: string, handler: MessageHandler<T>): () => void;
publish(message: ProtocolMessage): void;
```

**Wildcard Support:**

- `control.*` - All control plane messages
- `data.widget.*` - All widget data messages
- `*` - All messages (for debugging)

**Implementation:**

- Store handlers in `Map<string, Set<Handler>>`
- On publish, check exact match first, then wildcards
- Return unsubscribe function from subscribe

---

### F1.5 Protocol Message Serialization

**File:** `src/agent-host/ui/src/protocol/types.ts` (extend)

**Factory Function:**

```typescript
function createMessage<T>(
  type: string,
  payload: T,
  options?: { id?: string; correlationId?: string }
): ProtocolMessage<T>;
```

**Serialization:**

- Use `JSON.stringify` with camelCase keys (already correct)
- Include `timestamp` as ISO string
- Auto-generate `id` if not provided

---

### F1.6 System Message Handlers

**Location:** Registered via MessageBus

**Handlers:**

- `system.connection.established`: Store connectionId, update state
- `system.ping`: Auto-respond with `system.pong`
- `system.error`: Log error, emit event
- `system.connection.close`: Handle graceful close

---

### F1.7 Connection Status Component

**File:** `src/agent-host/ui/src/components/connection-status.ts`

**WebComponent:** `<connection-status>`

**Displays:**

- Current state (Connected, Connecting, Reconnecting, Disconnected)
- Reconnection countdown
- Connection quality indicator (optional)

**Styling:**

- Green dot: Connected
- Yellow dot: Connecting/Reconnecting
- Red dot: Disconnected
- Animate transitions

---

### F1.8 Debug/Logging Infrastructure

**File:** `src/agent-host/ui/src/core/logger.ts`

**Features:**

- Log levels: DEBUG, INFO, WARN, ERROR
- Configurable via `localStorage.setItem('debug', 'protocol:*')`
- Format: `[LEVEL] [COMPONENT] message`
- Include timestamps

**Components to log:**

- `protocol:client` - WebSocket client events
- `protocol:bus` - Message bus activity
- `protocol:reconnect` - Reconnection attempts

---

## Testing Tasks

### T1.1 Backend Unit Tests - Connection Manager

**File:** `tests/unit/websocket/test_manager.py`

**Test Cases:**

- `test_connect_creates_connection`
- `test_connect_sends_established_message`
- `test_disconnect_removes_connection`
- `test_broadcast_to_conversation`
- `test_send_to_user`
- `test_heartbeat_sends_ping`
- `test_cleanup_removes_stale_connections`

---

### T1.2 Backend Unit Tests - Message Router

**File:** `tests/unit/websocket/test_router.py`

**Test Cases:**

- `test_router_routes_to_handler`
- `test_router_handles_unknown_type`
- `test_middleware_chain_executes`
- `test_middleware_can_abort`

---

### T1.3 Frontend Unit Tests - Client

**File:** `tests/unit/protocol/client.test.ts`

**Test Cases:**

- `test_connect_establishes_connection`
- `test_connect_includes_auth_token`
- `test_send_serializes_message`
- `test_auto_responds_to_ping`
- `test_disconnect_closes_socket`
- `test_emits_connection_events`

---

### T1.4 Integration Tests - Connect/Disconnect

**File:** `tests/integration/test_connection_lifecycle.py`

**Test Cases:**

- `test_full_connection_lifecycle`
- `test_connection_with_conversation_id`
- `test_authentication_required`
- `test_invalid_token_rejected`
- `test_multiple_connections_same_user`

---

### T1.5 Integration Tests - Reconnection

**File:** `tests/integration/test_reconnection.py`

**Test Cases:**

- `test_reconnection_after_disconnect`
- `test_exponential_backoff`
- `test_max_attempts_exceeded`
- `test_resume_with_previous_connection_id`
- `test_message_replay_after_resume` (if applicable)

---

## Acceptance Criteria

- [ ] WebSocket connects within 500ms on localhost
- [ ] Authentication works with existing Keycloak tokens
- [ ] Reconnection succeeds within 5 attempts
- [ ] Ping/pong keeps connection alive over 5 minutes
- [ ] All unit tests pass with >80% coverage
- [ ] Integration tests pass for connection lifecycle
- [ ] Connection status UI reflects real state

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Protocol Pydantic models | ✅ Complete | `application/protocol/` |
| Protocol TypeScript types | ✅ Complete | `websocket-protocol-v1.types.ts` |
| Keycloak integration | ✅ Exists | Reuse existing auth |
| FastAPI app structure | ✅ Exists | Add new router |
| Redis (for PubSub) | ✅ Docker | Optional for Phase 1 |

---

## Related Documents

- [Implementation Plan](./websocket-protocol-implementation-plan.md)
- [Backend Implementation Guide](./backend-implementation-guide.md)
- [Frontend Implementation Guide](./frontend-implementation-guide.md)
- [Testing Strategy](./testing-strategy.md)

---

_Document maintained by: Development Team_
_Last review: December 18, 2025_
