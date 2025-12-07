/**
 * Data Table Component
 *
 * A reusable table component with sorting, filtering, and pagination.
 * Works with any data shape via column definitions.
 *
 * Usage:
 *   <data-table id="my-table"></data-table>
 *
 *   const table = document.getElementById('my-table');
 *   table.columns = [
 *     { key: 'name', label: 'Name', sortable: true },
 *     { key: 'status', label: 'Status', render: (val) => `<span class="badge">${val}</span>` }
 *   ];
 *   table.data = [...];
 */

const DEFAULT_PAGE_SIZE = 10;

class DataTable extends HTMLElement {
    constructor() {
        super();
        this._columns = [];
        this._data = [];
        this._filteredData = [];
        this._sortColumn = null;
        this._sortDirection = 'asc';
        this._currentPage = 1;
        this._pageSize = DEFAULT_PAGE_SIZE;
        this._searchTerm = '';
        this._loading = false;
        this._emptyMessage = 'No data available';
        this._selectable = false;
        this._selectedItems = new Set();
    }

    // Column definitions: [{ key, label, sortable?, render?, searchable? }]
    set columns(value) {
        this._columns = value;
        this.render();
    }

    get columns() {
        return this._columns;
    }

    // Data array
    set data(value) {
        this._data = value || [];
        this._applyFilter();
        this._currentPage = 1;
        this.render();
    }

    get data() {
        return this._data;
    }

    // Loading state
    set loading(value) {
        this._loading = value;
        this.render();
    }

    get loading() {
        return this._loading;
    }

    // Empty message
    set emptyMessage(value) {
        this._emptyMessage = value;
    }

    // Selectable rows
    set selectable(value) {
        this._selectable = value;
        this.render();
    }

    get selectedItems() {
        return Array.from(this._selectedItems);
    }

    // Page size
    set pageSize(value) {
        this._pageSize = value;
        this._currentPage = 1;
        this.render();
    }

    connectedCallback() {
        this.render();
    }

    render() {
        const paginatedData = this._getPaginatedData();
        const totalPages = Math.ceil(this._filteredData.length / this._pageSize);

        this.innerHTML = `
            <div class="data-table-container">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <div class="input-group" style="max-width: 300px;">
                        <span class="input-group-text">
                            <i class="bi bi-search"></i>
                        </span>
                        <input type="text" class="form-control" placeholder="Search..."
                               value="${this._escapeHtml(this._searchTerm)}" id="table-search">
                    </div>
                    <div class="text-muted small">
                        ${this._filteredData.length} items
                    </div>
                </div>

                <div class="table-responsive">
                    <table class="table table-hover align-middle">
                        <thead>
                            <tr>
                                ${this._selectable ? '<th class="select-col"><input type="checkbox" class="form-check-input" id="select-all"></th>' : ''}
                                ${this._columns.map(col => this._renderHeaderCell(col)).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${this._loading ? this._renderLoadingRows() : this._renderDataRows(paginatedData)}
                        </tbody>
                    </table>
                </div>

                ${totalPages > 1 ? this._renderPagination(totalPages) : ''}
            </div>
        `;

        this._attachEventListeners();
    }

    _renderHeaderCell(col) {
        const isSorted = this._sortColumn === col.key;
        const sortIcon = isSorted ? (this._sortDirection === 'asc' ? '<i class="bi bi-sort-up"></i>' : '<i class="bi bi-sort-down"></i>') : '';

        const sortClass = col.sortable ? 'sortable' : '';
        return `
            <th class="${sortClass}" data-column="${col.key}">
                ${this._escapeHtml(col.label)}
                ${col.sortable ? `<span class="sort-icon ms-1">${sortIcon}</span>` : ''}
            </th>
        `;
    }

    _renderLoadingRows() {
        return `
            <tr>
                <td colspan="${this._columns.length + (this._selectable ? 1 : 0)}" class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </td>
            </tr>
        `;
    }

    _renderDataRows(data) {
        if (data.length === 0) {
            return `
                <tr>
                    <td colspan="${this._columns.length + (this._selectable ? 1 : 0)}" class="text-center py-4 text-muted">
                        <i class="bi bi-inbox display-6 d-block mb-2"></i>
                        ${this._escapeHtml(this._emptyMessage)}
                    </td>
                </tr>
            `;
        }

        return data
            .map((row, index) => {
                const rowId = row.id || row._id || index;
                const isSelected = this._selectedItems.has(rowId);
                return `
                <tr data-row-id="${rowId}" class="${isSelected ? 'table-active' : ''}">
                    ${
                        this._selectable
                            ? `
                        <td class="select-col">
                            <input type="checkbox" class="form-check-input row-select"
                                   data-id="${rowId}" ${isSelected ? 'checked' : ''}>
                        </td>
                    `
                            : ''
                    }
                    ${this._columns.map(col => this._renderDataCell(row, col)).join('')}
                </tr>
            `;
            })
            .join('');
    }

    _renderDataCell(row, col) {
        const value = this._getNestedValue(row, col.key);
        const rendered = col.render ? col.render(value, row) : this._escapeHtml(value ?? '');
        return `<td>${rendered}</td>`;
    }

