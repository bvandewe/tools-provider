/**
 * SettingsService - Admin Settings Modal Management
 *
 * Handles admin settings modal functionality for LLM, Agent, and UI configuration.
 *
 * NOTE: This settings modal is being superseded by the /admin page for admin users.
 * Consider either:
 * 1. Removing this modal entirely if all settings management moves to /admin
 * 2. Or stripping it down to show only user-specific preferences for non-admin users
 *
 * @module services/SettingsService
 */

import { api } from './api.js';
import { modalService } from './ModalService.js';

/**
 * SettingsService manages admin settings modal and persistence
 */
export class SettingsService {
    /**
     * Create a new SettingsService instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {bootstrap.Modal|null} */
        this._settingsModal = null;

        /** @type {bootstrap.Modal|null} */
        this._resetConfirmModal = null;

        /** @type {Object|null} */
        this._currentSettings = null;

        /** @type {boolean} */
        this._isLoading = false;

        /** @type {Function|null} */
        this._isAdminFn = null;

        /** @type {Object} DOM element references */
        this._elements = {
            // LLM tab
            ollamaUrl: null,
            ollamaTimeout: null,
            ollamaModel: null,
            ollamaNumCtx: null,
            ollamaTemperature: null,
            ollamaTopP: null,
            temperatureValue: null,
            topPValue: null,
            allowModelSelection: null,
            availableModels: null,
            refreshModelsBtn: null,

            // Agent tab
            agentName: null,
            agentTimeout: null,
            maxIterations: null,
            maxToolCalls: null,
            maxRetries: null,
            stopOnError: null,
            retryOnError: null,
            systemPrompt: null,

            // UI tab
            welcomeMessage: null,
            rateLimitRpm: null,
            rateLimitConcurrent: null,
            appTag: null,
            appRepoUrl: null,

            // Modal controls
            saveBtn: null,
            resetBtn: null,
            statusText: null,
        };

        // Bind methods for callbacks
        this._saveSettings = this._saveSettings.bind(this);
        this._showResetConfirmation = this._showResetConfirmation.bind(this);
        this._confirmResetSettings = this._confirmResetSettings.bind(this);
        this._loadOllamaModels = this._loadOllamaModels.bind(this);
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize the settings service
     * @param {Function} [isAdminFn] - Function to check if current user is admin
     */
    init(isAdminFn = null) {
        if (this._initialized) {
            console.warn('[SettingsService] Already initialized');
            return;
        }

        this._isAdminFn = isAdminFn;

        const modalEl = document.getElementById('settings-modal');
        if (!modalEl) {
            console.warn('[SettingsService] Settings modal not found');
            return;
        }

        this._settingsModal = new bootstrap.Modal(modalEl);

        // Initialize reset confirmation modal
        const resetModalEl = document.getElementById('reset-settings-modal');
        if (resetModalEl) {
            this._resetConfirmModal = new bootstrap.Modal(resetModalEl);
        }

        // Cache DOM elements
        this._cacheElements();

        // Bind event handlers
        this._bindEvents();

        // Initialize tooltips in settings modal with proper auto-hide
        this._initSettingsTooltips(modalEl);

        this._initialized = true;
        console.log('[SettingsService] Initialized');
    }

    // =========================================================================
    // Public Methods
    // =========================================================================

    /**
     * Show the settings modal for admin users
     */
    async showSettingsModal() {
        if (!this._settingsModal) {
            console.error('[SettingsService] Settings modal not initialized');
            return;
        }

        this._setStatus('Loading settings...');
        this._settingsModal.show();

        try {
            await this._loadSettings();
            this._setStatus('');
        } catch (error) {
            console.error('[SettingsService] Failed to load settings:', error);
            this._setStatus('Failed to load settings', true);
        }
    }

