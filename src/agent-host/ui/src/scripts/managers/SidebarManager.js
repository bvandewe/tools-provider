/**
 * SidebarManager - Sidebar UI State Management
 *
 * Manages the sidebar DOM and state including:
 * - Sidebar expand/collapse
 * - Agent selector menu
 *
 * @module managers/SidebarManager
 */

import { eventBus, Events } from '../core/event-bus.js';
import { isMobile, MOBILE_BREAKPOINT } from '../utils/dom.js';
import { getSidebarCollapsed, saveSidebarCollapsed } from '../utils/storage.js';
import { selectDefinition, getDefinitionIcon } from '../domain/definition.js';

/**
 * SidebarManager manages the sidebar UI state
 */
export class SidebarManager {
    /**
     * Create a new SidebarManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Object} DOM element references */
        this._elements = {
            chatSidebar: null,
            sidebarOverlay: null,
            sidebarToggleBtn: null,
            collapseSidebarBtn: null,
            // Agent selector elements
            sidebarAgentMenu: null,
            sidebarSelectedAgentIcon: null,
            headerSelectedAgentIcon: null,
            headerSelectedAgentName: null,
        };

        /** @type {boolean} Whether sidebar is collapsed */
        this._isCollapsed = false;

        /** @type {boolean} Whether user is authenticated */
        this._isAuthenticated = false;

        // Bind methods for callbacks
        this._handleResize = this._handleResize.bind(this);
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize sidebar manager
     * @param {Object} domElements - DOM element references
     * @param {boolean} authState - Initial authentication state
     */
    init(domElements = {}, authState = false) {
        if (this._initialized) {
            console.warn('[SidebarManager] Already initialized');
            return;
        }

        this._elements = { ...this._elements, ...domElements };
        this._isAuthenticated = authState;

        // Load saved state
        this._isCollapsed = getSidebarCollapsed();

        // Apply initial state
        this._applyCollapsedState();

        // Handle window resize
        window.addEventListener('resize', this._handleResize);

        this._initialized = true;
        console.log('[SidebarManager] Initialized');
    }

    /**
     * Update authentication state
     * @param {boolean} authenticated - Whether user is authenticated
     */
    updateAuthState(authenticated) {
        this._isAuthenticated = authenticated;

        if (!authenticated) {
            this.closeSidebar();
        }
    }

    // =========================================================================
    // Sidebar Actions
    // =========================================================================

    /**
     * Expand sidebar
     */
    expandSidebar() {
        if (!this._elements.chatSidebar) return;

        this._elements.chatSidebar.classList.remove('collapsed');
        this._elements.chatSidebar.classList.add('expanded');

        if (isMobile()) {
            this._elements.sidebarOverlay?.classList.add('active');
        }

        this._isCollapsed = false;
        saveSidebarCollapsed(false);

        eventBus.emit(Events.UI_SIDEBAR_TOGGLE, { expanded: true });
    }

    /**
     * Collapse sidebar
     */
    collapseSidebar() {
        if (!this._elements.chatSidebar) return;

        this._elements.chatSidebar.classList.remove('expanded');
        this._elements.chatSidebar.classList.add('collapsed');
        this._elements.sidebarOverlay?.classList.remove('active');

        this._isCollapsed = true;
        saveSidebarCollapsed(true);

        eventBus.emit(Events.UI_SIDEBAR_TOGGLE, { expanded: false });
    }

    /**
     * Close sidebar (mobile)
     */
    closeSidebar() {
        if (!this._elements.chatSidebar) return;

        if (isMobile()) {
            this._elements.chatSidebar.classList.remove('expanded');
            this._elements.sidebarOverlay?.classList.remove('active');
        } else {
            this.collapseSidebar();
        }
    }

    /**
     * Toggle sidebar
     */
    toggleSidebar() {
        if (this._isCollapsed) {
            this.expandSidebar();
        } else {
            this.collapseSidebar();
        }
    }

    // =========================================================================
    // Internal Methods
    // =========================================================================

    /**
     * Apply collapsed state to DOM
     * @private
     */
    _applyCollapsedState() {
        if (!this._elements.chatSidebar) return;

        if (this._isCollapsed) {
            this._elements.chatSidebar.classList.add('collapsed');
            this._elements.chatSidebar.classList.remove('expanded');
        } else {
            this._elements.chatSidebar.classList.remove('collapsed');
            // Don't add expanded on desktop - let CSS handle it
            if (isMobile()) {
                this._elements.chatSidebar.classList.add('expanded');
            }
        }
    }

