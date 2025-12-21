/**
 * Definition Event Handlers
 *
 * Handles agent definition events (list loaded, selected).
 * Implements the two-phase flow: REST conversation creation → WebSocket connection.
 *
 * @module handlers/definition-handlers
 */

import { Events, eventBus } from '../core/event-bus.js';
import { api } from '../services/api.js';
import * as websocketClient from '../protocol/websocket-client.js';
import { stateManager, StateKeys } from '../core/state-manager.js';
import { enableInput } from '../ui/managers/chat-manager.js';
import { setUploadEnabled } from '../components/FileUpload.js';

// =============================================================================
// Constants
// =============================================================================

/**
 * Client capabilities - message types this client can handle.
 * Should match protocol-essentials.md specification.
 * @type {string[]}
 */
export const CLIENT_CAPABILITIES = [
    // System plane
    'system.connection.established',
    'system.connection.close',
    'system.ping',
    'system.pong',
    'system.error',
    // Control plane - conversation
    'control.conversation.config',
    'control.conversation.started',
    'control.conversation.paused',
    'control.conversation.resumed',
    'control.conversation.completed',
    // Control plane - item
    'control.item.context',
    'control.item.score',
    // Control plane - widget
    'control.widget.state',
    'control.widget.render',
    'control.widget.validation',
    // Control plane - flow
    'control.flow.chatInput',
    'control.flow.progress',
    // Data plane - content
    'data.content.chunk',
    'data.content.complete',
    // Data plane - tool
    'data.tool.call',
    'data.tool.result',
    // Data plane - message
    'data.message.ack',
    // Data plane - response
    'data.response.ack',
];

// =============================================================================
// Handler Functions (Factory Pattern)
// =============================================================================

/**
 * Handle definition list loaded - render tiles in welcome screen and populate sidebar agent menu
 * @param {Object} context - ChatApp instance
 * @returns {Function} Handler function
 */
function handleDefinitionListLoaded(context) {
    return definitions => {
        if (context.renderDefinitionTiles) {
            context.renderDefinitionTiles(definitions);
        }
        // Also populate the sidebar agent menu
        if (context.populateSidebarAgentMenu) {
            context.populateSidebarAgentMenu(definitions);
        }
    };
}

/**
 * Handle definition selected - create conversation via REST, then connect WebSocket
 *
 * Implements the two-phase flow:
 * 1. POST /chat/new with definition_id and client_capabilities
 * 2. Backend returns { conversation_id, ws_url, server_capabilities }
 * 3. Client connects WebSocket using ws_url
 * 4. On connect, backend initializes orchestrator and starts proactive flow if applicable
 *
 * @param {Object} context - ChatApp instance
 * @returns {Function} Handler function
 */
function handleDefinitionSelected(context) {
    return async ({ definition, previousId }) => {
        console.log(`[DefinitionHandlers] Definition selected: ${definition.id} (prev: ${previousId})`);

        // Update sidebar agent selector icon
        if (context.updateSidebarAgentSelector) {
            context.updateSidebarAgentSelector(definition);
        }
        if (context.updateDefinitionTileSelection) {
            context.updateDefinitionTileSelection(definition.id);
        }

        // Enable new chat button since an agent is selected
        if (context.elements?.newChatBtn) {
            context.elements.newChatBtn.disabled = false;
        }

        // Enable chat input and upload since an agent is selected
        enableInput('Type your message...');
        setUploadEnabled(true);
        if (context.elements?.sendBtn) {
            context.elements.sendBtn.disabled = false;
        }

        // Two-phase flow: Create conversation first, then connect WebSocket
        try {
            // Phase 1: Create conversation via REST
            console.log(`[DefinitionHandlers] Creating conversation for definition: ${definition.id}`);

            const result = await api.createConversation(definition.id, {
                clientCapabilities: CLIENT_CAPABILITIES,
            });

            console.log(`[DefinitionHandlers] Conversation created:`, {
                conversationId: result.conversation_id,
                wsUrl: result.ws_url,
                serverCapabilities: result.server_capabilities?.length || 0,
            });

            // Store server capabilities for later reference
            if (result.server_capabilities) {
                stateManager.set(StateKeys.SERVER_CAPABILITIES, result.server_capabilities);
            }

            // Emit conversation created event for other handlers
            eventBus.emit(Events.CONVERSATION_CREATED, {
                conversationId: result.conversation_id,
                definitionId: definition.id,
                wsUrl: result.ws_url,
            });

            // Phase 2: Connect WebSocket using the ws_url
            // Note: We pass the full URL since it includes conversation_id and definition_id
            const wsUrl = result.ws_url;

            // Extract just conversation_id for the client state
            const conversationId = result.conversation_id;

            console.log(`[DefinitionHandlers] Connecting WebSocket: ${wsUrl}`);

            await websocketClient.connect({
                conversationId: conversationId,
                definitionId: definition.id,
                wsUrl: wsUrl, // Full URL from backend
            });

            console.log(`[DefinitionHandlers] WebSocket connected for conversation: ${conversationId}`);
        } catch (error) {
            console.error('[DefinitionHandlers] Failed to create conversation or connect WebSocket:', error);

            eventBus.emit(Events.UI_TOAST, {
                message: `Failed to start conversation: ${error.message}`,
                type: 'error',
            });
        }
    };
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
        event: Events.DEFINITION_LIST_LOADED,
        handler: handleDefinitionListLoaded,
        description: 'Render definition tiles when loaded',
    },
    {
        event: Events.DEFINITION_SELECTED,
        handler: handleDefinitionSelected,
        description: 'Create conversation and connect WebSocket when definition is selected',
    },
];

export default handlers;
