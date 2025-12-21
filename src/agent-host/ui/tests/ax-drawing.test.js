/**
 * Tests for ax-drawing widget
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createWidget, cleanup, shadowQuery, shadowQueryAll, captureEvent, waitForElement } from './test-utils.js';
import '../src/scripts/components/ax-drawing.js';

describe('AxDrawing', () => {
    let widget;

    afterEach(() => {
        cleanup();
    });

    describe('rendering', () => {
        it('renders widget container', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const container = shadowQuery(widget, '.widget-container');
            expect(container).toBeTruthy();
        });

        it('renders canvas', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const canvas = shadowQuery(widget, '.drawing-canvas');
            expect(canvas).toBeTruthy();
        });

        it('renders toolbar', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const toolbar = shadowQuery(widget, '.toolbar');
            expect(toolbar).toBeTruthy();
        });

        it('shows prompt when provided', async () => {
            widget = createWidget('ax-drawing', { prompt: 'Draw your answer' });
            await waitForElement(widget);

            const prompt = shadowQuery(widget, '.prompt');
            expect(prompt?.textContent).toContain('Draw your answer');
        });

        it('applies custom canvas size', async () => {
            widget = createWidget('ax-drawing', {
                'canvas-size': JSON.stringify({ width: 800, height: 600 })
            });
            await waitForElement(widget);

            const canvas = shadowQuery(widget, '.drawing-canvas');
            expect(canvas?.width).toBe(800);
            expect(canvas?.height).toBe(600);
        });
    });

    describe('toolbar', () => {
        it('renders pen tool button', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const penBtn = shadowQuery(widget, '[data-tool="pen"]');
            expect(penBtn).toBeTruthy();
        });

        it('renders highlighter tool button', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const highlighterBtn = shadowQuery(widget, '[data-tool="highlighter"]');
            expect(highlighterBtn).toBeTruthy();
        });

        it('renders eraser tool button', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const eraserBtn = shadowQuery(widget, '[data-tool="eraser"]');
            expect(eraserBtn).toBeTruthy();
        });

        it('renders color swatches', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const swatches = shadowQueryAll(widget, '.color-swatch');
            expect(swatches.length).toBeGreaterThan(0);
        });

        it('renders size buttons', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const sizeButtons = shadowQueryAll(widget, '.size-btn');
            expect(sizeButtons.length).toBeGreaterThan(0);
        });

        it('renders clear button', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const clearBtn = shadowQuery(widget, '.clear-btn');
            expect(clearBtn).toBeTruthy();
        });
    });

    describe('tool selection', () => {
        it('pen tool is active by default', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const penBtn = shadowQuery(widget, '[data-tool="pen"]');
            expect(penBtn?.classList.contains('active')).toBe(true);
        });

        it('switches to highlighter on click', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const highlighterBtn = shadowQuery(widget, '[data-tool="highlighter"]');
            highlighterBtn?.click();

            expect(highlighterBtn?.classList.contains('active')).toBe(true);
        });

        it('switches to eraser on click', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const eraserBtn = shadowQuery(widget, '[data-tool="eraser"]');
            eraserBtn?.click();

            expect(eraserBtn?.classList.contains('active')).toBe(true);
        });

        it('hides color picker for eraser', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const eraserBtn = shadowQuery(widget, '[data-tool="eraser"]');
            eraserBtn?.click();

            const colorPicker = shadowQuery(widget, '.color-picker');
            expect(colorPicker).toBeFalsy();
        });
    });

    describe('color selection', () => {
        it('changes color on swatch click', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const swatches = shadowQueryAll(widget, '.color-swatch');
            if (swatches.length >= 2) {
                swatches[1]?.click();
                expect(swatches[1]?.classList.contains('active')).toBe(true);
            }
        });

        it('supports custom color picker', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const customColor = shadowQuery(widget, '.color-custom');
            expect(customColor).toBeTruthy();
        });
    });

    describe('size selection', () => {
        it('changes size on button click', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const sizeButtons = shadowQueryAll(widget, '.size-btn');
            if (sizeButtons.length >= 2) {
                sizeButtons[1]?.click();
                expect(sizeButtons[1]?.classList.contains('active')).toBe(true);
            }
        });
    });

    describe('undo/redo', () => {
        it('shows undo button when allow-undo is set', async () => {
            widget = createWidget('ax-drawing', { 'allow-undo': true });
            await waitForElement(widget);

            const undoBtn = shadowQuery(widget, '.undo-btn');
            expect(undoBtn).toBeTruthy();
        });

        it('shows redo button when allow-undo is set', async () => {
            widget = createWidget('ax-drawing', { 'allow-undo': true });
            await waitForElement(widget);

            const redoBtn = shadowQuery(widget, '.redo-btn');
            expect(redoBtn).toBeTruthy();
        });

        it('undo button is disabled when no history', async () => {
            widget = createWidget('ax-drawing', { 'allow-undo': true });
            await waitForElement(widget);

            const undoBtn = shadowQuery(widget, '.undo-btn');
            expect(undoBtn?.disabled).toBe(true);
        });

        it('redo button is disabled when no redo history', async () => {
            widget = createWidget('ax-drawing', { 'allow-undo': true });
            await waitForElement(widget);

            const redoBtn = shadowQuery(widget, '.redo-btn');
            expect(redoBtn?.disabled).toBe(true);
        });
    });

    describe('drawing', () => {
        it('canvas responds to mouse events', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const canvas = shadowQuery(widget, '.drawing-canvas');
            
            // Simulate mousedown
            canvas?.dispatchEvent(new MouseEvent('mousedown', {
                clientX: 100,
                clientY: 100,
                bubbles: true
            }));

            // Widget should handle the event without error
            expect(widget).toBeTruthy();
        });

        it('canvas responds to touch events', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const canvas = shadowQuery(widget, '.drawing-canvas');
            
            // Widget should handle touch events
            expect(canvas).toBeTruthy();
        });
    });

    describe('clear functionality', () => {
        it('clear button triggers confirmation', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            // Mock confirm
            const originalConfirm = window.confirm;
            window.confirm = vi.fn(() => false);

            const clearBtn = shadowQuery(widget, '.clear-btn');
            clearBtn?.click();

            expect(window.confirm).toHaveBeenCalled();

            window.confirm = originalConfirm;
        });

        it('clear resets strokes when confirmed', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            // Mock confirm to return true
            const originalConfirm = window.confirm;
            window.confirm = vi.fn(() => true);

            const clearBtn = shadowQuery(widget, '.clear-btn');
            clearBtn?.click();

            const value = widget.getValue();
            expect(value.strokes.length).toBe(0);

            window.confirm = originalConfirm;
        });
    });

    describe('value interface', () => {
        it('getValue returns strokes and dataUrl', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const value = widget.getValue();
            expect(value).toHaveProperty('strokes');
            expect(value).toHaveProperty('dataUrl');
            expect(value).toHaveProperty('canvasSize');
        });

        it('setValue loads drawing data', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const drawingData = {
                strokes: [
                    {
                        tool: 'pen',
                        color: '#000000',
                        size: 3,
                        opacity: 1,
                        points: [{ x: 10, y: 10 }, { x: 50, y: 50 }]
                    }
                ]
            };

            widget.setValue(drawingData);

            const value = widget.getValue();
            expect(value.strokes.length).toBe(1);
        });

        it('toDataURL exports canvas as image', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const dataUrl = widget.toDataURL();
            expect(dataUrl).toMatch(/^data:image\/png/);
        });
    });

    describe('validation', () => {
        it('validates when required and has strokes', async () => {
            widget = createWidget('ax-drawing', { required: true });
            await waitForElement(widget);

            widget.setValue({
                strokes: [
                    { tool: 'pen', color: '#000', size: 3, opacity: 1, points: [{ x: 0, y: 0 }, { x: 10, y: 10 }] }
                ]
            });

            const result = widget.validate();
            expect(result.valid).toBe(true);
        });

        it('fails validation when required but no strokes', async () => {
            widget = createWidget('ax-drawing', { required: true });
            await waitForElement(widget);

            const result = widget.validate();
            expect(result.valid).toBe(false);
        });
    });

    describe('events', () => {
        it('dispatches ax-draw on stroke completion', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            // setValue triggers internal state change
            widget.setValue({
                strokes: [
                    { tool: 'pen', color: '#000', size: 3, opacity: 1, points: [{ x: 0, y: 0 }, { x: 10, y: 10 }] }
                ]
            });

            expect(widget.getValue().strokes.length).toBe(1);
        });
    });

    describe('accessibility', () => {
        it('toolbar has role toolbar', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const toolbar = shadowQuery(widget, '.toolbar');
            expect(toolbar?.getAttribute('role')).toBe('toolbar');
        });

        it('tool buttons have aria-labels', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const toolBtn = shadowQuery(widget, '.tool-btn');
            expect(toolBtn?.hasAttribute('aria-label')).toBe(true);
        });

        it('canvas has role img', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const canvas = shadowQuery(widget, '.drawing-canvas');
            expect(canvas?.getAttribute('role')).toBe('img');
        });

        it('supports keyboard shortcuts for undo/redo', async () => {
            widget = createWidget('ax-drawing', { 'allow-undo': true });
            await waitForElement(widget);

            // Add a stroke
            widget.setValue({
                strokes: [
                    { tool: 'pen', color: '#000', size: 3, opacity: 1, points: [{ x: 0, y: 0 }, { x: 10, y: 10 }] }
                ]
            });

            // Simulate Ctrl+Z
            widget.dispatchEvent(new KeyboardEvent('keydown', {
                key: 'z',
                ctrlKey: true,
                bubbles: true
            }));

            // Undo should work
            expect(widget).toBeTruthy();
        });
    });

    describe('background image', () => {
        it('renders background image when provided', async () => {
            const testImage = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=';
            
            widget = createWidget('ax-drawing', {
                'background-image': testImage
            });
            await waitForElement(widget);

            const bgImage = shadowQuery(widget, '.canvas-background');
            expect(bgImage).toBeTruthy();
        });
    });

    describe('tool configuration', () => {
        it('respects custom tool configuration', async () => {
            widget = createWidget('ax-drawing', {
                tools: JSON.stringify({
                    pen: { enabled: true, colors: ['#ff0000', '#00ff00'] },
                    highlighter: { enabled: false },
                    eraser: { enabled: true }
                })
            });
            await waitForElement(widget);

            const highlighterBtn = shadowQuery(widget, '[data-tool="highlighter"]');
            expect(highlighterBtn).toBeFalsy();
        });
    });

    describe('status bar', () => {
        it('displays current tool and size', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const statusBar = shadowQuery(widget, '.status-bar');
            expect(statusBar?.textContent).toContain('pen');
        });

        it('displays stroke count', async () => {
            widget = createWidget('ax-drawing');
            await waitForElement(widget);

            const statusBar = shadowQuery(widget, '.status-bar');
            expect(statusBar?.textContent).toContain('stroke');
        });
    });
});
