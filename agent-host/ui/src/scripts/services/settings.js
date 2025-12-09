/**
 * Settings Service
 * Handles admin settings modal functionality
 */
import { api } from './api.js';
import { showToast } from './modals.js';

// Settings state
let settingsModal = null;
let resetConfirmModal = null;
let currentSettings = null;
let isLoading = false;

// DOM element references
const elements = {
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

/**
 * Initialize the settings service
 * @param {Function} isAdminFn - Function to check if current user is admin
 */
export function initSettings(isAdminFn) {
    const modalEl = document.getElementById('settings-modal');
    if (!modalEl) {
        console.warn('Settings modal not found');
        return;
    }

    settingsModal = new bootstrap.Modal(modalEl);

    // Initialize reset confirmation modal
    const resetModalEl = document.getElementById('reset-settings-modal');
    if (resetModalEl) {
        resetConfirmModal = new bootstrap.Modal(resetModalEl);
    }

    // Cache DOM elements
    cacheElements();

    // Bind event handlers
    bindEvents(isAdminFn);

    // Initialize tooltips in settings modal with proper auto-hide
    initSettingsTooltips(modalEl);
}

/**
 * Initialize Bootstrap tooltips within the settings modal
 * @param {HTMLElement} modalEl - The modal element
 */
function initSettingsTooltips(modalEl) {
    const tooltipTriggers = modalEl.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggers.forEach(el => {
        new bootstrap.Tooltip(el, {
            trigger: 'hover',
            delay: { show: 200, hide: 0 },
        });
    });
}

/**
 * Cache DOM element references
 */
function cacheElements() {
    // LLM tab
    elements.ollamaUrl = document.getElementById('settings-ollama-url');
    elements.ollamaTimeout = document.getElementById('settings-ollama-timeout');
    elements.ollamaModel = document.getElementById('settings-ollama-model');
    elements.ollamaNumCtx = document.getElementById('settings-ollama-num-ctx');
    elements.ollamaTemperature = document.getElementById('settings-ollama-temperature');
    elements.ollamaTopP = document.getElementById('settings-ollama-top-p');
    elements.temperatureValue = document.getElementById('temperature-value');
    elements.topPValue = document.getElementById('top-p-value');
    elements.allowModelSelection = document.getElementById('settings-allow-model-selection');
    elements.availableModels = document.getElementById('settings-available-models');
    elements.refreshModelsBtn = document.getElementById('refresh-models-btn');

    // Agent tab
    elements.agentName = document.getElementById('settings-agent-name');
    elements.agentTimeout = document.getElementById('settings-agent-timeout');
    elements.maxIterations = document.getElementById('settings-max-iterations');
    elements.maxToolCalls = document.getElementById('settings-max-tool-calls');
    elements.maxRetries = document.getElementById('settings-max-retries');
    elements.stopOnError = document.getElementById('settings-stop-on-error');
    elements.retryOnError = document.getElementById('settings-retry-on-error');
    elements.systemPrompt = document.getElementById('settings-system-prompt');

    // UI tab
    elements.welcomeMessage = document.getElementById('settings-welcome-message');
    elements.rateLimitRpm = document.getElementById('settings-rate-limit-rpm');
    elements.rateLimitConcurrent = document.getElementById('settings-rate-limit-concurrent');
    elements.appTag = document.getElementById('settings-app-tag');
    elements.appRepoUrl = document.getElementById('settings-app-repo-url');

    // Modal controls
    elements.saveBtn = document.getElementById('save-settings-btn');
    elements.resetBtn = document.getElementById('reset-settings-btn');
    elements.statusText = document.getElementById('settings-status');
}

/**
 * Bind event handlers
 */
function bindEvents(isAdminFn) {
    // Admin settings button
    const adminSettingsBtn = document.getElementById('admin-settings-btn');
    if (adminSettingsBtn) {
        adminSettingsBtn.addEventListener('click', () => {
            if (isAdminFn && isAdminFn()) {
                showSettingsModal();
            } else {
                showToast('Admin access required', 'warning');
            }
        });
    }

    // Save button
    elements.saveBtn?.addEventListener('click', saveSettings);

    // Reset button - opens confirmation modal
    elements.resetBtn?.addEventListener('click', showResetConfirmation);

    // Reset confirmation button in modal
    const resetConfirmBtn = document.getElementById('reset-settings-confirm-btn');
    if (resetConfirmBtn) {
        resetConfirmBtn.addEventListener('click', confirmResetSettings);
    }

    // Refresh models button
    elements.refreshModelsBtn?.addEventListener('click', loadOllamaModels);

    // Range input live updates
    elements.ollamaTemperature?.addEventListener('input', () => {
        if (elements.temperatureValue) {
            elements.temperatureValue.textContent = elements.ollamaTemperature.value;
        }
    });

    elements.ollamaTopP?.addEventListener('input', () => {
        if (elements.topPValue) {
            elements.topPValue.textContent = elements.ollamaTopP.value;
        }
    });
}

/**
 * Show the settings modal for admin users
 */
export async function showSettingsModal() {
    if (!settingsModal) {
        console.error('Settings modal not initialized');
        return;
    }

    setStatus('Loading settings...');
    settingsModal.show();

    try {
        await loadSettings();
        setStatus('');
    } catch (error) {
        console.error('Failed to load settings:', error);
        setStatus('Failed to load settings', true);
    }
}

/**
 * Load current settings from API
 */
async function loadSettings() {
    isLoading = true;
    try {
        currentSettings = await api.getSettings();
        populateForm(currentSettings);

        // Also load available Ollama models
        await loadOllamaModels();
    } finally {
        isLoading = false;
    }
}

/**
 * Load available Ollama models
 */
async function loadOllamaModels() {
    if (!elements.ollamaModel) return;

    const currentValue = elements.ollamaModel.value;
    elements.ollamaModel.innerHTML = '<option value="">Loading...</option>';

    try {
        const models = await api.getOllamaModels();

        elements.ollamaModel.innerHTML = '';

        if (models.length === 0) {
            elements.ollamaModel.innerHTML = '<option value="">No models found</option>';
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
            elements.ollamaModel.appendChild(option);
        });

        // Restore current value or set from settings
        if (currentValue) {
            elements.ollamaModel.value = currentValue;
        } else if (currentSettings?.llm?.ollama_model) {
            elements.ollamaModel.value = currentSettings.llm.ollama_model;
        }
    } catch (error) {
        console.error('Failed to load Ollama models:', error);
        elements.ollamaModel.innerHTML = '<option value="">Failed to load models</option>';

        // Add current model as option if we have it
        if (currentSettings?.llm?.ollama_model) {
            const option = document.createElement('option');
            option.value = currentSettings.llm.ollama_model;
            option.textContent = currentSettings.llm.ollama_model + ' (current)';
            option.selected = true;
            elements.ollamaModel.appendChild(option);
        }
    }
}