    /**
     * Handle window resize
     * @private
     */
    _handleResize() {
        // On resize, adjust sidebar behavior
        if (isMobile()) {
            // On mobile, always close sidebar when resizing
            if (this._elements.chatSidebar?.classList.contains('expanded')) {
                this.closeSidebar();
            }
        } else {
            // On desktop, remove overlay
            this._elements.sidebarOverlay?.classList.remove('active');
        }
    }

    /**
     * Check if sidebar is collapsed
     * @returns {boolean} Collapsed state
     */
    isSidebarCollapsed() {
        return this._isCollapsed;
    }

    // =========================================================================
    // Agent Selector
    // =========================================================================

    /**
     * Populate sidebar agent menu with available definitions
     * @param {Array} definitions - List of agent definitions
     */
    populateSidebarAgentMenu(definitions) {
        const menu = this._elements.sidebarAgentMenu;
        if (!menu) return;

        menu.innerHTML = '';

        // Sort definitions alphabetically by name
        const sortedDefinitions = [...definitions].sort((a, b) => (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' }));

        sortedDefinitions.forEach(def => {
            const icon = getDefinitionIcon(def);
            const description = def.description ? this._escapeHtml(def.description) : '';
            const li = document.createElement('li');
            li.innerHTML = `
                <button class="dropdown-item sidebar-agent-item" type="button" data-definition-id="${def.id}">
                    <span class="agent-icon"><i class="bi ${icon}"></i></span>
                    <span class="agent-info">
                        <span class="agent-name">${this._escapeHtml(def.name)}</span>
                        ${description ? `<span class="agent-description">${description}</span>` : ''}
                    </span>
                </button>
            `;

            li.querySelector('button').addEventListener('click', () => {
                selectDefinition(def.id);
            });

            menu.appendChild(li);
        });

        console.log(`[SidebarManager] Populated agent menu with ${definitions.length} definitions`);
    }

    /**
     * Update sidebar agent selector icon and active state
     * @param {Object} definition - Selected definition
     */
    updateSidebarAgentSelector(definition) {
        if (!definition) return;

        const icon = getDefinitionIcon(definition);
        if (this._elements.sidebarSelectedAgentIcon) {
            this._elements.sidebarSelectedAgentIcon.className = `bi ${icon}`;
            this._elements.sidebarSelectedAgentIcon.title = definition.name;
        }

        // Update active state in sidebar agent menu
        const menu = this._elements.sidebarAgentMenu;
        if (menu) {
            menu.querySelectorAll('.sidebar-agent-item').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.definitionId === definition.id);
            });
        }
    }

    /**
     * Update header agent selector (legacy - kept for compatibility)
     * @param {Object} definition - Selected definition
     */
    updateHeaderAgentSelector(definition) {
        if (!definition) return;

        if (this._elements.headerSelectedAgentIcon) {
            this._elements.headerSelectedAgentIcon.className = `bi ${definition.icon || 'bi-robot'}`;
        }
        if (this._elements.headerSelectedAgentName) {
            this._elements.headerSelectedAgentName.textContent = definition.name;
        }
    }

    /**
     * Reset sidebar agent selector to default state
     */
    resetSidebarAgentSelector() {
        if (this._elements.sidebarSelectedAgentIcon) {
            this._elements.sidebarSelectedAgentIcon.className = 'bi bi-robot';
        }
    }

    // =========================================================================
    // Utilities
    // =========================================================================

    /**
     * Escape HTML to prevent XSS
     * @private
     * @param {string} str - String to escape
     * @returns {string} Escaped string
     */
    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // =========================================================================
    // Getters
    // =========================================================================

    /**
     * Get DOM elements
     * @returns {Object} DOM elements
     */
    get elements() {
        return this._elements;
    }

    /**
     * Check if initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }

    // =========================================================================
    // Cleanup
    // =========================================================================

    /**
     * Cleanup resources
     */
    destroy() {
        window.removeEventListener('resize', this._handleResize);

        this._elements = {
            chatSidebar: null,
            sidebarOverlay: null,
            sidebarToggleBtn: null,
            collapseSidebarBtn: null,
            sidebarAgentMenu: null,
            sidebarSelectedAgentIcon: null,
            headerSelectedAgentIcon: null,
            headerSelectedAgentName: null,
        };

        this._initialized = false;
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const sidebarManager = new SidebarManager();
