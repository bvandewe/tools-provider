/**
 * AgentManager - Class-based agent aggregate state manager
 *
 * Core manager for Agent aggregate state, background sessions, and event buffering.
 *
 * Key responsibilities:
 * - Agent lifecycle (get-or-create, track active agents)
 * - Session management with background continuation
 * - Event buffering for background agents
 * - Session restriction enforcement based on agent/session settings
 *
 * The key feature is that when users switch between agents, background agents
 * continue running and buffer their events. When the user switches back,
 * buffered events are replayed to update the UI.
 *
 * @module managers/AgentManager
 */

import { agentApi, AgentType } from '../services/agent-api.js';
import { showToast } from '../services/modals.js';
import { eventBus, Events } from '../core/event-bus.js';

// =============================================================================
// Constants
// =============================================================================

/**
 * Default session restrictions for each agent type
 * These can be overridden by session config
 */
const DEFAULT_RESTRICTIONS = {
    [AgentType.TUTOR]: {
        canSwitchAgents: true,
        canAccessConversations: true,
        canTypeFreeText: true,
        canEndEarly: true,
    },
    [AgentType.THOUGHT]: {
        canSwitchAgents: true,
        canAccessConversations: true,
        canTypeFreeText: true,
        canEndEarly: true,
    },
    [AgentType.EVALUATOR]: {
        canSwitchAgents: false,
        canAccessConversations: false,
        canTypeFreeText: false,
        canEndEarly: false,
    },
    [AgentType.COACH]: {
        canSwitchAgents: true,
        canAccessConversations: true,
        canTypeFreeText: true,
        canEndEarly: true,
    },
};

/**
 * SSE event types to listen for
 */
const SSE_EVENT_TYPES = [
    'connected',
    'content_chunk',
    'tool_calls_detected',
    'tool_executing',
    'tool_result',
    'message_complete',
    'stream_complete',
    'client_action',
    'run_suspended',
    'run_resumed',
    'state',
    'session_completed',
    'error',
    'heartbeat',
];

/**
 * @class AgentManager
 * @description Manages agent aggregate state, sessions, and event buffering
 */
export class AgentManager {
    /**
     * Create AgentManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {string|null} Currently active (visible) agent ID */
        this._activeAgentId = null;

        /** @type {string|null} Currently active agent type */
        this._activeAgentType = null;

        /** @type {Map<string, Object>} Map of agent ID to agent data */
        this._agents = new Map();

        /** @type {Map<string, Object>} Map of agent ID to active session data */
        this._sessions = new Map();

        /** @type {Map<string, EventSource>} Map of agent ID to EventSource for SSE */
        this._eventSources = new Map();

        /** @type {Map<string, Array>} Map of agent ID to buffered events (for background agents) */
        this._eventBuffers = new Map();

        /** @type {Map<string, Object>} Map of agent ID to current restrictions */
        this._restrictions = new Map();

        /** @type {Set<string>} Set of agent IDs whose streams ended normally (to prevent reconnection) */
        this._streamsEndedNormally = new Set();

        /** @type {Object} Callbacks */
        this._callbacks = {
            onAgentChange: null,
            onSessionStart: null,
            onSessionEnd: null,
            onEventReceived: null,
            onBufferedEventsReplay: null,
            onRestrictionsChange: null,
        };

        /** @type {Function|null} Status update function */
        this._setStatusFn = null;
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize the agent manager
     * @param {Object} callbacks - Callback functions
     * @param {Function} setStatusFn - Status update function
     */
    init(callbacks = {}, setStatusFn = null) {
        if (this._initialized) {
            console.warn('[AgentManager] Already initialized');
            return;
        }

        this._callbacks = { ...this._callbacks, ...callbacks };
        this._setStatusFn = setStatusFn;
        this._initialized = true;
        console.log('[AgentManager] Initialized');
    }

