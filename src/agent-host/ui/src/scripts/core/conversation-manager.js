/**
 * Conversation Manager
 * Handles conversation list rendering, CRUD operations, and pinning
 */

import { api } from '../services/api.js';
import { showRenameModal, showDeleteModal, showShareModal, showConversationInfoModal, showToast } from '../services/modals.js';
import { escapeHtml, getPinnedConversations, savePinnedConversations, getPinnedSessions, savePinnedSessions, isMobile } from '../utils/helpers.js';
import { setConversation as setDraftConversation } from './draft-manager.js';
import { renderMessages, clearMessages, appendToContainer, scrollToBottom } from './message-renderer.js';
import { isStreaming, getStreamingConversationId, getStreamingThinkingElement } from './stream-handler.js';
import { closeSidebar } from './sidebar-manager.js';

// =============================================================================
// State
// =============================================================================

let currentConversationId = null;
let conversationListEl = null;
let welcomeMessageEl = null;
let messageInputEl = null;

// Callbacks
let onConversationLoad = null;
let updateSessionProtectionFn = null;
let autoResizeFn = null;

// =============================================================================
// Initialization
// =============================================================================

/**
 * Initialize conversation manager
 * @param {Object} elements - DOM element references
 * @param {Object} callbacks - Callback functions
 */
export function initConversationManager(elements, callbacks) {
    conversationListEl = elements.conversationList;
    welcomeMessageEl = elements.welcomeMessage;
    messageInputEl = elements.messageInput;

    onConversationLoad = callbacks.onLoad || null;
    updateSessionProtectionFn = callbacks.updateSessionProtection || null;
    autoResizeFn = callbacks.autoResize || null;
}

// =============================================================================
// Conversation Loading
// =============================================================================

/**
 * Load all conversations
 */
export async function loadConversations() {
    try {
        const conversations = await api.getConversations();
        renderConversations(conversations);
    } catch (error) {
        console.error('Failed to load conversations:', error);
    }
}

/**
 * Load a specific conversation
 * @param {string} conversationId - Conversation ID to load
 */
export async function loadConversation(conversationId) {
    try {
        // If switching to the currently streaming conversation, restore the UI
        if (isStreaming() && conversationId === getStreamingConversationId()) {
            currentConversationId = conversationId;
            setDraftConversation(conversationId);
            await loadConversations();
            return;
        }

        const conversation = await api.getConversation(conversationId);
        currentConversationId = conversationId;

        // Switch draft context - saves current draft and loads draft for new conversation
        const savedDraft = setDraftConversation(conversationId);

        renderMessages(conversation.messages);
        await loadConversations();

        // If there's a saved draft for this conversation, restore it
        if (savedDraft && messageInputEl) {
            messageInputEl.value = savedDraft;
            if (autoResizeFn) autoResizeFn();
            if (updateSessionProtectionFn) updateSessionProtectionFn();
        }

        // If there's an active stream for this conversation, restore the thinking indicator
        if (isStreaming() && getStreamingConversationId() === conversationId) {
            const thinkingEl = getStreamingThinkingElement();
            if (thinkingEl) {
                appendToContainer(thinkingEl);
                scrollToBottom(true);
            }
        }

        if (onConversationLoad) {
            onConversationLoad(conversationId);
        }
    } catch (error) {
        console.error('Failed to load conversation:', error);
        showToast('Failed to load conversation', 'error');
    }
}

/**
 * Create a new conversation
 */
export async function newConversation() {
    try {
        const data = await api.createConversation();
        currentConversationId = data.conversation_id;

        // Switch draft context to new conversation
        setDraftConversation(data.conversation_id);

        clearMessages();
        await loadConversations();

        // Close sidebar on mobile
        if (isMobile()) {
            closeSidebar();
        }

        return data.conversation_id;
    } catch (error) {
        console.error('Failed to create conversation:', error);
        showToast('Failed to create conversation', 'error');
        return null;
    }
}

// =============================================================================
// Conversation Rendering
// =============================================================================

/**
 * Render conversations in the sidebar
 * @param {Array} conversations - Array of conversation objects
 */
function renderConversations(conversations) {
    if (!conversationListEl) return;

    conversationListEl.innerHTML = '';

    if (conversations.length === 0) {
        conversationListEl.innerHTML = '<p class="text-muted p-3">No conversations yet</p>';
        return;
    }

    // Get pinned conversations and sort - pinned first, then by update date
    const pinnedIds = getPinnedConversations();
    const sortedConversations = [...conversations].sort((a, b) => {
        const aIsPinned = pinnedIds.has(a.id);
        const bIsPinned = pinnedIds.has(b.id);
        if (aIsPinned && !bIsPinned) return -1;
        if (!aIsPinned && bIsPinned) return 1;
        return 0;
    });

    sortedConversations.forEach(conv => {
        const item = createConversationItem(conv, pinnedIds.has(conv.id));
        conversationListEl.appendChild(item);
    });
}

