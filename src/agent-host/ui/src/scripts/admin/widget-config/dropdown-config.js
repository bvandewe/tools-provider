/**
 * Dropdown Widget Configuration
 *
 * Configuration UI for the 'dropdown' widget type.
 *
 * Python Schema Reference (DropdownConfig):
 * - options: list[DropdownOption] (required) - each has value, label, icon?, disabled?, group?
 * - groups: list[DropdownGroup] | None - each has id, label
 * - multiple: bool = False
 * - searchable: bool | None
 * - clearable: bool | None
 * - placeholder: str | None
 * - no_options_message: str | None (alias: noOptionsMessage)
 * - max_selections: int | None (alias: maxSelections)
 * - min_selections: int | None (alias: minSelections)
 * - creatable: bool | None
 * - default_value: str | list[str] | None (alias: defaultValue)
 * - disabled: bool | None
 * - loading: bool | None
 * - virtualized: bool | None
 * - max_dropdown_height: int | None (alias: maxDropdownHeight)
 *
 * @module admin/widget-config/dropdown-config
 */

import { WidgetConfigBase } from './config-base.js';

export class DropdownConfig extends WidgetConfigBase {
    /**
     * Render the dropdown widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        // Convert options array to text format for editing
        const options = config.options || [];
        const optionsText = options
            .map(opt => {
                if (typeof opt === 'string') return opt;
                return `${opt.value}|${opt.label}`;
            })
            .join('\n');

        this.container.innerHTML = `
            <div class="widget-config widget-config-dropdown">
                <div class="row g-2">
                    <div class="col-md-8">
                        <label class="form-label small mb-0">
                            Options
                            <span class="text-danger">*</span>
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="One option per line. Format: value|label (e.g., 'us|United States'). If only one value provided, it's used for both."></i>
                        </label>
                        ${this.createTextarea('config-options', optionsText, 'value1|Label 1\nvalue2|Label 2\nvalue3|Label 3', 4)}
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Placeholder
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Text shown when no option is selected."></i>
                        </label>
                        ${this.createTextInput('config-placeholder', config.placeholder, 'Select an option...')}
                        <div class="mt-2">
                            ${this.createSwitch('config-multiple', `${this.uid}-multiple`, 'Allow Multiple', 'Allow selecting multiple options.', config.multiple || false)}
                        </div>
                        <div class="mt-2">
                            ${this.createSwitch('config-searchable', `${this.uid}-searchable`, 'Searchable', 'Allow typing to filter options.', config.searchable || false)}
                        </div>
                    </div>
                </div>

                ${this.createCollapsibleSection(
                    `${this.uid}-advanced`,
                    'Advanced Options',
                    `
                    <div class="row g-2">
                        <div class="col-md-3">
                            ${this.createSwitch('config-clearable', `${this.uid}-clearable`, 'Clearable', 'Show a clear button to remove selection.', config.clearable || false)}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch('config-creatable', `${this.uid}-creatable`, 'Creatable', 'Allow creating new options by typing.', config.creatable || false)}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch('config-disabled', `${this.uid}-disabled`, 'Disabled', 'Disable the dropdown entirely.', config.disabled || false)}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch('config-virtualized', `${this.uid}-virtualized`, 'Virtualized', 'Use virtual scrolling for large option lists.', config.virtualized || false)}
                        </div>
                    </div>
                    <div class="row g-2 mt-2">
                        <div class="col-md-3">
                            <label class="form-label small mb-0">
                                Min Selections
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="Minimum selections required (for multiple mode)."></i>
                            </label>
                            ${this.createNumberInput('config-min-selections', config.min_selections ?? config.minSelections ?? '', '0', { min: 0 })}
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small mb-0">
                                Max Selections
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="Maximum selections allowed (for multiple mode)."></i>
                            </label>
                            ${this.createNumberInput('config-max-selections', config.max_selections ?? config.maxSelections ?? '', 'Unlimited', { min: 1 })}
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small mb-0">
                                Max Height (px)
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="Maximum dropdown height in pixels."></i>
                            </label>
                            ${this.createNumberInput('config-max-height', config.max_dropdown_height ?? config.maxDropdownHeight ?? '', '300', { min: 100 })}
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small mb-0">
                                Default Value
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="Pre-selected value. Must match an option value."></i>
                            </label>
                            ${this.createTextInput('config-default-value', config.default_value ?? config.defaultValue ?? '', 'Optional')}
                        </div>
                    </div>
                    <div class="row g-2 mt-2">
                        <div class="col-12">
                            <label class="form-label small mb-0">
                                No Options Message
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="Message shown when no options match the search."></i>
                            </label>
                            ${this.createTextInput('config-no-options-message', config.no_options_message ?? config.noOptionsMessage ?? '', 'No options available')}
                        </div>
                    </div>
                `
                )}
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

        // Parse options from textarea
        const optionsText = this.getInputValue('config-options', '');
        const options = optionsText
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map(line => {
                const parts = line.split('|');
                const value = parts[0].trim();
                const label = parts.length > 1 ? parts[1].trim() : value;
                return { value, label };
            });

        config.options = options;

        const placeholder = this.getInputValue('config-placeholder');
        if (placeholder) config.placeholder = placeholder;

        const multiple = this.getChecked('config-multiple');
        if (multiple) config.multiple = true;

        const searchable = this.getChecked('config-searchable');
        if (searchable) config.searchable = true;

        const clearable = this.getChecked('config-clearable');
        if (clearable) config.clearable = true;

        const creatable = this.getChecked('config-creatable');
        if (creatable) config.creatable = true;

        const disabled = this.getChecked('config-disabled');
        if (disabled) config.disabled = true;

        const virtualized = this.getChecked('config-virtualized');
        if (virtualized) config.virtualized = true;

        const minSelections = this.getIntValue('config-min-selections');
        if (minSelections !== null) config.min_selections = minSelections;

        const maxSelections = this.getIntValue('config-max-selections');
        if (maxSelections !== null) config.max_selections = maxSelections;

        const maxDropdownHeight = this.getIntValue('config-max-height');
        if (maxDropdownHeight !== null) config.max_dropdown_height = maxDropdownHeight;

        const defaultValue = this.getInputValue('config-default-value');
        if (defaultValue) config.default_value = defaultValue;

        const noOptionsMessage = this.getInputValue('config-no-options-message');
        if (noOptionsMessage) config.no_options_message = noOptionsMessage;

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const optionsText = this.getInputValue('config-options', '');
        const options = optionsText.split('\n').filter(l => l.trim().length > 0);

        if (options.length === 0) {
            errors.push('At least one option is required');
        }

        const minSelections = this.getIntValue('config-min-selections');
        const maxSelections = this.getIntValue('config-max-selections');

        if (minSelections !== null && maxSelections !== null && minSelections > maxSelections) {
            errors.push('Min selections cannot exceed max selections');
        }

        if (minSelections !== null && minSelections > options.length) {
            errors.push('Min selections cannot exceed total options');
        }

        return { valid: errors.length === 0, errors };
    }
}