/**
 * Populate the form with settings data
 */
function populateForm(settings) {
    if (!settings) return;

    // LLM settings
    if (settings.llm) {
        setInputValue(elements.ollamaUrl, settings.llm.ollama_url);
        setInputValue(elements.ollamaTimeout, settings.llm.ollama_timeout);
        setInputValue(elements.ollamaModel, settings.llm.ollama_model);
        setInputValue(elements.ollamaNumCtx, settings.llm.ollama_num_ctx);
        setInputValue(elements.ollamaTemperature, settings.llm.ollama_temperature);
        setInputValue(elements.ollamaTopP, settings.llm.ollama_top_p);
        setCheckboxValue(elements.allowModelSelection, settings.llm.allow_model_selection);
        setInputValue(elements.availableModels, settings.llm.available_models);

        // Update range display values
        if (elements.temperatureValue) {
            elements.temperatureValue.textContent = settings.llm.ollama_temperature;
        }
        if (elements.topPValue) {
            elements.topPValue.textContent = settings.llm.ollama_top_p;
        }
    }

    // Agent settings
    if (settings.agent) {
        setInputValue(elements.agentName, settings.agent.agent_name);
        setInputValue(elements.agentTimeout, settings.agent.timeout_seconds);
        setInputValue(elements.maxIterations, settings.agent.max_iterations);
        setInputValue(elements.maxToolCalls, settings.agent.max_tool_calls_per_iteration);
        setInputValue(elements.maxRetries, settings.agent.max_retries);
        setCheckboxValue(elements.stopOnError, settings.agent.stop_on_error);
        setCheckboxValue(elements.retryOnError, settings.agent.retry_on_error);
        setInputValue(elements.systemPrompt, settings.agent.system_prompt);
    }

    // UI settings
    if (settings.ui) {
        setInputValue(elements.welcomeMessage, settings.ui.welcome_message);
        setInputValue(elements.rateLimitRpm, settings.ui.rate_limit_requests_per_minute);
        setInputValue(elements.rateLimitConcurrent, settings.ui.rate_limit_concurrent_requests);
        setInputValue(elements.appTag, settings.ui.app_tag);
        setInputValue(elements.appRepoUrl, settings.ui.app_repo_url);
    }

    // Show if using defaults
    if (settings.is_default) {
        setStatus('Using default settings (no stored configuration)');
    } else if (settings.updated_at) {
        const updatedAt = new Date(settings.updated_at).toLocaleString();
        const updatedBy = settings.updated_by || 'unknown';
        setStatus(`Last updated: ${updatedAt} by ${updatedBy}`);
    }
}

/**
 * Save current settings
 */
