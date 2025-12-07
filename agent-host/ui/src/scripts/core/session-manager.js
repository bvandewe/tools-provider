/**
 * Session Manager for Agent Host
 *
 * Implements comprehensive session lifecycle management:
 * - Activity tracking (mouse, keyboard, touch, scroll, click)
 * - Idle timeout detection with warning modal
 * - Background token refresh when user is active
 * - OIDC Session Management iframe for cross-app synchronization
 * - Keycloak logout on session expiration
 *
 * Session settings are fetched from Keycloak via the backend.
 *
 * Note: This implementation does NOT use keycloak-js to avoid bundler
 * compatibility issues. Instead, it implements the OIDC Session Management
 * iframe manually using the postMessage API.
 */

import * as bootstrap from 'bootstrap';
import { showToast } from '../services/modals.js';

// =============================================================================
// Configuration (loaded from backend)
// =============================================================================

let config = {
    keycloakUrl: '',
    realm: '',
    clientId: '',
    ssoSessionIdleTimeoutSeconds: 1800, // 30 minutes default
    sessionExpirationWarningMinutes: 2, // Show warning 2 minutes before expiry
    checkSessionIframe: null,
};

// =============================================================================
// State
// =============================================================================

let sessionIframe = null;
let sessionCheckInterval = null;
let lastActivityTime = Date.now();
let idleCheckInterval = null;
let tokenRefreshInterval = null;
let warningModal = null;
let warningCountdownInterval = null;
let isWarningShown = false;
let isPaused = false; // Paused when warning is shown
let isInitialized = false;

// Callback for session expiration
let onSessionExpiredCallback = null;

// Activity events to track
const ACTIVITY_EVENTS = ['mousedown', 'mousemove', 'keydown', 'keypress', 'scroll', 'touchstart', 'touchmove', 'click', 'focus'];

// =============================================================================
// Activity Tracking
// =============================================================================

/**
 * Record user activity - resets the idle timer
 */
function recordActivity() {
    lastActivityTime = Date.now();
}

/**
 * Get idle time in seconds
 */
function getIdleTimeSeconds() {
    return (Date.now() - lastActivityTime) / 1000;
}

/**
 * Get idle time in minutes
 */
function getIdleTimeMinutes() {
    return getIdleTimeSeconds() / 60;
}

/**
 * Start tracking user activity
 */
function startActivityTracking() {
    ACTIVITY_EVENTS.forEach(event => {
        document.addEventListener(event, recordActivity, { passive: true });
    });
    console.log('[SessionManager] Activity tracking started');
}

/**
 * Stop tracking user activity
 */
function stopActivityTracking() {
    ACTIVITY_EVENTS.forEach(event => {
        document.removeEventListener(event, recordActivity);
    });
    console.log('[SessionManager] Activity tracking stopped');
}

// =============================================================================
// Token Refresh (Silent Refresh)
// =============================================================================

/**
 * Perform a silent token refresh
 * This keeps the Keycloak session alive when the user is active
 */
async function performTokenRefresh() {
    if (isPaused) {
        console.log('[SessionManager] Token refresh skipped - session paused (warning shown)');
        return false;
    }

    try {
        const response = await fetch('/api/auth/refresh', {
            method: 'POST',
            credentials: 'include',
        });

        if (response.ok) {
            console.log('[SessionManager] Token refreshed successfully');
            return true;
        } else if (response.status === 401) {
            console.log('[SessionManager] Token refresh failed - session expired at Keycloak');
            handleSessionExpired();
            return false;
        } else {
            console.warn('[SessionManager] Token refresh failed:', response.status);
            return false;
        }
    } catch (error) {
        console.error('[SessionManager] Token refresh error:', error);
        return false;
    }
}

/**
 * Start background token refresh (every 4 minutes when active)
 * Access tokens are typically 5 minutes, so refresh at 4 minutes
 */
