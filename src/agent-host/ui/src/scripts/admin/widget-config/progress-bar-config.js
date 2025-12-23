/**
 * Progress Bar Widget Configuration
 *
 * Configuration UI for the 'progress_bar' widget type.
 *
 * Attributes Reference (from ax-progress-bar.js):
 * - value: Current progress value (0-100 for percentage, or numeric)
 * - max: Maximum value (default: 100)
 * - variant: "determinate" | "indeterminate" (default: "determinate")
 * - label: Text label to display
 * - show_value: Show the current value/percentage
 * - size: "sm" | "md" | "lg" (default: "md")
 * - color: "primary" | "success" | "warning" | "danger" | custom hex
 * - striped: Show striped pattern
 * - animated: Animate the stripes
 *
 * @module admin/widget-config/progress-bar-config
 */

import { WidgetConfigBase } from './config-base.js';

export class ProgressBarConfig extends WidgetConfigBase {
    /**
     * Render the progress bar widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        const variantOptions = [
            { value: 'determinate', label: 'Determinate' },
            { value: 'indeterminate', label: 'Indeterminate' },
        ];

        const sizeOptions = [
            { value: 'sm', label: 'Small' },
            { value: 'md', label: 'Medium' },
            { value: 'lg', label: 'Large' },
        ];

        const colorOptions = [
            { value: 'primary', label: 'Primary' },
            { value: 'success', label: 'Success' },
            { value: 'warning', label: 'Warning' },
            { value: 'danger', label: 'Danger' },
        ];

        this.container.innerHTML = `
            <div class="widget-config widget-config-progress-bar">
                <div class="row g-2">
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Initial Value
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Initial progress value (0-100 or up to max)."></i>
                        </label>
                        ${this.createNumberInput('config-value', config.value ?? content.initial_value ?? 0, '0', { min: 0 })}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Max Value
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Maximum progress value (default: 100)."></i>
                        </label>
                        ${this.createNumberInput('config-max', config.max ?? 100, '100', { min: 1 })}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Variant
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Determinate shows actual progress, indeterminate shows loading animation."></i>
                        </label>
                        ${this.createSelect('config-variant', variantOptions, config.variant || 'determinate')}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Size
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Height of the progress bar."></i>
                        </label>
                        ${this.createSelect('config-size', sizeOptions, config.size || 'md')}
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Label
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Text label to display above the progress bar."></i>
                        </label>
                        ${this.createTextInput('config-label', config.label || '', 'Optional label')}
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Color
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Color theme for the progress bar."></i>
                        </label>
                        ${this.createSelect('config-color', colorOptions, config.color || 'primary')}
                    </div>
                    <div class="col-md-4">
                        <div class="mt-4">
                            ${this.createSwitch('config-show-value', `${this.uid}-show-value`, 'Show Value', 'Display the current progress percentage.', config.show_value ?? config.showValue ?? true)}
                        </div>
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-md-6">
                        ${this.createSwitch('config-striped', `${this.uid}-striped`, 'Striped', 'Show striped pattern on the progress bar.', config.striped ?? false)}
                    </div>
                    <div class="col-md-6">
                        ${this.createSwitch('config-animated', `${this.uid}-animated`, 'Animated', 'Animate the stripes (requires striped to be enabled).', config.animated ?? false)}
                    </div>
                </div>
            </div>
        `;

        this.initTooltips();
    }

    /**
     * Get configuration values matching widget attributes
     * @returns {Object} Widget configuration
     */
    getValue() {
        const config = {};

        const value = this.getNumericValue('config-value');
        if (value !== null) {
            config.value = value;
        }

        const max = this.getNumericValue('config-max', 100);
        if (max !== 100) {
            config.max = max;
        }

        const variant = this.getInputValue('config-variant', 'determinate');
        if (variant !== 'determinate') {
            config.variant = variant;
        }

        const size = this.getInputValue('config-size', 'md');
        if (size !== 'md') {
            config.size = size;
        }

        const label = this.getInputValue('config-label');
        if (label) {
            config.label = label;
        }

        const color = this.getInputValue('config-color', 'primary');
        if (color !== 'primary') {
            config.color = color;
        }

        const showValue = this.getChecked('config-show-value');
        if (!showValue) {
            config.show_value = false;
        }

        const striped = this.getChecked('config-striped');
        if (striped) {
            config.striped = true;
        }

        const animated = this.getChecked('config-animated');
        if (animated) {
            config.animated = true;
        }

        return config;
    }

    /**
     * Get initial value
     * @returns {number|null} Initial progress value
     */
    getInitialValue() {
        return this.getNumericValue('config-value');
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const value = this.getNumericValue('config-value', 0);
        const max = this.getNumericValue('config-max', 100);

        if (value < 0) {
            errors.push('Value must be greater than or equal to 0');
        }

        if (max <= 0) {
            errors.push('Max value must be greater than 0');
        }

        if (value > max) {
            errors.push('Value cannot exceed max value');
        }

        return { valid: errors.length === 0, errors };
    }
}
