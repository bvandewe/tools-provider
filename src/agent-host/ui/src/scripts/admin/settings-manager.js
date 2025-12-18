/**
 * Settings Manager for Admin Page
 *
 * Handles loading, saving, and resetting application settings.
 */

export class SettingsManager {
    constructor() {
        this.baseUrl = '/api';
        this.resetModal = null;
        this.hasUnsavedChanges = false;
    }

    /**
     * Initialize the settings manager
     */
    init() {
        this.resetModal = new bootstrap.Modal(document.getElementById('reset-settings-modal'));
        this.setupEventListeners();
        this.setupRangeInputs();
        this.setupAuthTypeToggle();
        this.setupProviderToggles();
        this.loadSettings();
        this.loadModels();
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Save button
        document.getElementById('save-settings-btn')?.addEventListener('click', () => {
            this.saveSettings();
        });

        // Reset button
        document.getElementById('reset-settings-btn')?.addEventListener('click', () => {
            this.resetModal.show();
        });

        // Reset confirmation
        document.getElementById('reset-settings-confirm-btn')?.addEventListener('click', () => {
            this.resetSettings();
        });

        // Refresh models button
        document.getElementById('refresh-models-btn')?.addEventListener('click', () => {
            this.loadModels();
        });

        // Track unsaved changes
        document.querySelectorAll('#settings-page input, #settings-page textarea, #settings-page select').forEach(el => {
            el.addEventListener('change', () => {
                this.hasUnsavedChanges = true;
            });
        });
    }

    /**
     * Set up range input value display
     */
    setupRangeInputs() {
        // Ollama temperature
        const ollamaTemperatureRange = document.getElementById('settings-ollama-temperature');
        const ollamaTemperatureValue = document.getElementById('ollama-temperature-value');
        if (ollamaTemperatureRange && ollamaTemperatureValue) {
            ollamaTemperatureRange.addEventListener('input', e => {
                ollamaTemperatureValue.textContent = e.target.value;
            });
        }

        // Ollama top-p
        const ollamaTopPRange = document.getElementById('settings-ollama-top-p');
        const ollamaTopPValue = document.getElementById('ollama-top-p-value');
        if (ollamaTopPRange && ollamaTopPValue) {
            ollamaTopPRange.addEventListener('input', e => {
                ollamaTopPValue.textContent = e.target.value;
            });
        }

        // OpenAI temperature
        const openaiTemperatureRange = document.getElementById('settings-openai-temperature');
        const openaiTemperatureValue = document.getElementById('openai-temperature-value');
        if (openaiTemperatureRange && openaiTemperatureValue) {
            openaiTemperatureRange.addEventListener('input', e => {
                openaiTemperatureValue.textContent = e.target.value;
            });
        }

        // OpenAI top-p
        const openaiTopPRange = document.getElementById('settings-openai-top-p');
        const openaiTopPValue = document.getElementById('openai-top-p-value');
        if (openaiTopPRange && openaiTopPValue) {
            openaiTopPRange.addEventListener('input', e => {
                openaiTopPValue.textContent = e.target.value;
            });
        }
    }

    /**
     * Set up OpenAI auth type toggle (API Key vs OAuth2)
     */
    setupAuthTypeToggle() {
        const authTypeSelect = document.getElementById('settings-openai-auth-type');
        const apiKeySection = document.getElementById('openai-api-key-section');
        const oauth2Section = document.getElementById('openai-oauth2-section');

        if (authTypeSelect && apiKeySection && oauth2Section) {
            authTypeSelect.addEventListener('change', e => {
                this.toggleAuthSections(e.target.value);
            });
        }
    }

    /**
     * Toggle visibility of auth sections based on auth type
     * @param {string} authType - 'api_key' or 'oauth2'
     */
    toggleAuthSections(authType) {
        const apiKeySection = document.getElementById('openai-api-key-section');
        const oauth2Section = document.getElementById('openai-oauth2-section');

        if (authType === 'oauth2') {
            if (apiKeySection) apiKeySection.style.display = 'none';
            if (oauth2Section) oauth2Section.style.display = 'block';
        } else {
            if (apiKeySection) apiKeySection.style.display = 'block';
            if (oauth2Section) oauth2Section.style.display = 'none';
        }
    }

    /**
     * Set up provider enable/disable toggles
     */
    setupProviderToggles() {
        const ollamaEnabled = document.getElementById('settings-ollama-enabled');
        const ollamaSection = document.getElementById('ollama-settings-section');

        if (ollamaEnabled && ollamaSection) {
            ollamaEnabled.addEventListener('change', e => {
                this.toggleProviderSection(ollamaSection, e.target.checked);
            });
        }

        const openaiEnabled = document.getElementById('settings-openai-enabled');
        const openaiSection = document.getElementById('openai-settings-section');

        if (openaiEnabled && openaiSection) {
            openaiEnabled.addEventListener('change', e => {
                this.toggleProviderSection(openaiSection, e.target.checked);
            });
        }
    }