function startTokenRefresh() {
    // Refresh every 4 minutes (240 seconds) if user is active
    const REFRESH_INTERVAL_MS = 4 * 60 * 1000;

    tokenRefreshInterval = setInterval(async () => {
        // Only refresh if user was recently active (within last 5 minutes)
        const idleMinutes = getIdleTimeMinutes();
        if (idleMinutes < 5 && !isPaused) {
            await performTokenRefresh();
        }
    }, REFRESH_INTERVAL_MS);

    console.log('[SessionManager] Token refresh started (every 4 minutes when active)');
}

/**
 * Stop background token refresh
 */
function stopTokenRefresh() {
    if (tokenRefreshInterval) {
        clearInterval(tokenRefreshInterval);
        tokenRefreshInterval = null;
    }
}

// =============================================================================
// Idle Detection & Warning Modal
// =============================================================================

/**
 * Check if user is idle and should be warned
 */
function checkIdleStatus() {
    if (isPaused || isWarningShown) {
        return;
    }

    const idleSeconds = getIdleTimeSeconds();
    const warningThresholdSeconds = config.ssoSessionIdleTimeoutSeconds - config.sessionExpirationWarningMinutes * 60;

    if (idleSeconds >= warningThresholdSeconds) {
        showIdleWarning();
    }
}

/**
 * Show the idle warning modal
 */
function showIdleWarning() {
    if (isWarningShown) return;

    isWarningShown = true;
    isPaused = true; // Pause token refresh

    const remainingSeconds = Math.max(0, config.ssoSessionIdleTimeoutSeconds - getIdleTimeSeconds());

    // Create modal if it doesn't exist
    let modalEl = document.getElementById('session-warning-modal');
    if (!modalEl) {
        modalEl = document.createElement('div');
        modalEl.id = 'session-warning-modal';
        modalEl.className = 'modal fade';
        modalEl.setAttribute('tabindex', '-1');
        modalEl.setAttribute('aria-labelledby', 'sessionWarningLabel');
        modalEl.setAttribute('data-bs-backdrop', 'static');
        modalEl.setAttribute('data-bs-keyboard', 'false');
        modalEl.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title" id="sessionWarningLabel">
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            Session Expiring Soon
                        </h5>
                    </div>
                    <div class="modal-body text-center">
                        <div class="mb-3">
                            <i class="bi bi-clock display-1 text-warning"></i>
                        </div>
                        <p class="lead">Your session will expire due to inactivity.</p>
                        <p class="text-muted">
                            Time remaining: <span id="warning-countdown" class="fw-bold fs-4"></span>
                        </p>
                        <p class="small text-muted">
                            Click "Continue" to extend your session.
                        </p>
                    </div>
                    <div class="modal-footer justify-content-center">
                        <button type="button" class="btn btn-primary btn-lg" id="extend-session-btn">
                            <i class="bi bi-arrow-repeat me-2"></i>
                            Continue
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modalEl);

        // Set up extend session button
        modalEl.querySelector('#extend-session-btn').addEventListener('click', async () => {
            await extendSession();
        });
    }

    // Update countdown display
    updateWarningCountdown(remainingSeconds);

    // Start countdown timer
    warningCountdownInterval = setInterval(() => {
        const remaining = Math.max(0, config.ssoSessionIdleTimeoutSeconds - getIdleTimeSeconds());

        if (remaining <= 0) {
            handleSessionExpired();
        } else {
            updateWarningCountdown(remaining);
        }
    }, 1000);

    // Show the modal
    warningModal = new bootstrap.Modal(modalEl);
    warningModal.show();

    console.log('[SessionManager] Idle warning shown');
}

/**
 * Update the countdown display in the warning modal
 */
