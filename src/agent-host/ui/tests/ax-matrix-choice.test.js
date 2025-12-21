/**
 * Tests for ax-matrix-choice widget
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createWidget, cleanup, shadowQuery, shadowQueryAll, captureEvent, waitForElement } from './test-utils.js';
import '../src/scripts/components/ax-matrix-choice.js';

describe('AxMatrixChoice', () => {
    let widget;

    const sampleRows = [
        { id: 'row1', label: 'Quality', description: 'Product quality' },
        { id: 'row2', label: 'Service', description: 'Customer service' },
        { id: 'row3', label: 'Value', description: 'Value for money' }
    ];

    const sampleColumns = [
        { id: 'col1', label: 'Poor' },
        { id: 'col2', label: 'Fair' },
        { id: 'col3', label: 'Good' },
        { id: 'col4', label: 'Excellent' }
    ];

    afterEach(() => {
        cleanup();
    });

    describe('rendering', () => {
        it('renders matrix table', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            const table = shadowQuery(widget, '.matrix-table');
            expect(table).toBeTruthy();
        });

        it('renders column headers', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            const headers = shadowQueryAll(widget, 'thead th');
            // First column is for row labels, then 4 columns
            expect(headers.length).toBe(5);
        });

        it('renders row labels', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            const rowLabels = shadowQueryAll(widget, '.row-label');
            expect(rowLabels.length).toBe(3);
        });

        it('shows prompt when provided', async () => {
            widget = createWidget('ax-matrix-choice', {
                prompt: 'Rate the following',
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            const prompt = shadowQuery(widget, '.prompt');
            expect(prompt?.textContent).toContain('Rate the following');
        });

        it('shows row descriptions', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            const descriptions = shadowQueryAll(widget, '.row-description');
            expect(descriptions.length).toBe(3);
        });
    });

    describe('selection mode', () => {
        it('uses radio buttons for single selection (default)', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            const radios = shadowQueryAll(widget, 'input[type="radio"]');
            expect(radios.length).toBeGreaterThan(0);
        });

        it('uses checkboxes for multiple selection', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns),
                'allow-multiple': true
            });
            await waitForElement(widget);

            const checkboxes = shadowQueryAll(widget, 'input[type="checkbox"]');
            expect(checkboxes.length).toBeGreaterThan(0);
        });
    });

    describe('selection behavior', () => {
        it('selects cell on click', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            const input = shadowQuery(widget, 'tbody input');
            input?.click();

            const value = widget.getValue();
            expect(Object.keys(value.selections).length).toBeGreaterThan(0);
        });

        it('only one column selected per row in single mode', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            // Select first cell in first row
            const firstRowInputs = shadowQueryAll(widget, 'tbody tr:first-child input');
            firstRowInputs[0]?.click();
            firstRowInputs[1]?.click();

            const value = widget.getValue();
            // In single mode, should only have one selection per row
            expect(value.selections['row1']?.length).toBe(1);
        });

        it('allows multiple columns per row in multiple mode', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns),
                'allow-multiple': true
            });
            await waitForElement(widget);

            const firstRowInputs = shadowQueryAll(widget, 'tbody tr:first-child input');
            firstRowInputs[0]?.click();
            firstRowInputs[1]?.click();

            const value = widget.getValue();
            expect(value.selections['row1']?.length).toBe(2);
        });
    });

    describe('progress indicator', () => {
        it('shows progress when show-progress is set', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns),
                'show-progress': true
            });
            await waitForElement(widget);

            const progress = shadowQuery(widget, '.matrix-progress');
            expect(progress).toBeTruthy();
        });

        it('updates progress on selection', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns),
                'show-progress': true
            });
            await waitForElement(widget);

            const input = shadowQuery(widget, 'tbody tr:first-child input');
            input?.click();

            const progressText = shadowQuery(widget, '.progress-text');
            expect(progressText?.textContent).toContain('1');
        });
    });

    describe('value interface', () => {
        it('getValue returns selections map', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            const value = widget.getValue();
            expect(value).toHaveProperty('selections');
            expect(typeof value.selections).toBe('object');
        });

        it('setValue updates selections', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            widget.setValue({
                selections: {
                    row1: ['col2'],
                    row2: ['col3']
                }
            });

            const value = widget.getValue();
            expect(value.selections['row1']).toContain('col2');
        });
    });

    describe('validation', () => {
        it('validates when all rows answered (require-all)', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns),
                'require-all-rows': true
            });
            await waitForElement(widget);

            widget.setValue({
                selections: {
                    row1: ['col1'],
                    row2: ['col2'],
                    row3: ['col3']
                }
            });

            const result = widget.validate();
            expect(result.valid).toBe(true);
        });

        it('fails validation when not all rows answered (require-all)', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns),
                'require-all-rows': true
            });
            await waitForElement(widget);

            widget.setValue({
                selections: {
                    row1: ['col1']
                }
            });

            const result = widget.validate();
            expect(result.valid).toBe(false);
        });

        it('validates when required and at least one selection', async () => {
            widget = createWidget('ax-matrix-choice', {
                required: true,
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            const input = shadowQuery(widget, 'tbody input');
            input?.click();

            const result = widget.validate();
            expect(result.valid).toBe(true);
        });
    });

    describe('events', () => {
        it('dispatches ax-change on selection', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            const eventPromise = captureEvent(widget, 'ax-change');

            const input = shadowQuery(widget, 'tbody input');
            input?.click();

            const event = await eventPromise;
            expect(event.detail).toHaveProperty('selections');
        });
    });

    describe('accessibility', () => {
        it('has proper table structure', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            const table = shadowQuery(widget, 'table');
            expect(table?.querySelector('thead')).toBeTruthy();
            expect(table?.querySelector('tbody')).toBeTruthy();
        });

        it('inputs are associated with labels', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            const label = shadowQuery(widget, '.matrix-cell label');
            expect(label).toBeTruthy();
        });

        it('radio groups share name per row', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns)
            });
            await waitForElement(widget);

            const row1Inputs = shadowQueryAll(widget, 'tbody tr:first-child input[type="radio"]');
            if (row1Inputs.length >= 2) {
                expect(row1Inputs[0].name).toBe(row1Inputs[1].name);
            }
        });
    });

    describe('shuffle', () => {
        it('can shuffle rows', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns),
                'shuffle-rows': true
            });
            await waitForElement(widget);

            // Widget should render without error
            const rows = shadowQueryAll(widget, 'tbody tr');
            expect(rows.length).toBe(3);
        });

        it('can shuffle columns', async () => {
            widget = createWidget('ax-matrix-choice', {
                rows: JSON.stringify(sampleRows),
                columns: JSON.stringify(sampleColumns),
                'shuffle-columns': true
            });
            await waitForElement(widget);

            // Widget should render without error
            const headers = shadowQueryAll(widget, 'thead th');
            expect(headers.length).toBe(5);
        });
    });
});
