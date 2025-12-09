/**
 * Tools Page Component
 *
 * Admin page for managing MCP tools.
 */

import * as bootstrap from 'bootstrap';
import { eventBus } from '../core/event-bus.js';
import * as ToolsAPI from '../api/tools.js';
import * as GroupsAPI from '../api/groups.js';
import * as LabelsAPI from '../api/labels.js';
import { showToast } from '../components/toast-notification.js';
import { ToolCard } from '../components/tool-card.js';
import { isAuthenticated } from '../api/client.js';
import { dispatchNavigationEvent } from '../core/modal-utils.js';
import { getToolDisplayName } from '../core/tool-utils.js';

class ToolsPage extends HTMLElement {
    constructor() {
        super();
        this._tools = [];
        this._labels = []; // Cache labels for display
        this._loading = true;
        this._viewMode = 'table'; // 'grid' or 'table'
        this._filterEnabled = null; // null = all, true = enabled, false = disabled
        this._filterMethod = null; // null = all, or specific method
        this._filterTag = null; // null = all, or specific OpenAPI tag
        this._filterSource = null; // null = all, or specific source ID
        this._filterLabel = null; // null = all, or specific label ID
        this._searchTerm = '';
        this._searchDebounceTimer = null;
        this._eventSubscriptions = [];
        this._selectedToolIds = new Set(); // Track selected tools for group creation
        this._syncStatus = null; // Track tool sync health status
    }

    connectedCallback() {
        this.render();
        this._loadTools();
        this._subscribeToEvents();

        // Listen for external navigation events (e.g., from group cards)
        this.addEventListener('open-tool-details', async e => {
            const { toolId } = e.detail || {};
            if (toolId) {
                await this._openToolDetailsById(toolId);
            }
        });

        // Listen for filter requests (e.g., from source details)
        this.addEventListener('open-filter-source', async e => {
            const { sourceId } = e.detail || {};
            if (sourceId) {
                // Wait for page to render
                await new Promise(resolve => setTimeout(resolve, 150));
                this._filterSource = sourceId;
                this.render();
            }
        });
    }

    disconnectedCallback() {
        this._unsubscribeFromEvents();
    }

    /**
     * Open tool details modal by tool ID (for cross-entity navigation)
     */
    async _openToolDetailsById(toolId) {
        // Wait for tools to load if not yet loaded
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

        // Find the tool in loaded tools
        let tool = this._tools.find(t => t.id === toolId);

        // If not found, try to fetch it directly
        if (!tool) {
            try {
                tool = await ToolsAPI.getTool(toolId);
            } catch (error) {
                console.error('Failed to fetch tool:', error);
                showToast('error', `Tool not found: ${toolId}`);
                return;
            }
        }

        if (tool) {
            this._showToolDetails(tool);
        }
    }

    async _loadTools() {
        // Skip loading if not authenticated (avoids console errors)
        if (!isAuthenticated()) {
            this._loading = false;
            this._tools = [];
            this._labels = [];
            this.render();
            return;
        }

        this._loading = true;
        this.render();

        try {
            // Load tools and labels in parallel
            const [tools, labels] = await Promise.all([
                ToolsAPI.getTools(),
                LabelsAPI.getLabels().catch(() => []), // Labels are optional
            ]);
            this._tools = tools;
            this._labels = labels;

            // Check sync status in background (don't block UI)
            this._checkSyncStatus();
        } catch (error) {
            // Don't show toast for auth errors - user will be redirected to login
            if (!error.message?.includes('Session expired')) {
                showToast('error', `Failed to load tools: ${error.message}`);
            }
            this._tools = [];
            this._labels = [];
        } finally {
            this._loading = false;
            this.render();
        }
    }

    _subscribeToEvents() {
        this._eventSubscriptions.push(
            eventBus.subscribe('tool:enabled', data => {
                this._updateToolStatus(data.tool_id, true);
            }),
            eventBus.subscribe('tool:disabled', data => {
                this._updateToolStatus(data.tool_id, false);
            }),
            eventBus.subscribe('source:inventory_refreshed', () => {
                // Clear sync status and reload tools when source inventory changes
                this._syncStatus = null;
                this._loadTools();
            }),
            eventBus.subscribe('label:created', () => {
                this._loadTools(); // Reload to get updated labels
            }),
            eventBus.subscribe('label:updated', () => {
                this._loadTools();
            }),
            eventBus.subscribe('label:deleted', () => {
                this._loadTools();
            })
        );
    }

    _unsubscribeFromEvents() {
        this._eventSubscriptions.forEach(unsub => unsub());
        this._eventSubscriptions = [];
    }

    /**
     * Check tool sync status between read and write models (admin only)
     */
    async _checkSyncStatus() {
        try {
            const status = await ToolsAPI.checkSyncStatus(20); // Sample 20 tools
            this._syncStatus = status;
            if (!status.is_healthy) {
                // Re-render to show warning banner
                this.render();
            }
        } catch (error) {
            // Silently ignore - user may not be admin or endpoint may not exist
            console.debug('Sync status check failed (admin-only):', error.message);
        }
    }

    _getLabelById(labelId) {
        return this._labels.find(l => l.id === labelId);
    }

    _updateToolStatus(toolId, enabled) {
        const tool = this._tools.find(t => t.id === toolId);
        if (tool) {
            tool.is_enabled = enabled;
            this.render();
        }
    }

    get _filteredTools() {
        return this._tools.filter(tool => {
            // Filter by enabled status
            if (this._filterEnabled !== null && tool.is_enabled !== this._filterEnabled) {
                return false;
            }
            // Filter by method
            if (this._filterMethod && tool.method?.toUpperCase() !== this._filterMethod) {
                return false;
            }
            // Filter by tag
            if (this._filterTag && !tool.tags?.includes(this._filterTag)) {
                return false;
            }
            // Filter by source
            if (this._filterSource && tool.source_id !== this._filterSource) {
                return false;
            }
            // Filter by search term (includes tags and source)
            if (this._searchTerm) {
                const term = this._searchTerm.toLowerCase();
                return (
                    tool.name?.toLowerCase().includes(term) ||
                    tool.description?.toLowerCase().includes(term) ||
                    tool.path?.toLowerCase().includes(term) ||
                    tool.source_id?.toLowerCase().includes(term) ||
                    tool.tags?.some(t => t.toLowerCase().includes(term))
                );
            }
            return true;
        });
    }

