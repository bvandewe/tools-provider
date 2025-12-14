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

// Custom renderer to handle sandbox: URLs and file download links
const renderer = new marked.Renderer();
const originalLinkRenderer = renderer.link.bind(renderer);

renderer.link = function (token) {
    // In newer marked versions, link receives a token object with href, title, text properties
    // Handle both old-style (href, title, text) and new-style (token object) API
    let href, title, text;

    if (typeof token === 'object' && token !== null) {
        // New API: token is an object
        href = token.href;
        title = token.title;
        text = token.text;
    } else {
        // Old API: separate arguments (fallback)
        href = token;
        title = arguments[1];
        text = arguments[2];
    }

    // Ensure href is a string
    if (typeof href !== 'string') {
        href = String(href || '');
    }

    // Handle sandbox: URLs - convert to proper download links
    // LLMs sometimes generate these for file links
    if (href.startsWith('sandbox:')) {
        href = href.replace('sandbox:', '');
    }

    // Check if this is a file download link (from our files API)
    const isFileDownload = href.includes('/api/files/');

    if (isFileDownload) {
        // Add download attribute and styling for file links
        const titleAttr = title ? ` title="${title}"` : ' title="Click to download"';
        const filename = text || href.split('/').pop();
        return `<a href="${href}"${titleAttr} class="file-download-link" download>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16" style="margin-right: 4px; vertical-align: -2px;">
                <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
                <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z"/>
            </svg>${filename}</a>`;
    }

    // For non-file links, update the token if using new API and delegate
    if (typeof token === 'object' && token !== null) {
        token.href = href;
        return originalLinkRenderer(token);
    }

    // Use original renderer for other links (old API)
    return originalLinkRenderer(href, title, text);
};

marked.use({ renderer });

