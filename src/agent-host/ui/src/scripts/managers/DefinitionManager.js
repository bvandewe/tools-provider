/**
 * DefinitionManager - Class-based agent definition manager
 *
 * Manages AgentDefinition selection and display.
 *
 * Key responsibilities:
 * - Load and cache available definitions
 * - Render definition tiles for user selection
 * - Track selected definition for new conversations
 * - Provide definition info for conversation context
 *
 * @module managers/DefinitionManager
 */

import { definitionsApi } from '../services/definitions-api.js';
import { showToast } from '../services/modals.js';
import { eventBus, Events } from '../core/event-bus.js';

const DEFAULT_DEFINITION_ID = 'chat';

const DEFAULT_ICONS = {
    chat: 'bi-chat-dots',
    tutor: 'bi-mortarboard',
    coach: 'bi-person-check',
    evaluator: 'bi-clipboard-check',
};

/**
 * @class DefinitionManager
 * @description Manages agent definitions and selection
 */
export class DefinitionManager {
    /**
     * Create DefinitionManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Array} All available definitions */
        this._definitions = [];

        /** @type {string|null} Currently selected definition ID */
        this._selectedDefinitionId = null;

        /** @type {Map<string, Object>} Cached definitions by ID */
        this._definitionsById = new Map();

        /** @type {boolean} Whether definitions have been loaded */
        this._isLoaded = false;

        /** @type {Object} DOM elements */
        this._elements = {
            definitionTiles: null,
            selectedDefinitionLabel: null,
            selectedDefinitionIcon: null,
        };

