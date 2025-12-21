# Phase 5: Frontend Architecture & Widget Expansion

**Document Version:** 1.0.0
**Last Updated:** December 19, 2025
**Duration:** Weeks 15-22 (8 weeks)
**Predecessor:** Phase 4 - Advanced Features

---

## Executive Summary

This phase addresses critical technical debt in the frontend architecture while expanding the widget catalog and admin capabilities. The goal is to establish a scalable, maintainable foundation that supports the dramatic increase in complexity expected from assessment-driven AI conversations.

### Key Objectives

1. **Architectural Refactor** - Transform monolithic JS modules into clean, scalable structure
2. **SASS 7-1 Pattern** - Professional styling architecture
3. **Widget Catalog Completion** - All 19 protocol widgets fully implemented
4. **Admin UI Expansion** - Complete widget configuration support
5. **Canvas System Completion** - Connections, groups, layers, presentation mode

---

## Current State Analysis

### Code Quality Issues

| File | Lines | Issue |
|------|-------|-------|
| `app.js` | 1,053 | Monolithic orchestrator, mixed concerns |
| `websocket-handler.js` | 733 | Handles too many message types inline |
| `templates-manager.js` | 1,314 | Only supports 4 widget types |
| `message-renderer.js` | 458 | Tightly coupled to DOM |

### Widget Implementation Status

| Category | Implemented | Missing | Priority |
|----------|-------------|---------|----------|
| P0 Critical | 5/5 | — | ✅ Complete |
| P1 Important | 5/5 | — | ✅ Complete |
| P2 Enhanced | 3/6 | file_upload, date_picker, video | Medium |
| Advanced | 0/6 | drag_drop, hotspot, matrix_choice, graph_topology, document_viewer, drawing | High |
| Data Display | 0/2 | chart, data_table | High |

---

## Phase 5 Structure

```
Phase 5 (8 weeks)
├── 5A: Foundation Refactor (Weeks 15-16)
│   ├── SASS 7-1 Pattern Migration
│   └── JS Module Restructure
├── 5B: Admin Widget Configs (Weeks 17-18)
│   └── All 19 widget configuration UIs
├── 5C: Widget Catalog Expansion (Weeks 19-20)
│   ├── Data Display: chart, data_table
│   ├── Advanced Input: drag_drop, hotspot, matrix_choice
│   └── Remaining: date_picker, drawing
├── 5D: Canvas System Completion (Weeks 21-22)
│   ├── Connection Lines
│   ├── Groups & Layers
│   └── Presentation Mode
```

---

## 5A: Foundation Refactor (Weeks 15-16)

### 5A.1 SASS 7-1 Pattern Migration

**Target Structure:**

```
ui/src/styles/
├── abstracts/
│   ├── _variables.scss      # Design tokens
│   ├── _mixins.scss         # Reusable mixins
│   ├── _functions.scss      # SASS functions
│   └── _index.scss          # Forward all
├── base/
│   ├── _reset.scss          # CSS reset
│   ├── _typography.scss     # Font styles
│   └── _index.scss
├── components/
│   ├── _buttons.scss
│   ├── _cards.scss
│   ├── _forms.scss
│   ├── _modals.scss
│   └── _index.scss
├── layout/
│   ├── _header.scss
│   ├── _sidebar.scss
│   ├── _chat-area.scss
│   └── _index.scss
├── pages/
│   ├── _admin.scss
│   ├── _chat.scss
│   └── _index.scss
├── themes/
│   ├── _light.scss
│   ├── _dark.scss
│   └── _index.scss
├── vendors/
│   ├── _bootstrap-overrides.scss
│   └── _index.scss
├── widgets/
│   ├── _widget-base.scss
│   ├── _multiple-choice.scss
│   ├── _slider.scss
│   └── ... (per widget)
├── main.scss               # Chat app entry
└── admin.scss              # Admin entry
```

**Migration Tasks:**

