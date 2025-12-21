/**
 * Widgets Module - Client Action Widget Components
 *
 * Re-exports widget components from their original locations
 * while providing a clean organized API.
 *
 * This follows the gradual migration strategy:
 * 1. New code imports from widgets/
 * 2. Old components/ files remain for backward compatibility
 * 3. Future phase will move files to subdirectories
 *
 * @module widgets
 */

// =============================================================================
// Re-export from components/
// =============================================================================

// Base class and utilities
export { AxWidgetBase, WidgetState } from '../components/ax-widget-base.js';
export { WIDGET_TAGS, WIDGET_TYPE_MAP, createWidget, isWidgetTypeSupported } from '../components/widgets.js';

// Display widgets
export { default as AxTextDisplay } from '../components/ax-text-display.js';
export { default as AxImageDisplay } from '../components/ax-image-display.js';

// Input widgets
export { default as AxMultipleChoice } from '../components/ax-multiple-choice.js';
export { default as AxFreeTextPrompt } from '../components/ax-free-text-prompt.js';
export { default as AxCodeEditor } from '../components/ax-code-editor.js';
export { default as AxSlider } from '../components/ax-slider.js';
export { default as AxCheckboxGroup } from '../components/ax-checkbox-group.js';
export { default as AxDropdown } from '../components/ax-dropdown.js';
export { default as AxRating } from '../components/ax-rating.js';

// Action widgets
export { default as AxSubmitButton } from '../components/ax-submit-button.js';

// Feedback widgets
export { default as AxProgressBar } from '../components/ax-progress-bar.js';
export { default as AxTimer } from '../components/ax-timer.js';

// Embedded content widgets
export { default as AxIframeWidget } from '../components/ax-iframe-widget.js';

// Chat components (not widgets, but used in chat UI)
export { default as ChatMessage } from '../components/ChatMessage.js';
export { default as ToolCallCard } from '../components/ToolCallCard.js';
export { default as FileUpload } from '../components/FileUpload.js';
export { default as AxConversationHeader } from '../components/ax-conversation-header.js';

// =============================================================================
// Category-based imports (for organized access)
// =============================================================================

/**
 * Base widgets and utilities
 */
export const base = {
    AxWidgetBase,
    WidgetState,
};

/**
 * Display widgets
 */
export const display = {
    AxTextDisplay: () => import('../components/ax-text-display.js'),
    AxImageDisplay: () => import('../components/ax-image-display.js'),
};

/**
 * Input widgets
 */
export const input = {
    AxMultipleChoice: () => import('../components/ax-multiple-choice.js'),
    AxFreeTextPrompt: () => import('../components/ax-free-text-prompt.js'),
    AxCodeEditor: () => import('../components/ax-code-editor.js'),
    AxSlider: () => import('../components/ax-slider.js'),
    AxCheckboxGroup: () => import('../components/ax-checkbox-group.js'),
    AxDropdown: () => import('../components/ax-dropdown.js'),
    AxRating: () => import('../components/ax-rating.js'),
};

/**
 * Action widgets
 */
export const action = {
    AxSubmitButton: () => import('../components/ax-submit-button.js'),
};

/**
 * Feedback widgets
 */
export const feedback = {
    AxProgressBar: () => import('../components/ax-progress-bar.js'),
    AxTimer: () => import('../components/ax-timer.js'),
};

/**
 * Embedded widgets
 */
export const embedded = {
    AxIframeWidget: () => import('../components/ax-iframe-widget.js'),
};