        /** @type {Object} Callbacks */
        this._callbacks = {
            onDefinitionSelect: null,
            onDefinitionsLoaded: null,
        };
    }

    /**
     * Initialize the definition manager
     * @param {Object} domElements - DOM element references
     * @param {Object} callbacks - Callback functions
     */
    init(domElements = {}, callbacks = {}) {
        if (this._initialized) {
            console.warn('[DefinitionManager] Already initialized');
            return;
        }

        this._elements = { ...this._elements, ...domElements };
        this._callbacks = { ...this._callbacks, ...callbacks };

        // Load stored selection
        const storedId = localStorage.getItem('selectedDefinitionId');
        if (storedId) {
            this._selectedDefinitionId = storedId;
        }

        this._initialized = true;
        console.log('[DefinitionManager] Initialized');
    }

    /**
     * Reset the definition manager state
     */
    reset() {
        this._definitions = [];
        this._selectedDefinitionId = null;
        this._definitionsById.clear();
        this._isLoaded = false;
        localStorage.removeItem('selectedDefinitionId');
        console.log('[DefinitionManager] State reset');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._definitions = [];
        this._selectedDefinitionId = null;
        this._definitionsById.clear();
        this._isLoaded = false;
        this._initialized = false;
        console.log('[DefinitionManager] Destroyed');
    }

    // =========================================================================
    // Definition Loading
    // =========================================================================

    /**
     * Load all available definitions from the API
     * @returns {Promise<Array>} List of definitions
     */
    async loadDefinitions() {
        try {
            const definitions = await definitionsApi.getDefinitions();

            this._definitions = definitions;
            this._definitionsById.clear();

            definitions.forEach(def => {
                this._definitionsById.set(def.id, def);
            });

            this._isLoaded = true;

            // Validate selected definition still exists
            if (this._selectedDefinitionId && !this._definitionsById.has(this._selectedDefinitionId)) {
                this._selectedDefinitionId = null;
            }

            // Default to first definition or 'chat' if available
            if (!this._selectedDefinitionId && definitions.length > 0) {
                const defaultDef = definitions.find(d => d.id === DEFAULT_DEFINITION_ID) || definitions[0];
                this._selectedDefinitionId = defaultDef.id;
            }

            console.log(`[DefinitionManager] Loaded ${definitions.length} definitions`);

            // Emit event for handlers
            eventBus.emit(Events.DEFINITION_LIST_LOADED, { definitions });

            if (this._callbacks.onDefinitionsLoaded) {
                this._callbacks.onDefinitionsLoaded(definitions);
            }

            return definitions;
        } catch (error) {
            console.error('[DefinitionManager] Failed to load definitions:', error);
            showToast('Failed to load agent definitions', 'error');
            return [];
        }
    }

    /**
     * Get a definition by ID
     * @param {string} definitionId - Definition ID
     * @returns {Object|null}
     */
    getDefinition(definitionId) {
        return this._definitionsById.get(definitionId) || null;
    }

    /**
     * Get all loaded definitions
     * @returns {Array}
     */
    getDefinitions() {
        return this._definitions;
    }

    // =========================================================================
    // Definition Selection
    // =========================================================================

    /**
     * Select a definition for new conversations
     * @param {string} definitionId - Definition ID to select
     * @param {boolean} skipCallback - If true, skip the callback
     */
    selectDefinition(definitionId, skipCallback = false) {
        const definition = this._definitionsById.get(definitionId);
        if (!definition) {
            console.warn(`[DefinitionManager] Definition not found: ${definitionId}`);
            return;
        }

        const previousId = this._selectedDefinitionId;
        this._selectedDefinitionId = definitionId;
        localStorage.setItem('selectedDefinitionId', definitionId);

        console.log(`[DefinitionManager] Selected definition: ${definitionId}`);

        this._updateSelectionUI();

        if (skipCallback) {
            return;
        }

        const isProactive = definition.is_proactive === true;
        if (this._callbacks.onDefinitionSelect && (isProactive || previousId !== definitionId)) {
            this._callbacks.onDefinitionSelect(definition, previousId);
        }

        // Emit event for handlers
        eventBus.emit(Events.DEFINITION_SELECTED, { definition, previousId });
    }

    /**
     * Get the currently selected definition
     * @returns {Object|null}
     */
    getSelectedDefinition() {
        if (!this._selectedDefinitionId) return null;
        return this._definitionsById.get(this._selectedDefinitionId) || null;
    }

    /**
     * Get the selected definition ID
     * @returns {string|null}
     */
    getSelectedDefinitionId() {
        return this._selectedDefinitionId;
    }

    // =========================================================================
    // UI Rendering
    // =========================================================================

    /**
     * Render definition tiles in the welcome screen
     * @param {HTMLElement} container - Container element for tiles
     */
    renderDefinitionTiles(container) {
        if (!container) return;

        container.innerHTML = '';

        this._definitions.forEach(def => {
            const tile = this._createDefinitionTile(def);
            container.appendChild(tile);
        });

        this._updateSelectionUI();
    }

    /**
     * Create a definition tile element
     * @private
     */
    _createDefinitionTile(definition) {
        const tile = document.createElement('button');
        tile.className = 'definition-tile';
        tile.dataset.definitionId = definition.id;

        const icon = definition.icon || DEFAULT_ICONS[definition.id] || 'bi-robot';
        const hasTemplate = definition.has_template;

        tile.innerHTML = `
            <div class="definition-tile-icon">
                <i class="bi ${icon}"></i>
                ${hasTemplate ? '<span class="proactive-badge" title="Has conversation template"><i class="bi bi-lightning-charge-fill"></i></span>' : ''}
            </div>
            <div class="definition-tile-content">
                <h4 class="definition-tile-name">${this._escapeHtml(definition.name)}</h4>
                ${definition.description ? `<p class="definition-tile-description">${this._escapeHtml(definition.description)}</p>` : ''}
            </div>
        `;

        tile.addEventListener('click', () => {
            this.selectDefinition(definition.id);
        });

        return tile;
    }

    /**
     * Update the selection UI
     * @private
     */
    _updateSelectionUI() {
        if (this._elements.definitionTiles) {
            const tiles = this._elements.definitionTiles.querySelectorAll('.definition-tile');
            tiles.forEach(tile => {
                const isSelected = tile.dataset.definitionId === this._selectedDefinitionId;
                tile.classList.toggle('selected', isSelected);
            });
        }

        if (this._elements.selectedDefinitionLabel) {
            const def = this.getSelectedDefinition();
            this._elements.selectedDefinitionLabel.textContent = def ? def.name : 'Select Agent';
        }

        if (this._elements.selectedDefinitionIcon) {
            const def = this.getSelectedDefinition();
            const icon = def?.icon || DEFAULT_ICONS[def?.id] || 'bi-robot';
            this._elements.selectedDefinitionIcon.className = `bi ${icon}`;
        }
    }

    // =========================================================================
    // Helper Methods
    // =========================================================================

    /**
     * Escape HTML
     * @private
     */
    _escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Check if a definition is proactive
     * @param {string} definitionId
     * @returns {boolean}
     */
    isProactiveDefinition(definitionId) {
        const def = this._definitionsById.get(definitionId);
        return def?.is_proactive || false;
    }

    /**
     * Check if should use WebSocket (always true)
     * @returns {boolean}
     */
    shouldUseWebSocket() {
        return true;
    }

    /**
     * Check if definitions have been loaded
     * @returns {boolean}
     */
    get isLoaded() {
        return this._isLoaded;
    }

    /**
     * Check if manager is initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }
}

// Export singleton instance
export const definitionManager = new DefinitionManager();
export default definitionManager;
