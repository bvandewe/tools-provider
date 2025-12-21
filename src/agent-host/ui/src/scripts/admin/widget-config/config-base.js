/**
 * Widget Configuration Base Class
 *
 * Base class for all widget configuration UIs in the admin templates editor.
 * Each widget type extends this class to provide its own config UI.
 *
 * @module admin/widget-config/config-base
 */

/**
 * Base class for widget configuration UIs
 */
export class WidgetConfigBase {
    /**
     * @param {HTMLElement} containerEl - Container element to render config into
     * @param {string} widgetType - Widget type identifier
     */
    constructor(containerEl, widgetType) {
        this.container = containerEl;
        this.widgetType = widgetType;
        this.uid = `config-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Render the configuration UI
     * @param {Object} config - Initial configuration values
     * @param {Object} content - Full content object (for options, correct_answer, etc.)
     */
    render(config = {}, content = {}) {
        throw new Error('render() must be implemented by subclass');
    }

    /**
     * Get current configuration values
     * @returns {Object} Widget configuration object matching Python schema
     */
    getValue() {
        throw new Error('getValue() must be implemented by subclass');
    }

    /**
     * Validate current configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        return { valid: true, errors: [] };
    }

    /**
     * Get options array (for widgets that support options)
     * @returns {string[]} Array of option strings
     */
    getOptions() {
        return [];
    }

    /**
     * Get correct answer (for widgets that support correct answers)
     * @returns {string|null} Correct answer value
     */
    getCorrectAnswer() {
        return null;
    }

    /**
     * Get initial value (for widgets that support initial values)
     * @returns {*} Initial value
     */
    getInitialValue() {
        return null;
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Create a form group with label and tooltip (no wrapper)
     * @param {string} label - Label text
     * @param {string} inputHtml - Inner HTML for the input element
     * @param {string} tooltip - Tooltip text
     * @param {boolean} [required=false] - Whether field is required (shows asterisk)
     * @returns {string} HTML string
     */
    createFormGroup(label, inputHtml, tooltip, required = false) {
        const requiredMark = required ? '<span class="text-danger">*</span>' : '';
        return `
            <label class="form-label small mb-0">
                ${this.escapeHtml(label)}${requiredMark}
                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                   title="${this.escapeHtml(tooltip)}"></i>
            </label>
            ${inputHtml}
        `;
    }

    /**
     * Create a text input field
     * @param {string} className - CSS class for the input
     * @param {string} value - Initial value
     * @param {string} placeholder - Placeholder text
     * @returns {string} HTML string
     */
    createTextInput(className, value, placeholder) {
        return `<input type="text" class="form-control form-control-sm ${className}"
                       value="${this.escapeHtml(value || '')}" placeholder="${this.escapeHtml(placeholder)}">`;
    }

    /**
     * Create a number input field
     * @param {string} className - CSS class for the input
     * @param {number|string} value - Initial value
     * @param {number|string} minOrPlaceholder - Min value (if number) or placeholder (if string)
     * @param {number} [max] - Max value (only used if minOrPlaceholder is number)
     * @param {number} [step] - Step value (only used if minOrPlaceholder is number)
     * @returns {string} HTML string
     */
    createNumberInput(className, value, minOrPlaceholder, max, step) {
        // Detect calling convention based on type of third argument
        let placeholder = '';
        let minAttr = '';
        let maxAttr = '';
        let stepAttr = '';

        if (typeof minOrPlaceholder === 'number') {
            // Called as: (className, value, min, max, step)
            minAttr = `min="${minOrPlaceholder}"`;
            if (max !== undefined) maxAttr = `max="${max}"`;
            if (step !== undefined) stepAttr = `step="${step}"`;
        } else if (typeof minOrPlaceholder === 'string') {
            // Called as: (className, value, placeholder, opts?)
            placeholder = minOrPlaceholder;
            // Check if max is actually an opts object (old signature)
            if (max && typeof max === 'object') {
                const opts = max;
                if (opts.min !== undefined) minAttr = `min="${opts.min}"`;
                if (opts.max !== undefined) maxAttr = `max="${opts.max}"`;
                if (opts.step !== undefined) stepAttr = `step="${opts.step}"`;
            }
        } else if (minOrPlaceholder && typeof minOrPlaceholder === 'object') {
            // Called as: (className, value, opts)
            const opts = minOrPlaceholder;
            if (opts.min !== undefined) minAttr = `min="${opts.min}"`;
            if (opts.max !== undefined) maxAttr = `max="${opts.max}"`;
            if (opts.step !== undefined) stepAttr = `step="${opts.step}"`;
            placeholder = opts.placeholder || '';
        }

        return `<input type="number" class="form-control form-control-sm ${className}"
                       value="${value ?? ''}" placeholder="${this.escapeHtml(placeholder)}"
                       ${minAttr} ${maxAttr} ${stepAttr}>`;
    }

    /**
     * Create a switch checkbox
     * @param {string} className - CSS class for the input
     * @param {string} id - Input element ID
     * @param {string} label - Label text
     * @param {string} tooltip - Tooltip text
     * @param {boolean} checked - Initial checked state
     * @returns {string} HTML string
     */
    createSwitch(className, id, label, tooltip, checked) {
        return `
            <div class="form-check form-switch">
                <input class="form-check-input ${className}" type="checkbox" id="${id}"
                       ${checked ? 'checked' : ''}>
                <label class="form-check-label small" for="${id}">
                    ${this.escapeHtml(label)}
                    <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                       title="${this.escapeHtml(tooltip)}"></i>
                </label>
            </div>
        `;
    }

    /**
     * Create a select dropdown
     * @param {string} className - CSS class for the select
     * @param {Array<{value: string, label: string}>} options - Options array
     * @param {string} selectedValue - Currently selected value
     * @returns {string} HTML string
     */
    createSelect(className, options, selectedValue) {
        const optionsHtml = options.map(opt => `<option value="${this.escapeHtml(opt.value)}" ${opt.value === selectedValue ? 'selected' : ''}>${this.escapeHtml(opt.label)}</option>`).join('');
        return `<select class="form-select form-select-sm ${className}">${optionsHtml}</select>`;
    }

    /**
     * Create a textarea
     * @param {string} className - CSS class for the textarea
     * @param {string} value - Initial value
     * @param {string} placeholder - Placeholder text
     * @param {number} [rows=3] - Number of rows
     * @returns {string} HTML string
     */
    createTextarea(className, value, placeholder, rows = 3) {
        return `<textarea class="form-control form-control-sm ${className}" rows="${rows}"
                          placeholder="${this.escapeHtml(placeholder)}">${this.escapeHtml(value || '')}</textarea>`;
    }

    /**
     * Create a collapsible section for advanced options
     * @param {string} id - Collapse element ID
     * @param {string} title - Section title
     * @param {string} contentHtml - Inner HTML for the collapsed content
     * @param {boolean} [expanded=false] - Initial expanded state
     * @returns {string} HTML string
     */
    createCollapsibleSection(id, title, contentHtml, expanded = false) {
        return `
            <div class="mt-2">
                <button class="btn btn-link btn-sm p-0 text-decoration-none" type="button"
                        data-bs-toggle="collapse" data-bs-target="#${id}"
                        aria-expanded="${expanded}" aria-controls="${id}">
                    <i class="bi bi-chevron-${expanded ? 'down' : 'right'} me-1"></i>
                    <small class="text-muted">${this.escapeHtml(title)}</small>
                </button>
                <div class="collapse ${expanded ? 'show' : ''}" id="${id}">
                    <div class="pt-2">
                        ${contentHtml}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Query element within container
     * @param {string} selector - CSS selector
     * @returns {HTMLElement|null} Found element or null
     */
    query(selector) {
        return this.container.querySelector(selector);
    }

    /**
     * Query all elements within container
     * @param {string} selector - CSS selector
     * @returns {NodeList} Found elements
     */
    queryAll(selector) {
        return this.container.querySelectorAll(selector);
    }

    /**
     * Get value from input by class name
     * @param {string} className - CSS class name (without dot)
     * @param {*} [defaultValue=null] - Default value if element not found
     * @returns {string} Input value
     */
    getInputValue(className, defaultValue = null) {
        const el = this.query(`.${className}`);
        return el?.value || defaultValue;
    }

    /**
     * Get numeric value from input by class name
     * @param {string} className - CSS class name (without dot)
     * @param {number|null} [defaultValue=null] - Default value if element not found or empty
     * @returns {number|null} Numeric value or null
     */
    getNumericValue(className, defaultValue = null) {
        const el = this.query(`.${className}`);
        if (!el?.value) return defaultValue;
        const parsed = parseFloat(el.value);
        return isNaN(parsed) ? defaultValue : parsed;
    }

    /**
     * Get integer value from input by class name
     * @param {string} className - CSS class name (without dot)
     * @param {number|null} [defaultValue=null] - Default value if element not found or empty
     * @returns {number|null} Integer value or null
     */
    getIntValue(className, defaultValue = null) {
        const el = this.query(`.${className}`);
        if (!el?.value) return defaultValue;
        const parsed = parseInt(el.value, 10);
        return isNaN(parsed) ? defaultValue : parsed;
    }

    /**
     * Get checkbox checked state by class name
     * @param {string} className - CSS class name (without dot)
     * @param {boolean} [defaultValue=false] - Default value if element not found
     * @returns {boolean} Checked state
     */
    getChecked(className, defaultValue = false) {
        const el = this.query(`.${className}`);
        return el?.checked ?? defaultValue;
    }

    /**
     * Initialize Bootstrap tooltips in the container
     */
    initTooltips() {
        const tooltipTriggers = this.container.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipTriggers.forEach(el => {
            if (!bootstrap.Tooltip.getInstance(el)) {
                new bootstrap.Tooltip(el, {
                    trigger: 'hover',
                    delay: { show: 200, hide: 0 },
                });
            }
        });
    }

    /**
     * Dispose Bootstrap tooltips in the container
     */
    disposeTooltips() {
        const tooltipTriggers = this.container.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipTriggers.forEach(el => {
            const tooltip = bootstrap.Tooltip.getInstance(el);
            tooltip?.dispose();
        });
    }
}
