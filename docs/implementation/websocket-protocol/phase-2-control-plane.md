# Phase 2: Control Plane - Detailed Tasks

**Document Version:** 1.0.0
**Last Updated:** December 18, 2025
**Duration:** Weeks 4-6

---

## Objective

Enable conversation and widget lifecycle management with state synchronization.

---

## Deliverables

1. Conversation configuration and state management
2. Widget rendering infrastructure
3. Widget state and validation handling
4. Flow control and navigation
5. Audit telemetry pipeline (basic)

---

## Backend Tasks

### B2.1 Conversation Config Handler

**File:** `src/agent-host/application/websocket/handlers/control_handlers.py`

**Handler:** `ConversationConfigHandler`

**Responsibilities:**

- Receive `control.conversation.config` from domain
- Associate connection with conversation
- Send conversation metadata to client
- Initialize conversation state

**Payload Processing:**

- Validate `ConversationConfigPayload`
- Store config in connection context
- Broadcast to all conversation participants

---

### B2.2 Widget State Management

**File:** `src/agent-host/application/websocket/handlers/control_handlers.py`

**Handlers:**

- `WidgetStateHandler` - Handle state changes
- `WidgetValidationHandler` - Handle validation results

**State Transitions:**

- `active` → `readonly` → `disabled` → `hidden`
- Server controls state via `control.widget.state`
- Client can request state (limited)

**Persistence:**

- Store current widget states in Redis (optional)
- Restore on reconnection

---

### B2.3 Widget Validation Handler

**File:** `src/agent-host/application/websocket/handlers/control_handlers.py`

**Handler:** `WidgetValidationHandler`

**Flow:**

1. Client submits response
2. Domain validates response
3. Domain emits validation result event
4. Handler sends `control.widget.validation` to client

**Validation Payload:**

```python
class WidgetValidationPayload:
    widget_id: str
    valid: bool
    messages: list[ValidationMessage]  # field, message, severity
```

---

### B2.4 Flow Control Handlers

**File:** `src/agent-host/application/websocket/handlers/control_handlers.py`

**Handlers:**

- `FlowStartHandler` - Start a flow sequence
- `FlowPauseHandler` - Pause current flow
- `FlowResumeHandler` - Resume paused flow
- `FlowCancelHandler` - Cancel flow

**Flow State:**

- Store current flow state in connection
- Broadcast flow events to all participants
- Integrate with domain FlowAggregate

---

### B2.5 Navigation Handlers

**File:** `src/agent-host/application/websocket/handlers/control_handlers.py`

**Handler:** `NavigationHandler` (shared for next/previous/skip)

**Message Types:**

- `control.navigation.next`
- `control.navigation.previous`
- `control.navigation.skip`

**Processing:**

- Validate navigation is allowed (based on item state)
- Dispatch navigation command to domain
- Domain emits new item context event

---

### B2.6 Audit Telemetry Pipeline

**File:** `src/agent-host/application/websocket/handlers/data_handlers.py`

**Handler:** `AuditEventsHandler`

**Flow:**

1. Client collects audit events (keystrokes, focus, clicks)
2. Client sends `data.audit.events` in batches
3. Handler validates and persists events
4. Handler sends `data.audit.ack` acknowledgment

**Storage:**

- Store in dedicated audit collection/table
- Index by conversation_id, widget_id, timestamp
- Consider time-series database for scale

**Rate Limiting:**

- Max 100 events per batch
- Max 10 batches per minute

---

### B2.7 Domain Event → WebSocket Broadcast

**Files:**

- `src/agent-host/application/events/websocket/widget_rendered_handler.py`
- `src/agent-host/application/events/websocket/conversation_updated_handler.py`
- `src/agent-host/application/events/websocket/item_context_handler.py`

**Pattern:**

1. Domain emits event (e.g., `WidgetRenderedEvent`)
2. Event handler subscribes via `@handles(EventType)`
3. Handler maps domain event to protocol message
4. Handler calls `connection_manager.broadcast_to_conversation()`

**Events to Handle:**

- `ConversationConfiguredEvent` → `control.conversation.config`
- `WidgetRenderedEvent` → `data.widget.render`
- `ItemContextChangedEvent` → `control.item.context`
- `ValidationCompletedEvent` → `control.widget.validation`
- `FlowStateChangedEvent` → `control.flow.*`

---

### B2.8 Conversation State Persistence

