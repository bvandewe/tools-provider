/**
 * Tests for ax-rating widget
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createWidget, cleanup, shadowQuery, shadowQueryAll, captureEvent, waitForElement, click } from './test-utils.js';
import '../src/scripts/components/ax-rating.js';

describe('AxRating', () => {
    let widget;

    afterEach(() => {
        cleanup();
    });

    describe('rendering', () => {
        it('renders 5 stars by default', async () => {
            widget = createWidget('ax-rating');
            await waitForElement(widget);

            const stars = shadowQueryAll(widget, '.star');
            expect(stars.length).toBe(5);
        });

        it('renders custom number of stars', async () => {
            widget = createWidget('ax-rating', { max: 10 });
            await waitForElement(widget);

            const stars = shadowQueryAll(widget, '.star');
            expect(stars.length).toBe(10);
        });

        it('shows prompt when provided', async () => {
            widget = createWidget('ax-rating', { prompt: 'Rate your experience' });
            await waitForElement(widget);

            const prompt = shadowQuery(widget, '.prompt');
            expect(prompt.textContent).toBe('Rate your experience');
        });

        it('shows value display when show-value is set', async () => {
            widget = createWidget('ax-rating', { 'show-value': true, value: 3 });
            await waitForElement(widget);

            const display = shadowQuery(widget, '.value-display');
            expect(display).toBeTruthy();
            expect(display.textContent).toContain('3');
        });
    });

    describe('value interface', () => {
        it('getValue returns current rating', async () => {
            widget = createWidget('ax-rating', { value: 4 });
            await waitForElement(widget);

            expect(widget.getValue()).toBe(4);
        });

        it('setValue updates the rating', async () => {
            widget = createWidget('ax-rating');
            await waitForElement(widget);

            widget.setValue(3);
            expect(widget.getValue()).toBe(3);
        });

        it('setValue clamps to max', async () => {
            widget = createWidget('ax-rating', { max: 5 });
            await waitForElement(widget);

            widget.setValue(10);
            expect(widget.getValue()).toBe(5);
        });
    });

    describe('visual state', () => {
        it('fills stars up to current value', async () => {
            widget = createWidget('ax-rating', { value: 3 });
            await waitForElement(widget);

            const filledStars = shadowQueryAll(widget, '.star.filled');
            expect(filledStars.length).toBe(3);
        });
    });

    describe('validation', () => {
        it('validates required rating', async () => {
            widget = createWidget('ax-rating', { required: true });
            await waitForElement(widget);

            const result = widget.validate();
            expect(result.valid).toBe(false);
            expect(result.errors[0]).toContain('rating');
        });

        it('passes validation when rating provided', async () => {
            widget = createWidget('ax-rating', { required: true, value: 3 });
            await waitForElement(widget);

            const result = widget.validate();
            expect(result.valid).toBe(true);
        });
    });

    describe('events', () => {
        it('dispatches ax-response on star click', async () => {
            widget = createWidget('ax-rating');
            await waitForElement(widget);

            const eventPromise = captureEvent(widget, 'ax-response');
            const stars = shadowQueryAll(widget, '.star');

            click(stars[2]); // Click 3rd star

            const event = await eventPromise;
            expect(event.detail.value).toBe(3);
        });
    });

    describe('disabled/readonly', () => {
        it('readonly prevents interaction', async () => {
            widget = createWidget('ax-rating', { readonly: true, value: 3 });
            await waitForElement(widget);

            const stars = shadowQueryAll(widget, '.star');
            click(stars[4]); // Try to click 5th star

            // Value should remain unchanged
            expect(widget.getValue()).toBe(3);
        });
    });
});
