/**
 * Widget Renderer - DOM rendering for client action widgets
 *
 * Handles rendering and interaction with client action widgets
 * (multiple choice, free text, slider, etc.)
 *
 * Architecture:
 * - All widgets for an item are rendered at once
 * - Widgets emit ax-selection events when user makes a selection (stored locally)
 * - If requireUserConfirmation=true: Submit button triggers batch submission
 * - If requireUserConfirmation=false: Each selection auto-submits immediately
 *
 * @module ui/renderers/widget-renderer
 */

import { eventBus, Events } from '../../core/event-bus.js';
import { stateManager, StateKeys } from '../../core/state-manager.js';
import { scrollToBottom } from '../../utils/dom.js';
import { sendMessage, submitWidgetResponse } from '../../protocol/websocket-client.js';

// =============================================================================
// State
// =============================================================================

/** @type {HTMLElement|null} */
let messagesContainer = null;

/** @type {Map<string, HTMLElement>} All rendered widget elements keyed by widgetId */
const renderedWidgets = new Map();

/** @type {Map<string, Object>} Pending responses keyed by widgetId */
const pendingResponses = new Map();

/** @type {Function|null} Widget response callback */
let widgetCallback = null;

/**
 * Widget stream state - controls whether user responses are shown
 * and when to reset for the next widget interaction
 */
const widgetStreamState = {
    showUserResponse: true,
};

/**
 * Check if should show user response bubble after widget submission
 * @returns {boolean}
 */
function shouldShowUserResponse() {
    return widgetStreamState.showUserResponse;
}

/**
 * Reset stream state for next widget interaction
 */
function resetStreamState() {
    widgetStreamState.showUserResponse = true;
}

/**
 * Set whether to show user response (called when widget is rendered)
 * @param {boolean} show - Whether to show user response
 */
export function setShowUserResponse(show) {
    widgetStreamState.showUserResponse = show;
}

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize widget renderer
 * @param {HTMLElement} container - Messages container element
 */
export function initWidgetRenderer(container) {
    messagesContainer = container;
    subscribeToEvents();
    console.log('[WidgetRenderer] Initialized');
}

/**
 * Subscribe to event bus events
 */
function subscribeToEvents() {
    eventBus.on(Events.WIDGET_RENDERED, data => {
        showWidget(data);
    });
}

/**
 * Clear all widgets and pending responses (called when moving to new item)
 */
export function clearWidgets() {
    renderedWidgets.forEach(widget => widget.remove());
    renderedWidgets.clear();
    pendingResponses.clear();
    console.log('[WidgetRenderer] Cleared all widgets and pending responses');
}

/**
 * Get all pending responses
 * @returns {Map<string, Object>}
 */
export function getPendingResponses() {
    return pendingResponses;
}

// =============================================================================
// Widget Display
// =============================================================================

/**
 * Check if current item requires user confirmation before submitting
 * @returns {boolean}
 */
function requiresConfirmation() {
    const itemContext = stateManager.get(StateKeys.CURRENT_ITEM_CONTEXT);
    return itemContext?.requireUserConfirmation === true;
}

/**
 * Show a client action widget
 * @param {Object} data - Widget data from server (WidgetRenderPayload)
 * @param {Function} [onResponse] - Response callback
 *
 * Expected payload structure:
 * - widgetId: Unique widget identifier
 * - widgetType: Widget type (e.g., "multiple_choice", "free_text")
 * - itemId: Parent item ID
 * - stem: Question/prompt text
 * - options: Choice options (for multiple_choice, checkbox_group, dropdown)
 * - widgetConfig: Widget-specific settings (shuffle_options, allow_multiple, etc.)
 * - required: Whether response is required
 * - skippable: Whether widget can be skipped
 * - initialValue: Pre-populated value
 * - showUserResponse: Whether to show response as chat bubble
 */