function updateWarningCountdown(remainingSeconds) {
    const countdownEl = document.getElementById('warning-countdown');
    if (countdownEl) {
        const minutes = Math.floor(remainingSeconds / 60);
        const seconds = Math.floor(remainingSeconds % 60);
        countdownEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
}

/**
 * Hide the warning modal
 */
function hideWarningModal() {
    if (warningModal) {
        warningModal.hide();
        warningModal = null;
    }

    if (warningCountdownInterval) {
        clearInterval(warningCountdownInterval);
        warningCountdownInterval = null;
    }

    isWarningShown = false;
}

/**
 * Extend session - user clicked "Continue"
 */
async function extendSession() {
    console.log('[SessionManager] User requested session extension');

    // Perform token refresh to reset Keycloak idle timer
    const success = await performTokenRefresh();

    if (success) {
        // Reset local state
        lastActivityTime = Date.now();
        isPaused = false;
        hideWarningModal();

        // Show success toast
        showToast('Session extended successfully', 'success');

        console.log('[SessionManager] Session extended successfully');
    } else {
        // Refresh failed - session is dead
        handleSessionExpired();
    }
}

// =============================================================================
// Session Expiration
// =============================================================================

/**
 * Handle session expiration
 * Clears local state and redirects to Keycloak login
 */
async function handleSessionExpired() {
    console.log('[SessionManager] Session expired - redirecting to login');

    // Stop all monitoring
    stopSessionMonitoring();

    // Hide warning modal if visible
    hideWarningModal();

    // Call callback if set (allows app to clean up)
    if (onSessionExpiredCallback) {
        try {
            onSessionExpiredCallback();
        } catch (error) {
            console.error('[SessionManager] Callback error:', error);
        }
    }

    // Redirect to login (via Keycloak)
    window.location.href = '/api/auth/login';
}

// =============================================================================
// OIDC Session Management Iframe
// =============================================================================

/**
 * Initialize OIDC Session Management iframe for cross-app logout detection
 *
 * This implements the OIDC Session Management spec without keycloak-js:
 * https://openid.net/specs/openid-connect-session-1_0.html
 *
 * The iframe checks the session state with Keycloak and detects if the
 * user logged out from another application.
 */
function initializeSessionIframe() {
    if (!config.checkSessionIframe) {
        console.log('[SessionManager] No check_session_iframe URL, skipping session iframe');
        return;
    }

    // Create hidden iframe for session checks
    sessionIframe = document.createElement('iframe');
    sessionIframe.id = 'keycloak-session-iframe';
    sessionIframe.style.display = 'none';
    sessionIframe.src = config.checkSessionIframe;
    document.body.appendChild(sessionIframe);

    // Listen for messages from the iframe
    window.addEventListener('message', handleSessionIframeMessage);

    // Note: We only check backend session when iframe reports a change
    // No periodic polling - the iframe handles session state detection

    console.log('[SessionManager] OIDC Session Management iframe initialized');
}

/**
 * Handle messages from the session iframe
 */
function handleSessionIframeMessage(event) {
    // Verify the message is from Keycloak
    if (!config.keycloakUrl) return;

    try {
        const keycloakOrigin = new URL(config.keycloakUrl).origin;
        if (event.origin !== keycloakOrigin) {
            return;
        }
    } catch {
        return;
    }

    const data = event.data;
    if (data === 'changed' || data === 'error') {
        console.log(`[SessionManager] Session iframe reports: ${data}`);
        // Session changed in Keycloak - verify with backend
        checkBackendSession();
    }
}

/**
 * Check if the backend session is still valid
 */
async function checkBackendSession() {
    try {
        const response = await fetch('/api/auth/me', {
            credentials: 'include',
        });

        if (response.status === 401) {
            console.log('[SessionManager] Backend session invalid - logging out');
            handleSessionExpired();
        }
    } catch (error) {
        console.warn('[SessionManager] Backend session check failed:', error);
    }
}

/**
 * Clean up the session iframe
 */
function cleanupSessionIframe() {
    if (sessionCheckInterval) {
        clearInterval(sessionCheckInterval);
        sessionCheckInterval = null;
    }

    window.removeEventListener('message', handleSessionIframeMessage);

    if (sessionIframe && sessionIframe.parentNode) {
        sessionIframe.parentNode.removeChild(sessionIframe);
        sessionIframe = null;
    }
}

// =============================================================================
// Idle Check Loop
// =============================================================================

/**
 * Start the idle check loop
 */
function startIdleCheck() {
    // Check every 10 seconds
    idleCheckInterval = setInterval(checkIdleStatus, 10000);
    console.log('[SessionManager] Idle check started');
}

/**
 * Stop the idle check loop
 */
function stopIdleCheck() {
    if (idleCheckInterval) {
        clearInterval(idleCheckInterval);
        idleCheckInterval = null;
    }
}

// =============================================================================
// Public API
// =============================================================================

/**
 * Fetch session settings from the backend
 */
async function fetchSessionSettings() {
    try {
        const response = await fetch('/api/auth/session-settings', {
            credentials: 'include',
        });

        if (response.ok) {
            const settings = await response.json();
            config.keycloakUrl = settings.keycloak_url || '';
            config.realm = settings.realm || '';
            config.clientId = settings.client_id || '';
            config.ssoSessionIdleTimeoutSeconds = settings.sso_session_idle_timeout_seconds || 1800;
            config.sessionExpirationWarningMinutes = settings.session_expiration_warning_minutes || 2;
            config.checkSessionIframe = settings.check_session_iframe || null;

            console.log(`[SessionManager] Loaded settings: idle_timeout=${config.ssoSessionIdleTimeoutSeconds}s, ` + `warning=${config.sessionExpirationWarningMinutes}min`);
        }
    } catch (error) {
        console.warn('[SessionManager] Failed to load session settings, using defaults:', error);
    }
}

/**
 * Start session monitoring
 * Call this after successful authentication
 * @param {Function} onExpired - Optional callback when session expires
 */
export async function startSessionMonitoring(onExpired = null) {
    if (isInitialized) {
        console.log('[SessionManager] Already initialized, resetting...');
        stopSessionMonitoring();
    }

    // Store callback
    onSessionExpiredCallback = onExpired;

    // Fetch settings from backend
    await fetchSessionSettings();

    // Initialize state
    lastActivityTime = Date.now();
    isPaused = false;
    isWarningShown = false;
    isInitialized = true;

    // Start all monitoring
    startActivityTracking();
    startIdleCheck();
    startTokenRefresh();

    // Initialize OIDC session iframe for cross-app sync
    initializeSessionIframe();

    console.log(`[SessionManager] Monitoring started. Idle timeout: ${config.ssoSessionIdleTimeoutSeconds}s, ` + `Warning: ${config.sessionExpirationWarningMinutes}min before expiry`);
}

/**
 * Stop session monitoring
 * Call this on logout
 */
export function stopSessionMonitoring() {
    stopActivityTracking();
    stopIdleCheck();
    stopTokenRefresh();
    cleanupSessionIframe();
    hideWarningModal();

    isInitialized = false;
    isPaused = false;
    isWarningShown = false;
    onSessionExpiredCallback = null;

    console.log('[SessionManager] Monitoring stopped');
}

/**
 * Reset session timer (call after successful auth or activity)
 */
export function resetSessionTimer() {
    lastActivityTime = Date.now();
    isPaused = false;
    isWarningShown = false;
    hideWarningModal();
    console.log('[SessionManager] Session timer reset');
}

/**
 * Get session info for debugging
 */
export function getSessionInfo() {
    return {
        idleTimeSeconds: getIdleTimeSeconds(),
        idleTimeoutSeconds: config.ssoSessionIdleTimeoutSeconds,
        warningMinutes: config.sessionExpirationWarningMinutes,
        isWarningShown,
        isPaused,
        isInitialized,
        keycloakUrl: config.keycloakUrl,
        realm: config.realm,
        clientId: config.clientId,
    };
}
