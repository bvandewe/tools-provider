/**
 * Dropdown Select Widget Component
 * Renders a dropdown/select with single or multi-select support.
 *
 * Attributes:
 * - prompt: Label text
 * - options: JSON array of {id, label, description?, disabled?, group?}
 * - placeholder: Placeholder text when nothing selected
 * - multiple: Allow multiple selections
 * - searchable: Enable search/filter
 * - disabled: Disable the dropdown
 *
 * Events:
 * - ax-response: Fired when selection changes
 *   Detail: { value: string|string[], label: string|string[] }
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

class AxDropdown extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'prompt', 'options', 'placeholder', 'multiple', 'searchable'];
    }

    constructor() {
        super();
        this._selectedIds = new Set();
        this._isOpen = false;
        this._searchTerm = '';
    }

    // Attribute getters
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

    get placeholder() {
        return this.getAttribute('placeholder') || 'Select...';
    }

    get multiple() {
        return this.hasAttribute('multiple');
    }

    get searchable() {
        return this.hasAttribute('searchable');
    }

    get _filteredOptions() {
        if (!this._searchTerm) return this.options;
        const term = this._searchTerm.toLowerCase();
        return this.options.filter(opt => (opt.label || opt.id).toLowerCase().includes(term));
    }

    // Value interface
    getValue() {
        const ids = Array.from(this._selectedIds);
        return this.multiple ? ids : ids[0] || null;
    }

    setValue(value) {
        if (Array.isArray(value)) {
            this._selectedIds = new Set(value);
        } else if (value) {
            this._selectedIds = new Set([value]);
        } else {
            this._selectedIds.clear();
        }
        this._updateDisplay();
    }

    validate() {
        const errors = [];
        if (this.required && this._selectedIds.size === 0) {
            errors.push('Please select an option');
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

            .dropdown-container {
                background: var(--widget-bg);
                border: 1px solid var(--widget-border);
                border-radius: 12px;
                padding: 1.25rem;
            }

            .prompt {
                font-size: 1rem;
                font-weight: 500;
                color: var(--text-color);
                margin-bottom: 0.75rem;
            }

            .select-trigger {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0.75rem 1rem;
                border: 1px solid var(--input-border);
                border-radius: 8px;
                background: var(--input-bg);
                cursor: pointer;
                min-height: 44px;
            }

            .select-trigger:hover:not(.disabled) {
                border-color: var(--primary-color);
            }

            .select-trigger.open {
                border-color: var(--primary-color);
                box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.15);
            }

            .select-trigger.disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }

            .selected-text {
                flex: 1;
                color: var(--text-color);
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .selected-text.placeholder {
                color: var(--text-muted);
            }

            .arrow {
                font-size: 0.8rem;
                transition: transform 0.2s ease;
                color: var(--text-muted);
            }

            .arrow.open {
                transform: rotate(180deg);
            }

            .dropdown-menu {
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                margin-top: 4px;
                background: var(--menu-bg);
                border: 1px solid var(--menu-border);
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                max-height: 280px;
                overflow-y: auto;
                z-index: 100;
            }

            .search-input {
                width: 100%;
                padding: 0.75rem 1rem;
                border: none;
                border-bottom: 1px solid var(--menu-border);
                background: var(--menu-bg);
                color: var(--text-color);
                font-size: 0.95rem;
                outline: none;
            }

            .search-input::placeholder {
                color: var(--text-muted);
            }

            .option-item {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 0.75rem 1rem;
                cursor: pointer;
                transition: background 0.1s ease;
                color: var(--text-color);
            }

            .option-item:hover:not(.disabled) {
                background: var(--option-hover);
            }

            .option-item.selected {
                background: var(--option-selected);
            }

            .option-item.disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            .option-checkbox {
                width: 16px;
                height: 16px;
                accent-color: var(--primary-color);
            }

            .option-label {
                flex: 1;
            }

            .option-check {
                color: var(--primary-color);
            }

            .no-results {
                padding: 1rem;
                text-align: center;
                color: var(--text-muted);
            }

            .select-wrapper {
                position: relative;
            }

            .selected-tags {
                display: flex;
                flex-wrap: wrap;
                gap: 0.25rem;
            }

            .tag {
                display: inline-flex;
                align-items: center;
                gap: 0.25rem;
                padding: 0.25rem 0.5rem;
                background: var(--tag-bg);
                border-radius: 4px;
                font-size: 0.85rem;
                color: var(--text-color);
            }

            .tag-remove {
                cursor: pointer;
                font-size: 1rem;
                line-height: 1;
            }
        `;
    }

    render() {
        const selectedLabels = this._getSelectedLabels();
        const displayText = selectedLabels.length > 0 ? (this.multiple ? '' : selectedLabels[0]) : '';

        this.shadowRoot.innerHTML = `
            <style>${this._styles || ''}</style>
            <div class="dropdown-container">
                ${this.prompt ? `<div class="prompt">${this.prompt}</div>` : ''}
                <div class="select-wrapper">
                    <div class="select-trigger ${this._isOpen ? 'open' : ''} ${this.disabled ? 'disabled' : ''}"
                         role="combobox" aria-expanded="${this._isOpen}" aria-haspopup="listbox" tabindex="0">
                        ${
                            this.multiple && selectedLabels.length > 0
                                ? this._renderTags(selectedLabels)
                                : `
                            <span class="selected-text ${!displayText ? 'placeholder' : ''}">
                                ${displayText || this.placeholder}
                            </span>
                        `
                        }
                        <span class="arrow ${this._isOpen ? 'open' : ''}">▼</span>
                    </div>
                    ${this._isOpen ? this._renderMenu() : ''}
                </div>
            </div>
        `;

        this._styles = this.shadowRoot.querySelector('style')?.textContent;
    }

    _renderTags(labels) {
        return `
            <div class="selected-tags">
                ${labels
                    .map(
                        (label, i) => `
                    <span class="tag">
                        ${label}
                        <span class="tag-remove" data-index="${i}">×</span>
                    </span>
                `
                    )
                    .join('')}
            </div>
        `;
    }

    _renderMenu() {
        const options = this._filteredOptions;
        return `
            <div class="dropdown-menu" role="listbox">
                ${
                    this.searchable
                        ? `
                    <input type="text" class="search-input"
                           placeholder="Search..."
                           value="${this._searchTerm}"/>
                `
                        : ''
                }
                ${
                    options.length === 0
                        ? `
                    <div class="no-results">No options found</div>
                `
                        : options.map(opt => this._renderOption(opt)).join('')
                }
            </div>
        `;
    }

    _renderOption(option) {
        const id = option.id || option.label;
        const isSelected = this._selectedIds.has(id);
        return `
            <div class="option-item ${isSelected ? 'selected' : ''} ${option.disabled ? 'disabled' : ''}"
                 data-id="${id}" role="option" aria-selected="${isSelected}">
                ${this.multiple ? `<input type="checkbox" class="option-checkbox" ${isSelected ? 'checked' : ''} ${option.disabled ? 'disabled' : ''}/>` : ''}
                <span class="option-label">${option.label || id}</span>
                ${!this.multiple && isSelected ? '<span class="option-check">✓</span>' : ''}
            </div>
        `;
    }

    _getSelectedLabels() {
        return Array.from(this._selectedIds).map(id => {
            const opt = this.options.find(o => (o.id || o.label) === id);
            return opt?.label || id;
        });
    }

    async loadStyles() {
        this._styles = await this.getStyles();
    }

    bindEvents() {
        const trigger = this.shadowRoot.querySelector('.select-trigger');
        const searchInput = this.shadowRoot.querySelector('.search-input');

        trigger?.addEventListener('click', () => {
            if (!this.disabled) this._toggleOpen();
        });

        trigger?.addEventListener('keydown', e => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                if (!this.disabled) this._toggleOpen();
            }
        });

        searchInput?.addEventListener('input', e => {
            this._searchTerm = e.target.value;
            this._renderMenuOnly();
        });

        this.shadowRoot.querySelectorAll('.option-item').forEach(opt => {
            opt.addEventListener('click', () => {
                if (!opt.classList.contains('disabled')) {
                    this._selectOption(opt.dataset.id);
                }
            });
        });

        this.shadowRoot.querySelectorAll('.tag-remove').forEach(btn => {
            btn.addEventListener('click', e => {
                e.stopPropagation();
                const labels = this._getSelectedLabels();
                const idx = parseInt(btn.dataset.index);
                const ids = Array.from(this._selectedIds);
                this._selectedIds.delete(ids[idx]);
                this._updateAndDispatch();
            });
        });

        // Close on outside click
        document.addEventListener('click', this._handleOutsideClick);
    }

    _handleOutsideClick = e => {
        if (!this.contains(e.target) && this._isOpen) {
            this._isOpen = false;
            this.render();
            this.bindEvents();
        }
    };

    cleanup() {
        document.removeEventListener('click', this._handleOutsideClick);
    }

    _toggleOpen() {
        this._isOpen = !this._isOpen;
        this._searchTerm = '';
        this.render();
        this.bindEvents();
        if (this._isOpen && this.searchable) {
            setTimeout(() => this.shadowRoot.querySelector('.search-input')?.focus(), 0);
        }
    }

    _selectOption(id) {
        this.clearError(); // Clear validation error on interaction

        if (this.multiple) {
            if (this._selectedIds.has(id)) {
                this._selectedIds.delete(id);
            } else {
                this._selectedIds.add(id);
            }
        } else {
            this._selectedIds.clear();
            this._selectedIds.add(id);
            this._isOpen = false;
        }
        this._updateAndDispatch();
    }

    _updateAndDispatch() {
        this.render();
        this.bindEvents();

        const detail = {
            value: this.getValue(),
            labels: this._getSelectedLabels(),
            widgetId: this.widgetId,
        };

        // Emit ax-selection for confirmation mode (captures current selection)
        this.dispatchEvent(
            new CustomEvent('ax-selection', {
                bubbles: true,
                composed: true,
                detail: detail,
            })
        );

        // Emit ax-response for auto-submit mode
        this.dispatchEvent(
            new CustomEvent('ax-response', {
                bubbles: true,
                composed: true,
                detail: detail,
            })
        );
    }

    _renderMenuOnly() {
        const menu = this.shadowRoot.querySelector('.dropdown-menu');
        if (menu) {
            const options = this._filteredOptions;
            const optionsHtml = options.length === 0 ? '<div class="no-results">No options found</div>' : options.map(opt => this._renderOption(opt)).join('');

            const searchHtml = this.searchable
                ? `
                <input type="text" class="search-input" placeholder="Search..." value="${this._searchTerm}"/>
            `
                : '';

            menu.innerHTML = searchHtml + optionsHtml;
            this.bindEvents();
        }
    }

    _updateDisplay() {
        this.render();
        this.bindEvents();
    }
}

customElements.define('ax-dropdown', AxDropdown);

export default AxDropdown;