    /**
     * Toggle visibility and disable state of a provider section
     * @param {HTMLElement} section - The section element
     * @param {boolean} enabled - Whether the provider is enabled
     */
    toggleProviderSection(section, enabled) {
        if (section) {
            section.style.opacity = enabled ? '1' : '0.5';
            section.querySelectorAll('input, select, textarea, button').forEach(el => {
                el.disabled = !enabled;
            });
        }
    }

    /**
     * Load settings from the API
     */
    async loadSettings() {
        try {
            const response = await fetch(`${this.baseUrl}/settings`, {
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error('Failed to load settings');
            }

            const settings = await response.json();
            this.populateForm(settings);
            this.hasUnsavedChanges = false;
        } catch (error) {
            console.error('Error loading settings:', error);
            this.showToast('Failed to load settings', 'danger');
        }
    }

    /**
     * Populate form fields with settings values
     * @param {Object} settings - Settings object from API (nested structure with llm, agent, ui)
     */
    populateForm(settings) {
        // LLM Settings (nested under settings.llm)
        const llm = settings.llm || {};

        // Default Provider
        this.setInputValue('settings-default-llm-provider', llm.default_llm_provider || 'ollama');

        // Ollama Settings
        this.setCheckboxValue('settings-ollama-enabled', llm.ollama_enabled ?? true);
        this.setInputValue('settings-ollama-url', llm.ollama_url);
        this.setInputValue('settings-ollama-timeout', llm.ollama_timeout);
        this.setInputValue('settings-ollama-model', llm.ollama_model);
        this.setInputValue('settings-ollama-num-ctx', llm.ollama_num_ctx);

        const ollamaTemp = llm.ollama_temperature ?? 0.7;
        this.setInputValue('settings-ollama-temperature', ollamaTemp);
        const ollamaTempValue = document.getElementById('ollama-temperature-value');
        if (ollamaTempValue) ollamaTempValue.textContent = ollamaTemp;

        const ollamaTopP = llm.ollama_top_p ?? 0.9;
        this.setInputValue('settings-ollama-top-p', ollamaTopP);
        const ollamaTopPValue = document.getElementById('ollama-top-p-value');
        if (ollamaTopPValue) ollamaTopPValue.textContent = ollamaTopP;

        // Toggle Ollama section based on enabled state
        const ollamaSection = document.getElementById('ollama-settings-section');
        this.toggleProviderSection(ollamaSection, llm.ollama_enabled ?? true);

        // OpenAI Settings
        this.setCheckboxValue('settings-openai-enabled', llm.openai_enabled ?? false);
        this.setInputValue('settings-openai-api-endpoint', llm.openai_api_endpoint);
        this.setInputValue('settings-openai-api-version', llm.openai_api_version);
        this.setInputValue('settings-openai-model', llm.openai_model);
        this.setInputValue('settings-openai-timeout', llm.openai_timeout);
        this.setInputValue('settings-openai-max-tokens', llm.openai_max_tokens);

        const openaiTemp = llm.openai_temperature ?? 0.7;
        this.setInputValue('settings-openai-temperature', openaiTemp);
        const openaiTempValue = document.getElementById('openai-temperature-value');
        if (openaiTempValue) openaiTempValue.textContent = openaiTemp;

        const openaiTopP = llm.openai_top_p ?? 0.9;
        this.setInputValue('settings-openai-top-p', openaiTopP);
        const openaiTopPValue = document.getElementById('openai-top-p-value');
        if (openaiTopPValue) openaiTopPValue.textContent = openaiTopP;

        // OpenAI Auth
        const authType = llm.openai_auth_type || 'api_key';
        this.setInputValue('settings-openai-auth-type', authType);
        this.setInputValue('settings-openai-api-key', llm.openai_api_key);
        this.setInputValue('settings-openai-oauth-endpoint', llm.openai_oauth_endpoint);
        this.setInputValue('settings-openai-oauth-client-id', llm.openai_oauth_client_id);
        this.setInputValue('settings-openai-oauth-client-secret', llm.openai_oauth_client_secret);
        this.setInputValue('settings-openai-oauth-token-ttl', llm.openai_oauth_token_ttl);

        // OpenAI Custom Headers
        this.setInputValue('settings-openai-app-key', llm.openai_app_key);
        this.setInputValue('settings-openai-client-id-header', llm.openai_client_id_header);

        // Toggle auth sections based on auth type
        this.toggleAuthSections(authType);

        // Toggle OpenAI section based on enabled state
        const openaiSection = document.getElementById('openai-settings-section');
        this.toggleProviderSection(openaiSection, llm.openai_enabled ?? false);

        // Model Selection
        this.setCheckboxValue('settings-allow-model-selection', llm.allow_model_selection);
        this.setInputValue('settings-available-models', llm.available_models || '');

        // Agent Settings (nested under settings.agent)
        const agent = settings.agent || {};
        this.setInputValue('settings-agent-name', agent.agent_name);
        this.setInputValue('settings-agent-timeout', agent.timeout_seconds);
        this.setInputValue('settings-max-iterations', agent.max_iterations);
        this.setInputValue('settings-max-tool-calls', agent.max_tool_calls_per_iteration);
        this.setInputValue('settings-max-retries', agent.max_retries);
        this.setCheckboxValue('settings-stop-on-error', agent.stop_on_error);
        this.setCheckboxValue('settings-retry-on-error', agent.retry_on_error);
        this.setInputValue('settings-system-prompt', agent.system_prompt);

        // UI Settings (nested under settings.ui)
        const ui = settings.ui || {};
        this.setInputValue('settings-welcome-message', ui.welcome_message);
        this.setInputValue('settings-rate-limit-rpm', ui.rate_limit_requests_per_minute);
        this.setInputValue('settings-rate-limit-concurrent', ui.rate_limit_concurrent_requests);
        this.setInputValue('settings-app-tag', ui.app_tag);
        this.setInputValue('settings-app-repo-url', ui.app_repo_url);
    }

    /**
     * Set input value helper
     * @param {string} id - Input element ID
     * @param {*} value - Value to set
     */
    setInputValue(id, value) {
        const el = document.getElementById(id);
        if (el && value !== undefined && value !== null) {
            el.value = value;
        }
    }

    /**
     * Set checkbox value helper
     * @param {string} id - Checkbox element ID
     * @param {boolean} checked - Checked state
     */
    setCheckboxValue(id, checked) {
        const el = document.getElementById(id);
        if (el) {
            el.checked = checked ?? false;
        }
    }

    /**
     * Load available models from config endpoint
     */
    async loadModels() {
        const select = document.getElementById('settings-ollama-model');
        const currentValue = select?.value;

        try {
            // Fetch from /config which includes available_models
            const response = await fetch(`${this.baseUrl}/config`, {
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error('Failed to load config');
            }

            const config = await response.json();
            const models = config.available_models || [];

            if (select) {
                select.innerHTML = '';
                models.forEach(model => {
                    const option = document.createElement('option');
                    // model has {name, description, provider}
                    option.value = `${model.provider}:${model.name}`;
                    option.textContent = `${model.name} (${model.provider})`;
                    if (model.description) {
                        option.title = model.description;
                    }
                    select.appendChild(option);
                });

                // Restore previous selection if it exists, or use default_model from config
                if (currentValue && select.querySelector(`option[value="${currentValue}"]`)) {
                    select.value = currentValue;
                } else if (config.default_model) {
                    select.value = config.default_model;
                }
            }
        } catch (error) {
            console.error('Error loading models:', error);
            if (select) {
                select.innerHTML = '<option value="">Error loading models</option>';
            }
        }
    }

    /**
     * Save settings to the API
     */
    async saveSettings() {
        const settings = this.collectFormValues();

        try {
            const response = await fetch(`${this.baseUrl}/settings`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(settings),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to save settings');
            }

            this.hasUnsavedChanges = false;
            this.showToast('Settings saved successfully', 'success');
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showToast(`Failed to save settings: ${error.message}`, 'danger');
        }
    }

    /**
     * Collect form values into a settings object
     * @returns {Object} Settings object matching API structure (nested llm, agent, ui)
     */
    collectFormValues() {
        return {
            // LLM Settings
            llm: {
                // Default provider
                default_llm_provider: document.getElementById('settings-default-llm-provider')?.value || 'ollama',

                // Ollama settings
                ollama_enabled: document.getElementById('settings-ollama-enabled')?.checked ?? true,
                ollama_url: document.getElementById('settings-ollama-url')?.value || null,
                ollama_model: document.getElementById('settings-ollama-model')?.value || null,
                ollama_timeout: parseFloat(document.getElementById('settings-ollama-timeout')?.value) || null,
                ollama_temperature: parseFloat(document.getElementById('settings-ollama-temperature')?.value) || null,
                ollama_top_p: parseFloat(document.getElementById('settings-ollama-top-p')?.value) || null,
                ollama_num_ctx: parseInt(document.getElementById('settings-ollama-num-ctx')?.value) || null,

                // OpenAI settings
                openai_enabled: document.getElementById('settings-openai-enabled')?.checked ?? false,
                openai_api_endpoint: document.getElementById('settings-openai-api-endpoint')?.value || null,
                openai_api_version: document.getElementById('settings-openai-api-version')?.value || null,
                openai_model: document.getElementById('settings-openai-model')?.value || null,
                openai_timeout: parseFloat(document.getElementById('settings-openai-timeout')?.value) || null,
                openai_temperature: parseFloat(document.getElementById('settings-openai-temperature')?.value) || null,
                openai_top_p: parseFloat(document.getElementById('settings-openai-top-p')?.value) || null,
                openai_max_tokens: parseInt(document.getElementById('settings-openai-max-tokens')?.value) || null,

                // OpenAI auth
                openai_auth_type: document.getElementById('settings-openai-auth-type')?.value || 'api_key',
                openai_api_key: document.getElementById('settings-openai-api-key')?.value || null,
                openai_oauth_endpoint: document.getElementById('settings-openai-oauth-endpoint')?.value || null,
                openai_oauth_client_id: document.getElementById('settings-openai-oauth-client-id')?.value || null,
                openai_oauth_client_secret: document.getElementById('settings-openai-oauth-client-secret')?.value || null,
                openai_oauth_token_ttl: parseInt(document.getElementById('settings-openai-oauth-token-ttl')?.value) || null,

                // OpenAI custom headers
                openai_app_key: document.getElementById('settings-openai-app-key')?.value || null,
                openai_client_id_header: document.getElementById('settings-openai-client-id-header')?.value || null,

                // Model selection
                allow_model_selection: document.getElementById('settings-allow-model-selection')?.checked || false,
                available_models: document.getElementById('settings-available-models')?.value || null,
            },

            // Agent Settings
            agent: {
                agent_name: document.getElementById('settings-agent-name')?.value || null,
                timeout_seconds: parseFloat(document.getElementById('settings-agent-timeout')?.value) || null,
                max_iterations: parseInt(document.getElementById('settings-max-iterations')?.value) || null,
                max_tool_calls_per_iteration: parseInt(document.getElementById('settings-max-tool-calls')?.value) || null,
                max_retries: parseInt(document.getElementById('settings-max-retries')?.value) || null,
                stop_on_error: document.getElementById('settings-stop-on-error')?.checked || false,
                retry_on_error: document.getElementById('settings-retry-on-error')?.checked || false,
                system_prompt: document.getElementById('settings-system-prompt')?.value || null,
            },

            // UI Settings
            ui: {
                welcome_message: document.getElementById('settings-welcome-message')?.value || null,
                rate_limit_requests_per_minute: parseInt(document.getElementById('settings-rate-limit-rpm')?.value) || null,
                rate_limit_concurrent_requests: parseInt(document.getElementById('settings-rate-limit-concurrent')?.value) || null,
                app_tag: document.getElementById('settings-app-tag')?.value || null,
                app_repo_url: document.getElementById('settings-app-repo-url')?.value || null,
            },
        };
    }

    /**
     * Reset settings to defaults
     */
    async resetSettings() {
        try {
            const response = await fetch(`${this.baseUrl}/settings`, {
                method: 'DELETE',
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error('Failed to reset settings');
            }

            this.resetModal.hide();
            await this.loadSettings();
            this.showToast('Settings reset to defaults', 'success');
        } catch (error) {
            console.error('Error resetting settings:', error);
            this.showToast(`Failed to reset settings: ${error.message}`, 'danger');
        }
    }

    /**
     * Check for unsaved changes
     * @returns {boolean} True if there are unsaved changes
     */
    hasChanges() {
        return this.hasUnsavedChanges;
    }

    /**
     * Show a toast notification
     * @param {string} message - Message to display
     * @param {string} type - Toast type (success, danger, warning, info)
     */
    showToast(message, type = 'info') {
        const toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) return;

        const toastId = `toast-${Date.now()}`;
        const iconMap = {
            success: 'bi-check-circle-fill',
            danger: 'bi-exclamation-triangle-fill',
            warning: 'bi-exclamation-circle-fill',
            info: 'bi-info-circle-fill',
        };

        const toastHtml = `
            <div id="${toastId}" class="toast" role="alert">
                <div class="toast-header">
                    <i class="bi ${iconMap[type]} text-${type} me-2"></i>
                    <strong class="me-auto">Settings</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">${message}</div>
            </div>
        `;

        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastEl = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastEl, { delay: 5000 });
        toast.show();

        toastEl.addEventListener('hidden.bs.toast', () => {
            toastEl.remove();
        });
    }
}
