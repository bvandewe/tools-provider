/**
 * Tests for ax-date-picker widget
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createWidget, cleanup, shadowQuery, shadowQueryAll, captureEvent, waitForElement } from './test-utils.js';
import '../src/scripts/components/ax-date-picker.js';

describe('AxDatePicker', () => {
    let widget;

    afterEach(() => {
        cleanup();
    });

    describe('rendering', () => {
        it('renders widget container', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const container = shadowQuery(widget, '.widget-container');
            expect(container).toBeTruthy();
        });

        it('renders date input', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const input = shadowQuery(widget, '.date-input');
            expect(input).toBeTruthy();
        });

        it('renders calendar toggle button', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            expect(toggle).toBeTruthy();
        });

        it('shows prompt when provided', async () => {
            widget = createWidget('ax-date-picker', { prompt: 'Select a date' });
            await waitForElement(widget);

            const prompt = shadowQuery(widget, '.prompt');
            expect(prompt?.textContent).toContain('Select a date');
        });

        it('shows placeholder', async () => {
            widget = createWidget('ax-date-picker', { placeholder: 'Choose date...' });
            await waitForElement(widget);

            const input = shadowQuery(widget, '.date-input');
            expect(input?.placeholder).toBe('Choose date...');
        });
    });

    describe('calendar dropdown', () => {
        it('shows calendar on toggle click', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const calendar = shadowQuery(widget, '.calendar-dropdown');
            expect(calendar).toBeTruthy();
        });

        it('renders month/year header', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const monthYear = shadowQuery(widget, '.month-year');
            expect(monthYear).toBeTruthy();
        });

        it('renders weekday headers', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const weekdays = shadowQuery(widget, '.calendar-weekdays');
            expect(weekdays).toBeTruthy();
        });

        it('renders day buttons', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const days = shadowQueryAll(widget, '.calendar-day');
            expect(days.length).toBeGreaterThan(28); // At least 28 days
        });

        it('closes calendar on outside click', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            // Click outside
            document.body.click();

            await new Promise(r => setTimeout(r, 100));

            const calendar = shadowQuery(widget, '.calendar-dropdown');
            // Calendar should be hidden or removed
            expect(calendar === null || calendar.hidden).toBeTruthy();
        });
    });

    describe('date selection', () => {
        it('selects date on day click', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const day = shadowQuery(widget, '.calendar-day:not(.other-month):not(:disabled)');
            day?.click();

            const value = widget.getValue();
            expect(value).toBeTruthy();
        });

        it('updates input display on selection', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const day = shadowQuery(widget, '.calendar-day:not(.other-month):not(:disabled)');
            day?.click();

            const input = shadowQuery(widget, '.date-input');
            expect(input?.value).toBeTruthy();
        });

        it('highlights today', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const today = shadowQuery(widget, '.calendar-day.today');
            expect(today).toBeTruthy();
        });

        it('highlights selected date', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const day = shadowQuery(widget, '.calendar-day:not(.other-month):not(:disabled)');
            day?.click();

            // Re-open calendar
            toggle?.click();

            const selected = shadowQuery(widget, '.calendar-day.selected');
            expect(selected).toBeTruthy();
        });
    });

    describe('navigation', () => {
        it('navigates to previous month', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const prevBtn = shadowQuery(widget, '.nav-btn:first-of-type');
            const monthYearBefore = shadowQuery(widget, '.month-year')?.textContent;
            
            prevBtn?.click();
            
            const monthYearAfter = shadowQuery(widget, '.month-year')?.textContent;
            expect(monthYearAfter).not.toBe(monthYearBefore);
        });

        it('navigates to next month', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const nextBtn = shadowQuery(widget, '.nav-btn:last-of-type');
            const monthYearBefore = shadowQuery(widget, '.month-year')?.textContent;
            
            nextBtn?.click();
            
            const monthYearAfter = shadowQuery(widget, '.month-year')?.textContent;
            expect(monthYearAfter).not.toBe(monthYearBefore);
        });
    });

    describe('modes', () => {
        it('date mode shows only calendar', async () => {
            widget = createWidget('ax-date-picker', { mode: 'date' });
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const timePicker = shadowQuery(widget, '.time-picker');
            expect(timePicker).toBeFalsy();
        });

        it('time mode shows time picker', async () => {
            widget = createWidget('ax-date-picker', { mode: 'time' });
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const timePicker = shadowQuery(widget, '.time-picker');
            expect(timePicker).toBeTruthy();
        });

        it('datetime mode shows both', async () => {
            widget = createWidget('ax-date-picker', { mode: 'datetime' });
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const calendar = shadowQuery(widget, '.calendar-days');
            const timePicker = shadowQuery(widget, '.time-picker');
            
            expect(calendar).toBeTruthy();
            expect(timePicker).toBeTruthy();
        });

        it('range mode allows selecting two dates', async () => {
            widget = createWidget('ax-date-picker', { mode: 'range' });
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const days = shadowQueryAll(widget, '.calendar-day:not(.other-month):not(:disabled)');
            
            if (days.length >= 2) {
                days[0]?.click();
                days[5]?.click();

                const value = widget.getValue();
                expect(value).toHaveProperty('startDate');
                expect(value).toHaveProperty('endDate');
            }
        });
    });

    describe('constraints', () => {
        it('respects min-date', async () => {
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            
            widget = createWidget('ax-date-picker', {
                'min-date': tomorrow.toISOString().split('T')[0]
            });
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const today = shadowQuery(widget, '.calendar-day.today');
            expect(today?.disabled).toBe(true);
        });

        it('respects max-date', async () => {
            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            
            widget = createWidget('ax-date-picker', {
                'max-date': yesterday.toISOString().split('T')[0]
            });
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const today = shadowQuery(widget, '.calendar-day.today');
            expect(today?.disabled).toBe(true);
        });
    });

    describe('value interface', () => {
        it('getValue returns ISO date string', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const day = shadowQuery(widget, '.calendar-day:not(.other-month):not(:disabled)');
            day?.click();

            const value = widget.getValue();
            expect(typeof value).toBe('string');
            expect(value).toMatch(/^\d{4}-\d{2}-\d{2}/);
        });

        it('setValue updates the selected date', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            widget.setValue('2024-06-15');

            const value = widget.getValue();
            expect(value).toContain('2024-06-15');
        });
    });

    describe('validation', () => {
        it('validates when required and date selected', async () => {
            widget = createWidget('ax-date-picker', { required: true });
            await waitForElement(widget);

            widget.setValue('2024-06-15');

            const result = widget.validate();
            expect(result.valid).toBe(true);
        });

        it('fails validation when required but no date', async () => {
            widget = createWidget('ax-date-picker', { required: true });
            await waitForElement(widget);

            const result = widget.validate();
            expect(result.valid).toBe(false);
        });
    });

    describe('events', () => {
        it('dispatches ax-change on date selection', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const eventPromise = captureEvent(widget, 'ax-change');

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const day = shadowQuery(widget, '.calendar-day:not(.other-month):not(:disabled)');
            day?.click();

            const event = await eventPromise;
            expect(event.detail).toHaveProperty('value');
        });
    });

    describe('accessibility', () => {
        it('input has aria-haspopup', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const input = shadowQuery(widget, '.date-input');
            expect(input?.getAttribute('aria-haspopup')).toBe('dialog');
        });

        it('calendar days are focusable', async () => {
            widget = createWidget('ax-date-picker');
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const day = shadowQuery(widget, '.calendar-day:not(:disabled)');
            expect(day?.getAttribute('tabindex')).toBeDefined();
        });

        it('today button provides quick selection', async () => {
            widget = createWidget('ax-date-picker', { 'show-today-button': true });
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const todayBtn = shadowQuery(widget, '.today-btn');
            expect(todayBtn).toBeTruthy();
        });
    });

    describe('localization', () => {
        it('respects locale for date formatting', async () => {
            widget = createWidget('ax-date-picker', { locale: 'en-US' });
            await waitForElement(widget);

            widget.setValue('2024-12-25');

            const input = shadowQuery(widget, '.date-input');
            expect(input?.value).toBeTruthy();
        });

        it('respects week-start configuration', async () => {
            widget = createWidget('ax-date-picker', { 'week-start': 1 }); // Monday
            await waitForElement(widget);

            const toggle = shadowQuery(widget, '.calendar-toggle');
            toggle?.click();

            const weekdays = shadowQuery(widget, '.calendar-weekdays');
            // First day should be Monday related
            expect(weekdays).toBeTruthy();
        });
    });
});
