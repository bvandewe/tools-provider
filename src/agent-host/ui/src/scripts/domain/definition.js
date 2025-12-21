/**
 * Definition Domain - Agent definition business logic
 *
 * Pure business logic for agent definitions.
 * No DOM dependencies - UI updates happen via event bus.
 *
 * @module domain/definition
 */

import { definitionsApi } from '../services/definitions-api.js';
import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';
import { saveSelectedDefinitionId, getSelectedDefinitionId as getStoredDefinitionId } from '../utils/storage.js';

// =============================================================================
// Constants
// =============================================================================

/** Default definition ID (fallback) */
const DEFAULT_DEFINITION_ID = 'chat';

/** Default icons for definitions without custom icons */
export const DEFAULT_ICONS = {
    chat: 'bi-chat-dots',
    tutor: 'bi-mortarboard',
    coach: 'bi-person-check',
    evaluator: 'bi-clipboard-check',
};

// =============================================================================
// Types
// =============================================================================

/**
 * @typedef {Object} AgentDefinition
 * @property {string} id - Definition ID
 * @property {string} name - Display name
 * @property {string} [description] - Description
 * @property {string} [icon] - Bootstrap icon class
 * @property {string} [model] - Override model ID
 * @property {boolean} [is_proactive] - Agent starts first
 * @property {boolean} [has_template] - Uses template flow
 * @property {string} [template_id] - Associated template ID
 */

// =============================================================================
// State
// =============================================================================

/** @type {Map<string, AgentDefinition>} */
const definitionsById = new Map();

// =============================================================================
// Definition Loading
// =============================================================================

/**
 * Load all available definitions from API
 * @returns {Promise<AgentDefinition[]>} List of definitions
 */
export async function loadDefinitions() {
    try {
        const definitions = await definitionsApi.getDefinitions();

        // Cache definitions
        definitionsById.clear();
        definitions.forEach(def => {
            definitionsById.set(def.id, def);
        });

        // Update state
        stateManager.set(StateKeys.DEFINITIONS, definitions);

        // Validate stored selection
        const storedId = getStoredDefinitionId();
        if (storedId && !definitionsById.has(storedId)) {
            // Stored definition no longer exists
            stateManager.set(StateKeys.SELECTED_DEFINITION_ID, null);
        }

        // Auto-select first or default if none selected
        const currentId = stateManager.get(StateKeys.SELECTED_DEFINITION_ID);
        if (!currentId && definitions.length > 0) {
            const defaultDef = definitions.find(d => d.id === DEFAULT_DEFINITION_ID) || definitions[0];
            selectDefinition(defaultDef.id, true); // silent select
        }

        console.log(`[Definition] Loaded ${definitions.length} definitions`);

        // Emit event for UI to render
        eventBus.emit(Events.DEFINITION_LIST_LOADED, definitions);

        return definitions;
    } catch (error) {
        console.error('[Definition] Failed to load definitions:', error);
        eventBus.emit(Events.UI_TOAST, {
            message: 'Failed to load agent definitions',
            type: 'error',
        });
        return [];
    }
}

// =============================================================================
// Definition Access
// =============================================================================

/**
 * Get a definition by ID
 * @param {string} definitionId - Definition ID
 * @returns {AgentDefinition|null} Definition or null
 */
export function getDefinition(definitionId) {
    return definitionsById.get(definitionId) || null;
}

/**
 * Get all loaded definitions
 * @returns {AgentDefinition[]} List of definitions
 */
export function getDefinitions() {
    return stateManager.get(StateKeys.DEFINITIONS, []);
}

/**
 * Get currently selected definition
 * @returns {AgentDefinition|null} Selected definition or null
 */
export function getSelectedDefinition() {
    const id = stateManager.get(StateKeys.SELECTED_DEFINITION_ID);
    return id ? definitionsById.get(id) || null : null;
}

/**
 * Get selected definition ID
 * @returns {string|null} Selected definition ID
 */
export function getSelectedDefinitionId() {
    return stateManager.get(StateKeys.SELECTED_DEFINITION_ID, null);
}

// =============================================================================
// Definition Selection
// =============================================================================

/**
 * Select a definition
 * @param {string} definitionId - Definition ID to select
 * @param {boolean} [silent=false] - If true, don't emit events
 * @returns {boolean} True if selection successful
 */
export function selectDefinition(definitionId, silent = false) {
    const definition = definitionsById.get(definitionId);
    if (!definition) {
        console.warn('[Definition] Definition not found:', definitionId);
        return false;
    }

    const previousId = stateManager.get(StateKeys.SELECTED_DEFINITION_ID);
    stateManager.set(StateKeys.SELECTED_DEFINITION_ID, definitionId);
    stateManager.set(StateKeys.SELECTED_DEFINITION, definition);
    saveSelectedDefinitionId(definitionId);

    console.log(`[Definition] Selected: ${definitionId}`);

    if (!silent && previousId !== definitionId) {
        eventBus.emit(Events.DEFINITION_SELECTED, {
            definition,
            previousId,
        });
    }

    return true;
}

// =============================================================================
// Definition Utilities
// =============================================================================

/**
 * Check if definition is proactive (agent starts first)
 * @param {string} definitionId - Definition ID
 * @returns {boolean} True if proactive
 */
export function isProactiveDefinition(definitionId) {
    const def = definitionsById.get(definitionId);
    return def?.is_proactive === true;
}

/**
 * Check if definition uses templates
 * @param {string} definitionId - Definition ID
 * @returns {boolean} True if uses templates
 */
export function hasTemplate(definitionId) {
    const def = definitionsById.get(definitionId);
    return def?.has_template === true || !!def?.template_id;
}

/**
 * Check if definition should use WebSocket
 * (proactive or template-based definitions use WebSocket)
 * @param {string} definitionId - Definition ID
 * @returns {boolean} True if should use WebSocket
 */
export function shouldUseWebSocket(definitionId) {
    const def = definitionsById.get(definitionId);
    if (!def) return false;
    return def.is_proactive === true || def.has_template === true || !!def.template_id;
}

/**
 * Get icon for definition
 * @param {AgentDefinition} definition - Definition
 * @returns {string} Bootstrap icon class
 */
export function getDefinitionIcon(definition) {
    if (definition.icon) return definition.icon;
    return DEFAULT_ICONS[definition.id] || 'bi-robot';
}

export default {
    loadDefinitions,
    getDefinition,
    getDefinitions,
    getSelectedDefinition,
    getSelectedDefinitionId,
    selectDefinition,
    isProactiveDefinition,
    hasTemplate,
    shouldUseWebSocket,
    getDefinitionIcon,
    DEFAULT_ICONS,
};
