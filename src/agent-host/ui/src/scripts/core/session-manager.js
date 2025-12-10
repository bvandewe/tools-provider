/**
 * Session Manager for Agent Host
 *
 * Simplified session lifecycle management:
 * - Silent token refresh in the background (every 4 minutes)
 * - Non-intrusive toast notifications only when SSO session is ending
 * - Protected mode for active streaming (prevents disruptive redirects)
 * - Draft preservation via localStorage (managed by draft-manager.js)
 *
 * Design Philosophy:
 * - Token refresh happens silently with NO UI as long as it succeeds
 * - Only show notifications when user action is actually needed
 * - Use toast notifications instead of blocking modals where possible
 * - Preserve user work (drafts) before any forced redirect
 */

import * as bootstrap from 'bootstrap';
import { showToast } from '../services/modals.js';
import { saveCurrentDraft } from './draft-manager.js';

// =============================================================================
// Configuration
// =============================================================================

const TOKEN_REFRESH_INTERVAL_MS = 4 * 60 * 1000; // 4 minutes

// Thresholds for warnings (in seconds)
const WARNING_THRESHOLD_SECONDS = 120; // Show warning when <2 min remaining on refresh token

// =============================================================================
// State
// =============================================================================

let tokenRefreshInterval = null;
let isInitialized = false;
let consecutiveRefreshFailures = 0;
let warningToastShown = false;
let sessionExpiredModal = null;

// Protected mode - prevents immediate redirect during active streaming
let isProtected = false;
let protectedReason = null;
let hasDeferredExpiration = false;

// Callbacks
let onSessionExpiredCallback = null;
let onBeforeRedirectCallback = null;

// =============================================================================
// Token Refresh (Silent Background Refresh)
// =============================================================================

/**
 * Perform a silent token refresh
 * The backend will only actually refresh if the token is near expiry.
 * Returns true if session is still valid (whether refreshed or not).
 */
async function performTokenRefresh() {
    try {
        const response = await fetch('/api/auth/refresh', {
            method: 'POST',
            credentials: 'include',
        });

        if (response.ok) {
            const data = await response.json();
            consecutiveRefreshFailures = 0;

            // Check if SSO session (refresh token) is expiring soon
            const refreshTokenExpiresIn = data.refresh_token_expires_in;
            if (refreshTokenExpiresIn !== null && refreshTokenExpiresIn !== undefined && refreshTokenExpiresIn < WARNING_THRESHOLD_SECONDS) {
                showSessionExpiringWarning(refreshTokenExpiresIn);
            } else {
                // Session healthy, clear any previous warnings
                warningToastShown = false;
            }

            // Log status (refreshed vs valid means backend decided whether to actually refresh)
            const statusMsg = data.status === 'refreshed' ? 'Token refreshed' : 'Token still valid';
            console.log('[SessionManager] ' + statusMsg + '. ' + 'Access token expires in ' + data.access_token_expires_in + 's, ' + 'Refresh token expires in ' + refreshTokenExpiresIn + 's');
            return true;
        } else if (response.status === 401) {
            consecutiveRefreshFailures++;
            console.log('[SessionManager] Session expired (401) - failure count: ' + consecutiveRefreshFailures);

            // Session is truly expired
            handleSessionExpired();
            return false;
        } else {
            console.warn('[SessionManager] Token refresh returned unexpected status: ' + response.status);
            return false;
        }
    } catch (error) {
        console.error('[SessionManager] Token refresh error:', error);
        consecutiveRefreshFailures++;
        if (consecutiveRefreshFailures >= 3) {
            handleSessionExpired();
        }
        return false;
    }
}

/**
 * Start background token refresh
 * No initial delay - the backend will only refresh if the token is near expiry,
 * so it's safe to call immediately.
 */
function startTokenRefresh() {
    // Regular refresh interval - backend handles the "should I actually refresh" logic
    tokenRefreshInterval = setInterval(async () => {
        await performTokenRefresh();
    }, TOKEN_REFRESH_INTERVAL_MS);

    console.log('[SessionManager] Token refresh started (every ' + TOKEN_REFRESH_INTERVAL_MS / 1000 + 's)');
}

