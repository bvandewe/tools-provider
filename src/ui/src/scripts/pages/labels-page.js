/**
 * Labels Page Component
 *
 * Admin page for managing tool labels.
 * Labels can be assigned to tools for categorization and filtering.
 */

import * as bootstrap from 'bootstrap';
import { eventBus } from '../core/event-bus.js';
import * as LabelsAPI from '../api/labels.js';
import { showToast } from '../components/toast-notification.js';
import { isAuthenticated } from '../api/client.js';

// Predefined color palette for labels
const LABEL_COLORS = [
    { name: 'Gray', value: '#6c757d' },
    { name: 'Blue', value: '#0d6efd' },
    { name: 'Green', value: '#198754' },
    { name: 'Red', value: '#dc3545' },
    { name: 'Yellow', value: '#ffc107' },
    { name: 'Cyan', value: '#0dcaf0' },
    { name: 'Purple', value: '#6f42c1' },
    { name: 'Pink', value: '#d63384' },
    { name: 'Orange', value: '#fd7e14' },
    { name: 'Teal', value: '#20c997' },
    { name: 'Indigo', value: '#6610f2' },
    { name: 'Navy', value: '#0a58ca' },
];

class LabelsPage extends HTMLElement {
    constructor() {
        super();
        this._labels = [];
        this._loading = true;
        this._eventSubscriptions = [];
        this._editingLabel = null;
    }

    connectedCallback() {
        this.render();
        this._loadLabels();
        this._subscribeToEvents();
    }

    disconnectedCallback() {
        this._unsubscribeFromEvents();
    }

    async _loadLabels() {
        // Skip loading if not authenticated (avoids console errors)
        if (!isAuthenticated()) {
            this._loading = false;
            this._labels = [];
            this.render();
            return;
        }

        this._loading = true;
        this.render();

        try {
            this._labels = await LabelsAPI.getLabels();
        } catch (error) {
            // Don't show toast for auth errors - user will be redirected to login
            if (!error.message?.includes('Session expired')) {
                showToast('error', `Failed to load labels: ${error.message}`);
            }
            this._labels = [];
        } finally {
            this._loading = false;
            this.render();
        }
    }

    _subscribeToEvents() {
        this._eventSubscriptions.push(
            eventBus.subscribe('label:created', () => this._loadLabels()),
            eventBus.subscribe('label:updated', () => this._loadLabels()),
            eventBus.subscribe('label:deleted', data => {
                this._labels = this._labels.filter(l => l.id !== data.label_id);
                this.render();
            })
        );
    }

    _unsubscribeFromEvents() {
        this._eventSubscriptions.forEach(unsub => unsub());
        this._eventSubscriptions = [];
    }

    render() {
        const totalTools = this._labels.reduce((sum, l) => sum + (l.tool_count || 0), 0);

        this.innerHTML = `
            <div class="labels-page">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h2 class="mb-1">
                            <i class="bi bi-tags text-primary me-2"></i>
                            Tool Labels
                        </h2>
                        <p class="text-muted mb-0">
                            Create and manage labels for categorizing tools
                        </p>
                    </div>
                    <button type="button" class="btn btn-primary" id="add-label-btn">
                        <i class="bi bi-plus-lg me-2"></i>
                        Create Label
                    </button>
                </div>

                ${this._renderStats(totalTools)}

                ${this._loading ? this._renderLoading() : this._renderLabels()}
            </div>

            ${this._renderAddLabelModal()}
            ${this._renderEditLabelModal()}
            ${this._renderDeleteConfirmModal()}
        `;

        this._attachEventListeners();
    }

    _renderStats(totalTools) {
        return `
            <div class="row g-3 mb-4">
                <div class="col-6 col-md-4">
                    <div class="card bg-primary bg-opacity-10 border-0">
                        <div class="card-body py-3 text-center">
                            <div class="fs-3 fw-bold text-primary">${this._labels.length}</div>
                            <small class="text-muted">Labels</small>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-4">
                    <div class="card bg-success bg-opacity-10 border-0">
                        <div class="card-body py-3 text-center">
                            <div class="fs-3 fw-bold text-success">${totalTools}</div>
                            <small class="text-muted">Tools Tagged</small>
                        </div>
                    </div>
                </div>
                <div class="col-12 col-md-4">
                    <div class="card bg-info bg-opacity-10 border-0">
                        <div class="card-body py-3 text-center">
                            <div class="fs-3 fw-bold text-info">
                                ${this._labels.filter(l => !l.is_deleted).length}
                            </div>
                            <small class="text-muted">Active Labels</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _renderLoading() {
        return `
            <div class="d-flex justify-content-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
    }