/**
 * Create a conversation list item element
 * @param {Object} conv - Conversation object
 * @param {boolean} isPinned - Whether conversation is pinned
 * @returns {HTMLElement} Conversation item element
 */
function createConversationItem(conv, isPinned) {
    const item = document.createElement('div');
    item.className = 'conversation-item';
    item.dataset.conversationId = conv.id;

    if (conv.id === currentConversationId) {
        item.classList.add('active');
    }
    if (isPinned) {
        item.classList.add('pinned');
    }

    item.innerHTML = `
        <div class="conversation-content">
            <div class="conversation-title-wrapper">
                ${isPinned ? '<i class="bi bi-pin-fill pin-indicator"></i>' : ''}
                <p class="conversation-title">${escapeHtml(conv.title || 'New conversation')}</p>
            </div>
            <div class="conversation-meta-row">
                <p class="conversation-meta">${conv.message_count} messages</p>
                <div class="conversation-actions">
                    <button class="btn-action btn-pin ${isPinned ? 'active' : ''}" title="${isPinned ? 'Unpin' : 'Pin'}">
                        <i class="bi bi-pin${isPinned ? '-fill' : ''}"></i>
                    </button>
                    <button class="btn-action btn-share" title="Share">
                        <i class="bi bi-share"></i>
                    </button>
                    <button class="btn-action btn-info-conv" title="Details">
                        <i class="bi bi-info-circle"></i>
                    </button>
                    <button class="btn-action btn-rename" title="Rename">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn-action btn-delete" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `;

    // Bind event handlers
    bindConversationItemEvents(item, conv);

    return item;
}

/**
 * Bind event handlers to a conversation item
 * @param {HTMLElement} item - Conversation item element
 * @param {Object} conv - Conversation object
 */
function bindConversationItemEvents(item, conv) {
    // Click on content loads conversation
    item.querySelector('.conversation-content').addEventListener('click', () => {
        loadConversation(conv.id);
        if (isMobile()) {
            closeSidebar();
        }
    });

    // Pin/Unpin button
    item.querySelector('.btn-pin').addEventListener('click', e => {
        e.stopPropagation();
        togglePinConversation(conv.id);
    });

    // Share button
    item.querySelector('.btn-share').addEventListener('click', async e => {
        e.stopPropagation();
        try {
            const fullConv = await api.getConversation(conv.id);
            showShareModal(fullConv);
        } catch (error) {
            console.error('Failed to load conversation for sharing:', error);
            showToast('Failed to share conversation', 'error');
        }
    });

    // Info button
    item.querySelector('.btn-info-conv').addEventListener('click', async e => {
        e.stopPropagation();
        try {
            const fullConv = await api.getConversation(conv.id);
            showConversationInfoModal(fullConv);
        } catch (error) {
            console.error('Failed to load conversation details:', error);
            showToast('Failed to load conversation details', 'error');
        }
    });

    // Rename button
    item.querySelector('.btn-rename').addEventListener('click', e => {
        e.stopPropagation();
        showRenameModal(conv.id, conv.title || 'New conversation', (id, newTitle) => {
            renameConversation(id, newTitle);
        });
    });

    // Delete button
    item.querySelector('.btn-delete').addEventListener('click', e => {
        e.stopPropagation();
        showDeleteModal(conv.id, conv.title || 'New conversation', id => {
            deleteConversation(id);
        });
    });
}

// =============================================================================
// Conversation Operations
// =============================================================================

/**
 * Toggle pin state for a conversation
 * @param {string} conversationId - Conversation ID to pin/unpin
 */
function togglePinConversation(conversationId) {
    const pinnedIds = getPinnedConversations();
    const wasPinned = pinnedIds.has(conversationId);

    if (wasPinned) {
        pinnedIds.delete(conversationId);
        showToast('Conversation unpinned', 'success');
    } else {
        pinnedIds.add(conversationId);
        showToast('Conversation pinned', 'success');
    }

    savePinnedConversations(pinnedIds);
    loadConversations();
}

/**
 * Rename a conversation
 * @param {string} conversationId - Conversation ID
 * @param {string} newTitle - New title
 */
async function renameConversation(conversationId, newTitle) {
    try {
        await api.renameConversation(conversationId, newTitle);
        await loadConversations();
        showToast('Conversation renamed', 'success');
    } catch (error) {
        console.error('Failed to rename conversation:', error);
        showToast(error.message || 'Failed to rename conversation', 'error');
    }
}

/**
 * Delete a conversation
 * @param {string} conversationId - Conversation ID
 */
