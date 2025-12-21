/**
 * Message Event Handlers
 *
 * Handles message-related events (sent, received, complete).
 *
 * @module handlers/message-handlers
 */

import { Events } from '../core/event-bus.js';
import { updateStreamingState } from '../ui/managers/chat-manager.js';
import { setUploadEnabled } from '../components/FileUpload.js';
import { loadConversations } from '../domain/conversation.js';

// =============================================================================
// Handler Functions
// =============================================================================

/**
 * Handle message complete - reset UI state and refresh conversations
 */
function handleMessageComplete() {
    updateStreamingState(false);
    setUploadEnabled(true);
    loadConversations();
}

/**
 * Handle message streaming state
 * @param {Object} payload - Event payload
 * @param {boolean} payload.isStreaming - Streaming state
 */
function handleMessageStreaming({ isStreaming }) {
    updateStreamingState(isStreaming);
    setUploadEnabled(!isStreaming);
}

// =============================================================================
// Handler Registrations
// =============================================================================

/**
 * Exported handlers for registry auto-discovery.
 * @type {import('./index.js').HandlerRegistration[]}
 */
export const handlers = [
    {
        event: Events.MESSAGE_COMPLETE,
        handler: handleMessageComplete,
        description: 'Reset UI state when message completes',
        isFactory: false,
    },
    {
        event: Events.MESSAGE_STREAMING,
        handler: handleMessageStreaming,
        description: 'Update UI during message streaming',
        isFactory: false,
    },
];

export default handlers;