| Task | File(s) | Priority |
|------|---------|----------|
| Create abstracts/ with design tokens | New | P0 |
| Extract variables from _variables.scss | Migrate | P0 |
| Create base/ with reset + typography | New | P0 |
| Split components/ from _index.scss | Migrate | P1 |
| Create layout/ from existing | Migrate | P1 |
| Create widgets/ for component styles | New | P1 |
| Create themes/ for dark/light | New | P2 |

---

### 5A.2 JavaScript Module Restructure

**Target Structure:**

```
ui/src/scripts/
├── index.js                    # Main entry (thin)
├── admin-index.js              # Admin entry (thin)
│
├── core/                       # Core infrastructure
│   ├── event-bus.js            # Pub/sub singleton
│   ├── state-manager.js        # Simple state container
│   ├── router.js               # Client-side routing (if needed)
│   └── index.js
│
├── protocol/                   # WebSocket protocol layer
│   ├── websocket-client.js     # Connection management
│   ├── message-router.js       # Type → handler dispatch
│   ├── message-handlers/       # Per-message-type handlers
│   │   ├── system-handlers.js
│   │   ├── control-handlers.js
│   │   ├── data-handlers.js
│   │   └── index.js
│   └── index.js
│
├── domain/                     # Business logic (no DOM)
│   ├── conversation.js         # Conversation state/logic
│   ├── definition.js           # Agent definition logic
│   ├── template.js             # Template logic
│   └── index.js
│
├── ui/                         # UI layer (DOM interaction)
│   ├── managers/               # UI orchestrators
│   │   ├── chat-manager.js     # Chat UI state
│   │   ├── sidebar-manager.js
│   │   ├── modal-manager.js
│   │   └── index.js
│   ├── renderers/              # DOM rendering
│   │   ├── message-renderer.js
│   │   ├── widget-renderer.js
│   │   └── index.js
│   └── index.js
│
├── widgets/                    # Web Components
│   ├── base/
│   │   ├── widget-base.js
│   │   ├── widget-registry.js
│   │   └── widget-factory.js
│   ├── input/                  # Input widgets
│   │   ├── multiple-choice.js
│   │   ├── free-text.js
│   │   ├── slider.js
│   │   ├── dropdown.js
│   │   ├── checkbox-group.js
│   │   ├── rating.js
│   │   ├── date-picker.js
│   │   ├── drag-drop.js
│   │   ├── hotspot.js
│   │   ├── matrix-choice.js
│   │   ├── drawing.js
│   │   └── index.js
│   ├── display/                # Display widgets
│   │   ├── text-display.js
│   │   ├── image-display.js
│   │   ├── chart.js
│   │   ├── data-table.js
│   │   └── index.js
│   ├── action/
│   │   ├── submit-button.js
│   │   └── index.js
│   ├── feedback/
│   │   ├── progress-bar.js
│   │   ├── timer.js
│   │   └── index.js
│   ├── embedded/
│   │   ├── iframe-widget.js
│   │   ├── code-editor.js
│   │   └── index.js
│   └── index.js
│
├── canvas/                     # Canvas system
│   ├── canvas-manager.js
│   ├── canvas-element.js
│   ├── connection-renderer.js  # NEW
│   ├── group-manager.js        # NEW
│   ├── layer-manager.js        # NEW
│   ├── presentation-mode.js    # NEW
│   └── index.js
│
├── admin/                      # Admin-specific
│   ├── definitions-manager.js
│   ├── templates-manager.js
│   ├── settings-manager.js
│   ├── widget-config/          # NEW: Widget config UIs
│   │   ├── config-base.js
│   │   ├── multiple-choice-config.js
│   │   ├── slider-config.js
│   │   ├── drag-drop-config.js
│   │   └── ... (per widget)
│   └── index.js
│
├── services/                   # External services
│   ├── api.js
│   ├── auth.js
│   ├── theme.js
│   └── index.js
│
└── utils/                      # Pure utilities
    ├── dom.js
    ├── format.js
    ├── validation.js
    └── index.js
```

**Refactor Strategy:**

