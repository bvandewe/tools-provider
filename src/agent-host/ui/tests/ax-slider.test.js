/**
 * Tests for ax-slider widget
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createWidget, cleanup, shadowQuery, captureEvent, waitForElement } from './test-utils.js';
import '../src/scripts/components/ax-slider.js';

describe('AxSlider', () => {
    let widget;

    afterEach(() => {
        cleanup();
    });

    describe('rendering', () => {
        it('renders with default values', async () => {
            widget = createWidget('ax-slider');
            await waitForElement(widget);

            const slider = shadowQuery(widget, '.slider-input');
            expect(slider).toBeTruthy();
            expect(slider.min).toBe('0');
            expect(slider.max).toBe('100');
        });

        it('renders with custom min/max/step', async () => {
            widget = createWidget('ax-slider', {
                min: 10,
                max: 50,
                step: 5,
            });
            await waitForElement(widget);

            const slider = shadowQuery(widget, '.slider-input');
            expect(slider.min).toBe('10');
            expect(slider.max).toBe('50');
            expect(slider.step).toBe('5');
        });

        it('shows prompt when provided', async () => {
            widget = createWidget('ax-slider', { prompt: 'Rate this' });
            await waitForElement(widget);

            const prompt = shadowQuery(widget, '.prompt');
            expect(prompt.textContent).toBe('Rate this');
        });

        it('shows value display when show-value is set', async () => {
            widget = createWidget('ax-slider', { 'show-value': true, value: 50 });
            await waitForElement(widget);

            const display = shadowQuery(widget, '.value-display');
            expect(display).toBeTruthy();
            expect(display.textContent).toContain('50');
        });

        it('shows labels when show-labels is set', async () => {
            widget = createWidget('ax-slider', { 'show-labels': true, min: 0, max: 100 });
            await waitForElement(widget);

            const labels = shadowQuery(widget, '.labels-row');
            expect(labels).toBeTruthy();
        });
    });

    describe('value interface', () => {
        it('getValue returns current value', async () => {
            widget = createWidget('ax-slider', { value: 75 });
            await waitForElement(widget);

            expect(widget.getValue()).toBe(75);
        });

        it('setValue updates the slider', async () => {
            widget = createWidget('ax-slider');
            await waitForElement(widget);

            widget.setValue(30);
            expect(widget.getValue()).toBe(30);
        });

        it('setValue clamps to min/max', async () => {
            widget = createWidget('ax-slider', { min: 0, max: 100 });
            await waitForElement(widget);

            widget.setValue(150);
            expect(widget.getValue()).toBe(100);

            widget.setValue(-10);
            expect(widget.getValue()).toBe(0);
        });
    });

    describe('validation', () => {
        it('validates value within range', async () => {
            widget = createWidget('ax-slider', { min: 0, max: 100, value: 50 });
            await waitForElement(widget);

            const result = widget.validate();
            expect(result.valid).toBe(true);
            expect(result.errors).toHaveLength(0);
        });
    });

    describe('events', () => {
        it('dispatches ax-response on change', async () => {
            widget = createWidget('ax-slider');
            await waitForElement(widget);

            const eventPromise = captureEvent(widget, 'ax-response');
            const slider = shadowQuery(widget, '.slider-input');

            slider.value = 42;
            slider.dispatchEvent(new Event('change', { bubbles: true }));

            const event = await eventPromise;
            expect(event.detail.value).toBe(42);
        });
    });

    describe('disabled state', () => {
        it('disables the slider input', async () => {
            widget = createWidget('ax-slider', { disabled: true });
            await waitForElement(widget);

            const slider = shadowQuery(widget, '.slider-input');
            expect(slider.disabled).toBe(true);
        });
    });
});
