/**
 * Conversation Event Handlers
 *
 * Handles conversation lifecycle events (loaded, updated, created, etc.).
 *
 * @module handlers/conversation-handlers
 */

import { Events, eventBus } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';
import { renderMessages } from '../ui/renderers/message-renderer.js';
import { hideWelcomeMessage } from '../ui/managers/chat-manager.js';
import { addConversationToList, setActiveConversation, renderConversationList } from '../core/conversation-manager.js';
import { api } from '../services/api.js';
import { getDefinition, getDefinitionIcon } from '../domain/definition.js';
import { connect as wsConnect, disconnect as wsDisconnect, isConnected as wsIsConnected, getConversationId as wsGetConversationId } from '../protocol/websocket-client.js';

// =============================================================================
// Handler Functions (Standalone - no context needed)
// =============================================================================

/**
 * Handle conversation loaded - render messages, connect WebSocket, hide welcome
 *
 * When the user selects an existing conversation from the sidebar:
 * 1. Domain layer loads conversation data → emits CONVERSATION_LOADED
 * 2. This handler renders messages from REST response (immediate feedback)
 * 3. Calls POST /connect to get ws_url
 * 4. Connects WebSocket with ws_url
 * 5. Orchestrator on backend will send control.conversation.config etc.
 *
 * @param {Object} payload - Event payload
 * @param {Object} payload.conversation - Loaded conversation
 * @param {string} payload.conversationId - Conversation ID
 * @param {string} [payload.definitionId] - Definition ID
 */
async function handleConversationLoaded({ conversation, conversationId, definitionId }) {
    console.log('[ConversationHandlers] Conversation loaded:', conversationId);

    // 1. Mark conversation as active in sidebar
    setActiveConversation(conversationId);

    // 2. Render messages immediately (optimistic UI from REST data)
    if (conversation.messages) {
        renderMessages(conversation.messages);
    }
    hideWelcomeMessage();

    // 3. Check if already connected to this conversation
    if (wsIsConnected() && wsGetConversationId() === conversationId) {
        console.log('[ConversationHandlers] Already connected to this conversation');
        return;
    }

    // 4. Disconnect existing WebSocket if connected to different conversation
    if (wsIsConnected()) {
        console.log('[ConversationHandlers] Switching conversation, disconnecting...');
        wsDisconnect();
    }

    // 5. Get WebSocket URL from backend (validates ownership, returns ws_url)
    try {
        console.log('[ConversationHandlers] Calling /connect for:', conversationId);
        const connectionData = await api.connectConversation(conversationId);

        // 6. Connect WebSocket with the backend-provided URL
        await wsConnect({
            wsUrl: connectionData.ws_url,
            conversationId: conversationId,
        });

        console.log('[ConversationHandlers] WebSocket connected for conversation:', conversationId);

        // Store definition info for later use
        if (connectionData.definition_id) {
            stateManager.set(StateKeys.CURRENT_DEFINITION_ID, connectionData.definition_id);
        }
    } catch (error) {
        console.error('[ConversationHandlers] Failed to connect to conversation:', error);
        // Don't show error toast - the REST data is already rendered
        // User can still read the conversation, just can't continue it
        eventBus.emit(Events.UI_TOAST, {
            message: 'Could not establish real-time connection',
            type: 'warning',
        });
    }
}

/**
 * Handle conversation list updated - render sidebar
 * @param {Array} conversations - Array of conversation objects from the domain layer
 */
function handleConversationListUpdated(conversations) {
    console.log('[ConversationHandlers] Conversation list updated');
    // Render the conversation list in the sidebar
    renderConversationList(conversations);
}

/**
 * Handle conversation created - add to sidebar list
 * This is emitted after POST /chat/new returns successfully.
 *
 * @param {Object} payload - Event payload
 * @param {string} payload.conversationId - New conversation ID
 * @param {string} payload.definitionId - Definition used
 * @param {string} payload.wsUrl - WebSocket URL
 */
function handleConversationCreated({ conversationId, definitionId, wsUrl }) {
    console.log('[ConversationHandlers] Conversation created:', conversationId);

    // Store the current conversation ID
    stateManager.set(StateKeys.WS_CONVERSATION_ID, conversationId);

    // Get definition info for sidebar display
    const definition = getDefinition(definitionId);
    const definitionIcon = definition ? getDefinitionIcon(definition) : 'bi-robot';
    const definitionName = definition?.name || 'Agent';

    // Create minimal conversation object for sidebar
    // The full data will be loaded when backend projects the event
    const conversation = {
        id: conversationId,
        definition_id: definitionId,
        definition_icon: definitionIcon,
        definition_name: definitionName,
        title: 'New Conversation',
        message_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
    };

    // Add to sidebar (optimistic UI)
    addConversationToList(conversation);

    // Mark as active
    setActiveConversation(conversationId);

    // Hide welcome message since we're starting a conversation
    hideWelcomeMessage();

    console.log('[ConversationHandlers] Added conversation to sidebar:', conversationId);
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
        event: Events.CONVERSATION_LOADED,
        handler: handleConversationLoaded,
        description: 'Render messages and connect WebSocket when conversation loads',
        isFactory: false,
    },
    {
        event: Events.CONVERSATION_LIST_UPDATED,
        handler: handleConversationListUpdated,
        description: 'Handle conversation list refresh',
        isFactory: false,
    },
    {
        event: Events.CONVERSATION_CREATED,
        handler: handleConversationCreated,
        description: 'Add new conversation to sidebar when created via REST',
        isFactory: false,
    },
];

export default handlers;
