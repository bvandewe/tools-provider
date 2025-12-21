/**
 * Data Plane Event Handlers
 *
 * Handles WebSocket protocol data-level messages:
 * - Content streaming (chunks, complete)
 * - Tool calls and results
 * - Message acknowledgments
 * - Response submissions
 * - Audit events
 *
 * These map to backend events from: application/protocol/data.py
 *
 * @module handlers/data-handlers
 */

import { Events } from '../core/event-bus.js';

// =============================================================================
// CONTENT STREAMING HANDLERS
// =============================================================================

/**
 * Handler for data.content.chunk
 * Server streams content chunk (from LLM)
 *
 * Payload:
 * - messageId: string - Parent message ID
 * - chunkIndex: number - Sequence number
 * - content: string - Text content chunk
 * - contentType: string - "text" | "markdown" | "code"
 * - isFinal: boolean - Hint that this may be last chunk
 */
function handleContentChunk(context) {
    return payload => {
        // Log chunk receipt for debugging
        console.log('[DataHandler] Content chunk received:', {
            messageId: payload.messageId,
            contentLength: payload.content?.length || 0,
            hasContext: !!context,
            hasAppendMethod: !!context?.appendStreamingContent,
        });

        // Append to streaming message
        if (context.appendStreamingContent) {
            context.appendStreamingContent(payload.messageId, payload.content, payload.contentType);
        } else {
            console.warn('[DataHandler] No appendStreamingContent method on context');
        }

        // Emit streaming event for UI updates
        if (context.eventBus) {
            context.eventBus.emit(Events.MESSAGE_STREAMING, payload);
        }
    };
}

/**
 * Handler for data.content.complete
 * Server signals content stream is complete
 *
 * Payload:
 * - messageId: string
 * - totalChunks: number
 * - finalContent: string - Complete assembled content (optional, for validation)
 * - metadata: object - Token counts, model info, etc.
 */
function handleContentComplete(context) {
    return payload => {
        console.log('[DataHandler] Content complete:', payload.messageId);

        // Finalize the streaming message
        if (context.finalizeStreamingMessage) {
            context.finalizeStreamingMessage(payload.messageId, payload.finalContent, payload.metadata);
        }

        // Emit completion event
        if (context.eventBus) {
            context.eventBus.emit(Events.MESSAGE_COMPLETE, payload);
        }

        // Re-enable chat input if was disabled during streaming
        if (context.enableChatInput) {
            context.enableChatInput(true);
        }

        // Update streaming state
        if (context.eventBus) {
            context.eventBus.emit(Events.UI_STREAMING_STATE, { isStreaming: false });
        }
    };
}

// =============================================================================
// TOOL CALL HANDLERS
// =============================================================================

/**
 * Handler for data.tool.call
 * Server/LLM is invoking a tool
 *
 * Payload from server:
 * - callId: string - Tool call ID
 * - toolName: string - Tool name
 * - arguments: object - Tool arguments
 */
function handleToolCall(context) {
    return payload => {
        const toolName = payload.toolName || payload.name;
        const callId = payload.callId || payload.toolCallId;

        console.log('[DataHandler] Tool call:', toolName, 'callId:', callId);

        // Store tool call for modal display (admin users)
        storeToolCall(callId, {
            callId,
            toolName,
            arguments: payload.arguments,
            status: 'calling',
            timestamp: new Date().toISOString(),
        });

        // Emit event for tool UI component (message renderer listens for this)
        if (context.eventBus) {
            context.eventBus.emit(Events.TOOL_CALL_STARTED, {
                name: toolName,
                callId,
                arguments: payload.arguments,
            });
        }
    };
}

/**
 * Handler for data.tool.result
 * Tool execution result
 *
 * Payload from server:
 * - callId: string - Tool call ID
 * - toolName: string - Tool name
 * - success: boolean
 * - result: any - Tool output
 * - executionTimeMs: number - Milliseconds
 */
function handleToolResult(context) {
    return payload => {
        const toolName = payload.toolName || payload.name;
        const callId = payload.callId || payload.toolCallId;
        const success = payload.success !== false;

        console.log('[DataHandler] Tool result:', toolName, 'callId:', callId, 'success:', success);

        // Update stored tool call with result (for modal display)
        updateToolCallResult(callId, {
            success,
            result: payload.result,
            executionTimeMs: payload.executionTimeMs || payload.executionTime,
        });

        // Emit completion event (message renderer listens for this)
        if (context.eventBus) {
            context.eventBus.emit(Events.TOOL_CALL_COMPLETED, {
                name: toolName,
                callId,
                success,
                result: payload.result,
                status: success ? 'completed' : 'failed',
                executionTimeMs: payload.executionTimeMs || payload.executionTime,
            });
        }
    };
}

// =============================================================================
// TOOL CALL STORAGE (for modal display)
// =============================================================================

/** @type {Map<string, Object>} Tool calls by callId */
const toolCallStore = new Map();

/**
 * Store a tool call for later display in modal
 * @param {string} callId - Tool call ID
 * @param {Object} data - Tool call data
 */
function storeToolCall(callId, data) {
    toolCallStore.set(callId, data);
}

/**
 * Update a stored tool call with result
 * @param {string} callId - Tool call ID
 * @param {Object} resultData - Result data to merge
 */
