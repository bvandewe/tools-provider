# Phase 4: Advanced Features - Detailed Tasks

**Document Version:** 1.0.0  
**Last Updated:** December 18, 2025  
**Duration:** Weeks 10-14  

---

## Objective

Complete widget catalog, canvas system, and IFRAME sandbox with E2E integration.

---

## Deliverables

1. All 19 widgets implemented and tested
2. Canvas system with pan/zoom and connections
3. IFRAME widget with postMessage bridge
4. Presentation mode
5. Full system E2E tests

---

## 4.1 Widget Catalog Tasks

### Widget Priority Tiers

**P0 - Critical (Weeks 10-11):**

| Widget | Type | Notes |
|--------|------|-------|
| Text Display | display | Markdown/HTML rendering |
| Multiple Choice | input | Radio buttons |
| Text Input | input | Single/multi-line |
| Submit Button | action | Form submission |
| Progress Bar | feedback | Determinate/indeterminate |

**P1 - Important (Week 12):**

| Widget | Type | Notes |
|--------|------|-------|
| Code Editor | input | Syntax highlighting |
| Checkbox Group | input | Multi-select |
| Slider | input | Numeric range |
| Timer | feedback | Countdown/elapsed |
| Image Display | display | Gallery support |

**P2 - Enhanced (Weeks 13-14):**

| Widget | Type | Notes |
|--------|------|-------|
| Dropdown Select | input | Single/multi |
| File Upload | input | With preview |
| Date Picker | input | Calendar |
| Rating | input | Stars/scale |
| Video Player | display | Controls, captions |
| Audio Player | display | With waveform |
| Chart | display | Via canvas or lib |
| Data Table | display | Sortable, paginated |
| Canvas Drawing | input | Freeform |

---

### W4.1 Widget Base Architecture

**File:** `src/agent-host/ui/src/widgets/base/widget-base.ts`

**Implementation:**

```typescript
export abstract class WidgetBase extends HTMLElement {
  protected shadow: ShadowRoot;
  protected config: WidgetConfig;
  protected state: WidgetState = 'idle';
  protected value: unknown;
  
  static observedAttributes = ['widget-id', 'disabled', 'readonly'];
  
  constructor() {
    super();
    this.shadow = this.attachShadow({ mode: 'open' });
  }
  
  async connectedCallback(): Promise<void> {
    await this.loadStyles();
    this.render();
    this.bindEvents();
    this.announceAccessibility();
  }
  
  disconnectedCallback(): void {
    this.cleanup();
  }
  
  abstract render(): void;
  abstract getValue(): unknown;
  abstract setValue(value: unknown): void;
  abstract validate(): ValidationResult;
  
  protected async loadStyles(): Promise<void> {
    const styles = await this.getStyles();
    const sheet = new CSSStyleSheet();
    await sheet.replace(styles);
    this.shadow.adoptedStyleSheets = [sheet];
  }
  
  protected abstract getStyles(): Promise<string>;
}
```

---

### W4.2 Text Display Widget

**File:** `src/agent-host/ui/src/widgets/display/text-display.ts`

**Tag:** `<agent-widget-text-display>`

**Config Options:**

- `content` - String (markdown/html/text)
- `contentType` - "markdown" | "html" | "text"
- `maxHeight` - Optional scroll container height
- `typography` - Font size, line height overrides

**Implementation Notes:**

- Sanitize HTML before rendering
- Support streaming content updates
- Apply syntax highlighting to code blocks
- Support expandable/collapsible sections

---

### W4.3 Multiple Choice Widget

**File:** `src/agent-host/ui/src/widgets/input/multiple-choice.ts`

**Tag:** `<agent-widget-multiple-choice>`

**Config Options:**

- `options` - Array of { id, label, description?, disabled? }
- `allowMultiple` - Boolean (radio vs checkbox)
- `minSelections` - Number
- `maxSelections` - Number
- `shuffle` - Boolean (randomize order)
- `layout` - "vertical" | "horizontal" | "grid"

**Accessibility:**