    /**
     * Update admin buttons visibility (settings and tools)
     * @param {boolean} isAdmin - Whether current user is admin
     * @param {boolean} isAuthenticated - Whether user is authenticated
     * @param {string} [toolsProviderUrl] - URL to the tools provider for admin tools link
     */
    updateAdminButtonVisibility(isAdmin, isAuthenticated, toolsProviderUrl = null) {
        const adminSettingsBtn = document.getElementById('admin-settings-btn');
        const adminToolsBtn = document.getElementById('admin-tools-btn');

        if (isAuthenticated && isAdmin) {
            // Show admin settings button
            if (adminSettingsBtn) {
                adminSettingsBtn.classList.remove('d-none');
            }
            // Show admin tools button and set href
            if (adminToolsBtn) {
                adminToolsBtn.classList.remove('d-none');
                if (toolsProviderUrl) {
                    adminToolsBtn.href = toolsProviderUrl;
                }
            }
        } else {
            // Hide both admin buttons
            if (adminSettingsBtn) {
                adminSettingsBtn.classList.add('d-none');
            }
            if (adminToolsBtn) {
                adminToolsBtn.classList.add('d-none');
            }
        }
    }

    /**
     * Get current settings
     * @returns {Object|null}
     */
    getCurrentSettings() {
        return this._currentSettings;
    }

    // =========================================================================
    // Private Methods - Initialization
    // =========================================================================

    /**
     * Cache DOM element references
     * @private
     */
    _cacheElements() {
        // LLM tab
        this._elements.ollamaUrl = document.getElementById('settings-ollama-url');
        this._elements.ollamaTimeout = document.getElementById('settings-ollama-timeout');
        this._elements.ollamaModel = document.getElementById('settings-ollama-model');
        this._elements.ollamaNumCtx = document.getElementById('settings-ollama-num-ctx');
        this._elements.ollamaTemperature = document.getElementById('settings-ollama-temperature');
        this._elements.ollamaTopP = document.getElementById('settings-ollama-top-p');
        this._elements.temperatureValue = document.getElementById('temperature-value');
        this._elements.topPValue = document.getElementById('top-p-value');
        this._elements.allowModelSelection = document.getElementById('settings-allow-model-selection');
        this._elements.availableModels = document.getElementById('settings-available-models');
        this._elements.refreshModelsBtn = document.getElementById('refresh-models-btn');

        // Agent tab
        this._elements.agentName = document.getElementById('settings-agent-name');
        this._elements.agentTimeout = document.getElementById('settings-agent-timeout');
        this._elements.maxIterations = document.getElementById('settings-max-iterations');
        this._elements.maxToolCalls = document.getElementById('settings-max-tool-calls');
        this._elements.maxRetries = document.getElementById('settings-max-retries');
        this._elements.stopOnError = document.getElementById('settings-stop-on-error');
        this._elements.retryOnError = document.getElementById('settings-retry-on-error');
        this._elements.systemPrompt = document.getElementById('settings-system-prompt');

        // UI tab
        this._elements.welcomeMessage = document.getElementById('settings-welcome-message');
        this._elements.rateLimitRpm = document.getElementById('settings-rate-limit-rpm');
        this._elements.rateLimitConcurrent = document.getElementById('settings-rate-limit-concurrent');
        this._elements.appTag = document.getElementById('settings-app-tag');
        this._elements.appRepoUrl = document.getElementById('settings-app-repo-url');

        // Modal controls
        this._elements.saveBtn = document.getElementById('save-settings-btn');
        this._elements.resetBtn = document.getElementById('reset-settings-btn');
        this._elements.statusText = document.getElementById('settings-status');
    }

