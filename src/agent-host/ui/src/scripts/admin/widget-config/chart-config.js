/**
 * Chart Widget Configuration
 *
 * Configuration UI for the 'chart' widget type.
 * Supports all Chart.js chart types including multi-axis combo charts.
 *
 * Features:
 * - Multiple chart types (bar, line, pie, doughnut, radar, polarArea, scatter, bubble)
 * - Multi-axis support (left/right Y-axes for combo charts like Volume vs Passrate)
 * - Visual dataset builder with add/remove
 * - CSV import for bulk data entry
 * - Live preview in modal
 * - Preset color palettes
 *
 * @module admin/widget-config/chart-config
 */

import { WidgetConfigBase } from './config-base.js';

// Chart.js lazy loading
let chartJsPromise = null;

/**
 * Load Chart.js dynamically
 * @returns {Promise<typeof import('chart.js').Chart>}
 */
async function loadChartJs() {
    if (chartJsPromise) return chartJsPromise;

    chartJsPromise = (async () => {
        try {
            const module = await import('chart.js/auto');
            return module.default || module.Chart || window.Chart;
        } catch (e) {
            console.warn('Failed to load Chart.js via import, trying window.Chart:', e);
            if (window.Chart) return window.Chart;
            throw new Error('Chart.js not available');
        }
    })();

    return chartJsPromise;
}

/**
 * Chart type options
 */
const CHART_TYPE_OPTIONS = [
    { value: 'bar', label: 'Bar Chart' },
    { value: 'line', label: 'Line Chart' },
    { value: 'pie', label: 'Pie Chart' },
    { value: 'doughnut', label: 'Doughnut Chart' },
    { value: 'radar', label: 'Radar Chart' },
    { value: 'polarArea', label: 'Polar Area Chart' },
    { value: 'scatter', label: 'Scatter Chart' },
    { value: 'bubble', label: 'Bubble Chart' },
];

/**
 * Dataset chart type options (for combo charts)
 */
const DATASET_TYPE_OPTIONS = [
    { value: 'bar', label: 'Bar' },
    { value: 'line', label: 'Line' },
];

/**
 * Y-axis options for multi-axis charts
 */
const Y_AXIS_OPTIONS = [
    { value: 'y', label: 'Left (Primary)' },
    { value: 'y1', label: 'Right (Secondary)' },
];

/**
 * Preset color palettes
 */
const COLOR_PRESETS = [
    { value: 'rgba(54, 162, 235, 0.6)', label: 'Blue', border: 'rgba(54, 162, 235, 1)' },
    { value: 'rgba(255, 99, 132, 0.6)', label: 'Red', border: 'rgba(255, 99, 132, 1)' },
    { value: 'rgba(75, 192, 192, 0.6)', label: 'Teal', border: 'rgba(75, 192, 192, 1)' },
    { value: 'rgba(255, 206, 86, 0.6)', label: 'Yellow', border: 'rgba(255, 206, 86, 1)' },
    { value: 'rgba(153, 102, 255, 0.6)', label: 'Purple', border: 'rgba(153, 102, 255, 1)' },
    { value: 'rgba(255, 159, 64, 0.6)', label: 'Orange', border: 'rgba(255, 159, 64, 1)' },
    { value: 'rgba(46, 204, 113, 0.6)', label: 'Green', border: 'rgba(46, 204, 113, 1)' },
    { value: 'rgba(142, 68, 173, 0.6)', label: 'Violet', border: 'rgba(142, 68, 173, 1)' },
    { value: 'rgba(52, 73, 94, 0.6)', label: 'Dark Gray', border: 'rgba(52, 73, 94, 1)' },
    { value: 'rgba(241, 196, 15, 0.6)', label: 'Gold', border: 'rgba(241, 196, 15, 1)' },
];

export class ChartConfig extends WidgetConfigBase {
    constructor(containerEl, widgetType) {
        super(containerEl, widgetType);
        this._datasets = [];
        this._labels = [];
    }

