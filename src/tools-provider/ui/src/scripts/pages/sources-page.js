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
import { dispatchNavigationEvent } from '../core/modal-utils.js';

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

        // Listen for external navigation events (e.g., from tool details)
        this.addEventListener('open-source-details', async e => {
            const { sourceId } = e.detail || {};
            if (sourceId) {
                await this._openSourceDetailsById(sourceId);
            }
        });
    }

    disconnectedCallback() {
        this._unsubscribeFromEvents();
    }

    /**
     * Open source details modal by source ID (for cross-entity navigation)
     */
    async _openSourceDetailsById(sourceId) {
        // Wait for sources to load if not yet loaded
        if (this._loading) {
            await new Promise(resolve => {
                const checkLoading = setInterval(() => {
                    if (!this._loading) {
                        clearInterval(checkLoading);
                        resolve();
                    }
                }, 100);
            });
        }

        // Find the source in loaded sources
        let source = this._sources.find(s => s.id === sourceId);

        // If not found, try to fetch it directly
        if (!source) {
            try {
                source = await SourcesAPI.getSource(sourceId);
            } catch (error) {
                console.error('Failed to fetch source:', error);
                showToast('error', `Source not found: ${sourceId}`);
                return;
            }
        }

        if (source) {
            this._showSourceDetails(source);
        }
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
            ${this._renderEditSourceModal()}
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
                <div class="modal-dialog modal-dialog-centered modal-lg">
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
                                    <label for="source-openapi-url" class="form-label">OpenAPI URL <span class="text-danger">*</span></label>
                                    <input type="url" class="form-control" id="source-openapi-url" required
                                           placeholder="https://api.example.com/openapi.json">
                                    <div class="form-text">URL to the OpenAPI specification (JSON or YAML)</div>
                                </div>
                                <div class="mb-3">
                                    <label for="source-url" class="form-label">
                                        Service URL
                                        <i class="bi bi-info-circle text-muted" data-bs-toggle="tooltip" data-bs-placement="right"
                                           title="Base URL of the service (e.g., https://api.example.com). If not provided, derived from OpenAPI URL."></i>
                                    </label>
                                    <input type="url" class="form-control" id="source-url"
                                           placeholder="https://api.example.com">
                                    <div class="form-text">
                                        Optional: Base URL of the service for documentation/linking
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label for="source-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="source-description" rows="2"
                                              placeholder="Optional description of this API source"></textarea>
                                </div>
                                <div class="mb-3">
                                    <label for="source-audience" class="form-label">
                                        Default Audience
                                        <i class="bi bi-info-circle text-muted" data-bs-toggle="tooltip" data-bs-placement="right"
                                           title="Keycloak client ID for token exchange (RFC 8693). Required if the upstream API validates JWT audience claims."></i>
                                    </label>
                                    <input type="text" class="form-control" id="source-audience"
                                           placeholder="e.g., my-api-backend">
                                    <div class="form-text">
                                        OAuth2 audience for token exchange. Leave empty if not required.
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label for="source-auth-mode" class="form-label">
                                        Authentication Mode
                                        <i class="bi bi-info-circle text-muted" data-bs-toggle="tooltip" data-bs-placement="right"
                                           title="How to authenticate requests to this upstream API. Token Exchange requires an audience."></i>
                                    </label>
                                    <select class="form-select" id="source-auth-mode">
                                        <option value="token_exchange" selected>Token Exchange (RFC 8693)</option>
                                        <option value="client_credentials">Client Credentials</option>
                                        <option value="http_basic">HTTP Basic</option>
                                        <option value="api_key">API Key</option>
                                        <option value="none">None (Public API)</option>
                                    </select>
                                    <div class="form-text">
                                        Select the authentication method for API calls.
                                    </div>
                                </div>

                                <!-- Token Exchange Fields (default) -->
                                <div id="auth-fields-token-exchange" class="auth-mode-fields">
                                    <div class="alert alert-info small py-2">
                                        <i class="bi bi-info-circle me-1"></i>
                                        Token Exchange uses the logged-in user's token, exchanged for a token with the target audience.
                                        Set the <strong>Default Audience</strong> above to the upstream service's Keycloak client ID.
                                    </div>
                                </div>

                                <!-- Client Credentials Fields -->
                                <div id="auth-fields-client-credentials" class="auth-mode-fields d-none">
                                    <div class="alert alert-info small py-2 mb-3">
                                        <i class="bi bi-info-circle me-1"></i>
                                        Client Credentials uses a service account. Leave fields empty to use the Tools Provider's default service account.
                                    </div>
                                    <div class="mb-3">
                                        <label for="oauth2-client-id" class="form-label">OAuth2 Client ID</label>
                                        <input type="text" class="form-control" id="oauth2-client-id"
                                               placeholder="Optional: source-specific client ID">
                                    </div>
                                    <div class="mb-3">
                                        <label for="oauth2-client-secret" class="form-label">OAuth2 Client Secret</label>
                                        <input type="password" class="form-control" id="oauth2-client-secret"
                                               placeholder="Optional: source-specific client secret">
                                    </div>
                                    <div class="mb-3">
                                        <label for="oauth2-token-url" class="form-label">OAuth2 Token URL</label>
                                        <input type="url" class="form-control" id="oauth2-token-url"
                                               placeholder="Optional: e.g., https://keycloak.example.com/realms/myrealm/protocol/openid-connect/token">
                                    </div>
                                    <div class="mb-3">
                                        <label for="oauth2-scopes" class="form-label">OAuth2 Scopes</label>
                                        <input type="text" class="form-control" id="oauth2-scopes"
                                               placeholder="Optional: space-separated scopes">
                                        <div class="form-text">Space-separated list of scopes (e.g., "openid profile")</div>
                                    </div>
                                </div>

                                <!-- API Key Fields -->
                                <div id="auth-fields-api-key" class="auth-mode-fields d-none">
                                    <div class="mb-3">
                                        <label for="api-key-name" class="form-label">API Key Header Name <span class="text-danger">*</span></label>
                                        <input type="text" class="form-control" id="api-key-name"
                                               placeholder="e.g., X-API-Key or Authorization">
                                    </div>
                                    <div class="mb-3">
                                        <label for="api-key-value" class="form-label">API Key Value <span class="text-danger">*</span></label>
                                        <input type="password" class="form-control" id="api-key-value"
                                               placeholder="Your API key">
                                    </div>
                                    <div class="mb-3">
                                        <label for="api-key-in" class="form-label">Send API Key In</label>
                                        <select class="form-select" id="api-key-in">
                                            <option value="header" selected>Header</option>
                                            <option value="query">Query Parameter</option>
                                        </select>
                                    </div>
                                </div>

                                <!-- HTTP Basic Auth Fields -->
                                <div id="auth-fields-http-basic" class="auth-mode-fields d-none">
                                    <div class="alert alert-info small py-2 mb-3">
                                        <i class="bi bi-info-circle me-1"></i>
                                        HTTP Basic authentication sends credentials in the Authorization header using Base64 encoding (RFC 7617).
                                    </div>
                                    <div class="mb-3">
                                        <label for="basic-username" class="form-label">Username <span class="text-danger">*</span></label>
                                        <input type="text" class="form-control" id="basic-username"
                                               placeholder="Username for Basic auth">
                                    </div>
                                    <div class="mb-3">
                                        <label for="basic-password" class="form-label">Password <span class="text-danger">*</span></label>
                                        <input type="password" class="form-control" id="basic-password"
                                               placeholder="Password for Basic auth">
                                    </div>
                                </div>

                                <!-- None (Public API) Fields -->
                                <div id="auth-fields-none" class="auth-mode-fields d-none">
                                    <div class="alert alert-success small py-2">
                                        <i class="bi bi-unlock me-1"></i>
                                        No authentication required. Requests will be sent without credentials.
                                    </div>
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

    _renderEditSourceModal() {
        return `
            <div class="modal fade" id="edit-source-modal" tabindex="-1" aria-labelledby="editSourceModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <form id="edit-source-form">
                            <input type="hidden" id="edit-source-id">
                            <div class="modal-header">
                                <h5 class="modal-title" id="editSourceModalLabel">
                                    <i class="bi bi-pencil-square me-2"></i>
                                    Edit Source
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="edit-source-name" class="form-label">Name <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control" id="edit-source-name" required
                                           placeholder="My API Service">
                                </div>
                                <div class="mb-3">
                                    <label for="edit-source-url" class="form-label">Service URL</label>
                                    <input type="url" class="form-control" id="edit-source-url"
                                           placeholder="https://api.example.com">
                                    <div class="form-text">Base URL of the service</div>
                                </div>
                                <div class="mb-3">
                                    <label for="edit-source-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="edit-source-description" rows="2"
                                              placeholder="Optional description of this API source"></textarea>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label text-muted">OpenAPI URL (read-only)</label>
                                    <input type="url" class="form-control" id="edit-source-openapi-url" disabled readonly>
                                    <div class="form-text">OpenAPI URL cannot be changed after registration</div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-primary" id="edit-submit-btn">
                                    <span class="spinner-border spinner-border-sm d-none me-2" id="edit-submit-spinner"></span>
                                    Save Changes
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

        // Form submissions
        this.querySelector('#add-source-form')?.addEventListener('submit', e => this._handleAddSource(e));
        this.querySelector('#edit-source-form')?.addEventListener('submit', e => this._handleEditSource(e));

        // Auth mode change handler - show/hide credential fields
        this.querySelector('#source-auth-mode')?.addEventListener('change', e => this._handleAuthModeChange(e.target.value));

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

        this.addEventListener('source-edit', e => {
            this._showEditModal(e.detail.data);
        });

        this.addEventListener('source-refresh', () => {
            // SSE will notify when refresh completes
        });
    }

    _handleAuthModeChange(authMode) {
        // Hide all auth mode field sections
        this.querySelectorAll('.auth-mode-fields').forEach(el => el.classList.add('d-none'));

        // Show the selected auth mode fields
        const fieldsId = `auth-fields-${authMode.replace('_', '-')}`;
        const fieldsEl = this.querySelector(`#${fieldsId}`);
        if (fieldsEl) {
            fieldsEl.classList.remove('d-none');
        }

        // Show/hide audience field based on auth mode
        const audienceField = this.querySelector('#source-audience')?.closest('.mb-3');
        if (audienceField) {
            // Audience is mainly for token_exchange, but can be useful for client_credentials too
            if (authMode === 'token_exchange') {
                audienceField.classList.remove('d-none');
            } else {
                audienceField.classList.add('d-none');
            }
        }
    }

    _showAddModal() {
        const modalEl = this.querySelector('#add-source-modal');
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
    }

    _showEditModal(source) {
        if (!source) return;

        // Populate form fields
        this.querySelector('#edit-source-id').value = source.id;
        this.querySelector('#edit-source-name').value = source.name || '';
        this.querySelector('#edit-source-url').value = source.url || '';
        this.querySelector('#edit-source-description').value = source.description || '';
        this.querySelector('#edit-source-openapi-url').value = source.openapi_url || source.url || '';

        const modalEl = this.querySelector('#edit-source-modal');
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

        // Auth mode display mapping
        const authModeMap = {
            none: { text: 'None (Public)', class: 'text-muted' },
            api_key: { text: 'API Key', class: 'text-warning' },
            http_basic: { text: 'HTTP Basic', class: 'text-info' },
            client_credentials: { text: 'Client Credentials', class: 'text-info' },
            token_exchange: { text: 'Token Exchange', class: 'text-success' },
        };
        const authMode = source.auth_mode?.toLowerCase() || 'token_exchange';
        const authModeDisplay = authModeMap[authMode] || authModeMap['token_exchange'];

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
                        <tr>
                            <td class="text-muted">Audience</td>
                            <td>
                                ${
                                    source.default_audience
                                        ? `<code class="small">${this._escapeHtml(source.default_audience)}</code>`
                                        : '<span class="text-muted fst-italic">None (no token exchange)</span>'
                                }
                            </td>
                        </tr>
                        <tr>
                            <td class="text-muted">Auth Mode</td>
                            <td>
                                <span class="${authModeDisplay.class}">
                                    <i class="bi bi-shield-lock me-1"></i>${authModeDisplay.text}
                                </span>
                            </td>
                        </tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6 class="text-muted mb-3">Inventory & Sync</h6>
                    <table class="table table-sm">
                        <tr>
                            <td class="text-muted" style="width: 40%">Tools Count</td>
                            <td>
                                <a href="#" class="text-decoration-none fw-medium text-primary tools-link"
                                   data-action="view-tools" data-source-id="${this._escapeHtml(source.id)}"
                                   title="View tools from this source">
                                    ${toolsCount}
                                    <i class="bi bi-box-arrow-up-right ms-1 small"></i>
                                </a>
                            </td>
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

        // Attach tools link handler for cross-navigation
        const toolsLink = detailsBody.querySelector('[data-action="view-tools"]');
        if (toolsLink) {
            toolsLink.addEventListener('click', e => {
                e.preventDefault();
                const sourceId = toolsLink.dataset.sourceId;
                if (sourceId) {
                    // Close current modal before navigating
                    const modalEl = this.querySelector('#source-details-modal');
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();
                    // Navigate to tools page with filter for this source
                    dispatchNavigationEvent('tools', 'filter-source', { sourceId, sourceName: source.name });
                }
            });
        }

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

        const audience = form.querySelector('#source-audience').value.trim();
        const openapiUrl = form.querySelector('#source-openapi-url').value.trim();
        const serviceUrl = form.querySelector('#source-url').value.trim();
        const authMode = form.querySelector('#source-auth-mode').value;

        // Build base source data
        const sourceData = {
            name: form.querySelector('#source-name').value.trim(),
            url: serviceUrl || openapiUrl, // Use service URL if provided, otherwise use openapi URL
            openapi_url: openapiUrl,
            description: form.querySelector('#source-description').value.trim() || undefined,
            default_audience: audience || undefined,
            auth_mode: authMode,
            auto_refresh: form.querySelector('#auto-refresh').checked,
        };

        // Add auth-mode specific fields
        if (authMode === 'api_key') {
            const apiKeyName = form.querySelector('#api-key-name')?.value.trim();
            const apiKeyValue = form.querySelector('#api-key-value')?.value.trim();
            const apiKeyIn = form.querySelector('#api-key-in')?.value;

            if (!apiKeyName || !apiKeyValue) {
                showToast('error', 'API Key name and value are required for API Key authentication');
                return;
            }

            sourceData.api_key_name = apiKeyName;
            sourceData.api_key_value = apiKeyValue;
            sourceData.api_key_in = apiKeyIn || 'header';
        } else if (authMode === 'http_basic') {
            const basicUsername = form.querySelector('#basic-username')?.value.trim();
            const basicPassword = form.querySelector('#basic-password')?.value.trim();

            if (!basicUsername || !basicPassword) {
                showToast('error', 'Username and password are required for HTTP Basic authentication');
                return;
            }

            sourceData.basic_username = basicUsername;
            sourceData.basic_password = basicPassword;
        } else if (authMode === 'client_credentials') {
            // Optional source-specific credentials (falls back to service account if empty)
            const oauth2ClientId = form.querySelector('#oauth2-client-id')?.value.trim();
            const oauth2ClientSecret = form.querySelector('#oauth2-client-secret')?.value.trim();
            const oauth2TokenUrl = form.querySelector('#oauth2-token-url')?.value.trim();
            const oauth2Scopes = form.querySelector('#oauth2-scopes')?.value.trim();

            if (oauth2ClientId) sourceData.oauth2_client_id = oauth2ClientId;
            if (oauth2ClientSecret) sourceData.oauth2_client_secret = oauth2ClientSecret;
            if (oauth2TokenUrl) sourceData.oauth2_token_url = oauth2TokenUrl;
            if (oauth2Scopes) sourceData.oauth2_scopes = oauth2Scopes.split(/\s+/).filter(s => s);
        }

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

    async _handleEditSource(e) {
        e.preventDefault();

        const form = e.target;
        const submitBtn = form.querySelector('#edit-submit-btn');
        const spinner = form.querySelector('#edit-submit-spinner');

        const sourceId = form.querySelector('#edit-source-id').value;
        const updateData = {
            name: form.querySelector('#edit-source-name').value.trim(),
            url: form.querySelector('#edit-source-url').value.trim() || undefined,
            description: form.querySelector('#edit-source-description').value.trim() || undefined,
        };

        submitBtn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            const updatedSource = await SourcesAPI.updateSource(sourceId, updateData);

            // Update local source data
            const index = this._sources.findIndex(s => s.id === sourceId);
            if (index !== -1) {
                this._sources[index] = updatedSource;
            }

            // Close modal
            const modal = bootstrap.Modal.getInstance(this.querySelector('#edit-source-modal'));
            modal.hide();

            showToast('success', `Source "${updateData.name}" updated successfully`);
            this.render();
        } catch (error) {
            showToast('error', `Failed to update source: ${error.message}`);
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
