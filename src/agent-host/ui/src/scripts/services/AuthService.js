/**
 * AuthService - Authentication and Session Management
 *
 * Handles OAuth2/Keycloak authentication flows, session monitoring,
 * and user permission checking.
 *
 * @module services/AuthService
 */

import { apiService } from './ApiService.js';
import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';

/**
 * AuthService manages authentication state and session lifecycle
 */
export class AuthService {
    /**
     * Create a new AuthService instance
     */
    constructor() {
        /** @type {boolean} */
        this._isAuthenticated = false;

        /** @type {Object|null} */
        this._currentUser = null;

        /** @type {number|null} */
        this._sessionCheckInterval = null;

        /** @type {number|null} */
        this._sessionExpiryTime = null;

        /** @type {boolean} */
        this._initialized = false;

        // Bind methods for callbacks
        this._handleSessionExpired = this._handleSessionExpired.bind(this);
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize the auth service
     */
    init() {
        if (this._initialized) {
            console.warn('[AuthService] Already initialized');
            return;
        }

        this._initialized = true;
        console.log('[AuthService] Initialized');
    }

    // =========================================================================
    // Authentication Check
    // =========================================================================

    /**
     * Check if user is authenticated
     * @returns {Promise<{isAuthenticated: boolean, user: Object|null}>}
     */
    async checkAuth() {
        try {
            const data = await apiService.checkAuth();
            this._isAuthenticated = true;
            this._currentUser = data.user;

            stateManager.set(StateKeys.IS_AUTHENTICATED, true);
            stateManager.set(StateKeys.CURRENT_USER, data.user);
            stateManager.set(StateKeys.IS_ADMIN, this.isAdmin());

            eventBus.emit(Events.AUTH_STATE_CHANGED, {
                isAuthenticated: true,
                user: data.user,
                isAdmin: this.isAdmin(),
            });

            return { isAuthenticated: true, user: data.user };
        } catch (error) {
            console.error('[AuthService] Auth check failed:', error);
            this._isAuthenticated = false;
            this._currentUser = null;

            stateManager.set(StateKeys.IS_AUTHENTICATED, false);
            stateManager.set(StateKeys.CURRENT_USER, null);
            stateManager.set(StateKeys.IS_ADMIN, false);

            eventBus.emit(Events.AUTH_STATE_CHANGED, {
                isAuthenticated: false,
                user: null,
                isAdmin: false,
            });

            return { isAuthenticated: false, user: null };
        }
    }

    // =========================================================================
    // User Info Getters
    // =========================================================================

    /**
     * Get current user
     * @returns {Object|null} Current user or null
     */
    getCurrentUser() {
        return this._currentUser;
    }

    /**
     * Check if user is authenticated
     * @returns {boolean}
     */
    isAuthenticated() {
        return this._isAuthenticated;
    }

    /**
     * Check if current user has admin role
     * @returns {boolean}
     */
    isAdmin() {
        const user = this._currentUser;
        if (!user) return false;

        // Try different role locations (Keycloak formats)
        let roles = user.roles || [];

        if (!roles.length && user.realm_access) {
            roles = user.realm_access.roles || [];
        }

        if (!roles.length && user.resource_access?.account) {
            roles = user.resource_access.account.roles || [];
        }

        return roles.includes('admin');
    }

    /**
     * Get user's OAuth2 scopes
     * @returns {string[]} Array of scope strings
     */
    getUserScopes() {
        const user = this._currentUser;
        if (!user) return [];
        return user.scope || [];
    }

    /**
     * Get user display name
     * @returns {string} User name or 'User'
     */
    getUserDisplayName() {
        const user = this._currentUser;
        if (!user) return 'User';
        return user.name || user.username || 'User';
    }

    // =========================================================================
    // Session Monitoring
    // =========================================================================

    /**
     * Start session monitoring
     * Periodically checks if session is still valid
     * @param {Function} [onExpired] - Callback when session expires
     * @param {Function} [beforeRedirect] - Callback before redirect (unused, for API compat)
     * @param {number} [intervalMs=60000] - Check interval in milliseconds
     */
    startSessionMonitoring(onExpired = null, beforeRedirect = null, intervalMs = 60000) {
        this.stopSessionMonitoring();

        // Store the callback for later use
        const handleExpired = onExpired || this._handleSessionExpired;

        this._sessionCheckInterval = setInterval(async () => {
            try {
                await apiService.checkAuth();
            } catch (error) {
                console.warn('[AuthService] Session check failed:', error);
                handleExpired();
            }
        }, intervalMs);

        console.log(`[AuthService] Session monitoring started (interval: ${intervalMs}ms)`);
    }

    /**
     * Stop session monitoring
     */
    stopSessionMonitoring() {
        if (this._sessionCheckInterval) {
            clearInterval(this._sessionCheckInterval);
            this._sessionCheckInterval = null;
        }
    }

    /**
     * Handle session expiration
     * @private
     */
    _handleSessionExpired() {
        this._isAuthenticated = false;
        this._currentUser = null;
        this.stopSessionMonitoring();

        stateManager.set(StateKeys.IS_AUTHENTICATED, false);
        stateManager.set(StateKeys.CURRENT_USER, null);
        stateManager.set(StateKeys.IS_ADMIN, false);

        eventBus.emit(Events.AUTH_SESSION_EXPIRED);
    }

    /**
     * Set unauthorized handler on API
     * @param {Function} handler - Handler for 401 responses
     */
    setUnauthorizedHandler(handler) {
        apiService.setUnauthorizedHandler(handler);
    }

    // =========================================================================
    // Auth Actions
    // =========================================================================

    /**
     * Logout current user
     */
    logout() {
        this.stopSessionMonitoring();
        apiService.logout();
    }

    /**
     * Get login URL
     * @param {string} [returnUrl] - URL to return to after login
     * @returns {string} Login URL
     */
    getLoginUrl(returnUrl = null) {
        const base = '/api/auth/login';
        if (returnUrl) {
            return `${base}?return_url=${encodeURIComponent(returnUrl)}`;
        }
        return base;
    }

    /**
     * Get logout URL
     * @returns {string} Logout URL
     */
    getLogoutUrl() {
        return '/api/auth/logout';
    }

    // =========================================================================
    // Cleanup
    // =========================================================================

    /**
     * Cleanup resources
     */
    destroy() {
        this.stopSessionMonitoring();
        this._isAuthenticated = false;
        this._currentUser = null;
        this._initialized = false;
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const authService = new AuthService();
