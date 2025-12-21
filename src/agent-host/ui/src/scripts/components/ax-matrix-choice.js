/**
 * Matrix Choice Widget Component
 * Renders Likert scales, rating grids, and matrix-style selection interfaces.
 *
 * Attributes:
 * - layout: "rows" (default) or "columns"
 * - rows: JSON array of row definitions [{ id, label }]
 * - columns: JSON array of column definitions [{ id, label, value? }]
 * - selection-mode: "single" (one per row) or "multiple" (multiple per row)
 * - require-all-rows: Require selection in every row
 * - shuffle-rows: Randomize row order
 * - shuffle-columns: Randomize column order
 * - show-row-numbers: Display row numbers
 * - sticky-header: Keep header visible when scrolling
 * - prompt: Question/instruction text
 *
 * Events:
 * - ax-cell-click: Fired when a cell is clicked
 * - ax-response: Fired with selection data
 *
 * @example
 * <ax-matrix-choice
 *   rows='[{"id":"q1","label":"Item 1"},{"id":"q2","label":"Item 2"}]'
 *   columns='[{"id":"sd","label":"Strongly Disagree"},{"id":"d","label":"Disagree"},{"id":"n","label":"Neutral"},{"id":"a","label":"Agree"},{"id":"sa","label":"Strongly Agree"}]'
 *   selection-mode="single"
 *   require-all-rows
 * ></ax-matrix-choice>
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

class AxMatrixChoice extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'layout', 'rows', 'columns', 'selection-mode', 'require-all-rows', 'shuffle-rows', 'shuffle-columns', 'show-row-numbers', 'sticky-header', 'prompt'];
    }

    constructor() {
        super();
        // Map: rowId -> Set of columnIds
        this._selections = new Map();
        this._displayRows = [];
        this._displayColumns = [];
    }

    // =========================================================================
    // Attribute Getters
    // =========================================================================

    get layout() {
        const l = this.getAttribute('layout') || 'rows';
        return ['rows', 'columns'].includes(l) ? l : 'rows';
    }

    get rows() {
        return this.parseJsonAttribute('rows', []);
    }

    get columns() {
        return this.parseJsonAttribute('columns', []);
    }

    get selectionMode() {
        // Support both selection-mode attribute and allow-multiple shorthand
        if (this.hasAttribute('allow-multiple')) {
            return 'multiple';
        }
        return this.getAttribute('selection-mode') || 'single';
    }

    get requireAllRows() {
        return this.hasAttribute('require-all-rows');
    }

    get shuffleRows() {
        return this.hasAttribute('shuffle-rows');
    }

    get shuffleColumns() {
        return this.hasAttribute('shuffle-columns');
    }

    get showRowNumbers() {
        return this.hasAttribute('show-row-numbers');
    }

    get stickyHeader() {
        return this.hasAttribute('sticky-header');
    }

    get showProgress() {
        return this.hasAttribute('show-progress');
    }

    get prompt() {
        return this.getAttribute('prompt') || '';
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    async connectedCallback() {
        // Initialize display order
        this._displayRows = this.shuffleRows ? this._shuffle([...this.rows]) : [...this.rows];
        this._displayColumns = this.shuffleColumns ? this._shuffle([...this.columns]) : [...this.columns];

        // Initialize selections map
        this.rows.forEach(row => {
            if (!this._selections.has(row.id)) {
                this._selections.set(row.id, new Set());
            }
        });

        await super.connectedCallback();
    }

    // =========================================================================
    // Value Interface
    // =========================================================================

    getValue() {
        const selections = {};

        this._selections.forEach((columnIds, rowId) => {
            const values = Array.from(columnIds);
            // Always return array format for consistency
            selections[rowId] = values;
        });

        return { selections };
    }

    setValue(value) {
        // Support both { selections: {...} } and direct object format
        const selectionsObj = value?.selections || value;
        if (typeof selectionsObj !== 'object' || selectionsObj === null) return;

        this._selections.clear();

        // Initialize all rows with empty sets
        this.rows.forEach(row => {
            this._selections.set(row.id, new Set());
        });

        Object.entries(selectionsObj).forEach(([rowId, selection]) => {
            const columnIds = new Set();
            if (Array.isArray(selection)) {
                selection.forEach(id => columnIds.add(id));
            } else if (selection) {
                columnIds.add(selection);
            }
            this._selections.set(rowId, columnIds);
        });

        this.render();
        this.bindEvents();
    }

    validate() {
        const errors = [];
        const warnings = [];

        if (this.requireAllRows) {
            const incompleteRows = this.rows.filter(row => {
                const selection = this._selections.get(row.id);
                return !selection || selection.size === 0;
            });

            if (incompleteRows.length > 0) {
                errors.push(`Please complete all rows (${incompleteRows.length} remaining)`);
            }
        }

        if (this.required && this._getTotalSelections() === 0) {
            errors.push('Please make at least one selection');
        }

        return { valid: errors.length === 0, errors, warnings };
    }

    // =========================================================================
    // Styles
    // =========================================================================

    async getStyles() {
        return `
            ${await this.getBaseStyles()}

            :host {
                display: block;
                font-family: var(--ax-font-family, system-ui, -apple-system, sans-serif);
            }

            .widget-container {
                background: var(--ax-widget-bg, #f8f9fa);
                border: 1px solid var(--ax-border-color, #dee2e6);
                border-radius: var(--ax-border-radius, 12px);
                padding: var(--ax-padding, 1.25rem);
                margin: var(--ax-margin, 0.5rem 0);
            }

            .prompt {
                font-size: 1rem;
                font-weight: 500;
                color: var(--ax-text-color, #212529);
                margin-bottom: 1rem;
                line-height: 1.5;
            }

            .matrix-wrapper {
                overflow-x: auto;
                margin: 0 -0.5rem;
                padding: 0 0.5rem;
            }

            .matrix-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.9rem;
            }

            .matrix-table th,
            .matrix-table td {
                padding: 0.75rem;
                text-align: center;
                border: 1px solid var(--ax-border-light, #e9ecef);
            }

            .matrix-table thead th {
                background: var(--ax-header-bg, #e9ecef);
                font-weight: 600;
                color: var(--ax-text-color, #212529);
                white-space: nowrap;
            }

            .matrix-table thead th.sticky {
                position: sticky;
                top: 0;
                z-index: 10;
            }

            .row-label-cell {
                text-align: left !important;
                font-weight: 500;
                background: var(--ax-row-label-bg, #fafafa);
                min-width: 200px;
            }

            .row-label {
                display: block;
                font-weight: 500;
            }

            .row-description {
                display: block;
                font-size: 0.85rem;
                color: var(--ax-text-muted, #6c757d);
                font-weight: normal;
                margin-top: 0.25rem;
            }

            .row-number {
                color: var(--ax-text-muted, #6c757d);
                margin-right: 0.5rem;
            }

            .selection-cell {
                cursor: pointer;
                transition: background 0.15s;
                position: relative;
            }

            .selection-cell:hover {
                background: var(--ax-cell-hover, #f0f0f0);
            }

            .selection-cell.selected {
                background: var(--ax-primary-light, #e7f1ff);
            }

            .selection-cell:focus-within {
                outline: 2px solid var(--ax-primary-color, #0d6efd);
                outline-offset: -2px;
            }

            /* Radio/Checkbox indicators */
            .indicator {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 24px;
                height: 24px;
                border: 2px solid var(--ax-border-color, #dee2e6);
                border-radius: ${this.selectionMode === 'single' ? '50%' : '4px'};
                transition: all 0.15s;
                background: white;
            }

            .selection-cell.selected .indicator {
                background: var(--ax-primary-color, #0d6efd);
                border-color: var(--ax-primary-color, #0d6efd);
            }

            .indicator svg {
                width: 14px;
                height: 14px;
                fill: white;
                opacity: 0;
                transition: opacity 0.15s;
            }

            .selection-cell.selected .indicator svg {
                opacity: 1;
            }

            /* Highlight incomplete rows */
            .row-incomplete .row-label-cell {
                border-left: 3px solid var(--ax-warning-color, #ffc107);
            }

            /* Progress indicator */
            .progress-indicator {
                margin-top: 1rem;
                font-size: 0.85rem;
                color: var(--ax-text-muted, #6c757d);
            }

            .progress-bar {
                height: 6px;
                background: var(--ax-border-color, #dee2e6);
                border-radius: 3px;
                margin-top: 0.5rem;
                overflow: hidden;
            }

            .progress-fill {
                height: 100%;
                background: var(--ax-primary-color, #0d6efd);
                border-radius: 3px;
                transition: width 0.3s ease;
            }

            .progress-complete .progress-fill {
                background: var(--ax-success-color, #198754);
            }

            /* Column layout variant */
            :host([layout="columns"]) .matrix-table {
                writing-mode: vertical-lr;
            }

            /* Dark mode */
            @media (prefers-color-scheme: dark) {
                .widget-container {
                    --ax-widget-bg: #2d3748;
                    --ax-border-color: #4a5568;
                    --ax-text-color: #e2e8f0;
                    --ax-header-bg: #1a202c;
                    --ax-row-label-bg: #374151;
                    --ax-border-light: #4a5568;
                    --ax-cell-hover: #374151;
                    --ax-primary-light: #1e3a5f;
                }

                .indicator {
                    background: #2d3748;
                }
            }

            /* Responsive */
            @media (max-width: 768px) {
                .matrix-table th,
                .matrix-table td {
                    padding: 0.5rem;
                    font-size: 0.85rem;
                }

                .row-label-cell {
                    min-width: 120px;
                }

                .indicator {
                    width: 20px;
                    height: 20px;
                }
            }
        `;
    }

    // =========================================================================
    // Rendering
    // =========================================================================

    render() {
        const rows = this._displayRows;
        const columns = this._displayColumns;
        const completedRows = this._getCompletedRowCount();
        const totalRows = rows.length;
        const isComplete = completedRows === totalRows;

        this.shadowRoot.innerHTML = `
            <style>${this._styles || ''}</style>
            <div class="widget-container">
                ${this.prompt ? `<div class="prompt">${this.renderMarkdown(this.prompt)}</div>` : ''}

                <div class="matrix-wrapper">
                    <table class="matrix-table" role="grid" aria-label="${this.prompt || 'Matrix selection'}">
                        <thead>
                            <tr>
                                <th class="${this.stickyHeader ? 'sticky' : ''}">&nbsp;</th>
                                ${columns
                                    .map(
                                        col => `
                                    <th class="${this.stickyHeader ? 'sticky' : ''}"
                                        scope="col"
                                        id="col-${col.id}">
                                        ${this.escapeHtml(col.label)}
                                    </th>
                                `
                                    )
                                    .join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${rows.map((row, rowIndex) => this._renderRow(row, columns, rowIndex)).join('')}
                        </tbody>
                    </table>
                </div>

                ${
                    this.requireAllRows || this.showProgress
                        ? `
                    <div class="progress-indicator matrix-progress ${isComplete ? 'progress-complete' : ''}" role="status" aria-live="polite">
                        <span class="progress-text">${completedRows} of ${totalRows} rows completed</span>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${(completedRows / totalRows) * 100}%"></div>
                        </div>
                    </div>
                `
                        : ''
                }
            </div>
        `;
    }

    _renderRow(row, columns, rowIndex) {
        const selection = this._selections.get(row.id) || new Set();
        const isComplete = selection.size > 0;

        return `
            <tr class="${!isComplete && this.requireAllRows ? 'row-incomplete' : ''}" data-row-id="${row.id}">
                <td class="row-label-cell" id="row-${row.id}">
                    ${this.showRowNumbers ? `<span class="row-number">${rowIndex + 1}.</span>` : ''}
                    <span class="row-label">${this.escapeHtml(row.label)}</span>
                    ${row.description ? `<span class="row-description">${this.escapeHtml(row.description)}</span>` : ''}
                </td>
                ${columns.map(col => this._renderCell(row, col, selection.has(col.id))).join('')}
            </tr>
        `;
    }

    _renderCell(row, column, isSelected) {
        const inputType = this.selectionMode === 'single' ? 'radio' : 'checkbox';
        const inputName = this.selectionMode === 'single' ? `matrix-${row.id}` : `matrix-${row.id}-${column.id}`;

        return `
            <td class="selection-cell matrix-cell ${isSelected ? 'selected' : ''}"
                data-row-id="${row.id}"
                data-column-id="${column.id}"
                role="gridcell"
                aria-labelledby="row-${row.id} col-${column.id}">
                <label class="indicator" tabindex="0">
                    <input type="${inputType}"
                           name="${inputName}"
                           value="${column.id}"
                           ${isSelected ? 'checked' : ''}
                           class="sr-only"
                           aria-label="${row.label}: ${column.label}" />
                    <svg viewBox="0 0 16 16" aria-hidden="true">
                        <path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/>
                    </svg>
                </label>
            </td>
        `;
    }

    // =========================================================================
    // Events
    // =========================================================================

    bindEvents() {
        // Cell clicks
        this.shadowRoot.querySelectorAll('.selection-cell').forEach(cell => {
            cell.addEventListener('click', e => {
                if (e.target.tagName === 'INPUT') return; // Let native handler work
                this._handleCellClick(cell.dataset.rowId, cell.dataset.columnId);
            });
        });

        // Keyboard navigation
        this.shadowRoot.querySelectorAll('.indicator').forEach(indicator => {
            indicator.addEventListener('keydown', e => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    const cell = indicator.closest('.selection-cell');
                    this._handleCellClick(cell.dataset.rowId, cell.dataset.columnId);
                }

                // Arrow key navigation
                if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
                    e.preventDefault();
                    this._handleArrowNavigation(e.key, indicator);
                }
            });
        });

        // Input change (for accessibility)
        this.shadowRoot.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(input => {
            input.addEventListener('change', () => {
                const cell = input.closest('.selection-cell');
                this._handleCellClick(cell.dataset.rowId, cell.dataset.columnId, input.checked);
            });
        });
    }

    _handleCellClick(rowId, columnId, forceValue = null) {
        if (this.disabled || this.readonly) return;

        const selection = this._selections.get(rowId) || new Set();
        const wasSelected = selection.has(columnId);

        if (this.selectionMode === 'single') {
            selection.clear();
            if (!wasSelected) {
                selection.add(columnId);
            }
        } else {
            if (forceValue !== null) {
                if (forceValue) {
                    selection.add(columnId);
                } else {
                    selection.delete(columnId);
                }
            } else {
                if (wasSelected) {
                    selection.delete(columnId);
                } else {
                    selection.add(columnId);
                }
            }
        }

        this._selections.set(rowId, selection);

        // Dispatch cell click event
        this.dispatchEvent(
            new CustomEvent('ax-cell-click', {
                bubbles: true,
                composed: true,
                detail: {
                    widgetId: this.widgetId,
                    rowId,
                    columnId,
                    isSelected: selection.has(columnId),
                },
            })
        );

        this._updateCellStyles(rowId);
        this._updateProgress();
        this._dispatchResponse();
    }

    _handleArrowNavigation(key, currentIndicator) {
        const cell = currentIndicator.closest('.selection-cell');
        const currentRow = cell.closest('tr');
        const cells = Array.from(currentRow.querySelectorAll('.selection-cell'));
        const currentIndex = cells.indexOf(cell);
        const rows = Array.from(this.shadowRoot.querySelectorAll('tbody tr'));
        const rowIndex = rows.indexOf(currentRow);

        let targetCell = null;

        switch (key) {
            case 'ArrowLeft':
                if (currentIndex > 0) {
                    targetCell = cells[currentIndex - 1];
                }
                break;
            case 'ArrowRight':
                if (currentIndex < cells.length - 1) {
                    targetCell = cells[currentIndex + 1];
                }
                break;
            case 'ArrowUp':
                if (rowIndex > 0) {
                    const prevRow = rows[rowIndex - 1];
                    const prevCells = prevRow.querySelectorAll('.selection-cell');
                    targetCell = prevCells[currentIndex];
                }
                break;
            case 'ArrowDown':
                if (rowIndex < rows.length - 1) {
                    const nextRow = rows[rowIndex + 1];
                    const nextCells = nextRow.querySelectorAll('.selection-cell');
                    targetCell = nextCells[currentIndex];
                }
                break;
        }

        if (targetCell) {
            const targetIndicator = targetCell.querySelector('.indicator');
            if (targetIndicator) {
                targetIndicator.focus();
            }
        }
    }

    _updateCellStyles(rowId) {
        const selection = this._selections.get(rowId) || new Set();
        const row = this.shadowRoot.querySelector(`tr[data-row-id="${rowId}"]`);
        if (!row) return;

        // Update cells
        row.querySelectorAll('.selection-cell').forEach(cell => {
            const colId = cell.dataset.columnId;
            const isSelected = selection.has(colId);
            cell.classList.toggle('selected', isSelected);

            const input = cell.querySelector('input');
            if (input) input.checked = isSelected;
        });

        // Update row incomplete state
        if (this.requireAllRows) {
            row.classList.toggle('row-incomplete', selection.size === 0);
        }
    }

    _updateProgress() {
        const progressIndicator = this.shadowRoot.querySelector('.progress-indicator');
        if (!progressIndicator) return;

        const completedRows = this._getCompletedRowCount();
        const totalRows = this._displayRows.length;
        const isComplete = completedRows === totalRows;

        // Update or create progress text
        let progressText = progressIndicator.querySelector('.progress-text');
        if (!progressText) {
            progressText = document.createElement('span');
            progressText.className = 'progress-text';
            progressIndicator.prepend(progressText);
        }
        progressText.textContent = `${completedRows} of ${totalRows} rows completed`;
        progressIndicator.classList.toggle('progress-complete', isComplete);

        const progressBar = progressIndicator.querySelector('.progress-bar');
        if (!progressBar) {
            progressIndicator.insertAdjacentHTML(
                'beforeend',
                `
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${(completedRows / totalRows) * 100}%"></div>
                </div>
            `
            );
        } else {
            const fill = progressBar.querySelector('.progress-fill');
            if (fill) {
                fill.style.width = `${(completedRows / totalRows) * 100}%`;
            }
        }
    }

    _dispatchResponse() {
        const value = this.getValue();
        this.dispatchEvent(
            new CustomEvent('ax-change', {
                bubbles: true,
                composed: true,
                detail: {
                    widgetId: this.widgetId,
                    selections: value.selections,
                },
            })
        );
        this.dispatchEvent(
            new CustomEvent('ax-response', {
                bubbles: true,
                composed: true,
                detail: {
                    widgetId: this.widgetId,
                    itemId: this.itemId,
                    value: value,
                    selections: value.selections,
                    timestamp: new Date().toISOString(),
                },
            })
        );
    }

    // =========================================================================
    // Utilities
    // =========================================================================

    _getCompletedRowCount() {
        return Array.from(this._selections.values()).filter(set => set.size > 0).length;
    }

    _getTotalSelections() {
        let total = 0;
        this._selections.forEach(set => (total += set.size));
        return total;
    }

    _shuffle(array) {
        const shuffled = [...array];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
    }

    async loadStyles() {
        this._styles = await this.getStyles();
    }

    onAttributeChange(name, oldValue, newValue) {
        if (!this._initialized) return;

        if (name === 'rows' || name === 'columns') {
            this._displayRows = this.shuffleRows ? this._shuffle([...this.rows]) : [...this.rows];
            this._displayColumns = this.shuffleColumns ? this._shuffle([...this.columns]) : [...this.columns];
        }

        this.render();
        this.bindEvents();
    }
}

// Register custom element
if (!customElements.get('ax-matrix-choice')) {
    customElements.define('ax-matrix-choice', AxMatrixChoice);
}

export default AxMatrixChoice;