class ChatMessage extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this._rawContent = '';
    }

    static get observedAttributes() {
        return ['role', 'content', 'status', 'tool-calls', 'tool-results', 'created-at'];
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

    /**
     * Parse tool-results attribute into an array of tool result objects
     */
    getToolResults() {
        const toolResultsAttr = this.getAttribute('tool-results');
        if (!toolResultsAttr) return [];
        try {
            return JSON.parse(toolResultsAttr);
        } catch (e) {
            return [];
        }
    }

    render() {
        const role = this.getAttribute('role') || 'assistant';
        const content = this.getAttribute('content') || '';
        const status = this.getAttribute('status') || 'complete';
        const createdAt = this.getAttribute('created-at') || '';
        const toolCalls = this.getToolCalls();
        const toolResults = this.getToolResults();

        // Get current theme from document
        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';

        // Show copy button for both assistant and user messages that have content
        const showCopyButton = (role === 'assistant' || role === 'user') && status === 'complete' && content.trim().length > 0;

        // Show tool badge for assistant messages that have tool calls OR tool results
        const showToolBadge = role === 'assistant' && (toolCalls.length > 0 || toolResults.length > 0);

        // Show timestamp for completed messages (not thinking or waiting)
        const showTimestamp = createdAt && status !== 'thinking' && status !== 'waiting';

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
                /* File download links */
                .content a.file-download-link {
                    display: inline-flex;
                    align-items: center;
                    padding: 6px 12px;
                    background: ${isDark ? 'rgba(13, 110, 253, 0.2)' : 'rgba(13, 110, 253, 0.1)'};
                    border: 1px solid ${isDark ? 'rgba(13, 110, 253, 0.4)' : 'rgba(13, 110, 253, 0.3)'};
                    border-radius: 6px;
                    color: ${isDark ? '#6ea8fe' : '#0d6efd'};
                    text-decoration: none;
                    font-weight: 500;
                    transition: all 0.2s ease;
                    margin: 4px 0;
                }
                .content a.file-download-link:hover {
                    background: ${isDark ? 'rgba(13, 110, 253, 0.3)' : 'rgba(13, 110, 253, 0.2)'};
                    border-color: ${isDark ? 'rgba(13, 110, 253, 0.6)' : 'rgba(13, 110, 253, 0.5)'};
                    text-decoration: none;
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
                .waiting {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 4px 0;
                    color: ${isDark ? '#ffc107' : '#d97706'};
                    font-size: 0.85rem;
                }
                .waiting-icon {
                    font-size: 1rem;
                    animation: pulse 1.5s infinite;
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }

                /* Copy button styles */
                .copy-container {
                    position: relative;
                    display: flex;
                    justify-content: flex-start;
                    align-items: center;
                    margin-top: 4px;
                    opacity: 0;
                    transition: opacity 0.2s ease;
                }
                /* User messages: align copy container to right */
                .message-wrapper.user .copy-container {
                    justify-content: flex-end;
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
                /* User message copy button - different styling */
                .message-wrapper.user .copy-btn {
                    background: rgba(255, 255, 255, 0.2);
                    color: rgba(255, 255, 255, 0.9);
                }
                .message-wrapper.user .copy-btn:hover {
                    background: rgba(255, 255, 255, 0.3);
                    color: white;
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
                /* User message dropdown - position right aligned */
                .message-wrapper.user .copy-dropdown {
                    left: auto;
                    right: 0;
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

                /* Tool badges container and header */
                .tool-badges-container {
                    margin-top: 12px;
                    padding-top: 8px;
                    border-top: 1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)'};
                }
                .tool-badges-header {
                    font-size: 0.75rem;
                    font-weight: 500;
                    color: ${isDark ? '#9ca3af' : '#6b7280'};
                    margin-bottom: 6px;
                }

                /* Tool badges for assistant messages */
                .tool-badges {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 4px;
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
                    cursor: pointer;
                    transition: all 0.15s ease;
                    border: 1px solid transparent;
                }
                .tool-badge:hover {
                    background: ${isDark ? 'rgba(13, 202, 240, 0.25)' : 'rgba(13, 110, 253, 0.2)'};
                    border-color: ${isDark ? 'rgba(13, 202, 240, 0.3)' : 'rgba(13, 110, 253, 0.3)'};
                }
                .tool-badge svg {
                    width: 12px;
                    height: 12px;
                }

                /* Timestamp styles */
                .timestamp {
                    font-size: 0.65rem;
                    color: ${isDark ? '#6c757d' : '#adb5bd'};
                    cursor: default;
                    position: relative;
                    margin-left: auto;
                    padding-left: 12px;
                }
                /* User messages: timestamp on left side */
                .message-wrapper.user .timestamp {
                    margin-left: 0;
                    margin-right: auto;
                    padding-left: 0;
                    padding-right: 12px;
                    order: -1;
                }
                .timestamp:hover {
                    color: ${isDark ? '#adb5bd' : '#6c757d'};
                }
                .timestamp .tooltip {
                    position: absolute;
                    top: 100%;
                    left: 0;
                    background: ${isDark ? '#212529' : '#333'};
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.7rem;
                    white-space: nowrap;
                    display: none;
                    z-index: 100;
                    margin-top: 4px;
                }
                /* User messages: tooltip aligned to right */
                .message-wrapper.user .timestamp .tooltip {
                    left: auto;
                    right: 0;
                }
                .timestamp .tooltip::after {
                    content: '';
                    position: absolute;
                    bottom: 100%;
                    left: 12px;
                    border: 4px solid transparent;
                    border-bottom-color: ${isDark ? '#212529' : '#333'};
                }
                .message-wrapper.user .timestamp .tooltip::after {
                    left: auto;
                    right: 12px;
                }
                .timestamp:hover .tooltip {
                    display: block;
                }
            </style>
            <div class="message-wrapper ${role}">
                <div class="message ${role}">
                    <div class="content">
                        ${
                            status === 'thinking'
                                ? '<div class="thinking"><span></span><span></span><span></span></div>'
                                : status === 'waiting'
                                  ? '<div class="waiting"><span class="waiting-icon">⏳</span> Waiting for your response...</div>'
                                  : this.formatContent(content)
                        }
                        ${showToolBadge ? this.renderToolBadges(toolCalls, toolResults, isDark) : ''}
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
                    ${
                        showTimestamp
                            ? `<span class="timestamp">
                        ${this.formatTimeAgo(createdAt)}
                        <span class="tooltip">${this.formatFullTimestamp(createdAt)}</span>
                    </span>`
                            : ''
                    }
                </div>
                `
                        : showTimestamp
                          ? `
                <div class="copy-container">
                    <span class="timestamp">
                        ${this.formatTimeAgo(createdAt)}
                        <span class="tooltip">${this.formatFullTimestamp(createdAt)}</span>
                    </span>
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

        // Bind tool badge click events
        if (showToolBadge) {
            this.bindToolBadgeEvents(toolCalls, toolResults);
        }
    }

    /**
     * Bind click events to tool badges
     */
    bindToolBadgeEvents(toolCalls, toolResults) {
        const badges = this.shadowRoot.querySelectorAll('.tool-badge');
        badges.forEach(badge => {
            badge.addEventListener('click', e => {
                e.stopPropagation();
                // Dispatch custom event with tool data
                this.dispatchEvent(
                    new CustomEvent('tool-badge-click', {
                        bubbles: true,
                        composed: true, // Allow event to cross shadow DOM boundary
                        detail: {
                            toolCalls,
                            toolResults,
                        },
                    })
                );
            });
        });
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
     * @param {Array} toolCalls - Array of tool call objects (requests)
     * @param {Array} toolResults - Array of tool result objects (responses)
     * @param {boolean} isDark - Whether dark theme is active
     * @returns {string} HTML string for tool badges
     */
    renderToolBadges(toolCalls, toolResults, isDark) {
        // Collect unique tool names from both calls and results
        const toolNames = new Set();

        if (toolCalls && toolCalls.length > 0) {
            // Handle both `name` (from backend) and `tool_name` (from client action) properties
            toolCalls.forEach(tc => {
                const toolName = tc.tool_name || tc.name;
                if (toolName) {
                    toolNames.add(toolName);
                }
            });
        }

        if (toolResults && toolResults.length > 0) {
            toolResults.forEach(tr => toolNames.add(tr.tool_name));
        }

        if (toolNames.size === 0) return '';

        // Determine success status from results
        const resultsMap = new Map();
        if (toolResults) {
            toolResults.forEach(tr => {
                resultsMap.set(tr.tool_name, tr.success);
            });
        }

        // Create header text based on number of tools
        const toolCount = toolNames.size;
        const headerText = toolCount === 1 ? 'ChatBot tool call...' : `ChatBot called ${toolCount} tools...`;

        const badges = Array.from(toolNames)
            .map(toolName => {
                const hasResult = resultsMap.has(toolName);
                const success = resultsMap.get(toolName);
                // Show checkmark for success, X for failure, gear for pending/call-only
                const statusIcon = hasResult
                    ? success
                        ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />'
                        : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />'
                    : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />';

                return `
                <span class="tool-badge" title="Click to view details: ${this.escapeHtml(toolName)}">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        ${statusIcon}
                    </svg>
                    ${this.escapeHtml(this.formatToolName(toolName))}
                </span>
            `;
            })
            .join('');

        return `
            <div class="tool-badges-container">
                <div class="tool-badges-header">${headerText}</div>
                <div class="tool-badges">${badges}</div>
            </div>
        `;
    }

    /**
     * Format tool name for display - convert operation_id to human-friendly format
     * @param {string} name - Tool name (e.g., "create_menu_item_api_menu_post")
     * @returns {string} Formatted name (e.g., "Create Menu Item")
     */
    formatToolName(name) {
        if (!name) return 'Unknown Tool';

        // If it's a full tool ID (source_id:operation_id), extract operation_id
        if (name.includes(':')) {
            name = name.split(':').pop();
        }

        // Remove common suffixes like _api_*, _get, _post, _put, _delete, _patch
        let cleanName = name
            .replace(/_api_[a-z_]+_(get|post|put|delete|patch)$/i, '')
            .replace(/_(get|post|put|delete|patch)$/i, '')
            .replace(/^(get|post|put|delete|patch)_/i, '');

        // Handle camelCase
        cleanName = cleanName.replace(/([a-z])([A-Z])/g, '$1_$2');

        // Split by underscores, dashes, or double underscores
        const words = cleanName
            .split(/[_\-]+/)
            .filter(word => word.length > 0)
            .filter(word => !['api', 'v1', 'v2'].includes(word.toLowerCase()));

        // Capitalize each word
        const formattedWords = words.map(word => {
            // Handle common abbreviations
            const upperWords = ['id', 'url', 'api', 'uuid', 'mcp'];
            if (upperWords.includes(word.toLowerCase())) {
                return word.toUpperCase();
            }
            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
        });

        const result = formattedWords.join(' ') || 'Unknown Tool';

        // Truncate if still too long
        if (result.length > 30) {
            return result.substring(0, 27) + '...';
        }
        return result;
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

    /**
     * Format a timestamp into "time ago" format using browser's locale
     * @param {string} isoString - ISO 8601 timestamp string
     * @returns {string} Human-readable "time ago" string
     */
    formatTimeAgo(isoString) {
        if (!isoString) return '';

        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffSecs = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSecs / 60);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        // Use Intl.RelativeTimeFormat for locale-aware relative time
        const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto', style: 'narrow' });

        if (diffSecs < 60) return rtf.format(-diffSecs, 'second');
        if (diffMins < 60) return rtf.format(-diffMins, 'minute');
        if (diffHours < 24) return rtf.format(-diffHours, 'hour');
        if (diffDays < 7) return rtf.format(-diffDays, 'day');

        // For older messages, show date in locale format
        return date.toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
        });
    }

    /**
     * Format a timestamp for tooltip display
     * @param {string} isoString - ISO 8601 timestamp string
     * @returns {string} Formatted date and time string
     */
    formatFullTimestamp(isoString) {
        if (!isoString) return '';

        const date = new Date(isoString);
        return date.toLocaleString(undefined, {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
    }
}

customElements.define('chat-message', ChatMessage);

export default ChatMessage;
