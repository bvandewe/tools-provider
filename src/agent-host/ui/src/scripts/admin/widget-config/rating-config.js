/**
 * Rating Widget Configuration
 *
 * Configuration UI for the 'rating' widget type.
 *
 * Python Schema Reference (RatingConfig):
 * - style: RatingStyle = "stars" ("stars" | "numeric" | "emoji" | "thumbs")
 * - max_rating: int (required, alias: maxRating)
 * - allow_half: bool | None (alias: allowHalf)
 * - default_value: float | None (alias: defaultValue)
 * - show_value: bool | None (alias: showValue)
 * - show_labels: bool | None (alias: showLabels)
 * - labels: dict[str, str] | None
 * - size: str | None ("small" | "medium" | "large")
 * - color: str | None
 * - empty_color: str | None (alias: emptyColor)
 * - icon: str | None
 * - required: bool | None
 *
 * @module admin/widget-config/rating-config
 */

import { WidgetConfigBase } from './config-base.js';

/**
 * Rating style options
 */
const STYLE_OPTIONS = [
    { value: 'stars', label: 'Stars ⭐' },
    { value: 'numeric', label: 'Numeric (1-N)' },
    { value: 'emoji', label: 'Emoji 😀' },
    { value: 'thumbs', label: 'Thumbs 👍👎' },
];

/**
 * Size options
 */
const SIZE_OPTIONS = [
    { value: '', label: 'Default' },
    { value: 'small', label: 'Small' },
    { value: 'medium', label: 'Medium' },
    { value: 'large', label: 'Large' },
];

export class RatingConfig extends WidgetConfigBase {
    /**
     * Render the rating widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        const labels = config.labels || {};

        this.container.innerHTML = `
            <div class="widget-config widget-config-rating">
                <div class="row g-2">
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Style
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Visual style of the rating component."></i>
                        </label>
                        ${this.createSelect('config-style', STYLE_OPTIONS, config.style || 'stars')}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Max Rating
                            <span class="text-danger">*</span>
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Maximum rating value (e.g., 5 for 5-star rating)."></i>
                        </label>
                        ${this.createNumberInput('config-max-rating', config.max_rating ?? config.maxRating ?? 5, '5', { min: 2, max: 10 })}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Default Value
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Pre-selected rating value."></i>
                        </label>
                        ${this.createNumberInput('config-default-value', config.default_value ?? config.defaultValue ?? '', 'Optional', { min: 0, step: 0.5 })}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Size
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Size of the rating icons."></i>
                        </label>
                        ${this.createSelect('config-size', SIZE_OPTIONS, config.size || '')}
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-md-3">
                        ${this.createSwitch(
                            'config-allow-half',
                            `${this.uid}-allow-half`,
                            'Allow Half Ratings',
                            'Allow half-star/half-point selections.',
                            config.allow_half ?? config.allowHalf ?? false
                        )}
                    </div>
                    <div class="col-md-3">
                        ${this.createSwitch(
                            'config-show-value',
                            `${this.uid}-show-value`,
                            'Show Numeric Value',
                            'Display the numeric value next to the rating.',
                            config.show_value ?? config.showValue ?? false
                        )}
                    </div>
                    <div class="col-md-3">
                        ${this.createSwitch('config-show-labels', `${this.uid}-show-labels`, 'Show Labels', 'Display labels for rating values.', config.show_labels ?? config.showLabels ?? false)}
                    </div>
                    <div class="col-md-3">
                        ${this.createSwitch('config-required', `${this.uid}-required`, 'Required', 'User must provide a rating.', config.required ?? false)}
                    </div>
                </div>

                ${this.createCollapsibleSection(
                    `${this.uid}-styling`,
                    'Styling Options',
                    `
                    <div class="row g-2">
                        <div class="col-md-4">
                            <label class="form-label small mb-0">
                                Active Color
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="Color for filled/selected rating items."></i>
                            </label>
                            <div class="input-group input-group-sm">
                                <input type="color" class="form-control form-control-color config-color"
                                       value="${config.color || '#ffc107'}" title="Choose color">
                                <input type="text" class="form-control config-color-text"
                                       value="${config.color || ''}" placeholder="#ffc107">
                            </div>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label small mb-0">
                                Empty Color
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="Color for empty/unselected rating items."></i>
                            </label>
                            <div class="input-group input-group-sm">
                                <input type="color" class="form-control form-control-color config-empty-color"
                                       value="${config.empty_color ?? config.emptyColor ?? '#e4e5e9'}" title="Choose color">
                                <input type="text" class="form-control config-empty-color-text"
                                       value="${config.empty_color ?? config.emptyColor ?? ''}" placeholder="#e4e5e9">
                            </div>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label small mb-0">
                                Custom Icon
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="Bootstrap icon name (e.g., 'heart', 'star-fill')."></i>
                            </label>
                            ${this.createTextInput('config-icon', config.icon, 'e.g., heart')}
                        </div>
                    </div>
                `
                )}

                ${this.createCollapsibleSection(
                    `${this.uid}-labels`,
                    'Rating Labels',
                    `
                    <p class="text-muted small mb-2">Define labels for specific rating values (e.g., 1=Poor, 5=Excellent)</p>
                    <div class="row g-2">
                        <div class="col-md-4">
                            <label class="form-label small mb-0">Low Label (1)</label>
                            ${this.createTextInput('config-label-1', labels['1'] || '', 'e.g., Poor')}
                        </div>
                        <div class="col-md-4">
                            <label class="form-label small mb-0">Mid Label</label>
                            ${this.createTextInput('config-label-mid', labels['3'] || '', 'e.g., Average')}
                        </div>
                        <div class="col-md-4">
                            <label class="form-label small mb-0">High Label (max)</label>
                            ${this.createTextInput('config-label-max', labels['5'] || labels.max || '', 'e.g., Excellent')}
                        </div>
                    </div>
                `
                )}
            </div>
        `;

        this.initTooltips();
        this.setupColorSync();
    }

    /**
     * Sync color picker with text input
     */
    setupColorSync() {
        const colorPicker = this.query('.config-color');
        const colorText = this.query('.config-color-text');
        const emptyColorPicker = this.query('.config-empty-color');
        const emptyColorText = this.query('.config-empty-color-text');

        if (colorPicker && colorText) {
            colorPicker.addEventListener('input', () => {
                colorText.value = colorPicker.value;
            });
            colorText.addEventListener('input', () => {
                if (/^#[0-9A-Fa-f]{6}$/.test(colorText.value)) {
                    colorPicker.value = colorText.value;
                }
            });
        }

        if (emptyColorPicker && emptyColorText) {
            emptyColorPicker.addEventListener('input', () => {
                emptyColorText.value = emptyColorPicker.value;
            });
            emptyColorText.addEventListener('input', () => {
                if (/^#[0-9A-Fa-f]{6}$/.test(emptyColorText.value)) {
                    emptyColorPicker.value = emptyColorText.value;
                }
            });
        }
    }

