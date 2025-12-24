/**
 * AuthService - Authentication and Session Management
 *
 * Handles OAuth2/Keycloak authentication flows and session monitoring.
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

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._isAuthenticated = false;
        this._currentUser = null;
        this._initialized = false;
        console.log('[AuthService] Destroyed');
    }

    // =========================================================================
    // Authentication Check
    // =========================================================================

    /**
     * Check if user is authenticated
     * @returns {Promise<{isAuthenticated: boolean, user: Object|null}>}
     */
    async checkAuth() {
        console.log('[AuthService] Checking authentication...');

        try {
            const data = await apiService.checkAuth();
            this._isAuthenticated = true;
            this._currentUser = data.user;

            stateManager.set(StateKeys.IS_AUTHENTICATED, true);
            stateManager.set(StateKeys.CURRENT_USER, data.user);
            stateManager.set(StateKeys.IS_ADMIN, this.isAdmin());

            console.log('[AuthService] Authenticated as:', data.user.preferred_username || data.user.email);

            eventBus.emit(Events.AUTH_STATE_CHANGED, {
                isAuthenticated: true,
                user: data.user,
                isAdmin: this.isAdmin(),
            });

            return { isAuthenticated: true, user: data.user };
        } catch (error) {
            console.log('[AuthService] Not authenticated');
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
    // Authentication State
    // =========================================================================

    /**
     * Check if user is authenticated
     * @returns {boolean}
     */
    isAuthenticated() {
        return this._isAuthenticated;
    }

    /**
     * Get current user
     * @returns {Object|null}
     */
    getCurrentUser() {
        return this._currentUser;
    }

    /**
     * Check if current user has admin role
     * @returns {boolean}
     */
    isAdmin() {
        if (!this._currentUser) return false;

        // Try different role locations (Keycloak formats)
        let roles = this._currentUser.roles || [];

        if (!roles.length && this._currentUser.realm_access) {
            roles = this._currentUser.realm_access.roles || [];
        }

        return roles.includes('admin');
    }

    // =========================================================================
    // Session Management
    // =========================================================================

    /**
     * Handle session expiration
     * @private
     */
    _handleSessionExpired() {
        console.log('[AuthService] Session expired');
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
    }

    /**
     * Get login URL
     * @returns {string}
     */
    getLoginUrl() {
        return '/api/auth/login';
    }

    /**
     * Get logout URL
     * @returns {string}
     */
    getLogoutUrl() {
        return '/api/auth/logout';
    }

    /**
     * Redirect to login page
     */
    redirectToLogin() {
        window.location.href = this.getLoginUrl();
    }

    /**
     * Redirect to logout
     */
    redirectToLogout() {
        window.location.href = this.getLogoutUrl();
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const authService = new AuthService();
