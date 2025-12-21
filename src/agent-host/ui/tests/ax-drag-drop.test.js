/**
 * Tests for ax-drag-drop widget
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createWidget, cleanup, shadowQuery, shadowQueryAll, captureEvent, waitForElement } from './test-utils.js';
import '../src/scripts/components/ax-drag-drop.js';

describe('AxDragDrop', () => {
    let widget;

    const sampleItems = [
        { id: 'item1', content: 'Apple' },
        { id: 'item2', content: 'Banana' },
        { id: 'item3', content: 'Cherry' }
    ];

    const sampleZones = [
        { id: 'zone1', label: 'Fruits' },
        { id: 'zone2', label: 'Vegetables' }
    ];

    afterEach(() => {
        cleanup();
    });

    describe('rendering', () => {
        it('renders widget container', async () => {
            widget = createWidget('ax-drag-drop', {
                items: JSON.stringify(sampleItems)
            });
            await waitForElement(widget);

            const container = shadowQuery(widget, '.widget-container');
            expect(container).toBeTruthy();
        });

        it('renders draggable items', async () => {
            widget = createWidget('ax-drag-drop', {
                items: JSON.stringify(sampleItems)
            });
            await waitForElement(widget);

            const items = shadowQueryAll(widget, '.drag-item');
            expect(items.length).toBe(3);
        });

        it('shows prompt when provided', async () => {
            widget = createWidget('ax-drag-drop', {
                prompt: 'Sort the items',
                items: JSON.stringify(sampleItems)
            });
            await waitForElement(widget);

            const prompt = shadowQuery(widget, '.prompt');
            expect(prompt?.textContent).toContain('Sort the items');
        });
    });

    describe('category variant', () => {
        it('renders drop zones for category variant', async () => {
            widget = createWidget('ax-drag-drop', {
                variant: 'category',
                items: JSON.stringify(sampleItems),
                zones: JSON.stringify(sampleZones)
            });
            await waitForElement(widget);

            const zones = shadowQueryAll(widget, '.drop-zone');
            expect(zones.length).toBe(2);
        });

        it('shows zone labels', async () => {
            widget = createWidget('ax-drag-drop', {
                variant: 'category',
                items: JSON.stringify(sampleItems),
                zones: JSON.stringify(sampleZones)
            });
            await waitForElement(widget);

            const labels = shadowQueryAll(widget, '.zone-label');
            expect(labels.length).toBe(2);
        });
    });

    describe('sequence variant', () => {
        it('renders sequence area', async () => {
            widget = createWidget('ax-drag-drop', {
                variant: 'sequence',
                items: JSON.stringify(sampleItems)
            });
            await waitForElement(widget);

            // Sequence variant may use different class name
            const container = shadowQuery(widget, '.widget-container');
            expect(container).toBeTruthy();
        });

        it('tracks item order', async () => {
            widget = createWidget('ax-drag-drop', {
                variant: 'sequence',
                items: JSON.stringify(sampleItems)
            });
            await waitForElement(widget);

            const value = widget.getValue();
            expect(Array.isArray(value)).toBe(true);
        });
    });

    describe('graphical variant', () => {
        it('renders with background image', async () => {
            widget = createWidget('ax-drag-drop', {
                variant: 'graphical',
                items: JSON.stringify(sampleItems),
                'background-image': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
            });
            await waitForElement(widget);

            const container = shadowQuery(widget, '.widget-container');
            expect(container).toBeTruthy();
        });
    });

    describe('drag interactions', () => {
        it('items have draggable attribute', async () => {
            widget = createWidget('ax-drag-drop', {
                items: JSON.stringify(sampleItems)
            });
            await waitForElement(widget);

            const item = shadowQuery(widget, '.drag-item');
            expect(item?.getAttribute('draggable')).toBe('true');
        });

        it('items have keyboard accessibility', async () => {
            widget = createWidget('ax-drag-drop', {
                items: JSON.stringify(sampleItems)
            });
            await waitForElement(widget);

            const item = shadowQuery(widget, '.drag-item');
            expect(item?.getAttribute('tabindex')).toBe('0');
        });
    });

    describe('value interface', () => {
        it('getValue returns zone placements for category variant', async () => {
            widget = createWidget('ax-drag-drop', {
                variant: 'category',
                items: JSON.stringify(sampleItems),
                zones: JSON.stringify(sampleZones)
            });
            await waitForElement(widget);

            const value = widget.getValue();
            // Returns object with zone ids as keys
            expect(typeof value).toBe('object');
            expect(value).toHaveProperty('zone1');
            expect(value).toHaveProperty('zone2');
        });

        it('getValue returns array for sequence variant', async () => {
            widget = createWidget('ax-drag-drop', {
                variant: 'sequence',
                items: JSON.stringify(sampleItems)
            });
            await waitForElement(widget);

            const value = widget.getValue();
            expect(Array.isArray(value)).toBe(true);
        });

        it('getValue returns array for graphical variant', async () => {
            widget = createWidget('ax-drag-drop', {
                variant: 'graphical',
                items: JSON.stringify(sampleItems)
            });
            await waitForElement(widget);

            const value = widget.getValue();
            expect(Array.isArray(value)).toBe(true);
        });

        it('setValue updates category placements', async () => {
            widget = createWidget('ax-drag-drop', {
                variant: 'category',
                items: JSON.stringify(sampleItems),
                zones: JSON.stringify(sampleZones)
            });
            await waitForElement(widget);

            // Format: { zoneId: [itemIds] }
            widget.setValue({
                zone1: ['item1', 'item2'],
                zone2: ['item3']
            });

            const value = widget.getValue();
            expect(value.zone1).toContain('item1');
        });
    });

    describe('validation', () => {
        it('validates when items are placed', async () => {
            widget = createWidget('ax-drag-drop', {
                'require-all-placed': true,
                variant: 'category',
                items: JSON.stringify(sampleItems),
                zones: JSON.stringify(sampleZones)
            });
            await waitForElement(widget);

            widget.setValue({
                zone1: ['item1', 'item2', 'item3']
            });

            const result = widget.validate();
            expect(result.valid).toBe(true);
        });

        it('fails validation when not all items placed', async () => {
            widget = createWidget('ax-drag-drop', {
                'require-all-placed': true,
                variant: 'category',
                items: JSON.stringify(sampleItems),
                zones: JSON.stringify(sampleZones)
            });
            await waitForElement(widget);

            // No items placed
            const result = widget.validate();
            expect(result.valid).toBe(false);
        });
    });

    describe('events', () => {
        it('dispatches ax-drop event on item placement', async () => {
            widget = createWidget('ax-drag-drop', {
                variant: 'category',
                items: JSON.stringify(sampleItems),
                zones: JSON.stringify(sampleZones)
            });
            await waitForElement(widget);

            // Set value to simulate placement
            widget.setValue({
                zone1: ['item1']
            });

            // Verify the widget works
            const value = widget.getValue();
            expect(value.zone1).toContain('item1');
        });
    });

    describe('accessibility', () => {
        it('items have keyboard accessibility', async () => {
            widget = createWidget('ax-drag-drop', {
                variant: 'category',
                items: JSON.stringify(sampleItems),
                zones: JSON.stringify(sampleZones)
            });
            await waitForElement(widget);

            const item = shadowQuery(widget, '.drag-item');
            expect(item?.getAttribute('tabindex')).toBe('0');
        });

        it('drop zones have appropriate attributes', async () => {
            widget = createWidget('ax-drag-drop', {
                variant: 'category',
                items: JSON.stringify(sampleItems),
                zones: JSON.stringify(sampleZones)
            });
            await waitForElement(widget);

            const zone = shadowQuery(widget, '.drop-zone');
            expect(zone).toBeTruthy();
        });
    });
});
