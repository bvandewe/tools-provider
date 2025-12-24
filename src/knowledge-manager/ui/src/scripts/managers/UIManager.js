/**
 * UIManager - Class-based UI State Manager
 *
 * Handles UI state updates, status indicator, and authentication UI.
 *
 * @module managers/UIManager
 */

import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';

/**
 * UIManager manages UI state and interactions
 */
export class UIManager {
    /**
     * Create UIManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Object} DOM elements */
        this._elements = {
            userDropdown: null,
            loginBtn: null,
            logoutBtn: null,
            navUsername: null,
            dropdownUserName: null,
            dropdownUserRoles: null,
            adminNav: null,
            adminNavItem: null,
            connectionStatus: null,
            appVersion: null,
            themeToggle: null,
        };
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize UI manager with DOM elements
     */
    init() {
        if (this._initialized) {
            console.warn('[UIManager] Already initialized');
            return;
        }

        this._cacheElements();
        this._initialized = true;
        console.log('[UIManager] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._elements = {};
        this._initialized = false;
        console.log('[UIManager] Destroyed');
    }

    /**
     * Cache DOM elements
     * @private
     */
    _cacheElements() {
        this._elements = {
            // Auth UI
            userDropdown: document.getElementById('user-dropdown'),
            loginBtn: document.getElementById('login-btn'),
            logoutBtn: document.getElementById('logout-btn'),
            navUsername: document.getElementById('nav-username'),
            dropdownUserName: document.getElementById('dropdown-user-name'),
            dropdownUserRoles: document.getElementById('dropdown-user-roles'),
            adminNav: document.getElementById('admin-nav'),
            adminNavItem: document.getElementById('admin-nav-item'),
            // Main content sections
            loginSection: document.getElementById('login-section'),
            mainContent: document.getElementById('main-content'),
            // Status
            connectionStatus: document.getElementById('connection-status'),
            appVersion: document.getElementById('app-version'),
            themeToggle: document.getElementById('theme-toggle'),
        };
    }

    // =========================================================================
    // UI State Updates
    // =========================================================================

    /**
     * Update UI based on authentication state
     * @param {boolean} isAuthenticated - Whether user is authenticated
     * @param {Object|null} currentUser - Current user object
     * @param {boolean} isAdmin - Whether user is admin
     */
    updateAuthUI(isAuthenticated, currentUser, isAdmin) {
        console.log('[UIManager] Updating auth UI, authenticated:', isAuthenticated);

        // Toggle login section and main content visibility
        if (this._elements.loginSection) {
            this._elements.loginSection.style.display = isAuthenticated ? 'none' : 'block';
        }
        if (this._elements.mainContent) {
            this._elements.mainContent.style.display = isAuthenticated ? 'block' : 'none';
        }

        // Toggle user dropdown visibility
        if (this._elements.userDropdown) {
            this._elements.userDropdown.style.display = isAuthenticated ? 'block' : 'none';
        }

        // Toggle login button visibility
        if (this._elements.loginBtn) {
            this._elements.loginBtn.style.display = isAuthenticated ? 'none' : 'flex';
        }

        // Toggle admin nav visibility
        if (this._elements.adminNav) {
            this._elements.adminNav.style.display = isAuthenticated ? 'flex' : 'none';
        }

        // Update user display
        if (isAuthenticated && currentUser) {
            const displayName = currentUser.name || currentUser.preferred_username || currentUser.email || 'User';

            if (this._elements.navUsername) {
                this._elements.navUsername.textContent = displayName;
            }
            if (this._elements.dropdownUserName) {
                this._elements.dropdownUserName.textContent = displayName;
            }
            if (this._elements.dropdownUserRoles) {
                const roles = currentUser.roles || [];
                this._elements.dropdownUserRoles.textContent = roles.length ? `Roles: ${roles.join(', ')}` : '';
            }

            // Show admin nav item for admin users
            if (this._elements.adminNavItem) {
                this._elements.adminNavItem.classList.toggle('d-none', !isAdmin);
            }
        }
    }

    /**
     * Update connection status indicator
     * @param {boolean} connected - Whether connected to API
     */
    updateConnectionStatus(connected) {
        stateManager.set(StateKeys.CONNECTION_STATUS, connected ? 'connected' : 'disconnected');

        if (this._elements.connectionStatus) {
            const icon = this._elements.connectionStatus.querySelector('i');
            if (icon) {
                if (connected) {
                    icon.className = 'bi bi-wifi';
                    this._elements.connectionStatus.classList.remove('text-secondary');
                    this._elements.connectionStatus.classList.add('text-success');
                    this._elements.connectionStatus.title = 'Connected';
                } else {
                    icon.className = 'bi bi-wifi-off';
                    this._elements.connectionStatus.classList.remove('text-success');
                    this._elements.connectionStatus.classList.add('text-secondary');
                    this._elements.connectionStatus.title = 'Disconnected';
                }
            }
        }

        eventBus.emit(Events.CONNECTION_STATUS_CHANGED, { connected });
    }

    /**
     * Update app version display
     * @param {string} version - App version string
     */
    updateAppVersion(version) {
        stateManager.set(StateKeys.APP_VERSION, version);

        if (this._elements.appVersion) {
            this._elements.appVersion.textContent = version || '-';
        }
    }

    // =========================================================================
    // Loading States
    // =========================================================================

    /**
     * Show loading state
     * @param {string} [message='Loading...'] - Loading message
     */
    showLoading(message = 'Loading...') {
        stateManager.set(StateKeys.IS_LOADING, true);
        eventBus.emit(Events.UI_LOADING_START, { message });
    }

    /**
     * Hide loading state
     */
    hideLoading() {
        stateManager.set(StateKeys.IS_LOADING, false);
        eventBus.emit(Events.UI_LOADING_END);
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const uiManager = new UIManager();
