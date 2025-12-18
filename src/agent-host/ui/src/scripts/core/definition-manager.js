/**
 * Definition Manager
 * Manages AgentDefinition selection and display.
 *
 * This module replaces the old session-mode-manager.js.
 * Instead of modes (chat, thought, learning), users select from available
 * AgentDefinitions which appear as tiles on the home screen.
 *
 * Key responsibilities:
 * - Load and cache available definitions
 * - Render definition tiles for user selection
 * - Track selected definition for new conversations
 * - Provide definition info for conversation context
 */

import { definitionsApi } from '../services/definitions-api.js';
import { showToast } from '../services/modals.js';

// =============================================================================
// Constants
// =============================================================================

/**
 * Default definition ID (fallback when none selected)
 */
const DEFAULT_DEFINITION_ID = 'chat';

/**
 * Default icons for definitions without custom icons
 */
const DEFAULT_ICONS = {
    chat: 'bi-chat-dots',
    tutor: 'bi-mortarboard',
    coach: 'bi-person-check',
    evaluator: 'bi-clipboard-check',
};

// =============================================================================
// State
// =============================================================================

let state = {
    /** All available definitions */
    definitions: [],

    /** Currently selected definition ID */
    selectedDefinitionId: null,

    /** Cached definition objects by ID */
    definitionsById: new Map(),

    /** Whether definitions have been loaded */
    isLoaded: false,

    /** Whether manager is initialized */
    isInitialized: false,
};

// DOM Elements
let elements = {
    definitionTiles: null,
    selectedDefinitionLabel: null,
    selectedDefinitionIcon: null,
};

// Callbacks
let callbacks = {
    onDefinitionSelect: null,
    onDefinitionsLoaded: null,
};

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize the definition manager
 * @param {Object} domElements - DOM element references
 * @param {Object} callbackFunctions - Callback functions
 */
export function initDefinitionManager(domElements = {}, callbackFunctions = {}) {
    elements = { ...elements, ...domElements };
    callbacks = { ...callbacks, ...callbackFunctions };
    state.isInitialized = true;

    // Load stored selection
    const storedId = localStorage.getItem('selectedDefinitionId');
    if (storedId) {
        state.selectedDefinitionId = storedId;
    }

    console.log('[DefinitionManager] Initialized');
}

/**
 * Reset the definition manager state
 */
export function resetDefinitionManager() {
    state = {
        definitions: [],
        selectedDefinitionId: null,
        definitionsById: new Map(),
        isLoaded: false,
        isInitialized: true,
    };
    localStorage.removeItem('selectedDefinitionId');
    console.log('[DefinitionManager] State reset');
}

// =============================================================================
// Definition Loading
// =============================================================================

/**
 * Load all available definitions from the API
 * @returns {Promise<Array>} List of definitions
 */
