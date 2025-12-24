/**
 * Knowledge Manager - Admin Script
 *
 * Admin page-specific initialization.
 * Uses the class-based architecture from main.js.
 *
 * @module admin
 */

import { apiService } from './services/ApiService.js';
import { authService } from './services/AuthService.js';
import { stateManager, StateKeys } from './core/state-manager.js';

// =============================================================================
// Admin Page Initialization
// =============================================================================

/**
 * Initialize admin page
 */
async function initAdmin() {
    console.log('[Admin] Initializing...');

    // Wait for main app to initialize
    await waitForApp();

    // Check system status
    await checkSystemStatus();

    // Load user info
    await loadUserInfo();

    // Load config info
    await loadConfigInfo();

    console.log('[Admin] Initialized');
}

/**
 * Wait for the main KnowledgeApp to be initialized
 * @returns {Promise<void>}
 */
async function waitForApp() {
    let attempts = 0;
    while (!window.knowledgeApp && attempts < 50) {
        await new Promise(resolve => setTimeout(resolve, 100));
        attempts++;
    }

    if (!window.knowledgeApp) {
        console.warn('[Admin] Main app not found, continuing anyway');
    }
}

// =============================================================================
// System Status
// =============================================================================

/**
 * Check system status for all services
 */
async function checkSystemStatus() {
    // Check API
    await checkService('status-api', '/api/app/health');

    // Check MongoDB via health endpoint
    await checkService('status-mongodb', '/api/app/health');

    // Neo4j and Qdrant status - placeholder for future implementation
    setStatusIndicator('status-neo4j', 'unknown');
    setStatusIndicator('status-qdrant', 'unknown');
}

/**
 * Check a service health endpoint
 * @param {string} elementId - Status indicator element ID
 * @param {string} endpoint - Health endpoint to check
 */
async function checkService(elementId, endpoint) {
    setStatusIndicator(elementId, 'loading');

    try {
        const healthy = await apiService.healthCheck();
        setStatusIndicator(elementId, healthy ? 'ok' : 'error');
    } catch (error) {
        setStatusIndicator(elementId, 'error');
    }
}

/**
 * Set status indicator state
 * @param {string} elementId - Element ID
 * @param {string} status - Status: 'ok', 'error', 'loading', 'unknown'
 */
function setStatusIndicator(elementId, status) {
    const el = document.getElementById(elementId);
    if (!el) return;

    el.className = `status-indicator status-${status}`;
}

// =============================================================================
// User Info
// =============================================================================

/**
 * Load current user info from state
 */
async function loadUserInfo() {
    const user = stateManager.get(StateKeys.CURRENT_USER);

    if (!user) {
        setElementText('user-username', 'Not authenticated');
        setElementText('user-email', '-');
        setElementText('user-roles', '-');
        return;
    }

    setElementText('user-username', user.preferred_username || user.name || '-');
    setElementText('user-email', user.email || '-');
    setElementText('user-roles', (user.roles || []).join(', ') || 'No roles');
}

// =============================================================================
// Config Info
// =============================================================================

/**
 * Load configuration info
 */
async function loadConfigInfo() {
    try {
        const info = await apiService.getAppInfo();
        setElementText('config-version', info.version || info.app_version || '-');
        setElementText('config-environment', info.environment || 'development');
        setElementText('config-debug', info.debug ? 'enabled' : 'disabled');
    } catch (error) {
        console.error('[Admin] Failed to load config info:', error);
        setElementText('config-version', 'Error');
        setElementText('config-environment', '-');
        setElementText('config-debug', '-');
    }
}

// =============================================================================
// Utilities
// =============================================================================

/**
 * Set text content of an element by ID
 * @param {string} elementId - Element ID
 * @param {string} text - Text to set
 */
function setElementText(elementId, text) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = text;
    }
}

// =============================================================================
// Initialize
// =============================================================================

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAdmin);
} else {
    initAdmin();
}
