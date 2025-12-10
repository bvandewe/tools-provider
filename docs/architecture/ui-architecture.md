# UI Architecture

**Version:** 1.0.0
**Status:** `DRAFT`
**Date:** December 10, 2025

---

## 1. Overview

Project AX uses a VanillaJS WebComponents architecture with an infinite canvas as the primary interaction surface. No frameworks (React, Vue, Angular) are used.

### 1.1 Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **UI Framework** | VanillaJS | No framework overhead |
| **Components** | Web Components (Custom Elements) | Native browser standard |
| **Canvas** | HTML5 Canvas / SVG hybrid | Infinite workspace |
| **State** | Custom Event Bus | Decoupled communication |
| **Streaming** | EventSource (SSE) | Real-time agent messages |

### 1.2 Design Principles

1. **Framework-Free**: Native browser APIs only
2. **Component Isolation**: Shadow DOM for encapsulation
3. **Spatial Interface**: Canvas-based, not page-based
4. **Agent-Driven UI**: Components respond to agent commands
5. **Accessibility**: ARIA support in all components

---

## 2. Canvas Architecture

### 2.1 Infinite Canvas Concept

```
┌─────────────────────────────────────────────┐
│  VIEWPORT (browser window)                  │
│  ┌───────────────────────────────────────┐  │
│  │                                       │  │
│  │    ┌─────────┐        ┌─────────┐     │  │
│  │    │ Session │        │ Session │     │  │
│  │    │  Card   │        │  Card   │     │  │
│  │    └─────────┘        └─────────┘     │  │
│  │                                       │  │
│  │              ┌─────────────────┐      │  │
│  │              │  Active Agent   │      │  │
│  │              │     Panel       │      │  │
│  │              └─────────────────┘      │  │
│  │                                       │  │
│  └───────────────────────────────────────┘  │
│                        ↕ Pan ↔ Zoom         │
│  WORLD (infinite coordinate space)          │
└─────────────────────────────────────────────┘
```

### 2.2 Canvas Manager

```javascript
// core/canvas-manager.js
class CanvasManager extends HTMLElement {
  #viewport = { x: 0, y: 0, zoom: 1 };
  #widgets = new Map();

  // Transform world coordinates to screen
  worldToScreen(worldX, worldY) {
    return {
      x: (worldX - this.#viewport.x) * this.#viewport.zoom,
      y: (worldY - this.#viewport.y) * this.#viewport.zoom
    };
  }

  // Handle pan (drag canvas)
  pan(deltaX, deltaY) {
    this.#viewport.x -= deltaX / this.#viewport.zoom;
    this.#viewport.y -= deltaY / this.#viewport.zoom;
    this.#updateTransform();
  }

  // Handle zoom (mouse wheel)
  zoom(delta, centerX, centerY) {
    const factor = delta > 0 ? 1.1 : 0.9;
    const newZoom = Math.max(0.1, Math.min(5, this.#viewport.zoom * factor));
    // Zoom toward cursor position
    this.#viewport.x += (centerX / this.#viewport.zoom - centerX / newZoom);
    this.#viewport.y += (centerY / this.#viewport.zoom - centerY / newZoom);
    this.#viewport.zoom = newZoom;
    this.#updateTransform();
  }

  // Add widget at world position
  addWidget(widget, worldX, worldY) {
    widget.dataset.worldX = worldX;
    widget.dataset.worldY = worldY;
    this.#widgets.set(widget.id, widget);
    this.shadowRoot.querySelector('.canvas-layer').appendChild(widget);
    this.#positionWidget(widget);
  }
}

customElements.define('ax-canvas', CanvasManager);
```

### 2.3 Gesture Support

```yaml
gestures:
  pan:
    mouse: "Middle-click drag OR Space + Left-click drag"
    touch: "Two-finger drag"

  zoom:
    mouse: "Ctrl + Mouse wheel"
    touch: "Pinch gesture"
    keyboard: "Ctrl + Plus/Minus"

  select:
    mouse: "Left-click"
    touch: "Tap"

  drag_widget:
    mouse: "Left-click drag on widget header"
    touch: "Long-press then drag"

  context_menu:
    mouse: "Right-click"
    touch: "Long-press"
```

---

