# WebSocket Protocol v1.0.0 - Essentials Summary

> **Purpose:** Condensed behavioral rules for implementation prompts.
> **Full Specification:** `docs/specs/websocket-protocol-v1.md` (~5400 lines)
> **Pydantic Models:** `src/agent-host/application/protocol/` (already implemented)

---

## 1. Protocol Fundamentals

### 1.1 Transport

- **Single WebSocket connection:** `wss://{host}/api/chat/ws`
- **Authentication:** Session cookie OR JWT query parameter (`?token=eyJ...`)
- **Connection parameters:** `conversation_id`, `definition_id`, `token`

### 1.2 Message Envelope (CloudEvents-Inspired)

```python
{
    "id": "msg_unique_id",           # Required: UUID/nanoid
    "type": "plane.category.action", # Required: Hierarchical
    "version": "1.0",                # Required: Protocol version
    "timestamp": "ISO8601Z",         # Required: With milliseconds
    "source": "client|server",       # Required: Origin
    "conversationId": "conv_xyz",    # Optional: null for system messages
    "payload": { ... }               # Required: Message-specific
}
```

### 1.3 Message Type Hierarchy

```
{plane}.{category}.{action}

Planes:
- system   → Connection lifecycle, errors
- control  → UI state, settings, commands
- data     → Content, widgets, responses
```

---

## 2. Connection Lifecycle

### 2.1 Handshake Sequence

```
Client                                    Server
  │──── WebSocket Upgrade (with auth) ────────►│
  │◄─── HTTP 101 Switching Protocols ──────────│
  │◄─── system.connection.established ─────────│
  │──── control.flow.start ───────────────────►│
  │◄─── control.conversation.config ───────────│
  │◄─── control.conversation.deadline ─────────│
  │◄─── control.item.context ──────────────────│
```

### 2.2 Keepalive

- **Client sends:** `system.ping` every **30 seconds**
- **Server responds:** `system.pong` within **5 seconds**
- **No response:** Client initiates reconnection

### 2.3 Reconnection Protocol

**Reconnectable codes:** 1006, 1011, 1012, 1013, 4006, 4014
**Do NOT reconnect:** 1000, 4000-4002, 4003, 4004, 4005, 4010

**Exponential Backoff:**

```
Attempt 1: ~1-2s
Attempt 2: ~2-3s
Attempt 3: ~4-5s
Attempt 4: ~8-9s
Attempt 5+: capped at 30s
```

**Resume sequence:**

```
Client → system.connection.resume {conversationId, lastMessageId, clientState}
Server → system.connection.resumed {resumedFromMessageId, stateValid}
```

### 2.4 Graceful Disconnect

```python
# Reasons: user_logout, session_expired, server_shutdown,
#          conversation_complete, idle_timeout
```

---

## 3. State Machines

### 3.1 Widget States

```
         ┌───────────────────┐
         │                   ▼
[render]─►  ACTIVE  ◄────► READONLY
              │              │
              ▼              ▼
           DISABLED ◄───► HIDDEN
```

| State | User Can Interact | Visible | Preserved Response |
|-------|-------------------|---------|-------------------|
| `active` | Yes | Yes | N/A |
| `readonly` | No | Yes (styled) | Yes |
| `disabled` | No | Yes (grayed) | No |
| `hidden` | No | No | Optional |

**Transitions via:** `control.widget.state {widgetId, state: "readonly"}`

### 3.2 Conversation Flow States

```
[START] → ACTIVE → PAUSED → ACTIVE → COMPLETED
                     │
                     └─────► CANCELLED
```

---

## 4. Control Levels & Scope

| Level | Scope | Example Messages |
|-------|-------|------------------|
| Connection | WebSocket session | `system.*` |
| Conversation | Entire conversation | `control.conversation.*` |
| Item | Current template step | `control.item.*`, `control.timer.*` |
| Widget | Specific widget | `control.widget.*`, `data.widget.*` |

---

## 5. Core Message Types (Backend Implementation Priority)

### 5.1 System Messages

