/**
 * Agent Host Widget Components Index
 *
 * This file exports all widget components for easy importing.
 *
 * Usage:
 *   import { AxWidgetBase, AxMultipleChoice, AxTextDisplay } from './components/widgets.js';
 *
 * Or import all widgets:
 *   import './components/widgets.js';
 */

// Base class
export { AxWidgetBase, WidgetState } from './ax-widget-base.js';

// Display widgets
export { default as AxTextDisplay } from './ax-text-display.js';
export { default as AxImageDisplay } from './ax-image-display.js';
export { default as AxChart } from './ax-chart.js';
export { default as AxDataTable } from './ax-data-table.js';

// Input widgets
export { default as AxMultipleChoice } from './ax-multiple-choice.js';
export { default as AxFreeTextPrompt } from './ax-free-text-prompt.js';
export { default as AxCodeEditor } from './ax-code-editor.js';
export { default as AxSlider } from './ax-slider.js';
export { default as AxCheckboxGroup } from './ax-checkbox-group.js';
export { default as AxDropdown } from './ax-dropdown.js';
export { default as AxRating } from './ax-rating.js';
export { default as AxDatePicker } from './ax-date-picker.js';
export { default as AxMatrixChoice } from './ax-matrix-choice.js';

// Interactive widgets
export { default as AxDragDrop } from './ax-drag-drop.js';
export { default as AxHotspot } from './ax-hotspot.js';
export { default as AxDrawing } from './ax-drawing.js';

// Action widgets
export { default as AxSubmitButton } from './ax-submit-button.js';

// Feedback widgets
export { default as AxProgressBar } from './ax-progress-bar.js';
export { default as AxTimer } from './ax-timer.js';

// Embedded content widgets
export { default as AxIframeWidget } from './ax-iframe-widget.js';

// Re-export for convenience
export const WIDGET_TAGS = {
    // Display
    TEXT_DISPLAY: 'ax-text-display',
    IMAGE_DISPLAY: 'ax-image-display',
    CHART: 'ax-chart',
    DATA_TABLE: 'ax-data-table',

    // Input
    MULTIPLE_CHOICE: 'ax-multiple-choice',
    FREE_TEXT: 'ax-free-text-prompt',
    CODE_EDITOR: 'ax-code-editor',
    SLIDER: 'ax-slider',
    CHECKBOX_GROUP: 'ax-checkbox-group',
    DROPDOWN: 'ax-dropdown',
    RATING: 'ax-rating',
    DATE_PICKER: 'ax-date-picker',
    MATRIX_CHOICE: 'ax-matrix-choice',

    // Interactive
    DRAG_DROP: 'ax-drag-drop',
    HOTSPOT: 'ax-hotspot',
    DRAWING: 'ax-drawing',

    // Action
    SUBMIT_BUTTON: 'ax-submit-button',

    // Feedback
    PROGRESS_BAR: 'ax-progress-bar',
    TIMER: 'ax-timer',

    // Embedded
    IFRAME: 'ax-iframe-widget',
};

/**
 * Widget type to tag mapping (matches protocol WidgetType enum)
 */
export const WIDGET_TYPE_MAP = {
    text_display: 'ax-text-display',
    image_display: 'ax-image-display',
    chart: 'ax-chart',
    data_table: 'ax-data-table',
    multiple_choice: 'ax-multiple-choice',
    free_text: 'ax-free-text-prompt',
    code_editor: 'ax-code-editor',
    slider: 'ax-slider',
    checkbox_group: 'ax-checkbox-group',
    dropdown: 'ax-dropdown',
    rating: 'ax-rating',
    date_picker: 'ax-date-picker',
    matrix_choice: 'ax-matrix-choice',
    drag_drop: 'ax-drag-drop',
    hotspot: 'ax-hotspot',
    drawing: 'ax-drawing',
    submit_button: 'ax-submit-button',
    progress_bar: 'ax-progress-bar',
    timer: 'ax-timer',
    iframe: 'ax-iframe-widget',
};

/**
 * Create a widget element from protocol widget type
 * @param {string} widgetType - Protocol widget type (e.g., "multiple_choice")
 * @returns {HTMLElement|null} Widget element or null if type unknown
 */
export function createWidget(widgetType) {
    const tag = WIDGET_TYPE_MAP[widgetType];
    if (!tag) {
        console.warn(`Unknown widget type: ${widgetType}`);
        return null;
    }
    return document.createElement(tag);
}

/**
 * Check if a widget type is supported
 * @param {string} widgetType - Protocol widget type
 * @returns {boolean}
 */
export function isWidgetTypeSupported(widgetType) {
    return widgetType in WIDGET_TYPE_MAP;
}
