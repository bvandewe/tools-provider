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

    render() {
        const minLength = this.minLength;
        const maxLength = this.maxLength;
        const isMultiline = this.multiline;

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    font-family: var(--font-family, system-ui, -apple-system, sans-serif);
                }

                .widget-container {
                    background: var(--widget-bg, #f8f9fa);
                    border: 1px solid var(--widget-border, #dee2e6);
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

                /* Dark mode support */
                @media (prefers-color-scheme: dark) {
                    .widget-container {
                        --widget-bg: #2d3748;
                        --widget-border: #4a5568;
                        --text-color: #e2e8f0;
                        --input-bg: #1a202c;
                        --input-border: #4a5568;
                        --text-muted: #9ca3af;
                    }
                }
            </style>

            <div class="widget-container">
                <div class="prompt" id="prompt">${this.escapeHtml(this.prompt)}</div>
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

            // Update validation state
            const isValid = this.validateInput(input.value);
            submitBtn.disabled = !isValid;

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

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

customElements.define('ax-free-text-prompt', AxFreeTextPrompt);

export default AxFreeTextPrompt;
