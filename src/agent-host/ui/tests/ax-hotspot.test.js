/**
 * Tests for ax-hotspot widget
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createWidget, cleanup, shadowQuery, shadowQueryAll, captureEvent, waitForElement } from './test-utils.js';
import '../src/scripts/components/ax-hotspot.js';

describe('AxHotspot', () => {
    let widget;

    // 1x1 transparent PNG
    const testImage = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=';

    const sampleRegions = [
        { id: 'region1', shape: 'rect', coords: { x: 10, y: 10, width: 20, height: 20 }, label: 'Area 1' },
        { id: 'region2', shape: 'circle', coords: { x: 50, y: 50, radius: 15 }, label: 'Area 2' }
    ];

    afterEach(() => {
        cleanup();
    });

    describe('rendering', () => {
        it('renders widget container', async () => {
            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(sampleRegions)
            });
            await waitForElement(widget);

            const container = shadowQuery(widget, '.widget-container');
            expect(container).toBeTruthy();
        });

        it('renders image', async () => {
            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(sampleRegions)
            });
            await waitForElement(widget);

            const img = shadowQuery(widget, '.hotspot-image');
            expect(img).toBeTruthy();
            expect(img?.src).toContain('data:image');
        });

        it('renders hotspot regions', async () => {
            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(sampleRegions)
            });
            await waitForElement(widget);

            const regions = shadowQueryAll(widget, '.hotspot-region');
            expect(regions.length).toBe(2);
        });

        it('shows prompt when provided', async () => {
            widget = createWidget('ax-hotspot', {
                prompt: 'Click on the correct area',
                image: testImage,
                regions: JSON.stringify(sampleRegions)
            });
            await waitForElement(widget);

            const prompt = shadowQuery(widget, '.prompt');
            expect(prompt?.textContent).toContain('Click on the correct area');
        });
    });

    describe('region shapes', () => {
        it('renders rectangular regions', async () => {
            const rectRegions = [
                { id: 'rect1', shape: 'rect', coords: { x: 10, y: 10, width: 30, height: 20 } }
            ];

            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(rectRegions)
            });
            await waitForElement(widget);

            const region = shadowQuery(widget, '.region-rect');
            expect(region).toBeTruthy();
        });

        it('renders circular regions', async () => {
            const circleRegions = [
                { id: 'circle1', shape: 'circle', coords: { x: 50, y: 50, radius: 25 } }
            ];

            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(circleRegions)
            });
            await waitForElement(widget);

            const region = shadowQuery(widget, '.region-circle');
            expect(region).toBeTruthy();
        });

        it('renders polygon regions via SVG', async () => {
            const polygonRegions = [
                { id: 'poly1', shape: 'polygon', coords: { points: [[10, 10], [50, 10], [30, 40]] } }
            ];

            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(polygonRegions)
            });
            await waitForElement(widget);

            const svg = shadowQuery(widget, '.hotspot-svg-overlay');
            expect(svg).toBeTruthy();
        });
    });

    describe('selection', () => {
        it('selects region on click', async () => {
            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(sampleRegions)
            });
            await waitForElement(widget);

            const region = shadowQuery(widget, '.hotspot-region');
            region?.click();

            const value = widget.getValue();
            expect(value.selectedRegions.length).toBe(1);
        });

        it('supports single selection mode', async () => {
            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(sampleRegions),
                'selection-mode': 'single'
            });
            await waitForElement(widget);

            const regions = shadowQueryAll(widget, '.hotspot-region');
            regions[0]?.click();
            regions[1]?.click();

            const value = widget.getValue();
            expect(value.selectedRegions.length).toBe(1);
        });

        it('supports multiple selection mode', async () => {
            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(sampleRegions),
                'selection-mode': 'multiple'
            });
            await waitForElement(widget);

            const regions = shadowQueryAll(widget, '.hotspot-region');
            regions[0]?.click();
            regions[1]?.click();

            const value = widget.getValue();
            expect(value.selectedRegions.length).toBe(2);
        });

        it('toggles selection on repeated click', async () => {
            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(sampleRegions),
                'selection-mode': 'multiple'
            });
            await waitForElement(widget);

            const region = shadowQuery(widget, '.hotspot-region');
            region?.click();
            region?.click();

            const value = widget.getValue();
            expect(value.selectedRegions.length).toBe(0);
        });
    });

    describe('value interface', () => {
        it('getValue returns selected regions', async () => {
            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(sampleRegions)
            });
            await waitForElement(widget);

            const value = widget.getValue();
            expect(value).toHaveProperty('selectedRegions');
            expect(Array.isArray(value.selectedRegions)).toBe(true);
        });

        it('setValue updates selection', async () => {
            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(sampleRegions)
            });
            await waitForElement(widget);

            widget.setValue({ selectedRegions: ['region1'] });

            const value = widget.getValue();
            expect(value.selectedRegions).toContain('region1');
        });
    });

    describe('validation', () => {
        it('validates when required and region selected', async () => {
            widget = createWidget('ax-hotspot', {
                required: true,
                image: testImage,
                regions: JSON.stringify(sampleRegions)
            });
            await waitForElement(widget);

            const region = shadowQuery(widget, '.hotspot-region');
            region?.click();

            const result = widget.validate();
            expect(result.valid).toBe(true);
        });

        it('fails validation when required but nothing selected', async () => {
            widget = createWidget('ax-hotspot', {
                required: true,
                image: testImage,
                regions: JSON.stringify(sampleRegions)
            });
            await waitForElement(widget);

            const result = widget.validate();
            expect(result.valid).toBe(false);
        });
    });

    describe('feedback', () => {
        it('shows correct feedback for regions', async () => {
            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(sampleRegions)
            });
            await waitForElement(widget);

            widget.showFeedback({ region1: true, region2: false });

            const correctRegion = shadowQuery(widget, '.correct');
            const incorrectRegion = shadowQuery(widget, '.incorrect');

            expect(correctRegion || incorrectRegion).toBeTruthy();
        });
    });

    describe('events', () => {
        it('dispatches ax-response on selection', async () => {
            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(sampleRegions)
            });
            await waitForElement(widget);

            const eventPromise = captureEvent(widget, 'ax-response');

            const region = shadowQuery(widget, '.hotspot-region');
            region?.click();

            const event = await eventPromise;
            expect(event.detail).toHaveProperty('selectedRegions');
        });
    });

    describe('accessibility', () => {
        it('regions are keyboard focusable', async () => {
            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(sampleRegions)
            });
            await waitForElement(widget);

            const region = shadowQuery(widget, '.hotspot-region');
            expect(region?.getAttribute('tabindex')).toBe('0');
        });

        it('regions have role button', async () => {
            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(sampleRegions)
            });
            await waitForElement(widget);

            const region = shadowQuery(widget, '.hotspot-region');
            expect(region?.getAttribute('role')).toBe('button');
        });

        it('selected regions have aria-pressed', async () => {
            widget = createWidget('ax-hotspot', {
                image: testImage,
                regions: JSON.stringify(sampleRegions)
            });
            await waitForElement(widget);

            const region = shadowQuery(widget, '.hotspot-region');
            region?.click();

            expect(region?.getAttribute('aria-pressed')).toBe('true');
        });
    });
});