    /**
     * Render the chart widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        // Initialize datasets from config
        this._datasets = config.data?.datasets || [];
        this._labels = config.data?.labels || [];

        // If no datasets, add a default one
        if (this._datasets.length === 0) {
            this._datasets.push({
                label: 'Dataset 1',
                data: [],
                backgroundColor: COLOR_PRESETS[0].value,
                borderColor: COLOR_PRESETS[0].border,
                type: null, // Uses chart default
                yAxisID: 'y',
            });
        }

        const chartType = config.chart_type || config.chartType || 'bar';
        const isComboSupported = ['bar', 'line'].includes(chartType);

        this.container.innerHTML = `
            <div class="widget-config widget-config-chart" data-uid="${this.uid}">
                <!-- Basic Settings -->
                <div class="row g-2">
                    <div class="col-md-4">
                        ${this.createFormGroup('Chart Type', this.createSelect('config-chart-type', CHART_TYPE_OPTIONS, chartType), 'The type of chart to display.')}
                    </div>
                    <div class="col-md-5">
                        ${this.createFormGroup('Title', this.createTextInput('config-title', config.title || '', 'Chart title...'), 'Optional title displayed above the chart.')}
                    </div>
                    <div class="col-md-3">
                        ${this.createFormGroup('Height (px)', this.createNumberInput('config-height', config.height || 400, 'Height', { min: 100, max: 1000 }), 'Chart height in pixels.')}
                    </div>
                </div>

                <!-- Labels (X-Axis) -->
                <div class="row g-2 mt-2">
                    <div class="col-12">
                        ${this.createFormGroup(
                            'Labels (X-Axis)',
                            `<div class="input-group input-group-sm">
                                ${this.createTextInput('config-labels', this._labels.join(', '), 'January, February, March, April, May...')}
                                <button class="btn btn-outline-secondary config-import-labels-btn" type="button"
                                        data-bs-toggle="tooltip" title="Import from CSV">
                                    <i class="bi bi-upload"></i>
                                </button>
                            </div>`,
                            'Comma-separated labels for the X-axis.',
                            true
                        )}
                    </div>
                </div>

                <!-- Multi-Axis Toggle -->
                <div class="row g-2 mt-2 multi-axis-toggle-row" style="${isComboSupported ? '' : 'display:none'}">
                    <div class="col-12">
                        ${this.createSwitch(
                            'config-multi-axis',
                            `${this.uid}-multi-axis`,
                            'Enable Multi-Axis (Combo Chart)',
                            'Allow different chart types and Y-axes per dataset. Great for Volume vs Passrate charts!',
                            config.options?.scales?.y1 ? true : false
                        )}
                    </div>
                </div>

                <!-- Datasets Section -->
                <div class="mt-3">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <label class="form-label small mb-0 fw-bold">
                            <i class="bi bi-bar-chart me-1"></i>Datasets
                            <span class="text-danger">*</span>
                        </label>
                        <div>
                            <button class="btn btn-outline-primary btn-sm config-import-csv-btn" type="button">
                                <i class="bi bi-file-earmark-spreadsheet me-1"></i>Import CSV
                            </button>
                            <button class="btn btn-outline-success btn-sm config-add-dataset-btn ms-1" type="button">
                                <i class="bi bi-plus-lg me-1"></i>Add Dataset
                            </button>
                        </div>
                    </div>
                    <div class="datasets-container">
                        ${this._renderDatasets(isComboSupported)}
                    </div>
                </div>

                <!-- Preview Button -->
                <div class="mt-3 d-flex justify-content-end">
                    <button class="btn btn-outline-info btn-sm config-preview-btn" type="button">
                        <i class="bi bi-eye me-1"></i>Preview Chart
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
     * Render all datasets
     * @private
     */
    _renderDatasets(isComboSupported = true) {
        return this._datasets.map((ds, idx) => this._renderDatasetCard(ds, idx, isComboSupported)).join('');
    }

