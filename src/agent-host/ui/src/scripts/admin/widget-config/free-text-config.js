/**
 * Free Text Widget Configuration
 *
 * Configuration UI for the 'free_text' widget type.
 *
 * Python Schema Reference (FreeTextConfig):
 * - placeholder: str | None
 * - min_length: int | None (alias: minLength)
 * - max_length: int | None (alias: maxLength)
 * - multiline: bool = False
 * - rows: int | None
 *
 * @module admin/widget-config/free-text-config
 */

import { WidgetConfigBase } from './config-base.js';

export class FreeTextConfig extends WidgetConfigBase {
    /**
     * Render the free text widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        this.container.innerHTML = `
            <div class="widget-config widget-config-free-text">
                <div class="row g-2">
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Placeholder
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Placeholder text shown in the input field."></i>
                        </label>
                        ${this.createTextInput('config-placeholder', config.placeholder, 'Enter placeholder text...')}
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small mb-0">
                            Min Length
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Minimum required character count."></i>
                        </label>
                        ${this.createNumberInput('config-min-length', config.min_length ?? config.minLength ?? '', '0', { min: 0 })}
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small mb-0">
                            Max Length
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Maximum allowed character count."></i>
                        </label>
                        ${this.createNumberInput('config-max-length', config.max_length ?? config.maxLength ?? '', 'None', { min: 1 })}
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small mb-0">
                            Rows
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Number of visible text rows (height). Only applies when multiline is enabled."></i>
                        </label>
                        ${this.createNumberInput('config-rows', config.rows ?? 3, '3', { min: 1, max: 20 })}
                    </div>
                    <div class="col-md-2">
                        <div class="mt-4">
                            ${this.createSwitch('config-multiline', `${this.uid}-multiline`, 'Multiline', 'If enabled, shows a textarea for multi-line input.', config.multiline !== false)}
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.initTooltips();
    }

    /**
     * Get configuration values matching Python schema
     * @returns {Object} Widget configuration
     */
    getValue() {
        const config = {};

        const placeholder = this.getInputValue('config-placeholder');
        if (placeholder) config.placeholder = placeholder;

        const minLength = this.getIntValue('config-min-length');
        if (minLength !== null) config.min_length = minLength;

        const maxLength = this.getIntValue('config-max-length');
        if (maxLength !== null) config.max_length = maxLength;

        const multiline = this.getChecked('config-multiline');
        config.multiline = multiline;

        if (multiline) {
            const rows = this.getIntValue('config-rows');
            if (rows !== null) config.rows = rows;
        }

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const minLength = this.getIntValue('config-min-length');
        const maxLength = this.getIntValue('config-max-length');

        if (minLength !== null && maxLength !== null && minLength > maxLength) {
            errors.push('Min length cannot be greater than max length');
        }

        if (minLength !== null && minLength < 0) {
            errors.push('Min length cannot be negative');
        }

        return { valid: errors.length === 0, errors };
    }
}
