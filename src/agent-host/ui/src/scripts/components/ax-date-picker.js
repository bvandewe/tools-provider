/**
 * Date Picker Widget Component
 * Calendar-based date selection with multiple modes.
 *
 * Attributes:
 * - mode: "date" | "time" | "datetime" | "range"
 * - format: Date format string (default: "YYYY-MM-DD")
 * - display-format: Format for display (localized)
 * - placeholder: Input placeholder text
 * - min-date: Minimum selectable date (ISO string)
 * - max-date: Maximum selectable date (ISO string)
 * - disabled-dates: JSON array of disabled dates
 * - disabled-days-of-week: JSON array [0-6, Sunday=0]
 * - default-value: Initial date value
 * - show-today-button: Show "Today" quick button
 * - show-clear-button: Show clear button
 * - week-starts-on: First day of week (0=Sunday, 1=Monday)
 * - locale: Locale for formatting
 * - prompt: Question/instruction text
 *
 * Events:
 * - ax-date-change: Fired when date changes
 * - ax-response: Fired with selected date
 *
 * @example
 * <ax-date-picker
 *   mode="date"
 *   format="YYYY-MM-DD"
 *   min-date="2024-01-01"
 *   max-date="2024-12-31"
 *   show-today-button
 *   show-clear-button
 * ></ax-date-picker>
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

class AxDatePicker extends AxWidgetBase {
    static get observedAttributes() {
        return [
            ...super.observedAttributes,
            'mode',
            'format',
            'display-format',
            'placeholder',
            'min-date',
            'max-date',
            'disabled-dates',
            'disabled-days-of-week',
            'default-value',
            'show-today-button',
            'show-clear-button',
            'week-starts-on',
            'locale',
            'prompt',
        ];
    }

    constructor() {
        super();
        this._selectedDate = null;
        this._selectedEndDate = null; // For range mode
        this._selectedTime = { hours: 0, minutes: 0 };
        this._viewDate = new Date();
        this._isOpen = false;
        this._selectingEndDate = false; // For range mode
    }

    // =========================================================================
    // Attribute Getters
    // =========================================================================

    get mode() {
        const m = this.getAttribute('mode') || 'date';
        return ['date', 'time', 'datetime', 'range'].includes(m) ? m : 'date';
    }

    get format() {
        return this.getAttribute('format') || 'YYYY-MM-DD';
    }

    get displayFormat() {
        return this.getAttribute('display-format') || null;
    }

    get placeholder() {
        return this.getAttribute('placeholder') || this._getDefaultPlaceholder();
    }

    get minDate() {
        const val = this.getAttribute('min-date');
        return val ? new Date(val) : null;
    }

    get maxDate() {
        const val = this.getAttribute('max-date');
        return val ? new Date(val) : null;
    }

    get disabledDates() {
        const dates = this.parseJsonAttribute('disabled-dates', []);
        return dates.map(d => new Date(d).toDateString());
    }

    get disabledDaysOfWeek() {
        return this.parseJsonAttribute('disabled-days-of-week', []);
    }

    get defaultValue() {
        return this.getAttribute('default-value') || null;
    }

    get showTodayButton() {
        return this.hasAttribute('show-today-button');
    }

    get showClearButton() {
        return this.hasAttribute('show-clear-button');
    }

    get weekStartsOn() {
        return parseInt(this.getAttribute('week-starts-on')) || 0;
    }

    get locale() {
        return this.getAttribute('locale') || navigator.language || 'en-US';
    }

    get prompt() {
        return this.getAttribute('prompt') || '';
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    async connectedCallback() {
        // Initialize from default value
        if (this.defaultValue) {
            if (this.mode === 'range') {
                const [start, end] = this.defaultValue.split(',');
                if (start) this._selectedDate = new Date(start.trim());
                if (end) this._selectedEndDate = new Date(end.trim());
            } else if (this.mode === 'time') {
                const [hours, minutes] = this.defaultValue.split(':');
                this._selectedTime = { hours: parseInt(hours) || 0, minutes: parseInt(minutes) || 0 };
            } else {
                this._selectedDate = new Date(this.defaultValue);
            }
        }

        // Initialize view date
        if (this._selectedDate && !isNaN(this._selectedDate)) {
            this._viewDate = new Date(this._selectedDate);
        }

        await super.connectedCallback();

        // Close on outside click
        this._boundCloseHandler = this._handleOutsideClick.bind(this);
        document.addEventListener('click', this._boundCloseHandler);
    }

    disconnectedCallback() {
        document.removeEventListener('click', this._boundCloseHandler);
        super.disconnectedCallback();
    }

    // =========================================================================
    // Value Interface
    // =========================================================================

    getValue() {
        if (this.mode === 'time') {
            const { hours, minutes } = this._selectedTime;
            return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
        }

        if (this.mode === 'range') {
            if (!this._selectedDate) return null;
            const startDate = this._formatDate(this._selectedDate);
            const endDate = this._selectedEndDate ? this._formatDate(this._selectedEndDate) : null;
            return { startDate, endDate };
        }

        if (!this._selectedDate) return null;

        if (this.mode === 'datetime') {
            const date = new Date(this._selectedDate);
            date.setHours(this._selectedTime.hours, this._selectedTime.minutes);
            return this._formatDateTime(date);
        }

        return this._formatDate(this._selectedDate);
    }

    setValue(value) {
        if (!value) {
            this._selectedDate = null;
            this._selectedEndDate = null;
            this._selectedTime = { hours: 0, minutes: 0 };
        } else if (this.mode === 'time') {
            const [hours, minutes] = String(value).split(':');
            this._selectedTime = { hours: parseInt(hours) || 0, minutes: parseInt(minutes) || 0 };
        } else if (this.mode === 'range' && typeof value === 'object') {
            if (value.start) this._selectedDate = new Date(value.start);
            if (value.end) this._selectedEndDate = new Date(value.end);
        } else {
            this._selectedDate = new Date(value);
            if (this.mode === 'datetime') {
                this._selectedTime = {
                    hours: this._selectedDate.getHours(),
                    minutes: this._selectedDate.getMinutes(),
                };
            }
        }

        this.render();
        this.bindEvents();
    }

    validate() {
        const errors = [];
        const value = this.getValue();

        if (this.required && !value) {
            errors.push('Please select a date');
        }

        if (this.mode === 'range' && value) {
            if (!value.end) {
                errors.push('Please select an end date');
            } else if (new Date(value.start) > new Date(value.end)) {
                errors.push('End date must be after start date');
            }
        }

        if (this._selectedDate && this.minDate && this._selectedDate < this.minDate) {
            errors.push(`Date must be on or after ${this._formatDisplayDate(this.minDate)}`);
        }

        if (this._selectedDate && this.maxDate && this._selectedDate > this.maxDate) {
            errors.push(`Date must be on or before ${this._formatDisplayDate(this.maxDate)}`);
        }

        return { valid: errors.length === 0, errors, warnings: [] };
    }

    // =========================================================================
    // Styles
    // =========================================================================

    async getStyles() {
        return `
            ${await this.getBaseStyles()}

            :host {
                display: block;
                font-family: var(--ax-font-family, system-ui, -apple-system, sans-serif);
            }

            .widget-container {
                background: var(--ax-widget-bg, #f8f9fa);
                border: 1px solid var(--ax-border-color, #dee2e6);
                border-radius: var(--ax-border-radius, 12px);
                padding: var(--ax-padding, 1.25rem);
                margin: var(--ax-margin, 0.5rem 0);
            }

            .prompt {
                font-size: 1rem;
                font-weight: 500;
                color: var(--ax-text-color, #212529);
                margin-bottom: 1rem;
                line-height: 1.5;
            }

            .picker-wrapper {
                position: relative;
            }

            .input-group {
                display: flex;
                gap: 0.5rem;
            }

            .date-input {
                flex: 1;
                padding: 0.625rem 0.875rem;
                border: 1px solid var(--ax-border-color, #dee2e6);
                border-radius: 6px;
                font-size: 0.95rem;
                color: var(--ax-text-color, #212529);
                background: white;
                cursor: pointer;
            }

            .date-input:focus {
                outline: none;
                border-color: var(--ax-primary-color, #0d6efd);
                box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.15);
            }

            .date-input::placeholder {
                color: var(--ax-text-muted, #6c757d);
            }

            .input-btn {
                padding: 0.625rem 0.75rem;
                border: 1px solid var(--ax-border-color, #dee2e6);
                border-radius: 6px;
                background: white;
                cursor: pointer;
                color: var(--ax-text-color, #212529);
                transition: background 0.15s;
            }

            .input-btn:hover {
                background: var(--ax-hover-bg, #f0f0f0);
            }

            .clear-btn:hover {
                color: var(--ax-error-color, #dc3545);
            }

            /* Dropdown */
            .picker-dropdown {
                position: absolute;
                top: 100%;
                left: 0;
                margin-top: 4px;
                background: white;
                border: 1px solid var(--ax-border-color, #dee2e6);
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                z-index: 1000;
                opacity: 0;
                visibility: hidden;
                transform: translateY(-10px);
                transition: all 0.2s ease;
            }

            .picker-dropdown.open {
                opacity: 1;
                visibility: visible;
                transform: translateY(0);
            }

            /* Calendar header */
            .calendar-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0.75rem;
                border-bottom: 1px solid var(--ax-border-light, #e9ecef);
            }

            .calendar-title {
                font-weight: 600;
                font-size: 1rem;
                color: var(--ax-text-color, #212529);
            }

            .nav-btn {
                width: 32px;
                height: 32px;
                border: none;
                background: transparent;
                border-radius: 50%;
                cursor: pointer;
                font-size: 1.2rem;
                color: var(--ax-text-color, #212529);
                transition: background 0.15s;
            }

            .nav-btn:hover {
                background: var(--ax-hover-bg, #f0f0f0);
            }

            .nav-btn:disabled {
                opacity: 0.3;
                cursor: not-allowed;
            }

            /* Calendar grid */
            .calendar-grid {
                padding: 0.5rem;
            }

            .weekdays {
                display: grid;
                grid-template-columns: repeat(7, 1fr);
                margin-bottom: 0.25rem;
            }

            .weekday {
                text-align: center;
                font-size: 0.75rem;
                font-weight: 600;
                color: var(--ax-text-muted, #6c757d);
                padding: 0.5rem 0;
            }

            .days {
                display: grid;
                grid-template-columns: repeat(7, 1fr);
                gap: 2px;
            }

            .day {
                aspect-ratio: 1;
                display: flex;
                align-items: center;
                justify-content: center;
                border: none;
                background: transparent;
                border-radius: 50%;
                cursor: pointer;
                font-size: 0.875rem;
                color: var(--ax-text-color, #212529);
                transition: all 0.15s;
            }

            .day:hover:not(:disabled) {
                background: var(--ax-hover-bg, #f0f0f0);
            }

            .day.today {
                font-weight: 700;
                border: 2px solid var(--ax-primary-color, #0d6efd);
            }

            .day.selected {
                background: var(--ax-primary-color, #0d6efd);
                color: white;
            }

            .day.in-range {
                background: var(--ax-primary-light, #e7f1ff);
                border-radius: 0;
            }

            .day.range-start {
                border-radius: 50% 0 0 50%;
            }

            .day.range-end {
                border-radius: 0 50% 50% 0;
            }

            .day.other-month {
                color: var(--ax-text-muted, #6c757d);
                opacity: 0.5;
            }

            .day:disabled {
                color: var(--ax-text-muted, #6c757d);
                opacity: 0.3;
                cursor: not-allowed;
            }

            /* Time picker */
            .time-picker {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                padding: 0.75rem;
                border-top: 1px solid var(--ax-border-light, #e9ecef);
            }

            .time-input {
                width: 60px;
                padding: 0.5rem;
                text-align: center;
                border: 1px solid var(--ax-border-color, #dee2e6);
                border-radius: 4px;
                font-size: 1rem;
            }

            .time-input:focus {
                outline: none;
                border-color: var(--ax-primary-color, #0d6efd);
            }

            .time-separator {
                font-size: 1.2rem;
                font-weight: 600;
            }

            /* Footer */
            .calendar-footer {
                display: flex;
                justify-content: space-between;
                padding: 0.75rem;
                border-top: 1px solid var(--ax-border-light, #e9ecef);
            }

            .footer-btn {
                padding: 0.5rem 1rem;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.875rem;
                transition: background 0.15s;
            }

            .today-btn {
                background: var(--ax-primary-light, #e7f1ff);
                color: var(--ax-primary-color, #0d6efd);
            }

            .today-btn:hover {
                background: var(--ax-primary-color, #0d6efd);
                color: white;
            }

            .confirm-btn {
                background: var(--ax-primary-color, #0d6efd);
                color: white;
            }

            .confirm-btn:hover {
                background: var(--ax-primary-dark, #0b5ed7);
            }

            /* Range indicator */
            .range-indicator {
                padding: 0.5rem 0.75rem;
                background: var(--ax-primary-light, #e7f1ff);
                text-align: center;
                font-size: 0.85rem;
                color: var(--ax-primary-color, #0d6efd);
            }

            /* Dark mode */
            @media (prefers-color-scheme: dark) {
                .widget-container {
                    --ax-widget-bg: #2d3748;
                    --ax-border-color: #4a5568;
                    --ax-text-color: #e2e8f0;
                }

                .date-input,
                .input-btn,
                .picker-dropdown,
                .time-input {
                    background: #1a202c;
                    border-color: #4a5568;
                    color: #e2e8f0;
                }
            }
        `;
    }

    // =========================================================================
    // Rendering
    // =========================================================================

    render() {
        const displayValue = this._getDisplayValue();

        this.shadowRoot.innerHTML = `
            <style>${this._styles || ''}</style>
            <div class="widget-container">
                ${this.prompt ? `<div class="prompt">${this.renderMarkdown(this.prompt)}</div>` : ''}

                <div class="picker-wrapper">
                    <div class="input-group">
                        <input type="text"
                               class="date-input"
                               value="${displayValue}"
                               placeholder="${this.placeholder}"
                               readonly
                               aria-label="${this.prompt || 'Select date'}"
                               aria-haspopup="dialog" />
                        ${
                            this.showClearButton && displayValue
                                ? `
                            <button class="input-btn clear-btn" aria-label="Clear date">✕</button>
                        `
                                : ''
                        }
                        <button class="input-btn calendar-btn calendar-toggle" aria-label="Open calendar">📅</button>
                    </div>

                    <div class="picker-dropdown calendar-dropdown ${this._isOpen ? 'open' : ''}" role="dialog" aria-label="Date picker">
                        ${this._renderPickerContent()}
                    </div>
                </div>
            </div>
        `;
    }

    _renderPickerContent() {
        if (this.mode === 'time') {
            return this._renderTimePicker();
        }

        const calendar = this._renderCalendar();
        const timePicker = this.mode === 'datetime' ? this._renderTimePicker() : '';
        const footer = this._renderFooter();

        return `
            ${
                this.mode === 'range'
                    ? `
                <div class="range-indicator">
                    ${this._selectingEndDate ? 'Select end date' : 'Select start date'}
                </div>
            `
                    : ''
            }
            ${calendar}
            ${timePicker}
            ${footer}
        `;
    }

    _renderCalendar() {
        const year = this._viewDate.getFullYear();
        const month = this._viewDate.getMonth();
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const monthName = this._viewDate.toLocaleDateString(this.locale, { month: 'long', year: 'numeric' });
        const weekdays = this._getWeekdayNames();
        const days = this._getCalendarDays(year, month);

        return `
            <div class="calendar-header">
                <button class="nav-btn prev-month" aria-label="Previous month">‹</button>
                <span class="calendar-title month-year">${monthName}</span>
                <button class="nav-btn next-month" aria-label="Next month">›</button>
            </div>
            <div class="calendar-grid">
                <div class="weekdays calendar-weekdays">
                    ${weekdays.map(day => `<span class="weekday">${day}</span>`).join('')}
                </div>
                <div class="days calendar-days">
                    ${days.map(day => this._renderDay(day, today)).join('')}
                </div>
            </div>
        `;
    }

    _renderDay(day, today) {
        const isToday = day.date.toDateString() === today.toDateString();
        const isSelected = this._isDateSelected(day.date);
        const isInRange = this._isInRange(day.date);
        const isRangeStart = this._selectedDate && day.date.toDateString() === this._selectedDate.toDateString();
        const isRangeEnd = this._selectedEndDate && day.date.toDateString() === this._selectedEndDate.toDateString();
        const isDisabled = this._isDateDisabled(day.date);

        const classes = [
            'day',
            'calendar-day',
            day.isOtherMonth ? 'other-month' : '',
            isToday ? 'today' : '',
            isSelected ? 'selected' : '',
            isInRange ? 'in-range' : '',
            isRangeStart ? 'range-start' : '',
            isRangeEnd ? 'range-end' : '',
        ]
            .filter(Boolean)
            .join(' ');

        return `
            <button class="${classes}"
                    data-date="${day.date.toISOString()}"
                    ${isDisabled ? 'disabled' : ''}
                    aria-label="${day.date.toLocaleDateString(this.locale)}"
                    aria-selected="${isSelected}">
                ${day.date.getDate()}
            </button>
        `;
    }

    _renderTimePicker() {
        return `
            <div class="time-picker">
                <input type="number" class="time-input hours"
                       min="0" max="23"
                       value="${String(this._selectedTime.hours).padStart(2, '0')}"
                       aria-label="Hours" />
                <span class="time-separator">:</span>
                <input type="number" class="time-input minutes"
                       min="0" max="59"
                       value="${String(this._selectedTime.minutes).padStart(2, '0')}"
                       aria-label="Minutes" />
            </div>
        `;
    }

    _renderFooter() {
        const showToday = this.showTodayButton && this.mode !== 'time';
        const showConfirm = this.mode === 'datetime' || this.mode === 'range';

        if (!showToday && !showConfirm) return '';

        return `
            <div class="calendar-footer">
                ${showToday ? '<button class="footer-btn today-btn">Today</button>' : '<span></span>'}
                ${showConfirm ? '<button class="footer-btn confirm-btn">Confirm</button>' : ''}
            </div>
        `;
    }

    // =========================================================================
    // Calendar Helpers
    // =========================================================================

    _getWeekdayNames() {
        const names = [];
        const date = new Date(2024, 0, 7); // Start from a Sunday

        for (let i = 0; i < 7; i++) {
            const dayIndex = (this.weekStartsOn + i) % 7;
            date.setDate(7 + dayIndex);
            names.push(date.toLocaleDateString(this.locale, { weekday: 'short' }).slice(0, 2));
        }

        return names;
    }

    _getCalendarDays(year, month) {
        const days = [];
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);

        // Adjust for week start
        let startOffset = firstDay.getDay() - this.weekStartsOn;
        if (startOffset < 0) startOffset += 7;

        // Previous month days
        for (let i = startOffset - 1; i >= 0; i--) {
            const date = new Date(year, month, -i);
            days.push({ date, isOtherMonth: true });
        }

        // Current month days
        for (let d = 1; d <= lastDay.getDate(); d++) {
            days.push({ date: new Date(year, month, d), isOtherMonth: false });
        }

        // Next month days to complete grid
        const remaining = 42 - days.length; // 6 rows * 7 days
        for (let i = 1; i <= remaining; i++) {
            const date = new Date(year, month + 1, i);
            days.push({ date, isOtherMonth: true });
        }

        return days;
    }

    _isDateSelected(date) {
        if (!this._selectedDate) return false;

        const selected = this._selectedDate.toDateString();
        const endSelected = this._selectedEndDate?.toDateString();

        return date.toDateString() === selected || date.toDateString() === endSelected;
    }

    _isInRange(date) {
        if (this.mode !== 'range' || !this._selectedDate || !this._selectedEndDate) return false;

        return date > this._selectedDate && date < this._selectedEndDate;
    }

    _isDateDisabled(date) {
        if (this.minDate && date < this.minDate) return true;
        if (this.maxDate && date > this.maxDate) return true;
        if (this.disabledDates.includes(date.toDateString())) return true;
        if (this.disabledDaysOfWeek.includes(date.getDay())) return true;
        return false;
    }

    // =========================================================================
    // Formatting
    // =========================================================================

    _formatDate(date) {
        if (!date || isNaN(date)) return '';

        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');

        return this.format.replace('YYYY', year).replace('MM', month).replace('DD', day);
    }

    _formatDateTime(date) {
        if (!date || isNaN(date)) return '';

        const dateStr = this._formatDate(date);
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');

        return `${dateStr}T${hours}:${minutes}`;
    }

    _formatDisplayDate(date) {
        if (!date || isNaN(date)) return '';

        const options = { year: 'numeric', month: 'short', day: 'numeric' };
        if (this.mode === 'datetime') {
            options.hour = '2-digit';
            options.minute = '2-digit';
        }

        return date.toLocaleDateString(this.locale, options);
    }

    _getDisplayValue() {
        if (this.mode === 'time') {
            const { hours, minutes } = this._selectedTime;
            if (hours === 0 && minutes === 0 && !this._selectedDate) return '';
            return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
        }

        if (this.mode === 'range') {
            if (!this._selectedDate) return '';
            const start = this._formatDisplayDate(this._selectedDate);
            const end = this._selectedEndDate ? this._formatDisplayDate(this._selectedEndDate) : '...';
            return `${start} → ${end}`;
        }

        if (!this._selectedDate) return '';

        if (this.mode === 'datetime') {
            const date = new Date(this._selectedDate);
            date.setHours(this._selectedTime.hours, this._selectedTime.minutes);
            return this._formatDisplayDate(date);
        }

        return this._formatDisplayDate(this._selectedDate);
    }

    _getDefaultPlaceholder() {
        switch (this.mode) {
            case 'time':
                return 'Select time';
            case 'datetime':
                return 'Select date and time';
            case 'range':
                return 'Select date range';
            default:
                return 'Select date';
        }
    }

    // =========================================================================
    // Events
    // =========================================================================

    bindEvents() {
        // Toggle dropdown
        const input = this.shadowRoot.querySelector('.date-input');
        const calendarBtn = this.shadowRoot.querySelector('.calendar-btn');

        [input, calendarBtn].forEach(el => {
            el?.addEventListener('click', e => {
                e.stopPropagation();
                this._toggleDropdown();
            });
        });

        // Clear button
        this.shadowRoot.querySelector('.clear-btn')?.addEventListener('click', e => {
            e.stopPropagation();
            this._clearSelection();
        });

        // Navigation
        this.shadowRoot.querySelector('.prev-month')?.addEventListener('click', () => {
            this._viewDate.setMonth(this._viewDate.getMonth() - 1);
            this._updateCalendar();
        });

        this.shadowRoot.querySelector('.next-month')?.addEventListener('click', () => {
            this._viewDate.setMonth(this._viewDate.getMonth() + 1);
            this._updateCalendar();
        });

        // Day clicks
        this.shadowRoot.querySelectorAll('.day:not(:disabled)').forEach(day => {
            day.addEventListener('click', () => {
                const date = new Date(day.dataset.date);
                this._handleDateSelect(date);
            });
        });

        // Time inputs
        const hoursInput = this.shadowRoot.querySelector('.hours');
        const minutesInput = this.shadowRoot.querySelector('.minutes');

        hoursInput?.addEventListener('change', e => {
            this._selectedTime.hours = Math.max(0, Math.min(23, parseInt(e.target.value) || 0));
            this._updateTimeDisplay();
        });

        minutesInput?.addEventListener('change', e => {
            this._selectedTime.minutes = Math.max(0, Math.min(59, parseInt(e.target.value) || 0));
            this._updateTimeDisplay();
        });

        // Today button
        this.shadowRoot.querySelector('.today-btn')?.addEventListener('click', () => {
            this._handleDateSelect(new Date());
        });

        // Confirm button
        this.shadowRoot.querySelector('.confirm-btn')?.addEventListener('click', () => {
            this._closeDropdown();
            this._dispatchResponse();
        });

        // Keyboard navigation
        this.shadowRoot.querySelector('.picker-dropdown')?.addEventListener('keydown', e => {
            if (e.key === 'Escape') {
                this._closeDropdown();
            }
        });
    }

    _handleDateSelect(date) {
        if (this.mode === 'range') {
            if (!this._selectingEndDate) {
                this._selectedDate = date;
                this._selectedEndDate = null;
                this._selectingEndDate = true;
            } else {
                if (date < this._selectedDate) {
                    this._selectedEndDate = this._selectedDate;
                    this._selectedDate = date;
                } else {
                    this._selectedEndDate = date;
                }
                this._selectingEndDate = false;
                this._closeDropdown();
            }
        } else {
            this._selectedDate = date;

            if (this.mode === 'date') {
                this._closeDropdown();
            }
        }

        this._updateCalendar();
        this._dispatchDateChange();

        if (this.mode === 'date' || (this.mode === 'range' && !this._selectingEndDate)) {
            this._dispatchResponse();
        }
    }

    _toggleDropdown() {
        this._isOpen = !this._isOpen;
        const dropdown = this.shadowRoot.querySelector('.picker-dropdown');
        if (dropdown) {
            dropdown.classList.toggle('open', this._isOpen);
            dropdown.hidden = !this._isOpen;
        }
    }

    _closeDropdown() {
        this._isOpen = false;
        const dropdown = this.shadowRoot.querySelector('.picker-dropdown');
        if (dropdown) {
            dropdown.classList.remove('open');
            dropdown.hidden = true;
        }
    }

    _handleOutsideClick(e) {
        if (!this._isOpen) return;
        if (!this.contains(e.target) && !this.shadowRoot.contains(e.target)) {
            this._closeDropdown();
        }
    }

    _clearSelection() {
        this._selectedDate = null;
        this._selectedEndDate = null;
        this._selectedTime = { hours: 0, minutes: 0 };
        this._selectingEndDate = false;
        this.render();
        this.bindEvents();
        this._dispatchDateChange();
        this._dispatchResponse();
    }

    _updateCalendar() {
        const grid = this.shadowRoot.querySelector('.calendar-grid');
        if (!grid) return;

        const year = this._viewDate.getFullYear();
        const month = this._viewDate.getMonth();
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const monthName = this._viewDate.toLocaleDateString(this.locale, { month: 'long', year: 'numeric' });
        const days = this._getCalendarDays(year, month);

        // Update title
        const title = this.shadowRoot.querySelector('.calendar-title');
        if (title) title.textContent = monthName;

        // Update days grid
        const daysEl = grid.querySelector('.days');
        if (daysEl) {
            daysEl.innerHTML = days.map(day => this._renderDay(day, today)).join('');

            // Rebind day clicks
            daysEl.querySelectorAll('.day:not(:disabled)').forEach(dayEl => {
                dayEl.addEventListener('click', () => {
                    const date = new Date(dayEl.dataset.date);
                    this._handleDateSelect(date);
                });
            });
        }

        // Update range indicator
        const indicator = this.shadowRoot.querySelector('.range-indicator');
        if (indicator) {
            indicator.textContent = this._selectingEndDate ? 'Select end date' : 'Select start date';
        }

        // Update input display
        const input = this.shadowRoot.querySelector('.date-input');
        if (input) {
            input.value = this._getDisplayValue();
        }
    }

    _updateTimeDisplay() {
        const input = this.shadowRoot.querySelector('.date-input');
        if (input) {
            input.value = this._getDisplayValue();
        }
        this._dispatchDateChange();
    }

    _dispatchDateChange() {
        const detail = {
            widgetId: this.widgetId,
            value: this.getValue(),
        };
        // Dispatch specific event
        this.dispatchEvent(
            new CustomEvent('ax-date-change', {
                bubbles: true,
                composed: true,
                detail,
            })
        );
        // Also dispatch generic ax-change for consistency
        this.dispatchEvent(
            new CustomEvent('ax-change', {
                bubbles: true,
                composed: true,
                detail,
            })
        );
    }

    _dispatchResponse() {
        this.dispatchResponse(this.getValue());
    }

    async loadStyles() {
        this._styles = await this.getStyles();
    }
}

// Register custom element
if (!customElements.get('ax-date-picker')) {
    customElements.define('ax-date-picker', AxDatePicker);
}

export default AxDatePicker;
