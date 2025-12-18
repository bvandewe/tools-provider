/**
 * Session Manager
 *
 * Implements comprehensive session lifecycle management:
 * - Activity tracking (mouse, keyboard, touch, scroll, click)
 * - Idle timeout detection with warning modal
 * - Background token refresh when user is active
 * - OIDC Session Management iframe for cross-app synchronization
 * - Keycloak logout on session expiration
 * - Page leave protection for unsaved work
 *
 * Session settings are fetched from Keycloak via the backend.
 */

import * as bootstrap from 'bootstrap';

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

// Page leave protection state
let protectionReasons = new Set();
let pendingExpirationCallback = null;

// Callbacks
let onSessionExpired = null;
let onBeforeRedirect = null;

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
// Page Leave Protection
// =============================================================================

/**
 * Handle beforeunload event - warn user about unsaved work
 */
function handleBeforeUnload(event) {
    if (protectionReasons.size > 0) {
        event.preventDefault();
        event.returnValue = '';
        return '';
    }
}

/**
 * Enable page leave protection
 * @param {string} reason - Reason for protection (e.g., 'draft', 'streaming')
 */
export function enableProtection(reason) {
    protectionReasons.add(reason);
    if (protectionReasons.size === 1) {
        window.addEventListener('beforeunload', handleBeforeUnload);
    }
    console.log(`[SessionManager] Protection enabled: ${reason}`);
}

/**
 * Disable page leave protection
 * @param {string} reason - Reason to remove
 */
export function disableProtection(reason) {
    protectionReasons.delete(reason);
    if (protectionReasons.size === 0) {
        window.removeEventListener('beforeunload', handleBeforeUnload);
    }
    console.log(`[SessionManager] Protection disabled: ${reason}`);
}

/**
 * Check if there's a pending expiration
 * @returns {boolean}
 */
export function hasPendingExpiration() {
    return isWarningShown;
}

/**
 * Notify that token has expired (from external source like stream-handler)
 */
export function notifyTokenExpired() {
    console.log('[SessionManager] Token expired notification received');
    handleSessionExpired();
}

// =============================================================================
// Token Refresh (Silent Refresh)
// =============================================================================

const WARNING_THRESHOLD_SECONDS = 120;
let consecutiveRefreshFailures = 0;

/**
 * Perform a silent token refresh
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
            const data = await response.json();
            consecutiveRefreshFailures = 0;

            // Check if SSO session (refresh token) is expiring soon
            const refreshTokenExpiresIn = data.refresh_token_expires_in;
            if (refreshTokenExpiresIn !== null && refreshTokenExpiresIn !== undefined && refreshTokenExpiresIn < WARNING_THRESHOLD_SECONDS) {
                showIdleWarning();
            }

            const statusMsg = data.status === 'refreshed' ? 'Token refreshed' : 'Token still valid';
            console.log('[SessionManager] ' + statusMsg + '. Access token expires in ' + data.access_token_expires_in + 's');
            return true;
        } else if (response.status === 401) {
            consecutiveRefreshFailures++;
            console.log('[SessionManager] Session expired (401) - failure count: ' + consecutiveRefreshFailures);
            handleSessionExpired();
            return false;
        } else {
            console.warn('[SessionManager] Token refresh failed:', response.status);
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
 * Start background token refresh (every 4 minutes)
 */
function startTokenRefresh() {
    const REFRESH_INTERVAL_MS = 4 * 60 * 1000;

    tokenRefreshInterval = setInterval(async () => {
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
    isPaused = true;

    const remainingSeconds = Math.max(0, config.ssoSessionIdleTimeoutSeconds - getIdleTimeSeconds());

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

        modalEl.querySelector('#extend-session-btn').addEventListener('click', async () => {
            await extendSession();
        });
    }

    updateWarningCountdown(remainingSeconds);

    warningCountdownInterval = setInterval(() => {
        const remaining = Math.max(0, config.ssoSessionIdleTimeoutSeconds - getIdleTimeSeconds());

        if (remaining <= 0) {
            handleSessionExpired();
        } else {
            updateWarningCountdown(remaining);
        }
    }, 1000);

    warningModal = new bootstrap.Modal(modalEl);
    warningModal.show();

    console.log('[SessionManager] Idle warning shown');
}

/**
 * Update the countdown display
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

    const success = await performTokenRefresh();

    if (success) {
        lastActivityTime = Date.now();
        isPaused = false;
        hideWarningModal();
        console.log('[SessionManager] Session extended successfully');
    } else {
        handleSessionExpired();
    }
}

// =============================================================================
// Session Expiration
// =============================================================================

/**
 * Handle session expiration
 */
async function handleSessionExpired() {
    console.log('[SessionManager] Session expired - redirecting to login');

    // Notify callback if set
    if (onSessionExpired) {
        onSessionExpired();
    }

    stopSessionMonitoring();
    hideWarningModal();

    // Clear protection before redirect
    protectionReasons.clear();
    window.removeEventListener('beforeunload', handleBeforeUnload);

    // Notify before redirect callback
    if (onBeforeRedirect) {
        onBeforeRedirect();
    }

    window.location.href = '/api/auth/login';
}

// =============================================================================
// OIDC Session Management Iframe
// =============================================================================

/**
 * Initialize OIDC Session Management iframe
 */
function initializeSessionIframe() {
    if (!config.checkSessionIframe) {
        console.log('[SessionManager] No check_session_iframe URL, skipping session iframe');
        return;
    }

    sessionIframe = document.createElement('iframe');
    sessionIframe.id = 'keycloak-session-iframe';
    sessionIframe.style.display = 'none';
    sessionIframe.src = config.checkSessionIframe;
    document.body.appendChild(sessionIframe);

    window.addEventListener('message', handleSessionIframeMessage);

    console.log('[SessionManager] OIDC Session Management iframe initialized');
}

/**
 * Handle messages from the session iframe
 */
function handleSessionIframeMessage(event) {
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
 * @param {Function} sessionExpiredCallback - Called when session expires
 * @param {Function} beforeRedirectCallback - Called before redirect to login
 */
export async function startSessionMonitoring(sessionExpiredCallback = null, beforeRedirectCallback = null) {
    if (isInitialized) {
        console.log('[SessionManager] Already initialized, resetting...');
        stopSessionMonitoring();
    }

    // Store callbacks
    onSessionExpired = sessionExpiredCallback;
    onBeforeRedirect = beforeRedirectCallback;

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
    onSessionExpired = null;
    onBeforeRedirect = null;

    console.log('[SessionManager] Monitoring stopped');
}

/**
 * Reset session timer
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
        protectionReasons: Array.from(protectionReasons),
    };
}
