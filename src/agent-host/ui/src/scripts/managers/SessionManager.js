/**
 * SessionManager - Class-based session lifecycle manager
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
 *
 * @module managers/SessionManager
 */

import * as bootstrap from 'bootstrap';

// Activity events to track
const ACTIVITY_EVENTS = ['mousedown', 'mousemove', 'keydown', 'keypress', 'scroll', 'touchstart', 'touchmove', 'click', 'focus'];
const REFRESH_INTERVAL_MS = 4 * 60 * 1000; // 4 minutes
const WARNING_THRESHOLD_SECONDS = 120;

/**
 * @class SessionManager
 * @description Manages session lifecycle, activity tracking, and token refresh
 */
export class SessionManager {
    /**
     * Create SessionManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Object} Configuration */
        this._config = {
            keycloakUrl: '',
            realm: '',
            clientId: '',
            ssoSessionIdleTimeoutSeconds: 1800, // 30 minutes default
            sessionExpirationWarningMinutes: 2, // Show warning 2 minutes before expiry
            checkSessionIframe: null,
        };

        /** @type {HTMLIFrameElement|null} */
        this._sessionIframe = null;

        /** @type {number|null} */
        this._sessionCheckInterval = null;

        /** @type {number} */
        this._lastActivityTime = Date.now();

        /** @type {number|null} */
        this._idleCheckInterval = null;

        /** @type {number|null} */
        this._tokenRefreshInterval = null;

        /** @type {bootstrap.Modal|null} */
        this._warningModal = null;

        /** @type {number|null} */
        this._warningCountdownInterval = null;

        /** @type {boolean} */
        this._isWarningShown = false;

        /** @type {boolean} */
        this._isPaused = false;

        /** @type {Set<string>} */
        this._protectionReasons = new Set();

        /** @type {number} */
        this._consecutiveRefreshFailures = 0;

        /** @type {Function|null} */
        this._onSessionExpired = null;

        /** @type {Function|null} */
        this._onBeforeRedirect = null;