async function deleteConversation(conversationId) {
    try {
        await api.deleteConversation(conversationId);

        // If we deleted the current conversation, clear the chat
        if (conversationId === currentConversationId) {
            currentConversationId = null;
            clearMessages();
            if (welcomeMessageEl) {
                welcomeMessageEl.style.display = '';
            }
        }

        await loadConversations();
        showToast('Conversation deleted', 'success');
    } catch (error) {
        console.error('Failed to delete conversation:', error);
        showToast(error.message || 'Failed to delete conversation', 'error');
    }
}

// =============================================================================
// State Getters/Setters
// =============================================================================

/**
 * Get current conversation ID
 * @returns {string|null}
 */
export function getCurrentConversationId() {
    return currentConversationId;
}

/**
 * Set current conversation ID
 * @param {string|null} id - Conversation ID
 */
export function setCurrentConversationId(id) {
    currentConversationId = id;
}

// =============================================================================
// Session List Management
// =============================================================================

// Current session tracking
let currentSessionId = null;
let currentSessionType = null;

/**
 * Load sessions for the sidebar
 * @param {string} [sessionType] - Optional filter by session type
 */
export async function loadSessions(sessionType = null) {
    currentSessionType = sessionType;
    try {
        const sessions = await api.getSessions();
        // Filter by session type if provided
        const filteredSessions = sessionType ? sessions.filter(s => s.session_type === sessionType) : sessions;
        renderSessions(filteredSessions);
    } catch (error) {
        console.error('Failed to load sessions:', error);
    }
}

/**
 * Render sessions in the sidebar
 * @param {Array} sessions - Array of session objects
 */
function renderSessions(sessions) {
    if (!conversationListEl) return;

    conversationListEl.innerHTML = '';

    if (!sessions || sessions.length === 0) {
        conversationListEl.innerHTML = '<p class="text-muted p-3">No sessions yet</p>';
        return;
    }

    // Get pinned sessions and sort - pinned first, then by update date
    const pinnedIds = getPinnedSessions();
    const sortedSessions = [...sessions].sort((a, b) => {
        const aIsPinned = pinnedIds.has(a.id);
        const bIsPinned = pinnedIds.has(b.id);
        if (aIsPinned && !bIsPinned) return -1;
        if (!aIsPinned && bIsPinned) return 1;
        // Then by date
        const aDate = new Date(a.updated_at || a.created_at);
        const bDate = new Date(b.updated_at || b.created_at);
        return bDate - aDate;
    });

    sortedSessions.forEach(session => {
        const isPinned = pinnedIds.has(session.id);
        const item = createSessionItem(session, isPinned);
        conversationListEl.appendChild(item);
    });
}

/**
 * Create a session list item element
 * @param {Object} session - Session object
 * @param {boolean} isPinned - Whether session is pinned
 * @returns {HTMLElement} Session item element
 */
function createSessionItem(session, isPinned) {
    const item = document.createElement('div');
    item.className = 'conversation-item session-item';
    item.dataset.sessionId = session.id;

    if (session.id === currentSessionId) {
        item.classList.add('active');
    }
    if (isPinned) {
        item.classList.add('pinned');
    }

    // Format timestamp
    const timestamp = new Date(session.updated_at || session.created_at);
    const timeStr = timestamp.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });

    // Session type icon
    const typeIcons = {
        learning: 'bi-mortarboard',
        thought: 'bi-lightbulb',
        validation: 'bi-check-circle',
    };
    const typeIcon = typeIcons[session.session_type] || 'bi-circle';

    // Session status
    const isActive = session.status === 'active';
    const statusBadge = isActive ? '<span class="badge bg-success ms-2">Active</span>' : '';

    // Title from config or default
    const title = session.config?.category_name || session.config?.topic || `${session.session_type} session`;

    item.innerHTML = `
        <div class="conversation-content">
            <div class="conversation-title-wrapper">
                ${isPinned ? '<i class="bi bi-pin-fill pin-indicator"></i>' : ''}
                <i class="bi ${typeIcon} me-2 text-muted session-type-icon"></i>
                <p class="conversation-title">${escapeHtml(title)}${statusBadge}</p>
            </div>
            <div class="conversation-meta-row">
                <p class="conversation-meta">${timeStr}</p>
                <div class="conversation-actions">
                    <button class="btn-action btn-pin ${isPinned ? 'active' : ''}" title="${isPinned ? 'Unpin' : 'Pin'}">
                        <i class="bi bi-pin${isPinned ? '-fill' : ''}"></i>
                    </button>
                    <button class="btn-action btn-delete" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `;

    // Bind event handlers
    bindSessionItemEvents(item, session);

    return item;
}

/**
 * Bind event handlers to a session item
 * @param {HTMLElement} item - Session item element
 * @param {Object} session - Session object
 */
