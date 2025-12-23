/**
 * AuthHandlers - Authentication Event Handler Class
 *
 * Handles auth-related events like state changes and session expiration.
 * Uses dependency injection via imported singletons instead of factory pattern.
 *
 * @module handlers/AuthHandlers
 */

import { Events, eventBus } from '../core/event-bus.js';
import { disconnect as wsDisconnect } from '../protocol/websocket-client.js';
import { authService } from '../services/AuthService.js';
import { showToast } from '../services/modals.js';

/**
 * AuthHandlers manages event handlers for authentication events
 */
export class AuthHandlers {
    /**
     * Create a new AuthHandlers instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Function[]} */
        this._unsubscribers = [];

        /** @type {boolean} Guard against multiple redirects */
        this._isRedirecting = false;

        // Bind handlers
        this._handleAuthStateChanged = this._handleAuthStateChanged.bind(this);
        this._handleSessionExpired = this._handleSessionExpired.bind(this);
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize and register event handlers
     */
    init() {
        if (this._initialized) {
            console.warn('[AuthHandlers] Already initialized');
            return;
        }

        this._subscribeToEvents();
        this._initialized = true;

        console.log('[AuthHandlers] Initialized');
    }

    /**
     * Subscribe to events
     * @private
     */
    _subscribeToEvents() {
        this._unsubscribers.push(eventBus.on(Events.AUTH_STATE_CHANGED, this._handleAuthStateChanged));

        this._unsubscribers.push(eventBus.on(Events.AUTH_SESSION_EXPIRED, this._handleSessionExpired));
    }

    // =========================================================================
    // Event Handlers
    // =========================================================================

    /**
     * Handle auth state change - update UI visibility
     * @private
     * @param {Object} payload - Event payload
     */
    _handleAuthStateChanged(payload) {
        console.log('[AuthHandlers] Auth state changed:', { isAuthenticated: payload.isAuthenticated });

        // Emit UI update event for components to respond
        eventBus.emit(Events.UI_STATUS_CHANGED, {
            status: payload.isAuthenticated ? 'authenticated' : 'unauthenticated',
            message: payload.isAuthenticated ? 'Authenticated' : 'Not authenticated',
        });
    }

    /**
     * Handle session expiration
     * Disconnects WebSocket and redirects to login page
     * @private
     */
    _handleSessionExpired() {
        // Guard against multiple redirects (can happen if multiple 401s occur)
        if (this._isRedirecting) {
            console.log('[AuthHandlers] Already redirecting, ignoring duplicate session expired event');
            return;
        }
        this._isRedirecting = true;

        console.log('[AuthHandlers] Session expired, disconnecting WebSocket and redirecting to login');

        // Show toast notification
        showToast('Session expired. Redirecting to login...', 'warning');

        // Disconnect WebSocket connection if active
        wsDisconnect();

        // Redirect to login page after a short delay for UI feedback
        setTimeout(() => {
            window.location.href = authService.getLoginUrl();
        }, 1500);
    }

    // =========================================================================
    // Cleanup
    // =========================================================================

    /**
     * Cleanup resources
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._isRedirecting = false;
        this._initialized = false;
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const authHandlers = new AuthHandlers();

// =============================================================================
// Legacy Compatibility - Handler Registrations for old index.js
// These are kept for backward compatibility during migration
// =============================================================================

/**
 * @deprecated Use authHandlers.init() instead
 * Legacy factory handlers for registry auto-discovery.
 */
export const handlers = [
    {
        event: Events.AUTH_STATE_CHANGED,
        handler: context => payload => {
            console.warn('[AuthHandlers] DEPRECATED: Using legacy factory pattern');
            authHandlers._handleAuthStateChanged(payload);
        },
        description: 'Update UI based on authentication state',
        isFactory: true,
    },
    {
        event: Events.AUTH_SESSION_EXPIRED,
        handler: context => () => {
            console.warn('[AuthHandlers] DEPRECATED: Using legacy factory pattern');
            authHandlers._handleSessionExpired();
        },
        description: 'Handle session expiration cleanup',
        isFactory: true,
    },
];

export default handlers;
