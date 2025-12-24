/**
 * Knowledge Manager - Dashboard Script
 *
 * Dashboard-specific initialization and event binding.
 * Uses the class-based architecture from main.js.
 *
 * @module dashboard
 */

import * as bootstrap from 'bootstrap';
import { eventBus, Events } from './core/event-bus.js';
import { stateManager, StateKeys } from './core/state-manager.js';
import { modalService } from './services/ModalService.js';
import { namespaceManager, statsManager } from './managers/index.js';
import { authService } from './services/AuthService.js';

// =============================================================================
// Dashboard Initialization
// =============================================================================

/**
 * Initialize dashboard page
 */
async function initDashboard() {
    console.log('[Dashboard] Initializing...');

    // Wait for main app to initialize
    await waitForApp();

    // Bind dashboard-specific event handlers
    bindEventHandlers();

    // Load initial data
    await loadInitialData();

    console.log('[Dashboard] Initialized');
}

/**
 * Wait for the main KnowledgeApp to be initialized
 * @returns {Promise<void>}
 */
async function waitForApp() {
    // Wait for the app to be available on window
    let attempts = 0;
    while (!window.knowledgeApp && attempts < 50) {
        await new Promise(resolve => setTimeout(resolve, 100));
        attempts++;
    }

    if (!window.knowledgeApp) {
        console.warn('[Dashboard] Main app not found, continuing anyway');
    }
}

/**
 * Bind dashboard-specific event handlers
 */
function bindEventHandlers() {
    // Button event handlers
    document.getElementById('btn-new-namespace')?.addEventListener('click', showCreateNamespaceModal);
    document.getElementById('btn-new-term')?.addEventListener('click', showCreateTermModal);
    document.getElementById('btn-browse-namespaces')?.addEventListener('click', () => {
        document.getElementById('namespaces-list')?.scrollIntoView({ behavior: 'smooth' });
    });
    document.getElementById('btn-refresh-namespaces')?.addEventListener('click', refreshNamespaces);
    document.getElementById('btn-submit-namespace')?.addEventListener('click', createNamespace);
    document.getElementById('btn-submit-term')?.addEventListener('click', createTerm);
}

/**
 * Load initial data
 */
async function loadInitialData() {
    // Show loading state in namespaces list
    const listEl = document.getElementById('namespaces-list');
    if (listEl) {
        listEl.innerHTML = `
            <div class="text-center text-muted py-4">
                <span class="loading-spinner me-2"></span>Loading namespaces...
            </div>
        `;
    }

    try {
        await namespaceManager.loadNamespaces();
        statsManager.updateStats();
    } catch (error) {
        console.error('[Dashboard] Failed to load initial data:', error);
    }
}

/**
 * Refresh namespaces list
 */
async function refreshNamespaces() {
    const listEl = document.getElementById('namespaces-list');
    if (listEl) {
        listEl.innerHTML = `
            <div class="text-center text-muted py-4">
                <span class="loading-spinner me-2"></span>Refreshing...
            </div>
        `;
    }

    try {
        await namespaceManager.loadNamespaces();
        statsManager.updateStats();
    } catch (error) {
        console.error('[Dashboard] Failed to refresh namespaces:', error);
    }
}

// =============================================================================
// Modal Handlers
// =============================================================================

/**
 * Show create namespace modal
 */
function showCreateNamespaceModal() {
    modalService.show('createNamespaceModal');
    document.getElementById('create-namespace-form')?.reset();
}

/**
 * Show create term modal
 */
function showCreateTermModal() {
    // Populate namespace dropdown
    const select = document.getElementById('term-namespace');
    const namespaces = stateManager.get(StateKeys.NAMESPACES, []);

    if (select) {
        select.innerHTML = '<option value="">Select a namespace...</option>';
        namespaces.forEach(ns => {
            const option = document.createElement('option');
            option.value = ns.slug;
            option.textContent = `${ns.name} (${ns.slug})`;
            select.appendChild(option);
        });
    }

    modalService.show('createTermModal');
    document.getElementById('create-term-form')?.reset();
}

// =============================================================================
// CRUD Operations
// =============================================================================

/**
 * Create a new namespace
 */
async function createNamespace() {
    const slugEl = document.getElementById('namespace-slug');
    const nameEl = document.getElementById('namespace-name');
    const descEl = document.getElementById('namespace-description');

    const data = {
        slug: slugEl?.value.trim(),
        name: nameEl?.value.trim(),
        description: descEl?.value.trim() || null,
    };

    if (!data.slug || !data.name) {
        modalService.warning('Please fill in required fields');
        return;
    }

    try {
        await namespaceManager.createNamespace(data);
        modalService.hide('createNamespaceModal');
        statsManager.updateStats();
    } catch (error) {
        console.error('[Dashboard] Failed to create namespace:', error);
        modalService.error(error.message || 'Failed to create namespace');
    }
}

/**
 * Create a new term
 */
async function createTerm() {
    const namespaceEl = document.getElementById('term-namespace');
    const slugEl = document.getElementById('term-slug');
    const labelEl = document.getElementById('term-label');
    const definitionEl = document.getElementById('term-definition');

    const namespaceSlug = namespaceEl?.value;
    const data = {
        slug: slugEl?.value.trim(),
        label: labelEl?.value.trim(),
        definition: definitionEl?.value.trim() || null,
    };

    if (!namespaceSlug || !data.slug || !data.label) {
        modalService.warning('Please fill in required fields');
        return;
    }

    try {
        const { apiService } = await import('./services/ApiService.js');
        await apiService.createTerm(namespaceSlug, data);
        modalService.success('Term created successfully!');
        modalService.hide('createTermModal');

        // Refresh namespaces to update term counts
        await namespaceManager.loadNamespaces();
        statsManager.updateStats();
    } catch (error) {
        console.error('[Dashboard] Failed to create term:', error);
        modalService.error(error.message || 'Failed to create term');
    }
}

// =============================================================================
// Initialize
// =============================================================================

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}