**Approach:** Use MongoDB read model for conversation state

**State to Persist:**

- Active widgets and their states
- Current item context
- Flow state
- Last activity timestamp

**Restoration:**

- On reconnection, query read model
- Send state restoration messages to client
- Include `messages_replayed` count

---

## Frontend Tasks

### F2.1 WebComponent Base Class

**File:** `src/agent-host/ui/src/widgets/base/widget-base.ts`

**Class:** `WidgetBase<TConfig, TValue> extends HTMLElement`

**Lifecycle:**

```typescript
class WidgetBase extends HTMLElement {
  // WebComponent lifecycle
  connectedCallback(): void;
  disconnectedCallback(): void;
  attributeChangedCallback(name, oldVal, newVal): void;

  // Configuration
  configure(config: TConfig, layout?: WidgetLayout): void;

  // Value
  getValue(): TValue | null;
  setValue(value: TValue): void;

  // State
  setState(state: WidgetState): void;

  // Validation
  validate(): ValidationResult;
  showValidation(result: ValidationResult): void;
  clearValidation(): void;

  // Events
  protected emitChange(value: TValue): void;
  protected emitSubmit(value: TValue): void;

  // Rendering
  protected abstract render(): void;
  protected getStyles(): string;
}
```

**Shadow DOM:**

- All widgets use Shadow DOM for encapsulation
- Styles injected via `<style>` in shadow root
- Slots for custom content where applicable

---

### F2.2 Widget Registry and Factory

**File:** `src/agent-host/ui/src/widgets/base/widget-registry.ts`

**Registry Pattern:**

```typescript
const widgetRegistry = new Map<WidgetType, CustomElementConstructor>();

function registerWidget(type: WidgetType, ctor: CustomElementConstructor): void {
  widgetRegistry.set(type, ctor);
  customElements.define(`agent-widget-${type.replace('_', '-')}`, ctor);
}
```

**Factory:**

```typescript
function createWidget(type: WidgetType): WidgetBase | null {
  const ctor = widgetRegistry.get(type);
  if (!ctor) return null;
  return document.createElement(`agent-widget-${type.replace('_', '-')}`) as WidgetBase;
}
```

**Auto-Registration:**

- Each widget module calls `registerWidget()` on import
- Main entry imports all widgets to trigger registration

---

### F2.3 Widget Lifecycle Management

**File:** `src/agent-host/ui/src/widgets/base/widget-manager.ts`

**Class:** `WidgetManager`

**Responsibilities:**

- Listen for `data.widget.render` messages
- Create widget instances via factory
- Insert into DOM at correct location
- Track active widgets
- Handle widget removal

**Methods:**

```typescript
class WidgetManager {
  constructor(container: HTMLElement, messageBus: MessageBus);

  renderWidget(payload: WidgetRenderPayload): WidgetBase;
  removeWidget(widgetId: string): void;
  getWidget(widgetId: string): WidgetBase | null;
  getAllWidgets(): WidgetBase[];

  // State management
  updateWidgetState(widgetId: string, state: WidgetState): void;
  showValidation(widgetId: string, result: ValidationResult): void;
}
```

---

### F2.4 Control Message Handlers

**File:** `src/agent-host/ui/src/protocol/control-handler.ts`

**Subscriptions:**

```typescript
// Conversation
messageBus.subscribe('control.conversation.config', handleConversationConfig);
messageBus.subscribe('control.conversation.display', handleDisplay);
messageBus.subscribe('control.conversation.deadline', handleDeadline);

// Widget
messageBus.subscribe('control.widget.state', handleWidgetState);
messageBus.subscribe('control.widget.validation', handleValidation);
messageBus.subscribe('control.widget.focus', handleFocus);

// Item
messageBus.subscribe('control.item.context', handleItemContext);
messageBus.subscribe('control.item.timeout', handleTimeout);
```

**Handler Pattern:**

```typescript
function handleWidgetState(message: ProtocolMessage<WidgetStatePayload>) {
  const { widgetId, state } = message.payload;
  widgetManager.updateWidgetState(widgetId, state);
}
```

---

### F2.5 Conversation State Store

**File:** `src/agent-host/ui/src/state/conversation-state.ts`

**Approach:** Simple observable state object (no Redux)

