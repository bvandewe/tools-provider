/**
 * TermsPageManager - Manages the Terms page/tab
 *
 * Handles term listing across all namespaces, CRUD operations via modals,
 * and table interactions with namespace filtering.
 *
 * @module managers/TermsPageManager
 */

import { eventBus, Events } from '../core/event-bus.js';
import { apiService } from '../services/ApiService.js';

/**
 * TermsPageManager class
 */
export class TermsPageManager {
    /**
     * Create TermsPageManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Array} */
        this._terms = [];

        /** @type {Array} */
        this._namespaces = [];

        /** @type {Object|null} */
        this._currentTerm = null;

        /** @type {boolean} */
        this._isLoading = false;

        /** @type {string|null} */
        this._filterNamespaceId = null;

        /** @type {Function[]} */
        this._unsubscribers = [];

        /** @type {Object|null} */
        this._modal = null;

        /** @type {Object|null} */
        this._deleteModal = null;
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize the page manager
     */
    init() {
        if (this._initialized) {
            console.warn('[TermsPageManager] Already initialized');
            return;
        }

        this._cacheElements();
        this._attachEventListeners();
        this._subscribeToEvents();
        this._initModals();
        this._initialized = true;
        console.log('[TermsPageManager] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._terms = [];
        this._namespaces = [];
        this._currentTerm = null;
        this._initialized = false;
        console.log('[TermsPageManager] Destroyed');
    }

    /**
     * Cache DOM elements
     * @private
     */
    _cacheElements() {
        this._elements = {
            page: document.getElementById('terms-page'),
            table: document.getElementById('terms-table'),
            tbody: document.getElementById('terms-tbody'),
            loading: document.getElementById('terms-loading'),
            empty: document.getElementById('terms-empty'),
            searchInput: document.getElementById('terms-search'),
            filterSelect: document.getElementById('terms-filter-namespace'),
            refreshBtn: document.getElementById('btn-refresh-terms'),
            createBtn: document.getElementById('btn-create-term'),
            // Modal elements
            modal: document.getElementById('termModal'),
            form: document.getElementById('term-form'),
            modalTitle: document.querySelector('#termModal .modal-title'),
            modalSaveBtn: document.getElementById('btn-save-term'),
            namespaceSelect: document.querySelector('#term-form #term-namespace-id'),
            // Delete modal
            deleteModal: document.getElementById('deleteModal'),
            deleteMessage: document.getElementById('delete-message'),
            deleteConfirmBtn: document.getElementById('btn-confirm-delete'),
        };
    }

    /**
     * Attach DOM event listeners
     * @private
     */
    _attachEventListeners() {
        // Refresh button
        this._elements.refreshBtn?.addEventListener('click', () => this.loadTerms());

        // Create button
        this._elements.createBtn?.addEventListener('click', () => this.openCreateModal());

        // Search input
        this._elements.searchInput?.addEventListener('input', e => this._handleSearch(e.target.value));

        // Namespace filter
        this._elements.filterSelect?.addEventListener('change', e => this._handleFilterChange(e.target.value));

        // Save button
        this._elements.modalSaveBtn?.addEventListener('click', () => this._handleSave());

        // Delete confirm button
        this._elements.deleteConfirmBtn?.addEventListener('click', () => this._handleDeleteConfirm());

        // Form submission prevention
        this._elements.form?.addEventListener('submit', e => {
            e.preventDefault();
            this._handleSave();
        });

        // Modal hidden event - reset form
        this._elements.modal?.addEventListener('hidden.bs.modal', () => this._resetForm());
    }

    /**
     * Subscribe to EventBus events
     * @private
     */
    _subscribeToEvents() {
        this._unsubscribers.push(
            eventBus.on(Events.UI_PAGE_CHANGED, data => {
                if (data.to === 'terms') {
                    this.loadTerms();
                }
            })
        );

        this._unsubscribers.push(eventBus.on(Events.TERM_CREATED, () => this.loadTerms()));

        this._unsubscribers.push(eventBus.on(Events.TERM_UPDATED, () => this.loadTerms()));

        this._unsubscribers.push(eventBus.on(Events.TERM_DELETED, () => this.loadTerms()));

        // Reload terms when namespaces change
        this._unsubscribers.push(
            eventBus.on(Events.NAMESPACES_LOADED, data => {
                this._namespaces = data.namespaces || [];
                this._populateNamespaceFilters();
            })
        );
    }

    /**
     * Initialize Bootstrap modals
     * @private
     */
    _initModals() {
        if (this._elements.modal && typeof bootstrap !== 'undefined') {
            this._modal = new bootstrap.Modal(this._elements.modal);
        }
        if (this._elements.deleteModal && typeof bootstrap !== 'undefined') {
            this._deleteModal = new bootstrap.Modal(this._elements.deleteModal);
        }
    }

    // =========================================================================
    // Data Loading
    // =========================================================================

    /**
     * Load all terms from all namespaces
     */
    async loadTerms() {
        if (this._isLoading) return;

        this._isLoading = true;
        this._showLoading(true);

        try {
            // First, ensure we have namespaces
            if (this._namespaces.length === 0) {
                this._namespaces = await apiService.getNamespaces();
                this._populateNamespaceFilters();
            }

            // Load terms from all namespaces
            const allTerms = [];
            for (const ns of this._namespaces) {
                try {
                    const terms = await apiService.getTerms(ns.id);
                    // Add namespace info to each term
                    terms.forEach(term => {
                        term.namespace_id = ns.id;
                        term.namespace_name = ns.name;
                    });
                    allTerms.push(...terms);
                } catch (error) {
                    console.warn(`[TermsPageManager] Failed to load terms for ${ns.id}:`, error);
                }
            }

            this._terms = allTerms;
            this._renderTable();
            console.log(`[TermsPageManager] Loaded ${this._terms.length} terms from ${this._namespaces.length} namespaces`);
        } catch (error) {
            console.error('[TermsPageManager] Failed to load terms:', error);
            this._showError('Failed to load terms');
        } finally {
            this._isLoading = false;
            this._showLoading(false);
        }
    }

    // =========================================================================
    // Rendering
    // =========================================================================

    /**
     * Populate namespace filter dropdowns
     * @private
     */
    _populateNamespaceFilters() {
        // Filter dropdown
        if (this._elements.filterSelect) {
            const currentValue = this._elements.filterSelect.value;
            this._elements.filterSelect.innerHTML = `
                <option value="">All Namespaces</option>
                ${this._namespaces.map(ns => `<option value="${this._escapeHtml(ns.id)}">${this._escapeHtml(ns.name)}</option>`).join('')}
            `;
            this._elements.filterSelect.value = currentValue;
        }

        // Modal namespace select
        if (this._elements.namespaceSelect) {
            this._elements.namespaceSelect.innerHTML = `
                <option value="">Select a namespace...</option>
                ${this._namespaces.map(ns => `<option value="${this._escapeHtml(ns.id)}">${this._escapeHtml(ns.name)}</option>`).join('')}
            `;
        }
    }

    /**
     * Render the terms table
     * @private
     */
    _renderTable() {
        if (!this._elements.tbody) return;

        // Apply filters
        const searchTerm = this._elements.searchInput?.value?.toLowerCase() || '';
        const filterNsId = this._filterNamespaceId;

        let filtered = this._terms;

        // Filter by namespace
        if (filterNsId) {
            filtered = filtered.filter(t => t.namespace_id === filterNsId);
        }

        // Filter by search
        if (searchTerm) {
            filtered = filtered.filter(
                t =>
                    t.slug?.toLowerCase().includes(searchTerm) ||
                    t.label?.toLowerCase().includes(searchTerm) ||
                    t.definition?.toLowerCase().includes(searchTerm) ||
                    t.namespace_name?.toLowerCase().includes(searchTerm)
            );
        }

        if (filtered.length === 0) {
            this._showEmpty(true);
            this._elements.table?.classList.add('d-none');
            return;
        }

        this._showEmpty(false);
        this._elements.table?.classList.remove('d-none');

        this._elements.tbody.innerHTML = filtered.map(term => this._renderRow(term)).join('');

        // Attach row click handlers
        this._attachRowListeners();
    }

    /**
     * Render a single table row
     * @private
     * @param {Object} term - Term object
     * @returns {string} HTML string
     */
    _renderRow(term) {
        const definitionPreview = term.definition ? (term.definition.length > 100 ? term.definition.substring(0, 100) + '...' : term.definition) : '-';

        return `
            <tr data-term-id="${this._escapeHtml(term.id || term.slug)}"
                data-namespace-id="${this._escapeHtml(term.namespace_id)}"
                role="button"
                class="term-row">
                <td>
                    <span class="badge bg-primary-subtle text-primary">
                        ${this._escapeHtml(term.namespace_name || term.namespace_id)}
                    </span>
                </td>
                <td>
                    <div class="fw-medium">${this._escapeHtml(term.label || term.slug)}</div>
                    <small class="text-muted"><code>${this._escapeHtml(term.slug)}</code></small>
                </td>
                <td class="text-muted">${this._escapeHtml(definitionPreview)}</td>
                <td class="text-end">
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary btn-edit" title="Edit">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-danger btn-delete" title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    /**
     * Attach row click listeners
     * @private
     */
    _attachRowListeners() {
        const rows = this._elements.tbody?.querySelectorAll('.term-row');
        rows?.forEach(row => {
            const termId = row.dataset.termId;
            const namespaceId = row.dataset.namespaceId;

            // Row click opens modal
            row.addEventListener('click', e => {
                if (e.target.closest('.btn-edit') || e.target.closest('.btn-delete')) {
                    return;
                }
                this.openEditModal(namespaceId, termId);
            });

            // Edit button
            row.querySelector('.btn-edit')?.addEventListener('click', e => {
                e.stopPropagation();
                this.openEditModal(namespaceId, termId);
            });

            // Delete button
            row.querySelector('.btn-delete')?.addEventListener('click', e => {
                e.stopPropagation();
                this.openDeleteModal(namespaceId, termId);
            });
        });
    }

    // =========================================================================
    // Modal Operations
    // =========================================================================

    /**
     * Open the create term modal
     * @param {string} [preselectedNamespaceId] - Optional namespace to preselect
     */
    openCreateModal(preselectedNamespaceId = null) {
        this._currentTerm = null;
        this._resetForm();
        this._elements.modalTitle.textContent = 'Create Term';
        this._elements.modalSaveBtn.innerHTML = '<i class="bi bi-plus-circle me-1"></i>Create';

        // Preselect namespace if provided
        if (preselectedNamespaceId && this._elements.namespaceSelect) {
            this._elements.namespaceSelect.value = preselectedNamespaceId;
        }

        this._modal?.show();
    }

    /**
     * Open the edit term modal
     * @param {string} namespaceId - Namespace ID
     * @param {string} termId - Term ID
     */
    async openEditModal(namespaceId, termId) {
        try {
            // Find in cache
            const term = this._terms.find(t => (t.id === termId || t.slug === termId) && t.namespace_id === namespaceId);

            if (!term) {
                console.warn('[TermsPageManager] Term not found in cache');
                return;
            }

            this._currentTerm = { ...term };
            this._populateForm(term);
            this._elements.modalTitle.textContent = 'Edit Term';
            this._elements.modalSaveBtn.innerHTML = '<i class="bi bi-check-circle me-1"></i>Save';
            this._modal?.show();
        } catch (error) {
            console.error('[TermsPageManager] Failed to load term:', error);
            eventBus.emit(Events.UI_TOAST, { type: 'error', message: 'Failed to load term' });
        }
    }

    /**
     * Open the delete confirmation modal
     * @param {string} namespaceId - Namespace ID
     * @param {string} termId - Term ID
     */
    openDeleteModal(namespaceId, termId) {
        const term = this._terms.find(t => (t.id === termId || t.slug === termId) && t.namespace_id === namespaceId);
        if (!term) return;

        this._currentTerm = { ...term };
        this._elements.deleteMessage.innerHTML = `
            Are you sure you want to delete the term
            <strong>${this._escapeHtml(term.label || term.slug)}</strong>
            from namespace <strong>${this._escapeHtml(term.namespace_name)}</strong>?
            <br><small class="text-muted">This action cannot be undone.</small>
        `;
        this._deleteModal?.show();
    }

    /**
     * Populate form with term data
     * @private
     * @param {Object} term - Term data
     */
    _populateForm(term) {
        const form = this._elements.form;
        if (!form) return;

        if (this._elements.namespaceSelect) {
            this._elements.namespaceSelect.value = term.namespace_id || '';
            this._elements.namespaceSelect.disabled = true; // Can't change namespace on edit
        }
        form.querySelector('#term-slug')?.setAttribute('value', term.slug || '');
        form.querySelector('#term-slug')?.setAttribute('readonly', 'true');
        form.querySelector('#term-label').value = term.label || '';
        form.querySelector('#term-definition').value = term.definition || '';
        form.querySelector('#term-aliases').value = (term.aliases || []).join(', ');
        form.querySelector('#term-examples').value = (term.examples || []).join('\n');
        form.querySelector('#term-context-hint').value = term.context_hint || '';
    }

    /**
     * Reset form to empty state
     * @private
     */
    _resetForm() {
        const form = this._elements.form;
        if (!form) return;

        form.reset();
        form.querySelector('#term-slug')?.removeAttribute('readonly');
        if (this._elements.namespaceSelect) {
            this._elements.namespaceSelect.disabled = false;
        }
        this._currentTerm = null;
    }

    /**
     * Handle form save
     * @private
     */
    async _handleSave() {
        const form = this._elements.form;
        if (!form || !form.checkValidity()) {
            form?.reportValidity();
            return;
        }

        const formData = new FormData(form);
        const namespaceId = formData.get('term-namespace-id');
        const data = {
            slug: formData.get('term-slug'),
            label: formData.get('term-label'),
            definition: formData.get('term-definition'),
            aliases:
                formData
                    .get('term-aliases')
                    ?.split(',')
                    .map(s => s.trim())
                    .filter(Boolean) || [],
            examples:
                formData
                    .get('term-examples')
                    ?.split('\n')
                    .map(s => s.trim())
                    .filter(Boolean) || [],
            context_hint: formData.get('term-context-hint') || null,
        };

        if (!namespaceId) {
            eventBus.emit(Events.UI_TOAST, { type: 'error', message: 'Please select a namespace' });
            return;
        }

        try {
            this._elements.modalSaveBtn.disabled = true;

            if (this._currentTerm) {
                // Update - Note: API may not support update yet, would need to add
                // For now, just emit event and show success
                // await apiService.updateTerm(this._currentTerm.namespace_id, this._currentTerm.slug, data);
                eventBus.emit(Events.TERM_UPDATED, {
                    namespaceId: this._currentTerm.namespace_id,
                    termId: this._currentTerm.slug,
                });
                eventBus.emit(Events.UI_TOAST, { type: 'info', message: 'Term update not yet implemented' });
            } else {
                // Create
                await apiService.createTerm(namespaceId, data);
                eventBus.emit(Events.TERM_CREATED, { namespaceId, termId: data.slug });
                eventBus.emit(Events.UI_TOAST, { type: 'success', message: 'Term created' });
            }

            this._modal?.hide();
        } catch (error) {
            console.error('[TermsPageManager] Save failed:', error);
            eventBus.emit(Events.UI_TOAST, { type: 'error', message: error.message || 'Save failed' });
        } finally {
            this._elements.modalSaveBtn.disabled = false;
        }
    }

    /**
     * Handle delete confirmation
     * @private
     */
    async _handleDeleteConfirm() {
        if (!this._currentTerm) return;

        try {
            this._elements.deleteConfirmBtn.disabled = true;
            // Note: API deleteTerm method would need to be added
            // await apiService.deleteTerm(this._currentTerm.namespace_id, this._currentTerm.slug);
            eventBus.emit(Events.TERM_DELETED, {
                namespaceId: this._currentTerm.namespace_id,
                termId: this._currentTerm.slug,
            });
            eventBus.emit(Events.UI_TOAST, { type: 'info', message: 'Term delete not yet implemented' });
            this._deleteModal?.hide();
        } catch (error) {
            console.error('[TermsPageManager] Delete failed:', error);
            eventBus.emit(Events.UI_TOAST, { type: 'error', message: error.message || 'Delete failed' });
        } finally {
            this._elements.deleteConfirmBtn.disabled = false;
            this._currentTerm = null;
        }
    }

    // =========================================================================
    // Filtering
    // =========================================================================

    /**
     * Handle search input
     * @private
     * @param {string} searchTerm - Search term
     */
    _handleSearch(searchTerm) {
        this._renderTable();
    }

    /**
     * Handle namespace filter change
     * @private
     * @param {string} namespaceId - Selected namespace ID
     */
    _handleFilterChange(namespaceId) {
        this._filterNamespaceId = namespaceId || null;
        this._renderTable();
    }

    // =========================================================================
    // UI State
    // =========================================================================

    /**
     * Show/hide loading state
     * @private
     * @param {boolean} show
     */
    _showLoading(show) {
        this._elements.loading?.classList.toggle('d-none', !show);
        this._elements.table?.classList.toggle('d-none', show);
    }

    /**
     * Show/hide empty state
     * @private
     * @param {boolean} show
     */
    _showEmpty(show) {
        this._elements.empty?.classList.toggle('d-none', !show);
    }

    /**
     * Show error message
     * @private
     * @param {string} message
     */
    _showError(message) {
        eventBus.emit(Events.UI_TOAST, { type: 'error', message });
    }

    // =========================================================================
    // Helpers
    // =========================================================================

    /**
     * Escape HTML to prevent XSS
     * @private
     * @param {string} str
     * @returns {string}
     */
    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

// Singleton export
export const termsPageManager = new TermsPageManager();