    _renderPagination(totalPages) {
        const pages = this._getPaginationRange(totalPages);

        return `
            <nav aria-label="Table navigation" class="mt-3">
                <ul class="pagination pagination-sm justify-content-center mb-0">
                    <li class="page-item ${this._currentPage === 1 ? 'disabled' : ''}">
                        <a class="page-link" href="#" data-page="${this._currentPage - 1}" aria-label="Previous">
                            <i class="bi bi-chevron-left"></i>
                        </a>
                    </li>
                    ${pages
                        .map(p => {
                            if (p === '...') {
                                return '<li class="page-item disabled"><span class="page-link">...</span></li>';
                            }
                            return `
                            <li class="page-item ${p === this._currentPage ? 'active' : ''}">
                                <a class="page-link" href="#" data-page="${p}">${p}</a>
                            </li>
                        `;
                        })
                        .join('')}
                    <li class="page-item ${this._currentPage === totalPages ? 'disabled' : ''}">
                        <a class="page-link" href="#" data-page="${this._currentPage + 1}" aria-label="Next">
                            <i class="bi bi-chevron-right"></i>
                        </a>
                    </li>
                </ul>
            </nav>
        `;
    }

    _getPaginationRange(totalPages) {
        const delta = 2;
        const range = [];
        const left = Math.max(2, this._currentPage - delta);
        const right = Math.min(totalPages - 1, this._currentPage + delta);

        range.push(1);
        if (left > 2) range.push('...');
        for (let i = left; i <= right; i++) range.push(i);
        if (right < totalPages - 1) range.push('...');
        if (totalPages > 1) range.push(totalPages);

        return range;
    }

    _attachEventListeners() {
        // Search
        const searchInput = this.querySelector('#table-search');
        if (searchInput) {
            searchInput.addEventListener('input', e => {
                this._searchTerm = e.target.value;
                this._applyFilter();
                this._currentPage = 1;
                this.render();
            });
        }

        // Sortable headers
        this.querySelectorAll('th.sortable').forEach(th => {
            th.addEventListener('click', () => {
                const column = th.dataset.column;
                if (this._sortColumn === column) {
                    this._sortDirection = this._sortDirection === 'asc' ? 'desc' : 'asc';
                } else {
                    this._sortColumn = column;
                    this._sortDirection = 'asc';
                }
                this._applySort();
                this.render();
            });
        });

        // Pagination
        this.querySelectorAll('.page-link[data-page]').forEach(link => {
            link.addEventListener('click', e => {
                e.preventDefault();
                const page = parseInt(link.dataset.page, 10);
                if (page >= 1 && page <= Math.ceil(this._filteredData.length / this._pageSize)) {
                    this._currentPage = page;
                    this.render();
                }
            });
        });

        // Row selection
        if (this._selectable) {
            const selectAll = this.querySelector('#select-all');
            if (selectAll) {
                selectAll.addEventListener('change', e => {
                    if (e.target.checked) {
                        this._filteredData.forEach((row, i) => {
                            this._selectedItems.add(row.id || row._id || i);
                        });
                    } else {
                        this._selectedItems.clear();
                    }
                    this.render();
                    this._dispatchSelectionChange();
                });
            }

            this.querySelectorAll('.row-select').forEach(cb => {
                cb.addEventListener('change', e => {
                    const id = cb.dataset.id;
                    if (e.target.checked) {
                        this._selectedItems.add(id);
                    } else {
                        this._selectedItems.delete(id);
                    }
                    this.render();
                    this._dispatchSelectionChange();
                });
            });
        }

        // Row click (dispatch event for parent handling)
        this.querySelectorAll('tbody tr[data-row-id]').forEach(tr => {
            tr.addEventListener('click', e => {
                // Don't trigger on checkbox click
                if (e.target.type === 'checkbox') return;

                const rowId = tr.dataset.rowId;
                const rowData = this._data.find((r, i) => (r.id || r._id || i).toString() === rowId);
                this.dispatchEvent(
                    new CustomEvent('row-click', {
                        detail: { id: rowId, data: rowData },
                        bubbles: true,
                    })
                );
            });
        });
    }

    _applyFilter() {
        if (!this._searchTerm) {
            this._filteredData = [...this._data];
        } else {
            const term = this._searchTerm.toLowerCase();
            this._filteredData = this._data.filter(row => {
                return this._columns.some(col => {
                    if (col.searchable === false) return false;
                    const value = this._getNestedValue(row, col.key);
                    return value && value.toString().toLowerCase().includes(term);
                });
            });
        }
        this._applySort();
    }

    _applySort() {
        if (!this._sortColumn) return;

        this._filteredData.sort((a, b) => {
            const aVal = this._getNestedValue(a, this._sortColumn);
            const bVal = this._getNestedValue(b, this._sortColumn);

            let comparison = 0;
            if (aVal === null || aVal === undefined) comparison = 1;
            else if (bVal === null || bVal === undefined) comparison = -1;
            else if (typeof aVal === 'string') comparison = aVal.localeCompare(bVal);
            else comparison = aVal - bVal;

            return this._sortDirection === 'asc' ? comparison : -comparison;
        });
    }

    _getPaginatedData() {
        const start = (this._currentPage - 1) * this._pageSize;
        return this._filteredData.slice(start, start + this._pageSize);
    }

    _getNestedValue(obj, path) {
        return path.split('.').reduce((o, p) => o?.[p], obj);
    }

    _escapeHtml(str) {
        if (str === null || str === undefined) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    _dispatchSelectionChange() {
        this.dispatchEvent(
            new CustomEvent('selection-change', {
                detail: { selected: this.selectedItems },
                bubbles: true,
            })
        );
    }

    // Public methods
    refresh() {
        this.render();
    }

    clearSelection() {
        this._selectedItems.clear();
        this.render();
    }
}

if (!customElements.get('data-table')) {
    customElements.define('data-table', DataTable);
}

export { DataTable };
