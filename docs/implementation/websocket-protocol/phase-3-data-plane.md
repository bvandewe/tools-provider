# Phase 3: Data Plane - Detailed Tasks

**Document Version:** 1.0.0
**Last Updated:** December 18, 2025
**Duration:** Weeks 7-9

---

## Objective

Enable content streaming, tool execution, and response handling with AI agent integration.

---

## Deliverables

1. Real-time content streaming with progressive display
2. Tool call execution flow (server → client → server)
3. User message handling
4. Response submission and persistence
5. Full conversation E2E test

---

## Backend Tasks

### B3.1 Content Streaming

**File:** `src/agent-host/application/events/websocket/content_generated_handler.py`

**Event Handler:** `ContentGeneratedEventHandler`

**Flow:**

1. AI agent generates content in chunks
2. Domain emits `ContentGeneratedEvent` per chunk
3. Handler converts to `data.content.chunk` message
4. Handler broadcasts to conversation

**Chunking Strategy:**

- Chunk by tokens (configurable, default 10-20 tokens)
- Or chunk by natural breaks (sentences, paragraphs)
- Include sequence number for ordering
- Mark final chunk with `is_final: true`

**Completion:**

- When streaming complete, emit `ContentGeneratedCompleteEvent`
- Handler sends `data.content.complete` with total stats

**Message Payloads:**

```python
ContentChunkPayload:
    content_id: str
    chunk: str
    sequence: int
    is_final: bool
    role: ContentRole  # "assistant" | "user" | "system"

ContentCompletePayload:
    content_id: str
    total_length: int
    role: ContentRole
```

---

### B3.2 Tool Call Dispatch

**File:** `src/agent-host/application/events/websocket/tool_call_handler.py`

**Event Handler:** `ToolCallEventHandler`

**Flow:**

1. AI agent decides to call a tool
2. Domain emits `ToolCallRequestedEvent`
3. Handler sends `data.tool.call` to client
4. Client executes tool (client-side tools)
5. Client sends `data.tool.result` back

**Tool Types:**

- **Server-side tools**: Execute on server, result sent to AI
- **Client-side tools**: Execute in browser, result returned via WebSocket

**Payload:**

```python
ToolCallPayload:
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    timeout: int | None  # Seconds before timeout
```

---

### B3.3 Tool Result Handling

**File:** `src/agent-host/application/websocket/handlers/data_handlers.py`

**Handler:** `ToolResultHandler`

**Processing:**

1. Validate tool_call_id matches pending call
2. Validate result schema if defined
3. Dispatch `ProcessToolResultCommand` to domain
4. Domain continues AI conversation with result

**Payload:**

```python
ToolResultPayload:
    tool_call_id: str
    result: Any
    success: bool
    error: str | None
    execution_time_ms: int | None
```

**Timeout Handling:**

- Track pending tool calls with timestamps
- If result not received within timeout, send error to AI
- Notify client of timeout via `system.error`

---

### B3.4 User Message Processing

**File:** `src/agent-host/application/websocket/handlers/data_handlers.py`

**Handler:** `MessageSendHandler`

**Flow:**

1. Client sends `data.message.send`
2. Handler validates message content
3. Dispatch `ProcessMessageCommand` to domain
4. Domain persists message, triggers AI
5. Handler sends `data.message.ack` with server message ID

**Rate Limiting:**

- Max 10 messages per minute per user
- Max 10KB message size
- Reject with `system.error` if exceeded

**Payload:**

```python
MessageSendPayload:
    content: str
    content_type: str  # "text" | "markdown" | "html"
    client_message_id: str | None  # For correlation
    attachments: list[Attachment] | None
    metadata: dict | None
```

---

### B3.5 Response Submission

**File:** `src/agent-host/application/websocket/handlers/data_handlers.py`

**Handler:** `ResponseSubmitHandler`

**Flow:**

1. Client submits widget response via `data.response.submit`
2. Handler validates against widget config
3. Dispatch `SubmitResponseCommand` to domain
4. Domain scores response, emits events
5. Validation result sent back to client

**Payload:**

```python
ResponseSubmitPayload:
    widget_id: str
    response_id: str  # Client-generated UUID
    value: Any  # Widget-specific value type
    submitted_at: str  # ISO timestamp
    time_spent_ms: int | None
    metadata: ResponseMetadata | None
```

