/**
 * System Plane Event Handlers
 *
 * Handles WebSocket protocol system-level messages:
 * - Connection lifecycle (establish, resume, close)
 * - Heartbeat (ping/pong)
 * - System errors
 *
 * These map to backend events from: application/protocol/system.py
 *
 * @module handlers/system-handlers
 */

import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';
import { ConnectionState } from '../core/constants.js';
import { updateModelsFromWebSocket } from '../core/config-manager.js';

/**
 * Handler for system.connection.established
 * Server confirms WebSocket connection with session info
 *
 * Payload:
 * - connectionId: string - Unique connection ID
 * - conversationId: string - Conversation ID
 * - userId: string - Authenticated user ID
 * - definitionId: string - Agent definition ID (optional)
 * - resuming: boolean - Whether this is a resumed connection
 * - sessionId: string - Server-assigned session ID
 * - protocolVersion: string - Protocol version (e.g., "1.0.0")
 * - serverTime: string - ISO timestamp
 * - heartbeatInterval: number - Ping interval in seconds
 * - serverCapabilities: string[] - Server-supported message types
 * - currentModel: string - Currently active model ID (optional)
 * - availableModels: Object[] - List of available models (optional)
 * - allowModelSelection: boolean - Whether user can change the model (optional)
 */
function handleConnectionEstablished(context) {
    return payload => {
        console.log('[SystemHandler] Connection established:', {
            connectionId: payload.connectionId?.slice(0, 8) + '...',
            conversationId: payload.conversationId,
            resuming: payload.resuming,
            capabilities: payload.serverCapabilities?.length || 0,
            currentModel: payload.currentModel,
            availableModels: payload.availableModels?.length || 0,
            allowModelSelection: payload.allowModelSelection,
        });

        // Store session info for reconnection
        if (payload.sessionId) {
            sessionStorage.setItem('ws_session_id', payload.sessionId);
        }

        // Update connection state
        context.connectionState = ConnectionState.CONNECTED;

        // Store server capabilities in state manager
        if (payload.serverCapabilities) {
            stateManager.set(StateKeys.SERVER_CAPABILITIES, payload.serverCapabilities);
            context.serverCapabilities = payload.serverCapabilities;
        }

        // Store conversation ID in state manager
        if (payload.conversationId) {
            stateManager.set(StateKeys.WS_CONVERSATION_ID, payload.conversationId);
        }

        // Store model information in state manager
        if (payload.availableModels) {
            stateManager.set(StateKeys.AVAILABLE_MODELS, payload.availableModels);
        }
        if (payload.currentModel) {
            stateManager.set(StateKeys.SELECTED_MODEL_ID, payload.currentModel);
        }
        if (typeof payload.allowModelSelection === 'boolean') {
            stateManager.set(StateKeys.ALLOW_MODEL_SELECTION, payload.allowModelSelection);
        }

        // Configure heartbeat if provided
        if (payload.heartbeatInterval && context.startHeartbeat) {
            context.startHeartbeat(payload.heartbeatInterval * 1000);
        }

        // Update UI to show connected state
        if (context.updateConnectionStatus) {
            context.updateConnectionStatus('connected', 'Connected');
        }

        // Update model selector from WebSocket connection data
        if (payload.availableModels || payload.allowModelSelection !== undefined) {
            updateModelsFromWebSocket({
                models: payload.availableModels || [],
                currentModel: payload.currentModel,
                allowSelection: payload.allowModelSelection ?? false,
            });
        }

        // Update tools indicator with tool count from server
        if (typeof payload.toolCount === 'number') {
            const toolsIndicator = document.querySelector('.tools-indicator');
            const toolsCountEl = document.querySelector('.tools-count');
            if (toolsCountEl) {
                toolsCountEl.textContent = payload.toolCount.toString();
                console.log(`[SystemHandler] Updated tools count: ${payload.toolCount}`);
            }
            // Add/remove 'has-tools' class to change indicator color to green
            if (toolsIndicator) {
                toolsIndicator.classList.toggle('has-tools', payload.toolCount > 0);
            }
            // Store in state manager for other components
            stateManager.set(StateKeys.TOOL_COUNT, payload.toolCount);
        }

        // Emit connected event with full payload for other components
        eventBus.emit(Events.WS_CONNECTED, {
            connectionId: payload.connectionId,
            conversationId: payload.conversationId,
            userId: payload.userId,
            definitionId: payload.definitionId,
            resuming: payload.resuming,
            serverCapabilities: payload.serverCapabilities,
            currentModel: payload.currentModel,
            availableModels: payload.availableModels,
            allowModelSelection: payload.allowModelSelection,
            toolCount: payload.toolCount,
        });
    };
}

/**
 * Handler for system.connection.resumed
 * Server confirms reconnection with previous session
 *
 * Payload:
 * - sessionId: string - Resumed session ID
 * - missedMessages: number - Count of messages sent while disconnected
 * - lastSequence: number - Last processed sequence number
 */
