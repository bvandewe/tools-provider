/**
 * Submit Button Widget Component
 * Renders a submit/action button with various states.
 *
 * Attributes:
 * - label: Button text (default: "Submit")
 * - variant: "primary" | "secondary" | "success" | "danger" | "outline" (default: "primary")
 * - size: "sm" | "md" | "lg" (default: "md")
 * - loading: Show loading spinner
 * - icon: Optional icon name (bootstrap-icons)
 * - confirm: Confirmation message before action
 * - countdown: Countdown seconds before auto-submit
 *
 * Events:
 * - ax-submit: Fired when button is clicked (after confirmation if set)
 *   Detail: { widgetId: string, timestamp: string }
 *
 * CSS Variables:
 * - --ax-btn-primary-bg: Primary button background
 * - --ax-btn-primary-hover: Primary button hover background
 * - --ax-btn-border-radius: Button border radius
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

class AxSubmitButton extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'label', 'variant', 'size', 'loading', 'icon', 'confirm', 'countdown'];
    }

    constructor() {
        super();
        this._countdownValue = 0;
        this._countdownInterval = null;
        this._submitted = false;
    }

    // =========================================================================
    // Attribute Getters
    // =========================================================================

    get label() {
        return this.getAttribute('label') || 'Submit';
    }

    set label(value) {
        this.setAttribute('label', value);
    }

    get variant() {
        return this.getAttribute('variant') || 'primary';
    }

    get size() {
        return this.getAttribute('size') || 'md';
    }

    get loading() {
        return this.hasAttribute('loading');
    }

    set loading(value) {
        if (value) {
            this.setAttribute('loading', '');
        } else {
            this.removeAttribute('loading');
        }
    }

    get icon() {
        return this.getAttribute('icon') || null;
    }

    get confirm() {
        return this.getAttribute('confirm') || null;
    }

    get countdown() {
        const val = this.getAttribute('countdown');
        return val ? parseInt(val, 10) : null;
    }

    // =========================================================================
    // AxWidgetBase Implementation
    // =========================================================================

    getValue() {
        return this._submitted;
    }

    setValue(value) {
        this._submitted = Boolean(value);
    }

    validate() {
        return { valid: true, errors: [], warnings: [] };
    }

    async getStyles() {
        const isDark = this._isDarkTheme();
        return `
            ${this.getBaseStyles()}

            :host {
                display: inline-block;
                --ax-btn-primary-bg: var(--ax-primary-color, #0d6efd);
                --ax-btn-primary-hover: #0b5ed7;
                --ax-btn-secondary-bg: #6c757d;
                --ax-btn-secondary-hover: #5c636a;
                --ax-btn-success-bg: #28a745;
                --ax-btn-success-hover: #218838;
                --ax-btn-danger-bg: #dc3545;
                --ax-btn-danger-hover: #c82333;
                --ax-btn-border-radius: 8px;
                --ax-text-color: ${isDark ? '#e2e8f0' : '#212529'};
                --ax-dialog-bg: ${isDark ? '#21262d' : '#ffffff'};
                --ax-dialog-border: ${isDark ? '#30363d' : '#dee2e6'};
            }

            .widget-container {
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }

            .submit-btn {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                font-family: inherit;
                font-weight: 500;
                text-align: center;
                white-space: nowrap;
                vertical-align: middle;
                user-select: none;
                border: 2px solid transparent;
                border-radius: var(--ax-btn-border-radius);
                cursor: pointer;
                transition: all 0.15s ease-in-out;
            }

            /* Size variants */
            .submit-btn.size-sm {
                padding: 0.375rem 0.75rem;
                font-size: 0.875rem;
            }

            .submit-btn.size-md {
                padding: 0.625rem 1.25rem;
                font-size: 1rem;
            }

            .submit-btn.size-lg {
                padding: 0.75rem 1.5rem;
                font-size: 1.125rem;
            }

            /* Color variants */
            .submit-btn.variant-primary {
                background-color: var(--ax-btn-primary-bg);
                border-color: var(--ax-btn-primary-bg);
                color: #ffffff;
            }

            .submit-btn.variant-primary:hover:not(:disabled) {
                background-color: var(--ax-btn-primary-hover);
                border-color: var(--ax-btn-primary-hover);
            }

            .submit-btn.variant-secondary {
                background-color: var(--ax-btn-secondary-bg);
                border-color: var(--ax-btn-secondary-bg);
                color: #ffffff;
            }

            .submit-btn.variant-secondary:hover:not(:disabled) {
                background-color: var(--ax-btn-secondary-hover);
                border-color: var(--ax-btn-secondary-hover);
            }

            .submit-btn.variant-success {
                background-color: var(--ax-btn-success-bg);
                border-color: var(--ax-btn-success-bg);
                color: #ffffff;
            }

            .submit-btn.variant-success:hover:not(:disabled) {
                background-color: var(--ax-btn-success-hover);
                border-color: var(--ax-btn-success-hover);
            }

            .submit-btn.variant-danger {
                background-color: var(--ax-btn-danger-bg);
                border-color: var(--ax-btn-danger-bg);
                color: #ffffff;
            }

            .submit-btn.variant-danger:hover:not(:disabled) {
                background-color: var(--ax-btn-danger-hover);
                border-color: var(--ax-btn-danger-hover);
            }

            .submit-btn.variant-outline {
                background-color: transparent;
                border-color: var(--ax-btn-primary-bg);
                color: var(--ax-btn-primary-bg);
            }

            .submit-btn.variant-outline:hover:not(:disabled) {
                background-color: var(--ax-btn-primary-bg);
                color: #ffffff;
            }

            /* States */
            .submit-btn:focus {
                outline: none;
                box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.25);
            }

            .submit-btn:disabled {
                opacity: 0.65;
                cursor: not-allowed;
            }

            .submit-btn.loading {
                pointer-events: none;
            }

            .submit-btn.submitted {
                background-color: var(--ax-btn-success-bg);
                border-color: var(--ax-btn-success-bg);
            }

            /* Icon */
            .btn-icon {
                width: 1em;
                height: 1em;
                flex-shrink: 0;
            }

            /* Spinner */
            .spinner {
                width: 1em;
                height: 1em;
                border: 2px solid currentColor;
                border-right-color: transparent;
                border-radius: 50%;
                animation: spin 0.75s linear infinite;
            }

            @keyframes spin {
                to {
                    transform: rotate(360deg);
                }
            }

            /* Countdown */
            .countdown {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 1.5em;
                height: 1.5em;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 50%;
                font-size: 0.75em;
                font-weight: 600;
            }

            /* Confirmation dialog */
            .confirm-dialog {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 9999;
                animation: fadeIn 0.2s ease;
            }

            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            .confirm-content {
                background: #ffffff;
                border-radius: 12px;
                padding: 1.5rem;
                max-width: 400px;
                width: 90%;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            }

            .confirm-message {
                margin-bottom: 1.25rem;
                font-size: 1rem;
                color: var(--ax-text-color, #212529);
            }

            .confirm-actions {
                display: flex;
                gap: 0.75rem;
                justify-content: flex-end;
            }

            .confirm-cancel {
                padding: 0.5rem 1rem;
                background: transparent;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                color: #6c757d;
                cursor: pointer;
            }

            .confirm-cancel:hover {
                background: ${isDark ? '#30363d' : '#f8f9fa'};
            }

            .confirm-ok {
                padding: 0.5rem 1rem;
                background: var(--ax-btn-primary-bg);
                border: none;
                border-radius: 6px;
                color: #ffffff;
                cursor: pointer;
            }

            .confirm-ok:hover {
                background: var(--ax-btn-primary-hover);
            }

            /* Theme-aware confirmation dialog */
            .confirm-content {
                background: var(--ax-dialog-bg);
                color: var(--ax-text-color);
            }

            .confirm-cancel {
                border-color: var(--ax-dialog-border);
                color: ${isDark ? '#a0aec0' : '#6c757d'};
            }
        `;
    }

    render() {
        const label = this.label;
        const variant = this.variant;
        const size = this.size;
        const isLoading = this.loading;
        const isDisabled = this.disabled || isLoading;
        const icon = this.icon;

        this.shadowRoot.innerHTML = `
            <div class="widget-container">
                <button
                    class="submit-btn variant-${variant} size-${size} ${isLoading ? 'loading' : ''} ${this._submitted ? 'submitted' : ''}"
                    ${isDisabled ? 'disabled' : ''}
                    aria-busy="${isLoading}"
                >
                    ${isLoading ? '<span class="spinner" aria-hidden="true"></span>' : ''}
                    ${icon && !isLoading ? this.renderIcon(icon) : ''}
                    ${this._countdownValue > 0 ? `<span class="countdown">${this._countdownValue}</span>` : ''}
                    <span class="btn-label">${this.escapeHtml(label)}</span>
                </button>
            </div>
        `;

        this.bindEvents();
    }

    bindEvents() {
        const button = this.shadowRoot.querySelector('.submit-btn');
        if (button) {
            button.addEventListener('click', e => this.handleClick(e));
        }
    }

    connectedCallback() {
        super.connectedCallback();

        // Start countdown if configured
        if (this.countdown && this.countdown > 0) {
            this.startCountdown(this.countdown);
        }
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        this.stopCountdown();
    }

    // =========================================================================
    // Event Handlers
    // =========================================================================

    /**
     * Handle button click
     * @param {Event} e - Click event
     */
    handleClick(e) {
        e.preventDefault();

        if (this.disabled || this.loading || this._submitted) {
            return;
        }

        if (this.confirm) {
            this.showConfirmDialog();
        } else {
            this.submit();
        }
    }

    /**
     * Submit the button action
     */
    submit() {
        this._submitted = true;
        this.stopCountdown();
        this.state = WidgetState.SUCCESS;

        // Show submitted state briefly
        this.render();

        this.dispatchEvent(
            new CustomEvent('ax-submit', {
                bubbles: true,
                composed: true,
                detail: {
                    widgetId: this.widgetId,
                    itemId: this.itemId,
                    timestamp: new Date().toISOString(),
                },
            })
        );

        // Also dispatch standard response
        this.dispatchResponse({ submitted: true });
    }

    // =========================================================================
    // Confirmation Dialog
    // =========================================================================

    /**
     * Show confirmation dialog
     */
    showConfirmDialog() {
        const dialog = document.createElement('div');
        dialog.className = 'confirm-dialog';
        dialog.innerHTML = `
            <div class="confirm-content" role="alertdialog" aria-modal="true">
                <p class="confirm-message">${this.escapeHtml(this.confirm)}</p>
                <div class="confirm-actions">
                    <button class="confirm-cancel" type="button">Cancel</button>
                    <button class="confirm-ok" type="button">Confirm</button>
                </div>
            </div>
        `;

        // Handle cancel
        dialog.querySelector('.confirm-cancel').addEventListener('click', () => {
            dialog.remove();
        });

        // Handle confirm
        dialog.querySelector('.confirm-ok').addEventListener('click', () => {
            dialog.remove();
            this.submit();
        });

        // Handle backdrop click
        dialog.addEventListener('click', e => {
            if (e.target === dialog) {
                dialog.remove();
            }
        });

        // Handle escape key
        dialog.addEventListener('keydown', e => {
            if (e.key === 'Escape') {
                dialog.remove();
            }
        });

        this.shadowRoot.appendChild(dialog);
        dialog.querySelector('.confirm-ok').focus();
    }

    // =========================================================================
    // Countdown
    // =========================================================================

    /**
     * Start countdown timer
     * @param {number} seconds - Countdown duration
     */
    startCountdown(seconds) {
        this._countdownValue = seconds;
        this.render();

        this._countdownInterval = setInterval(() => {
            this._countdownValue--;
            this.render();

            if (this._countdownValue <= 0) {
                this.stopCountdown();
                this.submit();
            }
        }, 1000);
    }

    /**
     * Stop countdown timer
     */
    stopCountdown() {
        if (this._countdownInterval) {
            clearInterval(this._countdownInterval);
            this._countdownInterval = null;
        }
        this._countdownValue = 0;
    }

    // =========================================================================
    // Icon Rendering
    // =========================================================================

    /**
     * Render an icon
     * @param {string} iconName - Icon name (bootstrap-icons)
     * @returns {string} Icon HTML
     */
    renderIcon(iconName) {
        // Common icons
        const icons = {
            check: '<path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/>',
            send: '<path d="M15.854.146a.5.5 0 0 1 .11.54l-5.819 14.547a.75.75 0 0 1-1.329.124l-3.178-4.995L.643 7.184a.75.75 0 0 1 .124-1.33L15.314.037a.5.5 0 0 1 .54.11ZM6.636 10.07l2.761 4.338L14.13 2.576 6.636 10.07Zm6.787-8.201L1.591 6.602l4.339 2.76 7.494-7.493Z"/>',
            arrow_right: '<path fill-rule="evenodd" d="M4 8a.5.5 0 0 1 .5-.5h5.793L8.146 5.354a.5.5 0 1 1 .708-.708l3 3a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708-.708L10.293 8.5H4.5A.5.5 0 0 1 4 8z"/>',
        };

        const iconPath = icons[iconName] || icons['check'];
        return `<svg class="btn-icon" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">${iconPath}</svg>`;
    }

    // =========================================================================
    // Public Methods
    // =========================================================================

    /**
     * Reset button to initial state
     */
    reset() {
        this._submitted = false;
        this.state = WidgetState.IDLE;
        this.loading = false;
        this.stopCountdown();
        this.render();
    }

    /**
     * Set loading state
     * @param {boolean} isLoading - Loading state
     */
    setLoading(isLoading) {
        this.loading = isLoading;
        this.render();
    }
}

customElements.define('ax-submit-button', AxSubmitButton);

export default AxSubmitButton;
