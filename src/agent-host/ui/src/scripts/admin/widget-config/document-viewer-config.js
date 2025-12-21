/**
 * Document Viewer Widget Configuration
 *
 * Configuration UI for the 'document_viewer' widget type.
 *
 * Python Schema Reference (DocumentViewerConfig):
 * - content: str | None - inline content
 * - content_url: str | None (alias: contentUrl) - external content URL
 * - content_type: ContentType = "markdown" (alias: contentType) - "markdown" | "html" | "text"
 * - table_of_contents: TableOfContentsConfig | None (alias: tableOfContents)
 * - navigation: NavigationConfig | None
 * - sections: list[DocumentSection] | None
 * - embedded_widgets: list[EmbeddedWidget] | None (alias: embeddedWidgets)
 * - reading_mode: ReadingModeConfig | None (alias: readingMode)
 *
 * TableOfContentsConfig: enabled, position, collapsible, defaultExpanded, maxDepth
 * NavigationConfig: showProgress, showPageNumbers, enableSearch, enableHighlight
 * DocumentSection: sectionId, heading, anchorId, requiredReadTime?, checkpoint?
 * ReadingModeConfig: fontSize, lineHeight, theme
 *
 * @module admin/widget-config/document-viewer-config
 */

import { WidgetConfigBase } from './config-base.js';

/**
 * Content type options
 */
const CONTENT_TYPE_OPTIONS = [
    { value: 'markdown', label: 'Markdown' },
    { value: 'html', label: 'HTML' },
    { value: 'text', label: 'Plain Text' },
];

/**
 * TOC position options
 */
const TOC_POSITION_OPTIONS = [
    { value: 'left', label: 'Left Sidebar' },
    { value: 'right', label: 'Right Sidebar' },
];

/**
 * Font size options
 */
const FONT_SIZE_OPTIONS = [
    { value: '', label: '(Default)' },
    { value: 'small', label: 'Small' },
    { value: 'medium', label: 'Medium' },
    { value: 'large', label: 'Large' },
];

/**
 * Theme options
 */
const THEME_OPTIONS = [
    { value: '', label: '(Default)' },
    { value: 'light', label: 'Light' },
    { value: 'dark', label: 'Dark' },
    { value: 'auto', label: 'Auto (System)' },
];

export class DocumentViewerConfig extends WidgetConfigBase {
    /**
     * Render the document viewer widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        const toc = config.table_of_contents ?? config.tableOfContents ?? {};
        const nav = config.navigation ?? {};
        const readingMode = config.reading_mode ?? config.readingMode ?? {};

        // Convert sections to text format: sectionId|heading|anchorId|readTime|checkpoint
        const sections = config.sections || [];
        const sectionsText = sections
            .map(s => {
                const parts = [s.section_id ?? s.sectionId, s.heading, s.anchor_id ?? s.anchorId];
                if (s.required_read_time ?? s.requiredReadTime) {
                    parts.push(s.required_read_time ?? s.requiredReadTime);
                }
                if (s.checkpoint) {
                    parts.push('checkpoint');
                }
                return parts.join('|');
            })
            .join('\n');

        this.container.innerHTML = `
            <div class="widget-config widget-config-document-viewer">
                <div class="row g-2">
                    <div class="col-md-8">
                        ${this.createFormGroup(
                            'Content URL',
                            this.createTextInput('config-content-url', config.content_url ?? config.contentUrl ?? '', 'https://example.com/document.md'),
                            'URL to external document content.'
                        )}
                    </div>
                    <div class="col-md-4">
                        ${this.createFormGroup(
                            'Content Type',
                            this.createSelect('config-content-type', CONTENT_TYPE_OPTIONS, config.content_type ?? config.contentType ?? 'markdown'),
                            'Format of the document content.'
                        )}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-12">
                        ${this.createFormGroup(
                            'Inline Content',
                            this.createTextarea('config-content', config.content ?? '', '# Document Title\n\nYour content here...', 6),
                            'Direct document content (used if Content URL is empty).'
                        )}
                    </div>
                </div>

                ${this.createCollapsibleSection(
                    `${this.uid}-toc`,
                    'Table of Contents',
                    `
                    <div class="row g-2">
                        <div class="col-md-3">
                            ${this.createSwitch('config-toc-enabled', `${this.uid}-toc-enabled`, 'Enabled', 'Show table of contents.', toc.enabled ?? true)}
                        </div>
                        <div class="col-md-3">
                            ${this.createFormGroup('Position', this.createSelect('config-toc-position', TOC_POSITION_OPTIONS, toc.position ?? 'left'), 'TOC sidebar position.')}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch('config-toc-collapsible', `${this.uid}-toc-collapsible`, 'Collapsible', 'Allow collapsing sections.', toc.collapsible ?? false)}
                        </div>
                        <div class="col-md-3">
                            ${this.createFormGroup('Max Depth', this.createNumberInput('config-toc-depth', toc.max_depth ?? toc.maxDepth ?? '', 1, 6, 1), 'Maximum heading depth to show.')}
                        </div>
                    </div>
                `
                )}

                ${this.createCollapsibleSection(
                    `${this.uid}-nav`,
                    'Navigation',
                    `
                    <div class="row g-2">
                        <div class="col-md-3">
                            ${this.createSwitch('config-show-progress', `${this.uid}-show-progress`, 'Show Progress', 'Display reading progress.', nav.show_progress ?? nav.showProgress ?? false)}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch(
                                'config-show-page-numbers',
                                `${this.uid}-show-page-numbers`,
                                'Page Numbers',
                                'Show page numbers.',
                                nav.show_page_numbers ?? nav.showPageNumbers ?? false
                            )}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch('config-enable-search', `${this.uid}-enable-search`, 'Enable Search', 'Allow searching document.', nav.enable_search ?? nav.enableSearch ?? false)}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch(
                                'config-enable-highlight',
                                `${this.uid}-enable-highlight`,
                                'Enable Highlight',
                                'Allow text highlighting.',
                                nav.enable_highlight ?? nav.enableHighlight ?? false
                            )}
                        </div>
                    </div>
                `
                )}

                ${this.createCollapsibleSection(
                    `${this.uid}-reading`,
                    'Reading Mode',
                    `
                    <div class="row g-2">
                        <div class="col-md-4">
                            ${this.createFormGroup('Font Size', this.createSelect('config-font-size', FONT_SIZE_OPTIONS, readingMode.font_size ?? readingMode.fontSize ?? ''), 'Text size preset.')}
                        </div>
                        <div class="col-md-4">
                            ${this.createFormGroup(
                                'Line Height',
                                this.createNumberInput('config-line-height', readingMode.line_height ?? readingMode.lineHeight ?? '', 1, 3, 0.1),
                                'Line spacing (1.0 - 3.0).'
                            )}
                        </div>
                        <div class="col-md-4">
                            ${this.createFormGroup('Theme', this.createSelect('config-theme', THEME_OPTIONS, readingMode.theme ?? ''), 'Color theme for reading.')}
                        </div>
                    </div>
                `
                )}

                ${this.createCollapsibleSection(
                    `${this.uid}-sections`,
                    'Sections',
                    `
                    ${this.createFormGroup(
                        'Document Sections',
                        this.createTextarea('config-sections', sectionsText, 'intro|Introduction|intro-anchor\nchapter1|Chapter 1|ch1-anchor|60|checkpoint', 4),
                        'One per line: sectionId|heading|anchorId[|readTimeSeconds][|checkpoint]'
                    )}
                `
                )}
            </div>
        `;

        this.initTooltips();
    }

    /**
     * Parse sections from textarea
     * @returns {Array|null} Parsed sections or null
     */
    parseSections() {
        const text = this.getInputValue('config-sections', '');
        if (!text.trim()) return null;

        return text
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map(line => {
                const parts = line.split('|').map(p => p.trim());
                const section = {
                    section_id: parts[0],
                    heading: parts[1] || parts[0],
                    anchor_id: parts[2] || parts[0],
                };
                // Check remaining parts
                for (let i = 3; i < parts.length; i++) {
                    if (parts[i] === 'checkpoint') {
                        section.checkpoint = true;
                    } else {
                        const readTime = parseInt(parts[i], 10);
                        if (!isNaN(readTime)) {
                            section.required_read_time = readTime;
                        }
                    }
                }
                return section;
            });
    }

