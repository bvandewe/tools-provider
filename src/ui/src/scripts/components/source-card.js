/**
 * Source Card Component
 *
 * Displays an OpenAPI source with its tools count and actions.
 *
 * Usage:
 *   <source-card id="source-123"></source-card>
 *   document.querySelector('source-card').data = sourceObject;
 */

import { confirmDelete } from './confirm-modal.js';
import { showToast } from './toast-notification.js';
import * as SourcesAPI from '../api/sources.js';

class SourceCard extends HTMLElement {
    constructor() {
        super();
        this._data = null;
        this._loading = false;
    }

    set data(value) {
        this._data = value;
        this.render();
    }

    get data() {
        return this._data;
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
                        <i class="bi bi-cloud-slash me-2"></i>
                        No source data
                    </div>
                </div>
            `;
            return;
        }

        const source = this._data;
        // Support both inventory_count (from API) and tools_count (legacy)
        const toolsCount = source.inventory_count ?? source.tools_count ?? source.tools?.length ?? 0;
        // Support both last_sync_at (from API) and last_refreshed_at (legacy)
        const lastRefresh = source.last_sync_at || source.last_refreshed_at ? new Date(source.last_sync_at || source.last_refreshed_at).toLocaleString() : 'Never';
        // Map health_status to display status
        const healthStatus = source.health_status || 'unknown';
        const statusMap = {
            healthy: { class: 'bg-success', text: 'HEALTHY' },
            degraded: { class: 'bg-warning', text: 'DEGRADED' },
            unhealthy: { class: 'bg-danger', text: 'UNHEALTHY' },
            unknown: { class: 'bg-secondary', text: 'UNKNOWN' },
        };
        const status = statusMap[healthStatus.toLowerCase()] || statusMap['unknown'];

        this.innerHTML = `
            <div class="card h-100 source-card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-cloud-arrow-down text-primary me-2"></i>
                        <span class="fw-medium text-truncate" title="${this._escapeHtml(source.name)}">
                            ${this._escapeHtml(source.name)}
                        </span>
                    </div>
                    <span class="badge ${status.class}">${status.text}</span>
                </div>
                <div class="card-body">
                    <div class="mb-2">
                        <small class="text-muted d-block text-truncate" title="${this._escapeHtml(source.url)}">
                            <i class="bi bi-link-45deg me-1"></i>${this._escapeHtml(source.url)}
                        </small>
                    </div>
                    <div class="d-flex gap-3 mb-3">
                        <div class="text-center flex-fill">
                            <div class="fs-4 fw-bold text-primary">${toolsCount}</div>
                            <small class="text-muted">Tools</small>
                        </div>
                        <div class="text-center flex-fill">
                            <div class="small text-muted">${lastRefresh}</div>
                            <small class="text-muted">Last Refresh</small>
                        </div>
                    </div>
                    ${
                        source.description
                            ? `
                        <p class="card-text small text-muted mb-0 text-truncate-2" title="${this._escapeHtml(source.description)}">
                            ${this._escapeHtml(source.description)}
                        </p>
                    `
                            : ''
                    }
                </div>
                <div class="card-footer bg-transparent border-top-0">
                    <div class="btn-group w-100" role="group">
                        <button type="button" class="btn btn-outline-primary btn-sm" data-action="refresh" title="Refresh inventory">
                            <i class="bi bi-arrow-clockwise"></i>
                        </button>
                        <button type="button" class="btn btn-outline-secondary btn-sm" data-action="view" title="View details">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button type="button" class="btn btn-outline-secondary btn-sm" data-action="edit" title="Edit source">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button type="button" class="btn btn-outline-danger btn-sm" data-action="delete" title="Delete source">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;

        this._attachEventListeners();
    }

    _attachEventListeners() {
        this.querySelector('[data-action="refresh"]')?.addEventListener('click', () => this._handleRefresh());
        this.querySelector('[data-action="view"]')?.addEventListener('click', () => this._handleView());
        this.querySelector('[data-action="edit"]')?.addEventListener('click', () => this._handleEdit());
        this.querySelector('[data-action="delete"]')?.addEventListener('click', () => this._handleDelete());
    }

    async _handleRefresh() {
        if (!this._data?.id) return;

        const btn = this.querySelector('[data-action="refresh"]');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        try {
            await SourcesAPI.refreshInventory(this._data.id);
            showToast('success', `Refreshing inventory for ${this._data.name}`);
            this.dispatchEvent(
                new CustomEvent('source-refresh', {
                    detail: { id: this._data.id },
                    bubbles: true,
                })
            );
        } catch (error) {
            showToast('error', `Failed to refresh: ${error.message}`);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-arrow-clockwise"></i>';
        }
    }

    _handleView() {
        this.dispatchEvent(
            new CustomEvent('source-view', {
                detail: { id: this._data?.id, data: this._data },
                bubbles: true,
            })
        );
    }

    _handleEdit() {
        this.dispatchEvent(
            new CustomEvent('source-edit', {
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
            await SourcesAPI.deleteSource(this._data.id);
            showToast('success', `Source "${this._data.name}" deleted`);
            this.dispatchEvent(
                new CustomEvent('source-delete', {
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

if (!customElements.get('source-card')) {
    customElements.define('source-card', SourceCard);
}

export { SourceCard };
