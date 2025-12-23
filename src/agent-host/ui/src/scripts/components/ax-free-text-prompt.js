/**
 * Free Text Prompt Widget Component
 * Renders a text input for the user to provide free-form text
 *
 * Attributes:
 * - prompt: The question or prompt to display
 * - placeholder: Placeholder text for the input
 * - min-length: Minimum character length required
 * - max-length: Maximum character length allowed
 * - multiline: Whether to use a textarea instead of input
 *
 * Events:
 * - ax-response: Fired when user submits their response
 *   Detail: { text: string }
 */
import { marked } from 'marked';

// Configure marked for safe HTML rendering
marked.setOptions({
    breaks: true,
    gfm: true,
});

class AxFreeTextPrompt extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    static get observedAttributes() {
        return ['prompt', 'placeholder', 'min-length', 'max-length', 'multiline'];
    }

    connectedCallback() {
        this.render();
        this.setupEventListeners();
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (oldValue !== newValue && this.shadowRoot) {
            this.render();
            this.setupEventListeners();
        }
    }

    get prompt() {
        return this.getAttribute('prompt') || '';
    }

    get placeholder() {
        return this.getAttribute('placeholder') || 'Type your response here...';
    }

    get minLength() {
        const val = this.getAttribute('min-length');
        return val ? parseInt(val, 10) : 0;
    }

    get maxLength() {
        const val = this.getAttribute('max-length');
        return val ? parseInt(val, 10) : null;
    }

    get multiline() {
        return this.hasAttribute('multiline');
    }

    /**
     * Check if dark theme is active.
     * Prioritizes explicit data-bs-theme setting over system preference.
     */
    _isDarkTheme() {
        // Check Bootstrap theme attribute FIRST - explicit setting takes priority
        const bsTheme = document.documentElement.getAttribute('data-bs-theme');
        if (bsTheme) {
            return bsTheme === 'dark';
        }
        // Check custom dark theme class
        if (document.documentElement.classList.contains('dark-theme') || document.body.classList.contains('dark-theme')) {
            return true;
        }
        // Fall back to system preference ONLY if no explicit theme is set
        return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    render() {
        const minLength = this.minLength;
        const maxLength = this.maxLength;
        const isMultiline = this.multiline;
        const isDark = this._isDarkTheme();

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    font-family: var(--font-family, system-ui, -apple-system, sans-serif);

                    /* Theme-aware variables */
                    --widget-bg: ${isDark ? '#21262d' : '#f8f9fa'};
                    --widget-border: ${isDark ? '#30363d' : '#dee2e6'};
                    --text-color: ${isDark ? '#e2e8f0' : '#212529'};
                    --text-muted: ${isDark ? '#8b949e' : '#6c757d'};
                    --input-bg: ${isDark ? '#0d1117' : '#ffffff'};
                    --input-border: ${isDark ? '#30363d' : '#dee2e6'};
                }

                .widget-container {
                    background: var(--widget-bg);
                    border: 1px solid var(--widget-border);
                    border-radius: 12px;
                    padding: 1.25rem;
                    margin: 0.5rem 0;
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

                .prompt {
                    font-size: 1rem;
                    font-weight: 500;
                    color: var(--text-color, #212529);
                    margin-bottom: 1rem;
                    line-height: 1.5;
                }

                /* Markdown content styles */
                .prompt p {
                    margin: 0 0 0.5rem 0;
                }
                .prompt p:last-child {
                    margin-bottom: 0;
                }
                .prompt pre {
                    background: #1e1e1e;
                    color: #d4d4d4;
                    padding: 12px;
                    border-radius: 8px;
                    overflow-x: auto;
                    margin: 8px 0;
                    font-size: 0.875em;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
                .prompt code {
                    font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
                    font-size: 0.9em;
                    background: rgba(0, 0, 0, 0.05);
                    padding: 2px 6px;
                    border-radius: 4px;
                }
                .prompt pre code {
                    background: transparent;
                    padding: 0;
                }
                .prompt table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 8px 0;
                    font-size: 0.9em;
                }
                .prompt th, .prompt td {
                    border: 1px solid var(--input-border, #dee2e6);
                    padding: 8px 12px;
                    text-align: left;
                }
                .prompt th {
                    background: var(--input-bg, #ffffff);
                    font-weight: 600;
                }
                .prompt ul, .prompt ol {
                    margin: 8px 0;
                    padding-left: 1.5rem;
                }
                .prompt li {
                    margin: 4px 0;
                }
                .prompt blockquote {
                    border-left: 4px solid var(--primary-color, #0d6efd);
                    margin: 8px 0;
                    padding-left: 1rem;
                    color: var(--text-muted, #6c757d);
                }

                .input-container {
                    position: relative;
                }

                .text-input,
                .text-area {
                    width: 100%;
                    padding: 0.75rem 1rem;
                    font-size: 0.95rem;
                    font-family: inherit;
                    color: var(--text-color, #212529);
                    background: var(--input-bg, #ffffff);
                    border: 2px solid var(--input-border, #dee2e6);
                    border-radius: 8px;
                    transition: border-color 0.15s ease, box-shadow 0.15s ease;
                    box-sizing: border-box;
                }

                .text-input:focus,
                .text-area:focus {
                    outline: none;
                    border-color: var(--primary-color, #0d6efd);
                    box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.25);
                }

                .text-area {
                    min-height: 120px;
                    resize: vertical;
                    line-height: 1.5;
                }

                .footer {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-top: 0.75rem;
                }

                .char-count {
                    font-size: 0.8rem;
                    color: var(--text-muted, #6c757d);
                }

                .char-count.warning {
                    color: var(--warning-color, #ffc107);
                }

                .char-count.error {
                    color: var(--error-color, #dc3545);
                }

                .char-count.valid {
                    color: var(--success-color, #198754);
                }

                .submit-btn {
                    padding: 0.5rem 1.5rem;
                    background: var(--primary-color, #0d6efd);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 0.95rem;
                    font-weight: 500;
                    cursor: pointer;
                    transition: background 0.15s ease;
                }

                .submit-btn:hover:not(:disabled) {
                    background: var(--primary-hover, #0b5ed7);
                }

                .submit-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .validation-message {
                    font-size: 0.8rem;
                    color: var(--error-color, #dc3545);
                    margin-top: 0.5rem;
                    display: none;
                }

                .validation-message.visible {
                    display: block;
                }

                /* Error state styles */
                .widget-container.has-error {
                    border-color: #dc3545;
                    animation: shake 0.4s ease-in-out;
                }

                @keyframes shake {
                    0%, 100% { transform: translateX(0); }
                    25% { transform: translateX(-5px); }
                    50% { transform: translateX(5px); }
                    75% { transform: translateX(-5px); }
                }
            </style>

            <div class="widget-container">
                <div class="prompt" id="prompt">${this.renderMarkdown(this.prompt)}</div>
                <div class="input-container">
                    ${
                        isMultiline
                            ? `
                        <textarea
                            class="text-area"
                            placeholder="${this.escapeHtml(this.placeholder)}"
                            ${maxLength ? `maxlength="${maxLength}"` : ''}
                            aria-labelledby="prompt"
                        ></textarea>
                    `
                            : `
                        <input
                            type="text"
                            class="text-input"
                            placeholder="${this.escapeHtml(this.placeholder)}"
                            ${maxLength ? `maxlength="${maxLength}"` : ''}
                            aria-labelledby="prompt"
                        />
                    `
                    }
                </div>
                <div class="validation-message" role="alert"></div>
                <div class="footer">
                    <span class="char-count">
                        <span class="current">0</span>${maxLength ? ` / ${maxLength}` : ''} characters
                        ${minLength > 0 ? ` (min: ${minLength})` : ''}
                    </span>
                    <button class="submit-btn" disabled>Submit</button>
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        const input = this.shadowRoot.querySelector('.text-input, .text-area');
        const submitBtn = this.shadowRoot.querySelector('.submit-btn');
        const charCount = this.shadowRoot.querySelector('.char-count');
        const currentCount = this.shadowRoot.querySelector('.current');
        const validationMsg = this.shadowRoot.querySelector('.validation-message');

        if (!input) return;

        // Update character count and validation on input
        input.addEventListener('input', () => {
            const length = input.value.length;
            currentCount.textContent = length;

            // Clear any validation error when user starts typing
            this.clearError();

            // Update validation state
            const isValid = this.validateInput(input.value);
            submitBtn.disabled = !isValid;

            // Emit ax-selection on every change for confirmation mode support
            // This allows external confirmation buttons to capture the current value
            if (input.value.trim().length > 0) {
                this.dispatchEvent(
                    new CustomEvent('ax-selection', {
                        bubbles: true,
                        composed: true,
                        detail: {
                            text: input.value.trim(),
                        },
                    })
                );
            }

            // Update char count styling
            charCount.classList.remove('warning', 'error', 'valid');
            if (this.maxLength && length >= this.maxLength * 0.9) {
                charCount.classList.add('warning');
            }
            if (this.minLength > 0 && length >= this.minLength) {
                charCount.classList.add('valid');
            }
            if (this.minLength > 0 && length < this.minLength && length > 0) {
                charCount.classList.add('error');
            }
        });

        // Submit on Enter for single-line input
        if (!this.multiline) {
            input.addEventListener('keydown', e => {
                if (e.key === 'Enter' && !submitBtn.disabled) {
                    e.preventDefault();
                    this.submit();
                }
            });
        } else {
            // Ctrl/Cmd + Enter for multiline
            input.addEventListener('keydown', e => {
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !submitBtn.disabled) {
                    e.preventDefault();
                    this.submit();
                }
            });
        }

        // Submit button click
        submitBtn.addEventListener('click', () => this.submit());

        // Focus the input
        setTimeout(() => input.focus(), 100);
    }

    validateInput(text) {
        const length = text.trim().length;

        if (this.minLength > 0 && length < this.minLength) {
            return false;
        }

        if (this.maxLength && length > this.maxLength) {
            return false;
        }

        return length > 0;
    }

    submit() {
        const input = this.shadowRoot.querySelector('.text-input, .text-area');
        const text = input.value.trim();

        if (!this.validateInput(text)) {
            const validationMsg = this.shadowRoot.querySelector('.validation-message');
            if (this.minLength > 0 && text.length < this.minLength) {
                validationMsg.textContent = `Please enter at least ${this.minLength} characters.`;
                validationMsg.classList.add('visible');
            }
            return;
        }

        // Dispatch response event
        this.dispatchEvent(
            new CustomEvent('ax-response', {
                bubbles: true,
                composed: true,
                detail: {
                    text: text,
                },
            })
        );
    }

    /**
     * Get current value for external confirmation mode
     * @returns {Object|null} Current text value or null if empty
     */
    getValue() {
        const input = this.shadowRoot?.querySelector('.text-input, .text-area');
        if (!input) return null;

        const text = input.value.trim();
        if (text.length === 0) {
            return null;
        }
        return { text };
    }

    /**
     * Check if the widget has a valid value
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    isValid() {
        const input = this.shadowRoot?.querySelector('.text-input, .text-area');
        if (!input) {
            return { valid: false, errors: ['Widget not initialized'] };
        }

        const text = input.value.trim();
        const isRequired = this.hasAttribute('required');
        const errors = [];

        if (isRequired && text.length === 0) {
            errors.push('This field is required');
        } else if (this.minLength > 0 && text.length > 0 && text.length < this.minLength) {
            errors.push(`Please enter at least ${this.minLength} characters`);
        } else if (this.maxLength && text.length > this.maxLength) {
            errors.push(`Please enter no more than ${this.maxLength} characters`);
        }

        return { valid: errors.length === 0, errors };
    }

    /**
     * Show validation error state on the widget
     * @param {string} message - Error message to display
     */
    showError(message) {
        const container = this.shadowRoot?.querySelector('.widget-container');
        const validationMsg = this.shadowRoot?.querySelector('.validation-message');
        if (container) {
            container.classList.add('has-error');
        }
        if (validationMsg) {
            validationMsg.textContent = message;
            validationMsg.classList.add('visible');
        }
    }

    /**
     * Clear validation error state
     */
    clearError() {
        const container = this.shadowRoot?.querySelector('.widget-container');
        const validationMsg = this.shadowRoot?.querySelector('.validation-message');
        if (container) {
            container.classList.remove('has-error');
        }
        if (validationMsg) {
            validationMsg.textContent = '';
            validationMsg.classList.remove('visible');
        }
    }

    /**
     * Refresh theme - called by ThemeService when theme changes
     * Re-renders the component with updated theme-aware styles
     */
    refreshTheme() {
        this.render();
        this.setupEventListeners();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    renderMarkdown(text) {
        if (!text) return '';
        try {
            return marked.parse(text);
        } catch (e) {
            // Fallback to escaped HTML if markdown parsing fails
            return this.escapeHtml(text);
        }
    }
}

customElements.define('ax-free-text-prompt', AxFreeTextPrompt);

export default AxFreeTextPrompt;
