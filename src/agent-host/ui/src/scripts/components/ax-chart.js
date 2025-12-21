/**
 * Chart Widget Component
 * Renders interactive charts using Chart.js with lazy loading.
 *
 * Attributes:
 * - chart-type: Type of chart ("bar" | "line" | "pie" | "doughnut")
 * - data: JSON chart data { labels: [], datasets: [] }
 * - options: JSON Chart.js options
 * - responsive: Whether chart should resize (default: true)
 * - prompt: Optional label/title for the chart
 *
 * Events:
 * - ax-chart-click: Fired when user clicks on chart element
 *   Detail: { datasetIndex, index, value, label }
 *
 * @example
 * <ax-chart
 *   chart-type="bar"
 *   data='{"labels":["A","B","C"],"datasets":[{"label":"Values","data":[10,20,30]}]}'
 *   responsive
 * ></ax-chart>
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

// Chart.js loading state
let chartJsPromise = null;
let chartJsLoaded = false;

/**
 * Lazy load Chart.js
 * @returns {Promise<typeof Chart>}
 */
async function loadChartJs() {
    if (chartJsLoaded && window.Chart) {
        return window.Chart;
    }

    if (chartJsPromise) {
        return chartJsPromise;
    }

    chartJsPromise = (async () => {
        try {
            // Dynamically import Chart.js
            const module = await import('chart.js/auto');
            chartJsLoaded = true;
            return module.default || module.Chart || window.Chart;
        } catch (e) {
            console.warn('Failed to load Chart.js via import, trying CDN fallback:', e);

            // CDN fallback
            return new Promise((resolve, reject) => {
                if (window.Chart) {
                    chartJsLoaded = true;
                    resolve(window.Chart);
                    return;
                }

                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
                script.onload = () => {
                    chartJsLoaded = true;
                    resolve(window.Chart);
                };
                script.onerror = () => reject(new Error('Failed to load Chart.js'));
                document.head.appendChild(script);
            });
        }
    })();

    return chartJsPromise;
}