async function saveSettings() {
    if (isLoading) return;

    setStatus('Saving...');
    elements.saveBtn.disabled = true;

    try {
        const settings = collectFormData();
        const result = await api.updateSettings(settings);

        currentSettings = result;
        showToast('Settings saved successfully. Reloading...', 'success');
        setStatus('Saved successfully');

        // Reload the page to apply new settings
        setTimeout(() => {
            window.location.reload();
        }, 1500);
    } catch (error) {
        console.error('Failed to save settings:', error);
        showToast(error.message || 'Failed to save settings', 'danger');
        setStatus('Save failed', true);
    } finally {
        elements.saveBtn.disabled = false;
    }
}

/**
 * Show reset confirmation modal
 */
function showResetConfirmation() {
    if (isLoading) return;

    if (resetConfirmModal) {
        resetConfirmModal.show();
    } else {
        // Fallback if modal not available
        if (confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
            confirmResetSettings();
        }
    }
}

/**
 * Confirm and execute reset settings
 */
async function confirmResetSettings() {
    if (isLoading) return;

    // Hide confirmation modal
    resetConfirmModal?.hide();

    setStatus('Resetting...');
    elements.resetBtn.disabled = true;

    try {
        const result = await api.resetSettings();
        currentSettings = result;
        populateForm(result);
        showToast('Settings reset to defaults. Reloading...', 'success');
        setStatus('Reset to defaults');

        // Reload the page to apply default settings
        setTimeout(() => {
            window.location.reload();
        }, 1500);
    } catch (error) {
        console.error('Failed to reset settings:', error);
        showToast(error.message || 'Failed to reset settings', 'danger');
        setStatus('Reset failed', true);
    } finally {
        elements.resetBtn.disabled = false;
    }
}

/**
 * Collect form data into settings object
 * Note: app_tag is read-only and not included (set via env vars only)
 */
function collectFormData() {
    return {
        llm: {
            ollama_url: getInputValue(elements.ollamaUrl),
            ollama_timeout: getNumberValue(elements.ollamaTimeout),
            ollama_model: getInputValue(elements.ollamaModel),
            ollama_num_ctx: getNumberValue(elements.ollamaNumCtx),
            ollama_temperature: getNumberValue(elements.ollamaTemperature),
            ollama_top_p: getNumberValue(elements.ollamaTopP),
            ollama_stream: true, // Always enabled
            allow_model_selection: getCheckboxValue(elements.allowModelSelection),
            available_models: getInputValue(elements.availableModels),
        },
        agent: {
            agent_name: getInputValue(elements.agentName),
            timeout_seconds: getNumberValue(elements.agentTimeout),
            max_iterations: getNumberValue(elements.maxIterations),
            max_tool_calls_per_iteration: getNumberValue(elements.maxToolCalls),
            max_retries: getNumberValue(elements.maxRetries),
            stop_on_error: getCheckboxValue(elements.stopOnError),
            retry_on_error: getCheckboxValue(elements.retryOnError),
            system_prompt: getInputValue(elements.systemPrompt),
        },
        ui: {
            welcome_message: getInputValue(elements.welcomeMessage),
            rate_limit_requests_per_minute: getNumberValue(elements.rateLimitRpm),
            rate_limit_concurrent_requests: getNumberValue(elements.rateLimitConcurrent),
            // app_tag is read-only - set via AGENT_HOST_APP_TAG env var only
            app_repo_url: getInputValue(elements.appRepoUrl),
        },
    };
}

// Helper functions
function setInputValue(el, value) {
    if (el && value !== undefined && value !== null) {
        el.value = value;
    }
}

function setCheckboxValue(el, value) {
    if (el) {
        el.checked = !!value;
    }
}

function getInputValue(el) {
    return el?.value?.trim() || null;
}

function getNumberValue(el) {
    if (!el) return null;
    const val = parseFloat(el.value);
    return isNaN(val) ? null : val;
}

function getCheckboxValue(el) {
    return el?.checked ?? false;
}

function setStatus(text, isError = false) {
    if (elements.statusText) {
        elements.statusText.textContent = text;
        elements.statusText.classList.toggle('text-danger', isError);
        elements.statusText.classList.toggle('text-muted', !isError);
    }
}

/**
 * Update admin settings button visibility
 * @param {boolean} isAdmin - Whether current user is admin
 * @param {boolean} isAuthenticated - Whether user is authenticated
 */
export function updateAdminButtonVisibility(isAdmin, isAuthenticated) {
    const adminSettingsBtn = document.getElementById('admin-settings-btn');
    if (adminSettingsBtn) {
        if (isAuthenticated && isAdmin) {
            adminSettingsBtn.classList.remove('d-none');
        } else {
            adminSettingsBtn.classList.add('d-none');
        }
    }
}
