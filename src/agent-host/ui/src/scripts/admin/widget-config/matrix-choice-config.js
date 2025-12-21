/**
 * Matrix Choice Widget Configuration
 *
 * Configuration UI for the 'matrix_choice' widget type.
 *
 * Python Schema Reference (MatrixChoiceConfig):
 * - layout: MatrixLayout = "rows" ("rows" | "columns" | "likert")
 * - rows: list[MatrixChoiceRow] (required) - each has id, label
 * - columns: list[MatrixChoiceColumn] (required) - each has id, label, value?
 * - selection_mode: SelectionMode = "single" (alias: selectionMode)
 * - require_all_rows: bool | None (alias: requireAllRows)
 * - shuffle_rows: bool | None (alias: shuffleRows)
 * - shuffle_columns: bool | None (alias: shuffleColumns)
 * - show_row_numbers: bool | None (alias: showRowNumbers)
 * - sticky_header: bool | None (alias: stickyHeader)
 *
 * @module admin/widget-config/matrix-choice-config
 */

import { WidgetConfigBase } from './config-base.js';

/**
 * Layout options
 */
const LAYOUT_OPTIONS = [
    { value: 'rows', label: 'Rows (standard matrix)' },
    { value: 'columns', label: 'Columns (transposed)' },
    { value: 'likert', label: 'Likert Scale' },
];

/**
 * Selection mode options
 */
const SELECTION_MODE_OPTIONS = [
    { value: 'single', label: 'Single Selection (per row)' },
    { value: 'multiple', label: 'Multiple Selection (per row)' },
];

export class MatrixChoiceConfig extends WidgetConfigBase {
    /**
     * Render the matrix choice widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        // Convert rows to text format: id|label
        const rows = config.rows || [];
        const rowsText = rows.map(row => `${row.id}|${row.label}`).join('\n');

        // Convert columns to text format: id|label|value
        const columns = config.columns || [];
        const columnsText = columns
            .map(col => {
                let line = `${col.id}|${col.label}`;
                if (col.value !== undefined && col.value !== null) {
                    line += `|${col.value}`;
                }
                return line;
            })
            .join('\n');

        this.container.innerHTML = `
            <div class="widget-config widget-config-matrix-choice">
                <div class="row g-2">
                    <div class="col-md-6">
                        ${this.createFormGroup('Layout', this.createSelect('config-layout', LAYOUT_OPTIONS, config.layout || 'rows'), 'How the matrix is displayed.')}
                    </div>
                    <div class="col-md-6">
                        ${this.createFormGroup(
                            'Selection Mode',
                            this.createSelect('config-selection-mode', SELECTION_MODE_OPTIONS, config.selection_mode ?? config.selectionMode ?? 'single'),
                            'Allow one or multiple selections per row.'
                        )}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-6">
                        ${this.createFormGroup(
                            'Rows (Questions)',
                            this.createTextarea('config-rows', rowsText, 'row1|How satisfied are you?\nrow2|Would you recommend us?\nrow3|How easy was the process?', 5),
                            'One row per line. Format: id|label',
                            true
                        )}
                    </div>
                    <div class="col-md-6">
                        ${this.createFormGroup(
                            'Columns (Options)',
                            this.createTextarea('config-columns', columnsText, 'col1|Very Dissatisfied|1\ncol2|Dissatisfied|2\ncol3|Neutral|3\ncol4|Satisfied|4\ncol5|Very Satisfied|5', 5),
                            'One column per line. Format: id|label[|value]',
                            true
                        )}
                    </div>
                </div>

                <div class="row g-2 mt-3">
                    <div class="col-md-4">
                        ${this.createSwitch(
                            'config-require-all',
                            `${this.uid}-require-all`,
                            'Require All Rows',
                            'All rows must have a selection.',
                            config.require_all_rows ?? config.requireAllRows ?? false
                        )}
                    </div>
                    <div class="col-md-4">
                        ${this.createSwitch(
                            'config-show-row-numbers',
                            `${this.uid}-show-row-numbers`,
                            'Show Row Numbers',
                            'Display numbers before each row.',
                            config.show_row_numbers ?? config.showRowNumbers ?? false
                        )}
                    </div>
                    <div class="col-md-4">
                        ${this.createSwitch(
                            'config-sticky-header',
                            `${this.uid}-sticky-header`,
                            'Sticky Header',
                            'Keep column headers visible when scrolling.',
                            config.sticky_header ?? config.stickyHeader ?? false
                        )}
                    </div>
                </div>

                ${this.createCollapsibleSection(
                    `${this.uid}-advanced`,
                    'Advanced Options',
                    `
                    <div class="row g-2">
                        <div class="col-md-6">
                            ${this.createSwitch('config-shuffle-rows', `${this.uid}-shuffle-rows`, 'Shuffle Rows', 'Randomize the order of rows.', config.shuffle_rows ?? config.shuffleRows ?? false)}
                        </div>
                        <div class="col-md-6">
                            ${this.createSwitch(
                                'config-shuffle-columns',
                                `${this.uid}-shuffle-columns`,
                                'Shuffle Columns',
                                'Randomize the order of columns.',
                                config.shuffle_columns ?? config.shuffleColumns ?? false
                            )}
                        </div>
                    </div>
                `
                )}
            </div>
        `;

        this.initTooltips();
    }

    /**
     * Parse rows from textarea
     * @returns {Array} Parsed rows array
     */
    parseRows() {
        const text = this.getInputValue('config-rows', '');
        if (!text.trim()) return [];

        return text
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map(line => {
                const parts = line.split('|').map(p => p.trim());
                return {
                    id: parts[0],
                    label: parts[1] || parts[0],
                };
            });
    }

