/**
 * DefinitionHandlers - Definition Event Handler Class
 *
 * Handles agent definition events (list loaded, selected).
 * Implements the two-phase flow: REST conversation creation → WebSocket connection.
 *
 * Uses dependency injection via imported singletons instead of factory pattern.
 *
 * @module handlers/DefinitionHandlers
 */

import { Events, eventBus } from '../core/event-bus.js';
import { api } from '../services/api.js';
import * as websocketClient from '../protocol/websocket-client.js';
import { stateManager, StateKeys } from '../core/state-manager.js';

// Import managers (DI via singletons)
import { chatManager } from '../managers/ChatManager.js';
import { sidebarManager } from '../managers/SidebarManager.js';

// Import renderers
import { messageRenderer } from '../renderers/MessageRenderer.js';
import { widgetRenderer } from '../renderers/WidgetRenderer.js';

// Import file upload component
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

/**
 * DefinitionHandlers manages event handlers for definition events
 */
export class DefinitionHandlers {
    /**
     * Create a new DefinitionHandlers instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Function[]} */
        this._unsubscribers = [];

        // Bind handlers
        this._handleDefinitionListLoaded = this._handleDefinitionListLoaded.bind(this);
        this._handleDefinitionSelected = this._handleDefinitionSelected.bind(this);
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize and register event handlers
     */
    init() {
        if (this._initialized) {
            console.warn('[DefinitionHandlers] Already initialized');
            return;
        }

        this._subscribeToEvents();
        this._initialized = true;

        console.log('[DefinitionHandlers] Initialized');
    }

    /**
     * Subscribe to events
     * @private
     */
    _subscribeToEvents() {
        this._unsubscribers.push(eventBus.on(Events.DEFINITION_LIST_LOADED, this._handleDefinitionListLoaded));

        this._unsubscribers.push(eventBus.on(Events.DEFINITION_SELECTED, this._handleDefinitionSelected));
    }

    // =========================================================================
    // Event Handlers
    // =========================================================================

    /**
     * Handle definition list loaded - render tiles in welcome screen and populate sidebar agent menu
     * @private
     * @param {Array} definitions - List of definitions
     */
    _handleDefinitionListLoaded(definitions) {
        console.log(`[DefinitionHandlers] Definitions loaded: ${definitions.length}`);

        // Populate sidebar agent menu using the manager
        sidebarManager.populateSidebarAgentMenu(definitions);

        // Emit event for renderers to handle tile rendering
        // This decouples handlers from specific rendering logic
        eventBus.emit(Events.UI_RENDER_DEFINITION_TILES, { definitions });
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
     * @private
     * @param {Object} payload - Event payload
     * @param {Object} payload.definition - Selected definition
     * @param {string} [payload.previousId] - Previous definition ID
     */
    async _handleDefinitionSelected({ definition, previousId }) {
        console.log(`[DefinitionHandlers] Definition selected: ${definition.id} (prev: ${previousId})`);

        // Update sidebar agent selector icon using the manager
        sidebarManager.updateSidebarAgentSelector(definition);

        // Emit event for renderers to update tile selection
        eventBus.emit(Events.UI_UPDATE_DEFINITION_SELECTION, { definitionId: definition.id });

        // === RESET PREVIOUS CONVERSATION STATE ===
        // Disconnect existing WebSocket connection if any
        if (websocketClient.isConnected()) {
            console.log('[DefinitionHandlers] Disconnecting existing WebSocket connection');
            websocketClient.disconnect();
        }

        // Clear previous conversation messages
        messageRenderer.clearMessages();

        // Clear widget renderer state
        widgetRenderer.clearWidgets();

        // Clear current conversation ID
        stateManager.set(StateKeys.CURRENT_CONVERSATION_ID, null);

        // Enable chat input and upload since an agent is selected
        chatManager.enableInput();
        setUploadEnabled(true);

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
            const wsUrl = result.ws_url;
            const conversationId = result.conversation_id;

            console.log(`[DefinitionHandlers] Connecting WebSocket: ${wsUrl}`);

            await websocketClient.connect({
                conversationId: conversationId,
                definitionId: definition.id,
                wsUrl: wsUrl,
            });

            console.log(`[DefinitionHandlers] WebSocket connected for conversation: ${conversationId}`);
        } catch (error) {
            console.error('[DefinitionHandlers] Failed to create conversation or connect WebSocket:', error);

            eventBus.emit(Events.UI_TOAST, {
                message: `Failed to start conversation: ${error.message}`,
                type: 'error',
            });
        }
    }

    // =========================================================================
    // Cleanup
    // =========================================================================

    /**
     * Cleanup resources
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._initialized = false;
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const definitionHandlers = new DefinitionHandlers();

// =============================================================================
// Legacy Compatibility - Handler Registrations for old index.js
// These are kept for backward compatibility during migration
// =============================================================================

/**
 * @deprecated Use definitionHandlers.init() instead
 * Legacy factory handlers for registry auto-discovery.
 */
export const handlers = [
    {
        event: Events.DEFINITION_LIST_LOADED,
        handler: context => definitions => {
            console.warn('[DefinitionHandlers] DEPRECATED: Using legacy factory pattern');
            // Delegate to new class instance
            definitionHandlers._handleDefinitionListLoaded(definitions);
        },
        description: 'Render definition tiles when loaded',
        isFactory: true,
    },
    {
        event: Events.DEFINITION_SELECTED,
        handler: context => async payload => {
            console.warn('[DefinitionHandlers] DEPRECATED: Using legacy factory pattern');
            // Delegate to new class instance
            await definitionHandlers._handleDefinitionSelected(payload);
        },
        description: 'Create conversation and connect WebSocket when definition is selected',
        isFactory: true,
    },
];

export default handlers;