    /**
     * Get configuration values matching Python schema
     * @returns {Object} Widget configuration
     */
    getValue() {
        const config = {};

        const contentUrl = this.getInputValue('config-content-url');
        if (contentUrl) config.content_url = contentUrl;

        const content = this.getInputValue('config-content');
        if (content) config.content = content;

        config.content_type = this.getInputValue('config-content-type', 'markdown');

        // Build table of contents config
        const toc = {};
        const tocEnabled = this.getChecked('config-toc-enabled');
        toc.enabled = tocEnabled;

        if (tocEnabled) {
            toc.position = this.getInputValue('config-toc-position', 'left');

            const tocCollapsible = this.getChecked('config-toc-collapsible');
            if (tocCollapsible) toc.collapsible = true;

            const tocDepth = this.getInputValue('config-toc-depth');
            if (tocDepth) {
                const parsed = parseInt(tocDepth, 10);
                if (!isNaN(parsed)) toc.max_depth = parsed;
            }
        }

        if (Object.keys(toc).length > 1 || !toc.enabled) {
            config.table_of_contents = toc;
        }

        // Build navigation config
        const nav = {};

        const showProgress = this.getChecked('config-show-progress');
        if (showProgress) nav.show_progress = true;

        const showPageNumbers = this.getChecked('config-show-page-numbers');
        if (showPageNumbers) nav.show_page_numbers = true;

        const enableSearch = this.getChecked('config-enable-search');
        if (enableSearch) nav.enable_search = true;

        const enableHighlight = this.getChecked('config-enable-highlight');
        if (enableHighlight) nav.enable_highlight = true;

        if (Object.keys(nav).length > 0) {
            config.navigation = nav;
        }

        // Build reading mode config
        const readingMode = {};

        const fontSize = this.getInputValue('config-font-size');
        if (fontSize) readingMode.font_size = fontSize;

        const lineHeight = this.getInputValue('config-line-height');
        if (lineHeight) {
            const parsed = parseFloat(lineHeight);
            if (!isNaN(parsed)) readingMode.line_height = parsed;
        }

        const theme = this.getInputValue('config-theme');
        if (theme) readingMode.theme = theme;

        if (Object.keys(readingMode).length > 0) {
            config.reading_mode = readingMode;
        }

        // Parse sections
        const sections = this.parseSections();
        if (sections && sections.length > 0) {
            config.sections = sections;
        }

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const content = this.getInputValue('config-content', '');
        const contentUrl = this.getInputValue('config-content-url', '');

        if (!content && !contentUrl) {
            errors.push('Either content or content URL is required');
        }

        return { valid: errors.length === 0, errors };
    }
}