    /**
     * Reset the agent manager state
     */
    reset() {
        // Close all event sources
        this._eventSources.forEach((es, agentId) => {
            es.close();
            console.log(`[AgentManager] Closed EventSource for agent ${agentId}`);
        });

        this._activeAgentId = null;
        this._activeAgentType = null;
        this._agents.clear();
        this._sessions.clear();
        this._eventSources.clear();
        this._eventBuffers.clear();
        this._restrictions.clear();
        this._streamsEndedNormally.clear();

        console.log('[AgentManager] State reset');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this.reset();
        this._callbacks = {};
        this._setStatusFn = null;
        this._initialized = false;
        console.log('[AgentManager] Destroyed');
    }

    // =========================================================================
    // Status Helper
    // =========================================================================

    /**
     * Update status indicator
     * @private
     */
    _setStatus(state, text) {
        if (this._setStatusFn) {
            this._setStatusFn(state, text);
        }
    }

    // =========================================================================
    // Agent Lifecycle
    // =========================================================================

    /**
     * Get or create an agent by type
     * @param {string} agentType - Agent type (tutor, thought, evaluator)
     * @returns {Promise<Object>} Agent data
     */
    async getOrCreateAgent(agentType) {
        try {
            const agent = await agentApi.getOrCreateAgent(agentType);
            this._agents.set(agent.id, agent);

            // Initialize restrictions for this agent
            const restrictions = { ...DEFAULT_RESTRICTIONS[agentType] };
            this._restrictions.set(agent.id, restrictions);

            console.log(`[AgentManager] Got/created agent: ${agent.id} (${agentType})`);
            return agent;
        } catch (error) {
            console.error(`[AgentManager] Failed to get/create agent:`, error);
            throw error;
        }
    }

    /**
     * Get agent by ID (from cache or fetch)
     * @param {string} agentId - Agent ID
     * @returns {Promise<Object>} Agent data
     */
    async getAgent(agentId) {
        // Check cache first
        if (this._agents.has(agentId)) {
            return this._agents.get(agentId);
        }

        try {
            const agent = await agentApi.getAgent(agentId);
            this._agents.set(agentId, agent);
            return agent;
        } catch (error) {
            console.error(`[AgentManager] Failed to get agent ${agentId}:`, error);
            throw error;
        }
    }

    /**
     * Load all agents for the current user
     * @returns {Promise<Array>} List of agents
     */
    async loadAgents() {
        try {
            const agents = await agentApi.getAgents();
            agents.forEach(agent => {
                this._agents.set(agent.id, agent);
            });
            console.log(`[AgentManager] Loaded ${agents.length} agents`);
            return agents;
        } catch (error) {
            console.error('[AgentManager] Failed to load agents:', error);
            throw error;
        }
    }

    // =========================================================================
    // Agent Switching (with Background Continuation)
    // =========================================================================

    /**
     * Switch to a different agent
     * The previous agent continues running in the background with events buffered.
     * @param {string} agentType - Agent type to switch to
     * @returns {Promise<Object>} The agent that was switched to
     */
    async switchToAgent(agentType) {
        const previousAgentId = this._activeAgentId;
        const previousAgentType = this._activeAgentType;

        // Check if current agent allows switching
        if (previousAgentId && !this.canSwitchAgents()) {
            showToast('Cannot switch agents during this session', 'warning');
            throw new Error('Agent switching not allowed');
        }

        try {
            this._setStatus('connecting', 'Switching agent...');

            // Get or create the target agent
            const agent = await this.getOrCreateAgent(agentType);

            // Update active state
            this._activeAgentId = agent.id;
            this._activeAgentType = agentType;

            // If previous agent had an active session, move it to background
            if (previousAgentId && this._sessions.has(previousAgentId)) {
                console.log(`[AgentManager] Moving agent ${previousAgentId} to background`);
                // EventSource continues running, events will be buffered
                this._eventBuffers.set(previousAgentId, []);
            }

            // If there are buffered events for this agent, replay them
            if (this._eventBuffers.has(agent.id)) {
                const bufferedEvents = this._eventBuffers.get(agent.id);
                if (bufferedEvents.length > 0 && this._callbacks.onBufferedEventsReplay) {
                    console.log(`[AgentManager] Replaying ${bufferedEvents.length} buffered events`);
                    this._callbacks.onBufferedEventsReplay(agent.id, bufferedEvents);
                }
                this._eventBuffers.delete(agent.id);
            }

            // Notify callback
            if (this._callbacks.onAgentChange) {
                this._callbacks.onAgentChange(agent, previousAgentId, previousAgentType);
            }

            // Emit event
            eventBus.emit(Events.AGENT_CHANGED, { agent, previousAgentId, previousAgentType });

            this._setStatus('connected', 'Connected');
            console.log(`[AgentManager] Switched to agent ${agent.id} (${agentType})`);

            return agent;
        } catch (error) {
            console.error('[AgentManager] Failed to switch agent:', error);
            this._setStatus('error', 'Failed to switch agent');
            throw error;
        }
    }