| Type | Direction | Description |
|------|-----------|-------------|
| `system.connection.established` | S→C | Connection accepted |
| `system.connection.resume` | C→S | Resume after disconnect |
| `system.connection.resumed` | S→C | Resume confirmation |
| `system.connection.close` | Both | Graceful shutdown |
| `system.ping` / `system.pong` | Both | Keepalive |
| `system.error` | S→C | Error notification |

### 5.2 Control - Conversation Level (Server → Client)

| Type | Description |
|------|-------------|
| `control.conversation.config` | Initial settings (displayMode, navigation, etc.) |
| `control.conversation.deadline` | Absolute deadline timestamp |
| `control.conversation.display` | Set flow/canvas mode |
| `control.conversation.pause` | Server-initiated pause |
| `control.conversation.resume` | Server-initiated resume |
| `control.conversation.complete` | Conversation finished |

### 5.3 Control - Item Level

| Type | Direction | Description |
|------|-----------|-------------|
| `control.item.context` | S→C | New item started |
| `control.item.score` | S→C | Score feedback |
| `control.item.timeout` | S→C | Item time expired |
| `control.item.expired` | C→S | Frontend reports timeout |

### 5.4 Control - Widget Level

| Type | Direction | Description |
|------|-----------|-------------|
| `control.widget.state` | S→C | Set active/readonly/disabled/hidden |
| `control.widget.focus` | S→C | Request focus |
| `control.widget.validation` | S→C | Validation feedback |

### 5.5 Data - Content Streaming

| Type | Direction | Description |
|------|-----------|-------------|
| `data.content.chunk` | S→C | Streaming text chunk |
| `data.content.complete` | S→C | Stream finished |
| `data.message.send` | C→S | User text message |

### 5.6 Data - Widgets

| Type | Direction | Description |
|------|-----------|-------------|
| `data.widget.render` | S→C | Render widget with config |
| `data.response.submit` | C→S | User submitted response |

### 5.7 Data - Tools

| Type | Direction | Description |
|------|-----------|-------------|
| `data.tool.call` | S→C | Tool being invoked |
| `data.tool.result` | S→C | Tool execution result |

---

## 6. Error Handling

### 6.1 Error Message Structure

```python
{
    "type": "system.error",
    "payload": {
        "category": "validation|authentication|business|server|rate_limit",
        "code": "INVALID_WIDGET_RESPONSE",
        "message": "Human-readable description",
        "details": { ... },
        "isRetryable": true,
        "retryAfterMs": 1000  # null if immediate retry OK
    }
}
```

### 6.2 Error Categories

| Category | Description | Retryable |
|----------|-------------|-----------|
| `transport` | Connection issues | Usually yes |
| `authentication` | Auth failures | No (re-auth) |
| `validation` | Invalid data | No (fix data) |
| `business` | Logic errors | Depends |
| `server` | Internal errors | Yes (backoff) |
| `rate_limit` | Throttled | Yes (wait) |

### 6.3 Critical Error Codes

| Code | Category | Client Action |
|------|----------|---------------|
| `AUTH_EXPIRED` | authentication | Redirect to login |
| `CONVERSATION_PAUSED` | business | Show paused UI |
| `TIME_EXPIRED` | business | Disable input |
| `RATE_LIMITED` | rate_limit | Wait + retry |
| `LLM_ERROR` | server | Show error + retry |

---

## 7. Timing & Deadlines

### 7.1 Architecture

```
CONVERSATION DEADLINE (Server, absolute timestamp)
    └── ITEM TIMER (Frontend countdown, seconds from server)
```

### 7.2 Clock Synchronization

1. Server sends `serverTime` in `system.connection.established`
2. Client calculates `offset = serverTime - clientTime`
3. All deadline comparisons use adjusted time

### 7.3 Timer Behavior

- **Deadline:** Server enforces; sends in every `control.item.context`
- **Item timer:** Frontend counts down; sends `control.item.expired`
- **Re-sync:** Deadline refreshed on every item transition

---

## 8. Widget Response Format

### 8.1 Generic Response Structure

```python
{
    "type": "data.response.submit",
    "payload": {
        "widgetId": "widget_mc_1",
        "value": { ... },  # Widget-specific
        "submittedAt": "ISO8601Z"
    }
}
```

### 8.2 Widget-Specific Values

