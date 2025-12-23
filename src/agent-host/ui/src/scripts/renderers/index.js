/**
 * Renderers Module - Pure DOM Rendering Layer
 *
 * Provides class-based renderers for DOM manipulation.
 * Renderers listen to UI rendering events and update the DOM.
 * All renderers are singleton instances.
 *
 * @module renderers
 */

// Definition Renderer
export { DefinitionRenderer, definitionRenderer } from './DefinitionRenderer.js';

// Message Renderer
export { MessageRenderer, messageRenderer } from './MessageRenderer.js';

// Widget Renderer
export { WidgetRenderer, widgetRenderer } from './WidgetRenderer.js';
