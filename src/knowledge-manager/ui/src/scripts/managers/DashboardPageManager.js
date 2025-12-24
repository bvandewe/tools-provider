/**
 * DashboardPageManager - Manages the Dashboard page
 *
 * Handles dashboard stats display, recent items, and quick actions.
 *
 * @module managers/DashboardPageManager
 */

import { eventBus, Events } from '../core/event-bus.js';
import { apiService } from '../services/ApiService.js';
import { navigationManager, Pages } from './NavigationManager.js';

/**
 * DashboardPageManager class
 */
export class DashboardPageManager {
    /**
     * Create DashboardPageManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Array} */
        this._namespaces = [];

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
            console.warn('[DashboardPageManager] Already initialized');
            return;
        }

        this._cacheElements();
        this._attachEventListeners();
        this._subscribeToEvents();
        this._initialized = true;
        console.log('[DashboardPageManager] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._namespaces = [];
        this._initialized = false;
        console.log('[DashboardPageManager] Destroyed');
    }

    /**
     * Cache DOM elements
     * @private
     */
    _cacheElements() {
        this._elements = {
            page: document.getElementById('dashboard-page'),
            // Stats
            namespaceCount: document.getElementById('namespace-count'),
            termCount: document.getElementById('term-count'),
            relationshipCount: document.getElementById('relationship-count'),
            // Stats cards (for navigation)
            statsCards: document.querySelectorAll('.stats-card[data-navigate]'),
            // Quick actions
            btnNewNamespace: document.getElementById('btn-new-namespace'),
            btnNewTerm: document.getElementById('btn-new-term'),
            // View all buttons
            btnViewAllNamespaces: document.getElementById('btn-view-all-namespaces'),
            btnViewAllTerms: document.getElementById('btn-view-all-terms'),
            // Recent lists
            recentNamespacesList: document.getElementById('recent-namespaces-list'),
            recentTermsList: document.getElementById('recent-terms-list'),
        };
    }

    /**
     * Attach DOM event listeners
     * @private
     */
    _attachEventListeners() {
        // Stats cards click to navigate
        this._elements.statsCards?.forEach(card => {
            card.addEventListener('click', () => {
                const page = card.dataset.navigate;
                if (page) {
                    navigationManager.navigateTo(page);
                }
            });
        });

        // Quick action buttons
        this._elements.btnNewNamespace?.addEventListener('click', () => {
            eventBus.emit(Events.MODAL_NAMESPACE_OPEN, { mode: 'create' });
        });

        this._elements.btnNewTerm?.addEventListener('click', () => {
            eventBus.emit(Events.MODAL_TERM_OPEN, { mode: 'create' });
        });

        // View all buttons
        this._elements.btnViewAllNamespaces?.addEventListener('click', () => {
            navigationManager.navigateTo(Pages.NAMESPACES);
        });

        this._elements.btnViewAllTerms?.addEventListener('click', () => {
            navigationManager.navigateTo(Pages.TERMS);
        });
    }

    /**
     * Subscribe to EventBus events
     * @private
     */
    _subscribeToEvents() {
        this._unsubscribers.push(
            eventBus.on(Events.UI_PAGE_CHANGED, data => {
                if (data.to === 'dashboard') {
                    this.loadDashboard();
                }
            })
        );

        // Load dashboard on initial auth
        this._unsubscribers.push(
            eventBus.on(Events.AUTH_STATE_CHANGED, data => {
                if (data.isAuthenticated) {
                    // Small delay to ensure DOM is ready
                    setTimeout(() => this.loadDashboard(), 100);
                }
            })
        );

        // Refresh on data changes
        this._unsubscribers.push(eventBus.on(Events.NAMESPACE_CREATED, () => this.loadDashboard()));
        this._unsubscribers.push(eventBus.on(Events.NAMESPACE_DELETED, () => this.loadDashboard()));
        this._unsubscribers.push(eventBus.on(Events.TERM_CREATED, () => this.loadDashboard()));
        this._unsubscribers.push(eventBus.on(Events.TERM_DELETED, () => this.loadDashboard()));
    }

    // =========================================================================
    // Data Loading
    // =========================================================================

    /**
     * Load dashboard data
     */
    async loadDashboard() {
        try {
            // Load namespaces for stats and recent list
            this._namespaces = await apiService.getNamespaces();

            // Update stats
            this._updateStats();

            // Render recent items
            this._renderRecentNamespaces();
            await this._loadAndRenderRecentTerms();

            console.log('[DashboardPageManager] Dashboard loaded');
        } catch (error) {
            console.error('[DashboardPageManager] Failed to load dashboard:', error);
        }
    }

    /**
     * Update stats counts
     * @private
     */
    _updateStats() {
        if (this._elements.namespaceCount) {
            this._elements.namespaceCount.textContent = this._namespaces.length;
        }

        // Calculate total terms (would need to load all terms - for now just show placeholder)
        if (this._elements.termCount) {
            const totalTerms = this._namespaces.reduce((sum, ns) => sum + (ns.term_count || 0), 0);
            this._elements.termCount.textContent = totalTerms;
        }

        // Relationships - placeholder for now
        if (this._elements.relationshipCount) {
            this._elements.relationshipCount.textContent = '-';
        }
    }

    /**
     * Render recent namespaces list
     * @private
     */
    _renderRecentNamespaces() {
        if (!this._elements.recentNamespacesList) return;

        // Sort by updated_at desc and take top 5
        const recent = [...this._namespaces].sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at)).slice(0, 5);

        if (recent.length === 0) {
            this._elements.recentNamespacesList.innerHTML = `
                <div class="text-center text-muted py-3">
                    <small>No namespaces yet</small>
                </div>
            `;
            return;
        }

        this._elements.recentNamespacesList.innerHTML = recent
            .map(
                ns => `
            <a href="#" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
               data-namespace-id="${this._escapeHtml(ns.id)}">
                <div>
                    <div class="fw-medium">${this._escapeHtml(ns.name)}</div>
                    <small class="text-muted">${ns.term_count || 0} terms</small>
                </div>
                <span class="badge bg-${this._getAccessLevelColor(ns.access_level)}">${ns.access_level || 'private'}</span>
            </a>
        `
            )
            .join('');

        // Attach click handlers
        this._elements.recentNamespacesList.querySelectorAll('[data-namespace-id]').forEach(el => {
            el.addEventListener('click', e => {
                e.preventDefault();
                const namespaceId = el.dataset.namespaceId;
                // Navigate to namespaces tab and open modal
                navigationManager.navigateTo(Pages.NAMESPACES);
                eventBus.emit(Events.MODAL_NAMESPACE_OPEN, { namespaceId, mode: 'edit' });
            });
        });
    }

    /**
     * Load and render recent terms
     * @private
     */
    async _loadAndRenderRecentTerms() {
        if (!this._elements.recentTermsList) return;

        try {
            // Load terms from first few namespaces
            const allTerms = [];
            const namespacesToFetch = this._namespaces.slice(0, 3);

            for (const ns of namespacesToFetch) {
                try {
                    const terms = await apiService.getTerms(ns.id);
                    terms.forEach(t => {
                        t.namespace_id = ns.id;
                        t.namespace_name = ns.name;
                    });
                    allTerms.push(...terms);
                } catch (e) {
                    // Ignore individual namespace failures
                }
            }

            // Sort by updated_at desc and take top 5
            const recent = allTerms.sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at)).slice(0, 5);

            if (recent.length === 0) {
                this._elements.recentTermsList.innerHTML = `
                    <div class="text-center text-muted py-3">
                        <small>No terms yet</small>
                    </div>
                `;
                return;
            }

            this._elements.recentTermsList.innerHTML = recent
                .map(
                    term => `
                <a href="#" class="list-group-item list-group-item-action"
                   data-term-id="${this._escapeHtml(term.slug)}"
                   data-namespace-id="${this._escapeHtml(term.namespace_id)}">
                    <div class="d-flex justify-content-between">
                        <span class="fw-medium">${this._escapeHtml(term.label || term.slug)}</span>
                        <span class="badge bg-primary-subtle text-primary">${this._escapeHtml(term.namespace_name)}</span>
                    </div>
                    <small class="text-muted text-truncate d-block">${this._escapeHtml(term.definition || '')}</small>
                </a>
            `
                )
                .join('');

            // Attach click handlers
            this._elements.recentTermsList.querySelectorAll('[data-term-id]').forEach(el => {
                el.addEventListener('click', e => {
                    e.preventDefault();
                    const termId = el.dataset.termId;
                    const namespaceId = el.dataset.namespaceId;
                    // Navigate to terms tab and open modal
                    navigationManager.navigateTo(Pages.TERMS);
                    eventBus.emit(Events.MODAL_TERM_OPEN, { termId, namespaceId, mode: 'edit' });
                });
            });
        } catch (error) {
            console.error('[DashboardPageManager] Failed to load recent terms:', error);
            this._elements.recentTermsList.innerHTML = `
                <div class="text-center text-muted py-3">
                    <small>Failed to load terms</small>
                </div>
            `;
        }
    }

    // =========================================================================
    // Helpers
    // =========================================================================

    /**
     * Get color for access level badge
     * @private
     * @param {string} accessLevel
     * @returns {string}
     */
    _getAccessLevelColor(accessLevel) {
        const colors = {
            public: 'success',
            tenant: 'warning',
            private: 'secondary',
        };
        return colors[accessLevel] || 'secondary';
    }

    /**
     * Escape HTML to prevent XSS
     * @private
     * @param {string} str
     * @returns {string}
     */
    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

// Singleton export
export const dashboardPageManager = new DashboardPageManager();
