/**
 * Templates Manager
 *
 * Handles CRUD operations for ConversationTemplates in the admin panel.
 */

import { showToast } from '../services/modals.js';
import Sortable from 'sortablejs';
import { createConfigUI, hasConfigUI, generateWidgetTypeOptions } from './widget-config/config-registry.js';
import { downloadTemplateAsYaml, importTemplateFromYaml } from './yaml-export.js';

const API_BASE = '/api';

/**
 * Manages ConversationTemplate CRUD operations
 */
export class TemplatesManager {
    constructor() {
        this.templates = [];
        this.editingTemplate = null;
        this.modal = null;
        this.deleteModal = null;
        this.itemsSortable = null;
        /** @type {Map<string, import('./widget-config/config-base.js').WidgetConfigBase>} */
        this.configInstances = new Map();
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
            console.error('[TemplatesManager] API Error:', {
                url,
                method: config.method || 'GET',
                status: response.status,
                error,
            });

            // Format Pydantic validation errors properly
            let errorMessage = `Request failed: ${response.status}`;
            if (error.detail) {
                if (Array.isArray(error.detail)) {
                    // Pydantic validation errors are an array of {loc, msg, type}
                    errorMessage = error.detail.map(e => `${e.loc?.join(' > ') || 'field'}: ${e.msg}`).join('\n');
                } else if (typeof error.detail === 'string') {
                    errorMessage = error.detail;
                } else {
                    errorMessage = JSON.stringify(error.detail);
                }
            }
            throw new Error(errorMessage);
        }

        if (response.status === 204) {
            return null;
        }

