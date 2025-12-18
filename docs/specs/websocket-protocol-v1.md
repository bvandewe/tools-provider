# Agent Host WebSocket Protocol Specification

**Version:** 1.0.0
**Status:** `DRAFT`
**Date:** December 18, 2025
**Authors:** Architecture Team

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Transport Layer](#2-transport-layer)
3. [Message Envelope](#3-message-envelope)
4. [Control Plane](#4-control-plane)
   - 4.2.1 Conversation-Level Controls
   - 4.2.1.1 Configuration Dependencies & Constraints
   - 4.2.1.2 Audit Configuration
   - 4.2.2 Item-Level Controls
   - 4.2.3 Widget-Level Controls
5. [Data Plane](#5-data-plane)
6. [Widget System](#6-widget-system)
   - 6.1 Widget Rendering
   - 6.2 Layout Object
   - 6.3 Constraints Object
   - 6.4 Widget Types (19 types)
   - 6.5 Widget Configuration Schemas
     - 6.3.1 Multiple Choice
     - 6.3.2 Free Text
     - 6.3.3 Code Editor
     - 6.3.4 Slider
     - 6.3.5 Drag & Drop (Category, Sequence, Graphical)
     - 6.3.6 Graph Topology Builder
     - 6.3.7 Matrix Choice
     - 6.3.8 Document Viewer
     - 6.3.9 Hotspot
     - 6.3.10 Drawing
     - 6.3.11 File Upload
     - 6.3.12 Rating
     - 6.3.13 Date Picker
     - 6.3.14 Dropdown
     - 6.3.15 Image
     - 6.3.16 Video
     - 6.3.17 Sticky Note
   - 6.4 Widget Lifecycle
   - 6.5 Widget Completion Behavior
7. [2D Canvas System](#7-2d-canvas-system)
   - 7.1 Canvas Architecture
   - 7.2 Canvas Configuration
   - 7.3 Viewport Control
   - 7.4 Canvas Mode Control
   - 7.5 Connections
   - 7.6 Groups and Containers
   - 7.7 Layers
   - 7.8 Selection
   - 7.9 Annotations
   - 7.10 Presentation Mode
   - 7.11 Collaboration Features
   - 7.12 Grid and Alignment
   - 7.13 State Management
   - 7.14 Conditional Widget Visibility
   - 7.15 Bookmarks and Navigation Points
   - 7.16 Drawing Layer
   - 7.17 Smart Guides and Snapping
   - 7.18 Copy, Paste, and Duplicate
   - 7.19 Search and Filter
   - 7.20 Comments and Threads
   - 7.21 History and Timeline
   - 7.22 Widget Templates and Cloning
   - 7.23 Canvas Export and Import
8. [Connection Lifecycle](#8-connection-lifecycle)
   - 8.1 Connection Establishment
   - 8.2 Keepalive
   - 8.3 Reconnection
   - 8.4 Graceful Disconnect
   - 8.5 WebSocket Close Codes
9. [Error Handling](#9-error-handling)
10. [Timing & Deadlines](#10-timing--deadlines)
11. [Message Reference](#11-message-reference)
12. [IFRAME Widget](#12-iframe-widget)
13. [Implementation Notes](#13-implementation-notes)

---

## 1. Executive Summary

This specification defines the **bidirectional WebSocket protocol** for communication between the Agent Host frontend and backend. The protocol supersedes the previous dual-transport architecture (SSE + WebSocket) with a unified WebSocket-only approach.

### 1.1 Design Principles

| Principle | Description |
|-----------|-------------|
| **WebSocket-Only** | Single transport for all conversation flows (reactive and proactive) |
| **CloudEvent-Aligned** | Message envelope inspired by CloudEvents specification |
| **Atomic Commands** | Control signals are discrete, independent commands |
| **Bidirectional Control** | Both client and server can initiate control signals |
| **Generic Payloads** | Widget responses use a generic format for extensibility |
| **Versioned Protocol** | Built-in versioning for future-proof evolution |
| **Dual Display Modes** | Support for 1D flow (traditional chat) and 2D canvas layouts |
| **Widget State Machine** | Widgets can transition between active, readonly, disabled, hidden states |

### 1.2 Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Transport | WebSocket-only | Simplifies architecture, enables real-time bidirectional control |
| Authentication | Session cookie OR JWT | Maintains existing security model |
| Message Acks | Not required | TCP guarantees delivery; WebSocket is connection-oriented |
| Capability Negotiation | Deferred | Frontend/backend are tightly coupled; add if needed later |
| Control Signals | Atomic commands | Easier to extend; UI event bus handles reconciliation |
| Widget Responses | Generic format | Consistent handling across widget types |
| Widget After Completion | Readonly (not text) | Better UX; preserves widget features (e.g., code highlighting) |
| Display Modes | Flow (1D) + Canvas (2D) | Enables traditional chat and spatial learning experiences |
| Widget Reactivation | Supported | Backend can reactivate readonly widgets for revisiting content |

---

## 2. Transport Layer

### 2.1 Connection Endpoint

```
WebSocket: wss://{host}/api/chat/ws
```

### 2.2 Authentication

Authentication is handled at the HTTP layer during the WebSocket upgrade handshake:

| Method | Mechanism | Header/Parameter |
|--------|-----------|------------------|
| **Session Cookie** | HTTP-only cookie from OAuth2 BFF flow | `Cookie: session=...` |
| **JWT Bearer Token** | Query parameter for programmatic access | `?token=eyJ...` |

The server validates credentials during the upgrade request. If invalid, the connection is rejected with HTTP 401/403.

### 2.3 Connection Parameters

Query parameters accepted during connection:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `conversation_id` | `string` | No | Resume existing conversation |
| `definition_id` | `string` | No | Start new conversation with agent definition |
| `token` | `string` | No | JWT access token (alternative to cookie) |

**Examples:**

```
# New conversation with agent definition
wss://host/api/chat/ws?definition_id=tutor-python

# Resume existing conversation
wss://host/api/chat/ws?conversation_id=conv_abc123

# With JWT authentication
wss://host/api/chat/ws?definition_id=tutor-python&token=eyJ...
```

---

## 3. Message Envelope

All messages use a consistent envelope structure inspired by the CloudEvents specification.

### 3.1 Envelope Schema

```json
{
  "id": "msg_unique_id",
  "type": "plane.category.action",
  "version": "1.0",
  "timestamp": "2025-12-18T10:30:00.000Z",
  "source": "client|server",
  "conversationId": "conv_abc123",
  "payload": { ... }
}
```

### 3.2 Envelope Attributes

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | `string` | Yes | Unique message identifier (UUID or nanoid) |
| `type` | `string` | Yes | Hierarchical message type (see §3.3) |
| `version` | `string` | Yes | Protocol version (semver format: `"1.0"`) |
| `timestamp` | `string` | Yes | ISO 8601 timestamp with milliseconds |
| `source` | `string` | Yes | Origin: `"client"` or `"server"` |
| `conversationId` | `string` | No | Conversation context (null for connection-level messages) |
| `payload` | `object` | Yes | Message-specific data |

### 3.3 Message Type Hierarchy

Message types follow a hierarchical naming convention:

```
{plane}.{category}.{action}
```

| Plane | Description | Direction |
|-------|-------------|-----------|
| `control` | UI state, settings, lifecycle commands | Bidirectional |
| `data` | Content, widgets, user responses | Bidirectional |
| `system` | Connection lifecycle, errors | Bidirectional |

**Examples:**

- `system.connection.established`
- `control.conversation.config`
- `control.item.progress`
- `control.timer.start`
- `data.content.chunk`
- `data.widget.render`
- `data.response.submit`

---

## 4. Control Plane

Control plane messages manage UI state, conversation settings, and user interaction controls.

### 4.1 Control Levels

Control signals are scoped to specific levels:

| Level | Scope | Examples |
|-------|-------|----------|
| **Connection** | WebSocket session | Pause, resume, disconnect |
| **Conversation** | Entire conversation | Display mode, navigation, deadline |
| **Item** | Current template item | Chat input, timer, progress |
| **Widget** | Specific widget instance | Focus, validation, readonly |

### 4.2 Server → Client Control Messages

#### 4.2.1 Conversation-Level Controls

**`control.conversation.config`**

Sent at conversation start to configure overall behavior.

```json
{
  "type": "control.conversation.config",
  "payload": {
    "templateId": "assessment-python-101",
    "templateName": "Python Fundamentals Assessment",
    "totalItems": 10,
    "displayMode": "append",
    "showConversationHistory": true,
    "allowBackwardNavigation": true,
    "allowConcurrentItemWidgets": false,
    "allowSkip": false,
    "enableChatInputInitially": false,
    "displayProgressIndicator": true,
    "displayFinalScoreReport": true,
    "continueAfterCompletion": false,
    "audit": {
      "enabled": true,
      "captureKeystrokes": true,
      "captureMouseClicks": true,
      "captureMousePosition": false,
      "captureFocusChanges": true,
      "captureClipboard": false,
      "batchIntervalMs": 1000,
      "excludeWidgetTypes": []
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `displayMode` | `"append" \| "replace"` | Whether items stack or replace previous |
| `showConversationHistory` | `boolean` | Show list of previous conversations for navigation |
| `allowBackwardNavigation` | `boolean` | User can go to previous items within current conversation |
| `allowConcurrentItemWidgets` | `boolean` | Widgets from multiple items can be active simultaneously |
| `allowSkip` | `boolean` | User can skip items |
| `enableChatInputInitially` | `boolean` | Chat input enabled at start |
| `displayProgressIndicator` | `boolean` | Show progress bar |
| `displayFinalScoreReport` | `boolean` | Show score at end |
| `continueAfterCompletion` | `boolean` | Allow chat after template completes |
| `audit` | `object?` | Audit/telemetry configuration (see §4.2.1.2) |

#### 4.2.1.1 Configuration Dependencies & Constraints

Certain configuration options have inter-dependencies that must be respected for coherent behavior.

**Required Dependencies:**

| Option | Requires | Reason |
|--------|----------|--------|
| `allowConcurrentItemWidgets: true` | `allowBackwardNavigation: true` | Must navigate between items to interact with multiple |
| `allowConcurrentItemWidgets: true` | `displayMode: "append"` OR `mode: "canvas"` | Items must be visible simultaneously |
| `allowBackwardNavigation: true` | `widgetCompletionBehavior` ≠ `"hidden"` | Hidden widgets cannot be revisited |

**Conflicting Combinations:**

| Combination | Conflict | Resolution |
|-------------|----------|------------|
| `displayMode: "replace"` + `allowConcurrentItemWidgets: true` | Items replace each other, cannot coexist | Server rejects; log warning |
| `widgetCompletionBehavior: "hidden"` + `allowBackwardNavigation: true` | Cannot revisit hidden widgets | Treat as `"readonly"` when navigating back |
| `timeLimitSeconds` (item) > remaining `conversationDeadline` | Item timer exceeds conversation time | Item timer capped at remaining deadline |
| `preventSkipAhead: true` (video) + `allowSkip: true` (item) | Widget blocks skip, item allows it | Widget restriction takes precedence while widget active |

**Timer Behavior with Concurrent Items:**

When `allowConcurrentItemWidgets: true`:

| Timer Mode | Behavior |
|------------|----------|
| `parallel` (default) | All visible item timers run simultaneously |
| `focused` | Only the focused/selected item's timer runs; others pause |
| `aggregate` | Single timer for all items combined |

Specify via `itemTimerMode` field:

```json
{
  "type": "control.conversation.config",
  "payload": {
    "allowConcurrentItemWidgets": true,
    "itemTimerMode": "focused"
  }
}
```

**Canvas Mode Interaction:**

When `mode: "canvas"` is set in `control.conversation.display`:

| Conversation Config | Canvas Behavior |
|---------------------|-----------------|
| `displayMode: "append"` | Widgets accumulate on canvas |
| `displayMode: "replace"` | Previous widgets hidden (but remain in DOM for navigation) |
| `allowConcurrentItemWidgets: true` | All visible widgets accept input |
| `allowConcurrentItemWidgets: false` | Only current item's widgets are interactive; others readonly |

**Validation Rules:**

The server SHOULD validate configuration coherence and:

1. **Warn** in logs for soft conflicts (e.g., unusual but valid combinations)
2. **Reject** with `system.error` for hard conflicts (e.g., impossible combinations)
3. **Auto-correct** where safe (e.g., cap item timer to deadline)

```json
{
  "type": "system.error",
  "payload": {
    "category": "validation",
    "code": "CONFIG_CONFLICT",
    "message": "allowConcurrentItemWidgets requires displayMode 'append' or canvas mode",
    "details": {
      "conflictingFields": ["allowConcurrentItemWidgets", "displayMode"]
    }
  }
}
```

#### 4.2.1.2 Audit Configuration

The `audit` object enables detailed interaction tracking for proctoring, analytics, and compliance purposes.

**Audit Configuration Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `boolean` | `false` | Master switch for audit logging |
| `captureKeystrokes` | `boolean` | `false` | Record keystrokes in widgets/chat |
| `captureMouseClicks` | `boolean` | `false` | Record mouse click events with position |
| `captureMousePosition` | `boolean` | `false` | Record mouse movement (high volume) |
| `captureFocusChanges` | `boolean` | `true` | Record focus transitions between elements |
| `captureClipboard` | `boolean` | `false` | Record paste events (privacy-sensitive) |
| `batchIntervalMs` | `number` | `1000` | Batch events before sending (reduce traffic) |
| `excludeWidgetTypes` | `string[]` | `[]` | Widget types to exclude from auditing |

**Privacy & Compliance Notes:**

- When `audit.enabled: true`, frontend SHOULD display a visible indicator to the user
- `captureKeystrokes` captures key codes, not rendered characters (respects IME)
- `captureClipboard` only captures paste events, not clipboard content by default
- All audit events include `userId` for accountability

---

**`control.audit.config`** (Server → Client)

Update audit configuration mid-conversation (e.g., enable during specific items).

```json
{
  "type": "control.audit.config",
  "payload": {
    "enabled": true,
    "captureKeystrokes": true,
    "reason": "High-stakes assessment section"
  }
}
```

---

**`data.audit.events`** (Client → Server)

Batched audit events from frontend.

```json
{
  "type": "data.audit.events",
  "payload": {
    "userId": "user_123",
    "sessionId": "sess_abc",
    "batchId": "batch_001",
    "events": [
      {
        "eventId": "evt_001",
        "eventType": "focus_change",
        "timestamp": "2025-12-18T10:30:00.123Z",
        "context": {
          "fromElement": {"type": "widget", "widgetId": "widget_mc_1", "itemId": "item_1"},
          "toElement": {"type": "widget", "widgetId": "widget_code_1", "itemId": "item_2"}
        }
      },
      {
        "eventId": "evt_002",
        "eventType": "keystroke",
        "timestamp": "2025-12-18T10:30:01.456Z",
        "context": {
          "element": {"type": "widget", "widgetId": "widget_code_1", "itemId": "item_2"},
          "key": "KeyA",
          "modifiers": ["shift"],
          "inputLength": 45
        }
      },
      {
        "eventId": "evt_003",
        "eventType": "mouse_click",
        "timestamp": "2025-12-18T10:30:02.789Z",
        "context": {
          "element": {"type": "canvas", "widgetId": null, "itemId": null},
          "position": {"x": 450, "y": 320},
          "button": "left",
          "clickType": "single"
        }
      },
      {
        "eventId": "evt_004",
        "eventType": "paste",
        "timestamp": "2025-12-18T10:30:03.012Z",
        "context": {
          "element": {"type": "widget", "widgetId": "widget_code_1", "itemId": "item_2"},
          "contentLength": 156,
          "contentType": "text/plain"
        }
      }
    ]
  }
}
```

**Audit Event Types:**

| Event Type | Description | Context Fields |
|------------|-------------|----------------|
| `focus_change` | Focus moved between elements | `fromElement`, `toElement` |
| `keystroke` | Key pressed in input | `element`, `key`, `modifiers`, `inputLength` |
| `mouse_click` | Mouse click event | `element`, `position`, `button`, `clickType` |
| `mouse_move` | Mouse movement (if enabled) | `element`, `position` |
| `paste` | Content pasted | `element`, `contentLength`, `contentType` |
| `copy` | Content copied | `element`, `contentLength` |
| `scroll` | Scroll event | `element`, `scrollTop`, `scrollLeft` |
| `visibility_change` | Tab/window visibility | `visible`, `hiddenDuration` |
| `window_blur` | Window lost focus | `blurredAt` |
| `window_focus` | Window regained focus | `focusedAt`, `blurDuration` |

**Element Context:**

```json
{
  "element": {
    "type": "widget | chat | canvas | background | toolbar | navigation",
    "widgetId": "widget_mc_1",
    "widgetType": "multiple_choice",
    "itemId": "item_1",
    "region": {"x": 100, "y": 200, "width": 400, "height": 300}
  }
}
```

| Element Type | Description |
|--------------|-------------|
| `widget` | Interaction with a specific widget |
| `chat` | Chat input area |
| `canvas` | Canvas background (not on widget) |
| `background` | Page background outside canvas/flow |
| `toolbar` | Toolbar/menu interactions |
| `navigation` | Navigation controls (next/prev/skip) |

**Keystroke Context:**

| Field | Type | Description |
|-------|------|-------------|
| `key` | `string` | Key code (e.g., `KeyA`, `Enter`, `Backspace`) |
| `modifiers` | `string[]` | Active modifiers: `shift`, `ctrl`, `alt`, `meta` |
| `inputLength` | `number` | Current length of input field (not content) |
| `cursorPosition` | `number?` | Cursor position in input |

**Mouse Click Context:**

| Field | Type | Description |
|-------|------|-------------|
| `position` | `{x, y}` | Click position (canvas coords or viewport) |
| `button` | `"left" \| "right" \| "middle"` | Mouse button |
| `clickType` | `"single" \| "double" \| "triple"` | Click type |

**Focus Change Context:**

| Field | Type | Description |
|-------|------|-------------|
| `fromElement` | `object?` | Previous focused element (null if from outside) |
| `toElement` | `object?` | New focused element (null if to outside) |
| `focusDuration` | `number?` | Time spent on previous element (ms) |

---

**`data.audit.ack`** (Server → Client)

Acknowledge receipt of audit batch.

```json
{
  "type": "data.audit.ack",
  "payload": {
    "batchId": "batch_001",
    "receivedCount": 4,
    "status": "stored"
  }
}
```

---

**`control.audit.flush`** (Server → Client)

Request immediate flush of pending audit events (e.g., before item transition).

```json
{
  "type": "control.audit.flush",
  "payload": {
    "reason": "item_transition"
  }
}
```

---

**`data.audit.flushed`** (Client → Server)

Confirm flush completed.

```json
{
  "type": "data.audit.flushed",
  "payload": {
    "pendingBatches": 0,
    "totalEventsFlushed": 47
  }
}
```

---

**`control.conversation.display`**

Configures the display mode for the conversation. This determines whether content appears in traditional 1D chat flow or on a 2D spatial canvas.

```json
{
  "type": "control.conversation.display",
  "payload": {
    "mode": "canvas",
    "flowConfig": null,
    "canvasConfig": {
      "width": 3000,
      "height": 2000,
      "background": "#f5f5f5",
      "gridEnabled": true,
      "gridSize": 20,
      "snapToGrid": true,
      "minZoom": 0.25,
      "maxZoom": 4.0,
      "initialZoom": 1.0,
      "initialViewport": { "x": 0, "y": 0 }
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `mode` | `"flow" \| "canvas"` | Display mode |
| `flowConfig` | `object?` | Configuration for flow mode (see below) |
| `canvasConfig` | `object?` | Configuration for canvas mode (see below) |

**Flow Config (1D Mode):**

```json
{
  "flowConfig": {
    "behavior": "append",
    "maxVisibleMessages": null,
    "autoScroll": true
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `behavior` | `"append" \| "replace"` | Whether items stack or replace |
| `maxVisibleMessages` | `number?` | Limit visible messages (null = unlimited) |
| `autoScroll` | `boolean` | Auto-scroll to new content |

**Canvas Config (2D Mode):**

| Field | Type | Description |
|-------|------|-------------|
| `width` | `number` | Canvas width in pixels |
| `height` | `number` | Canvas height in pixels |
| `background` | `string` | Background color or image URL |
| `gridEnabled` | `boolean` | Show alignment grid |
| `gridSize` | `number` | Grid cell size in pixels |
| `snapToGrid` | `boolean` | Snap widgets to grid |
| `minZoom` | `number` | Minimum zoom level (0.25 = 25%) |
| `maxZoom` | `number` | Maximum zoom level (4.0 = 400%) |
| `initialZoom` | `number` | Starting zoom level |
| `initialViewport` | `{x, y}` | Starting viewport position |

---

**`control.conversation.deadline`**

Sets or updates the conversation-level deadline.

```json
{
  "type": "control.conversation.deadline",
  "payload": {
    "deadline": "2025-12-18T11:00:00.000Z",
    "showWarning": true,
    "warningThresholdSeconds": 300
  }
}
```

---

**`control.conversation.pause`** / **`control.conversation.resume`**

Server-initiated pause/resume (e.g., proctor intervention).

```json
{
  "type": "control.conversation.pause",
  "payload": {
    "reason": "Proctor review",
    "pausedAt": "2025-12-18T10:35:00.000Z"
  }
}
```

---

#### 4.2.2 Item-Level Controls

**`control.item.context`**

Sent when advancing to a new template item.

```json
{
  "type": "control.item.context",
  "payload": {
    "itemId": "item_q3",
    "itemIndex": 2,
    "totalItems": 10,
    "itemTitle": "Question 3: List Comprehensions",
    "enableChatInput": false,
    "timeLimitSeconds": 120,
    "showRemainingTime": true,
    "widgetCompletionBehavior": "readonly",
    "conversationDeadline": "2025-12-18T11:00:00.000Z"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `itemId` | `string` | Unique item identifier |
| `itemIndex` | `number` | 0-based index in sequence |
| `totalItems` | `number` | Total items in template |
| `itemTitle` | `string?` | Display title (if enabled) |
| `enableChatInput` | `boolean` | Whether chat input is enabled for this item |
| `timeLimitSeconds` | `number?` | Time limit for this item (null = no limit) |
| `showRemainingTime` | `boolean` | Display countdown timer |
| `widgetCompletionBehavior` | `"readonly" \| "text" \| "hidden"` | How completed widgets appear |
| `conversationDeadline` | `string?` | Current deadline (for sync) |

---

**`control.item.score`**

Optional score feedback after item completion.

```json
{
  "type": "control.item.score",
  "payload": {
    "itemId": "item_q3",
    "score": 1.0,
    "maxScore": 1.0,
    "feedback": "Correct! Great use of list comprehension.",
    "correctAnswer": "B"
  }
}
```

---

**`control.item.timeout`**

Sent when item time limit expires.

```json
{
  "type": "control.item.timeout",
  "payload": {
    "itemId": "item_q3",
    "action": "auto_advance"
  }
}
```

| `action` Value | Behavior |
|----------------|----------|
| `auto_advance` | Automatically move to next item |
| `lock` | Lock input but stay on item |
| `warn` | Show warning, allow continuation |

---

#### 4.2.3 Widget-Level Controls

**`control.widget.state`**

Controls the interactive state of a widget. Replaces the simpler `readonly` control with full state machine support. This enables widget reactivation for revisiting content.

```json
{
  "type": "control.widget.state",
  "payload": {
    "widgetId": "widget_mc_1",
    "state": "readonly",
    "clearValue": false,
    "reason": "item_completed"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `widgetId` | `string` | Target widget identifier |
| `state` | `string` | New state (see state machine below) |
| `clearValue` | `boolean` | Reset widget value when reactivating |
| `reason` | `string?` | Optional reason for state change |

**Widget States:**

| State | Description | User Can Interact |
|-------|-------------|-------------------|
| `active` | Normal interactive state | ✅ Yes |
| `readonly` | Visible but not editable (preserves formatting) | ❌ No |
| `disabled` | Visible but grayed out | ❌ No |
| `hidden` | Not visible | ❌ No |

**State Transitions:**

```
                    clearValue=true
         ┌──────────────────────────────────┐
         │                                  │
         ▼                                  │
    ┌─────────┐                        ┌─────────┐
    │ ACTIVE  │ ──── response ────────►│READONLY │
    └─────────┘                        └─────────┘
         ▲                                  │
         │         reactivate               │
         └──────────────────────────────────┘

    Any state can transition to:
    - hidden (widget disappears)
    - disabled (widget grayed out)
    - active (widget reactivated)
```

**Use Case - Revisiting Content:**

```json
// Instructor says "let's revisit question 3"
{
  "type": "control.widget.state",
  "payload": {
    "widgetId": "widget_q3_mc",
    "state": "active",
    "clearValue": false,
    "reason": "instructor_revisit"
  }
}
```

---

**`control.widget.focus`**

Request focus on a specific widget.

```json
{
  "type": "control.widget.focus",
  "payload": {
    "widgetId": "widget_mc_1",
    "highlight": true,
    "scrollIntoView": true
  }
}
```

---

**`control.widget.validation`**

Display validation error on a widget.

```json
{
  "type": "control.widget.validation",
  "payload": {
    "widgetId": "widget_code_1",
    "valid": false,
    "message": "Your code has a syntax error on line 3",
    "details": {
      "line": 3,
      "column": 15,
      "errorType": "SyntaxError"
    }
  }
}
```

---

**`control.widget.layout`** (Canvas Mode)

Update a widget's position, size, or constraints on the canvas. Used when server needs to reposition widgets.

```json
{
  "type": "control.widget.layout",
  "payload": {
    "widgetId": "widget_mc_1",
    "layout": {
      "position": { "x": 200, "y": 150 },
      "dimensions": { "width": 400, "height": 300 },
      "zIndex": 10
    },
    "animate": true,
    "animationDuration": 300
  }
}
```

---

### 4.3 Client → Server Control Messages

#### 4.3.1 Flow Control

**`control.flow.start`**

Start the conversation/template flow (proactive agent).

```json
{
  "type": "control.flow.start",
  "payload": {}
}
```

---

**`control.flow.pause`** / **`control.flow.resume`**

User-initiated pause/resume.

```json
{
  "type": "control.flow.pause",
  "payload": {
    "reason": "user_requested"
  }
}
```

---

**`control.flow.cancel`**

Cancel the current operation (e.g., stop LLM generation).

```json
{
  "type": "control.flow.cancel",
  "payload": {
    "requestId": "req_abc123"
  }
}
```

---

#### 4.3.2 Navigation Control

**`control.navigation.next`** / **`control.navigation.previous`**

Navigate between items (when allowed).

```json
{
  "type": "control.navigation.previous",
  "payload": {
    "currentItemId": "item_q3"
  }
}
```

---

**`control.navigation.skip`**

Skip current item (when allowed).

```json
{
  "type": "control.navigation.skip",
  "payload": {
    "itemId": "item_q3",
    "reason": "user_skip"
  }
}
```

---

#### 4.3.3 Widget Layout Updates (Canvas Mode)

**`control.widget.moved`** (Client → Server)

Notify server when user moves a widget on canvas.

```json
{
  "type": "control.widget.moved",
  "payload": {
    "widgetId": "widget_mc_1",
    "position": { "x": 250, "y": 180 }
  }
}
```

---

**`control.widget.resized`** (Client → Server)

Notify server when user resizes a widget on canvas.

```json
{
  "type": "control.widget.resized",
  "payload": {
    "widgetId": "widget_mc_1",
    "dimensions": { "width": 450, "height": 320 }
  }
}
```

---

**`control.widget.dismissed`** (Client → Server)

Notify server when user dismisses a widget.

```json
{
  "type": "control.widget.dismissed",
  "payload": {
    "widgetId": "widget_mc_1",
    "action": "hide"
  }
}
```

---

### 4.4 Unknown Control Signal Handling

When either party receives an unknown control signal:

| Party | Behavior |
|-------|----------|
| **Frontend** | Log to console with `[PROTOCOL]` prefix; ignore gracefully |
| **Backend** | Log with warning level; ignore gracefully |

This ensures forward compatibility as new control signals are added.

---

## 5. Data Plane

Data plane messages handle content delivery and user responses.

### 5.1 Server → Client Data Messages

#### 5.1.1 Content Streaming

**`data.content.chunk`**

Streaming text content from LLM.

```json
{
  "type": "data.content.chunk",
  "payload": {
    "content": "Let me explain list comprehensions...",
    "messageId": "msg_assistant_1",
    "final": false
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `content` | `string` | Text chunk to append |
| `messageId` | `string` | Identifier for this message |
| `final` | `boolean` | If true, this is the last chunk |

---

**`data.content.complete`**

Marks a content message as complete.

```json
{
  "type": "data.content.complete",
  "payload": {
    "messageId": "msg_assistant_1",
    "role": "assistant",
    "fullContent": "Let me explain list comprehensions..."
  }
}
```

---

#### 5.1.2 Tool Execution

**`data.tool.call`**

Notification that a tool is being called.

```json
{
  "type": "data.tool.call",
  "payload": {
    "callId": "call_xyz789",
    "toolName": "execute_code",
    "arguments": {
      "code": "print('Hello')",
      "language": "python"
    }
  }
}
```

---

**`data.tool.result`**

Result of tool execution.

```json
{
  "type": "data.tool.result",
  "payload": {
    "callId": "call_xyz789",
    "toolName": "execute_code",
    "success": true,
    "result": "Hello\n",
    "executionTimeMs": 234
  }
}
```

---

### 5.2 Client → Server Data Messages

#### 5.2.1 User Messages

**`data.message.send`**

User sends a free-text message.

```json
{
  "type": "data.message.send",
  "payload": {
    "content": "Can you explain that again?",
    "attachments": []
  }
}
```

---

#### 5.2.2 Widget Responses

**`data.response.submit`**

Generic widget response submission.

```json
{
  "type": "data.response.submit",
  "payload": {
    "itemId": "item_q3",
    "widgetId": "widget_mc_1",
    "widgetType": "multiple_choice",
    "value": "B",
    "metadata": {
      "selectionIndex": 1,
      "timeSpentMs": 15234
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `itemId` | `string` | Parent item identifier |
| `widgetId` | `string` | Widget instance identifier |
| `widgetType` | `string` | Widget type for context |
| `value` | `any` | The response value (generic) |
| `metadata` | `object?` | Optional metadata (timing, selection details) |

**Value Examples by Widget Type:**

| Widget Type | `value` Example |
|-------------|-----------------|
| `multiple_choice` (single) | `"B"` |
| `multiple_choice` (multi) | `["A", "C"]` |
| `free_text` | `"My answer text..."` |
| `code_editor` | `"def hello():\n    print('hi')"` |
| `slider` | `75` |
| `drag_drop` | `{"zone1": ["item1"], "zone2": ["item2", "item3"]}` |

---

## 6. Widget System

### 6.1 Widget Rendering

**`data.widget.render`**

Server requests rendering of a widget. In canvas mode, includes layout information for positioning.

```json
{
  "type": "data.widget.render",
  "payload": {
    "itemId": "item_q3",
    "widgetId": "widget_mc_1",
    "widgetType": "multiple_choice",
    "stem": "Which syntax correctly creates a list comprehension?",
    "config": {
      "options": [
        "A) [x for x in range(10)]",
        "B) [for x in range(10): x]",
        "C) (x for x in range(10))",
        "D) {x for x in range(10)}"
      ],
      "allowMultiple": false,
      "shuffleOptions": true
    },
    "required": true,
    "skippable": false,
    "initialValue": null,
    "showUserResponse": true,
    "layout": {
      "mode": "flow",
      "position": null,
      "dimensions": null,
      "anchor": "top-left",
      "zIndex": null
    },
    "constraints": {
      "moveable": false,
      "resizable": false,
      "dismissable": false,
      "dismissAction": "hide"
    }
  }
}
```

### 6.2 Layout Object

The `layout` object controls how a widget is positioned and sized.

```json
{
  "layout": {
    "mode": "canvas",
    "position": { "x": 100, "y": 200 },
    "dimensions": {
      "width": 400,
      "height": 300,
      "minWidth": 200,
      "minHeight": 100,
      "maxWidth": 800,
      "maxHeight": 600
    },
    "anchor": "top-left",
    "zIndex": 10
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `mode` | `"flow" \| "canvas"` | Display mode (inherited from conversation if not set) |
| `position` | `{x, y}?` | Position in canvas mode (pixels from top-left) |
| `dimensions` | `object?` | Size constraints (see below) |
| `anchor` | `string` | Anchor point for positioning |
| `zIndex` | `number?` | Stacking order (higher = on top) |

**Dimensions Object:**

| Field | Type | Description |
|-------|------|-------------|
| `width` | `number?` | Current/initial width in pixels |
| `height` | `number?` | Current/initial height in pixels |
| `minWidth` | `number?` | Minimum allowed width |
| `minHeight` | `number?` | Minimum allowed height |
| `maxWidth` | `number?` | Maximum allowed width |
| `maxHeight` | `number?` | Maximum allowed height |

**Anchor Values:**

| Anchor | Description |
|--------|-------------|
| `top-left` | Position is top-left corner (default) |
| `top-center` | Position is top-center |
| `top-right` | Position is top-right corner |
| `center-left` | Position is center-left |
| `center` | Position is center of widget |
| `center-right` | Position is center-right |
| `bottom-left` | Position is bottom-left corner |
| `bottom-center` | Position is bottom-center |
| `bottom-right` | Position is bottom-right corner |

### 6.3 Constraints Object

The `constraints` object controls what users can do with a widget.

```json
{
  "constraints": {
    "moveable": true,
    "resizable": true,
    "dismissable": true,
    "dismissAction": "minimize",
    "selectable": true,
    "connectable": true
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `moveable` | `boolean` | `false` | User can drag widget |
| `resizable` | `boolean` | `false` | User can resize widget |
| `dismissable` | `boolean` | `false` | User can dismiss/close widget |
| `dismissAction` | `string` | `"hide"` | What happens on dismiss |
| `selectable` | `boolean` | `true` | Widget can be selected |
| `connectable` | `boolean` | `false` | Widget can have connections (see §7.3) |

**Dismiss Actions:**

| Action | Description |
|--------|-------------|
| `hide` | Widget becomes invisible |
| `minimize` | Widget collapses to icon |
| `collapse` | Widget shows only header |

### 6.4 Widget Types

| Type | Component | Description |
|------|-----------|-------------|
| `message` | N/A | Plain text/markdown (no interaction) |
| `multiple_choice` | `<ax-multiple-choice>` | Single or multi-select options |
| `free_text` | `<ax-free-text-prompt>` | Text area input |
| `code_editor` | `<ax-code-editor>` | Code editing with syntax highlighting |
| `slider` | `<ax-slider>` | Numeric range selection |
| `hotspot` | `<ax-hotspot>` | Click region on image |
| `drag_drop` | `<ax-drag-drop>` | Drag items to zones (multiple variants) |
| `dropdown` | `<ax-dropdown>` | Single or multiple dropdowns |
| `iframe` | `<ax-iframe>` | Embedded external content (see §12) |
| `sticky_note` | `<ax-sticky-note>` | Lightweight annotation (canvas mode) |
| `image` | `<ax-image>` | Static or interactive image |
| `video` | `<ax-video>` | Video player with optional checkpoints |
| `graph_topology` | `<ax-graph-topology>` | Node/edge graph builder |
| `matrix_choice` | `<ax-matrix-choice>` | Matrix of MCSA/MCMA questions |
| `document_viewer` | `<ax-document-viewer>` | Markdown/text with TOC navigation |
| `file_upload` | `<ax-file-upload>` | File upload with type constraints |
| `rating` | `<ax-rating>` | Star/numeric rating input |
| `date_picker` | `<ax-date-picker>` | Date/time selection |
| `drawing` | `<ax-drawing>` | Freehand drawing canvas |

### 6.3 Widget Configuration Schema

#### 6.3.1 Multiple Choice

```json
{
  "widgetType": "multiple_choice",
  "config": {
    "options": ["Option A", "Option B", "Option C"],
    "allowMultiple": false,
    "shuffleOptions": true,
    "showLabels": true,
    "labelStyle": "letter"
  }
}
```

#### 6.3.2 Free Text

```json
{
  "widgetType": "free_text",
  "config": {
    "placeholder": "Type your answer...",
    "minLength": 10,
    "maxLength": 500,
    "multiline": true,
    "rows": 4
  }
}
```

#### 6.3.3 Code Editor

```json
{
  "widgetType": "code_editor",
  "config": {
    "language": "python",
    "initialCode": "def solution():\n    pass",
    "minLines": 5,
    "maxLines": 30,
    "readOnly": false,
    "showLineNumbers": true
  }
}
```

#### 6.3.4 Slider

```json
{
  "widgetType": "slider",
  "config": {
    "min": 0,
    "max": 100,
    "step": 1,
    "defaultValue": 50,
    "showValue": true,
    "labels": {
      "0": "Not at all",
      "50": "Somewhat",
      "100": "Extremely"
    }
  }
}
```

#### 6.3.5 Drag & Drop

The drag_drop widget supports multiple variants for different use cases.

##### 6.3.5.1 Category Drag & Drop (Default)

Drag items into categorical buckets/zones.

```json
{
  "widgetType": "drag_drop",
  "config": {
    "variant": "category",
    "items": [
      {"id": "item1", "content": "Python", "reusable": false},
      {"id": "item2", "content": "JavaScript", "reusable": false},
      {"id": "item3", "content": "SQL", "reusable": false}
    ],
    "zones": [
      {"id": "zone1", "label": "Compiled Languages", "ordered": false},
      {"id": "zone2", "label": "Interpreted Languages", "ordered": false},
      {"id": "zone_unused", "label": "Not Applicable", "ordered": false}
    ],
    "allowMultiplePerZone": true,
    "requireAllPlaced": true,
    "shuffleItems": true,
    "showZoneCapacity": false
  }
}
```

| Config Field | Type | Description |
|--------------|------|-------------|
| `variant` | `"category"` | Category-based drag and drop |
| `items[].reusable` | `boolean` | Can item be dragged multiple times |
| `zones[].ordered` | `boolean` | Is order within zone significant |
| `allowMultiplePerZone` | `boolean` | Multiple items per zone |
| `requireAllPlaced` | `boolean` | Must all items be placed |
| `showZoneCapacity` | `boolean` | Show max items per zone |

##### 6.3.5.2 Ordered Sequence Drag & Drop

Drag items to establish a specific order (e.g., steps in a process).

```json
{
  "widgetType": "drag_drop",
  "config": {
    "variant": "sequence",
    "items": [
      {"id": "step1", "content": "Initialize variables"},
      {"id": "step2", "content": "Read input"},
      {"id": "step3", "content": "Process data"},
      {"id": "step4", "content": "Output results"}
    ],
    "zones": [
      {"id": "ordered_zone", "label": "Correct Order", "ordered": true, "slots": 4}
    ],
    "shuffleItems": true,
    "showSlotNumbers": true
  }
}
```

##### 6.3.5.3 Graphical Drag & Drop

Drag items onto a background image with defined placement regions.

```json
{
  "widgetType": "drag_drop",
  "config": {
    "variant": "graphical",
    "backgroundImage": "https://example.com/diagram.png",
    "backgroundSize": {"width": 800, "height": 600},
    "items": [
      {"id": "label1", "content": "CPU", "reusable": true, "icon": "chip"},
      {"id": "label2", "content": "RAM", "reusable": true, "icon": "memory"},
      {"id": "label3", "content": "GPU", "reusable": false, "icon": "gpu"},
      {"id": "label4", "content": "SSD", "reusable": true, "icon": "storage"}
    ],
    "placeholders": [
      {
        "id": "ph1",
        "region": {"x": 100, "y": 150, "width": 80, "height": 40},
        "accepts": ["label1", "label2", "label3", "label4"],
        "hint": "Processing unit goes here"
      },
      {
        "id": "ph2",
        "region": {"x": 300, "y": 150, "width": 80, "height": 40},
        "accepts": ["label2"],
        "hint": "Memory module"
      },
      {
        "id": "ph3",
        "region": {"x": 500, "y": 150, "width": 80, "height": 40},
        "accepts": null,
        "hint": "Any component"
      }
    ],
    "showPlaceholderHints": true,
    "snapToPlaceholder": true,
    "allowFreePositioning": false
  }
}
```

| Config Field | Type | Description |
|--------------|------|-------------|
| `variant` | `"graphical"` | Image-based drag and drop |
| `backgroundImage` | `string` | URL of background image |
| `items[].reusable` | `boolean` | Can drag same item multiple times |
| `items[].icon` | `string?` | Optional icon identifier |
| `placeholders[].region` | `object` | Drop zone rectangle on image |
| `placeholders[].accepts` | `string[]?` | Allowed item IDs (null = any) |
| `placeholders[].hint` | `string?` | Tooltip for placeholder |
| `snapToPlaceholder` | `boolean` | Snap items to placeholder center |
| `allowFreePositioning` | `boolean` | Allow drops outside placeholders |

**Response Format for Graphical Drag & Drop:**

```json
{
  "widgetId": "widget_dnd_graphical",
  "value": {
    "placements": [
      {"placeholderId": "ph1", "itemId": "label1"},
      {"placeholderId": "ph2", "itemId": "label2"},
      {"placeholderId": "ph3", "itemId": "label4"}
    ],
    "freePositions": []
  }
}
```

#### 6.3.6 Graph Topology Builder

Interactive node/edge graph builder for creating topologies, flowcharts, and network diagrams.

```json
{
  "widgetType": "graph_topology",
  "config": {
    "mode": "build",
    "nodeTypes": [
      {
        "typeId": "server",
        "label": "Server",
        "icon": "server",
        "color": "#4CAF50",
        "maxInstances": null,
        "properties": [
          {"name": "hostname", "type": "text", "required": true},
          {"name": "cpu_cores", "type": "number", "default": 4}
        ]
      },
      {
        "typeId": "database",
        "label": "Database",
        "icon": "database",
        "color": "#2196F3",
        "maxInstances": 2,
        "properties": [
          {"name": "engine", "type": "select", "options": ["PostgreSQL", "MySQL", "MongoDB"]}
        ]
      },
      {
        "typeId": "client",
        "label": "Client",
        "icon": "monitor",
        "color": "#FF9800",
        "maxInstances": null,
        "properties": []
      }
    ],
    "edgeTypes": [
      {
        "typeId": "connection",
        "label": "Connects To",
        "style": "arrow",
        "color": "#666",
        "bidirectional": false
      },
      {
        "typeId": "replication",
        "label": "Replicates",
        "style": "dashed-arrow",
        "color": "#9C27B0",
        "bidirectional": true
      }
    ],
    "regions": [
      {
        "regionId": "vpc_public",
        "label": "Public Subnet",
        "color": "rgba(76, 175, 80, 0.1)",
        "borderColor": "#4CAF50"
      },
      {
        "regionId": "vpc_private",
        "label": "Private Subnet",
        "color": "rgba(33, 150, 243, 0.1)",
        "borderColor": "#2196F3"
      }
    ],
    "constraints": {
      "minNodes": 2,
      "maxNodes": 20,
      "minEdges": 1,
      "maxEdges": 50,
      "allowCycles": true,
      "allowSelfLoops": false,
      "requireConnected": true
    },
    "initialGraph": null,
    "toolbar": {
      "showNodePalette": true,
      "showEdgeTools": true,
      "showRegionTools": true,
      "showLayoutTools": true
    },
    "validation": {
      "rules": [
        {"rule": "each_client_connects_to_server", "message": "Each client must connect to at least one server"}
      ]
    }
  }
}
```

**Response Format for Graph Topology:**

```json
{
  "widgetId": "widget_graph_1",
  "value": {
    "nodes": [
      {"nodeId": "n1", "typeId": "server", "position": {"x": 100, "y": 100}, "properties": {"hostname": "web-01", "cpu_cores": 8}},
      {"nodeId": "n2", "typeId": "database", "position": {"x": 300, "y": 100}, "properties": {"engine": "PostgreSQL"}},
      {"nodeId": "n3", "typeId": "client", "position": {"x": 100, "y": 300}, "properties": {}}
    ],
    "edges": [
      {"edgeId": "e1", "typeId": "connection", "sourceNodeId": "n3", "targetNodeId": "n1"},
      {"edgeId": "e2", "typeId": "connection", "sourceNodeId": "n1", "targetNodeId": "n2"}
    ],
    "regions": [
      {"regionId": "r1", "typeId": "vpc_public", "bounds": {"x": 50, "y": 50, "width": 400, "height": 150}, "containedNodes": ["n1", "n2"]}
    ]
  }
}
```

#### 6.3.7 Matrix Choice

Grid of multiple choice questions (MCSA or MCMA per row/column).

```json
{
  "widgetType": "matrix_choice",
  "config": {
    "layout": "rows",
    "rows": [
      {"id": "row1", "label": "Python is a compiled language"},
      {"id": "row2", "label": "JavaScript runs in browsers"},
      {"id": "row3", "label": "SQL is used for styling"},
      {"id": "row4", "label": "HTML is a programming language"}
    ],
    "columns": [
      {"id": "col_true", "label": "True"},
      {"id": "col_false", "label": "False"},
      {"id": "col_depends", "label": "It Depends"}
    ],
    "selectionMode": "single",
    "requireAllRows": true,
    "shuffleRows": true,
    "shuffleColumns": false,
    "showRowNumbers": true,
    "stickyHeader": true
  }
}
```

| Config Field | Type | Description |
|--------------|------|-------------|
| `layout` | `"rows" \| "columns"` | Primary axis for questions |
| `selectionMode` | `"single" \| "multiple"` | MCSA or MCMA per row |
| `requireAllRows` | `boolean` | Must answer every row |
| `shuffleRows` | `boolean` | Randomize row order |
| `shuffleColumns` | `boolean` | Randomize column order |
| `stickyHeader` | `boolean` | Keep header visible on scroll |

**Alternative: Column-based Matrix (Likert Scale)**

```json
{
  "widgetType": "matrix_choice",
  "config": {
    "layout": "likert",
    "rows": [
      {"id": "q1", "label": "I enjoy learning new programming languages"},
      {"id": "q2", "label": "I prefer working in teams"},
      {"id": "q3", "label": "I find debugging frustrating"}
    ],
    "columns": [
      {"id": "1", "label": "Strongly Disagree", "value": 1},
      {"id": "2", "label": "Disagree", "value": 2},
      {"id": "3", "label": "Neutral", "value": 3},
      {"id": "4", "label": "Agree", "value": 4},
      {"id": "5", "label": "Strongly Agree", "value": 5}
    ],
    "selectionMode": "single",
    "requireAllRows": true
  }
}
```

**Response Format for Matrix Choice:**

```json
{
  "widgetId": "widget_matrix_1",
  "value": {
    "selections": {
      "row1": ["col_false"],
      "row2": ["col_true"],
      "row3": ["col_false"],
      "row4": ["col_false"]
    }
  }
}
```

#### 6.3.8 Document Viewer

Rich text/markdown viewer with navigation and optional comprehension widgets.

```json
{
  "widgetType": "document_viewer",
  "config": {
    "content": "# Chapter 1: Introduction\n\n## 1.1 Overview\n\nThis document covers...\n\n## 1.2 Prerequisites\n\n...",
    "contentType": "markdown",
    "contentUrl": null,
    "tableOfContents": {
      "enabled": true,
      "position": "left",
      "collapsible": true,
      "defaultExpanded": true,
      "maxDepth": 3
    },
    "navigation": {
      "showProgress": true,
      "showPageNumbers": false,
      "enableSearch": true,
      "enableHighlight": true
    },
    "sections": [
      {
        "sectionId": "sec_1_1",
        "heading": "1.1 Overview",
        "anchorId": "overview",
        "requiredReadTime": 30,
        "checkpoint": true
      },
      {
        "sectionId": "sec_1_2",
        "heading": "1.2 Prerequisites",
        "anchorId": "prerequisites",
        "requiredReadTime": 60,
        "checkpoint": false
      }
    ],
    "embeddedWidgets": [
      {
        "anchorId": "quiz_1",
        "widgetId": "embedded_mc_1",
        "widgetType": "multiple_choice",
        "config": {"options": ["A", "B", "C"], "allowMultiple": false}
      }
    ],
    "readingMode": {
      "fontSize": "medium",
      "lineHeight": 1.6,
      "theme": "auto"
    }
  }
}
```

| Config Field | Type | Description |
|--------------|------|-------------|
| `content` | `string?` | Inline markdown/text content |
| `contentUrl` | `string?` | URL to fetch content from |
| `contentType` | `"markdown" \| "html" \| "text"` | Content format |
| `tableOfContents.maxDepth` | `number` | Heading levels to include (1-6) |
| `sections[].requiredReadTime` | `number?` | Seconds user must spend |
| `sections[].checkpoint` | `boolean` | Trigger progress event |
| `embeddedWidgets` | `array` | Inline widgets at anchor points |

**Response Format for Document Viewer:**

```json
{
  "widgetId": "widget_doc_1",
  "value": {
    "readSections": ["sec_1_1", "sec_1_2"],
    "timeSpent": 145,
    "highlights": [
      {"sectionId": "sec_1_1", "text": "important concept", "color": "yellow"}
    ],
    "embeddedResponses": {
      "embedded_mc_1": {"value": "B"}
    }
  }
}
```

#### 6.3.9 Hotspot

Interactive image with clickable regions.

```json
{
  "widgetType": "hotspot",
  "config": {
    "image": "https://example.com/anatomy.png",
    "imageSize": {"width": 800, "height": 600},
    "regions": [
      {
        "id": "region1",
        "shape": "circle",
        "coords": {"cx": 200, "cy": 150, "r": 30},
        "label": "Heart",
        "correct": true
      },
      {
        "id": "region2",
        "shape": "rect",
        "coords": {"x": 350, "y": 100, "width": 80, "height": 60},
        "label": "Lungs",
        "correct": false
      },
      {
        "id": "region3",
        "shape": "polygon",
        "coords": {"points": [[100, 200], [150, 250], [100, 300], [50, 250]]},
        "label": "Liver",
        "correct": false
      }
    ],
    "selectionMode": "single",
    "showLabels": false,
    "highlightOnHover": true,
    "showFeedbackImmediately": false
  }
}
```

#### 6.3.10 Drawing

Freehand drawing canvas for diagrams, sketches, or handwriting.

```json
{
  "widgetType": "drawing",
  "config": {
    "canvasSize": {"width": 800, "height": 600},
    "backgroundImage": null,
    "backgroundColor": "#ffffff",
    "tools": {
      "pen": {"enabled": true, "colors": ["#000", "#f00", "#00f", "#0f0"], "sizes": [2, 4, 8]},
      "highlighter": {"enabled": true, "colors": ["#ffff00", "#ff9900"], "opacity": 0.4},
      "eraser": {"enabled": true, "sizes": [10, 20, 40]},
      "shapes": {"enabled": true, "types": ["rectangle", "circle", "arrow", "line"]},
      "text": {"enabled": true, "fonts": ["sans-serif", "monospace"]}
    },
    "initialDrawing": null,
    "allowUndo": true,
    "maxUndoSteps": 50
  }
}
```

**Response Format for Drawing:**

```json
{
  "widgetId": "widget_drawing_1",
  "value": {
    "format": "svg",
    "data": "<svg>...</svg>",
    "png_base64": "iVBORw0KGgo..."
  }
}
```

#### 6.3.11 File Upload

File upload with type and size constraints.

```json
{
  "widgetType": "file_upload",
  "config": {
    "accept": [".pdf", ".docx", ".txt", "image/*"],
    "maxFileSize": 10485760,
    "maxFiles": 5,
    "minFiles": 1,
    "allowDragDrop": true,
    "showPreview": true,
    "previewMaxHeight": 200,
    "uploadEndpoint": "/api/uploads",
    "uploadMethod": "POST",
    "uploadHeaders": {},
    "autoUpload": true,
    "showProgress": true,
    "allowRemove": true,
    "placeholder": "Drag files here or click to browse",
    "helperText": "Accepted formats: PDF, DOCX, TXT, images. Max 10MB per file."
  }
}
```

| Config Field | Type | Description |
|--------------|------|-------------|
| `accept` | `string[]` | Accepted file types (MIME types or extensions) |
| `maxFileSize` | `number` | Maximum file size in bytes |
| `maxFiles` | `number` | Maximum number of files |
| `minFiles` | `number` | Minimum required files |
| `uploadEndpoint` | `string` | URL to upload files to |
| `autoUpload` | `boolean` | Upload immediately on selection |

**Response Format for File Upload:**

```json
{
  "widgetId": "widget_upload_1",
  "value": {
    "files": [
      {
        "fileId": "file_abc123",
        "filename": "assignment.pdf",
        "mimeType": "application/pdf",
        "size": 245678,
        "uploadedAt": "2025-12-18T10:30:00.000Z",
        "url": "https://storage.example.com/uploads/file_abc123"
      }
    ]
  }
}
```

#### 6.3.12 Rating

Star or numeric rating input.

```json
{
  "widgetType": "rating",
  "config": {
    "style": "stars",
    "maxRating": 5,
    "allowHalf": true,
    "defaultValue": null,
    "showValue": true,
    "showLabels": true,
    "labels": {
      "1": "Poor",
      "2": "Fair",
      "3": "Good",
      "4": "Very Good",
      "5": "Excellent"
    },
    "size": "medium",
    "color": "#FFB400",
    "emptyColor": "#E0E0E0",
    "icon": "star",
    "required": true
  }
}
```

| Config Field | Type | Description |
|--------------|------|-------------|
| `style` | `"stars" \| "numeric" \| "emoji" \| "thumbs"` | Rating display style |
| `maxRating` | `number` | Maximum rating value (typically 5 or 10) |
| `allowHalf` | `boolean` | Allow half-star ratings |
| `icon` | `string` | Icon type: `star`, `heart`, `circle`, custom |

**Response Format for Rating:**

```json
{
  "widgetId": "widget_rating_1",
  "value": 4.5
}
```

#### 6.3.13 Date Picker

Date, time, or datetime selection.

```json
{
  "widgetType": "date_picker",
  "config": {
    "mode": "date",
    "format": "YYYY-MM-DD",
    "displayFormat": "MMMM D, YYYY",
    "placeholder": "Select a date",
    "minDate": "2025-01-01",
    "maxDate": "2025-12-31",
    "disabledDates": ["2025-12-25", "2025-01-01"],
    "disabledDaysOfWeek": [0, 6],
    "defaultValue": null,
    "showTodayButton": true,
    "showClearButton": true,
    "weekStartsOn": 1,
    "locale": "en-US",
    "timezone": "America/New_York",
    "required": true
  }
}
```

| Config Field | Type | Description |
|--------------|------|-------------|
| `mode` | `"date" \| "time" \| "datetime" \| "daterange"` | Picker mode |
| `format` | `string` | Output format (ISO 8601 recommended) |
| `displayFormat` | `string` | Display format for UI |
| `minDate` | `string?` | Earliest selectable date |
| `maxDate` | `string?` | Latest selectable date |
| `disabledDates` | `string[]` | Specific dates to disable |
| `disabledDaysOfWeek` | `number[]` | Days of week to disable (0=Sunday) |

**Response Format for Date Picker:**

```json
{
  "widgetId": "widget_date_1",
  "value": "2025-06-15"
}

// For daterange mode:
{
  "widgetId": "widget_date_1",
  "value": {
    "start": "2025-06-15",
    "end": "2025-06-20"
  }
}

// For datetime mode:
{
  "widgetId": "widget_date_1",
  "value": "2025-06-15T14:30:00.000Z"
}
```

#### 6.3.14 Dropdown

Single or multiple dropdown selection.

```json
{
  "widgetType": "dropdown",
  "config": {
    "options": [
      {"value": "js", "label": "JavaScript", "icon": "js-icon"},
      {"value": "py", "label": "Python", "icon": "python-icon"},
      {"value": "ts", "label": "TypeScript", "icon": "ts-icon", "disabled": true},
      {"value": "go", "label": "Go", "group": "Compiled"}
    ],
    "groups": [
      {"id": "interpreted", "label": "Interpreted Languages"},
      {"id": "compiled", "label": "Compiled Languages"}
    ],
    "multiple": false,
    "searchable": true,
    "clearable": true,
    "placeholder": "Select a language...",
    "noOptionsMessage": "No languages found",
    "maxSelections": null,
    "minSelections": 1,
    "creatable": false,
    "defaultValue": null,
    "disabled": false,
    "loading": false,
    "virtualized": false,
    "maxDropdownHeight": 300
  }
}
```

| Config Field | Type | Description |
|--------------|------|-------------|
| `options` | `array` | Available options with value, label, optional icon/group |
| `groups` | `array?` | Option groupings |
| `multiple` | `boolean` | Allow multiple selections |
| `searchable` | `boolean` | Enable search/filter |
| `creatable` | `boolean` | Allow creating new options |
| `virtualized` | `boolean` | Use virtualization for large lists |

**Response Format for Dropdown:**

```json
// Single selection
{
  "widgetId": "widget_dropdown_1",
  "value": "py"
}

// Multiple selection
{
  "widgetId": "widget_dropdown_1",
  "value": ["py", "js"]
}
```

#### 6.3.15 Image

Static or interactive image display.

```json
{
  "widgetType": "image",
  "config": {
    "src": "https://example.com/diagram.png",
    "alt": "System architecture diagram",
    "caption": "Figure 1: High-level architecture",
    "width": 800,
    "height": 600,
    "objectFit": "contain",
    "zoomable": true,
    "maxZoom": 3.0,
    "pannable": true,
    "showControls": true,
    "downloadable": false,
    "fallbackSrc": "https://example.com/placeholder.png",
    "lazyLoad": true,
    "borderRadius": 8,
    "shadow": true
  }
}
```

| Config Field | Type | Description |
|--------------|------|-------------|
| `objectFit` | `"contain" \| "cover" \| "fill" \| "none"` | How image fits container |
| `zoomable` | `boolean` | Enable zoom interaction |
| `pannable` | `boolean` | Enable pan when zoomed |
| `downloadable` | `boolean` | Show download button |
| `lazyLoad` | `boolean` | Lazy load the image |

**Response Format for Image (if interactive):**

```json
{
  "widgetId": "widget_image_1",
  "value": {
    "viewed": true,
    "zoomLevel": 1.5,
    "viewDuration": 45
  }
}
```

#### 6.3.16 Video

Video player with optional checkpoints and interactions.

```json
{
  "widgetType": "video",
  "config": {
    "src": "https://videos.example.com/lesson-1.mp4",
    "poster": "https://videos.example.com/lesson-1-poster.jpg",
    "title": "Introduction to Python",
    "duration": 600,
    "autoplay": false,
    "muted": false,
    "loop": false,
    "controls": {
      "play": true,
      "pause": true,
      "seek": true,
      "volume": true,
      "fullscreen": true,
      "playbackSpeed": true,
      "captions": true,
      "quality": true
    },
    "playbackSpeeds": [0.5, 0.75, 1, 1.25, 1.5, 2],
    "captions": [
      {"language": "en", "label": "English", "src": "https://.../en.vtt"},
      {"language": "es", "label": "Spanish", "src": "https://.../es.vtt"}
    ],
    "qualities": [
      {"label": "1080p", "src": "https://.../1080p.mp4"},
      {"label": "720p", "src": "https://.../720p.mp4"},
      {"label": "480p", "src": "https://.../480p.mp4"}
    ],
    "checkpoints": [
      {
        "checkpointId": "cp_1",
        "timestamp": 120,
        "pauseOnReach": true,
        "required": true,
        "widget": {
          "widgetId": "video_quiz_1",
          "widgetType": "multiple_choice",
          "config": {"options": ["A", "B", "C"], "allowMultiple": false}
        }
      },
      {
        "checkpointId": "cp_2",
        "timestamp": 300,
        "pauseOnReach": false,
        "required": false,
        "action": "show_note",
        "note": "Key concept: This is important!"
      }
    ],
    "chapters": [
      {"title": "Introduction", "startTime": 0},
      {"title": "Core Concepts", "startTime": 60},
      {"title": "Examples", "startTime": 180},
      {"title": "Summary", "startTime": 480}
    ],
    "requiredWatchPercentage": 90,
    "preventSkipAhead": true,
    "trackProgress": true
  }
}
```

| Config Field | Type | Description |
|--------------|------|-------------|
| `checkpoints` | `array` | Timestamps with actions or embedded widgets |
| `chapters` | `array` | Video chapters for navigation |
| `requiredWatchPercentage` | `number?` | Minimum percentage to watch |
| `preventSkipAhead` | `boolean` | Block skipping to unwatched sections |
| `trackProgress` | `boolean` | Track viewing progress |

**Response Format for Video:**

```json
{
  "widgetId": "widget_video_1",
  "value": {
    "watchedPercentage": 95,
    "totalWatchTime": 580,
    "completedCheckpoints": ["cp_1", "cp_2"],
    "checkpointResponses": {
      "video_quiz_1": {"value": "B"}
    },
    "lastPosition": 570,
    "playbackEvents": [
      {"event": "play", "timestamp": 0, "time": "2025-12-18T10:00:00Z"},
      {"event": "pause", "timestamp": 120, "time": "2025-12-18T10:02:00Z"},
      {"event": "seek", "from": 120, "to": 180, "time": "2025-12-18T10:05:00Z"}
    ]
  }
}
```

#### 6.3.17 Sticky Note

Lightweight annotation for canvas mode.

```json
{
  "widgetType": "sticky_note",
  "config": {
    "content": "Remember: Lists are mutable!",
    "editable": true,
    "maxLength": 500,
    "placeholder": "Add a note...",
    "style": {
      "backgroundColor": "#FFF59D",
      "textColor": "#333333",
      "fontSize": 14,
      "fontFamily": "sans-serif",
      "shadow": true,
      "rotation": -2
    },
    "showTimestamp": true,
    "showAuthor": true,
    "author": "Instructor",
    "createdAt": "2025-12-18T10:30:00.000Z",
    "pinned": false,
    "minimizable": true,
    "minimized": false
  }
}
```

| Config Field | Type | Description |
|--------------|------|-------------|
| `editable` | `boolean` | User can edit content |
| `style.rotation` | `number?` | Degrees of rotation (-15 to 15 for natural look) |
| `pinned` | `boolean` | Prevent moving/dismissing |
| `minimizable` | `boolean` | Can collapse to icon |

**Response Format for Sticky Note:**

```json
{
  "widgetId": "widget_sticky_1",
  "value": {
    "content": "Updated note content from user",
    "editedAt": "2025-12-18T10:35:00.000Z"
  }
}
```

### 6.4 Widget Lifecycle

```
┌─────────────┐    data.widget.render    ┌─────────────┐
│   PENDING   │ ───────────────────────► │  RENDERED   │
└─────────────┘                          └─────────────┘
                                               │
                                               │ User interacts
                                               ▼
                                         ┌─────────────┐
                                         │   ACTIVE    │
                                         └─────────────┘
                                               │
                                               │ data.response.submit
                                               ▼
┌─────────────┐  control.widget.readonly ┌─────────────┐
│  READONLY   │ ◄─────────────────────── │  SUBMITTED  │
└─────────────┘                          └─────────────┘
```

### 6.5 Widget Completion Behavior

After a widget receives a response, its appearance is controlled by `widgetCompletionBehavior`:

| Value | Behavior |
|-------|----------|
| `readonly` | Widget stays visible but disabled (preserves features like code highlighting) |
| `text` | Widget is replaced with plain text representation |
| `hidden` | Widget is removed from view |

**Recommendation:** Use `readonly` for best UX as it preserves widget-specific formatting.

---

## 7. 2D Canvas System

The canvas system enables spatial, non-linear conversations where widgets can be positioned, connected, and organized freely on a 2D plane. This is designed to support advanced use cases like mind mapping, flowchart-based learning, visual programming, and collaborative workspaces.

### 7.1 Canvas Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          CANVAS VIEWPORT                                  │
│                         (Browser Window)                                  │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │    ┌──────────────────────────────────────────────────────────┐    │  │
│  │    │                     CANVAS WORLD                          │    │  │
│  │    │                   (Large scrollable)                      │    │  │
│  │    │                                                           │    │  │
│  │    │   ┌─────────┐                   ┌─────────┐               │    │  │
│  │    │   │ Widget  │───Connection────►│ Widget  │               │    │  │
│  │    │   │   A     │                   │   B     │               │    │  │
│  │    │   └─────────┘                   └─────────┘               │    │  │
│  │    │        │                                                   │    │  │
│  │    │        │ Connection                                        │    │  │
│  │    │        ▼                                                   │    │  │
│  │    │   ┌─────────┐         ┌─ ─ ─ ─ ─ ─┐                       │    │  │
│  │    │   │ Widget  │         │   Group   │                       │    │  │
│  │    │   │   C     │         │┌─────────┐│                       │    │  │
│  │    │   └─────────┘         ││Widget D ││                       │    │  │
│  │    │                       │└─────────┘│                       │    │  │
│  │    │                       │┌─────────┐│                       │    │  │
│  │    │                       ││Widget E ││                       │    │  │
│  │    │                       │└─────────┘│                       │    │  │
│  │    │                       └─ ─ ─ ─ ─ ─┘                       │    │  │
│  │    │                                                           │    │  │
│  │    └──────────────────────────────────────────────────────────┘    │  │
│  │                                                                     │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                           ┌─────────────┐                                │
│                           │  MINIMAP    │                                │
│                           └─────────────┘                                │
└──────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Canvas Configuration

**`control.canvas.config`** (Server → Client)

Configure canvas properties. Sent with `control.conversation.display` when mode is "canvas".

```json
{
  "type": "control.canvas.config",
  "payload": {
    "canvas": {
      "width": 5000,
      "height": 4000,
      "backgroundColor": "#1a1a1a",
      "backgroundImage": null,
      "backgroundPattern": "dots"
    },
    "grid": {
      "enabled": true,
      "size": 20,
      "snapToGrid": true,
      "visible": true,
      "color": "#333333"
    },
    "zoom": {
      "initial": 1.0,
      "min": 0.1,
      "max": 4.0,
      "step": 0.1
    },
    "viewport": {
      "initialX": 0,
      "initialY": 0,
      "panEnabled": true,
      "panButton": "middle"
    },
    "minimap": {
      "enabled": true,
      "position": "bottom-right",
      "size": { "width": 200, "height": 150 }
    },
    "features": {
      "connections": true,
      "groups": true,
      "layers": true,
      "annotations": true,
      "multiSelect": true,
      "collaboration": false
    }
  }
}
```

**Background Patterns:**

| Pattern | Description |
|---------|-------------|
| `none` | Solid color |
| `dots` | Dot grid pattern |
| `lines` | Line grid pattern |
| `crosshatch` | Crosshatch pattern |
| `custom` | Use `backgroundImage` |

### 7.3 Viewport Control

**`control.canvas.viewport`** (Server → Client)

Programmatically control the viewport (what part of canvas is visible).

```json
{
  "type": "control.canvas.viewport",
  "payload": {
    "action": "focus",
    "target": {
      "type": "widget",
      "widgetId": "widget_mc_1"
    },
    "zoom": 1.5,
    "padding": 50,
    "animate": true,
    "animationDuration": 500,
    "animationEasing": "ease-out"
  }
}
```

**Viewport Actions:**

| Action | Description | Required Fields |
|--------|-------------|-----------------|
| `focus` | Center view on target | `target` |
| `pan` | Pan to absolute position | `position` |
| `panBy` | Pan by relative offset | `offset` |
| `zoom` | Set zoom level | `zoom` |
| `zoomToFit` | Fit all content in view | - |
| `zoomToSelection` | Fit selected items | - |
| `reset` | Reset to initial view | - |

**Focus Target Types:**

```json
// Focus on specific widget
{ "type": "widget", "widgetId": "widget_mc_1" }

// Focus on group
{ "type": "group", "groupId": "group_concept_1" }

// Focus on multiple widgets (bounding box)
{ "type": "widgets", "widgetIds": ["w1", "w2", "w3"] }

// Focus on coordinates
{ "type": "point", "x": 500, "y": 300 }

// Focus on region
{ "type": "region", "x": 100, "y": 100, "width": 800, "height": 600 }
```

---

**`control.canvas.zoom`** (Server → Client)

Set zoom level.

```json
{
  "type": "control.canvas.zoom",
  "payload": {
    "level": 1.5,
    "center": { "x": 400, "y": 300 },
    "animate": true
  }
}
```

---

**`control.canvas.viewportChanged`** (Client → Server)

Notify server of viewport changes (for analytics/sync).

```json
{
  "type": "control.canvas.viewportChanged",
  "payload": {
    "position": { "x": 250, "y": 100 },
    "zoom": 1.2,
    "visibleRegion": {
      "x": 250,
      "y": 100,
      "width": 1200,
      "height": 800
    }
  }
}
```

### 7.4 Canvas Mode Control

**`control.canvas.mode`** (Server → Client)

Switch canvas interaction modes.

```json
{
  "type": "control.canvas.mode",
  "payload": {
    "mode": "connect",
    "config": {
      "connectionType": "arrow",
      "sourceWidget": "widget_a"
    }
  }
}
```

**Canvas Modes:**

| Mode | Description |
|------|-------------|
| `select` | Default mode, select and interact with widgets |
| `pan` | Pan/scroll the canvas |
| `connect` | Draw connections between widgets |
| `annotate` | Add sticky notes and annotations |
| `draw` | Freehand drawing mode |
| `presentation` | Lock view, follow guided path |

---

**`control.canvas.modeChanged`** (Client → Server)

Notify server of mode change.

```json
{
  "type": "control.canvas.modeChanged",
  "payload": {
    "mode": "connect",
    "previousMode": "select"
  }
}
```

### 7.5 Connections

Connections create visual relationships between widgets (arrows, lines).

**`control.canvas.connection.create`** (Server → Client)

Create a connection between widgets.

```json
{
  "type": "control.canvas.connection.create",
  "payload": {
    "connectionId": "conn_a_to_b",
    "source": {
      "widgetId": "widget_a",
      "anchor": "right"
    },
    "target": {
      "widgetId": "widget_b",
      "anchor": "left"
    },
    "style": {
      "type": "arrow",
      "color": "#4CAF50",
      "width": 2,
      "dash": null,
      "animate": false
    },
    "label": {
      "text": "leads to",
      "position": "middle"
    },
    "interactive": true,
    "condition": null
  }
}
```

**Connection Anchors:**

| Anchor | Description |
|--------|-------------|
| `auto` | Automatic best anchor |
| `top` | Top center of widget |
| `right` | Right center of widget |
| `bottom` | Bottom center of widget |
| `left` | Left center of widget |
| `top-left` | Top-left corner |
| `top-right` | Top-right corner |
| `bottom-left` | Bottom-left corner |
| `bottom-right` | Bottom-right corner |

**Connection Types:**

| Type | Description |
|------|-------------|
| `arrow` | Arrow pointing to target |
| `line` | Simple line |
| `curve` | Curved bezier line |
| `elbow` | Right-angle connector |
| `double-arrow` | Arrows on both ends |

---

**`control.canvas.connection.update`** (Server → Client)

Update connection properties.

```json
{
  "type": "control.canvas.connection.update",
  "payload": {
    "connectionId": "conn_a_to_b",
    "style": {
      "color": "#F44336",
      "animate": true
    },
    "label": {
      "text": "incorrect path"
    }
  }
}
```

---

**`control.canvas.connection.delete`** (Server → Client)

Remove a connection.

```json
{
  "type": "control.canvas.connection.delete",
  "payload": {
    "connectionId": "conn_a_to_b",
    "animate": true
  }
}
```

---

**`control.canvas.connection.created`** (Client → Server)

User manually created a connection (when allowed).

```json
{
  "type": "control.canvas.connection.created",
  "payload": {
    "sourceWidgetId": "widget_a",
    "sourceAnchor": "right",
    "targetWidgetId": "widget_b",
    "targetAnchor": "left"
  }
}
```

---

**Conditional Connections:**

Connections can be conditional based on widget responses:

```json
{
  "type": "control.canvas.connection.create",
  "payload": {
    "connectionId": "conn_branch_1",
    "source": { "widgetId": "widget_q1" },
    "target": { "widgetId": "widget_correct" },
    "condition": {
      "sourceWidget": "widget_q1",
      "operator": "equals",
      "value": "A"
    },
    "style": { "type": "arrow", "color": "#4CAF50" },
    "label": { "text": "Correct!" }
  }
}
```

**Condition Operators:**

| Operator | Description |
|----------|-------------|
| `equals` | Exact match |
| `not_equals` | Not equal |
| `contains` | String contains |
| `in` | Value in array |
| `greater_than` | Numeric comparison |
| `less_than` | Numeric comparison |
| `regex` | Regex match |

### 7.6 Groups and Containers

Groups allow organizing widgets into logical units.

**`control.canvas.group.create`** (Server → Client)

Create a group.

```json
{
  "type": "control.canvas.group.create",
  "payload": {
    "groupId": "group_concept_1",
    "title": "Python Basics",
    "widgetIds": ["widget_a", "widget_b", "widget_c"],
    "style": {
      "backgroundColor": "rgba(100, 100, 255, 0.1)",
      "borderColor": "#6464FF",
      "borderRadius": 8
    },
    "collapsible": true,
    "collapsed": false,
    "draggable": true,
    "layout": {
      "position": { "x": 100, "y": 100 },
      "padding": 20
    }
  }
}
```

---

**`control.canvas.group.update`** (Server → Client)

Update group properties.

```json
{
  "type": "control.canvas.group.update",
  "payload": {
    "groupId": "group_concept_1",
    "collapsed": true,
    "title": "Python Basics (Completed)"
  }
}
```

---

**`control.canvas.group.add`** (Server → Client)

Add widgets to group.

```json
{
  "type": "control.canvas.group.add",
  "payload": {
    "groupId": "group_concept_1",
    "widgetIds": ["widget_d"]
  }
}
```

---

**`control.canvas.group.remove`** (Server → Client)

Remove widgets from group (but not delete them).

```json
{
  "type": "control.canvas.group.remove",
  "payload": {
    "groupId": "group_concept_1",
    "widgetIds": ["widget_a"]
  }
}
```

---

**`control.canvas.group.delete`** (Server → Client)

Delete the group container (widgets remain).

```json
{
  "type": "control.canvas.group.delete",
  "payload": {
    "groupId": "group_concept_1",
    "deleteWidgets": false
  }
}
```

---

**`control.canvas.group.toggled`** (Client → Server)

User toggled group collapse state.

```json
{
  "type": "control.canvas.group.toggled",
  "payload": {
    "groupId": "group_concept_1",
    "collapsed": true
  }
}
```

### 7.7 Layers

Layers control visibility and organization of canvas elements.

**`control.canvas.layer.create`** (Server → Client)

Create a new layer.

```json
{
  "type": "control.canvas.layer.create",
  "payload": {
    "layerId": "layer_hints",
    "name": "Hints",
    "visible": true,
    "locked": false,
    "opacity": 1.0,
    "zIndex": 10
  }
}
```

---

**`control.canvas.layer.update`** (Server → Client)

Update layer properties.

```json
{
  "type": "control.canvas.layer.update",
  "payload": {
    "layerId": "layer_hints",
    "visible": false
  }
}
```

---

**`control.canvas.layer.assign`** (Server → Client)

Assign widgets to a layer.

```json
{
  "type": "control.canvas.layer.assign",
  "payload": {
    "layerId": "layer_hints",
    "widgetIds": ["hint_1", "hint_2", "hint_3"]
  }
}
```

---

**`control.canvas.layer.toggled`** (Client → Server)

User toggled layer visibility.

```json
{
  "type": "control.canvas.layer.toggled",
  "payload": {
    "layerId": "layer_hints",
    "visible": false
  }
}
```

### 7.8 Selection

Multi-select functionality for batch operations.

**`control.canvas.selection.set`** (Server → Client)

Set current selection.

```json
{
  "type": "control.canvas.selection.set",
  "payload": {
    "widgetIds": ["widget_a", "widget_b"],
    "groupIds": [],
    "connectionIds": []
  }
}
```

---

**`control.canvas.selection.changed`** (Client → Server)

User changed selection.

```json
{
  "type": "control.canvas.selection.changed",
  "payload": {
    "widgetIds": ["widget_a", "widget_b", "widget_c"],
    "groupIds": [],
    "connectionIds": [],
    "selectionMethod": "lasso"
  }
}
```

**Selection Methods:**

| Method | Description |
|--------|-------------|
| `click` | Single click |
| `ctrl_click` | Control/Cmd + click |
| `shift_click` | Shift + click (range) |
| `lasso` | Lasso selection tool |
| `marquee` | Rectangle selection |

### 7.9 Annotations

Lightweight notes and drawings on the canvas.

**`data.annotation.create`** (Server → Client)

Create an annotation.

```json
{
  "type": "data.annotation.create",
  "payload": {
    "annotationId": "note_1",
    "annotationType": "sticky_note",
    "content": "Remember: Lists are mutable!",
    "position": { "x": 300, "y": 200 },
    "style": {
      "backgroundColor": "#FFF59D",
      "textColor": "#333",
      "fontSize": 14
    },
    "author": "Instructor",
    "timestamp": "2025-12-18T10:30:00.000Z"
  }
}
```

**Annotation Types:**

| Type | Description |
|------|-------------|
| `sticky_note` | Text note |
| `callout` | Callout pointing to element |
| `highlight` | Highlight region |
| `drawing` | Freehand drawing |
| `shape` | Rectangle, circle, etc. |
| `text` | Plain text label |

---

**`data.annotation.created`** (Client → Server)

User created annotation (when allowed).

```json
{
  "type": "data.annotation.created",
  "payload": {
    "annotationType": "sticky_note",
    "content": "I don't understand this part",
    "position": { "x": 450, "y": 320 }
  }
}
```

### 7.10 Presentation Mode

Guided tours and presentation sequences.

**`control.canvas.presentation.start`** (Server → Client)

Start a presentation/guided tour.

```json
{
  "type": "control.canvas.presentation.start",
  "payload": {
    "presentationId": "tour_intro",
    "title": "Introduction to Python Lists",
    "steps": [
      {
        "stepId": "step_1",
        "target": { "type": "widget", "widgetId": "widget_intro" },
        "zoom": 1.2,
        "narration": "Let's start by understanding what lists are...",
        "duration": null,
        "action": "await_interaction"
      },
      {
        "stepId": "step_2",
        "target": { "type": "widgets", "widgetIds": ["w1", "w2"] },
        "zoom": 1.0,
        "narration": "Here are two examples of list creation.",
        "duration": 5000,
        "action": "auto_advance"
      },
      {
        "stepId": "step_3",
        "target": { "type": "group", "groupId": "group_exercises" },
        "zoom": 0.8,
        "narration": "Now try these exercises!",
        "duration": null,
        "action": "await_all_complete"
      }
    ],
    "controls": {
      "showProgress": true,
      "allowSkip": true,
      "allowBack": true
    }
  }
}
```

**Presentation Step Actions:**

| Action | Description |
|--------|-------------|
| `auto_advance` | Advance after duration |
| `await_click` | Wait for click/tap |
| `await_interaction` | Wait for widget interaction |
| `await_complete` | Wait for widget completion |
| `await_all_complete` | Wait for all visible widgets |
| `manual` | Wait for next/previous navigation |

---

**`control.canvas.presentation.step`** (Server → Client)

Move to specific step.

```json
{
  "type": "control.canvas.presentation.step",
  "payload": {
    "stepId": "step_2",
    "animate": true
  }
}
```

---

**`control.canvas.presentation.end`** (Server → Client)

End presentation mode.

```json
{
  "type": "control.canvas.presentation.end",
  "payload": {
    "presentationId": "tour_intro",
    "reason": "completed"
  }
}
```

---

**`control.canvas.presentation.navigated`** (Client → Server)

User navigated within presentation.

```json
{
  "type": "control.canvas.presentation.navigated",
  "payload": {
    "presentationId": "tour_intro",
    "fromStep": "step_1",
    "toStep": "step_2",
    "action": "next"
  }
}
```

### 7.11 Collaboration Features

Real-time multi-user features (when enabled).

**`control.canvas.cursor.update`** (Both Directions)

Share cursor position.

```json
{
  "type": "control.canvas.cursor.update",
  "payload": {
    "userId": "user_123",
    "userName": "Alice",
    "position": { "x": 450, "y": 300 },
    "color": "#FF5722"
  }
}
```

---

**`control.canvas.presence.update`** (Server → Client)

Update list of active users.

```json
{
  "type": "control.canvas.presence.update",
  "payload": {
    "users": [
      {
        "userId": "user_123",
        "userName": "Alice",
        "color": "#FF5722",
        "focusedWidget": "widget_q1"
      },
      {
        "userId": "user_456",
        "userName": "Bob",
        "color": "#2196F3",
        "focusedWidget": null
      }
    ]
  }
}
```

---

**`control.canvas.lock.acquire`** (Client → Server)

Request lock on element.

```json
{
  "type": "control.canvas.lock.acquire",
  "payload": {
    "elementType": "widget",
    "elementId": "widget_q1"
  }
}
```

---

**`control.canvas.lock.acquired`** (Server → Client)

Lock acquisition result.

```json
{
  "type": "control.canvas.lock.acquired",
  "payload": {
    "elementType": "widget",
    "elementId": "widget_q1",
    "success": true,
    "lockedBy": "user_123",
    "expiresAt": "2025-12-18T10:35:00.000Z"
  }
}
```

### 7.12 Grid and Alignment

**`control.canvas.grid.update`** (Server → Client)

Update grid settings.

```json
{
  "type": "control.canvas.grid.update",
  "payload": {
    "enabled": true,
    "size": 25,
    "snapToGrid": true,
    "visible": true
  }
}
```

---

**`control.canvas.align`** (Server → Client)

Align multiple widgets.

```json
{
  "type": "control.canvas.align",
  "payload": {
    "widgetIds": ["w1", "w2", "w3"],
    "alignment": "center-horizontal",
    "distribute": false,
    "animate": true
  }
}
```

**Alignment Options:**

| Alignment | Description |
|-----------|-------------|
| `left` | Align left edges |
| `center-horizontal` | Align centers horizontally |
| `right` | Align right edges |
| `top` | Align top edges |
| `center-vertical` | Align centers vertically |
| `bottom` | Align bottom edges |

**Distribution Options:**

| Option | Description |
|--------|-------------|
| `horizontal` | Distribute evenly horizontally |
| `vertical` | Distribute evenly vertically |

### 7.13 State Management

**`control.canvas.state.save`** (Client → Server)

Request state checkpoint.

```json
{
  "type": "control.canvas.state.save",
  "payload": {
    "name": "Before experiment",
    "includeResponses": true
  }
}
```

---

**`control.canvas.state.saved`** (Server → Client)

Confirm state saved.

```json
{
  "type": "control.canvas.state.saved",
  "payload": {
    "checkpointId": "ckpt_123",
    "name": "Before experiment",
    "timestamp": "2025-12-18T10:30:00.000Z"
  }
}
```

---

**`control.canvas.state.restore`** (Client → Server)

Request state restoration.

```json
{
  "type": "control.canvas.state.restore",
  "payload": {
    "checkpointId": "ckpt_123"
  }
}
```

---

**`control.canvas.undo`** / **`control.canvas.redo`** (Client → Server)

Undo/redo canvas operations.

```json
{
  "type": "control.canvas.undo",
  "payload": {}
}
```

### 7.14 Conditional Widget Visibility

Control widget visibility based on other widget responses.

**`control.widget.condition`** (Server → Client)

Set visibility/state condition for a widget.

```json
{
  "type": "control.widget.condition",
  "payload": {
    "widgetId": "widget_advanced",
    "conditions": [
      {
        "sourceWidget": "widget_skill_level",
        "operator": "equals",
        "value": "advanced",
        "effect": "show"
      }
    ],
    "defaultState": "hidden",
    "evaluateOn": "submit"
  }
}
```

**Effects:**

| Effect | Description |
|--------|-------------|
| `show` | Make widget visible |
| `hide` | Hide widget |
| `enable` | Enable widget |
| `disable` | Disable widget |
| `focus` | Focus on widget |

### 7.15 Bookmarks and Navigation Points

Named locations on the canvas for quick navigation.

**`control.canvas.bookmark.create`** (Server → Client)

Create a bookmark/navigation point.

```json
{
  "type": "control.canvas.bookmark.create",
  "payload": {
    "bookmarkId": "bm_intro",
    "name": "Introduction",
    "description": "Starting point for the lesson",
    "target": {
      "type": "region",
      "x": 0,
      "y": 0,
      "width": 800,
      "height": 600
    },
    "zoom": 1.0,
    "icon": "flag",
    "color": "#4CAF50",
    "showInNavigation": true,
    "sortOrder": 1
  }
}
```

---

**`control.canvas.bookmark.update`** (Server → Client)

Update bookmark properties.

```json
{
  "type": "control.canvas.bookmark.update",
  "payload": {
    "bookmarkId": "bm_intro",
    "name": "Introduction (Completed)",
    "icon": "check"
  }
}
```

---

**`control.canvas.bookmark.delete`** (Server → Client)

Remove a bookmark.

```json
{
  "type": "control.canvas.bookmark.delete",
  "payload": {
    "bookmarkId": "bm_intro"
  }
}
```

---

**`control.canvas.bookmark.navigate`** (Client → Server)

User navigated to bookmark.

```json
{
  "type": "control.canvas.bookmark.navigate",
  "payload": {
    "bookmarkId": "bm_intro"
  }
}
```

---

**`control.canvas.bookmark.created`** (Client → Server)

User created a personal bookmark (when allowed).

```json
{
  "type": "control.canvas.bookmark.created",
  "payload": {
    "name": "My note",
    "position": {"x": 500, "y": 300},
    "zoom": 1.2
  }
}
```

### 7.16 Drawing Layer

Freehand drawing and shape annotations directly on the canvas.

**`control.canvas.drawing.start`** (Server → Client)

Enable drawing mode with specific tools.

```json
{
  "type": "control.canvas.drawing.start",
  "payload": {
    "layerId": "drawing_layer_1",
    "tools": {
      "pen": {"enabled": true, "defaultColor": "#FF0000", "defaultSize": 3},
      "highlighter": {"enabled": true, "defaultColor": "#FFFF00", "opacity": 0.4},
      "eraser": {"enabled": true, "defaultSize": 20},
      "shapes": {"enabled": true, "types": ["rectangle", "circle", "arrow", "line"]},
      "text": {"enabled": true, "defaultFont": "sans-serif", "defaultSize": 14}
    },
    "persistent": true,
    "collaborative": false
  }
}
```

---

**`control.canvas.drawing.stroke`** (Client → Server)

User drew a stroke/shape.

```json
{
  "type": "control.canvas.drawing.stroke",
  "payload": {
    "strokeId": "stroke_123",
    "tool": "pen",
    "color": "#FF0000",
    "size": 3,
    "points": [[100, 100], [105, 102], [110, 105], [120, 110]],
    "layerId": "drawing_layer_1"
  }
}
```

---

**`control.canvas.drawing.shape`** (Client → Server)

User created a shape.

```json
{
  "type": "control.canvas.drawing.shape",
  "payload": {
    "shapeId": "shape_123",
    "shapeType": "rectangle",
    "bounds": {"x": 100, "y": 100, "width": 200, "height": 150},
    "style": {
      "strokeColor": "#000000",
      "strokeWidth": 2,
      "fillColor": "rgba(66, 133, 244, 0.2)"
    },
    "layerId": "drawing_layer_1"
  }
}
```

---

**`control.canvas.drawing.clear`** (Both Directions)

Clear drawing content.

```json
{
  "type": "control.canvas.drawing.clear",
  "payload": {
    "layerId": "drawing_layer_1",
    "scope": "all"
  }
}
```

| Scope | Description |
|-------|-------------|
| `all` | Clear all drawings on layer |
| `user` | Clear only current user's drawings |
| `selection` | Clear selected elements |

### 7.17 Smart Guides and Snapping

Alignment aids for precise widget positioning.

**`control.canvas.guides.config`** (Server → Client)

Configure smart guide behavior.

```json
{
  "type": "control.canvas.guides.config",
  "payload": {
    "smartGuides": {
      "enabled": true,
      "snapThreshold": 10,
      "showDistances": true,
      "color": "#FF4081"
    },
    "customGuides": [
      {"type": "vertical", "position": 400, "label": "Center"},
      {"type": "horizontal", "position": 300, "label": "Middle"}
    ],
    "rulers": {
      "enabled": true,
      "units": "px"
    }
  }
}
```

---

**`control.canvas.guides.add`** (Server → Client)

Add a custom guide line.

```json
{
  "type": "control.canvas.guides.add",
  "payload": {
    "guideId": "guide_1",
    "type": "vertical",
    "position": 500,
    "label": "Section Boundary",
    "locked": true
  }
}
```

---

**`control.canvas.guides.added`** (Client → Server)

User added a guide.

```json
{
  "type": "control.canvas.guides.added",
  "payload": {
    "type": "horizontal",
    "position": 250
  }
}
```

### 7.18 Copy, Paste, and Duplicate

Clipboard operations for canvas elements.

**`control.canvas.clipboard.copy`** (Client → Server)

User copied elements.

```json
{
  "type": "control.canvas.clipboard.copy",
  "payload": {
    "widgetIds": ["w1", "w2"],
    "connectionIds": ["conn_1"],
    "includeResponses": false
  }
}
```

---

**`control.canvas.clipboard.paste`** (Client → Server)

User pasted elements.

```json
{
  "type": "control.canvas.clipboard.paste",
  "payload": {
    "position": {"x": 500, "y": 300},
    "offset": {"x": 20, "y": 20}
  }
}
```

---

**`control.canvas.clipboard.pasted`** (Server → Client)

Confirm paste with new element IDs.

```json
{
  "type": "control.canvas.clipboard.pasted",
  "payload": {
    "mapping": {
      "w1": "w1_copy_1",
      "w2": "w2_copy_1",
      "conn_1": "conn_1_copy_1"
    },
    "widgets": [
      {"widgetId": "w1_copy_1", "position": {"x": 520, "y": 320}},
      {"widgetId": "w2_copy_1", "position": {"x": 720, "y": 320}}
    ]
  }
}
```

---

**`control.canvas.duplicate`** (Client → Server)

Quick duplicate (copy + paste in place).

```json
{
  "type": "control.canvas.duplicate",
  "payload": {
    "widgetIds": ["w1"],
    "offset": {"x": 50, "y": 50}
  }
}
```

### 7.19 Search and Filter

Find and filter canvas elements.

**`control.canvas.search.query`** (Client → Server)

User searched for content.

```json
{
  "type": "control.canvas.search.query",
  "payload": {
    "query": "python list",
    "scope": "all",
    "filters": {
      "widgetTypes": ["multiple_choice", "free_text"],
      "states": ["active", "readonly"],
      "layers": null
    }
  }
}
```

---

**`control.canvas.search.results`** (Server → Client)

Return search results.

```json
{
  "type": "control.canvas.search.results",
  "payload": {
    "query": "python list",
    "results": [
      {
        "type": "widget",
        "widgetId": "w1",
        "matchedText": "Python list comprehension",
        "position": {"x": 100, "y": 200}
      },
      {
        "type": "annotation",
        "annotationId": "note_5",
        "matchedText": "Remember: lists are mutable",
        "position": {"x": 300, "y": 400}
      }
    ],
    "totalCount": 2
  }
}
```

---

**`control.canvas.search.highlight`** (Server → Client)

Highlight search result.

```json
{
  "type": "control.canvas.search.highlight",
  "payload": {
    "resultIndex": 0,
    "focusViewport": true
  }
}
```

---

**`control.canvas.filter.apply`** (Both Directions)

Apply visual filter to canvas.

```json
{
  "type": "control.canvas.filter.apply",
  "payload": {
    "filterId": "filter_completed",
    "criteria": {
      "widgetStates": ["readonly"],
      "effect": "dim"
    }
  }
}
```

| Effect | Description |
|--------|-------------|
| `dim` | Reduce opacity of non-matching |
| `hide` | Hide non-matching elements |
| `highlight` | Highlight matching elements |
| `isolate` | Show only matching elements |

### 7.20 Comments and Threads

Discussion threads attached to canvas elements.

**`control.canvas.comment.create`** (Server → Client)

Create a comment thread.

```json
{
  "type": "control.canvas.comment.create",
  "payload": {
    "commentId": "comment_1",
    "threadId": "thread_1",
    "attachedTo": {
      "type": "widget",
      "widgetId": "w1"
    },
    "position": {"x": 350, "y": 100},
    "author": {
      "userId": "user_instructor",
      "name": "Dr. Smith",
      "avatar": "https://..."
    },
    "content": "Great attempt! Consider edge cases.",
    "timestamp": "2025-12-18T10:30:00.000Z",
    "resolved": false
  }
}
```

---

**`control.canvas.comment.reply`** (Client → Server)

User replied to comment.

```json
{
  "type": "control.canvas.comment.reply",
  "payload": {
    "threadId": "thread_1",
    "content": "Thanks! I'll add error handling."
  }
}
```

---

**`control.canvas.comment.resolve`** (Both Directions)

Mark thread as resolved.

```json
{
  "type": "control.canvas.comment.resolve",
  "payload": {
    "threadId": "thread_1",
    "resolved": true
  }
}
```

---

**`control.canvas.comment.delete`** (Both Directions)

Delete a comment.

```json
{
  "type": "control.canvas.comment.delete",
  "payload": {
    "commentId": "comment_1"
  }
}
```

### 7.21 History and Timeline

View and navigate canvas history.

**`control.canvas.history.list`** (Client → Server)

Request history entries.

```json
{
  "type": "control.canvas.history.list",
  "payload": {
    "limit": 50,
    "offset": 0
  }
}
```

---

**`control.canvas.history.entries`** (Server → Client)

Return history entries.

```json
{
  "type": "control.canvas.history.entries",
  "payload": {
    "entries": [
      {
        "entryId": "hist_1",
        "timestamp": "2025-12-18T10:30:00.000Z",
        "action": "widget_response",
        "description": "Answered question 1",
        "widgetId": "w1",
        "canRevert": true
      },
      {
        "entryId": "hist_2",
        "timestamp": "2025-12-18T10:31:00.000Z",
        "action": "widget_moved",
        "description": "Moved widget",
        "widgetId": "w2",
        "canRevert": true
      }
    ],
    "totalCount": 25,
    "hasMore": false
  }
}
```

---

**`control.canvas.history.revert`** (Client → Server)

Revert to a specific history point.

```json
{
  "type": "control.canvas.history.revert",
  "payload": {
    "entryId": "hist_1",
    "preserveAfter": false
  }
}
```

---

**`control.canvas.history.timeline`** (Server → Client)

Show interactive timeline visualization.

```json
{
  "type": "control.canvas.history.timeline",
  "payload": {
    "enabled": true,
    "position": "bottom",
    "showThumbnails": true,
    "autoplay": false
  }
}
```

### 7.22 Widget Templates and Cloning

Pre-defined widget configurations for rapid creation.

**`control.canvas.template.list`** (Server → Client)

Provide available widget templates.

```json
{
  "type": "control.canvas.template.list",
  "payload": {
    "templates": [
      {
        "templateId": "tpl_mc_basic",
        "name": "Multiple Choice (4 options)",
        "category": "assessment",
        "preview": "https://...",
        "widgetType": "multiple_choice",
        "config": {
          "options": ["Option A", "Option B", "Option C", "Option D"],
          "allowMultiple": false
        }
      },
      {
        "templateId": "tpl_code_python",
        "name": "Python Code Editor",
        "category": "coding",
        "widgetType": "code_editor",
        "config": {
          "language": "python",
          "initialCode": "# Your code here\n",
          "minLines": 10
        }
      }
    ]
  }
}
```

---

**`control.canvas.template.instantiate`** (Client → Server)

User created widget from template.

```json
{
  "type": "control.canvas.template.instantiate",
  "payload": {
    "templateId": "tpl_mc_basic",
    "position": {"x": 200, "y": 300}
  }
}
```

### 7.23 Canvas Export and Import

Export canvas state for sharing or backup.

**`control.canvas.export.request`** (Client → Server)

Request canvas export.

```json
{
  "type": "control.canvas.export.request",
  "payload": {
    "format": "json",
    "includeResponses": true,
    "includeHistory": false,
    "region": null
  }
}
```

| Format | Description |
|--------|-------------|
| `json` | Full canvas state as JSON |
| `png` | Screenshot as PNG image |
| `svg` | Vector export as SVG |
| `pdf` | PDF document |

---

**`control.canvas.export.ready`** (Server → Client)

Export is ready for download.

```json
{
  "type": "control.canvas.export.ready",
  "payload": {
    "exportId": "exp_123",
    "format": "json",
    "url": "https://...",
    "expiresAt": "2025-12-18T11:00:00.000Z",
    "size": 125000
  }
}
```

---

**`control.canvas.import.request`** (Client → Server)

Request to import canvas state.

```json
{
  "type": "control.canvas.import.request",
  "payload": {
    "format": "json",
    "data": "{...}",
    "mergeMode": "replace"
  }
}
```

| Merge Mode | Description |
|------------|-------------|
| `replace` | Replace entire canvas |
| `append` | Add to existing canvas |
| `merge` | Smart merge by widget ID |

---

## 8. Connection Lifecycle

### 8.1 Connection Establishment

```
Client                                    Server
  │                                         │
  │──── WebSocket Upgrade Request ─────────►│
  │     (with auth cookie/JWT)              │
  │                                         │
  │◄─── HTTP 101 Switching Protocols ───────│
  │                                         │
  │◄─── system.connection.established ──────│
  │     {conversationId, userId, ...}       │
  │                                         │
```

**`system.connection.established`**

Sent by server immediately after WebSocket connection.

```json
{
  "type": "system.connection.established",
  "payload": {
    "connectionId": "conn_abc123",
    "conversationId": "conv_xyz789",
    "userId": "user_123",
    "definitionId": "tutor-python",
    "resuming": false,
    "serverTime": "2025-12-18T10:30:00.000Z"
  }
}
```

### 8.2 Keepalive

**`system.ping`** / **`system.pong`**

Bidirectional keepalive mechanism.

```json
{
  "type": "system.ping",
  "payload": {
    "timestamp": "2025-12-18T10:30:00.000Z"
  }
}
```

**Timing:**

- Client sends ping every **30 seconds**
- Server responds with pong within **5 seconds**
- If no pong received, client initiates reconnection

### 8.3 Reconnection

When the WebSocket connection is lost and re-established:

**`system.connection.resume`** (Client → Server)

```json
{
  "type": "system.connection.resume",
  "payload": {
    "conversationId": "conv_xyz789",
    "lastMessageId": "msg_abc123",
    "lastItemIndex": 2,
    "clientState": {
      "pendingWidgetIds": ["widget_mc_1"],
      "inputContent": "partially typed..."
    }
  }
}
```

**`system.connection.resumed`** (Server → Client)

```json
{
  "type": "system.connection.resumed",
  "payload": {
    "conversationId": "conv_xyz789",
    "resumedFromMessageId": "msg_abc123",
    "currentItemIndex": 2,
    "missedMessages": 0,
    "stateValid": true
  }
}
```

If `stateValid: false`, client should request full state refresh.

### 8.4 Graceful Disconnect

**`system.connection.close`**

Graceful connection closure.

```json
{
  "type": "system.connection.close",
  "payload": {
    "reason": "user_logout",
    "code": 1000
  }
}
```

| Reason | Description |
|--------|-------------|
| `user_logout` | User explicitly logged out |
| `session_expired` | Authentication expired |
| `server_shutdown` | Server is shutting down |
| `conversation_complete` | Conversation ended |
| `idle_timeout` | Connection idle too long |

### 8.5 WebSocket Close Codes

WebSocket close codes follow RFC 6455 with application-specific extensions.

#### 8.5.1 Standard Close Codes

| Code | Name | Description | Client Action |
|------|------|-------------|---------------|
| `1000` | Normal Closure | Clean shutdown | No reconnect needed |
| `1001` | Going Away | Server shutting down or client navigating away | May reconnect after delay |
| `1002` | Protocol Error | Protocol violation detected | Do not reconnect; log error |
| `1003` | Unsupported Data | Received data type not supported | Do not reconnect; log error |
| `1005` | No Status Received | No close code provided | May reconnect |
| `1006` | Abnormal Closure | Connection lost unexpectedly | Reconnect with backoff |
| `1007` | Invalid Payload Data | Message data was invalid | Do not reconnect; fix client |
| `1008` | Policy Violation | Message violates policy | Do not reconnect |
| `1009` | Message Too Big | Message exceeds size limit | Do not reconnect; reduce size |
| `1010` | Mandatory Extension | Server didn't negotiate required extension | Do not reconnect |
| `1011` | Internal Error | Server encountered unexpected condition | Reconnect with backoff |
| `1012` | Service Restart | Server restarting | Reconnect after delay |
| `1013` | Try Again Later | Server temporarily overloaded | Reconnect after `Retry-After` |
| `1014` | Bad Gateway | Server acting as gateway received invalid response | Reconnect with backoff |
| `1015` | TLS Handshake | TLS handshake failed | Check certificates; do not reconnect |

#### 8.5.2 Application-Specific Close Codes (4000-4999)

| Code | Name | Description | Client Action |
|------|------|-------------|---------------|
| `4000` | Authentication Required | No valid credentials provided | Redirect to login |
| `4001` | Authentication Expired | Session/JWT expired | Refresh token and reconnect |
| `4002` | Authentication Invalid | Credentials rejected | Redirect to login |
| `4003` | Conversation Not Found | Requested conversation doesn't exist | Show error; don't reconnect |
| `4004` | Conversation Ended | Conversation was completed or terminated | Show completion; don't reconnect |
| `4005` | Definition Not Found | Agent definition not found | Show error; don't reconnect |
| `4006` | Rate Limited | Too many connections/messages | Reconnect after backoff |
| `4007` | Duplicate Connection | Another connection for same session exists | Close this connection |
| `4008` | Idle Timeout | Connection idle too long | May reconnect if user active |
| `4009` | Maintenance Mode | Server in maintenance | Show message; reconnect later |
| `4010` | Version Mismatch | Protocol version incompatible | Update client |
| `4011` | Payload Too Large | Message exceeded size limit | Reduce message size |
| `4012` | Invalid Message | Message failed validation | Fix message format |
| `4013` | Resource Exhausted | Server resources exhausted | Reconnect after delay |
| `4014` | Upstream Error | Backend service failed | Reconnect with backoff |
| `4015` | Conversation Paused | Conversation paused by proctor/admin | Wait for resume |

#### 8.5.3 Reconnection Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    RECONNECTION DECISION TREE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  WebSocket Closed                                                │
│        │                                                         │
│        ▼                                                         │
│  ┌──────────────┐                                                │
│  │ Check Code   │                                                │
│  └──────────────┘                                                │
│        │                                                         │
│        ├── 1000, 4004: ──────► DO NOT RECONNECT (normal end)     │
│        │                                                         │
│        ├── 4000-4002: ───────► REDIRECT TO LOGIN                 │
│        │                                                         │
│        ├── 4003, 4005, 4010: ─► SHOW ERROR (unrecoverable)       │
│        │                                                         │
│        ├── 1006, 1011, 1012,                                     │
│        │   1013, 4006, 4014: ─► RECONNECT WITH BACKOFF           │
│        │                                                         │
│        └── 4007: ────────────► CLOSE (duplicate)                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Exponential Backoff Algorithm:**

```typescript
function calculateBackoff(attempt: number): number {
  const baseDelay = 1000;    // 1 second
  const maxDelay = 30000;    // 30 seconds
  const jitter = Math.random() * 1000;  // 0-1 second jitter

  const delay = Math.min(
    baseDelay * Math.pow(2, attempt) + jitter,
    maxDelay
  );

  return delay;
}

// Usage:
// Attempt 1: ~1-2 seconds
// Attempt 2: ~2-3 seconds
// Attempt 3: ~4-5 seconds
// Attempt 4: ~8-9 seconds
// Attempt 5+: capped at 30 seconds
```

**Maximum Reconnection Attempts:**

| Scenario | Max Attempts | Action After |
|----------|--------------|---------------|
| Network blip (1006) | 10 | Show "connection lost" UI |
| Server restart (1012) | 5 | Show retry button |
| Rate limited (4006) | 3 | Show "slow down" message |
| Auth expired (4001) | 1 | Redirect to refresh/login |

---

## 9. Error Handling

### 9.1 Error Message Structure

**`system.error`**

```json
{
  "type": "system.error",
  "payload": {
    "category": "validation",
    "code": "INVALID_WIDGET_RESPONSE",
    "message": "Response value is required for this widget",
    "details": {
      "widgetId": "widget_mc_1",
      "field": "value"
    },
    "isRetryable": true,
    "retryAfterMs": null
  }
}
```

### 9.2 Error Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `transport` | WebSocket/connection issues | Connection lost, timeout |
| `authentication` | Auth failures | Token expired, unauthorized |
| `validation` | Invalid request data | Missing fields, invalid format |
| `business` | Business logic errors | Item locked, navigation denied |
| `server` | Internal server errors | LLM failure, database error |
| `rate_limit` | Rate limiting triggered | Too many requests |

### 9.3 Error Codes

| Code | Category | Description |
|------|----------|-------------|
| `CONNECTION_LOST` | transport | WebSocket disconnected |
| `CONNECTION_TIMEOUT` | transport | Keepalive timeout |
| `AUTH_EXPIRED` | authentication | JWT/session expired |
| `AUTH_INVALID` | authentication | Invalid credentials |
| `INVALID_MESSAGE` | validation | Malformed message envelope |
| `INVALID_WIDGET_RESPONSE` | validation | Invalid widget response value |
| `MISSING_REQUIRED_FIELD` | validation | Required field not provided |
| `ITEM_LOCKED` | business | Cannot modify completed item |
| `NAVIGATION_DENIED` | business | Navigation not allowed |
| `CONVERSATION_PAUSED` | business | Conversation is paused |
| `TIME_EXPIRED` | business | Item/conversation time limit exceeded |
| `LLM_ERROR` | server | LLM provider error |
| `TOOL_EXECUTION_FAILED` | server | Tool execution error |
| `INTERNAL_ERROR` | server | Unexpected server error |
| `RATE_LIMITED` | rate_limit | Too many requests |

### 9.4 Retryable Errors

| `isRetryable` | Behavior |
|---------------|----------|
| `true` | Client may retry the operation |
| `false` | Client should not retry; user intervention needed |

When `isRetryable: true` and `retryAfterMs` is set, client should wait before retrying.

---

## 10. Timing & Deadlines

### 10.1 Timer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     TIMING HIERARCHY                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  CONVERSATION DEADLINE (Server-Controlled)               │    │
│  │  ─────────────────────────────────────────────────────   │    │
│  │  • Server sends absolute timestamp                       │    │
│  │  • Synced at every item context change                   │    │
│  │  • Server enforces expiration                            │    │
│  │                                                          │    │
│  │  ┌─────────────────┐  ┌─────────────────┐                │    │
│  │  │ ITEM 1 TIMER    │  │ ITEM 2 TIMER    │  ...           │    │
│  │  │ (Frontend)      │  │ (Frontend)      │                │    │
│  │  │                 │  │                 │                │    │
│  │  │ • Duration from │  │ • Duration from │                │    │
│  │  │   server        │  │   server        │                │    │
│  │  │ • Countdown by  │  │ • Countdown by  │                │    │
│  │  │   frontend      │  │   frontend      │                │    │
│  │  │ • Notify server │  │ • Notify server │                │    │
│  │  │   on expire     │  │   on expire     │                │    │
│  │  └─────────────────┘  └─────────────────┘                │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Conversation Deadline

- **Controller:** Server
- **Format:** Absolute timestamp (ISO 8601)
- **Delivery:** `control.conversation.deadline` and within `control.item.context`
- **Sync:** Re-sent at every item transition for clock drift mitigation
- **Enforcement:** Server rejects operations after deadline

```json
{
  "type": "control.conversation.deadline",
  "payload": {
    "deadline": "2025-12-18T11:00:00.000Z"
  }
}
```

### 10.3 Item Timer

- **Controller:** Frontend (countdown)
- **Duration Source:** Server sends `timeLimitSeconds` in `control.item.context`
- **Display:** Controlled by `showRemainingTime` flag
- **Expiration:** Frontend sends `control.item.expired` when timer reaches zero

**Frontend behavior options:**

| `showRemainingTime` | `timeLimitSeconds` | Behavior |
|---------------------|-------------------|----------|
| `true` | set | Display countdown, enforce |
| `false` | set | No display, still enforce |
| `false` | `null` | No timer |

**`control.item.expired`** (Client → Server)

```json
{
  "type": "control.item.expired",
  "payload": {
    "itemId": "item_q3",
    "expiredAt": "2025-12-18T10:35:00.000Z"
  }
}
```

### 10.4 Clock Synchronization

To handle client/server clock drift:

1. Server includes `serverTime` in `system.connection.established`
2. Client calculates offset: `offset = serverTime - clientTime`
3. All server timestamps are adjusted by offset for display
4. Deadline comparisons use adjusted time

---

## 11. Message Reference

### 11.1 Complete Message Type List

#### System Messages

| Type | Direction | Description |
|------|-----------|-------------|
| `system.connection.established` | S→C | Connection successful |
| `system.connection.resume` | C→S | Resume after reconnect |
| `system.connection.resumed` | S→C | Resume confirmation |
| `system.connection.close` | Both | Graceful disconnect |
| `system.ping` | Both | Keepalive ping |
| `system.pong` | Both | Keepalive response |
| `system.error` | S→C | Error notification |

#### Control Messages - Conversation Level (Server → Client)

| Type | Description |
|------|-------------|
| `control.conversation.config` | Initial configuration |
| `control.conversation.deadline` | Set/update deadline |
| `control.conversation.display` | Set display mode (flow/canvas) |
| `control.conversation.pause` | Server-initiated pause |
| `control.conversation.resume` | Server-initiated resume |
| `control.conversation.complete` | Conversation finished |

#### Control Messages - Item Level (Server → Client)

| Type | Description |
|------|-------------|
| `control.item.context` | New item context |
| `control.item.score` | Score feedback |
| `control.item.timeout` | Item time expired |

#### Control Messages - Widget Level (Server → Client)

| Type | Description |
|------|-------------|
| `control.widget.state` | Set widget state (active/readonly/disabled/hidden) |
| `control.widget.focus` | Request focus |
| `control.widget.validation` | Validation feedback |
| `control.widget.layout` | Update widget position/size (canvas) |
| `control.widget.condition` | Set conditional visibility |

#### Control Messages - Canvas (Server → Client)

| Type | Description |
|------|-------------|
| `control.canvas.config` | Configure canvas settings |
| `control.canvas.viewport` | Control viewport (pan/zoom/focus) |
| `control.canvas.zoom` | Set zoom level |
| `control.canvas.mode` | Switch canvas mode (select/pan/connect/annotate) |
| `control.canvas.connection.create` | Create widget connection |
| `control.canvas.connection.update` | Update connection properties |
| `control.canvas.connection.delete` | Remove connection |
| `control.canvas.group.create` | Create widget group |
| `control.canvas.group.update` | Update group properties |
| `control.canvas.group.add` | Add widgets to group |
| `control.canvas.group.remove` | Remove widgets from group |
| `control.canvas.group.delete` | Delete group container |
| `control.canvas.layer.create` | Create layer |
| `control.canvas.layer.update` | Update layer properties |
| `control.canvas.layer.assign` | Assign widgets to layer |
| `control.canvas.selection.set` | Set current selection |
| `control.canvas.grid.update` | Update grid settings |
| `control.canvas.align` | Align multiple widgets |
| `control.canvas.state.saved` | Confirm state checkpoint |
| `control.canvas.presentation.start` | Start guided presentation |
| `control.canvas.presentation.step` | Move to presentation step |
| `control.canvas.presentation.end` | End presentation |
| `control.canvas.presence.update` | Update active users |
| `control.canvas.lock.acquired` | Lock acquisition result |
| `control.canvas.cursor.update` | Share cursor position |
| `control.canvas.bookmark.create` | Create navigation bookmark |
| `control.canvas.bookmark.update` | Update bookmark properties |
| `control.canvas.bookmark.delete` | Remove bookmark |
| `control.canvas.drawing.start` | Enable drawing mode |
| `control.canvas.guides.config` | Configure smart guides |
| `control.canvas.guides.add` | Add custom guide line |
| `control.canvas.clipboard.pasted` | Confirm paste with new IDs |
| `control.canvas.search.results` | Return search results |
| `control.canvas.search.highlight` | Highlight search result |
| `control.canvas.filter.apply` | Apply visual filter |
| `control.canvas.comment.create` | Create comment thread |
| `control.canvas.comment.resolve` | Mark thread resolved |
| `control.canvas.comment.delete` | Delete comment |
| `control.canvas.history.entries` | Return history entries |
| `control.canvas.history.timeline` | Show timeline visualization |
| `control.canvas.template.list` | Provide widget templates |
| `control.canvas.export.ready` | Export ready for download |

#### Control Messages - Audit (Server → Client)

| Type | Description |
|------|-------------|
| `control.audit.config` | Update audit configuration mid-conversation |
| `control.audit.flush` | Request immediate flush of pending audit events |

#### Control Messages - IFRAME (Server → Client)

| Type | Description |
|------|-------------|
| `control.iframe.resize` | Request IFRAME size change |
| `control.iframe.navigate` | Navigate IFRAME to different content |

#### Control Messages (Client → Server)

| Type | Description |
|------|-------------|
| `control.flow.start` | Start conversation/template |
| `control.flow.pause` | User-initiated pause |
| `control.flow.resume` | User-initiated resume |
| `control.flow.cancel` | Cancel current operation |
| `control.navigation.next` | Navigate forward |
| `control.navigation.previous` | Navigate backward |
| `control.navigation.skip` | Skip current item |
| `control.item.expired` | Item timer expired |
| `control.widget.moved` | User moved widget (canvas) |
| `control.widget.resized` | User resized widget (canvas) |
| `control.widget.dismissed` | User dismissed widget |
| `control.canvas.viewportChanged` | Viewport position/zoom changed |
| `control.canvas.modeChanged` | Canvas mode changed |
| `control.canvas.connection.created` | User created connection |
| `control.canvas.group.toggled` | Group collapse toggled |
| `control.canvas.layer.toggled` | Layer visibility toggled |
| `control.canvas.selection.changed` | Selection changed |
| `control.canvas.state.save` | Request state checkpoint |
| `control.canvas.state.restore` | Request state restoration |
| `control.canvas.undo` | Undo operation |
| `control.canvas.redo` | Redo operation |
| `control.canvas.presentation.navigated` | Presentation navigation |
| `control.canvas.lock.acquire` | Request element lock |
| `control.canvas.cursor.update` | Share cursor position |
| `control.canvas.bookmark.navigate` | User navigated to bookmark |
| `control.canvas.bookmark.created` | User created personal bookmark |
| `control.canvas.drawing.stroke` | User drew a stroke |
| `control.canvas.drawing.shape` | User created a shape |
| `control.canvas.drawing.clear` | Clear drawing content |
| `control.canvas.guides.added` | User added guide line |
| `control.canvas.clipboard.copy` | User copied elements |
| `control.canvas.clipboard.paste` | User pasted elements |
| `control.canvas.duplicate` | Quick duplicate elements |
| `control.canvas.search.query` | User searched for content |
| `control.canvas.filter.apply` | Apply visual filter |
| `control.canvas.comment.reply` | User replied to comment |
| `control.canvas.comment.resolve` | Mark thread resolved |
| `control.canvas.comment.delete` | Delete comment |
| `control.canvas.history.list` | Request history entries |
| `control.canvas.history.revert` | Revert to history point |
| `control.canvas.template.instantiate` | Create widget from template |
| `control.canvas.export.request` | Request canvas export |
| `control.canvas.import.request` | Request canvas import |

#### Data Messages (Server → Client)

| Type | Description |
|------|-------------|
| `data.content.chunk` | Streaming content |
| `data.content.complete` | Content finished |
| `data.widget.render` | Render widget |
| `data.tool.call` | Tool being called |
| `data.tool.result` | Tool result |
| `data.message.ack` | Message acknowledged |
| `data.annotation.create` | Create annotation (canvas) |
| `data.iframe.command` | Command to relay to IFRAME |
| `data.iframe.state` | IFRAME state sync |
| `data.audit.ack` | Acknowledge receipt of audit batch |

#### Data Messages (Client → Server)

| Type | Description |
|------|-------------|
| `data.message.send` | User text message |
| `data.response.submit` | Widget response |
| `data.annotation.created` | User created annotation |
| `data.iframe.event` | Event relayed from IFRAME |
| `data.iframe.state` | IFRAME state sync |
| `data.iframe.error` | IFRAME error report |
| `data.audit.events` | Batched audit events (keystrokes, clicks, focus) |
| `data.audit.flushed` | Confirm flush completed |

### 11.2 Example Conversation Flow

```
CLIENT                                          SERVER
  │                                               │
  │──── [Connect WebSocket] ─────────────────────►│
  │                                               │
  │◄──── system.connection.established ───────────│
  │      {conversationId, userId}                 │
  │                                               │
  │──── control.flow.start ──────────────────────►│
  │     {}                                        │
  │                                               │
  │◄──── control.conversation.config ─────────────│
  │      {templateName, totalItems, ...}          │
  │                                               │
  │◄──── control.conversation.deadline ───────────│
  │      {deadline: "2025-12-18T11:00:00Z"}       │
  │                                               │
  │◄──── control.item.context ────────────────────│
  │      {itemId, itemIndex: 0, totalItems: 10}   │
  │                                               │
  │◄──── data.content.chunk ──────────────────────│
  │      {content: "Welcome to..."}               │
  │                                               │
  │◄──── data.widget.render ──────────────────────│
  │      {widgetId, widgetType: "multiple_choice"}│
  │                                               │
  │      [User selects option B]                  │
  │                                               │
  │──── data.response.submit ────────────────────►│
  │     {widgetId, value: "B"}                    │
  │                                               │
  │◄──── control.widget.readonly ─────────────────│
  │      {widgetId, readonly: true}               │
  │                                               │
  │◄──── control.item.score ──────────────────────│
  │      {score: 1, feedback: "Correct!"}         │
  │                                               │
  │◄──── control.item.context ────────────────────│
  │      {itemId, itemIndex: 1, ...}              │
  │                                               │
  │      ... [continues] ...                      │
  │                                               │
  │◄──── control.conversation.complete ───────────│
  │      {totalScore, maxScore}                   │
  │                                               │
```

### 11.3 Example Canvas Mode Flow

```
CLIENT                                          SERVER
  │                                               │
  │──── [Connect WebSocket] ─────────────────────►│
  │                                               │
  │◄──── system.connection.established ───────────│
  │      {conversationId, userId}                 │
  │                                               │
  │──── control.flow.start ──────────────────────►│
  │     {}                                        │
  │                                               │
  │◄──── control.conversation.display ────────────│
  │      {mode: "canvas", canvasConfig: {...}}    │
  │                                               │
  │◄──── control.canvas.config ───────────────────│
  │      {canvas: {width, height}, grid, zoom}    │
  │                                               │
  │◄──── data.widget.render ──────────────────────│
  │      {widgetId: "w1", layout: {x:100, y:100}} │
  │                                               │
  │◄──── data.widget.render ──────────────────────│
  │      {widgetId: "w2", layout: {x:400, y:100}} │
  │                                               │
  │◄──── control.canvas.connection.create ────────│
  │      {source: "w1", target: "w2"}             │
  │                                               │
  │◄──── control.canvas.group.create ─────────────│
  │      {groupId: "g1", widgetIds: ["w1", "w2"]} │
  │                                               │
  │      [User drags widget w1]                   │
  │                                               │
  │──── control.widget.moved ────────────────────►│
  │     {widgetId: "w1", position: {x:150, y:120}}│
  │                                               │
  │      [User completes widget w1]               │
  │                                               │
  │──── data.response.submit ────────────────────►│
  │     {widgetId: "w1", value: "answer"}         │
  │                                               │
  │◄──── control.widget.state ────────────────────│
  │      {widgetId: "w1", state: "readonly"}      │
  │                                               │
  │◄──── control.canvas.connection.update ────────│
  │      {connectionId, style: {color: "green"}}  │
  │                                               │
  │◄──── data.widget.render ──────────────────────│
  │      {widgetId: "w3", layout: {x:700, y:100}} │
  │                                               │
  │◄──── control.canvas.connection.create ────────│
  │      {source: "w2", target: "w3",             │
  │       condition: {sourceWidget: "w1", ...}}   │
  │                                               │
  │◄──── control.canvas.viewport ─────────────────│
  │      {action: "focus", target: {widgetId:"w3"}}│
  │                                               │
  │      ... [continues] ...                      │
  │                                               │
```

### 11.4 Example IFRAME Integration Flow

```
FRONTEND                    IFRAME                      BACKEND
  │                           │                            │
  │── Render <ax-iframe> ────►│                            │
  │                           │                            │
  │◄── postMessage(ready) ────│                            │
  │                           │                            │
  │── data.iframe.event ──────────────────────────────────►│
  │   {eventType: "ready"}    │                            │
  │                           │                            │
  │◄── data.iframe.command ────────────────────────────────│
  │   {command: "start", params: {difficulty: "medium"}}   │
  │                           │                            │
  │── postMessage(start) ────►│                            │
  │                           │                            │
  │                           │  [User interacts]          │
  │                           │                            │
  │◄── postMessage(progress) ─│                            │
  │   {step: 3, total: 5}     │                            │
  │                           │                            │
  │── data.iframe.event ──────────────────────────────────►│
  │   {eventType: "progress"} │                            │
  │                           │                            │
  │                           │  [User needs help]         │
  │                           │                            │
  │◄── postMessage(hint) ─────│                            │
  │   {type: "request_hint"}  │                            │
  │                           │                            │
  │── data.iframe.event ──────────────────────────────────►│
  │   {eventType: "request_hint"}                          │
  │                           │                            │
  │                           │   [LLM generates hint]     │
  │                           │                            │
  │◄── data.iframe.command ────────────────────────────────│
  │   {command: "provide_hint", params: {hint: "..."}}     │
  │                           │                            │
  │── postMessage(hint) ─────►│                            │
  │                           │                            │
  │                           │  [User completes]          │
  │                           │                            │
  │◄── postMessage(complete) ─│                            │
  │   {score: 85, time: 120}  │                            │
  │                           │                            │
  │── data.response.submit ───────────────────────────────►│
  │   {widgetId, value: {type: "iframe_result", ...}}      │
  │                           │                            │
  │◄── control.widget.state ───────────────────────────────│
  │   {widgetId, state: "readonly"}                        │
  │                           │                            │
```

---

## 12. IFRAME Widget

The IFRAME widget enables embedding external interactive content within conversations. This is a powerful feature for integrating third-party simulations, games, specialized editors, and other web-based tools.

### 12.1 Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        AGENT HOST FRONTEND                                  │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                     Canvas / Flow Area                              │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │              <ax-iframe> Widget Component                    │   │    │
│  │  │  ┌──────────────────────────────────────────────────────┐   │   │    │
│  │  │  │                                                       │   │   │    │
│  │  │  │              EMBEDDED IFRAME CONTENT                  │   │   │    │
│  │  │  │         (Third-party application/game)                │   │   │    │
│  │  │  │                                                       │   │   │    │
│  │  │  │    Communicates via postMessage ◄──────────────┐      │   │   │    │
│  │  │  │                                                │      │   │   │    │
│  │  │  └──────────────────────────────────────────────────────┘   │   │    │
│  │  │                          │                                   │   │    │
│  │  └──────────────────────────│───────────────────────────────────┘   │    │
│  │                             │ postMessage                            │    │
│  │                             ▼                                        │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │           WebSocket Handler (Protocol Messages)              │   │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │
│  │                             │                                        │    │
│  └─────────────────────────────│────────────────────────────────────────┘    │
│                                │ WebSocket                                    │
│                                ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                      AGENT HOST BACKEND                                  │ │
│  │                      (Relays events, may involve LLM)                    │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────┘
```

### 12.2 Communication Modes

IFRAME widgets support two communication architectures:

#### Mode 1: Relay (Recommended)

The IFRAME content communicates with the Agent Host frontend via `postMessage`, and the frontend relays relevant events to/from the backend over WebSocket.

```
IFRAME ◄──postMessage──► Frontend ◄──WebSocket──► Backend
```

**Advantages:**

- Single WebSocket connection (simpler)
- Frontend can filter/validate messages
- Backend remains stateless regarding iframe internals
- Works with sandboxed iframes

#### Mode 2: Independent

The IFRAME opens its own WebSocket connection directly to the Agent Host backend (or its own backend). The frontend only handles positioning/visibility.

```
IFRAME ◄──WebSocket──► Backend (direct)
Frontend ◄──WebSocket──► Backend (conversation)
```

**Advantages:**

- IFRAME has full control of its protocol
- No message relay overhead
- Suitable for complex real-time applications

### 12.3 Widget Configuration

**`data.widget.render`** for IFRAME type:

```json
{
  "type": "data.widget.render",
  "payload": {
    "itemId": "item_sim_1",
    "widgetId": "widget_iframe_sim",
    "widgetType": "iframe",
    "stem": "Complete the circuit simulation:",
    "config": {
      "src": "https://simulations.example.com/circuits/basic",
      "communicationMode": "relay",
      "sandbox": ["allow-scripts", "allow-same-origin"],
      "allow": ["fullscreen"],
      "loading": "lazy",
      "dimensions": {
        "width": 800,
        "height": 600,
        "aspectRatio": "4:3"
      },
      "initParams": {
        "circuitId": "circuit_123",
        "difficulty": "medium",
        "userId": "${userId}",
        "sessionToken": "${sessionToken}"
      },
      "messageOrigin": "https://simulations.example.com",
      "timeout": 30000,
      "fallbackContent": "<p>Simulation unavailable. <a href='...'>Try alternative</a></p>"
    },
    "required": true,
    "layout": {
      "mode": "canvas",
      "position": { "x": 100, "y": 200 }
    },
    "constraints": {
      "resizable": true,
      "dismissable": false
    }
  }
}
```

**Configuration Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `src` | `string` | URL of iframe content |
| `communicationMode` | `"relay" \| "independent"` | How iframe communicates |
| `sandbox` | `string[]` | Sandbox permissions |
| `allow` | `string[]` | Feature policy permissions |
| `loading` | `"eager" \| "lazy"` | Loading strategy |
| `dimensions` | `object` | Size configuration |
| `initParams` | `object` | Parameters passed to iframe on load |
| `messageOrigin` | `string` | Expected origin for postMessage |
| `timeout` | `number?` | Milliseconds to wait for iframe ready |
| `fallbackContent` | `string?` | HTML to show if iframe fails |

**Sandbox Permissions:**

| Permission | Description |
|------------|-------------|
| `allow-scripts` | Enable JavaScript |
| `allow-same-origin` | Treat as same origin |
| `allow-forms` | Allow form submission |
| `allow-popups` | Allow popups |
| `allow-modals` | Allow modal dialogs |

### 12.4 IFRAME ↔ Frontend Communication (Relay Mode)

#### 12.4.1 IFRAME → Frontend

The IFRAME sends messages to the parent window using `postMessage`:

```javascript
// Inside IFRAME content
window.parent.postMessage({
  type: 'agentHost.iframe.event',
  payload: {
    eventType: 'simulation_complete',
    data: {
      score: 85,
      completionTime: 120,
      attempts: 3
    }
  }
}, 'https://agenthost.example.com');
```

#### 12.4.2 Frontend → IFRAME

The frontend sends messages to the iframe's contentWindow:

```javascript
// Agent Host frontend
iframeElement.contentWindow.postMessage({
  type: 'agentHost.iframe.command',
  payload: {
    command: 'reset',
    params: { difficulty: 'hard' }
  }
}, 'https://simulations.example.com');
```

### 12.5 Protocol Messages

**`data.iframe.event`** (Client → Server)

Frontend relays significant events from IFRAME to backend.

```json
{
  "type": "data.iframe.event",
  "payload": {
    "widgetId": "widget_iframe_sim",
    "eventType": "simulation_complete",
    "data": {
      "score": 85,
      "completionTime": 120,
      "attempts": 3,
      "correctConnections": ["a-b", "c-d"],
      "incorrectConnections": ["e-f"]
    },
    "timestamp": "2025-12-18T10:35:00.000Z"
  }
}
```

**Standard Event Types:**

| Event Type | Description |
|------------|-------------|
| `ready` | IFRAME content loaded and ready |
| `progress` | Progress update (partial completion) |
| `complete` | Activity completed |
| `error` | Error occurred |
| `interaction` | User interacted (for analytics) |
| `state_change` | Internal state changed |
| `request_hint` | User requested help |
| `timeout` | Activity timed out internally |

---

**`data.iframe.command`** (Server → Client)

Backend sends command to be relayed to IFRAME.

```json
{
  "type": "data.iframe.command",
  "payload": {
    "widgetId": "widget_iframe_sim",
    "command": "provide_hint",
    "params": {
      "hintLevel": 2,
      "component": "resistor_placement"
    }
  }
}
```

**Standard Commands:**

| Command | Description |
|---------|-------------|
| `reset` | Reset to initial state |
| `start` | Start/resume activity |
| `pause` | Pause activity |
| `resume` | Resume paused activity |
| `provide_hint` | Display a hint |
| `set_difficulty` | Change difficulty |
| `skip` | Skip to completion |
| `update_config` | Update configuration |
| `focus_element` | Focus on specific element |
| `evaluate` | Trigger evaluation |

---

**`data.iframe.state`** (Both Directions)

Sync state between IFRAME and backend.

```json
{
  "type": "data.iframe.state",
  "payload": {
    "widgetId": "widget_iframe_sim",
    "state": {
      "currentStep": 3,
      "totalSteps": 5,
      "score": 60,
      "elements": {
        "resistor1": { "placed": true, "correct": true },
        "resistor2": { "placed": false }
      }
    },
    "stateVersion": 12
  }
}
```

---

**`control.iframe.resize`** (Server → Client)

Request IFRAME size change.

```json
{
  "type": "control.iframe.resize",
  "payload": {
    "widgetId": "widget_iframe_sim",
    "dimensions": { "width": 1024, "height": 768 },
    "animate": true
  }
}
```

---

**`control.iframe.navigate`** (Server → Client)

Navigate IFRAME to different content.

```json
{
  "type": "control.iframe.navigate",
  "payload": {
    "widgetId": "widget_iframe_sim",
    "src": "https://simulations.example.com/circuits/advanced",
    "preserveState": false
  }
}
```

### 12.6 IFRAME Response Format

When IFRAME activities complete, the result is captured via `data.response.submit`:

```json
{
  "type": "data.response.submit",
  "payload": {
    "widgetId": "widget_iframe_sim",
    "value": {
      "type": "iframe_result",
      "eventType": "complete",
      "data": {
        "score": 85,
        "maxScore": 100,
        "completionTime": 120,
        "attempts": 3,
        "details": {
          "correctConnections": 8,
          "incorrectConnections": 1,
          "hintsUsed": 2
        }
      }
    },
    "submittedAt": "2025-12-18T10:35:00.000Z"
  }
}
```

### 12.7 Initialization Sequence

```
Frontend                      IFRAME                      Backend
    │                           │                            │
    │── Load iframe (src) ─────►│                            │
    │                           │                            │
    │◄── postMessage(ready) ────│                            │
    │                           │                            │
    │── data.iframe.event ────────────────────────────────────►│
    │   {eventType: "ready"}    │                            │
    │                           │                            │
    │◄── data.iframe.command ─────────────────────────────────│
    │   {command: "start"}      │                            │
    │                           │                            │
    │── postMessage(start) ────►│                            │
    │                           │                            │
    │                           │   [User interaction]       │
    │                           │                            │
    │◄── postMessage(progress) ─│                            │
    │                           │                            │
    │── data.iframe.event ────────────────────────────────────►│
    │   {eventType: "progress"} │                            │
    │                           │                            │
    │                           │   [Completion]             │
    │                           │                            │
    │◄── postMessage(complete) ─│                            │
    │                           │                            │
    │── data.response.submit ─────────────────────────────────►│
    │   {value: iframe_result}  │                            │
    │                           │                            │
```

### 12.8 Security Considerations

#### Content Security Policy

The Agent Host should set appropriate CSP headers:

```
Content-Security-Policy: frame-src https://simulations.example.com https://trusted-iframes.example.com;
```

#### Origin Validation

Always validate `postMessage` origins:

```javascript
// Frontend handler
window.addEventListener('message', (event) => {
  if (event.origin !== widget.config.messageOrigin) {
    console.warn('Rejected message from unknown origin:', event.origin);
    return;
  }
  // Process message
});
```

#### Sandbox Recommendations

| Use Case | Recommended Sandbox |
|----------|---------------------|
| Read-only content | `allow-scripts` |
| Interactive game | `allow-scripts allow-same-origin` |
| Form submission | `allow-scripts allow-forms` |
| Full application | `allow-scripts allow-same-origin allow-forms allow-popups` |

### 12.9 Error Handling

**`data.iframe.error`** (Client → Server)

Report iframe errors to backend.

```json
{
  "type": "data.iframe.error",
  "payload": {
    "widgetId": "widget_iframe_sim",
    "errorType": "load_failed",
    "message": "Failed to load iframe content",
    "details": {
      "src": "https://simulations.example.com/circuits/basic",
      "status": 404
    }
  }
}
```

**Error Types:**

| Error Type | Description |
|------------|-------------|
| `load_failed` | Failed to load iframe src |
| `timeout` | Iframe didn't respond to ready check |
| `sandbox_blocked` | Action blocked by sandbox |
| `origin_mismatch` | postMessage from unexpected origin |
| `communication_error` | Message format error |
| `content_error` | Error from iframe content |

---

## 13. Implementation Notes

### 13.1 Frontend Implementation

```typescript
// Event bus pattern for control signals
class ProtocolEventBus {
  private handlers: Map<string, Set<Handler>> = new Map();

  on(type: string, handler: Handler): void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler);
  }

  emit(message: ProtocolMessage): void {
    const handlers = this.handlers.get(message.type);
    if (handlers) {
      handlers.forEach(h => h(message.payload));
    } else {
      console.log(`[PROTOCOL] Unknown message type: ${message.type}`);
    }
  }
}

// WebSocket handler
class WebSocketHandler {
  private bus: ProtocolEventBus;
  private socket: WebSocket;

  handleMessage(event: MessageEvent): void {
    const message = JSON.parse(event.data);
    this.bus.emit(message);
  }

  send(type: string, payload: any): void {
    const message = {
      id: generateId(),
      type,
      version: "1.0",
      timestamp: new Date().toISOString(),
      source: "client",
      conversationId: this.conversationId,
      payload
    };
    this.socket.send(JSON.stringify(message));
  }
}
```

### 13.2 Backend Implementation

```python
# Protocol message envelope
@dataclass
class ProtocolMessage:
    id: str
    type: str
    version: str
    timestamp: str
    source: str
    conversation_id: str | None
    payload: dict[str, Any]

    @classmethod
    def create(cls, type: str, payload: dict, conversation_id: str | None = None):
        return cls(
            id=str(uuid4()),
            type=type,
            version="1.0",
            timestamp=datetime.now(UTC).isoformat(),
            source="server",
            conversation_id=conversation_id,
            payload=payload
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self))


# WebSocket handler
async def handle_websocket(websocket: WebSocket, conversation: Conversation):
    await websocket.accept()

    # Send connection established
    await send_message(websocket, ProtocolMessage.create(
        type="system.connection.established",
        payload={
            "connectionId": str(uuid4()),
            "conversationId": conversation.id(),
            "userId": user_id,
            "serverTime": datetime.now(UTC).isoformat()
        }
    ))

    # Message loop
    async for raw in websocket.iter_text():
        message = ProtocolMessage(**json.loads(raw))
        await dispatch_message(message, conversation, websocket)
```

### 13.3 Migration from SSE

| SSE Event | WebSocket Equivalent |
|-----------|---------------------|
| `stream_started` | `system.connection.established` |
| `content_chunk` | `data.content.chunk` |
| `message_complete` | `data.content.complete` |
| `tool_call` | `data.tool.call` |
| `tool_result` | `data.tool.result` |
| `client_action` | `data.widget.render` |
| `template_config` | `control.conversation.config` |
| `template_progress` | `control.item.context` |
| `stream_complete` | `control.item.context` (next item) |
| `error` | `system.error` |

### 13.4 Testing Protocol Compliance

```python
# Protocol message validator
def validate_message(message: dict) -> bool:
    required_fields = ["id", "type", "version", "timestamp", "source", "payload"]

    for field in required_fields:
        if field not in message:
            raise ProtocolError(f"Missing required field: {field}")

    if not message["type"].count(".") >= 2:
        raise ProtocolError(f"Invalid type format: {message['type']}")

    if message["version"] not in SUPPORTED_VERSIONS:
        raise ProtocolError(f"Unsupported version: {message['version']}")

    return True
```

---

## Appendix A: Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-18 | Initial specification |

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Control Plane** | Messages managing UI state and conversation flow |
| **Data Plane** | Messages carrying content and user responses |
| **Widget** | Interactive UI component for structured input |
| **Item** | A step in a template-based conversation |
| **Template** | Structured conversation definition with items |
| **Envelope** | Standard message wrapper with metadata |

---

## Appendix C: Related Documents

- [Agent Host Architecture](../architecture/agent-host-architecture.md)
- [Conversation Flows](../architecture/conversation-flows.md)
- [Simplified Architecture v3](simplified-architecture-v3.md)
