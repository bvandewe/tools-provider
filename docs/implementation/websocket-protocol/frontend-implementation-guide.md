# Frontend Implementation Guide

**Document Version:** 1.0.0
**Last Updated:** December 18, 2025
**Target:** TypeScript + WebComponents + Modular SASS (No Framework)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Project Structure](#2-project-structure)
3. [Build Configuration](#3-build-configuration)
4. [Core Components](#4-core-components)
5. [Widget System](#5-widget-system)
6. [Canvas System](#6-canvas-system)
7. [State Management](#7-state-management)
8. [Styling Architecture](#8-styling-architecture)

---

## 1. Overview

### Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Language | TypeScript 5.3+ | Type safety, IDE support |
| Components | WebComponents (Custom Elements) | No framework, native browser APIs |
| Bundler | Vite | Fast dev server, optimized builds |
| Styling | Modular SASS | Scoped styles, design tokens |
| Testing | Vitest + Playwright | Unit + E2E |

### Design Principles

1. **Zero Framework Dependencies**: Pure TypeScript + browser APIs
2. **Modular Architecture**: Each widget is self-contained
3. **Protocol-First**: TypeScript types generated from spec
4. **Progressive Enhancement**: Core functionality without JS, enhanced with it

---

## 2. Project Structure

```
src/agent-host/ui/
├── src/
│   ├── index.ts                    # Public API exports
│   │
│   ├── protocol/                   # WebSocket protocol layer
│   │   ├── types.ts                # ✅ COMPLETE - TypeScript interfaces
│   │   ├── client.ts               # WebSocketClient class
│   │   ├── reconnect.ts            # Reconnection with backoff
│   │   ├── message-bus.ts          # Pub/sub for message routing
│   │   └── state-machine.ts        # Connection state management
│   │
│   ├── core/                       # Core utilities
│   │   ├── events.ts               # Custom event helpers
│   │   ├── dom.ts                  # DOM manipulation utilities
│   │   └── storage.ts              # Local/session storage helpers
│   │
│   ├── widgets/                    # WebComponent widgets
│   │   ├── base/
│   │   │   ├── widget-base.ts      # Base class for all widgets
│   │   │   ├── widget-registry.ts  # Widget type → class registry
│   │   │   └── widget-factory.ts   # Factory for creating widgets
│   │   ├── multiple-choice/
│   │   │   ├── multiple-choice.ts
│   │   │   └── multiple-choice.scss
│   │   ├── free-text/
│   │   ├── code-editor/
│   │   ├── slider/
│   │   ├── drag-drop/
│   │   ├── ... (other widgets)
│   │   └── index.ts                # Widget exports
│   │
│   ├── canvas/                     # Canvas system
│   │   ├── canvas-engine.ts        # Main canvas controller
│   │   ├── viewport.ts             # Pan/zoom/focus
│   │   ├── connections.ts          # Connection rendering
│   │   ├── groups.ts               # Group management
│   │   ├── layers.ts               # Layer system
│   │   ├── selection.ts            # Selection handling
│   │   └── presentation.ts         # Presentation mode
│   │
│   ├── components/                 # Non-widget UI components
│   │   ├── connection-status.ts
│   │   ├── message-input.ts
│   │   ├── content-stream.ts
│   │   └── navigation-controls.ts
│   │
│   └── styles/                     # Global styles
│       ├── _variables.scss
│       ├── _mixins.scss
│       ├── _reset.scss
│       └── main.scss
│
├── package.json
├── tsconfig.json
├── vite.config.ts
└── vitest.config.ts
```

---

## 3. Build Configuration

### package.json

```json
{
  "name": "@agent-host/ui",
  "version": "1.0.0",
  "type": "module",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "dev": "vite",
    "build": "vite build && tsc --emitDeclarationOnly",
    "test": "vitest",
    "test:e2e": "playwright test"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "sass": "^1.69.0",
    "vitest": "^1.0.0",
    "@playwright/test": "^1.40.0"
  }
}
```

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "strict": true,
    "declaration": true,
    "declarationDir": "dist",
    "outDir": "dist",
    "rootDir": "src",
    "experimentalDecorators": true,
    "useDefineForClassFields": false
  },
  "include": ["src/**/*"]
}
```

### vite.config.ts

```typescript
import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  build: {
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      name: 'AgentHostUI',
      fileName: 'agent-host-ui',
      formats: ['es', 'umd']
    },
    rollupOptions: {
      output: {
        assetFileNames: 'styles/[name].[ext]'
      }
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "src/styles/_variables" as *;`
      }
    }
  }
});
```

---

## 4. Core Components

### 4.1 WebSocketClient

**Location:** `src/protocol/client.ts`

**Responsibilities:**

- Establish WebSocket connection with authentication
- Parse incoming messages and dispatch to message bus
- Send outgoing messages with proper formatting
- Handle connection lifecycle (open, close, error)

**Key Interface:**

```typescript
interface WebSocketClientOptions {
  url: string;
  token?: string;
  conversationId?: string;
  reconnect?: boolean;
  heartbeatInterval?: number;
}

class WebSocketClient {
  constructor(options: WebSocketClientOptions);

  connect(): Promise<void>;
  disconnect(code?: number, reason?: string): void;
  send<T>(type: string, payload: T): void;

  readonly state: ConnectionState;
  readonly connectionId: string | null;

  on(event: 'connected' | 'disconnected' | 'error', handler: Function): void;
  off(event: string, handler: Function): void;
}
```

**Implementation Notes:**

- Use native `WebSocket` API
- JSON serialization with `by_alias` for camelCase
- Automatic ping response on `system.ping`
- Emit custom events for state changes

### 4.2 ReconnectionManager

**Location:** `src/protocol/reconnect.ts`

**Responsibilities:**

- Implement exponential backoff algorithm
- Track reconnection attempts
- Persist connection state for resume
- Coordinate with WebSocketClient

**Key Interface:**

```typescript
interface ReconnectionConfig {
  baseDelay: number;      // Default: 1000ms
  maxDelay: number;       // Default: 30000ms
  maxAttempts: number;    // Default: 10
  jitterFactor: number;   // Default: 0.1
}

class ReconnectionManager {
  constructor(client: WebSocketClient, config?: Partial<ReconnectionConfig>);

  start(): void;
  stop(): void;
  reset(): void;

  readonly attempt: number;
  readonly nextDelay: number;
}
```

**Algorithm:**

```
delay = min(baseDelay * 2^attempt, maxDelay)
jitter = delay * jitterFactor * random(-1, 1)
finalDelay = delay + jitter
```

### 4.3 MessageBus

**Location:** `src/protocol/message-bus.ts`

**Responsibilities:**

- Route incoming messages to subscribers by type
- Support wildcard subscriptions (e.g., `control.*`)
- Maintain subscription registry
- Provide unsubscribe mechanism

**Key Interface:**

```typescript
type MessageHandler<T = unknown> = (message: ProtocolMessage<T>) => void;

class MessageBus {
  subscribe<T>(type: string, handler: MessageHandler<T>): () => void;
  subscribeOnce<T>(type: string, handler: MessageHandler<T>): () => void;
  publish(message: ProtocolMessage): void;

  // Wildcard patterns
  subscribe('control.*', handler);      // All control messages
  subscribe('data.widget.*', handler);  // All widget data messages
}
```

### 4.4 ConnectionStateMachine

**Location:** `src/protocol/state-machine.ts`

**States:**

- `disconnected` → `connecting` → `connected` → `active`
- `active` → `reconnecting` → `connected`
- Any → `disconnected`

**Transitions emit events** for UI updates (connection status indicator).

---

## 5. Widget System

### 5.1 WidgetBase Class

**Location:** `src/widgets/base/widget-base.ts`

**Responsibilities:**

- Extend `HTMLElement` for WebComponent
- Lifecycle management (connectedCallback, disconnectedCallback)
- Protocol integration (receive config, submit responses)
- Validation state handling
- Layout management

**Key Interface:**

```typescript
abstract class WidgetBase<TConfig, TValue> extends HTMLElement {
  // Protocol
  abstract readonly widgetType: WidgetType;
  protected config: TConfig | null = null;
  protected value: TValue | null = null;

  // Lifecycle
  connectedCallback(): void;
  disconnectedCallback(): void;

  // Configuration
  configure(config: TConfig, layout?: WidgetLayout): void;

  // Value management
  getValue(): TValue | null;
  setValue(value: TValue): void;

  // Validation
  validate(): ValidationResult;
  showValidation(result: ValidationResult): void;
  clearValidation(): void;

  // State
  setState(state: WidgetState): void;

  // Events
  protected emitChange(value: TValue): void;
  protected emitSubmit(value: TValue): void;

  // Rendering
  protected abstract render(): void;
  protected getStyles(): string;
}
```

### 5.2 Widget Registry

**Location:** `src/widgets/base/widget-registry.ts`

**Pattern:** Map widget type strings to WebComponent classes.

```typescript
const widgetRegistry = new Map<WidgetType, typeof WidgetBase>();

function registerWidget(type: WidgetType, constructor: typeof WidgetBase): void {
  widgetRegistry.set(type, constructor);
  customElements.define(`agent-widget-${type}`, constructor);
}

function createWidget(type: WidgetType): WidgetBase | null {
  const constructor = widgetRegistry.get(type);
  if (!constructor) return null;
  return new constructor();
}
```

### 5.3 Widget Implementation Pattern

Each widget follows this structure:

```
widgets/multiple-choice/
├── multiple-choice.ts      # WebComponent class
├── multiple-choice.scss    # Scoped styles
└── index.ts                # Exports
```

**Example: MultipleChoice Widget**

```typescript
// multiple-choice.ts
import { WidgetBase } from '../base/widget-base';
import { MultipleChoiceConfig } from '../../protocol/types';
import styles from './multiple-choice.scss?inline';

class MultipleChoiceWidget extends WidgetBase<MultipleChoiceConfig, string[]> {
  readonly widgetType = 'multiple_choice';

  private selectedOptions: Set<string> = new Set();

  protected render(): void {
    if (!this.config) return;

    const { options, minSelections, maxSelections, layout } = this.config;

    this.shadowRoot!.innerHTML = `
      <style>${styles}</style>
      <div class="mc-container mc-layout-${layout || 'vertical'}">
        ${options.map(opt => `
          <label class="mc-option" data-id="${opt.id}">
            <input type="${maxSelections === 1 ? 'radio' : 'checkbox'}"
                   name="mc-${this.config.widgetId}"
                   value="${opt.id}"
                   ${opt.disabled ? 'disabled' : ''}>
            <span class="mc-label">${opt.label}</span>
          </label>
        `).join('')}
      </div>
    `;

    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    this.shadowRoot!.querySelectorAll('input').forEach(input => {
      input.addEventListener('change', this.handleChange.bind(this));
    });
  }

  private handleChange(event: Event): void {
    const input = event.target as HTMLInputElement;

    if (input.checked) {
      this.selectedOptions.add(input.value);
    } else {
      this.selectedOptions.delete(input.value);
    }

    this.emitChange(Array.from(this.selectedOptions));
  }

  getValue(): string[] {
    return Array.from(this.selectedOptions);
  }

  validate(): ValidationResult {
    const { minSelections = 1, maxSelections } = this.config!;
    const count = this.selectedOptions.size;

    if (count < minSelections) {
      return { valid: false, message: `Select at least ${minSelections}` };
    }
    if (maxSelections && count > maxSelections) {
      return { valid: false, message: `Select at most ${maxSelections}` };
    }
    return { valid: true };
  }
}

customElements.define('agent-widget-multiple-choice', MultipleChoiceWidget);
export { MultipleChoiceWidget };
```

### 5.4 Widget Priority List

| Priority | Widget | Complexity | Effort |
|----------|--------|------------|--------|
| P0 | Multiple Choice | Low | 2d |
| P0 | Free Text | Low | 1d |
| P0 | Slider | Low | 1d |
| P0 | Rating | Low | 1d |
| P0 | Date Picker | Medium | 1d |
| P0 | Dropdown | Medium | 1d |
| P0 | Image | Low | 1d |
| P1 | Code Editor | High | 3d |
| P1 | File Upload | Medium | 2d |
| P1 | Drag & Drop | High | 4d |
| P1 | Matrix Choice | Medium | 2d |
| P1 | Document Viewer | High | 3d |
| P1 | Video | Medium | 3d |
| P1 | Hotspot | High | 3d |
| P1 | Sticky Note | Low | 1d |
| P2 | Graph Topology | Very High | 5d |
| P2 | Drawing | Very High | 4d |
| P2 | IFRAME | High | 4d |

---

## 6. Canvas System

### 6.1 CanvasEngine

**Location:** `src/canvas/canvas-engine.ts`

**Responsibilities:**

- Initialize canvas container
- Coordinate viewport, connections, groups, layers
- Handle widget positioning
- Process canvas control messages

**Key Interface:**

```typescript
interface CanvasEngineOptions {
  container: HTMLElement;
  config: CanvasFullConfig;
  messageBus: MessageBus;
}

class CanvasEngine {
  constructor(options: CanvasEngineOptions);

  // Widget management
  addWidget(widget: WidgetBase, position: Position): void;
  removeWidget(widgetId: string): void;
  moveWidget(widgetId: string, position: Position): void;
  resizeWidget(widgetId: string, dimensions: Dimensions): void;

  // Viewport
  panTo(position: Position, animate?: boolean): void;
  zoomTo(level: number, animate?: boolean): void;
  focusOn(target: ViewportFocusTarget): void;

  // Mode
  setMode(mode: CanvasMode): void;
  readonly mode: CanvasMode;

  // Selection
  select(ids: string[]): void;
  clearSelection(): void;
  readonly selection: string[];
}
```

### 6.2 Viewport

**Location:** `src/canvas/viewport.ts`

**Features:**

- Pan (drag or programmatic)
- Zoom (wheel, pinch, buttons)
- Focus on widget/region
- Minimap rendering

**Implementation Notes:**

- Use CSS transforms for performance
- Throttle scroll/pan events
- Support touch gestures
- Respect zoom limits from config

### 6.3 Connections

**Location:** `src/canvas/connections.ts`

**Rendering:**

- SVG overlay for connection lines
- Support line types: arrow, line, curve, elbow
- Anchors: auto, top, right, bottom, left, corners
- Labels at start/middle/end

**Implementation:**

- Calculate anchor points based on widget positions
- Bézier curves for smooth connections
- Update on widget move/resize
- Animate creation/deletion

### 6.4 Layers & Groups

**Layers:** Z-index management, visibility toggle, opacity control

**Groups:**

- Container element wrapping widgets
- Collapsible UI
- Drag entire group
- Style (background, border)

---

## 7. State Management

### 7.1 Approach: Event-Driven State

**No central store.** Components communicate via:

1. **MessageBus** for protocol messages
2. **Custom Events** for UI interactions
3. **Direct method calls** for parent-child

### 7.2 Conversation State

```typescript
// src/state/conversation-state.ts

class ConversationState {
  private config: ConversationConfigPayload | null = null;
  private widgets: Map<string, WidgetState> = new Map();
  private items: Map<string, ItemState> = new Map();

  constructor(private messageBus: MessageBus) {
    this.subscribeToMessages();
  }

  private subscribeToMessages(): void {
    this.messageBus.subscribe('control.conversation.config', this.handleConfig);
    this.messageBus.subscribe('control.widget.state', this.handleWidgetState);
    this.messageBus.subscribe('control.item.*', this.handleItemMessage);
  }

  getWidgetState(widgetId: string): WidgetState | undefined;
  getItemState(itemId: string): ItemState | undefined;

  // Emit events for UI updates
  onConfigChange: EventEmitter<ConversationConfigPayload>;
  onWidgetStateChange: EventEmitter<{ widgetId: string; state: WidgetState }>;
}
```

### 7.3 Persistence

- **SessionStorage:** Connection ID for resume
- **LocalStorage:** User preferences, audit buffer
- **IndexedDB:** Large data (canvas state, file uploads)

---

## 8. Styling Architecture

### 8.1 Design Tokens

**Location:** `src/styles/_variables.scss`

```scss
// Colors
$color-primary: #0066cc;
$color-secondary: #6c757d;
$color-success: #28a745;
$color-error: #dc3545;
$color-warning: #ffc107;

// Typography
$font-family-base: system-ui, -apple-system, sans-serif;
$font-family-mono: 'SF Mono', Consolas, monospace;
$font-size-base: 16px;
$line-height-base: 1.5;

// Spacing
$spacing-unit: 8px;
$spacing-xs: $spacing-unit * 0.5;  // 4px
$spacing-sm: $spacing-unit;         // 8px
$spacing-md: $spacing-unit * 2;     // 16px
$spacing-lg: $spacing-unit * 3;     // 24px
$spacing-xl: $spacing-unit * 4;     // 32px

// Borders
$border-radius-sm: 4px;
$border-radius-md: 8px;
$border-radius-lg: 12px;

// Shadows
$shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
$shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
$shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);

// Z-index layers
$z-index-widget: 100;
$z-index-connection: 50;
$z-index-group: 75;
$z-index-overlay: 200;
$z-index-modal: 300;

// Animation
$transition-fast: 150ms ease;
$transition-base: 250ms ease;
$transition-slow: 350ms ease;
```

### 8.2 Mixins

**Location:** `src/styles/_mixins.scss`

```scss
@mixin widget-container {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: $border-radius-md;
  padding: $spacing-md;
  box-shadow: $shadow-sm;
}

@mixin widget-state-disabled {
  opacity: 0.6;
  pointer-events: none;
  filter: grayscale(20%);
}

@mixin widget-state-readonly {
  pointer-events: none;
}

@mixin widget-validation-error {
  border-color: $color-error;

  .validation-message {
    color: $color-error;
    font-size: 0.875em;
    margin-top: $spacing-xs;
  }
}

@mixin focus-ring {
  outline: 2px solid $color-primary;
  outline-offset: 2px;
}

@mixin truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

### 8.3 Widget Styling Pattern

Each widget uses Shadow DOM with scoped styles:

```typescript
class MyWidget extends WidgetBase {
  protected getStyles(): string {
    return `
      @use '../styles/_variables' as *;
      @use '../styles/_mixins' as *;

      :host {
        display: block;
        @include widget-container;
      }

      :host([state="disabled"]) {
        @include widget-state-disabled;
      }

      :host([validation="error"]) {
        @include widget-validation-error;
      }
    `;
  }
}
```

---

## Related Documents

- [Implementation Plan](./websocket-protocol-implementation-plan.md)
- [Backend Implementation Guide](./backend-implementation-guide.md)
- [Testing Strategy](./testing-strategy.md)
- [Protocol Specification](../specs/websocket-protocol-v1.md)
- [TypeScript Interfaces](../specs/websocket-protocol-v1.types.ts)

---

_Document maintained by: Development Team_
_Last review: December 18, 2025_