function bindSessionItemEvents(item, session) {
    // Click to load session
    item.addEventListener('click', e => {
        // Don't trigger on action button clicks
        if (e.target.closest('.conversation-actions')) return;
        loadSession(session.id);
    });

    // Pin button
    const pinBtn = item.querySelector('.btn-pin');
    pinBtn?.addEventListener('click', e => {
        e.stopPropagation();
        toggleSessionPin(session.id);
    });

    // Delete button
    const deleteBtn = item.querySelector('.btn-delete');
    deleteBtn?.addEventListener('click', e => {
        e.stopPropagation();
        const sessionTitle = session.config?.category_name || session.config?.topic || `${session.session_type} session`;
        showDeleteModal(session.id, sessionTitle, () => deleteSession(session.id));
    });
}

/**
 * Load a session (view its history in the chat area)
 * @param {string} sessionId - Session ID to load
 */
export async function loadSession(sessionId) {
    try {
        // Get session details which includes conversation_id and items
        const session = await api.getSession(sessionId);
        currentSessionId = sessionId;

        // Try to load conversation messages first
        let hasMessages = false;
        if (session.conversation_id) {
            const conversation = await api.getConversation(session.conversation_id);
            if (conversation.messages && conversation.messages.length > 0) {
                renderMessages(conversation.messages);
                hasMessages = true;
            }
        }

        // If no conversation messages, try to reconstruct from session items
        if (!hasMessages && session.items && session.items.length > 0) {
            const reconstructedMessages = reconstructSessionMessages(session);
            if (reconstructedMessages.length > 0) {
                renderMessages(reconstructedMessages);
                hasMessages = true;
            }
        }

        // If still no messages, show a placeholder
        if (!hasMessages) {
            clearMessages();
            const placeholder = document.createElement('div');
            placeholder.className = 'text-muted text-center p-4';
            placeholder.innerHTML = `
                <i class="bi bi-chat-square-text fs-1 d-block mb-2"></i>
                <p>No messages in this session yet.</p>
                <small>Session status: ${session.status}</small>
            `;
            const container = document.getElementById('messages-container');
            container?.appendChild(placeholder);
        }

        // Mark active in list
        document.querySelectorAll('.session-item').forEach(el => {
            el.classList.toggle('active', el.dataset.sessionId === sessionId);
        });

        // Close sidebar on mobile
        if (isMobile()) {
            closeSidebar();
        }

        console.log('[ConversationManager] Session loaded:', sessionId, session);
    } catch (error) {
        console.error('Failed to load session:', error);
        showToast('Failed to load session', 'error');
    }
}

/**
 * Reconstruct chat messages from session items
 * @param {Object} session - Session object with items
 * @returns {Array} Array of message objects for rendering
 */
function reconstructSessionMessages(session) {
    const messages = [];

    for (const item of session.items || []) {
        // Add agent's question/content as assistant message
        if (item.content) {
            messages.push({
                role: 'assistant',
                content: item.content,
            });
        }

        // Add user's response if present
        if (item.response !== undefined && item.response !== null) {
            let responseText = item.response;
            // Handle structured responses
            if (typeof item.response === 'object') {
                responseText = item.response.value || item.response.text || JSON.stringify(item.response);
            }
            messages.push({
                role: 'user',
                content: String(responseText),
            });
        }
    }

    return messages;
}

/**
 * Toggle pin state for a session
 * @param {string} sessionId - Session ID
 */
function toggleSessionPin(sessionId) {
    const pinnedIds = getPinnedSessions();

    if (pinnedIds.has(sessionId)) {
        pinnedIds.delete(sessionId);
        showToast('Session unpinned', 'info');
    } else {
        pinnedIds.add(sessionId);
        showToast('Session pinned', 'success');
    }

    savePinnedSessions(pinnedIds);
    loadSessions(currentSessionType);
}

/**
 * Delete a session
 * @param {string} sessionId - Session ID
 */
async function deleteSession(sessionId) {
    try {
        await api.terminateSession(sessionId);

        // If we deleted the current session, clear the view
        if (sessionId === currentSessionId) {
            currentSessionId = null;
            clearMessages();
            if (welcomeMessageEl) {
                welcomeMessageEl.style.display = '';
            }
        }

        // Remove from pinned if present
        const pinnedIds = getPinnedSessions();
        if (pinnedIds.has(sessionId)) {
            pinnedIds.delete(sessionId);
            savePinnedSessions(pinnedIds);
        }

        await loadSessions(currentSessionType);
        showToast('Session deleted', 'success');
    } catch (error) {
        console.error('Failed to delete session:', error);
        showToast(error.message || 'Failed to delete session', 'error');
    }
}

/**
 * Get current session ID
 * @returns {string|null}
 */
export function getCurrentSessionId() {
    return currentSessionId;
}

/**
 * Set current session ID
 * @param {string|null} id - Session ID
 */
export function setCurrentSessionId(id) {
    currentSessionId = id;
}