/**
 * Stop token refresh
 */
function stopTokenRefresh() {
    if (tokenRefreshInterval) {
        clearInterval(tokenRefreshInterval);
        tokenRefreshInterval = null;
    }
}

// =============================================================================
// Notifications (Non-Intrusive)
// =============================================================================

/**
 * Show a warning toast that SSO session is expiring soon
 * This is non-blocking - user can continue working
 */
function showSessionExpiringWarning(secondsRemaining) {
    if (warningToastShown) return;
    warningToastShown = true;

    const minutes = Math.ceil(secondsRemaining / 60);
    const timeText = minutes <= 1 ? 'less than a minute' : minutes + ' minutes';

    showToast(
        'Your session will expire in ' + timeText + '. ' + 'Save your work or click <a href="/api/auth/login" class="alert-link">here to re-authenticate</a>.',
        'warning',
        15000 // 15 second display
    );

    console.log('[SessionManager] Session expiring warning shown (' + secondsRemaining + 's remaining)');
}

// =============================================================================
// Session Expiration Handling
// =============================================================================

/**
 * Handle session expiration - respects protected mode
 */
async function handleSessionExpired() {
    // If already handling expiration in protected mode, don't trigger again
    if (hasDeferredExpiration && isProtected) {
        return;
    }

    // If in protected mode (streaming), defer the redirect
    if (isProtected) {
        console.log('[SessionManager] Session expired but protected ' + '(' + protectedReason + ') - deferring redirect');
        hasDeferredExpiration = true;
        showSessionExpiredModal();
        return;
    }

    // Not protected - proceed with expiration flow
    forceSessionExpired();
}

/**
 * Force session expiration - bypasses protected mode
 */
function forceSessionExpired() {
    console.log('[SessionManager] Session expired - saving drafts and redirecting');

    // Stop all monitoring
    stopSessionMonitoring();

    // Save any unsent drafts immediately
    try {
        saveCurrentDraft();
    } catch (error) {
        console.error('[SessionManager] Failed to save draft:', error);
    }

    // Call before-redirect callback
    if (onBeforeRedirectCallback) {
        try {
            onBeforeRedirectCallback();
        } catch (error) {
            console.error('[SessionManager] Before-redirect callback error:', error);
        }
    }

    // Call expired callback
    if (onSessionExpiredCallback) {
        try {
            onSessionExpiredCallback();
        } catch (error) {
            console.error('[SessionManager] Expired callback error:', error);
        }
    }

    // Hide any modals
    hideSessionExpiredModal();

    // Redirect to login
    window.location.href = '/api/auth/login';
}

// =============================================================================
// Session Expired Modal (only for protected mode)
// =============================================================================

/**
 * Show session expired modal when in protected mode
 * This is only shown during active streaming to let user know
 * they'll be redirected when streaming completes
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
        modalEl.innerHTML =
            '\
            <div class="modal-dialog modal-dialog-centered">\
                <div class="modal-content">\
                    <div class="modal-header bg-warning text-dark">\
                        <h5 class="modal-title" id="sessionExpiredLabel">\
                            <i class="bi bi-exclamation-triangle me-2"></i>\
                            Session Expired\
                        </h5>\
                    </div>\
                    <div class="modal-body text-center">\
                        <div class="mb-3">\
                            <i class="bi bi-cloud-check display-1 text-success"></i>\
                        </div>\
                        <p class="lead">Your session has expired.</p>\
                        <p class="text-muted">\
                            <i class="bi bi-check-circle text-success me-1"></i>\
                            Your draft message is automatically saved and will be \
                            restored after you log in again.\
                        </p>\
                        <p class="text-muted small">\
                            The current response will complete, then you\'ll be \
                            redirected to log in.\
                        </p>\
                    </div>\
                    <div class="modal-footer justify-content-center">\
                        <button type="button" class="btn btn-primary" id="login-now-btn">\
                            <i class="bi bi-box-arrow-in-right me-2"></i>\
                            Log In Now\
                        </button>\
                    </div>\
                </div>\
            </div>\
        ';
        document.body.appendChild(modalEl);

        // Set up login button
        modalEl.querySelector('#login-now-btn').addEventListener('click', function () {
            forceSessionExpired();
        });
    }

    sessionExpiredModal = new bootstrap.Modal(modalEl);
    sessionExpiredModal.show();

    console.log('[SessionManager] Session expired modal shown (protected mode)');
}

/**
 * Hide the session expired modal
 */
