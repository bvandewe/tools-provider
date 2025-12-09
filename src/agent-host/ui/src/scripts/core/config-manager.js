/**
 * Config Manager
 * Handles application configuration loading and model selector initialization
 */

import { api } from '../services/api.js';
import { showToast } from '../services/modals.js';
import { getSelectedModel, saveSelectedModel } from '../utils/helpers.js';

// =============================================================================
// State
// =============================================================================

let appConfig = null;
let availableModels = [];
let selectedModelId = null;
let modelSelector = null;

// =============================================================================
// Default Configuration
// =============================================================================

const DEFAULT_CONFIG = {
    app_name: 'Agent Host',
    welcome_message: 'Your AI assistant with access to powerful tools.',
    rate_limit_requests_per_minute: 20,
    rate_limit_concurrent_requests: 1,
    app_tag: '',
    app_repo_url: '',
    available_models: [],
    tools_provider_url: '',
};

// =============================================================================
// Configuration Loading
// =============================================================================

/**
 * Load application configuration from the backend
 * @param {HTMLSelectElement} modelSelectorEl - Model selector element
 * @returns {Promise<Object>} Application configuration
 */
export async function loadAppConfig(modelSelectorEl) {
    modelSelector = modelSelectorEl;

    try {
        appConfig = await api.getConfig();

        // Apply app name to page title, header, and welcome message
        applyAppName(appConfig.app_name);

        // Apply welcome message
        applyWelcomeMessage(appConfig.welcome_message);

        // Load model options from config (only if model selection is allowed)
        if (appConfig.allow_model_selection && appConfig.available_models?.length > 0) {
            availableModels = appConfig.available_models;
            initModelSelector();
        }

        // Apply sidebar footer
        updateSidebarFooter(appConfig);

        console.log('App config loaded:', appConfig);
        return appConfig;
    } catch (error) {
        console.error('Failed to load app config:', error);
        appConfig = { ...DEFAULT_CONFIG };
        return appConfig;
    }
}

/**
 * Apply app name to page elements
 * @param {string} appName - Application name
 */
function applyAppName(appName) {
    if (!appName) return;

    document.title = `${appName} - AI Chat`;

    const headerAppName = document.getElementById('header-app-name');
    if (headerAppName) {
        headerAppName.textContent = appName;
    }

    const welcomeTitle = document.getElementById('welcome-title');
    if (welcomeTitle) {
        welcomeTitle.textContent = `Welcome to ${appName}`;
    }
}

/**
 * Apply welcome message to subtitle
 * @param {string} message - Welcome message
 */
function applyWelcomeMessage(message) {
    const welcomeSubtitle = document.getElementById('welcome-subtitle');
    if (welcomeSubtitle && message) {
        welcomeSubtitle.textContent = message;
    }
}

/**
 * Update the sidebar footer with app tag, copyright, and GitHub link
 * @param {Object} config - Application configuration
 */
function updateSidebarFooter(config) {
    const appTagEl = document.getElementById('app-tag');
    const copyrightYearEl = document.getElementById('copyright-year');
    const githubLinkEl = document.getElementById('github-link');

    // Set current year for copyright
    if (copyrightYearEl) {
        copyrightYearEl.textContent = new Date().getFullYear();
    }

    // Set app tag if configured
    if (appTagEl && config.app_tag) {
        appTagEl.textContent = config.app_tag;
    }

    // Show GitHub link if URL is configured
    if (githubLinkEl && config.app_repo_url) {
        githubLinkEl.href = config.app_repo_url;
        githubLinkEl.classList.remove('d-none');
    }
}

// =============================================================================
// Model Selector
// =============================================================================

/**
 * Initialize the model selector dropdown
 */
function initModelSelector() {
    if (!modelSelector || !availableModels.length) return;

    // Restore previously selected model from localStorage
    const savedModelId = getSelectedModel();

    // Clear and populate options
    modelSelector.innerHTML = '';

    availableModels.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = model.name;
        option.title = model.description || '';
        modelSelector.appendChild(option);
    });

    // Restore selection or use first model as default
    if (savedModelId && availableModels.some(m => m.id === savedModelId)) {
        selectedModelId = savedModelId;
        modelSelector.value = savedModelId;
    } else if (availableModels.length > 0) {
        selectedModelId = availableModels[0].id;
        modelSelector.value = selectedModelId;
    }

    // Show the model selector container
    const modelSelectorContainer = document.getElementById('model-selector-container');
    if (modelSelectorContainer) {
        modelSelectorContainer.classList.remove('d-none');
    }
}

/**
 * Handle model selection change
 * @param {Event} e - Change event
 */
export function handleModelChange(e) {
    selectedModelId = e.target.value;
    saveSelectedModel(selectedModelId);

    const selectedModel = availableModels.find(m => m.id === selectedModelId);
    if (selectedModel) {
        showToast(`Switched to ${selectedModel.name}`, 'info');
    }
}

// =============================================================================
// Getters
// =============================================================================

/**
 * Get current application configuration
 * @returns {Object} Application configuration
 */
export function getAppConfig() {
    return appConfig;
}

/**
 * Get currently selected model ID
 * @returns {string|null} Selected model ID
 */
export function getSelectedModelId() {
    return selectedModelId;
}

/**
 * Get available models
 * @returns {Array} Available models
 */
export function getAvailableModels() {
    return availableModels;
}
