/**
 * Conversation Manager
 * Handles conversation list rendering, CRUD operations, and pinning
 */

import { api } from '../services/api.js';
import { showRenameModal, showDeleteModal, showShareModal, showConversationInfoModal, showToast } from '../services/modals.js';
import { escapeHtml, getPinnedConversations, savePinnedConversations, isMobile } from '../utils/helpers.js';
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
