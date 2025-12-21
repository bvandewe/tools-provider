/**
 * Sidebar Manager - Sidebar UI State Management
 *
 * Manages the sidebar DOM and state.
 *
 * @module ui/managers/sidebar-manager
 */

import { eventBus, Events } from '../../core/event-bus.js';
import { isMobile, MOBILE_BREAKPOINT } from '../../utils/dom.js';
import { getSidebarCollapsed, saveSidebarCollapsed } from '../../utils/storage.js';

// =============================================================================
// State
// =============================================================================

/** @type {Object} DOM element references */
let elements = {
    chatSidebar: null,
    sidebarOverlay: null,
    sidebarToggleBtn: null,
    collapseSidebarBtn: null,
};

/** @type {boolean} Whether sidebar is collapsed */
let isCollapsed = false;

/** @type {boolean} Whether user is authenticated */
let isAuthenticated = false;

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize sidebar manager
 * @param {Object} domElements - DOM element references
 * @param {boolean} authState - Initial authentication state
 */
export function initSidebarManager(domElements, authState = false) {
    elements = { ...elements, ...domElements };
    isAuthenticated = authState;

    // Load saved state
    isCollapsed = getSidebarCollapsed();

    // Apply initial state
    applyCollapsedState();

    // Handle window resize
    window.addEventListener('resize', handleResize);

    console.log('[SidebarManager] Initialized');
}

/**
 * Update authentication state
 * @param {boolean} authenticated - Whether user is authenticated
 */
export function updateAuthState(authenticated) {
    isAuthenticated = authenticated;

    if (!authenticated) {
        closeSidebar();
    }
}

// =============================================================================
// Sidebar Actions
// =============================================================================

/**
 * Expand sidebar
 */
export function expandSidebar() {
    if (!elements.chatSidebar) return;

    elements.chatSidebar.classList.remove('collapsed');
    elements.chatSidebar.classList.add('expanded');

    if (isMobile()) {
        elements.sidebarOverlay?.classList.add('active');
    }

    isCollapsed = false;
    saveSidebarCollapsed(false);

    eventBus.emit(Events.UI_SIDEBAR_TOGGLE, { expanded: true });
}

/**
 * Collapse sidebar
 */
export function collapseSidebar() {
    if (!elements.chatSidebar) return;

    elements.chatSidebar.classList.remove('expanded');
    elements.chatSidebar.classList.add('collapsed');
    elements.sidebarOverlay?.classList.remove('active');

    isCollapsed = true;
    saveSidebarCollapsed(true);

    eventBus.emit(Events.UI_SIDEBAR_TOGGLE, { expanded: false });
}

/**
 * Close sidebar (mobile)
 */
export function closeSidebar() {
    if (!elements.chatSidebar) return;

    if (isMobile()) {
        elements.chatSidebar.classList.remove('expanded');
        elements.sidebarOverlay?.classList.remove('active');
    } else {
        collapseSidebar();
    }
}

/**
 * Toggle sidebar
 */
export function toggleSidebar() {
    if (isCollapsed) {
        expandSidebar();
    } else {
        collapseSidebar();
    }
}

// =============================================================================
// Internal Functions
// =============================================================================

/**
 * Apply collapsed state to DOM
 */
function applyCollapsedState() {
    if (!elements.chatSidebar) return;

    if (isCollapsed) {
        elements.chatSidebar.classList.add('collapsed');
        elements.chatSidebar.classList.remove('expanded');
    } else {
        elements.chatSidebar.classList.remove('collapsed');
        // Don't add expanded on desktop - let CSS handle it
        if (isMobile()) {
            elements.chatSidebar.classList.add('expanded');
        }
    }
}

/**
 * Handle window resize
 */
export function handleResize() {
    // On resize, adjust sidebar behavior
    if (isMobile()) {
        // On mobile, always close sidebar when resizing
        if (elements.chatSidebar?.classList.contains('expanded')) {
            closeSidebar();
        }
    } else {
        // On desktop, remove overlay
        elements.sidebarOverlay?.classList.remove('active');
    }
}

/**
 * Check if sidebar is collapsed
 * @returns {boolean} Collapsed state
 */
export function isSidebarCollapsed() {
    return isCollapsed;
}

export default {
    initSidebarManager,
    updateAuthState,
    expandSidebar,
    collapseSidebar,
    closeSidebar,
    toggleSidebar,
    handleResize,
    isSidebarCollapsed,
};