function hideSessionExpiredModal() {
    if (sessionExpiredModal) {
        try {
            sessionExpiredModal.hide();
        } catch (e) {
            // Modal may already be disposed
        }
        sessionExpiredModal = null;
    }

    // Also remove the element if it exists
    const modalEl = document.getElementById('session-expired-modal');
    if (modalEl) {
        modalEl.remove();
    }
}

// =============================================================================
// Public API
// =============================================================================

/**
 * Start session monitoring
 * Call this after successful authentication
 *
 * @param {Function} onExpired - Optional callback when session expires
 * @param {Function} onBeforeRedirect - Optional callback before redirect
 */
export async function startSessionMonitoring(onExpired = null, onBeforeRedirect = null) {
    if (isInitialized) {
        console.log('[SessionManager] Already initialized, resetting...');
        stopSessionMonitoring();
    }

    // Store callbacks
    onSessionExpiredCallback = onExpired;
    onBeforeRedirectCallback = onBeforeRedirect;

    // Initialize state
    consecutiveRefreshFailures = 0;
    warningToastShown = false;
    isProtected = false;
    protectedReason = null;
    hasDeferredExpiration = false;
    isInitialized = true;

    // Start background token refresh only
    // The backend handles the "should I refresh" logic, so we just call /refresh periodically
    startTokenRefresh();

    console.log('[SessionManager] Monitoring started (silent token refresh every 4 min)');
}

/**
 * Stop session monitoring
 * Call this on logout
 */
export function stopSessionMonitoring() {
    stopTokenRefresh();
    hideSessionExpiredModal();

    isInitialized = false;
    consecutiveRefreshFailures = 0;
    warningToastShown = false;
    isProtected = false;
    protectedReason = null;
    hasDeferredExpiration = false;
    onSessionExpiredCallback = null;
    onBeforeRedirectCallback = null;

    console.log('[SessionManager] Monitoring stopped');
}

/**
 * Reset session state
 * Call this after successful re-authentication
 */
export function resetSessionTimer() {
    consecutiveRefreshFailures = 0;
    warningToastShown = false;
    hasDeferredExpiration = false;
    hideSessionExpiredModal();
    console.log('[SessionManager] Session state reset');
}

/**
 * Enable protected mode - prevents immediate redirect on session expiration
 * Use this when streaming a response or doing critical work
 *
 * @param {string} reason - Reason for protection (e.g., 'streaming', 'submitting')
 */
export function enableProtection(reason) {
    isProtected = true;
    protectedReason = reason;
    console.log('[SessionManager] Protection enabled: ' + reason);
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
        // Small delay to let any UI updates complete
        setTimeout(function () {
            forceSessionExpired();
        }, 500);
    }
}

/**
 * Check if session has a deferred expiration pending
 * @returns {boolean}
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
 * Notify session manager of authentication failure (e.g., 401 during API call)
 * This allows the session manager to handle expiration appropriately
 */
export function notifyTokenExpired() {
    console.log('[SessionManager] Token expired notification received');
    consecutiveRefreshFailures++;

    if (consecutiveRefreshFailures >= 2) {
        handleSessionExpired();
    } else {
        // Try one more refresh
        performTokenRefresh();
    }
}

/**
 * Force an immediate token refresh
 * Call this after user interaction if you want to ensure session is valid
 */
export async function forceRefresh() {
    return await performTokenRefresh();
}

/**
 * Get session info for debugging
 */
export function getSessionInfo() {
    return {
        isInitialized: isInitialized,
        isProtected: isProtected,
        protectedReason: protectedReason,
        hasDeferredExpiration: hasDeferredExpiration,
        consecutiveRefreshFailures: consecutiveRefreshFailures,
        warningToastShown: warningToastShown,
    };
}