**Idempotency:**

- Use response_id as idempotency key
- If same response_id received, return cached result
- Prevent duplicate submissions

---

### B3.6 AI Agent Backend Integration

**File:** `src/agent-host/application/services/agent_service.py`

**Integration Points:**

- Connect to AI agent (LLM) service
- Stream responses token by token
- Handle tool calls from AI
- Manage conversation context

**Architecture:**

```
WebSocket Handler → Domain Command → Agent Service → LLM API
                                         ↓
                                   Domain Events ← Tool Execution
                                         ↓
                                   WebSocket Broadcast
```

**Considerations:**

- Use async streaming for LLM responses
- Handle LLM timeouts (30s default)
- Rate limit AI calls per conversation
- Cache conversation context for efficiency

---

### B3.7 Rate Limiting for Data Messages

**File:** `src/agent-host/application/websocket/middleware/rate_limit.py`

**Limits:**

| Message Type | Rate | Window |
|--------------|------|--------|
| `data.message.send` | 10 | 60s |
| `data.response.submit` | 30 | 60s |
| `data.audit.events` | 10 | 60s |
| `data.tool.result` | 20 | 60s |

**Implementation:**

- Token bucket per user per message type
- Return `system.error` with `retryAfter` on exceed
- Close connection on persistent abuse

---

## Frontend Tasks

### F3.1 Content Streaming Display

**File:** `src/agent-host/ui/src/components/content-stream.ts`

**WebComponent:** `<content-stream>`

**Features:**

- Progressive text rendering
- Smooth character/word reveal animation
- Support markdown rendering
- Handle multiple concurrent streams

**Implementation:**

```typescript
class ContentStream extends HTMLElement {
  private chunks: Map<string, ChunkBuffer> = new Map();

  handleChunk(payload: ContentChunkPayload): void {
    let buffer = this.chunks.get(payload.content_id);
    if (!buffer) {
      buffer = new ChunkBuffer(payload.content_id);
      this.chunks.set(payload.content_id, buffer);
    }
    buffer.addChunk(payload.chunk, payload.sequence);
    this.render(buffer);
  }

  handleComplete(payload: ContentCompletePayload): void {
    const buffer = this.chunks.get(payload.content_id);
    if (buffer) {
      buffer.finalize();
      this.finalRender(buffer);
    }
  }
}
```

---

### F3.2 Markdown/HTML Rendering

**File:** `src/agent-host/ui/src/core/renderer.ts`

**Options:**

1. **Marked.js** - Lightweight markdown parser
2. **Custom parser** - If minimal dependencies needed
3. **Sanitized HTML** - For HTML content type

**Security:**

- Sanitize all HTML before rendering
- Strip dangerous tags: `<script>`, `<iframe>`, `<object>`
- Whitelist safe tags and attributes
- Use DOMPurify or similar library

**Syntax Highlighting:**

- Use Prism.js or Highlight.js for code blocks
- Lazy load language modules
- Theme integration with design system

---

### F3.3 Tool Call UI

**File:** `src/agent-host/ui/src/components/tool-call.ts`

**WebComponent:** `<tool-call-indicator>`

**States:**

- `pending` - Tool call dispatched, waiting for result
- `executing` - Tool is running
- `success` - Tool completed successfully
- `error` - Tool failed
- `timeout` - Tool timed out

**Display:**

- Tool name and icon
- Arguments (sanitized, expandable)
- Progress/spinner for pending
- Result preview for success
- Error message for failure

---

### F3.4 Message Input Component

**File:** `src/agent-host/ui/src/components/message-input.ts`

**WebComponent:** `<message-input>`

**Features:**

- Multi-line textarea
- Submit button
- Keyboard shortcut (Enter or Cmd/Ctrl+Enter)
- Character count (if limit)
- File attachment button (future)

**Events:**

```typescript
// Dispatched when user submits message
this.dispatchEvent(new CustomEvent('submit', {
  detail: { content: this.value, contentType: 'text' }
}));
```

**Integration:**

```typescript
messageInput.addEventListener('submit', (e) => {
  client.send(MessageTypes.DATA_MESSAGE_SEND, {
    content: e.detail.content,
    contentType: e.detail.contentType,
    clientMessageId: crypto.randomUUID(),
  });
});
```

---

### F3.5 Response Submission Logic

