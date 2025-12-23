/**
 * Data Table Widget Configuration
 *
 * Configuration UI for the 'data_table' widget type.
 * Supports sortable, filterable, paginated tables with type hints.
 *
 * Features:
 * - Visual column builder with add/remove
 * - Column type hints (text, number, date, boolean)
 * - CSV import for bulk data entry
 * - Live preview in modal
 * - Sorting/filtering per column
 *
 * @module admin/widget-config/data-table-config
 */

import { WidgetConfigBase } from './config-base.js';

/**
 * Column data type options
 */
const COLUMN_TYPE_OPTIONS = [
    { value: 'text', label: 'Text' },
    { value: 'number', label: 'Number' },
    { value: 'date', label: 'Date' },
    { value: 'boolean', label: 'Boolean' },
];

/**
 * Page size options
 */
const PAGE_SIZE_OPTIONS = [
    { value: '5', label: '5 rows' },
    { value: '10', label: '10 rows' },
    { value: '15', label: '15 rows' },
    { value: '20', label: '20 rows' },
    { value: '25', label: '25 rows' },
    { value: '50', label: '50 rows' },
];

export class DataTableConfig extends WidgetConfigBase {
    constructor(containerEl, widgetType) {
        super(containerEl, widgetType);
        this._columns = [];
        this._data = [];
    }

    /**
     * Render the data table widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        // Initialize columns and data from config
        this._columns = config.columns || [];
        this._data = config.data || [];

        // If no columns, add a default one
        if (this._columns.length === 0) {
            this._columns.push({
                id: 'column1',
                label: 'Column 1',
                type: 'text',
                sortable: true,
                filterable: true,
                width: null,
            });
        }

        this.container.innerHTML = `
            <div class="widget-config widget-config-data-table" data-uid="${this.uid}">
                <!-- Table Options -->
                <div class="row g-2">
                    <div class="col-md-2">
                        ${this.createSwitch('config-sortable', `${this.uid}-sortable`, 'Sortable', 'Allow sorting by clicking column headers.', config.sortable !== false)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-filterable', `${this.uid}-filterable`, 'Filterable', 'Show filter inputs for columns.', config.filterable !== false)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-paginated', `${this.uid}-paginated`, 'Paginated', 'Show pagination controls.', config.paginated !== false)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-selectable', `${this.uid}-selectable`, 'Selectable', 'Allow row selection with checkboxes.', config.selectable === true)}
                    </div>
                    <div class="col-md-2">
                        ${this.createFormGroup(
                            'Page Size',
                            this.createSelect('config-page-size', PAGE_SIZE_OPTIONS, String(config.page_size || config.pageSize || 10)),
                            'Rows per page when paginated.'
                        )}
                    </div>
                </div>

                <!-- Columns Section -->
                <div class="mt-3">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <label class="form-label small mb-0 fw-bold">
                            <i class="bi bi-layout-three-columns me-1"></i>Columns
                            <span class="text-danger">*</span>
                        </label>
                        <button class="btn btn-outline-success btn-sm config-add-column-btn" type="button">
                            <i class="bi bi-plus-lg me-1"></i>Add Column
                        </button>
                    </div>
                    <div class="columns-container">
                        ${this._renderColumns()}
                    </div>
                </div>

                <!-- Data Section -->
                <div class="mt-3">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <label class="form-label small mb-0 fw-bold">
                            <i class="bi bi-table me-1"></i>Data Rows
                            <span class="badge bg-secondary ms-1">${this._data.length} rows</span>
                        </label>
                        <div>
                            <button class="btn btn-outline-primary btn-sm config-import-csv-btn" type="button">
                                <i class="bi bi-file-earmark-spreadsheet me-1"></i>Import CSV
                            </button>
                            <button class="btn btn-outline-success btn-sm config-add-row-btn ms-1" type="button">
                                <i class="bi bi-plus-lg me-1"></i>Add Row
                            </button>
                            <button class="btn btn-outline-danger btn-sm config-clear-data-btn ms-1" type="button"
                                    ${this._data.length === 0 ? 'disabled' : ''}>
                                <i class="bi bi-trash me-1"></i>Clear All
                            </button>
                        </div>
                    </div>
                    <div class="data-container">
                        ${this._renderDataTable()}
                    </div>
                </div>

                <!-- Preview Button -->
                <div class="mt-3 d-flex justify-content-end">
                    <button class="btn btn-outline-info btn-sm config-preview-btn" type="button">
                        <i class="bi bi-eye me-1"></i>Preview Table
                    </button>
                </div>

                <!-- CSV Import Modal -->
                ${this._renderCsvImportModal()}

                <!-- Preview Modal -->
                ${this._renderPreviewModal()}
            </div>
        `;

        this._bindEvents();
        this.initTooltips();
    }

    /**
     * Render all columns
     * @private
     */
    _renderColumns() {
        return this._columns
            .map(
                (col, idx) => `
            <div class="card mb-2 column-card" data-index="${idx}">
                <div class="card-body p-2">
                    <div class="row g-2 align-items-end">
                        <div class="col-md-2">
                            <label class="form-label small mb-0">ID</label>
                            <input type="text" class="form-control form-control-sm column-id"
                                   value="${this.escapeHtml(col.id || `col${idx + 1}`)}"
                                   placeholder="column_id">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small mb-0">Label</label>
                            <input type="text" class="form-control form-control-sm column-label"
                                   value="${this.escapeHtml(col.label || `Column ${idx + 1}`)}"
                                   placeholder="Column Label">
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small mb-0">Type</label>
                            ${this.createSelect('column-type', COLUMN_TYPE_OPTIONS, col.type || 'text')}
                        </div>
                        <div class="col-md-1">
                            <label class="form-label small mb-0">Width</label>
                            <input type="text" class="form-control form-control-sm column-width"
                                   value="${this.escapeHtml(col.width || '')}"
                                   placeholder="auto">
                        </div>
                        <div class="col-md-1">
                            <div class="form-check">
                                <input type="checkbox" class="form-check-input column-sortable"
                                       ${col.sortable !== false ? 'checked' : ''}>
                                <label class="form-check-label small">Sort</label>
                            </div>
                        </div>
                        <div class="col-md-1">
                            <div class="form-check">
                                <input type="checkbox" class="form-check-input column-filterable"
                                       ${col.filterable !== false ? 'checked' : ''}>
                                <label class="form-check-label small">Filter</label>
                            </div>
                        </div>
                        <div class="col-auto">
                            <button class="btn btn-sm btn-outline-danger remove-column-btn" type="button"
                                    ${this._columns.length <= 1 ? 'disabled' : ''}>
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `
            )
            .join('');
    }