    render() {
        const filteredTools = this._filteredTools;
        const enabledCount = this._tools.filter(t => t.is_enabled !== false).length;
        const disabledCount = this._tools.length - enabledCount;

        this.innerHTML = `
            <div class="tools-page">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h2 class="mb-1">
                            <i class="bi bi-wrench text-primary me-2"></i>
                            MCP Tools
                        </h2>
                        <p class="text-muted mb-0">
                            Browse and manage tools imported from upstream sources
                        </p>
                    </div>
                    <div class="d-flex gap-2">
                        <div class="btn-group" role="group" aria-label="View mode">
                            <button type="button" class="btn btn-outline-secondary ${this._viewMode === 'grid' ? 'active' : ''}"
                                    data-view="grid" title="Grid view">
                                <i class="bi bi-grid-3x3-gap"></i>
                            </button>
                            <button type="button" class="btn btn-outline-secondary ${this._viewMode === 'table' ? 'active' : ''}"
                                    data-view="table" title="Table view">
                                <i class="bi bi-list"></i>
                            </button>
                        </div>
                        <button type="button" class="btn btn-outline-primary" id="refresh-btn" title="Refresh">
                            <i class="bi bi-arrow-clockwise"></i>
                        </button>
                    </div>
                </div>

                ${this._renderSyncWarning()}
                ${this._renderStats(enabledCount, disabledCount)}
                ${this._renderFilters()}

                <div class="tools-container">
                    ${this._loading ? this._renderLoading() : this._renderTools(filteredTools)}
                </div>

                ${this._renderDetailsModal()}
                ${this._renderCreateGroupModal()}
            </div>
        `;

        this._attachEventListeners();
    }