- `role="radiogroup"` or `role="group"` for checkboxes
- Arrow key navigation
- Clear focus indicators
- Screen reader announcements

---

### W4.4 Text Input Widget

**File:** `src/agent-host/ui/src/widgets/input/text-input.ts`

**Tag:** `<agent-widget-text-input>`

**Config Options:**

- `placeholder` - String
- `multiline` - Boolean (input vs textarea)
- `minLength`, `maxLength` - Validation
- `pattern` - Regex validation
- `inputMode` - Keyboard hint (text, numeric, email, etc.)
- `autoResize` - Auto-grow textarea

**Features:**

- Character count display
- Real-time validation feedback
- Clear button
- Debounced onChange events

---

### W4.5 Code Editor Widget

**File:** `src/agent-host/ui/src/widgets/input/code-editor.ts`

**Tag:** `<agent-widget-code-editor>`

**Options:**

1. **Monaco Editor** - Full featured, heavier
2. **CodeMirror 6** - Lighter, modular
3. **Prism + contenteditable** - Lightweight, limited

**Config Options:**

- `language` - Syntax mode
- `theme` - "light" | "dark" | "auto"
- `readOnly` - Boolean
- `lineNumbers` - Boolean
- `minLines`, `maxLines` - Height constraints
- `initialCode` - Starter code
- `highlightLines` - Array of line numbers

**Lazy Loading:**

- Load editor bundle only when widget mounted
- Show placeholder textarea during load

---

### W4.6 Widget State Synchronization

**Backend:** `src/agent-host/application/websocket/handlers/widget_sync.py`

**Handler:** `WidgetStateUpdateHandler`

**Sync Strategy:**

- Widget sends `control.widget.stateUpdate` on value change
- Server validates and broadcasts to other tabs
- Debounce updates (250ms default)

**Conflict Resolution:**

- Last-write-wins with server timestamp
- Optimistic updates on client
- Rollback if server rejects

---

## 4.2 Canvas System Tasks

### C4.1 Canvas Manager

**File:** `src/agent-host/ui/src/canvas/canvas-manager.ts`

**Class:** `CanvasManager`

**Responsibilities:**

- Coordinate system management (world vs screen)
- Pan/zoom controls
- Element positioning
- Selection handling
- Keyboard shortcuts

**Implementation:**

```typescript
class CanvasManager {
  private viewTransform: DOMMatrix;
  private elements: Map<string, CanvasElement>;
  private selectedIds: Set<string>;
  
  pan(dx: number, dy: number): void {
    this.viewTransform = this.viewTransform.translate(dx, dy);
    this.render();
  }
  
  zoom(factor: number, centerX: number, centerY: number): void {
    // Zoom around center point
    this.viewTransform = this.viewTransform
      .translate(centerX, centerY)
      .scale(factor)
      .translate(-centerX, -centerY);
    this.clampZoom();
    this.render();
  }
  
  screenToWorld(screenX: number, screenY: number): Point {
    return this.viewTransform.inverse().transformPoint({ x: screenX, y: screenY });
  }
}
```

---

### C4.2 Canvas Element

**File:** `src/agent-host/ui/src/canvas/canvas-element.ts`

**WebComponent:** `<canvas-element>`

**Features:**

- Absolute positioning within canvas
- Resize handles
- Drag to move
- Selection state

**Properties:**

```typescript
interface CanvasElementProps {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  zIndex: number;
  locked: boolean;
  resizable: boolean;
  draggable: boolean;
}
```

---

### C4.3 Connection Lines

**File:** `src/agent-host/ui/src/canvas/connection.ts`

**Class:** `ConnectionRenderer`

**Line Types:**

- Straight
- Bezier curve
- Orthogonal (right angles)
- Elbow (step pattern)

**Rendering:**

- SVG overlay for connections
- Path calculations for anchors
- Arrow heads
- Labels on connections

**Anchors:**

- Define anchor points on elements
- Auto-route around obstacles (optional)
- Snap to grid option

---

### C4.4 Canvas Groups