1. **Create new structure** alongside existing code
2. **Extract in order:** utils → services → domain → protocol → ui → widgets
3. **Update imports** incrementally
4. **Delete old files** only after migration complete
5. **Test each extraction** before proceeding

**app.js Decomposition:**

| Current Responsibility | Target Location |
|------------------------|-----------------|
| DOM element references | `ui/managers/chat-manager.js` |
| Event binding | `ui/managers/chat-manager.js` |
| Auth handling | `services/auth.js` |
| Config loading | `domain/config.js` |
| Message sending | `protocol/websocket-client.js` |
| Conversation management | `domain/conversation.js` |
| Definition selection | `domain/definition.js` |
| UI state updates | `ui/managers/` |

---

## 5B: Admin Widget Configs (Weeks 17-18)

### Widget Configuration Matrix

Each widget needs a dedicated config UI in the admin templates editor:

| Widget Type | Config Fields | Complexity |
|-------------|---------------|------------|
| `message` | stem only | Low |
| `multiple_choice` | options[], allowMultiple, shuffle, correctAnswer | Medium |
| `free_text` | placeholder, minLength, maxLength, multiline, rows | Medium |
| `slider` | min, max, step, defaultValue, labels{} | Medium |
| `code_editor` | language, initialCode, minLines, maxLines, readOnly | Medium |
| `checkbox_group` | options[], minSelections, maxSelections | Medium |
| `dropdown` | options[], placeholder, searchable, multiple | Medium |
| `rating` | style, maxRating, labels[], allowHalf | Medium |
| `date_picker` | mode, minDate, maxDate, format, timezone | Medium |
| `timer` | mode, duration, warningThreshold, autoStart | Medium |
| `progress_bar` | mode, showPercentage, animated | Low |
| `image_display` | src, alt, maxWidth, maxHeight, objectFit | Medium |
| `text_display` | contentType, maxHeight, typography | Low |
| `submit_button` | label, style, disabled | Low |
| `iframe` | src, sandbox, allow, width, height, allowedOrigins | High |
| `drag_drop` | variant, items[], zones[], placeholders[] | High |
| `hotspot` | image, regions[], selectionMode | High |
| `matrix_choice` | rows[], columns[], layout, selectionMode | High |
| `chart` | type, data, options, responsive | High |
| `data_table` | columns[], data, sortable, filterable, paginated | High |

### Implementation Pattern

**Base Config Component:**

```javascript
// admin/widget-config/config-base.js
export class WidgetConfigBase {
    constructor(containerEl, widgetType) {
        this.container = containerEl;
        this.widgetType = widgetType;
    }

    render(config = {}) { throw new Error('Override'); }
    getValue() { throw new Error('Override'); }
    validate() { return { valid: true, errors: [] }; }
}
```

**Config Registry:**

```javascript
// admin/widget-config/config-registry.js
const CONFIG_REGISTRY = {
    multiple_choice: MultipleChoiceConfig,
    slider: SliderConfig,
    drag_drop: DragDropConfig,
    // ... all 19
};

export function createConfigUI(container, widgetType, initialConfig) {
    const ConfigClass = CONFIG_REGISTRY[widgetType];
    if (!ConfigClass) return null;
    const instance = new ConfigClass(container, widgetType);
    instance.render(initialConfig);
    return instance;
}
```

### templates-manager.js Changes

Replace the inline `renderWidgetConfig()` switch with:

```javascript
import { createConfigUI } from './widget-config/config-registry.js';

// In renderContentCard():
const configContainer = contentEl.querySelector('.widget-config-container');
this._activeConfig = createConfigUI(configContainer, widgetType, existingConfig);

// In collectContentData():
const widgetConfig = this._activeConfig?.getValue() ?? {};
```

---

## 5C: Widget Catalog Expansion (Weeks 19-20)

### Priority Order

**Week 19:**

1. `ax-chart` - Inline reporting (wrap Chart.js or similar)
2. `ax-data-table` - Sortable, filterable tables
3. `ax-drag-drop` - Category, sequence, graphical variants
4. `ax-hotspot` - Image region selection

