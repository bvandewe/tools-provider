/**
 * Widget Event Handlers (Class-based)
 *
 * Handles widget-related events using class-based architecture
 * with dependency injection via imported singletons.
 *
 * @module handlers/WidgetHandlers
 */

import { Events, eventBus } from '../core/event-bus.js';

/**
 * @class WidgetHandlers
 * @description Handles all widget-related events (rendered, response, validated)
 */
export class WidgetHandlers {
    /**
     * Create WidgetHandlers instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Function[]} */
        this._unsubscribers = [];

        // Bind methods to preserve context
        this._handleWidgetResponse = this._handleWidgetResponse.bind(this);
        this._handleWidgetRendered = this._handleWidgetRendered.bind(this);
        this._handleWidgetValidated = this._handleWidgetValidated.bind(this);
    }

    /**
     * Initialize handlers and subscribe to events
     * @returns {void}
     */
    init() {
        if (this._initialized) {
            console.warn('[WidgetHandlers] Already initialized');
            return;
        }

        this._subscribeToEvents();
        this._initialized = true;
        console.log('[WidgetHandlers] Initialized');
    }

    /**
     * Subscribe to EventBus events
     * @private
     */
    _subscribeToEvents() {
        this._unsubscribers.push(
            eventBus.on(Events.WIDGET_RESPONSE, this._handleWidgetResponse),
            eventBus.on(Events.WIDGET_RENDERED, this._handleWidgetRendered),
            eventBus.on(Events.WIDGET_VALIDATED, this._handleWidgetValidated)
        );
    }

    /**
     * Handle widget response event
     * NOTE: Submissions are now handled directly by widget-renderer.js using submitWidgetResponse()
     * which sends data.response.submit. This handler is kept for logging/analytics only.
     *
     * @private
     * @param {Object} response - Widget response payload
     */
    _handleWidgetResponse(response) {
        console.log('[WidgetHandlers] Widget response event received:', response);

        // Analytics/logging hook - actual submission is handled elsewhere
    }

    /**
     * Handle widget rendered event - for analytics or logging
     * @private
     * @param {Object} payload - Event payload
     * @param {string} payload.widgetType - Type of widget rendered
     * @param {string} payload.widgetId - Widget ID
     */
    _handleWidgetRendered({ widgetType, widgetId }) {
        console.debug('[WidgetHandlers] Widget rendered:', widgetType, widgetId);

        // Could emit analytics event here
    }

    /**
     * Handle widget validated event
     * @private
     * @param {Object} payload - Event payload
     * @param {string} payload.widgetId - Widget ID
     * @param {boolean} payload.isValid - Validation result
     * @param {string[]} [payload.errors] - Validation errors
     */
    _handleWidgetValidated({ widgetId, isValid, errors }) {
        if (!isValid) {
            console.debug('[WidgetHandlers] Widget validation failed:', widgetId, errors);
        }

        // Could emit analytics event for validation failures
    }

    /**
     * Cleanup and unsubscribe from events
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._initialized = false;
        console.log('[WidgetHandlers] Destroyed');
    }

    /**
     * Check if handlers are initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }
}

// Export singleton instance
export const widgetHandlers = new WidgetHandlers();
export default widgetHandlers;
