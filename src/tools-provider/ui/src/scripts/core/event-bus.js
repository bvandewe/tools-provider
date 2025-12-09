/**
 * EventBus - Centralized pub/sub system for SSE event distribution
 *
 * This module provides a singleton EventBus that:
 * 1. Maintains a single SSE connection to /api/admin/sse
 * 2. Dispatches received events to registered handlers
 * 3. Handles reconnection on connection loss
 * 4. Provides typed event subscriptions
 */

/**
 * @typedef {Object} AdminEvent
 * @property {string} entity_type - source, tool, group, policy
 * @property {string} action - created, updated, deleted, etc.
 * @property {string} entity_id - ID of the affected entity
 * @property {string} [entity_name] - Name of the affected entity
 * @property {Object} details - Additional event details
 * @property {number} timestamp - Unix timestamp
 */

/**
 * @typedef {function(AdminEvent): void} EventHandler
 */

class EventBus {
    constructor() {
        /** @type {EventSource|null} */
        this._eventSource = null;

        /** @type {Map<string, Set<EventHandler>>} */
        this._handlers = new Map();

        /** @type {boolean} */
        this._connected = false;

        /** @type {number} */
        this._reconnectAttempts = 0;

        /** @type {number} */
        this._maxReconnectAttempts = 10;

        /** @type {number} */
        this._reconnectDelay = 1000; // Start with 1 second

        /** @type {number|null} */
        this._reconnectTimer = null;

        /** @type {Set<function(boolean): void>} */
        this._connectionListeners = new Set();
    }

    /**
     * Connect to the admin SSE endpoint
     * @returns {Promise<void>}
     */
    async connect() {
        if (this._eventSource) {
            console.log('[EventBus] Already connected or connecting');
            return;
        }

        return new Promise((resolve, reject) => {
            console.log('[EventBus] Connecting to /api/admin/sse...');

            this._eventSource = new EventSource('/api/admin/sse', {
                withCredentials: true, // Send cookies for authentication
            });

            this._eventSource.onopen = () => {
                console.log('[EventBus] SSE connection opened');
                this._connected = true;
                this._reconnectAttempts = 0;
                this._reconnectDelay = 1000;
                this._notifyConnectionListeners(true);
                resolve();
            };

            this._eventSource.onerror = error => {
                console.error('[EventBus] SSE connection error:', error);
                this._connected = false;
                this._notifyConnectionListeners(false);

                if (this._eventSource?.readyState === EventSource.CLOSED) {
                    this._eventSource = null;
                    this._scheduleReconnect();
                }
            };

            // Handle specific event types
            this._setupEventListeners();
        });
    }

    /**
     * Set up listeners for all event types
     * @private
     */
    _setupEventListeners() {
        if (!this._eventSource) return;

        // Connected event
        this._eventSource.addEventListener('connected', event => {
            console.log('[EventBus] Received connected event:', event.data);
            this._dispatch('connected', JSON.parse(event.data));
        });

        // Heartbeat event
        this._eventSource.addEventListener('heartbeat', event => {
            // Silent heartbeat, just log at debug level
            const data = JSON.parse(event.data);
            console.debug('[EventBus] Heartbeat:', data);
            this._dispatch('heartbeat', data);
        });

        // Source events
        const sourceEvents = ['source_registered', 'source_deleted', 'source_inventory_updated', 'source_health_changed'];
        sourceEvents.forEach(eventType => {
            this._eventSource.addEventListener(eventType, event => {
                console.log(`[EventBus] ${eventType}:`, event.data);
                this._dispatch(eventType, JSON.parse(event.data));
                this._dispatch('source', JSON.parse(event.data)); // Generic source event
            });
        });

        // Tool events
        const toolEvents = ['tool_discovered', 'tool_enabled', 'tool_disabled', 'tool_deprecated', 'tool_deleted'];
        toolEvents.forEach(eventType => {
            this._eventSource.addEventListener(eventType, event => {
                console.log(`[EventBus] ${eventType}:`, event.data);
                this._dispatch(eventType, JSON.parse(event.data));
                this._dispatch('tool', JSON.parse(event.data)); // Generic tool event
            });
        });

        // Group events
        const groupEvents = ['group_created', 'group_updated', 'group_activated', 'group_deactivated', 'group_deleted'];
        groupEvents.forEach(eventType => {
            this._eventSource.addEventListener(eventType, event => {
                console.log(`[EventBus] ${eventType}:`, event.data);
                this._dispatch(eventType, JSON.parse(event.data));
                this._dispatch('group', JSON.parse(event.data)); // Generic group event
            });
        });

        // Policy events
        const policyEvents = ['policy_defined', 'policy_updated', 'policy_activated', 'policy_deactivated', 'policy_deleted'];
        policyEvents.forEach(eventType => {
            this._eventSource.addEventListener(eventType, event => {
                console.log(`[EventBus] ${eventType}:`, event.data);
                this._dispatch(eventType, JSON.parse(event.data));
                this._dispatch('policy', JSON.parse(event.data)); // Generic policy event
            });
        });

        // Shutdown event - server is shutting down, close connection gracefully
        this._eventSource.addEventListener('shutdown', event => {
            console.log('[EventBus] Server shutdown event received:', event.data);
            this._dispatch('shutdown', JSON.parse(event.data));
            // Don't attempt to reconnect - server is shutting down
            this._maxReconnectAttempts = 0;
            this.disconnect();
        });

        // Error event
        this._eventSource.addEventListener('error', event => {
            console.error('[EventBus] SSE error event:', event.data);
            if (event.data) {
                this._dispatch('error', JSON.parse(event.data));
            }
        });
    }

