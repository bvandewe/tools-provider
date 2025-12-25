/**
 * AdminPageManager - Manages the Admin page/tab
 *
 * Handles system status display, configuration info,
 * and user details.
 *
 * @module managers/AdminPageManager
 */

import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';
import { apiService } from '../services/ApiService.js';

/**
 * AdminPageManager class
 */
export class AdminPageManager {
    /**
     * Create AdminPageManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {boolean} */
        this._isLoading = false;

        /** @type {Function[]} */
        this._unsubscribers = [];
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize the page manager
     */
    init() {
        if (this._initialized) {
            console.warn('[AdminPageManager] Already initialized');
            return;
        }

        this._cacheElements();
        this._subscribeToEvents();
        this._initialized = true;
        console.log('[AdminPageManager] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._initialized = false;
        console.log('[AdminPageManager] Destroyed');
    }

    /**
     * Cache DOM elements
     * @private
     */
    _cacheElements() {
        this._elements = {
            // System Status indicators
            statusApi: document.getElementById('status-api'),
            statusMongodb: document.getElementById('status-mongodb'),
            statusNeo4j: document.getElementById('status-neo4j'),
            statusQdrant: document.getElementById('status-qdrant'),

            // Configuration info
            configVersion: document.getElementById('config-version'),
            configEnvironment: document.getElementById('config-environment'),
            configDebug: document.getElementById('config-debug'),

            // User info
            userUsername: document.getElementById('admin-user-username'),
            userEmail: document.getElementById('admin-user-email'),
            userRoles: document.getElementById('admin-user-roles'),
        };
    }

    /**
     * Subscribe to EventBus events
     * @private
     */
    _subscribeToEvents() {
        this._unsubscribers.push(
            eventBus.on(Events.UI_PAGE_CHANGED, data => {
                if (data.to === 'admin') {
                    this.loadAdminData();
                }
            })
        );
    }

    // =========================================================================
    // Data Loading
    // =========================================================================

    /**
     * Load admin page data
     */
    async loadAdminData() {
        if (this._isLoading) return;

        this._isLoading = true;
        console.log('[AdminPageManager] Loading admin data...');

        try {
            // Load system status
            await this._loadSystemStatus();

            // Load configuration
            await this._loadConfiguration();

            // Load user info from state
            this._loadUserInfo();
        } catch (error) {
            console.error('[AdminPageManager] Error loading admin data:', error);
        } finally {
            this._isLoading = false;
        }
    }

    /**
     * Load system status from health endpoint
     * @private
     */
    async _loadSystemStatus() {
        try {
            const health = await apiService.getHealth();

            // Update API status (if we got here, API is up)
            this._updateStatusIndicator(this._elements.statusApi, 'healthy');

            // Check individual service statuses if available
            if (health.services) {
                this._updateStatusIndicator(this._elements.statusMongodb, health.services.mongodb?.status || 'unknown');
                this._updateStatusIndicator(this._elements.statusNeo4j, health.services.neo4j?.status || 'unknown');
                this._updateStatusIndicator(this._elements.statusQdrant, health.services.qdrant?.status || 'unknown');
            } else {
                // Set all to unknown if no service details
                this._updateStatusIndicator(this._elements.statusMongodb, 'unknown');
                this._updateStatusIndicator(this._elements.statusNeo4j, 'unknown');
                this._updateStatusIndicator(this._elements.statusQdrant, 'unknown');
            }
        } catch (error) {
            console.error('[AdminPageManager] Failed to load system status:', error);
            this._updateStatusIndicator(this._elements.statusApi, 'unhealthy');
            this._updateStatusIndicator(this._elements.statusMongodb, 'unknown');
            this._updateStatusIndicator(this._elements.statusNeo4j, 'unknown');
            this._updateStatusIndicator(this._elements.statusQdrant, 'unknown');
        }
    }

    /**
     * Update status indicator element
     * @private
     * @param {HTMLElement} element - Status indicator element
     * @param {string} status - Status value ('healthy', 'unhealthy', 'unknown')
     */
    _updateStatusIndicator(element, status) {
        if (!element) return;

        // Remove existing status classes
        element.classList.remove('status-healthy', 'status-unhealthy', 'status-unknown');

        // Add new status class
        switch (status) {
            case 'healthy':
            case 'ok':
            case 'up':
                element.classList.add('status-healthy');
                break;
            case 'unhealthy':
            case 'error':
            case 'down':
                element.classList.add('status-unhealthy');
                break;
            default:
                element.classList.add('status-unknown');
        }
    }

    /**
     * Load configuration info
     * @private
     */
    async _loadConfiguration() {
        try {
            // Try to get config from API info endpoint if available
            const info = (await apiService.getInfo?.()) || {};

            if (this._elements.configVersion) {
                this._elements.configVersion.textContent = info.version || '1.0.0';
            }
            if (this._elements.configEnvironment) {
                this._elements.configEnvironment.textContent = info.environment || 'development';
            }
            if (this._elements.configDebug) {
                this._elements.configDebug.textContent = info.debug ? 'Enabled' : 'Disabled';
            }
        } catch (error) {
            console.warn('[AdminPageManager] Failed to load configuration:', error);
            // Set defaults
            if (this._elements.configVersion) this._elements.configVersion.textContent = '-';
            if (this._elements.configEnvironment) this._elements.configEnvironment.textContent = '-';
            if (this._elements.configDebug) this._elements.configDebug.textContent = '-';
        }
    }

    /**
     * Load user info from state
     * @private
     */
    _loadUserInfo() {
        const user = stateManager.get(StateKeys.USER_INFO) || {};

        if (this._elements.userUsername) {
            this._elements.userUsername.textContent = user.preferred_username || user.username || '-';
        }
        if (this._elements.userEmail) {
            this._elements.userEmail.textContent = user.email || '-';
        }
        if (this._elements.userRoles) {
            const roles = user.realm_access?.roles || user.roles || [];
            this._elements.userRoles.textContent = roles.length > 0 ? roles.join(', ') : '-';
        }
    }
}

// Export singleton instance
export const adminPageManager = new AdminPageManager();
