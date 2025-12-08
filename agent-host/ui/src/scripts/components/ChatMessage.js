/**
 * ChatMessage Web Component
 * Displays a chat message with role-based styling and markdown support
 */
import { marked } from 'marked';

// Configure marked for safe HTML rendering
marked.setOptions({
    breaks: true,
    gfm: true,
});

class ChatMessage extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this._rawContent = '';
    }

    static get observedAttributes() {
        return ['role', 'content', 'status', 'tool-calls'];
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (name === 'content') {
            this._rawContent = newValue || '';
        }
        this.render();
    }

    connectedCallback() {
        this._rawContent = this.getAttribute('content') || '';
        this.render();
    }

    /**
     * Parse tool-calls attribute into an array of tool call objects
     */
    getToolCalls() {
        const toolCallsAttr = this.getAttribute('tool-calls');
        if (!toolCallsAttr) return [];
        try {
            return JSON.parse(toolCallsAttr);
        } catch (e) {
            return [];
        }
    }

    render() {
        const role = this.getAttribute('role') || 'assistant';
        const content = this.getAttribute('content') || '';
        const status = this.getAttribute('status') || 'complete';
        const toolCalls = this.getToolCalls();

        // Get current theme from document
        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';

        // Only show copy button for assistant messages that have content
        const showCopyButton = role === 'assistant' && status === 'complete' && content.trim().length > 0;

        // Show tool badge for assistant messages that used tools
        const showToolBadge = role === 'assistant' && toolCalls.length > 0;

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: flex;
                    margin-bottom: 1rem;
                    animation: fadeIn 0.3s ease;
                    color-scheme: ${isDark ? 'dark' : 'light'};
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .message-wrapper {
                    max-width: 80%;
                    position: relative;
                }
                .message-wrapper.user {
                    margin-left: auto;
                }
                .message-wrapper.assistant {
                    margin-right: auto;
                }
                .message {
                    padding: 1rem 1.25rem;
                    border-radius: 1.25rem;
                    line-height: 1.5;
                    word-wrap: break-word;
                }
                .message.user {
                    background: #0d6efd;
                    color: white;
                    border-bottom-right-radius: 0.25rem;
                }
                .message.assistant {
                    background: ${isDark ? '#2b3035' : '#f8f9fa'};
                    color: ${isDark ? '#e9ecef' : '#212529'};
                    border: 1px solid ${isDark ? '#495057' : '#e9ecef'};
                    border-bottom-left-radius: 0.25rem;
                }
                .content {
                    overflow-wrap: break-word;
                }
                .content p {
                    margin: 0 0 0.5rem 0;
                }
                .content p:last-child {
                    margin-bottom: 0;
                }
                .content pre {
                    background: #1e1e1e;
                    color: #d4d4d4;
                    padding: 12px;
                    border-radius: 8px;
                    overflow-x: auto;
                    margin: 8px 0;
                    font-size: 0.875em;
                }
                .content code {
                    font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
                    font-size: 0.9em;
                }
                .message.user .content code {
                    background: rgba(255, 255, 255, 0.2);
                    padding: 2px 6px;
                    border-radius: 4px;
                }
                .message.assistant .content code {
                    background: ${isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)'};
                    padding: 2px 6px;
                    border-radius: 4px;
                }
                .thinking {
                    display: flex;
                    gap: 4px;
                    padding: 4px 0;
                }
                .thinking span {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: ${isDark ? '#adb5bd' : '#6c757d'};
                    animation: bounce 1.4s infinite ease-in-out;
                }
                .thinking span:nth-child(1) { animation-delay: -0.32s; }
                .thinking span:nth-child(2) { animation-delay: -0.16s; }
                @keyframes bounce {
                    0%, 80%, 100% { transform: scale(0); }
                    40% { transform: scale(1); }
                }

                /* Copy button styles */
                .copy-container {
                    position: relative;
                    display: flex;
                    justify-content: flex-start;
                    margin-top: 4px;
                    opacity: 0;
                    transition: opacity 0.2s ease;
                }
                .message-wrapper:hover .copy-container {
                    opacity: 1;
                }
                .copy-btn {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    padding: 4px 8px;
                    border: none;
                    border-radius: 4px;
                    background: ${isDark ? '#495057' : '#e9ecef'};
                    color: ${isDark ? '#adb5bd' : '#6c757d'};
                    font-size: 0.75rem;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                .copy-btn:hover {
                    background: ${isDark ? '#5c636a' : '#dee2e6'};
                    color: ${isDark ? '#f8f9fa' : '#495057'};
                }
                .copy-btn svg {
                    width: 14px;
                    height: 14px;
                }
                .copy-dropdown {
                    position: absolute;
                    bottom: 100%;
                    left: 0;
                    margin-bottom: 4px;
                    background: ${isDark ? '#2b3035' : '#ffffff'};
                    border: 1px solid ${isDark ? '#495057' : '#e9ecef'};
                    border-radius: 6px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    display: none;
                    z-index: 100;
                    min-width: 140px;
                }
                .copy-dropdown.show {
                    display: block;
                }
                .copy-option {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 8px 12px;
                    border: none;
                    background: none;
                    color: ${isDark ? '#e9ecef' : '#212529'};
                    font-size: 0.8rem;
                    cursor: pointer;
                    width: 100%;
                    text-align: left;
                    transition: background 0.15s ease;
                }
                .copy-option:hover {
                    background: ${isDark ? '#495057' : '#f8f9fa'};
                }
                .copy-option:first-child {
                    border-radius: 6px 6px 0 0;
                }
                .copy-option:last-child {
                    border-radius: 0 0 6px 6px;
                }
                .copy-option svg {
                    width: 14px;
                    height: 14px;
                    opacity: 0.7;
                }
                .copied-toast {
                    position: absolute;
                    bottom: 100%;
                    left: 50%;
                    transform: translateX(-50%);
                    background: ${isDark ? '#198754' : '#198754'};
                    color: white;
                    padding: 4px 10px;
                    border-radius: 4px;
                    font-size: 0.75rem;
                    display: none;
                    white-space: nowrap;
                }
                .copied-toast.show {
                    display: block;
                    animation: fadeOut 1.5s ease forwards;
                }
                @keyframes fadeOut {
                    0%, 70% { opacity: 1; }
                    100% { opacity: 0; }
                }

                /* Tool badges for assistant messages */
                .tool-badges {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 4px;
                    margin-top: 8px;
                    padding-top: 8px;
                    border-top: 1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)'};
                }
                .tool-badge {
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    padding: 2px 8px;
                    border-radius: 12px;
                    background: ${isDark ? 'rgba(13, 202, 240, 0.15)' : 'rgba(13, 110, 253, 0.1)'};
                    color: ${isDark ? '#0dcaf0' : '#0d6efd'};
                    font-size: 0.7rem;
                    font-weight: 500;
                }
                .tool-badge svg {
                    width: 12px;
                    height: 12px;
                }
            </style>
            <div class="message-wrapper ${role}">
                <div class="message ${role}">
                    <div class="content">
                        ${status === 'thinking' ? '<div class="thinking"><span></span><span></span><span></span></div>' : this.formatContent(content)}
                        ${showToolBadge ? this.renderToolBadges(toolCalls, isDark) : ''}
                    </div>
                </div>
                ${
                    showCopyButton
                        ? `
                <div class="copy-container">
                    <button class="copy-btn" title="Copy message">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        Copy
                    </button>
                    <div class="copy-dropdown">
                        <button class="copy-option" data-format="markdown">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                            </svg>
                            Copy Markdown
                        </button>
                        <button class="copy-option" data-format="text">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7" />
                            </svg>
                            Copy Text
                        </button>
                        <button class="copy-option" data-format="html">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                            </svg>
                            Copy HTML
                        </button>
                    </div>
                    <div class="copied-toast">Copied!</div>
                </div>
                `
                        : ''
                }
            </div>
        `;

        // Bind copy button events if present
        if (showCopyButton) {
            this.bindCopyEvents();
        }
    }

    bindCopyEvents() {
        const copyBtn = this.shadowRoot.querySelector('.copy-btn');
        const dropdown = this.shadowRoot.querySelector('.copy-dropdown');
        const toast = this.shadowRoot.querySelector('.copied-toast');

        if (!copyBtn || !dropdown) return;

        // Toggle dropdown on button click
        copyBtn.addEventListener('click', e => {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', () => {
            dropdown.classList.remove('show');
        });

        // Handle copy options
        const options = this.shadowRoot.querySelectorAll('.copy-option');
        options.forEach(option => {
            option.addEventListener('click', async e => {
                e.stopPropagation();
                const format = option.dataset.format;
                await this.copyContent(format);

                // Show toast
                dropdown.classList.remove('show');
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 1500);
            });
        });
    }

    async copyContent(format) {
        const content = this._rawContent;

        try {
            switch (format) {
                case 'markdown':
                    await navigator.clipboard.writeText(content);
                    break;
                case 'text':
                    // Strip markdown formatting for plain text
                    const plainText = this.stripMarkdown(content);
                    await navigator.clipboard.writeText(plainText);
                    break;
                case 'html':
                    const html = marked.parse(content);
                    // Use ClipboardItem for HTML copying
                    const blob = new Blob([html], { type: 'text/html' });
                    const clipboardItem = new ClipboardItem({
                        'text/html': blob,
                        'text/plain': new Blob([content], { type: 'text/plain' }),
                    });
                    await navigator.clipboard.write([clipboardItem]);
                    break;
            }
        } catch (err) {
            console.error('Failed to copy:', err);
            // Fallback to basic copy
            await navigator.clipboard.writeText(content);
        }
    }

    stripMarkdown(text) {
        return (
            text
                // Remove headers
                .replace(/^#{1,6}\s+/gm, '')
                // Remove bold/italic
                .replace(/\*\*([^*]+)\*\*/g, '$1')
                .replace(/\*([^*]+)\*/g, '$1')
                .replace(/__([^_]+)__/g, '$1')
                .replace(/_([^_]+)_/g, '$1')
                // Remove inline code
                .replace(/`([^`]+)`/g, '$1')
                // Remove code blocks
                .replace(/```[\s\S]*?```/g, '')
                // Remove links but keep text
                .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
                // Remove images
                .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
                // Remove blockquotes
                .replace(/^>\s+/gm, '')
                // Remove horizontal rules
                .replace(/^[-*_]{3,}\s*$/gm, '')
                // Remove list markers
                .replace(/^[\s]*[-*+]\s+/gm, '')
                .replace(/^[\s]*\d+\.\s+/gm, '')
                // Normalize whitespace
                .replace(/\n{3,}/g, '\n\n')
                .trim()
        );
    }

    formatContent(content) {
        // Use marked for proper markdown parsing
        return marked.parse(content);
    }

    /**
     * Render tool badges showing which tools were used in this response
     * @param {Array} toolCalls - Array of tool call objects
     * @param {boolean} isDark - Whether dark theme is active
     * @returns {string} HTML string for tool badges
     */
    renderToolBadges(toolCalls, isDark) {
        if (!toolCalls || toolCalls.length === 0) return '';

        const badges = toolCalls
            .map(
                tc => `
            <span class="tool-badge" title="${this.escapeHtml(tc.tool_name)}">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                ${this.escapeHtml(this.formatToolName(tc.tool_name))}
            </span>
        `
            )
            .join('');

        return `<div class="tool-badges">${badges}</div>`;
    }

    /**
     * Format tool name for display (shorten long names)
     * @param {string} name - Tool name
     * @returns {string} Formatted name
     */
    formatToolName(name) {
        // Shorten very long tool names
        if (name.length > 25) {
            return name.substring(0, 22) + '...';
        }
        return name;
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
}

customElements.define('chat-message', ChatMessage);

export default ChatMessage;
