/**
 * ViewManager - SPA View State Manager
 *
 * Handles view transitions for the single-page application.
 * Manages showing/hiding of different view sections.
 *
 * @module managers/ViewManager
 */

import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';
import { namespaceManager } from './NamespaceManager.js';

/**
 * View identifiers
 * @readonly
 * @enum {string}
 */
export const Views = {
    DASHBOARD: 'dashboard',
    NAMESPACE_DETAIL: 'namespace-detail',
};

/**
 * ViewManager manages SPA view transitions
 */
export class ViewManager {
    /**
     * Create ViewManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {string} */
        this._currentView = Views.DASHBOARD;

        /** @type {Function[]} */
        this._unsubscribers = [];
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize view manager
     */
    init() {
        if (this._initialized) {
            console.warn('[ViewManager] Already initialized');
            return;
        }

        this._subscribeToEvents();
        this._initialized = true;
        console.log('[ViewManager] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._initialized = false;
        console.log('[ViewManager] Destroyed');
    }

    /**
     * Subscribe to events
     * @private
     */
    _subscribeToEvents() {
        this._unsubscribers.push(eventBus.on(Events.NAMESPACE_SELECTED, payload => this._handleNamespaceSelected(payload)));
    }

    // =========================================================================
    // View Navigation
    // =========================================================================

    /**
     * Show the dashboard view
     */
    showDashboard() {
        this._hideAllViews();
        this._showView('dashboard-view');
        this._currentView = Views.DASHBOARD;
        stateManager.set(StateKeys.CURRENT_NAMESPACE, null);
        stateManager.set(StateKeys.CURRENT_NAMESPACE_ID, null);
        console.log('[ViewManager] Showing dashboard');
    }

    /**
     * Show the namespace detail view
     * @param {Object} namespace - The namespace to display
     */
    showNamespaceDetail(namespace) {
        this._hideAllViews();
        this._renderNamespaceDetail(namespace);
        this._showView('namespace-detail-view');
        this._currentView = Views.NAMESPACE_DETAIL;
        console.log(`[ViewManager] Showing namespace: ${namespace.id}`);
    }

    /**
     * Get current view
     * @returns {string}
     */
    getCurrentView() {
        return this._currentView;
    }

    // =========================================================================
    // Event Handlers
    // =========================================================================

    /**
     * Handle namespace selected event
     * @private
     * @param {Object} payload - Event payload with namespaceId
     */
    async _handleNamespaceSelected(payload) {
        const { namespaceId } = payload;
        console.log(`[ViewManager] Loading namespace: ${namespaceId}`);

        try {
            // Load the namespace details
            const namespace = await namespaceManager.loadNamespace(namespaceId);
            this.showNamespaceDetail(namespace);
        } catch (error) {
            console.error(`[ViewManager] Failed to load namespace ${namespaceId}:`, error);
            eventBus.emit(Events.UI_TOAST, {
                type: 'error',
                message: `Failed to load namespace: ${error.message}`,
            });
        }
    }

    // =========================================================================
    // Private Methods
    // =========================================================================

    /**
     * Hide all views
     * @private
     */
    _hideAllViews() {
        const views = document.querySelectorAll('[data-view]');
        views.forEach(view => {
            view.classList.add('d-none');
        });
    }

    /**
     * Show a specific view
     * @private
     * @param {string} viewId - The view element ID
     */
    _showView(viewId) {
        const view = document.getElementById(viewId);
        if (view) {
            view.classList.remove('d-none');
        } else {
            console.warn(`[ViewManager] View not found: ${viewId}`);
        }
    }

    /**
     * Render namespace detail view content
     * @private
     * @param {Object} namespace - The namespace data
     */
    _renderNamespaceDetail(namespace) {
        const container = document.getElementById('namespace-detail-content');
        if (!container) {
            console.warn('[ViewManager] Namespace detail container not found');
            return;
        }

        const accessLevelBadgeColor = this._getAccessLevelBadgeColor(namespace.access_level);

        container.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-4">
                <div>
                    <h2 class="mb-1">
                        <i class="bi bi-collection me-2 text-primary"></i>${this._escapeHtml(namespace.name)}
                    </h2>
                    <p class="text-muted mb-2">${this._escapeHtml(namespace.description || 'No description')}</p>
                    <div class="d-flex gap-2 align-items-center">
                        <code class="bg-light px-2 py-1 rounded">${namespace.id}</code>
                        <span class="badge bg-${accessLevelBadgeColor}">${namespace.access_level}</span>
                    </div>
                </div>
                <div class="d-flex gap-2">
                    <button class="btn btn-outline-secondary" id="btn-back-to-dashboard">
                        <i class="bi bi-arrow-left me-1"></i>Back
                    </button>
                    <button class="btn btn-outline-primary" id="btn-edit-namespace">
                        <i class="bi bi-pencil me-1"></i>Edit
                    </button>
                </div>
            </div>

            <!-- Namespace Stats -->
            <div class="row mb-4">
                <div class="col-md-4">
                    <div class="card bg-light">
                        <div class="card-body text-center">
                            <h3 class="mb-0">${namespace.term_count || 0}</h3>
                            <small class="text-muted">Terms</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-light">
                        <div class="card-body text-center">
                            <h3 class="mb-0">${namespace.relationship_count || 0}</h3>
                            <small class="text-muted">Relationships</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-light">
                        <div class="card-body text-center">
                            <h3 class="mb-0">${namespace.rule_count || 0}</h3>
                            <small class="text-muted">Rules</small>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Terms Section -->
            <div class="card mb-4">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0">
                        <i class="bi bi-tags me-2"></i>Terms
                    </h5>
                    <button class="btn btn-sm btn-success" id="btn-add-term-to-namespace">
                        <i class="bi bi-plus-circle me-1"></i>Add Term
                    </button>
                </div>
                <div class="card-body">
                    <div id="namespace-terms-list" class="list-group list-group-flush">
                        ${this._renderTermsPlaceholder(namespace.term_count)}
                    </div>
                </div>
            </div>

            <!-- Metadata -->
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title mb-0">
                        <i class="bi bi-info-circle me-2"></i>Metadata
                    </h5>
                </div>
                <div class="card-body">
                    <dl class="row mb-0">
                        <dt class="col-sm-3">Created</dt>
                        <dd class="col-sm-9">${this._formatDate(namespace.created_at)}</dd>
                        <dt class="col-sm-3">Last Updated</dt>
                        <dd class="col-sm-9">${this._formatDate(namespace.updated_at)}</dd>
                        <dt class="col-sm-3">Owner</dt>
                        <dd class="col-sm-9">${namespace.owner_id || 'Unknown'}</dd>
                        <dt class="col-sm-3">Revision</dt>
                        <dd class="col-sm-9">${namespace.current_revision || 0}</dd>
                    </dl>
                </div>
            </div>
        `;

        // Attach event listeners
        this._attachNamespaceDetailListeners();
    }

    /**
     * Render terms placeholder or empty state
     * @private
     * @param {number} termCount - Number of terms
     * @returns {string} HTML string
     */
    _renderTermsPlaceholder(termCount) {
        if (termCount === 0) {
            return `
                <div class="text-center text-muted py-4">
                    <i class="bi bi-tags fs-3 d-block mb-2"></i>
                    No terms yet. Add one to get started!
                </div>
            `;
        }
        return `
            <div class="text-center text-muted py-4">
                <span class="loading-spinner me-2"></span>Loading terms...
            </div>
        `;
    }

    /**
     * Attach event listeners to namespace detail view elements
     * @private
     */
    _attachNamespaceDetailListeners() {
        document.getElementById('btn-back-to-dashboard')?.addEventListener('click', () => {
            this.showDashboard();
        });

        document.getElementById('btn-edit-namespace')?.addEventListener('click', () => {
            const namespace = stateManager.get(StateKeys.CURRENT_NAMESPACE);
            if (namespace) {
                eventBus.emit(Events.UI_TOAST, {
                    type: 'info',
                    message: 'Edit namespace coming soon!',
                });
            }
        });

        document.getElementById('btn-add-term-to-namespace')?.addEventListener('click', () => {
            eventBus.emit(Events.UI_TOAST, {
                type: 'info',
                message: 'Add term coming soon!',
            });
        });
    }

    // =========================================================================
    // Utilities
    // =========================================================================

    /**
     * Escape HTML to prevent XSS
     * @private
     * @param {string} str - String to escape
     * @returns {string}
     */
    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Format date for display
     * @private
     * @param {string} dateString - ISO date string
     * @returns {string}
     */
    _formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    /**
     * Get badge color for access level
     * @private
     * @param {string} accessLevel - Access level
     * @returns {string}
     */
    _getAccessLevelBadgeColor(accessLevel) {
        switch (accessLevel) {
            case 'public':
                return 'success';
            case 'tenant':
                return 'info';
            case 'private':
                return 'secondary';
            default:
                return 'secondary';
        }
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const viewManager = new ViewManager();
