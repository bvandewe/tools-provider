/**
 * Checkbox Group Widget Component
 * Renders a group of checkboxes for multi-select options.
 *
 * Attributes:
 * - prompt: The question or label to display
 * - options: JSON array of {id, label, description?, disabled?}
 * - min-selections: Minimum required selections
 * - max-selections: Maximum allowed selections
 * - layout: "vertical" | "horizontal" | "grid"
 * - disabled: Disable all checkboxes
 *
 * Events:
 * - ax-response: Fired when selections change
 *   Detail: { selections: string[], indices: number[] }
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

class AxCheckboxGroup extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'prompt', 'options', 'min-selections', 'max-selections', 'layout'];
    }

    constructor() {
        super();
        this._selectedIds = new Set();
    }

    // Attribute getters
    get prompt() {
        return this.getAttribute('prompt') || '';
    }

    get options() {
        try {
            const raw = JSON.parse(this.getAttribute('options') || '[]');
            // Normalize: handle both string arrays and object arrays
            return raw.map((opt, idx) => {
                if (typeof opt === 'string') {
                    return { id: opt, label: opt };
                }
                // Ensure id exists
                return { id: opt.id || opt.value || `option-${idx}`, label: opt.label || opt.id || opt.value, ...opt };
            });
        } catch {
            return [];
        }
    }

    get minSelections() {
        return parseInt(this.getAttribute('min-selections')) || 0;
    }

    get maxSelections() {
        return parseInt(this.getAttribute('max-selections')) || Infinity;
    }

    get layout() {
        return this.getAttribute('layout') || 'vertical';
    }

    // Value interface
    getValue() {
        return Array.from(this._selectedIds);
    }

    setValue(value) {
        this._selectedIds = new Set(Array.isArray(value) ? value : []);
        this._updateCheckboxes();
    }

    validate() {
        const count = this._selectedIds.size;
        const errors = [];

        if (count < this.minSelections) {
            errors.push(`Select at least ${this.minSelections} option(s)`);
        }
        if (count > this.maxSelections) {
            errors.push(`Select at most ${this.maxSelections} option(s)`);
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

            .prompt {
                font-size: 1rem;
                font-weight: 500;
                color: var(--text-color);
                margin-bottom: 1rem;
                line-height: 1.5;
            }

            .options-container {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }

            .options-container.horizontal {
                flex-direction: row;
                flex-wrap: wrap;
            }

            .options-container.grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 0.5rem;
            }

            .option-item {
                display: flex;
                align-items: flex-start;
                gap: 0.75rem;
                padding: 0.75rem;
                border: 1px solid var(--widget-border);
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.15s ease;
                background: var(--input-bg);
            }

            .option-item:hover:not(.disabled) {
                border-color: var(--primary-color, #0d6efd);
                background: var(--hover-bg);
            }

            .option-item.selected {
                border-color: var(--primary-color, #0d6efd);
                background: var(--option-selected);
            }

            .option-item.disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            .checkbox-input {
                width: 18px;
                height: 18px;
                margin: 0;
                cursor: pointer;
                accent-color: var(--primary-color, #0d6efd);
            }

            .checkbox-input:disabled {
                cursor: not-allowed;
            }

            .option-content {
                flex: 1;
            }

            .option-label {
                font-weight: 500;
                color: var(--text-color);
            }

            .option-description {
                font-size: 0.85rem;
                color: var(--text-muted);
                margin-top: 0.25rem;
            }

            .selection-info {
                font-size: 0.85rem;
                color: var(--text-muted);
                margin-top: 0.75rem;
            }

            :host([disabled]) .widget-container {
                opacity: 0.6;
            }
        `;
    }

    render() {
        const options = this.options;
        const layoutClass = this.layout;

        this.shadowRoot.innerHTML = `
            <style>${this._styles || ''}</style>
            <div class="widget-container">
                ${this.prompt ? `<div class="prompt">${this.prompt}</div>` : ''}
                <div class="options-container ${layoutClass}" role="group" aria-label="${this.prompt}">
                    ${options.map((opt, idx) => this._renderOption(opt, idx)).join('')}
                </div>
                ${this._renderSelectionInfo()}
            </div>
        `;

        this._styles = this.shadowRoot.querySelector('style')?.textContent;
    }

    _renderOption(option, index) {
        const id = option.id || `option-${index}`;
        const isSelected = this._selectedIds.has(id);
        const isDisabled = this.disabled || option.disabled;
        const atMax = this._selectedIds.size >= this.maxSelections && !isSelected;

        return `
            <label class="option-item ${isSelected ? 'selected' : ''} ${isDisabled || atMax ? 'disabled' : ''}"
                   data-id="${id}" data-index="${index}">
                <input type="checkbox"
                       class="checkbox-input"
                       value="${id}"
                       ${isSelected ? 'checked' : ''}
                       ${isDisabled || atMax ? 'disabled' : ''}
                       aria-describedby="${option.description ? `desc-${id}` : ''}"/>
                <div class="option-content">
                    <div class="option-label">${option.label || id}</div>
                    ${option.description ? `<div class="option-description" id="desc-${id}">${option.description}</div>` : ''}
                </div>
            </label>
        `;
    }

    _renderSelectionInfo() {
        if (this.minSelections === 0 && this.maxSelections === Infinity) {
            return '';
        }
        const count = this._selectedIds.size;
        let info = `${count} selected`;
        if (this.minSelections > 0) {
            info += ` (min: ${this.minSelections})`;
        }
        if (this.maxSelections !== Infinity) {
            info += ` (max: ${this.maxSelections})`;
        }
        return `<div class="selection-info">${info}</div>`;
    }

    async loadStyles() {
        this._styles = await this.getStyles();
    }

    bindEvents() {
        this.shadowRoot.addEventListener('change', e => {
            if (e.target.classList.contains('checkbox-input')) {
                this._handleCheckboxChange(e.target);
            }
        });
    }

    _handleCheckboxChange(checkbox) {
        const label = checkbox.closest('.option-item');
        const id = label.dataset.id;

        this.clearError(); // Clear validation error on interaction

        if (checkbox.checked) {
            this._selectedIds.add(id);
        } else {
            this._selectedIds.delete(id);
        }

        this.render();
        this.bindEvents();
        this.dispatchResponse();
    }

    _updateCheckboxes() {
        const checkboxes = this.shadowRoot.querySelectorAll('.checkbox-input');
        checkboxes.forEach(cb => {
            const label = cb.closest('.option-item');
            const id = label.dataset.id;
            cb.checked = this._selectedIds.has(id);
        });
    }

    dispatchResponse() {
        const selections = Array.from(this._selectedIds);
        const indices = selections.map(id => {
            const opt = this.options.findIndex(o => (o.id || `option-${this.options.indexOf(o)}`) === id);
            return opt;
        });

        this.dispatchEvent(
            new CustomEvent('ax-response', {
                bubbles: true,
                composed: true,
                detail: { selections, indices, widgetId: this.widgetId },
            })
        );
    }
}

customElements.define('ax-checkbox-group', AxCheckboxGroup);

export default AxCheckboxGroup;