**Week 20:**
5. `ax-matrix-choice` - Likert scales, rating grids
6. `ax-date-picker` - Calendar with time support
7. `ax-drawing` - Freehand canvas

### Widget Implementation Checklist

For each widget:

- [ ] Create component file in `widgets/{category}/`
- [ ] Extend `AxWidgetBase`
- [ ] Implement: `render()`, `getValue()`, `setValue()`, `validate()`
- [ ] Add to `widgets/index.js` exports
- [ ] Add to `WIDGET_TYPE_MAP` in widget factory
- [ ] Create SCSS in `styles/widgets/`
- [ ] Create admin config UI in `admin/widget-config/`
- [ ] Add to templates-manager dropdown
- [ ] Write unit tests
- [ ] Document accessibility features

### Chart Widget Spec

```javascript
// widgets/display/chart.js
class AxChart extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes,
            'chart-type', 'data', 'options', 'responsive'];
    }

    // Lazy-load Chart.js
    async connectedCallback() {
        await this.loadChartLibrary();
        super.connectedCallback();
    }

    async loadChartLibrary() {
        if (!window.Chart) {
            await import('chart.js/auto');
        }
    }
}
```

### Drag & Drop Widget Spec

```javascript
// widgets/input/drag-drop.js
class AxDragDrop extends AxWidgetBase {
    // Supports three variants per protocol:
    // - category: Sort items into labeled zones
    // - sequence: Order items in sequence
    // - graphical: Place items on background image

    get variant() {
        return this.getAttribute('variant') || 'category';
    }

    // Use native drag API + SortableJS for mobile
}
```

---

## 5D: Canvas System Completion (Weeks 21-22)

### Connection Renderer

**File:** `canvas/connection-renderer.js`

```javascript
export class ConnectionRenderer {
    constructor(svgLayer) {
        this.svg = svgLayer;
        this.connections = new Map();
    }

    addConnection(id, fromEl, toEl, options = {}) {
        const path = this.calculatePath(fromEl, toEl, options.type);
        // Render SVG path
    }

    calculatePath(from, to, type) {
        switch (type) {
            case 'straight': return this.straightPath(from, to);
            case 'bezier': return this.bezierPath(from, to);
            case 'elbow': return this.elbowPath(from, to);
            default: return this.straightPath(from, to);
        }
    }

    // Update on element move
    updateConnection(id) { /* recalculate path */ }
}
```

### Group Manager

**File:** `canvas/group-manager.js`

```javascript
export class GroupManager {
    constructor(canvasManager) {
        this.canvas = canvasManager;
        this.groups = new Map();
    }

    createGroup(elementIds, options = {}) {
        const groupId = generateId();
        const bounds = this.calculateGroupBounds(elementIds);
        // Create group container, move elements inside
        return groupId;
    }

    moveGroup(groupId, dx, dy) {
        const group = this.groups.get(groupId);
        group.elements.forEach(el => {
            el.x += dx;
            el.y += dy;
        });
    }
}
```

### Layer Manager

**File:** `canvas/layer-manager.js`

```javascript
export class LayerManager {
    constructor(canvasContainer) {
        this.container = canvasContainer;
        this.layers = [
            { id: 'background', zIndex: 0, visible: true, locked: false },
            { id: 'content', zIndex: 100, visible: true, locked: false },
            { id: 'overlay', zIndex: 200, visible: true, locked: false }
        ];
    }

    assignToLayer(elementId, layerId) { /* ... */ }
    setLayerVisibility(layerId, visible) { /* ... */ }
    setLayerLock(layerId, locked) { /* ... */ }
}
```

### Presentation Mode

**File:** `canvas/presentation-mode.js`