export async function loadDefinitions() {
    try {
        const definitions = await definitionsApi.getDefinitions();

        state.definitions = definitions;
        state.definitionsById.clear();

        definitions.forEach(def => {
            state.definitionsById.set(def.id, def);
        });

        state.isLoaded = true;

        // Validate selected definition still exists
        if (state.selectedDefinitionId && !state.definitionsById.has(state.selectedDefinitionId)) {
            state.selectedDefinitionId = null;
        }

        // Default to first definition or 'chat' if available
        if (!state.selectedDefinitionId && definitions.length > 0) {
            const defaultDef = definitions.find(d => d.id === DEFAULT_DEFINITION_ID) || definitions[0];
            state.selectedDefinitionId = defaultDef.id;
        }

        console.log(`[DefinitionManager] Loaded ${definitions.length} definitions`);

        if (callbacks.onDefinitionsLoaded) {
            callbacks.onDefinitionsLoaded(definitions);
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
 * @returns {Object|null} Definition or null
 */
export function getDefinition(definitionId) {
    return state.definitionsById.get(definitionId) || null;
}

/**
 * Get all loaded definitions
 * @returns {Array} List of definitions
 */
export function getDefinitions() {
    return state.definitions;
}

// =============================================================================
// Definition Selection
// =============================================================================

/**
 * Select a definition for new conversations
 * @param {string} definitionId - Definition ID to select
 * @param {boolean} skipCallback - If true, skip the onDefinitionSelect callback (used when loading existing conversations)
 */
export function selectDefinition(definitionId, skipCallback = false) {
    const definition = state.definitionsById.get(definitionId);
    if (!definition) {
        console.warn(`[DefinitionManager] Definition not found: ${definitionId}`);
        return;
    }

    const previousId = state.selectedDefinitionId;
    state.selectedDefinitionId = definitionId;
    localStorage.setItem('selectedDefinitionId', definitionId);

    console.log(`[DefinitionManager] Selected definition: ${definitionId}`);

    // Update UI
    updateSelectionUI();

    // Skip callback when loading existing conversations to avoid triggering proactive flow
    if (skipCallback) {
        return;
    }

    // Always call callback for proactive definitions (they should start fresh conversations)
    // For non-proactive, only call if it's a different definition
    const isProactive = definition.is_proactive === true;
    if (callbacks.onDefinitionSelect && (isProactive || previousId !== definitionId)) {
        callbacks.onDefinitionSelect(definition, previousId);
    }
}

/**
 * Get the currently selected definition
 * @returns {Object|null} Selected definition or null
 */
export function getSelectedDefinition() {
    if (!state.selectedDefinitionId) return null;
    return state.definitionsById.get(state.selectedDefinitionId) || null;
}

/**
 * Get the selected definition ID
 * @returns {string|null} Definition ID or null
 */
export function getSelectedDefinitionId() {
    return state.selectedDefinitionId;
}

// =============================================================================
// UI Rendering
// =============================================================================

/**
 * Render definition tiles in the welcome screen
 * @param {HTMLElement} container - Container element for tiles
 */
export function renderDefinitionTiles(container) {
    if (!container) return;

    container.innerHTML = '';

    state.definitions.forEach(def => {
        const tile = createDefinitionTile(def);
        container.appendChild(tile);
    });

    updateSelectionUI();
}

/**
 * Create a definition tile element
 * @param {Object} definition - Definition data
 * @returns {HTMLElement} Tile element
 */
function createDefinitionTile(definition) {
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
            <h4 class="definition-tile-name">${escapeHtml(definition.name)}</h4>
            ${definition.description ? `<p class="definition-tile-description">${escapeHtml(definition.description)}</p>` : ''}
        </div>
    `;

    tile.addEventListener('click', () => {
        selectDefinition(definition.id);
    });

    return tile;
}

/**
 * Update the selection UI to reflect current selection
 */
function updateSelectionUI() {
    // Update tile selection state
    if (elements.definitionTiles) {
        const tiles = elements.definitionTiles.querySelectorAll('.definition-tile');
        tiles.forEach(tile => {
            const isSelected = tile.dataset.definitionId === state.selectedDefinitionId;
            tile.classList.toggle('selected', isSelected);
        });
    }

    // Update label if present
    if (elements.selectedDefinitionLabel) {
        const def = getSelectedDefinition();
        elements.selectedDefinitionLabel.textContent = def ? def.name : 'Select Agent';
    }

    // Update icon if present
    if (elements.selectedDefinitionIcon) {
        const def = getSelectedDefinition();
        const icon = def?.icon || DEFAULT_ICONS[def?.id] || 'bi-robot';
        elements.selectedDefinitionIcon.className = `bi ${icon}`;
    }
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Check if a definition is proactive (agent-starts-first)
 * @param {string} definitionId - Definition ID
 * @returns {boolean} True if proactive
 */
export function isProactiveDefinition(definitionId) {
    const def = state.definitionsById.get(definitionId);
    return def?.is_proactive || false;
}

/**
 * Check if definitions have been loaded
 * @returns {boolean} True if loaded
 */
export function isDefinitionsLoaded() {
    return state.isLoaded;
}
