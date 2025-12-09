/**
 * ToolCallCard Web Component
 * Displays a tool call with its status and result
 */
class ToolCallCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    static get observedAttributes() {
        return ['tool-name', 'status', 'result'];
    }

    attributeChangedCallback() {
        this.render();
    }

    connectedCallback() {
        this.render();
    }

    render() {
        const toolName = this.getAttribute('tool-name') || 'Unknown';
        const status = this.getAttribute('status') || 'pending';
        const result = this.getAttribute('result');

        // Get current theme from document
        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';

        const statusColors = {
            pending: '#6c757d',
            executing: '#0d6efd',
            success: '#198754',
            error: '#dc3545',
        };

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    margin: 8px 0;
                    color-scheme: ${isDark ? 'dark' : 'light'};
                }
                .tool-card {
                    background: ${isDark ? '#2b3035' : '#f8f9fa'};
                    border: 1px solid ${isDark ? '#495057' : '#e9ecef'};
                    border-radius: 8px;
                    padding: 12px 16px;
                    font-size: 0.9em;
                }
                .tool-header {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                .tool-icon {
                    font-size: 1.1em;
                }
                .tool-name {
                    font-weight: 600;
                    color: ${isDark ? '#adb5bd' : '#495057'};
                }
                .tool-status {
                    margin-left: auto;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 0.85em;
                    color: white;
                    background: ${statusColors[status]};
                }
                .tool-result {
                    margin-top: 8px;
                    padding: 8px;
                    background: #1e1e1e;
                    color: #d4d4d4;
                    border-radius: 4px;
                    font-family: 'Monaco', 'Menlo', monospace;
                    font-size: 0.85em;
                    max-height: 200px;
                    overflow: auto;
                }
                .tool-result pre {
                    margin: 0;
                    white-space: pre-wrap;
                    word-break: break-word;
                }
                .executing .tool-icon {
                    animation: spin 1s linear infinite;
                }
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            </style>
            <div class="tool-card ${status}">
                <div class="tool-header">
                    <span class="tool-icon">${status === 'executing' ? '⚙️' : '🔧'}</span>
                    <span class="tool-name">${toolName}</span>
                    <span class="tool-status">${status === 'executing' ? 'Executing...' : status}</span>
                </div>
                ${result ? `<div class="tool-result"><pre>${result}</pre></div>` : ''}
            </div>
        `;
    }

    setStatus(status) {
        this.setAttribute('status', status);
    }

    setResult(result) {
        this.setAttribute('result', typeof result === 'object' ? JSON.stringify(result, null, 2) : result);
    }
}

customElements.define('tool-call-card', ToolCallCard);

export default ToolCallCard;
