/**
 * Code Editor Widget Component
 * Renders a code editor with syntax highlighting using CodeMirror 6
 *
 * Attributes:
 * - prompt: The question or prompt to display
 * - language: Programming language for syntax hints (python, json, xml, yaml)
 * - initial-code: Pre-populated code in the editor
 * - min-lines: Minimum number of lines for the editor
 * - max-lines: Maximum number of lines for the editor
 *
 * Events:
 * - ax-response: Fired when user submits their code
 *   Detail: { code: string, language: string }
 * - ax-selection: Fired on every change for confirmation mode support
 *   Detail: { code: string, language: string }
 */
import { marked } from 'marked';

// CodeMirror 6 imports
import { EditorView, basicSetup } from 'codemirror';
import { EditorState, Compartment } from '@codemirror/state';
import { keymap } from '@codemirror/view';
import { indentWithTab } from '@codemirror/commands';
import { indentUnit } from '@codemirror/language';
import { oneDark } from '@codemirror/theme-one-dark';

// Language imports
import { python } from '@codemirror/lang-python';
import { json } from '@codemirror/lang-json';
import { xml } from '@codemirror/lang-xml';
import { yaml } from '@codemirror/lang-yaml';

// Configure marked for safe HTML rendering
marked.setOptions({
    breaks: true,
    gfm: true,
});

/**
 * Light theme for CodeMirror (matches Bootstrap light theme)
 */
const lightTheme = EditorView.theme({
    '&': {
        backgroundColor: '#ffffff',
        color: '#24292e',
    },
    '.cm-content': {
        caretColor: '#24292e',
    },
    '.cm-cursor, .cm-dropCursor': {
        borderLeftColor: '#24292e',
    },
    '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': {
        backgroundColor: '#add6ff',
    },
    '.cm-gutters': {
        backgroundColor: '#f6f8fa',
        color: '#6e7781',
        borderRight: '1px solid #d0d7de',
    },
    '.cm-activeLineGutter': {
        backgroundColor: '#eaeef2',
    },
    '.cm-activeLine': {
        backgroundColor: '#f6f8fa',
    },
});

