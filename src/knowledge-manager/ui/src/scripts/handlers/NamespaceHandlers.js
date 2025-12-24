/**
 * NamespaceHandlers - Namespace Event Handler Class
 *
 * Handles namespace-related events and updates UI accordingly.
 *
 * @module handlers/NamespaceHandlers
 */

import { Events, eventBus } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';
import { modalService } from '../services/ModalService.js';
import { authService } from '../services/AuthService.js';

/**
 * NamespaceHandlers manages event handlers for namespace events
 */
export class NamespaceHandlers {
    /**
     * Create a new NamespaceHandlers instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Function[]} */
        this._unsubscribers = [];

        // Bind handlers
        this._handleNamespacesLoaded = this._handleNamespacesLoaded.bind(this);
        this._handleNamespaceCreated = this._handleNamespaceCreated.bind(this);
        this._handleNamespaceDeleted = this._handleNamespaceDeleted.bind(this);
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize and register event handlers
     */
    init() {
        if (this._initialized) {
            console.warn('[NamespaceHandlers] Already initialized');
            return;
        }

        this._subscribeToEvents();
        this._initialized = true;

        console.log('[NamespaceHandlers] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._initialized = false;
        console.log('[NamespaceHandlers] Destroyed');
    }

    /**
     * Subscribe to events
     * @private
     */
    _subscribeToEvents() {
        this._unsubscribers.push(eventBus.on(Events.NAMESPACES_LOADED, this._handleNamespacesLoaded));

        this._unsubscribers.push(eventBus.on(Events.NAMESPACE_CREATED, this._handleNamespaceCreated));

        this._unsubscribers.push(eventBus.on(Events.NAMESPACE_DELETED, this._handleNamespaceDeleted));
    }

    // =========================================================================
    // Event Handlers
    // =========================================================================

    /**
     * Handle namespaces loaded - render list
     * @private
     * @param {Object} payload - Event payload
     */
    _handleNamespacesLoaded(payload) {
        const { namespaces, error } = payload;
        const listEl = document.getElementById('namespaces-list');
        if (!listEl) return;

        if (error) {
            listEl.innerHTML = `
                <div class="text-center text-danger py-4">
                    <i class="bi bi-exclamation-triangle fs-3 d-block mb-2"></i>
                    Failed to load namespaces. <a href="#" onclick="location.reload()">Retry</a>
                </div>
            `;
            return;
        }

        if (!stateManager.get(StateKeys.IS_AUTHENTICATED)) {
            listEl.innerHTML = `
                <div class="text-center py-4">
                    <i class="bi bi-lock fs-3 d-block mb-2 text-warning"></i>
                    <p class="text-muted mb-3">Please log in to view namespaces</p>
                    <a href="/api/auth/login" class="btn btn-primary">
                        <i class="bi bi-box-arrow-in-right me-1"></i>Login
                    </a>
                </div>
            `;
            return;
        }

        this._renderNamespacesList(listEl, namespaces);
        this._updateQuickActions();
    }

    /**
     * Handle namespace created
     * @private
     * @param {Object} payload - Event payload
     */
    _handleNamespaceCreated(payload) {
        modalService.success(`Namespace "${payload.namespace.name}" created successfully`);

        // Re-render list
        const namespaces = stateManager.get(StateKeys.NAMESPACES, []);
        const listEl = document.getElementById('namespaces-list');
        if (listEl) {
            this._renderNamespacesList(listEl, namespaces);
        }
    }

    /**
     * Handle namespace deleted
     * @private
     * @param {Object} payload - Event payload
     */
    _handleNamespaceDeleted(payload) {
        modalService.success(`Namespace "${payload.namespaceId}" deleted successfully`);

        // Re-render list
        const namespaces = stateManager.get(StateKeys.NAMESPACES, []);
        const listEl = document.getElementById('namespaces-list');
        if (listEl) {
            this._renderNamespacesList(listEl, namespaces);
        }
    }

    // =========================================================================
    // Rendering
    // =========================================================================

    /**
     * Render namespaces list
     * @private
     * @param {HTMLElement} container - Container element
     * @param {Array} namespaces - Namespaces array
     */
    _renderNamespacesList(container, namespaces) {
        if (namespaces.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="bi bi-folder-x fs-3 d-block mb-2"></i>
                    No namespaces yet. Create one to get started!
                </div>
            `;
            return;
        }

        container.innerHTML = namespaces
            .map(
                ns => `
                <div class="list-group-item list-group-item-action namespace-card"
                     data-namespace-id="${this._escapeHtml(ns.id)}"
                     role="button"
                     tabindex="0">
                    <div class="d-flex w-100 justify-content-between align-items-start">
                        <div>
                            <h6 class="mb-1">
                                <i class="bi bi-collection me-1 text-primary"></i>${this._escapeHtml(ns.name)}
                            </h6>
                            <p class="mb-1 text-muted small">${this._escapeHtml(ns.description || 'No description')}</p>
                            <small class="text-muted">
                                <code>${ns.id}</code> ·
                                ${ns.term_count || 0} terms ·
                                Created ${this._formatDate(ns.created_at)}
                            </small>
                        </div>
                        <span class="badge bg-${this._getAccessLevelBadgeColor(ns.access_level)}">${ns.access_level}</span>
                    </div>
                </div>
            `
            )
            .join('');

        // Attach click handlers to namespace cards
        this._attachNamespaceCardListeners(container);
    }

    /**
     * Attach click listeners to namespace cards
     * @private
     * @param {HTMLElement} container - Container element
     */
    _attachNamespaceCardListeners(container) {
        const cards = container.querySelectorAll('.namespace-card[data-namespace-id]');
        cards.forEach(card => {
            card.addEventListener('click', e => {
                e.preventDefault();
                const namespaceId = card.dataset.namespaceId;
                this._handleNamespaceCardClick(namespaceId);
            });

            // Also handle keyboard navigation (Enter/Space)
            card.addEventListener('keydown', e => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    const namespaceId = card.dataset.namespaceId;
                    this._handleNamespaceCardClick(namespaceId);
                }
            });
        });
    }

    /**
     * Handle namespace card click
     * @private
     * @param {string} namespaceId - The namespace ID
     */
    _handleNamespaceCardClick(namespaceId) {
        console.log(`[NamespaceHandlers] Namespace selected: ${namespaceId}`);
        eventBus.emit(Events.NAMESPACE_SELECTED, { namespaceId });
    }

    /**
     * Update quick action buttons based on auth and role
     * @private
     */
    _updateQuickActions() {
        const isAdmin = authService.isAdmin();
        const newNamespaceBtn = document.getElementById('btn-new-namespace');
        const newTermBtn = document.getElementById('btn-new-term');

        if (newNamespaceBtn) {
            newNamespaceBtn.disabled = !isAdmin;
            if (!isAdmin) {
                newNamespaceBtn.title = 'Requires admin role';
            }
        }
        if (newTermBtn) {
            newTermBtn.disabled = !isAdmin;
            if (!isAdmin) {
                newTermBtn.title = 'Requires admin role';
            }
        }
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
        });
    }

    /**
     * Get badge color for namespace access level
     * @private
     * @param {string} accessLevel - Namespace access level
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

export const namespaceHandlers = new NamespaceHandlers();
