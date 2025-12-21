/**
 * Multiple Choice Widget Configuration
 *
 * Configuration UI for the 'multiple_choice' widget type.
 *
 * Python Schema Reference (MultipleChoiceConfig):
 * - options: list[str] (required)
 * - allow_multiple: bool = False (alias: allowMultiple)
 * - shuffle_options: bool | None (alias: shuffleOptions)
 * - show_labels: bool | None (alias: showLabels)
 * - label_style: str | None - "letter" | "number" (alias: labelStyle)
 *
 * @module admin/widget-config/multiple-choice-config
 */

import { WidgetConfigBase } from './config-base.js';

export class MultipleChoiceConfig extends WidgetConfigBase {
    /**
     * Render the multiple choice widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object (includes options, correct_answer)
     */
    render(config = {}, content = {}) {
        const options = content.options || [];
        const optionsText = Array.isArray(options) ? options.join('\n') : '';
        const correctAnswer = content.correct_answer || '';

        this.container.innerHTML = `
            <div class="widget-config widget-config-multiple-choice">
                <div class="row g-2">
                    <div class="col-12">
                        <label class="form-label small mb-0">
                            Options (one per line)
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Enter each option on a separate line. These will be displayed as choices."></i>
                        </label>
                        ${this.createTextarea('config-options', optionsText, 'Option 1\nOption 2\nOption 3', 4)}
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-md-4">
                        ${this.createSwitch(
                            'config-allow-multiple',
                            `${this.uid}-allow-multiple`,
                            'Allow Multiple',
                            'If enabled, users can select multiple options.',
                            config.allow_multiple || config.allowMultiple || false
                        )}
                    </div>
                    <div class="col-md-4">
                        ${this.createSwitch(
                            'config-shuffle-options',
                            `${this.uid}-shuffle-options`,
                            'Shuffle Options',
                            'If enabled, options will be presented in random order.',
                            config.shuffle_options || config.shuffleOptions || false
                        )}
                    </div>
                    <div class="col-md-4">
                        ${this.createSwitch(
                            'config-show-labels',
                            `${this.uid}-show-labels`,
                            'Show Labels',
                            'If enabled, display letter or number labels next to options.',
                            config.show_labels || config.showLabels || false
                        )}
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-md-6">
                        <label class="form-label small mb-0">
                            Label Style
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Style of labels shown next to options (A, B, C or 1, 2, 3)."></i>
                        </label>
                        ${this.createSelect(
                            'config-label-style',
                            [
                                { value: '', label: 'None' },
                                { value: 'letter', label: 'Letters (A, B, C...)' },
                                { value: 'number', label: 'Numbers (1, 2, 3...)' },
                            ],
                            config.label_style || config.labelStyle || ''
                        )}
                    </div>
                    <div class="col-md-6">
                        <label class="form-label small mb-0">
                            Correct Answer
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="The correct answer for scoring and feedback. Must match an option exactly."></i>
                        </label>
                        ${this.createTextInput('config-correct-answer', correctAnswer, 'Optional - must match an option')}
                    </div>
                </div>
            </div>
        `;

        this.initTooltips();
    }

    /**
     * Get configuration values matching Python schema
     * @returns {Object} Widget configuration with camelCase aliases
     */
    getValue() {
        const config = {};

        const allowMultiple = this.getChecked('config-allow-multiple');
        if (allowMultiple) config.allow_multiple = true;

        const shuffleOptions = this.getChecked('config-shuffle-options');
        if (shuffleOptions) config.shuffle_options = true;

        const showLabels = this.getChecked('config-show-labels');
        if (showLabels) config.show_labels = true;

        const labelStyle = this.getInputValue('config-label-style');
        if (labelStyle) config.label_style = labelStyle;

        return config;
    }

    /**
     * Get options array
     * @returns {string[]} Array of option strings
     */
    getOptions() {
        const optionsEl = this.query('.config-options');
        if (!optionsEl?.value) return [];

        return optionsEl.value
            .split('\n')
            .map(opt => opt.trim())
            .filter(opt => opt.length > 0);
    }

    /**
     * Get correct answer
     * @returns {string|null} Correct answer value
     */
    getCorrectAnswer() {
        return this.getInputValue('config-correct-answer') || null;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];
        const options = this.getOptions();

        if (options.length < 2) {
            errors.push('Multiple choice requires at least 2 options');
        }

        const correctAnswer = this.getCorrectAnswer();
        if (correctAnswer && !options.includes(correctAnswer)) {
            errors.push('Correct answer must match one of the options exactly');
        }

        return { valid: errors.length === 0, errors };
    }
}
