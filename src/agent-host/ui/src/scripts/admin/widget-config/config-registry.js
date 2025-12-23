/**
 * Widget Configuration Registry
 *
 * Central registry mapping widget types to their configuration UI classes.
 * Provides factory function for creating config UI instances.
 *
 * Keys match WidgetType enum from Python protocol/enums.py:
 * "message", "multiple_choice", "free_text", "code_editor", "slider",
 * "hotspot", "drag_drop", "dropdown", "iframe", "sticky_note", "image",
 * "video", "graph_topology", "matrix_choice", "document_viewer",
 * "file_upload", "rating", "date_picker", "drawing"
 *
 * @module admin/widget-config/config-registry
 */

// P0 Widgets (Core interaction)
import { MessageConfig } from './message-config.js';
import { MultipleChoiceConfig } from './multiple-choice-config.js';
import { FreeTextConfig } from './free-text-config.js';
import { SliderConfig } from './slider-config.js';

// P1 Widgets (Common functionality)
import { CodeEditorConfig } from './code-editor-config.js';
import { DropdownConfig } from './dropdown-config.js';
import { RatingConfig } from './rating-config.js';
import { DatePickerConfig } from './date-picker-config.js';
import { ImageConfig } from './image-config.js';

// P2 Widgets (Advanced functionality)
import { IframeConfig } from './iframe-config.js';
import { DragDropConfig } from './drag-drop-config.js';
import { HotspotConfig } from './hotspot-config.js';
import { MatrixChoiceConfig } from './matrix-choice-config.js';
import { StickyNoteConfig } from './sticky-note-config.js';
import { VideoConfig } from './video-config.js';
import { GraphTopologyConfig } from './graph-topology-config.js';
import { DocumentViewerConfig } from './document-viewer-config.js';
import { FileUploadConfig } from './file-upload-config.js';
import { DrawingConfig } from './drawing-config.js';

// P3 Widgets (Data visualization)
import { ChartConfig } from './chart-config.js';
import { DataTableConfig } from './data-table-config.js';

// P4 Widgets (Interactive UI elements)
import { ProgressBarConfig } from './progress-bar-config.js';
import { TimerConfig } from './timer-config.js';
import { SubmitButtonConfig } from './submit-button-config.js';

/**
 * Registry mapping widget type strings to their config class constructors.
 * Keys must match WidgetType enum values from Python protocol/enums.py exactly.
 *
 * @type {Object.<string, typeof import('./config-base.js').WidgetConfigBase>}
 */
const CONFIG_REGISTRY = {
    // Display widgets
    message: MessageConfig,
    text_display: MessageConfig, // Similar to message, uses stem for content
    image: ImageConfig,
    image_display: ImageConfig, // Alias for image
    video: VideoConfig,
    chart: ChartConfig,
    data_table: DataTableConfig,
    document_viewer: DocumentViewerConfig,
    sticky_note: StickyNoteConfig,
    graph_topology: GraphTopologyConfig,

    // Input widgets
    multiple_choice: MultipleChoiceConfig,
    checkbox_group: MultipleChoiceConfig, // Similar to multiple_choice
    free_text: FreeTextConfig,
    slider: SliderConfig,
    dropdown: DropdownConfig,
    rating: RatingConfig,
    date_picker: DatePickerConfig,
    file_upload: FileUploadConfig,

    // Advanced widgets
    code_editor: CodeEditorConfig,
    drag_drop: DragDropConfig,
    hotspot: HotspotConfig,
    matrix_choice: MatrixChoiceConfig,
    drawing: DrawingConfig,

    // Embedded widgets
    iframe: IframeConfig,

    // Interactive UI widgets
    progress_bar: ProgressBarConfig,
    timer: TimerConfig,
    submit_button: SubmitButtonConfig,
};

/**
 * List of all supported widget types for dropdown population.
 * Must match WidgetType enum from Python protocol/enums.py.
 *
 * @type {Array<{value: string, label: string, category: string}>}
 */
