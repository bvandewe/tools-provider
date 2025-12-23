/**
 * Submit Button Widget Configuration
 *
 * Configuration UI for the 'submit_button' widget type.
 *
 * Attributes Reference (from ax-submit-button.js):
 * - label: Button text (default: "Submit")
 * - variant: "primary" | "secondary" | "success" | "danger" | "outline" (default: "primary")
 * - size: "sm" | "md" | "lg" (default: "md")
 * - icon: Optional icon name (bootstrap-icons)
 * - confirm: Confirmation message before action
 * - countdown: Countdown seconds before auto-submit
 *
 * @module admin/widget-config/submit-button-config
 */

import { WidgetConfigBase } from './config-base.js';

export class SubmitButtonConfig extends WidgetConfigBase {
    /**
     * Render the submit button widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        const variantOptions = [
            { value: 'primary', label: 'Primary' },
            { value: 'secondary', label: 'Secondary' },
            { value: 'success', label: 'Success' },
            { value: 'danger', label: 'Danger' },
            { value: 'outline', label: 'Outline' },
        ];

        const sizeOptions = [
            { value: 'sm', label: 'Small' },
            { value: 'md', label: 'Medium' },
            { value: 'lg', label: 'Large' },
        ];

        this.container.innerHTML = `
            <div class="widget-config widget-config-submit-button">
                <div class="row g-2">
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Button Label<span class="text-danger">*</span>
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Text displayed on the button."></i>
                        </label>
                        ${this.createTextInput('config-label', config.label || 'Submit', 'Submit')}
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Variant
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Button color/style variant."></i>
                        </label>
                        ${this.createSelect('config-variant', variantOptions, config.variant || 'primary')}
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Size
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Button size."></i>
                        </label>
                        ${this.createSelect('config-size', sizeOptions, config.size || 'md')}
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Icon
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Bootstrap icon name (e.g., 'send', 'check', 'arrow-right')."></i>
                        </label>
                        ${this.createTextInput('config-icon', config.icon || '', 'e.g., send')}
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Confirmation Message
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="If set, shows a confirmation dialog before submitting."></i>
                        </label>
                        ${this.createTextInput('config-confirm', config.confirm || '', 'Are you sure?')}
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Auto-Submit Countdown
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="If set, button auto-submits after this many seconds."></i>
                        </label>
                        ${this.createNumberInput('config-countdown', config.countdown ?? '', 'Optional', { min: 1 })}
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

        const label = this.getInputValue('config-label', 'Submit');
        if (label !== 'Submit') {
            config.label = label;
        }

        const variant = this.getInputValue('config-variant', 'primary');
        if (variant !== 'primary') {
            config.variant = variant;
        }

        const size = this.getInputValue('config-size', 'md');
        if (size !== 'md') {
            config.size = size;
        }

        const icon = this.getInputValue('config-icon');
        if (icon) {
            config.icon = icon;
        }

        const confirm = this.getInputValue('config-confirm');
        if (confirm) {
            config.confirm = confirm;
        }

        const countdown = this.getNumericValue('config-countdown');
        if (countdown !== null) {
            config.countdown = countdown;
        }

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const label = this.getInputValue('config-label');
        if (!label || label.trim() === '') {
            errors.push('Button label is required');
        }

        const countdown = this.getNumericValue('config-countdown');
        if (countdown !== null && countdown <= 0) {
            errors.push('Countdown must be greater than 0');
        }

        return { valid: errors.length === 0, errors };
    }
}