        return response.json();
    }

    async init() {
        console.log('📋 Initializing Templates Manager...');

        // Get modal instances
        this.modal = new bootstrap.Modal(document.getElementById('template-modal'));
        this.deleteModal = new bootstrap.Modal(document.getElementById('delete-modal'));

        // Setup event listeners
        this.setupEventListeners();

        // Initialize tooltips in the modal
        this.initTooltips();

        // Initialize sortable for items
        this.initItemsSortable();

        // Load templates
        await this.loadTemplates();
    }

    initTooltips() {
        // Initialize tooltips when modal is shown
        const modalEl = document.getElementById('template-modal');
        modalEl?.addEventListener('shown.bs.modal', () => {
            const tooltipTriggers = modalEl.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltipTriggers.forEach(el => {
                new bootstrap.Tooltip(el, {
                    trigger: 'hover',
                    delay: { show: 200, hide: 0 },
                });
            });
        });

        // Dispose tooltips when modal is hidden
        modalEl?.addEventListener('hidden.bs.modal', () => {
            const tooltipTriggers = modalEl.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltipTriggers.forEach(el => {
                const tooltip = bootstrap.Tooltip.getInstance(el);
                tooltip?.dispose();
            });
        });
    }

    initItemsSortable() {
        const container = document.getElementById('items-container');
        if (!container) return;

        this.itemsSortable = new Sortable(container, {
            handle: '.drag-handle',
            animation: 150,
            ghostClass: 'bg-light',
            onEnd: () => {
                this.reindexItems();
                this.updateItemCountBadge();
            },
        });
    }

    updateItemCountBadge() {
        const count = document.querySelectorAll('#items-container .item-card').length;
        const badge = document.getElementById('items-count-badge');
        if (badge) {
            badge.textContent = count.toString();
        }

        // Show/hide empty state
        const emptyState = document.getElementById('items-empty-state');
        if (emptyState) {
            emptyState.style.display = count === 0 ? 'block' : 'none';
        }
    }

    setupEventListeners() {
        // Create buttons
        document.getElementById('create-template-btn')?.addEventListener('click', () => this.showCreateModal());
        document.getElementById('create-template-btn-empty')?.addEventListener('click', () => this.showCreateModal());

        // Import button - trigger hidden file input
        document.getElementById('import-template-btn')?.addEventListener('click', () => {
            document.getElementById('import-template-file')?.click();
        });

        // Import file input - handle file selection
        document.getElementById('import-template-file')?.addEventListener('change', e => this.handleImportFile(e));

        // Save button
        document.getElementById('save-template-btn')?.addEventListener('click', () => this.saveTemplate());

        // Delete confirmation button (shared modal)
        document.getElementById('confirm-delete-btn')?.addEventListener('click', () => this.confirmDelete());

        // ID field - disable after creation
        const idInput = document.getElementById('template-id');
        this.modal?._element?.addEventListener('hidden.bs.modal', () => {
            if (idInput) idInput.disabled = false;
            this.editingTemplate = null;
        });

        // Filter buttons
        document.getElementById('filter-all')?.addEventListener('click', () => this.filterTemplates('all'));
        document.getElementById('filter-proactive')?.addEventListener('click', () => this.filterTemplates('proactive'));
        document.getElementById('filter-assessments')?.addEventListener('click', () => this.filterTemplates('assessments'));

        // Add item button
        document.getElementById('add-item-btn')?.addEventListener('click', () => this.addItem());

        // Mutual exclusivity: shuffle_items and allow_backward_navigation
        this.setupMutualExclusivity();
    }

    /**
     * Setup mutual exclusivity between shuffle_items and allow_backward_navigation
     * These options cannot both be enabled simultaneously because:
     * - Shuffle randomizes item order, making "previous" item undefined
     * - Backward navigation requires a deterministic item sequence
     */
    setupMutualExclusivity() {
        const shuffleCheckbox = document.getElementById('template-shuffle-items');
        const backwardCheckbox = document.getElementById('template-allow-backward');

        if (!shuffleCheckbox || !backwardCheckbox) return;

        // When shuffle is enabled, disable backward navigation
        shuffleCheckbox.addEventListener('change', () => {
            if (shuffleCheckbox.checked) {
                backwardCheckbox.checked = false;
                backwardCheckbox.disabled = true;
                backwardCheckbox.parentElement?.classList.add('text-muted');
                showToast('Backward navigation disabled: incompatible with shuffled items', 'info');
            } else {
                backwardCheckbox.disabled = false;
                backwardCheckbox.parentElement?.classList.remove('text-muted');
            }
        });

        // When backward navigation is enabled, disable shuffle
        backwardCheckbox.addEventListener('change', () => {
            if (backwardCheckbox.checked) {
                shuffleCheckbox.checked = false;
                shuffleCheckbox.disabled = true;
                shuffleCheckbox.parentElement?.classList.add('text-muted');
                showToast('Shuffle disabled: incompatible with backward navigation', 'info');
            } else {
                shuffleCheckbox.disabled = false;
                shuffleCheckbox.parentElement?.classList.remove('text-muted');
            }
        });
    }

    /**
     * Apply mutual exclusivity state based on current checkbox values
     * Called when loading template data into the form
     */
    applyMutualExclusivityState() {
        const shuffleCheckbox = document.getElementById('template-shuffle-items');
        const backwardCheckbox = document.getElementById('template-allow-backward');

        if (!shuffleCheckbox || !backwardCheckbox) return;

        // Reset both to enabled state first
        shuffleCheckbox.disabled = false;
        backwardCheckbox.disabled = false;
        shuffleCheckbox.parentElement?.classList.remove('text-muted');
        backwardCheckbox.parentElement?.classList.remove('text-muted');

        // Then apply constraints based on current values
        if (shuffleCheckbox.checked) {
            backwardCheckbox.disabled = true;
            backwardCheckbox.parentElement?.classList.add('text-muted');
        } else if (backwardCheckbox.checked) {
            shuffleCheckbox.disabled = true;
            shuffleCheckbox.parentElement?.classList.add('text-muted');
        }
    }

    async loadTemplates() {
        const loading = document.getElementById('templates-loading');
        const empty = document.getElementById('templates-empty');
        const tableContainer = document.getElementById('templates-table-container');

        try {
            loading.style.display = 'block';
            empty.style.display = 'none';
            tableContainer.style.display = 'none';

            this.templates = (await this.request('/admin/templates')) || [];

            loading.style.display = 'none';

            if (this.templates.length === 0) {
                empty.style.display = 'block';
            } else {
                tableContainer.style.display = 'block';
                this.renderTemplates();
            }
        } catch (error) {
            console.error('Failed to load templates:', error);
            loading.style.display = 'none';
            showToast('Failed to load templates', 'error');
        }
    }

    renderTemplates(filter = 'all') {
        const tbody = document.getElementById('templates-table-body');
        tbody.innerHTML = '';

        let filtered = this.templates;
        if (filter === 'proactive') {
            filtered = this.templates.filter(t => t.agent_starts_first);
        } else if (filter === 'assessments') {
            filtered = this.templates.filter(t => t.is_assessment);
        }

        filtered.forEach(template => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <div class="fw-medium">${this.escapeHtml(template.name)}</div>
                    <small class="text-muted font-monospace">${this.escapeHtml(template.id)}</small>
                </td>
                <td>
                    <span class="badge ${template.agent_starts_first ? 'bg-info' : 'bg-secondary'}">
                        ${template.agent_starts_first ? 'Proactive' : 'Reactive'}
                    </span>
                </td>
                <td>
                    <span class="badge ${template.is_assessment ? 'bg-warning text-dark' : 'bg-light text-dark'}">
                        ${template.is_assessment ? 'Assessment' : 'Conversation'}
                    </span>
                </td>
                <td>
                    <span class="badge bg-light text-dark">${template.item_count || 0} items</span>
                </td>
                <td>
                    <span class="badge bg-light text-dark">v${template.version}</span>
                </td>
                <td>
                    <small class="text-muted">${this.formatDate(template.updated_at)}</small>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" title="Edit" data-action="edit" data-id="${template.id}">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-info" title="Duplicate" data-action="duplicate" data-id="${template.id}">
                            <i class="bi bi-copy"></i>
                        </button>
                        <button class="btn btn-outline-secondary" title="Export YAML" data-action="export" data-id="${template.id}">
                            <i class="bi bi-download"></i>
                        </button>
                        <button class="btn btn-outline-danger" title="Delete" data-action="delete" data-id="${template.id}">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            `;

            // Add row click to open edit modal
            row.style.cursor = 'pointer';
            row.addEventListener('click', e => {
                // Don't trigger if clicking on buttons or their icons
                if (e.target.closest('button, a, input, select')) return;
                this.showEditModal(template.id);
            });

            // Add button event listeners (stopPropagation to prevent row click)
            row.querySelector('[data-action="edit"]').addEventListener('click', e => {
                e.stopPropagation();
                this.showEditModal(template.id);
            });
            row.querySelector('[data-action="duplicate"]').addEventListener('click', e => {
                e.stopPropagation();
                this.duplicateTemplate(template.id);
            });
            row.querySelector('[data-action="export"]').addEventListener('click', e => {
                e.stopPropagation();
                this.exportTemplate(template.id);
            });
            row.querySelector('[data-action="delete"]').addEventListener('click', e => {
                e.stopPropagation();
                this.showDeleteModal(template.id);
            });

            tbody.appendChild(row);
        });

        // Update filter button states
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === filter);
        });
    }

    filterTemplates(filter) {
        this.renderTemplates(filter);
    }

    showCreateModal() {
        this.editingTemplate = null;

        // Reset form
        document.getElementById('template-form').reset();
        document.getElementById('template-id').disabled = false;
        document.getElementById('template-version').value = '1';

        // Clear items and show empty state
        const container = document.getElementById('items-container');
        container.innerHTML = `
            <div class="text-center py-5 text-muted" id="items-empty-state">
                <i class="bi bi-inbox display-4"></i>
                <p class="mt-2 mb-0">No items yet. Click "Add Item" to add conversation steps.</p>
            </div>
        `;
        this.updateItemCountBadge();

        // Switch to Basic Settings tab
        const basicTab = document.getElementById('basic-tab');
        if (basicTab) {
            bootstrap.Tab.getOrCreateInstance(basicTab).show();
        }

        // Update modal title
        document.getElementById('template-modal-title').textContent = 'Create Template';
        document.getElementById('save-template-text').textContent = 'Create';

        // Apply mutual exclusivity state (both should be enabled for new templates)
        this.applyMutualExclusivityState();

        this.modal.show();
    }

    async showEditModal(id) {
        try {
            const template = await this.request(`/admin/templates/${id}`);
            this.editingTemplate = template;

            // Populate form
            document.getElementById('template-id').value = template.id;
            document.getElementById('template-id').disabled = true; // ID is immutable
            document.getElementById('template-name').value = template.name;
            document.getElementById('template-description').value = template.description || '';
            document.getElementById('template-version').value = template.version;

            // Flow configuration
            document.getElementById('template-agent-starts-first').checked = template.agent_starts_first;
            document.getElementById('template-allow-navigation').checked = template.allow_navigation;
            document.getElementById('template-allow-backward').checked = template.allow_backward_navigation;
            document.getElementById('template-enable-chat-initially').checked = template.enable_chat_input_initially;
            document.getElementById('template-continue-after-completion').checked = template.continue_after_completion || false;

            // Timing
            document.getElementById('template-max-duration').value = template.max_duration_seconds || '';

            // Display options
            document.getElementById('template-shuffle-items').checked = template.shuffle_items;
            document.getElementById('template-show-progress').checked = template.display_progress_indicator;
            document.getElementById('template-show-final-score').checked = template.display_final_score_report;
            document.getElementById('template-include-feedback').checked = template.include_feedback;

            // Messages
            document.getElementById('template-intro-message').value = template.introduction_message || '';
            document.getElementById('template-completion-message').value = template.completion_message || '';

            // Scoring
            document.getElementById('template-passing-score').value = template.passing_score_percent || '';

            // Render items
            this.renderItems(template.items || []);
            this.updateItemCountBadge();

            // Switch to Basic Settings tab
            const basicTab = document.getElementById('basic-tab');
            if (basicTab) {
                bootstrap.Tab.getOrCreateInstance(basicTab).show();
            }

            // Update modal title
            document.getElementById('template-modal-title').textContent = 'Edit Template';
            document.getElementById('save-template-text').textContent = 'Save Changes';

            // Apply mutual exclusivity state based on loaded values
            this.applyMutualExclusivityState();

            this.modal.show();
        } catch (error) {
            console.error('Failed to load template:', error);
            showToast('Failed to load template', 'error');
        }
    }

    async duplicateTemplate(id) {
        try {
            const template = await this.request(`/admin/templates/${id}`);
            this.editingTemplate = null;

            // Populate form with new ID
            document.getElementById('template-id').value = `${template.id}-copy`;
            document.getElementById('template-id').disabled = false;
            document.getElementById('template-name').value = `${template.name} (Copy)`;
            document.getElementById('template-description').value = template.description || '';
            document.getElementById('template-version').value = '1';

            // Copy all other fields...
            document.getElementById('template-agent-starts-first').checked = template.agent_starts_first;
            document.getElementById('template-allow-navigation').checked = template.allow_navigation;
            document.getElementById('template-allow-backward').checked = template.allow_backward_navigation;
            document.getElementById('template-enable-chat-initially').checked = template.enable_chat_input_initially;
            document.getElementById('template-continue-after-completion').checked = template.continue_after_completion || false;
            document.getElementById('template-max-duration').value = template.max_duration_seconds || '';
            document.getElementById('template-shuffle-items').checked = template.shuffle_items;
            document.getElementById('template-show-progress').checked = template.display_progress_indicator;
            document.getElementById('template-show-final-score').checked = template.display_final_score_report;
            document.getElementById('template-include-feedback').checked = template.include_feedback;
            document.getElementById('template-intro-message').value = template.introduction_message || '';
            document.getElementById('template-completion-message').value = template.completion_message || '';
            document.getElementById('template-passing-score').value = template.passing_score_percent || '';

            // Render items
            this.renderItems(template.items || []);
            this.updateItemCountBadge();

            // Switch to Basic Settings tab
            const basicTab = document.getElementById('basic-tab');
            if (basicTab) {
                bootstrap.Tab.getOrCreateInstance(basicTab).show();
            }

            // Update modal title
            document.getElementById('template-modal-title').textContent = 'Duplicate Template';
            document.getElementById('save-template-text').textContent = 'Create Copy';

            // Apply mutual exclusivity state based on copied values
            this.applyMutualExclusivityState();

            this.modal.show();
        } catch (error) {
            console.error('Failed to duplicate template:', error);
            showToast('Failed to duplicate template', 'error');
        }
    }

    showDeleteModal(id) {
        const template = this.templates.find(t => t.id === id);
        if (!template) return;

        document.getElementById('delete-modal-title').textContent = 'Delete Template';
        document.getElementById('delete-modal-message').innerHTML = `
            Are you sure you want to delete the template <strong>${this.escapeHtml(template.name)}</strong>?
        `;
        document.getElementById('delete-modal-warning').textContent = 'This action cannot be undone. Any agents using this template will need to be updated.';
        document.getElementById('delete-item-id').value = id;
        document.getElementById('delete-item-type').value = 'template';
        document.getElementById('delete-item-version').value = template.version;

        this.deleteModal.show();
    }

    /**
     * Export a template as YAML file
     * @param {string} id - The template ID to export
     */
    async exportTemplate(id) {
        try {
            // Download YAML from backend (generates seeder-compatible format)
            await downloadTemplateAsYaml(id);
            showToast(`Exported template as YAML`, 'success');
        } catch (error) {
            console.error('Failed to export template:', error);
            showToast('Failed to export template', 'error');
        }
    }

    /**
     * Handle import file selection
     * @param {Event} e - The change event from file input
     */
    async handleImportFile(e) {
        const file = e.target.files?.[0];
        if (!file) return;

        // Reset file input so same file can be re-selected
        e.target.value = '';

        try {
            const result = await importTemplateFromYaml(file);
            showToast(`Imported template: ${result.name}`, 'success');
            // Reload templates to show the new one
            await this.loadTemplates();
        } catch (error) {
            console.error('Failed to import template:', error);
            showToast(`Import failed: ${error.message}`, 'error');
        }
    }

    renderItems(items) {
        const container = document.getElementById('items-container');
        container.innerHTML = '';

        if (items.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5 text-muted" id="items-empty-state">
                    <i class="bi bi-inbox display-4"></i>
                    <p class="mt-2 mb-0">No items yet. Click "Add Item" to add conversation steps.</p>
                </div>
            `;
            return;
        }

        items.forEach((item, index) => {
            const itemEl = this.createItemElement(item, index);
            container.appendChild(itemEl);
        });
    }

    createItemElement(item, index) {
        const div = document.createElement('div');
        div.className = 'card mb-2 item-card';
        div.dataset.itemIndex = index;
        div.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center py-2" style="cursor: pointer;">
                <div class="d-flex align-items-center">
                    <i class="bi bi-grip-vertical text-muted me-2 drag-handle" style="cursor: grab;" title="Drag to reorder"></i>
                    <span class="badge bg-secondary me-2 item-order-badge">#${index + 1}</span>
                    <input type="text" class="form-control form-control-sm item-id"
                           value="${this.escapeHtml(item.id || `item-${index + 1}`)}"
                           placeholder="item-id" style="width: 120px;">
                    <input type="text" class="form-control form-control-sm ms-2 item-title"
                           value="${this.escapeHtml(item.title || '')}"
                           placeholder="Title" style="width: 150px;">
                </div>
                <div class="btn-group btn-group-sm">
                    <button type="button" class="btn btn-outline-secondary duplicate-item-btn" title="Duplicate Item">
                        <i class="bi bi-copy"></i>
                    </button>
                    <button type="button" class="btn btn-outline-secondary toggle-item-btn" title="Expand/Collapse">
                        <i class="bi bi-chevron-down"></i>
                    </button>
                    <button type="button" class="btn btn-outline-danger remove-item-btn" title="Remove Item">
                        <i class="bi bi-x"></i>
                    </button>
                </div>
            </div>
            <div class="card-body item-details" style="display: none;">
                <div class="row g-2 mb-2">
                    <div class="col-6 col-md-4">
                        <div class="form-check form-switch">
                            <input class="form-check-input item-enable-chat" type="checkbox" id="item-enable-chat-${index}"
                                   ${item.enable_chat_input ? 'checked' : ''}>
                            <label class="form-check-label small" for="item-enable-chat-${index}">
                                Enable Chat Input
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="If enabled, users can type messages during this item. Disable to force widget-only input."></i>
                            </label>
                        </div>
                    </div>
                    <div class="col-6 col-md-4">
                        <div class="form-check form-switch">
                            <input class="form-check-input item-provide-feedback" type="checkbox" id="item-provide-feedback-${index}"
                                   ${item.provide_feedback ? 'checked' : ''}>
                            <label class="form-check-label small" for="item-provide-feedback-${index}">
                                Provide Feedback
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="If enabled, the agent will provide feedback after the user responds to this item."></i>
                            </label>
                        </div>
                    </div>
                    <div class="col-6 col-md-4">
                        <div class="form-check form-switch">
                            <input class="form-check-input item-reveal-answer" type="checkbox" id="item-reveal-answer-${index}"
                                   ${item.reveal_correct_answer ? 'checked' : ''}>
                            <label class="form-check-label small" for="item-reveal-answer-${index}">
                                Reveal Answer
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="If enabled and a correct answer is defined, reveal it after the user responds."></i>
                            </label>
                        </div>
                    </div>
                    <div class="col-6 col-md-4">
                        <div class="form-check form-switch">
                            <input class="form-check-input item-show-expiration-warning" type="checkbox" id="item-show-expiration-warning-${index}"
                                   ${item.show_expiration_warning ? 'checked' : ''}>
                            <label class="form-check-label small" for="item-show-expiration-warning-${index}">
                                Show Expiration Warning
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="If enabled and time limit is set, show a warning before time expires."></i>
                            </label>
                        </div>
                    </div>
                </div>
                <div class="row g-2">
                    <div class="col-6 col-md-4">
                        <label class="form-label small mb-1">
                            Time Limit (sec)
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Maximum time allowed for this item in seconds. Leave empty for no time limit."></i>
                        </label>
                        <input type="number" class="form-control form-control-sm item-time-limit"
                               value="${item.time_limit_seconds || ''}" placeholder="Optional">
                    </div>
                    <div class="col-6 col-md-4">
                        <label class="form-label small mb-1">
                            Warning Time (sec)
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Seconds before expiration to show warning. Only applies if time limit is set."></i>
                        </label>
                        <input type="number" class="form-control form-control-sm item-expiration-warning-seconds"
                               value="${item.expiration_warning_seconds || 30}" placeholder="30">
                    </div>
                    <div class="col-12 col-md-4">
                        <label class="form-label small mb-1">
                            Warning Message
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Message displayed when the warning timer is triggered."></i>
                        </label>
                        <input type="text" class="form-control form-control-sm item-warning-message"
                               value="${this.escapeHtml(item.warning_message || '')}" placeholder="Time is running out...">
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-6 col-md-4">
                        <div class="form-check form-switch">
                            <input class="form-check-input item-require-confirmation" type="checkbox" id="item-require-confirmation-${index}"
                                   ${item.require_user_confirmation ? 'checked' : ''}>
                            <label class="form-check-label small" for="item-require-confirmation-${index}">
                                Require User Confirmation
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="If enabled, users must click a confirmation button before advancing to the next item."></i>
                            </label>
                        </div>
                    </div>
                    <div class="col-6 col-md-4">
                        <label class="form-label small mb-1">
                            Confirmation Button Text
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Text displayed on the confirmation button. Only used if 'Require User Confirmation' is enabled."></i>
                        </label>
                        <input type="text" class="form-control form-control-sm item-confirmation-text"
                               value="${this.escapeHtml(item.confirmation_button_text || 'Submit')}" placeholder="Submit">
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-12">
                        <label class="form-label small mb-1">
                            LLM Instructions
                            <i class="bi bi-info-circle text-primary ms-1" data-bs-toggle="tooltip" data-bs-html="true"
                               title="<strong>Admin-defined prompt for LLM content generation.</strong><br><br>Supports Jinja-style variables:<br>• <code>{{ user_id }}</code> - User's ID<br>• <code>{{ user_name }}</code> - User's name<br>• <code>{{ conversation_id }}</code> - Conversation ID<br>• <code>{{ agent_name }}</code> - Agent's name<br>• <code>{{ current_item }}</code> - Current item # (1-based)<br>• <code>{{ total_items }}</code> - Total items<br>• <code>{{ timestamp }}</code> - Current timestamp<br><br>These are replaced before sending to the LLM. The LLM may generate additional dynamic content like math problems."></i>
                        </label>
                        <textarea class="form-control form-control-sm item-instructions" rows="3"
                               placeholder="Optional: Instructions for the LLM when generating templated content. Use {{ variable }} for dynamic values.">${this.escapeHtml(
                                   item.instructions || ''
                               )}</textarea>
                    </div>
                </div>
                <hr class="my-2">
                <div class="contents-container">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <small class="text-muted">Contents</small>
                        <button type="button" class="btn btn-outline-primary btn-sm add-content-btn">
                            <i class="bi bi-plus"></i> Add Content
                        </button>
                    </div>
                    <div class="contents-list">
                        ${this.renderContents(item.contents || [])}
                    </div>
                </div>
            </div>
        `;

        // Toggle expand/collapse
        const toggleDetails = () => {
            const details = div.querySelector('.item-details');
            const icon = div.querySelector('.toggle-item-btn i');
            if (details.style.display === 'none') {
                details.style.display = 'block';
                icon.className = 'bi bi-chevron-up';
            } else {
                details.style.display = 'none';
                icon.className = 'bi bi-chevron-down';
            }
        };

        div.querySelector('.toggle-item-btn').addEventListener('click', toggleDetails);

        // Allow clicking on header to toggle, except on interactive elements
        div.querySelector('.card-header').addEventListener('click', e => {
            // Don't toggle if clicking on interactive elements
            const target = e.target;
            const isInteractive = target.closest('.drag-handle') || target.closest('input') || target.closest('button') || target.closest('.btn');
            if (!isInteractive) {
                toggleDetails();
            }
        });

        // Remove item
        div.querySelector('.remove-item-btn').addEventListener('click', () => {
            div.remove();
            this.reindexItems();
            this.updateItemCountBadge();
        });

        // Duplicate item
        div.querySelector('.duplicate-item-btn').addEventListener('click', () => {
            this.duplicateItem(div);
        });

        // Add content
        div.querySelector('.add-content-btn').addEventListener('click', () => {
            this.addContent(div);
        });

        // Setup event listeners for existing content cards
        div.querySelectorAll('.content-card').forEach(contentEl => {
            this.setupContentEventListeners(contentEl);
        });

        // Hydrate any widget config placeholders (for registry-based configs)
        this.hydrateWidgetConfigPlaceholders(div);

        return div;
    }

    renderContents(contents) {
        if (!contents.length) {
            return '<p class="text-muted small mb-0">No contents. Click "Add Content" to add.</p>';
        }

        return contents.map((content, idx) => this.renderContentCard(content, idx)).join('');
    }

    renderContentCard(content, idx) {
        const widgetType = content.widget_type || 'message';
        const options = content.options || [];
        const widgetConfig = content.widget_config || {};

        return `
            <div class="card card-body p-2 mb-2 content-card" data-content-index="${idx}">
                <!-- Row 1: ID, Widget Type, Remove -->
                <div class="row g-2 align-items-center mb-2">
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Content ID
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Unique identifier for this content within the item."></i>
                        </label>
                        <input type="text" class="form-control form-control-sm content-id"
                               value="${this.escapeHtml(content.id || `content-${idx + 1}`)}"
                               placeholder="content-id">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Widget Type
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Type of UI widget for this content."></i>
                        </label>
                        <select class="form-select form-select-sm content-widget-type">
                            ${generateWidgetTypeOptions(widgetType)}
                        </select>
                    </div>
                    <div class="col-md-4">
                        <div class="form-check form-switch mt-3">
                            <input class="form-check-input content-is-templated" type="checkbox"
                                   ${content.is_templated ? 'checked' : ''}>
                            <label class="form-check-label small">
                                LLM Generated (Templated)
                                <i class="bi bi-info-circle text-primary ms-1" data-bs-toggle="tooltip" data-bs-html="true"
                                   title="<strong>When enabled:</strong><br>The LLM generates this content dynamically using the item's LLM Instructions.<br><br><strong>Available Variables (Jinja-style):</strong><br>• <code>{{ user_id }}</code><br>• <code>{{ user_name }}</code><br>• <code>{{ conversation_id }}</code><br>• <code>{{ agent_name }}</code><br>• <code>{{ current_item }}</code><br>• <code>{{ total_items }}</code><br>• <code>{{ timestamp }}</code><br><br>Variables are replaced <em>before</em> sending to LLM. The LLM can generate additional dynamic content (e.g., math problems like <code>{{ a }} + {{ b }}</code> where the LLM defines a=5, b=3)."></i>
                            </label>
                        </div>
                    </div>
                    <div class="col-md-2 text-end">
                        <button type="button" class="btn btn-outline-danger btn-sm remove-content-btn mt-3">
                            <i class="bi bi-x"></i> Remove
                        </button>
                    </div>
                </div>

                <!-- Row 2: Stem -->
                <div class="row g-2 mb-2">
                    <div class="col-12">
                        <label class="form-label small mb-0">
                            Stem (Question/Message)
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="The main text content or question to display. For templated content, this can include variables."></i>
                        </label>
                        <textarea class="form-control form-control-sm content-stem" rows="2"
                               placeholder="Question or message text">${this.escapeHtml(content.stem || '')}</textarea>
                    </div>
                </div>

                <!-- Row 2.5: Content Settings (Required, Skippable) -->
                <div class="row g-2 mb-2">
                    <div class="col-md-3">
                        <div class="form-check form-switch">
                            <input class="form-check-input content-required" type="checkbox" id="content-required-${idx}"
                                   ${content.required !== false ? 'checked' : ''}>
                            <label class="form-check-label small" for="content-required-${idx}">
                                Required
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip" data-bs-html="true"
                                   title="<strong>Required:</strong> User must provide a response before proceeding.<br><br><em>Mutually exclusive with Skippable.</em>"></i>
                            </label>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-check form-switch">
                            <input class="form-check-input content-skippable" type="checkbox" id="content-skippable-${idx}"
                                   ${content.skippable ? 'checked' : ''}>
                            <label class="form-check-label small" for="content-skippable-${idx}">
                                Skippable
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip" data-bs-html="true"
                                   title="<strong>Skippable:</strong> User can dismiss/skip this widget.<br><br><em>Mutually exclusive with Required.</em><br><br><strong>Both OFF:</strong> Widget is optional but stays visible (no dismiss button)."></i>
                            </label>
                        </div>
                    </div>
                </div>

                <!-- Row 3: Widget-specific configuration -->
                ${this.renderWidgetConfig(widgetType, options, widgetConfig, content)}
            </div>
        `;
    }

    renderWidgetConfig(widgetType, options, widgetConfig, content) {
        // Generate unique ID for this content's toggles
        const uid = content.id || `content-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        // Check if we have a registry-based config for this widget type
        if (hasConfigUI(widgetType)) {
            // Return a placeholder that will be hydrated after DOM insertion
            return `<div class="widget-config-placeholder" data-widget-type="${widgetType}" data-content-uid="${uid}"
                        data-widget-config='${JSON.stringify(widgetConfig).replace(/'/g, '&#39;')}'
                        data-content='${JSON.stringify(content).replace(/'/g, '&#39;')}'
                        data-options='${JSON.stringify(options).replace(/'/g, '&#39;')}'>
                        <div class="d-flex justify-content-center py-3">
                            <div class="spinner-border spinner-border-sm text-muted" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                    </div>`;
        }

        // Fallback for widgets without registry-based config
        switch (widgetType) {
            case 'multiple_choice':
                return `
                    <div class="widget-config widget-config-multiple-choice">
                        <div class="row g-2">
                            <div class="col-12">
                                <label class="form-label small mb-0">
                                    Options (one per line)
                                    <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                       title="Enter each option on a separate line. These will be displayed as choices."></i>
                                </label>
                                <textarea class="form-control form-control-sm content-options" rows="4"
                                    placeholder="Option 1&#10;Option 2&#10;Option 3">${this.escapeHtml(options.join('\n'))}</textarea>
                            </div>
                        </div>
                        <div class="row g-2 mt-1">
                            <div class="col-md-4">
                                <div class="form-check form-switch">
                                    <input class="form-check-input content-shuffle-options" type="checkbox" id="shuffle-options-${uid}"
                                           ${widgetConfig.shuffle_options ? 'checked' : ''}>
                                    <label class="form-check-label small" for="shuffle-options-${uid}">
                                        Shuffle Options
                                        <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                           title="If enabled, options will be presented in random order."></i>
                                    </label>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="form-check form-switch">
                                    <input class="form-check-input content-allow-multiple" type="checkbox" id="allow-multiple-${uid}"
                                           ${widgetConfig.allow_multiple ? 'checked' : ''}>
                                    <label class="form-check-label small" for="allow-multiple-${uid}">
                                        Allow Multiple
                                        <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                           title="If enabled, users can select multiple options."></i>
                                    </label>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small mb-0">
                                    Correct Answer
                                    <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                       title="The correct answer for scoring and feedback. Must match an option exactly."></i>
                                </label>
                                <input type="text" class="form-control form-control-sm content-correct-answer"
                                       value="${this.escapeHtml(content.correct_answer || '')}"
                                       placeholder="Optional">
                            </div>
                        </div>
                    </div>
                `;

            case 'slider':
                return `
                    <div class="widget-config widget-config-slider">
                        <div class="row g-2">
                            <div class="col-md-3">
                                <label class="form-label small mb-0">
                                    Min Value
                                    <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                       title="Minimum value on the slider scale."></i>
                                </label>
                                <input type="number" class="form-control form-control-sm content-slider-min"
                                       value="${widgetConfig.min ?? 0}" placeholder="0">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label small mb-0">
                                    Max Value
                                    <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                       title="Maximum value on the slider scale."></i>
                                </label>
                                <input type="number" class="form-control form-control-sm content-slider-max"
                                       value="${widgetConfig.max ?? 100}" placeholder="100">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label small mb-0">
                                    Step
                                    <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                       title="Increment step when moving the slider."></i>
                                </label>
                                <input type="number" class="form-control form-control-sm content-slider-step"
                                       value="${widgetConfig.step ?? 1}" placeholder="1">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label small mb-0">
                                    Initial Value
                                    <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                       title="Pre-selected value when slider first appears."></i>
                                </label>
                                <input type="number" class="form-control form-control-sm content-initial-value"
                                       value="${content.initial_value ?? ''}" placeholder="Optional">
                            </div>
                        </div>
                        <div class="row g-2 mt-1">
                            <div class="col-md-6">
                                <label class="form-label small mb-0">
                                    Min Label
                                    <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                       title="Label displayed at the minimum end of the slider."></i>
                                </label>
                                <input type="text" class="form-control form-control-sm content-slider-min-label"
                                       value="${this.escapeHtml(widgetConfig.min_label || '')}" placeholder="e.g., Not at all">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label small mb-0">
                                    Max Label
                                    <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                       title="Label displayed at the maximum end of the slider."></i>
                                </label>
                                <input type="text" class="form-control form-control-sm content-slider-max-label"
                                       value="${this.escapeHtml(widgetConfig.max_label || '')}" placeholder="e.g., Very much">
                            </div>
                        </div>
                    </div>
                `;

            case 'free_text':
                return `
                    <div class="widget-config widget-config-free-text">
                        <div class="row g-2">
                            <div class="col-md-4">
                                <label class="form-label small mb-0">
                                    Placeholder
                                    <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                       title="Placeholder text shown in the input field."></i>
                                </label>
                                <input type="text" class="form-control form-control-sm content-placeholder"
                                       value="${this.escapeHtml(widgetConfig.placeholder || '')}"
                                       placeholder="Enter placeholder text...">
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small mb-0">
                                    Min Length
                                    <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                       title="Minimum required character count."></i>
                                </label>
                                <input type="number" class="form-control form-control-sm content-min-length"
                                       value="${widgetConfig.min_length ?? ''}" placeholder="0">
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small mb-0">
                                    Max Length
                                    <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                       title="Maximum allowed character count."></i>
                                </label>
                                <input type="number" class="form-control form-control-sm content-max-length"
                                       value="${widgetConfig.max_length ?? ''}" placeholder="None">
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small mb-0">
                                    Rows
                                    <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                       title="Number of visible text rows (height)."></i>
                                </label>
                                <input type="number" class="form-control form-control-sm content-rows"
                                       value="${widgetConfig.rows ?? 3}" placeholder="3">
                            </div>
                            <div class="col-md-2">
                                <div class="form-check form-switch mt-4">
                                    <input class="form-check-input content-multiline" type="checkbox" id="multiline-${uid}"
                                           ${widgetConfig.multiline !== false ? 'checked' : ''}>
                                    <label class="form-check-label small" for="multiline-${uid}">
                                        Multiline
                                        <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                           title="If enabled, shows a textarea for multi-line input."></i>
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                `;

            case 'message':
            default:
                return `
                    <div class="widget-config widget-config-message">
                        <p class="text-muted small mb-0"><i class="bi bi-info-circle"></i> Message widgets display text only (no user input).</p>
                    </div>
                `;
        }
    }

    addItem() {
        const container = document.getElementById('items-container');

        // Hide empty state if present
        const emptyState = container.querySelector('.items-empty-state');
        if (emptyState) emptyState.style.display = 'none';

        const index = container.querySelectorAll('.item-card').length;
        const newItem = {
            id: `item-${index + 1}`,
            order: index + 1,
            title: '',
            enable_chat_input: true,
            provide_feedback: false,
            reveal_correct_answer: false,
            instructions: '',
            require_user_confirmation: false,
            confirmation_button_text: 'Submit',
            contents: [],
        };
        const itemEl = this.createItemElement(newItem, index);
        container.appendChild(itemEl);

        // Update badge count
        this.updateItemCountBadge();
    }

    addContent(itemEl) {
        const contentsList = itemEl.querySelector('.contents-list');
        const existingContents = contentsList.querySelectorAll('.content-card');
        const idx = existingContents.length;

        // Remove "no contents" message if present
        const emptyMsg = contentsList.querySelector('p.text-muted');
        if (emptyMsg) emptyMsg.remove();

        // Create a default content object
        const newContentData = {
            id: `content-${idx + 1}`,
            order: idx + 1,
            widget_type: 'message',
            stem: '',
            is_templated: false,
            options: [],
            widget_config: {},
        };

        const contentHtml = this.renderContentCard(newContentData, idx);
        contentsList.insertAdjacentHTML('beforeend', contentHtml);

        // Add event listeners
        const newContent = contentsList.lastElementChild;
        this.setupContentEventListeners(newContent);

        // Hydrate any widget config placeholders
        this.hydrateWidgetConfigPlaceholders(newContent);
    }

    setupContentEventListeners(contentEl) {
        // Remove button
        contentEl.querySelector('.remove-content-btn').addEventListener('click', () => {
            // Clean up config instance
            const placeholder = contentEl.querySelector('.widget-config-placeholder, .widget-config');
            if (placeholder) {
                const uid = placeholder.dataset.contentUid;
                if (uid) this.configInstances.delete(uid);
            }
            contentEl.remove();
        });

        // Widget type change - re-render widget config
        const widgetTypeSelect = contentEl.querySelector('.content-widget-type');
        widgetTypeSelect.addEventListener('change', e => {
            this.updateWidgetConfig(contentEl, e.target.value);
        });

        // Required/Skippable mutual exclusivity
        // If required is checked, skippable must be unchecked (and vice versa)
        const requiredCheckbox = contentEl.querySelector('.content-required');
        const skippableCheckbox = contentEl.querySelector('.content-skippable');

        if (requiredCheckbox && skippableCheckbox) {
            requiredCheckbox.addEventListener('change', () => {
                if (requiredCheckbox.checked) {
                    skippableCheckbox.checked = false;
                }
            });

            skippableCheckbox.addEventListener('change', () => {
                if (skippableCheckbox.checked) {
                    requiredCheckbox.checked = false;
                }
            });
        }
    }

    updateWidgetConfig(contentEl, widgetType) {
        // Remove existing widget config and clean up instance
        const existingConfig = contentEl.querySelector('.widget-config, .widget-config-placeholder');
        if (existingConfig) {
            const uid = existingConfig.dataset.contentUid;
            if (uid) this.configInstances.delete(uid);
            existingConfig.remove();
        }

        // Add new widget config
        const configHtml = this.renderWidgetConfig(widgetType, [], {}, {});
        contentEl.insertAdjacentHTML('beforeend', configHtml);

        // Hydrate if using registry-based config
        this.hydrateWidgetConfigPlaceholders(contentEl);
    }

    /**
     * Hydrate widget config placeholders with registry-based config UIs
     * @param {HTMLElement} container - Container to search for placeholders
     */
    hydrateWidgetConfigPlaceholders(container) {
        const placeholders = container.querySelectorAll('.widget-config-placeholder');
        placeholders.forEach(placeholder => {
            const widgetType = placeholder.dataset.widgetType;
            const uid = placeholder.dataset.contentUid;
            const widgetConfig = JSON.parse(placeholder.dataset.widgetConfig || '{}');
            const content = JSON.parse(placeholder.dataset.content || '{}');

            try {
                // Create the config UI instance
                const instance = createConfigUI(placeholder, widgetType, widgetConfig, content);
                if (instance) {
                    // Store instance for later value collection
                    this.configInstances.set(uid, instance);
                    // Mark as hydrated
                    placeholder.classList.remove('widget-config-placeholder');
                    placeholder.classList.add('widget-config');
                }
            } catch (error) {
                console.error(`Failed to hydrate widget config for ${widgetType}:`, error);
                placeholder.innerHTML = `<div class="alert alert-warning small py-1 mb-0">
                    <i class="bi bi-exclamation-triangle"></i> Failed to load configuration UI
                </div>`;
            }
        });
    }

    collectWidgetConfig(contentEl, widgetType) {
        // Check for registry-based config instance first
        const configContainer = contentEl.querySelector('.widget-config');
        if (configContainer && configContainer.dataset.contentUid) {
            const uid = configContainer.dataset.contentUid;
            const instance = this.configInstances.get(uid);
            if (instance) {
                return instance.getValue();
            }
        }

        // Fallback to legacy DOM-based collection
        const config = {};

        switch (widgetType) {
            case 'multiple_choice':
                const shuffleOptions = contentEl.querySelector('.content-shuffle-options');
                const allowMultiple = contentEl.querySelector('.content-allow-multiple');
                if (shuffleOptions?.checked) config.shuffle_options = true;
                if (allowMultiple?.checked) config.allow_multiple = true;
                break;

            case 'slider':
                const minEl = contentEl.querySelector('.content-slider-min');
                const maxEl = contentEl.querySelector('.content-slider-max');
                const stepEl = contentEl.querySelector('.content-slider-step');
                const minLabelEl = contentEl.querySelector('.content-slider-min-label');
                const maxLabelEl = contentEl.querySelector('.content-slider-max-label');

                if (minEl?.value) config.min = parseFloat(minEl.value);
                if (maxEl?.value) config.max = parseFloat(maxEl.value);
                if (stepEl?.value) config.step = parseFloat(stepEl.value);
                if (minLabelEl?.value) config.min_label = minLabelEl.value;
                if (maxLabelEl?.value) config.max_label = maxLabelEl.value;
                break;

            case 'free_text':
                const placeholderEl = contentEl.querySelector('.content-placeholder');
                const minLengthEl = contentEl.querySelector('.content-min-length');
                const maxLengthEl = contentEl.querySelector('.content-max-length');
                const rowsEl = contentEl.querySelector('.content-rows');
                const multilineEl = contentEl.querySelector('.content-multiline');

                if (placeholderEl?.value) config.placeholder = placeholderEl.value;
                if (minLengthEl?.value) config.min_length = parseInt(minLengthEl.value);
                if (maxLengthEl?.value) config.max_length = parseInt(maxLengthEl.value);
                if (rowsEl?.value) config.rows = parseInt(rowsEl.value);
                if (multilineEl && !multilineEl.checked) config.multiline = false;
                break;
        }

        return config;
    }

    /**
     * Collect options from config instance or legacy DOM
     */
    collectOptions(contentEl, widgetType) {
        // Check for registry-based config instance
        const configContainer = contentEl.querySelector('.widget-config');
        if (configContainer && configContainer.dataset.contentUid) {
            const uid = configContainer.dataset.contentUid;
            const instance = this.configInstances.get(uid);
            if (instance && typeof instance.getOptions === 'function') {
                return instance.getOptions() || [];
            }
        }

        // Fallback: legacy approach for multiple_choice
        if (widgetType !== 'multiple_choice') return [];

        const optionsEl = contentEl.querySelector('.content-options');
        if (!optionsEl?.value) return [];

        return optionsEl.value
            .split('\n')
            .map(opt => opt.trim())
            .filter(opt => opt.length > 0);
    }

    /**
     * Collect initial value from config instance or legacy DOM
     */
    collectInitialValue(contentEl, widgetType) {
        // Check for registry-based config instance
        const configContainer = contentEl.querySelector('.widget-config');
        if (configContainer && configContainer.dataset.contentUid) {
            const uid = configContainer.dataset.contentUid;
            const instance = this.configInstances.get(uid);
            if (instance && typeof instance.getInitialValue === 'function') {
                return instance.getInitialValue();
            }
        }

        // Fallback: legacy approach
        if (widgetType === 'slider') {
            const initialEl = contentEl.querySelector('.content-initial-value');
            if (initialEl?.value) return parseFloat(initialEl.value);
        }
        return null;
    }

    /**
     * Collect correct answer from config instance or legacy DOM
     */
    collectCorrectAnswer(contentEl, widgetType) {
        // Check for registry-based config instance
        const configContainer = contentEl.querySelector('.widget-config');
        if (configContainer && configContainer.dataset.contentUid) {
            const uid = configContainer.dataset.contentUid;
            const instance = this.configInstances.get(uid);
            if (instance && typeof instance.getCorrectAnswer === 'function') {
                return instance.getCorrectAnswer();
            }
        }

        // Fallback: legacy DOM approach
        const correctAnswerEl = contentEl.querySelector('.content-correct-answer');
        return correctAnswerEl?.value || null;
    }

    reindexItems() {
        const container = document.getElementById('items-container');
        container.querySelectorAll('.item-card').forEach((item, index) => {
            item.dataset.itemIndex = index;
            item.querySelector('.item-order-badge').textContent = `#${index + 1}`;
        });
    }

    duplicateItem(itemElement) {
        // Collect data from the original item
        const itemData = this.collectItemData(itemElement);

        // Generate a new ID by appending "-copy" or incrementing
        const originalId = itemData.id;
        let newId = `${originalId}-copy`;

        // Check if copy already exists, increment if so
        const existingIds = Array.from(document.querySelectorAll('.item-card .item-id')).map(el => el.value);
        let copyNum = 1;
        while (existingIds.includes(newId)) {
            newId = `${originalId}-copy-${copyNum}`;
            copyNum++;
        }
        itemData.id = newId;
        itemData.title = `${itemData.title || ''} (Copy)`.trim();

        // Get current index and create new element
        const currentIndex = parseInt(itemElement.dataset.itemIndex);
        const newElement = this.createItemElement(itemData, currentIndex + 1);

        // Insert after the original
        itemElement.after(newElement);

        // Reindex all items and update badge
        this.reindexItems();
        this.updateItemCountBadge();

        // Flash the new item to draw attention
        newElement.classList.add('border-primary');
        setTimeout(() => newElement.classList.remove('border-primary'), 1000);
    }

    collectItemData(itemElement) {
        // Helper to collect data from a single item element
        const contents = [];
        itemElement.querySelectorAll('.content-card').forEach((contentEl, contentIndex) => {
            const widgetType = contentEl.querySelector('.content-widget-type').value;
            const isTemplated = contentEl.querySelector('.content-is-templated')?.checked || false;

            const content = {
                id: contentEl.querySelector('.content-id').value || `content-${contentIndex + 1}`,
                stem: contentEl.querySelector('.content-stem').value || '',
                widget_type: widgetType,
                is_templated: isTemplated,
            };

            // Collect options for multiple_choice
            if (widgetType === 'multiple_choice') {
                const optionsContainer = contentEl.querySelector('.options-container');
                if (optionsContainer) {
                    content.options = Array.from(optionsContainer.querySelectorAll('.option-item')).map(opt => ({
                        label: opt.querySelector('.option-label').value || '',
                        value: opt.querySelector('.option-value').value || '',
                        is_correct: opt.querySelector('.option-is-correct')?.checked || false,
                    }));
                }
            }

            // Collect widget config
            const widgetConfig = this.collectWidgetConfig(contentEl, widgetType);
            if (Object.keys(widgetConfig).length > 0) {
                content.widget_config = widgetConfig;
            }

            contents.push(content);
        });

        return {
            id: itemElement.querySelector('.item-id').value || '',
            title: itemElement.querySelector('.item-title').value || '',
            enable_chat_input: itemElement.querySelector('.item-enable-chat')?.checked || false,
            provide_feedback: itemElement.querySelector('.item-provide-feedback')?.checked || false,
            reveal_correct_answer: itemElement.querySelector('.item-reveal-answer')?.checked || false,
            show_expiration_warning: itemElement.querySelector('.item-show-expiration-warning')?.checked || false,
            time_limit_seconds: parseInt(itemElement.querySelector('.item-time-limit')?.value) || null,
            instructions: itemElement.querySelector('.item-instructions')?.value || null,
            require_user_confirmation: itemElement.querySelector('.item-require-confirmation')?.checked || false,
            confirmation_button_text: itemElement.querySelector('.item-confirmation-text')?.value || 'Submit',
            contents: contents,
        };
    }

    collectFormData() {
        const form = document.getElementById('template-form');
        const formData = new FormData(form);

        // Collect items from DOM
        const items = [];
        document.querySelectorAll('.item-card').forEach((itemEl, itemIndex) => {
            const contents = [];
            itemEl.querySelectorAll('.content-card').forEach((contentEl, contentIndex) => {
                const widgetType = contentEl.querySelector('.content-widget-type').value;
                const isTemplated = contentEl.querySelector('.content-is-templated')?.checked || false;

                // Collect widget-specific configuration (uses registry-based instances when available)
                const widgetConfig = this.collectWidgetConfig(contentEl, widgetType);
                const options = this.collectOptions(contentEl, widgetType);
                const correctAnswer = this.collectCorrectAnswer(contentEl, widgetType);
                const initialValue = this.collectInitialValue(contentEl, widgetType);

                contents.push({
                    id: contentEl.querySelector('.content-id').value,
                    order: contentIndex + 1,
                    widget_type: widgetType,
                    stem: contentEl.querySelector('.content-stem').value || null,
                    is_templated: isTemplated,
                    options: options.length > 0 ? options : null,
                    correct_answer: correctAnswer,
                    initial_value: initialValue,
                    widget_config: Object.keys(widgetConfig).length > 0 ? widgetConfig : {},
                    skippable: contentEl.querySelector('.content-skippable')?.checked || false,
                    required: contentEl.querySelector('.content-required')?.checked !== false,
                    max_score: 1.0,
                });
            });

            items.push({
                id: itemEl.querySelector('.item-id').value,
                order: itemIndex + 1,
                title: itemEl.querySelector('.item-title').value || null,
                enable_chat_input: itemEl.querySelector('.item-enable-chat').checked,
                provide_feedback: itemEl.querySelector('.item-provide-feedback').checked,
                reveal_correct_answer: itemEl.querySelector('.item-reveal-answer').checked,
                time_limit_seconds: parseInt(itemEl.querySelector('.item-time-limit').value) || null,
                show_expiration_warning: itemEl.querySelector('.item-show-expiration-warning').checked,
                expiration_warning_seconds: parseInt(itemEl.querySelector('.item-expiration-warning-seconds').value) || 30,
                warning_message: itemEl.querySelector('.item-warning-message').value || null,
                instructions: itemEl.querySelector('.item-instructions')?.value || null,
                require_user_confirmation: itemEl.querySelector('.item-require-confirmation')?.checked || false,
                confirmation_button_text: itemEl.querySelector('.item-confirmation-text')?.value || 'Submit',
                contents,
            });
        });

        return {
            id: formData.get('id'),
            name: formData.get('name'),
            description: formData.get('description') || null,
            agent_starts_first: document.getElementById('template-agent-starts-first').checked,
            allow_navigation: document.getElementById('template-allow-navigation').checked,
            allow_backward_navigation: document.getElementById('template-allow-backward').checked,
            enable_chat_input_initially: document.getElementById('template-enable-chat-initially').checked,
            continue_after_completion: document.getElementById('template-continue-after-completion').checked,
            allow_agent_switching: true,
            max_duration_seconds: parseInt(formData.get('max_duration_seconds')) || null,
            min_duration_seconds: null,
            shuffle_items: document.getElementById('template-shuffle-items').checked,
            display_progress_indicator: document.getElementById('template-show-progress').checked,
            display_item_score: false,
            display_item_title: true,
            display_final_score_report: document.getElementById('template-show-final-score').checked,
            include_feedback: document.getElementById('template-include-feedback').checked,
            append_items_to_view: true,
            introduction_message: formData.get('introduction_message') || null,
            completion_message: formData.get('completion_message') || null,
            passing_score_percent: parseFloat(formData.get('passing_score_percent')) || null,
            items,
        };
    }

    async saveTemplate() {
        const form = document.getElementById('template-form');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const saveBtn = document.getElementById('save-template-btn');
        const originalText = saveBtn.innerHTML;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';

        try {
            const data = this.collectFormData();
            console.log('[TemplatesManager] Saving template data:', JSON.stringify(data, null, 2));

            if (this.editingTemplate) {
                // Update existing - use the stored ID since the field is disabled
                data.id = this.editingTemplate.id;
                data.version = parseInt(document.getElementById('template-version').value, 10);
                await this.request(`/admin/templates/${this.editingTemplate.id}`, {
                    method: 'PUT',
                    body: JSON.stringify(data),
                });
                showToast('Template updated successfully', 'success');
            } else {
                // Create new
                await this.request('/admin/templates', {
                    method: 'POST',
                    body: JSON.stringify(data),
                });
                showToast('Template created successfully', 'success');
            }

            this.modal.hide();
            await this.loadTemplates();
        } catch (error) {
            console.error('Failed to save template:', error);
            const message = error.message || 'Failed to save template';
            showToast(message, 'error');
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalText;
        }
    }

    async confirmDelete() {
        const id = document.getElementById('delete-item-id').value;
        const itemType = document.getElementById('delete-item-type').value;

        if (itemType !== 'template') return;

        const deleteBtn = document.getElementById('confirm-delete-btn');
        const originalText = deleteBtn.innerHTML;
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Deleting...';

        try {
            await this.request(`/admin/templates/${id}`, {
                method: 'DELETE',
            });
            showToast('Template deleted successfully', 'success');
            this.deleteModal.hide();
            await this.loadTemplates();
        } catch (error) {
            console.error('Failed to delete template:', error);
            showToast(error.message || 'Failed to delete template', 'error');
        } finally {
            deleteBtn.disabled = false;
            deleteBtn.innerHTML = originalText;
        }
    }

    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
