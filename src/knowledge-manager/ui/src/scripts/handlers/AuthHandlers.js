/**
 * AuthHandlers - Authentication Event Handler Class
 *
 * Handles auth-related events like state changes and session expiration.
 *
 * @module handlers/AuthHandlers
 */

import { Events, eventBus } from '../core/event-bus.js';
import { uiManager } from '../managers/UIManager.js';
import { modalService } from '../services/ModalService.js';

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
     * Cleanup and destroy
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._isRedirecting = false;
        this._initialized = false;
        console.log('[AuthHandlers] Destroyed');
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

        // Update UI via UIManager
        uiManager.updateAuthUI(payload.isAuthenticated, payload.user, payload.isAdmin);

        // Emit UI update event for components to respond
        eventBus.emit(Events.UI_STATUS_CHANGED, {
            status: payload.isAuthenticated ? 'authenticated' : 'unauthenticated',
            message: payload.isAuthenticated ? 'Authenticated' : 'Not authenticated',
        });
    }

    /**
     * Handle session expiration
     * @private
     */
    _handleSessionExpired() {
        // Guard against multiple redirects
        if (this._isRedirecting) {
            console.log('[AuthHandlers] Already redirecting, ignoring duplicate session expired event');
            return;
        }

        console.log('[AuthHandlers] Session expired');

        // Show toast notification
        modalService.warning('Your session has expired. Please log in again.');

        // Update UI to show unauthenticated state
        uiManager.updateAuthUI(false, null, false);
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const authHandlers = new AuthHandlers();
