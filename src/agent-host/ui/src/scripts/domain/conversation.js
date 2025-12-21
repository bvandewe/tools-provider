/**
 * Conversation Domain - Conversation business logic
 *
 * Pure business logic for conversations.
 * No DOM dependencies - UI updates happen via event bus.
 *
 * @module domain/conversation
 */

import { api } from '../services/api.js';
import { eventBus, Events } from '../core/event-bus.js';
import { stateManager, StateKeys } from '../core/state-manager.js';
import { getPinnedConversations, savePinnedConversations } from '../utils/storage.js';

// =============================================================================
// Types
// =============================================================================

/**
 * @typedef {Object} Conversation
 * @property {string} id - Conversation ID
 * @property {string} [title] - Conversation title
 * @property {string} [definition_id] - Associated definition ID
 * @property {string} created_at - Creation timestamp
 * @property {string} [updated_at] - Last update timestamp
 * @property {Object[]} [messages] - Messages in conversation
 */

/**
 * @typedef {Object} Message
 * @property {string} id - Message ID
 * @property {string} role - 'user' | 'assistant' | 'system'
 * @property {string} content - Message content
 * @property {string} created_at - Timestamp
 */

// =============================================================================
// Conversation List
// =============================================================================

/**
 * Load all conversations
 * @returns {Promise<Conversation[]>} List of conversations
 */
export async function loadConversations() {
    try {
        const conversations = await api.getConversations();

        stateManager.set(StateKeys.CONVERSATIONS, conversations);

        eventBus.emit(Events.CONVERSATION_LIST_UPDATED, conversations);

        return conversations;
    } catch (error) {
        console.error('[Conversation] Failed to load conversations:', error);
        return stateManager.get(StateKeys.CONVERSATIONS, []);
    }
}

/**
 * Get cached conversations
 * @returns {Conversation[]} Cached conversations
 */
export function getConversations() {
    return stateManager.get(StateKeys.CONVERSATIONS, []);
}

// =============================================================================
// Conversation CRUD
// =============================================================================

/**
 * Load a single conversation
 * @param {string} conversationId - Conversation ID
 * @returns {Promise<Conversation|null>} Conversation or null
 */
export async function loadConversation(conversationId) {
    try {
        const conversation = await api.getConversation(conversationId);

        stateManager.set(StateKeys.CURRENT_CONVERSATION_ID, conversationId);

        eventBus.emit(Events.CONVERSATION_LOADED, {
            conversation,
            conversationId,
            definitionId: conversation.definition_id,
        });

        return conversation;
    } catch (error) {
        console.error('[Conversation] Failed to load:', error);
        eventBus.emit(Events.UI_TOAST, {
            message: 'Failed to load conversation',
            type: 'error',
        });
        return null;
    }
}

/**
 * Create a new conversation
 * @param {string|null} [definitionId] - Optional definition ID
 * @returns {Promise<Conversation|null>} Created conversation or null
 */
export async function createConversation(definitionId = null) {
    try {
        const conversation = await api.createConversation(definitionId);

        stateManager.set(StateKeys.CURRENT_CONVERSATION_ID, conversation.id);

        eventBus.emit(Events.CONVERSATION_CREATED, conversation);

        return conversation;
    } catch (error) {
        console.error('[Conversation] Failed to create:', error);
        eventBus.emit(Events.UI_TOAST, {
            message: 'Failed to create conversation',
            type: 'error',
        });
        return null;
    }
}

/**
 * Rename a conversation
 * @param {string} conversationId - Conversation ID
 * @param {string} title - New title
 * @returns {Promise<boolean>} Success status
 */
export async function renameConversation(conversationId, title) {
    try {
        await api.renameConversation(conversationId, title);

        eventBus.emit(Events.CONVERSATION_UPDATED, {
            conversationId,
            changes: { title },
        });

        // Refresh list
        loadConversations();

        return true;
    } catch (error) {
        console.error('[Conversation] Failed to rename:', error);
        eventBus.emit(Events.UI_TOAST, {
            message: 'Failed to rename conversation',
            type: 'error',
        });
        return false;
    }
}

