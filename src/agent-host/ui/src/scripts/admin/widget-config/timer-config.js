/**
 * Timer Widget Configuration
 *
 * Configuration UI for the 'timer' widget type.
 *
 * Attributes Reference (from ax-timer.js):
 * - mode: "countdown" | "elapsed" (default: "countdown")
 * - duration: Duration in seconds (required for countdown mode)
 * - auto_start: Automatically start the timer
 * - show_controls: Show play/pause/reset controls
 * - format: "hh:mm:ss" | "mm:ss" | "seconds" (default: "mm:ss")
 * - warning_threshold: Seconds remaining to trigger warning state
 *
 * @module admin/widget-config/timer-config
 */

import { WidgetConfigBase } from './config-base.js';

export class TimerConfig extends WidgetConfigBase {
    /**
     * Render the timer widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        const modeOptions = [
            { value: 'countdown', label: 'Countdown' },
            { value: 'elapsed', label: 'Elapsed Time' },
        ];

        const formatOptions = [
            { value: 'mm:ss', label: 'MM:SS' },
            { value: 'hh:mm:ss', label: 'HH:MM:SS' },
            { value: 'seconds', label: 'Seconds only' },
        ];

        this.container.innerHTML = `
            <div class="widget-config widget-config-timer">
                <div class="row g-2">
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Mode<span class="text-danger">*</span>
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Countdown: counts down from duration. Elapsed: counts up from zero."></i>
                        </label>
                        ${this.createSelect('config-mode', modeOptions, config.mode || 'countdown')}
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Duration (seconds)
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Duration in seconds. Required for countdown mode."></i>
                        </label>
                        ${this.createNumberInput('config-duration', config.duration ?? 60, '60', { min: 1 })}
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Display Format
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="How to display the time value."></i>
                        </label>
                        ${this.createSelect('config-format', formatOptions, config.format || 'mm:ss')}
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Warning Threshold
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Seconds remaining when the timer turns to warning color (countdown mode only)."></i>
                        </label>
                        ${this.createNumberInput('config-warning-threshold', config.warning_threshold ?? config.warningThreshold ?? '', 'Optional', { min: 1 })}
                    </div>
                    <div class="col-md-4">
                        <div class="mt-4">
                            ${this.createSwitch(
                                'config-auto-start',
                                `${this.uid}-auto-start`,
                                'Auto Start',
                                'Automatically start the timer when displayed.',
                                config.auto_start ?? config.autoStart ?? false
                            )}
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mt-4">
                            ${this.createSwitch(
                                'config-show-controls',
                                `${this.uid}-show-controls`,
                                'Show Controls',
                                'Display play, pause, and reset buttons.',
                                config.show_controls ?? config.showControls ?? true
                            )}
                        </div>
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

        const mode = this.getInputValue('config-mode', 'countdown');
        config.mode = mode;

        const duration = this.getNumericValue('config-duration');
        if (duration !== null) {
            config.duration = duration;
        }

        const format = this.getInputValue('config-format', 'mm:ss');
        if (format !== 'mm:ss') {
            config.format = format;
        }

        const warningThreshold = this.getNumericValue('config-warning-threshold');
        if (warningThreshold !== null) {
            config.warning_threshold = warningThreshold;
        }

        const autoStart = this.getChecked('config-auto-start');
        if (autoStart) {
            config.auto_start = true;
        }

        const showControls = this.getChecked('config-show-controls');
        if (!showControls) {
            config.show_controls = false;
        }

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const mode = this.getInputValue('config-mode', 'countdown');
        const duration = this.getNumericValue('config-duration');

        if (mode === 'countdown' && (duration === null || duration <= 0)) {
            errors.push('Duration is required for countdown mode and must be greater than 0');
        }

        const warningThreshold = this.getNumericValue('config-warning-threshold');
        if (warningThreshold !== null) {
            if (warningThreshold <= 0) {
                errors.push('Warning threshold must be greater than 0');
            }
            if (duration !== null && warningThreshold >= duration) {
                errors.push('Warning threshold must be less than duration');
            }
        }

        return { valid: errors.length === 0, errors };
    }
}
