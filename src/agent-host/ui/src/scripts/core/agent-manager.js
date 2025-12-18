/**
 * Agent Manager
 * Core module for managing Agent aggregate state, background sessions, and event buffering.
 *
 * This module handles:
 * - Agent lifecycle (get-or-create, track active agents)
 * - Session management with background continuation (Option B)
 * - Event buffering for background agents
 * - Session restriction enforcement based on agent/session settings
 *
 * The key feature is that when users switch between agents, background agents
 * continue running and buffer their events. When the user switches back,
 * buffered events are replayed to update the UI.
 */

import { agentApi, AgentType, SessionModeToAgentType } from '../services/agent-api.js';
import { showToast } from '../services/modals.js';
import { setStatus } from './ui-manager.js';

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
        canEndEarly: false, // Configurable per session
    },
    [AgentType.COACH]: {
        canSwitchAgents: true,
        canAccessConversations: true,
        canTypeFreeText: true,
        canEndEarly: true,
    },
};

// =============================================================================
// State
// =============================================================================

/**
 * Agent manager state
 */
let state = {
    /** Currently active (visible) agent ID */
    activeAgentId: null,

    /** Currently active agent type */
    activeAgentType: null,

    /** Map of agent ID to agent data */
    agents: new Map(),

    /** Map of agent ID to active session data */
    sessions: new Map(),

    /** Map of agent ID to EventSource for SSE */
    eventSources: new Map(),

    /** Map of agent ID to buffered events (for background agents) */
    eventBuffers: new Map(),

    /** Map of agent ID to current restrictions */
    restrictions: new Map(),

    /** Set of agent IDs whose streams ended normally (to prevent reconnection) */
    streamsEndedNormally: new Set(),

    /** Whether manager is initialized */
    isInitialized: false,
};

// Callbacks
let callbacks = {
    onAgentChange: null,
    onSessionStart: null,
    onSessionEnd: null,
    onEventReceived: null,
    onBufferedEventsReplay: null,
    onRestrictionsChange: null,
};

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize the agent manager
 * @param {Object} callbackFunctions - Callback functions
 */
export function initAgentManager(callbackFunctions = {}) {
    callbacks = { ...callbacks, ...callbackFunctions };
    state.isInitialized = true;
    console.log('[AgentManager] Initialized');
}

/**
 * Reset the agent manager state
 */
export function resetAgentManager() {
    // Close all event sources
    state.eventSources.forEach((es, agentId) => {
        es.close();
        console.log(`[AgentManager] Closed EventSource for agent ${agentId}`);
    });

    state = {
        activeAgentId: null,
        activeAgentType: null,
        agents: new Map(),
        sessions: new Map(),
        eventSources: new Map(),
        eventBuffers: new Map(),
        restrictions: new Map(),
        streamsEndedNormally: new Set(),
        isInitialized: true,
    };

    console.log('[AgentManager] State reset');
}

// =============================================================================
// Agent Lifecycle
// =============================================================================

/**
 * Get or create an agent by type
 * @param {string} agentType - Agent type (tutor, thought, evaluator)
 * @returns {Promise<Object>} Agent data
 */
