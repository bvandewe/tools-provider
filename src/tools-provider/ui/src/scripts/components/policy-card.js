/**
 * Access Policy Card Component
 *
 * Displays an access policy with claim matchers and allowed groups.
 */

import { confirmDelete } from './confirm-modal.js';
import { showToast } from './toast-notification.js';
import * as PoliciesAPI from '../api/policies.js';

class PolicyCard extends HTMLElement {
    constructor() {
        super();
        this._data = null;
        this._groups = []; // Available groups for name resolution
        this._loading = false;
    }

    set data(value) {
        this._data = value;
        this.render();
    }

    get data() {
        return this._data;
    }

    set groups(value) {
        this._groups = value || [];
        this.render();
    }

    get groups() {
        return this._groups;
    }

    set loading(value) {
        this._loading = value;
        this.render();
    }

    connectedCallback() {
        this.render();
    }

    render() {
        if (this._loading) {
            this.innerHTML = `
                <div class="card h-100">
                    <div class="card-body d-flex align-items-center justify-content-center">
                        <div class="spinner-border spinner-border-sm text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                </div>
            `;
            return;
        }

        if (!this._data) {
            this.innerHTML = `
                <div class="card h-100 border-dashed">
                    <div class="card-body d-flex align-items-center justify-content-center text-muted">
                        <i class="bi bi-shield me-2"></i>
                        No policy data
                    </div>
                </div>
            `;
            return;
        }

        const policy = this._data;
        const isActive = policy.is_active !== false;
        const matcherCount = policy.claim_matchers?.length || policy.matcher_count || 0;
        const groupCount = policy.allowed_group_ids?.length || policy.group_count || 0;

        this.innerHTML = `
            <div class="card h-100 policy-card ${isActive ? '' : 'opacity-75'}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-shield-check text-primary me-2"></i>
                        <span class="fw-medium">${this._escapeHtml(policy.name)}</span>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <span class="badge bg-info">
                            Priority: ${policy.priority || 0}
                        </span>
                        <span class="badge ${isActive ? 'bg-success' : 'bg-secondary'}">
                            ${isActive ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                </div>
                <div class="card-body">
                    ${policy.description ? `<p class="card-text small text-muted mb-3">${this._escapeHtml(policy.description)}</p>` : ''}

                    <div class="row g-2 mb-3">
                        <div class="col-6 text-center">
                            <div class="fs-5 fw-bold text-primary">${matcherCount}</div>
                            <small class="text-muted">Claim Rules</small>
                        </div>
                        <div class="col-6 text-center">
                            <div class="fs-5 fw-bold text-success">${groupCount}</div>
                            <small class="text-muted">Tool Groups</small>
                        </div>
                    </div>

                    ${this._renderClaimMatchers(policy.claim_matchers)}
                    ${this._renderAllowedGroups(policy.allowed_group_ids, this._groups)}
                </div>
                <div class="card-footer bg-transparent border-top-0">
                    <div class="btn-group btn-group-sm w-100" role="group">
                        <button type="button" class="btn btn-outline-secondary" data-action="view" title="View details">
                            <i class="bi bi-eye"></i> Details
                        </button>
                        <button type="button" class="btn btn-outline-primary" data-action="edit" title="Edit policy">
                            <i class="bi bi-pencil"></i> Edit
                        </button>
                        <button type="button" class="btn btn-outline-danger" data-action="delete" title="Delete policy">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;

        this._attachEventListeners();
    }

    _renderClaimMatchers(matchers) {
        if (!matchers || matchers.length === 0) {
            return `
                <div class="mb-3">
                    <small class="text-muted d-block mb-1">Claim Matchers</small>
                    <span class="text-muted small">No claim rules defined</span>
                </div>
            `;
        }

        return `
            <div class="mb-3">
                <small class="text-muted d-block mb-1">Claim Matchers</small>
                <div class="d-flex flex-wrap gap-1">
                    ${matchers
                        .slice(0, 3)
                        .map(
                            m => `
                        <span class="badge bg-primary bg-opacity-10 text-primary border border-primary">
                            <i class="bi bi-funnel me-1"></i>
                            ${this._escapeHtml(m.json_path)} ${m.operator} "${this._escapeHtml(m.value || '')}"
                        </span>
                    `
                        )
                        .join('')}
                    ${matchers.length > 3 ? `<span class="badge bg-secondary">+${matchers.length - 3} more</span>` : ''}
                </div>
            </div>
        `;
    }

    _renderAllowedGroups(groupIds, groups = []) {
        if (!groupIds || groupIds.length === 0) {
            return `
                <div>
                    <small class="text-muted d-block mb-1">Allowed Tool Groups</small>
                    <span class="text-muted small">No groups assigned</span>
                </div>
            `;
        }

        // Resolve group names from IDs
        const resolveGroupName = id => {
            const group = groups.find(g => g.id === id);
            return group ? group.name : id.substring(0, 8) + '...';
        };

        return `
            <div>
                <small class="text-muted d-block mb-1">Allowed Tool Groups</small>
                <div class="d-flex flex-wrap gap-1">
                    ${groupIds
                        .slice(0, 3)
                        .map(
                            id => `
                        <span class="badge bg-success bg-opacity-10 text-success border border-success">
                            <i class="bi bi-collection me-1"></i>
                            ${this._escapeHtml(resolveGroupName(id))}
                        </span>
                    `
                        )
                        .join('')}
                    ${groupIds.length > 3 ? `<span class="badge bg-secondary">+${groupIds.length - 3} more</span>` : ''}
                </div>
            </div>
        `;
    }

    _attachEventListeners() {
        this.querySelector('[data-action="view"]')?.addEventListener('click', () => this._handleView());
        this.querySelector('[data-action="edit"]')?.addEventListener('click', () => this._handleEdit());
        this.querySelector('[data-action="delete"]')?.addEventListener('click', () => this._handleDelete());
    }

    _handleView() {
        this.dispatchEvent(
            new CustomEvent('policy-view', {
                detail: { id: this._data?.id, data: this._data },
                bubbles: true,
            })
        );
    }

    _handleEdit() {
        this.dispatchEvent(
            new CustomEvent('policy-edit', {
                detail: { id: this._data?.id, data: this._data },
                bubbles: true,
            })
        );
    }

    async _handleDelete() {
        if (!this._data?.id) return;

        const confirmed = await confirmDelete(this._data.name);
        if (!confirmed) return;

        try {
            await PoliciesAPI.deletePolicy(this._data.id);
            showToast('success', `Policy "${this._data.name}" deleted`);
            this.dispatchEvent(
                new CustomEvent('policy-delete', {
                    detail: { id: this._data.id },
                    bubbles: true,
                })
            );
        } catch (error) {
            showToast('error', `Failed to delete: ${error.message}`);
        }
    }

    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

if (!customElements.get('policy-card')) {
    customElements.define('policy-card', PolicyCard);
}

export { PolicyCard };
