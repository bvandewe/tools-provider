/**
 * NavigationManager - SPA Tab Navigation with URL Hash Routing
 *
 * Handles page navigation for the single-page application.
 * Manages showing/hiding of different page sections and URL hash routing.
 *
 * @module managers/NavigationManager
 */

import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';

/**
 * Page identifiers
 * @readonly
 * @enum {string}
 */
export const Pages = {
    DASHBOARD: 'dashboard',
    NAMESPACES: 'namespaces',
    TERMS: 'terms',
    ADMIN: 'admin',
};

/**
 * NavigationManager manages SPA page transitions with URL hash routing
 */
export class NavigationManager {
    /**
     * Create NavigationManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {string} */
        this._currentPage = Pages.DASHBOARD;

        /** @type {Function[]} */
        this._unsubscribers = [];

        /** @type {Map<string, HTMLElement>} */
        this._pageElements = new Map();

        /** @type {Map<string, HTMLElement>} */
        this._navLinks = new Map();

        /** @type {Function|null} */
        this._hashChangeHandler = null;
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize navigation manager
     */
    init() {
        if (this._initialized) {
            console.warn('[NavigationManager] Already initialized');
            return;
        }

        this._cacheElements();
        this._attachEventListeners();
        this._handleInitialRoute();
        this._initialized = true;
        console.log('[NavigationManager] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];

        if (this._hashChangeHandler) {
            window.removeEventListener('hashchange', this._hashChangeHandler);
            this._hashChangeHandler = null;
        }

        this._pageElements.clear();
        this._navLinks.clear();
        this._initialized = false;
        console.log('[NavigationManager] Destroyed');
    }

    /**
     * Cache page and nav elements
     * @private
     */
    _cacheElements() {
        // Cache page elements
        document.querySelectorAll('[data-page]').forEach(el => {
            const page = el.dataset.page;
            // Only cache page containers (not nav links)
            if (el.classList.contains('page-content')) {
                this._pageElements.set(page, el);
            }
        });

        // Cache nav links
        document.querySelectorAll('#admin-nav [data-page]').forEach(el => {
            const page = el.dataset.page;
            this._navLinks.set(page, el);
        });

        console.log(`[NavigationManager] Cached ${this._pageElements.size} pages, ${this._navLinks.size} nav links`);
    }

    /**
     * Attach event listeners
     * @private
     */
    _attachEventListeners() {
        // Listen for nav link clicks
        this._navLinks.forEach((link, page) => {
            link.addEventListener('click', e => {
                e.preventDefault();
                this.navigateTo(page);
            });
        });

        // Listen for hash changes (browser back/forward)
        this._hashChangeHandler = () => this._handleHashChange();
        window.addEventListener('hashchange', this._hashChangeHandler);

        // Subscribe to relevant events
        this._unsubscribers.push(eventBus.on(Events.AUTH_STATE_CHANGED, () => this._handleAuthStateChange()));
    }

    /**
     * Handle initial route from URL hash
     * @private
     */
    _handleInitialRoute() {
        const hash = window.location.hash;
        const page = this._pageFromHash(hash);
        const targetPage = page && this._pageElements.has(page) ? page : Pages.DASHBOARD;

        this._showPage(targetPage);

        // Emit UI_PAGE_CHANGED so page managers load their data
        // Use setTimeout to ensure all managers are fully initialized
        setTimeout(() => {
            eventBus.emit(Events.UI_PAGE_CHANGED, {
                from: null,
                to: targetPage,
            });
        }, 0);
    }

    /**
     * Handle URL hash change
     * @private
     */
    _handleHashChange() {
        const hash = window.location.hash;
        const page = this._pageFromHash(hash);

        if (page && this._pageElements.has(page) && page !== this._currentPage) {
            this._showPage(page);
        }
    }

    /**
     * Handle auth state change
     * @private
     */
    _handleAuthStateChange() {
        // On logout, reset to dashboard
        const isAuthenticated = stateManager.get(StateKeys.IS_AUTHENTICATED);
        if (!isAuthenticated) {
            this._currentPage = Pages.DASHBOARD;
        }
    }

    // =========================================================================
    // Navigation
    // =========================================================================

    /**
     * Navigate to a specific page
     * @param {string} page - The page identifier
     * @param {Object} [options={}] - Navigation options
     * @param {boolean} [options.updateHash=true] - Whether to update URL hash
     */
    navigateTo(page, { updateHash = true } = {}) {
        if (!this._pageElements.has(page)) {
            console.warn(`[NavigationManager] Unknown page: ${page}`);
            return;
        }

        if (page === this._currentPage) {
            console.log(`[NavigationManager] Already on page: ${page}`);
            return;
        }

        // Update URL hash
        if (updateHash) {
            const hash = this._hashFromPage(page);
            history.pushState(null, '', hash);
        }

        this._showPage(page);

        // Emit navigation event
        eventBus.emit(Events.UI_PAGE_CHANGED, {
            from: this._currentPage,
            to: page,
        });
    }

    /**
     * Get current page
     * @returns {string}
     */
    getCurrentPage() {
        return this._currentPage;
    }

    // =========================================================================
    // Private Methods
    // =========================================================================

    /**
     * Show a specific page
     * @private
     * @param {string} page - The page identifier
     */
    _showPage(page) {
        // Hide all pages
        this._pageElements.forEach(el => {
            el.classList.add('d-none');
        });

        // Show target page
        const pageEl = this._pageElements.get(page);
        if (pageEl) {
            pageEl.classList.remove('d-none');
        }

        // Update nav active state
        this._navLinks.forEach((link, linkPage) => {
            if (linkPage === page) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });

        this._currentPage = page;
        console.log(`[NavigationManager] Showing page: ${page}`);
    }

    /**
     * Convert hash to page identifier
     * @private
     * @param {string} hash - URL hash (e.g., '#/namespaces')
     * @returns {string|null}
     */
    _pageFromHash(hash) {
        if (!hash || hash === '#' || hash === '#/') {
            return Pages.DASHBOARD;
        }

        // Remove '#/' prefix
        const pageName = hash.replace(/^#\/?/, '').toLowerCase();

        // Map to page constant
        switch (pageName) {
            case 'dashboard':
            case '':
                return Pages.DASHBOARD;
            case 'namespaces':
                return Pages.NAMESPACES;
            case 'terms':
                return Pages.TERMS;
            case 'admin':
                return Pages.ADMIN;
            default:
                return null;
        }
    }

    /**
     * Convert page identifier to hash
     * @private
     * @param {string} page - Page identifier
     * @returns {string}
     */
    _hashFromPage(page) {
        switch (page) {
            case Pages.DASHBOARD:
                return '#/dashboard';
            case Pages.NAMESPACES:
                return '#/namespaces';
            case Pages.TERMS:
                return '#/terms';
            default:
                return '#/';
        }
    }
}

// Singleton export
export const navigationManager = new NavigationManager();
