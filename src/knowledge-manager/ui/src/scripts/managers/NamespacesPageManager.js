/**
 * NamespacesPageManager - Manages the Namespaces page/tab
 *
 * Handles namespace listing, CRUD operations via modals,
 * and table interactions.
 *
 * @module managers/NamespacesPageManager
 */

import { eventBus, Events } from '../core/event-bus.js';
import { apiService } from '../services/ApiService.js';

/**
 * NamespacesPageManager class
 */
export class NamespacesPageManager {
    /**
     * Create NamespacesPageManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Array} */
        this._namespaces = [];

        /** @type {Object|null} */
        this._currentNamespace = null;

        /** @type {boolean} */
        this._isLoading = false;

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
            console.warn('[NamespacesPageManager] Already initialized');
            return;
        }

        this._cacheElements();
        this._attachEventListeners();
        this._subscribeToEvents();
        this._initModals();
        this._initialized = true;
        console.log('[NamespacesPageManager] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._namespaces = [];
        this._currentNamespace = null;
        this._initialized = false;
        console.log('[NamespacesPageManager] Destroyed');
    }

    /**
     * Cache DOM elements
     * @private
     */
    _cacheElements() {
        this._elements = {
            page: document.getElementById('namespaces-page'),
            table: document.getElementById('namespaces-table'),
            tbody: document.getElementById('namespaces-tbody'),
            loading: document.getElementById('namespaces-loading'),
            empty: document.getElementById('namespaces-empty'),
            searchInput: document.getElementById('namespaces-search'),
            refreshBtn: document.getElementById('btn-refresh-namespaces'),
            createBtn: document.getElementById('btn-create-namespace'),
            // Modal elements
            modal: document.getElementById('namespaceModal'),
            form: document.getElementById('namespace-form'),
            modalTitle: document.querySelector('#namespaceModal .modal-title'),
            modalSaveBtn: document.getElementById('btn-save-namespace'),
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
        this._elements.refreshBtn?.addEventListener('click', () => this.loadNamespaces());

        // Create button
        this._elements.createBtn?.addEventListener('click', () => this.openCreateModal());

        // Search input
        this._elements.searchInput?.addEventListener('input', e => this._handleSearch(e.target.value));

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
                if (data.to === 'namespaces') {
                    this.loadNamespaces();
                }
            })
        );

        // Listen for modal open events (e.g., from Dashboard Quick Actions)
        this._unsubscribers.push(
            eventBus.on(Events.MODAL_NAMESPACE_OPEN, data => {
                if (data?.mode === 'create') {
                    this.openCreateModal();
                } else if (data?.namespaceId) {
                    this.openEditModal(data.namespaceId);
                }
            })
        );

        this._unsubscribers.push(eventBus.on(Events.NAMESPACE_CREATED, () => this.loadNamespaces()));

        this._unsubscribers.push(eventBus.on(Events.NAMESPACE_UPDATED, () => this.loadNamespaces()));

        this._unsubscribers.push(eventBus.on(Events.NAMESPACE_DELETED, () => this.loadNamespaces()));
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
     * Load namespaces from API
     */
    async loadNamespaces() {
        if (this._isLoading) return;

        this._isLoading = true;
        this._showLoading(true);

        try {
            const namespaces = await apiService.getNamespaces();
            this._namespaces = namespaces || [];
            this._renderTable();
            console.log(`[NamespacesPageManager] Loaded ${this._namespaces.length} namespaces`);
        } catch (error) {
            console.error('[NamespacesPageManager] Failed to load namespaces:', error);
            this._showError('Failed to load namespaces');
        } finally {
            this._isLoading = false;
            this._showLoading(false);
        }
    }

    // =========================================================================
    // Rendering
    // =========================================================================

    /**
     * Render the namespaces table
     * @private
     */
    _renderTable() {
        if (!this._elements.tbody) return;

        // Filter by search
        const searchTerm = this._elements.searchInput?.value?.toLowerCase() || '';
        const filtered = this._namespaces.filter(ns => ns.id?.toLowerCase().includes(searchTerm) || ns.name?.toLowerCase().includes(searchTerm) || ns.description?.toLowerCase().includes(searchTerm));

        if (filtered.length === 0) {
            this._showEmpty(true);
            this._elements.table?.classList.add('d-none');
            return;
        }

        this._showEmpty(false);
        this._elements.table?.classList.remove('d-none');

        this._elements.tbody.innerHTML = filtered.map(ns => this._renderRow(ns)).join('');

        // Attach row click handlers
        this._attachRowListeners();
    }

    /**
     * Render a single table row
     * @private
     * @param {Object} ns - Namespace object
     * @returns {string} HTML string
     */
    _renderRow(ns) {
        const accessLevelBadge = this._getAccessLevelBadge(ns.access_level);
        const termCount = ns.term_count || 0;
        const updatedAt = ns.updated_at ? new Date(ns.updated_at).toLocaleDateString() : '-';

        return `
            <tr data-namespace-id="${this._escapeHtml(ns.id)}" role="button" class="namespace-row">
                <td>
                    <div class="fw-medium">${this._escapeHtml(ns.name)}</div>
                    <small class="text-muted"><code>${this._escapeHtml(ns.id)}</code></small>
                </td>
                <td>${this._escapeHtml(ns.description || '-')}</td>
                <td class="text-center">${accessLevelBadge}</td>
                <td class="text-center">
                    <span class="badge bg-secondary">${termCount}</span>
                </td>
                <td class="text-muted">${updatedAt}</td>
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
        const rows = this._elements.tbody?.querySelectorAll('.namespace-row');
        rows?.forEach(row => {
            const namespaceId = row.dataset.namespaceId;

            // Row click opens modal
            row.addEventListener('click', e => {
                // Ignore if clicking buttons
                if (e.target.closest('.btn-edit') || e.target.closest('.btn-delete')) {
                    return;
                }
                this.openEditModal(namespaceId);
            });

            // Edit button
            row.querySelector('.btn-edit')?.addEventListener('click', e => {
                e.stopPropagation();
                this.openEditModal(namespaceId);
            });

            // Delete button
            row.querySelector('.btn-delete')?.addEventListener('click', e => {
                e.stopPropagation();
                this.openDeleteModal(namespaceId);
            });
        });
    }

    // =========================================================================
    // Modal Operations
    // =========================================================================

    /**
     * Open the create namespace modal
     */
    openCreateModal() {
        this._currentNamespace = null;
        this._resetForm();
        this._elements.modalTitle.textContent = 'Create Namespace';
        this._elements.modalSaveBtn.innerHTML = '<i class="bi bi-plus-circle me-1"></i>Create';
        this._modal?.show();
    }

    /**
     * Open the edit namespace modal
     * @param {string} namespaceId - The namespace ID to edit
     */
    async openEditModal(namespaceId) {
        try {
            // Find in cache or fetch
            let namespace = this._namespaces.find(ns => ns.id === namespaceId);
            if (!namespace) {
                namespace = await apiService.getNamespace(namespaceId);
            }

            this._currentNamespace = namespace;
            this._populateForm(namespace);
            this._elements.modalTitle.textContent = 'Edit Namespace';
            this._elements.modalSaveBtn.innerHTML = '<i class="bi bi-check-circle me-1"></i>Save';
            this._modal?.show();
        } catch (error) {
            console.error('[NamespacesPageManager] Failed to load namespace:', error);
            eventBus.emit(Events.UI_TOAST, { type: 'error', message: 'Failed to load namespace' });
        }
    }

    /**
     * Open the delete confirmation modal
     * @param {string} namespaceId - The namespace ID to delete
     */
    openDeleteModal(namespaceId) {
        const namespace = this._namespaces.find(ns => ns.id === namespaceId);
        if (!namespace) return;

        this._currentNamespace = namespace;
        this._elements.deleteMessage.innerHTML = `
            Are you sure you want to delete the namespace
            <strong>${this._escapeHtml(namespace.name)}</strong>?
            <br><small class="text-muted">This action cannot be undone.</small>
        `;
        this._deleteModal?.show();
    }

    /**
     * Populate form with namespace data
     * @private
     * @param {Object} namespace - Namespace data
     */
    _populateForm(namespace) {
        const form = this._elements.form;
        if (!form) return;

        form.querySelector('#namespace-id')?.setAttribute('value', namespace.id || '');
        form.querySelector('#namespace-id')?.setAttribute('readonly', 'true');
        form.querySelector('#namespace-name').value = namespace.name || '';
        form.querySelector('#namespace-description').value = namespace.description || '';
        form.querySelector('#namespace-access-level').value = namespace.access_level || 'private';
    }

    /**
     * Reset form to empty state
     * @private
     */
    _resetForm() {
        const form = this._elements.form;
        if (!form) return;

        form.reset();
        form.querySelector('#namespace-id')?.removeAttribute('readonly');
        this._currentNamespace = null;
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
        const data = {
            slug: formData.get('namespace-id'),
            name: formData.get('namespace-name'),
            description: formData.get('namespace-description'),
            is_public: formData.get('namespace-access-level') === 'public',
        };

        try {
            this._elements.modalSaveBtn.disabled = true;

            if (this._currentNamespace) {
                // Update
                await apiService.updateNamespace(this._currentNamespace.id, {
                    name: data.name,
                    description: data.description,
                    is_public: data.is_public,
                });
                eventBus.emit(Events.NAMESPACE_UPDATED, { namespaceId: this._currentNamespace.id });
                eventBus.emit(Events.UI_TOAST, { type: 'success', message: 'Namespace updated' });
            } else {
                // Create
                await apiService.createNamespace(data);
                eventBus.emit(Events.NAMESPACE_CREATED, { namespaceId: data.slug });
                eventBus.emit(Events.UI_TOAST, { type: 'success', message: 'Namespace created' });
            }

            this._modal?.hide();
        } catch (error) {
            console.error('[NamespacesPageManager] Save failed:', error);
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
        if (!this._currentNamespace) return;

        try {
            this._elements.deleteConfirmBtn.disabled = true;
            await apiService.deleteNamespace(this._currentNamespace.id);
            eventBus.emit(Events.NAMESPACE_DELETED, { namespaceId: this._currentNamespace.id });
            eventBus.emit(Events.UI_TOAST, { type: 'success', message: 'Namespace deleted' });
            this._deleteModal?.hide();
        } catch (error) {
            console.error('[NamespacesPageManager] Delete failed:', error);
            eventBus.emit(Events.UI_TOAST, { type: 'error', message: error.message || 'Delete failed' });
        } finally {
            this._elements.deleteConfirmBtn.disabled = false;
            this._currentNamespace = null;
        }
    }

    // =========================================================================
    // Search
    // =========================================================================

    /**
     * Handle search input
     * @private
     * @param {string} searchTerm - Search term
     */
    _handleSearch(searchTerm) {
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
     * Get access level badge HTML
     * @private
     * @param {string} accessLevel
     * @returns {string}
     */
    _getAccessLevelBadge(accessLevel) {
        const colors = {
            public: 'success',
            tenant: 'warning',
            private: 'secondary',
        };
        const color = colors[accessLevel] || 'secondary';
        return `<span class="badge bg-${color}">${accessLevel || 'private'}</span>`;
    }

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
export const namespacesPageManager = new NamespacesPageManager();