    /**
     * Deactivate the current agent (return to CHAT mode)
     * Agent continues running in background if it has an active session.
     */
    deactivateAgent() {
        const previousAgentId = this._activeAgentId;
        const previousAgentType = this._activeAgentType;

        if (previousAgentId && this._sessions.has(previousAgentId)) {
            console.log(`[AgentManager] Agent ${previousAgentId} moved to background`);
            this._eventBuffers.set(previousAgentId, []);
        }

        this._activeAgentId = null;
        this._activeAgentType = null;

        if (this._callbacks.onAgentChange) {
            this._callbacks.onAgentChange(null, previousAgentId, previousAgentType);
        }

        eventBus.emit(Events.AGENT_DEACTIVATED, { previousAgentId, previousAgentType });

        console.log('[AgentManager] Deactivated agent, returned to CHAT mode');
    }

    // =========================================================================
    // Session Management
    // =========================================================================

    /**
     * Start a new session with the active agent
     * @param {Object} options - Session options
     * @returns {Promise<Object>} Session data
     */
    async startSession(options = {}) {
        const agentId = this._activeAgentId;
        if (!agentId) {
            throw new Error('No active agent');
        }

        try {
            this._setStatus('connecting', 'Starting session...');

            const session = await agentApi.startSession(agentId, options);
            this._sessions.set(agentId, session);

            // Clear the "stream ended normally" flag for this agent since we're starting a new session
            this._streamsEndedNormally.delete(agentId);

            // Apply session-specific restrictions if provided
            if (session.config?.restrictions) {
                const currentRestrictions = this._restrictions.get(agentId) || {};
                this._restrictions.set(agentId, {
                    ...currentRestrictions,
                    ...session.config.restrictions,
                });

                if (this._callbacks.onRestrictionsChange) {
                    this._callbacks.onRestrictionsChange(agentId, this._restrictions.get(agentId));
                }
            }

            // Notify callback FIRST so stream-handler can initialize the thinking element
            // before events start arriving
            if (this._callbacks.onSessionStart) {
                this._callbacks.onSessionStart(agentId, session);
            }

            // Connect to SSE stream AFTER UI is ready
            this._connectAgentStream(agentId, session.session_id);

            this._setStatus('streaming', 'Session active');
            console.log(`[AgentManager] Started session ${session.session_id} for agent ${agentId}`);

            return session;
        } catch (error) {
            console.error('[AgentManager] Failed to start session:', error);
            this._setStatus('error', 'Session failed');
            throw error;
        }
    }