class AxCodeEditor extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this._editorView = null;
        this._languageCompartment = new Compartment();
        this._themeCompartment = new Compartment();
    }

    static get observedAttributes() {
        return ['prompt', 'language', 'initial-code', 'min-lines', 'max-lines'];
    }

    connectedCallback() {
        this.render();
        this._initCodeMirror();
    }

    disconnectedCallback() {
        // Clean up CodeMirror instance
        if (this._editorView) {
            this._editorView.destroy();
            this._editorView = null;
        }
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (oldValue !== newValue && this._editorView) {
            if (name === 'language') {
                // Update language without re-rendering
                this._updateLanguage();
            } else if (name === 'initial-code') {
                // Update content
                this._setContent(newValue || '');
            } else if (name === 'prompt') {
                // Update prompt text
                const promptEl = this.shadowRoot.querySelector('.prompt');
                if (promptEl) {
                    promptEl.innerHTML = this.renderMarkdown(this.prompt);
                }
            }
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

    /**
     * Check if dark theme is active
     */
    _isDarkTheme() {
        const bsTheme = document.documentElement.getAttribute('data-bs-theme');
        if (bsTheme) {
            return bsTheme === 'dark';
        }
        if (document.documentElement.classList.contains('dark-theme') || document.body.classList.contains('dark-theme')) {
            return true;
        }
        return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    /**
     * Get CodeMirror language extension for the current language
     */
    _getLanguageExtension() {
        const lang = this.language.toLowerCase();
        switch (lang) {
            case 'python':
            case 'py':
                return python();
            case 'json':
                return json();
            case 'xml':
            case 'html':
                return xml();
            case 'yaml':
            case 'yml':
                return yaml();
            default:
                // Return empty extension for unsupported languages
                return [];
        }
    }

    /**
     * Get CodeMirror theme extension
     */
    _getThemeExtension() {
        return this._isDarkTheme() ? oneDark : lightTheme;
    }

    /**
     * Initialize CodeMirror editor
     */
    _initCodeMirror() {
        const editorContainer = this.shadowRoot.querySelector('.codemirror-container');
        if (!editorContainer || this._editorView) return;

        const lineHeight = 1.5;
        const minHeight = this.minLines * lineHeight * 16; // Convert rem to px
        const maxHeight = this.maxLines * lineHeight * 16;

        // Create update listener
        const updateListener = EditorView.updateListener.of(update => {
            if (update.docChanged) {
                this._onDocChange();
            }
            if (update.selectionSet) {
                this._updateCursorPosition();
            }
        });

        // Create Ctrl/Cmd+Enter keybinding
        const submitKeymap = keymap.of([
            {
                key: 'Mod-Enter',
                run: () => {
                    this.submit();
                    return true;
                },
            },
        ]);

        // Create editor state
        const state = EditorState.create({
            doc: this.initialCode,
            extensions: [
                basicSetup,
                keymap.of([indentWithTab]),
                indentUnit.of('    '),
                submitKeymap,
                this._languageCompartment.of(this._getLanguageExtension()),
                this._themeCompartment.of(this._getThemeExtension()),
                updateListener,
                EditorView.lineWrapping,
                EditorView.theme({
                    '&': {
                        minHeight: `${minHeight}px`,
                        maxHeight: `${maxHeight}px`,
                        fontSize: '14px',
                    },
                    '.cm-scroller': {
                        overflow: 'auto',
                        fontFamily: "'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Consolas', monospace",
                    },
                    '.cm-content': {
                        minHeight: `${minHeight}px`,
                    },
                }),
            ],
        });

        // Create editor view
        this._editorView = new EditorView({
            state,
            parent: editorContainer,
        });

        // Update submit button state
        this._updateSubmitState();

        // Focus editor
        setTimeout(() => this._editorView?.focus(), 100);
    }

    /**
     * Update language extension
     */
    _updateLanguage() {
        if (!this._editorView) return;
        this._editorView.dispatch({
            effects: this._languageCompartment.reconfigure(this._getLanguageExtension()),
        });

        // Update language badge
        const badge = this.shadowRoot.querySelector('.language-badge');
        if (badge) {
            badge.innerHTML = `${this.getLanguageIcon()} ${this.escapeHtml(this.language)}`;
        }
    }

    /**
     * Update theme
     */
    _updateTheme() {
        if (!this._editorView) return;
        this._editorView.dispatch({
            effects: this._themeCompartment.reconfigure(this._getThemeExtension()),
        });
    }

    /**
     * Set editor content
     */
    _setContent(content) {
        if (!this._editorView) return;
        this._editorView.dispatch({
            changes: {
                from: 0,
                to: this._editorView.state.doc.length,
                insert: content,
            },
        });
    }

    /**
     * Get editor content
     */
    _getContent() {
        if (!this._editorView) return '';
        return this._editorView.state.doc.toString();
    }

    /**
     * Handle document changes
     */
    _onDocChange() {
        this._updateSubmitState();
        this.clearError(); // Clear validation error on interaction

        const code = this._getContent();
        if (code.trim().length > 0) {
            this.dispatchEvent(
                new CustomEvent('ax-selection', {
                    bubbles: true,
                    composed: true,
                    detail: {
                        code: code,
                        language: this.language,
                    },
                })
            );
        }
    }

    /**
     * Update cursor position display
     */
    _updateCursorPosition() {
        if (!this._editorView) return;

        const pos = this._editorView.state.selection.main.head;
        const line = this._editorView.state.doc.lineAt(pos);

        const currentLine = this.shadowRoot.querySelector('.current-line');
        const currentCol = this.shadowRoot.querySelector('.current-col');

        if (currentLine) currentLine.textContent = line.number;
        if (currentCol) currentCol.textContent = pos - line.from + 1;
    }

    /**
     * Update submit button state
     */
    _updateSubmitState() {
        const submitBtn = this.shadowRoot.querySelector('.submit-btn');
        if (submitBtn) {
            submitBtn.disabled = this._getContent().trim().length === 0;
        }
    }

    render() {
        const isDark = this._isDarkTheme();

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    font-family: var(--font-family, system-ui, -apple-system, sans-serif);

                    /* Theme-aware variables */
                    --widget-bg: ${isDark ? '#21262d' : '#f8f9fa'};
                    --widget-border: ${isDark ? '#30363d' : '#dee2e6'};
                    --text-color: ${isDark ? '#e2e8f0' : '#212529'};
                    --text-muted: ${isDark ? '#8b949e' : '#6c757d'};
                }

                .widget-container {
                    background: var(--widget-bg);
                    border: 1px solid var(--widget-border);
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
                .prompt p { margin: 0 0 0.5rem 0; }
                .prompt p:last-child { margin-bottom: 0; }
                .prompt code {
                    font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
                    font-size: 0.9em;
                    background: ${isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)'};
                    padding: 2px 6px;
                    border-radius: 4px;
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
                    background: ${isDark ? '#30363d' : '#e9ecef'};
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

                .codemirror-container {
                    border: 2px solid ${isDark ? '#3c3c3c' : '#d0d7de'};
                    border-radius: 8px;
                    overflow: hidden;
                }

                /* CodeMirror overrides */
                .codemirror-container .cm-editor {
                    font-size: 14px;
                }

                .codemirror-container .cm-editor.cm-focused {
                    outline: none;
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
                    background: ${isDark ? '#4a5568' : '#e9ecef'};
                    color: ${isDark ? '#e2e8f0' : '#495057'};
                    border: none;
                    border-radius: 4px;
                    font-size: 0.8rem;
                    cursor: pointer;
                    transition: background 0.15s ease;
                }

                .action-btn:hover {
                    background: ${isDark ? '#5a6778' : '#dee2e6'};
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
                    color: var(--text-muted);
                    margin-top: 0.5rem;
                    text-align: right;
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

                <div class="codemirror-container"></div>

                <div class="footer">
                    <span class="line-info">
                        Line <span class="current-line">1</span>, Column <span class="current-col">1</span>
                    </span>
                    <div class="actions">
                        <button class="action-btn clear-btn" title="Clear code">Clear</button>
                        <button class="action-btn reset-btn" title="Reset to initial code">Reset</button>
                        <button class="submit-btn" disabled>Run Code</button>
                    </div>
                </div>
                <div class="keyboard-hint">
                    Press Ctrl/Cmd + Enter to submit
                </div>
            </div>
        `;

        this._setupButtonListeners();
    }

    /**
     * Setup button event listeners
     */
    _setupButtonListeners() {
        const clearBtn = this.shadowRoot.querySelector('.clear-btn');
        const resetBtn = this.shadowRoot.querySelector('.reset-btn');
        const submitBtn = this.shadowRoot.querySelector('.submit-btn');

        clearBtn?.addEventListener('click', () => {
            this._setContent('');
            this._editorView?.focus();
        });

        resetBtn?.addEventListener('click', () => {
            this._setContent(this.initialCode);
            this._editorView?.focus();
        });

        submitBtn?.addEventListener('click', () => this.submit());
    }

    submit() {
        const code = this._getContent();

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
            json: `<svg class="language-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M5.759 3.975h1.783V5.76H5.759v4.458A1.783 1.783 0 013.975 12a1.783 1.783 0 011.784 1.783v4.459h1.783v1.783H5.759c-.954-.24-1.784-.803-1.784-1.783v-3.567a1.783 1.783 0 00-1.783-1.783H1.3v-1.783h.892a1.783 1.783 0 001.783-1.784V5.758c0-.98.83-1.543 1.784-1.783zm12.482 0c.954.24 1.784.803 1.784 1.783v3.567a1.783 1.783 0 001.783 1.784h.892v1.783h-.892a1.783 1.783 0 00-1.783 1.783v3.567c0 .98-.83 1.543-1.784 1.783h-1.783V18.24h1.783v-4.459A1.783 1.783 0 0120.025 12a1.783 1.783 0 01-1.784-1.783V5.76h-1.783V3.975h1.783z"/>
            </svg>`,
            xml: `<svg class="language-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12.89 3l1.96.4L11.11 21l-1.96-.4L12.89 3zm-7.3 4.48L8.6 10.5l-3 3-1.02 1.02L7.6 17.52l1.41-1.41-3-3 3-3L7.6 8.69l-1.01-.21zM19.6 10.5l-3-3-1.41 1.41 3 3-3 3 1.41 1.42 4.02-4.02-.01-.01-1.01-.8z"/>
            </svg>`,
            yaml: `<svg class="language-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 3h18v18H3V3zm16.5 16.5v-15h-15v15h15zM7.5 8.25h2.25L12 11.5l2.25-3.25h2.25L13.5 12.5V16h-3v-3.5L7.5 8.25z"/>
            </svg>`,
        };

        const lang = this.language.toLowerCase();
        return icons[lang] || icons['json'] || `<span>📝</span>`;
    }

    /**
     * Refresh theme - called by ThemeService when theme changes
     * Updates CodeMirror theme without full re-render
     */
    refreshTheme() {
        // Update wrapper styles
        const container = this.shadowRoot.querySelector('.widget-container');
        const isDark = this._isDarkTheme();

        if (container) {
            container.style.setProperty('--widget-bg', isDark ? '#21262d' : '#f8f9fa');
            container.style.setProperty('--widget-border', isDark ? '#30363d' : '#dee2e6');
            container.style.setProperty('--text-color', isDark ? '#e2e8f0' : '#212529');
            container.style.setProperty('--text-muted', isDark ? '#8b949e' : '#6c757d');
        }

        // Update CodeMirror theme
        this._updateTheme();
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
            return this.escapeHtml(text);
        }
    }

    /**
     * Public API: Get current code value
     */
    getValue() {
        return {
            code: this._getContent(),
            language: this.language,
        };
    }

    /**
     * Public API: Set code value
     */
    setValue(value) {
        if (typeof value === 'string') {
            this._setContent(value);
        } else if (value && typeof value === 'object' && value.code) {
            this._setContent(value.code);
        }
    }

    /**
     * Public API: Focus the editor
     */
    focus() {
        this._editorView?.focus();
    }
}

customElements.define('ax-code-editor', AxCodeEditor);

export default AxCodeEditor;
