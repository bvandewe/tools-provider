/**
 * UI Renderers Index
 *
 * Aggregates all UI renderers for convenient import.
 *
 * @module ui/renderers
 */

// Message renderer
export {
    initMessageRenderer,
    clearMessages,
    renderMessages,
    addUserMessage,
    addAssistantMessage,
    addThinkingMessage,
    getThinkingElement,
    appendToContainer,
    scrollMessagesToBottom,
} from './message-renderer.js';

// Widget renderer
export { initWidgetRenderer, showWidget, hideWidget, getCurrentWidget } from './widget-renderer.js';