    /**
     * Resume an existing session (after page refresh or returning to agent)
     * @param {string} agentId - Agent ID
     * @returns {Promise<Object|null>} Session data or null if no active session
     */
    async resumeSession(agentId) {
        try {
            const session = await agentApi.getCurrentSession(agentId);
            if (!session) {
                return null;
            }

            this._sessions.set(agentId, session);

            // Clear the "stream ended normally" flag for this agent since we're resuming
            this._streamsEndedNormally.delete(agentId);

            // Use session_id or id (depending on API response format)
            const sessionId = session.session_id || session.id;

            // Notify callback FIRST so stream-handler can initialize the thinking element
            // before events start arriving (important for resumed sessions too)
            if (agentId === this._activeAgentId && this._callbacks.onSessionStart) {
                this._callbacks.onSessionStart(agentId, session);
            }

            // Connect to SSE stream AFTER UI is ready
            if (agentId === this._activeAgentId) {
                this._connectAgentStream(agentId, sessionId);
            }

            console.log(`[AgentManager] Resumed session ${sessionId} for agent ${agentId}`);
            return session;
        } catch (error) {
            console.error(`[AgentManager] Failed to resume session for agent ${agentId}:`, error);
            return null;
        }
    }

    /**
     * Terminate the current session for an agent
     * @param {string} agentId - Agent ID (defaults to active agent)
     * @param {string} reason - Reason for termination
     * @returns {Promise<boolean>} Success
     */
    async terminateSession(agentId = null, reason = 'User terminated') {
        agentId = agentId || this._activeAgentId;
        if (!agentId) {
            throw new Error('No agent specified');
        }

        // Check if session can be ended early
        if (!this.canEndEarly(agentId)) {
            showToast('Cannot end this session early', 'warning');
            throw new Error('Early termination not allowed');
        }

        try {
            await agentApi.terminateSession(agentId, reason);

            // Clean up
            const session = this._sessions.get(agentId);
            this._sessions.delete(agentId);
            this._streamsEndedNormally.delete(agentId);
            this._disconnectAgentStream(agentId);
            this._eventBuffers.delete(agentId);

            if (this._callbacks.onSessionEnd) {
                this._callbacks.onSessionEnd(agentId, session, reason);
            }

            console.log(`[AgentManager] Terminated session for agent ${agentId}: ${reason}`);
            return true;
        } catch (error) {
            console.error(`[AgentManager] Failed to terminate session:`, error);
            throw error;
        }
    }

    /**
     * Submit a response to a pending widget/client action
     * @param {string} agentId - Agent ID (defaults to active agent)
     * @param {Object} responseData - Response data
     * @returns {Promise<Object>} Updated session state
     */
    async submitResponse(agentId = null, responseData) {
        agentId = agentId || this._activeAgentId;
        if (!agentId) {
            throw new Error('No agent specified');
        }

        try {
            const result = await agentApi.submitResponse(agentId, responseData);
            console.log(`[AgentManager] Submitted response for agent ${agentId}`);
            return result;
        } catch (error) {
            console.error(`[AgentManager] Failed to submit response:`, error);
            throw error;
        }
    }

    // =========================================================================
    // SSE Streaming
    // =========================================================================

