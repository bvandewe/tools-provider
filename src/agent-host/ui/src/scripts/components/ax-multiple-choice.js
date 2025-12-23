/**
 * Multiple Choice Widget Component
 * Renders a list of options for the user to select from
 *
 * Attributes:
 * - prompt: The question or prompt to display
 * - options: JSON array of option strings
 * - allow-multiple: Whether multiple selections are allowed
 *
 * Events:
 * - ax-response: Fired when user makes a selection
 *   Detail: { selection: string, index: number } or { selections: string[], indices: number[] }
 */
import { marked } from 'marked';

// Configure marked for safe HTML rendering
marked.setOptions({
    breaks: true,
    gfm: true,
});

class AxMultipleChoice extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this._selectedIndex = -1;
        this._selectedIndices = new Set();
    }

    static get observedAttributes() {
        return ['prompt', 'options', 'allow-multiple'];
    }

    connectedCallback() {
        this.render();
        this.setupKeyboardNavigation();
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (oldValue !== newValue && this.shadowRoot) {
            this.render();
        }
    }

    get prompt() {
        return this.getAttribute('prompt') || '';
    }

    get options() {
        try {
            return JSON.parse(this.getAttribute('options') || '[]');
        } catch {
            return [];
        }
    }

    get allowMultiple() {
        return this.hasAttribute('allow-multiple');
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
        const options = this.options;
        const prompt = this.prompt;
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
                    --option-bg: ${isDark ? '#0d1117' : '#ffffff'};
                    --option-border: ${isDark ? '#30363d' : '#dee2e6'};
                    --option-hover-bg: ${isDark ? '#30363d' : '#e9ecef'};
                    --option-hover-border: ${isDark ? '#484f58' : '#adb5bd'};
                    --primary-light: ${isDark ? '#1f3a5f' : '#e7f1ff'};
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
                    border: 1px solid var(--option-border, #dee2e6);
                    padding: 8px 12px;
                    text-align: left;
                }
                .prompt th {
                    background: var(--option-bg, #ffffff);
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

                .options-list {
                    display: flex;
                    flex-direction: column;
                    gap: 0.5rem;
                }

                .option-btn {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    width: 100%;
                    padding: 0.75rem 1rem;
                    background: var(--option-bg, #ffffff);
                    border: 2px solid var(--option-border, #dee2e6);
                    border-radius: 8px;
                    font-size: 0.95rem;
                    color: var(--text-color, #212529);
                    cursor: pointer;
                    transition: all 0.15s ease;
                    text-align: left;
                }

                .option-btn:hover {
                    background: var(--option-hover-bg, #e9ecef);
                    border-color: var(--option-hover-border, #adb5bd);
                }

                .option-btn:focus {
                    outline: none;
                    border-color: var(--primary-color, #0d6efd);
                    box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.25);
                }

                .option-btn.selected {
                    background: var(--primary-light, #e7f1ff);
                    border-color: var(--primary-color, #0d6efd);
                    color: var(--primary-color, #0d6efd);
                }

                .option-btn.focused {
                    border-color: var(--primary-color, #0d6efd);
                }

                .option-indicator {
                    width: 20px;
                    height: 20px;
                    border: 2px solid var(--option-border, #dee2e6);
                    border-radius: ${this.allowMultiple ? '4px' : '50%'};
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex-shrink: 0;
                    transition: all 0.15s ease;
                }

                .option-btn.selected .option-indicator {
                    background: var(--primary-color, #0d6efd);
                    border-color: var(--primary-color, #0d6efd);
                }

                .option-indicator svg {
                    width: 12px;
                    height: 12px;
                    fill: white;
                    opacity: 0;
                    transition: opacity 0.15s ease;
                }

                .option-btn.selected .option-indicator svg {
                    opacity: 1;
                }

                .option-text {
                    flex: 1;
                }

                .submit-row {
                    margin-top: 1rem;
                    display: ${this.allowMultiple ? 'flex' : 'none'};
                    justify-content: flex-end;
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

                .keyboard-hint {
                    font-size: 0.75rem;
                    color: var(--text-muted);
                    margin-top: 0.75rem;
                    text-align: center;
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

                .error-message {
                    color: #dc3545;
                    font-size: 0.875rem;
                    margin-top: 0.75rem;
                    padding: 0.5rem 0.75rem;
                    background: rgba(220, 53, 69, 0.1);
                    border-radius: 6px;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                }

                .error-message::before {
                    content: "⚠";
                }
            </style>

            <div class="widget-container" role="group" aria-labelledby="prompt">
                <div class="prompt" id="prompt">${this.renderMarkdown(prompt)}</div>
                <div class="options-list" role="listbox" aria-label="Options">
                    ${options
                        .map(
                            (option, index) => `
                        <button class="option-btn"
                                role="option"
                                data-index="${index}"
                                aria-selected="false"
                                tabindex="${index === 0 ? '0' : '-1'}">
                            <span class="option-indicator">
                                <svg viewBox="0 0 16 16" aria-hidden="true">
                                    <path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/>
                                </svg>
                            </span>
                            <span class="option-text">${this.escapeHtml(option)}</span>
                        </button>
                    `
                        )
                        .join('')}
                </div>
                <div class="submit-row">
                    <button class="submit-btn" disabled>Submit</button>
                </div>
                <div class="keyboard-hint">
                    Use ↑↓ arrow keys to navigate, Enter to select
                </div>
            </div>
        `;

        // Add click handlers
        this.shadowRoot.querySelectorAll('.option-btn').forEach(btn => {
            btn.addEventListener('click', () => this.selectOption(parseInt(btn.dataset.index)));
        });

        // Add submit handler for multiple selection
        if (this.allowMultiple) {
            const submitBtn = this.shadowRoot.querySelector('.submit-btn');
            submitBtn.addEventListener('click', () => this.submitMultiple());
        }
    }

    setupKeyboardNavigation() {
        this.shadowRoot.addEventListener('keydown', e => {
            const buttons = Array.from(this.shadowRoot.querySelectorAll('.option-btn'));
            const currentIndex = buttons.findIndex(btn => btn === this.shadowRoot.activeElement);

            switch (e.key) {
                case 'ArrowDown':
                case 'ArrowRight':
                    e.preventDefault();
                    const nextIndex = currentIndex < buttons.length - 1 ? currentIndex + 1 : 0;
                    buttons[nextIndex].focus();
                    break;

                case 'ArrowUp':
                case 'ArrowLeft':
                    e.preventDefault();
                    const prevIndex = currentIndex > 0 ? currentIndex - 1 : buttons.length - 1;
                    buttons[prevIndex].focus();
                    break;

                case 'Enter':
                case ' ':
                    e.preventDefault();
                    if (currentIndex >= 0) {
                        this.selectOption(currentIndex);
                    }
                    break;
            }
        });
    }

    selectOption(index) {
        const options = this.options;
        if (index < 0 || index >= options.length) return;

        // Clear any validation error when user makes a selection
        this.clearError();

        const buttons = this.shadowRoot.querySelectorAll('.option-btn');

        if (this.allowMultiple) {
            // Toggle selection
            if (this._selectedIndices.has(index)) {
                this._selectedIndices.delete(index);
                buttons[index].classList.remove('selected');
                buttons[index].setAttribute('aria-selected', 'false');
            } else {
                this._selectedIndices.add(index);
                buttons[index].classList.add('selected');
                buttons[index].setAttribute('aria-selected', 'true');
            }

            // Update submit button
            const submitBtn = this.shadowRoot.querySelector('.submit-btn');
            submitBtn.disabled = this._selectedIndices.size === 0;

            // Emit ax-selection on every change for confirmation mode support
            // This allows external confirmation buttons to capture the current selections
            if (this._selectedIndices.size > 0) {
                const indices = Array.from(this._selectedIndices).sort((a, b) => a - b);
                const selections = indices.map(i => options[i]);
                this.dispatchEvent(
                    new CustomEvent('ax-selection', {
                        bubbles: true,
                        composed: true,
                        detail: {
                            selections: selections,
                            indices: indices,
                        },
                    })
                );
            }
        } else {
            // Single selection - emit immediately
            buttons.forEach(btn => {
                btn.classList.remove('selected');
                btn.setAttribute('aria-selected', 'false');
            });
            buttons[index].classList.add('selected');
            buttons[index].setAttribute('aria-selected', 'true');

            this._selectedIndex = index;

            // Emit response
            this.dispatchEvent(
                new CustomEvent('ax-response', {
                    bubbles: true,
                    composed: true,
                    detail: {
                        selection: options[index],
                        index: index,
                    },
                })
            );
        }
    }

    submitMultiple() {
        const options = this.options;
        const indices = Array.from(this._selectedIndices).sort((a, b) => a - b);
        const selections = indices.map(i => options[i]);

        this.dispatchEvent(
            new CustomEvent('ax-response', {
                bubbles: true,
                composed: true,
                detail: {
                    selections: selections,
                    indices: indices,
                },
            })
        );
    }

    /**
     * Get current value for external confirmation mode
     * Returns null if nothing selected and widget is required
     * @returns {Object|null} Current selection(s) or null
     */
    getValue() {
        const options = this.options;

        if (this.allowMultiple) {
            if (this._selectedIndices.size === 0) {
                return null;
            }
            const indices = Array.from(this._selectedIndices).sort((a, b) => a - b);
            const selections = indices.map(i => options[i]);
            return { selections, indices };
        } else {
            if (this._selectedIndex < 0) {
                return null;
            }
            return {
                selection: options[this._selectedIndex],
                index: this._selectedIndex,
            };
        }
    }

    /**
     * Check if the widget has a valid value
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    isValid() {
        const hasSelection = this.allowMultiple ? this._selectedIndices.size > 0 : this._selectedIndex >= 0;
        const isRequired = this.hasAttribute('required');

        if (isRequired && !hasSelection) {
            return {
                valid: false,
                errors: ['Please select an option'],
            };
        }
        return { valid: true, errors: [] };
    }

    /**
     * Show validation error state on the widget
     * @param {string} message - Error message to display
     */
    showError(message) {
        const container = this.shadowRoot?.querySelector('.widget-container');
        if (container) {
            container.classList.add('has-error');
            // Add error message if not already present
            let errorEl = this.shadowRoot.querySelector('.error-message');
            if (!errorEl) {
                errorEl = document.createElement('div');
                errorEl.className = 'error-message';
                container.appendChild(errorEl);
            }
            errorEl.textContent = message;
        }
    }

    /**
     * Clear validation error state
     */
    clearError() {
        const container = this.shadowRoot?.querySelector('.widget-container');
        if (container) {
            container.classList.remove('has-error');
            const errorEl = this.shadowRoot.querySelector('.error-message');
            if (errorEl) {
                errorEl.remove();
            }
        }
    }

    /**
     * Refresh theme - called by ThemeService when theme changes
     * Re-renders the component with updated theme-aware styles
     */
    refreshTheme() {
        this.render();
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

customElements.define('ax-multiple-choice', AxMultipleChoice);

export default AxMultipleChoice;
