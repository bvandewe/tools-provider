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
    // Validation UI Methods
    // =========================================================================

    /**
     * Check if widget value is valid (convenience method for WidgetRenderer)
     * @returns {{valid: boolean, errors: string[]}}
     */
    isValid() {
        const validation = this.validate();
        this._validationResult = validation;
        return {
            valid: validation.valid,
            errors: validation.errors || [],
        };
    }

    /**
     * Show validation error with visual feedback
     * @param {string} message - Error message to display
     */
    showError(message) {
        this.state = WidgetState.ERROR;

        // Find the widget container
        const container = this.shadowRoot?.querySelector('.widget-container');
        if (container) {
            container.classList.add('has-error');

            // Add shake animation
            container.style.animation = 'none';
            container.offsetHeight; // Trigger reflow
            container.style.animation = 'shake 0.4s ease-in-out';
        }

        // Show error message (create or update)
        let errorEl = this.shadowRoot?.querySelector('.validation-error-message');
        if (!errorEl && this.shadowRoot) {
            errorEl = document.createElement('div');
            errorEl.className = 'validation-error-message';
            // Insert after widget container
            if (container) {
                container.insertAdjacentElement('afterend', errorEl);
            } else {
                this.shadowRoot.appendChild(errorEl);
            }
        }
        if (errorEl) {
            errorEl.innerHTML = `<i class="bi bi-exclamation-triangle-fill"></i> ${this.escapeHtml(message)}`;
        }

        // Inject shake animation and error styles if not present
        if (!this.shadowRoot?.querySelector('#validation-error-styles')) {
            const style = document.createElement('style');
            style.id = 'validation-error-styles';
            style.textContent = `
                @keyframes shake {
                    0%, 100% { transform: translateX(0); }
                    10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
                    20%, 40%, 60%, 80% { transform: translateX(5px); }
                }
                .widget-container.has-error {
                    border-color: var(--ax-error-color, #dc3545) !important;
                    box-shadow: 0 0 0 2px rgba(220, 53, 69, 0.25);
                }
                .validation-error-message {
                    color: var(--ax-error-color, #dc3545);
                    background: rgba(220, 53, 69, 0.1);
                    padding: 0.5rem 0.75rem;
                    border-radius: 6px;
                    font-size: 0.875rem;
                    margin-top: 0.5rem;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                }
                .validation-error-message i {
                    font-size: 1rem;
                }
            `;
            this.shadowRoot?.appendChild(style);
        }
    }

    /**
     * Clear validation error state
     */
    clearError() {
        if (this.state === WidgetState.ERROR) {
            this.state = WidgetState.IDLE;
        }

        const container = this.shadowRoot?.querySelector('.widget-container');
        if (container) {
            container.classList.remove('has-error');
            container.style.animation = '';
        }

        // Remove error message
        const errorEl = this.shadowRoot?.querySelector('.validation-error-message');
        if (errorEl) {
            errorEl.remove();
        }
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
     * Refresh styles and re-render for theme changes
     * Called by ThemeService when theme is toggled
     */
    async refreshTheme() {
        console.log(`[${this.tagName}] refreshTheme() called`);
        await this.loadStyles();
        console.log(`[${this.tagName}] loadStyles() completed, calling render()`);
        this.render();
        console.log(`[${this.tagName}] render() completed`);
    }

    /**
     * Detect if dark theme is currently active
     * Checks data-bs-theme attribute first (explicit setting takes priority),
     * then dark-theme class, then falls back to prefers-color-scheme
     * @returns {boolean}
     */
    _isDarkTheme() {
        // Check Bootstrap theme attribute FIRST - explicit setting takes priority
        const bsTheme = document.documentElement.getAttribute('data-bs-theme');
        if (bsTheme) {
            // If data-bs-theme is explicitly set, use it and don't check system preference
            const isDark = bsTheme === 'dark';
            console.log(`[${this.tagName}] _isDarkTheme: ${isDark} (data-bs-theme='${bsTheme}')`);
            return isDark;
        }

        // Check custom dark theme class
        if (document.documentElement.classList.contains('dark-theme') || document.body.classList.contains('dark-theme')) {
            console.log(`[${this.tagName}] _isDarkTheme: TRUE (dark-theme class)`);
            return true;
        }

        // Fall back to system preference ONLY if no explicit theme is set
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            console.log(`[${this.tagName}] _isDarkTheme: TRUE (prefers-color-scheme fallback)`);
            return true;
        }

        console.log(`[${this.tagName}] _isDarkTheme: FALSE (no theme set, light default)`);
        return false;
    }

    /**
     * Get base styles shared by all widgets
     * Includes automatic dark theme support based on document theme
     * @returns {string} Base CSS
     */
    getBaseStyles() {
        const isDark = this._isDarkTheme();
        return `
            :host {
                display: block;
                font-family: var(--ax-font-family, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
                font-size: var(--ax-font-size, 1rem);
                color: var(--text-color);
                line-height: 1.5;

                /* Theme-aware CSS variables */
                --widget-bg: ${isDark ? '#1c2128' : '#f8f9fa'};
                --widget-border: ${isDark ? '#2d3748' : '#dee2e6'};
                --text-color: ${isDark ? '#e2e8f0' : '#212529'};
                --text-muted: ${isDark ? '#9ca3af' : '#6c757d'};
                --input-bg: ${isDark ? '#0d1117' : '#ffffff'};
                --input-border: ${isDark ? '#30363d' : '#ced4da'};
                --menu-bg: ${isDark ? '#161b22' : '#ffffff'};
                --menu-border: ${isDark ? '#30363d' : '#dee2e6'};
                --option-hover: ${isDark ? '#21262d' : '#f8f9fa'};
                --option-selected: ${isDark ? '#1f3a5f' : '#e7f1ff'};
                --hover-bg: ${isDark ? '#30363d' : '#e9ecef'};
                --tag-bg: ${isDark ? '#30363d' : '#e9ecef'};
                --star-empty: ${isDark ? '#4a5568' : '#dee2e6'};
                --star-filled: #ffc107;
                --primary-color: #0d6efd;
            }

            :host([disabled]) {
                opacity: 0.6;
                pointer-events: none;
            }

            :host([state="error"]) {
                --widget-border: var(--ax-error-color, #dc3545);
            }

            :host([state="success"]) {
                --widget-border: var(--ax-success-color, #28a745);
            }

            .widget-container {
                background: var(--widget-bg);
                border: 1px solid var(--widget-border);
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
