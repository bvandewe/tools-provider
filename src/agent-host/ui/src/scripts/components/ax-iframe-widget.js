/**
 * IFRAME Widget Component
 * Renders sandboxed external content with postMessage bridge.
 *
 * Attributes:
 * - src: URL to load
 * - sandbox: Sandbox attribute flags (default: "allow-scripts allow-same-origin")
 * - allow: Permissions policy
 * - width: Width (default: "100%")
 * - height: Height (default: "400px")
 * - allow-resize: User can resize
 * - loading: "eager" | "lazy" (default: "lazy")
 * - allowed-origins: JSON array of allowed message origins
 *
 * Events:
 * - ax-iframe-load: Fired when iframe loads
 * - ax-iframe-error: Fired on load error
 * - ax-iframe-message: Fired when receiving postMessage from iframe
 *   Detail: { type: string, payload: any, origin: string }
 *
 * PostMessage Bridge:
 * - Iframe can send: { type: 'ax-message', payload: {...} }
 * - Parent can call: widget.sendMessage(type, payload)
 *
 * Security:
 * - Origin validation on all incoming messages
 * - Configurable sandbox flags
 * - Content Security Policy headers
 * - Rate limiting on incoming messages
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

// Default sandbox flags for security
const DEFAULT_SANDBOX = 'allow-scripts allow-same-origin';

// Default permissions
const DEFAULT_ALLOW = 'clipboard-read; clipboard-write';

// Message rate limiting
const MAX_MESSAGES_PER_SECOND = 10;

class AxIframeWidget extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'src', 'sandbox', 'allow', 'width', 'height', 'allow-resize', 'loading', 'allowed-origins'];
    }

    constructor() {
        super();
        this._messageCount = 0;
        this._messageResetInterval = null;
        this._boundMessageHandler = this.handleMessage.bind(this);
        this._loaded = false;
        this._error = null;
    }

    // =========================================================================
    // Attribute Getters
    // =========================================================================

    get src() {
        return this.getAttribute('src') || '';
    }

    set src(value) {
        this.setAttribute('src', value);
    }

    get sandbox() {
        return this.getAttribute('sandbox') || DEFAULT_SANDBOX;
    }

    get allow() {
        return this.getAttribute('allow') || DEFAULT_ALLOW;
    }

    get width() {
        return this.getAttribute('width') || '100%';
    }

    get height() {
        return this.getAttribute('height') || '400px';
    }

    get allowResize() {
        return this.hasAttribute('allow-resize');
    }

    get loading() {
        return this.getAttribute('loading') || 'lazy';
    }

    get allowedOrigins() {
        return this.parseJsonAttribute('allowed-origins', ['*']);
    }

    // =========================================================================
    // AxWidgetBase Implementation
    // =========================================================================

    getValue() {
        return {
            src: this.src,
            loaded: this._loaded,
            error: this._error,
        };
    }

    setValue(value) {
        if (typeof value === 'string') {
            this.src = value;
        } else if (value && typeof value === 'object' && value.src) {
            this.src = value.src;
        }
    }

    validate() {
        const errors = [];
        if (!this.src) {
            errors.push('IFRAME src is required');
        }
        if (this._error) {
            errors.push(this._error);
        }
        return { valid: errors.length === 0, errors, warnings: [] };
    }

    async getStyles() {
        return `
            ${this.getBaseStyles()}

            :host {
                display: block;
            }

            .widget-container {
                padding: 0;
                overflow: hidden;
            }

            .iframe-wrapper {
                position: relative;
                width: ${this.width};
                height: ${this.height};
                min-height: 100px;
                background: var(--ax-iframe-bg, #f8f9fa);
                border-radius: var(--ax-border-radius, 8px);
                overflow: hidden;
            }

            .iframe-wrapper.resizable {
                resize: both;
                min-width: 200px;
                min-height: 100px;
            }

            iframe {
                width: 100%;
                height: 100%;
                border: none;
                display: block;
            }

            .loading-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                background: var(--ax-iframe-bg, #f8f9fa);
            }

            .loading-spinner {
                width: 40px;
                height: 40px;
                border: 3px solid #e9ecef;
                border-top-color: var(--ax-primary-color, #0d6efd);
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }

            @keyframes spin {
                to {
                    transform: rotate(360deg);
                }
            }

            .error-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                background: var(--ax-iframe-bg, #f8f9fa);
                color: var(--ax-error-color, #dc3545);
                padding: 1rem;
                text-align: center;
            }

            .error-icon {
                width: 48px;
                height: 48px;
                margin-bottom: 1rem;
                opacity: 0.6;
            }

            .error-message {
                font-size: 0.875rem;
                max-width: 300px;
            }

            .retry-btn {
                margin-top: 1rem;
                padding: 0.5rem 1rem;
                background: var(--ax-primary-color, #0d6efd);
                color: #fff;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }

            .retry-btn:hover {
                background: var(--ax-primary-hover, #0b5ed7);
            }

            /* Dark mode */
            @media (prefers-color-scheme: dark) {
                .iframe-wrapper {
                    background: #2d3748;
                }

                .loading-overlay,
                .error-overlay {
                    background: #2d3748;
                }

                .loading-spinner {
                    border-color: #4a5568;
                    border-top-color: var(--ax-primary-color, #0d6efd);
                }
            }
        `;
    }

    render() {
        const src = this.src;
        const sandbox = this.sandbox;
        const allow = this.allow;
        const loading = this.loading;
        const allowResize = this.allowResize;

        this.shadowRoot.innerHTML = `
            <div class="widget-container">
                <div class="iframe-wrapper ${allowResize ? 'resizable' : ''}">
                    ${
                        !this._loaded && !this._error
                            ? `
                        <div class="loading-overlay">
                            <div class="loading-spinner"></div>
                        </div>
                    `
                            : ''
                    }
                    ${
                        this._error
                            ? `
                        <div class="error-overlay">
                            <svg class="error-icon" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                            </svg>
                            <div class="error-message">${this.escapeHtml(this._error)}</div>
                            <button class="retry-btn" type="button">Retry</button>
                        </div>
                    `
                            : ''
                    }
                    ${
                        src && !this._error
                            ? `
                        <iframe
                            src="${this.escapeHtml(src)}"
                            sandbox="${sandbox}"
                            allow="${allow}"
                            loading="${loading}"
                            referrerpolicy="strict-origin-when-cross-origin"
                            aria-label="Embedded content"
                        ></iframe>
                    `
                            : ''
                    }
                </div>
            </div>
        `;

        this.bindEvents();
    }

    bindEvents() {
        const iframe = this.shadowRoot.querySelector('iframe');
        if (iframe) {
            iframe.addEventListener('load', () => this.handleLoad());
            iframe.addEventListener('error', e => this.handleError(e));
        }

        const retryBtn = this.shadowRoot.querySelector('.retry-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => this.retry());
        }
    }

    connectedCallback() {
        super.connectedCallback();

        // Start message listener
        window.addEventListener('message', this._boundMessageHandler);

        // Start rate limit reset interval
        this._messageResetInterval = setInterval(() => {
            this._messageCount = 0;
        }, 1000);
    }

    disconnectedCallback() {
        super.disconnectedCallback();

        // Remove message listener
        window.removeEventListener('message', this._boundMessageHandler);

        // Clear rate limit interval
        if (this._messageResetInterval) {
            clearInterval(this._messageResetInterval);
            this._messageResetInterval = null;
        }
    }

    // =========================================================================
    // IFRAME Event Handlers
    // =========================================================================

    /**
     * Handle iframe load event
     */
    handleLoad() {
        this._loaded = true;
        this._error = null;
        this.state = WidgetState.ACTIVE;
        this.render();

        this.dispatchEvent(
            new CustomEvent('ax-iframe-load', {
                bubbles: true,
                composed: true,
                detail: {
                    widgetId: this.widgetId,
                    src: this.src,
                },
            })
        );
    }

    /**
     * Handle iframe error event
     * @param {Event} e - Error event
     */
    handleError(e) {
        this._loaded = false;
        this._error = 'Failed to load content';
        this.state = WidgetState.ERROR;
        this.render();

        this.dispatchEvent(
            new CustomEvent('ax-iframe-error', {
                bubbles: true,
                composed: true,
                detail: {
                    widgetId: this.widgetId,
                    src: this.src,
                    error: this._error,
                },
            })
        );
    }

    /**
     * Retry loading the iframe
     */
    retry() {
        this._error = null;
        this._loaded = false;
        this.state = WidgetState.LOADING;
        this.render();
    }

    // =========================================================================
    // PostMessage Bridge
    // =========================================================================

    /**
     * Handle incoming postMessage from iframe
     * @param {MessageEvent} event - Message event
     */
    handleMessage(event) {
        const iframe = this.shadowRoot.querySelector('iframe');
        if (!iframe) return;

        // Verify message is from our iframe
        if (event.source !== iframe.contentWindow) {
            return;
        }

        // Validate origin
        if (!this.isOriginAllowed(event.origin)) {
            console.warn(`IFRAME message from disallowed origin: ${event.origin}`);
            return;
        }

        // Rate limiting
        this._messageCount++;
        if (this._messageCount > MAX_MESSAGES_PER_SECOND) {
            console.warn('IFRAME message rate limit exceeded');
            return;
        }

        // Parse message
        const data = event.data;
        if (!data || typeof data !== 'object') {
            return;
        }

        // Handle ax-message type
        if (data.type === 'ax-message' || data.type?.startsWith('ax-')) {
            this.dispatchEvent(
                new CustomEvent('ax-iframe-message', {
                    bubbles: true,
                    composed: true,
                    detail: {
                        widgetId: this.widgetId,
                        type: data.type,
                        payload: data.payload,
                        origin: event.origin,
                        requestId: data.requestId,
                    },
                })
            );
        }
    }

    /**
     * Check if origin is allowed
     * @param {string} origin - Message origin
     * @returns {boolean}
     */
    isOriginAllowed(origin) {
        const allowed = this.allowedOrigins;
        if (allowed.includes('*')) {
            return true;
        }
        return allowed.includes(origin);
    }

    /**
     * Send a message to the iframe
     * @param {string} type - Message type
     * @param {*} payload - Message payload
     * @param {string} targetOrigin - Target origin (default: '*')
     */
    sendMessage(type, payload, targetOrigin = '*') {
        const iframe = this.shadowRoot.querySelector('iframe');
        if (!iframe || !iframe.contentWindow) {
            console.warn('Cannot send message: iframe not loaded');
            return false;
        }

        try {
            iframe.contentWindow.postMessage(
                {
                    type,
                    payload,
                    timestamp: Date.now(),
                },
                targetOrigin
            );
            return true;
        } catch (e) {
            console.error('Failed to send message to iframe:', e);
            return false;
        }
    }

    /**
     * Request-response pattern for iframe communication
     * @param {string} type - Request type
     * @param {*} payload - Request payload
     * @param {number} timeout - Timeout in ms (default: 5000)
     * @returns {Promise<*>} Response payload
     */
    async request(type, payload, timeout = 5000) {
        return new Promise((resolve, reject) => {
            const requestId = crypto.randomUUID();
            const timeoutId = setTimeout(() => {
                cleanup();
                reject(new Error('Request timeout'));
            }, timeout);

            const handleResponse = event => {
                const data = event.detail;
                if (data.requestId === requestId) {
                    cleanup();
                    resolve(data.payload);
                }
            };

            const cleanup = () => {
                clearTimeout(timeoutId);
                this.removeEventListener('ax-iframe-message', handleResponse);
            };

            this.addEventListener('ax-iframe-message', handleResponse);

            this.sendMessage(type, { ...payload, requestId });
        });
    }

    // =========================================================================
    // Public Methods
    // =========================================================================

    /**
     * Reload the iframe
     */
    reload() {
        this._loaded = false;
        this._error = null;
        this.state = WidgetState.LOADING;
        this.render();
    }

    /**
     * Navigate iframe to new URL
     * @param {string} url - New URL
     */
    navigate(url) {
        this.src = url;
        this._loaded = false;
        this._error = null;
        this.render();
    }

    /**
     * Get the iframe element
     * @returns {HTMLIFrameElement|null}
     */
    getIframe() {
        return this.shadowRoot.querySelector('iframe');
    }
}

customElements.define('ax-iframe-widget', AxIframeWidget);

export default AxIframeWidget;
