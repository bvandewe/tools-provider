/**
 * Sidebar Manager
 * Handles sidebar state (collapse/expand) and responsive behavior
 */

import { isMobile, getSidebarCollapsed, saveSidebarCollapsed } from '../utils/helpers.js';

// =============================================================================
// State
// =============================================================================

let sidebarCollapsed = false;
let elements = {
    chatSidebar: null,
    sidebarOverlay: null,
    sidebarToggleBtn: null,
    collapseSidebarBtn: null,
    headerNewChatBtn: null,
};
let isAuthenticated = false;

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize sidebar manager
 * @param {Object} domElements - DOM element references
 * @param {boolean} authenticated - Whether user is authenticated
 */
export function initSidebarManager(domElements, authenticated) {
    elements = { ...domElements };
    isAuthenticated = authenticated;

    // Initialize state
    if (isMobile()) {
        // Always start collapsed on mobile
        sidebarCollapsed = true;
    } else {
        // Restore from localStorage on desktop
        sidebarCollapsed = getSidebarCollapsed();
    }

    applySidebarState();
}

/**
 * Update authentication state
 * @param {boolean} authenticated - Whether user is authenticated
 */
export function updateAuthState(authenticated) {
    isAuthenticated = authenticated;
    applySidebarState();
}

// =============================================================================
// State Management
// =============================================================================

/**
 * Apply the current sidebar collapsed state to the DOM
 */
function applySidebarState() {
    const mobile = isMobile();

    if (elements.chatSidebar) {
        // Hide sidebar completely if not authenticated
        if (!isAuthenticated) {
            elements.chatSidebar.classList.add('d-none');
            elements.chatSidebar.classList.remove('collapsed', 'open');
        } else {
            elements.chatSidebar.classList.remove('d-none');

            if (mobile) {
                // On mobile, use 'open' class (sidebar slides in from left)
                elements.chatSidebar.classList.remove('collapsed');
                elements.chatSidebar.classList.toggle('open', !sidebarCollapsed);
            } else {
                // On desktop, use 'collapsed' class (sidebar shrinks width)
                elements.chatSidebar.classList.remove('open');
                elements.chatSidebar.classList.toggle('collapsed', sidebarCollapsed);
            }
        }
    }

    // Show/hide header buttons based on sidebar state and auth
    if (elements.sidebarToggleBtn) {
        // Show expand button when collapsed AND authenticated
        elements.sidebarToggleBtn.classList.toggle('d-none', !sidebarCollapsed || !isAuthenticated);
    }

    if (elements.headerNewChatBtn) {
        // Show new chat in header when sidebar is collapsed and user is authenticated
        const showInHeader = sidebarCollapsed && isAuthenticated;
        elements.headerNewChatBtn.classList.toggle('d-none', !showInHeader);
    }
}

/**
 * Collapse the sidebar (hide it)
 */
export function collapseSidebar() {
    sidebarCollapsed = true;

    // Persist state (only on desktop)
    if (!isMobile()) {
        saveSidebarCollapsed(true);
    }

    applySidebarState();
    elements.sidebarOverlay?.classList.remove('active');
}

/**
 * Expand the sidebar (show it)
 */
export function expandSidebar() {
    sidebarCollapsed = false;

    // Persist state (only on desktop)
    if (!isMobile()) {
        saveSidebarCollapsed(false);
    }

    applySidebarState();

    // Show overlay on mobile when sidebar is open
    if (isMobile()) {
        elements.sidebarOverlay?.classList.add('active');
    }
}

/**
 * Close the sidebar (mobile only - same as collapse)
 */
export function closeSidebar() {
    collapseSidebar();
}

/**
 * Handle window resize events
 */
export function handleResize() {
    const mobile = isMobile();

    if (mobile) {
        // Auto-collapse on mobile when resizing down
        if (!sidebarCollapsed) {
            sidebarCollapsed = true;
            applySidebarState();
            elements.sidebarOverlay?.classList.remove('active');
        }
    } else {
        // Remove mobile classes when going back to desktop
        elements.chatSidebar?.classList.remove('open');
        elements.sidebarOverlay?.classList.remove('active');
        // Reapply desktop state
        applySidebarState();
    }
}

/**
 * Check if sidebar is currently collapsed
 * @returns {boolean}
 */
export function isSidebarCollapsed() {
    return sidebarCollapsed;
}
