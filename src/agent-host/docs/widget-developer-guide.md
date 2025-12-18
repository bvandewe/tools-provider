# Widget Developer Guide

This guide explains how to create and use interactive widgets in the Agent Host application.

## Overview

The Agent Host supports **proactive sessions** where the AI agent can request client-side input through interactive widgets. This enables:

- Multiple choice questions
- Free text input prompts
- Code editors for programming exercises

## Architecture

The Agent Host uses **dual streaming transports** for widget delivery:

| Transport | Handler | Use Case |
|-----------|---------|----------|
| **SSE** | `stream-handler.js` | Reactive chat with `client_action` events |
| **WebSocket** | `websocket-handler.js` | Proactive templates with `widget` messages |

```
ProactiveAgent
    ↓ (tool call or template)
ChatService
    ↓ (WebSocket message or SSE event)
Frontend Handler
    ↓ (renders)
Web Component (widget)
    ↓ (user interaction)
ClientResponse
    ↓ (WebSocket message or API call)
ChatService
```

## Client Tools

Client tools are special tool definitions that are intercepted before reaching the LLM and rendered as widgets on the client side.

### Defining a Client Tool

```python
from application.agents.client_tools import (
    ClientToolDefinition,
    is_client_tool,
    WidgetType,
)

MY_WIDGET_TOOL = ClientToolDefinition(
    name="my_widget",
    description="Renders a custom widget for user input",
    widget_type=WidgetType.FREE_TEXT,
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "placeholder": {"type": "string"},
        },
        "required": ["prompt"],
    },
)
```

### Built-in Client Tools

| Tool | Widget Type | Purpose |
|------|-------------|---------|
| `present_choices` | `multiple_choice` | Multiple choice questions |
| `request_free_text` | `free_text` | Open text input |
| `present_code_editor` | `code_editor` | Code input with syntax highlighting |

## Frontend Widgets

Widgets are implemented as Web Components using shadow DOM for encapsulation.

### Widget Component Structure

```javascript
// ui/src/scripts/components/ax-my-widget.js
export class AxMyWidget extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    static get observedAttributes() {
        return ['action-id', 'prompt', 'other-props'];
    }

    connectedCallback() {
        this.render();
        this.setupEventListeners();
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                /* Component styles */
            </style>
            <div class="widget-container">
                <label>${this.getAttribute('prompt')}</label>
                <!-- Widget content -->
                <button type="submit">Submit</button>
            </div>
        `;
    }

    handleSubmit(response) {
        this.dispatchEvent(new CustomEvent('widget-response', {
            bubbles: true,
            composed: true,
            detail: {
                actionId: this.getAttribute('action-id'),
                response: response,
            }
        }));
    }
}

customElements.define('ax-my-widget', AxMyWidget);
```

### Widget Events

Widgets must dispatch a `widget-response` event with:

```javascript
{
    bubbles: true,
    composed: true,  // Crosses shadow DOM boundary
    detail: {
        actionId: string,   // From action-id attribute
        response: object,   // User's response data
    }
}
```

## Backend Events

The backend delivers widgets via **two transports**:

### SSE Events (Reactive Chat via `stream-handler.js`)

#### `client_action` Event

Triggers widget display in reactive chat:

```json
{
    "event": "client_action",
    "data": {
        "action_type": "widget",
        "widget_type": "multiple_choice",
        "content_id": "uuid-here",
        "item_id": "uuid-here",
        "stem": "What is 2 + 2?",
        "options": ["3", "4", "5", "6"],
        "required": true
    }
}
```

### WebSocket Messages (Proactive Templates via `websocket-handler.js`)

#### `widget` Message

Triggers widget display in proactive template flows:

```json
{
    "type": "widget",
    "data": {
        "widget_type": "multiple_choice",
        "content_id": "uuid-here",
        "item_id": "uuid-here",
        "stem": "What is 2 + 2?",
        "options": ["3", "4", "5", "6"],
        "required": true,
        "skippable": false,
        "show_user_response": true
    }
}
```

#### `progress` Message

Template progression update:

```json
{
    "type": "progress",
    "data": {
        "current_item": 2,
        "total_items": 5,
        "item_title": "Question 3"
    }
}
```

## Adding a New Widget

### 1. Define the Client Tool

In `application/agents/client_tools.py`:

```python
MY_NEW_TOOL = ClientToolDefinition(
    name="my_new_widget",
    description="Description for LLM",
    widget_type=WidgetType.MY_NEW_TYPE,  # Add to WidgetType enum
    parameters={...},
)

# Add to ALL_CLIENT_TOOLS list
ALL_CLIENT_TOOLS.append(MY_NEW_TOOL)
```

### 2. Create the Web Component

In `ui/src/scripts/components/ax-my-new-widget.js`:

```javascript
export class AxMyNewWidget extends HTMLElement {
    // Implementation
}
customElements.define('ax-my-new-widget', AxMyNewWidget);
```

### 3. Register in Main

In `ui/src/scripts/main.js`:

```javascript
import './components/ax-my-new-widget.js';
```

### 4. Update Both Frontend Handlers

**For SSE (reactive chat)** - In `ui/src/scripts/core/stream-handler.js`:

Handle the `client_action` SSE event for your widget type.

**For WebSocket (proactive templates)** - In `ui/src/scripts/core/websocket-handler.js`:

Handle the `widget` WebSocket message for your widget type.

**Shared rendering** - In `ui/src/scripts/core/message-renderer.js`, add to `showClientActionWidget()`:

```javascript
case 'my_new_type':
    html = `<ax-my-new-widget
        action-id="${actionId}"
        ${propsToAttributes(props)}
    ></ax-my-new-widget>`;
    break;