        // Bind methods for event listeners
        this._recordActivity = this._recordActivity.bind(this);
        this._handleBeforeUnload = this._handleBeforeUnload.bind(this);
        this._handleSessionIframeMessage = this._handleSessionIframeMessage.bind(this);
    }

    // =========================================================================
    // Activity Tracking
    // =========================================================================

    /**
     * Record user activity - resets the idle timer
     * @private
     */
    _recordActivity() {
        this._lastActivityTime = Date.now();
    }

    /**
     * Get idle time in seconds
     * @private
     * @returns {number}
     */
    _getIdleTimeSeconds() {
        return (Date.now() - this._lastActivityTime) / 1000;
    }

    /**
     * Get idle time in minutes
     * @private
     * @returns {number}
     */
    _getIdleTimeMinutes() {
        return this._getIdleTimeSeconds() / 60;
    }

    /**
     * Start tracking user activity
     * @private
     */
    _startActivityTracking() {
        ACTIVITY_EVENTS.forEach(event => {
            document.addEventListener(event, this._recordActivity, { passive: true });
        });
        console.log('[SessionManager] Activity tracking started');
    }

    /**
     * Stop tracking user activity
     * @private
     */
    _stopActivityTracking() {
        ACTIVITY_EVENTS.forEach(event => {
            document.removeEventListener(event, this._recordActivity);
        });
        console.log('[SessionManager] Activity tracking stopped');
    }

    // =========================================================================
    // Page Leave Protection
    // =========================================================================

    /**
     * Handle beforeunload event - warn user about unsaved work
     * @private
     */
    _handleBeforeUnload(event) {
        if (this._protectionReasons.size > 0) {
            event.preventDefault();
            event.returnValue = '';
            return '';
        }
    }

    /**
     * Enable page leave protection
     * @param {string} reason - Reason for protection (e.g., 'draft', 'streaming')
     */
    enableProtection(reason) {
        this._protectionReasons.add(reason);
        if (this._protectionReasons.size === 1) {
            window.addEventListener('beforeunload', this._handleBeforeUnload);
        }
        console.log(`[SessionManager] Protection enabled: ${reason}`);
    }

    /**
     * Disable page leave protection
     * @param {string} reason - Reason to remove
     */
    disableProtection(reason) {
        this._protectionReasons.delete(reason);
        if (this._protectionReasons.size === 0) {
            window.removeEventListener('beforeunload', this._handleBeforeUnload);
        }
        console.log(`[SessionManager] Protection disabled: ${reason}`);
    }

    /**
     * Check if there's a pending expiration
     * @returns {boolean}
     */
    hasPendingExpiration() {
        return this._isWarningShown;
    }

    /**
     * Notify that token has expired (from external source like stream-handler)
     */
    notifyTokenExpired() {
        console.log('[SessionManager] Token expired notification received');
        this._handleSessionExpired();
    }

    // =========================================================================
    // Token Refresh (Silent Refresh)
    // =========================================================================

    /**
     * Perform a silent token refresh
     * @private
     * @returns {Promise<boolean>}
     */
    async _performTokenRefresh() {
        if (this._isPaused) {
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
                this._consecutiveRefreshFailures = 0;

                // Check if SSO session (refresh token) is expiring soon
                const refreshTokenExpiresIn = data.refresh_token_expires_in;
                if (refreshTokenExpiresIn !== null && refreshTokenExpiresIn !== undefined && refreshTokenExpiresIn < WARNING_THRESHOLD_SECONDS) {
                    this._showIdleWarning();
                }

                const statusMsg = data.status === 'refreshed' ? 'Token refreshed' : 'Token still valid';
                console.log('[SessionManager] ' + statusMsg + '. Access token expires in ' + data.access_token_expires_in + 's');
                return true;
            } else if (response.status === 401) {
                this._consecutiveRefreshFailures++;
                console.log('[SessionManager] Session expired (401) - failure count: ' + this._consecutiveRefreshFailures);
                this._handleSessionExpired();
                return false;
            } else {
                console.warn('[SessionManager] Token refresh failed:', response.status);
                return false;
            }
        } catch (error) {
            console.error('[SessionManager] Token refresh error:', error);
            this._consecutiveRefreshFailures++;
            if (this._consecutiveRefreshFailures >= 3) {
                this._handleSessionExpired();
            }
            return false;
        }
    }

    /**
     * Start background token refresh (every 4 minutes)
     * @private
     */
    _startTokenRefresh() {
        this._tokenRefreshInterval = setInterval(async () => {
            const idleMinutes = this._getIdleTimeMinutes();
            if (idleMinutes < 5 && !this._isPaused) {
                await this._performTokenRefresh();
            }
        }, REFRESH_INTERVAL_MS);

        console.log('[SessionManager] Token refresh started (every 4 minutes when active)');
    }

    /**
     * Stop background token refresh
     * @private
     */
    _stopTokenRefresh() {
        if (this._tokenRefreshInterval) {
            clearInterval(this._tokenRefreshInterval);
            this._tokenRefreshInterval = null;
        }
    }

    // =========================================================================
    // Idle Detection & Warning Modal
    // =========================================================================

    /**
     * Check if user is idle and should be warned
     * @private
     */
    _checkIdleStatus() {
        if (this._isPaused || this._isWarningShown) {
            return;
        }

        const idleSeconds = this._getIdleTimeSeconds();
        const warningThresholdSeconds = this._config.ssoSessionIdleTimeoutSeconds - this._config.sessionExpirationWarningMinutes * 60;

        if (idleSeconds >= warningThresholdSeconds) {
            this._showIdleWarning();
        }
    }

    /**
     * Show the idle warning modal
     * @private
     */
    _showIdleWarning() {
        if (this._isWarningShown) return;

        this._isWarningShown = true;
        this._isPaused = true;

        const remainingSeconds = Math.max(0, this._config.ssoSessionIdleTimeoutSeconds - this._getIdleTimeSeconds());

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
                await this._extendSession();
            });
        }

        this._updateWarningCountdown(remainingSeconds);

        this._warningCountdownInterval = setInterval(() => {
            const remaining = Math.max(0, this._config.ssoSessionIdleTimeoutSeconds - this._getIdleTimeSeconds());

            if (remaining <= 0) {
                this._handleSessionExpired();
            } else {
                this._updateWarningCountdown(remaining);
            }
        }, 1000);

        this._warningModal = new bootstrap.Modal(modalEl);
        this._warningModal.show();

        console.log('[SessionManager] Idle warning shown');
    }

    /**
     * Update the countdown display
     * @private
     */
    _updateWarningCountdown(remainingSeconds) {
        const countdownEl = document.getElementById('warning-countdown');
        if (countdownEl) {
            const minutes = Math.floor(remainingSeconds / 60);
            const seconds = Math.floor(remainingSeconds % 60);
            countdownEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
    }

    /**
     * Hide the warning modal
     * @private
     */
    _hideWarningModal() {
        if (this._warningModal) {
            this._warningModal.hide();
            this._warningModal = null;
        }

        if (this._warningCountdownInterval) {
            clearInterval(this._warningCountdownInterval);
            this._warningCountdownInterval = null;
        }

        this._isWarningShown = false;
    }

    /**
     * Extend session - user clicked "Continue"
     * @private
     */
    async _extendSession() {
        console.log('[SessionManager] User requested session extension');

        const success = await this._performTokenRefresh();

        if (success) {
            this._lastActivityTime = Date.now();
            this._isPaused = false;
            this._hideWarningModal();
            console.log('[SessionManager] Session extended successfully');
        } else {
            this._handleSessionExpired();
        }
    }

    // =========================================================================
    // Session Expiration
    // =========================================================================

    /**
     * Handle session expiration
     * @private
     */
    async _handleSessionExpired() {
        console.log('[SessionManager] Session expired - redirecting to login');

        // Notify callback if set
        if (this._onSessionExpired) {
            this._onSessionExpired();
        }

        this.stopMonitoring();
        this._hideWarningModal();

        // Clear protection before redirect
        this._protectionReasons.clear();
        window.removeEventListener('beforeunload', this._handleBeforeUnload);

        // Notify before redirect callback
        if (this._onBeforeRedirect) {
            this._onBeforeRedirect();
        }

        window.location.href = '/api/auth/login';
    }

    // =========================================================================
    // OIDC Session Management Iframe
    // =========================================================================

    /**
     * Initialize OIDC Session Management iframe
     * @private
     */
    _initializeSessionIframe() {
        if (!this._config.checkSessionIframe) {
            console.log('[SessionManager] No check_session_iframe URL, skipping session iframe');
            return;
        }

        this._sessionIframe = document.createElement('iframe');
        this._sessionIframe.id = 'keycloak-session-iframe';
        this._sessionIframe.style.display = 'none';
        this._sessionIframe.src = this._config.checkSessionIframe;
        document.body.appendChild(this._sessionIframe);

        window.addEventListener('message', this._handleSessionIframeMessage);

        console.log('[SessionManager] OIDC Session Management iframe initialized');
    }

    /**
     * Handle messages from the session iframe
     * @private
     */
    _handleSessionIframeMessage(event) {
        if (!this._config.keycloakUrl) return;

        try {
            const keycloakOrigin = new URL(this._config.keycloakUrl).origin;
            if (event.origin !== keycloakOrigin) {
                return;
            }
        } catch {
            return;
        }

        const data = event.data;
        if (data === 'changed' || data === 'error') {
            console.log(`[SessionManager] Session iframe reports: ${data}`);
            this._checkBackendSession();
        }
    }

    /**
     * Check if the backend session is still valid
     * @private
     */
    async _checkBackendSession() {
        try {
            const response = await fetch('/api/auth/me', {
                credentials: 'include',
            });

            if (response.status === 401) {
                console.log('[SessionManager] Backend session invalid - logging out');
                this._handleSessionExpired();
            }
        } catch (error) {
            console.warn('[SessionManager] Backend session check failed:', error);
        }
    }

    /**
     * Clean up the session iframe
     * @private
     */
    _cleanupSessionIframe() {
        if (this._sessionCheckInterval) {
            clearInterval(this._sessionCheckInterval);
            this._sessionCheckInterval = null;
        }

        window.removeEventListener('message', this._handleSessionIframeMessage);

        if (this._sessionIframe && this._sessionIframe.parentNode) {
            this._sessionIframe.parentNode.removeChild(this._sessionIframe);
            this._sessionIframe = null;
        }
    }

    // =========================================================================
    // Idle Check Loop
    // =========================================================================

    /**
     * Start the idle check loop
     * @private
     */
    _startIdleCheck() {
        this._idleCheckInterval = setInterval(() => this._checkIdleStatus(), 10000);
        console.log('[SessionManager] Idle check started');
    }

    /**
     * Stop the idle check loop
     * @private
     */
    _stopIdleCheck() {
        if (this._idleCheckInterval) {
            clearInterval(this._idleCheckInterval);
            this._idleCheckInterval = null;
        }
    }

    // =========================================================================
    // Public API
    // =========================================================================

    /**
     * Initialize the session manager
     * Note: This is a placeholder for consistency with other managers.
     * Actual monitoring starts via startMonitoring() after authentication.
     */
    init() {
        // No-op: actual initialization happens in startMonitoring()
        // This method exists for API consistency with other managers
        console.log('[SessionManager] Initialized (monitoring not started yet)');
    }

    /**
     * Fetch session settings from the backend
     * @private
     */
    async _fetchSessionSettings() {
        try {
            const response = await fetch('/api/auth/session-settings', {
                credentials: 'include',
            });

            if (response.ok) {
                const settings = await response.json();
                this._config.keycloakUrl = settings.keycloak_url || '';
                this._config.realm = settings.realm || '';
                this._config.clientId = settings.client_id || '';
                this._config.ssoSessionIdleTimeoutSeconds = settings.sso_session_idle_timeout_seconds || 1800;
                this._config.sessionExpirationWarningMinutes = settings.session_expiration_warning_minutes || 2;
                this._config.checkSessionIframe = settings.check_session_iframe || null;

                console.log(`[SessionManager] Loaded settings: idle_timeout=${this._config.ssoSessionIdleTimeoutSeconds}s, ` + `warning=${this._config.sessionExpirationWarningMinutes}min`);
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
    async startMonitoring(sessionExpiredCallback = null, beforeRedirectCallback = null) {
        if (this._initialized) {
            console.log('[SessionManager] Already initialized, resetting...');
            this.stopMonitoring();
        }

        // Store callbacks
        this._onSessionExpired = sessionExpiredCallback;
        this._onBeforeRedirect = beforeRedirectCallback;

        // Fetch settings from backend
        await this._fetchSessionSettings();

        // Initialize state
        this._lastActivityTime = Date.now();
        this._isPaused = false;
        this._isWarningShown = false;
        this._initialized = true;

        // Start all monitoring
        this._startActivityTracking();
        this._startIdleCheck();
        this._startTokenRefresh();

        // Initialize OIDC session iframe for cross-app sync
        this._initializeSessionIframe();

        console.log(`[SessionManager] Monitoring started. Idle timeout: ${this._config.ssoSessionIdleTimeoutSeconds}s, ` + `Warning: ${this._config.sessionExpirationWarningMinutes}min before expiry`);
    }

    /**
     * Stop session monitoring
     */
    stopMonitoring() {
        this._stopActivityTracking();
        this._stopIdleCheck();
        this._stopTokenRefresh();
        this._cleanupSessionIframe();
        this._hideWarningModal();

        this._initialized = false;
        this._isPaused = false;
        this._isWarningShown = false;
        this._onSessionExpired = null;
        this._onBeforeRedirect = null;

        console.log('[SessionManager] Monitoring stopped');
    }

    /**
     * Reset session timer
     */
    resetTimer() {
        this._lastActivityTime = Date.now();
        this._isPaused = false;
        this._isWarningShown = false;
        this._hideWarningModal();
        console.log('[SessionManager] Session timer reset');
    }

    /**
     * Get session info for debugging
     * @returns {Object}
     */
    getSessionInfo() {
        return {
            idleTimeSeconds: this._getIdleTimeSeconds(),
            idleTimeoutSeconds: this._config.ssoSessionIdleTimeoutSeconds,
            warningMinutes: this._config.sessionExpirationWarningMinutes,
            isWarningShown: this._isWarningShown,
            isPaused: this._isPaused,
            isInitialized: this._initialized,
            keycloakUrl: this._config.keycloakUrl,
            realm: this._config.realm,
            clientId: this._config.clientId,
            protectionReasons: Array.from(this._protectionReasons),
        };
    }

    /**
     * Check if manager is initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }
}

// Export singleton instance
export const sessionManager = new SessionManager();
export default sessionManager;
