/**
 * Widget Base Class
 * Abstract base class for all Agent Host widgets.
 *
 * Provides common functionality:
 * - Shadow DOM with scoped styles
 * - Attribute observation and change handling
 * - Value get/set interface
 * - Validation framework
 * - Accessibility helpers
 * - Event dispatching
 * - State management (idle, active, disabled, readonly, error, success)
 *
 * Usage:
 *   class MyWidget extends AxWidgetBase {
 *     static get observedAttributes() {
 *       return [...super.observedAttributes, 'my-attr'];
 *     }
 *     render() { ... }
 *     getValue() { ... }
 *     setValue(value) { ... }
 *     validate() { ... }
 *   }
 *
 * @abstract
 */
import { marked } from 'marked';

// Configure marked for safe HTML rendering
marked.setOptions({
    breaks: true,
    gfm: true,
});

/**
 * Widget state enum
 * @enum {string}
 */
export const WidgetState = {
    IDLE: 'idle',
    ACTIVE: 'active',
    DISABLED: 'disabled',
    READONLY: 'readonly',
    ERROR: 'error',
    SUCCESS: 'success',
    LOADING: 'loading',
};

/**
 * Validation result structure
 * @typedef {Object} ValidationResult
 * @property {boolean} valid - Whether validation passed
 * @property {string[]} errors - List of error messages
 * @property {string[]} warnings - List of warning messages
 */

/**
 * Abstract base class for all Agent Host widgets
 * @abstract
 */
export class AxWidgetBase extends HTMLElement {
    /**
     * Attributes common to all widgets
     * @returns {string[]}
     */
    static get observedAttributes() {
        return ['widget-id', 'item-id', 'disabled', 'readonly', 'required', 'state'];
    }

