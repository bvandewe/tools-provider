/**
 * Progress Bar Widget Component
 * Renders a progress indicator with various styles.
 *
 * Attributes:
 * - value: Current progress value (0-100 for percentage, or numeric)
 * - max: Maximum value (default: 100)
 * - variant: "determinate" | "indeterminate" (default: "determinate")
 * - label: Text label to display
 * - show-value: Show the current value/percentage
 * - size: "sm" | "md" | "lg" (default: "md")
 * - color: "primary" | "success" | "warning" | "danger" | custom hex
 * - striped: Show striped pattern
 * - animated: Animate the stripes
 *
 * Events:
 * - ax-progress-complete: Fired when progress reaches 100%
 *   Detail: { widgetId: string }
 *
 * CSS Variables:
 * - --ax-progress-bg: Background color
 * - --ax-progress-bar-bg: Progress bar fill color
 * - --ax-progress-height: Progress bar height
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

class AxProgressBar extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'value', 'max', 'variant', 'label', 'show-value', 'size', 'color', 'striped', 'animated'];
    }

    constructor() {
        super();
        this._completed = false;
    }

    // =========================================================================
    // Attribute Getters
    // =========================================================================

    get value() {
        const val = this.getAttribute('value');
        return val !== null ? parseFloat(val) : 0;
    }

    set value(val) {
        this.setAttribute('value', String(val));
    }

    get max() {
        const val = this.getAttribute('max');
        return val !== null ? parseFloat(val) : 100;
    }

    get variant() {
        return this.getAttribute('variant') || 'determinate';
    }

    get label() {
        return this.getAttribute('label') || null;
    }

    get showValue() {
        return this.hasAttribute('show-value');
    }

    get size() {
        return this.getAttribute('size') || 'md';
    }

    get color() {
        return this.getAttribute('color') || 'primary';
    }

    get striped() {
        return this.hasAttribute('striped');
    }

    get animated() {
        return this.hasAttribute('animated');
    }

    /**
     * Calculate progress percentage
     * @returns {number} Percentage (0-100)
     */
    get percentage() {
        const max = this.max || 100;
        return Math.min(100, Math.max(0, (this.value / max) * 100));
    }

    // =========================================================================
    // AxWidgetBase Implementation
    // =========================================================================

    getValue() {
        return this.value;
    }

    setValue(value) {
        this.value = value;
    }

    validate() {
        return { valid: true, errors: [], warnings: [] };
    }

    async getStyles() {
        return `
            ${this.getBaseStyles()}

            :host {
                display: block;
                --ax-progress-bg: #e9ecef;
                --ax-progress-bar-bg: var(--ax-primary-color, #0d6efd);
                --ax-progress-height: 1rem;
            }

            .widget-container {
                background: transparent;
                border: none;
                padding: 0;
                margin: var(--ax-margin, 0.5rem 0);
            }

            .progress-wrapper {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }

            .progress-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.875rem;
            }

            .progress-label {
                color: var(--ax-text-color, #212529);
                font-weight: 500;
            }

            .progress-value {
                color: var(--ax-text-muted, #6c757d);
            }

            /* Progress bar container */
            .progress {
                height: var(--ax-progress-height);
                background-color: var(--ax-progress-bg);
                border-radius: calc(var(--ax-progress-height) / 2);
                overflow: hidden;
            }

            /* Size variants */
            .progress.size-sm {
                --ax-progress-height: 0.5rem;
            }

            .progress.size-md {
                --ax-progress-height: 1rem;
            }

            .progress.size-lg {
                --ax-progress-height: 1.5rem;
            }

            /* Progress bar fill */
            .progress-bar {
                height: 100%;
                background-color: var(--ax-progress-bar-bg);
                border-radius: calc(var(--ax-progress-height) / 2);
                transition: width 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            /* Color variants */
            .progress-bar.color-primary {
                --ax-progress-bar-bg: var(--ax-primary-color, #0d6efd);
            }

            .progress-bar.color-success {
                --ax-progress-bar-bg: #28a745;
            }

            .progress-bar.color-warning {
                --ax-progress-bar-bg: #ffc107;
            }

            .progress-bar.color-danger {
                --ax-progress-bar-bg: #dc3545;
            }

            /* Striped pattern */
            .progress-bar.striped {
                background-image: linear-gradient(
                    45deg,
                    rgba(255, 255, 255, 0.15) 25%,
                    transparent 25%,
                    transparent 50%,
                    rgba(255, 255, 255, 0.15) 50%,
                    rgba(255, 255, 255, 0.15) 75%,
                    transparent 75%,
                    transparent
                );
                background-size: 1rem 1rem;
            }

            .progress-bar.striped.animated {
                animation: stripeMove 1s linear infinite;
            }

            @keyframes stripeMove {
                from {
                    background-position: 1rem 0;
                }
                to {
                    background-position: 0 0;
                }
            }

            /* Indeterminate animation */
            .progress-bar.indeterminate {
                width: 30% !important;
                animation: indeterminate 1.5s ease-in-out infinite;
            }

            @keyframes indeterminate {
                0% {
                    transform: translateX(-100%);
                }
                100% {
                    transform: translateX(400%);
                }
            }

            /* Value inside bar (for lg size) */
            .progress-bar-value {
                color: #ffffff;
                font-size: 0.75rem;
                font-weight: 600;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
            }

            /* Completed state */
            .progress-bar.completed {
                animation: pulse 0.5s ease;
            }

            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.02); }
                100% { transform: scale(1); }
            }

            /* Dark mode */
            @media (prefers-color-scheme: dark) {
                :host {
                    --ax-progress-bg: #4a5568;
                }

                .progress-label {
                    color: #e2e8f0;
                }

                .progress-value {
                    color: #a0aec0;
                }
            }
        `;
    }

    render() {
        const percentage = this.percentage;
        const isIndeterminate = this.variant === 'indeterminate';
        const showValue = this.showValue;
        const label = this.label;
        const size = this.size;
        const color = this.getColorClass();
        const striped = this.striped;
        const animated = this.animated;

        // Check for completion
        if (percentage >= 100 && !this._completed) {
            this._completed = true;
            this.dispatchEvent(
                new CustomEvent('ax-progress-complete', {
                    bubbles: true,
                    composed: true,
                    detail: { widgetId: this.widgetId },
                })
            );
        }

        const barClasses = [
            'progress-bar',
            `color-${color}`,
            isIndeterminate ? 'indeterminate' : '',
            striped ? 'striped' : '',
            animated && striped ? 'animated' : '',
            this._completed ? 'completed' : '',
        ]
            .filter(Boolean)
            .join(' ');

        this.shadowRoot.innerHTML = `
            <div class="widget-container" role="progressbar"
                 aria-valuenow="${isIndeterminate ? '' : this.value}"
                 aria-valuemin="0"
                 aria-valuemax="${this.max}"
                 aria-label="${label || 'Progress'}">
                <div class="progress-wrapper">
                    ${
                        label || showValue
                            ? `
                        <div class="progress-header">
                            ${label ? `<span class="progress-label">${this.escapeHtml(label)}</span>` : ''}
                            ${showValue && !isIndeterminate ? `<span class="progress-value">${Math.round(percentage)}%</span>` : ''}
                        </div>
                    `
                            : ''
                    }
                    <div class="progress size-${size}">
                        <div class="${barClasses}"
                             style="width: ${isIndeterminate ? '30%' : percentage + '%'}">
                            ${size === 'lg' && showValue && !isIndeterminate && percentage > 10 ? `<span class="progress-bar-value">${Math.round(percentage)}%</span>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    onAttributeChange(name, oldValue, newValue) {
        if (name === 'value') {
            // Check if progress went from complete back to incomplete
            if (this.percentage < 100) {
                this._completed = false;
            }
        }
        this.render();
    }

    // =========================================================================
    // Helper Methods
    // =========================================================================

    /**
     * Get color class from color attribute
     * @returns {string} Color class name
     */
    getColorClass() {
        const color = this.color;
        const validColors = ['primary', 'success', 'warning', 'danger'];
        if (validColors.includes(color)) {
            return color;
        }
        // For custom hex colors, set CSS variable
        if (color.startsWith('#') || color.startsWith('rgb')) {
            this.style.setProperty('--ax-progress-bar-bg', color);
            return 'primary'; // Use primary class structure
        }
        return 'primary';
    }

    // =========================================================================
    // Public Methods
    // =========================================================================

    /**
     * Increment progress by a value
     * @param {number} amount - Amount to increment
     */
    increment(amount = 1) {
        this.value = Math.min(this.max, this.value + amount);
    }

    /**
     * Decrement progress by a value
     * @param {number} amount - Amount to decrement
     */
    decrement(amount = 1) {
        this.value = Math.max(0, this.value - amount);
    }

    /**
     * Reset progress to 0
     */
    reset() {
        this.value = 0;
        this._completed = false;
        this.render();
    }

    /**
     * Set to indeterminate mode
     */
    setIndeterminate() {
        this.setAttribute('variant', 'indeterminate');
    }

    /**
     * Set to determinate mode
     */
    setDeterminate() {
        this.setAttribute('variant', 'determinate');
    }
}

customElements.define('ax-progress-bar', AxProgressBar);

export default AxProgressBar;