/**
 * Delete a conversation
 * @param {string} conversationId - Conversation ID
 * @returns {Promise<boolean>} Success status
 */
export async function deleteConversation(conversationId) {
    try {
        await api.deleteConversation(conversationId);

        // If deleted current conversation, clear it
        if (stateManager.get(StateKeys.CURRENT_CONVERSATION_ID) === conversationId) {
            stateManager.set(StateKeys.CURRENT_CONVERSATION_ID, null);
        }

        eventBus.emit(Events.CONVERSATION_DELETED, { conversationId });

        // Refresh list
        loadConversations();

        return true;
    } catch (error) {
        console.error('[Conversation] Failed to delete:', error);
        eventBus.emit(Events.UI_TOAST, {
            message: 'Failed to delete conversation',
            type: 'error',
        });
        return false;
    }
}

/**
 * Delete multiple conversations
 * @param {string[]} conversationIds - Conversation IDs
 * @returns {Promise<{deleted_count: number, failed_ids: string[]}>}
 */
export async function deleteConversations(conversationIds) {
    try {
        const result = await api.deleteConversations(conversationIds);

        // Check if current conversation was deleted
        const currentId = stateManager.get(StateKeys.CURRENT_CONVERSATION_ID);
        if (currentId && conversationIds.includes(currentId)) {
            stateManager.set(StateKeys.CURRENT_CONVERSATION_ID, null);
        }

        // Refresh list
        loadConversations();

        return result;
    } catch (error) {
        console.error('[Conversation] Failed to delete multiple:', error);
        eventBus.emit(Events.UI_TOAST, {
            message: 'Failed to delete conversations',
            type: 'error',
        });
        return { deleted_count: 0, failed_ids: conversationIds };
    }
}

/**
 * Delete all unpinned conversations
 * @returns {Promise<number>} Number of deleted conversations
 */
export async function deleteAllUnpinned() {
    const conversations = getConversations();
    const pinned = getPinnedConversations();

    const unpinnedIds = conversations
        .filter(c => !pinned.has(c.id))
        .map(c => c.id);

    if (unpinnedIds.length === 0) {
        return 0;
    }

    const result = await deleteConversations(unpinnedIds);
    return result.deleted_count;
}

// =============================================================================
// Current Conversation
// =============================================================================

/**
 * Get current conversation ID
 * @returns {string|null} Current conversation ID
 */
export function getCurrentConversationId() {
    return stateManager.get(StateKeys.CURRENT_CONVERSATION_ID, null);
}

/**
 * Set current conversation ID
 * @param {string|null} conversationId - Conversation ID
 */
export function setCurrentConversationId(conversationId) {
    stateManager.set(StateKeys.CURRENT_CONVERSATION_ID, conversationId);
}

// =============================================================================
// Pinning
// =============================================================================

/**
 * Toggle pinned state of a conversation
 * @param {string} conversationId - Conversation ID
 * @returns {boolean} New pinned state
 */
export function togglePinned(conversationId) {
    const pinned = getPinnedConversations();
    const newState = !pinned.has(conversationId);

    if (newState) {
        pinned.add(conversationId);
    } else {
        pinned.delete(conversationId);
    }

    savePinnedConversations(pinned);

    eventBus.emit(Events.CONVERSATION_UPDATED, {
        conversationId,
        changes: { isPinned: newState },
    });

    return newState;
}

/**
 * Check if conversation is pinned
 * @param {string} conversationId - Conversation ID
 * @returns {boolean} True if pinned
 */
export function isPinned(conversationId) {
    return getPinnedConversations().has(conversationId);
}

/**
 * Get pinned conversation IDs
 * @returns {Set<string>} Set of pinned IDs
 */
export { getPinnedConversations };

export default {
    loadConversations,
    getConversations,
    loadConversation,
    createConversation,
    renameConversation,
    deleteConversation,
    deleteConversations,
    deleteAllUnpinned,
    getCurrentConversationId,
    setCurrentConversationId,
    togglePinned,
    isPinned,
    getPinnedConversations,
};
