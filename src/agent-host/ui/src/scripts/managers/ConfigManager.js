/**
 * ConfigManager - Class-based application configuration manager
 *
 * Manages app config loading and model selection.
 *
 * Key responsibilities:
 * - Load application configuration from API
 * - Initialize and manage model selector
 * - Handle model selection updates via WebSocket
 * - Render welcome messages based on definition
 *
 * @module managers/ConfigManager
 */

import { api } from '../services/api.js';
import { showToast } from '../services/modals.js';
import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';

/**
 * @class ConfigManager
 * @description Manages application configuration and model selection
 */
export class ConfigManager {
    /**
     * Create ConfigManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Object|null} Application configuration */
        this._appConfig = null;

        /** @type {string|null} Selected model ID */
        this._selectedModelId = null;

        /** @type {Object} DOM elements */
        this._elements = {
            modelSelector: null,
            welcomeMessage: null,
            welcomeSubtitle: null,
        };

        /** @type {Function|null} WebSocket connection for model updates */
        this._webSocketSendFn = null;
    }

    /**
     * Initialize the config manager
     * @param {Object} domElements - DOM element references
     */
    init(domElements = {}) {
        if (this._initialized) {
            console.warn('[ConfigManager] Already initialized');
            return;
        }

        this._elements = { ...this._elements, ...domElements };
        this._initialized = true;
        console.log('[ConfigManager] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._appConfig = null;
        this._selectedModelId = null;
        this._webSocketSendFn = null;
        this._initialized = false;
        console.log('[ConfigManager] Destroyed');
    }

    // =========================================================================
    // Config Loading
    // =========================================================================

    /**
     * Load application configuration from API
     * @returns {Promise<Object|null>}
     */
    async loadConfig() {
        try {
            const config = await api.getAppConfig();
            this._appConfig = config;

            // Store in state for global access
            stateManager.set(StateKeys.APP_CONFIG, config);

            console.log('[ConfigManager] Config loaded:', config);
            eventBus.emit(Events.CONFIG_LOADED, { config });

            return config;
        } catch (error) {
            console.error('[ConfigManager] Failed to load config:', error);
            showToast('Failed to load application configuration', 'error');
            return null;
        }
    }

    /**
     * Get the loaded app configuration
     * @returns {Object|null}
     */
    getConfig() {
        return this._appConfig;
    }

    /**
     * Get a specific config value
     * @param {string} key - Config key
     * @param {*} defaultValue - Default value if not found
     * @returns {*}
     */
    getValue(key, defaultValue = null) {
        if (!this._appConfig) return defaultValue;
        return this._appConfig[key] ?? defaultValue;
    }

    // =========================================================================
    // Model Selection
    // =========================================================================

    /**
     * Initialize the model selector dropdown
     * @param {HTMLElement} selectorElement - The model selector element
     */
    initModelSelector(selectorElement) {
        if (!selectorElement) {
            console.warn('[ConfigManager] Model selector element not provided');
            return;
        }

        this._elements.modelSelector = selectorElement;

        if (!this._appConfig?.models || this._appConfig.models.length === 0) {
            console.warn('[ConfigManager] No models available in config');
            selectorElement.style.display = 'none';
            return;
        }

        // Clear existing options
        selectorElement.innerHTML = '';

        // Add model options
        this._appConfig.models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = model.display_name || model.id;

            if (model.is_default) {
                option.selected = true;
                this._selectedModelId = model.id;
            }

            selectorElement.appendChild(option);
        });

        // If no default was set, select first model
        if (!this._selectedModelId && this._appConfig.models.length > 0) {
            this._selectedModelId = this._appConfig.models[0].id;
            selectorElement.value = this._selectedModelId;
        }

        // Handle selection change
        selectorElement.addEventListener('change', e => {
            this._handleModelChange(e.target.value);
        });

        console.log(`[ConfigManager] Model selector initialized with ${this._appConfig.models.length} models`);
    }

    /**
     * Handle model selection change
     * @private
     */
    _handleModelChange(modelId) {
        const previousModelId = this._selectedModelId;
        this._selectedModelId = modelId;

        console.log(`[ConfigManager] Model changed: ${previousModelId} -> ${modelId}`);

        // Update state
        stateManager.set(StateKeys.SELECTED_MODEL, modelId);

        // Send model update via WebSocket if connected
        this._sendModelUpdate(modelId);

        // Emit event
        eventBus.emit(Events.MODEL_CHANGED, { modelId, previousModelId });
    }

    /**
     * Send model update via WebSocket
     * @private
     */
    _sendModelUpdate(modelId) {
        if (!this._webSocketSendFn) {
            console.log('[ConfigManager] WebSocket not connected, skipping model update');
            return;
        }

        try {
            this._webSocketSendFn({
                plane: 'control',
                type: 'context-update',
                action: 'replace',
                data: {
                    model_id: modelId,
                },
            });
            console.log(`[ConfigManager] Sent model update via WebSocket: ${modelId}`);
        } catch (error) {
            console.error('[ConfigManager] Failed to send model update:', error);
        }
    }

    /**
     * Set the WebSocket send function for model updates
     * @param {Function} sendFn - Function to send WebSocket messages
     */
    setWebSocketSendFn(sendFn) {
        this._webSocketSendFn = sendFn;
    }

    /**
     * Get the selected model ID
     * @returns {string|null}
     */
    getSelectedModelId() {
        return this._selectedModelId;
    }

    /**
     * Get the selected model object
     * @returns {Object|null}
     */
    getSelectedModel() {
        if (!this._appConfig?.models || !this._selectedModelId) return null;
        return this._appConfig.models.find(m => m.id === this._selectedModelId) || null;
    }

    /**
     * Set the selected model programmatically
     * @param {string} modelId - Model ID to select
     */
    setSelectedModel(modelId) {
        if (this._elements.modelSelector) {
            this._elements.modelSelector.value = modelId;
        }
        this._handleModelChange(modelId);
    }

    // =========================================================================
    // Welcome Message
    // =========================================================================

    /**
     * Update welcome message based on selected definition
     * @param {Object} definition - Selected definition
     */
    updateWelcomeMessage(definition) {
        if (!this._elements.welcomeMessage) return;

        const title = definition?.welcome_title || definition?.name || 'Welcome';
        const subtitle = definition?.welcome_subtitle || definition?.description || 'How can I help you today?';

        this._elements.welcomeMessage.textContent = title;

        if (this._elements.welcomeSubtitle) {
            this._elements.welcomeSubtitle.textContent = subtitle;
        }
    }

    /**
     * Set welcome message elements
     * @param {HTMLElement} titleElement - Title element
     * @param {HTMLElement} subtitleElement - Subtitle element
     */
    setWelcomeElements(titleElement, subtitleElement) {
        this._elements.welcomeMessage = titleElement;
        this._elements.welcomeSubtitle = subtitleElement;
    }

    // =========================================================================
    // Feature Flags
    // =========================================================================

    /**
     * Check if a feature is enabled
     * @param {string} featureName - Feature name
     * @returns {boolean}
     */
    isFeatureEnabled(featureName) {
        if (!this._appConfig?.features) return false;
        return this._appConfig.features[featureName] === true;
    }

    /**
     * Get all available models
     * @returns {Array}
     */
    getModels() {
        return this._appConfig?.models || [];
    }

    /**
     * Check if manager is initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }

    /**
     * Check if config is loaded
     * @returns {boolean}
     */
    get isLoaded() {
        return this._appConfig !== null;
    }
}

// Export singleton instance
export const configManager = new ConfigManager();
export default configManager;
