/**
 * Application Constants
 *
 * Centralized location for constant values used throughout the application.
 *
 * @module core/constants
 */

// =============================================================================
// Connection States
// =============================================================================

/**
 * WebSocket connection states
 * @readonly
 * @enum {string}
 */
export const ConnectionState = {
    DISCONNECTED: 'disconnected',
    CONNECTING: 'connecting',
    CONNECTED: 'connected',
    RECONNECTING: 'reconnecting',
    ERROR: 'error',
};

// =============================================================================
// Message Types (Legacy - for backward compatibility)
// =============================================================================

/**
 * Legacy message types before protocol v1.0.0
 * @readonly
 * @enum {string}
 */
export const LegacyMessageTypes = {
    CONNECTED: 'connected',
    MESSAGE: 'message',
    CHUNK: 'chunk',
    DONE: 'done',
    ERROR: 'error',
    PING: 'ping',
    PONG: 'pong',
};

// =============================================================================
// Widget States
// =============================================================================

/**
 * Widget interaction states
 * @readonly
 * @enum {string}
 */
export const WidgetState = {
    PENDING: 'pending',
    ACTIVE: 'active',
    ANSWERED: 'answered',
    EXPIRED: 'expired',
    DISABLED: 'disabled',
};

// =============================================================================
// Conversation States
// =============================================================================

/**
 * Conversation lifecycle states
 * @readonly
 * @enum {string}
 */
export const ConversationState = {
    CREATED: 'created',
    ACTIVE: 'active',
    PAUSED: 'paused',
    COMPLETED: 'completed',
    TERMINATED: 'terminated',
};

// =============================================================================
// UI States
// =============================================================================

/**
 * Chat input states
 * @readonly
 * @enum {string}
 */
export const ChatInputState = {
    ENABLED: 'enabled',
    DISABLED: 'disabled',
    STREAMING: 'streaming',
    HIDDEN: 'hidden',
};

/**
 * Display states for conversation panels
 * @readonly
 * @enum {string}
 */
export const DisplayState = {
    NORMAL: 'normal',
    MINIMIZED: 'minimized',
    FULLSCREEN: 'fullscreen',
    HIDDEN: 'hidden',
};

// =============================================================================
// Error Codes
// =============================================================================

/**
 * Protocol error codes
 * @readonly
 * @enum {string}
 */
export const ErrorCode = {
    AUTH_EXPIRED: 'AUTH_EXPIRED',
    AUTH_INVALID: 'AUTH_INVALID',
    RATE_LIMITED: 'RATE_LIMITED',
    INTERNAL_ERROR: 'INTERNAL_ERROR',
    INVALID_MESSAGE: 'INVALID_MESSAGE',
    NOT_FOUND: 'NOT_FOUND',
    FORBIDDEN: 'FORBIDDEN',
};

// =============================================================================
// Timeouts
// =============================================================================

/**
 * Default timeout values (in milliseconds)
 * @readonly
 */
export const Timeouts = {
    TOAST_DURATION: 3000,
    DEBOUNCE_DELAY: 300,
    RECONNECT_BASE_DELAY: 1000,
    PING_INTERVAL: 30000,
    CONNECTION_TIMEOUT: 10000,
};

export default {
    ConnectionState,
    LegacyMessageTypes,
    WidgetState,
    ConversationState,
    ChatInputState,
    DisplayState,
    ErrorCode,
    Timeouts,
};