    _renderLabels() {
        if (this._labels.length === 0) {
            return `
                <div class="text-center py-5">
                    <i class="bi bi-tags display-1 text-muted"></i>
                    <h4 class="mt-3 text-muted">No Labels Created</h4>
                    <p class="text-muted">Create labels to categorize and filter your tools</p>
                    <button type="button" class="btn btn-primary" data-action="add-first">
                        <i class="bi bi-plus-lg me-2"></i>
                        Create Your First Label
                    </button>
                </div>
            `;
        }

        return `
            <div class="card">
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead class="table-light">
                            <tr>
                                <th style="width: 40px"></th>
                                <th>Name</th>
                                <th>Description</th>
                                <th class="text-center" style="width: 100px">Tools</th>
                                <th class="text-end" style="width: 120px">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${this._labels.map(label => this._renderLabelRow(label)).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    _renderLabelRow(label) {
        return `
            <tr data-label-id="${label.id}">
                <td>
                    <span class="badge rounded-pill" style="background-color: ${label.color}; width: 24px; height: 24px;">&nbsp;</span>
                </td>
                <td>
                    <span class="badge rounded-pill me-2" style="background-color: ${label.color}">
                        ${this._escapeHtml(label.name)}
                    </span>
                </td>
                <td class="text-muted">
                    ${label.description ? this._escapeHtml(label.description) : '<em>No description</em>'}
                </td>
                <td class="text-center">
                    <span class="badge bg-secondary">${label.tool_count || 0}</span>
                </td>
                <td class="text-end">
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" data-action="edit" data-label-id="${label.id}" title="Edit label">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-danger" data-action="delete" data-label-id="${label.id}" title="Delete label">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    _renderColorPicker(selectedColor = '#6c757d', idPrefix = '') {
        return `
            <div class="color-picker-grid d-flex flex-wrap gap-2">
                ${LABEL_COLORS.map(
                    color => `
                    <label class="color-option" title="${color.name}">
                        <input type="radio" name="${idPrefix}label-color" value="${color.value}"
                               ${color.value === selectedColor ? 'checked' : ''} class="d-none">
                        <span class="color-swatch rounded-circle d-inline-block"
                              style="width: 32px; height: 32px; background-color: ${color.value};
                                     cursor: pointer; border: 3px solid ${color.value === selectedColor ? '#000' : 'transparent'};">
                        </span>
                    </label>
                `
                ).join('')}
            </div>
        `;
    }

    _renderAddLabelModal() {
        return `
            <div class="modal fade" id="add-label-modal" tabindex="-1" aria-labelledby="addLabelModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <form id="add-label-form">
                            <div class="modal-header">
                                <h5 class="modal-title" id="addLabelModalLabel">
                                    <i class="bi bi-tag me-2"></i>
                                    Create Label
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="label-name" class="form-label">Name <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control" id="label-name" required
                                           placeholder="e.g., Production, Deprecated, Internal">
                                </div>
                                <div class="mb-3">
                                    <label for="label-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="label-description" rows="2"
                                              placeholder="Optional description of this label"></textarea>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Color</label>
                                    ${this._renderColorPicker('#6c757d', 'add-')}
                                </div>

                                <!-- Preview -->
                                <div class="mb-3">
                                    <label class="form-label">Preview</label>
                                    <div id="label-preview" class="p-3 bg-light rounded">
                                        <span class="badge rounded-pill" id="label-preview-badge" style="background-color: #6c757d">
                                            New Label
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-primary" id="create-label-btn">
                                    <i class="bi bi-plus-lg me-2"></i>
                                    Create Label
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
    }

    _renderEditLabelModal() {
        return `
            <div class="modal fade" id="edit-label-modal" tabindex="-1" aria-labelledby="editLabelModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <form id="edit-label-form">
                            <div class="modal-header">
                                <h5 class="modal-title" id="editLabelModalLabel">
                                    <i class="bi bi-pencil me-2"></i>
                                    Edit Label
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="edit-label-name" class="form-label">Name <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control" id="edit-label-name" required>
                                </div>
                                <div class="mb-3">
                                    <label for="edit-label-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="edit-label-description" rows="2"></textarea>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Color</label>
                                    ${this._renderColorPicker('#6c757d', 'edit-')}
                                </div>

                                <!-- Preview -->
                                <div class="mb-3">
                                    <label class="form-label">Preview</label>
                                    <div id="edit-label-preview" class="p-3 bg-light rounded">
                                        <span class="badge rounded-pill" id="edit-label-preview-badge" style="background-color: #6c757d">
                                            Label
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-primary" id="save-label-btn">
                                    <i class="bi bi-check-lg me-2"></i>
                                    Save Changes
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
    }

    _renderDeleteConfirmModal() {
        return `
            <div class="modal fade" id="delete-label-modal" tabindex="-1" aria-labelledby="deleteLabelModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="deleteLabelModalLabel">
                                <i class="bi bi-exclamation-triangle text-danger me-2"></i>
                                Delete Label
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <p>Are you sure you want to delete the label <strong id="delete-label-name"></strong>?</p>
                            <div class="alert alert-warning mb-0">
                                <i class="bi bi-info-circle me-2"></i>
                                This will remove the label from all tools it's currently assigned to.
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-danger" id="confirm-delete-label-btn">
                                <i class="bi bi-trash me-2"></i>
                                Delete Label
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _attachEventListeners() {
        // Add label button
        const addBtn = this.querySelector('#add-label-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this._showAddModal());
        }

        // "Create first" button
        const addFirstBtn = this.querySelector('[data-action="add-first"]');
        if (addFirstBtn) {
            addFirstBtn.addEventListener('click', () => this._showAddModal());
        }

        // Add form submission
        const addForm = this.querySelector('#add-label-form');
        if (addForm) {
            addForm.addEventListener('submit', e => this._handleAddLabel(e));
        }

        // Edit form submission
        const editForm = this.querySelector('#edit-label-form');
        if (editForm) {
            editForm.addEventListener('submit', e => this._handleEditLabel(e));
        }

        // Color picker changes (add modal)
        const addColorInputs = this.querySelectorAll('[name="add-label-color"]');
        addColorInputs.forEach(input => {
            input.addEventListener('change', () => this._updateAddPreview());
        });

        // Name input change (add modal)
        const nameInput = this.querySelector('#label-name');
        if (nameInput) {
            nameInput.addEventListener('input', () => this._updateAddPreview());
        }

        // Color picker changes (edit modal)
        const editColorInputs = this.querySelectorAll('[name="edit-label-color"]');
        editColorInputs.forEach(input => {
            input.addEventListener('change', () => this._updateEditPreview());
        });

        // Name input change (edit modal)
        const editNameInput = this.querySelector('#edit-label-name');
        if (editNameInput) {
            editNameInput.addEventListener('input', () => this._updateEditPreview());
        }

        // Table row actions
        this.querySelectorAll('[data-action="edit"]').forEach(btn => {
            btn.addEventListener('click', e => this._showEditModal(e.currentTarget.dataset.labelId));
        });

        this.querySelectorAll('[data-action="delete"]').forEach(btn => {
            btn.addEventListener('click', e => this._showDeleteModal(e.currentTarget.dataset.labelId));
        });

        // Confirm delete
        const confirmDeleteBtn = this.querySelector('#confirm-delete-label-btn');
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', () => this._handleDeleteLabel());
        }
    }

    _showAddModal() {
        const modal = new bootstrap.Modal(this.querySelector('#add-label-modal'));

        // Reset form
        const form = this.querySelector('#add-label-form');
        if (form) form.reset();

        // Reset color picker
        const defaultColor = this.querySelector('[name="add-label-color"][value="#6c757d"]');
        if (defaultColor) defaultColor.checked = true;
        this._updateColorSwatchBorders('add-');

        this._updateAddPreview();
        modal.show();
    }

    _showEditModal(labelId) {
        const label = this._labels.find(l => l.id === labelId);
        if (!label) return;

        this._editingLabel = label;

        // Populate form
        const nameInput = this.querySelector('#edit-label-name');
        const descInput = this.querySelector('#edit-label-description');

        if (nameInput) nameInput.value = label.name;
        if (descInput) descInput.value = label.description || '';

        // Set color
        const colorInput = this.querySelector(`[name="edit-label-color"][value="${label.color}"]`);
        if (colorInput) {
            colorInput.checked = true;
        } else {
            // Default to gray if color not found
            const defaultColor = this.querySelector('[name="edit-label-color"][value="#6c757d"]');
            if (defaultColor) defaultColor.checked = true;
        }
        this._updateColorSwatchBorders('edit-');

        this._updateEditPreview();

        const modal = new bootstrap.Modal(this.querySelector('#edit-label-modal'));
        modal.show();
    }

    _showDeleteModal(labelId) {
        const label = this._labels.find(l => l.id === labelId);
        if (!label) return;

        this._editingLabel = label;

        const nameEl = this.querySelector('#delete-label-name');
        if (nameEl) nameEl.textContent = label.name;

        const modal = new bootstrap.Modal(this.querySelector('#delete-label-modal'));
        modal.show();
    }

    _updateAddPreview() {
        const nameInput = this.querySelector('#label-name');
        const colorInput = this.querySelector('[name="add-label-color"]:checked');
        const previewBadge = this.querySelector('#label-preview-badge');

        if (previewBadge) {
            previewBadge.textContent = nameInput?.value || 'New Label';
            previewBadge.style.backgroundColor = colorInput?.value || '#6c757d';
        }

        this._updateColorSwatchBorders('add-');
    }

    _updateEditPreview() {
        const nameInput = this.querySelector('#edit-label-name');
        const colorInput = this.querySelector('[name="edit-label-color"]:checked');
        const previewBadge = this.querySelector('#edit-label-preview-badge');

        if (previewBadge) {
            previewBadge.textContent = nameInput?.value || 'Label';
            previewBadge.style.backgroundColor = colorInput?.value || '#6c757d';
        }

        this._updateColorSwatchBorders('edit-');
    }

    _updateColorSwatchBorders(prefix) {
        const checkedInput = this.querySelector(`[name="${prefix}label-color"]:checked`);
        const allSwatches = this.querySelectorAll(`[name="${prefix}label-color"]`);

        allSwatches.forEach(input => {
            const swatch = input.nextElementSibling;
            if (swatch) {
                swatch.style.borderColor = input === checkedInput ? '#000' : 'transparent';
            }
        });
    }

    async _handleAddLabel(e) {
        e.preventDefault();

        const nameInput = this.querySelector('#label-name');
        const descInput = this.querySelector('#label-description');
        const colorInput = this.querySelector('[name="add-label-color"]:checked');
        const submitBtn = this.querySelector('#create-label-btn');

        const name = nameInput?.value?.trim();
        if (!name) {
            showToast('error', 'Label name is required');
            return;
        }

        // Disable submit button
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Creating...';
        }

        // Get modal reference BEFORE any re-rendering
        const modalElement = this.querySelector('#add-label-modal');
        const modal = modalElement ? bootstrap.Modal.getInstance(modalElement) : null;

        try {
            await LabelsAPI.createLabel({
                name,
                description: descInput?.value?.trim() || '',
                color: colorInput?.value || '#6c757d',
            });

            showToast('success', `Label "${name}" created successfully`);

            // Close modal BEFORE reloading to prevent backdrop issues
            if (modal) {
                modal.hide();
            }
            // Remove any lingering backdrop
            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('overflow');
            document.body.style.removeProperty('padding-right');

            // Reload labels to show the new one
            this._loadLabels();
        } catch (error) {
            showToast('error', `Failed to create label: ${error.message}`);
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="bi bi-plus-lg me-2"></i>Create Label';
            }
        }
    }

    async _handleEditLabel(e) {
        e.preventDefault();

        if (!this._editingLabel) return;

        const nameInput = this.querySelector('#edit-label-name');
        const descInput = this.querySelector('#edit-label-description');
        const colorInput = this.querySelector('[name="edit-label-color"]:checked');
        const submitBtn = this.querySelector('#save-label-btn');

        const name = nameInput?.value?.trim();
        if (!name) {
            showToast('error', 'Label name is required');
            return;
        }

        // Disable submit button
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
        }

        // Get modal reference BEFORE any re-rendering
        const modalElement = this.querySelector('#edit-label-modal');
        const modal = modalElement ? bootstrap.Modal.getInstance(modalElement) : null;

        try {
            await LabelsAPI.updateLabel(this._editingLabel.id, {
                name,
                description: descInput?.value?.trim() || '',
                color: colorInput?.value || '#6c757d',
            });

            showToast('success', `Label "${name}" updated successfully`);

            // Close modal BEFORE reloading to prevent backdrop issues
            if (modal) {
                modal.hide();
            }
            // Remove any lingering backdrop
            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('overflow');
            document.body.style.removeProperty('padding-right');

            this._editingLabel = null;

            // Reload labels to show the update
            this._loadLabels();
        } catch (error) {
            showToast('error', `Failed to update label: ${error.message}`);
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="bi bi-check-lg me-2"></i>Save Changes';
            }
        }
    }

    async _handleDeleteLabel() {
        if (!this._editingLabel) return;

        const deleteBtn = this.querySelector('#confirm-delete-label-btn');

        // Disable delete button
        if (deleteBtn) {
            deleteBtn.disabled = true;
            deleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Deleting...';
        }

        // Get modal reference BEFORE any re-rendering
        const modalElement = this.querySelector('#delete-label-modal');
        const modal = modalElement ? bootstrap.Modal.getInstance(modalElement) : null;

        try {
            await LabelsAPI.deleteLabel(this._editingLabel.id);

            showToast('success', `Label "${this._editingLabel.name}" deleted successfully`);

            // Close modal BEFORE reloading to prevent backdrop issues
            if (modal) {
                modal.hide();
            }
            // Remove any lingering backdrop
            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('overflow');
            document.body.style.removeProperty('padding-right');

            this._editingLabel = null;

            // Reload labels to reflect deletion
            this._loadLabels();
        } catch (error) {
            showToast('error', `Failed to delete label: ${error.message}`);
        } finally {
            if (deleteBtn) {
                deleteBtn.disabled = false;
                deleteBtn.innerHTML = '<i class="bi bi-trash me-2"></i>Delete Label';
            }
        }
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

customElements.define('labels-page', LabelsPage);

export { LabelsPage };
