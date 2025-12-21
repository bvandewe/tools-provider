/**
 * Timer Widget Component
 * Displays countdown or elapsed time with optional controls.
 *
 * Attributes:
 * - mode: "countdown" | "elapsed" (default: countdown)
 * - duration: Duration in seconds (for countdown mode)
 * - auto-start: Start automatically on mount
 * - show-controls: Show play/pause/reset buttons
 * - format: "hh:mm:ss" | "mm:ss" | "ss" (default: mm:ss)
 * - warning-threshold: Seconds remaining to show warning style
 *
 * Events:
 * - ax-timer-tick: Fired each second with current time
 * - ax-timer-complete: Fired when countdown reaches zero
 * - ax-timer-start: Fired when timer starts
 * - ax-timer-pause: Fired when timer pauses
 * - ax-timer-reset: Fired when timer resets
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

class AxTimer extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'mode', 'duration', 'auto-start', 'show-controls', 'format', 'warning-threshold'];
    }

    constructor() {
        super();
        this._elapsed = 0;
        this._intervalId = null;
        this._isRunning = false;
        this._startTime = null;
    }

    // Attribute getters
    get mode() {
        return this.getAttribute('mode') || 'countdown';
    }

    get duration() {
        return parseInt(this.getAttribute('duration')) || 60;
    }

    get autoStart() {
        return this.hasAttribute('auto-start');
    }

    get showControls() {
        return this.hasAttribute('show-controls');
    }

    get format() {
        return this.getAttribute('format') || 'mm:ss';
    }

    get warningThreshold() {
        return parseInt(this.getAttribute('warning-threshold')) || 10;
    }

    // Value interface
    getValue() {
        return {
            elapsed: this._elapsed,
            remaining: this.mode === 'countdown' ? Math.max(0, this.duration - this._elapsed) : null,
            isRunning: this._isRunning,
            isComplete: this.mode === 'countdown' && this._elapsed >= this.duration,
        };
    }

    setValue(value) {
        if (typeof value === 'number') {
            this._elapsed = value;
        } else if (value?.elapsed !== undefined) {
            this._elapsed = value.elapsed;
        }
        this._updateDisplay();
    }

    validate() {
        return { valid: true, errors: [], warnings: [] };
    }

    async getStyles() {
        return `
            ${await this.getBaseStyles()}

            :host {
                display: block;
                font-family: var(--font-family, system-ui, -apple-system, sans-serif);
            }

            .timer-container {
                background: var(--widget-bg, #f8f9fa);
                border: 1px solid var(--widget-border, #dee2e6);
                border-radius: 12px;
                padding: 1.25rem;
                text-align: center;
            }

            .timer-display {
                font-size: 2.5rem;
                font-weight: 700;
                font-variant-numeric: tabular-nums;
                color: var(--text-color, #212529);
                padding: 1rem;
                transition: color 0.3s ease;
            }

            .timer-display.warning {
                color: var(--warning-color, #ffc107);
            }

            .timer-display.danger {
                color: var(--danger-color, #dc3545);
                animation: pulse 1s infinite;
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.6; }
            }

            .timer-display.complete {
                color: var(--success-color, #198754);
            }

            .controls {
                display: flex;
                justify-content: center;
                gap: 0.5rem;
                margin-top: 1rem;
            }

            .control-btn {
                padding: 0.5rem 1rem;
                border: 1px solid var(--widget-border, #dee2e6);
                border-radius: 6px;
                background: var(--btn-bg, #fff);
                cursor: pointer;
                font-size: 0.9rem;
                transition: all 0.15s ease;
            }

            .control-btn:hover:not(:disabled) {
                background: var(--btn-hover-bg, #e9ecef);
            }

            .control-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            .control-btn.primary {
                background: var(--primary-color, #0d6efd);
                color: white;
                border-color: var(--primary-color, #0d6efd);
            }

            .control-btn.primary:hover:not(:disabled) {
                background: var(--primary-hover, #0b5ed7);
            }

            .status-label {
                font-size: 0.85rem;
                color: var(--text-muted, #6c757d);
                margin-top: 0.5rem;
            }
        `;
    }

    render() {
        const displayTime = this._getDisplayTime();
        const displayClass = this._getDisplayClass();

        this.shadowRoot.innerHTML = `
            <style>${this._styles || ''}</style>
            <div class="timer-container">
                <div class="timer-display ${displayClass}" role="timer" aria-live="polite">
                    ${displayTime}
                </div>
                ${this.showControls ? this._renderControls() : ''}
                <div class="status-label">${this._getStatusLabel()}</div>
            </div>
        `;

        this._styles = this.shadowRoot.querySelector('style')?.textContent;
    }

    _renderControls() {
        return `
            <div class="controls">
                <button class="control-btn primary" data-action="${this._isRunning ? 'pause' : 'start'}">
                    ${this._isRunning ? '⏸ Pause' : '▶ Start'}
                </button>
                <button class="control-btn" data-action="reset">↺ Reset</button>
            </div>
        `;
    }

    _getDisplayTime() {
        const seconds = this.mode === 'countdown' ? Math.max(0, this.duration - this._elapsed) : this._elapsed;

        return this._formatTime(seconds);
    }

    _formatTime(totalSeconds) {
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;

        const pad = n => String(n).padStart(2, '0');

        switch (this.format) {
            case 'hh:mm:ss':
                return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
            case 'ss':
                return `${totalSeconds}`;
            case 'mm:ss':
            default:
                return `${pad(minutes)}:${pad(seconds)}`;
        }
    }

    _getDisplayClass() {
        if (this.mode === 'countdown') {
            const remaining = this.duration - this._elapsed;
            if (remaining <= 0) return 'complete';
            if (remaining <= this.warningThreshold / 2) return 'danger';
            if (remaining <= this.warningThreshold) return 'warning';
        }
        return '';
    }

    _getStatusLabel() {
        if (this.mode === 'countdown' && this._elapsed >= this.duration) {
            return "Time's up!";
        }
        return this._isRunning ? 'Running' : 'Paused';
    }

    async loadStyles() {
        this._styles = await this.getStyles();
    }

    connectedCallback() {
        super.connectedCallback();
        if (this.autoStart) {
            this.start();
        }
    }

    disconnectedCallback() {
        this.pause();
        super.disconnectedCallback();
    }

    bindEvents() {
        this.shadowRoot.addEventListener('click', e => {
            const btn = e.target.closest('.control-btn');
            if (!btn) return;

            const action = btn.dataset.action;
            if (action === 'start') this.start();
            else if (action === 'pause') this.pause();
            else if (action === 'reset') this.reset();
        });
    }

    start() {
        if (this._isRunning) return;
        if (this.mode === 'countdown' && this._elapsed >= this.duration) return;

        this._isRunning = true;
        this._startTime = Date.now() - this._elapsed * 1000;

        this._intervalId = setInterval(() => this._tick(), 1000);

        this.dispatchEvent(
            new CustomEvent('ax-timer-start', {
                bubbles: true,
                composed: true,
                detail: { elapsed: this._elapsed },
            })
        );

        this._updateDisplay();
    }

    pause() {
        if (!this._isRunning) return;

        this._isRunning = false;
        clearInterval(this._intervalId);
        this._intervalId = null;

        this.dispatchEvent(
            new CustomEvent('ax-timer-pause', {
                bubbles: true,
                composed: true,
                detail: { elapsed: this._elapsed },
            })
        );

        this._updateDisplay();
    }

    reset() {
        this.pause();
        this._elapsed = 0;

        this.dispatchEvent(
            new CustomEvent('ax-timer-reset', {
                bubbles: true,
                composed: true,
            })
        );

        this.render();
        this.bindEvents();
    }

    _tick() {
        this._elapsed = Math.floor((Date.now() - this._startTime) / 1000);

        this.dispatchEvent(
            new CustomEvent('ax-timer-tick', {
                bubbles: true,
                composed: true,
                detail: this.getValue(),
            })
        );

        if (this.mode === 'countdown' && this._elapsed >= this.duration) {
            this.pause();
            this.dispatchEvent(
                new CustomEvent('ax-timer-complete', {
                    bubbles: true,
                    composed: true,
                })
            );
        }

        this._updateDisplay();
    }

    _updateDisplay() {
        const display = this.shadowRoot.querySelector('.timer-display');
        const statusLabel = this.shadowRoot.querySelector('.status-label');
        const startBtn = this.shadowRoot.querySelector('[data-action="start"], [data-action="pause"]');

        if (display) {
            display.textContent = this._getDisplayTime();
            display.className = `timer-display ${this._getDisplayClass()}`;
        }
        if (statusLabel) {
            statusLabel.textContent = this._getStatusLabel();
        }
        if (startBtn) {
            startBtn.dataset.action = this._isRunning ? 'pause' : 'start';
            startBtn.textContent = this._isRunning ? '⏸ Pause' : '▶ Start';
        }
    }
}

customElements.define('ax-timer', AxTimer);

export default AxTimer;
