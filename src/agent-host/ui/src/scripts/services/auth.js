/**
 * Auth Service - Authentication and session management
 *
 * Handles OAuth2/Keycloak authentication flows, session monitoring,
 * and user permission checking.
 *
 * @module services/auth
 */

import { api } from './api.js';
import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';

// =============================================================================
// Auth State
// =============================================================================

let authState = {
    isAuthenticated: false,
    currentUser: null,
    sessionCheckInterval: null,
    sessionExpiryTime: null,
};

// =============================================================================
// Session Check
// =============================================================================

/**
 * Check if user is authenticated
 * @returns {Promise<{isAuthenticated: boolean, user: Object|null}>}
 */
export async function checkAuth() {
    try {
        const data = await api.checkAuth();
        authState.isAuthenticated = true;
        authState.currentUser = data.user;

        stateManager.set(StateKeys.IS_AUTHENTICATED, true);
        stateManager.set(StateKeys.CURRENT_USER, data.user);
        stateManager.set(StateKeys.IS_ADMIN, isAdmin());

        eventBus.emit(Events.AUTH_STATE_CHANGED, {
            isAuthenticated: true,
            user: data.user,
            isAdmin: isAdmin(),
        });

        return { isAuthenticated: true, user: data.user };
    } catch (error) {
        console.error('Auth check failed:', error);
        authState.isAuthenticated = false;
        authState.currentUser = null;

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

// =============================================================================
// User Info
// =============================================================================

/**
 * Get current user
 * @returns {Object|null} Current user or null
 */
export function getCurrentUser() {
    return authState.currentUser;
}

/**
 * Check if user is authenticated
 * @returns {boolean}
 */
export function isAuthenticated() {
    return authState.isAuthenticated;
}

/**
 * Check if current user has admin role
 * @returns {boolean}
 */
export function isAdmin() {
    const user = authState.currentUser;
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
export function getUserScopes() {
    const user = authState.currentUser;
    if (!user) return [];
    return user.scope || [];
}

/**
 * Get user display name
 * @returns {string} User name or 'User'
 */
export function getUserDisplayName() {
    const user = authState.currentUser;
    if (!user) return 'User';
    return user.name || user.username || 'User';
}

// =============================================================================
// Session Monitoring
// =============================================================================

/**
 * Start session monitoring
 * Periodically checks if session is still valid
 * @param {Function} [onExpired] - Callback when session expires
 * @param {Function} [beforeRedirect] - Callback before redirect (unused, for API compat)
 * @param {number} [intervalMs=60000] - Check interval in milliseconds
 */
export function startSessionMonitoring(onExpired = null, beforeRedirect = null, intervalMs = 60000) {
    stopSessionMonitoring();

    // Store the callback for later use
    const handleExpired = onExpired || handleSessionExpired;

    authState.sessionCheckInterval = setInterval(async () => {
        try {
            await api.checkAuth();
        } catch (error) {
            console.warn('[Auth] Session check failed:', error);
            handleExpired();
        }
    }, intervalMs);

    console.log(`[Auth] Session monitoring started (interval: ${intervalMs}ms)`);
}

/**
 * Stop session monitoring
 */
export function stopSessionMonitoring() {
    if (authState.sessionCheckInterval) {
        clearInterval(authState.sessionCheckInterval);
        authState.sessionCheckInterval = null;
    }
}

/**
 * Handle session expiration
 */
export function handleSessionExpired() {
    authState.isAuthenticated = false;
    authState.currentUser = null;
    stopSessionMonitoring();

    stateManager.set(StateKeys.IS_AUTHENTICATED, false);
    stateManager.set(StateKeys.CURRENT_USER, null);
    stateManager.set(StateKeys.IS_ADMIN, false);

    eventBus.emit(Events.AUTH_SESSION_EXPIRED);
}

/**
 * Set unauthorized handler on API
 * @param {Function} handler - Handler for 401 responses
 */
export function setUnauthorizedHandler(handler) {
    api.setUnauthorizedHandler(handler);
}

// =============================================================================
// Auth Actions
// =============================================================================

/**
 * Logout current user
 */
export function logout() {
    stopSessionMonitoring();
    api.logout();
}

/**
 * Get login URL
 * @returns {string} Login endpoint URL
 */
export function getLoginUrl() {
    return '/api/auth/login';
}

/**
 * Get logout URL
 * @returns {string} Logout endpoint URL
 */
export function getLogoutUrl() {
    return '/api/auth/logout';
}

export default {
    checkAuth,
    getCurrentUser,
    isAuthenticated,
    isAdmin,
    getUserScopes,
    getUserDisplayName,
    startSessionMonitoring,
    stopSessionMonitoring,
    handleSessionExpired,
    setUnauthorizedHandler,
    logout,
    getLoginUrl,
    getLogoutUrl,
};
