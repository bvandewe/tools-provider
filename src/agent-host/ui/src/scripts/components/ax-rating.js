/**
 * Rating Widget Component
 * Displays star/scale rating input.
 *
 * Attributes:
 * - prompt: Label text
 * - max: Maximum rating value (default: 5)
 * - value: Current rating
 * - icon: "star" | "heart" | "circle" (default: star)
 * - allow-half: Allow half-star ratings
 * - show-value: Show numeric value
 * - readonly: Display only, no input
 * - disabled: Disable interaction
 *
 * Events:
 * - ax-response: Fired when rating changes
 *   Detail: { value: number }
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

class AxRating extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'prompt', 'max', 'value', 'icon', 'allow-half', 'show-value'];
    }

    constructor() {
        super();
        this._value = 0;
        this._hoverValue = null;
    }

    // Attribute getters
    get prompt() {
        return this.getAttribute('prompt') || '';
    }

    get max() {
        return parseInt(this.getAttribute('max')) || 5;
    }

    get icon() {
        return this.getAttribute('icon') || 'star';
    }

    get allowHalf() {
        return this.hasAttribute('allow-half');
    }

    get showValue() {
        return this.hasAttribute('show-value');
    }

    // Icon characters
    get _icons() {
        const icons = {
            star: { empty: '☆', full: '★', half: '⯨' },
            heart: { empty: '♡', full: '♥', half: '♥' },
            circle: { empty: '○', full: '●', half: '◐' },
        };
        return icons[this.icon] || icons.star;
    }

    // Value interface
    getValue() {
        return this._value;
    }

    setValue(value) {
        this._value = Math.max(0, Math.min(this.max, parseFloat(value) || 0));
        this._updateDisplay();
    }

    validate() {
        const errors = [];
        if (this.required && this._value === 0) {
            errors.push('Please provide a rating');
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

            .rating-container {
                background: var(--widget-bg, #f8f9fa);
                border: 1px solid var(--widget-border, #dee2e6);
                border-radius: 12px;
                padding: 1.25rem;
            }

            .prompt {
                font-size: 1rem;
                font-weight: 500;
                color: var(--text-color, #212529);
                margin-bottom: 0.75rem;
            }

            .rating-row {
                display: flex;
                align-items: center;
                gap: 1rem;
            }

            .stars {
                display: flex;
                gap: 0.25rem;
            }

            .star {
                font-size: 2rem;
                cursor: pointer;
                transition: transform 0.1s ease;
                user-select: none;
                color: var(--star-empty, #dee2e6);
            }

            .star:hover {
                transform: scale(1.15);
            }

            .star.filled {
                color: var(--star-filled, #ffc107);
            }

            .star.half {
                color: var(--star-filled, #ffc107);
            }

            :host([readonly]) .star,
            :host([disabled]) .star {
                cursor: default;
            }

            :host([readonly]) .star:hover,
            :host([disabled]) .star:hover {
                transform: none;
            }

            :host([disabled]) .stars {
                opacity: 0.5;
            }

            .value-display {
                font-size: 1.25rem;
                font-weight: 600;
                color: var(--text-color, #212529);
                min-width: 50px;
            }

            .value-display .max {
                color: var(--text-muted, #6c757d);
                font-weight: 400;
            }

            .clear-btn {
                padding: 0.25rem 0.5rem;
                border: 1px solid var(--widget-border, #dee2e6);
                border-radius: 4px;
                background: transparent;
                font-size: 0.8rem;
                cursor: pointer;
                color: var(--text-muted, #6c757d);
            }

            .clear-btn:hover {
                background: var(--hover-bg, #e9ecef);
            }
        `;
    }

    render() {
        // Initialize from attribute
        const attrValue = this.getAttribute('value');
        if (attrValue !== null && this._value === 0) {
            this._value = parseFloat(attrValue) || 0;
        }

        const displayValue = this._hoverValue ?? this._value;

        this.shadowRoot.innerHTML = `
            <style>${this._styles || ''}</style>
            <div class="rating-container">
                ${this.prompt ? `<div class="prompt">${this.prompt}</div>` : ''}
                <div class="rating-row">
                    <div class="stars" role="slider" aria-valuemin="0" aria-valuemax="${this.max}" aria-valuenow="${this._value}">
                        ${this._renderStars(displayValue)}
                    </div>
                    ${
                        this.showValue
                            ? `
                        <div class="value-display">
                            ${this._value}<span class="max">/${this.max}</span>
                        </div>
                    `
                            : ''
                    }
                    ${
                        this._value > 0 && !this.readonly && !this.disabled
                            ? `
                        <button class="clear-btn" type="button">Clear</button>
                    `
                            : ''
                    }
                </div>
            </div>
        `;

        this._styles = this.shadowRoot.querySelector('style')?.textContent;
    }

    _renderStars(displayValue) {
        const icons = this._icons;
        let html = '';

        for (let i = 1; i <= this.max; i++) {
            let icon, className;

            if (displayValue >= i) {
                icon = icons.full;
                className = 'star filled';
            } else if (this.allowHalf && displayValue >= i - 0.5) {
                icon = icons.half;
                className = 'star half';
            } else {
                icon = icons.empty;
                className = 'star';
            }

            html += `<span class="${className}" data-value="${i}" data-half="${i - 0.5}">${icon}</span>`;
        }

        return html;
    }

    async loadStyles() {
        this._styles = await this.getStyles();
    }

    bindEvents() {
        if (this.readonly || this.disabled) return;

        const stars = this.shadowRoot.querySelectorAll('.star');

        stars.forEach(star => {
            star.addEventListener('click', e => {
                const rect = star.getBoundingClientRect();
                const isLeftHalf = e.clientX < rect.left + rect.width / 2;
                const value = this.allowHalf && isLeftHalf ? parseFloat(star.dataset.half) : parseFloat(star.dataset.value);
                this._selectRating(value);
            });

            star.addEventListener('mouseenter', e => {
                const rect = star.getBoundingClientRect();
                const isLeftHalf = e.clientX < rect.left + rect.width / 2;
                this._hoverValue = this.allowHalf && isLeftHalf ? parseFloat(star.dataset.half) : parseFloat(star.dataset.value);
                this._updateStars();
            });

            star.addEventListener('mousemove', e => {
                const rect = star.getBoundingClientRect();
                const isLeftHalf = e.clientX < rect.left + rect.width / 2;
                const newHover = this.allowHalf && isLeftHalf ? parseFloat(star.dataset.half) : parseFloat(star.dataset.value);
                if (newHover !== this._hoverValue) {
                    this._hoverValue = newHover;
                    this._updateStars();
                }
            });
        });

        this.shadowRoot.querySelector('.stars')?.addEventListener('mouseleave', () => {
            this._hoverValue = null;
            this._updateStars();
        });

        this.shadowRoot.querySelector('.clear-btn')?.addEventListener('click', () => {
            this._selectRating(0);
        });

        // Keyboard support
        this.shadowRoot.querySelector('.stars')?.addEventListener('keydown', e => {
            const step = this.allowHalf ? 0.5 : 1;
            if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
                e.preventDefault();
                this._selectRating(Math.min(this.max, this._value + step));
            } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
                e.preventDefault();
                this._selectRating(Math.max(0, this._value - step));
            }
        });
    }

    _selectRating(value) {
        this._value = value;
        this.render();
        this.bindEvents();

        this.dispatchEvent(
            new CustomEvent('ax-response', {
                bubbles: true,
                composed: true,
                detail: { value: this._value, widgetId: this.widgetId },
            })
        );
    }

    _updateStars() {
        const displayValue = this._hoverValue ?? this._value;
        const starsContainer = this.shadowRoot.querySelector('.stars');
        if (starsContainer) {
            starsContainer.innerHTML = this._renderStars(displayValue);
            this.bindEvents();
        }
    }

    _updateDisplay() {
        this.render();
        this.bindEvents();
    }
}

customElements.define('ax-rating', AxRating);

export default AxRating;
