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
                            Tool Sources
                        </h2>
                        <p class="text-muted mb-0">
                            Manage upstream services that provide MCP tools
                        </p>
                    </div>
                    <div class="dropdown">
                        <button type="button" class="btn btn-primary dropdown-toggle" id="add-source-dropdown"
                                data-bs-toggle="dropdown" aria-expanded="false">
                            <i class="bi bi-plus-lg me-2"></i>
                            Add Source
                        </button>
                        <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="add-source-dropdown">
                            <li>
                                <a class="dropdown-item" href="#" data-source-type="openapi">
                                    <i class="bi bi-file-code text-primary me-2"></i>
                                    <span>OpenAPI Service</span>
                                    <small class="d-block text-muted ms-4">Import tools from an OpenAPI specification</small>
                                </a>
                            </li>
                            <li>
                                <a class="dropdown-item" href="#" data-source-type="builtin">
                                    <i class="bi bi-tools text-success me-2"></i>
                                    <span>Built-in Tools</span>
                                    <small class="d-block text-muted ms-4">Utility tools (fetch URL, datetime, etc.)</small>
                                </a>
                            </li>
                            <li><hr class="dropdown-divider"></li>
                            <li>
                                <a class="dropdown-item" href="#" data-source-type="mcp">
                                    <i class="bi bi-hdd-network text-info me-2"></i>
                                    <span>MCP Plugin</span>
                                    <small class="d-block text-muted ms-4">Register a local MCP server plugin</small>
                                </a>
                            </li>
                            <li>
                                <a class="dropdown-item" href="#" data-source-type="mcp-remote">
                                    <i class="bi bi-globe text-info me-2"></i>
                                    <span>Remote MCP Server</span>
                                    <small class="d-block text-muted ms-4">Connect to an external MCP server via HTTP</small>
                                </a>
                            </li>
                            <li><hr class="dropdown-divider"></li>
                            <li>
                                <a class="dropdown-item disabled" href="#" data-source-type="workflow">
                                    <i class="bi bi-diagram-3 text-warning me-2"></i>
                                    <span>Workflow</span>
                                    <small class="d-block text-muted ms-4">Multi-step tool orchestration (coming soon)</small>
                                </a>
                            </li>
                        </ul>
                    </div>
                </div>

                ${this._loading ? this._renderLoading() : this._renderSources()}
            </div>

            ${this._renderAddSourceModal()}
            ${this._renderAddBuiltinModal()}
            ${this._renderAddMcpModal()}
            ${this._renderAddRemoteMcpModal()}
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
                    <p class="text-muted">Add a source to get started with MCP tools</p>
                    <div class="dropdown d-inline-block">
                        <button type="button" class="btn btn-primary dropdown-toggle" id="add-first-dropdown"
                                data-bs-toggle="dropdown" aria-expanded="false">
                            <i class="bi bi-plus-lg me-2"></i>
                            Add Your First Source
                        </button>
                        <ul class="dropdown-menu" aria-labelledby="add-first-dropdown">
                            <li>
                                <a class="dropdown-item" href="#" data-source-type="openapi">
                                    <i class="bi bi-file-code text-primary me-2"></i>
                                    OpenAPI Service
                                </a>
                            </li>
                            <li>
                                <a class="dropdown-item" href="#" data-source-type="builtin">
                                    <i class="bi bi-tools text-success me-2"></i>
                                    Built-in Tools
                                </a>
                            </li>
                        </ul>
                    </div>
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
                                    <div class="alert alert-warning small py-2 mb-0">
                                        <i class="bi bi-key me-1"></i>
                                        <strong>API Key authentication requires configuration in the secrets file.</strong>
                                        <hr class="my-2">
                                        <p class="mb-1">After registering this source, add credentials to <code>secrets/sources.yaml</code>:</p>
                                        <pre class="bg-dark text-light p-2 rounded small mb-0"><code>sources:
  &lt;source-id&gt;:  # Copy the ID after registration
    auth_type: api_key
    api_key_name: X-API-Key
    api_key_value: your-api-key-here
    api_key_in: header  # or "query"</code></pre>
                                        <p class="mt-2 mb-0 text-muted"><small>See <a href="/docs/architecture/secret-management/" target="_blank">Secret Management docs</a> for details.</small></p>
                                    </div>
                                </div>

                                <!-- HTTP Basic Auth Fields -->
                                <div id="auth-fields-http-basic" class="auth-mode-fields d-none">
                                    <div class="alert alert-warning small py-2 mb-0">
                                        <i class="bi bi-person-lock me-1"></i>
                                        <strong>HTTP Basic authentication requires configuration in the secrets file.</strong>
                                        <hr class="my-2">
                                        <p class="mb-1">After registering this source, add credentials to <code>secrets/sources.yaml</code>:</p>
                                        <pre class="bg-dark text-light p-2 rounded small mb-0"><code>sources:
  &lt;source-id&gt;:  # Copy the ID after registration
    auth_type: http_basic
    basic_username: your-username
    basic_password: your-password</code></pre>
                                        <p class="mt-2 mb-0 text-muted"><small>Credentials are Base64 encoded per RFC 7617. See <a href="/docs/architecture/secret-management/" target="_blank">Secret Management docs</a>.</small></p>
                                    </div>
                                </div>

                                <!-- None (Public API) Fields -->
                                <div id="auth-fields-none" class="auth-mode-fields d-none">
                                    <div class="alert alert-success small py-2">
                                        <i class="bi bi-unlock me-1"></i>
                                        No authentication required. Requests will be sent without credentials.
                                    </div>
                                </div>

                                <!-- Required Scopes (Access Control) -->
                                <div class="mb-3">
                                    <label for="source-required-scopes" class="form-label">
                                        Required Scopes
                                        <i class="bi bi-info-circle text-muted" data-bs-toggle="tooltip" data-bs-placement="right"
                                           title="OAuth2 scopes required for ALL tools from this source. Users must have these scopes to execute tools."></i>
                                    </label>
                                    <input type="text" class="form-control" id="source-required-scopes"
                                           placeholder="e.g., orders:read, orders:write">
                                    <div class="form-text">
                                        Comma-separated list of scopes. Leave empty to use auto-discovered scopes from OpenAPI.
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

    _renderAddBuiltinModal() {
        return `
            <div class="modal fade" id="add-builtin-modal" tabindex="-1" aria-labelledby="addBuiltinModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <form id="add-builtin-form">
                            <div class="modal-header">
                                <h5 class="modal-title" id="addBuiltinModalLabel">
                                    <i class="bi bi-tools text-success me-2"></i>
                                    Add Built-in Tools
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="alert alert-info">
                                    <i class="bi bi-info-circle me-2"></i>
                                    <strong>Built-in tools</strong> are utility tools that run locally within the Tools Provider.
                                    They don't require external API calls.
                                </div>

                                <div class="mb-3">
                                    <label for="builtin-name" class="form-label">Name <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control" id="builtin-name" required
                                           value="Built-in Utilities" placeholder="Built-in Utilities">
                                    <div class="form-text">A friendly name for this tool collection</div>
                                </div>

                                <div class="mb-3">
                                    <label for="builtin-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="builtin-description" rows="2"
                                              placeholder="Optional description">Utility tools for fetching URLs, date/time operations, encoding, and more.</textarea>
                                </div>

                                <h6 class="mb-3">Included Tools (17):</h6>
                                <div class="list-group list-group-flush small" style="max-height: 400px; overflow-y: auto;">
                                    <!-- Utility Tools -->
                                    <div class="list-group-item bg-light fw-bold px-0 pt-2 pb-1 border-0">
                                        <i class="bi bi-wrench me-1"></i> Utility Tools
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-globe text-primary me-2 mt-1"></i>
                                        <div>
                                            <strong>fetch_url</strong>
                                            <span class="text-muted ms-1">— Download content from URLs (web pages, files, APIs)</span>
                                        </div>
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-clock text-primary me-2 mt-1"></i>
                                        <div>
                                            <strong>get_current_datetime</strong>
                                            <span class="text-muted ms-1">— Get current date/time with timezone support</span>
                                        </div>
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-calculator text-primary me-2 mt-1"></i>
                                        <div>
                                            <strong>calculate</strong>
                                            <span class="text-muted ms-1">— Safe mathematical expression evaluation</span>
                                        </div>
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-upc text-primary me-2 mt-1"></i>
                                        <div>
                                            <strong>generate_uuid</strong>
                                            <span class="text-muted ms-1">— Generate unique identifiers</span>
                                        </div>
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-code text-primary me-2 mt-1"></i>
                                        <div>
                                            <strong>encode_decode</strong>, <strong>regex_extract</strong>, <strong>json_transform</strong>, <strong>text_stats</strong>
                                            <span class="text-muted ms-1">— Text and data transformation utilities</span>
                                        </div>
                                    </div>

                                    <!-- Web & Search Tools -->
                                    <div class="list-group-item bg-light fw-bold px-0 pt-3 pb-1 border-0">
                                        <i class="bi bi-search me-1"></i> Web & Search Tools
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-google text-success me-2 mt-1"></i>
                                        <div>
                                            <strong>web_search</strong>
                                            <span class="text-muted ms-1">— Search the web using DuckDuckGo</span>
                                        </div>
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-wikipedia text-dark me-2 mt-1"></i>
                                        <div>
                                            <strong>wikipedia_query</strong>
                                            <span class="text-muted ms-1">— Search and retrieve Wikipedia articles</span>
                                        </div>
                                    </div>

                                    <!-- Code Execution -->
                                    <div class="list-group-item bg-light fw-bold px-0 pt-3 pb-1 border-0">
                                        <i class="bi bi-terminal me-1"></i> Code Execution
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-filetype-py text-warning me-2 mt-1"></i>
                                        <div>
                                            <strong>execute_python</strong>
                                            <span class="text-muted ms-1">— Execute Python code in a sandboxed environment</span>
                                        </div>
                                    </div>

                                    <!-- File Tools -->
                                    <div class="list-group-item bg-light fw-bold px-0 pt-3 pb-1 border-0">
                                        <i class="bi bi-folder me-1"></i> File Tools
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-file-earmark-arrow-down text-info me-2 mt-1"></i>
                                        <div>
                                            <strong>file_writer</strong>
                                            <span class="text-muted ms-1">— Write content to files in the workspace</span>
                                        </div>
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-file-earmark-arrow-up text-info me-2 mt-1"></i>
                                        <div>
                                            <strong>file_reader</strong>
                                            <span class="text-muted ms-1">— Read content from files in the workspace</span>
                                        </div>
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-file-earmark-excel text-success me-2 mt-1"></i>
                                        <div>
                                            <strong>spreadsheet_read</strong>
                                            <span class="text-muted ms-1">— Read Excel/XLSX spreadsheets with pagination and stats</span>
                                        </div>
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-file-earmark-spreadsheet text-success me-2 mt-1"></i>
                                        <div>
                                            <strong>spreadsheet_write</strong>
                                            <span class="text-muted ms-1">— Create and edit Excel/XLSX spreadsheets</span>
                                        </div>
                                    </div>

                                    <!-- Memory Tools -->
                                    <div class="list-group-item bg-light fw-bold px-0 pt-3 pb-1 border-0">
                                        <i class="bi bi-memory me-1"></i> Memory Tools
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-box-arrow-in-down text-purple me-2 mt-1" style="color: #6f42c1;"></i>
                                        <div>
                                            <strong>memory_store</strong>
                                            <span class="text-muted ms-1">— Store key-value pairs for later retrieval (per user)</span>
                                        </div>
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-box-arrow-up text-purple me-2 mt-1" style="color: #6f42c1;"></i>
                                        <div>
                                            <strong>memory_retrieve</strong>
                                            <span class="text-muted ms-1">— Retrieve stored values by key (per user)</span>
                                        </div>
                                    </div>

                                    <!-- Human Interaction -->
                                    <div class="list-group-item bg-light fw-bold px-0 pt-3 pb-1 border-0">
                                        <i class="bi bi-person-raised-hand me-1"></i> Human Interaction
                                    </div>
                                    <div class="list-group-item d-flex align-items-start px-0 py-1">
                                        <i class="bi bi-chat-dots text-danger me-2 mt-1"></i>
                                        <div>
                                            <strong>ask_human</strong>
                                            <span class="text-muted ms-1">— Request input or clarification from the user</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-success" id="submit-builtin-btn">
                                    <span class="spinner-border spinner-border-sm d-none me-2" id="submit-builtin-spinner"></span>
                                    <i class="bi bi-plus-lg me-2"></i>
                                    Add Built-in Tools
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
    }

    _renderAddMcpModal() {
        return `
            <div class="modal fade" id="add-mcp-modal" tabindex="-1" aria-labelledby="addMcpModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content">
                        <form id="add-mcp-form">
                            <div class="modal-header">
                                <h5 class="modal-title" id="addMcpModalLabel">
                                    <i class="bi bi-hdd-network text-info me-2"></i>
                                    Add MCP Plugin
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="alert alert-info">
                                    <i class="bi bi-info-circle me-2"></i>
                                    <strong>MCP Plugins</strong> are Model Context Protocol servers that run as local subprocesses.
                                    They expose tools via JSON-RPC over stdio or SSE transport.
                                </div>

                                <div class="mb-3">
                                    <label for="mcp-name" class="form-label">Name <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control" id="mcp-name" required
                                           placeholder="My MCP Plugin">
                                    <div class="form-text">A friendly name for this plugin</div>
                                </div>

                                <div class="mb-3">
                                    <label for="mcp-plugin-dir" class="form-label">
                                        Plugin Directory <span class="text-danger">*</span>
                                        <i class="bi bi-info-circle text-muted" data-bs-toggle="tooltip" data-bs-placement="right"
                                           title="Absolute path to the directory containing the MCP plugin and its server.json manifest."></i>
                                    </label>
                                    <input type="text" class="form-control" id="mcp-plugin-dir" required
                                           placeholder="/path/to/mcp-plugins/my-plugin">
                                    <div class="form-text">Absolute path containing the plugin files and server.json manifest</div>
                                </div>

                                <div class="mb-3">
                                    <label for="mcp-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="mcp-description" rows="2"
                                              placeholder="Optional description of this MCP plugin"></textarea>
                                </div>

                                <hr class="my-3">
                                <h6 class="mb-3"><i class="bi bi-gear me-1"></i> Transport & Lifecycle</h6>

                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label for="mcp-transport-type" class="form-label">
                                                Transport Type
                                                <i class="bi bi-info-circle text-muted" data-bs-toggle="tooltip" data-bs-placement="right"
                                                   title="How to communicate with the MCP server. STDIO uses stdin/stdout JSON-RPC, SSE uses HTTP streaming."></i>
                                            </label>
                                            <select class="form-select" id="mcp-transport-type">
                                                <option value="stdio" selected>STDIO (stdin/stdout)</option>
                                                <option value="sse">SSE (HTTP Streaming)</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label for="mcp-lifecycle-mode" class="form-label">
                                                Lifecycle Mode
                                                <i class="bi bi-info-circle text-muted" data-bs-toggle="tooltip" data-bs-placement="right"
                                                   title="How to manage the subprocess. Transient spawns per request, Singleton keeps alive."></i>
                                            </label>
                                            <select class="form-select" id="mcp-lifecycle-mode">
                                                <option value="transient" selected>Transient (per-request)</option>
                                                <option value="singleton">Singleton (keep-alive)</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>

                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label for="mcp-runtime-hint" class="form-label">
                                                Runtime Hint
                                                <i class="bi bi-info-circle text-muted" data-bs-toggle="tooltip" data-bs-placement="right"
                                                   title="Preferred runtime to use when starting the plugin. Leave empty for auto-detection."></i>
                                            </label>
                                            <select class="form-select" id="mcp-runtime-hint">
                                                <option value="" selected>Auto-detect</option>
                                                <option value="uvx">uvx (Python)</option>
                                                <option value="npx">npx (Node.js)</option>
                                                <option value="python">python</option>
                                                <option value="node">node</option>
                                                <option value="docker">docker</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label for="mcp-command" class="form-label">
                                                Custom Command
                                                <i class="bi bi-info-circle text-muted" data-bs-toggle="tooltip" data-bs-placement="right"
                                                   title="Override the start command from the manifest. Leave empty to use manifest defaults."></i>
                                            </label>
                                            <input type="text" class="form-control" id="mcp-command"
                                                   placeholder="e.g., python -m my_plugin">
                                            <div class="form-text">Optional: Overrides manifest command</div>
                                        </div>
                                    </div>
                                </div>

                                <hr class="my-3">
                                <h6 class="mb-3"><i class="bi bi-key me-1"></i> Environment Variables</h6>

                                <div class="mb-3">
                                    <div class="alert alert-secondary small py-2">
                                        <i class="bi bi-lightbulb me-1"></i>
                                        Add environment variables required by the plugin. For secrets, use the format
                                        <code>\${secrets:secret_name}</code> to reference values from the secrets store.
                                    </div>
                                    <div id="mcp-env-vars-container">
                                        <!-- Dynamic env var rows will be added here -->
                                    </div>
                                    <button type="button" class="btn btn-sm btn-outline-secondary mt-2" id="add-env-var-btn">
                                        <i class="bi bi-plus me-1"></i>
                                        Add Environment Variable
                                    </button>
                                </div>

                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="mcp-validate" checked>
                                        <label class="form-check-label" for="mcp-validate">
                                            Validate plugin before registration
                                        </label>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-info" id="submit-mcp-btn">
                                    <span class="spinner-border spinner-border-sm d-none me-2" id="submit-mcp-spinner"></span>
                                    <i class="bi bi-plus-lg me-2"></i>
                                    Add MCP Plugin
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
    }

    _renderAddRemoteMcpModal() {
        return `
            <div class="modal fade" id="add-remote-mcp-modal" tabindex="-1" aria-labelledby="addRemoteMcpModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content">
                        <form id="add-remote-mcp-form">
                            <div class="modal-header">
                                <h5 class="modal-title" id="addRemoteMcpModalLabel">
                                    <i class="bi bi-cloud text-primary me-2"></i>
                                    Add Remote MCP Server
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="alert alert-info">
                                    <i class="bi bi-info-circle me-2"></i>
                                    <strong>Remote MCP Servers</strong> are externally-managed Model Context Protocol servers
                                    accessible over HTTP. They expose tools via JSON-RPC using the Streamable HTTP transport.
                                </div>

                                <div class="mb-3">
                                    <label for="remote-mcp-name" class="form-label">Name <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control" id="remote-mcp-name" required
                                           placeholder="My Remote MCP Server">
                                    <div class="form-text">A friendly name for this remote MCP server</div>
                                </div>

                                <div class="mb-3">
                                    <label for="remote-mcp-server-url" class="form-label">
                                        Server URL <span class="text-danger">*</span>
                                        <i class="bi bi-info-circle text-muted" data-bs-toggle="tooltip" data-bs-placement="right"
                                           title="The base URL of the remote MCP server. The server should expose a /mcp endpoint for JSON-RPC and optionally a /health endpoint."></i>
                                    </label>
                                    <input type="url" class="form-control" id="remote-mcp-server-url" required
                                           placeholder="http://cml-mcp:9000">
                                    <div class="form-text">Base URL of the remote MCP server (e.g., http://cml-mcp:9000)</div>
                                </div>

                                <div class="mb-3">
                                    <label for="remote-mcp-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="remote-mcp-description" rows="2"
                                              placeholder="Optional description of this remote MCP server"></textarea>
                                </div>

                                <hr class="my-3">
                                <h6 class="mb-3"><i class="bi bi-key me-1"></i> Environment Variables (Optional)</h6>

                                <div class="mb-3">
                                    <div class="alert alert-secondary small py-2">
                                        <i class="bi bi-lightbulb me-1"></i>
                                        Add environment variables to pass to the remote server. These will be sent as headers
                                        with the <code>X-MCP-Env-</code> prefix. For secrets, use <code>\${secrets:secret_name}</code>.
                                    </div>
                                    <div id="remote-mcp-env-vars-container">
                                        <!-- Dynamic env var rows will be added here -->
                                    </div>
                                    <button type="button" class="btn btn-sm btn-outline-secondary mt-2" id="add-remote-env-var-btn">
                                        <i class="bi bi-plus me-1"></i>
                                        Add Environment Variable
                                    </button>
                                </div>

                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="remote-mcp-validate" checked>
                                        <label class="form-check-label" for="remote-mcp-validate">
                                            Validate server connectivity before registration
                                        </label>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-primary" id="submit-remote-mcp-btn">
                                    <span class="spinner-border spinner-border-sm d-none me-2" id="submit-remote-mcp-spinner"></span>
                                    <i class="bi bi-plus-lg me-2"></i>
                                    Add Remote MCP Server
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
                                    <label for="edit-source-required-scopes" class="form-label">
                                        Required Scopes
                                        <i class="bi bi-info-circle text-muted" data-bs-toggle="tooltip" data-bs-placement="right"
                                           title="OAuth2 scopes required for ALL tools from this source. Users must have these scopes to execute tools."></i>
                                    </label>
                                    <input type="text" class="form-control" id="edit-source-required-scopes"
                                           placeholder="e.g., orders:read, orders:write">
                                    <div class="form-text">
                                        Comma-separated list of scopes. Leave empty to use auto-discovered scopes.
                                    </div>
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
        // Source type dropdown handlers
        this.querySelectorAll('[data-source-type]').forEach(item => {
            item.addEventListener('click', e => {
                e.preventDefault();
                const sourceType = item.dataset.sourceType;
                if (item.classList.contains('disabled')) return;

                if (sourceType === 'openapi') {
                    this._showAddModal();
                } else if (sourceType === 'builtin') {
                    this._showAddBuiltinModal();
                } else if (sourceType === 'mcp') {
                    this._showAddMcpModal();
                } else if (sourceType === 'mcp-remote') {
                    this._showAddRemoteMcpModal();
                }
                // Future: handle 'workflow' type
            });
        });

        // Form submissions
        this.querySelector('#add-source-form')?.addEventListener('submit', e => this._handleAddSource(e));
        this.querySelector('#add-builtin-form')?.addEventListener('submit', e => this._handleAddBuiltin(e));
        this.querySelector('#add-mcp-form')?.addEventListener('submit', e => this._handleAddMcp(e));
        this.querySelector('#add-remote-mcp-form')?.addEventListener('submit', e => this._handleAddRemoteMcp(e));
        this.querySelector('#edit-source-form')?.addEventListener('submit', e => this._handleEditSource(e));

        // MCP environment variable add button
        this.querySelector('#add-env-var-btn')?.addEventListener('click', () => this._addEnvVarRow());
        this.querySelector('#add-remote-env-var-btn')?.addEventListener('click', () => this._addRemoteEnvVarRow());

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

    _showAddBuiltinModal() {
        const modalEl = this.querySelector('#add-builtin-modal');
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
    }

    _showAddMcpModal() {
        const modalEl = this.querySelector('#add-mcp-modal');
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        // Clear any existing env var rows
        const container = this.querySelector('#mcp-env-vars-container');
        if (container) {
            container.innerHTML = '';
        }
        modal.show();
    }

    _addEnvVarRow() {
        const container = this.querySelector('#mcp-env-vars-container');
        if (!container) return;

        const rowId = `env-var-${Date.now()}`;
        const row = document.createElement('div');
        row.className = 'row mb-2 env-var-row';
        row.id = rowId;
        row.innerHTML = `
            <div class="col-5">
                <input type="text" class="form-control form-control-sm env-var-name"
                       placeholder="Variable name (e.g., API_KEY)">
            </div>
            <div class="col-5">
                <input type="text" class="form-control form-control-sm env-var-value"
                       placeholder="Value or \${secrets:name}">
            </div>
            <div class="col-2">
                <button type="button" class="btn btn-sm btn-outline-danger remove-env-var-btn" data-row-id="${rowId}">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        `;
        container.appendChild(row);

        // Add remove handler
        row.querySelector('.remove-env-var-btn').addEventListener('click', e => {
            const rowToRemove = document.getElementById(e.currentTarget.dataset.rowId);
            if (rowToRemove) rowToRemove.remove();
        });
    }

    _showAddRemoteMcpModal() {
        const modalEl = this.querySelector('#add-remote-mcp-modal');
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        // Clear any existing env var rows
        const container = this.querySelector('#remote-mcp-env-vars-container');
        if (container) {
            container.innerHTML = '';
        }
        modal.show();
    }

    _addRemoteEnvVarRow() {
        const container = this.querySelector('#remote-mcp-env-vars-container');
        if (!container) return;

        const rowId = `remote-env-var-${Date.now()}`;
        const row = document.createElement('div');
        row.className = 'row mb-2 remote-env-var-row';
        row.id = rowId;
        row.innerHTML = `
            <div class="col-5">
                <input type="text" class="form-control form-control-sm remote-env-var-name"
                       placeholder="Variable name (e.g., API_KEY)">
            </div>
            <div class="col-5">
                <input type="text" class="form-control form-control-sm remote-env-var-value"
                       placeholder="Value or \${secrets:name}">
            </div>
            <div class="col-2">
                <button type="button" class="btn btn-sm btn-outline-danger remove-remote-env-var-btn" data-row-id="${rowId}">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        `;
        container.appendChild(row);

        // Add remove handler
        row.querySelector('.remove-remote-env-var-btn').addEventListener('click', e => {
            const rowToRemove = document.getElementById(e.currentTarget.dataset.rowId);
            if (rowToRemove) rowToRemove.remove();
        });
    }

    _showEditModal(source) {
        if (!source) return;

        // Populate form fields
        this.querySelector('#edit-source-id').value = source.id;
        this.querySelector('#edit-source-name').value = source.name || '';
        this.querySelector('#edit-source-url').value = source.url || '';
        this.querySelector('#edit-source-description').value = source.description || '';
        this.querySelector('#edit-source-openapi-url').value = source.openapi_url || source.url || '';
        // Display required_scopes as comma-separated string
        const scopes = source.required_scopes || [];
        this.querySelector('#edit-source-required-scopes').value = scopes.join(', ');

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
        // For built-in sources, show 'Local' instead of 'Public' since they execute in-process
        const isBuiltin = source.source_type?.toLowerCase() === 'builtin';
        let authModeDisplay;
        if (isBuiltin) {
            authModeDisplay = { text: 'Local (No upstream auth needed)', class: 'text-success' };
        } else {
            authModeDisplay = authModeMap[authMode] || authModeMap['token_exchange'];
        }

        // Source type display mapping
        const sourceTypeMap = {
            openapi: { icon: 'bi-file-code', text: 'OpenAPI', class: 'text-primary' },
            builtin: { icon: 'bi-tools', text: 'Built-in', class: 'text-success' },
            workflow: { icon: 'bi-diagram-3', text: 'Workflow', class: 'text-warning' },
            mcp: { icon: 'bi-hdd-network', text: 'MCP Plugin', class: 'text-info' },
        };
        const sourceType = source.source_type?.toLowerCase() || 'openapi';
        // Check if this is a remote MCP server
        const isRemoteMcp = sourceType === 'mcp' && source.mcp_config?.server_url != null;
        let sourceTypeDisplay;
        if (isRemoteMcp) {
            sourceTypeDisplay = { icon: 'bi-cloud', text: 'Remote MCP', class: 'text-primary' };
        } else {
            sourceTypeDisplay = sourceTypeMap[sourceType] || sourceTypeMap['openapi'];
        }
        const isMcp = sourceType === 'mcp';

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
                            <td>
                                <span class="${sourceTypeDisplay.class}">
                                    <i class="bi ${sourceTypeDisplay.icon} me-1"></i>${sourceTypeDisplay.text}
                                </span>
                            </td>
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
                        <tr>
                            <td class="text-muted">Required Scopes</td>
                            <td>
                                ${
                                    source.required_scopes && source.required_scopes.length > 0
                                        ? source.required_scopes.map(s => `<span class="badge bg-info text-dark me-1">${this._escapeHtml(s)}</span>`).join('')
                                        : '<span class="text-muted fst-italic">None (public)</span>'
                                }
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
            ${isMcp ? this._renderMcpDetailsSection(source) : this._renderUrlSection(source)}
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

    _renderUrlSection(source) {
        return `
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
    }

    _renderMcpDetailsSection(source) {
        const mcpConfig = source.mcp_config || {};
        const isRemote = mcpConfig.server_url != null;
        const transportTypes = {
            stdio: 'STDIO (stdin/stdout)',
            sse: 'SSE (HTTP Streaming)',
            streamable_http: 'Streamable HTTP (Remote)',
        };
        const lifecycleModes = { transient: 'Transient (per-request)', singleton: 'Singleton (keep-alive)' };

        const transportDisplay = transportTypes[mcpConfig.transport_type?.toLowerCase()] || mcpConfig.transport_type || 'Unknown';
        const lifecycleDisplay = lifecycleModes[mcpConfig.lifecycle_mode?.toLowerCase()] || mcpConfig.lifecycle_mode || 'Unknown';
        const envVars = mcpConfig.environment || {};
        const envVarCount = Object.keys(envVars).length;

        // Different header and layout for remote vs local
        const headerIcon = isRemote ? 'bi-cloud' : 'bi-hdd-network';
        const headerText = isRemote ? 'Remote MCP Server Configuration' : 'MCP Plugin Configuration';

        return `
            <div class="mt-3">
                <h6 class="text-muted mb-2"><i class="bi ${headerIcon} me-1"></i> ${headerText}</h6>
                <div class="row">
                    <div class="col-md-6">
                        <table class="table table-sm">
                            ${
                                isRemote
                                    ? `
                            <tr>
                                <td class="text-muted" style="width: 40%">Server URL</td>
                                <td>
                                    <a href="${this._escapeHtml(mcpConfig.server_url)}" target="_blank" class="text-decoration-none">
                                        <code class="small text-break">${this._escapeHtml(mcpConfig.server_url)}</code>
                                        <i class="bi bi-box-arrow-up-right ms-1 small"></i>
                                    </a>
                                </td>
                            </tr>
                            `
                                    : `
                            <tr>
                                <td class="text-muted" style="width: 40%">Plugin Directory</td>
                                <td>
                                    <code class="small text-break">${this._escapeHtml(mcpConfig.plugin_dir || 'N/A')}</code>
                                </td>
                            </tr>
                            `
                            }
                            <tr>
                                <td class="text-muted">Transport</td>
                                <td><span class="badge ${isRemote ? 'bg-primary' : 'bg-info'} text-dark">${this._escapeHtml(transportDisplay)}</span></td>
                            </tr>
                            ${
                                !isRemote
                                    ? `
                            <tr>
                                <td class="text-muted">Lifecycle</td>
                                <td><span class="badge bg-secondary">${this._escapeHtml(lifecycleDisplay)}</span></td>
                            </tr>
                            `
                                    : ''
                            }
                        </table>
                    </div>
                    <div class="col-md-6">
                        <table class="table table-sm">
                            ${
                                !isRemote
                                    ? `
                            <tr>
                                <td class="text-muted" style="width: 40%">Runtime</td>
                                <td><code class="small">${this._escapeHtml(mcpConfig.runtime_hint || 'auto')}</code></td>
                            </tr>
                            <tr>
                                <td class="text-muted">Command</td>
                                <td><code class="small text-break">${this._escapeHtml((mcpConfig.command || []).join(' ') || 'From manifest')}</code></td>
                            </tr>
                            `
                                    : `
                            <tr>
                                <td class="text-muted" style="width: 40%">Type</td>
                                <td><span class="badge bg-success">Externally Managed</span></td>
                            </tr>
                            `
                            }
                            <tr>
                                <td class="text-muted">Environment</td>
                                <td>
                                    ${
                                        envVarCount > 0
                                            ? `<span class="badge bg-secondary">${envVarCount} variable${envVarCount > 1 ? 's' : ''}</span>`
                                            : '<span class="text-muted fst-italic">None</span>'
                                    }
                                </td>
                            </tr>
                        </table>
                    </div>
                </div>
                ${
                    envVarCount > 0
                        ? `
                    <div class="mt-2">
                        <details>
                            <summary class="text-muted small cursor-pointer">
                                <i class="bi bi-key me-1"></i>Environment Variables
                            </summary>
                            <div class="mt-2">
                                <table class="table table-sm table-bordered">
                                    <thead class="table-light">
                                        <tr>
                                            <th class="small">Name</th>
                                            <th class="small">Value</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${Object.entries(envVars)
                                            .map(
                                                ([k, v]) => `
                                            <tr>
                                                <td><code class="small">${this._escapeHtml(k)}</code></td>
                                                <td class="small text-break">${v.includes('secrets:') ? '<span class="text-muted">[secret reference]</span>' : this._escapeHtml(v)}</td>
                                            </tr>
                                        `
                                            )
                                            .join('')}
                                    </tbody>
                                </table>
                            </div>
                        </details>
                    </div>
                `
                        : ''
                }
            </div>
        `;
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

        // Parse required scopes (comma-separated)
        const requiredScopesInput = form.querySelector('#source-required-scopes').value.trim();
        const requiredScopes = requiredScopesInput
            ? requiredScopesInput
                  .split(',')
                  .map(s => s.trim())
                  .filter(s => s)
            : undefined;

        // Build base source data
        const sourceData = {
            name: form.querySelector('#source-name').value.trim(),
            url: serviceUrl || openapiUrl, // Use service URL if provided, otherwise use openapi URL
            openapi_url: openapiUrl,
            description: form.querySelector('#source-description').value.trim() || undefined,
            default_audience: audience || undefined,
            auth_mode: authMode,
            required_scopes: requiredScopes,
            auto_refresh: form.querySelector('#auto-refresh').checked,
        };

        // Add auth-mode specific fields
        // Note: api_key and http_basic credentials are configured via secrets/sources.yaml file,
        // not through this form. Only auth_mode is persisted to indicate the expected auth type.
        if (authMode === 'client_credentials') {
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

            // Show appropriate success message based on auth mode
            if (authMode === 'api_key' || authMode === 'http_basic') {
                showToast('success', `Source "${sourceData.name}" registered. Configure credentials in secrets/sources.yaml using ID: ${newSource.id}`);
            } else {
                showToast('success', `Source "${sourceData.name}" added successfully`);
            }
            this.render();
        } catch (error) {
            showToast('error', `Failed to add source: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    }

    async _handleAddBuiltin(e) {
        e.preventDefault();

        const form = e.target;
        const submitBtn = form.querySelector('#submit-builtin-btn');
        const spinner = form.querySelector('#submit-builtin-spinner');

        const sourceData = {
            name: form.querySelector('#builtin-name').value.trim(),
            url: 'builtin://tools', // Special URL for built-in tools
            source_type: 'builtin',
            description: form.querySelector('#builtin-description').value.trim() || 'Built-in utility tools',
            auth_mode: 'none', // Built-in tools don't need external auth
            validate_url: false, // Skip URL validation for builtin://
        };

        submitBtn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            const newSource = await SourcesAPI.registerSource(sourceData);
            this._sources.push(newSource);

            // Close modal and reset form
            const modal = bootstrap.Modal.getInstance(this.querySelector('#add-builtin-modal'));
            modal.hide();
            form.reset();

            showToast('success', `Built-in tools "${sourceData.name}" added successfully! ${newSource.tools_count || 17} tools are now available.`);
            this.render();
        } catch (error) {
            showToast('error', `Failed to add built-in tools: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    }

    async _handleAddMcp(e) {
        e.preventDefault();

        const form = e.target;
        const submitBtn = form.querySelector('#submit-mcp-btn');
        const spinner = form.querySelector('#submit-mcp-spinner');

        const pluginDir = form.querySelector('#mcp-plugin-dir').value.trim();
        const name = form.querySelector('#mcp-name').value.trim();

        // Collect environment variables from dynamic rows
        const envVars = {};
        const envVarRows = this.querySelectorAll('.env-var-row');
        envVarRows.forEach(row => {
            const varName = row.querySelector('.env-var-name')?.value.trim();
            const varValue = row.querySelector('.env-var-value')?.value.trim();
            if (varName && varValue) {
                envVars[varName] = varValue;
            }
        });

        const sourceData = {
            name: name,
            url: `mcp://${pluginDir}`, // MCP URL scheme
            source_type: 'mcp',
            description: form.querySelector('#mcp-description').value.trim() || `MCP Plugin: ${name}`,
            auth_mode: 'none', // MCP plugins don't use external auth
            validate_url: form.querySelector('#mcp-validate').checked,

            // MCP-specific fields
            mcp_plugin_dir: pluginDir,
            mcp_transport_type: form.querySelector('#mcp-transport-type').value,
            mcp_lifecycle_mode: form.querySelector('#mcp-lifecycle-mode').value,
            mcp_runtime_hint: form.querySelector('#mcp-runtime-hint').value || undefined,
            mcp_command: form.querySelector('#mcp-command').value.trim() || undefined,
            mcp_env_vars: Object.keys(envVars).length > 0 ? envVars : undefined,
        };

        submitBtn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            const newSource = await SourcesAPI.registerSource(sourceData);
            this._sources.push(newSource);

            // Close modal and reset form
            const modal = bootstrap.Modal.getInstance(this.querySelector('#add-mcp-modal'));
            modal.hide();
            form.reset();

            // Clear env var rows
            const envContainer = this.querySelector('#mcp-env-vars-container');
            if (envContainer) envContainer.innerHTML = '';

            const toolsCount = newSource.tools_count || newSource.inventory_count || 0;
            showToast('success', `MCP Plugin "${sourceData.name}" added successfully! ${toolsCount} tools discovered.`);
            this.render();
        } catch (error) {
            showToast('error', `Failed to add MCP plugin: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    }

    async _handleAddRemoteMcp(e) {
        e.preventDefault();

        const form = e.target;
        const submitBtn = form.querySelector('#submit-remote-mcp-btn');
        const spinner = form.querySelector('#submit-remote-mcp-spinner');

        const serverUrl = form.querySelector('#remote-mcp-server-url').value.trim();
        const name = form.querySelector('#remote-mcp-name').value.trim();

        // Collect environment variables from dynamic rows
        const envVars = {};
        const envVarRows = this.querySelectorAll('.remote-env-var-row');
        envVarRows.forEach(row => {
            const varName = row.querySelector('.remote-env-var-name')?.value.trim();
            const varValue = row.querySelector('.remote-env-var-value')?.value.trim();
            if (varName && varValue) {
                envVars[varName] = varValue;
            }
        });

        const sourceData = {
            name: name,
            url: serverUrl, // Use the server URL as the source URL
            source_type: 'mcp',
            description: form.querySelector('#remote-mcp-description').value.trim() || `Remote MCP Server: ${name}`,
            auth_mode: 'none', // Auth handled by the remote server
            validate_url: form.querySelector('#remote-mcp-validate').checked,

            // Remote MCP-specific fields
            mcp_server_url: serverUrl,
            mcp_env_vars: Object.keys(envVars).length > 0 ? envVars : undefined,
        };

        submitBtn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            const newSource = await SourcesAPI.registerSource(sourceData);
            this._sources.push(newSource);

            // Close modal and reset form
            const modal = bootstrap.Modal.getInstance(this.querySelector('#add-remote-mcp-modal'));
            modal.hide();
            form.reset();

            // Clear env var rows
            const envContainer = this.querySelector('#remote-mcp-env-vars-container');
            if (envContainer) envContainer.innerHTML = '';

            const toolsCount = newSource.tools_count || newSource.inventory_count || 0;
            showToast('success', `Remote MCP Server "${sourceData.name}" added successfully! ${toolsCount} tools discovered.`);
            this.render();
        } catch (error) {
            showToast('error', `Failed to add remote MCP server: ${error.message}`);
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

        // Parse required scopes (comma-separated)
        const requiredScopesInput = form.querySelector('#edit-source-required-scopes').value.trim();
        const requiredScopes = requiredScopesInput
            ? requiredScopesInput
                  .split(',')
                  .map(s => s.trim())
                  .filter(s => s)
            : [];

        const updateData = {
            name: form.querySelector('#edit-source-name').value.trim(),
            url: form.querySelector('#edit-source-url').value.trim() || undefined,
            description: form.querySelector('#edit-source-description').value.trim() || undefined,
            required_scopes: requiredScopes,
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
