/**
 * Config Domain - Application configuration business logic
 *
 * Pure business logic for application configuration.
 * No DOM dependencies - UI updates happen via event bus.
 *
 * @module domain/config
 */

import { api } from '../services/api.js';
import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';
import { getSelectedModel, saveSelectedModel } from '../utils/storage.js';

// =============================================================================
// Default Configuration
// =============================================================================

/** @type {AppConfig} */
const DEFAULT_CONFIG = {
    app_name: 'Agent Host',
    welcome_message: 'Your AI assistant with access to powerful tools.',
    rate_limit_requests_per_minute: 20,
    rate_limit_concurrent_requests: 1,
    app_tag: '',
    app_repo_url: '',
    available_models: [],
    tools_provider_url: '',
    allow_model_selection: false,
};

/**
 * @typedef {Object} ModelConfig
 * @property {string} id - Model identifier
 * @property {string} name - Display name
 * @property {string} [description] - Model description
 */

/**
 * @typedef {Object} AppConfig
 * @property {string} app_name - Application name
 * @property {string} welcome_message - Welcome message
 * @property {number} rate_limit_requests_per_minute - Rate limit
 * @property {number} rate_limit_concurrent_requests - Concurrent limit
 * @property {string} app_tag - Application tag/version
 * @property {string} app_repo_url - Repository URL
 * @property {ModelConfig[]} available_models - Available models
 * @property {string} tools_provider_url - Tools provider URL
 * @property {boolean} allow_model_selection - Whether to show model selector
 */

// =============================================================================
// Configuration Loading
// =============================================================================

/**
 * Load application configuration from backend
 * @returns {Promise<AppConfig>} Application configuration
 */
export async function loadAppConfig() {
    try {
        const config = await api.getConfig();

        stateManager.set(StateKeys.APP_CONFIG, config);
        stateManager.set(StateKeys.AVAILABLE_MODELS, config.available_models || []);

        // Initialize model selection if allowed
        if (config.allow_model_selection && config.available_models?.length > 0) {
            initializeModelSelection(config.available_models);
        }

        console.log('[Config] Loaded app config');
        return config;
    } catch (error) {
        console.error('[Config] Failed to load app config:', error);
        stateManager.set(StateKeys.APP_CONFIG, DEFAULT_CONFIG);
        return DEFAULT_CONFIG;
    }
}

/**
 * Initialize model selection from available models
 * @param {ModelConfig[]} models - Available models
 */
function initializeModelSelection(models) {
    const savedModelId = getSelectedModel();

    // Use saved model if valid, otherwise use first model
    if (savedModelId && models.some(m => m.id === savedModelId)) {
        stateManager.set(StateKeys.SELECTED_MODEL_ID, savedModelId);
    } else if (models.length > 0) {
        stateManager.set(StateKeys.SELECTED_MODEL_ID, models[0].id);
    }
}

// =============================================================================
// Getters
// =============================================================================

/**
 * Get application configuration
 * @returns {AppConfig} App config
 */
export function getAppConfig() {
    return stateManager.get(StateKeys.APP_CONFIG, DEFAULT_CONFIG);
}

/**
 * Get app name
 * @returns {string} Application name
 */
export function getAppName() {
    const config = getAppConfig();
    return config.app_name || DEFAULT_CONFIG.app_name;
}

/**
 * Get welcome message
 * @returns {string} Welcome message
 */
export function getWelcomeMessage() {
    const config = getAppConfig();
    return config.welcome_message || DEFAULT_CONFIG.welcome_message;
}

/**
 * Get tools provider URL
 * @returns {string} Tools provider URL
 */
export function getToolsProviderUrl() {
    const config = getAppConfig();
    return config.tools_provider_url || '';
}

/**
 * Check if model selection is allowed
 * @returns {boolean} True if model selection allowed
 */
export function isModelSelectionAllowed() {
    const config = getAppConfig();
    return config.allow_model_selection && (config.available_models?.length || 0) > 0;
}

// =============================================================================
// Model Selection
// =============================================================================

/**
 * Get available models
 * @returns {ModelConfig[]} Available models
 */
export function getAvailableModels() {
    return stateManager.get(StateKeys.AVAILABLE_MODELS, []);
}

/**
 * Get currently selected model ID
 * @returns {string|null} Selected model ID
 */
export function getSelectedModelId() {
    return stateManager.get(StateKeys.SELECTED_MODEL_ID, null);
}

/**
 * Get currently selected model
 * @returns {ModelConfig|null} Selected model
 */
export function getSelectedModel() {
    const modelId = getSelectedModelId();
    const models = getAvailableModels();
    return models.find(m => m.id === modelId) || null;
}

/**
 * Set selected model ID
 * @param {string} modelId - Model ID to select
 * @param {boolean} [skipSave=false] - Skip saving to localStorage
 * @returns {boolean} True if model was set successfully
 */
export function setSelectedModelId(modelId, skipSave = false) {
    const models = getAvailableModels();
    const model = models.find(m => m.id === modelId);

    if (!model) {
        console.warn('[Config] Model not found:', modelId);
        return false;
    }

    stateManager.set(StateKeys.SELECTED_MODEL_ID, modelId);

    if (!skipSave) {
        saveSelectedModel(modelId);
    }

    return true;
}

/**
 * Handle model change from UI
 * @param {string} modelId - New model ID
 */
export function handleModelChange(modelId) {
    if (setSelectedModelId(modelId)) {
        const model = getSelectedModel();
        eventBus.emit(Events.UI_TOAST, {
            message: `Switched to ${model?.name || modelId}`,
            type: 'info',
        });
    }
}

export default {
    loadAppConfig,
    getAppConfig,
    getAppName,
    getWelcomeMessage,
    getToolsProviderUrl,
    isModelSelectionAllowed,
    getAvailableModels,
    getSelectedModelId,
    getSelectedModel,
    setSelectedModelId,
    handleModelChange,
};
