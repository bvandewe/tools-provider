/**
 * Sources Page Component
 *
 * Admin page for managing OpenAPI sources.
 */

import * as bootstrap from 'bootstrap';
import { eventBus } from '../core/event-bus.js';
import * as SourcesAPI from '../api/sources.js';
import { showToast } from '../components/toast-notification.js';
import { SourceCard } from '../components/source-card.js';
import { isAuthenticated } from '../api/client.js';

class SourcesPage extends HTMLElement {
    constructor() {
        super();
        this._sources = [];
        this._loading = true;
        this._eventSubscriptions = [];
    }

    connectedCallback() {
        this.render();
        this._loadSources();
        this._subscribeToEvents();
    }

    disconnectedCallback() {
        this._unsubscribeFromEvents();
    }

    async _loadSources() {
        // Skip loading if not authenticated (avoids console errors)
        if (!isAuthenticated()) {
            this._loading = false;
            this._sources = [];
            this.render();
            return;
        }

        this._loading = true;
        this.render();

        try {
            this._sources = await SourcesAPI.getSources();
        } catch (error) {
            // Don't show toast for auth errors - user will be redirected to login
            if (!error.message?.includes('Session expired')) {
                showToast('error', `Failed to load sources: ${error.message}`);
            }
            this._sources = [];
        } finally {
            this._loading = false;
            this.render();
        }
    }

    _subscribeToEvents() {
        // Subscribe to SSE events for real-time updates
        this._eventSubscriptions.push(
            eventBus.subscribe('source:registered', data => {
                this._handleSourceRegistered(data);
            }),
            eventBus.subscribe('source:deleted', data => {
                this._handleSourceDeleted(data);
            }),
            eventBus.subscribe('source:inventory_refreshed', data => {
                this._handleInventoryRefreshed(data);
            })
        );
    }

    _unsubscribeFromEvents() {
        this._eventSubscriptions.forEach(unsub => unsub());
        this._eventSubscriptions = [];
    }

    _handleSourceRegistered(data) {
        // Add new source to list if not already present
        const exists = this._sources.some(s => s.id === data.source_id);
        if (!exists) {
            // Reload to get full source data
            this._loadSources();
            showToast('info', `New source registered: ${data.name || 'Unknown'}`);
        }
    }

    _handleSourceDeleted(data) {
        this._sources = this._sources.filter(s => s.id !== data.source_id);
        this.render();
    }

    _handleInventoryRefreshed(data) {
        const source = this._sources.find(s => s.id === data.source_id);
        if (source) {
            source.last_refreshed_at = new Date().toISOString();
            source.tools_count = data.tools_count;
            this.render();
        }
    }