class AxChart extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'chart-type', 'data', 'labels', 'datasets', 'options', 'responsive', 'prompt', 'title', 'height', 'width'];
    }

    constructor() {
        super();
        this._chart = null;
        this._chartData = null;
        this._chartOptions = null;
    }

    // =========================================================================
    // Attribute Getters
    // =========================================================================

    get chartType() {
        const type = this.getAttribute('chart-type') || 'bar';
        const validTypes = ['bar', 'line', 'pie', 'doughnut', 'radar', 'polarArea', 'bubble', 'scatter'];
        return validTypes.includes(type) ? type : 'bar';
    }

    get data() {
        // Support both combined "data" attribute and separate "labels"/"datasets" attributes
        const dataAttr = this.getAttribute('data');
        if (dataAttr) {
            return this.parseJsonAttribute('data', { labels: [], datasets: [] });
        }
        // Fallback to separate attributes
        const labels = this.parseJsonAttribute('labels', []);
        const datasets = this.parseJsonAttribute('datasets', []);
        return { labels, datasets };
    }

    get options() {
        return this.parseJsonAttribute('options', {});
    }

    get responsive() {
        return this.hasAttribute('responsive') || !this.hasAttribute('responsive'); // default true
    }

    get prompt() {
        return this.getAttribute('prompt') || '';
    }

    get title() {
        return this.getAttribute('title') || this.prompt || '';
    }

    get height() {
        return this.getAttribute('height') || '300px';
    }

    get width() {
        return this.getAttribute('width') || 'auto';
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    async connectedCallback() {
        this.state = WidgetState.LOADING;
        await this.loadStyles();
        this.render();
        await this._initChart();
        this.bindEvents();
        this.announceAccessibility();
        this._initialized = true;
        this.state = WidgetState.IDLE;
    }

    disconnectedCallback() {
        this._destroyChart();
        this.cleanup();
    }

    // =========================================================================
    // Value Interface
    // =========================================================================

    getValue() {
        // Return internal data or fall back to attribute data
        return this._chartData || this.data;
    }

    setValue(data) {
        this._chartData = data;
        if (this._chart) {
            this._chart.data = data;
            this._chart.update();
        }
    }

    validate() {
        const data = this.getValue();
        const errors = [];

        if (!data.labels || !Array.isArray(data.labels)) {
            errors.push('Chart data must include a labels array');
        }
        if (!data.datasets || !Array.isArray(data.datasets) || data.datasets.length === 0) {
            errors.push('Chart data must include at least one dataset');
        }

        return { valid: errors.length === 0, errors, warnings: [] };
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

            .chart-container {
                position: relative;
                width: 100%;
                min-height: 200px;
            }

            .chart-canvas {
                width: 100% !important;
                height: auto !important;
            }

            .loading-indicator {
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 200px;
                color: var(--ax-text-muted, #6c757d);
            }

            .loading-spinner {
                width: 32px;
                height: 32px;
                border: 3px solid var(--ax-border-color, #dee2e6);
                border-top-color: var(--ax-primary-color, #0d6efd);
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }

            @keyframes spin {
                to { transform: rotate(360deg); }
            }

            .error-message {
                color: var(--ax-error-color, #dc3545);
                padding: 1rem;
                text-align: center;
            }

            /* Dark mode */
            @media (prefers-color-scheme: dark) {
                .widget-container {
                    --ax-widget-bg: #2d3748;
                    --ax-border-color: #4a5568;
                    --ax-text-color: #e2e8f0;
                    --ax-text-muted: #a0aec0;
                }
            }
        `;
    }

    // =========================================================================
    // Rendering
    // =========================================================================

    render() {
        const isLoading = this.state === WidgetState.LOADING;
        const chartTitle = this.title || this.prompt;
        const widthStyle = this.width !== 'auto' ? `width: ${this.width}px;` : '';

        this.shadowRoot.innerHTML = `
            <style>${this._styles || ''}</style>
            <div class="widget-container" role="figure" aria-label="${chartTitle || 'Chart'}">
                ${chartTitle ? `<div class="prompt chart-title">${this.escapeHtml(chartTitle)}</div>` : ''}
                <div class="chart-container chart-wrapper" style="height: ${this.height}; ${widthStyle}">
                    <canvas class="chart-canvas" role="img" aria-label="${chartTitle || 'Interactive chart'}"></canvas>
                    ${
                        isLoading
                            ? `
                        <div class="loading-indicator" aria-live="polite" style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.8);">
                            <div class="loading-spinner" aria-label="Loading chart..."></div>
                        </div>
                    `
                            : ''
                    }
                </div>
            </div>
        `;
    }

    async loadStyles() {
        this._styles = await this.getStyles();
    }

    // =========================================================================
    // Chart Management
    // =========================================================================

    async _initChart() {
        try {
            const Chart = await loadChartJs();

            // Re-render without loading indicator (Chart.js loaded)
            this.state = WidgetState.IDLE;
            this.render();

            const canvas = this.shadowRoot.querySelector('.chart-canvas');
            if (!canvas) {
                console.error('Chart canvas not found');
                return;
            }

            const ctx = canvas.getContext('2d');
            const data = this.data;
            const customOptions = this.options;

            // Default options with accessibility considerations
            const defaultOptions = {
                responsive: this.responsive,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 16,
                        },
                    },
                    tooltip: {
                        enabled: true,
                        mode: 'index',
                        intersect: false,
                    },
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false,
                },
            };

            // Merge options
            const mergedOptions = this._deepMerge(defaultOptions, customOptions);

            // Apply color scheme for accessibility
            if (data.datasets && data.datasets.length > 0) {
                const colors = this._getAccessibleColors();
                data.datasets.forEach((dataset, i) => {
                    if (!dataset.backgroundColor) {
                        if (['pie', 'doughnut', 'polarArea'].includes(this.chartType)) {
                            dataset.backgroundColor = colors;
                        } else {
                            dataset.backgroundColor = colors[i % colors.length];
                            dataset.borderColor = colors[i % colors.length];
                        }
                    }
                });
            }

            this._chartData = data;
            this._chartOptions = mergedOptions;

            this._chart = new Chart(ctx, {
                type: this.chartType,
                data: data,
                options: mergedOptions,
            });
        } catch (error) {
            console.error('Failed to initialize chart:', error);
            // Still render canvas for testing/fallback purposes
            this.state = WidgetState.IDLE;
            this.render();
        }
    }

    _destroyChart() {
        if (this._chart) {
            this._chart.destroy();
            this._chart = null;
        }
    }

    /**
     * Update chart with new data
     * @param {Object} newData - New chart data
     */
    updateData(newData) {
        if (this._chart) {
            this._chart.data = newData;
            this._chartData = newData;
            this._chart.update('active');
        }
    }

    /**
     * Update chart options
     * @param {Object} newOptions - New options to merge
     */
    updateOptions(newOptions) {
        if (this._chart) {
            const merged = this._deepMerge(this._chartOptions, newOptions);
            this._chart.options = merged;
            this._chartOptions = merged;
            this._chart.update('active');
        }
    }

    // =========================================================================
    // Events
    // =========================================================================

    bindEvents() {
        const canvas = this.shadowRoot.querySelector('.chart-canvas');
        if (!canvas || !this._chart) return;

        canvas.addEventListener('click', event => {
            const points = this._chart.getElementsAtEventForMode(event, 'nearest', { intersect: true }, false);

            if (points.length > 0) {
                const point = points[0];
                const { datasetIndex, index } = point;
                const dataset = this._chart.data.datasets[datasetIndex];
                const label = this._chart.data.labels[index];
                const value = dataset.data[index];

                this.dispatchEvent(
                    new CustomEvent('ax-chart-click', {
                        bubbles: true,
                        composed: true,
                        detail: {
                            widgetId: this.widgetId,
                            datasetIndex,
                            index,
                            label,
                            value,
                            datasetLabel: dataset.label,
                        },
                    })
                );
            }
        });
    }

    onAttributeChange(name, oldValue, newValue) {
        if (!this._initialized) return;

        if (name === 'data' || name === 'chart-type' || name === 'options') {
            this._destroyChart();
            this._initChart();
        }
    }

    // =========================================================================
    // Utilities
    // =========================================================================

    /**
     * Get accessible color palette
     * @returns {string[]}
     */
    _getAccessibleColors() {
        return [
            '#0d6efd', // Blue
            '#198754', // Green
            '#dc3545', // Red
            '#ffc107', // Yellow
            '#6f42c1', // Purple
            '#20c997', // Teal
            '#fd7e14', // Orange
            '#6c757d', // Gray
            '#0dcaf0', // Cyan
            '#d63384', // Pink
        ];
    }

    /**
     * Deep merge objects
     * @param {Object} target
     * @param {Object} source
     * @returns {Object}
     */
    _deepMerge(target, source) {
        const result = { ...target };

        for (const key in source) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                result[key] = this._deepMerge(result[key] || {}, source[key]);
            } else {
                result[key] = source[key];
            }
        }

        return result;
    }
}

// Register custom element
if (!customElements.get('ax-chart')) {
    customElements.define('ax-chart', AxChart);
}

export default AxChart;
