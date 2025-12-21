/**
 * Date Picker Widget Configuration
 *
 * Configuration UI for the 'date_picker' widget type.
 *
 * Python Schema Reference (DatePickerConfig):
 * - mode: DatePickerMode = "date" ("date" | "time" | "datetime" | "daterange")
 * - format: str = "YYYY-MM-DD"
 * - display_format: str | None (alias: displayFormat)
 * - placeholder: str | None
 * - min_date: str | None (alias: minDate)
 * - max_date: str | None (alias: maxDate)
 * - disabled_dates: list[str] | None (alias: disabledDates)
 * - disabled_days_of_week: list[int] | None (alias: disabledDaysOfWeek)
 * - default_value: str | None (alias: defaultValue)
 * - show_today_button: bool | None (alias: showTodayButton)
 * - show_clear_button: bool | None (alias: showClearButton)
 * - week_starts_on: int | None (alias: weekStartsOn) - 0=Sunday, 1=Monday
 * - locale: str | None
 * - timezone: str | None
 * - required: bool | None
 *
 * @module admin/widget-config/date-picker-config
 */

import { WidgetConfigBase } from './config-base.js';

/**
 * Date picker mode options
 */
const MODE_OPTIONS = [
    { value: 'date', label: 'Date Only' },
    { value: 'time', label: 'Time Only' },
    { value: 'datetime', label: 'Date & Time' },
    { value: 'daterange', label: 'Date Range' },
];

/**
 * Common date format options
 */
