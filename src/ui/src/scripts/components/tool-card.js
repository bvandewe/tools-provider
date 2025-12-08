/**
 * Tool Card Component
 *
 * Displays an MCP tool with its details and enable/disable toggle.
 */

import { confirmDelete } from './confirm-modal.js';
import { showToast } from './toast-notification.js';
import * as ToolsAPI from '../api/tools.js';

class ToolCard extends HTMLElement {
    constructor() {
        super();
        this._data = null;
        this._loading = false;
        this._compact = false;
    }

    static get observedAttributes() {
        return ['compact'];
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

    attributeChangedCallback(name, oldValue, newValue) {
        if (name === 'compact') {
            this._compact = newValue !== null;
            this.render();
        }
    }

    connectedCallback() {
        this._compact = this.hasAttribute('compact');
        this.render();
    }

    render() {
        if (this._loading) {
            this.innerHTML = `
                <div class="card h-100">
                    <div class="card-body d-flex align-items-center justify-content-center py-3">
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
                    <div class="card-body d-flex align-items-center justify-content-center text-muted py-3">
                        <i class="bi bi-wrench me-2"></i>
                        No tool data
                    </div>
                </div>
            `;
            return;
        }

        const tool = this._data;
        const isEnabled = tool.is_enabled !== false;
        const method = tool.method?.toUpperCase() || 'GET';
        const methodClass = this._getMethodClass(method);

        if (this._compact) {
            this._renderCompact(tool, isEnabled, method, methodClass);
        } else {
            this._renderFull(tool, isEnabled, method, methodClass);
        }

        this._attachEventListeners();
    }

    _renderCompact(tool, isEnabled, method, methodClass) {
        const toolName = tool.tool_name || tool.name;
        this.innerHTML = `
            <div class="card tool-card tool-card-compact ${isEnabled ? '' : 'opacity-50'}">
                <div class="card-body py-2 px-3">
                    <div class="d-flex align-items-center justify-content-between">
                        <div class="d-flex align-items-center flex-grow-1 min-width-0">
                            <span class="badge ${methodClass} me-2">${method}</span>
                            <span class="fw-medium text-truncate" title="${this._escapeHtml(toolName)}">
                                ${this._escapeHtml(toolName)}
                            </span>
                        </div>
                        <div class="form-check form-switch mb-0 ms-2">
                            <input class="form-check-input" type="checkbox" role="switch"
                                   ${isEnabled ? 'checked' : ''} data-action="toggle">
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _renderFull(tool, isEnabled, method, methodClass) {
        const sourceName = tool.source_name || tool.source?.name || 'Unknown';
        // Use params_count from summary, or compute from input_schema/parameters
        const paramsCount = tool.params_count ?? (tool.input_schema?.properties ? Object.keys(tool.input_schema.properties).length : tool.parameters?.length || 0);
        const tags = tool.tags || [];

        this.innerHTML = `
            <div class="card h-100 tool-card ${isEnabled ? '' : 'border-secondary opacity-75'}">
                <div class="card-header d-flex justify-content-between align-items-center py-2">
                    <div class="d-flex align-items-center min-width-0 flex-grow-1">
                        <span class="badge ${methodClass} me-2">${method}</span>
                        <span class="fw-medium text-truncate" title="${this._escapeHtml(tool.tool_name || tool.name)}">
                            ${this._escapeHtml(tool.tool_name || tool.name)}
                        </span>
                    </div>
                    <div class="form-check form-switch mb-0">
                        <input class="form-check-input" type="checkbox" role="switch"
                               ${isEnabled ? 'checked' : ''} data-action="toggle"
                               title="${isEnabled ? 'Disable tool' : 'Enable tool'}">
                    </div>
                </div>
                <div class="card-body py-2">
                    <p class="card-text small text-muted mb-2 text-truncate-2" title="${this._escapeHtml(tool.description || '')}">
                        ${this._escapeHtml(tool.description || 'No description')}
                    </p>
                    <div class="d-flex gap-3 small">
                        <span class="text-muted" title="Source">
                            <i class="bi bi-cloud me-1"></i>${this._escapeHtml(sourceName)}
                        </span>
                        <span class="text-muted" title="Parameters">
                            <i class="bi bi-sliders me-1"></i>${paramsCount} params
                        </span>
                    </div>
                    ${
                        tool.path
                            ? `
                        <div class="mt-2">
                            <code class="small text-truncate d-block" title="${this._escapeHtml(tool.path)}">
                                ${this._escapeHtml(tool.path)}
                            </code>
                        </div>
                    `
                            : ''
                    }
                    ${
                        tags.length > 0
                            ? `
                        <div class="mt-2">
                            ${tags.map(tag => `<span class="badge bg-secondary bg-opacity-25 text-secondary me-1" title="OpenAPI tag">${this._escapeHtml(tag)}</span>`).join('')}
                        </div>
                    `
                            : ''
                    }
                </div>
                <div class="card-footer bg-transparent border-top-0 py-2">
                    <div class="btn-group btn-group-sm w-100" role="group">
                        <button type="button" class="btn btn-outline-secondary" data-action="view" title="View details">
                            <i class="bi bi-eye"></i> Details
                        </button>
                        <button type="button" class="btn btn-outline-primary" data-action="test" title="Test tool">
                            <i class="bi bi-play"></i> Test
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    _attachEventListeners() {
        this.querySelector('[data-action="toggle"]')?.addEventListener('change', e => this._handleToggle(e));
        this.querySelector('[data-action="view"]')?.addEventListener('click', () => this._handleView());
        this.querySelector('[data-action="test"]')?.addEventListener('click', () => this._handleTest());
    }

    async _handleToggle(e) {
        if (!this._data?.id) {
            console.error('Tool card has no ID:', this._data);
            showToast('error', 'Cannot toggle tool: missing tool ID');
            e.target.checked = !e.target.checked; // Revert
            return;
        }

        const isEnabled = e.target.checked;
        const toggle = e.target;
        toggle.disabled = true;

        try {
            if (isEnabled) {
                await ToolsAPI.enableTool(this._data.id);
                showToast('success', `Tool "${this._data.name}" enabled`);
            } else {
                await ToolsAPI.disableTool(this._data.id);
                showToast('success', `Tool "${this._data.name}" disabled`);
            }

            this._data.is_enabled = isEnabled;
            this.dispatchEvent(
                new CustomEvent('tool-toggle', {
                    detail: { id: this._data.id, enabled: isEnabled },
                    bubbles: true,
                })
            );
        } catch (error) {
            // Revert the toggle
            toggle.checked = !isEnabled;
            showToast('error', `Failed to ${isEnabled ? 'enable' : 'disable'} tool: ${error.message}`);
        } finally {
            toggle.disabled = false;
        }
    }

    _handleView() {
        this.dispatchEvent(
            new CustomEvent('tool-view', {
                detail: { id: this._data?.id, data: this._data },
                bubbles: true,
            })
        );
    }

    _handleTest() {
        this.dispatchEvent(
            new CustomEvent('tool-test', {
                detail: { id: this._data?.id, data: this._data },
                bubbles: true,
            })
        );
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

    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

if (!customElements.get('tool-card')) {
    customElements.define('tool-card', ToolCard);
}

export { ToolCard };
