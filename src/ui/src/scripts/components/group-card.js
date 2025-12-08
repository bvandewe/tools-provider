/**
 * Tool Group Card Component
 *
 * Displays a tool group with member tools and actions.
 */

import { confirmDelete } from './confirm-modal.js';
import { showToast } from './toast-notification.js';
import * as GroupsAPI from '../api/groups.js';
import { apiSelectorToUiFormat } from '../api/groups.js';
import { getToolDisplayName, getMethodClass, inferMethodFromName } from '../core/tool-utils.js';

class GroupCard extends HTMLElement {
    constructor() {
        super();
        this._data = null;
        this._loading = false;
        this._expanded = false;
        this._resolvedTools = null; // Cache resolved tools
        this._loadingTools = false;
    }

    set data(value) {
        this._data = value;
        this._resolvedTools = null; // Reset resolved tools when data changes
        this.render();
        // Fetch resolved tools count in background
        this._fetchResolvedTools();
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

    async _fetchResolvedTools() {
        if (!this._data?.id) return;

        try {
            const resolved = await GroupsAPI.getGroupTools(this._data.id);
            this._resolvedTools = resolved.tool_ids || [];
            this.render(); // Re-render to show updated count
        } catch (error) {
            console.error('Failed to load tools for group:', error);
            this._resolvedTools = [];
        }
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
                        <i class="bi bi-collection me-2"></i>
                        No group data
                    </div>
                </div>
            `;
            return;
        }

        const group = this._data;
        // Use resolved tools count if available, otherwise show explicit_tool_count or 0
        const toolsCount = this._resolvedTools?.length ?? group.explicit_tool_count ?? group.tool_count ?? 0;
        const selectorsCount = group.selectors?.length || group.selector_count || 0;
        const exclusionsCount = group.excluded_tool_ids?.length || group.excluded_tool_count || 0;
        const isActive = group.is_active !== undefined ? group.is_active : group.status === 'active';

        this.innerHTML = `
            <div class="card h-100 group-card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-collection text-primary me-2"></i>
                        <span class="fw-medium">${this._escapeHtml(group.name)}</span>
                    </div>
                    <span class="badge ${isActive ? 'bg-success' : 'bg-secondary'}">
                        ${isActive ? 'Active' : 'Inactive'}
                    </span>
                </div>
                <div class="card-body">
                    ${
                        group.description
                            ? `
                        <p class="card-text small text-muted mb-3">
                            ${this._escapeHtml(group.description)}
                        </p>
                    `
                            : ''
                    }

                    <div class="row g-2 mb-3">
                        <div class="col-4 text-center">
                            <div class="fs-5 fw-bold text-primary">${toolsCount}</div>
                            <small class="text-muted">Tools</small>
                        </div>
                        <div class="col-4 text-center">
                            <div class="fs-5 fw-bold text-info">${selectorsCount}</div>
                            <small class="text-muted">Selectors</small>
                        </div>
                        <div class="col-4 text-center">
                            <div class="fs-5 fw-bold text-warning">${exclusionsCount}</div>
                            <small class="text-muted">Exclusions</small>
                        </div>
                    </div>

                    ${this._renderSelectors(group.selectors)}

                    ${this._expanded ? this._renderToolsList() : ''}
                </div>
                <div class="card-footer bg-transparent border-top-0">
                    <div class="d-flex gap-2">
                        <button type="button" class="btn btn-outline-secondary btn-sm flex-fill" data-action="expand">
                            <i class="bi ${this._expanded ? 'bi-chevron-up' : 'bi-chevron-down'}"></i>
                            ${this._expanded ? 'Collapse' : 'Show Tools'}
                        </button>
                        <button type="button" class="btn btn-outline-primary btn-sm" data-action="edit" title="Edit group">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button type="button" class="btn btn-outline-danger btn-sm" data-action="delete" title="Delete group">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;

        this._attachEventListeners();
    }

    _renderSelectors(selectors) {
        if (!selectors || selectors.length === 0) return '';

        // Convert API format selectors to UI format for display
        const uiSelectors = selectors.map(apiSelectorToUiFormat);

        return `
            <div class="mb-2">
                <small class="text-muted d-block mb-1">Selectors:</small>
                <div class="d-flex flex-wrap gap-1">
                    ${uiSelectors
                        .slice(0, 3)
                        .map(
                            sel => `
                        <span class="badge bg-info bg-opacity-10 text-info border border-info">
                            ${this._escapeHtml(sel.type)}: ${this._escapeHtml(sel.pattern)}
                        </span>
                    `
                        )
                        .join('')}
                    ${
                        selectors.length > 3
                            ? `
                        <span class="badge bg-secondary bg-opacity-10 text-secondary">
                            +${selectors.length - 3} more
                        </span>
                    `
                            : ''
                    }
                </div>
            </div>
        `;
    }

    _renderToolsList() {
        if (this._loadingTools) {
            return `
                <div class="mt-3 pt-3 border-top">
                    <div class="d-flex justify-content-center py-2">
                        <div class="spinner-border spinner-border-sm text-primary" role="status">
                            <span class="visually-hidden">Loading tools...</span>
                        </div>
                    </div>
                </div>
            `;
        }

        const tools = this._resolvedTools;
        if (!tools || tools.length === 0) {
            return `
                <div class="mt-3 pt-3 border-top">
                    <p class="text-muted small mb-0">No tools in this group</p>
                </div>
            `;
        }

        return `
            <div class="mt-3 pt-3 border-top">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <small class="text-muted">Tools (${tools.length}):</small>
                    <button type="button" class="btn btn-outline-primary btn-sm" data-action="add-tools" title="Add tools to this group">
                        <i class="bi bi-plus-lg me-1"></i>Add Tools
                    </button>
                </div>
                <div class="list-group list-group-flush" style="max-height: 250px; overflow-y: auto;">
                    ${tools
                        .map(toolId => {
                            const displayName = getToolDisplayName(toolId);
                            const method = inferMethodFromName(toolId);
                            const methodClass = getMethodClass(method);
                            return `
                        <div class="list-group-item list-group-item-action py-2 px-2 d-flex justify-content-between align-items-center">
                            <div class="d-flex align-items-center flex-grow-1 overflow-hidden">
                                <span class="badge ${methodClass} me-2" style="font-size: 0.6rem;">${method}</span>
                                <span class="small text-truncate" title="${this._escapeHtml(toolId)}">${this._escapeHtml(displayName)}</span>
                            </div>
                            <button type="button" class="btn btn-outline-danger btn-sm ms-2 flex-shrink-0"
                                    data-action="exclude-tool" data-tool-id="${this._escapeHtml(toolId)}"
                                    title="Exclude this tool from the group">
                                <i class="bi bi-x-lg"></i>
                            </button>
                        </div>
                    `;
                        })
                        .join('')}
                </div>
            </div>
        `;
    }

    _attachEventListeners() {
        this.querySelector('[data-action="expand"]')?.addEventListener('click', () => this._handleExpand());
        this.querySelector('[data-action="edit"]')?.addEventListener('click', () => this._handleEdit());
        this.querySelector('[data-action="delete"]')?.addEventListener('click', () => this._handleDelete());
        this.querySelector('[data-action="add-tools"]')?.addEventListener('click', () => this._handleAddTools());

        // Exclude tool buttons
        this.querySelectorAll('[data-action="exclude-tool"]').forEach(btn => {
            btn.addEventListener('click', async e => {
                e.stopPropagation();
                const toolId = btn.dataset.toolId;
                await this._handleExcludeTool(toolId);
            });
        });
    }

    async _handleExcludeTool(toolId) {
        if (!this._data?.id || !toolId) return;

        try {
            await GroupsAPI.excludeTool(this._data.id, toolId, 'Manually excluded via UI');

            // Remove from resolved tools list
            if (this._resolvedTools) {
                this._resolvedTools = this._resolvedTools.filter(id => id !== toolId);
            }

            showToast('success', `Tool excluded from group`);
            this.render();

            // Notify parent that group was updated
            this.dispatchEvent(
                new CustomEvent('group-updated', {
                    detail: { id: this._data.id },
                    bubbles: true,
                })
            );
        } catch (error) {
            showToast('error', `Failed to exclude tool: ${error.message}`);
        }
    }

    _handleAddTools() {
        // Dispatch event to parent to open tool selector modal
        this.dispatchEvent(
            new CustomEvent('group-add-tools', {
                detail: { id: this._data?.id, data: this._data },
                bubbles: true,
            })
        );
    }

    async _handleExpand() {
        this._expanded = !this._expanded;

        // Fetch resolved tools when expanding (if not already loaded)
        if (this._expanded && !this._resolvedTools && this._data?.id) {
            this._loadingTools = true;
            this.render();

            try {
                const resolved = await GroupsAPI.getGroupTools(this._data.id);
                this._resolvedTools = resolved.tool_ids || [];
            } catch (error) {
                console.error('Failed to load tools for group:', error);
                this._resolvedTools = [];
            } finally {
                this._loadingTools = false;
            }
        }

        this.render();
    }

    _handleEdit() {
        this.dispatchEvent(
            new CustomEvent('group-edit', {
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
            await GroupsAPI.deleteGroup(this._data.id);
            showToast('success', `Group "${this._data.name}" deleted`);
            this.dispatchEvent(
                new CustomEvent('group-delete', {
                    detail: { id: this._data.id },
                    bubbles: true,
                })
            );
        } catch (error) {
            showToast('error', `Failed to delete: ${error.message}`);
        }
    }

    _getMethodClass(method) {
        const classes = {
            get: 'bg-success',
            post: 'bg-primary',
            put: 'bg-warning text-dark',
            patch: 'bg-info text-dark',
            delete: 'bg-danger',
        };
        return classes[(method || '').toLowerCase()] || 'bg-secondary';
    }

    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

if (!customElements.get('group-card')) {
    customElements.define('group-card', GroupCard);
}

export { GroupCard };