    /**
     * Get configuration values matching Python schema
     * @returns {Object} Widget configuration
     */
    getValue() {
        const config = {};

        const style = this.getInputValue('config-style', 'stars');
        config.style = style;

        const maxRating = this.getIntValue('config-max-rating', 5);
        config.max_rating = maxRating;

        const allowHalf = this.getChecked('config-allow-half');
        if (allowHalf) config.allow_half = true;

        const defaultValue = this.getNumericValue('config-default-value');
        if (defaultValue !== null) config.default_value = defaultValue;

        const showValue = this.getChecked('config-show-value');
        if (showValue) config.show_value = true;

        const showLabels = this.getChecked('config-show-labels');
        if (showLabels) config.show_labels = true;

        const required = this.getChecked('config-required');
        if (required) config.required = true;

        const size = this.getInputValue('config-size');
        if (size) config.size = size;

        const color = this.getInputValue('config-color-text');
        if (color) config.color = color;

        const emptyColor = this.getInputValue('config-empty-color-text');
        if (emptyColor) config.empty_color = emptyColor;

        const icon = this.getInputValue('config-icon');
        if (icon) config.icon = icon;

        // Collect labels
        const labels = {};
        const label1 = this.getInputValue('config-label-1');
        const labelMid = this.getInputValue('config-label-mid');
        const labelMax = this.getInputValue('config-label-max');

        if (label1) labels['1'] = label1;
        if (labelMid) labels['3'] = labelMid;
        if (labelMax) labels[String(maxRating)] = labelMax;

        if (Object.keys(labels).length > 0) {
            config.labels = labels;
        }

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const maxRating = this.getIntValue('config-max-rating');
        if (maxRating === null || maxRating < 2) {
            errors.push('Max rating must be at least 2');
        }

        const defaultValue = this.getNumericValue('config-default-value');
        if (defaultValue !== null && maxRating !== null) {
            if (defaultValue < 0 || defaultValue > maxRating) {
                errors.push(`Default value must be between 0 and ${maxRating}`);
            }
        }

        return { valid: errors.length === 0, errors };
    }
}
