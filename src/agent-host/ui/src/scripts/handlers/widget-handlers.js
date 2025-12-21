/**
 * Widget Event Handlers
 *
 * Handles widget-related events (rendered, response, validated).
 *
 * @module handlers/widget-handlers
 */

import { Events } from '../core/event-bus.js';

// =============================================================================
// Handler Functions
// =============================================================================

/**
 * Handle widget response - log only (actual submission is handled by widget-renderer via submitWidgetResponse)
 * @param {Object} response - Widget response payload
 */
function handleWidgetResponse(response) {
    // NOTE: Submissions are now handled directly by widget-renderer.js using submitWidgetResponse()
    // which sends data.response.submit. This handler is kept for logging/analytics only.
    console.log('[WidgetHandlers] Widget response event received:', response);
}

/**
 * Handle widget rendered - for analytics or logging
 * @param {Object} payload - Event payload
 * @param {string} payload.widgetType - Type of widget rendered
 * @param {string} payload.widgetId - Widget ID
 */
function handleWidgetRendered({ widgetType, widgetId }) {
    console.debug('[WidgetHandlers] Widget rendered:', widgetType, widgetId);
}

/**
 * Handle widget validated
 * @param {Object} payload - Event payload
 * @param {string} payload.widgetId - Widget ID
 * @param {boolean} payload.isValid - Validation result
 * @param {string[]} [payload.errors] - Validation errors
 */
function handleWidgetValidated({ widgetId, isValid, errors }) {
    if (!isValid) {
        console.debug('[WidgetHandlers] Widget validation failed:', widgetId, errors);
    }
}

// =============================================================================
// Handler Registrations
// =============================================================================

/**
 * Exported handlers for registry auto-discovery.
 * @type {import('./index.js').HandlerRegistration[]}
 */
export const handlers = [
    {
        event: Events.WIDGET_RESPONSE,
        handler: handleWidgetResponse,
        description: 'Send widget response via WebSocket',
        isFactory: false,
    },
    {
        event: Events.WIDGET_RENDERED,
        handler: handleWidgetRendered,
        description: 'Log widget render events',
        isFactory: false,
    },
    {
        event: Events.WIDGET_VALIDATED,
        handler: handleWidgetValidated,
        description: 'Handle widget validation results',
        isFactory: false,
    },
];

export default handlers;
