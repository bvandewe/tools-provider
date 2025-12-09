/**
 * Session Manager for Agent Host
 *
 * Implements comprehensive session lifecycle management:
 * - Activity tracking (mouse, keyboard, touch, scroll, click)
 * - Idle timeout detection with warning modal
 * - Background token refresh when user is active
 * - Protected mode for active conversations (prevents disruptive redirects)
 * - Draft preservation on session expiration
 * - Keycloak logout on session expiration (deferred if protected)
 *
 * Session settings are fetched from Keycloak via the backend.
 *
 * Note: This implementation does NOT use keycloak-js or OIDC Session Management
 * iframe. Instead, it relies on token expiration and backend session validation.
 * This simplifies the architecture and avoids unexpected page reloads.
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
};

// =============================================================================
// State
// =============================================================================

let lastActivityTime = Date.now();
let idleCheckInterval = null;
let tokenRefreshInterval = null;
let warningModal = null;
let warningCountdownInterval = null;
let isWarningShown = false;
let isPaused = false; // Paused when warning is shown
let isInitialized = false;

// Protected mode - prevents immediate redirect during active conversation
let isProtected = false;
let protectedReason = null; // 'streaming' or 'draft'

// Callbacks
let onSessionExpiredCallback = null;
let onBeforeRedirectCallback = null; // Called before redirect to save state

// Deferred expiration - redirect after protection ends
let hasDeferredExpiration = false;

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
    isPaused = false; // Allow refresh
    const success = await performTokenRefresh();

    if (success) {
        // Reset local state
        lastActivityTime = Date.now();
        isPaused = false;
        hasDeferredExpiration = false;
        hideWarningModal();

        // Show success toast
        showToast('Session extended successfully', 'success');

        console.log('[SessionManager] Session extended successfully');
    } else {
        // Refresh failed - session is truly expired
        forceSessionExpired();
    }
}

// =============================================================================
// Session Expiration
// =============================================================================

/**
 * Handle session expiration - checks protected mode before redirecting
 * If in protected mode, shows a non-blocking notification and defers redirect.
 * @param {boolean} fromTokenRefresh - True if triggered by token refresh failure
 */
async function handleSessionExpired(fromTokenRefresh = false) {
    // If already handling expiration, don't trigger again
    if (hasDeferredExpiration && isProtected) {
        return;
    }

    // If in protected mode (streaming or has draft), defer the redirect
    if (isProtected) {
        console.log(`[SessionManager] Session expired but protected (${protectedReason}) - deferring redirect`);
        hasDeferredExpiration = true;

        // Hide any existing warning modal
        hideWarningModal();

        // Show session expired modal with draft-saved message
        showSessionExpiredModal();

        return;
    }

    // Not protected - proceed with normal expiration flow
    forceSessionExpired();
}

/**
 * Force session expiration - bypasses protected mode
 * Used when user explicitly acknowledges expiration or protection ends
 */
function forceSessionExpired() {
    console.log('[SessionManager] Session expired - redirecting to login');

    // Stop all monitoring
    stopSessionMonitoring();

    // Hide any modals
    hideWarningModal();
    hideSessionExpiredModal();

    // Call before-redirect callback (for saving drafts)
    if (onBeforeRedirectCallback) {
        try {
            onBeforeRedirectCallback();
        } catch (error) {
            console.error('[SessionManager] Before-redirect callback error:', error);
        }
    }

    // Call expired callback (for app cleanup)
    if (onSessionExpiredCallback) {
        try {
            onSessionExpiredCallback();
        } catch (error) {
            console.error('[SessionManager] Expired callback error:', error);
        }
    }

    // Redirect to login (via Keycloak)
    window.location.href = '/api/auth/login';
}

// =============================================================================
// Session Expired Modal (for protected mode)
// =============================================================================

let sessionExpiredModal = null;

/**
 * Show session expired modal when in protected mode
 */
