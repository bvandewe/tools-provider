/**
 * KnowledgeApp - Modular Application Orchestrator
 *
 * Thin orchestrator that coordinates modules via event bus.
 * All business logic lives in services/, managers/, and handlers/ layers.
 *
 * Architecture:
 * - Event-driven module coordination
 * - Clean separation of concerns
 * - Class-based singletons for services, managers, handlers
 *
 * Responsibilities:
 * - Initialize all modules on startup
 * - Bind top-level DOM events
 * - Coordinate cross-module workflows
 *
 * @module App
 */

import * as bootstrap from 'bootstrap';
import { eventBus, Events } from './core/event-bus.js';
import { stateManager, StateKeys } from './core/state-manager.js';

// =============================================================================
// Class-Based Services
// =============================================================================
import { apiService } from './services/ApiService.js';
import { authService } from './services/AuthService.js';
import { themeService } from './services/ThemeService.js';
import { modalService } from './services/ModalService.js';

// =============================================================================
// Class-Based Managers
// =============================================================================
import { uiManager, namespaceManager, statsManager, navigationManager, dashboardPageManager, namespacesPageManager, termsPageManager, adminPageManager } from './managers/index.js';

// =============================================================================
// Class-Based Handlers Registry
// =============================================================================
import { initAllHandlers, destroyAllHandlers } from './handlers/HandlersRegistry.js';

// =============================================================================
// KnowledgeApp Class
// =============================================================================

export class KnowledgeApp {
    constructor() {
        /** @type {boolean} */
        this._initialized = false;
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize the application
     */
    async init() {
        if (this._initialized) {
            console.warn('[KnowledgeApp] Already initialized');
            return;
        }

        try {
            console.log('[KnowledgeApp] Initializing...');

            // Set up global error handler
            this._setupErrorHandler();

            // Initialize services
            this._initServices();

            // Initialize managers
            this._initManagers();

            // Initialize handlers (event subscriptions)
            this._initHandlers();

            // Initialize Bootstrap tooltips
            this._initTooltips();

            // Check authentication and load data
            await this._checkAuthAndLoad();

            this._initialized = true;
            console.log('[KnowledgeApp] Initialized successfully');
        } catch (error) {
            console.error('[KnowledgeApp] Initialization failed:', error);
            modalService.error('Application failed to initialize. Please refresh the page.');
        }
    }

    /**
     * Destroy the application
     */
    destroy() {
        destroyAllHandlers();
        this._initialized = false;
        console.log('[KnowledgeApp] Destroyed');
    }

    // =========================================================================
    // Private Initialization Methods
    // =========================================================================

    /**
     * Set up global error handler
     * @private
     */
    _setupErrorHandler() {
        window.addEventListener('unhandledrejection', event => {
            console.error('Unhandled promise rejection:', event.reason);
            modalService.error('An unexpected error occurred');
        });
    }

    /**
     * Initialize all services
     * @private
     */
    _initServices() {
        apiService.init();
        authService.init();
        themeService.init();
        modalService.init();

        console.log('[KnowledgeApp] Services initialized');
    }

    /**
     * Initialize all managers
     * @private
     */
    _initManagers() {
        uiManager.init();
        namespaceManager.init();
        statsManager.init();

        // Initialize page managers BEFORE navigation manager
        // so they can subscribe to UI_PAGE_CHANGED before initial route handling
        dashboardPageManager.init();
        namespacesPageManager.init();
        termsPageManager.init();
        adminPageManager.init();

        // Navigation manager must be initialized LAST
        // so it can emit UI_PAGE_CHANGED after page managers are ready
        navigationManager.init();

        console.log('[KnowledgeApp] Managers initialized');
    }

    /**
     * Initialize all handlers
     * @private
     */
    _initHandlers() {
        initAllHandlers();
        console.log('[KnowledgeApp] Handlers initialized');
    }

    /**
     * Initialize Bootstrap tooltips
     * @private
     */
    _initTooltips() {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));
    }

    // =========================================================================
    // Authentication and Data Loading
    // =========================================================================

    /**
     * Check authentication and load initial data
     * @private
     */
    async _checkAuthAndLoad() {
        // Check authentication
        await authService.checkAuth();

        // Fetch app info (version)
        await this._fetchAppInfo();

        // Check API connection
        await this._checkConnection();
    }

    /**
     * Fetch and display app version
     * @private
     */
    async _fetchAppInfo() {
        try {
            const info = await apiService.getAppInfo();
            uiManager.updateAppVersion(info.version || info.app_version || '-');
        } catch (error) {
            console.debug('[KnowledgeApp] Could not fetch app info:', error);
        }
    }

    /**
     * Check API connection status
     * @private
     */
    async _checkConnection() {
        const connected = await apiService.healthCheck();
        uiManager.updateConnectionStatus(connected);
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const knowledgeApp = new KnowledgeApp();
