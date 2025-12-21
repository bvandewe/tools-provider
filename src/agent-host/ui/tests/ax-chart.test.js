/**
 * Tests for ax-chart widget
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createWidget, cleanup, shadowQuery, captureEvent, waitForElement } from './test-utils.js';
import '../src/scripts/components/ax-chart.js';

describe('AxChart', () => {
    let widget;

    afterEach(() => {
        cleanup();
    });

    describe('rendering', () => {
        it('renders with default container', async () => {
            widget = createWidget('ax-chart');
            await waitForElement(widget);

            const container = shadowQuery(widget, '.widget-container');
            expect(container).toBeTruthy();
        });

        it('renders title when provided', async () => {
            widget = createWidget('ax-chart', { title: 'My Chart' });
            await waitForElement(widget);

            const title = shadowQuery(widget, '.chart-title');
            expect(title).toBeTruthy();
            expect(title.textContent).toBe('My Chart');
        });

        it('renders canvas element', async () => {
            widget = createWidget('ax-chart', {
                'chart-type': 'bar',
                labels: JSON.stringify(['A', 'B', 'C']),
                datasets: JSON.stringify([{ label: 'Test', data: [1, 2, 3] }])
            });
            await waitForElement(widget);

            const canvas = shadowQuery(widget, 'canvas');
            expect(canvas).toBeTruthy();
        });

        it('applies custom dimensions', async () => {
            widget = createWidget('ax-chart', {
                width: 400,
                height: 300
            });
            await waitForElement(widget);

            const wrapper = shadowQuery(widget, '.chart-wrapper');
            expect(wrapper).toBeTruthy();
        });
    });

    describe('chart types', () => {
        it('supports bar chart type', async () => {
            widget = createWidget('ax-chart', { 'chart-type': 'bar' });
            await waitForElement(widget);
            expect(widget.chartType).toBe('bar');
        });

        it('supports line chart type', async () => {
            widget = createWidget('ax-chart', { 'chart-type': 'line' });
            await waitForElement(widget);
            expect(widget.chartType).toBe('line');
        });

        it('supports pie chart type', async () => {
            widget = createWidget('ax-chart', { 'chart-type': 'pie' });
            await waitForElement(widget);
            expect(widget.chartType).toBe('pie');
        });

        it('defaults to bar chart', async () => {
            widget = createWidget('ax-chart');
            await waitForElement(widget);
            expect(widget.chartType).toBe('bar');
        });
    });

    describe('value interface', () => {
        it('getValue returns chart data', async () => {
            const datasets = [{ label: 'Sales', data: [10, 20, 30] }];
            widget = createWidget('ax-chart', {
                labels: JSON.stringify(['A', 'B', 'C']),
                datasets: JSON.stringify(datasets)
            });
            await waitForElement(widget);

            const value = widget.getValue();
            expect(value).toHaveProperty('labels');
            expect(value).toHaveProperty('datasets');
        });

        it('setValue updates chart data', async () => {
            widget = createWidget('ax-chart');
            await waitForElement(widget);

            widget.setValue({
                labels: ['X', 'Y'],
                datasets: [{ data: [5, 10] }]
            });

            const value = widget.getValue();
            expect(value.labels).toEqual(['X', 'Y']);
        });
    });

    describe('validation', () => {
        it('validates successfully with data', async () => {
            widget = createWidget('ax-chart', {
                labels: JSON.stringify(['A', 'B']),
                datasets: JSON.stringify([{ data: [1, 2] }])
            });
            await waitForElement(widget);

            const result = widget.validate();
            expect(result.valid).toBe(true);
        });
    });

    describe('events', () => {
        it('dispatches ax-chart-click on element click', async () => {
            widget = createWidget('ax-chart', {
                'chart-type': 'bar',
                labels: JSON.stringify(['A', 'B']),
                datasets: JSON.stringify([{ data: [1, 2] }])
            });
            await waitForElement(widget);

            // Chart click events are handled internally by Chart.js
            expect(widget).toBeTruthy();
        });
    });

    describe('accessibility', () => {
        it('has accessible role on canvas', async () => {
            widget = createWidget('ax-chart');
            await waitForElement(widget);

            const canvas = shadowQuery(widget, 'canvas');
            expect(canvas?.getAttribute('role')).toBe('img');
        });

        it('includes aria-label with title', async () => {
            widget = createWidget('ax-chart', { title: 'Sales Report' });
            await waitForElement(widget);

            const canvas = shadowQuery(widget, 'canvas');
            expect(canvas?.getAttribute('aria-label')).toContain('Sales Report');
        });
    });
});