**File:** `src/agent-host/ui/src/protocol/response-handler.ts`

**Functions:**

```typescript
async function submitResponse(
  client: WebSocketClient,
  widgetId: string,
  value: unknown,
  metadata?: ResponseMetadata
): Promise<void> {
  const responseId = crypto.randomUUID();
  const startTime = performance.now();

  client.send(MessageTypes.DATA_RESPONSE_SUBMIT, {
    widgetId,
    responseId,
    value,
    submittedAt: new Date().toISOString(),
    timeSpentMs: Math.round(performance.now() - startTime),
    metadata,
  });

  // Store for potential retry
  pendingResponses.set(responseId, { widgetId, value });
}
```

**Optimistic Update:**

- Mark widget as submitted immediately
- Rollback if server rejects
- Show loading state during validation

---

### F3.6 Progress Indicators

**File:** `src/agent-host/ui/src/components/progress-indicator.ts`

**Types:**

- **Streaming progress**: Animated dots or typing indicator
- **Submission progress**: Spinner or progress bar
- **Tool execution progress**: Named step indicator

**Styling:**

```scss
.progress-streaming {
  display: inline-flex;
  gap: 4px;

  .dot {
    width: 8px;
    height: 8px;
    background: $color-primary;
    border-radius: 50%;
    animation: bounce 1s infinite;

    &:nth-child(2) { animation-delay: 0.1s; }
    &:nth-child(3) { animation-delay: 0.2s; }
  }
}
```

---

## Testing Tasks

### T3.1 Streaming Unit Tests

**Backend:** `tests/unit/websocket/test_streaming.py`

**Test Cases:**

- `test_chunk_message_structure`
- `test_sequence_ordering`
- `test_completion_message`
- `test_concurrent_streams`

**Frontend:** `tests/unit/components/content-stream.test.ts`

**Test Cases:**

- `test_renders_chunks_progressively`
- `test_handles_out_of_order_chunks`
- `test_finalizes_on_complete`
- `test_renders_markdown`

---

### T3.2 Tool Execution Integration Tests

**File:** `tests/integration/test_tool_execution.py`

**Test Cases:**

- `test_tool_call_sent_to_client`
- `test_tool_result_received`
- `test_tool_timeout_handled`
- `test_tool_error_propagated`
- `test_multiple_tool_calls`

---

### T3.3 E2E: Full Conversation Flow

**File:** `tests/e2e/conversation.spec.ts`

**Scenario:**

1. User connects to conversation
2. System sends greeting
3. User sends message
4. AI streams response
5. AI renders widget
6. User interacts with widget
7. User submits response
8. Validation result displayed
9. Conversation continues or completes

**Playwright Test:**

```typescript
test('full conversation flow', async ({ page }) => {
  await page.goto('/conversation/test-123');

  // Wait for connection
  await expect(page.locator('.connection-status')).toHaveText('Connected');

  // Send message
  await page.fill('message-input textarea', 'Hello AI');
  await page.click('message-input button[type="submit"]');

  // Wait for streaming response
  await expect(page.locator('content-stream')).toContainText('Hello');

  // Wait for widget
  const widget = page.locator('agent-widget-multiple-choice');
  await expect(widget).toBeVisible();

  // Interact with widget
  await widget.locator('label:has-text("Option A")').click();

  // Submit
  await page.click('button:has-text("Submit")');

  // Verify validation
  await expect(page.locator('.validation-message')).not.toBeVisible();
});
```

---

## Acceptance Criteria

- [ ] Content streams display progressively
- [ ] Streaming feels smooth (no jank)
- [ ] Tool calls execute end-to-end
- [ ] User messages persist and trigger AI
- [ ] Response submissions are validated
- [ ] Rate limiting protects system
- [ ] E2E test passes for full flow
- [ ] Latency < 100ms for message delivery

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Phase 2 Complete | Required | Control plane |
| AI Agent Service | Needed | LLM integration |
| Markdown Parser | To install | Marked.js or similar |
| DOMPurify | To install | HTML sanitization |

---

## Related Documents

- [Implementation Plan](./websocket-protocol-implementation-plan.md)
- [Phase 2: Control Plane](./phase-2-control-plane.md)
- [Testing Strategy](./testing-strategy.md)

---

_Document maintained by: Development Team_
_Last review: December 18, 2025_