```typescript
class ConversationState {
  private _config: ConversationConfigPayload | null = null;
  private _items: Map<string, ItemState> = new Map();
  private _widgets: Map<string, WidgetState> = new Map();

  // Getters
  get config(): ConversationConfigPayload | null;
  get currentItem(): ItemState | null;
  getWidget(id: string): WidgetState | null;

  // Updates (emit events)
  setConfig(config: ConversationConfigPayload): void;
  setItemContext(item: ItemContextPayload): void;
  setWidgetState(widgetId: string, state: WidgetState): void;

  // Event emitter
  on(event: string, handler: Function): () => void;
}
```

---

### F2.6 Widget Validation Display

**In WidgetBase:**

```typescript
showValidation(result: ValidationResult): void {
  if (!result.valid) {
    this.setAttribute('validation', 'error');
    this.renderValidationMessages(result.messages);
  } else {
    this.removeAttribute('validation');
    this.clearValidationMessages();
  }
}
```

**Styling:**

```scss
:host([validation="error"]) {
  border-color: $color-error;

  .validation-message {
    color: $color-error;
    font-size: 0.875em;
  }
}
```

---

### F2.7 Navigation Controls

**File:** `src/agent-host/ui/src/components/navigation-controls.ts`

**WebComponent:** `<navigation-controls>`

**Elements:**

- Previous button (if allowed)
- Next/Submit button
- Skip button (if allowed)
- Progress indicator

**State:**

- Listen for `control.item.context` to update enabled state
- Disable when submitting
- Show loading state during transitions

---

### F2.8 Audit Event Collection

**File:** `src/agent-host/ui/src/audit/audit-collector.ts`

**Class:** `AuditCollector`

**Events to Capture:**

- `focus_change` - Element focus changes
- `keystroke` - Key presses (without content for privacy)
- `mouse_click` - Click events with position
- `paste` / `copy` - Clipboard events
- `visibility_change` - Tab visibility
- `scroll` - Scroll events (throttled)

**Batching:**

- Collect events in buffer
- Send batch every N seconds or when buffer full
- Flush on page unload

**Configuration:**

- Respect `AuditConfig` from server
- Enable/disable event types
- Adjust sampling rate

---

## Testing Tasks

### T2.1 Widget Lifecycle Unit Tests

**File:** `tests/unit/widgets/widget-base.test.ts`

**Test Cases:**

- `test_configure_sets_config`
- `test_getValue_returns_current_value`
- `test_setState_updates_attribute`
- `test_validate_returns_result`
- `test_showValidation_displays_errors`
- `test_emitChange_dispatches_event`

---

### T2.2 State Management Unit Tests

**File:** `tests/unit/state/conversation-state.test.ts`

**Test Cases:**

- `test_setConfig_stores_config`
- `test_setConfig_emits_event`
- `test_setWidgetState_updates_state`
- `test_getWidget_returns_state`
- `test_state_persists_across_reconnect`

---

### T2.3 Integration: Conversation Flow

**File:** `tests/integration/test_conversation_flow.py`

**Test Cases:**

- `test_conversation_config_sent_on_connect`
- `test_item_context_changes_on_navigation`
- `test_flow_start_pause_resume`
- `test_conversation_complete_closes_connection`

---

### T2.4 Integration: Widget Render/Validate

**File:** `tests/integration/test_widget_lifecycle.py`

**Test Cases:**

- `test_widget_render_message_received`
- `test_response_submit_triggers_validation`
- `test_validation_result_sent_to_client`
- `test_widget_state_change_updates_client`

---

## Acceptance Criteria

- [ ] Conversation config received within 1s of connect
- [ ] Widgets render within 100ms of message receipt
- [ ] State changes reflect immediately in UI
- [ ] Validation errors display with clear messaging
- [ ] Navigation works between items
- [ ] Audit events batch and send successfully
- [ ] All tests pass with >80% coverage

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Phase 1 Complete | Required | WebSocket infrastructure |
| Domain ConversationAggregate | ✅ Exists | Integrate events |
| Domain FlowAggregate | ✅ Exists | Flow control |
| MongoDB Read Model | ✅ Exists | State persistence |

---

## Related Documents

- [Implementation Plan](./websocket-protocol-implementation-plan.md)
- [Phase 1: Core Infrastructure](./phase-1-core-infrastructure.md)
- [Frontend Implementation Guide](./frontend-implementation-guide.md)

---

_Document maintained by: Development Team_
_Last review: December 18, 2025_