export const WIDGET_TYPE_OPTIONS = [
    // Display widgets (read-only)
    { value: 'message', label: 'Message', category: 'Display' },
    { value: 'text_display', label: 'Text Display', category: 'Display' },
    { value: 'image_display', label: 'Image', category: 'Display' },
    { value: 'video', label: 'Video', category: 'Display' },
    { value: 'chart', label: 'Chart', category: 'Display' },
    { value: 'data_table', label: 'Data Table', category: 'Display' },
    { value: 'document_viewer', label: 'Document Viewer', category: 'Display' },
    { value: 'sticky_note', label: 'Sticky Note', category: 'Display' },

    // Input widgets (user response)
    { value: 'multiple_choice', label: 'Multiple Choice', category: 'Input' },
    { value: 'checkbox_group', label: 'Checkbox Group', category: 'Input' },
    { value: 'free_text', label: 'Free Text', category: 'Input' },
    { value: 'slider', label: 'Slider', category: 'Input' },
    { value: 'dropdown', label: 'Dropdown', category: 'Input' },
    { value: 'rating', label: 'Rating', category: 'Input' },
    { value: 'date_picker', label: 'Date Picker', category: 'Input' },
    { value: 'file_upload', label: 'File Upload', category: 'Input' },

    // Advanced widgets
    { value: 'code_editor', label: 'Code Editor', category: 'Advanced' },
    { value: 'drag_drop', label: 'Drag & Drop', category: 'Advanced' },
    { value: 'hotspot', label: 'Hotspot', category: 'Advanced' },
    { value: 'matrix_choice', label: 'Matrix Choice', category: 'Advanced' },
    { value: 'drawing', label: 'Drawing', category: 'Advanced' },
    { value: 'graph_topology', label: 'Graph Topology', category: 'Advanced' },

    // Embedded widgets
    { value: 'iframe', label: 'IFrame', category: 'Embedded' },

    // Interactive UI widgets
    { value: 'progress_bar', label: 'Progress Bar', category: 'Interactive' },
    { value: 'timer', label: 'Timer', category: 'Interactive' },
    { value: 'submit_button', label: 'Submit Button', category: 'Interactive' },
];

/**
 * Check if a widget type has a registered configuration UI
 * @param {string} widgetType - Widget type identifier
 * @returns {boolean} True if config UI is available
 */
export function hasConfigUI(widgetType) {
    return widgetType in CONFIG_REGISTRY;
}

/**
 * Get the config class for a widget type
 * @param {string} widgetType - Widget type identifier
 * @returns {typeof import('./config-base.js').WidgetConfigBase|null} Config class or null
 */
export function getConfigClass(widgetType) {
    return CONFIG_REGISTRY[widgetType] || null;
}

/**
 * Create a widget configuration UI instance
 *
 * @param {HTMLElement} container - Container element to render config into
 * @param {string} widgetType - Widget type identifier
 * @param {Object} [initialConfig={}] - Initial configuration values
 * @param {Object} [content={}] - Full content object (for options, correct_answer, etc.)
 * @returns {import('./config-base.js').WidgetConfigBase|null} Config UI instance or null
 */
export function createConfigUI(container, widgetType, initialConfig = {}, content = {}) {
    const ConfigClass = CONFIG_REGISTRY[widgetType];

    if (!ConfigClass) {
        console.warn(`No config UI registered for widget type: ${widgetType}`);
        return null;
    }

    try {
        const instance = new ConfigClass(container, widgetType);
        instance.render(initialConfig, content);
        return instance;
    } catch (error) {
        console.error(`Failed to create config UI for ${widgetType}:`, error);
        return null;
    }
}

/**
 * Generate HTML options for widget type dropdown, grouped by category
 * @param {string} [selectedValue='message'] - Currently selected widget type
 * @returns {string} HTML string with optgroup and option elements
 */
export function generateWidgetTypeOptions(selectedValue = 'message') {
    const categories = {};

    // Group by category
    WIDGET_TYPE_OPTIONS.forEach(opt => {
        if (!categories[opt.category]) {
            categories[opt.category] = [];
        }
        categories[opt.category].push(opt);
    });

    // Generate HTML
    let html = '';
    for (const [category, options] of Object.entries(categories)) {
        html += `<optgroup label="${category}">`;
        options.forEach(opt => {
            const selected = opt.value === selectedValue ? 'selected' : '';
            html += `<option value="${opt.value}" ${selected}>${opt.label}</option>`;
        });
        html += '</optgroup>';
    }

    return html;
}

// Export registry for advanced use cases
export { CONFIG_REGISTRY };