function updateToolCallResult(callId, resultData) {
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
export function getToolCall(callId) {
    return toolCallStore.get(callId);
}

/**
 * Get all stored tool calls
 * @returns {Array<Object>} All tool calls
 */
export function getAllToolCalls() {
    return Array.from(toolCallStore.values());
}

/**
 * Clear tool calls (e.g., when starting new conversation)
 */
export function clearToolCalls() {
    toolCallStore.clear();
}

// =============================================================================
// MESSAGE HANDLERS
// =============================================================================

/**
 * Handler for data.message.send
 * Client's message was sent (echo/confirmation)
 *
 * Note: This is typically emitted locally when user sends a message,
 * but can also come from server for cross-device sync.
 *
 * Payload:
 * - messageId: string
 * - content: string
 * - sentAt: string - ISO timestamp
 */
function handleMessageSend(context) {
    return payload => {
        console.log('[DataHandler] Message send confirmed:', payload.messageId);

        // Emit local event
        if (context.eventBus) {
            context.eventBus.emit(Events.MESSAGE_SENT, payload);
        }
    };
}

/**
 * Handler for data.message.ack
 * Server acknowledges receipt of user message
 *
 * Payload:
 * - messageId: string - Client-provided message ID
 * - serverMessageId: string - Server-assigned ID
 * - receivedAt: string - ISO timestamp
 * - sequence: number - Server sequence number
 */
function handleMessageAck(context) {
    return payload => {
        console.log('[DataHandler] Message ack:', payload.messageId);

        // Update message status from "sending" to "sent"
        if (context.updateMessageStatus) {
            context.updateMessageStatus(payload.messageId, 'sent', payload.serverMessageId);
        }

        // Start streaming state (server is now processing)
        if (context.eventBus) {
            context.eventBus.emit(Events.UI_STREAMING_STATE, { isStreaming: true });
        }
    };
}

// =============================================================================
// RESPONSE HANDLERS (Widget responses)
// =============================================================================

/**
 * Handler for data.response.submit
 * Client's widget response was submitted (echo/confirmation)
 *
 * Payload:
 * - responseId: string
 * - widgetId: string
 * - itemId: string
 * - value: any - Submitted value
 * - submittedAt: string
 */
function handleResponseSubmit(context) {
    return payload => {
        console.log('[DataHandler] Response submitted:', payload.responseId);

        // Emit local event
        if (context.eventBus) {
            context.eventBus.emit(Events.WIDGET_RESPONSE, payload);
        }
    };
}

/**
 * Handler for data.response.ack
 * Server acknowledges widget response
 *
 * Payload:
 * - responseId: string
 * - widgetId: string
 * - accepted: boolean
 * - validationErrors: array (if not accepted)
 * - serverResponseId: string
 */
function handleResponseAck(context) {
    return payload => {
        console.log('[DataHandler] Response ack:', payload.responseId);

        // Update widget state based on acceptance
        if (payload.accepted) {
            if (context.updateWidgetState) {
                context.updateWidgetState(payload.widgetId, 'answered');
            }
        } else {
            // Show validation errors
            if (context.showWidgetValidationErrors) {
                context.showWidgetValidationErrors(payload.widgetId, payload.validationErrors);
            }

            if (context.eventBus) {
                context.eventBus.emit(Events.WIDGET_VALIDATED, {
                    widgetId: payload.widgetId,
                    valid: false,
                    errors: payload.validationErrors,
                });
            }
        }
    };
}

// =============================================================================
// AUDIT HANDLERS
// =============================================================================

/**
 * Handler for data.audit.batch
 * Server sends batch of audit events (for proctoring/compliance)
 *
 * Payload:
 * - batchId: string
 * - events: array - Audit event records
 * - startTime: string
 * - endTime: string
 */
function handleAuditBatch(context) {
    return payload => {
        // Usually no client action needed - server is recording
        console.debug('[DataHandler] Audit batch received:', payload.batchId);
    };
}

/**
 * Handler for data.audit.ack
 * Server acknowledges client's audit submission
 *
 * Payload:
 * - batchId: string
 * - accepted: boolean
 */
function handleAuditAck(context) {
    return payload => {
        console.debug('[DataHandler] Audit ack:', payload.batchId);

        // Clear pending audit batch from local queue
        if (context.clearAuditBatch) {
            context.clearAuditBatch(payload.batchId);
        }
    };
}

// =============================================================================
// EXPORTS
// =============================================================================

/**
 * Data plane handlers registration
 *
 * @type {Array<{event: string, handler: Function, description: string}>}
 */
export const handlers = [
    // Content streaming
    {
        event: Events.DATA_CONTENT_CHUNK,
        handler: handleContentChunk,
        description: 'Server streams content chunk from LLM',
    },
    {
        event: Events.DATA_CONTENT_COMPLETE,
        handler: handleContentComplete,
        description: 'Server signals content stream is complete',
    },

    // Tool calls
    {
        event: Events.DATA_TOOL_CALL,
        handler: handleToolCall,
        description: 'Server/LLM is invoking a tool',
    },
    {
        event: Events.DATA_TOOL_RESULT,
        handler: handleToolResult,
        description: 'Tool execution result',
    },

    // Message handling
    {
        event: Events.DATA_MESSAGE_SEND,
        handler: handleMessageSend,
        description: 'Client message send confirmation',
    },
    {
        event: Events.DATA_MESSAGE_ACK,
        handler: handleMessageAck,
        description: 'Server acknowledges receipt of user message',
    },

    // Response handling
    {
        event: Events.DATA_RESPONSE_SUBMIT,
        handler: handleResponseSubmit,
        description: 'Client widget response submission confirmation',
    },
    {
        event: Events.DATA_RESPONSE_ACK,
        handler: handleResponseAck,
        description: 'Server acknowledges widget response',
    },

    // Audit
    {
        event: Events.DATA_AUDIT_BATCH,
        handler: handleAuditBatch,
        description: 'Server sends audit event batch',
    },
    {
        event: Events.DATA_AUDIT_ACK,
        handler: handleAuditAck,
        description: 'Server acknowledges client audit submission',
    },
];

export default handlers;
