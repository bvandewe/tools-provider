/**
 * WidgetRenderer - Class-based DOM rendering for client action widgets
 *
 * Handles rendering and interaction with client action widgets
 * (multiple choice, free text, slider, etc.)
 *
 * Architecture:
 * - Widgets are categorized by behavior: display, input, interactive, action, feedback
 * - Display widgets auto-add a "Next" button when skippable
 * - Input widgets emit ax-response events on submission
 * - If requireUserConfirmation=true: Submit button triggers batch submission
 * - If requireUserConfirmation=false: Each selection auto-submits immediately
 *
 * @module renderers/WidgetRenderer
 */

import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';
import { scrollToBottom } from '../utils/dom.js';
import { sendMessage, submitWidgetResponse, submitBatchResponse } from '../protocol/websocket-client.js';

// =============================================================================
// WIDGET TYPE CONFIGURATION
// =============================================================================

/**
 * Widget category definitions
 * @readonly
 * @enum {string}
 */
const WidgetCategory = {
    DISPLAY: 'display', // Read-only content (text, image, chart)
    INPUT: 'input', // User input widgets (text, choice, slider)
    INTERACTIVE: 'interactive', // Complex interactive (drag-drop, hotspot, drawing)
    ACTION: 'action', // Buttons and actions
    FEEDBACK: 'feedback', // Progress, timer, status
    EMBEDDED: 'embedded', // iframes, external content
};

/**
 * Widget type configuration with metadata
 * Each entry defines: tag name, category, and any special attribute handling
 *
 * IMPORTANT: This must stay aligned with backend WidgetType enum in:
 * application/protocol/enums.py
 */
const WIDGET_CONFIG = {
    // =========================================================================
    // Core message type
    // =========================================================================
    message: {
        tag: 'chat-message',
        category: WidgetCategory.DISPLAY,
    },

    // =========================================================================
    // Display widgets - read-only, typically need a "Next" button
    // =========================================================================
    text_display: {
        tag: 'ax-text-display',
        category: WidgetCategory.DISPLAY,
        stemAttribute: 'content', // Uses 'content' instead of 'prompt'
        formatAttribute: 'content-type', // Maps widgetConfig.format
    },
    image_display: {
        tag: 'ax-image-display',
        category: WidgetCategory.DISPLAY,
    },
    chart: {
        tag: 'ax-chart',
        category: WidgetCategory.DISPLAY,
    },
    data_table: {
        tag: 'ax-data-table',
        category: WidgetCategory.DISPLAY,
    },
    video: {
        tag: 'ax-video',
        category: WidgetCategory.DISPLAY,
    },
    graph_topology: {
        tag: 'ax-graph-topology',
        category: WidgetCategory.DISPLAY,
    },
    document_viewer: {
        tag: 'ax-document-viewer',
        category: WidgetCategory.DISPLAY,
    },
    sticky_note: {
        tag: 'ax-sticky-note',
        category: WidgetCategory.DISPLAY,
    },

    // =========================================================================
    // Input widgets - collect user responses
    // =========================================================================
    multiple_choice: {
        tag: 'ax-multiple-choice',
        category: WidgetCategory.INPUT,
    },
    checkbox_group: {
        tag: 'ax-checkbox-group',
        category: WidgetCategory.INPUT,
    },
    free_text: {
        tag: 'ax-free-text-prompt',
        category: WidgetCategory.INPUT,
    },
    code_editor: {
        tag: 'ax-code-editor',
        category: WidgetCategory.INPUT,
    },
    slider: {
        tag: 'ax-slider',
        category: WidgetCategory.INPUT,
    },
    dropdown: {
        tag: 'ax-dropdown',
        category: WidgetCategory.INPUT,
    },
    rating: {
        tag: 'ax-rating',
        category: WidgetCategory.INPUT,
    },
    date_picker: {
        tag: 'ax-date-picker',
        category: WidgetCategory.INPUT,
    },
    matrix_choice: {
        tag: 'ax-matrix-choice',
        category: WidgetCategory.INPUT,
    },
    file_upload: {
        tag: 'ax-file-upload',
        category: WidgetCategory.INPUT,
    },

    // =========================================================================
    // Interactive widgets - complex user interaction
    // =========================================================================
    hotspot: {
        tag: 'ax-hotspot',
        category: WidgetCategory.INTERACTIVE,
    },
    drag_drop: {
        tag: 'ax-drag-drop',
        category: WidgetCategory.INTERACTIVE,
    },
    drawing: {
        tag: 'ax-drawing',
        category: WidgetCategory.INTERACTIVE,
    },

    // =========================================================================
    // Action widgets - buttons and actions
    // =========================================================================
    button: {
        tag: 'ax-submit-button',
        category: WidgetCategory.ACTION,
    },
    submit_button: {
        tag: 'ax-submit-button',
        category: WidgetCategory.ACTION,
    },

    // =========================================================================
    // Feedback widgets - status display
    // =========================================================================
    progress_bar: {
        tag: 'ax-progress-bar',
        category: WidgetCategory.FEEDBACK,
    },
    timer: {
        tag: 'ax-timer',
        category: WidgetCategory.FEEDBACK,
    },

    // =========================================================================
    // Embedded content
    // =========================================================================
    iframe: {
        tag: 'ax-iframe-widget',
        category: WidgetCategory.EMBEDDED,
    },
};

