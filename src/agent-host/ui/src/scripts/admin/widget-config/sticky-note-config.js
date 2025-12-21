/**
 * Sticky Note Widget Configuration
 *
 * Configuration UI for the 'sticky_note' widget type.
 *
 * Python Schema Reference (StickyNoteConfig):
 * - content: str (required)
 * - editable: bool | None
 * - max_length: int | None (alias: maxLength)
 * - placeholder: str | None
 * - style: StickyNoteStyle | None
 * - show_timestamp: bool | None (alias: showTimestamp)
 * - show_author: bool | None (alias: showAuthor)
 * - author: str | None
 * - created_at: str | None (alias: createdAt)
 * - pinned: bool | None
 * - minimizable: bool | None
 * - minimized: bool | None
 *
 * StickyNoteStyle:
 * - background_color: str | None (alias: backgroundColor)
 * - text_color: str | None (alias: textColor)
 * - font_size: int | None (alias: fontSize)
 * - font_family: str | None (alias: fontFamily)
 * - shadow: bool | None
 * - rotation: int | None (degrees)
 *
 * @module admin/widget-config/sticky-note-config
 */

import { WidgetConfigBase } from './config-base.js';

/**
 * Predefined color options for sticky notes
 */
const COLOR_OPTIONS = [
    { value: '', label: '(Default)' },
    { value: '#fffacd', label: 'Yellow' },
    { value: '#ffb6c1', label: 'Pink' },
    { value: '#98fb98', label: 'Green' },
    { value: '#87ceeb', label: 'Blue' },
    { value: '#dda0dd', label: 'Purple' },
    { value: '#ffa07a', label: 'Orange' },
];

/**
 * Font family options
 */
const FONT_OPTIONS = [
    { value: '', label: '(Default)' },
    { value: 'Arial, sans-serif', label: 'Arial' },
    { value: 'Georgia, serif', label: 'Georgia' },
    { value: 'Courier New, monospace', label: 'Courier New' },
    { value: 'Comic Sans MS, cursive', label: 'Comic Sans' },
    { value: 'Handlee, cursive', label: 'Handlee (handwritten)' },
];