    /**
     * Render data table for editing
     * @private
     */
    _renderDataTable() {
        if (this._columns.length === 0) {
            return '<p class="text-muted small">Add columns first, then add data rows.</p>';
        }

        if (this._data.length === 0) {
            return '<p class="text-muted small">No data rows. Click "Add Row" or "Import CSV" to add data.</p>';
        }

        // Limit display to first 20 rows for performance
        const displayData = this._data.slice(0, 20);
        const hasMore = this._data.length > 20;

        let html = `
            <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
                <table class="table table-sm table-bordered table-hover data-edit-table">
                    <thead class="table-light sticky-top">
                        <tr>
                            <th style="width: 40px">#</th>
                            ${this._columns.map(col => `<th>${this.escapeHtml(col.label || col.id)}</th>`).join('')}
                            <th style="width: 50px"></th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        displayData.forEach((row, rowIdx) => {
            html += `
                <tr data-row-index="${rowIdx}">
                    <td class="text-muted small">${rowIdx + 1}</td>
                    ${this._columns
                        .map(
                            col => `
                        <td>
                            <input type="text" class="form-control form-control-sm border-0 data-cell"
                                   data-column="${col.id}"
                                   value="${this.escapeHtml(row[col.id] ?? '')}">
                        </td>
                    `
                        )
                        .join('')}
                    <td>
                        <button class="btn btn-sm btn-link text-danger p-0 remove-row-btn" type="button">
                            <i class="bi bi-x-lg"></i>
                        </button>
                    </td>
                </tr>
            `;
        });

        html += '</tbody></table></div>';

        if (hasMore) {
            html += `<p class="text-muted small mt-1">Showing first 20 of ${this._data.length} rows. All data will be saved.</p>`;
        }

        return html;
    }

    /**
     * Render CSV import modal
     * @private
     */
    _renderCsvImportModal() {
        return `
            <div class="modal fade" id="${this.uid}-csv-modal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-file-earmark-spreadsheet me-2"></i>Import Data from CSV
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">Delimiter</label>
                                <div class="btn-group" role="group">
                                    <input type="radio" class="btn-check" name="${this.uid}-delimiter"
                                           id="${this.uid}-delim-auto" value="auto" checked>
                                    <label class="btn btn-outline-secondary btn-sm" for="${this.uid}-delim-auto">Auto-detect</label>

                                    <input type="radio" class="btn-check" name="${this.uid}-delimiter"
                                           id="${this.uid}-delim-comma" value=",">
                                    <label class="btn btn-outline-secondary btn-sm" for="${this.uid}-delim-comma">Comma (,)</label>

                                    <input type="radio" class="btn-check" name="${this.uid}-delimiter"
                                           id="${this.uid}-delim-tab" value="\t">
                                    <label class="btn btn-outline-secondary btn-sm" for="${this.uid}-delim-tab">Tab</label>
                                </div>
                            </div>
                            <div class="form-check mb-3">
                                <input type="checkbox" class="form-check-input" id="${this.uid}-has-headers" checked>
                                <label class="form-check-label" for="${this.uid}-has-headers">
                                    First row contains column headers
                                </label>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">
                                    Paste CSV Data
                                </label>
                                <textarea class="form-control csv-input" rows="10"
                                          placeholder="name,category,price,stock&#10;Wireless Mouse,Electronics,29.99,150&#10;Keyboard,Electronics,89.99,75"></textarea>
                            </div>
                            <div class="csv-preview-container" style="display:none">
                                <label class="form-label">Preview</label>
                                <div class="table-responsive" style="max-height: 200px; overflow-y: auto;">
                                    <table class="table table-sm table-bordered csv-preview-table"></table>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary csv-apply-btn">
                                <i class="bi bi-check-lg me-1"></i>Apply
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render preview modal
     * @private
     */
    _renderPreviewModal() {
        return `
            <div class="modal fade" id="${this.uid}-preview-modal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-table me-2"></i>Data Table Preview
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="table-preview-container"></div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Bind event handlers
     * @private
     */
    _bindEvents() {
        // Add column
        this.query('.config-add-column-btn')?.addEventListener('click', () => {
            this._addColumn();
        });

        // Add row
        this.query('.config-add-row-btn')?.addEventListener('click', () => {
            this._addRow();
        });

        // Clear all data
        this.query('.config-clear-data-btn')?.addEventListener('click', () => {
            if (confirm('Are you sure you want to clear all data rows?')) {
                this._data = [];
                this._rerenderData();
            }
        });

        // Import CSV button
        this.query('.config-import-csv-btn')?.addEventListener('click', () => {
            const modal = new bootstrap.Modal(document.getElementById(`${this.uid}-csv-modal`));
            modal.show();
        });

        // CSV input change - show preview
        this.query('.csv-input')?.addEventListener('input', e => {
            this._previewCsv(e.target.value);
        });

        // CSV apply
        this.query('.csv-apply-btn')?.addEventListener('click', () => {
            this._applyCsv();
        });

        // Preview button
        this.query('.config-preview-btn')?.addEventListener('click', () => {
            this._showPreview();
        });

        // Bind column and row events
        this._bindColumnEvents();
        this._bindDataEvents();
    }

    /**
     * Bind events for column cards
     * @private
     */
    _bindColumnEvents() {
        // Remove column buttons
        this.queryAll('.remove-column-btn').forEach(btn => {
            btn.addEventListener('click', e => {
                const card = e.target.closest('.column-card');
                const index = parseInt(card.dataset.index, 10);
                this._removeColumn(index);
            });
        });

        // Column ID change - update data table headers
        this.queryAll('.column-id').forEach(input => {
            input.addEventListener('change', () => {
                this._collectColumnValues();
                this._rerenderData();
            });
        });
    }

    /**
     * Bind events for data table
     * @private
     */
    _bindDataEvents() {
        // Remove row buttons
        this.queryAll('.remove-row-btn').forEach(btn => {
            btn.addEventListener('click', e => {
                const row = e.target.closest('tr');
                const index = parseInt(row.dataset.rowIndex, 10);
                this._removeRow(index);
            });
        });

        // Data cell changes
        this.queryAll('.data-cell').forEach(input => {
            input.addEventListener('change', () => {
                this._collectDataValues();
            });
        });
    }

    /**
     * Add a new column
     * @private
     */
    _addColumn() {
        this._collectColumnValues();

        const nextIndex = this._columns.length;
        const newColumn = {
            id: `column${nextIndex + 1}`,
            label: `Column ${nextIndex + 1}`,
            type: 'text',
            sortable: true,
            filterable: true,
            width: null,
        };
        this._columns.push(newColumn);

        this._rerenderColumns();
        this._rerenderData();
    }

    /**
     * Remove a column
     * @private
     */
    _removeColumn(index) {
        this._collectColumnValues();
        const removedCol = this._columns[index];
        this._columns.splice(index, 1);

        // Remove column data from all rows
        if (removedCol) {
            this._data.forEach(row => {
                delete row[removedCol.id];
            });
        }

        this._rerenderColumns();
        this._rerenderData();
    }

    /**
     * Add a new data row
     * @private
     */
    _addRow() {
        this._collectColumnValues();
        this._collectDataValues();

        const newRow = {};
        this._columns.forEach(col => {
            newRow[col.id] = '';
        });
        this._data.push(newRow);

        this._rerenderData();
    }

    /**
     * Remove a data row
     * @private
     */
    _removeRow(index) {
        this._collectDataValues();
        this._data.splice(index, 1);
        this._rerenderData();
    }

    /**
     * Re-render columns
     * @private
     */
    _rerenderColumns() {
        const container = this.query('.columns-container');
        container.innerHTML = this._renderColumns();
        this._bindColumnEvents();
        this.initTooltips();
    }

    /**
     * Re-render data table
     * @private
     */
    _rerenderData() {
        const container = this.query('.data-container');
        container.innerHTML = this._renderDataTable();

        // Update row count badge
        const badge = this.query('.badge');
        if (badge) badge.textContent = `${this._data.length} rows`;

        // Enable/disable clear button
        const clearBtn = this.query('.config-clear-data-btn');
        if (clearBtn) clearBtn.disabled = this._data.length === 0;

        this._bindDataEvents();
    }

    /**
     * Collect current column values from DOM
     * @private
     */
    _collectColumnValues() {
        this._columns = [];
        this.queryAll('.column-card').forEach(card => {
            this._columns.push({
                id: card.querySelector('.column-id')?.value || `col${this._columns.length + 1}`,
                label: card.querySelector('.column-label')?.value || '',
                type: card.querySelector('.column-type')?.value || 'text',
                sortable: card.querySelector('.column-sortable')?.checked ?? true,
                filterable: card.querySelector('.column-filterable')?.checked ?? true,
                width: card.querySelector('.column-width')?.value || null,
            });
        });
    }

    /**
     * Collect current data values from DOM
     * @private
     */
    _collectDataValues() {
        const newData = [];
        this.queryAll('.data-edit-table tbody tr').forEach(row => {
            const rowData = {};
            row.querySelectorAll('.data-cell').forEach(cell => {
                const colId = cell.dataset.column;
                rowData[colId] = cell.value;
            });
            newData.push(rowData);
        });

        // Merge with existing data (for rows beyond display limit)
        if (newData.length > 0) {
            for (let i = 0; i < newData.length; i++) {
                this._data[i] = newData[i];
            }
        }
    }

    /**
     * Preview CSV data
     * @private
     */
    _previewCsv(csvText) {
        const previewContainer = this.query('.csv-preview-container');
        const previewTable = this.query('.csv-preview-table');

        if (!csvText.trim()) {
            previewContainer.style.display = 'none';
            return;
        }

        const delimiter = this._detectDelimiter(csvText);
        const rows = this._parseCsv(csvText, delimiter);

        if (rows.length === 0) {
            previewContainer.style.display = 'none';
            return;
        }

        const hasHeaders = document.getElementById(`${this.uid}-has-headers`)?.checked ?? true;

        // Build preview table
        let html = '<thead><tr>';
        const headers = hasHeaders ? rows[0] : rows[0].map((_, i) => `Column ${i + 1}`);
        headers.forEach(h => {
            html += `<th>${this.escapeHtml(h)}</th>`;
        });
        html += '</tr></thead><tbody>';

        const startRow = hasHeaders ? 1 : 0;
        for (let i = startRow; i < Math.min(rows.length, startRow + 5); i++) {
            html += '<tr>';
            rows[i].forEach(cell => {
                html += `<td>${this.escapeHtml(cell)}</td>`;
            });
            html += '</tr>';
        }
        if (rows.length > startRow + 5) {
            html += `<tr><td colspan="${headers.length}" class="text-muted text-center">... and ${rows.length - startRow - 5} more rows</td></tr>`;
        }
        html += '</tbody>';

        previewTable.innerHTML = html;
        previewContainer.style.display = 'block';
    }

    /**
     * Detect CSV delimiter (auto-detect comma vs tab)
     * @private
     */
    _detectDelimiter(csvText) {
        const selectedDelim = document.querySelector(`input[name="${this.uid}-delimiter"]:checked`)?.value;
        if (selectedDelim && selectedDelim !== 'auto') {
            return selectedDelim;
        }

        // Auto-detect: count commas vs tabs in first line
        const firstLine = csvText.split('\n')[0] || '';
        const commas = (firstLine.match(/,/g) || []).length;
        const tabs = (firstLine.match(/\t/g) || []).length;
        return tabs > commas ? '\t' : ',';
    }

    /**
     * Parse CSV text into rows
     * @private
     */
    _parseCsv(csvText, delimiter = ',') {
        const lines = csvText.trim().split('\n');
        return lines.map(line => line.split(delimiter).map(cell => cell.trim()));
    }

    /**
     * Apply CSV data to table config
     * @private
     */
    _applyCsv() {
        const csvText = this.query('.csv-input')?.value || '';
        const delimiter = this._detectDelimiter(csvText);
        const rows = this._parseCsv(csvText, delimiter);

        if (rows.length === 0) {
            alert('No data to import');
            return;
        }

        const hasHeaders = document.getElementById(`${this.uid}-has-headers`)?.checked ?? true;

        // Build columns from headers
        const headerRow = rows[0];
        this._columns = headerRow.map((header, i) => ({
            id: hasHeaders ? this._sanitizeId(header) : `column${i + 1}`,
            label: hasHeaders ? header : `Column ${i + 1}`,
            type: 'text', // Will try to auto-detect
            sortable: true,
            filterable: true,
            width: null,
        }));

        // Build data from remaining rows
        const startRow = hasHeaders ? 1 : 0;
        this._data = [];
        for (let i = startRow; i < rows.length; i++) {
            const rowData = {};
            rows[i].forEach((cell, j) => {
                if (j < this._columns.length) {
                    rowData[this._columns[j].id] = cell;
                }
            });
            this._data.push(rowData);
        }

        // Try to auto-detect column types
        this._autoDetectColumnTypes();

        // Re-render
        this._rerenderColumns();
        this._rerenderData();

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById(`${this.uid}-csv-modal`));
        modal?.hide();
    }

    /**
     * Sanitize string to be a valid ID
     * @private
     */
    _sanitizeId(str) {
        return str
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/^_|_$/g, '');
    }

    /**
     * Auto-detect column types from data
     * @private
     */
    _autoDetectColumnTypes() {
        this._columns.forEach(col => {
            const values = this._data.map(row => row[col.id]).filter(v => v !== '' && v !== null && v !== undefined);

            if (values.length === 0) return;

            // Check if all values are numbers
            const allNumbers = values.every(v => !isNaN(parseFloat(v)) && isFinite(v));
            if (allNumbers) {
                col.type = 'number';
                return;
            }

            // Check if all values are booleans
            const boolValues = ['true', 'false', 'yes', 'no', '1', '0'];
            const allBooleans = values.every(v => boolValues.includes(String(v).toLowerCase()));
            if (allBooleans) {
                col.type = 'boolean';
                return;
            }

            // Check if all values look like dates
            const datePattern = /^\d{4}-\d{2}-\d{2}|^\d{1,2}\/\d{1,2}\/\d{2,4}/;
            const allDates = values.every(v => datePattern.test(String(v)));
            if (allDates) {
                col.type = 'date';
                return;
            }

            // Default to text
            col.type = 'text';
        });
    }

    /**
     * Show table preview
     * @private
     */
    _showPreview() {
        this._collectColumnValues();
        this._collectDataValues();

        const config = this.getValue();
        const modal = new bootstrap.Modal(document.getElementById(`${this.uid}-preview-modal`));
        modal.show();

        // Render preview table
        const container = this.query('.table-preview-container');
        container.innerHTML = this._buildPreviewTable(config);
    }

    /**
     * Build preview table HTML
     * @private
     */
    _buildPreviewTable(config) {
        const columns = config.columns || [];
        const data = config.data || [];

        if (columns.length === 0) {
            return '<p class="text-muted">No columns defined</p>';
        }

        let html = `
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            ${columns.map(col => `<th style="${col.width ? `width:${col.width}` : ''}">${this.escapeHtml(col.label)}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
        `;

        const displayData = data.slice(0, config.page_size || 10);
        displayData.forEach(row => {
            html += '<tr>';
            columns.forEach(col => {
                let value = row[col.id] ?? '';

                // Format based on type
                if (col.type === 'number' && value !== '') {
                    value = parseFloat(value).toLocaleString();
                } else if (col.type === 'boolean') {
                    const isTrue = ['true', 'yes', '1'].includes(String(value).toLowerCase());
                    value = isTrue ? '<i class="bi bi-check-circle-fill text-success"></i>' : '<i class="bi bi-x-circle-fill text-danger"></i>';
                }

                html += `<td>${col.type === 'boolean' ? value : this.escapeHtml(value)}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table></div>';

        if (data.length > (config.page_size || 10)) {
            html += `<p class="text-muted small">Showing first ${config.page_size || 10} of ${data.length} rows</p>`;
        }

        return html;
    }

    /**
     * Get current configuration values
     * @returns {Object} Widget configuration object
     */
    getValue() {
        this._collectColumnValues();
        this._collectDataValues();

        return {
            sortable: this.getChecked('config-sortable', true),
            filterable: this.getChecked('config-filterable', true),
            paginated: this.getChecked('config-paginated', true),
            selectable: this.getChecked('config-selectable', false),
            page_size: this.getIntValue('config-page-size', 10),
            columns: this._columns.map(col => ({
                id: col.id,
                label: col.label,
                type: col.type,
                sortable: col.sortable,
                filterable: col.filterable,
                width: col.width || null,
            })),
            data: this._data,
        };
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}}
     */
    validate() {
        const errors = [];

        this._collectColumnValues();
        if (this._columns.length === 0) {
            errors.push('At least one column is required');
        }

        this._columns.forEach((col, i) => {
            if (!col.id) {
                errors.push(`Column ${i + 1}: ID is required`);
            }
            if (!col.label) {
                errors.push(`Column ${i + 1}: Label is required`);
            }
        });

        // Check for duplicate column IDs
        const ids = this._columns.map(c => c.id);
        const duplicates = ids.filter((id, i) => ids.indexOf(id) !== i);
        if (duplicates.length > 0) {
            errors.push(`Duplicate column IDs: ${duplicates.join(', ')}`);
        }

        return { valid: errors.length === 0, errors };
    }
}
