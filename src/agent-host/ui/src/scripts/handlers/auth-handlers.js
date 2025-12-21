/**
 * Authentication Event Handlers
 *
 * Handles auth-related events like state changes and session expiration.
 *
 * @module handlers/auth-handlers
 */

import { Events } from '../core/event-bus.js';
import { disconnect as wsDisconnect } from '../protocol/websocket-client.js';
import { getLoginUrl } from '../services/auth.js';

// =============================================================================
// Handler Functions (Factory Pattern)
// =============================================================================

/**
 * Handle auth state change - update UI visibility
 * @param {Object} context - ChatApp instance
 * @returns {Function} Handler function
 */
function handleAuthStateChanged(context) {
    return payload => {
        if (context.updateAuthUI) {
            context.updateAuthUI(payload.isAuthenticated);
        }
    };
}

/**
 * Handle session expiration
 * Disconnects WebSocket and redirects to login page
 * @param {Object} context - ChatApp instance
 * @returns {Function} Handler function
 */
function handleSessionExpired(context) {
    return () => {
        console.log('[AuthHandlers] Session expired, disconnecting WebSocket and redirecting to login');

        // Disconnect WebSocket connection if active
        wsDisconnect();

        // Call context handler for UI cleanup
        if (context.handleSessionExpired) {
            context.handleSessionExpired();
        }

        // Redirect to login page after a short delay for UI feedback
        setTimeout(() => {
            window.location.href = getLoginUrl();
        }, 1500);
    };
}

// =============================================================================
// Handler Registrations
// =============================================================================

/**
 * Exported handlers for registry auto-discovery.
 * Each entry maps an event to its handler function.
 *
 * @type {import('./index.js').HandlerRegistration[]}
 */
export const handlers = [
    {
        event: Events.AUTH_STATE_CHANGED,
        handler: handleAuthStateChanged,
        description: 'Update UI based on authentication state',
    },
    {
        event: Events.AUTH_SESSION_EXPIRED,
        handler: handleSessionExpired,
        description: 'Handle session expiration cleanup',
    },
];

export default handlers;