    /**
     * Connect to an agent's SSE stream
     * @private
     * @param {string} agentId - Agent ID
     * @param {string} [sessionId] - Optional session ID (uses session stream for actual execution)
     */
    _connectAgentStream(agentId, sessionId = null) {
        // Don't reconnect if stream ended normally for this agent
        if (this._streamsEndedNormally.has(agentId)) {
            console.log(`[AgentManager] Skipping reconnect - stream already ended normally for agent ${agentId}`);
            return;
        }

        // Close existing connection if any
        if (this._eventSources.has(agentId)) {
            this._eventSources.get(agentId).close();
            this._eventSources.delete(agentId);
        }

        const eventSource = agentApi.createEventSource(agentId, sessionId);

        eventSource.onmessage = event => {
            this._handleAgentEvent(agentId, 'message', JSON.parse(event.data));
        };

        eventSource.onerror = error => {
            // SSE fires onerror when connection closes, even on normal end
            // Check state-level flag to prevent reconnection after normal stream completion
            if (this._streamsEndedNormally.has(agentId)) {
                console.log(`[AgentManager] SSE stream ended normally for agent ${agentId}, not reconnecting`);
                // Clean up the EventSource
                if (this._eventSources.has(agentId)) {
                    this._eventSources.get(agentId).close();
                    this._eventSources.delete(agentId);
                }
                return;
            }
            console.error(`[AgentManager] SSE error for agent ${agentId}:`, error);
            // Only attempt reconnection if this was an unexpected error and session is still active
            setTimeout(() => {
                if (this._sessions.has(agentId) && !this._streamsEndedNormally.has(agentId)) {
                    console.log(`[AgentManager] Attempting SSE reconnection for agent ${agentId}`);
                    this._connectAgentStream(agentId, sessionId);
                }
            }, 3000);
        };

        // Listen for specific event types
        SSE_EVENT_TYPES.forEach(type => {
            eventSource.addEventListener(type, event => {
                try {
                    const data = JSON.parse(event.data);

                    // Mark stream as ended normally on stream_complete and close EventSource
                    // to prevent browser's auto-reconnection
                    if (type === 'stream_complete') {
                        this._streamsEndedNormally.add(agentId);
                        console.log(`[AgentManager] Stream completed normally for agent ${agentId}, closing EventSource`);
                        // Close EventSource to prevent auto-reconnection
                        eventSource.close();
                        this._eventSources.delete(agentId);
                    }

                    this._handleAgentEvent(agentId, type, data);
                } catch (e) {
                    console.error(`[AgentManager] Failed to parse event ${type}:`, e);
                }
            });
        });

        this._eventSources.set(agentId, eventSource);
        console.log(`[AgentManager] Connected to SSE stream for agent ${agentId}`);
    }

    /**
     * Disconnect from an agent's SSE stream
     * @private
     * @param {string} agentId - Agent ID
     */
    _disconnectAgentStream(agentId) {
        if (this._eventSources.has(agentId)) {
            this._eventSources.get(agentId).close();
            this._eventSources.delete(agentId);
            console.log(`[AgentManager] Disconnected SSE stream for agent ${agentId}`);
        }
        // Also clear the stream ended flag when explicitly disconnecting
        this._streamsEndedNormally.delete(agentId);
    }

    /**
     * Handle an event from an agent's SSE stream
     * @private
     * @param {string} agentId - Agent ID
     * @param {string} eventType - Event type
     * @param {Object} data - Event data
     */
    _handleAgentEvent(agentId, eventType, data) {
        // If this is the active agent, process immediately
        if (agentId === this._activeAgentId) {
            if (this._callbacks.onEventReceived) {
                this._callbacks.onEventReceived(agentId, eventType, data);
            }
        } else {
            // Buffer the event for later replay
            if (!this._eventBuffers.has(agentId)) {
                this._eventBuffers.set(agentId, []);
            }
            this._eventBuffers.get(agentId).push({ type: eventType, data, timestamp: Date.now() });
            console.log(`[AgentManager] Buffered event ${eventType} for background agent ${agentId}`);
        }

        // Handle session completion regardless of active state
        if (eventType === 'session_completed') {
            this._sessions.delete(agentId);
            this._streamsEndedNormally.add(agentId); // Mark as ended normally
            this._disconnectAgentStream(agentId);

            if (this._callbacks.onSessionEnd) {
                this._callbacks.onSessionEnd(agentId, data, 'Session completed');
            }
        }
    }

    // =========================================================================
    // Restriction Checks
    // =========================================================================

    /**
     * Check if current agent allows switching to another agent
     * @returns {boolean}
     */
    canSwitchAgents() {
        if (!this._activeAgentId) return true;
        const restrictions = this._restrictions.get(this._activeAgentId);
        return restrictions?.canSwitchAgents ?? true;
    }

    /**
     * Check if current agent allows accessing conversations sidebar
     * @returns {boolean}
     */
    canAccessConversations() {
        if (!this._activeAgentId) return true;
        const restrictions = this._restrictions.get(this._activeAgentId);
        return restrictions?.canAccessConversations ?? true;
    }

