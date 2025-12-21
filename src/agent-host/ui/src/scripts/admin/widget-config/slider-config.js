/**
 * Slider Widget Configuration
 *
 * Configuration UI for the 'slider' widget type.
 *
 * Python Schema Reference (SliderConfig):
 * - min: float (required)
 * - max: float (required)
 * - step: float (required)
 * - default_value: float | None (alias: defaultValue)
 * - show_value: bool | None (alias: showValue)
 * - labels: dict[str, str] | None
 *
 * @module admin/widget-config/slider-config
 */

import { WidgetConfigBase } from './config-base.js';

export class SliderConfig extends WidgetConfigBase {
    /**
     * Render the slider widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object (includes initial_value)
     */
    render(config = {}, content = {}) {
        // Support both snake_case and camelCase
        const labels = config.labels || {};
        const minLabel = labels.min || config.min_label || '';
        const maxLabel = labels.max || config.max_label || '';

        this.container.innerHTML = `
            <div class="widget-config widget-config-slider">
                <div class="row g-2">
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Min Value
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Minimum value on the slider scale."></i>
                        </label>
                        ${this.createNumberInput('config-min', config.min ?? 0, '0')}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Max Value
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Maximum value on the slider scale."></i>
                        </label>
                        ${this.createNumberInput('config-max', config.max ?? 100, '100')}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Step
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Increment step when moving the slider."></i>
                        </label>
                        ${this.createNumberInput('config-step', config.step ?? 1, '1', { step: 'any', min: 0.01 })}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Default Value
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Pre-selected value when slider first appears."></i>
                        </label>
                        ${this.createNumberInput('config-default-value', config.default_value ?? config.defaultValue ?? content.initial_value ?? '', 'Optional')}
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Min Label
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Label displayed at the minimum end of the slider."></i>
                        </label>
                        ${this.createTextInput('config-min-label', minLabel, 'e.g., Not at all')}
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Max Label
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Label displayed at the maximum end of the slider."></i>
                        </label>
                        ${this.createTextInput('config-max-label', maxLabel, 'e.g., Very much')}
                    </div>
                    <div class="col-md-4">
                        <div class="mt-4">
                            ${this.createSwitch(
                                'config-show-value',
                                `${this.uid}-show-value`,
                                'Show Value',
                                'Display the current numeric value next to the slider.',
                                config.show_value ?? config.showValue ?? true
                            )}
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

        const min = this.getNumericValue('config-min', 0);
        const max = this.getNumericValue('config-max', 100);
        const step = this.getNumericValue('config-step', 1);

        config.min = min;
        config.max = max;
        config.step = step;

        const defaultValue = this.getNumericValue('config-default-value');
        if (defaultValue !== null) {
            config.default_value = defaultValue;
        }

        const showValue = this.getChecked('config-show-value');
        if (!showValue) {
            config.show_value = false;
        }

        // Build labels dict
        const minLabel = this.getInputValue('config-min-label');
        const maxLabel = this.getInputValue('config-max-label');
        if (minLabel || maxLabel) {
            config.labels = {};
            if (minLabel) config.labels.min = minLabel;
            if (maxLabel) config.labels.max = maxLabel;
        }

        return config;
    }

    /**
     * Get initial value
     * @returns {number|null} Default value for the slider
     */
    getInitialValue() {
        return this.getNumericValue('config-default-value');
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const min = this.getNumericValue('config-min', 0);
        const max = this.getNumericValue('config-max', 100);
        const step = this.getNumericValue('config-step', 1);

        if (min >= max) {
            errors.push('Min value must be less than max value');
        }

        if (step <= 0) {
            errors.push('Step must be greater than 0');
        }

        if (step > max - min) {
            errors.push('Step cannot be larger than the range (max - min)');
        }

        const defaultValue = this.getNumericValue('config-default-value');
        if (defaultValue !== null) {
            if (defaultValue < min || defaultValue > max) {
                errors.push('Default value must be within the min/max range');
            }
        }

        return { valid: errors.length === 0, errors };
    }
}