function showSessionExpiredModal() {
    let modalEl = document.getElementById('session-expired-modal');
    if (!modalEl) {
        modalEl = document.createElement('div');
        modalEl.id = 'session-expired-modal';
        modalEl.className = 'modal fade';
        modalEl.setAttribute('tabindex', '-1');
        modalEl.setAttribute('aria-labelledby', 'sessionExpiredLabel');
        modalEl.setAttribute('data-bs-backdrop', 'static');
        modalEl.setAttribute('data-bs-keyboard', 'false');
        modalEl.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-danger text-white">
                        <h5 class="modal-title" id="sessionExpiredLabel">
                            <i class="bi bi-shield-exclamation me-2"></i>
                            Session Expired
                        </h5>
                    </div>
                    <div class="modal-body text-center">
                        <div class="mb-3">
                            <i class="bi bi-cloud-check display-1 text-success"></i>
                        </div>
                        <p class="lead">Your session has expired.</p>
                        <p class="text-muted">
                            <i class="bi bi-check-circle text-success me-1"></i>
                            Your draft message has been saved and will be restored after you log in again.
                        </p>
                    </div>
                    <div class="modal-footer justify-content-center">
                        <button type="button" class="btn btn-primary btn-lg" id="login-again-btn">
                            <i class="bi bi-box-arrow-in-right me-2"></i>
                            Log In Again
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modalEl);

        // Set up login button
        modalEl.querySelector('#login-again-btn').addEventListener('click', () => {
            forceSessionExpired();
        });
    }

    sessionExpiredModal = new bootstrap.Modal(modalEl);
    sessionExpiredModal.show();

    console.log('[SessionManager] Session expired modal shown');
}

/**
 * Hide the session expired modal
 */
function hideSessionExpiredModal() {
    if (sessionExpiredModal) {
        sessionExpiredModal.hide();
        sessionExpiredModal = null;
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

            console.log(`[SessionManager] Loaded settings: idle_timeout=${config.ssoSessionIdleTimeoutSeconds}s, ` + `warning=${config.sessionExpirationWarningMinutes}min`);
        }
    } catch (error) {
        console.warn('[SessionManager] Failed to load session settings, using defaults:', error);
    }
}

/**
 * Start session monitoring
 * Call this after successful authentication
 * @param {Function} onExpired - Optional callback when session expires (for app cleanup)
 * @param {Function} onBeforeRedirect - Optional callback before redirect (for saving drafts)
 */
export async function startSessionMonitoring(onExpired = null, onBeforeRedirect = null) {
    if (isInitialized) {
        console.log('[SessionManager] Already initialized, resetting...');
        stopSessionMonitoring();
    }

    // Store callbacks
    onSessionExpiredCallback = onExpired;
    onBeforeRedirectCallback = onBeforeRedirect;

    // Fetch settings from backend
    await fetchSessionSettings();

    // Initialize state
    lastActivityTime = Date.now();
    isPaused = false;
    isWarningShown = false;
    isProtected = false;
    protectedReason = null;
    hasDeferredExpiration = false;
    isInitialized = true;

    // Start all monitoring
    startActivityTracking();
    startIdleCheck();
    startTokenRefresh();

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
    hideWarningModal();
    hideSessionExpiredModal();

    isInitialized = false;
    isPaused = false;
    isWarningShown = false;
    isProtected = false;
    protectedReason = null;
    hasDeferredExpiration = false;
    onSessionExpiredCallback = null;
    onBeforeRedirectCallback = null;

    console.log('[SessionManager] Monitoring stopped');
}

/**
 * Reset session timer (call after successful auth or activity)
 */
export function resetSessionTimer() {
    lastActivityTime = Date.now();
    isPaused = false;
    isWarningShown = false;
    hasDeferredExpiration = false;
    hideWarningModal();
    hideSessionExpiredModal();
    console.log('[SessionManager] Session timer reset');
}

/**
 * Enable protected mode - prevents immediate redirect on session expiration
 * @param {string} reason - Reason for protection ('streaming' or 'draft')
 */
export function enableProtection(reason) {
    isProtected = true;
    protectedReason = reason;
    console.log(`[SessionManager] Protection enabled: ${reason}`);
}

/**
 * Disable protected mode
 * If session expired while protected, will now redirect
 */
export function disableProtection() {
    isProtected = false;
    protectedReason = null;
    console.log('[SessionManager] Protection disabled');

    // If session expired while protected, handle it now
    if (hasDeferredExpiration) {
        console.log('[SessionManager] Processing deferred expiration');
        forceSessionExpired();
    }
}

/**
 * Check if session has a deferred expiration pending
 * @returns {boolean} True if session expired while protected
 */
export function hasPendingExpiration() {
    return hasDeferredExpiration;
}

/**
 * Check if currently in protected mode
 * @returns {boolean}
 */
export function isInProtectedMode() {
    return isProtected;
}

/**
 * Notify session manager of token refresh failure (e.g., 401 during API call)
 * This allows the session manager to handle expiration appropriately
 */
export function notifyTokenExpired() {
    console.log('[SessionManager] Token expired notification received');
    handleSessionExpired(true);
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
        isProtected,
        protectedReason,
        hasDeferredExpiration,
        keycloakUrl: config.keycloakUrl,
        realm: config.realm,
        clientId: config.clientId,
    };
}
