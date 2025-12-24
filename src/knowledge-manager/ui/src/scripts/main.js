/**
 * Knowledge Manager - Main Application Script
 *
 * Entry point - imports and initializes all modules
 *
 * Module Structure:
 * - core/       - Event bus, state manager
 * - services/   - Class-based services (ApiService, AuthService, ThemeService, ModalService)
 * - managers/   - Class-based UI managers
 * - handlers/   - Class-based event handlers via HandlersRegistry
 *
 * Architecture:
 * - All modules use class-based singleton pattern
 * - Communication via EventBus (pub/sub)
 * - State managed by StateManager
 * - DI through module imports (no context passing)
 *
 * @module main
 */

import * as bootstrap from 'bootstrap';

// Make bootstrap available globally for modals
window.bootstrap = bootstrap;

// Import class-based theme service (initialized early for FOUC prevention)
import { themeService } from './services/ThemeService.js';

// Import class-based main application orchestrator
import { KnowledgeApp } from './App.js';

// Import authService for the legacy functions
import { authService } from './services/AuthService.js';

// =============================================================================
// Application Initialization
// =============================================================================

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme service first (handles button binding internally)
    themeService.init();

    // Create and initialize the main application
    window.knowledgeApp = new KnowledgeApp();
    window.knowledgeApp.init();
});

// =============================================================================
// Legacy Exports for Backward Compatibility
// =============================================================================

// Re-export commonly used functions for modules that haven't been migrated
export { showToast } from './services/ModalService.js';
export { authService } from './services/AuthService.js';

/**
 * Make an authenticated API request (legacy wrapper)
 * @param {string} url - The API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise<Response>}
 */
export async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
    };

    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers,
        },
    };

    return fetch(url, mergedOptions);
}

/**
 * Format a date for display
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date
 */
export function formatDate(dateString) {
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
 * Check if user is authenticated (legacy wrapper)
 * @returns {boolean}
 */
export function isAuthenticated() {
    return authService.isAuthenticated();
}

/**
 * Check if user is admin (legacy wrapper)
 * @returns {boolean}
 */
export function isAdmin() {
    return authService.isAdmin();
}