    /**
     * Check if current agent allows free text input
     * @returns {boolean}
     */
    canTypeFreeText() {
        if (!this._activeAgentId) return true;
        const restrictions = this._restrictions.get(this._activeAgentId);
        return restrictions?.canTypeFreeText ?? true;
    }

    /**
     * Check if an agent's session can be ended early
     * @param {string} agentId - Agent ID (defaults to active agent)
     * @returns {boolean}
     */
    canEndEarly(agentId = null) {
        agentId = agentId || this._activeAgentId;
        if (!agentId) return true;
        const restrictions = this._restrictions.get(agentId);
        return restrictions?.canEndEarly ?? true;
    }

    /**
     * Get all restrictions for an agent
     * @param {string} agentId - Agent ID (defaults to active agent)
     * @returns {Object} Restrictions object
     */
    getRestrictions(agentId = null) {
        agentId = agentId || this._activeAgentId;
        if (!agentId) return {};
        return this._restrictions.get(agentId) || {};
    }

    /**
     * Update restrictions for an agent
     * @param {string} agentId - Agent ID
     * @param {Object} newRestrictions - Restrictions to merge
     */
    updateRestrictions(agentId, newRestrictions) {
        const current = this._restrictions.get(agentId) || {};
        this._restrictions.set(agentId, { ...current, ...newRestrictions });

        if (this._callbacks.onRestrictionsChange) {
            this._callbacks.onRestrictionsChange(agentId, this._restrictions.get(agentId));
        }
    }

    // =========================================================================
    // State Getters
    // =========================================================================

    /**
     * Get the active agent ID
     * @returns {string|null}
     */
    getActiveAgentId() {
        return this._activeAgentId;
    }

    /**
     * Get the active agent type
     * @returns {string|null}
     */
    getActiveAgentType() {
        return this._activeAgentType;
    }

    /**
     * Get the active agent data
     * @returns {Object|null}
     */
    getActiveAgent() {
        if (!this._activeAgentId) return null;
        return this._agents.get(this._activeAgentId) || null;
    }

    /**
     * Get session for an agent
     * @param {string} agentId - Agent ID (defaults to active agent)
     * @returns {Object|null}
     */
    getSession(agentId = null) {
        agentId = agentId || this._activeAgentId;
        if (!agentId) return null;
        return this._sessions.get(agentId) || null;
    }

    /**
     * Check if an agent has an active session
     * @param {string} agentId - Agent ID (defaults to active agent)
     * @returns {boolean}
     */
    hasActiveSession(agentId = null) {
        agentId = agentId || this._activeAgentId;
        if (!agentId) return false;
        return this._sessions.has(agentId);
    }

    /**
     * Check if we're in agent mode (vs CHAT mode)
     * @returns {boolean}
     */
    isInAgentMode() {
        return this._activeAgentId !== null;
    }

    /**
     * Get all agents with active sessions (including background)
     * @returns {Array<string>} Array of agent IDs
     */
    getAgentsWithActiveSessions() {
        return Array.from(this._sessions.keys());
    }

    /**
     * Get buffered event count for a background agent
     * @param {string} agentId - Agent ID
     * @returns {number}
     */
    getBufferedEventCount(agentId) {
        const buffer = this._eventBuffers.get(agentId);
        return buffer ? buffer.length : 0;
    }

    /**
     * Check if manager is initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }

    /**
     * Get active agent ID (alias for getter pattern consistency)
     * @returns {string|null}
     */
    get activeAgentId() {
        return this._activeAgentId;
    }

    /**
     * Get active agent type (alias for getter pattern consistency)
     * @returns {string|null}
     */
    get activeAgentType() {
        return this._activeAgentType;
    }
}

// Export singleton instance
export const agentManager = new AgentManager();
export default agentManager;