export function showWidget(data, onResponse) {
    // Support both widgetId (new) and contentId (legacy)
    const { widgetType, widgetId, contentId, itemId, stem, options, required, skippable, initialValue, widgetConfig, showUserResponse } = data;

    // Set whether to show user response bubble after submission
    widgetStreamState.showUserResponse = showUserResponse !== false;

    widgetCallback = onResponse;

    // Create widget element based on type
    const tagName = getWidgetTagName(widgetType);
    const widget = document.createElement(tagName);

    // Set common attributes (prefer widgetId, fallback to contentId for legacy)
    const id = widgetId || contentId;
    if (id) widget.setAttribute('content-id', id);
    if (id) widget.setAttribute('widget-id', id);
    if (itemId) widget.setAttribute('item-id', itemId);
    if (widgetType) widget.setAttribute('widget-type', widgetType); // Store widget type for later use
    if (stem) widget.setAttribute('prompt', stem);
    if (required) widget.setAttribute('required', '');
    if (skippable) widget.setAttribute('skippable', '');
    if (initialValue !== undefined) {
        widget.setAttribute('initial-value', JSON.stringify(initialValue));
    }

    // Set options for choice-based widgets
    if (options) {
        widget.setAttribute('options', JSON.stringify(options));
    }

    // Set widget-specific config attributes
    if (widgetConfig) {
        Object.entries(widgetConfig).forEach(([key, value]) => {
            // Convert snake_case to kebab-case for HTML attributes
            const attrName = key.replace(/_/g, '-');
            widget.setAttribute(attrName, typeof value === 'object' ? JSON.stringify(value) : String(value));
        });
    }

    // Check if this is the confirmation button (button with action=confirm)
    const isConfirmButton = widgetType === 'button' && widgetConfig?.action === 'confirm';
    const needsConfirmation = requiresConfirmation();

    console.log('[WidgetRenderer] showWidget:', {
        widgetType,
        widgetId: id,
        isConfirmButton,
        needsConfirmation,
        itemContext: stateManager.get(StateKeys.CURRENT_ITEM_CONTEXT),
    });

    if (isConfirmButton) {
        // Confirmation button: triggers batch submission of all pending responses
        widget.addEventListener('ax-submit', handleConfirmationSubmit);
    } else if (needsConfirmation) {
        // Item requires confirmation: store selection, don't auto-submit
        // Listen for various selection events (widgets may emit different event names)
        widget.addEventListener('ax-selection', handleWidgetSelection);
        widget.addEventListener('ax-response', handleWidgetSelection); // ax-multiple-choice emits this
        widget.addEventListener('ax-submit', handleWidgetSelection); // Fallback for other widgets
        widget.addEventListener('ax-skip', handleWidgetSkip);
    } else {
        // No confirmation required: auto-submit on selection (legacy behavior)
        widget.addEventListener('ax-response', handleWidgetSubmit); // ax-multiple-choice emits this
        widget.addEventListener('ax-submit', handleWidgetSubmit);
        widget.addEventListener('ax-skip', handleWidgetSkip);
    }

    // Store reference in map
    if (id) {
        renderedWidgets.set(id, widget);
    }

    // Append and scroll
    messagesContainer?.appendChild(widget);
    scrollToBottom(messagesContainer);
}

/**
 * Hide a specific widget by ID
 * @param {string} [widgetId] - Widget ID to hide. If not provided, does nothing (use clearWidgets instead).
 */
export function hideWidget(widgetId) {
    if (widgetId && renderedWidgets.has(widgetId)) {
        const widget = renderedWidgets.get(widgetId);
        widget.remove();
        renderedWidgets.delete(widgetId);
        pendingResponses.delete(widgetId);
    }
}

/**
 * Get a rendered widget element by ID
 * @param {string} widgetId - Widget ID
 * @returns {HTMLElement|null}
 */
export function getWidget(widgetId) {
    return renderedWidgets.get(widgetId) || null;
}

/**
 * Get current widget element (legacy - returns first rendered widget)
 * @returns {HTMLElement|null}
 * @deprecated Use getWidget(widgetId) instead
 */
export function getCurrentWidget() {
    const widgets = Array.from(renderedWidgets.values());
    return widgets.length > 0 ? widgets[0] : null;
}

// =============================================================================
// Widget Event Handlers
// =============================================================================

/**
 * Handle widget submission (auto-submit when no confirmation required)
 * @param {CustomEvent} event - Submit event
 */
function handleWidgetSubmit(event) {
    const widget = event.target;
    const widgetId = widget.getAttribute('widget-id') || widget.getAttribute('content-id');
    const widgetType = widget.getAttribute('widget-type') || 'unknown';
    const response = event.detail;
    console.log('[WidgetRenderer] Widget auto-submitted:', widgetId, response);

    // Get current item context for itemId
    const itemContext = stateManager.get(StateKeys.CURRENT_ITEM_CONTEXT);
    const itemId = itemContext?.itemId;

    // Hide this specific widget
    hideWidget(widgetId);

    // Extract message text from response
    const messageText = extractMessageText(response);

    // Show user response bubble if configured
    if (shouldShowUserResponse()) {
        const userBubble = document.createElement('chat-message');
        userBubble.setAttribute('role', 'user');
        userBubble.setAttribute('content', messageText);
        messagesContainer?.appendChild(userBubble);
    }

    // Reset stream state
    resetStreamState();

    // Send to server via data.response.submit
    if (itemId) {
        submitWidgetResponse(itemId, widgetId, widgetType, response);
    } else {
        // Fallback to message-based submission if no item context
        console.warn('[WidgetRenderer] No item context, falling back to sendMessage');
        sendMessage(messageText);
    }

    // Call callback if set
    if (widgetCallback) {
        widgetCallback(response);
    }

    eventBus.emit(Events.WIDGET_RESPONSE, response);
}

/**
 * Handle widget skip
 * @param {CustomEvent} event - Skip event
 */
function handleWidgetSkip(event) {
    const widget = event.target;
    const widgetId = widget.getAttribute('widget-id') || widget.getAttribute('content-id');
    console.log('[WidgetRenderer] Widget skipped:', widgetId);

    if (requiresConfirmation()) {
        // Store skip in pending responses
        if (widgetId) {
            pendingResponses.set(widgetId, { skipped: true });
        }
    } else {
        // No confirmation required: submit immediately
        hideWidget();
        sendMessage('[SKIPPED]');

        if (widgetCallback) {
            widgetCallback({ skipped: true });
        }

        eventBus.emit(Events.WIDGET_RESPONSE, { skipped: true });
    }
}