```

### 5. Add Tests

Add unit tests for the client tool in `tests/application/test_client_tools.py`.

## Best Practices

### Widget Design

1. **Accessibility**: Include ARIA attributes, keyboard navigation
2. **Focus Management**: Auto-focus primary input on display
3. **Validation**: Validate input before allowing submission
4. **Loading States**: Show spinner during submission
5. **Error Handling**: Display errors gracefully

### Tool Definition

1. **Clear Descriptions**: LLM uses description to decide when to use tool
2. **Parameter Validation**: Use JSON Schema for parameter validation
3. **Sensible Defaults**: Provide defaults for optional parameters

### Testing

1. **Unit Tests**: Test tool definition and parameter extraction
2. **Component Tests**: Test widget rendering and interactions
3. **E2E Tests**: Test complete flow from agent to widget to response

## Example: Rating Widget

Here's a complete example of adding a star rating widget:

### Backend (client_tools.py)

```python
RATING_TOOL = ClientToolDefinition(
    name="request_rating",
    description="Request a star rating from 1-5 from the user",
    widget_type=WidgetType.RATING,
    parameters={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Question to ask user",
            },
            "max_stars": {
                "type": "integer",
                "default": 5,
            },
        },
        "required": ["prompt"],
    },
)
```

### Frontend (ax-rating-widget.js)

```javascript
export class AxRatingWidget extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.selectedRating = 0;
    }

    connectedCallback() {
        const maxStars = parseInt(this.getAttribute('max-stars') || '5');

        this.shadowRoot.innerHTML = `
            <style>
                .stars { display: flex; gap: 4px; }
                .star {
                    font-size: 24px;
                    cursor: pointer;
                    color: #ccc;
                }
                .star.selected { color: gold; }
            </style>
            <div class="rating-widget">
                <label>${this.getAttribute('prompt')}</label>
                <div class="stars" role="radiogroup">
                    ${Array(maxStars).fill().map((_, i) => `
                        <span class="star" data-value="${i + 1}"
                              role="radio" tabindex="0">★</span>
                    `).join('')}
                </div>
                <button type="submit" disabled>Submit</button>
            </div>
        `;

        this.shadowRoot.querySelectorAll('.star').forEach(star => {
            star.addEventListener('click', () => this.selectRating(star));
            star.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this.selectRating(star);
            });
        });

        this.shadowRoot.querySelector('button').addEventListener('click',
            () => this.submit());
    }

    selectRating(star) {
        this.selectedRating = parseInt(star.dataset.value);
        this.shadowRoot.querySelectorAll('.star').forEach((s, i) => {
            s.classList.toggle('selected', i < this.selectedRating);
        });
        this.shadowRoot.querySelector('button').disabled = false;
    }

    submit() {
        this.dispatchEvent(new CustomEvent('widget-response', {
            bubbles: true,
            composed: true,
            detail: {
                actionId: this.getAttribute('action-id'),
                response: { rating: this.selectedRating }
            }
        }));
    }
}

customElements.define('ax-rating-widget', AxRatingWidget);
```

## Debugging

### Backend Logging

```python
import logging
logger = logging.getLogger(__name__)

# In ChatService
logger.debug(f"Emitting widget: {widget_type}, content_id: {content_id}")
```

### Frontend Debugging

```javascript
// In stream-handler.js (SSE)
console.debug('[StreamHandler] Received event:', eventType, data);

// In websocket-handler.js (WebSocket)
console.debug('[WebSocket] Received:', data.type, data);

// In widget
console.debug('Widget initialized:', this.getAttribute('action-id'));
```

### Testing SSE Events

Use browser DevTools Network tab, filter by Fetch/XHR to see SSE streaming responses.

### Testing WebSocket

Use browser DevTools Network tab, filter by WS to see WebSocket frames.

```javascript
// Console test for WebSocket
const ws = new WebSocket('ws://localhost:8001/api/chat/ws?definition_id=YOUR_ID');
ws.onmessage = e => console.log(JSON.parse(e.data));
ws.onopen = () => ws.send(JSON.stringify({type: 'start'}));
```

## Troubleshooting

### Widget Not Appearing

1. Check browser console for JavaScript errors
2. Verify widget component is imported in main.js
3. Check SSE connection in Network tab
4. Verify action_id matches between event and widget

### Response Not Received

1. Verify `widget-response` event has `composed: true`
2. Check stream-handler is listening for widget-response
3. Verify API endpoint for response submission

### Session Not Resuming

1. Check backend logs for resume errors
2. Verify action_id in response matches suspended action
3. Check session hasn't timed out
