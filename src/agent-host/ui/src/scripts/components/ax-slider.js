/**
 * Slider Widget Component
 * Renders a range slider with optional labels and value display.
 *
 * Attributes:
 * - prompt: The question or label to display
 * - min: Minimum value (default: 0)
 * - max: Maximum value (default: 100)
 * - step: Step increment (default: 1)
 * - value: Initial value
 * - show-value: Show current value display
 * - show-labels: Show min/max labels
 * - unit: Unit suffix (e.g., "%", "px")
 * - disabled: Disable the slider
 *
 * Events:
 * - ax-response: Fired when user changes value
 *   Detail: { value: number }
 * - ax-change: Fired on each value change (includes during drag)
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

class AxSlider extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'prompt', 'min', 'max', 'step', 'value', 'show-value', 'show-labels', 'unit'];
    }

    constructor() {
        super();
        this._value = null;
        this._isDragging = false;
    }

    // Attribute getters
    get prompt() {
        return this.getAttribute('prompt') || '';
    }

    get min() {
        return parseFloat(this.getAttribute('min')) || 0;
    }

    get max() {
        return parseFloat(this.getAttribute('max')) || 100;
    }

    get step() {
        return parseFloat(this.getAttribute('step')) || 1;
    }

    get showValue() {
        return this.hasAttribute('show-value');
    }

    get showLabels() {
        return this.hasAttribute('show-labels');
    }

    get unit() {
        return this.getAttribute('unit') || '';
    }

    // Value interface
    getValue() {
        return this._value ?? this.min;
    }

    setValue(value) {
        const numValue = parseFloat(value);
        if (!isNaN(numValue)) {
            this._value = Math.min(this.max, Math.max(this.min, numValue));
            this._updateDisplay();
        }
    }

    validate() {
        const value = this.getValue();
        const errors = [];

        if (value < this.min) {
            errors.push(`Value must be at least ${this.min}`);
        }
        if (value > this.max) {
            errors.push(`Value must be at most ${this.max}`);
        }

        return { valid: errors.length === 0, errors, warnings: [] };
    }

    async getStyles() {
        return `
            ${await this.getBaseStyles()}

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
            }

            .prompt {
                font-size: 1rem;
                font-weight: 500;
                color: var(--text-color, #212529);
                margin-bottom: 1rem;
                line-height: 1.5;
            }

            .slider-wrapper {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }

            .slider-row {
                display: flex;
                align-items: center;
                gap: 1rem;
            }

            .slider-input {
                flex: 1;
                height: 8px;
                -webkit-appearance: none;
                appearance: none;
                background: var(--slider-track, #dee2e6);
                border-radius: 4px;
                outline: none;
                cursor: pointer;
            }

            .slider-input::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 20px;
                height: 20px;
                background: var(--primary-color, #0d6efd);
                border-radius: 50%;
                cursor: pointer;
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }

            .slider-input::-webkit-slider-thumb:hover {
                transform: scale(1.1);
                box-shadow: 0 0 0 4px rgba(13, 110, 253, 0.2);
            }

            .slider-input::-moz-range-thumb {
                width: 20px;
                height: 20px;
                background: var(--primary-color, #0d6efd);
                border: none;
                border-radius: 50%;
                cursor: pointer;
            }

            .slider-input:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            .slider-input:disabled::-webkit-slider-thumb {
                cursor: not-allowed;
            }

            .value-display {
                min-width: 60px;
                text-align: center;
                font-weight: 600;
                font-size: 1.1rem;
                color: var(--primary-color, #0d6efd);
                padding: 0.25rem 0.5rem;
                background: var(--value-bg, #e7f1ff);
                border-radius: 6px;
            }

            .labels-row {
                display: flex;
                justify-content: space-between;
                font-size: 0.85rem;
                color: var(--text-muted, #6c757d);
            }

            :host([disabled]) .widget-container {
                opacity: 0.6;
            }
        `;
    }

    render() {
        const initialValue = this.getAttribute('value');
        if (initialValue !== null && this._value === null) {
            this._value = parseFloat(initialValue);
        }
        if (this._value === null) {
            this._value = this.min;
        }

        const percentage = ((this._value - this.min) / (this.max - this.min)) * 100;

        this.shadowRoot.innerHTML = `
            <style>${this._styles || ''}</style>
            <div class="widget-container">
                ${this.prompt ? `<div class="prompt">${this.prompt}</div>` : ''}
                <div class="slider-wrapper">
                    <div class="slider-row">
                        <input
                            type="range"
                            class="slider-input"
                            min="${this.min}"
                            max="${this.max}"
                            step="${this.step}"
                            value="${this._value}"
                            ${this.disabled ? 'disabled' : ''}
                            aria-label="${this.prompt || 'Slider'}"
                            aria-valuemin="${this.min}"
                            aria-valuemax="${this.max}"
                            aria-valuenow="${this._value}"
                        />
                        ${
                            this.showValue
                                ? `
                            <div class="value-display" aria-live="polite">
                                ${this._value}${this.unit}
                            </div>
                        `
                                : ''
                        }
                    </div>
                    ${
                        this.showLabels
                            ? `
                        <div class="labels-row">
                            <span>${this.min}${this.unit}</span>
                            <span>${this.max}${this.unit}</span>
                        </div>
                    `
                            : ''
                    }
                </div>
            </div>
        `;

        this._styles = this.shadowRoot.querySelector('style')?.textContent;
    }

    async loadStyles() {
        this._styles = await this.getStyles();
    }

    bindEvents() {
        const slider = this.shadowRoot.querySelector('.slider-input');
        if (!slider) return;

        slider.addEventListener('input', e => {
            this._value = parseFloat(e.target.value);
            this.clearError(); // Clear validation error on interaction
            this._updateDisplay();
            this.dispatchChange();
            // Emit ax-selection for confirmation mode support
            this.dispatchEvent(
                new CustomEvent('ax-selection', {
                    bubbles: true,
                    composed: true,
                    detail: { value: this._value, widgetId: this.widgetId },
                })
            );
        });

        slider.addEventListener('change', e => {
            this._value = parseFloat(e.target.value);
            this._updateDisplay();
            this.dispatchResponse();
        });
    }

    _updateDisplay() {
        const slider = this.shadowRoot.querySelector('.slider-input');
        const valueDisplay = this.shadowRoot.querySelector('.value-display');

        if (slider) {
            slider.value = this._value;
            slider.setAttribute('aria-valuenow', this._value);
        }
        if (valueDisplay) {
            valueDisplay.textContent = `${this._value}${this.unit}`;
        }
    }

    dispatchChange() {
        this.dispatchEvent(
            new CustomEvent('ax-change', {
                bubbles: true,
                composed: true,
                detail: { value: this._value, widgetId: this.widgetId },
            })
        );
    }

    dispatchResponse() {
        this.dispatchEvent(
            new CustomEvent('ax-response', {
                bubbles: true,
                composed: true,
                detail: { value: this._value, widgetId: this.widgetId },
            })
        );
    }
}

customElements.define('ax-slider', AxSlider);

export default AxSlider;
