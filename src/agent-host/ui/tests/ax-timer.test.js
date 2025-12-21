/**
 * Tests for ax-timer widget
 */
import { describe, it, expect, afterEach, vi } from 'vitest';
import '../src/scripts/components/ax-timer.js';

// Simple test helpers inline to avoid async issues
function createTimerWidget(attributes = {}) {
    const element = document.createElement('ax-timer');
    for (const [key, value] of Object.entries(attributes)) {
        if (typeof value === 'boolean') {
            if (value) element.setAttribute(key, '');
        } else {
            element.setAttribute(key, String(value));
        }
    }
    document.body.appendChild(element);
    return element;
}

function shadowQuery(host, selector) {
    return host.shadowRoot?.querySelector(selector);
}

describe('AxTimer', () => {
    let widget;

    afterEach(() => {
        if (widget) {
            widget.pause?.();
        }
        document.body.innerHTML = '';
        vi.restoreAllMocks();
    });

    describe('rendering', () => {
        it('renders countdown timer', async () => {
            widget = createTimerWidget({ mode: 'countdown', duration: 60 });
            await new Promise(r => setTimeout(r, 50));

            const display = shadowQuery(widget, '.timer-display');
            expect(display).toBeTruthy();
            expect(display.textContent.trim()).toBe('01:00');
        });

        it('renders elapsed timer starting at 00:00', async () => {
            widget = createTimerWidget({ mode: 'elapsed' });
            await new Promise(r => setTimeout(r, 50));

            const display = shadowQuery(widget, '.timer-display');
            expect(display.textContent.trim()).toBe('00:00');
        });

        it('shows controls when show-controls is set', async () => {
            widget = createTimerWidget({ 'show-controls': true });
            await new Promise(r => setTimeout(r, 50));

            const controls = shadowQuery(widget, '.controls');
            expect(controls).toBeTruthy();
        });
    });

    describe('value interface', () => {
        it('getValue returns timer state', async () => {
            widget = createTimerWidget({ mode: 'countdown', duration: 60 });
            await new Promise(r => setTimeout(r, 50));

            const value = widget.getValue();
            expect(value.elapsed).toBe(0);
            expect(value.remaining).toBe(60);
            expect(value.isRunning).toBe(false);
        });

        it('setValue sets elapsed time', async () => {
            widget = createTimerWidget({ mode: 'countdown', duration: 60 });
            await new Promise(r => setTimeout(r, 50));

            widget.setValue(30);
            const value = widget.getValue();
            expect(value.elapsed).toBe(30);
            expect(value.remaining).toBe(30);
        });
    });

    describe('controls', () => {
        it('start begins the timer', async () => {
            widget = createTimerWidget({ 'show-controls': true });
            await new Promise(r => setTimeout(r, 50));

            widget.start();
            expect(widget.getValue().isRunning).toBe(true);
            widget.pause();
        });

        it('pause stops the timer', async () => {
            widget = createTimerWidget({ 'show-controls': true });
            await new Promise(r => setTimeout(r, 50));

            widget.start();
            widget.pause();
            expect(widget.getValue().isRunning).toBe(false);
        });

        it('reset returns to zero', async () => {
            widget = createTimerWidget({ 'show-controls': true });
            await new Promise(r => setTimeout(r, 50));

            widget.setValue(30);
            widget.reset();
            expect(widget.getValue().elapsed).toBe(0);
        });
    });

    describe('format', () => {
        it('formats as mm:ss by default', async () => {
            widget = createTimerWidget({ mode: 'countdown', duration: 90 });
            await new Promise(r => setTimeout(r, 50));

            const display = shadowQuery(widget, '.timer-display');
            expect(display.textContent.trim()).toBe('01:30');
        });

        it('formats as hh:mm:ss when specified', async () => {
            widget = createTimerWidget({ mode: 'countdown', duration: 3661, format: 'hh:mm:ss' });
            await new Promise(r => setTimeout(r, 50));

            const display = shadowQuery(widget, '.timer-display');
            expect(display.textContent.trim()).toBe('01:01:01');
        });
    });

    describe('events', () => {
        it('dispatches ax-timer-start on start', async () => {
            widget = createTimerWidget();
            await new Promise(r => setTimeout(r, 50));

            let eventFired = false;
            widget.addEventListener('ax-timer-start', () => {
                eventFired = true;
            });

            widget.start();
            widget.pause();

            expect(eventFired).toBe(true);
        });

        it('dispatches ax-timer-pause on pause', async () => {
            widget = createTimerWidget();
            await new Promise(r => setTimeout(r, 50));

            let eventFired = false;
            widget.addEventListener('ax-timer-pause', () => {
                eventFired = true;
            });

            widget.start();
            widget.pause();

            expect(eventFired).toBe(true);
        });

        it('dispatches ax-timer-reset on reset', async () => {
            widget = createTimerWidget();
            await new Promise(r => setTimeout(r, 50));

            let eventFired = false;
            widget.addEventListener('ax-timer-reset', () => {
                eventFired = true;
            });

            widget.setValue(30);
            widget.reset();

            expect(eventFired).toBe(true);
        });
    });

    describe('warning threshold', () => {
        it('adds warning class when below threshold', async () => {
            widget = createTimerWidget({
                mode: 'countdown',
                duration: 60,
                'warning-threshold': 10,
            });
            await new Promise(r => setTimeout(r, 50));

            widget.setValue(55);
            await new Promise(r => setTimeout(r, 50));

            const display = shadowQuery(widget, '.timer-display');
            expect(display.classList.contains('danger')).toBe(true);
        });
    });
});