function handleConnectionResumed(context) {
    return payload => {
        console.log('[SystemHandler] Connection resumed:', payload);

        context.connectionState = ConnectionState.CONNECTED;

        // Handle missed messages if any
        if (payload.missedMessages > 0) {
            console.log(`[SystemHandler] ${payload.missedMessages} messages missed during disconnect`);
            // Could trigger a sync/refresh here
        }

        if (context.updateConnectionStatus) {
            context.updateConnectionStatus('connected', 'Reconnected');
        }
    };
}

/**
 * Handler for system.connection.close
 * Server initiates graceful connection close
 *
 * Payload:
 * - code: number - Close code (1000 = normal, 4xxx = application errors)
 * - reason: string - Human-readable reason
 * - canReconnect: boolean - Whether client should attempt reconnection
 */
function handleConnectionClose(context) {
    return payload => {
        console.log('[SystemHandler] Connection close requested:', payload);

        context.connectionState = ConnectionState.DISCONNECTED;

        // Clear session if server says no reconnect
        if (!payload.canReconnect) {
            sessionStorage.removeItem('ws_session_id');
        }

        if (context.updateConnectionStatus) {
            context.updateConnectionStatus('disconnected', payload.reason || 'Disconnected');
        }

        // Show user-friendly message for specific close codes
        if (payload.code >= 4000 && context.showToast) {
            context.showToast('error', payload.reason || 'Connection closed by server');
        }
    };
}

/**
 * Handler for system.ping
 * Server heartbeat - client must respond with pong
 *
 * Payload:
 * - timestamp: string - Server timestamp (echo back in pong)
 * - sequence: number - Ping sequence number
 */
function handlePing(context) {
    return payload => {
        // Respond with pong immediately
        if (context.sendMessage) {
            context.sendMessage({
                type: 'system.pong',
                payload: {
                    timestamp: payload.timestamp,
                    sequence: payload.sequence,
                },
            });
        }
    };
}

/**
 * Handler for system.pong
 * Response to client ping (for latency measurement)
 *
 * Payload:
 * - timestamp: string - Original ping timestamp
 * - sequence: number - Pong sequence number
 */
function handlePong(context) {
    return payload => {
        // Calculate round-trip latency
        if (payload.timestamp) {
            const latency = Date.now() - new Date(payload.timestamp).getTime();
            context.lastLatency = latency;

            // Could emit latency metric here
            console.debug(`[SystemHandler] Pong received, latency: ${latency}ms`);
        }
    };
}

/**
 * Handler for system.error
 * Server-side error notification
 *
 * Payload:
 * - code: string - Error code (e.g., "AUTH_EXPIRED", "RATE_LIMITED")
 * - message: string - Human-readable error message
 * - details: object - Additional error context
 * - recoverable: boolean - Whether error is recoverable
 * - retryAfter: number - Seconds to wait before retry (optional)
 */
function handleSystemError(context) {
    return payload => {
        console.error('[SystemHandler] System error:', payload);

        // Handle specific error codes
        switch (payload.code) {
            case 'AUTH_EXPIRED':
            case 'AUTH_INVALID':
                // Trigger re-authentication
                if (context.eventBus) {
                    context.eventBus.emit(Events.AUTH_SESSION_EXPIRED, payload);
                }
                break;

            case 'RATE_LIMITED':
                // Show rate limit message with retry time
                if (context.showToast) {
                    const retryMsg = payload.retryAfter ? `Rate limited. Retry in ${payload.retryAfter}s` : 'Rate limited. Please slow down.';
                    context.showToast('warning', retryMsg);
                }
                break;

            case 'INTERNAL_ERROR':
                // Log and show generic error
                if (context.showToast) {
                    context.showToast('error', 'Server error. Please try again.');
                }
                break;

            default:
                // Generic error handling
                if (context.showToast && payload.message) {
                    context.showToast('error', payload.message);
                }
        }

        // If not recoverable, may need to reconnect
        if (!payload.recoverable) {
            console.warn('[SystemHandler] Non-recoverable error, may need reconnection');
        }
    };
}

/**
 * System plane handlers registration
 *
 * @type {Array<{event: string, handler: Function, description: string}>}
 */
export const handlers = [
    {
        event: Events.SYSTEM_CONNECTION_ESTABLISHED,
        handler: handleConnectionEstablished,
        description: 'Server confirms WebSocket connection with session info',
    },
    {
        event: Events.SYSTEM_CONNECTION_RESUMED,
        handler: handleConnectionResumed,
        description: 'Server confirms reconnection with previous session state',
    },
    {
        event: Events.SYSTEM_CONNECTION_CLOSE,
        handler: handleConnectionClose,
        description: 'Server initiates graceful connection close',
    },
    {
        event: Events.SYSTEM_PING,
        handler: handlePing,
        description: 'Server heartbeat - respond with pong',
    },
    {
        event: Events.SYSTEM_PONG,
        handler: handlePong,
        description: 'Response to client ping for latency measurement',
    },
    {
        event: Events.SYSTEM_ERROR,
        handler: handleSystemError,
        description: 'Server-side error notification',
    },
];

export default handlers;
