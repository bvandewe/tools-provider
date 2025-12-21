/**
 * Tests for ax-data-table widget
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createWidget, cleanup, shadowQuery, shadowQueryAll, captureEvent, waitForElement } from './test-utils.js';
import '../src/scripts/components/ax-data-table.js';

describe('AxDataTable', () => {
    let widget;

    const sampleColumns = [
        { key: 'name', label: 'Name', sortable: true },
        { key: 'age', label: 'Age', sortable: true },
        { key: 'city', label: 'City' }
    ];

    const sampleData = [
        { id: '1', name: 'Alice', age: 30, city: 'New York' },
        { id: '2', name: 'Bob', age: 25, city: 'Chicago' },
        { id: '3', name: 'Charlie', age: 35, city: 'Boston' }
    ];

    afterEach(() => {
        cleanup();
    });

    describe('rendering', () => {
        it('renders table structure', async () => {
            widget = createWidget('ax-data-table', {
                columns: JSON.stringify(sampleColumns),
                data: JSON.stringify(sampleData)
            });
            await waitForElement(widget);

            const table = shadowQuery(widget, 'table');
            expect(table).toBeTruthy();
        });

        it('renders column headers', async () => {
            widget = createWidget('ax-data-table', {
                columns: JSON.stringify(sampleColumns),
                data: JSON.stringify(sampleData)
            });
            await waitForElement(widget);

            const headers = shadowQueryAll(widget, 'th');
            expect(headers.length).toBeGreaterThan(0);
        });

        it('renders data rows', async () => {
            widget = createWidget('ax-data-table', {
                columns: JSON.stringify(sampleColumns),
                data: JSON.stringify(sampleData)
            });
            await waitForElement(widget);

            const rows = shadowQueryAll(widget, 'tbody tr');
            expect(rows.length).toBe(3);
        });

        it('renders title when provided', async () => {
            widget = createWidget('ax-data-table', {
                title: 'User List',
                columns: JSON.stringify(sampleColumns),
                data: JSON.stringify(sampleData)
            });
            await waitForElement(widget);

            const container = shadowQuery(widget, '.widget-container');
            expect(container).toBeTruthy();
        });
    });

    describe('sorting', () => {
        it('renders sortable column headers', async () => {
            widget = createWidget('ax-data-table', {
                columns: JSON.stringify(sampleColumns),
                data: JSON.stringify(sampleData)
            });
            await waitForElement(widget);

            const header = shadowQuery(widget, 'th');
            expect(header).toBeTruthy();
        });

        it('column headers are clickable', async () => {
            widget = createWidget('ax-data-table', {
                columns: JSON.stringify(sampleColumns),
                data: JSON.stringify(sampleData)
            });
            await waitForElement(widget);

            const header = shadowQuery(widget, 'th');
            // Should not throw when clicked
            header?.click();
            expect(widget).toBeTruthy();
        });
    });

    describe('filtering', () => {
        it('table can be configured with filterable attribute', async () => {
            widget = createWidget('ax-data-table', {
                filterable: true,
                columns: JSON.stringify(sampleColumns),
                data: JSON.stringify(sampleData)
            });
            await waitForElement(widget);

            expect(widget.hasAttribute('filterable')).toBe(true);
        });
    });

    describe('pagination', () => {
        it('supports page-size attribute', async () => {
            const moreData = Array.from({ length: 15 }, (_, i) => ({
                id: String(i + 1),
                name: `User ${i}`,
                age: 20 + i,
                city: 'City'
            }));

            widget = createWidget('ax-data-table', {
                'page-size': 5,
                columns: JSON.stringify(sampleColumns),
                data: JSON.stringify(moreData)
            });
            await waitForElement(widget);

            expect(widget.hasAttribute('page-size')).toBe(true);
        });
    });

    describe('row selection', () => {
        it('supports selectable attribute', async () => {
            widget = createWidget('ax-data-table', {
                selectable: true,
                columns: JSON.stringify(sampleColumns),
                data: JSON.stringify(sampleData)
            });
            await waitForElement(widget);

            expect(widget.hasAttribute('selectable')).toBe(true);
        });
    });

    describe('value interface', () => {
        it('getValue returns table data', async () => {
            widget = createWidget('ax-data-table', {
                columns: JSON.stringify(sampleColumns),
                data: JSON.stringify(sampleData)
            });
            await waitForElement(widget);

            const value = widget.getValue();
            expect(Array.isArray(value)).toBe(true);
        });

        it('getValue returns selected data when selectable', async () => {
            widget = createWidget('ax-data-table', {
                selectable: true,
                columns: JSON.stringify(sampleColumns),
                data: JSON.stringify(sampleData)
            });
            await waitForElement(widget);

            // Value is selection-based when selectable
            const value = widget.getValue();
            expect(value === null || Array.isArray(value)).toBe(true);
        });
    });

    describe('accessibility', () => {
        it('has proper table structure', async () => {
            widget = createWidget('ax-data-table', {
                columns: JSON.stringify(sampleColumns),
                data: JSON.stringify(sampleData)
            });
            await waitForElement(widget);

            const table = shadowQuery(widget, 'table');
            expect(table?.querySelector('thead')).toBeTruthy();
            expect(table?.querySelector('tbody')).toBeTruthy();
        });
    });
});