## 3. Component Hierarchy

### 3.1 Component Tree

```
ax-app (root)
├── ax-toolbar
│   ├── ax-session-selector
│   ├── ax-zoom-controls
│   └── ax-user-menu
├── ax-canvas
│   ├── ax-session-card (multiple)
│   │   ├── ax-card-header
│   │   └── ax-card-content
│   ├── ax-agent-panel
│   │   ├── ax-message-stream
│   │   ├── ax-client-action-slot
│   │   └── ax-chat-input
│   └── ax-connection-lines (SVG overlay)
├── ax-sidebar
│   ├── ax-track-browser
│   └── ax-session-history
└── ax-notification-toast
```

### 3.2 Base Component Class

```javascript
// core/base-component.js
class AXComponent extends HTMLElement {
  static observedAttributes = [];

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this.render();
    this.setupEventListeners();
  }

  disconnectedCallback() {
    this.cleanup();
  }

  // Override in subclasses
  render() {}
  setupEventListeners() {}
  cleanup() {}

  // Utility: emit custom event
  emit(eventName, detail) {
    this.dispatchEvent(new CustomEvent(eventName, {
      bubbles: true,
      composed: true,  // Cross shadow DOM
      detail
    }));
  }

  // Utility: subscribe to event bus
  subscribe(eventName, handler) {
    window.axEventBus.on(eventName, handler);
    this._subscriptions = this._subscriptions || [];
    this._subscriptions.push({ eventName, handler });
  }
}
```

---

## 4. Agentic UI Components

### 4.1 Client Action Renderer

The key component that renders UI based on agent `client_action` events.

```javascript
// components/client-action-renderer.js
class ClientActionRenderer extends AXComponent {
  static COMPONENT_MAP = {
    'multiple_choice': 'ax-multiple-choice',
    'free_text': 'ax-free-text-prompt',
    'code_editor': 'ax-code-editor',
    'diagram': 'ax-diagram-viewer',
    'rating_scale': 'ax-rating-scale'
  };

  renderAction(actionPayload) {
    const { component, props, tool_call_id } = actionPayload;
    const tagName = ClientActionRenderer.COMPONENT_MAP[component];

    if (!tagName) {
      console.error(`Unknown component: ${component}`);
      return;
    }

    // Clear previous action
    this.shadowRoot.innerHTML = '';

    // Create component
    const element = document.createElement(tagName);
    element.dataset.toolCallId = tool_call_id;
    Object.assign(element, props);

    // Listen for response
    element.addEventListener('ax-response', (e) => {
      this.emit('client-action-response', {
        tool_call_id,
        result: e.detail
      });
    });

    this.shadowRoot.appendChild(element);

    // Lock/unlock chat input based on props
    if (props.lock_input) {
      this.emit('lock-chat-input', { locked: true });
    }
  }

  clear() {
    this.shadowRoot.innerHTML = '';
    this.emit('lock-chat-input', { locked: false });
  }
}

customElements.define('ax-client-action-renderer', ClientActionRenderer);
```

### 4.2 Multiple Choice Component

```javascript
// components/multiple-choice.js
class MultipleChoice extends AXComponent {
  static observedAttributes = ['question', 'options', 'allow-bypass'];

  render() {
    const options = JSON.parse(this.getAttribute('options') || '[]');
    const question = this.getAttribute('question');

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; padding: 1rem; }
        .question { font-weight: 600; margin-bottom: 1rem; }
        .options { display: flex; flex-direction: column; gap: 0.5rem; }
        .option-btn {
          padding: 0.75rem 1rem;
          border: 2px solid var(--ax-border);
          border-radius: 8px;
          background: var(--ax-surface);
          cursor: pointer;
          text-align: left;
          transition: all 0.2s;
        }
        .option-btn:hover { border-color: var(--ax-primary); }
        .option-btn.selected {
          border-color: var(--ax-primary);
          background: var(--ax-primary-light);
        }
      </style>
      <div class="question">${question}</div>
      <div class="options">
        ${options.map((opt, i) => `
          <button class="option-btn" data-index="${i}" data-value="${opt}">
            ${String.fromCharCode(65 + i)}. ${opt}
          </button>
        `).join('')}
      </div>
    `;
  }

  setupEventListeners() {
    this.shadowRoot.querySelectorAll('.option-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        // Visual feedback
        this.shadowRoot.querySelectorAll('.option-btn').forEach(b =>
          b.classList.remove('selected'));
        btn.classList.add('selected');

        // Emit response
        this.emit('ax-response', {
          selection: btn.dataset.value,
          index: parseInt(btn.dataset.index)
        });
      });
    });
  }
}