/**
 * @class WidgetRenderer
 * @description Manages rendering and interaction of client action widgets
 */
export class WidgetRenderer {
    /**
     * Create WidgetRenderer instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Function[]} */
        this._unsubscribers = [];

        /** @type {HTMLElement|null} */
        this._messagesContainer = null;

        /** @type {Map<string, HTMLElement>} All rendered widget elements keyed by widgetId */
        this._renderedWidgets = new Map();

        /** @type {Map<string, Object>} Pending responses keyed by widgetId */
        this._pendingResponses = new Map();

        /** @type {Function|null} Widget response callback */
        this._widgetCallback = null;

        /** @type {boolean} Whether to show user response bubble */
        this._showUserResponse = true;

        // Bind methods
        this._handleWidgetRendered = this._handleWidgetRendered.bind(this);
        this._handleWidgetSubmit = this._handleWidgetSubmit.bind(this);
        this._handleWidgetSkip = this._handleWidgetSkip.bind(this);
        this._handleWidgetSelection = this._handleWidgetSelection.bind(this);
        this._handleConfirmationSubmit = this._handleConfirmationSubmit.bind(this);
    }

    /**
     * Initialize widget renderer
     * @param {HTMLElement} container - Messages container element
     */
    init(container) {
        if (this._initialized) {
            console.warn('[WidgetRenderer] Already initialized');
            return;
        }

        this._messagesContainer = container;
        this._subscribeToEvents();
        this._initialized = true;

        console.log('[WidgetRenderer] Initialized');
    }

    /**
     * Subscribe to event bus events
     * @private
     */
    _subscribeToEvents() {
        this._unsubscribers.push(eventBus.on(Events.WIDGET_RENDERED, this._handleWidgetRendered));
    }

    /**
     * Handle widget rendered event
     * @private
     */
    _handleWidgetRendered(data) {
        this.showWidget(data);
    }

    // =========================================================================
    // Widget Display
    // =========================================================================

    /**
     * Get widget configuration by type
     * @private
     * @param {string} widgetType - Widget type name
     * @returns {Object} Widget configuration
     */
    _getWidgetConfig(widgetType) {
        return (
            WIDGET_CONFIG[widgetType] || {
                tag: `ax-${widgetType.replace(/_/g, '-')}`,
                category: WidgetCategory.INPUT, // Default to input
            }
        );
    }

    /**
     * Check if widget type is a display-only widget
     * @private
     * @param {string} widgetType - Widget type name
     * @returns {boolean}
     */
    _isDisplayWidget(widgetType) {
        const config = this._getWidgetConfig(widgetType);
        return config.category === WidgetCategory.DISPLAY;
    }

    /**
     * Check if current item requires user confirmation before submitting
     * @private
     * @returns {boolean}
     */
    _requiresConfirmation() {
        const itemContext = stateManager.get(StateKeys.CURRENT_ITEM_CONTEXT);
        return itemContext?.requireUserConfirmation === true;
    }

    /**
     * Show a client action widget based on control.widget.render payload
     *
     * This is the main entry point for rendering widgets. It handles:
     * 1. Widget element creation with proper tag name
     * 2. Attribute mapping (stem → content/prompt, options, config)
     * 3. Event listener attachment based on widget category
     * 4. Adding navigation buttons for display widgets
     *
     * @param {Object} data - Widget data from server (control.widget.render payload)
     * @param {string} data.widgetType - Type of widget to render
     * @param {string} [data.widgetId] - Unique widget identifier
     * @param {string} [data.contentId] - Content identifier (fallback for widgetId)
     * @param {string} [data.itemId] - Parent item identifier
     * @param {string} [data.stem] - Question/prompt text or content
     * @param {Array} [data.options] - Options for choice-based widgets
     * @param {boolean} [data.required] - Whether response is required
     * @param {boolean} [data.skippable] - Whether widget can be skipped
     * @param {*} [data.initialValue] - Initial value for the widget
     * @param {Object} [data.widgetConfig] - Widget-specific configuration
     * @param {boolean} [data.showUserResponse] - Show user response in chat
     * @param {Function} [onResponse] - Response callback
     */
    showWidget(data, onResponse) {
        const { widgetType, widgetId, contentId, itemId, stem, options, required, skippable, initialValue, widgetConfig, showUserResponse } = data;

        this._showUserResponse = showUserResponse !== false;
        this._widgetCallback = onResponse;

        const config = this._getWidgetConfig(widgetType);
        const id = widgetId || contentId;

        console.log('[WidgetRenderer] showWidget:', {
            widgetType,
            category: config.category,
            widgetId: id,
            skippable,
            required,
        });

        // Create widget element from config
        const widget = document.createElement(config.tag);

        // Set common attributes
        if (id) {
            widget.setAttribute('content-id', id);
            widget.setAttribute('widget-id', id);
        }
        if (itemId) widget.setAttribute('item-id', itemId);
        if (widgetType) widget.setAttribute('widget-type', widgetType);

        // Handle stem/content based on widget configuration
        if (stem) {
            const stemAttr = config.stemAttribute || 'prompt';
            widget.setAttribute(stemAttr, stem);

            // Handle format attribute for widgets that support it
            if (config.formatAttribute && widgetConfig?.format) {
                widget.setAttribute(config.formatAttribute, widgetConfig.format);
            }
        }

        // Set required/skippable flags
        if (required) widget.setAttribute('required', '');
        if (skippable) widget.setAttribute('skippable', '');

        // Set initial value
        if (initialValue !== undefined) {
            widget.setAttribute('initial-value', JSON.stringify(initialValue));
        }

        // Set options for choice-based widgets
        if (options) {
            widget.setAttribute('options', JSON.stringify(options));
        }

        // Apply widget-specific configuration
        if (widgetConfig) {
            Object.entries(widgetConfig).forEach(([key, value]) => {
                // Skip format as it's handled separately via formatAttribute
                if (key === 'format' && config.formatAttribute) return;

                const attrName = key.replace(/_/g, '-');
                if (typeof value === 'object') {
                    widget.setAttribute(attrName, JSON.stringify(value));
                } else {
                    widget.setAttribute(attrName, String(value));
                }
            });
        }

        // Attach event listeners based on widget category and context
        const isConfirmButton = widgetType === 'button' && widgetConfig?.action === 'confirm';
        const needsConfirmation = this._requiresConfirmation();

        console.log('[WidgetRenderer] Event listener decision:', {
            widgetId: id,
            widgetType,
            isConfirmButton,
            needsConfirmation,
            category: config.category,
        });

        if (isConfirmButton) {
            // Confirmation button for batch submission
            widget.addEventListener('ax-submit', this._handleConfirmationSubmit);
            console.log('[WidgetRenderer] Attached ax-submit -> _handleConfirmationSubmit');
        } else if (config.category === WidgetCategory.DISPLAY) {
            // Display widgets don't need response handlers
            // Navigation is handled by the "Next" button added below
            console.log('[WidgetRenderer] Display widget - no response handlers attached');
        } else if (needsConfirmation) {
            // Store selections for later batch submission
            widget.addEventListener('ax-selection', this._handleWidgetSelection);
            widget.addEventListener('ax-response', this._handleWidgetSelection);
            widget.addEventListener('ax-submit', this._handleWidgetSelection);
            widget.addEventListener('ax-skip', this._handleWidgetSkip);
            console.log('[WidgetRenderer] Attached selection listeners for confirmation mode');
        } else {
            // Auto-submit on response
            widget.addEventListener('ax-response', this._handleWidgetSubmit);
            widget.addEventListener('ax-submit', this._handleWidgetSubmit);
            widget.addEventListener('ax-skip', this._handleWidgetSkip);
            console.log('[WidgetRenderer] Attached auto-submit listeners');
        }

        // Store the widget
        if (id) {
            this._renderedWidgets.set(id, widget);
            console.log('[WidgetRenderer] Stored widget in renderedWidgets:', id);
        }

        // Append widget to container
        this._messagesContainer?.appendChild(widget);
        console.log('[WidgetRenderer] Appended widget to container:', id);

        // For INPUT widgets that are skippable (but NOT in confirmation mode),
        // add a "Skip" link below the widget
        const isInputWidget = config.category === WidgetCategory.INPUT;
        const shouldAddSkipLink = isInputWidget && skippable && !needsConfirmation;

        if (shouldAddSkipLink) {
            console.log('[WidgetRenderer] Adding "Skip" link for skippable input widget:', id);
            this._addSkipLink(widget, id, itemId, widgetType);
        }

        // For display widgets, add a "Next" navigation button ONLY if:
        // 1. It's a display widget AND
        // 2. (skippable OR not required) AND
        // 3. NOT in confirmation mode (confirmation button handles advancement)
        const shouldAddNextButton = config.category === WidgetCategory.DISPLAY && (skippable || !required) && !needsConfirmation;

        if (shouldAddNextButton) {
            console.log('[WidgetRenderer] Adding "Next" button for display widget:', id);
            this._addDisplayNavigationButton(id, itemId, widgetType);
        } else {
            console.log('[WidgetRenderer] NOT adding "Next" button:', {
                category: config.category,
                skippable,
                required,
                needsConfirmation,
            });
        }

        scrollToBottom(this._messagesContainer);
        console.log('[WidgetRenderer] showWidget COMPLETE:', id);
    }

    /**
     * Add a "Next" navigation button for display widgets
     * @private
     * @param {string} widgetId - Parent widget ID
     * @param {string} itemId - Item ID
     * @param {string} widgetType - Widget type
     */
    _addDisplayNavigationButton(widgetId, itemId, widgetType) {
        console.log('[WidgetRenderer] _addDisplayNavigationButton START:', { widgetId, itemId, widgetType });
        const buttonId = `${widgetId}-next`;

        // Create navigation button
        const nextButton = document.createElement('ax-submit-button');
        nextButton.setAttribute('widget-id', buttonId);
        nextButton.setAttribute('content-id', buttonId);
        nextButton.setAttribute('item-id', itemId);
        nextButton.setAttribute('widget-type', 'button');
        nextButton.setAttribute('label', 'Next');
        nextButton.setAttribute('variant', 'primary');
        nextButton.setAttribute('size', 'md');

        // Store reference
        this._renderedWidgets.set(buttonId, nextButton);
        console.log('[WidgetRenderer] _addDisplayNavigationButton created button:', buttonId);

        // Handle click - submit acknowledgment and advance
        nextButton.addEventListener('ax-submit', () => {
            console.log('[WidgetRenderer] Display widget "Next" clicked:', widgetId);

            // Submit acknowledgment for the display widget
            if (itemId && widgetId) {
                submitWidgetResponse(itemId, widgetId, widgetType, { acknowledged: true });
            }

            // Clean up this widget and button
            this.hideWidget(widgetId);
            this.hideWidget(buttonId);

            // Emit response event
            eventBus.emit(Events.WIDGET_RESPONSE, { acknowledged: true, widgetId });
        });

        // Append button to container
        this._messagesContainer?.appendChild(nextButton);
    }

    /**
     * Add a "Skip" link below a skippable input widget
     * @private
     * @param {HTMLElement} widget - The widget element
     * @param {string} widgetId - Widget ID
     * @param {string} itemId - Item ID
     * @param {string} widgetType - Widget type
     */
    _addSkipLink(widget, widgetId, itemId, widgetType) {
        const skipLinkId = `${widgetId}-skip`;

        // Create skip link container
        const skipContainer = document.createElement('div');
        skipContainer.className = 'widget-skip-container';
        skipContainer.id = skipLinkId;
        skipContainer.innerHTML = `
            <div class="widget-skip-link-wrapper">
                <span class="widget-optional-badge">
                    <i class="bi bi-circle"></i> Optional
                </span>
                <button type="button" class="widget-skip-link">
                    Skip this question <i class="bi bi-chevron-right"></i>
                </button>
            </div>
        `;

        // Add styles if not already present
        if (!document.getElementById('widget-skip-styles')) {
            const style = document.createElement('style');
            style.id = 'widget-skip-styles';
            style.textContent = `
                .widget-skip-container {
                    margin-top: 0.5rem;
                    margin-bottom: 0.5rem;
                }
                .widget-skip-link-wrapper {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 0.5rem 0.75rem;
                    background: var(--bs-tertiary-bg, #f8f9fa);
                    border-radius: 6px;
                    font-size: 0.875rem;
                }
                [data-bs-theme="dark"] .widget-skip-link-wrapper {
                    background: var(--bs-tertiary-bg, #212529);
                }
                .widget-optional-badge {
                    color: var(--bs-secondary-color, #6c757d);
                    display: flex;
                    align-items: center;
                    gap: 0.35rem;
                }
                .widget-optional-badge i {
                    font-size: 0.65rem;
                }
                .widget-skip-link {
                    background: none;
                    border: none;
                    color: var(--bs-link-color, #0d6efd);
                    cursor: pointer;
                    padding: 0.25rem 0.5rem;
                    border-radius: 4px;
                    transition: background-color 0.15s ease;
                    display: flex;
                    align-items: center;
                    gap: 0.25rem;
                }
                .widget-skip-link:hover {
                    background: var(--bs-tertiary-bg, rgba(0,0,0,0.05));
                    text-decoration: underline;
                }
                .widget-skip-link i {
                    font-size: 0.75rem;
                }
            `;
            document.head.appendChild(style);
        }

        // Handle skip click
        skipContainer.querySelector('.widget-skip-link').addEventListener('click', () => {
            console.log('[WidgetRenderer] Skip link clicked:', widgetId);

            // Submit skip response
            if (itemId && widgetId) {
                submitWidgetResponse(itemId, widgetId, widgetType, { skipped: true });
            }

            // Clean up widget and skip link
            this.hideWidget(widgetId);
            skipContainer.remove();

            // Emit skip event
            eventBus.emit(Events.WIDGET_RESPONSE, { skipped: true, widgetId });
        });

        // Store reference for cleanup
        this._renderedWidgets.set(skipLinkId, skipContainer);

        // Append skip link after widget
        widget.insertAdjacentElement('afterend', skipContainer);
    }

    /**
     * Hide a specific widget by ID
     * @param {string} [widgetId] - Widget ID to hide
     */
    hideWidget(widgetId) {
        if (widgetId && this._renderedWidgets.has(widgetId)) {
            const widget = this._renderedWidgets.get(widgetId);
            widget.remove();
            this._renderedWidgets.delete(widgetId);
            this._pendingResponses.delete(widgetId);
        }
    }

    /**
     * Get a rendered widget element by ID
     * @param {string} widgetId - Widget ID
     * @returns {HTMLElement|null}
     */
    getWidget(widgetId) {
        return this._renderedWidgets.get(widgetId) || null;
    }

    /**
     * Get all pending responses
     * @returns {Map<string, Object>}
     */
    getPendingResponses() {
        return this._pendingResponses;
    }

    // =========================================================================
    // Widget Event Handlers
    // =========================================================================

    /**
     * Handle widget submission (auto-submit)
     * @private
     */
    _handleWidgetSubmit(event) {
        const widget = event.target;
        const widgetId = widget.getAttribute('widget-id') || widget.getAttribute('content-id');
        const widgetType = widget.getAttribute('widget-type') || 'unknown';
        const response = event.detail;

        console.log('[WidgetRenderer] Widget auto-submitted:', {
            widgetId,
            widgetType,
            response,
            eventType: event.type,
        });

        const itemContext = stateManager.get(StateKeys.CURRENT_ITEM_CONTEXT);
        const itemId = itemContext?.itemId;

        this.hideWidget(widgetId);

        const messageText = this._extractMessageText(response);

        if (this._showUserResponse) {
            const userBubble = document.createElement('chat-message');
            userBubble.setAttribute('role', 'user');
            userBubble.setAttribute('content', messageText);
            this._messagesContainer?.appendChild(userBubble);
        }

        this._showUserResponse = true;

        if (itemId) {
            submitWidgetResponse(itemId, widgetId, widgetType, response);
        } else {
            console.warn('[WidgetRenderer] No item context, falling back to sendMessage');
            sendMessage(messageText);
        }

        if (this._widgetCallback) {
            this._widgetCallback(response);
        }

        eventBus.emit(Events.WIDGET_RESPONSE, response);
    }

    /**
     * Handle widget skip
     * @private
     */
    _handleWidgetSkip(event) {
        const widget = event.target;
        const widgetId = widget.getAttribute('widget-id') || widget.getAttribute('content-id');

        console.log('[WidgetRenderer] Widget skipped:', widgetId);

        if (this._requiresConfirmation()) {
            if (widgetId) {
                this._pendingResponses.set(widgetId, { skipped: true });
            }
        } else {
            this.hideWidget(widgetId);
            sendMessage('[SKIPPED]');

            if (this._widgetCallback) {
                this._widgetCallback({ skipped: true });
            }

            eventBus.emit(Events.WIDGET_RESPONSE, { skipped: true });
        }
    }

    /**
     * Handle widget selection (when confirmation required)
     * @private
     */
    _handleWidgetSelection(event) {
        const widget = event.target;
        const widgetId = widget.getAttribute('widget-id') || widget.getAttribute('content-id');
        const response = event.detail;

        console.log('[WidgetRenderer] Widget selection event received:', {
            eventType: event.type,
            widgetId,
            widgetTagName: widget.tagName,
            response,
        });

        if (widgetId) {
            this._pendingResponses.set(widgetId, response);
            console.log('[WidgetRenderer] Response stored in _pendingResponses, current size:', this._pendingResponses.size);
        } else {
            console.warn('[WidgetRenderer] No widgetId found on element:', widget);
        }

        eventBus.emit(Events.WIDGET_SELECTION_CHANGED, { widgetId, response });
    }

    /**
     * Handle confirmation button click
     * @private
     */
    _handleConfirmationSubmit(event) {
        console.log('[WidgetRenderer] Confirmation button clicked');

        const itemContext = stateManager.get(StateKeys.CURRENT_ITEM_CONTEXT);
        const itemId = itemContext?.itemId;

        if (!itemId) {
            console.error('[WidgetRenderer] No item ID in context');
            return;
        }

        // Validate required widgets before collecting responses
        const validationErrors = [];
        this._renderedWidgets.forEach((widget, widgetId) => {
            const widgetType = widget?.getAttribute('widget-type');
            const config = this._getWidgetConfig(widgetType);

            // Skip display widgets and confirm buttons
            if (config.category === WidgetCategory.DISPLAY || widgetType === 'button') {
                return;
            }

            // Check if widget is required and validate
            const isRequired = widget.hasAttribute('required');
            if (isRequired && typeof widget.isValid === 'function') {
                const result = widget.isValid();
                if (!result.valid) {
                    validationErrors.push({ widgetId, widget, errors: result.errors });
                    // Show error on widget if it supports it
                    if (typeof widget.showError === 'function') {
                        widget.showError(result.errors[0] || 'This field is required');
                    }
                }
            } else if (isRequired && typeof widget.getValue === 'function') {
                // Fallback for widgets without isValid but with getValue
                const value = widget.getValue();
                if (value === null || value === undefined) {
                    validationErrors.push({ widgetId, widget, errors: ['This field is required'] });
                    if (typeof widget.showError === 'function') {
                        widget.showError('This field is required');
                    }
                }
            }
        });

        // If validation failed, don't submit
        if (validationErrors.length > 0) {
            console.warn('[WidgetRenderer] Validation failed:', validationErrors);

            // Reset the submit button so user can try again
            this._renderedWidgets.forEach((widget, widgetId) => {
                const widgetType = widget?.getAttribute('widget-type');
                if (widgetType === 'button' && typeof widget.reset === 'function') {
                    widget.reset();
                }
            });

            eventBus.emit(Events.WIDGET_VALIDATED, {
                valid: false,
                errors: validationErrors.flatMap(e => e.errors),
            });
            return;
        }

        // Collect responses from all rendered input widgets
        // This ensures we capture default values even if user didn't interact
        const responses = {};
        const combinedText = [];

        this._renderedWidgets.forEach((widget, widgetId) => {
            const widgetType = widget?.getAttribute('widget-type');
            const config = this._getWidgetConfig(widgetType);

            // Skip display widgets and confirm buttons
            if (config.category === WidgetCategory.DISPLAY || widgetType === 'button') {
                return;
            }

            // Clear any previous error states
            if (typeof widget.clearError === 'function') {
                widget.clearError();
            }

            // Check if we have a pending response from user interaction
            if (this._pendingResponses.has(widgetId)) {
                responses[widgetId] = this._pendingResponses.get(widgetId);
            } else if (typeof widget.getValue === 'function') {
                // Query widget for its current value (captures defaults)
                const value = widget.getValue();
                if (value !== null && value !== undefined) {
                    responses[widgetId] = { value, widgetId };
                    console.log('[WidgetRenderer] Captured default value for widget:', widgetId, value);
                }
            }
        });

        // Build combined text for user bubble
        Object.entries(responses).forEach(([widgetId, response]) => {
            if (!response.skipped) {
                combinedText.push(this._extractMessageText(response));
            }
        });

        console.log('[WidgetRenderer] Submitting responses:', responses);

        if (this._showUserResponse && combinedText.length > 0) {
            const userBubble = document.createElement('chat-message');
            userBubble.setAttribute('role', 'user');
            userBubble.setAttribute('content', combinedText.join('\n'));
            this._messagesContainer?.appendChild(userBubble);
        }

        this._showUserResponse = true;

        // Build batch response payload with widgetType for each widget
        const batchResponses = {};
        Object.entries(responses).forEach(([widgetId, response]) => {
            const widget = this._renderedWidgets.get(widgetId);
            const widgetType = widget?.getAttribute('widget-type') || 'unknown';
            batchResponses[widgetId] = {
                widgetType: widgetType,
                value: response,
            };
        });

        // Submit all responses in a single batch call
        submitBatchResponse(itemId, batchResponses);

        this.clearWidgets();

        eventBus.emit(Events.WIDGET_RESPONSE, { confirmed: true, responses });
    }

    // =========================================================================
    // Helper Methods
    // =========================================================================

    /**
     * Extract message text from widget response
     * @private
     */
    _extractMessageText(response) {
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

    /**
     * Set whether to show user response
     * @param {boolean} show - Whether to show
     */
    setShowUserResponse(show) {
        this._showUserResponse = show;
    }

    /**
     * Clear all widgets and pending responses
     * Call this when switching conversations or resetting state
     */
    clearWidgets() {
        // Remove all rendered widget elements from DOM
        this._renderedWidgets.forEach((widget, widgetId) => {
            if (widget && widget.parentNode) {
                widget.parentNode.removeChild(widget);
            }
        });

        // Clear internal state
        this._renderedWidgets.clear();
        this._pendingResponses.clear();
        this._widgetCallback = null;
        this._showUserResponse = true;

        console.log('[WidgetRenderer] Widgets cleared');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this.clearWidgets();
        this._messagesContainer = null;
        this._widgetCallback = null;
        this._initialized = false;
        console.log('[WidgetRenderer] Destroyed');
    }

    /**
     * Check if renderer is initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }
}

// Export singleton instance
export const widgetRenderer = new WidgetRenderer();
export default widgetRenderer;