    render() {
        this.innerHTML = `
            <div class="sources-page">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h2 class="mb-1">
                            <i class="bi bi-cloud-arrow-down text-primary me-2"></i>
                            OpenAPI Sources
                        </h2>
                        <p class="text-muted mb-0">
                            Manage upstream OpenAPI services that provide MCP tools
                        </p>
                    </div>
                    <button type="button" class="btn btn-primary" id="add-source-btn">
                        <i class="bi bi-plus-lg me-2"></i>
                        Add Source
                    </button>
                </div>

                ${this._loading ? this._renderLoading() : this._renderSources()}
            </div>

            ${this._renderAddSourceModal()}
            ${this._renderDetailsModal()}
        `;

        this._attachEventListeners();
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

    _renderSources() {
        if (this._sources.length === 0) {
            return `
                <div class="text-center py-5">
                    <i class="bi bi-cloud-slash display-1 text-muted"></i>
                    <h4 class="mt-3 text-muted">No Sources Configured</h4>
                    <p class="text-muted">Add an OpenAPI source to get started</p>
                    <button type="button" class="btn btn-primary" data-action="add-first">
                        <i class="bi bi-plus-lg me-2"></i>
                        Add Your First Source
                    </button>
                </div>
            `;
        }

        return `
            <div class="row g-4">
                ${this._sources
                    .map(
                        source => `
                    <div class="col-12 col-md-6 col-lg-4">
                        <source-card data-source-id="${source.id}"></source-card>
                    </div>
                `
                    )
                    .join('')}
            </div>
        `;
    }

    _renderAddSourceModal() {
        return `
            <div class="modal fade" id="add-source-modal" tabindex="-1" aria-labelledby="addSourceModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <form id="add-source-form">
                            <div class="modal-header">
                                <h5 class="modal-title" id="addSourceModalLabel">
                                    <i class="bi bi-cloud-plus me-2"></i>
                                    Add OpenAPI Source
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="source-name" class="form-label">Name <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control" id="source-name" required
                                           placeholder="My API Service">
                                </div>
                                <div class="mb-3">
                                    <label for="source-url" class="form-label">OpenAPI URL <span class="text-danger">*</span></label>
                                    <input type="url" class="form-control" id="source-url" required
                                           placeholder="https://api.example.com/openapi.json">
                                    <div class="form-text">URL to the OpenAPI specification (JSON or YAML)</div>
                                </div>
                                <div class="mb-3">
                                    <label for="source-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="source-description" rows="2"
                                              placeholder="Optional description of this API source"></textarea>
                                </div>
                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="auto-refresh" checked>
                                        <label class="form-check-label" for="auto-refresh">
                                            Auto-refresh inventory
                                        </label>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-primary" id="submit-source-btn">
                                    <span class="spinner-border spinner-border-sm d-none me-2" id="submit-spinner"></span>
                                    Add Source
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
    }

    _attachEventListeners() {
        // Add source buttons
        this.querySelector('#add-source-btn')?.addEventListener('click', () => this._showAddModal());
        this.querySelector('[data-action="add-first"]')?.addEventListener('click', () => this._showAddModal());

        // Form submission
        this.querySelector('#add-source-form')?.addEventListener('submit', e => this._handleAddSource(e));

        // Bind data to source cards
        this.querySelectorAll('source-card').forEach(card => {
            const sourceId = card.dataset.sourceId;
            const source = this._sources.find(s => s.id === sourceId);
            if (source) {
                card.data = source;
            }
        });

        // Listen for card events
        this.addEventListener('source-delete', e => {
            this._sources = this._sources.filter(s => s.id !== e.detail.id);
            this.render();
        });

        this.addEventListener('source-view', e => {
            this._showSourceDetails(e.detail.data);
        });

        this.addEventListener('source-refresh', () => {
            // SSE will notify when refresh completes
        });
    }

    _showAddModal() {
        const modalEl = this.querySelector('#add-source-modal');
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
    }

    _renderDetailsModal() {
        return `
            <div class="modal fade" id="source-details-modal" tabindex="-1" aria-labelledby="sourceDetailsModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="sourceDetailsModalLabel">
                                <i class="bi bi-info-circle me-2"></i>
                                Source Details
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body" id="source-details-body">
                            <!-- Content will be populated dynamically -->
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _showSourceDetails(source) {
        if (!source) return;

        const detailsBody = this.querySelector('#source-details-body');
        if (!detailsBody) return;

        const healthStatus = source.health_status || 'unknown';
        const statusMap = {
            healthy: { class: 'bg-success', text: 'HEALTHY' },
            degraded: { class: 'bg-warning', text: 'DEGRADED' },
            unhealthy: { class: 'bg-danger', text: 'UNHEALTHY' },
            unknown: { class: 'bg-secondary', text: 'UNKNOWN' },
        };
        const status = statusMap[healthStatus.toLowerCase()] || statusMap['unknown'];

        const toolsCount = source.inventory_count ?? source.tools_count ?? 0;
        const lastSync = source.last_sync_at ? new Date(source.last_sync_at).toLocaleString() : 'Never';
        const createdAt = source.created_at ? new Date(source.created_at).toLocaleString() : 'Unknown';
        const updatedAt = source.updated_at ? new Date(source.updated_at).toLocaleString() : 'Unknown';

        detailsBody.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-muted mb-3">General Information</h6>
                    <table class="table table-sm">
                        <tr>
                            <td class="text-muted" style="width: 40%">Name</td>
                            <td class="fw-medium">${this._escapeHtml(source.name)}</td>
                        </tr>
                        <tr>
                            <td class="text-muted">ID</td>
                            <td><code class="small">${this._escapeHtml(source.id)}</code></td>
                        </tr>
                        <tr>
                            <td class="text-muted">Type</td>
                            <td>${source.source_type || 'openapi'}</td>
                        </tr>
                        <tr>
                            <td class="text-muted">Status</td>
                            <td><span class="badge ${status.class}">${status.text}</span></td>
                        </tr>
                        <tr>
                            <td class="text-muted">Enabled</td>
                            <td>
                                <i class="bi ${source.is_enabled !== false ? 'bi-check-circle text-success' : 'bi-x-circle text-danger'}"></i>
                                ${source.is_enabled !== false ? 'Yes' : 'No'}
                            </td>
                        </tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6 class="text-muted mb-3">Inventory & Sync</h6>
                    <table class="table table-sm">
                        <tr>
                            <td class="text-muted" style="width: 40%">Tools Count</td>
                            <td class="fw-medium text-primary">${toolsCount}</td>
                        </tr>
                        <tr>
                            <td class="text-muted">Last Sync</td>
                            <td>${lastSync}</td>
                        </tr>
                        <tr>
                            <td class="text-muted">Created</td>
                            <td>${createdAt}</td>
                        </tr>
                        <tr>
                            <td class="text-muted">Updated</td>
                            <td>${updatedAt}</td>
                        </tr>
                        ${
                            source.last_sync_error
                                ? `
                        <tr>
                            <td class="text-muted">Last Error</td>
                            <td class="text-danger small">${this._escapeHtml(source.last_sync_error)}</td>
                        </tr>
                        `
                                : ''
                        }
                    </table>
                </div>
            </div>
            <div class="mt-3">
                <h6 class="text-muted mb-2">OpenAPI URL</h6>
                <div class="input-group">
                    <input type="text" class="form-control form-control-sm" value="${this._escapeHtml(source.url)}" readonly>
                    <button class="btn btn-outline-secondary btn-sm" type="button" onclick="navigator.clipboard.writeText('${this._escapeHtml(
                        source.url
                    )}'); this.innerHTML='<i class=\\'bi bi-check\\'></i>';">
                        <i class="bi bi-clipboard"></i>
                    </button>
                    <a href="${this._escapeHtml(source.url)}" target="_blank" class="btn btn-outline-secondary btn-sm">
                        <i class="bi bi-box-arrow-up-right"></i>
                    </a>
                </div>
            </div>
        `;

        const modalEl = this.querySelector('#source-details-modal');
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
    }

    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    async _handleAddSource(e) {
        e.preventDefault();

        const form = e.target;
        const submitBtn = form.querySelector('#submit-source-btn');
        const spinner = form.querySelector('#submit-spinner');

        const sourceData = {
            name: form.querySelector('#source-name').value.trim(),
            url: form.querySelector('#source-url').value.trim(),
            description: form.querySelector('#source-description').value.trim() || undefined,
            auto_refresh: form.querySelector('#auto-refresh').checked,
        };

        submitBtn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            const newSource = await SourcesAPI.registerSource(sourceData);
            this._sources.push(newSource);

            // Close modal and reset form
            const modal = bootstrap.Modal.getInstance(this.querySelector('#add-source-modal'));
            modal.hide();
            form.reset();

            showToast('success', `Source "${sourceData.name}" added successfully`);
            this.render();
        } catch (error) {
            showToast('error', `Failed to add source: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    }
}

if (!customElements.get('sources-page')) {
    customElements.define('sources-page', SourcesPage);
}

export { SourcesPage };