**File:** `src/agent-host/ui/src/canvas/group.ts`

**Features:**

- Group multiple elements
- Move/scale group as unit
- Ungroup
- Nested groups

**Protocol Message:**

```typescript
interface CanvasGroupPayload {
  groupId: string;
  action: 'create' | 'add' | 'remove' | 'destroy';
  elementIds: string[];
  transform?: Transform;
}
```

---

### C4.5 Canvas Layers

**File:** `src/agent-host/ui/src/canvas/layer-manager.ts`

**Features:**

- Multiple layer support
- Layer visibility toggle
- Layer locking
- Reorder layers
- Layer opacity

**Use Cases:**

- Background layer (non-interactive)
- Content layer (widgets)
- Overlay layer (annotations)
- Presentation layer (highlights)

---

### C4.6 Presentation Mode

**File:** `src/agent-host/ui/src/canvas/presentation-mode.ts`

**Features:**

- Navigate through waypoints
- Animated transitions
- Hide UI chrome
- Keyboard navigation (arrows, space)
- Timer display

**Protocol:**

```typescript
interface PresentationPayload {
  action: 'start' | 'stop' | 'next' | 'previous' | 'goto';
  waypointId?: string;
  transition?: 'instant' | 'smooth' | 'animated';
}
```

---

### C4.7 Canvas Backend Support

**File:** `src/agent-host/application/websocket/handlers/canvas_handlers.py`

**Messages:**

- `canvas.element.create` / `.update` / `.delete`
- `canvas.connection.create` / `.update` / `.delete`
- `canvas.group.create` / `.update` / `.destroy`
- `canvas.layer.*`
- `canvas.presentation.*`
- `canvas.viewport.update`

**State Management:**

- Persist canvas state to domain
- Broadcast changes to all viewers
- Support undo/redo via event log

---

## 4.3 IFRAME Widget Tasks

### I4.1 IFRAME Widget

**File:** `src/agent-host/ui/src/widgets/iframe/iframe-widget.ts`

**Tag:** `<agent-widget-iframe>`

**Config Options:**

- `src` - URL to load
- `sandbox` - Sandbox attribute flags
- `allow` - Permissions policy
- `width`, `height` - Dimensions
- `allowResize` - User resizable

**Security Defaults:**

```html
<iframe 
  sandbox="allow-scripts allow-same-origin" 
  allow="clipboard-read; clipboard-write"
  referrerpolicy="strict-origin-when-cross-origin"
></iframe>
```

---

### I4.2 PostMessage Bridge

**File:** `src/agent-host/ui/src/widgets/iframe/postmessage-bridge.ts`

**Architecture:**

```
Parent Window ←→ Bridge ←→ IFRAME Content
     ↓              ↓
 WebSocket     Origin Validation
```

**Message Format:**

```typescript
interface BridgeMessage {
  type: string;
  payload: unknown;
  requestId?: string;  // For request-response
  origin: string;
}
```

**Security:**

- Validate origin on every message
- Whitelist allowed message types
- Rate limit incoming messages
- Sanitize payload data

---

### I4.3 IFRAME Permissions

**File:** `src/agent-host/ui/src/widgets/iframe/permission-manager.ts`

**Permission Categories:**

- **Navigation** - Allow links, redirects
- **Forms** - Allow form submission
- **Modals** - Allow dialogs, popups
- **Scripts** - Allow JavaScript
- **Storage** - Allow localStorage, cookies

**Dynamic Permissions:**

```typescript
iframeWidget.updatePermissions({
  allowScripts: true,
  allowStorage: false,
  allowNavigation: 'same-origin',
});
```

---

### I4.4 Content Security Policy

**File:** `src/agent-host/ui/src/widgets/iframe/csp-generator.ts`

**Generated CSP for IFRAME:**

```typescript
function generateIframeCsp(config: IframeSecurityConfig): string {
  const directives = [
    `default-src 'self'`,
    `script-src ${config.allowScripts ? "'unsafe-inline'" : "'none'"}`,
    `style-src 'self' 'unsafe-inline'`,
    `img-src 'self' data: https:`,
    `frame-ancestors 'self'`,
  ];
  return directives.join('; ');
}
```

