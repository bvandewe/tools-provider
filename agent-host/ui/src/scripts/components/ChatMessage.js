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
    }

    static get observedAttributes() {
        return ['role', 'content', 'status'];
    }

    attributeChangedCallback() {
        this.render();
    }

    connectedCallback() {
        this.render();
    }

    render() {
        const role = this.getAttribute('role') || 'assistant';
        const content = this.getAttribute('content') || '';
        const status = this.getAttribute('status') || 'complete';

        // Get current theme from document
        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';

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
                .message {
                    max-width: 80%;
                    padding: 1rem 1.25rem;
                    border-radius: 1.25rem;
                    line-height: 1.5;
                    word-wrap: break-word;
                }
                .message.user {
                    margin-left: auto;
                    background: #0d6efd;
                    color: white;
                    border-bottom-right-radius: 0.25rem;
                }
                .message.assistant {
                    margin-right: auto;
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
            </style>
            <div class="message ${role}">
                <div class="content">
                    ${status === 'thinking' ? '<div class="thinking"><span></span><span></span><span></span></div>' : this.formatContent(content)}
                </div>
            </div>
        `;
    }

    formatContent(content) {
        // Use marked for proper markdown parsing
        return marked.parse(content);
    }
}

customElements.define('chat-message', ChatMessage);

export default ChatMessage;
