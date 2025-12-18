/**
 * Definitions Manager
 *
 * Handles CRUD operations for AgentDefinitions in the admin panel.
 */

import { showToast } from '../services/modals.js';

const API_BASE = '/api';

/**
 * Manages AgentDefinition CRUD operations
 */
export class DefinitionsManager {
    constructor() {
        this.definitions = [];
        this.templates = [];
        this.models = [];
        this.editingDefinition = null;
        this.modal = null;
        this.deleteModal = null;
    }

    /**
     * Make an API request with credentials
     */
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const config = {
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        const response = await fetch(url, config);

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || `Request failed: ${response.status}`);
        }

        if (response.status === 204) {
            return null;
        }

        return response.json();
    }

    async init() {
        console.log('📋 Initializing Definitions Manager...');

        // Get modal instances
        this.modal = new bootstrap.Modal(document.getElementById('definition-modal'));
        this.deleteModal = new bootstrap.Modal(document.getElementById('delete-modal'));

        // Setup event listeners
        this.setupEventListeners();

        // Load templates and models for dropdowns
        await Promise.all([this.loadTemplates(), this.loadModels()]);

        // Load definitions
        await this.loadDefinitions();
    }

    setupEventListeners() {
        // Create buttons
        document.getElementById('create-definition-btn')?.addEventListener('click', () => this.showCreateModal());
        document.getElementById('create-definition-btn-empty')?.addEventListener('click', () => this.showCreateModal());

        // Save button
        document.getElementById('save-definition-btn')?.addEventListener('click', () => this.saveDefinition());

        // Delete confirm button
        document.getElementById('confirm-delete-btn')?.addEventListener('click', () => this.confirmDelete());

        // Icon preview
        const iconInput = document.getElementById('definition-icon');
        iconInput?.addEventListener('input', e => this.updateIconPreview(e.target.value));

        // ID field - disable after creation
        const idInput = document.getElementById('definition-id');
        this.modal?._element?.addEventListener('hidden.bs.modal', () => {
            idInput.disabled = false;
            this.editingDefinition = null;
        });
    }

    async loadDefinitions() {
        const loading = document.getElementById('definitions-loading');
        const empty = document.getElementById('definitions-empty');
        const tableContainer = document.getElementById('definitions-table-container');

        try {
            loading.style.display = 'block';
            empty.style.display = 'none';
            tableContainer.style.display = 'none';

            this.definitions = (await this.request('/admin/definitions')) || [];

            loading.style.display = 'none';

            if (this.definitions.length === 0) {
                empty.style.display = 'block';
            } else {
                tableContainer.style.display = 'block';
                this.renderDefinitions();
            }
        } catch (error) {
            console.error('Failed to load definitions:', error);
            loading.style.display = 'none';
            showToast('Failed to load definitions', 'error');
        }
    }

    renderDefinitions() {
        const tbody = document.getElementById('definitions-table-body');
        tbody.innerHTML = '';

        this.definitions.forEach(def => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <i class="bi ${def.icon || 'bi-robot'} fs-5 text-primary"></i>
                </td>
                <td>
                    <div class="fw-medium">${this.escapeHtml(def.name)}</div>
                    <small class="text-muted font-monospace">${this.escapeHtml(def.id)}</small>
                </td>
                <td>
                    ${
                        def.conversation_template_name
                            ? `<span class="badge bg-info" title="${this.escapeHtml(def.conversation_template_id || '')}">${this.escapeHtml(def.conversation_template_name)}</span>`
                            : '<span class="text-muted">—</span>'
                    }
                </td>
                <td>
                    <span class="badge ${def.is_public ? 'bg-success' : 'bg-warning'}">
                        ${def.is_public ? 'Public' : 'Private'}
                    </span>
                </td>
                <td>
                    ${def.owner_user_id ? `<small class="text-muted">${this.escapeHtml(def.owner_user_id.substring(0, 8))}...</small>` : '<span class="badge bg-dark">System</span>'}
                </td>
                <td>
                    <span class="badge bg-light text-dark">v${def.version}</span>
                </td>
                <td>
                    <small class="text-muted">${this.formatDate(def.updated_at)}</small>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" title="Edit" data-action="edit" data-id="${def.id}">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-danger" title="Delete" data-action="delete" data-id="${def.id}">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            `;

            // Add event listeners
            row.querySelector('[data-action="edit"]').addEventListener('click', () => this.showEditModal(def.id));
            row.querySelector('[data-action="delete"]').addEventListener('click', () => this.showDeleteModal(def.id));

            tbody.appendChild(row);
        });
    }

    showCreateModal() {
        this.editingDefinition = null;

        // Reset form
        document.getElementById('definition-form').reset();
        document.getElementById('definition-id').disabled = false;
        document.getElementById('definition-version').value = '1';

        // Update modal title
        document.getElementById('definition-modal-title').textContent = 'Create Definition';
        document.getElementById('save-definition-text').textContent = 'Create';

        // Reset icon preview
        this.updateIconPreview('bi-robot');

        // Set default system prompt placeholder
        const systemPrompt = document.getElementById('definition-system-prompt');
        systemPrompt.value = '';
        systemPrompt.placeholder = 'You are a helpful AI assistant. Be concise but thorough in your responses.';

        // Populate template dropdown
        this.populateTemplateDropdown(null);

        // Populate model dropdown (no selection - use default)
        this.populateModelDropdown(null);

        this.modal.show();
    }

    async showEditModal(id) {
        try {
            const def = await this.request(`/admin/definitions/${id}`);
            this.editingDefinition = def;

            // Populate form
            document.getElementById('definition-id').value = def.id;
            document.getElementById('definition-id').disabled = true; // ID is immutable
            document.getElementById('definition-name').value = def.name;
            document.getElementById('definition-description').value = def.description || '';
            document.getElementById('definition-icon').value = def.icon || 'bi-robot';
            document.getElementById('definition-system-prompt').value = def.system_prompt;
            document.getElementById('definition-is-public').checked = def.is_public;
            document.getElementById('definition-required-roles').value = (def.required_roles || []).join(', ');
            document.getElementById('definition-required-scopes').value = (def.required_scopes || []).join(', ');
            document.getElementById('definition-allowed-users').value = (def.allowed_users || []).join(', ');
            document.getElementById('definition-version').value = def.version;

            // Update icon preview
            this.updateIconPreview(def.icon || 'bi-robot');

            // Populate template dropdown and select current template
            this.populateTemplateDropdown(def.conversation_template_id);

            // Populate model dropdown and select current model
            this.populateModelDropdown(def.model);

            // Update modal title
            document.getElementById('definition-modal-title').textContent = 'Edit Definition';
            document.getElementById('save-definition-text').textContent = 'Save Changes';

            this.modal.show();
        } catch (error) {
            console.error('Failed to load definition:', error);
            showToast('Failed to load definition', 'error');
        }
    }

    showDeleteModal(id) {
        const def = this.definitions.find(d => d.id === id);
        if (!def) return;

        document.getElementById('delete-modal-title').textContent = 'Delete Definition';
        document.getElementById('delete-modal-message').innerHTML = `
            Are you sure you want to delete the definition <strong>${this.escapeHtml(def.name)}</strong>?
        `;
        document.getElementById('delete-modal-warning').textContent = 'This action cannot be undone. Any conversations using this definition will be affected.';
        document.getElementById('delete-item-id').value = id;
        document.getElementById('delete-item-type').value = 'definition';
        document.getElementById('delete-item-version').value = def.version;

        this.deleteModal.show();
    }

    async saveDefinition() {
        const form = document.getElementById('definition-form');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const saveBtn = document.getElementById('save-definition-btn');
        const originalText = saveBtn.innerHTML;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';

        try {
            const formData = new FormData(form);

            // When editing, the ID field is disabled (not included in FormData)
            // Use the stored editingDefinition.id instead
            const id = this.editingDefinition ? this.editingDefinition.id : formData.get('id');

            const data = {
                id: id,
                name: formData.get('name'),
                description: formData.get('description') || '',
                icon: formData.get('icon') || null,
                model: formData.get('model') || null,
                system_prompt: formData.get('system_prompt'),
                conversation_template_id: formData.get('conversation_template_id') || null,
                is_public: document.getElementById('definition-is-public').checked,
                tools: [], // TODO: Implement tools selection
                required_roles: this.parseCommaSeparated(formData.get('required_roles')),
                required_scopes: this.parseCommaSeparated(formData.get('required_scopes')),
                allowed_users: this.parseCommaSeparatedOrNull(formData.get('allowed_users')),
            };

            if (this.editingDefinition) {
                // Update existing
                data.version = parseInt(formData.get('version'), 10);
                await this.request(`/admin/definitions/${data.id}`, {
                    method: 'PUT',
                    body: JSON.stringify(data),
                });
                showToast('Definition updated successfully', 'success');
            } else {
                // Create new
                await this.request('/admin/definitions', {
                    method: 'POST',
                    body: JSON.stringify(data),
                });
                showToast('Definition created successfully', 'success');
            }

            this.modal.hide();
            await this.loadDefinitions();
        } catch (error) {
            console.error('Failed to save definition:', error);
            const message = error.message || 'Failed to save definition';
            showToast(message, 'error');
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalText;
        }
    }

    async confirmDelete() {
        const id = document.getElementById('delete-item-id').value;
        const version = document.getElementById('delete-item-version').value;

        const deleteBtn = document.getElementById('confirm-delete-btn');
        const originalText = deleteBtn.innerHTML;
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Deleting...';

        try {
            await this.request(`/admin/definitions/${id}?version=${version}`, {
                method: 'DELETE',
            });
            showToast('Definition deleted successfully', 'success');
            this.deleteModal.hide();
            await this.loadDefinitions();
        } catch (error) {
            console.error('Failed to delete definition:', error);
            showToast(error.message || 'Failed to delete definition', 'error');
        } finally {
            deleteBtn.disabled = false;
            deleteBtn.innerHTML = originalText;
        }
    }

    updateIconPreview(iconClass) {
        const preview = document.getElementById('icon-preview');
        if (preview) {
            preview.innerHTML = `<i class="bi ${iconClass || 'bi-robot'}"></i>`;
        }
    }

    parseCommaSeparated(value) {
        if (!value || !value.trim()) return [];
        return value
            .split(',')
            .map(s => s.trim())
            .filter(s => s.length > 0);
    }

    parseCommaSeparatedOrNull(value) {
        const parsed = this.parseCommaSeparated(value);
        return parsed.length > 0 ? parsed : null;
    }

    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    /**
     * Load available conversation templates
     */
    async loadTemplates() {
        try {
            this.templates = (await this.request('/admin/templates')) || [];
            console.log(`📋 Loaded ${this.templates.length} templates`);
        } catch (error) {
            console.error('Failed to load templates:', error);
            this.templates = [];
        }
    }

    /**
     * Load available LLM models from config
     */
    async loadModels() {
        try {
            const config = await fetch(`${API_BASE}/config`, { credentials: 'include' }).then(r => r.json());
            this.models = config.available_models || [];
            console.log(`🤖 Loaded ${this.models.length} available models`);
        } catch (error) {
            console.error('Failed to load models:', error);
            this.models = [];
        }
    }

    /**
     * Populate the template dropdown with available templates
     * @param {string|null} selectedId - The ID of the template to select
     */
    populateTemplateDropdown(selectedId) {
        const select = document.getElementById('definition-template');
        if (!select) return;

        // Clear existing options except the first "None" option
        select.innerHTML = '<option value="">None (Reactive)</option>';

        // Add template options
        this.templates.forEach(template => {
            const option = document.createElement('option');
            option.value = template.id;
            option.textContent = template.name;
            if (template.id === selectedId) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    }

    /**
     * Populate the model dropdown with available models
     * @param {string|null} selectedModel - The model ID to select (e.g., "openai:gpt-4o")
     */
    populateModelDropdown(selectedModel) {
        const select = document.getElementById('definition-model');
        if (!select) return;

        // Clear existing options and add default
        select.innerHTML = '<option value="">Use Default</option>';

        // Add model options
        this.models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id; // e.g., "openai:gpt-4o"
            option.textContent = `${model.name} (${model.provider})`;
            if (model.description) {
                option.title = model.description;
            }
            if (model.id === selectedModel) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