---

## Testing Tasks

### T4.1 Widget Unit Tests

**Location:** `tests/unit/widgets/`

**Per Widget:**

- `test_render_with_config`
- `test_value_get_set`
- `test_validation`
- `test_disabled_state`
- `test_accessibility`
- `test_keyboard_navigation`

**Example:**

```typescript
describe('MultipleChoice', () => {
  test('renders all options', () => {
    const widget = createWidget('multiple-choice', {
      options: [{ id: 'a', label: 'A' }, { id: 'b', label: 'B' }],
    });
    expect(widget.shadowRoot.querySelectorAll('label')).toHaveLength(2);
  });
  
  test('returns selected value', () => {
    const widget = createWidget('multiple-choice', { /* config */ });
    widget.shadowRoot.querySelector('input#a').click();
    expect(widget.getValue()).toBe('a');
  });
});
```

---

### T4.2 Canvas Integration Tests

**Location:** `tests/integration/canvas/`

**Test Scenarios:**

- `test_pan_updates_viewport`
- `test_zoom_limits_respected`
- `test_element_drag_persists`
- `test_connection_follows_elements`
- `test_multi_select`
- `test_undo_redo`

---

### T4.3 IFRAME Security Tests

**Location:** `tests/security/iframe/`

**Test Cases:**

- `test_sandbox_prevents_parent_access`
- `test_origin_validation_blocks_unknown`
- `test_csp_blocks_inline_scripts`
- `test_rate_limit_prevents_flood`
- `test_permissions_enforced`

---

### T4.4 E2E: Complete System Tests

**Location:** `tests/e2e/`

**Full Flow Tests:**

1. **Onboarding Flow**
   - Connect → Config → Multiple widgets → Submit → Complete

2. **Assessment Flow**
   - Connect → Timed questions → Score display

3. **Collaborative Canvas**
   - Two users → Shared canvas → Real-time sync

4. **Presentation Mode**
   - Navigate waypoints → Timer → Complete

**Performance Tests:**

- 100 concurrent connections
- 1000 messages per second throughput
- Canvas with 100 elements
- 50 widgets on single page

---

### T4.5 Accessibility Audit

**Tools:**

- axe-core automated testing
- Manual screen reader testing
- Keyboard navigation verification

**Requirements:**

- WCAG 2.1 AA compliance
- All widgets keyboard accessible
- Focus management correct
- Screen reader announcements

---

## Acceptance Criteria

- [ ] All 19 widgets implemented and documented
- [ ] Widget catalog page for reference
- [ ] Canvas pan/zoom smooth at 60fps
- [ ] Canvas elements draggable and resizable
- [ ] Connections render correctly on move
- [ ] Presentation mode navigates waypoints
- [ ] IFRAME sandboxed appropriately
- [ ] PostMessage bridge secure
- [ ] All E2E tests pass
- [ ] Performance targets met
- [ ] Accessibility audit pass

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Phase 3 Complete | Required | Data plane |
| Monaco/CodeMirror | To choose | Code editor |
| Chart library | To choose | If needed |
| axe-core | To install | Accessibility |

---

## Widget Documentation Template

Each widget should have:

1. **README.md** in widget folder
2. **Config schema** (JSON Schema)
3. **Usage examples** (code snippets)
4. **Accessibility notes**
5. **Known limitations**

**Example Location:** `src/agent-host/ui/src/widgets/input/multiple-choice/README.md`

---

## Related Documents

- [Implementation Plan](./websocket-protocol-implementation-plan.md)
- [Phase 3: Data Plane](./phase-3-data-plane.md)
- [Frontend Implementation Guide](./frontend-implementation-guide.md)
- [Protocol Spec - Widgets](../specs/websocket-protocol-v1.md#widgets)

---

_Document maintained by: Development Team_  
_Last review: December 18, 2025_