/**
 * Handle widget selection (when confirmation is required)
 * Stores the response locally but doesn't submit to server
 * @param {CustomEvent} event - Selection event
 */
function handleWidgetSelection(event) {
    const widget = event.target;
    const widgetId = widget.getAttribute('widget-id') || widget.getAttribute('content-id');
    const response = event.detail;

    console.log('[WidgetRenderer] Widget selection stored:', widgetId, response);

    // Store pending response
    if (widgetId) {
        pendingResponses.set(widgetId, response);
    }

    // Emit local event for UI updates (e.g., show checkmark on selected option)
    eventBus.emit(Events.WIDGET_SELECTION_CHANGED, { widgetId, response });
}

/**
 * Handle confirmation button click
 * Submits all pending responses to the server
 * @param {CustomEvent} event - Submit event from confirmation button
 */
function handleConfirmationSubmit(event) {
    console.log('[WidgetRenderer] Confirmation button clicked, submitting all pending responses');

    // Get current item context for itemId
    const itemContext = stateManager.get(StateKeys.CURRENT_ITEM_CONTEXT);
    const itemId = itemContext?.itemId;

    if (!itemId) {
        console.error('[WidgetRenderer] No item ID in context, cannot submit responses');
        return;
    }

    // Collect all pending responses
    const responses = {};
    let combinedText = [];

    pendingResponses.forEach((response, widgetId) => {
        responses[widgetId] = response;
        if (!response.skipped) {
            combinedText.push(extractMessageText(response));
        }
    });

    console.log('[WidgetRenderer] Submitting responses:', responses);

    // Show combined user response bubble if configured
    if (shouldShowUserResponse() && combinedText.length > 0) {
        const userBubble = document.createElement('chat-message');
        userBubble.setAttribute('role', 'user');
        userBubble.setAttribute('content', combinedText.join('\n'));
        messagesContainer?.appendChild(userBubble);
    }

    // Reset stream state
    resetStreamState();

    // Submit each widget response via data.response.submit
    pendingResponses.forEach((response, widgetId) => {
        // Get the widget to determine its type
        const widget = renderedWidgets.get(widgetId);
        const widgetType = widget?.getAttribute('widget-type') || 'unknown';
        submitWidgetResponse(itemId, widgetId, widgetType, response);
    });

    // Submit the confirmation button click itself
    const confirmWidgetId = `${itemId}-confirm`;
    submitWidgetResponse(itemId, confirmWidgetId, 'button', { confirmed: true });

    // Clear widgets and pending responses
    clearWidgets();

    // Emit event
    eventBus.emit(Events.WIDGET_RESPONSE, { confirmed: true, responses });
}

/**
 * Extract message text from widget response
 * @param {Object} response - Widget response
 * @returns {string} Message text
 */
function extractMessageText(response) {
    if (typeof response === 'string') {
        return response;
    }
    if (response.selected) {
        return Array.isArray(response.selected) ? response.selected.join(', ') : response.selected;
    }
    if (response.text) {
        return response.text;
    }
    if (response.code) {
        return response.code;
    }
    if (response.value !== undefined) {
        return String(response.value);
    }
    return JSON.stringify(response);
}

// =============================================================================
// Widget Type Mapping
// =============================================================================

/**
 * Widget type to custom element tag mapping
 * Matches protocol WidgetType enum (see widgets.js for canonical reference)
 */
const WIDGET_TYPE_MAP = {
    // Display widgets
    text_display: 'ax-text-display',
    image_display: 'ax-image-display',
    chart: 'ax-chart',
    data_table: 'ax-data-table',

    // Input widgets
    multiple_choice: 'ax-multiple-choice',
    free_text: 'ax-free-text-prompt',
    code_editor: 'ax-code-editor',
    slider: 'ax-slider',
    checkbox_group: 'ax-checkbox-group',
    dropdown: 'ax-dropdown',
    rating: 'ax-rating',
    date_picker: 'ax-date-picker',
    matrix_choice: 'ax-matrix-choice',

    // Interactive widgets
    drag_drop: 'ax-drag-drop',
    hotspot: 'ax-hotspot',
    drawing: 'ax-drawing',

    // Action widgets
    button: 'ax-submit-button',
    submit_button: 'ax-submit-button', // Legacy alias

    // Feedback widgets
    progress_bar: 'ax-progress-bar',
    timer: 'ax-timer',

    // Embedded content
    iframe: 'ax-iframe-widget',
};

/**
 * Get custom element tag name for widget type
 * @param {string} widgetType - Widget type
 * @returns {string} Tag name
 */
function getWidgetTagName(widgetType) {
    return WIDGET_TYPE_MAP[widgetType] || `ax-${widgetType.replace(/_/g, '-')}`;
}

export default {
    initWidgetRenderer,
    showWidget,
    hideWidget,
    getWidget,
    getCurrentWidget,
    clearWidgets,
    getPendingResponses,
};
