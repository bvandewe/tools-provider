/**
 * Text Display Widget Component
 * Renders formatted text content (markdown, HTML, or plain text).
 *
 * Attributes:
 * - content: The text content to display
 * - content-type: "markdown" | "html" | "text" (default: "markdown")
 * - max-height: Optional maximum height with scroll
 * - collapsible: Whether content can be collapsed
 * - collapsed: Initial collapsed state
 *
 * Events:
 * - ax-toggle: Fired when collapsed state changes
 *   Detail: { collapsed: boolean }
 *
 * CSS Variables:
 * - --ax-text-display-bg: Background color
 * - --ax-text-display-border: Border color
 * - --ax-text-display-font-size: Font size
 * - --ax-text-display-line-height: Line height
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';
import DOMPurify from 'dompurify';
import { marked } from 'marked';

// Configure marked for safe HTML rendering
marked.setOptions({
    breaks: true,
    gfm: true,
});

class AxTextDisplay extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'content', 'content-type', 'max-height', 'collapsible', 'collapsed'];
    }

    constructor() {
        super();
        this._collapsed = false;
    }

    // =========================================================================
    // Attribute Getters
    // =========================================================================

    get content() {
        return this.getAttribute('content') || '';
    }

    set content(value) {
        this.setAttribute('content', value);
    }

    get contentType() {
        return this.getAttribute('content-type') || 'markdown';
    }

    get maxHeight() {
        return this.getAttribute('max-height') || null;
    }

    get collapsible() {
        return this.hasAttribute('collapsible');
    }

    get collapsed() {
        return this.hasAttribute('collapsed') || this._collapsed;
    }

    set collapsed(value) {
        this._collapsed = value;
        if (value) {
            this.setAttribute('collapsed', '');
        } else {
            this.removeAttribute('collapsed');
        }
        this.render();
    }

    // =========================================================================
    // AxWidgetBase Implementation
    // =========================================================================

    getValue() {
        return this.content;
    }

    setValue(value) {
        this.content = value;
    }

    validate() {
        // Display widgets don't typically need validation
        return { valid: true, errors: [], warnings: [] };
    }

    async getStyles() {
        return `
            ${this.getBaseStyles()}

            :host {
                --ax-text-display-bg: var(--ax-widget-bg, #ffffff);
                --ax-text-display-border: var(--ax-border-color, #e9ecef);
            }

            .widget-container {
                background: var(--ax-text-display-bg);
                border: 1px solid var(--ax-text-display-border);
            }

            .content-wrapper {
                position: relative;
                overflow: hidden;
                ${this.maxHeight ? `max-height: ${this.collapsed ? '4rem' : this.maxHeight};` : ''}
                transition: max-height 0.3s ease;
            }

            .content-wrapper.scrollable {
                overflow-y: auto;
            }

            .content-wrapper.collapsed {
                max-height: 4rem;
            }

            .content-wrapper.collapsed::after {
                content: '';
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                height: 2rem;
                background: linear-gradient(transparent, var(--ax-text-display-bg));
                pointer-events: none;
            }

            .content {
                font-size: var(--ax-text-display-font-size, 1rem);
                line-height: var(--ax-text-display-line-height, 1.6);
                color: var(--ax-text-color, #212529);
            }

            /* Markdown/HTML content styles */
            .content p {
                margin: 0 0 1rem 0;
            }

            .content p:last-child {
                margin-bottom: 0;
            }

            .content h1, .content h2, .content h3,
            .content h4, .content h5, .content h6 {
                margin: 1.5rem 0 0.75rem 0;
                font-weight: 600;
                line-height: 1.25;
            }

            .content h1:first-child, .content h2:first-child,
            .content h3:first-child, .content h4:first-child,
            .content h5:first-child, .content h6:first-child {
                margin-top: 0;
            }

            .content h1 { font-size: 1.75rem; }
            .content h2 { font-size: 1.5rem; }
            .content h3 { font-size: 1.25rem; }
            .content h4 { font-size: 1.125rem; }
            .content h5 { font-size: 1rem; }
            .content h6 { font-size: 0.875rem; }

            .content pre {
                background: #1e1e1e;
                color: #d4d4d4;
                padding: 1rem;
                border-radius: 8px;
                overflow-x: auto;
                margin: 1rem 0;
                font-size: 0.875em;
                white-space: pre-wrap;
                word-wrap: break-word;
            }

            .content code {
                font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
                font-size: 0.9em;
                background: rgba(0, 0, 0, 0.05);
                padding: 2px 6px;
                border-radius: 4px;
            }

            .content pre code {
                background: transparent;
                padding: 0;
            }

            .content table {
                width: 100%;
                border-collapse: collapse;
                margin: 1rem 0;
                font-size: 0.9em;
            }

            .content th, .content td {
                border: 1px solid var(--ax-text-display-border);
                padding: 8px 12px;
                text-align: left;
            }

            .content th {
                background: var(--ax-widget-bg, #f8f9fa);
                font-weight: 600;
            }

            .content ul, .content ol {
                margin: 1rem 0;
                padding-left: 1.5rem;
            }

            .content li {
                margin: 0.25rem 0;
            }

            .content blockquote {
                border-left: 4px solid var(--ax-primary-color, #0d6efd);
                margin: 1rem 0;
                padding-left: 1rem;
                color: var(--ax-text-muted, #6c757d);
            }

            .content a {
                color: var(--ax-primary-color, #0d6efd);
                text-decoration: none;
            }

            .content a:hover {
                text-decoration: underline;
            }

            .content img {
                max-width: 100%;
                height: auto;
                border-radius: 4px;
            }

            .content hr {
                border: none;
                border-top: 1px solid var(--ax-text-display-border);
                margin: 1.5rem 0;
            }

            .toggle-btn {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin-top: 0.75rem;
                padding: 0.5rem 0;
                background: transparent;
                border: none;
                color: var(--ax-primary-color, #0d6efd);
                font-size: 0.875rem;
                cursor: pointer;
                transition: color 0.15s ease;
            }

            .toggle-btn:hover {
                color: var(--ax-primary-hover, #0b5ed7);
            }

            .toggle-btn svg {
                width: 16px;
                height: 16px;
                transition: transform 0.3s ease;
            }

            .toggle-btn.expanded svg {
                transform: rotate(180deg);
            }

            /* Dark mode support */
            @media (prefers-color-scheme: dark) {
                :host {
                    --ax-text-display-bg: #1a202c;
                    --ax-text-display-border: #4a5568;
                }

                .content code {
                    background: rgba(255, 255, 255, 0.1);
                }
            }
        `;
    }

    render() {
        const content = this.content;
        const renderedContent = this.renderContent(content);
        const isCollapsible = this.collapsible;
        const isCollapsed = this.collapsed;

        this.shadowRoot.innerHTML = `
            <div class="widget-container" role="region" aria-label="Text content">
                <div class="content-wrapper ${this.maxHeight ? 'scrollable' : ''} ${isCollapsed ? 'collapsed' : ''}">
                    <div class="content">
                        ${renderedContent}
                    </div>
                </div>
                ${
                    isCollapsible
                        ? `
                    <button class="toggle-btn ${isCollapsed ? '' : 'expanded'}" aria-expanded="${!isCollapsed}">
                        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                            <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
                        </svg>
                        <span>${isCollapsed ? 'Show more' : 'Show less'}</span>
                    </button>
                `
                        : ''
                }
            </div>
        `;

        this.bindEvents();
    }

    bindEvents() {
        if (this.collapsible) {
            const toggleBtn = this.shadowRoot.querySelector('.toggle-btn');
            if (toggleBtn) {
                toggleBtn.addEventListener('click', () => this.toggleCollapsed());
            }
        }
    }

    // =========================================================================
    // Content Rendering
    // =========================================================================

    /**
     * Render content based on content type
     * @param {string} content - Raw content
     * @returns {string} Rendered HTML
     */
    renderContent(content) {
        if (!content) return '';

        switch (this.contentType) {
            case 'html':
                return this.sanitizeHtml(content);
            case 'text':
                return this.escapeHtml(content);
            case 'markdown':
            default:
                return this.renderMarkdownSafe(content);
        }
    }

    /**
     * Render markdown with sanitization
     * @param {string} text - Markdown text
     * @returns {string} Sanitized HTML
     */
    renderMarkdownSafe(text) {
        try {
            const html = marked.parse(text);
            return this.sanitizeHtml(html);
        } catch (e) {
            console.warn('Markdown parsing failed:', e);
            return this.escapeHtml(text);
        }
    }

    /**
     * Sanitize HTML content
     * @param {string} html - HTML content
     * @returns {string} Sanitized HTML
     */
    sanitizeHtml(html) {
        // Use DOMPurify if available, otherwise basic sanitization
        if (typeof DOMPurify !== 'undefined') {
            return DOMPurify.sanitize(html, {
                ALLOWED_TAGS: [
                    'h1',
                    'h2',
                    'h3',
                    'h4',
                    'h5',
                    'h6',
                    'p',
                    'br',
                    'hr',
                    'ul',
                    'ol',
                    'li',
                    'dl',
                    'dt',
                    'dd',
                    'table',
                    'thead',
                    'tbody',
                    'tr',
                    'th',
                    'td',
                    'blockquote',
                    'pre',
                    'code',
                    'strong',
                    'em',
                    'a',
                    'img',
                    'span',
                    'div',
                    'sup',
                    'sub',
                ],
                ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'id', 'target', 'rel'],
                ALLOW_DATA_ATTR: false,
            });
        }
        // Fallback: basic sanitization (strips dangerous elements)
        return html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '').replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '');
    }

    // =========================================================================
    // Collapsible Behavior
    // =========================================================================

    /**
     * Toggle collapsed state
     */
    toggleCollapsed() {
        this.collapsed = !this.collapsed;
        this.dispatchEvent(
            new CustomEvent('ax-toggle', {
                bubbles: true,
                composed: true,
                detail: { collapsed: this.collapsed },
            })
        );
    }

    // =========================================================================
    // Streaming Support
    // =========================================================================

    /**
     * Append content for streaming display
     * @param {string} chunk - Content chunk to append
     */
    appendContent(chunk) {
        const currentContent = this.content;
        this.content = currentContent + chunk;
    }

    /**
     * Clear all content
     */
    clearContent() {
        this.content = '';
    }
}

customElements.define('ax-text-display', AxTextDisplay);

export default AxTextDisplay;