    /**
     * Parse columns from textarea
     * @returns {Array} Parsed columns array
     */
    parseColumns() {
        const text = this.getInputValue('config-columns', '');
        if (!text.trim()) return [];

        return text
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map(line => {
                const parts = line.split('|').map(p => p.trim());
                const column = {
                    id: parts[0],
                    label: parts[1] || parts[0],
                };
                if (parts[2]) {
                    const value = parseInt(parts[2], 10);
                    if (!isNaN(value)) column.value = value;
                }
                return column;
            });
    }

    /**
     * Get configuration values matching Python schema
     * @returns {Object} Widget configuration
     */
    getValue() {
        const config = {};

        config.layout = this.getInputValue('config-layout', 'rows');
        config.rows = this.parseRows();
        config.columns = this.parseColumns();
        config.selection_mode = this.getInputValue('config-selection-mode', 'single');

        const requireAll = this.getChecked('config-require-all');
        if (requireAll) config.require_all_rows = true;

        const showRowNumbers = this.getChecked('config-show-row-numbers');
        if (showRowNumbers) config.show_row_numbers = true;

        const stickyHeader = this.getChecked('config-sticky-header');
        if (stickyHeader) config.sticky_header = true;

        const shuffleRows = this.getChecked('config-shuffle-rows');
        if (shuffleRows) config.shuffle_rows = true;

        const shuffleColumns = this.getChecked('config-shuffle-columns');
        if (shuffleColumns) config.shuffle_columns = true;

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const rows = this.parseRows();
        if (rows.length < 1) {
            errors.push('At least 1 row is required');
        }

        const columns = this.parseColumns();
        if (columns.length < 2) {
            errors.push('At least 2 columns are required');
        }

        // Check for duplicate row IDs
        const rowIds = rows.map(r => r.id);
        const uniqueRowIds = new Set(rowIds);
        if (rowIds.length !== uniqueRowIds.size) {
            errors.push('Row IDs must be unique');
        }

        // Check for duplicate column IDs
        const colIds = columns.map(c => c.id);
        const uniqueColIds = new Set(colIds);
        if (colIds.length !== uniqueColIds.size) {
            errors.push('Column IDs must be unique');
        }

        // Validate that all rows and columns have labels
        for (const row of rows) {
            if (!row.id || !row.label) {
                errors.push('All rows must have an ID and label');
                break;
            }
        }

        for (const col of columns) {
            if (!col.id || !col.label) {
                errors.push('All columns must have an ID and label');
                break;
            }
        }

        return { valid: errors.length === 0, errors };
    }
}
