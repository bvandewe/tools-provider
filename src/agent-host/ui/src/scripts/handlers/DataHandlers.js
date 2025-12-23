/**
 * Data Plane Event Handlers (Class-based)
 *
 * Handles WebSocket protocol data-level messages using class-based architecture
 * with dependency injection via imported singletons.
 *
 * Data events include:
 * - Content streaming (chunks, complete)
 * - Tool calls and results
 * - Message acknowledgments
 * - Response submissions
 * - Audit events
 *
 * These map to backend events from: application/protocol/data.py
 *
 * @module handlers/DataHandlers
 */

import { Events, eventBus } from '../core/event-bus.js';

/**
 * Tool call storage for modal display
 * @type {Map<string, Object>}
 */
const toolCallStore = new Map();

/**
 * @class DataHandlers
 * @description Handles all WebSocket data plane events
 */
export class DataHandlers {
    /**
     * Create DataHandlers instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Function[]} */
        this._unsubscribers = [];

        // Bind all handlers
        this._handleContentChunk = this._handleContentChunk.bind(this);
        this._handleContentComplete = this._handleContentComplete.bind(this);
        this._handleToolCall = this._handleToolCall.bind(this);
        this._handleToolResult = this._handleToolResult.bind(this);
        this._handleMessageSend = this._handleMessageSend.bind(this);
        this._handleMessageAck = this._handleMessageAck.bind(this);
        this._handleResponseSubmit = this._handleResponseSubmit.bind(this);
        this._handleResponseAck = this._handleResponseAck.bind(this);
        this._handleAuditBatch = this._handleAuditBatch.bind(this);
        this._handleAuditAck = this._handleAuditAck.bind(this);
    }

    /**
     * Initialize handlers and subscribe to events
     * @returns {void}
     */
    init() {
        if (this._initialized) {
            console.warn('[DataHandlers] Already initialized');
            return;
        }

        this._subscribeToEvents();
        this._initialized = true;
        console.log('[DataHandlers] Initialized');
    }

    /**
     * Subscribe to EventBus events
     * @private
     */
    _subscribeToEvents() {
        // Content streaming
        this._unsubscribers.push(eventBus.on(Events.DATA_CONTENT_CHUNK, this._handleContentChunk), eventBus.on(Events.DATA_CONTENT_COMPLETE, this._handleContentComplete));

        // Tool calls
        this._unsubscribers.push(eventBus.on(Events.DATA_TOOL_CALL, this._handleToolCall), eventBus.on(Events.DATA_TOOL_RESULT, this._handleToolResult));

        // Message handling
        this._unsubscribers.push(eventBus.on(Events.DATA_MESSAGE_SEND, this._handleMessageSend), eventBus.on(Events.DATA_MESSAGE_ACK, this._handleMessageAck));

        // Response handling
        this._unsubscribers.push(eventBus.on(Events.DATA_RESPONSE_SUBMIT, this._handleResponseSubmit), eventBus.on(Events.DATA_RESPONSE_ACK, this._handleResponseAck));

        // Audit
        this._unsubscribers.push(eventBus.on(Events.DATA_AUDIT_BATCH, this._handleAuditBatch), eventBus.on(Events.DATA_AUDIT_ACK, this._handleAuditAck));
    }

    // =========================================================================
    // CONTENT STREAMING HANDLERS
    // =========================================================================

    /**
     * Handler for data.content.chunk
     * Server streams content chunk (from LLM)
     * @private
     */
    _handleContentChunk(payload) {
        console.log('[DataHandlers] Content chunk received:', {
            messageId: payload.messageId,
            contentLength: payload.content?.length || 0,
        });

        // Emit streaming event for MessageRenderer to handle
        eventBus.emit(Events.MESSAGE_STREAMING, payload);
    }

    /**
     * Handler for data.content.complete
     * Server signals content stream is complete
     * @private
     */
    _handleContentComplete(payload) {
        console.log('[DataHandlers] Content complete:', payload.messageId);

        // Emit completion event
        eventBus.emit(Events.MESSAGE_COMPLETE, payload);

        // Update streaming state
        eventBus.emit(Events.UI_STREAMING_STATE, { isStreaming: false });
    }

    // =========================================================================
    // TOOL CALL HANDLERS
    // =========================================================================

    /**
     * Handler for data.tool.call
     * Server/LLM is invoking a tool
     * @private
     */
    _handleToolCall(payload) {
        const toolName = payload.toolName || payload.name;
        const callId = payload.callId || payload.toolCallId;

        console.log('[DataHandlers] Tool call:', toolName, 'callId:', callId);

        // Store tool call for modal display (admin users)
        this._storeToolCall(callId, {
            callId,
            toolName,
            arguments: payload.arguments,
            status: 'calling',
            timestamp: new Date().toISOString(),
        });

        // Emit event for tool UI component
        eventBus.emit(Events.TOOL_CALL_STARTED, {
            name: toolName,
            callId,
            arguments: payload.arguments,
        });
    }

    /**
     * Handler for data.tool.result
     * Tool execution result
     * @private
     */
    _handleToolResult(payload) {
        const toolName = payload.toolName || payload.name;
        const callId = payload.callId || payload.toolCallId;
        const success = payload.success !== false;

        console.log('[DataHandlers] Tool result:', toolName, 'callId:', callId, 'success:', success);

        // Update stored tool call with result
        this._updateToolCallResult(callId, {
            success,
            result: payload.result,
            executionTimeMs: payload.executionTimeMs || payload.executionTime,
        });

        // Emit completion event
        eventBus.emit(Events.TOOL_CALL_COMPLETED, {
            name: toolName,
            callId,
            success,
            result: payload.result,
            status: success ? 'completed' : 'failed',
            executionTimeMs: payload.executionTimeMs || payload.executionTime,
        });
    }

    // =========================================================================
    // MESSAGE HANDLERS
    // =========================================================================

    /**
     * Handler for data.message.send
     * Client's message was sent (echo/confirmation)
     * @private
     */
    _handleMessageSend(payload) {
        console.log('[DataHandlers] Message send confirmed:', payload.messageId);

        eventBus.emit(Events.MESSAGE_SENT, payload);
    }

    /**
     * Handler for data.message.ack
     * Server acknowledges receipt of user message
     * @private
     */
    _handleMessageAck(payload) {
        console.log('[DataHandlers] Message ack:', payload.messageId);

        // Start streaming state (server is now processing)
        eventBus.emit(Events.UI_STREAMING_STATE, { isStreaming: true });
    }

    // =========================================================================
    // RESPONSE HANDLERS (Widget responses)
    // =========================================================================

    /**
     * Handler for data.response.submit
     * Client's widget response was submitted (echo/confirmation)
     * @private
     */
    _handleResponseSubmit(payload) {
        console.log('[DataHandlers] Response submitted:', payload.widgetId || payload.responseId);

        eventBus.emit(Events.WIDGET_RESPONSE, payload);
    }

    /**
     * Handler for data.response.ack
     * Server acknowledges widget response
     * @private
     */
    _handleResponseAck(payload) {
        console.log('[DataHandlers] Response ack:', payload.widgetId, 'status:', payload.status);

        // Backend sends { widgetId, itemId, status: "received" } for success
        // or { widgetId, accepted: false, validationErrors: [...] } for validation failure
        if (payload.status === 'received' || payload.accepted === true) {
            // Widget response accepted - emit success event
            eventBus.emit(Events.WIDGET_VALIDATED, {
                widgetId: payload.widgetId,
                valid: true,
            });
        } else if (payload.accepted === false) {
            // Show validation errors
            eventBus.emit(Events.WIDGET_VALIDATED, {
                widgetId: payload.widgetId,
                valid: false,
                errors: payload.validationErrors,
            });
        }
        // If neither status nor accepted, just log (already done above)
    }

    // =========================================================================
    // AUDIT HANDLERS
    // =========================================================================

    /**
     * Handler for data.audit.batch
     * @private
     */
    _handleAuditBatch(payload) {
        console.debug('[DataHandlers] Audit batch received:', payload.batchId);
        // Server is recording - usually no client action needed
    }

    /**
     * Handler for data.audit.ack
     * @private
     */
    _handleAuditAck(payload) {
        console.debug('[DataHandlers] Audit ack:', payload.batchId);
        // Clear pending audit batch from local queue would go here
    }

    // =========================================================================
    // TOOL CALL STORAGE
    // =========================================================================

    /**
     * Store a tool call for later display in modal
     * @private
     * @param {string} callId - Tool call ID
     * @param {Object} data - Tool call data
     */
    _storeToolCall(callId, data) {
        toolCallStore.set(callId, data);
    }

    /**
     * Update a stored tool call with result
     * @private
     * @param {string} callId - Tool call ID
     * @param {Object} resultData - Result data to merge
     */
    _updateToolCallResult(callId, resultData) {
        const existing = toolCallStore.get(callId);
        if (existing) {
            toolCallStore.set(callId, {
                ...existing,
                ...resultData,
                status: resultData.success ? 'completed' : 'failed',
            });
        }
    }

    /**
     * Get a stored tool call by ID
     * @param {string} callId - Tool call ID
     * @returns {Object|undefined} Tool call data
     */
    getToolCall(callId) {
        return toolCallStore.get(callId);
    }

    /**
     * Get all stored tool calls
     * @returns {Array<Object>} All tool calls
     */
    getAllToolCalls() {
        return Array.from(toolCallStore.values());
    }

    /**
     * Clear tool calls (e.g., when starting new conversation)
     */
    clearToolCalls() {
        toolCallStore.clear();
    }

    /**
     * Cleanup and unsubscribe from events
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        toolCallStore.clear();
        this._initialized = false;
        console.log('[DataHandlers] Destroyed');
    }

    /**
     * Check if handlers are initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }
}

// Export singleton instance
export const dataHandlers = new DataHandlers();

// Export tool call utilities for external use
export const getToolCall = callId => dataHandlers.getToolCall(callId);
export const getAllToolCalls = () => dataHandlers.getAllToolCalls();
export const clearToolCalls = () => dataHandlers.clearToolCalls();

export default dataHandlers;
