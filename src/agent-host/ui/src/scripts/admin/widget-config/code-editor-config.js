/**
 * Code Editor Widget Configuration
 *
 * Configuration UI for the 'code_editor' widget type.
 *
 * Python Schema Reference (CodeEditorConfig):
 * - language: str (required)
 * - initial_code: str | None (alias: initialCode)
 * - min_lines: int | None (alias: minLines)
 * - max_lines: int | None (alias: maxLines)
 * - read_only: bool | None (alias: readOnly)
 * - show_line_numbers: bool | None (alias: showLineNumbers)
 *
 * @module admin/widget-config/code-editor-config
 */

import { WidgetConfigBase } from './config-base.js';

/**
 * Common programming languages for the dropdown
 */
const LANGUAGE_OPTIONS = [
    { value: 'python', label: 'Python' },
    { value: 'javascript', label: 'JavaScript' },
    { value: 'typescript', label: 'TypeScript' },
    { value: 'java', label: 'Java' },
    { value: 'csharp', label: 'C#' },
    { value: 'cpp', label: 'C++' },
    { value: 'c', label: 'C' },
    { value: 'go', label: 'Go' },
    { value: 'rust', label: 'Rust' },
    { value: 'ruby', label: 'Ruby' },
    { value: 'php', label: 'PHP' },
    { value: 'swift', label: 'Swift' },
    { value: 'kotlin', label: 'Kotlin' },
    { value: 'sql', label: 'SQL' },
    { value: 'html', label: 'HTML' },
    { value: 'css', label: 'CSS' },
    { value: 'json', label: 'JSON' },
    { value: 'yaml', label: 'YAML' },
    { value: 'xml', label: 'XML' },
    { value: 'markdown', label: 'Markdown' },
    { value: 'bash', label: 'Bash/Shell' },
    { value: 'plaintext', label: 'Plain Text' },
];

export class CodeEditorConfig extends WidgetConfigBase {
    /**
     * Render the code editor widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        const language = config.language || 'python';
        const initialCode = config.initial_code ?? config.initialCode ?? '';

        this.container.innerHTML = `
            <div class="widget-config widget-config-code-editor">
                <div class="row g-2">
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Language
                            <span class="text-danger">*</span>
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Programming language for syntax highlighting."></i>
                        </label>
                        ${this.createSelect('config-language', LANGUAGE_OPTIONS, language)}
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Min Lines
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Minimum editor height in lines."></i>
                        </label>
                        ${this.createNumberInput('config-min-lines', config.min_lines ?? config.minLines ?? '', '5', { min: 1, max: 100 })}
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Max Lines
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Maximum editor height in lines. Leave empty for auto-expand."></i>
                        </label>
                        ${this.createNumberInput('config-max-lines', config.max_lines ?? config.maxLines ?? '', '20', { min: 1, max: 500 })}
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-md-6">
                        ${this.createSwitch(
                            'config-show-line-numbers',
                            `${this.uid}-show-line-numbers`,
                            'Show Line Numbers',
                            'Display line numbers in the gutter.',
                            config.show_line_numbers ?? config.showLineNumbers ?? true
                        )}
                    </div>
                    <div class="col-md-6">
                        ${this.createSwitch(
                            'config-read-only',
                            `${this.uid}-read-only`,
                            'Read Only',
                            'Prevent users from editing the code (view only mode).',
                            config.read_only ?? config.readOnly ?? false
                        )}
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-12">
                        <label class="form-label small mb-0">
                            Initial Code
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Pre-populated code when the editor loads. Can include starter code or template."></i>
                        </label>
                        ${this.createTextarea('config-initial-code', initialCode, '# Enter starter code here...', 6)}
                    </div>
                </div>
            </div>
        `;

        this.initTooltips();
    }

    /**
     * Get configuration values matching Python schema
     * @returns {Object} Widget configuration
     */
    getValue() {
        const config = {};

        // Language is required
        const language = this.getInputValue('config-language', 'python');
        config.language = language;

        const initialCode = this.getInputValue('config-initial-code');
        if (initialCode) {
            config.initial_code = initialCode;
        }

        const minLines = this.getIntValue('config-min-lines');
        if (minLines !== null) {
            config.min_lines = minLines;
        }

        const maxLines = this.getIntValue('config-max-lines');
        if (maxLines !== null) {
            config.max_lines = maxLines;
        }

        const readOnly = this.getChecked('config-read-only');
        if (readOnly) {
            config.read_only = true;
        }

        const showLineNumbers = this.getChecked('config-show-line-numbers');
        if (!showLineNumbers) {
            config.show_line_numbers = false;
        }

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const language = this.getInputValue('config-language');
        if (!language) {
            errors.push('Language is required');
        }

        const minLines = this.getIntValue('config-min-lines');
        const maxLines = this.getIntValue('config-max-lines');

        if (minLines !== null && maxLines !== null && minLines > maxLines) {
            errors.push('Min lines cannot be greater than max lines');
        }

        if (minLines !== null && minLines < 1) {
            errors.push('Min lines must be at least 1');
        }

        return { valid: errors.length === 0, errors };
    }
}
