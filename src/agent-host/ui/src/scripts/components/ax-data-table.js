/**
 * Data Table Widget Component
 * Renders a sortable, filterable, paginated data table.
 *
 * Attributes:
 * - columns: JSON array of column definitions [{ id, label, sortable, filterable, width }]
 * - data: JSON array of row data [{ col1: value, col2: value }]
 * - sortable: Enable column sorting (default: true)
 * - filterable: Enable column filtering (default: false)
 * - paginated: Enable pagination (default: false)
 * - page-size: Rows per page (default: 10)
 * - prompt: Optional title for the table
 * - selectable: Enable row selection
 * - selection-mode: "single" or "multiple"
 *
 * Events:
 * - ax-row-click: Fired when user clicks a row
 * - ax-row-select: Fired when row selection changes
 * - ax-sort-change: Fired when sort order changes
 * - ax-page-change: Fired when page changes
 * - ax-response: Fired with selected rows
 *
 * @example
 * <ax-data-table
 *   columns='[{"id":"name","label":"Name","sortable":true},{"id":"age","label":"Age"}]'
 *   data='[{"name":"Alice","age":30},{"name":"Bob","age":25}]'
 *   sortable
 *   paginated
 *   page-size="5"
 * ></ax-data-table>
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

class AxDataTable extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'columns', 'data', 'sortable', 'filterable', 'paginated', 'page-size', 'prompt', 'selectable', 'selection-mode'];
    }

    constructor() {
        super();
        this._sortColumn = null;
        this._sortDirection = 'asc';
        this._filters = {};
        this._currentPage = 1;
        this._selectedRows = new Set();
        this._processedData = [];
    }

    // =========================================================================
    // Attribute Getters
    // =========================================================================

    get columns() {
        return this.parseJsonAttribute('columns', []);
    }

    get data() {
        return this.parseJsonAttribute('data', []);
    }

    get sortable() {
        return this.hasAttribute('sortable');
    }

    get filterable() {
        return this.hasAttribute('filterable');
    }

    get paginated() {
        return this.hasAttribute('paginated');
    }

    get pageSize() {
        return parseInt(this.getAttribute('page-size')) || 10;
    }

    get prompt() {
        return this.getAttribute('prompt') || '';
    }

    get selectable() {
        return this.hasAttribute('selectable');
    }

    get selectionMode() {
        return this.getAttribute('selection-mode') || 'single';
    }

    // =========================================================================
    // Value Interface
    // =========================================================================

    getValue() {
        if (this.selectable) {
            const selectedData = this.data.filter((_, i) => this._selectedRows.has(i));
            return this.selectionMode === 'single' ? selectedData[0] || null : selectedData;
        }
        return this._processedData;
    }

    setValue(value) {
        if (this.selectable && Array.isArray(value)) {
            this._selectedRows = new Set(value);
            this.render();
        }
    }

    validate() {
        const errors = [];
        const warnings = [];

        if (this.columns.length === 0) {
            errors.push('Table must have at least one column defined');
        }

        if (this.selectable && this._selectedRows.size === 0 && this.required) {
            errors.push('Please select at least one row');
        }

        return { valid: errors.length === 0, errors, warnings };
    }

    // =========================================================================
    // Styles
    // =========================================================================

    async getStyles() {
        const isDark = this._isDarkTheme();
        return `
            ${await this.getBaseStyles()}

            :host {
                display: block;
                font-family: var(--ax-font-family, system-ui, -apple-system, sans-serif);

                /* Theme-aware variables */
                --ax-widget-bg: ${isDark ? '#1c2128' : '#f8f9fa'};
                --ax-border-color: ${isDark ? '#30363d' : '#dee2e6'};
                --ax-text-color: ${isDark ? '#e2e8f0' : '#212529'};
                --ax-text-muted: ${isDark ? '#8b949e' : '#6c757d'};
                --ax-header-bg: ${isDark ? '#21262d' : '#e9ecef'};
                --ax-header-hover-bg: ${isDark ? '#30363d' : '#dee2e6'};
                --ax-row-hover: ${isDark ? '#21262d' : '#f8f9fa'};
                --ax-filter-bg: ${isDark ? '#161b22' : '#f8f9fa'};
                --ax-border-light: ${isDark ? '#21262d' : '#f0f0f0'};
                --ax-input-bg: ${isDark ? '#0d1117' : '#ffffff'};
                --ax-primary-light: ${isDark ? '#1f3a5f' : '#e7f1ff'};
            }

            .widget-container {
                background: var(--ax-widget-bg);
                border: 1px solid var(--ax-border-color);
                border-radius: var(--ax-border-radius, 12px);
                padding: var(--ax-padding, 1.25rem);
                margin: var(--ax-margin, 0.5rem 0);
                overflow: hidden;
            }

            .prompt {
                font-size: 1rem;
                font-weight: 500;
                color: var(--ax-text-color);
                margin-bottom: 1rem;
                line-height: 1.5;
            }

            .table-wrapper {
                overflow-x: auto;
                margin: 0 -0.5rem;
                padding: 0 0.5rem;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.9rem;
            }

            thead {
                position: sticky;
                top: 0;
                z-index: 1;
            }

            th {
                background: var(--ax-header-bg);
                padding: 0.75rem 1rem;
                text-align: left;
                font-weight: 600;
                color: var(--ax-text-color);
                border-bottom: 2px solid var(--ax-border-color);
                white-space: nowrap;
            }

            th.sortable {
                cursor: pointer;
                user-select: none;
            }

            th.sortable:hover {
                background: var(--ax-header-hover-bg);
            }

            .sort-icon {
                display: inline-block;
                margin-left: 0.5rem;
                opacity: 0.3;
                transition: opacity 0.15s, transform 0.15s;
            }

            th.sorted .sort-icon {
                opacity: 1;
            }

            th.sorted.desc .sort-icon {
                transform: rotate(180deg);
            }

            td {
                padding: 0.75rem 1rem;
                border-bottom: 1px solid var(--ax-border-light);
                color: var(--ax-text-color);
            }

            tbody tr {
                transition: background 0.15s;
            }

            tbody tr:hover {
                background: var(--ax-row-hover);
            }

            tbody tr.selected {
                background: var(--ax-primary-light);
            }

            tbody tr.selectable {
                cursor: pointer;
            }

            .filter-row th {
                padding: 0.5rem;
                background: var(--ax-filter-bg);
            }

            .filter-input {
                width: 100%;
                padding: 0.375rem 0.5rem;
                border: 1px solid var(--ax-border-color);
                border-radius: 4px;
                font-size: 0.85rem;
                background: var(--ax-input-bg);
                color: var(--ax-text-color);
            }

            .filter-input::placeholder {
                color: var(--ax-text-muted);
            }

            .filter-input:focus {
                outline: none;
                border-color: var(--ax-primary-color, #0d6efd);
                box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.2);
            }

            .pagination {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding-top: 1rem;
                border-top: 1px solid var(--ax-border-color);
                margin-top: 1rem;
                gap: 1rem;
                flex-wrap: wrap;
            }

            .pagination-info {
                font-size: 0.85rem;
                color: var(--ax-text-muted);
            }

            .pagination-controls {
                display: flex;
                gap: 0.25rem;
            }

            .page-btn {
                padding: 0.375rem 0.75rem;
                border: 1px solid var(--ax-border-color);
                background: var(--ax-input-bg);
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.85rem;
                color: var(--ax-text-color);
                transition: all 0.15s;
            }

            .page-btn:hover:not(:disabled) {
                background: var(--ax-header-hover-bg);
            }

            .page-btn.active {
                background: var(--ax-primary-color, #0d6efd);
                border-color: var(--ax-primary-color, #0d6efd);
                color: white;
            }

            .page-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            .checkbox-cell {
                width: 40px;
                text-align: center;
            }

            .row-checkbox {
                width: 18px;
                height: 18px;
                cursor: pointer;
                accent-color: var(--ax-primary-color, #0d6efd);
            }

            .empty-message {
                text-align: center;
                padding: 2rem;
                color: var(--ax-text-muted);
            }
        `;
    }

    // =========================================================================
    // Rendering
    // =========================================================================

    render() {
        const columns = this.columns;
        const rawData = this.data;

        // Process data: filter, sort, paginate
        let processedData = [...rawData];

        // Apply filters
        if (this.filterable) {
            processedData = this._applyFilters(processedData);
        }

        // Apply sorting
        if (this._sortColumn) {
            processedData = this._applySort(processedData);
        }

        this._processedData = processedData;

        // Apply pagination
        const totalRows = processedData.length;
        const totalPages = this.paginated ? Math.ceil(totalRows / this.pageSize) : 1;

        if (this._currentPage > totalPages && totalPages > 0) {
            this._currentPage = totalPages;
        }

        const paginatedData = this.paginated ? processedData.slice((this._currentPage - 1) * this.pageSize, this._currentPage * this.pageSize) : processedData;

        this.shadowRoot.innerHTML = `
            <style>${this._styles || ''}</style>
            <div class="widget-container">
                ${this.prompt ? `<div class="prompt">${this.renderMarkdown(this.prompt)}</div>` : ''}
                <div class="table-wrapper">
                    <table role="grid" aria-label="${this.prompt || 'Data table'}">
                        <thead>
                            ${this._renderHeaderRow(columns)}
                            ${this.filterable ? this._renderFilterRow(columns) : ''}
                        </thead>
                        <tbody>
                            ${
                                paginatedData.length > 0
                                    ? paginatedData.map((row, i) => this._renderDataRow(row, columns, (this._currentPage - 1) * this.pageSize + i)).join('')
                                    : `<tr><td colspan="${columns.length + (this.selectable ? 1 : 0)}" class="empty-message">No data available</td></tr>`
                            }
                        </tbody>
                    </table>
                </div>
                ${this.paginated ? this._renderPagination(totalRows, totalPages) : ''}
            </div>
        `;
    }

    _renderHeaderRow(columns) {
        return `
            <tr>
                ${
                    this.selectable
                        ? `
                    <th class="checkbox-cell">
                        ${
                            this.selectionMode === 'multiple'
                                ? `
                            <input type="checkbox" class="row-checkbox select-all"
                                   aria-label="Select all rows"
                                   ${this._isAllSelected() ? 'checked' : ''}>
                        `
                                : ''
                        }
                    </th>
                `
                        : ''
                }
                ${columns
                    .map(
                        col => `
                    <th class="${col.sortable !== false && this.sortable ? 'sortable' : ''}
                               ${this._sortColumn === col.id ? 'sorted' : ''}
                               ${this._sortDirection === 'desc' ? 'desc' : ''}"
                        data-column="${col.id}"
                        style="${col.width ? `width: ${col.width}` : ''}"
                        ${col.sortable !== false && this.sortable ? 'role="columnheader" aria-sort="' + this._getAriaSortValue(col.id) + '"' : ''}>
                        ${this.escapeHtml(col.label)}
                        ${
                            col.sortable !== false && this.sortable
                                ? `
                            <span class="sort-icon" aria-hidden="true">▲</span>
                        `
                                : ''
                        }
                    </th>
                `
                    )
                    .join('')}
            </tr>
        `;
    }

    _renderFilterRow(columns) {
        return `
            <tr class="filter-row">
                ${this.selectable ? '<th></th>' : ''}
                ${columns
                    .map(
                        col => `
                    <th>
                        ${
                            col.filterable !== false
                                ? `
                            <input type="text"
                                   class="filter-input"
                                   data-column="${col.id}"
                                   placeholder="Filter..."
                                   value="${this._filters[col.id] || ''}"
                                   aria-label="Filter ${col.label}">
                        `
                                : ''
                        }
                    </th>
                `
                    )
                    .join('')}
            </tr>
        `;
    }

    _renderDataRow(row, columns, index) {
        const isSelected = this._selectedRows.has(index);
        return `
            <tr class="${isSelected ? 'selected' : ''} ${this.selectable ? 'selectable' : ''}"
                data-index="${index}"
                role="row"
                aria-selected="${isSelected}">
                ${
                    this.selectable
                        ? `
                    <td class="checkbox-cell">
                        <input type="${this.selectionMode === 'single' ? 'radio' : 'checkbox'}"
                               class="row-checkbox"
                               name="row-select"
                               ${isSelected ? 'checked' : ''}
                               aria-label="Select row ${index + 1}">
                    </td>
                `
                        : ''
                }
                ${columns
                    .map(
                        col => `
                    <td>${this._formatCell(row[col.id], col)}</td>
                `
                    )
                    .join('')}
            </tr>
        `;
    }

    _renderPagination(totalRows, totalPages) {
        const start = (this._currentPage - 1) * this.pageSize + 1;
        const end = Math.min(this._currentPage * this.pageSize, totalRows);

        return `
            <div class="pagination" role="navigation" aria-label="Table pagination">
                <span class="pagination-info">
                    Showing ${totalRows > 0 ? start : 0}–${end} of ${totalRows} rows
                </span>
                <div class="pagination-controls">
                    <button class="page-btn" data-page="prev" ${this._currentPage <= 1 ? 'disabled' : ''} aria-label="Previous page">
                        ‹
                    </button>
                    ${this._renderPageButtons(totalPages)}
                    <button class="page-btn" data-page="next" ${this._currentPage >= totalPages ? 'disabled' : ''} aria-label="Next page">
                        ›
                    </button>
                </div>
            </div>
        `;
    }

    _renderPageButtons(totalPages) {
        if (totalPages <= 7) {
            return Array.from({ length: totalPages }, (_, i) => i + 1)
                .map(p => `<button class="page-btn ${p === this._currentPage ? 'active' : ''}" data-page="${p}">${p}</button>`)
                .join('');
        }

        // Abbreviated pagination for many pages
        const pages = [];
        pages.push(1);

        if (this._currentPage > 3) pages.push('...');

        for (let i = Math.max(2, this._currentPage - 1); i <= Math.min(totalPages - 1, this._currentPage + 1); i++) {
            pages.push(i);
        }

        if (this._currentPage < totalPages - 2) pages.push('...');

        if (totalPages > 1) pages.push(totalPages);

        return pages
            .map(p => {
                if (p === '...') return '<span class="page-btn" disabled>…</span>';
                return `<button class="page-btn ${p === this._currentPage ? 'active' : ''}" data-page="${p}">${p}</button>`;
            })
            .join('');
    }

    // =========================================================================
    // Data Processing
    // =========================================================================

    _applyFilters(data) {
        return data.filter(row => {
            return Object.entries(this._filters).every(([colId, filterValue]) => {
                if (!filterValue) return true;
                const cellValue = String(row[colId] || '').toLowerCase();
                return cellValue.includes(filterValue.toLowerCase());
            });
        });
    }

    _applySort(data) {
        const col = this._sortColumn;
        const dir = this._sortDirection;

        return [...data].sort((a, b) => {
            let valA = a[col];
            let valB = b[col];

            // Handle null/undefined
            if (valA == null) return dir === 'asc' ? -1 : 1;
            if (valB == null) return dir === 'asc' ? 1 : -1;

            // Numeric comparison
            if (typeof valA === 'number' && typeof valB === 'number') {
                return dir === 'asc' ? valA - valB : valB - valA;
            }

            // String comparison
            valA = String(valA).toLowerCase();
            valB = String(valB).toLowerCase();

            if (valA < valB) return dir === 'asc' ? -1 : 1;
            if (valA > valB) return dir === 'asc' ? 1 : -1;
            return 0;
        });
    }

    _formatCell(value, column) {
        if (value == null) return '';

        if (column.formatter) {
            return column.formatter(value);
        }

        if (column.type === 'date' && value) {
            try {
                return new Date(value).toLocaleDateString();
            } catch {
                return value;
            }
        }

        if (column.type === 'number' && typeof value === 'number') {
            return value.toLocaleString();
        }

        return this.escapeHtml(String(value));
    }

    _getAriaSortValue(columnId) {
        if (this._sortColumn !== columnId) return 'none';
        return this._sortDirection === 'asc' ? 'ascending' : 'descending';
    }

    _isAllSelected() {
        const data = this.data;
        return data.length > 0 && data.every((_, i) => this._selectedRows.has(i));
    }

    /**
     * Update only table body and pagination without re-rendering header/filters
     * This preserves filter input focus during filtering
     * @private
     */
    _updateTableContent() {
        const columns = this.columns;
        let processedData = [...this.data];

        // Apply filters
        if (this.filterable) {
            processedData = this._applyFilters(processedData);
        }

        // Apply sorting
        if (this._sortColumn) {
            processedData = this._applySort(processedData);
        }

        this._processedData = processedData;

        // Apply pagination
        const totalRows = processedData.length;
        const totalPages = this.paginated ? Math.ceil(totalRows / this.pageSize) : 1;

        if (this._currentPage > totalPages && totalPages > 0) {
            this._currentPage = totalPages;
        }

        const paginatedData = this.paginated ? processedData.slice((this._currentPage - 1) * this.pageSize, this._currentPage * this.pageSize) : processedData;

        // Update only tbody
        const tbody = this.shadowRoot.querySelector('tbody');
        if (tbody) {
            tbody.innerHTML =
                paginatedData.length > 0
                    ? paginatedData.map((row, i) => this._renderDataRow(row, columns, (this._currentPage - 1) * this.pageSize + i)).join('')
                    : `<tr><td colspan="${columns.length + (this.selectable ? 1 : 0)}" class="empty-message">No data available</td></tr>`;
        }

        // Update pagination if present
        const pagination = this.shadowRoot.querySelector('.pagination');
        if (pagination && this.paginated) {
            pagination.outerHTML = this._renderPagination(totalRows, totalPages);
            // Re-bind pagination events
            this.shadowRoot.querySelectorAll('.page-btn[data-page]').forEach(btn => {
                btn.addEventListener('click', () => this._handlePageChange(btn.dataset.page));
            });
        }

        // Re-bind row events
        this._bindRowEvents();
    }

    /**
     * Bind events only to rows (not header/filters)
     * @private
     */
    _bindRowEvents() {
        // Row selection
        if (this.selectable) {
            this.shadowRoot.querySelectorAll('tbody tr.selectable').forEach(tr => {
                tr.addEventListener('click', e => {
                    if (e.target.classList.contains('row-checkbox')) return;
                    this._handleRowSelect(parseInt(tr.dataset.index));
                });
            });

            this.shadowRoot.querySelectorAll('.row-checkbox:not(.select-all)').forEach(cb => {
                cb.addEventListener('change', e => {
                    const tr = e.target.closest('tr');
                    this._handleRowSelect(parseInt(tr.dataset.index));
                });
            });
        }

        // Row click
        this.shadowRoot.querySelectorAll('tbody tr').forEach(tr => {
            tr.addEventListener('dblclick', () => {
                const index = parseInt(tr.dataset.index);
                const row = this.data[index];
                this.dispatchEvent(
                    new CustomEvent('ax-row-click', {
                        bubbles: true,
                        composed: true,
                        detail: { widgetId: this.widgetId, index, row },
                    })
                );
            });
        });
    }

    // =========================================================================
    // Events
    // =========================================================================

    bindEvents() {
        // Sort headers
        this.shadowRoot.querySelectorAll('th.sortable').forEach(th => {
            th.addEventListener('click', () => this._handleSort(th.dataset.column));
        });

        // Filter inputs - use keyup with debounce, update only table body
        this.shadowRoot.querySelectorAll('.filter-input').forEach(input => {
            // Store reference to prevent re-binding issues
            if (input._filterBound) return;
            input._filterBound = true;

            const debouncedFilter = this.debounce((value, column) => {
                this._filters[column] = value;
                this._currentPage = 1;
                this._updateTableContent();
            }, 300);

            input.addEventListener('input', e => {
                debouncedFilter(e.target.value, e.target.dataset.column);
            });
        });

        // Pagination
        this.shadowRoot.querySelectorAll('.page-btn[data-page]').forEach(btn => {
            btn.addEventListener('click', () => this._handlePageChange(btn.dataset.page));
        });

        // Row selection
        if (this.selectable) {
            this.shadowRoot.querySelectorAll('tbody tr.selectable').forEach(tr => {
                tr.addEventListener('click', e => {
                    if (e.target.classList.contains('row-checkbox')) return;
                    this._handleRowSelect(parseInt(tr.dataset.index));
                });
            });

            this.shadowRoot.querySelectorAll('.row-checkbox:not(.select-all)').forEach(cb => {
                cb.addEventListener('change', e => {
                    const tr = e.target.closest('tr');
                    this._handleRowSelect(parseInt(tr.dataset.index));
                });
            });

            const selectAll = this.shadowRoot.querySelector('.select-all');
            if (selectAll) {
                selectAll.addEventListener('change', () => this._handleSelectAll());
            }
        }

        // Row click
        this.shadowRoot.querySelectorAll('tbody tr').forEach(tr => {
            tr.addEventListener('dblclick', () => {
                const index = parseInt(tr.dataset.index);
                const row = this.data[index];
                this.dispatchEvent(
                    new CustomEvent('ax-row-click', {
                        bubbles: true,
                        composed: true,
                        detail: { widgetId: this.widgetId, index, row },
                    })
                );
            });
        });
    }

    _handleSort(columnId) {
        if (this._sortColumn === columnId) {
            this._sortDirection = this._sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this._sortColumn = columnId;
            this._sortDirection = 'asc';
        }

        this.dispatchEvent(
            new CustomEvent('ax-sort-change', {
                bubbles: true,
                composed: true,
                detail: {
                    widgetId: this.widgetId,
                    column: columnId,
                    direction: this._sortDirection,
                },
            })
        );

        this.render();
        this.bindEvents();
    }

    _handlePageChange(page) {
        if (page === 'prev') {
            this._currentPage = Math.max(1, this._currentPage - 1);
        } else if (page === 'next') {
            const totalPages = Math.ceil(this._processedData.length / this.pageSize);
            this._currentPage = Math.min(totalPages, this._currentPage + 1);
        } else {
            this._currentPage = parseInt(page);
        }

        this.dispatchEvent(
            new CustomEvent('ax-page-change', {
                bubbles: true,
                composed: true,
                detail: { widgetId: this.widgetId, page: this._currentPage },
            })
        );

        this.render();
        this.bindEvents();
    }

    _handleRowSelect(index) {
        if (this.selectionMode === 'single') {
            this._selectedRows.clear();
            this._selectedRows.add(index);
        } else {
            if (this._selectedRows.has(index)) {
                this._selectedRows.delete(index);
            } else {
                this._selectedRows.add(index);
            }
        }

        this.dispatchEvent(
            new CustomEvent('ax-row-select', {
                bubbles: true,
                composed: true,
                detail: {
                    widgetId: this.widgetId,
                    selectedIndices: Array.from(this._selectedRows),
                    selectedRows: this.getValue(),
                },
            })
        );

        this.render();
        this.bindEvents();
    }

    _handleSelectAll() {
        const data = this.data;

        if (this._isAllSelected()) {
            this._selectedRows.clear();
        } else {
            data.forEach((_, i) => this._selectedRows.add(i));
        }

        this.dispatchEvent(
            new CustomEvent('ax-row-select', {
                bubbles: true,
                composed: true,
                detail: {
                    widgetId: this.widgetId,
                    selectedIndices: Array.from(this._selectedRows),
                    selectedRows: this.getValue(),
                },
            })
        );

        this.render();
        this.bindEvents();
    }

    onAttributeChange(name, oldValue, newValue) {
        if (!this._initialized) return;

        if (name === 'data' || name === 'columns') {
            this._currentPage = 1;
            this._selectedRows.clear();
        }

        this.render();
        this.bindEvents();
    }

    async loadStyles() {
        this._styles = await this.getStyles();
    }
}

// Register custom element
if (!customElements.get('ax-data-table')) {
    customElements.define('ax-data-table', AxDataTable);
}

export default AxDataTable;