    /**
     * Render a single dataset card
     * @private
     */
    _renderDatasetCard(dataset, index, isComboSupported = true) {
        const colorIndex = index % COLOR_PRESETS.length;
        const bgColor = dataset.backgroundColor || COLOR_PRESETS[colorIndex].value;
        const dataStr = Array.isArray(dataset.data) ? dataset.data.join(', ') : '';

        return `
            <div class="card mb-2 dataset-card" data-index="${index}">
                <div class="card-body p-2">
                    <div class="row g-2 align-items-end">
                        <div class="col-md-3">
                            <label class="form-label small mb-0">Label</label>
                            <input type="text" class="form-control form-control-sm dataset-label"
                                   value="${this.escapeHtml(dataset.label || `Dataset ${index + 1}`)}"
                                   placeholder="Dataset name">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label small mb-0">Data Values</label>
                            <input type="text" class="form-control form-control-sm dataset-data"
                                   value="${this.escapeHtml(dataStr)}"
                                   placeholder="10, 20, 30, 40, 50...">
                        </div>
                        <div class="col-md-2 combo-options" style="${isComboSupported && this.query('.config-multi-axis')?.checked ? '' : 'display:none'}">
                            <label class="form-label small mb-0">Type</label>
                            ${this.createSelect(`dataset-type-${index}`, DATASET_TYPE_OPTIONS, dataset.type || 'bar')}
                        </div>
                        <div class="col-md-2 combo-options" style="${isComboSupported && this.query('.config-multi-axis')?.checked ? '' : 'display:none'}">
                            <label class="form-label small mb-0">Y-Axis</label>
                            ${this.createSelect(`dataset-axis-${index}`, Y_AXIS_OPTIONS, dataset.yAxisID || 'y')}
                        </div>
                        <div class="col-auto">
                            <label class="form-label small mb-0">Color</label>
                            <div class="dropdown">
                                <button class="btn btn-sm btn-outline-secondary dropdown-toggle dataset-color-btn"
                                        type="button" data-bs-toggle="dropdown" aria-expanded="false"
                                        style="background-color: ${bgColor}; min-width: 60px;">
                                    &nbsp;
                                </button>
                                <ul class="dropdown-menu color-palette-menu">
                                    ${COLOR_PRESETS.map(
                                        c => `
                                        <li>
                                            <a class="dropdown-item color-option d-flex align-items-center"
                                               href="#" data-color="${c.value}" data-border="${c.border}">
                                                <span class="color-swatch me-2" style="background-color: ${c.value}; width: 20px; height: 20px; border-radius: 3px; display: inline-block;"></span>
                                                ${c.label}
                                            </a>
                                        </li>
                                    `
                                    ).join('')}
                                </ul>
                            </div>
                            <input type="hidden" class="dataset-bg-color" value="${bgColor}">
                            <input type="hidden" class="dataset-border-color" value="${dataset.borderColor || COLOR_PRESETS[colorIndex].border}">
                        </div>
                        <div class="col-auto">
                            <button class="btn btn-sm btn-outline-danger remove-dataset-btn" type="button"
                                    ${this._datasets.length <= 1 ? 'disabled' : ''}>
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
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
                            <div class="mb-3">
                                <label class="form-label">
                                    Paste CSV Data
                                    <small class="text-muted">(First row = labels, subsequent rows = dataset values)</small>
                                </label>
                                <textarea class="form-control csv-input" rows="10"
                                          placeholder="Label,Jan,Feb,Mar,Apr,May&#10;Sales 2024,65,59,80,81,56&#10;Sales 2023,45,48,62,70,52"></textarea>
                            </div>
                            <div class="csv-preview-container" style="display:none">
                                <label class="form-label">Preview</label>
                                <div class="table-responsive">
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
                                <i class="bi bi-bar-chart me-2"></i>Chart Preview
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="chart-preview-container" style="position: relative; height: 400px;">
                                <canvas id="${this.uid}-preview-canvas"></canvas>
                            </div>
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
        // Chart type change - show/hide multi-axis toggle
        this.query('.config-chart-type')?.addEventListener('change', e => {
            const isCombo = ['bar', 'line'].includes(e.target.value);
            const toggleRow = this.query('.multi-axis-toggle-row');
            if (toggleRow) {
                toggleRow.style.display = isCombo ? '' : 'none';
            }
            if (!isCombo) {
                // Disable multi-axis if not supported
                const multiAxisCheck = this.query('.config-multi-axis');
                if (multiAxisCheck) multiAxisCheck.checked = false;
                this._toggleComboOptions(false);
            }
        });

        // Multi-axis toggle
        this.query('.config-multi-axis')?.addEventListener('change', e => {
            this._toggleComboOptions(e.target.checked);
        });

        // Add dataset
        this.query('.config-add-dataset-btn')?.addEventListener('click', () => {
            this._addDataset();
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

        // Bind dataset events
        this._bindDatasetEvents();
    }

    /**
     * Toggle combo chart options visibility
     * @private
     */
    _toggleComboOptions(show) {
        this.queryAll('.combo-options').forEach(el => {
            el.style.display = show ? '' : 'none';
        });
    }

    /**
     * Bind events for dataset cards
     * @private
     */
    _bindDatasetEvents() {
        // Remove dataset buttons
        this.queryAll('.remove-dataset-btn').forEach(btn => {
            btn.addEventListener('click', e => {
                const card = e.target.closest('.dataset-card');
                const index = parseInt(card.dataset.index, 10);
                this._removeDataset(index);
            });
        });

        // Color selection
        this.queryAll('.color-option').forEach(option => {
            option.addEventListener('click', e => {
                e.preventDefault();
                const card = e.target.closest('.dataset-card');
                const color = e.target.closest('.color-option').dataset.color;
                const border = e.target.closest('.color-option').dataset.border;
                card.querySelector('.dataset-bg-color').value = color;
                card.querySelector('.dataset-border-color').value = border;
                card.querySelector('.dataset-color-btn').style.backgroundColor = color;
            });
        });
    }

    /**
     * Add a new dataset
     * @private
     */
    _addDataset() {
        const nextIndex = this._datasets.length;
        const colorIndex = nextIndex % COLOR_PRESETS.length;
        const newDataset = {
            label: `Dataset ${nextIndex + 1}`,
            data: [],
            backgroundColor: COLOR_PRESETS[colorIndex].value,
            borderColor: COLOR_PRESETS[colorIndex].border,
            type: null,
            yAxisID: 'y',
        };
        this._datasets.push(newDataset);

        const container = this.query('.datasets-container');
        const isCombo = this.query('.config-multi-axis')?.checked;
        container.insertAdjacentHTML('beforeend', this._renderDatasetCard(newDataset, nextIndex, isCombo));

        // Enable all remove buttons if we have more than 1 dataset
        if (this._datasets.length > 1) {
            this.queryAll('.remove-dataset-btn').forEach(btn => (btn.disabled = false));
        }

        this._bindDatasetEvents();
        this.initTooltips();
    }

    /**
     * Remove a dataset
     * @private
     */
    _removeDataset(index) {
        this._collectDatasetValues(); // Save current values before removal
        this._datasets.splice(index, 1);
        this._rerenderDatasets();
    }

    /**
     * Re-render all datasets
     * @private
     */
    _rerenderDatasets() {
        const container = this.query('.datasets-container');
        const isCombo = this.query('.config-multi-axis')?.checked;
        container.innerHTML = this._renderDatasets(isCombo);
        this._bindDatasetEvents();
        this.initTooltips();
    }

    /**
     * Collect current dataset values from DOM
     * @private
     */
    _collectDatasetValues() {
        this._datasets = [];
        this.queryAll('.dataset-card').forEach(card => {
            const label = card.querySelector('.dataset-label')?.value || 'Dataset';
            const dataStr = card.querySelector('.dataset-data')?.value || '';
            const data = dataStr
                .split(',')
                .map(s => parseFloat(s.trim()))
                .filter(n => !isNaN(n));

            const index = parseInt(card.dataset.index, 10);
            const typeSelect = card.querySelector(`[class*="dataset-type-${index}"]`);
            const axisSelect = card.querySelector(`[class*="dataset-axis-${index}"]`);

            this._datasets.push({
                label,
                data,
                backgroundColor: card.querySelector('.dataset-bg-color')?.value || COLOR_PRESETS[0].value,
                borderColor: card.querySelector('.dataset-border-color')?.value || COLOR_PRESETS[0].border,
                type: typeSelect?.value || null,
                yAxisID: axisSelect?.value || 'y',
            });
        });
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

        // Build preview table
        let html = '<thead><tr>';
        const headers = rows[0];
        headers.forEach((h, i) => {
            html += `<th class="${i === 0 ? 'text-muted' : ''}">${this.escapeHtml(h)}</th>`;
        });
        html += '</tr></thead><tbody>';

        for (let i = 1; i < Math.min(rows.length, 6); i++) {
            html += '<tr>';
            rows[i].forEach((cell, j) => {
                html += `<td class="${j === 0 ? 'fw-bold' : ''}">${this.escapeHtml(cell)}</td>`;
            });
            html += '</tr>';
        }
        if (rows.length > 6) {
            html += `<tr><td colspan="${headers.length}" class="text-muted text-center">... and ${rows.length - 6} more rows</td></tr>`;
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
     * Apply CSV data to chart config
     * @private
     */
    _applyCsv() {
        const csvText = this.query('.csv-input')?.value || '';
        const delimiter = this._detectDelimiter(csvText);
        const rows = this._parseCsv(csvText, delimiter);

        if (rows.length < 2) {
            alert('CSV must have at least 2 rows (headers + 1 data row)');
            return;
        }

        // First row (after first cell) = labels
        const labels = rows[0].slice(1);
        this.query('.config-labels').value = labels.join(', ');
        this._labels = labels;

        // Subsequent rows = datasets
        this._datasets = [];
        for (let i = 1; i < rows.length; i++) {
            const row = rows[i];
            const label = row[0] || `Dataset ${i}`;
            const data = row.slice(1).map(v => parseFloat(v) || 0);
            const colorIndex = (i - 1) % COLOR_PRESETS.length;

            this._datasets.push({
                label,
                data,
                backgroundColor: COLOR_PRESETS[colorIndex].value,
                borderColor: COLOR_PRESETS[colorIndex].border,
                type: null,
                yAxisID: 'y',
            });
        }

        // Re-render datasets
        this._rerenderDatasets();

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById(`${this.uid}-csv-modal`));
        modal?.hide();
    }

    /**
     * Show chart preview
     * @private
     */
    async _showPreview() {
        const config = this.getValue();
        const modal = new bootstrap.Modal(document.getElementById(`${this.uid}-preview-modal`));
        modal.show();

        // Wait for modal to open, then render chart
        setTimeout(async () => {
            const canvas = document.getElementById(`${this.uid}-preview-canvas`);
            if (!canvas) return;

            try {
                const Chart = await loadChartJs();

                // Destroy existing chart if any
                const existingChart = Chart.getChart(canvas);
                if (existingChart) existingChart.destroy();

                // Build Chart.js config
                const chartConfig = this._buildChartJsConfig(config);
                new Chart(canvas, chartConfig);
            } catch (e) {
                console.error('Failed to load Chart.js for preview:', e);
                canvas.parentElement.innerHTML = '<p class="text-danger">Failed to load Chart.js</p>';
            }
        }, 300);
    }

    /**
     * Build Chart.js configuration from our config
     * @private
     */
    _buildChartJsConfig(config) {
        const chartType = config.chart_type || 'bar';
        const isMultiAxis = config.options?.scales?.y1 !== undefined;

        const datasets = config.data.datasets.map(ds => {
            const dataset = {
                label: ds.label,
                data: ds.data,
                backgroundColor: ds.backgroundColor,
                borderColor: ds.borderColor,
                borderWidth: 1,
            };

            // For combo charts, set type and yAxisID
            if (isMultiAxis && ds.type) {
                dataset.type = ds.type;
                dataset.yAxisID = ds.yAxisID || 'y';

                // Line charts need special styling
                if (ds.type === 'line') {
                    dataset.fill = false;
                    dataset.tension = 0.1;
                    dataset.borderWidth = 2;
                }
            }

            return dataset;
        });

        const chartJsConfig = {
            type: chartType,
            data: {
                labels: config.data.labels,
                datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: !!config.title,
                        text: config.title || '',
                    },
                },
            },
        };

        // Add multi-axis scales if needed
        if (isMultiAxis) {
            chartJsConfig.options.scales = {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false,
                    },
                },
            };
        }

        return chartJsConfig;
    }

    /**
     * Get current configuration values
     * @returns {Object} Widget configuration object
     */
    getValue() {
        this._collectDatasetValues();

        const chartType = this.getInputValue('config-chart-type', 'bar');
        const title = this.getInputValue('config-title', '');
        const height = this.getIntValue('config-height', 400);
        const labelsStr = this.getInputValue('config-labels', '');
        const labels = labelsStr
            .split(',')
            .map(s => s.trim())
            .filter(s => s);

        const isMultiAxis = this.query('.config-multi-axis')?.checked || false;

        const config = {
            chart_type: chartType,
            title: title || null,
            height,
            data: {
                labels,
                datasets: this._datasets.map(ds => {
                    const dataset = {
                        label: ds.label,
                        data: ds.data,
                        backgroundColor: ds.backgroundColor,
                        borderColor: ds.borderColor,
                    };

                    // Only include combo options if multi-axis is enabled
                    if (isMultiAxis && ['bar', 'line'].includes(chartType)) {
                        if (ds.type) dataset.type = ds.type;
                        dataset.yAxisID = ds.yAxisID || 'y';
                    }

                    return dataset;
                }),
            },
        };

        // Add multi-axis options if enabled
        if (isMultiAxis && ['bar', 'line'].includes(chartType)) {
            config.options = {
                scales: {
                    y: { type: 'linear', display: true, position: 'left' },
                    y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false } },
                },
            };
        }

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}}
     */
    validate() {
        const errors = [];
        const labelsStr = this.getInputValue('config-labels', '');
        if (!labelsStr.trim()) {
            errors.push('Labels are required');
        }

        this._collectDatasetValues();
        if (this._datasets.length === 0) {
            errors.push('At least one dataset is required');
        }

        this._datasets.forEach((ds, i) => {
            if (!ds.label) {
                errors.push(`Dataset ${i + 1}: Label is required`);
            }
            if (ds.data.length === 0) {
                errors.push(`Dataset ${i + 1}: Data values are required`);
            }
        });

        return { valid: errors.length === 0, errors };
    }
}