    /**
     * Bind event handlers
     * @private
     */
    _bindEvents() {
        // Admin settings button - redirects to /admin page for admin users
        const adminSettingsBtn = document.getElementById('admin-settings-btn');
        if (adminSettingsBtn) {
            adminSettingsBtn.addEventListener('click', () => {
                if (this._isAdminFn && this._isAdminFn()) {
                    // Redirect to dedicated admin page
                    window.location.href = '/admin';
                } else {
                    modalService.showToast('Admin access required', 'warning');
                }
            });
        }

        // Save button
        this._elements.saveBtn?.addEventListener('click', this._saveSettings);

        // Reset button - opens confirmation modal
        this._elements.resetBtn?.addEventListener('click', this._showResetConfirmation);

        // Reset confirmation button in modal
        const resetConfirmBtn = document.getElementById('reset-settings-confirm-btn');
        if (resetConfirmBtn) {
            resetConfirmBtn.addEventListener('click', this._confirmResetSettings);
        }

        // Refresh models button
        this._elements.refreshModelsBtn?.addEventListener('click', this._loadOllamaModels);

        // Range input live updates
        this._elements.ollamaTemperature?.addEventListener('input', () => {
            if (this._elements.temperatureValue) {
                this._elements.temperatureValue.textContent = this._elements.ollamaTemperature.value;
            }
        });

        this._elements.ollamaTopP?.addEventListener('input', () => {
            if (this._elements.topPValue) {
                this._elements.topPValue.textContent = this._elements.ollamaTopP.value;
            }
        });
    }

    /**
     * Initialize Bootstrap tooltips within the settings modal
     * @param {HTMLElement} modalEl - The modal element
     * @private
     */
    _initSettingsTooltips(modalEl) {
        const tooltipTriggers = modalEl.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipTriggers.forEach(el => {
            new bootstrap.Tooltip(el, {
                trigger: 'hover',
                delay: { show: 200, hide: 0 },
            });
        });
    }

    // =========================================================================
    // Private Methods - Settings Operations
    // =========================================================================

    /**
     * Load current settings from API
     * @private
     */
    async _loadSettings() {
        this._isLoading = true;
        try {
            this._currentSettings = await api.getSettings();
            this._populateForm(this._currentSettings);

            // Also load available Ollama models
            await this._loadOllamaModels();
        } finally {
            this._isLoading = false;
        }
    }

    /**
     * Load available Ollama models
     * @private
     */
    async _loadOllamaModels() {
        if (!this._elements.ollamaModel) return;

        const currentValue = this._elements.ollamaModel.value;
        this._elements.ollamaModel.innerHTML = '<option value="">Loading...</option>';

        try {
            const models = await api.getOllamaModels();

            this._elements.ollamaModel.innerHTML = '';

            if (models.length === 0) {
                this._elements.ollamaModel.innerHTML = '<option value="">No models found</option>';
                return;
            }

            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.name;
                option.textContent = model.name;
                if (model.size) {
                    const sizeMB = Math.round(model.size / 1024 / 1024);
                    option.textContent += ` (${sizeMB > 1024 ? Math.round(sizeMB / 1024) + 'GB' : sizeMB + 'MB'})`;
                }
                this._elements.ollamaModel.appendChild(option);
            });