customElements.define('ax-multiple-choice', MultipleChoice);
```

### 4.3 Free Text Prompt Component

```javascript
// components/free-text-prompt.js
class FreeTextPrompt extends AXComponent {
  render() {
    const prompt = this.getAttribute('prompt');
    const minLength = parseInt(this.getAttribute('min-length') || '0');
    const placeholder = this.getAttribute('placeholder') || 'Type your response...';

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; padding: 1rem; }
        .prompt { font-weight: 600; margin-bottom: 1rem; }
        textarea {
          width: 100%;
          min-height: 120px;
          padding: 0.75rem;
          border: 2px solid var(--ax-border);
          border-radius: 8px;
          resize: vertical;
        }
        .submit-btn {
          margin-top: 0.5rem;
          padding: 0.5rem 1rem;
          background: var(--ax-primary);
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
        }
        .submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .char-count { font-size: 0.875rem; color: var(--ax-muted); }
      </style>
      <div class="prompt">${prompt}</div>
      <textarea placeholder="${placeholder}"></textarea>
      <div class="footer">
        <span class="char-count">0 / ${minLength} min characters</span>
        <button class="submit-btn" disabled>Submit</button>
      </div>
    `;
  }

  setupEventListeners() {
    const textarea = this.shadowRoot.querySelector('textarea');
    const submitBtn = this.shadowRoot.querySelector('.submit-btn');
    const charCount = this.shadowRoot.querySelector('.char-count');
    const minLength = parseInt(this.getAttribute('min-length') || '0');

    textarea.addEventListener('input', () => {
      const len = textarea.value.length;
      charCount.textContent = `${len} / ${minLength} min characters`;
      submitBtn.disabled = len < minLength;
    });

    submitBtn.addEventListener('click', () => {
      this.emit('ax-response', { text: textarea.value });
    });
  }
}

customElements.define('ax-free-text-prompt', FreeTextPrompt);
```

---

## 5. SSE Stream Handler

### 5.1 Event Source Manager

```javascript
// core/stream-manager.js
class StreamManager {
  #eventSource = null;
  #conversationId = null;
  #handlers = new Map();

  connect(conversationId, authToken) {
    this.#conversationId = conversationId;
    const url = `/api/v1/conversations/${conversationId}/stream`;

    this.#eventSource = new EventSource(url, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    // Standard SSE events
    this.#eventSource.onopen = () => this.#emit('connected');
    this.#eventSource.onerror = (e) => this.#emit('error', e);

    // Custom event types
    this.#eventSource.addEventListener('content', (e) => {
      const data = JSON.parse(e.data);
      this.#emit('content', data);
    });

    this.#eventSource.addEventListener('client_action', (e) => {
      const data = JSON.parse(e.data);
      this.#emit('client_action', data);
    });

    this.#eventSource.addEventListener('tool_result', (e) => {
      const data = JSON.parse(e.data);
      this.#emit('tool_result', data);
    });

    this.#eventSource.addEventListener('state', (e) => {
      const data = JSON.parse(e.data);
      this.#emit('state', data);
    });

    this.#eventSource.addEventListener('done', () => {
      this.#emit('done');
    });
  }

  disconnect() {
    if (this.#eventSource) {
      this.#eventSource.close();
      this.#eventSource = null;
    }
  }

  on(event, handler) {
    if (!this.#handlers.has(event)) {
      this.#handlers.set(event, new Set());
    }
    this.#handlers.get(event).add(handler);
  }

  off(event, handler) {
    this.#handlers.get(event)?.delete(handler);
  }

  #emit(event, data) {
    this.#handlers.get(event)?.forEach(h => h(data));
  }
}

// Singleton
window.axStreamManager = new StreamManager();
```

### 5.2 Agent Panel Integration

```javascript
// components/agent-panel.js
class AgentPanel extends AXComponent {
  #streamManager = window.axStreamManager;

  connectedCallback() {
    super.connectedCallback();
    this.#setupStreamHandlers();
  }

  #setupStreamHandlers() {
    this.#streamManager.on('content', (data) => {
      this.#appendContent(data.content, data.finished);
    });

    this.#streamManager.on('client_action', (data) => {
      this.#renderClientAction(data);
    });

    this.#streamManager.on('state', (data) => {
      this.#updateState(data.state);
      if (data.pending_action) {
        this.#renderClientAction(data.pending_action);
      }
    });
  }

  #appendContent(content, finished) {
    const messageStream = this.shadowRoot.querySelector('ax-message-stream');
    messageStream.appendToCurrentMessage(content);
    if (finished) {
      messageStream.finalizeCurrentMessage();
    }
  }

  #renderClientAction(actionData) {
    const renderer = this.shadowRoot.querySelector('ax-client-action-renderer');
    renderer.renderAction(actionData);
  }

  #updateState(state) {
    this.dataset.state = state;
    const chatInput = this.shadowRoot.querySelector('ax-chat-input');
    chatInput.disabled = (state === 'generating' || state === 'awaiting_client_action');
  }
}

customElements.define('ax-agent-panel', AgentPanel);
```

---

## 6. Session Cards

### 6.1 Session Card Widget

```javascript
// components/session-card.js
class SessionCard extends AXComponent {
  static observedAttributes = ['session-id', 'session-type', 'title', 'status'];

  render() {
    const type = this.getAttribute('session-type');
    const title = this.getAttribute('title');
    const status = this.getAttribute('status');

    const iconMap = {
      'thought': '💭',
      'learning': '📚',
      'validation': '✅'
    };

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          width: 280px;
          background: var(--ax-surface);
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
          overflow: hidden;
        }
        .header {
          padding: 0.75rem 1rem;
          background: var(--ax-${type}-color, var(--ax-primary));
          color: white;
          cursor: grab;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        .header:active { cursor: grabbing; }
        .content { padding: 1rem; }
        .status {
          font-size: 0.75rem;
          padding: 0.25rem 0.5rem;
          background: var(--ax-status-${status});
          border-radius: 4px;
        }
        .actions { display: flex; gap: 0.5rem; margin-top: 0.75rem; }
        .action-btn {
          flex: 1;
          padding: 0.5rem;
          border: 1px solid var(--ax-border);
          border-radius: 6px;
          background: transparent;
          cursor: pointer;
        }
      </style>
      <div class="header" draggable="true">
        <span class="icon">${iconMap[type]}</span>
        <span class="title">${title}</span>
      </div>
      <div class="content">
        <span class="status">${status}</span>
        <div class="actions">
          <button class="action-btn" data-action="open">Open</button>
          <button class="action-btn" data-action="details">Details</button>
        </div>
      </div>
    `;
  }

  setupEventListeners() {
    const header = this.shadowRoot.querySelector('.header');

    header.addEventListener('dragstart', (e) => {
      e.dataTransfer.setData('text/plain', this.getAttribute('session-id'));
      this.emit('widget-drag-start', { widget: this });
    });

    this.shadowRoot.querySelectorAll('.action-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.emit('session-action', {
          sessionId: this.getAttribute('session-id'),
          action: btn.dataset.action
        });
      });
    });
  }
}