| Widget Type | Value Format |
|-------------|--------------|
| `multiple_choice` | `{"selected": ["A"]}` or `"A"` |
| `free_text` | `{"text": "..."}` |
| `code_editor` | `{"code": "...", "language": "python"}` |
| `slider` | `{"value": 75}` |
| `rating` | `{"rating": 4}` |
| `file_upload` | `{"files": [{id, name, size, type}]}` |
| `iframe` | `{"type": "iframe_result", "data": {...}}` |

---

## 9. Display Modes

### 9.1 Flow Mode (1D)

- Traditional chat interface
- Items stack vertically (append) or replace
- Widgets inline with content

### 9.2 Canvas Mode (2D)

- Spatial layout with pan/zoom
- Widgets positioned by coordinates
- Connections between widgets
- Groups, layers, annotations

**Mode switch:** `control.conversation.display {mode: "canvas"}`

---

## 10. Configuration Dependencies

### 10.1 Required Combinations

| Option | Requires |
|--------|----------|
| `allowConcurrentItemWidgets: true` | `allowBackwardNavigation: true` |
| `allowConcurrentItemWidgets: true` | `displayMode: "append"` OR `mode: "canvas"` |

### 10.2 Conflicting Combinations (Server Must Reject)

| Combination | Issue |
|-------------|-------|
| `displayMode: "replace"` + `allowConcurrentItemWidgets: true` | Items can't coexist |
| `widgetCompletionBehavior: "hidden"` + `allowBackwardNavigation: true` | Can't revisit hidden |

---

## 11. WebSocket Close Codes

### 11.1 Standard Codes

| Code | Action |
|------|--------|
| `1000` | Normal close - no reconnect |
| `1006` | Abnormal - reconnect with backoff |
| `1011` | Server error - reconnect with backoff |
| `1012` | Server restart - reconnect after delay |

### 11.2 Application Codes (4000-4999)

| Code | Action |
|------|--------|
| `4000-4002` | Auth issue - redirect to login |
| `4003-4005` | Unrecoverable - show error |
| `4006` | Rate limited - wait + reconnect |
| `4007` | Duplicate - close silently |

---

## 12. Implementation Checklist

### 12.1 Backend Must Implement

- [ ] Message envelope validation (all required fields)
- [ ] Message type routing (hierarchical dispatch)
- [ ] Connection established on WebSocket accept
- [ ] Ping/pong keepalive handling
- [ ] Graceful close with reason codes
- [ ] Resume protocol with state validation
- [ ] Error response with category/code/retryable
- [ ] Deadline enforcement (reject after expiry)
- [ ] Widget state transitions
- [ ] Content streaming (chunk + complete)

### 12.2 Backend Should Emit

- [ ] `system.connection.established` immediately on connect
- [ ] `control.conversation.config` at conversation start
- [ ] `control.conversation.deadline` with every item
- [ ] `control.item.context` for item transitions
- [ ] `control.widget.state` after response submission
- [ ] `system.error` for all error conditions

---

## 13. Quick Reference: Type → Pydantic Model

Pydantic models are in `src/agent-host/application/protocol/`:

| Message Type Prefix | Module |
|---------------------|--------|
| `system.*` | `system_messages.py` |
| `control.conversation.*` | `control_messages.py` |
| `control.item.*` | `control_messages.py` |
| `control.widget.*` | `control_messages.py` |
| `control.canvas.*` | `canvas_messages.py` |
| `control.audit.*` | `audit_messages.py` |
| `data.content.*` | `data_messages.py` |
| `data.widget.*` | `data_messages.py` |
| `data.response.*` | `data_messages.py` |
| `data.tool.*` | `data_messages.py` |
| `data.iframe.*` | `iframe_messages.py` |
| `data.audit.*` | `audit_messages.py` |

---

## 14. References

- **Full Protocol Spec:** [websocket-protocol-v1.md](../../specs/websocket-protocol-v1.md)
- **TypeScript Types:** [websocket-protocol-v1.types.ts](../../specs/websocket-protocol-v1.types.ts)
- **Pydantic Models:** [src/agent-host/application/protocol/](../../../src/agent-host/application/protocol/)
- **Pattern Reference:** [pattern-discovery-reference.md](./pattern-discovery-reference.md)