const FORMAT_OPTIONS = [
    { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD (ISO)' },
    { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY (US)' },
    { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY (EU)' },
    { value: 'DD-MM-YYYY', label: 'DD-MM-YYYY' },
    { value: 'YYYY/MM/DD', label: 'YYYY/MM/DD' },
];

/**
 * Week start day options
 */
const WEEK_START_OPTIONS = [
    { value: '', label: 'Default' },
    { value: '0', label: 'Sunday' },
    { value: '1', label: 'Monday' },
    { value: '6', label: 'Saturday' },
];

/**
 * Common locale options
 */
const LOCALE_OPTIONS = [
    { value: '', label: 'Browser Default' },
    { value: 'en-US', label: 'English (US)' },
    { value: 'en-GB', label: 'English (UK)' },
    { value: 'de-DE', label: 'German' },
    { value: 'fr-FR', label: 'French' },
    { value: 'es-ES', label: 'Spanish' },
    { value: 'it-IT', label: 'Italian' },
    { value: 'pt-BR', label: 'Portuguese (BR)' },
    { value: 'ja-JP', label: 'Japanese' },
    { value: 'zh-CN', label: 'Chinese (Simplified)' },
];

export class DatePickerConfig extends WidgetConfigBase {
    /**
     * Render the date picker widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        // Convert disabled days to comma-separated string
        const disabledDays = (config.disabled_days_of_week ?? config.disabledDaysOfWeek ?? []).join(', ');

        this.container.innerHTML = `
            <div class="widget-config widget-config-date-picker">
                <div class="row g-2">
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Mode
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Type of date/time selection."></i>
                        </label>
                        ${this.createSelect('config-mode', MODE_OPTIONS, config.mode || 'date')}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Format
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Date format for the submitted value."></i>
                        </label>
                        ${this.createSelect('config-format', FORMAT_OPTIONS, config.format || 'YYYY-MM-DD')}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Display Format
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Format shown to user (if different from submission format)."></i>
                        </label>
                        ${this.createTextInput('config-display-format', config.display_format ?? config.displayFormat ?? '', 'Same as format')}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Placeholder
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Placeholder text when empty."></i>
                        </label>
                        ${this.createTextInput('config-placeholder', config.placeholder, 'Select a date...')}
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Min Date
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Earliest selectable date (YYYY-MM-DD format)."></i>
                        </label>
                        ${this.createTextInput('config-min-date', config.min_date ?? config.minDate ?? '', 'YYYY-MM-DD')}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Max Date
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Latest selectable date (YYYY-MM-DD format)."></i>
                        </label>
                        ${this.createTextInput('config-max-date', config.max_date ?? config.maxDate ?? '', 'YYYY-MM-DD')}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Default Value
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Pre-selected date value."></i>
                        </label>
                        ${this.createTextInput('config-default-value', config.default_value ?? config.defaultValue ?? '', 'YYYY-MM-DD')}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Week Starts On
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="First day of the week in calendar."></i>
                        </label>
                        ${this.createSelect('config-week-starts', WEEK_START_OPTIONS, String(config.week_starts_on ?? config.weekStartsOn ?? ''))}
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-md-3">
                        ${this.createSwitch(
                            'config-show-today',
                            `${this.uid}-show-today`,
                            'Show Today Button',
                            "Display a button to select today's date.",
                            config.show_today_button ?? config.showTodayButton ?? true
                        )}
                    </div>
                    <div class="col-md-3">
                        ${this.createSwitch(
                            'config-show-clear',
                            `${this.uid}-show-clear`,
                            'Show Clear Button',
                            'Display a button to clear the selection.',
                            config.show_clear_button ?? config.showClearButton ?? true
                        )}
                    </div>
                    <div class="col-md-3">
                        ${this.createSwitch('config-required', `${this.uid}-required`, 'Required', 'User must select a date.', config.required ?? false)}
                    </div>
                </div>

                ${this.createCollapsibleSection(
                    `${this.uid}-advanced`,
                    'Advanced Options',
                    `
                    <div class="row g-2">
                        <div class="col-md-4">
                            <label class="form-label small mb-0">
                                Locale
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="Language and regional formatting."></i>
                            </label>
                            ${this.createSelect('config-locale', LOCALE_OPTIONS, config.locale || '')}
                        </div>
                        <div class="col-md-4">
                            <label class="form-label small mb-0">
                                Timezone
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="Timezone for date/time display (e.g., 'America/New_York')."></i>
                            </label>
                            ${this.createTextInput('config-timezone', config.timezone, 'e.g., America/New_York')}
                        </div>
                        <div class="col-md-4">
                            <label class="form-label small mb-0">
                                Disabled Days of Week
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="Days to disable (0=Sun, 1=Mon, ..., 6=Sat). Comma-separated."></i>
                            </label>
                            ${this.createTextInput('config-disabled-days', disabledDays, 'e.g., 0, 6 for weekends')}
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

        const mode = this.getInputValue('config-mode', 'date');
        config.mode = mode;

        const format = this.getInputValue('config-format', 'YYYY-MM-DD');
        config.format = format;

        const displayFormat = this.getInputValue('config-display-format');
        if (displayFormat) config.display_format = displayFormat;

        const placeholder = this.getInputValue('config-placeholder');
        if (placeholder) config.placeholder = placeholder;

        const minDate = this.getInputValue('config-min-date');
        if (minDate) config.min_date = minDate;

        const maxDate = this.getInputValue('config-max-date');
        if (maxDate) config.max_date = maxDate;

        const defaultValue = this.getInputValue('config-default-value');
        if (defaultValue) config.default_value = defaultValue;

        const weekStartsOn = this.getInputValue('config-week-starts');
        if (weekStartsOn !== '') {
            config.week_starts_on = parseInt(weekStartsOn, 10);
        }

        const showToday = this.getChecked('config-show-today');
        if (!showToday) config.show_today_button = false;

        const showClear = this.getChecked('config-show-clear');
        if (!showClear) config.show_clear_button = false;

        const required = this.getChecked('config-required');
        if (required) config.required = true;

        const locale = this.getInputValue('config-locale');
        if (locale) config.locale = locale;

        const timezone = this.getInputValue('config-timezone');
        if (timezone) config.timezone = timezone;

        // Parse disabled days
        const disabledDaysStr = this.getInputValue('config-disabled-days');
        if (disabledDaysStr) {
            const disabledDays = disabledDaysStr
                .split(',')
                .map(d => parseInt(d.trim(), 10))
                .filter(d => !isNaN(d) && d >= 0 && d <= 6);
            if (disabledDays.length > 0) {
                config.disabled_days_of_week = disabledDays;
            }
        }

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const minDate = this.getInputValue('config-min-date');
        const maxDate = this.getInputValue('config-max-date');

        if (minDate && maxDate) {
            const min = new Date(minDate);
            const max = new Date(maxDate);
            if (min > max) {
                errors.push('Min date cannot be after max date');
            }
        }

        // Validate date formats
        const datePattern = /^\d{4}-\d{2}-\d{2}$/;
        if (minDate && !datePattern.test(minDate)) {
            errors.push('Min date must be in YYYY-MM-DD format');
        }
        if (maxDate && !datePattern.test(maxDate)) {
            errors.push('Max date must be in YYYY-MM-DD format');
        }

        return { valid: errors.length === 0, errors };
    }
}