```javascript
export class PresentationMode {
    constructor(canvasManager) {
        this.canvas = canvasManager;
        this.waypoints = [];
        this.currentIndex = -1;
        this.isActive = false;
    }

    start(waypoints) {
        this.waypoints = waypoints;
        this.currentIndex = 0;
        this.isActive = true;
        this.hideChrome();
        this.navigateTo(0);
    }

    next() {
        if (this.currentIndex < this.waypoints.length - 1) {
            this.navigateTo(++this.currentIndex);
        }
    }

    navigateTo(index) {
        const wp = this.waypoints[index];
        this.canvas.animateToViewport(wp.viewport, wp.transition);
    }

    hideChrome() { /* Hide toolbar, sidebar */ }
}
```

---

## Testing Requirements

### Unit Tests (Per Component)

| Component Type | Test Coverage Target |
|----------------|---------------------|
| Widgets | 90% |
| Canvas | 85% |
| Protocol handlers | 95% |
| Admin configs | 80% |

### Integration Tests

- Widget ↔ WebSocket message flow
- Admin config → Widget render round-trip
- Canvas state persistence

### E2E Tests

- Full conversation with all widget types
- Admin creates template with complex widgets
- Canvas-based assessment flow

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Refactor breaks existing features | Feature-flag new code, maintain old until validated |
| Widget complexity explosion | Strict base class contract, thorough code review |
| Performance with many canvas elements | Virtual rendering, lazy initialization |
| Admin config UX overwhelm | Progressive disclosure, sensible defaults |

---

## Success Criteria

1. **Week 16:** SASS 7-1 complete, JS structure in place, all tests passing
2. **Week 18:** All 19 widget configs available in admin UI
3. **Week 20:** All widgets implemented with tests
4. **Week 22:** Canvas connections, groups, layers, presentation mode functional

---

## Appendix A: Design Tokens

```scss
// abstracts/_variables.scss
$color-primary: #0d6efd;
$color-primary-light: #e7f1ff;
$color-secondary: #6c757d;
$color-success: #198754;
$color-warning: #ffc107;
$color-danger: #dc3545;

$font-family-base: system-ui, -apple-system, sans-serif;
$font-family-mono: 'Monaco', 'Menlo', monospace;

$spacing-unit: 0.25rem;
$border-radius-sm: 4px;
$border-radius-md: 8px;
$border-radius-lg: 12px;

$shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
$shadow-md: 0 4px 6px rgba(0,0,0,0.1);
$shadow-lg: 0 10px 15px rgba(0,0,0,0.1);

$z-index-dropdown: 1000;
$z-index-modal: 1050;
$z-index-tooltip: 1100;
```

---

## Appendix B: Event Bus Pattern

```javascript
// core/event-bus.js
class EventBus {
    constructor() {
        this.listeners = new Map();
    }

    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);
        return () => this.off(event, callback);
    }

    off(event, callback) {
        this.listeners.get(event)?.delete(callback);
    }

    emit(event, data) {
        this.listeners.get(event)?.forEach(cb => cb(data));
    }
}

export const eventBus = new EventBus();
```

---

## Appendix C: File Migration Checklist

| Old File | Status | New Location(s) |
|----------|--------|-----------------|
| `app.js` | 🔄 | Split across `domain/`, `ui/managers/`, `protocol/` |
| `websocket-handler.js` | 🔄 | `protocol/websocket-client.js`, `protocol/message-handlers/` |
| `message-renderer.js` | 🔄 | `ui/renderers/message-renderer.js` |
| `stream-handler.js` | 🔄 | `protocol/message-handlers/data-handlers.js` |
| `ui-manager.js` | 🔄 | `ui/managers/chat-manager.js` |
| `sidebar-manager.js` | ✅ | `ui/managers/sidebar-manager.js` |
| `config-manager.js` | 🔄 | `domain/config.js` |
| `conversation-manager.js` | 🔄 | `domain/conversation.js` |
| `definition-manager.js` | 🔄 | `domain/definition.js` |
| `draft-manager.js` | ✅ | `services/draft.js` |
| `session-manager.js` | ✅ | `services/session.js` |
| `templates-manager.js` | 🔄 | `admin/templates-manager.js` + `admin/widget-config/` |