    _renderSyncWarning() {
        if (!this._syncStatus || this._syncStatus.is_healthy) {
            return '';
        }

        const missingCount = this._syncStatus.orphaned_tool_count;
        const orphanedIds = this._syncStatus.orphaned_tool_ids || [];

        // Group missing tools by source_id
        const missingBySource = {};
        orphanedIds.forEach(toolId => {
            // Tool ID format is "source_id:operation_id"
            const colonIndex = toolId.indexOf(':');
            const sourceId = colonIndex > 0 ? toolId.substring(0, colonIndex) : 'unknown';
            if (!missingBySource[sourceId]) {
                missingBySource[sourceId] = [];
            }
            missingBySource[sourceId].push(toolId);
        });

        const sourcesList = Object.entries(missingBySource)
            .map(([sourceId, tools]) => `<li><strong>${sourceId}</strong>: ${tools.length} tool(s)</li>`)
            .join('');

        return `
            <div class="alert alert-warning alert-dismissible fade show mb-4" role="alert">
                <div class="d-flex align-items-start">
                    <i class="bi bi-exclamation-triangle-fill fs-4 me-3 text-warning"></i>
                    <div class="flex-grow-1">
                        <h5 class="alert-heading mb-2">Database Sync Issue Detected</h5>
                        <p class="mb-2">
                            <strong>${missingCount}</strong> tool(s) exist in the read model (MongoDB) but not in the write model (EventStoreDB).
                            This can happen when EventStoreDB is cleared without clearing MongoDB.
                        </p>
                        <p class="mb-2"><strong>Affected sources:</strong></p>
                        <ul class="mb-3">${sourcesList}</ul>
                        <p class="mb-0 small text-muted">
                            <i class="bi bi-info-circle me-1"></i>
                            To fix: Go to the Sources page and refresh the inventory for the affected sources,
                            or clear all data and re-import.
                        </p>
                    </div>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
    }

    _renderStats(enabledCount, disabledCount) {
        return `
            <div class="row g-3 mb-4">
                <div class="col-6 col-md-3">
                    <div class="card bg-primary bg-opacity-10 border-0">
                        <div class="card-body py-3 text-center">
                            <div class="fs-3 fw-bold text-primary">${this._tools.length}</div>
                            <small class="text-muted">Total Tools</small>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card bg-success bg-opacity-10 border-0">
                        <div class="card-body py-3 text-center">
                            <div class="fs-3 fw-bold text-success">${enabledCount}</div>
                            <small class="text-muted">Enabled</small>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card bg-secondary bg-opacity-10 border-0">
                        <div class="card-body py-3 text-center">
                            <div class="fs-3 fw-bold text-secondary">${disabledCount}</div>
                            <small class="text-muted">Disabled</small>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card bg-info bg-opacity-10 border-0">
                        <div class="card-body py-3 text-center">
                            <div class="fs-3 fw-bold text-info stats-showing-count">${this._filteredTools.length}</div>
                            <small class="text-muted">Showing</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _renderFilters() {
        const methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];
        // Collect unique tags from all tools
        const uniqueTags = [...new Set(this._tools.flatMap(t => t.tags || []))].sort();
        // Collect unique sources from all tools (map source_id -> source_name)
        const sourceMap = new Map();
        this._tools.forEach(t => {
            if (t.source_id && !sourceMap.has(t.source_id)) {
                sourceMap.set(t.source_id, t.source_name || t.source_id);
            }
        });
        // Sort by source name
        const uniqueSources = [...sourceMap.entries()].sort((a, b) => a[1].localeCompare(b[1]));

        // Check if any filters are active
        const hasActiveFilters = this._filterEnabled !== null || this._filterMethod || this._filterTag || this._filterSource || this._searchTerm;
        const filteredTools = this._filteredTools;
        const filteredCount = filteredTools.length;
        const selectedCount = this._selectedToolIds.size;

        // Auto-select all filtered tools when filters change
        if (hasActiveFilters && filteredCount > 0) {
            // Sync selection with filtered tools
            this._syncSelectionWithFiltered();
        }

        return `
            <div class="card mb-4">
                <div class="card-body py-3">
                    <div class="row g-3 align-items-center">
                        <div class="col-12 col-md-3">
                            <div class="input-group">
                                <span class="input-group-text">
                                    <i class="bi bi-search"></i>
                                </span>
                                <input type="text" class="form-control" placeholder="Search tools..."
                                       id="search-input" value="${this._escapeHtml(this._searchTerm)}">
                            </div>
                        </div>
                        <div class="col-6 col-md-2">
                            <select class="form-select" id="filter-enabled">
                                <option value="" ${this._filterEnabled === null ? 'selected' : ''}>All Status</option>
                                <option value="true" ${this._filterEnabled === true ? 'selected' : ''}>Enabled Only</option>
                                <option value="false" ${this._filterEnabled === false ? 'selected' : ''}>Disabled Only</option>
                            </select>
                        </div>
                        <div class="col-6 col-md-2">
                            <select class="form-select" id="filter-method">
                                <option value="" ${!this._filterMethod ? 'selected' : ''}>All Methods</option>
                                ${methods
                                    .map(
                                        m => `
                                    <option value="${m}" ${this._filterMethod === m ? 'selected' : ''}>${m}</option>
                                `
                                    )
                                    .join('')}
                            </select>
                        </div>
                        <div class="col-6 col-md-2">
                            <select class="form-select" id="filter-tag">
                                <option value="" ${!this._filterTag ? 'selected' : ''}>All Tags</option>
                                ${uniqueTags
                                    .map(
                                        tag => `
                                    <option value="${this._escapeHtml(tag)}" ${this._filterTag === tag ? 'selected' : ''}>${this._escapeHtml(tag)}</option>
                                `
                                    )
                                    .join('')}
                            </select>
                        </div>
                        <div class="col-6 col-md-2">
                            <select class="form-select" id="filter-source">
                                <option value="" ${!this._filterSource ? 'selected' : ''}>All Sources</option>
                                ${uniqueSources
                                    .map(
                                        ([sourceId, sourceName]) => `
                                    <option value="${this._escapeHtml(sourceId)}" ${this._filterSource === sourceId ? 'selected' : ''}>${this._escapeHtml(sourceName)}</option>
                                `
                                    )
                                    .join('')}
                            </select>
                        </div>
                        <div class="col-6 col-md-1">
                            <div class="d-flex gap-2">
                                <button type="button" class="btn btn-outline-secondary flex-shrink-0" id="clear-filters" title="Clear filters">
                                    <i class="bi bi-x-lg"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="row mt-3 create-group-from-filter-row" style="display: ${hasActiveFilters && filteredCount > 0 ? 'block' : 'none'};">
                        <div class="col-12">
                            <button type="button" class="btn btn-primary" id="create-group-from-filter"
                                    title="Create a tool group from the ${selectedCount} selected tools">
                                <i class="bi bi-collection me-1"></i>
                                Create Group from <span class="selected-count">${selectedCount}</span> Filtered Tools
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Sync selection with currently filtered tools
     * Called when filters change to auto-select all filtered tools
     */
    _syncSelectionWithFiltered() {
        const filteredToolIds = new Set(this._filteredTools.map(t => t.id));
        // Add all filtered tools to selection
        filteredToolIds.forEach(id => this._selectedToolIds.add(id));
        // Remove tools that are no longer in the filtered list
        this._selectedToolIds = new Set([...this._selectedToolIds].filter(id => filteredToolIds.has(id)));
    }

    /**
     * Update the selection count in the Create Group button
     */
    _updateSelectionCount() {
        const btn = this.querySelector('#create-group-from-filter');
        const countSpan = this.querySelector('.selected-count');
        if (btn && countSpan) {
            const count = this._selectedToolIds.size;
            countSpan.textContent = count;
            btn.disabled = count === 0;
            btn.title = `Create a tool group from the ${count} selected tools`;
        }
    }

    /**
     * Partial re-render of just the tools list (preserves filter inputs and focus)
     */
    _renderToolsList() {
        const toolsContainer = this.querySelector('.tools-container');
        if (!toolsContainer) {
            // Fallback to full render if container not found
            this.render();
            return;
        }

        const filteredTools = this._filteredTools;

        // Auto-select all filtered tools
        this._syncSelectionWithFiltered();

        toolsContainer.innerHTML = this._loading ? this._renderLoading() : this._renderTools(filteredTools);

        // Re-attach tool card data bindings and event listeners
        this._attachToolCardListeners();

        // Update the "Showing" count in stats
        const showingCount = this.querySelector('.stats-showing-count');
        if (showingCount) {
            showingCount.textContent = filteredTools.length;
        }

        // Update "Create Group from X Filtered Tools" button visibility
        const createGroupRow = this.querySelector('.create-group-from-filter-row');
        const hasActiveFilters = this._filterEnabled !== null || this._filterMethod || this._filterTag || this._filterSource || this._searchTerm;
        if (createGroupRow) {
            if (hasActiveFilters && filteredTools.length > 0) {
                createGroupRow.style.display = 'block';
                this._updateSelectionCount();
            } else {
                createGroupRow.style.display = 'none';
            }
        }
    }

    /**
     * Attach event listeners to tool cards (called after partial render)
     */
    _attachToolCardListeners() {
        // Bind data to tool cards (grid view)
        this.querySelectorAll('tool-card').forEach(card => {
            const toolId = card.dataset.toolId;
            const tool = this._tools.find(t => t.id === toolId);
            if (tool) {
                card.data = tool;
            }
        });

        // Tool card events (grid view)
        this.querySelectorAll('tool-card').forEach(card => {
            card.addEventListener('toggle', async e => {
                const toolId = e.detail.toolId;
                const tool = this._tools.find(t => t.id === toolId);
                if (tool) {
                    await this._toggleTool(tool);
                }
            });

            card.addEventListener('details', e => {
                const toolId = e.detail.toolId;
                const tool = this._tools.find(t => t.id === toolId);
                if (tool) {
                    this._showToolDetails(tool);
                }
            });
        });

        // Tool selection checkboxes (for group creation)
        this.querySelectorAll('.tool-select-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', e => {
                const toolId = checkbox.dataset.toolId;
                if (e.target.checked) {
                    this._selectedToolIds.add(toolId);
                } else {
                    this._selectedToolIds.delete(toolId);
                }
                this._updateSelectionCount();

                // Update visual state for grid view (border highlight)
                const card = checkbox.closest('.col-12, .col-md-6, .col-lg-4')?.querySelector('tool-card');
                if (card) {
                    if (e.target.checked) {
                        card.classList.add('border-primary');
                    } else {
                        card.classList.remove('border-primary');
                    }
                }
            });
        });

        // Select all checkbox (table view)
        this.querySelector('#select-all-tools')?.addEventListener('change', e => {
            const isChecked = e.target.checked;
            const filteredTools = this._filteredTools;

            if (isChecked) {
                filteredTools.forEach(tool => this._selectedToolIds.add(tool.id));
            } else {
                filteredTools.forEach(tool => this._selectedToolIds.delete(tool.id));
            }

            // Update all individual checkboxes
            this.querySelectorAll('.tool-select-checkbox').forEach(checkbox => {
                checkbox.checked = isChecked;
            });

            this._updateSelectionCount();
        });

        // Table row actions
        this.querySelectorAll('.tool-toggle-btn').forEach(btn => {
            btn.addEventListener('click', async e => {
                const toolId = btn.dataset.toolId;
                const tool = this._tools.find(t => t.id === toolId);
                if (tool) {
                    await this._toggleTool(tool);
                }
            });
        });

        this.querySelectorAll('.tool-details-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const toolId = btn.dataset.toolId;
                const tool = this._tools.find(t => t.id === toolId);
                if (tool) {
                    this._showToolDetails(tool);
                }
            });
        });
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

    _renderTools(tools) {
        if (tools.length === 0) {
            return `
                <div class="text-center py-5">
                    <i class="bi bi-wrench display-1 text-muted"></i>
                    <h4 class="mt-3 text-muted">No Tools Found</h4>
                    <p class="text-muted">
                        ${this._tools.length === 0 ? 'Add an OpenAPI source to import tools' : 'Try adjusting your filters'}
                    </p>
                </div>
            `;
        }

        if (this._viewMode === 'grid') {
            return this._renderGridView(tools);
        }
        return this._renderTableView(tools);
    }

    _renderGridView(tools) {
        const hasActiveFilters = this._filterEnabled !== null || this._filterMethod || this._filterTag || this._filterSource || this._searchTerm;

        return `
            <div class="row g-3">
                ${tools
                    .map(tool => {
                        const isSelected = this._selectedToolIds.has(tool.id);
                        return `
                    <div class="col-12 col-md-6 col-lg-4 position-relative">
                        ${
                            hasActiveFilters
                                ? `
                        <div class="position-absolute top-0 start-0 mt-2 ms-2" style="z-index: 10;">
                            <div class="form-check">
                                <input class="form-check-input tool-select-checkbox" type="checkbox"
                                       data-tool-id="${tool.id}" ${isSelected ? 'checked' : ''}>
                            </div>
                        </div>
                        `
                                : ''
                        }
                        <tool-card data-tool-id="${tool.id}" class="${hasActiveFilters && isSelected ? 'border-primary' : ''}"></tool-card>
                    </div>
                `;
                    })
                    .join('')}
            </div>
        `;
    }

    _renderTableView(tools) {
        const hasActiveFilters = this._filterEnabled !== null || this._filterMethod || this._filterTag || this._filterSource || this._searchTerm;
        const allSelected = tools.length > 0 && tools.every(t => this._selectedToolIds.has(t.id));

        return `
            <div class="table-responsive">
                <table class="table table-hover align-middle">
                    <thead>
                        <tr>
                            ${
                                hasActiveFilters
                                    ? `
                            <th style="width: 40px;">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="select-all-tools"
                                           ${allSelected ? 'checked' : ''} title="Select/deselect all">
                                </div>
                            </th>
                            `
                                    : ''
                            }
                            <th>Method</th>
                            <th>Name</th>
                            <th>Path</th>
                            <th>Tags</th>
                            <th>Source</th>
                            <th class="text-center">Enabled</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tools.map(tool => this._renderTableRow(tool, hasActiveFilters)).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    _renderTableRow(tool, showCheckbox = false) {
        const method = (tool.method || 'GET').toUpperCase();
        const methodClass = this._getMethodClass(method);
        const isEnabled = tool.is_enabled !== false;
        const tags = tool.tags || [];
        const toolName = tool.tool_name || tool.name;
        const sourceName = tool.source_name || tool.source?.name || 'Unknown';
        const isSelected = this._selectedToolIds.has(tool.id);

        return `
            <tr data-tool-id="${tool.id}" class="${isEnabled ? '' : 'table-secondary'}">
                ${
                    showCheckbox
                        ? `
                <td>
                    <div class="form-check">
                        <input class="form-check-input tool-select-checkbox" type="checkbox"
                               data-tool-id="${tool.id}" ${isSelected ? 'checked' : ''}>
                    </div>
                </td>
                `
                        : ''
                }
                <td><span class="badge ${methodClass}">${method}</span></td>
                <td class="fw-medium">${this._escapeHtml(toolName)}</td>
                <td><code class="small">${this._escapeHtml(tool.path || '')}</code></td>
                <td>${tags.map(tag => `<span class="badge bg-secondary me-1">${this._escapeHtml(tag)}</span>`).join('')}</td>
                <td class="text-muted small">${this._escapeHtml(sourceName)}</td>
                <td class="text-center">
                    <div class="form-check form-switch d-inline-block">
                        <input class="form-check-input" type="checkbox" role="switch"
                               ${isEnabled ? 'checked' : ''} data-action="toggle" data-id="${tool.id}">
                    </div>
                </td>
                <td>
                    <button type="button" class="btn btn-sm btn-outline-secondary"
                            data-action="view" data-id="${tool.id}" title="View details">
                        <i class="bi bi-eye"></i>
                    </button>
                </td>
            </tr>
        `;
    }

    _attachEventListeners() {
        // View mode toggle
        this.querySelectorAll('[data-view]').forEach(btn => {
            btn.addEventListener('click', () => {
                this._viewMode = btn.dataset.view;
                this.render();
            });
        });

        // Refresh button
        this.querySelector('#refresh-btn')?.addEventListener('click', () => this._loadTools());

        // Search with debouncing to avoid focus loss
        this.querySelector('#search-input')?.addEventListener('input', e => {
            this._searchTerm = e.target.value;

            // Clear previous timer
            if (this._searchDebounceTimer) {
                clearTimeout(this._searchDebounceTimer);
            }

            // Debounce: only re-render after user stops typing for 300ms
            this._searchDebounceTimer = setTimeout(() => {
                this._renderToolsList();
            }, 300);
        });

        // Filters
        this.querySelector('#filter-enabled')?.addEventListener('change', e => {
            const val = e.target.value;
            this._filterEnabled = val === '' ? null : val === 'true';
            this._renderToolsList();
        });

        this.querySelector('#filter-method')?.addEventListener('change', e => {
            this._filterMethod = e.target.value || null;
            this._renderToolsList();
        });

        this.querySelector('#filter-tag')?.addEventListener('change', e => {
            this._filterTag = e.target.value || null;
            this._renderToolsList();
        });

        this.querySelector('#filter-source')?.addEventListener('change', e => {
            this._filterSource = e.target.value || null;
            this._renderToolsList();
        });

        this.querySelector('#clear-filters')?.addEventListener('click', () => {
            this._filterEnabled = null;
            this._filterMethod = null;
            this._filterTag = null;
            this._filterSource = null;
            this._searchTerm = '';
            this.render();
        });

        // Create group from filter button
        this.querySelector('#create-group-from-filter')?.addEventListener('click', () => {
            this._showCreateGroupModal();
        });

        // Bind data to tool cards (grid view)
        this.querySelectorAll('tool-card').forEach(card => {
            const toolId = card.dataset.toolId;
            const tool = this._tools.find(t => t.id === toolId);
            if (tool) {
                card.data = tool;
            }
        });

        // Listen for tool-view events from tool-cards
        this.addEventListener('tool-view', e => {
            this._showToolDetails(e.detail.data);
        });

        // Table view: View button handlers
        this.querySelectorAll('[data-action="view"]').forEach(btn => {
            btn.addEventListener('click', () => {
                const toolId = btn.dataset.id;
                const tool = this._tools.find(t => t.id === toolId);
                if (tool) {
                    this._showToolDetails(tool);
                }
            });
        });

        // Table view toggle handlers
        this.querySelectorAll('[data-action="toggle"]').forEach(toggle => {
            toggle.addEventListener('change', async e => {
                const toolId = toggle.dataset.id;
                const enabled = e.target.checked;
                try {
                    if (enabled) {
                        await ToolsAPI.enableTool(toolId);
                    } else {
                        await ToolsAPI.disableTool(toolId);
                    }
                    this._updateToolStatus(toolId, enabled);
                    showToast('success', `Tool ${enabled ? 'enabled' : 'disabled'}`);
                } catch (error) {
                    toggle.checked = !enabled;
                    showToast('error', `Failed: ${error.message}`);
                }
            });
        });
    }

    _renderDetailsModal() {
        return `
            <div class="modal fade" id="tool-details-modal" tabindex="-1" aria-labelledby="toolDetailsModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="toolDetailsModalLabel">
                                <i class="bi bi-wrench me-2"></i>
                                Tool Details
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body" id="tool-details-body">
                            <!-- Content will be populated dynamically -->
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-outline-primary" id="edit-tool-btn">
                                <i class="bi bi-pencil me-1"></i>Edit
                            </button>
                            <button type="button" class="btn btn-primary d-none" id="save-tool-btn">
                                <i class="bi bi-check me-1"></i>Save
                            </button>
                            <button type="button" class="btn btn-secondary" id="cancel-edit-tool-btn" style="display: none;">Cancel</button>
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="close-tool-btn">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async _showToolDetails(tool) {
        if (!tool) return;

        const detailsBody = this.querySelector('#tool-details-body');
        if (!detailsBody) return;

        // Show loading state first
        detailsBody.innerHTML = `
            <div class="d-flex justify-content-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;

        const modalEl = this.querySelector('#tool-details-modal');
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();

        // Fetch full tool details if input_schema is missing (summary doesn't include it)
        let fullTool = tool;
        if (!tool.input_schema && !tool.definition?.input_schema) {
            try {
                fullTool = await ToolsAPI.getTool(tool.id);
            } catch (error) {
                console.error('Failed to fetch tool details:', error);
                // Continue with partial data
            }
        }

        this._renderToolDetailsContent(fullTool, detailsBody);
    }

    _renderToolDetailsContent(tool, detailsBody) {
        const toolName = tool.tool_name || tool.name;
        const operationId = tool.operation_id || tool.id?.split(':')[1] || '-';
        const sourceName = tool.source_name || tool.source?.name || 'Unknown';
        const method = (tool.method || 'GET').toUpperCase();
        const methodClass = this._getMethodClass(method);
        const isEnabled = tool.is_enabled !== false;
        const tags = tool.tags || [];
        const labelIds = tool.label_ids || [];
        const inputSchema = tool.input_schema || tool.definition?.input_schema;
        const paramsCount = tool.params_count ?? (inputSchema?.properties ? Object.keys(inputSchema.properties).length : 0);
        const updatedAt = tool.updated_at ? new Date(tool.updated_at).toLocaleString() : 'Unknown';
        const description = tool.description || '';

        // Get label objects for display
        const toolLabels = labelIds.map(id => this._getLabelById(id)).filter(Boolean);

        // Build parameters table if input_schema available
        let paramsHtml = '<p class="text-muted">No parameter information available</p>';
        if (inputSchema?.properties) {
            const required = inputSchema.required || [];
            const props = Object.entries(inputSchema.properties);
            if (props.length > 0) {
                paramsHtml = `
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Required</th>
                                <th>Description</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${props
                                .map(
                                    ([name, schema]) => `
                                <tr>
                                    <td><code>${this._escapeHtml(name)}</code></td>
                                    <td>${this._escapeHtml(schema.type || 'any')}</td>
                                    <td>${required.includes(name) ? '<i class="bi bi-check-circle text-success"></i>' : '<i class="bi bi-dash text-muted"></i>'}</td>
                                    <td class="small text-muted">${this._escapeHtml(schema.description || '-')}</td>
                                </tr>
                            `
                                )
                                .join('')}
                        </tbody>
                    </table>
                `;
            }
        }

        detailsBody.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-muted mb-3">General Information</h6>
                    <table class="table table-sm">
                        <tr>
                            <td class="text-muted" style="width: 40%">Name</td>
                            <td class="fw-medium">
                                <span class="tool-name-display">${this._escapeHtml(toolName)}</span>
                                <input type="text" class="form-control form-control-sm tool-name-edit d-none"
                                       id="edit-tool-name" value="${this._escapeHtml(toolName)}"
                                       placeholder="Enter tool display name">
                            </td>
                        </tr>
                        <tr>
                            <td class="text-muted">Operation ID</td>
                            <td><code class="small text-muted">${this._escapeHtml(operationId)}</code>
                                <i class="bi bi-info-circle ms-1 small text-muted" title="Original operation ID from upstream API (read-only)"></i>
                            </td>
                        </tr>
                        <tr>
                            <td class="text-muted">ID</td>
                            <td><code class="small">${this._escapeHtml(tool.id)}</code></td>
                        </tr>
                        <tr>
                            <td class="text-muted">Method</td>
                            <td><span class="badge ${methodClass}">${method}</span></td>
                        </tr>
                        <tr>
                            <td class="text-muted">Path</td>
                            <td><code class="small">${this._escapeHtml(tool.path || '-')}</code></td>
                        </tr>
                        <tr>
                            <td class="text-muted">Enabled</td>
                            <td>
                                <i class="bi ${isEnabled ? 'bi-check-circle text-success' : 'bi-x-circle text-danger'}"></i>
                                ${isEnabled ? 'Yes' : 'No'}
                            </td>
                        </tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6 class="text-muted mb-3">Source & Metadata</h6>
                    <table class="table table-sm">
                        <tr>
                            <td class="text-muted" style="width: 40%">Source</td>
                            <td class="fw-medium">
                                <a href="#" class="text-decoration-none source-link"
                                   data-action="view-source" data-source-id="${this._escapeHtml(tool.source_id || '')}"
                                   title="View source details">
                                    ${this._escapeHtml(sourceName)}
                                    <i class="bi bi-box-arrow-up-right ms-1 small"></i>
                                </a>
                            </td>
                        </tr>
                        <tr>
                            <td class="text-muted">Source ID</td>
                            <td><code class="small">${this._escapeHtml(tool.source_id || '-')}</code></td>
                        </tr>
                        <tr>
                            <td class="text-muted">Parameters</td>
                            <td>${paramsCount}</td>
                        </tr>
                        <tr>
                            <td class="text-muted">Status</td>
                            <td>${tool.status || 'active'}</td>
                        </tr>
                        <tr>
                            <td class="text-muted">Updated</td>
                            <td>${updatedAt}</td>
                        </tr>
                    </table>
                </div>
            </div>
            ${
                tags.length > 0
                    ? `
            <div class="mt-3">
                <h6 class="text-muted mb-2">Tags</h6>
                <div>
                    ${tags.map(tag => `<span class="badge bg-secondary me-1">${this._escapeHtml(tag)}</span>`).join('')}
                </div>
            </div>
            `
                    : ''
            }
            <div class="mt-3">
                <h6 class="text-muted mb-2">
                    <i class="bi bi-tags me-1"></i>Labels
                    <button class="btn btn-sm btn-outline-primary ms-2" id="manage-tool-labels-btn" data-tool-id="${this._escapeHtml(tool.id)}">
                        <i class="bi bi-pencil"></i>
                    </button>
                </h6>
                <div id="tool-labels-container">
                    ${
                        toolLabels.length > 0
                            ? toolLabels.map(label => `<span class="badge rounded-pill me-1" style="background-color: ${label.color}">${this._escapeHtml(label.name)}</span>`).join('')
                            : '<span class="text-muted">No labels assigned</span>'
                    }
                </div>
            </div>
            <div class="mt-3">
                <h6 class="text-muted mb-2">Description</h6>
                <p class="mb-0 tool-description-display">${this._escapeHtml(description || 'No description available')}</p>
                <textarea class="form-control tool-description-edit d-none" id="edit-tool-description"
                          rows="3" placeholder="Enter tool description">${this._escapeHtml(description)}</textarea>
            </div>
            <div class="mt-3">
                <h6 class="text-muted mb-2">Parameters (${paramsCount})</h6>
                ${paramsHtml}
            </div>
        `;

        // Store current tool for edit operations
        this._currentTool = tool;
        this._currentToolForLabels = tool;

        // Attach label management button handler
        const manageLabelBtn = this.querySelector('#manage-tool-labels-btn');
        if (manageLabelBtn) {
            manageLabelBtn.addEventListener('click', () => this._showLabelManager(tool));
        }

        // Attach source link handler for cross-navigation
        const sourceLink = detailsBody.querySelector('[data-action="view-source"]');
        if (sourceLink) {
            sourceLink.addEventListener('click', e => {
                e.preventDefault();
                const sourceId = sourceLink.dataset.sourceId;
                if (sourceId) {
                    // Close current modal before navigating
                    const modalEl = this.querySelector('#tool-details-modal');
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();
                    // Navigate to sources page and open source details
                    dispatchNavigationEvent('sources', 'source-details', { sourceId });
                }
            });
        }

        // Attach edit/save/cancel button handlers
        this._attachToolEditHandlers();
    }

    /**
     * Attach handlers for tool edit/save/cancel buttons
     */
    _attachToolEditHandlers() {
        const editBtn = this.querySelector('#edit-tool-btn');
        const saveBtn = this.querySelector('#save-tool-btn');
        const cancelBtn = this.querySelector('#cancel-edit-tool-btn');
        const closeBtn = this.querySelector('#close-tool-btn');

        if (editBtn) {
            editBtn.onclick = () => this._enterToolEditMode();
        }
        if (saveBtn) {
            saveBtn.onclick = () => this._saveToolChanges();
        }
        if (cancelBtn) {
            cancelBtn.onclick = () => this._exitToolEditMode();
        }
    }

    /**
     * Enter edit mode for tool name and description
     */
    _enterToolEditMode() {
        // Show edit fields, hide display fields
        this.querySelector('.tool-name-display')?.classList.add('d-none');
        this.querySelector('.tool-name-edit')?.classList.remove('d-none');
        this.querySelector('.tool-description-display')?.classList.add('d-none');
        this.querySelector('.tool-description-edit')?.classList.remove('d-none');

        // Toggle buttons
        this.querySelector('#edit-tool-btn')?.classList.add('d-none');
        this.querySelector('#save-tool-btn')?.classList.remove('d-none');
        this.querySelector('#cancel-edit-tool-btn').style.display = '';
        this.querySelector('#close-tool-btn')?.classList.add('d-none');
    }

    /**
     * Exit edit mode without saving
     */
    _exitToolEditMode() {
        const tool = this._currentTool;
        if (!tool) return;

        // Reset values to original
        const nameInput = this.querySelector('#edit-tool-name');
        const descInput = this.querySelector('#edit-tool-description');
        if (nameInput) nameInput.value = tool.tool_name || tool.name || '';
        if (descInput) descInput.value = tool.description || '';

        // Hide edit fields, show display fields
        this.querySelector('.tool-name-display')?.classList.remove('d-none');
        this.querySelector('.tool-name-edit')?.classList.add('d-none');
        this.querySelector('.tool-description-display')?.classList.remove('d-none');
        this.querySelector('.tool-description-edit')?.classList.add('d-none');

        // Toggle buttons
        this.querySelector('#edit-tool-btn')?.classList.remove('d-none');
        this.querySelector('#save-tool-btn')?.classList.add('d-none');
        this.querySelector('#cancel-edit-tool-btn').style.display = 'none';
        this.querySelector('#close-tool-btn')?.classList.remove('d-none');
    }

    /**
     * Save tool changes (name and/or description)
     */
    async _saveToolChanges() {
        const tool = this._currentTool;
        if (!tool) return;

        const nameInput = this.querySelector('#edit-tool-name');
        const descInput = this.querySelector('#edit-tool-description');
        const saveBtn = this.querySelector('#save-tool-btn');

        const newName = nameInput?.value?.trim() || null;
        const newDescription = descInput?.value?.trim() || null;
        const originalName = tool.tool_name || tool.name || '';
        const originalDescription = tool.description || '';

        // Check if anything changed
        const nameChanged = newName && newName !== originalName;
        const descChanged = newDescription !== null && newDescription !== originalDescription;

        if (!nameChanged && !descChanged) {
            showToast('info', 'No changes to save');
            this._exitToolEditMode();
            return;
        }

        // Show loading state
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Saving...';
        }

        try {
            const updates = {};
            if (nameChanged) updates.tool_name = newName;
            if (descChanged) updates.description = newDescription;

            await ToolsAPI.updateTool(tool.id, updates);

            // Update local state
            if (nameChanged) {
                tool.tool_name = newName;
                this.querySelector('.tool-name-display').textContent = newName;
            }
            if (descChanged) {
                tool.description = newDescription;
                this.querySelector('.tool-description-display').textContent = newDescription || 'No description available';
            }

            // Update tool in list
            const toolInList = this._tools.find(t => t.id === tool.id);
            if (toolInList) {
                if (nameChanged) toolInList.tool_name = newName;
                if (descChanged) toolInList.description = newDescription;
            }

            showToast('success', 'Tool updated successfully');
            this._exitToolEditMode();
        } catch (error) {
            console.error('Failed to update tool:', error);
            showToast('error', `Failed to update tool: ${error.message}`);
        } finally {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="bi bi-check me-1"></i>Save';
            }
        }
    }

    async _showLabelManager(tool) {
        const container = this.querySelector('#tool-labels-container');
        if (!container) return;

        // Check if already in edit mode
        if (container.classList.contains('edit-mode')) {
            // Switch back to view mode
            this._renderLabelsViewMode(container, tool);
            return;
        }

        // Switch to edit mode - show checkboxes for all available labels
        container.classList.add('edit-mode');
        const toolLabelIds = tool.label_ids || [];

        container.innerHTML = `
            <div class="label-editor p-2 border rounded">
                <div class="mb-2">
                    ${
                        this._labels.length > 0
                            ? this._labels
                                  .map(
                                      label => `
                            <div class="form-check">
                                <input class="form-check-input label-checkbox" type="checkbox"
                                       id="label-${label.id}" value="${label.id}"
                                       ${toolLabelIds.includes(label.id) ? 'checked' : ''}>
                                <label class="form-check-label" for="label-${label.id}">
                                    <span class="badge rounded-pill me-1" style="background-color: ${label.color}">${this._escapeHtml(label.name)}</span>
                                </label>
                            </div>
                        `
                                  )
                                  .join('')
                            : '<p class="text-muted mb-0">No labels available. <a href="#" data-page="labels">Create some first</a>.</p>'
                    }
                </div>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-primary" id="save-labels-btn">
                        <i class="bi bi-check me-1"></i>Save
                    </button>
                    <button class="btn btn-sm btn-secondary" id="cancel-labels-btn">Cancel</button>
                </div>
            </div>
        `;

        // Attach handlers
        this.querySelector('#save-labels-btn')?.addEventListener('click', () => this._saveToolLabels(tool));
        this.querySelector('#cancel-labels-btn')?.addEventListener('click', () => this._renderLabelsViewMode(container, tool));
    }

    _renderLabelsViewMode(container, tool) {
        container.classList.remove('edit-mode');
        const toolLabels = (tool.label_ids || []).map(id => this._getLabelById(id)).filter(Boolean);

        container.innerHTML =
            toolLabels.length > 0
                ? toolLabels.map(label => `<span class="badge rounded-pill me-1" style="background-color: ${label.color}">${this._escapeHtml(label.name)}</span>`).join('')
                : '<span class="text-muted">No labels assigned</span>';
    }

    async _saveToolLabels(tool) {
        const checkboxes = this.querySelectorAll('.label-checkbox');
        const selectedLabelIds = Array.from(checkboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);

        const currentLabelIds = tool.label_ids || [];

        // Find labels to add and remove
        const toAdd = selectedLabelIds.filter(id => !currentLabelIds.includes(id));
        const toRemove = currentLabelIds.filter(id => !selectedLabelIds.includes(id));

        const saveBtn = this.querySelector('#save-labels-btn');
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        }

        try {
            // Process additions
            for (const labelId of toAdd) {
                await ToolsAPI.addLabelToTool(tool.id, labelId);
            }

            // Process removals
            for (const labelId of toRemove) {
                await ToolsAPI.removeLabelFromTool(tool.id, labelId);
            }

            // Update local state
            tool.label_ids = selectedLabelIds;

            // Update tool in list
            const toolInList = this._tools.find(t => t.id === tool.id);
            if (toolInList) {
                toolInList.label_ids = selectedLabelIds;
            }

            showToast('success', 'Labels updated successfully');

            // Switch back to view mode
            const container = this.querySelector('#tool-labels-container');
            if (container) {
                this._renderLabelsViewMode(container, tool);
            }
        } catch (error) {
            showToast('error', `Failed to update labels: ${error.message}`);
        } finally {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="bi bi-check me-1"></i>Save';
            }
        }
    }

    _getMethodClass(method) {
        const classes = {
            GET: 'bg-success',
            POST: 'bg-primary',
            PUT: 'bg-warning text-dark',
            PATCH: 'bg-info text-dark',
            DELETE: 'bg-danger',
        };
        return classes[method] || 'bg-secondary';
    }

    // =========================================================================
    // CREATE GROUP FROM FILTERS METHODS
    // =========================================================================

    _renderCreateGroupModal() {
        return `
            <div class="modal fade" id="create-group-modal" tabindex="-1" aria-labelledby="createGroupModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content">
                        <form id="create-group-form">
                            <div class="modal-header">
                                <h5 class="modal-title" id="createGroupModalLabel">
                                    <i class="bi bi-collection me-2"></i>
                                    Create Group from Current Filter
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="new-group-name" class="form-label">Group Name <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control" id="new-group-name" required
                                           placeholder="e.g., User Management Tools">
                                </div>
                                <div class="mb-3">
                                    <label for="new-group-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="new-group-description" rows="2"
                                              placeholder="Optional description of this group"></textarea>
                                </div>

                                <hr>
                                <h6 class="mb-3">
                                    <i class="bi bi-funnel me-2"></i>
                                    Selectors from Current Filter
                                </h6>
                                <div id="new-group-selectors" class="mb-3">
                                    <!-- Selectors will be populated dynamically -->
                                </div>

                                <hr>
                                <h6 class="mb-3">
                                    <i class="bi bi-eye me-2"></i>
                                    Tools That Will Be Included
                                    <span class="badge bg-success ms-2" id="new-group-tool-count">0</span>
                                </h6>
                                <div id="new-group-tool-preview" class="tool-preview-container">
                                    <!-- Preview will be populated dynamically -->
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-primary" id="submit-new-group-btn">
                                    <span class="spinner-border spinner-border-sm d-none me-2" id="new-group-spinner"></span>
                                    Create Group
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
    }

    _showCreateGroupModal() {
        // Get selected tools (not just filtered)
        const selectedTools = this._tools.filter(t => this._selectedToolIds.has(t.id));

        // Build selectors from current filters
        const selectors = [];
        if (this._searchTerm) {
            selectors.push({ type: 'name', pattern: `*${this._searchTerm}*`, label: 'Name contains' });
        }
        if (this._filterTag) {
            selectors.push({ type: 'tag', pattern: this._filterTag, label: 'Tag' });
        }
        // Note: Method and enabled filters don't map directly to selectors

        // Populate selectors display
        const selectorsContainer = this.querySelector('#new-group-selectors');
        if (selectorsContainer) {
            if (selectors.length > 0) {
                selectorsContainer.innerHTML = selectors
                    .map(
                        sel => `
                    <div class="d-flex align-items-center gap-2 mb-2">
                        <span class="badge bg-secondary">${this._escapeHtml(sel.label)}</span>
                        <code class="small">${this._escapeHtml(sel.pattern)}</code>
                    </div>
                `
                    )
                    .join('');
            } else {
                selectorsContainer.innerHTML = `
                    <div class="text-muted small">
                        <i class="bi bi-info-circle me-1"></i>
                        Current filters cannot be converted to selectors.
                        The ${selectedTools.length} selected tools will be added explicitly.
                    </div>
                `;
            }
        }

        // Update tool count badge
        const countBadge = this.querySelector('#new-group-tool-count');
        if (countBadge) {
            countBadge.textContent = selectedTools.length;
        }

        // Populate tool preview
        const previewContainer = this.querySelector('#new-group-tool-preview');
        if (previewContainer) {
            const maxDisplay = 10;
            const displayTools = selectedTools.slice(0, maxDisplay);
            const remaining = selectedTools.length - maxDisplay;

            previewContainer.innerHTML = `
                <div class="list-group list-group-flush tool-preview-list" style="max-height: 200px; overflow-y: auto;">
                    ${displayTools
                        .map(
                            tool => `
                        <div class="list-group-item py-2 px-3 d-flex justify-content-between align-items-center">
                            <div>
                                <span class="fw-medium">${this._escapeHtml(tool.tool_name || tool.name)}</span>
                                <small class="text-muted ms-2">${this._escapeHtml(tool.source_name || '')}</small>
                            </div>
                            <div>
                                <span class="badge bg-secondary text-uppercase" style="font-size: 0.65rem;">${tool.method || 'GET'}</span>
                            </div>
                        </div>
                    `
                        )
                        .join('')}
                    ${
                        remaining > 0
                            ? `
                        <div class="list-group-item py-2 px-3 text-muted text-center">
                            <i class="bi bi-three-dots me-1"></i>
                            and ${remaining} more tool${remaining !== 1 ? 's' : ''}
                        </div>
                    `
                            : ''
                    }
                </div>
            `;
        }

        // Suggest group name based on filters
        const nameInput = this.querySelector('#new-group-name');
        if (nameInput && !nameInput.value) {
            let suggestedName = '';
            if (this._filterTag) {
                suggestedName = `${this._filterTag} Tools`;
            } else if (this._searchTerm) {
                suggestedName = `${this._searchTerm} Tools`;
            }
            nameInput.value = suggestedName;
        }

        // Attach form submit handler
        const form = this.querySelector('#create-group-form');
        if (form) {
            // Remove previous listener if any
            form.removeEventListener('submit', this._boundHandleCreateGroup);
            this._boundHandleCreateGroup = e => this._handleCreateGroupFromFilter(e, selectors, selectedTools);
            form.addEventListener('submit', this._boundHandleCreateGroup);
        }

        // Show modal
        const modalEl = this.querySelector('#create-group-modal');
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
    }

    async _handleCreateGroupFromFilter(e, selectors, selectedTools) {
        e.preventDefault();

        const form = e.target;
        const submitBtn = form.querySelector('#submit-new-group-btn');
        const spinner = form.querySelector('#new-group-spinner');

        const groupName = form.querySelector('#new-group-name').value.trim();
        const groupDescription = form.querySelector('#new-group-description').value.trim();

        submitBtn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            // Create group with selectors if available, otherwise create empty and add tools explicitly
            const groupData = {
                name: groupName,
                description: groupDescription || undefined,
            };

            // If we have selectors, add them
            if (selectors.length > 0) {
                groupData.selectors = selectors.map(sel => ({
                    type: sel.type,
                    pattern: sel.pattern,
                }));
            }

            const newGroup = await GroupsAPI.createGroup(groupData);

            // If no selectors, add tools explicitly
            if (selectors.length === 0 && selectedTools.length > 0) {
                // Add tools explicitly (limit to 100 tools to avoid overwhelming the API)
                for (const tool of selectedTools.slice(0, 100)) {
                    try {
                        await GroupsAPI.addExplicitTool(newGroup.id, tool.id);
                    } catch (err) {
                        console.warn(`Failed to add tool ${tool.id} to group:`, err);
                    }
                }
            }

            // Close modal
            const modal = bootstrap.Modal.getInstance(this.querySelector('#create-group-modal'));
            modal.hide();
            form.reset();

            showToast('success', `Group "${groupName}" created with ${selectedTools.length} tools`);

            // Clear filters and selection after successful creation
            this._filterEnabled = null;
            this._filterMethod = null;
            this._filterTag = null;
            this._filterSource = null;
            this._searchTerm = '';
            this._selectedToolIds.clear();
            this.render();
        } catch (error) {
            showToast('error', `Failed to create group: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    }

    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

if (!customElements.get('tools-page')) {
    customElements.define('tools-page', ToolsPage);
}

export { ToolsPage };