export async function getOrCreateAgent(agentType) {
    try {
        const agent = await agentApi.getOrCreateAgent(agentType);
        state.agents.set(agent.id, agent);

        // Initialize restrictions for this agent
        const restrictions = { ...DEFAULT_RESTRICTIONS[agentType] };
        state.restrictions.set(agent.id, restrictions);

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
export async function getAgent(agentId) {
    // Check cache first
    if (state.agents.has(agentId)) {
        return state.agents.get(agentId);
    }

    try {
        const agent = await agentApi.getAgent(agentId);
        state.agents.set(agentId, agent);
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
export async function loadAgents() {
    try {
        const agents = await agentApi.getAgents();
        agents.forEach(agent => {
            state.agents.set(agent.id, agent);
        });
        console.log(`[AgentManager] Loaded ${agents.length} agents`);
        return agents;
    } catch (error) {
        console.error('[AgentManager] Failed to load agents:', error);
        throw error;
    }
}

// =============================================================================
// Agent Switching (with Background Continuation)
// =============================================================================

/**
 * Switch to a different agent
 * The previous agent continues running in the background with events buffered.
 * @param {string} agentType - Agent type to switch to
 * @returns {Promise<Object>} The agent that was switched to
 */
export async function switchToAgent(agentType) {
    const previousAgentId = state.activeAgentId;
    const previousAgentType = state.activeAgentType;

    // Check if current agent allows switching
    if (previousAgentId && !canSwitchAgents()) {
        showToast('Cannot switch agents during this session', 'warning');
        throw new Error('Agent switching not allowed');
    }

    try {
        setStatus('connecting', 'Switching agent...');

        // Get or create the target agent
        const agent = await getOrCreateAgent(agentType);

        // Update active state
        state.activeAgentId = agent.id;
        state.activeAgentType = agentType;

        // If previous agent had an active session, move it to background
        if (previousAgentId && state.sessions.has(previousAgentId)) {
            console.log(`[AgentManager] Moving agent ${previousAgentId} to background`);
            // EventSource continues running, events will be buffered
            state.eventBuffers.set(previousAgentId, []);
        }

        // Check if this agent has an existing session
        let session = state.sessions.get(agent.id);

        // If there are buffered events for this agent, replay them
        if (state.eventBuffers.has(agent.id)) {
            const bufferedEvents = state.eventBuffers.get(agent.id);
            if (bufferedEvents.length > 0 && callbacks.onBufferedEventsReplay) {
                console.log(`[AgentManager] Replaying ${bufferedEvents.length} buffered events`);
                callbacks.onBufferedEventsReplay(agent.id, bufferedEvents);
            }
            state.eventBuffers.delete(agent.id);
        }

        // Notify callback
        if (callbacks.onAgentChange) {
            callbacks.onAgentChange(agent, previousAgentId, previousAgentType);
        }

        setStatus('connected', 'Connected');
        console.log(`[AgentManager] Switched to agent ${agent.id} (${agentType})`);

        return agent;
    } catch (error) {
        console.error('[AgentManager] Failed to switch agent:', error);
        setStatus('error', 'Failed to switch agent');
        throw error;
    }
}

/**
 * Deactivate the current agent (return to CHAT mode)
 * Agent continues running in background if it has an active session.
 */
export function deactivateAgent() {
    const previousAgentId = state.activeAgentId;
    const previousAgentType = state.activeAgentType;

    if (previousAgentId && state.sessions.has(previousAgentId)) {
        console.log(`[AgentManager] Agent ${previousAgentId} moved to background`);
        state.eventBuffers.set(previousAgentId, []);
    }

    state.activeAgentId = null;
    state.activeAgentType = null;

    if (callbacks.onAgentChange) {
        callbacks.onAgentChange(null, previousAgentId, previousAgentType);
    }

    console.log('[AgentManager] Deactivated agent, returned to CHAT mode');
}

// =============================================================================
// Session Management
// =============================================================================

/**
 * Start a new session with the active agent
 * @param {Object} options - Session options
 * @returns {Promise<Object>} Session data
 */
export async function startSession(options = {}) {
    const agentId = state.activeAgentId;
    if (!agentId) {
        throw new Error('No active agent');
    }

    try {
        setStatus('connecting', 'Starting session...');

        const session = await agentApi.startSession(agentId, options);
        state.sessions.set(agentId, session);

        // Clear the "stream ended normally" flag for this agent since we're starting a new session
        state.streamsEndedNormally.delete(agentId);

        // Apply session-specific restrictions if provided
        if (session.config?.restrictions) {
            const currentRestrictions = state.restrictions.get(agentId) || {};
            state.restrictions.set(agentId, {
                ...currentRestrictions,
                ...session.config.restrictions,
            });

            if (callbacks.onRestrictionsChange) {
                callbacks.onRestrictionsChange(agentId, state.restrictions.get(agentId));
            }
        }

        // Notify callback FIRST so stream-handler can initialize the thinking element
        // before events start arriving
        if (callbacks.onSessionStart) {
            callbacks.onSessionStart(agentId, session);
        }

        // Connect to SSE stream AFTER UI is ready
        connectAgentStream(agentId, session.session_id);

        setStatus('streaming', 'Session active');
        console.log(`[AgentManager] Started session ${session.session_id} for agent ${agentId}`);

        return session;
    } catch (error) {
        console.error('[AgentManager] Failed to start session:', error);
        setStatus('error', 'Session failed');
        throw error;
    }
}

/**
 * Resume an existing session (after page refresh or returning to agent)
 * @param {string} agentId - Agent ID
 * @returns {Promise<Object|null>} Session data or null if no active session
 */
export async function resumeSession(agentId) {
    try {
        const session = await agentApi.getCurrentSession(agentId);
        if (!session) {
            return null;
        }

        state.sessions.set(agentId, session);

        // Clear the "stream ended normally" flag for this agent since we're resuming
        state.streamsEndedNormally.delete(agentId);

        // Use session_id or id (depending on API response format)
        const sessionId = session.session_id || session.id;

        // Notify callback FIRST so stream-handler can initialize the thinking element
        // before events start arriving (important for resumed sessions too)
        if (agentId === state.activeAgentId && callbacks.onSessionStart) {
            callbacks.onSessionStart(agentId, session);
        }

        // Connect to SSE stream AFTER UI is ready
        if (agentId === state.activeAgentId) {
            connectAgentStream(agentId, sessionId);
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
export async function terminateSession(agentId = null, reason = 'User terminated') {
    agentId = agentId || state.activeAgentId;
    if (!agentId) {
        throw new Error('No agent specified');
    }

    // Check if session can be ended early
    if (!canEndEarly(agentId)) {
        showToast('Cannot end this session early', 'warning');
        throw new Error('Early termination not allowed');
    }

    try {
        await agentApi.terminateSession(agentId, reason);

        // Clean up
        const session = state.sessions.get(agentId);
        state.sessions.delete(agentId);
        state.streamsEndedNormally.delete(agentId);
        disconnectAgentStream(agentId);
        state.eventBuffers.delete(agentId);

        if (callbacks.onSessionEnd) {
            callbacks.onSessionEnd(agentId, session, reason);
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
export async function submitResponse(agentId = null, responseData) {
    agentId = agentId || state.activeAgentId;
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

// =============================================================================
// SSE Streaming
// =============================================================================

/**
 * Connect to an agent's SSE stream
 * @param {string} agentId - Agent ID
 * @param {string} [sessionId] - Optional session ID (uses session stream for actual execution)
 */
function connectAgentStream(agentId, sessionId = null) {
    // Don't reconnect if stream ended normally for this agent
    if (state.streamsEndedNormally.has(agentId)) {
        console.log(`[AgentManager] Skipping reconnect - stream already ended normally for agent ${agentId}`);
        return;
    }

    // Close existing connection if any
    if (state.eventSources.has(agentId)) {
        state.eventSources.get(agentId).close();
        state.eventSources.delete(agentId);
    }

    const eventSource = agentApi.createEventSource(agentId, sessionId);

    eventSource.onmessage = event => {
        handleAgentEvent(agentId, 'message', JSON.parse(event.data));
    };

    eventSource.onerror = error => {
        // SSE fires onerror when connection closes, even on normal end
        // Check state-level flag to prevent reconnection after normal stream completion
        if (state.streamsEndedNormally.has(agentId)) {
            console.log(`[AgentManager] SSE stream ended normally for agent ${agentId}, not reconnecting`);
            // Clean up the EventSource
            if (state.eventSources.has(agentId)) {
                state.eventSources.get(agentId).close();
                state.eventSources.delete(agentId);
            }
            return;
        }
        console.error(`[AgentManager] SSE error for agent ${agentId}:`, error);
        // Only attempt reconnection if this was an unexpected error and session is still active
        setTimeout(() => {
            if (state.sessions.has(agentId) && !state.streamsEndedNormally.has(agentId)) {
                console.log(`[AgentManager] Attempting SSE reconnection for agent ${agentId}`);
                connectAgentStream(agentId, sessionId);
            }
        }, 3000);
    };

    // Listen for specific event types
    const eventTypes = [
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

    eventTypes.forEach(type => {
        eventSource.addEventListener(type, event => {
            try {
                const data = JSON.parse(event.data);

                // Mark stream as ended normally on stream_complete and close EventSource
                // to prevent browser's auto-reconnection
                if (type === 'stream_complete') {
                    state.streamsEndedNormally.add(agentId);
                    console.log(`[AgentManager] Stream completed normally for agent ${agentId}, closing EventSource`);
                    // Close EventSource to prevent auto-reconnection
                    eventSource.close();
                    state.eventSources.delete(agentId);
                }

                handleAgentEvent(agentId, type, data);
            } catch (e) {
                console.error(`[AgentManager] Failed to parse event ${type}:`, e);
            }
        });
    });

    state.eventSources.set(agentId, eventSource);
    console.log(`[AgentManager] Connected to SSE stream for agent ${agentId}`);
}

/**
 * Disconnect from an agent's SSE stream
 * @param {string} agentId - Agent ID
 */
function disconnectAgentStream(agentId) {
    if (state.eventSources.has(agentId)) {
        state.eventSources.get(agentId).close();
        state.eventSources.delete(agentId);
        console.log(`[AgentManager] Disconnected SSE stream for agent ${agentId}`);
    }
    // Also clear the stream ended flag when explicitly disconnecting
    state.streamsEndedNormally.delete(agentId);
}

/**
 * Handle an event from an agent's SSE stream
 * @param {string} agentId - Agent ID
 * @param {string} eventType - Event type
 * @param {Object} data - Event data
 */
function handleAgentEvent(agentId, eventType, data) {
    // If this is the active agent, process immediately
    if (agentId === state.activeAgentId) {
        if (callbacks.onEventReceived) {
            callbacks.onEventReceived(agentId, eventType, data);
        }
    } else {
        // Buffer the event for later replay
        if (!state.eventBuffers.has(agentId)) {
            state.eventBuffers.set(agentId, []);
        }
        state.eventBuffers.get(agentId).push({ type: eventType, data, timestamp: Date.now() });
        console.log(`[AgentManager] Buffered event ${eventType} for background agent ${agentId}`);
    }

    // Handle session completion regardless of active state
    if (eventType === 'session_completed') {
        state.sessions.delete(agentId);
        state.streamsEndedNormally.add(agentId); // Mark as ended normally
        disconnectAgentStream(agentId);

        if (callbacks.onSessionEnd) {
            callbacks.onSessionEnd(agentId, data, 'Session completed');
        }
    }
}

// =============================================================================
// Restriction Checks
// =============================================================================

/**
 * Check if current agent allows switching to another agent
 * @returns {boolean}
 */
export function canSwitchAgents() {
    if (!state.activeAgentId) return true;
    const restrictions = state.restrictions.get(state.activeAgentId);
    return restrictions?.canSwitchAgents ?? true;
}

/**
 * Check if current agent allows accessing conversations sidebar
 * @returns {boolean}
 */
export function canAccessConversations() {
    if (!state.activeAgentId) return true;
    const restrictions = state.restrictions.get(state.activeAgentId);
    return restrictions?.canAccessConversations ?? true;
}

/**
 * Check if current agent allows free text input
 * @returns {boolean}
 */
export function canTypeFreeText() {
    if (!state.activeAgentId) return true;
    const restrictions = state.restrictions.get(state.activeAgentId);
    return restrictions?.canTypeFreeText ?? true;
}

/**
 * Check if an agent's session can be ended early
 * @param {string} agentId - Agent ID (defaults to active agent)
 * @returns {boolean}
 */
export function canEndEarly(agentId = null) {
    agentId = agentId || state.activeAgentId;
    if (!agentId) return true;
    const restrictions = state.restrictions.get(agentId);
    return restrictions?.canEndEarly ?? true;
}

/**
 * Get all restrictions for an agent
 * @param {string} agentId - Agent ID (defaults to active agent)
 * @returns {Object} Restrictions object
 */
export function getRestrictions(agentId = null) {
    agentId = agentId || state.activeAgentId;
    if (!agentId) return {};
    return state.restrictions.get(agentId) || {};
}

/**
 * Update restrictions for an agent
 * @param {string} agentId - Agent ID
 * @param {Object} newRestrictions - Restrictions to merge
 */
export function updateRestrictions(agentId, newRestrictions) {
    const current = state.restrictions.get(agentId) || {};
    state.restrictions.set(agentId, { ...current, ...newRestrictions });

    if (callbacks.onRestrictionsChange) {
        callbacks.onRestrictionsChange(agentId, state.restrictions.get(agentId));
    }
}

// =============================================================================
// State Getters
// =============================================================================

/**
 * Get the active agent ID
 * @returns {string|null}
 */
export function getActiveAgentId() {
    return state.activeAgentId;
}

/**
 * Get the active agent type
 * @returns {string|null}
 */
export function getActiveAgentType() {
    return state.activeAgentType;
}

/**
 * Get the active agent data
 * @returns {Object|null}
 */
export function getActiveAgent() {
    if (!state.activeAgentId) return null;
    return state.agents.get(state.activeAgentId) || null;
}

/**
 * Get session for an agent
 * @param {string} agentId - Agent ID (defaults to active agent)
 * @returns {Object|null}
 */
export function getSession(agentId = null) {
    agentId = agentId || state.activeAgentId;
    if (!agentId) return null;
    return state.sessions.get(agentId) || null;
}

/**
 * Check if an agent has an active session
 * @param {string} agentId - Agent ID (defaults to active agent)
 * @returns {boolean}
 */
export function hasActiveSession(agentId = null) {
    agentId = agentId || state.activeAgentId;
    if (!agentId) return false;
    return state.sessions.has(agentId);
}

/**
 * Check if we're in agent mode (vs CHAT mode)
 * @returns {boolean}
 */
export function isInAgentMode() {
    return state.activeAgentId !== null;
}

/**
 * Get all agents with active sessions (including background)
 * @returns {Array<string>} Array of agent IDs
 */
export function getAgentsWithActiveSessions() {
    return Array.from(state.sessions.keys());
}

/**
 * Get buffered event count for a background agent
 * @param {string} agentId - Agent ID
 * @returns {number}
 */
export function getBufferedEventCount(agentId) {
    const buffer = state.eventBuffers.get(agentId);
    return buffer ? buffer.length : 0;
}