customElements.define('ax-session-card', SessionCard);
```

---

## 7. State Management

### 7.1 Event Bus

```javascript
// core/event-bus.js
class EventBus {
  #handlers = new Map();

  on(event, handler) {
    if (!this.#handlers.has(event)) {
      this.#handlers.set(event, new Set());
    }
    this.#handlers.get(event).add(handler);
    return () => this.off(event, handler);
  }

  off(event, handler) {
    this.#handlers.get(event)?.delete(handler);
  }

  emit(event, data) {
    this.#handlers.get(event)?.forEach(h => h(data));
    // Also emit to '*' wildcard subscribers
    this.#handlers.get('*')?.forEach(h => h({ event, data }));
  }
}

window.axEventBus = new EventBus();
```

### 7.2 Application State

```javascript
// core/app-state.js
class AppState {
  #state = {
    user: null,
    activeSession: null,
    sessions: [],
    viewport: { x: 0, y: 0, zoom: 1 },
    ui: {
      sidebarOpen: true,
      chatInputLocked: false
    }
  };

  #subscribers = new Set();

  get(path) {
    return path.split('.').reduce((obj, key) => obj?.[key], this.#state);
  }

  set(path, value) {
    const keys = path.split('.');
    const last = keys.pop();
    const target = keys.reduce((obj, key) => obj[key], this.#state);
    target[last] = value;
    this.#notify(path, value);
  }

  subscribe(callback) {
    this.#subscribers.add(callback);
    return () => this.#subscribers.delete(callback);
  }

  #notify(path, value) {
    this.#subscribers.forEach(cb => cb(path, value, this.#state));
  }
}