export class StickyNoteConfig extends WidgetConfigBase {
    /**
     * Render the sticky note widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        const style = config.style || {};

        this.container.innerHTML = `
            <div class="widget-config widget-config-sticky-note">
                <div class="row g-2">
                    <div class="col-12">
                        ${this.createFormGroup(
                            'Content',
                            this.createTextarea('config-content', config.content ?? '', 'Enter the sticky note text...', 3),
                            'The text content of the sticky note.',
                            true
                        )}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-4">
                        ${this.createFormGroup('Placeholder', this.createTextInput('config-placeholder', config.placeholder ?? '', 'Enter a note...'), 'Placeholder text when editable and empty.')}
                    </div>
                    <div class="col-md-4">
                        ${this.createFormGroup(
                            'Max Length',
                            this.createNumberInput('config-max-length', config.max_length ?? config.maxLength ?? '', 0, 10000, 50),
                            'Maximum number of characters (if editable).'
                        )}
                    </div>
                    <div class="col-md-4">
                        ${this.createFormGroup('Author', this.createTextInput('config-author', config.author ?? '', 'Author name'), 'Display author name on the note.')}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-2">
                        ${this.createSwitch('config-editable', `${this.uid}-editable`, 'Editable', 'Allow users to edit the note.', config.editable ?? false)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-pinned', `${this.uid}-pinned`, 'Pinned', 'Note is pinned (cannot be moved).', config.pinned ?? false)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-minimizable', `${this.uid}-minimizable`, 'Minimizable', 'Allow note to be minimized.', config.minimizable ?? false)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-minimized', `${this.uid}-minimized`, 'Start Minimized', 'Note starts in minimized state.', config.minimized ?? false)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-show-timestamp', `${this.uid}-show-timestamp`, 'Show Time', 'Display creation timestamp.', config.show_timestamp ?? config.showTimestamp ?? false)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-show-author', `${this.uid}-show-author`, 'Show Author', 'Display author name.', config.show_author ?? config.showAuthor ?? false)}
                    </div>
                </div>

                ${this.createCollapsibleSection(
                    `${this.uid}-style`,
                    'Style Options',
                    `
                    <div class="row g-2">
                        <div class="col-md-4">
                            ${this.createFormGroup(
                                'Background Color',
                                this.createSelect('config-bg-color', COLOR_OPTIONS, style.background_color ?? style.backgroundColor ?? ''),
                                'Background color of the note.'
                            )}
                        </div>
                        <div class="col-md-4">
                            ${this.createFormGroup('Text Color', this.createTextInput('config-text-color', style.text_color ?? style.textColor ?? '', '#333333'), 'Text color (hex, e.g., #333333).')}
                        </div>
                        <div class="col-md-4">
                            ${this.createFormGroup('Font Family', this.createSelect('config-font-family', FONT_OPTIONS, style.font_family ?? style.fontFamily ?? ''), 'Font family for the note text.')}
                        </div>
                    </div>
                    <div class="row g-2 mt-2">
                        <div class="col-md-4">
                            ${this.createFormGroup('Font Size', this.createNumberInput('config-font-size', style.font_size ?? style.fontSize ?? '', 8, 48, 1), 'Font size in pixels.')}
                        </div>
                        <div class="col-md-4">
                            ${this.createFormGroup('Rotation', this.createNumberInput('config-rotation', style.rotation ?? '', -15, 15, 1), 'Rotation angle in degrees (-15 to 15).')}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch('config-shadow', `${this.uid}-shadow`, 'Drop Shadow', 'Add a drop shadow effect.', style.shadow ?? false)}
                        </div>
                    </div>
                `
                )}
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

        config.content = this.getInputValue('config-content', '');

        const placeholder = this.getInputValue('config-placeholder');
        if (placeholder) config.placeholder = placeholder;

        const maxLength = this.getInputValue('config-max-length');
        if (maxLength) {
            const parsed = parseInt(maxLength, 10);
            if (!isNaN(parsed) && parsed > 0) config.max_length = parsed;
        }

        const author = this.getInputValue('config-author');
        if (author) config.author = author;

        const editable = this.getChecked('config-editable');
        if (editable) config.editable = true;

        const pinned = this.getChecked('config-pinned');
        if (pinned) config.pinned = true;

        const minimizable = this.getChecked('config-minimizable');
        if (minimizable) config.minimizable = true;

        const minimized = this.getChecked('config-minimized');
        if (minimized) config.minimized = true;

        const showTimestamp = this.getChecked('config-show-timestamp');
        if (showTimestamp) config.show_timestamp = true;

        const showAuthor = this.getChecked('config-show-author');
        if (showAuthor) config.show_author = true;

        // Build style object
        const style = {};

        const bgColor = this.getInputValue('config-bg-color');
        if (bgColor) style.background_color = bgColor;

        const textColor = this.getInputValue('config-text-color');
        if (textColor) style.text_color = textColor;

        const fontFamily = this.getInputValue('config-font-family');
        if (fontFamily) style.font_family = fontFamily;

        const fontSize = this.getInputValue('config-font-size');
        if (fontSize) {
            const parsed = parseInt(fontSize, 10);
            if (!isNaN(parsed)) style.font_size = parsed;
        }

        const rotation = this.getInputValue('config-rotation');
        if (rotation) {
            const parsed = parseInt(rotation, 10);
            if (!isNaN(parsed)) style.rotation = parsed;
        }

        const shadow = this.getChecked('config-shadow');
        if (shadow) style.shadow = true;

        if (Object.keys(style).length > 0) {
            config.style = style;
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
        const editable = this.getChecked('config-editable');

        // Content is required unless editable with placeholder
        if (!content && !editable) {
            errors.push('Content is required for non-editable sticky notes');
        }

        // Validate text color format if provided
        const textColor = this.getInputValue('config-text-color');
        if (textColor && !textColor.match(/^#[0-9A-Fa-f]{6}$/)) {
            errors.push('Text color must be a valid hex color (e.g., #333333)');
        }

        return { valid: errors.length === 0, errors };
    }

    /**
     * Get initial content value
     * @returns {string} Initial content
     */
    getInitialValue() {
        return this.getInputValue('config-content', '');
    }
}
