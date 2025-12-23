/**
 * Conversation Header Component
 * Displays template progress, timer, title, and navigation controls for templated conversations.
 *
 * Attributes:
 * - title: The conversation/template title
 * - current-item: Current item index (0-based)
 * - total-items: Total number of items
 * - deadline: ISO timestamp for countdown timer
 * - show-progress: Whether to show progress indicator
 * - allow-backward: Whether backward navigation is allowed
 * - is-paused: Whether the conversation is paused
 *
 * Events:
 * - ax-navigate-back: Fired when user clicks the back button
 * - ax-pause: Fired when user clicks the pause button
 * - ax-resume: Fired when user clicks the resume button
 */

class AxConversationHeader extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this._timerInterval = null;
        this._deadline = null;
        this._isPaused = false;
    }

    static get observedAttributes() {
        return ['title', 'current-item', 'total-items', 'deadline', 'show-progress', 'allow-backward', 'is-paused'];
    }

    connectedCallback() {
        this.render();
        this.startTimer();
    }

    disconnectedCallback() {
        this.stopTimer();
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (oldValue !== newValue && this.shadowRoot) {
            if (name === 'deadline') {
                this._deadline = newValue ? new Date(newValue) : null;
                this.restartTimer();
            } else if (name === 'is-paused') {
                this._isPaused = newValue === 'true' || newValue === '';
            }
            this.render();
        }
    }

    get title() {
        return this.getAttribute('title') || '';
    }

    get currentItem() {
        return parseInt(this.getAttribute('current-item') || '0', 10);
    }

    get totalItems() {
        return parseInt(this.getAttribute('total-items') || '0', 10);
    }

    get deadline() {
        const val = this.getAttribute('deadline');
        return val ? new Date(val) : null;
    }

    get showProgress() {
        return this.hasAttribute('show-progress');
    }

    get allowBackward() {
        return this.hasAttribute('allow-backward') && this.currentItem > 0;
    }

    get isPaused() {
        return this.hasAttribute('is-paused');
    }

    startTimer() {
        if (this._deadline && !this._isPaused) {
            this._timerInterval = setInterval(() => this.updateTimer(), 1000);
            this.updateTimer();
        }
    }

    stopTimer() {
        if (this._timerInterval) {
            clearInterval(this._timerInterval);
            this._timerInterval = null;
        }
    }

    restartTimer() {
        this.stopTimer();
        this._deadline = this.deadline;
        if (!this._isPaused) {
            this.startTimer();
        }
    }

    updateTimer() {
        if (!this._deadline) return;

        const now = new Date();
        const remaining = Math.max(0, this._deadline.getTime() - now.getTime());
        const timerEl = this.shadowRoot?.querySelector('.timer-value');

        if (timerEl) {
            if (remaining <= 0) {
                timerEl.textContent = '00:00';
                timerEl.classList.add('expired');
                this.stopTimer();
                // Dispatch time expired event
                this.dispatchEvent(new CustomEvent('ax-time-expired', { bubbles: true, composed: true }));
            } else {
                const minutes = Math.floor(remaining / 60000);
                const seconds = Math.floor((remaining % 60000) / 1000);
                timerEl.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

                // Add warning class when less than 1 minute remaining
                if (remaining < 60000) {
                    timerEl.classList.add('warning');
                } else {
                    timerEl.classList.remove('warning');
                }
            }
        }
    }

    handleBackClick() {
        if (!this.allowBackward) return;
        this.dispatchEvent(
            new CustomEvent('ax-navigate-back', {
                bubbles: true,
                composed: true,
                detail: { currentItem: this.currentItem },
            })
        );
    }

    handlePauseClick() {
        if (this._isPaused) {
            this.dispatchEvent(new CustomEvent('ax-resume', { bubbles: true, composed: true }));
        } else {
            this.dispatchEvent(new CustomEvent('ax-pause', { bubbles: true, composed: true }));
        }
    }

    /**
     * Check if dark theme is active.
     * Prioritizes explicit data-bs-theme setting over system preference.
     */
    _isDarkTheme() {
        // Check Bootstrap theme attribute FIRST - explicit setting takes priority
        const bsTheme = document.documentElement.getAttribute('data-bs-theme');
        if (bsTheme) {
            return bsTheme === 'dark';
        }
        // Check custom dark theme class
        if (document.documentElement.classList.contains('dark-theme') || document.body.classList.contains('dark-theme')) {
            return true;
        }
        // Fall back to system preference ONLY if no explicit theme is set
        return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    render() {
        const hasTimer = this._deadline !== null;
        const hasProgress = this.showProgress && this.totalItems > 0;
        const hasTitle = this.title.length > 0;
        const hasBackButton = this.allowBackward;
        const hasPauseButton = hasTimer || hasProgress;
        const isDark = this._isDarkTheme();

        // Don't render if nothing to show
        if (!hasTimer && !hasProgress && !hasTitle && !hasBackButton) {
            this.shadowRoot.innerHTML = '';
            return;
        }

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    font-family: var(--bs-body-font-family, system-ui, -apple-system, sans-serif);

                    /* Theme-aware variables */
                    --header-bg: ${isDark ? '#21262d' : '#e9ecef'};
                    --header-border: ${isDark ? '#30363d' : '#dee2e6'};
                    --header-text: ${isDark ? '#e2e8f0' : '#212529'};
                    --btn-bg: ${isDark ? '#0d1117' : '#f8f9fa'};
                    --btn-border: ${isDark ? '#30363d' : '#dee2e6'};
                }

                .header-container {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 1rem;
                    padding: 0.75rem 1rem;
                    background-color: var(--header-bg);
                    border: 1px solid var(--header-border);
                    border-radius: var(--bs-border-radius, 0.375rem);
                    margin-bottom: 1rem;
                    color: var(--header-text);
                }

                .left-section {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                }

                .center-section {
                    flex: 1;
                    text-align: center;
                }

                .right-section {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                }

                .back-button {
                    display: flex;
                    align-items: center;
                    gap: 0.25rem;
                    background-color: var(--btn-bg);
                    border: 1px solid var(--btn-border);
                    border-radius: var(--bs-border-radius, 0.375rem);
                    padding: 0.5rem 0.75rem;
                    color: var(--header-text);
                    cursor: pointer;
                    font-size: 0.875rem;
                    font-weight: 500;
                    transition: background-color 0.2s, transform 0.1s;
                }

                .back-button:hover:not(:disabled) {
                    background-color: ${isDark ? '#30363d' : '#e9ecef'};
                    transform: translateX(-2px);
                }

                .back-button:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .back-button svg {
                    width: 16px;
                    height: 16px;
                }

                .title {
                    font-size: 1rem;
                    font-weight: 600;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    max-width: 300px;
                    color: var(--bs-body-color, #212529);
                }

                .progress-indicator {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    font-size: 0.875rem;
                    font-weight: 500;
                    background-color: var(--bs-primary, #0d6efd);
                    color: #fff;
                    padding: 0.4rem 0.75rem;
                    border-radius: 20px;
                }

                .progress-dots {
                    display: flex;
                    gap: 4px;
                }

                .progress-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.4);
                    transition: background 0.3s;
                }

                .progress-dot.completed {
                    background: var(--bs-success, #198754);
                }

                .progress-dot.current {
                    background: white;
                    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.4);
                }

                .timer {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    font-size: 1rem;
                    font-weight: 600;
                    background-color: var(--btn-bg);
                    border: 1px solid var(--btn-border);
                    color: var(--header-text);
                    padding: 0.5rem 0.75rem;
                    border-radius: var(--bs-border-radius, 0.375rem);
                }

                .timer svg {
                    width: 18px;
                    height: 18px;
                }

                .timer-value {
                    font-variant-numeric: tabular-nums;
                    min-width: 4ch;
                    text-align: center;
                }

                .timer-value.warning {
                    color: var(--bs-warning, #ffc107);
                    animation: pulse 1s infinite;
                }

                .timer-value.expired {
                    color: var(--bs-danger, #dc3545);
                }

                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }

                .pause-button {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background-color: var(--btn-bg);
                    border: 1px solid var(--btn-border);
                    border-radius: var(--bs-border-radius, 0.375rem);
                    padding: 0.5rem;
                    color: var(--header-text);
                    cursor: pointer;
                    transition: background-color 0.2s;
                }

                .pause-button:hover {
                    background-color: ${isDark ? '#30363d' : '#e9ecef'};
                }

                .pause-button svg {
                    width: 18px;
                    height: 18px;
                }

                /* Mobile adjustments */
                @media (max-width: 640px) {
                    .header-container {
                        flex-wrap: wrap;
                        gap: 0.5rem;
                    }

                    .center-section {
                        order: -1;
                        flex-basis: 100%;
                    }

                    .title {
                        max-width: 100%;
                    }

                    .progress-dots {
                        display: none;
                    }
                }
            </style>

            <div class="header-container">
                <div class="left-section">
                    ${hasBackButton ? this.renderBackButton() : ''}
                </div>

                <div class="center-section">
                    ${hasTitle ? `<div class="title">${this.escapeHtml(this.title)}</div>` : ''}
                </div>

                <div class="right-section">
                    ${hasProgress ? this.renderProgress() : ''}
                    ${hasTimer ? this.renderTimer() : ''}
                    ${hasPauseButton ? this.renderPauseButton() : ''}
                </div>
            </div>
        `;

        // Add event listeners
        const backBtn = this.shadowRoot.querySelector('.back-button');
        if (backBtn) {
            backBtn.addEventListener('click', () => this.handleBackClick());
        }

        const pauseBtn = this.shadowRoot.querySelector('.pause-button');
        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => this.handlePauseClick());
        }

        // Update timer immediately
        this.updateTimer();
    }

    renderBackButton() {
        return `
            <button class="back-button" ${!this.allowBackward ? 'disabled' : ''} title="Go to previous item">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                </svg>
                Back
            </button>
        `;
    }

    renderProgress() {
        const current = this.currentItem + 1; // 1-based for display
        const total = this.totalItems;

        // Render dots for up to 10 items, otherwise just show text
        let dotsHtml = '';
        if (total <= 10) {
            const dots = [];
            for (let i = 0; i < total; i++) {
                let cls = 'progress-dot';
                if (i < this.currentItem) cls += ' completed';
                else if (i === this.currentItem) cls += ' current';
                dots.push(`<span class="${cls}"></span>`);
            }
            dotsHtml = `<div class="progress-dots">${dots.join('')}</div>`;
        }

        return `
            <div class="progress-indicator">
                <span>Item ${current} of ${total}</span>
                ${dotsHtml}
            </div>
        `;
    }

    renderTimer() {
        return `
            <div class="timer">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span class="timer-value">--:--</span>
            </div>
        `;
    }

    renderPauseButton() {
        const icon = this._isPaused
            ? `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
               </svg>`
            : `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
               </svg>`;

        return `
            <button class="pause-button" title="${this._isPaused ? 'Resume' : 'Pause'}">
                ${icon}
            </button>
        `;
    }

    /**
     * Refresh theme - called by ThemeService when theme changes
     * Re-renders the component with updated theme-aware styles
     */
    refreshTheme() {
        this.render();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Register the component
customElements.define('ax-conversation-header', AxConversationHeader);

export default AxConversationHeader;