window.axState = new AppState();
```

---

## 8. Theming

### 8.1 CSS Custom Properties

```css
/* styles/theme.css */
:root {
  /* Colors */
  --ax-primary: #4f46e5;
  --ax-primary-light: #e0e7ff;
  --ax-surface: #ffffff;
  --ax-background: #f8fafc;
  --ax-border: #e2e8f0;
  --ax-text: #1e293b;
  --ax-muted: #64748b;

  /* Session type colors */
  --ax-thought-color: #8b5cf6;
  --ax-learning-color: #0ea5e9;
  --ax-validation-color: #10b981;

  /* Status colors */
  --ax-status-active: #22c55e;
  --ax-status-paused: #f59e0b;
  --ax-status-completed: #3b82f6;
  --ax-status-terminated: #ef4444;

  /* Spacing */
  --ax-spacing-xs: 0.25rem;
  --ax-spacing-sm: 0.5rem;
  --ax-spacing-md: 1rem;
  --ax-spacing-lg: 1.5rem;
  --ax-spacing-xl: 2rem;

  /* Typography */
  --ax-font-sans: 'Inter', system-ui, sans-serif;
  --ax-font-mono: 'JetBrains Mono', monospace;

  /* Shadows */
  --ax-shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --ax-shadow-md: 0 4px 6px rgba(0,0,0,0.1);
  --ax-shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
  :root {
    --ax-surface: #1e293b;
    --ax-background: #0f172a;
    --ax-border: #334155;
    --ax-text: #f1f5f9;
    --ax-muted: #94a3b8;
  }
}
```

---

## 9. File Structure

```
agent-host/ui/
├── index.html
├── src/
│   ├── scripts/
│   │   ├── core/
│   │   │   ├── base-component.js
│   │   │   ├── canvas-manager.js
│   │   │   ├── event-bus.js
│   │   │   ├── app-state.js
│   │   │   ├── stream-manager.js
│   │   │   └── api-client.js
│   │   ├── components/
│   │   │   ├── ax-app.js
│   │   │   ├── ax-toolbar.js
│   │   │   ├── ax-canvas.js
│   │   │   ├── ax-session-card.js
│   │   │   ├── ax-agent-panel.js
│   │   │   ├── ax-message-stream.js
│   │   │   ├── ax-chat-input.js
│   │   │   ├── ax-client-action-renderer.js
│   │   │   ├── ax-multiple-choice.js
│   │   │   ├── ax-free-text-prompt.js
│   │   │   ├── ax-code-editor.js
│   │   │   └── ax-sidebar.js
│   │   └── main.js
│   └── styles/
│       ├── theme.css
│       ├── reset.css
│       └── utilities.css
└── assets/
    └── icons/
```

---

## 10. Accessibility

### 10.1 ARIA Guidelines

```javascript
// All interactive components must include:
// - role attribute when semantic HTML isn't sufficient
// - aria-label or aria-labelledby
// - aria-describedby for additional context
// - aria-live regions for dynamic content
// - Keyboard navigation support

class AccessibleComponent extends AXComponent {
  setupAccessibility() {
    // Focus management
    this.setAttribute('tabindex', '0');

    // Keyboard handlers
    this.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        this.activate();
      }
    });

    // Screen reader announcements
    this.setAttribute('role', 'region');
    this.setAttribute('aria-label', this.getLabel());
  }
}
```

---

_End of UI Architecture Document_