    constructor() {
        super();
        this.attachShadow({ mode: 'open' });

        // Internal state
        this._value = null;
        this._state = WidgetState.IDLE;
        this._initialized = false;
        this._validationResult = { valid: true, errors: [], warnings: [] };
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    /**
     * Called when element is added to DOM
     */
    async connectedCallback() {
        await this.loadStyles();
        this.render();
        this.bindEvents();
        this.announceAccessibility();
        this._initialized = true;
    }

    /**
     * Called when element is removed from DOM
     */
    disconnectedCallback() {
        this.cleanup();
    }

    /**
     * Called when observed attribute changes
     * @param {string} name - Attribute name
     * @param {string|null} oldValue - Previous value
     * @param {string|null} newValue - New value
     */
    attributeChangedCallback(name, oldValue, newValue) {
        if (oldValue !== newValue && this._initialized) {
            this.onAttributeChange(name, oldValue, newValue);
        }
    }

    // =========================================================================
    // Abstract Methods (must be implemented by subclasses)
    // =========================================================================

    /**
     * Render the widget content
     * @abstract
     */
    render() {
        throw new Error('render() must be implemented by subclass');
    }

    /**
     * Get the current widget value
     * @abstract
     * @returns {*} The widget value
     */
    getValue() {
        throw new Error('getValue() must be implemented by subclass');
    }

    /**
     * Set the widget value
     * @abstract
     * @param {*} value - The value to set
     */
    setValue(value) {
        throw new Error('setValue() must be implemented by subclass');
    }

    /**
     * Validate the current widget value
     * @abstract
     * @returns {ValidationResult} Validation result
     */
    validate() {
        return { valid: true, errors: [], warnings: [] };
    }

    // =========================================================================
    // Optional Overrides
    // =========================================================================

    /**
     * Get widget-specific styles
     * Override in subclass to add custom styles
     * @returns {Promise<string>} CSS string
     */
    async getStyles() {
        return this.getBaseStyles();
    }

    /**
     * Bind event listeners
     * Override in subclass to add custom event handlers
     */
    bindEvents() {
        // Default: no-op
    }

    /**
     * Cleanup resources on disconnect
     * Override in subclass for custom cleanup
     */
    cleanup() {
        // Default: no-op
    }

    /**
     * Handle attribute changes
     * Override in subclass for custom attribute handling
     * @param {string} name - Attribute name
     * @param {string|null} oldValue - Previous value
     * @param {string|null} newValue - New value
     */
    onAttributeChange(name, oldValue, newValue) {
        // Default: re-render on any attribute change
        this.render();
    }

    // =========================================================================
    // Common Getters (Attributes)
    // =========================================================================

    get widgetId() {
        return this.getAttribute('widget-id') || '';
    }

    get itemId() {
        return this.getAttribute('item-id') || '';
    }

    get disabled() {
        return this.hasAttribute('disabled');
    }

    set disabled(val) {
        if (val) {
            this.setAttribute('disabled', '');
        } else {
            this.removeAttribute('disabled');
        }
    }

    get readonly() {
        return this.hasAttribute('readonly');
    }

    set readonly(val) {
        if (val) {
            this.setAttribute('readonly', '');
        } else {
            this.removeAttribute('readonly');
        }
    }

    get required() {
        return this.hasAttribute('required');
    }

    set required(val) {
        if (val) {
            this.setAttribute('required', '');
        } else {
            this.removeAttribute('required');
        }
    }

    // =========================================================================
    // State Management
    // =========================================================================

    /**
     * Get current widget state
     * @returns {string} Current state
     */
    get state() {
        return this._state;
    }

    /**
     * Set widget state
     * @param {string} newState - New state value
     */
    set state(newState) {
        const oldState = this._state;
        if (oldState !== newState) {
            this._state = newState;
            this.setAttribute('state', newState);
            this.dispatchEvent(
                new CustomEvent('ax-state-change', {
                    bubbles: true,
                    composed: true,
                    detail: { oldState, newState, widgetId: this.widgetId },
                })
            );
        }
    }

    // =========================================================================
    // Value Management
    // =========================================================================

    /**
     * Get validated value (calls validate() first)
     * @returns {{value: *, validation: ValidationResult}}
     */
    getValidatedValue() {
        const value = this.getValue();
        const validation = this.validate();
        this._validationResult = validation;
        return { value, validation };
    }

    /**
     * Get last validation result
     * @returns {ValidationResult}
     */
    getValidationResult() {
        return this._validationResult;
    }

    // =========================================================================
    // Event Helpers
    // =========================================================================

    /**
     * Dispatch a response event
     * @param {*} value - Response value
     * @param {Object} metadata - Optional metadata
     */
    dispatchResponse(value, metadata = {}) {
        this.dispatchEvent(
            new CustomEvent('ax-response', {
                bubbles: true,
                composed: true,
                detail: {
                    widgetId: this.widgetId,
                    itemId: this.itemId,
                    value,
                    timestamp: new Date().toISOString(),
                    ...metadata,
                },
            })
        );
    }

    /**
     * Dispatch a value change event (for live updates)
     * @param {*} value - New value
     */
    dispatchValueChange(value) {
        this.dispatchEvent(
            new CustomEvent('ax-value-change', {
                bubbles: true,
                composed: true,
                detail: {
                    widgetId: this.widgetId,
                    value,
                },
            })
        );
    }

    // =========================================================================
    // Accessibility
    // =========================================================================

    /**
     * Announce widget for screen readers
     */
    announceAccessibility() {
        // Set basic ARIA attributes if not already set
        if (!this.getAttribute('role')) {
            this.setAttribute('role', 'group');
        }
        if (this.disabled) {
            this.setAttribute('aria-disabled', 'true');
        }
    }

    /**
     * Announce a message to screen readers
     * @param {string} message - Message to announce
     * @param {string} priority - 'polite' or 'assertive'
     */
    announce(message, priority = 'polite') {
        const announcer = document.createElement('div');
        announcer.setAttribute('aria-live', priority);
        announcer.setAttribute('aria-atomic', 'true');
        announcer.className = 'sr-only';
        announcer.style.cssText = 'position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;';
        announcer.textContent = message;
        this.shadowRoot.appendChild(announcer);
        setTimeout(() => announcer.remove(), 1000);
    }

    // =========================================================================
    // Style Management
    // =========================================================================

    /**
     * Load and apply styles
     */
    async loadStyles() {
        const styles = await this.getStyles();
        const sheet = new CSSStyleSheet();
        await sheet.replace(styles);
        this.shadowRoot.adoptedStyleSheets = [sheet];
    }

    /**
     * Get base styles shared by all widgets
     * @returns {string} Base CSS
     */
    getBaseStyles() {
        return `
            :host {
                display: block;
                font-family: var(--ax-font-family, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
                font-size: var(--ax-font-size, 1rem);
                color: var(--ax-text-color, #212529);
                line-height: 1.5;
            }

            :host([disabled]) {
                opacity: 0.6;
                pointer-events: none;
            }

            :host([state="error"]) {
                --ax-border-color: var(--ax-error-color, #dc3545);
            }

            :host([state="success"]) {
                --ax-border-color: var(--ax-success-color, #28a745);
            }

            .widget-container {
                background: var(--ax-widget-bg, #f8f9fa);
                border: 1px solid var(--ax-border-color, #dee2e6);
                border-radius: var(--ax-border-radius, 12px);
                padding: var(--ax-padding, 1.25rem);
                margin: var(--ax-margin, 0.5rem 0);
                animation: slideIn 0.3s ease-out;
            }

            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .sr-only {
                position: absolute;
                width: 1px;
                height: 1px;
                padding: 0;
                margin: -1px;
                overflow: hidden;
                clip: rect(0, 0, 0, 0);
                white-space: nowrap;
                border: 0;
            }

            .error-message {
                color: var(--ax-error-color, #dc3545);
                font-size: 0.875rem;
                margin-top: 0.5rem;
            }

            .warning-message {
                color: var(--ax-warning-color, #ffc107);
                font-size: 0.875rem;
                margin-top: 0.5rem;
            }

            /* Dark mode support */
            @media (prefers-color-scheme: dark) {
                :host {
                    --ax-widget-bg: #2d3748;
                    --ax-border-color: #4a5568;
                    --ax-text-color: #e2e8f0;
                }
            }
        `;
    }

    // =========================================================================
    // Utility Methods
    // =========================================================================

    /**
     * Escape HTML special characters
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Render markdown to HTML
     * @param {string} text - Markdown text
     * @returns {string} HTML string
     */
    renderMarkdown(text) {
        if (!text) return '';
        try {
            return marked.parse(text);
        } catch (e) {
            console.warn('Markdown parsing failed:', e);
            return this.escapeHtml(text);
        }
    }

    /**
     * Parse JSON attribute safely
     * @param {string} attrName - Attribute name
     * @param {*} defaultValue - Default value if parsing fails
     * @returns {*} Parsed value or default
     */
    parseJsonAttribute(attrName, defaultValue = null) {
        try {
            const value = this.getAttribute(attrName);
            return value ? JSON.parse(value) : defaultValue;
        } catch (e) {
            console.warn(`Failed to parse JSON attribute "${attrName}":`, e);
            return defaultValue;
        }
    }

    /**
     * Debounce a function
     * @param {Function} fn - Function to debounce
     * @param {number} delay - Delay in milliseconds
     * @returns {Function} Debounced function
     */
    debounce(fn, delay = 250) {
        let timeoutId;
        return (...args) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn.apply(this, args), delay);
        };
    }
}

// Export for use in other modules
export default AxWidgetBase;
