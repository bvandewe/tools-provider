/**
 * Code Editor Widget Component
 * Renders a code editor for the user to write code
 *
 * Note: This is a simplified version using a styled textarea.
 * For production, consider integrating Monaco Editor for full IDE features.
 *
 * Attributes:
 * - prompt: The question or prompt to display
 * - language: Programming language for syntax hints (python, javascript, etc.)
 * - initial-code: Pre-populated code in the editor
 * - min-lines: Minimum number of lines for the editor
 * - max-lines: Maximum number of lines for the editor
 *
 * Events:
 * - ax-response: Fired when user submits their code
 *   Detail: { code: string, language: string }
 */
import { marked } from 'marked';

// Configure marked for safe HTML rendering
marked.setOptions({
    breaks: true,
    gfm: true,
});

class AxCodeEditor extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    static get observedAttributes() {
        return ['prompt', 'language', 'initial-code', 'min-lines', 'max-lines'];
    }

    connectedCallback() {
        this.render();
        this.setupEventListeners();
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (oldValue !== newValue && this.shadowRoot) {
            this.render();
            this.setupEventListeners();
        }
    }

    get prompt() {
        return this.getAttribute('prompt') || '';
    }

    get language() {
        return this.getAttribute('language') || 'python';
    }

    get initialCode() {
        return this.getAttribute('initial-code') || '';
    }

    get minLines() {
        const val = this.getAttribute('min-lines');
        return val ? parseInt(val, 10) : 5;
    }

    get maxLines() {
        const val = this.getAttribute('max-lines');
        return val ? parseInt(val, 10) : 30;
    }

    render() {
        const lineHeight = 1.5; // rem
        const minHeight = this.minLines * lineHeight;
        const maxHeight = this.maxLines * lineHeight;

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    font-family: var(--font-family, system-ui, -apple-system, sans-serif);
                }

                .widget-container {
                    background: var(--widget-bg, #f8f9fa);
                    border: 1px solid var(--widget-border, #dee2e6);
                    border-radius: 12px;
                    padding: 1.25rem;
                    margin: 0.5rem 0;
                    animation: slideIn 0.3s ease-out;
                }

                @keyframes slideIn {
                    from {
                        opacity: 0;
                        transform: translateY(10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                .prompt {
                    font-size: 1rem;
                    font-weight: 500;
                    color: var(--text-color, #212529);
                    margin-bottom: 1rem;
                    line-height: 1.5;
                }

                /* Markdown content styles */
                .prompt p {
                    margin: 0 0 0.5rem 0;
                }
                .prompt p:last-child {
                    margin-bottom: 0;
                }
                .prompt pre {
                    background: #1e1e1e;
                    color: #d4d4d4;
                    padding: 12px;
                    border-radius: 8px;
                    overflow-x: auto;
                    margin: 8px 0;
                    font-size: 0.875em;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
                .prompt code {
                    font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
                    font-size: 0.9em;
                    background: rgba(0, 0, 0, 0.05);
                    padding: 2px 6px;
                    border-radius: 4px;
                }
                .prompt pre code {
                    background: transparent;
                    padding: 0;
                }
                .prompt table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 8px 0;
                    font-size: 0.9em;
                }
                .prompt th, .prompt td {
                    border: 1px solid var(--widget-border, #dee2e6);
                    padding: 8px 12px;
                    text-align: left;
                }
                .prompt th {
                    background: var(--widget-bg, #f8f9fa);
                    font-weight: 600;
                }
                .prompt ul, .prompt ol {
                    margin: 8px 0;
                    padding-left: 1.5rem;
                }
                .prompt li {
                    margin: 4px 0;
                }
                .prompt blockquote {
                    border-left: 4px solid var(--primary-color, #0d6efd);
                    margin: 8px 0;
                    padding-left: 1rem;
                    color: var(--text-muted, #6c757d);
                }

                .editor-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 0.5rem;
                }

                .language-badge {
                    display: inline-flex;
                    align-items: center;
                    gap: 0.375rem;
                    padding: 0.25rem 0.625rem;
                    background: var(--badge-bg, #e9ecef);
                    border-radius: 4px;
                    font-size: 0.75rem;
                    color: var(--text-muted, #6c757d);
                    text-transform: uppercase;
                    font-weight: 500;
                }

                .language-icon {
                    width: 14px;
                    height: 14px;
                }

                .editor-container {
                    position: relative;
                    border: 2px solid var(--editor-border, #343a40);
                    border-radius: 8px;
                    overflow: hidden;
                }

                .line-numbers {
                    position: absolute;
                    left: 0;
                    top: 0;
                    bottom: 0;
                    width: 3rem;
                    background: var(--line-numbers-bg, #2d3748);
                    color: var(--line-numbers-color, #6c757d);
                    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Consolas', monospace;
                    font-size: 0.875rem;
                    line-height: ${lineHeight}rem;
                    padding: 0.75rem 0.5rem;
                    text-align: right;
                    user-select: none;
                    overflow: hidden;
                }

                .code-area {
                    width: 100%;
                    min-height: ${minHeight}rem;
                    max-height: ${maxHeight}rem;
                    padding: 0.75rem 1rem 0.75rem 4rem;
                    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Consolas', monospace;
                    font-size: 0.875rem;
                    line-height: ${lineHeight}rem;
                    color: var(--code-color, #e2e8f0);
                    background: var(--code-bg, #1a202c);
                    border: none;
                    resize: vertical;
                    white-space: pre;
                    overflow-x: auto;
                    tab-size: 4;
                    box-sizing: border-box;
                }

                .code-area:focus {
                    outline: none;
                }

                .code-area::placeholder {
                    color: var(--placeholder-color, #4a5568);
                }

                .footer {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-top: 0.75rem;
                }

                .line-info {
                    font-size: 0.8rem;
                    color: var(--text-muted, #6c757d);
                }

                .actions {
                    display: flex;
                    gap: 0.5rem;
                }

                .action-btn {
                    padding: 0.375rem 0.75rem;
                    background: var(--action-btn-bg, #4a5568);
                    color: var(--action-btn-color, #e2e8f0);
                    border: none;
                    border-radius: 4px;
                    font-size: 0.8rem;
                    cursor: pointer;
                    transition: background 0.15s ease;
                }

                .action-btn:hover {
                    background: var(--action-btn-hover, #5a6778);
                }

                .submit-btn {
                    padding: 0.5rem 1.5rem;
                    background: var(--primary-color, #0d6efd);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 0.95rem;
                    font-weight: 500;
                    cursor: pointer;
                    transition: background 0.15s ease;
                }

                .submit-btn:hover:not(:disabled) {
                    background: var(--primary-hover, #0b5ed7);
                }

                .submit-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .keyboard-hint {
                    font-size: 0.75rem;
                    color: var(--text-muted, #6c757d);
                    margin-top: 0.5rem;
                    text-align: right;
                }

                /* Dark mode - already styled for dark by default */
                @media (prefers-color-scheme: light) {
                    .widget-container {
                        --widget-bg: #f8f9fa;
                        --widget-border: #dee2e6;
                        --text-color: #212529;
                    }

                    /* Keep editor dark even in light mode for better code readability */
                }
            </style>

            <div class="widget-container">
                <div class="prompt" id="prompt">${this.renderMarkdown(this.prompt)}</div>

                <div class="editor-header">
                    <span class="language-badge">
                        ${this.getLanguageIcon()}
                        ${this.escapeHtml(this.language)}
                    </span>
                </div>

                <div class="editor-container">
                    <div class="line-numbers" aria-hidden="true">1</div>
                    <textarea
                        class="code-area"
                        placeholder="Write your ${this.language} code here..."
                        spellcheck="false"
                        aria-labelledby="prompt"
                    >${this.escapeHtml(this.initialCode)}</textarea>
                </div>

                <div class="footer">
                    <span class="line-info">
                        Line <span class="current-line">1</span>, Column <span class="current-col">1</span>
                    </span>
                    <div class="actions">
                        <button class="action-btn clear-btn" title="Clear code">Clear</button>
                        <button class="action-btn reset-btn" title="Reset to initial code">Reset</button>
                        <button class="submit-btn">Run Code</button>
                    </div>
                </div>
                <div class="keyboard-hint">
                    Press Ctrl/Cmd + Enter to submit
                </div>
            </div>
        `;
    }

    setupEventListeners() {
        const codeArea = this.shadowRoot.querySelector('.code-area');
        const lineNumbers = this.shadowRoot.querySelector('.line-numbers');
        const submitBtn = this.shadowRoot.querySelector('.submit-btn');
        const clearBtn = this.shadowRoot.querySelector('.clear-btn');
        const resetBtn = this.shadowRoot.querySelector('.reset-btn');
        const currentLine = this.shadowRoot.querySelector('.current-line');
        const currentCol = this.shadowRoot.querySelector('.current-col');

        if (!codeArea) return;

        // Update line numbers on input
        codeArea.addEventListener('input', () => {
            this.updateLineNumbers(codeArea, lineNumbers);
            this.updateSubmitState(codeArea, submitBtn);
        });

        // Sync scroll between code area and line numbers
        codeArea.addEventListener('scroll', () => {
            lineNumbers.scrollTop = codeArea.scrollTop;
        });

        // Update cursor position
        codeArea.addEventListener('keyup', () => this.updateCursorPosition(codeArea, currentLine, currentCol));
        codeArea.addEventListener('click', () => this.updateCursorPosition(codeArea, currentLine, currentCol));

        // Handle Tab key for indentation
        codeArea.addEventListener('keydown', e => {
            if (e.key === 'Tab') {
                e.preventDefault();
                const start = codeArea.selectionStart;
                const end = codeArea.selectionEnd;
                codeArea.value = codeArea.value.substring(0, start) + '    ' + codeArea.value.substring(end);
                codeArea.selectionStart = codeArea.selectionEnd = start + 4;
                this.updateLineNumbers(codeArea, lineNumbers);
            }

            // Submit on Ctrl/Cmd + Enter
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                if (!submitBtn.disabled) {
                    this.submit();
                }
            }
        });

        // Clear button
        clearBtn.addEventListener('click', () => {
            codeArea.value = '';
            this.updateLineNumbers(codeArea, lineNumbers);
            this.updateSubmitState(codeArea, submitBtn);
            codeArea.focus();
        });

        // Reset button
        resetBtn.addEventListener('click', () => {
            codeArea.value = this.initialCode;
            this.updateLineNumbers(codeArea, lineNumbers);
            this.updateSubmitState(codeArea, submitBtn);
            codeArea.focus();
        });

        // Submit button
        submitBtn.addEventListener('click', () => this.submit());

        // Initial setup
        this.updateLineNumbers(codeArea, lineNumbers);
        this.updateSubmitState(codeArea, submitBtn);

        // Focus the code area
        setTimeout(() => codeArea.focus(), 100);
    }

    updateLineNumbers(codeArea, lineNumbers) {
        const lines = codeArea.value.split('\n').length;
        const lineNums = Array.from({ length: lines }, (_, i) => i + 1).join('\n');
        lineNumbers.textContent = lineNums;
    }

    updateCursorPosition(codeArea, currentLine, currentCol) {
        const pos = codeArea.selectionStart;
        const text = codeArea.value.substring(0, pos);
        const lines = text.split('\n');
        currentLine.textContent = lines.length;
        currentCol.textContent = lines[lines.length - 1].length + 1;
    }

    updateSubmitState(codeArea, submitBtn) {
        submitBtn.disabled = codeArea.value.trim().length === 0;
    }

    submit() {
        const codeArea = this.shadowRoot.querySelector('.code-area');
        const code = codeArea.value;

        if (code.trim().length === 0) {
            return;
        }

        this.dispatchEvent(
            new CustomEvent('ax-response', {
                bubbles: true,
                composed: true,
                detail: {
                    code: code,
                    language: this.language,
                },
            })
        );
    }

    getLanguageIcon() {
        const icons = {
            python: `<svg class="language-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.372 0 5.372 2.93 5.372 2.93v3.044h6.628v1.03H3.906S0 6.63 0 11.97c0 5.34 3.407 5.152 3.407 5.152h2.035v-3.47s-.11-3.408 3.352-3.408h5.768s3.245.052 3.245-3.138V3.246S18.27 0 12 0zM8.727 1.894a1.107 1.107 0 110 2.214 1.107 1.107 0 010-2.214z"/>
                <path d="M12 24c6.628 0 6.628-2.93 6.628-2.93v-3.044h-6.628v-1.03h8.094S24 17.37 24 12.03c0-5.34-3.407-5.152-3.407-5.152h-2.035v3.47s.11 3.408-3.352 3.408H9.438s-3.245-.052-3.245 3.138v3.86S5.73 24 12 24zm3.273-1.894a1.107 1.107 0 110-2.214 1.107 1.107 0 010 2.214z"/>
            </svg>`,
            javascript: `<svg class="language-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M0 0h24v24H0V0zm22.034 18.276c-.175-1.095-.888-2.015-3.003-2.873-.736-.345-1.554-.585-1.797-1.14-.091-.33-.105-.51-.046-.705.15-.646.915-.84 1.515-.66.39.12.75.42.976.9 1.034-.676 1.034-.676 1.755-1.125-.27-.42-.404-.601-.586-.78-.63-.705-1.469-1.065-2.834-1.034l-.705.089c-.676.165-1.32.525-1.71 1.005-1.14 1.291-.811 3.541.569 4.471 1.365 1.02 3.361 1.244 3.616 2.205.24 1.17-.87 1.545-1.966 1.41-.811-.18-1.26-.586-1.755-1.336l-1.83 1.051c.21.48.45.689.81 1.109 1.74 1.756 6.09 1.666 6.871-1.004.029-.09.24-.705.074-1.65l.046.067zm-8.983-7.245h-2.248c0 1.938-.009 3.864-.009 5.805 0 1.232.063 2.363-.138 2.711-.33.689-1.18.601-1.566.48-.396-.196-.597-.466-.83-.855-.063-.105-.11-.196-.127-.196l-1.825 1.125c.305.63.75 1.172 1.324 1.517.855.51 2.004.675 3.207.405.783-.226 1.458-.691 1.811-1.411.51-.93.402-2.07.397-3.346.012-2.054 0-4.109 0-6.179l.004-.056z"/>
            </svg>`,
        };

        return icons[this.language.toLowerCase()] || `<span>📝</span>`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    renderMarkdown(text) {
        if (!text) return '';
        try {
            return marked.parse(text);
        } catch (e) {
            // Fallback to escaped HTML if markdown parsing fails
            return this.escapeHtml(text);
        }
    }
}

customElements.define('ax-code-editor', AxCodeEditor);

export default AxCodeEditor;
