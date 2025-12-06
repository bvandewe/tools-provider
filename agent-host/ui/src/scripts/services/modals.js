/**
 * Modal Service
 * Manages Bootstrap modals for the application
 */

// Store modal instances and callbacks
const modalState = {
    renameCallback: null,
    deleteCallback: null,
    currentConversationId: null,
    currentTitle: null,
};

/**
 * Initialize modal event handlers
 * Call this once after DOM is ready
 */
export function initModals() {
    // Rename modal
    const renameModal = document.getElementById('rename-modal');
    const renameInput = document.getElementById('rename-input');
    const renameConfirmBtn = document.getElementById('rename-confirm-btn');

    if (renameModal && renameInput && renameConfirmBtn) {
        // Focus input when modal opens
        renameModal.addEventListener('shown.bs.modal', () => {
            renameInput.focus();
            renameInput.select();
        });

        // Clear state when modal hides
        renameModal.addEventListener('hidden.bs.modal', () => {
            modalState.renameCallback = null;
            modalState.currentConversationId = null;
            modalState.currentTitle = null;
        });

        // Handle confirm button
        renameConfirmBtn.addEventListener('click', () => {
            const newTitle = renameInput.value.trim();
            if (newTitle && modalState.renameCallback) {
                modalState.renameCallback(modalState.currentConversationId, newTitle);
            }
            bootstrap.Modal.getInstance(renameModal)?.hide();
        });

        // Handle Enter key in input
        renameInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') {
                e.preventDefault();
                renameConfirmBtn.click();
            }
        });
    }

    // Delete confirmation modal
    const deleteModal = document.getElementById('delete-modal');
    const deleteConfirmBtn = document.getElementById('delete-confirm-btn');
    const deleteTitle = document.getElementById('delete-conversation-title');

    if (deleteModal && deleteConfirmBtn) {
        // Clear state when modal hides
        deleteModal.addEventListener('hidden.bs.modal', () => {
            modalState.deleteCallback = null;
            modalState.currentConversationId = null;
        });

        // Handle confirm button
        deleteConfirmBtn.addEventListener('click', () => {
            if (modalState.deleteCallback && modalState.currentConversationId) {
                modalState.deleteCallback(modalState.currentConversationId);
            }
            bootstrap.Modal.getInstance(deleteModal)?.hide();
        });
    }
}

/**
 * Show the rename conversation modal
 * @param {string} conversationId - ID of the conversation to rename
 * @param {string} currentTitle - Current title of the conversation
 * @param {Function} onConfirm - Callback function(conversationId, newTitle)
 */
export function showRenameModal(conversationId, currentTitle, onConfirm) {
    const renameModal = document.getElementById('rename-modal');
    const renameInput = document.getElementById('rename-input');

    if (!renameModal || !renameInput) {
        console.error('Rename modal elements not found');
        // Fallback to prompt
        const newTitle = prompt('Enter new conversation title:', currentTitle);
        if (newTitle && newTitle.trim() && newTitle !== currentTitle) {
            onConfirm(conversationId, newTitle.trim());
        }
        return;
    }

    // Store state
    modalState.currentConversationId = conversationId;
    modalState.currentTitle = currentTitle;
    modalState.renameCallback = onConfirm;

    // Set input value
    renameInput.value = currentTitle;

    // Show modal
    const modal = new bootstrap.Modal(renameModal);
    modal.show();
}

/**
 * Show the delete confirmation modal
 * @param {string} conversationId - ID of the conversation to delete
 * @param {string} title - Title of the conversation (for display)
 * @param {Function} onConfirm - Callback function(conversationId)
 */
export function showDeleteModal(conversationId, title, onConfirm) {
    const deleteModal = document.getElementById('delete-modal');
    const deleteTitle = document.getElementById('delete-conversation-title');

    if (!deleteModal) {
        console.error('Delete modal not found');
        // Fallback to confirm
        if (confirm(`Delete conversation "${title}"?\n\nThis action cannot be undone.`)) {
            onConfirm(conversationId);
        }
        return;
    }

    // Store state
    modalState.currentConversationId = conversationId;
    modalState.deleteCallback = onConfirm;

    // Set title in modal
    if (deleteTitle) {
        deleteTitle.textContent = title;
    }

    // Show modal
    const modal = new bootstrap.Modal(deleteModal);
    modal.show();
}

/**
 * Show the tools modal with a list of available tools
 * @param {Array} tools - Array of tool objects
 */
export function showToolsModal(tools) {
    const toolsList = document.getElementById('tools-list');
    const toolsModal = document.getElementById('tools-modal');

    if (!toolsList || !toolsModal) {
        console.error('Tools modal elements not found');
        return;
    }

    toolsList.innerHTML = '';

    if (!tools || tools.length === 0) {
        toolsList.innerHTML = '<p class="text-muted">No tools available</p>';
    } else {
        tools.forEach(tool => {
            const item = document.createElement('div');
            item.className = 'tool-item';
            item.innerHTML = `
                <div class="tool-header">
                    <span>🔧</span>
                    <span class="tool-name">${escapeHtml(tool.name)}</span>
                </div>
                <p class="tool-description">${escapeHtml(tool.description || '')}</p>
                <div class="tool-params">
                    ${(tool.parameters || [])
                        .map(
                            p => `
                        <span class="param">
                            <span class="param-name">${escapeHtml(p.name)}</span>
                            <span class="param-type">(${escapeHtml(p.type)})</span>
                        </span>
                    `
                        )
                        .join('')}
                </div>
            `;
            toolsList.appendChild(item);
        });
    }

    const modal = new bootstrap.Modal(toolsModal);
    modal.show();
}

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of toast (success, error, warning, info)
 */
export function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        // Create container if it doesn't exist
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
    }

    const bgClass =
        {
            success: 'bg-success',
            error: 'bg-danger',
            warning: 'bg-warning',
            info: 'bg-primary',
        }[type] || 'bg-primary';

    const toastId = `toast-${Date.now()}`;
    const toastHtml = `
        <div id="${toastId}" class="toast ${bgClass} text-white" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">${escapeHtml(message)}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;

    document.getElementById('toast-container').insertAdjacentHTML('beforeend', toastHtml);

    const toastEl = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: 3000 });
    toast.show();

    // Remove from DOM after hidden
    toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove();
    });
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

export default {
    initModals,
    showRenameModal,
    showDeleteModal,
    showToolsModal,
    showToast,
};
