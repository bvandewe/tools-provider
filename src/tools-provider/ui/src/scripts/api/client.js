/**
 * API Client Module
 * Handles all HTTP requests to the backend API
 */

// Track if we've already triggered the session expired handler
let sessionExpiredShown = false;

// Track if user was authenticated (set after successful checkAuth)
let wasAuthenticated = false;

/**
 * Check if user is currently authenticated
 * Pages can use this to avoid making API calls when not logged in
 * @returns {boolean}
 */
export function isAuthenticated() {
    return wasAuthenticated;
}

/**
 * Make an authenticated API request
 * @param {string} url - The API endpoint URL
 * @param {Object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise<Response>} - The fetch response
 */
export async function apiRequest(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include', // Always send cookies
    });

    if (response.status === 401) {
        // Only trigger session expired if user WAS authenticated
        // This prevents redirect loops on initial page load
        if (wasAuthenticated) {
            handleSessionExpired();
        }
        throw new Error('Session expired');
    }

    return response;
}

/**
 * Make an API request and return JSON
 * @param {string} url - The API endpoint URL
 * @param {Object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise<Object>} - The parsed JSON response
 */
export async function apiRequestJson(url, options = {}) {
    const response = await apiRequest(url, options);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || error.message || `HTTP ${response.status}`);
    }

    // Handle 204 No Content
    if (response.status === 204) {
        return null;
    }

    return response.json();
}

/**
 * Handle session expiration
 * When session expires (401), perform full logout from Keycloak.
 * No modal overlay - user is fully logged out and redirected.
 */
async function handleSessionExpired() {
    if (sessionExpiredShown) return;
    sessionExpiredShown = true;

    console.log('[APIClient] Session expired - performing full logout');

    // Stop session monitoring if active
    try {
        const { stopSessionMonitoring } = await import('../core/session-manager.js');
        stopSessionMonitoring();
    } catch {
        // Session manager not available, continue
    }

    // Disconnect from SSE if connected
    try {
        const { eventBus } = await import('../core/event-bus.js');
        eventBus.disconnect();
    } catch {
        // Event bus not available, continue
    }

    // Redirect to Keycloak logout endpoint for full logout
    // This will clear the session cookie, logout from Keycloak, and redirect back to login
    window.location.href = '/api/auth/logout';
}

/**
 * Reset session expired state (call after successful login)
 */
export function resetSessionExpiredState() {
    sessionExpiredShown = false;
}

/**
 * Check if user is authenticated
 * @returns {Promise<Object|null>} - User object or null
 */
export async function checkAuth() {
    try {
        const response = await fetch('/api/auth/user', {
            credentials: 'include', // Send session cookie
        });

        if (response.ok) {
            const user = await response.json();
            resetSessionExpiredState(); // Reset state on successful auth
            wasAuthenticated = true; // Mark that user is now authenticated
            return user;
        }

        // Not authenticated - reset the flag
        wasAuthenticated = false;
        return null;
    } catch {
        wasAuthenticated = false;
        return null;
    }
}