            // Restore current value or set from settings
            if (currentValue) {
                this._elements.ollamaModel.value = currentValue;
            } else if (this._currentSettings?.llm?.ollama_model) {
                this._elements.ollamaModel.value = this._currentSettings.llm.ollama_model;
            }
        } catch (error) {
            console.error('[SettingsService] Failed to load Ollama models:', error);
            this._elements.ollamaModel.innerHTML = '<option value="">Failed to load models</option>';

            // Add current model as option if we have it
            if (this._currentSettings?.llm?.ollama_model) {
                const option = document.createElement('option');
                option.value = this._currentSettings.llm.ollama_model;
                option.textContent = this._currentSettings.llm.ollama_model + ' (current)';
                option.selected = true;
                this._elements.ollamaModel.appendChild(option);
            }
        }
    }

    /**
     * Populate the form with settings data
     * @param {Object} settings - Settings object
     * @private
     */
    _populateForm(settings) {
        if (!settings) return;

        // LLM settings
        if (settings.llm) {
            this._setInputValue(this._elements.ollamaUrl, settings.llm.ollama_url);
            this._setInputValue(this._elements.ollamaTimeout, settings.llm.ollama_timeout);
            this._setInputValue(this._elements.ollamaModel, settings.llm.ollama_model);
            this._setInputValue(this._elements.ollamaNumCtx, settings.llm.ollama_num_ctx);
            this._setInputValue(this._elements.ollamaTemperature, settings.llm.ollama_temperature);
            this._setInputValue(this._elements.ollamaTopP, settings.llm.ollama_top_p);
            this._setCheckboxValue(this._elements.allowModelSelection, settings.llm.allow_model_selection);
            this._setInputValue(this._elements.availableModels, settings.llm.available_models);

            // Update range display values
            if (this._elements.temperatureValue) {
                this._elements.temperatureValue.textContent = settings.llm.ollama_temperature;
            }
            if (this._elements.topPValue) {
                this._elements.topPValue.textContent = settings.llm.ollama_top_p;
            }
        }

        // Agent settings
        if (settings.agent) {
            this._setInputValue(this._elements.agentName, settings.agent.agent_name);
            this._setInputValue(this._elements.agentTimeout, settings.agent.timeout_seconds);
            this._setInputValue(this._elements.maxIterations, settings.agent.max_iterations);
            this._setInputValue(this._elements.maxToolCalls, settings.agent.max_tool_calls_per_iteration);
            this._setInputValue(this._elements.maxRetries, settings.agent.max_retries);
            this._setCheckboxValue(this._elements.stopOnError, settings.agent.stop_on_error);
            this._setCheckboxValue(this._elements.retryOnError, settings.agent.retry_on_error);
            this._setInputValue(this._elements.systemPrompt, settings.agent.system_prompt);
        }

        // UI settings
        if (settings.ui) {
            this._setInputValue(this._elements.welcomeMessage, settings.ui.welcome_message);
            this._setInputValue(this._elements.rateLimitRpm, settings.ui.rate_limit_requests_per_minute);
            this._setInputValue(this._elements.rateLimitConcurrent, settings.ui.rate_limit_concurrent_requests);
            this._setInputValue(this._elements.appTag, settings.ui.app_tag);
            this._setInputValue(this._elements.appRepoUrl, settings.ui.app_repo_url);
        }

        // Show if using defaults
        if (settings.is_default) {
            this._setStatus('Using default settings (no stored configuration)');
        } else if (settings.updated_at) {
            const updatedAt = new Date(settings.updated_at).toLocaleString();
            const updatedBy = settings.updated_by || 'unknown';
            this._setStatus(`Last updated: ${updatedAt} by ${updatedBy}`);
        }
    }

    /**
     * Save current settings
     * @private
     */
    async _saveSettings() {
        if (this._isLoading) return;

        this._setStatus('Saving...');
        this._elements.saveBtn.disabled = true;

        try {
            const settings = this._collectFormData();
            const result = await api.updateSettings(settings);

            this._currentSettings = result;
            modalService.showToast('Settings saved successfully. Reloading...', 'success');
            this._setStatus('Saved successfully');

            // Reload the page to apply new settings
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } catch (error) {
            console.error('[SettingsService] Failed to save settings:', error);
            modalService.showToast(error.message || 'Failed to save settings', 'error');
            this._setStatus('Save failed', true);
        } finally {
            this._elements.saveBtn.disabled = false;
        }
    }

    /**
     * Show reset confirmation modal
     * @private
     */
    _showResetConfirmation() {
        if (this._isLoading) return;

        if (this._resetConfirmModal) {
            this._resetConfirmModal.show();
        } else {
            // Fallback if modal not available
            if (confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
                this._confirmResetSettings();
            }
        }
    }

    /**
     * Confirm and execute reset settings
     * @private
     */
    async _confirmResetSettings() {
        if (this._isLoading) return;

        // Hide confirmation modal
        this._resetConfirmModal?.hide();

        this._setStatus('Resetting...');
        this._elements.resetBtn.disabled = true;

        try {
            const result = await api.resetSettings();
            this._currentSettings = result;
            this._populateForm(result);
            modalService.showToast('Settings reset to defaults. Reloading...', 'success');
            this._setStatus('Reset to defaults');

            // Reload the page to apply default settings
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } catch (error) {
            console.error('[SettingsService] Failed to reset settings:', error);
            modalService.showToast(error.message || 'Failed to reset settings', 'error');
            this._setStatus('Reset failed', true);
        } finally {
            this._elements.resetBtn.disabled = false;
        }
    }

    /**
     * Collect form data into settings object
     * Note: app_tag is read-only and not included (set via env vars only)
     * @returns {Object} Settings object
     * @private
     */
    _collectFormData() {
        return {
            llm: {
                ollama_url: this._getInputValue(this._elements.ollamaUrl),
                ollama_timeout: this._getNumberValue(this._elements.ollamaTimeout),
                ollama_model: this._getInputValue(this._elements.ollamaModel),
                ollama_num_ctx: this._getNumberValue(this._elements.ollamaNumCtx),
                ollama_temperature: this._getNumberValue(this._elements.ollamaTemperature),
                ollama_top_p: this._getNumberValue(this._elements.ollamaTopP),
                ollama_stream: true, // Always enabled
                allow_model_selection: this._getCheckboxValue(this._elements.allowModelSelection),
                available_models: this._getInputValue(this._elements.availableModels),
            },
            agent: {
                agent_name: this._getInputValue(this._elements.agentName),
                timeout_seconds: this._getNumberValue(this._elements.agentTimeout),
                max_iterations: this._getNumberValue(this._elements.maxIterations),
                max_tool_calls_per_iteration: this._getNumberValue(this._elements.maxToolCalls),
                max_retries: this._getNumberValue(this._elements.maxRetries),
                stop_on_error: this._getCheckboxValue(this._elements.stopOnError),
                retry_on_error: this._getCheckboxValue(this._elements.retryOnError),
                system_prompt: this._getInputValue(this._elements.systemPrompt),
            },
            ui: {
                welcome_message: this._getInputValue(this._elements.welcomeMessage),
                rate_limit_requests_per_minute: this._getNumberValue(this._elements.rateLimitRpm),
                rate_limit_concurrent_requests: this._getNumberValue(this._elements.rateLimitConcurrent),
                // app_tag is read-only - set via AGENT_HOST_APP_TAG env var only
                app_repo_url: this._getInputValue(this._elements.appRepoUrl),
            },
        };
    }

    // =========================================================================
    // Private Helpers - Form Utilities
    // =========================================================================

    /**
     * Set input element value
     * @param {HTMLElement} el - Input element
     * @param {*} value - Value to set
     * @private
     */
    _setInputValue(el, value) {
        if (el && value !== undefined && value !== null) {
            el.value = value;
        }
    }

    /**
     * Set checkbox element value
     * @param {HTMLElement} el - Checkbox element
     * @param {boolean} value - Value to set
     * @private
     */
    _setCheckboxValue(el, value) {
        if (el) {
            el.checked = !!value;
        }
    }

    /**
     * Get input element value
     * @param {HTMLElement} el - Input element
     * @returns {string|null} Trimmed value or null
     * @private
     */
    _getInputValue(el) {
        return el?.value?.trim() || null;
    }

    /**
     * Get number value from input element
     * @param {HTMLElement} el - Input element
     * @returns {number|null} Parsed number or null
     * @private
     */
    _getNumberValue(el) {
        if (!el) return null;
        const val = parseFloat(el.value);
        return isNaN(val) ? null : val;
    }

    /**
     * Get checkbox element value
     * @param {HTMLElement} el - Checkbox element
     * @returns {boolean} Checked state
     * @private
     */
    _getCheckboxValue(el) {
        return el?.checked ?? false;
    }

    /**
     * Set status text
     * @param {string} text - Status text
     * @param {boolean} [isError=false] - Whether this is an error status
     * @private
     */
    _setStatus(text, isError = false) {
        if (this._elements.statusText) {
            this._elements.statusText.textContent = text;
            this._elements.statusText.classList.toggle('text-danger', isError);
            this._elements.statusText.classList.toggle('text-muted', !isError);
        }
    }
}

// Export singleton instance
export const settingsService = new SettingsService();