    /**
     * Dispatch an event to registered handlers
     * @private
     * @param {string} eventType
     * @param {AdminEvent} data
     */
    _dispatch(eventType, data) {
        const handlers = this._handlers.get(eventType);
        if (handlers) {
            handlers.forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`[EventBus] Error in handler for ${eventType}:`, error);
                }
            });
        }

        // Also dispatch to wildcard handlers
        const wildcardHandlers = this._handlers.get('*');
        if (wildcardHandlers) {
            wildcardHandlers.forEach(handler => {
                try {
                    handler({ type: eventType, ...data });
                } catch (error) {
                    console.error('[EventBus] Error in wildcard handler:', error);
                }
            });
        }
    }

    /**
     * Schedule a reconnection attempt
     * @private
     */
    _scheduleReconnect() {
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
        }

        if (this._reconnectAttempts >= this._maxReconnectAttempts) {
            console.error('[EventBus] Max reconnection attempts reached');
            this._dispatch('reconnect_failed', { attempts: this._reconnectAttempts });
            return;
        }

        this._reconnectAttempts++;
        const delay = Math.min(this._reconnectDelay * Math.pow(2, this._reconnectAttempts - 1), 30000);

        console.log(`[EventBus] Scheduling reconnect attempt ${this._reconnectAttempts} in ${delay}ms`);

        this._reconnectTimer = setTimeout(() => {
            this.connect().catch(error => {
                console.error('[EventBus] Reconnect failed:', error);
            });
        }, delay);
    }

    /**
     * Subscribe to an event type
     * @param {string} eventType - Event type to subscribe to, or '*' for all events
     * @param {EventHandler} handler - Handler function
     * @returns {function(): void} Unsubscribe function
     */
    on(eventType, handler) {
        if (!this._handlers.has(eventType)) {
            this._handlers.set(eventType, new Set());
        }
        this._handlers.get(eventType).add(handler);

        // Return unsubscribe function
        return () => {
            this.off(eventType, handler);
        };
    }

    /**
     * Alias for on() - subscribe to an event type
     * @param {string} eventType - Event type to subscribe to
     * @param {EventHandler} handler - Handler function
     * @returns {function(): void} Unsubscribe function
     */
    subscribe(eventType, handler) {
        return this.on(eventType, handler);
    }

    /**
     * Unsubscribe from an event type
     * @param {string} eventType
     * @param {EventHandler} handler
     */
    off(eventType, handler) {
        const handlers = this._handlers.get(eventType);
        if (handlers) {
            handlers.delete(handler);
        }
    }

    /**
     * Alias for off() - unsubscribe from an event type
     * @param {string} eventType
     * @param {EventHandler} handler
     */
    unsubscribe(eventType, handler) {
        this.off(eventType, handler);
    }

    /**
     * Subscribe to connection state changes
     * @param {function(boolean): void} listener
     * @returns {function(): void} Unsubscribe function
     */
    onConnectionChange(listener) {
        this._connectionListeners.add(listener);
        // Immediately notify of current state
        listener(this._connected);
        return () => {
            this._connectionListeners.delete(listener);
        };
    }

    /**
     * Notify connection state listeners
     * @private
     * @param {boolean} connected
     */
    _notifyConnectionListeners(connected) {
        this._connectionListeners.forEach(listener => {
            try {
                listener(connected);
            } catch (error) {
                console.error('[EventBus] Error in connection listener:', error);
            }
        });
    }

    /**
     * Disconnect from SSE
     */
    disconnect() {
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
            this._reconnectTimer = null;
        }

        if (this._eventSource) {
            this._eventSource.close();
            this._eventSource = null;
        }

        this._connected = false;
        this._notifyConnectionListeners(false);
        console.log('[EventBus] Disconnected');
    }

    /**
     * Check if connected
     * @returns {boolean}
     */
    get isConnected() {
        return this._connected;
    }
}

// Singleton instance
const eventBus = new EventBus();

export { eventBus, EventBus };
export default eventBus;
