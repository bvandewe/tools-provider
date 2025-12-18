/**
 * Modal Service
 * Manages Bootstrap modals for the application
 */

import { marked } from 'marked';

// Configure marked for safe HTML rendering
marked.setOptions({
    breaks: true,
    gfm: true,
});

// Store modal instances and callbacks
const modalState = {
    renameCallback: null,
    deleteCallback: null,
    deleteAllUnpinnedCallback: null,
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

    // Delete all unpinned confirmation modal
    const deleteAllUnpinnedModal = document.getElementById('delete-all-unpinned-modal');
    const deleteAllUnpinnedConfirmBtn = document.getElementById('delete-all-unpinned-confirm-btn');

    if (deleteAllUnpinnedModal && deleteAllUnpinnedConfirmBtn) {
        // Clear state when modal hides
        deleteAllUnpinnedModal.addEventListener('hidden.bs.modal', () => {
            modalState.deleteAllUnpinnedCallback = null;
        });

        // Handle confirm button
        deleteAllUnpinnedConfirmBtn.addEventListener('click', () => {
            if (modalState.deleteAllUnpinnedCallback) {
                modalState.deleteAllUnpinnedCallback();
            }
            bootstrap.Modal.getInstance(deleteAllUnpinnedModal)?.hide();
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
 * Show a confirmation modal for deleting all unpinned conversations
 * @param {number} count - Number of unpinned conversations to delete
 * @param {Function} onConfirm - Callback function when confirmed
 */
export function showDeleteAllUnpinnedModal(count, onConfirm) {
    const deleteAllUnpinnedModal = document.getElementById('delete-all-unpinned-modal');
    const countEl = document.getElementById('delete-all-unpinned-count');
    const pluralEl = document.getElementById('delete-all-unpinned-plural');

    if (!deleteAllUnpinnedModal) {
        console.error('Delete all unpinned modal not found');
        // Fallback to confirm
        const confirmed = confirm(`Delete ${count} unpinned conversation${count === 1 ? '' : 's'}?\n\n` + 'This action cannot be undone. Pinned conversations will be preserved.');
        if (confirmed && onConfirm) {
            onConfirm();
        }
        return;
    }

    // Store callback
    modalState.deleteAllUnpinnedCallback = onConfirm;

    // Set count in modal
    if (countEl) {
        countEl.textContent = count;
    }
    // Handle plural/singular
    if (pluralEl) {
        pluralEl.style.display = count === 1 ? 'none' : '';
    }

    // Show modal
    const modal = new bootstrap.Modal(deleteAllUnpinnedModal);
    modal.show();
}

/**
 * Show the tools modal with a list of available tools
 * @param {Array} tools - Array of tool objects
 * @param {Function} onRefresh - Optional callback to refresh tools list
 */
export function showToolsModal(tools, onRefresh = null) {
    const toolsList = document.getElementById('tools-list');
    const toolsModal = document.getElementById('tools-modal');
    const refreshBtn = document.getElementById('tools-refresh-btn');
    const searchInput = document.getElementById('tools-search-input');
    const countLabel = document.getElementById('tools-count-label');

    if (!toolsList || !toolsModal) {
        console.error('Tools modal elements not found');
        return;
    }

    // Store tools for filtering
    let currentTools = tools;
    const totalCount = tools?.length || 0;

    // Helper to update count label
    const updateCountLabel = (filteredCount, isFiltered) => {
        if (countLabel) {
            if (isFiltered) {
                countLabel.textContent = `${filteredCount} of ${totalCount} Available Tools`;
            } else {
                countLabel.textContent = `${totalCount} Available Tools`;
            }
        }
    };

    // Render tools list
    renderToolsList(toolsList, currentTools);
    updateCountLabel(totalCount, false);

    // Set up search input
    if (searchInput) {
        searchInput.value = '';
        searchInput.oninput = () => {
            const query = searchInput.value.toLowerCase().trim();
            if (!query) {
                renderToolsList(toolsList, currentTools);
                updateCountLabel(currentTools.length, false);
            } else {
                const filtered = currentTools.filter(tool => {
                    const name = (tool.name || '').toLowerCase();
                    const description = (tool.description || '').toLowerCase();
                    return name.includes(query) || description.includes(query);
                });
                renderToolsList(toolsList, filtered);
                updateCountLabel(filtered.length, true);
            }
        };
    }

    // Set up refresh button
    if (refreshBtn && onRefresh) {
        refreshBtn.classList.remove('d-none');
        refreshBtn.onclick = async () => {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Refreshing...';
            try {
                const newTools = await onRefresh();
                currentTools = newTools;
                // Re-apply filter if there's a search query
                if (searchInput && searchInput.value.trim()) {
                    searchInput.dispatchEvent(new Event('input'));
                } else {
                    renderToolsList(toolsList, currentTools);
                    updateCountLabel(currentTools.length, false);
                }
                showToast('Tools refreshed', 'success');
            } finally {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Refresh';
            }
        };
    } else if (refreshBtn) {
        refreshBtn.classList.add('d-none');
    }

    // Focus search input when modal opens
    toolsModal.addEventListener(
        'shown.bs.modal',
        () => {
            if (searchInput) {
                searchInput.focus();
            }
        },
        { once: true }
    );

    const modal = new bootstrap.Modal(toolsModal);
    modal.show();
}

/**
 * Render tools list into container
 * @param {HTMLElement} container - The container element
 * @param {Array} tools - Array of tool objects
 */
function renderToolsList(container, tools) {
    container.innerHTML = '';

    if (!tools || tools.length === 0) {
        container.innerHTML = '<p class="text-muted">No tools available</p>';
        return;
    }

    tools.forEach(tool => {
        const item = document.createElement('div');
        item.className = 'tool-item';
        const displayName = formatToolName(tool.name);

        // Parse description as markdown
        const descriptionHtml = tool.description ? marked.parse(tool.description) : '';

        item.innerHTML = `
            <div class="tool-header">
                <span>🔧</span>
                <span class="tool-name">${escapeHtml(displayName)}</span>
            </div>
            <div class="tool-description markdown-content">${descriptionHtml}</div>
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
        container.appendChild(item);
    });
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

/**
 * Convert an operation_id/tool name to a human-friendly format.
 *
 * Examples:
 * - "create_menu_item_api_menu_post" -> "Create Menu Item"
 * - "get_user_by_id_api_users__user_id__get" -> "Get User By Id"
 * - "listAllOrders" -> "List All Orders"
 *
 * @param {string} name - The operation ID or tool name
 * @returns {string} Human-friendly name
 */
function formatToolName(name) {
    if (!name) return 'Unknown Tool';

    // If it's a full tool ID (source_id:operation_id), extract operation_id
    if (name.includes(':')) {
        name = name.split(':').pop();
    }

    // Remove common suffixes like _api_*, _get, _post, _put, _delete, _patch
    let cleanName = name
        .replace(/_api_[a-z_]+_(get|post|put|delete|patch)$/i, '')
        .replace(/_(get|post|put|delete|patch)$/i, '')
        .replace(/^(get|post|put|delete|patch)_/i, '');

    // Handle camelCase
    cleanName = cleanName.replace(/([a-z])([A-Z])/g, '$1_$2');

    // Split by underscores, dashes, or double underscores
    const words = cleanName
        .split(/[_\-]+/)
        .filter(word => word.length > 0)
        .filter(word => !['api', 'v1', 'v2'].includes(word.toLowerCase()));

    // Capitalize each word
    const formattedWords = words.map(word => {
        // Handle common abbreviations
        const upperWords = ['id', 'url', 'api', 'uuid', 'mcp'];
        if (upperWords.includes(word.toLowerCase())) {
            return word.toUpperCase();
        }
        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    });

    return formattedWords.join(' ') || 'Unknown Tool';
}

/**
 * Show the health check modal and run health check
 * @param {Function} healthCheckFn - Async function that returns health status
 */
export async function showHealthModal(healthCheckFn) {
    const healthModal = document.getElementById('health-modal');
    const healthContent = document.getElementById('health-content');
    const healthRefreshBtn = document.getElementById('health-refresh-btn');

    if (!healthModal || !healthContent) {
        console.error('Health modal elements not found');
        return;
    }

    // Show loading state
    healthContent.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Checking services...</span>
            </div>
            <p class="mt-3 text-muted">Checking services...</p>
        </div>
    `;

    // Show modal
    const modal = new bootstrap.Modal(healthModal);
    modal.show();

    // Run health check
    await runHealthCheck(healthCheckFn, healthContent);

    // Set up refresh button
    if (healthRefreshBtn) {
        healthRefreshBtn.onclick = async () => {
            healthRefreshBtn.disabled = true;
            healthRefreshBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i>';
            await runHealthCheck(healthCheckFn, healthContent);
            healthRefreshBtn.disabled = false;
            healthRefreshBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i>';
        };
    }
}

/**
 * Run health check and render results
 * @param {Function} healthCheckFn - Async function that returns health status
 * @param {HTMLElement} container - Container to render results into
 */
async function runHealthCheck(healthCheckFn, container) {
    try {
        const health = await healthCheckFn();
        renderHealthStatus(container, health);
    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <strong>Health check failed:</strong> ${escapeHtml(error.message)}
            </div>
        `;
    }
}

/**
 * Render health status into container
 * @param {HTMLElement} container - Container element
 * @param {Object} health - Health status object from SystemHealthResponse
 */
function renderHealthStatus(container, health) {
    const statusIcon = {
        healthy: '<i class="bi bi-check-circle-fill text-success"></i>',
        degraded: '<i class="bi bi-exclamation-triangle-fill text-warning"></i>',
        unhealthy: '<i class="bi bi-x-circle-fill text-danger"></i>',
        unknown: '<i class="bi bi-question-circle-fill text-secondary"></i>',
    };

    const componentIcon = {
        healthy: 'bi-check-circle-fill text-success',
        degraded: 'bi-exclamation-triangle-fill text-warning',
        unhealthy: 'bi-x-circle-fill text-danger',
        unknown: 'bi-question-circle-fill text-secondary',
    };

    const componentsHtml = health.components
        .map(comp => {
            const icon = componentIcon[comp.status] || componentIcon.unknown;
            const latencyBadge = comp.latency_ms !== null && comp.latency_ms !== undefined ? `<span class="badge bg-secondary ms-2">${comp.latency_ms.toFixed(0)}ms</span>` : '';

            // Build details section if there are details
            let detailsHtml = '';
            if (comp.details) {
                const detailItems = Object.entries(comp.details)
                    .filter(([key]) => key !== 'version')
                    .map(([key, value]) => `<span class="badge bg-light text-dark me-1">${escapeHtml(key)}: ${escapeHtml(String(value))}</span>`)
                    .join('');
                if (detailItems) {
                    detailsHtml = `<div class="mt-1">${detailItems}</div>`;
                }
            }

            return `
                <div class="health-component ${comp.status}">
                    <div class="d-flex align-items-center justify-content-between">
                        <div class="d-flex align-items-center">
                            <i class="bi ${icon} me-2"></i>
                            <span class="component-name">${escapeHtml(comp.name)}</span>
                        </div>
                        <div>
                            <span class="badge ${comp.status === 'healthy' ? 'bg-success' : comp.status === 'degraded' ? 'bg-warning' : comp.status === 'unknown' ? 'bg-secondary' : 'bg-danger'}">
                                ${comp.status}
                            </span>
                            ${latencyBadge}
                        </div>
                    </div>
                    <p class="text-muted small mb-0 mt-1">${escapeHtml(comp.message)}</p>
                    ${detailsHtml}
                </div>
            `;
        })
        .join('');

    // Map overall_status to display format
    const status = health.overall_status;
    const overallStatusClass = status === 'healthy' ? 'success' : status === 'degraded' ? 'warning' : status === 'unknown' ? 'secondary' : 'danger';

    container.innerHTML = `
        <div class="health-overview mb-3">
            <div class="d-flex align-items-center justify-content-between p-3 bg-${overallStatusClass} bg-opacity-10 rounded">
                <div class="d-flex align-items-center">
                    ${statusIcon[status] || statusIcon.unknown}
                    <span class="ms-2 fw-bold">${escapeHtml(health.message)}</span>
                </div>
                <span class="badge bg-${overallStatusClass} fs-6">${status.toUpperCase()}</span>
            </div>
        </div>
        <div class="health-chain">
            <h6 class="text-muted mb-3">
                <i class="bi bi-diagram-3 me-1"></i>
                Service Chain
            </h6>
            <div class="health-components">
                ${componentsHtml}
            </div>
        </div>
        <p class="text-muted small mt-3 mb-0">
            <i class="bi bi-clock me-1"></i>
            Checked: ${new Date(health.checked_at).toLocaleString()}
        </p>
    `;
}

/**
 * Show the conversation info modal with statistics
 * @param {Object} conversation - Conversation object with messages
 * @param {string} conversation.id - Conversation ID
 * @param {string} conversation.title - Conversation title
 * @param {Array} conversation.messages - Array of messages
 * @param {string} conversation.created_at - ISO timestamp
 * @param {string} conversation.updated_at - ISO timestamp
 */
export function showConversationInfoModal(conversation) {
    const modal = document.getElementById('conversation-info-modal');
    const contentEl = document.getElementById('conversation-info-content');

    if (!modal || !contentEl) {
        console.error('Conversation info modal elements not found');
        return;
    }

    // Calculate statistics
    const messages = conversation.messages || [];
    const userMessages = messages.filter(m => m.role === 'user');
    const assistantMessages = messages.filter(m => m.role === 'assistant');

    // Token estimation (rough: ~4 chars per token)
    let totalChars = 0;
    let totalToolCalls = 0;
    const toolsUsed = new Set();

    messages.forEach(msg => {
        if (msg.content) {
            totalChars += msg.content.length;
        }
        if (msg.tool_calls && msg.tool_calls.length > 0) {
            totalToolCalls += msg.tool_calls.length;
            msg.tool_calls.forEach(tc => {
                if (tc.name) toolsUsed.add(tc.name);
            });
        }
        if (msg.tool_results && msg.tool_results.length > 0) {
            totalToolCalls = Math.max(totalToolCalls, msg.tool_results.length);
            msg.tool_results.forEach(tr => {
                if (tr.name) toolsUsed.add(tr.name);
            });
        }
    });

    const estimatedTokens = Math.round(totalChars / 4);
    const totalBytes = new Blob([messages.map(m => m.content || '').join('')]).size;

    // Format dates
    const createdDate = conversation.created_at ? new Date(conversation.created_at).toLocaleString() : 'Unknown';
    const updatedDate = conversation.updated_at ? new Date(conversation.updated_at).toLocaleString() : 'Unknown';

    // Build tools list HTML
    let toolsHtml = '';
    if (toolsUsed.size > 0) {
        const toolBadges = Array.from(toolsUsed)
            .map(tool => `<span class="badge bg-info bg-opacity-10 text-info me-1 mb-1">${escapeHtml(formatToolName(tool))}</span>`)
            .join('');
        toolsHtml = `
            <div class="mt-3">
                <h6 class="text-secondary mb-2"><i class="bi bi-tools me-1"></i>Tools Used (${toolsUsed.size})</h6>
                <div class="d-flex flex-wrap">${toolBadges}</div>
            </div>
        `;
    }

    contentEl.innerHTML = `
        <div class="conversation-info">
            <h6 class="border-bottom pb-2 mb-3">${escapeHtml(conversation.title || 'Untitled Conversation')}</h6>

            <div class="row g-3 mb-3">
                <div class="col-6">
                    <div class="stat-card p-3 rounded bg-body-secondary">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-chat-dots text-primary fs-4 me-2"></i>
                            <div>
                                <div class="stat-value fs-5 fw-bold">${messages.length}</div>
                                <div class="stat-label text-muted small">Total Messages</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="stat-card p-3 rounded bg-body-secondary">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-coin text-warning fs-4 me-2"></i>
                            <div>
                                <div class="stat-value fs-5 fw-bold">~${estimatedTokens.toLocaleString()}</div>
                                <div class="stat-label text-muted small">Est. Tokens</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="stat-card p-3 rounded bg-body-secondary">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-person text-success fs-4 me-2"></i>
                            <div>
                                <div class="stat-value fs-5 fw-bold">${userMessages.length}</div>
                                <div class="stat-label text-muted small">User Messages</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="stat-card p-3 rounded bg-body-secondary">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-robot text-info fs-4 me-2"></i>
                            <div>
                                <div class="stat-value fs-5 fw-bold">${assistantMessages.length}</div>
                                <div class="stat-label text-muted small">Assistant Messages</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="details-section">
                <div class="d-flex justify-content-between text-muted small mb-2">
                    <span><i class="bi bi-file-binary me-1"></i>Size</span>
                    <span>${formatBytes(totalBytes)}</span>
                </div>
                <div class="d-flex justify-content-between text-muted small mb-2">
                    <span><i class="bi bi-gear me-1"></i>Tool Calls</span>
                    <span>${totalToolCalls}</span>
                </div>
                <div class="d-flex justify-content-between text-muted small mb-2">
                    <span><i class="bi bi-calendar-plus me-1"></i>Created</span>
                    <span>${createdDate}</span>
                </div>
                <div class="d-flex justify-content-between text-muted small">
                    <span><i class="bi bi-calendar-check me-1"></i>Last Updated</span>
                    <span>${updatedDate}</span>
                </div>
            </div>

            ${toolsHtml}

            <div class="mt-3 pt-3 border-top">
                <small class="text-muted">
                    <i class="bi bi-hash me-1"></i>ID: <code>${escapeHtml(conversation.id)}</code>
                </small>
            </div>
        </div>
    `;

    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Format bytes to human readable string
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Show the tool details modal with tabbed interface
 * @param {Array} toolCalls - Array of tool call objects (requests)
 * @param {Array} toolResults - Array of tool result objects (responses)
 * @param {Object} options - Additional options
 * @param {boolean} options.isAdmin - Whether the current user has admin role
 * @param {Function} options.fetchSourceInfo - Async function to fetch source info for a tool
 */
export function showToolDetailsModal(toolCalls, toolResults, options = {}) {
    const toolDetailsModal = document.getElementById('tool-details-modal');
    const toolCallContent = document.getElementById('tool-call-content');
    const sourceInfoContent = document.getElementById('source-info-content');
    const sourceInfoTabItem = document.getElementById('source-info-tab-item');
    const sourceInfoTab = document.getElementById('source-info-tab');

    if (!toolDetailsModal || !toolCallContent) {
        console.error('Tool details modal elements not found');
        return;
    }

    // Combine tool calls and results for display
    const toolExecutions = [];

    // Process tool results (these have execution data)
    if (toolResults && toolResults.length > 0) {
        toolResults.forEach(tr => {
            toolExecutions.push({
                toolName: tr.tool_name,
                callId: tr.call_id,
                success: tr.success,
                result: tr.result,
                error: tr.error,
                executionTime: tr.execution_time_ms,
                hasResult: true,
            });
        });
    }

    // Process tool calls that don't have corresponding results
    if (toolCalls && toolCalls.length > 0) {
        toolCalls.forEach(tc => {
            // Check if this call already has a result
            const hasResult = toolExecutions.some(te => te.callId === tc.call_id);
            if (!hasResult) {
                toolExecutions.push({
                    toolName: tc.tool_name,
                    callId: tc.call_id,
                    arguments: tc.arguments,
                    success: null, // Pending
                    hasResult: false,
                });
            }
        });
    }

    // Render the tool call content
    toolCallContent.innerHTML = renderToolDetails(toolExecutions);

    // Handle Source Info tab visibility (admin only)
    const isAdmin = options.isAdmin || false;
    const fetchSourceInfo = options.fetchSourceInfo || null;

    if (isAdmin && sourceInfoTabItem && sourceInfoTab && sourceInfoContent) {
        sourceInfoTabItem.classList.remove('d-none');

        // Reset source info content to loading state
        sourceInfoContent.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2 text-muted small">Loading source information...</p>
            </div>
        `;

        // Track if source info has been loaded
        let sourceInfoLoaded = false;

        // Remove any existing event listeners by cloning the element
        const newSourceInfoTab = sourceInfoTab.cloneNode(true);
        sourceInfoTab.parentNode.replaceChild(newSourceInfoTab, sourceInfoTab);

        // Set up lazy loading when tab is shown
        const loadSourceInfo = async () => {
            if (sourceInfoLoaded || !fetchSourceInfo) return;

            sourceInfoLoaded = true;

            // Get unique tool names to fetch source info for
            const toolNames = [...new Set(toolExecutions.map(te => te.toolName))];

            try {
                const sourceInfos = await Promise.all(
                    toolNames.map(async toolName => {
                        try {
                            const info = await fetchSourceInfo(toolName);
                            return { toolName, info, error: null };
                        } catch (err) {
                            return { toolName, info: null, error: err.message };
                        }
                    })
                );

                sourceInfoContent.innerHTML = renderSourceInfo(sourceInfos);
            } catch (err) {
                sourceInfoContent.innerHTML = `
                    <div class="alert alert-danger" role="alert">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Failed to load source information: ${escapeHtml(err.message)}
                    </div>
                `;
            }
        };

        // Listen for tab shown event
        newSourceInfoTab.addEventListener('shown.bs.tab', loadSourceInfo, { once: true });
    } else if (sourceInfoTabItem) {
        // Hide source info tab for non-admin users
        sourceInfoTabItem.classList.add('d-none');
    }

    // Reset to first tab
    const toolCallTab = document.getElementById('tool-call-tab');
    if (toolCallTab) {
        const tabInstance = new bootstrap.Tab(toolCallTab);
        tabInstance.show();
    }

    // Show modal
    const modal = new bootstrap.Modal(toolDetailsModal);
    modal.show();
}

/**
 * Render source info for tools
 * @param {Array} sourceInfos - Array of {toolName, info, error} objects
 * @returns {string} HTML string
 */
function renderSourceInfo(sourceInfos) {
    if (!sourceInfos || sourceInfos.length === 0) {
        return '<p class="text-muted">No source information available.</p>';
    }

    return sourceInfos
        .map((item, index) => {
            if (item.error) {
                return `
                    <div class="source-info-card ${index > 0 ? 'mt-4 pt-4 border-top' : ''}">
                        <h6 class="fw-bold text-danger">
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            ${escapeHtml(item.toolName)}
                        </h6>
                        <p class="text-muted small">Failed to load source info: ${escapeHtml(item.error)}</p>
                    </div>
                `;
            }

            const info = item.info;
            const statusBadge =
                info.health_status === 'healthy'
                    ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Healthy</span>'
                    : info.health_status === 'degraded'
                      ? '<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle me-1"></i>Degraded</span>'
                      : '<span class="badge bg-danger"><i class="bi bi-x-circle me-1"></i>Unhealthy</span>';

            const enabledBadge = info.is_enabled
                ? '<span class="badge bg-success ms-2"><i class="bi bi-toggle-on me-1"></i>Enabled</span>'
                : '<span class="badge bg-secondary ms-2"><i class="bi bi-toggle-off me-1"></i>Disabled</span>';

            return `
                <div class="source-info-card ${index > 0 ? 'mt-4 pt-4 border-top' : ''}">
                    <div class="d-flex align-items-center justify-content-between mb-3">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-cloud text-primary me-2 fs-5"></i>
                            <h6 class="mb-0 fw-bold">${escapeHtml(item.toolName)}</h6>
                        </div>
                        <div>
                            ${statusBadge}
                            ${enabledBadge}
                        </div>
                    </div>

                    <table class="table table-sm table-borderless mb-0">
                        <tbody>
                            <tr>
                                <td class="text-muted" style="width: 140px;"><i class="bi bi-tag me-2"></i>Source Name</td>
                                <td><strong>${escapeHtml(info.source_name)}</strong></td>
                            </tr>
                            <tr>
                                <td class="text-muted"><i class="bi bi-link-45deg me-2"></i>Source URL</td>
                                <td>
                                    <a href="${escapeHtml(info.source_url)}" target="_blank" rel="noopener noreferrer" class="text-decoration-none">
                                        ${escapeHtml(info.source_url)}
                                        <i class="bi bi-box-arrow-up-right ms-1 small"></i>
                                    </a>
                                </td>
                            </tr>
                            ${
                                info.openapi_url
                                    ? `
                            <tr>
                                <td class="text-muted"><i class="bi bi-file-earmark-text me-2"></i>OpenAPI URL</td>
                                <td>
                                    <a href="${escapeHtml(info.openapi_url)}" target="_blank" rel="noopener noreferrer" class="text-decoration-none">
                                        ${escapeHtml(info.openapi_url)}
                                        <i class="bi bi-box-arrow-up-right ms-1 small"></i>
                                    </a>
                                </td>
                            </tr>
                            `
                                    : ''
                            }
                            <tr>
                                <td class="text-muted"><i class="bi bi-file-earmark-code me-2"></i>Source Type</td>
                                <td><code>${escapeHtml(info.source_type)}</code></td>
                            </tr>
                            ${
                                info.default_audience
                                    ? `
                            <tr>
                                <td class="text-muted"><i class="bi bi-person-badge me-2"></i>Audience</td>
                                <td><code>${escapeHtml(info.default_audience)}</code></td>
                            </tr>
                            `
                                    : ''
                            }
                            <tr>
                                <td class="text-muted"><i class="bi bi-tools me-2"></i>Tool Count</td>
                                <td>${info.tool_count || 0} tools</td>
                            </tr>
                            ${
                                info.last_sync_at
                                    ? `
                            <tr>
                                <td class="text-muted"><i class="bi bi-clock-history me-2"></i>Last Sync</td>
                                <td>${formatDateTime(info.last_sync_at)}</td>
                            </tr>
                            `
                                    : ''
                            }
                        </tbody>
                    </table>
                </div>
            `;
        })
        .join('');
}

/**
 * Format ISO datetime string to human-readable format
 * @param {string} isoString - ISO 8601 datetime string
 * @returns {string} Formatted datetime string
 */
function formatDateTime(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

/**
 * Render tool execution details
 * @param {Array} toolExecutions - Array of tool execution objects
 * @returns {string} HTML string
 */
function renderToolDetails(toolExecutions) {
    if (!toolExecutions || toolExecutions.length === 0) {
        return '<p class="text-muted">No tool execution details available.</p>';
    }

    return toolExecutions
        .map((exec, index) => {
            // Check for insufficient_scope error
            const isInsufficientScope =
                exec.error &&
                (exec.error.includes('insufficient_scope') || exec.error.includes('Insufficient scope') || (typeof exec.result === 'object' && exec.result?.error === 'insufficient_scope'));

            const statusBadge = exec.hasResult
                ? exec.success
                    ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Success</span>'
                    : isInsufficientScope
                      ? '<span class="badge bg-warning text-dark"><i class="bi bi-lock-fill me-1"></i>Access Denied</span>'
                      : '<span class="badge bg-danger"><i class="bi bi-x-circle me-1"></i>Failed</span>'
                : '<span class="badge bg-secondary"><i class="bi bi-hourglass-split me-1"></i>Pending</span>';

            const executionTime = exec.executionTime ? `<span class="badge bg-info text-dark ms-2"><i class="bi bi-stopwatch me-1"></i>${exec.executionTime.toFixed(0)}ms</span>` : '';

            // Format the result/error for display
            let resultContent = '';
            if (exec.hasResult) {
                if (exec.success && exec.result !== undefined) {
                    try {
                        const formatted = typeof exec.result === 'string' ? exec.result : JSON.stringify(exec.result, null, 2);
                        resultContent = `
                            <div class="mt-3">
                                <h6 class="text-success mb-2"><i class="bi bi-box-arrow-in-down me-1"></i>Result</h6>
                                <pre class="bg-dark text-light p-3 rounded small" style="max-height: 300px; overflow: auto;"><code>${escapeHtml(formatted)}</code></pre>
                            </div>
                        `;
                    } catch (e) {
                        resultContent = `<div class="mt-3 text-muted">Result data could not be formatted.</div>`;
                    }
                } else if (exec.error) {
                    // Check if this is an insufficient_scope error and format accordingly
                    if (isInsufficientScope) {
                        // Try to extract missing scopes from the error message
                        let missingScopes = [];
                        const scopeMatch = exec.error.match(/missing[:\s]+\[?([^\]]+)\]?/i) || exec.error.match(/required[:\s]+\[?([^\]]+)\]?/i) || exec.error.match(/scopes?[:\s]+\[?([^\]]+)\]?/i);
                        if (scopeMatch) {
                            missingScopes = scopeMatch[1]
                                .split(',')
                                .map(s => s.trim().replace(/['"]/g, ''))
                                .filter(Boolean);
                        }

                        resultContent = `
                            <div class="mt-3">
                                <div class="alert alert-warning mb-0">
                                    <h6 class="alert-heading mb-2"><i class="bi bi-lock-fill me-2"></i>Permission Required</h6>
                                    <p class="mb-2">You don't have sufficient permissions to execute this tool.</p>
                                    ${
                                        missingScopes.length > 0
                                            ? `
                                        <p class="mb-2"><strong>Required scopes:</strong></p>
                                        <div class="mb-2">
                                            ${missingScopes.map(s => `<span class="badge bg-secondary me-1">${escapeHtml(s)}</span>`).join('')}
                                        </div>
                                    `
                                            : ''
                                    }
                                    <hr>
                                    <p class="mb-0 small text-muted">
                                        <i class="bi bi-info-circle me-1"></i>
                                        Contact your administrator to request access to this tool.
                                    </p>
                                </div>
                            </div>
                        `;
                    } else {
                        resultContent = `
                            <div class="mt-3">
                                <h6 class="text-danger mb-2"><i class="bi bi-exclamation-triangle me-1"></i>Error</h6>
                                <pre class="bg-danger bg-opacity-10 text-danger p-3 rounded small">${escapeHtml(exec.error)}</pre>
                            </div>
                        `;
                    }
                }
            }

            // Format arguments if present
            let argsContent = '';
            if (exec.arguments) {
                try {
                    const formatted = typeof exec.arguments === 'string' ? exec.arguments : JSON.stringify(exec.arguments, null, 2);
                    argsContent = `
                        <div class="mt-3">
                            <h6 class="text-secondary mb-2"><i class="bi bi-box-arrow-up me-1"></i>Arguments</h6>
                            <pre class="bg-secondary bg-opacity-10 p-3 rounded small" style="max-height: 150px; overflow: auto;"><code>${escapeHtml(formatted)}</code></pre>
                        </div>
                    `;
                } catch (e) {
                    // Ignore formatting errors
                }
            }

            return `
                <div class="tool-execution-card ${index > 0 ? 'mt-4 pt-4 border-top' : ''}">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-gear-wide-connected text-primary me-2 fs-5"></i>
                            <h6 class="mb-0 fw-bold">${escapeHtml(exec.toolName)}</h6>
                        </div>
                        <div>
                            ${statusBadge}
                            ${executionTime}
                        </div>
                    </div>
                    ${exec.callId ? `<p class="text-muted small mb-0"><i class="bi bi-hash me-1"></i>Call ID: <code>${escapeHtml(exec.callId)}</code></p>` : ''}
                    ${argsContent}
                    ${resultContent}
                </div>
            `;
        })
        .join('');
}

/**
 * Show the share conversation modal
 * @param {Object} conversation - Conversation object with messages
 * @param {string} conversation.id - Conversation ID
 * @param {string} conversation.title - Conversation title
 * @param {Array} conversation.messages - Array of messages
 */
export function showShareModal(conversation) {
    const modal = document.getElementById('share-modal');
    const contentEl = document.getElementById('share-content');

    if (!modal || !contentEl) {
        console.error('Share modal elements not found');
        return;
    }

    // Generate conversation export
    const exportData = {
        title: conversation.title || 'Untitled Conversation',
        exported_at: new Date().toISOString(),
        message_count: conversation.messages?.length || 0,
        messages: (conversation.messages || []).map(msg => ({
            role: msg.role,
            content: msg.content,
            created_at: msg.created_at,
        })),
    };

    const jsonExport = JSON.stringify(exportData, null, 2);
    const textExport = (conversation.messages || []).map(msg => `[${msg.role?.toUpperCase() || 'UNKNOWN'}]\n${msg.content || ''}\n`).join('\n---\n\n');

    contentEl.innerHTML = `
        <div class="share-content">
            <div class="alert alert-info mb-3">
                <i class="bi bi-info-circle me-2"></i>
                <strong>Share Options</strong>
                <p class="mb-0 mt-2 small">Export this conversation to share with others. Direct sharing with specific users will be available in a future update.</p>
            </div>

            <h6 class="text-secondary mb-3">${escapeHtml(conversation.title || 'Untitled Conversation')}</h6>

            <div class="d-grid gap-2">
                <button type="button" class="btn btn-outline-primary share-btn" data-format="json">
                    <i class="bi bi-filetype-json me-2"></i>
                    Copy as JSON
                </button>
                <button type="button" class="btn btn-outline-primary share-btn" data-format="text">
                    <i class="bi bi-file-text me-2"></i>
                    Copy as Text
                </button>
                <button type="button" class="btn btn-outline-secondary share-btn" data-format="download">
                    <i class="bi bi-download me-2"></i>
                    Download JSON
                </button>
            </div>

            <div class="mt-3 pt-3 border-top">
                <p class="text-muted small mb-0">
                    <i class="bi bi-shield-check me-1"></i>
                    Conversation data is not stored externally. Sharing creates a local copy.
                </p>
            </div>
        </div>
    `;

    // Bind button events
    const shareButtons = contentEl.querySelectorAll('.share-btn');
    shareButtons.forEach(btn => {
        btn.addEventListener('click', async () => {
            const format = btn.dataset.format;

            try {
                if (format === 'json') {
                    await navigator.clipboard.writeText(jsonExport);
                    showToast('Conversation copied as JSON', 'success');
                } else if (format === 'text') {
                    await navigator.clipboard.writeText(textExport);
                    showToast('Conversation copied as text', 'success');
                } else if (format === 'download') {
                    // Download as JSON file
                    const blob = new Blob([jsonExport], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `conversation-${conversation.id || 'export'}.json`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    showToast('Conversation downloaded', 'success');
                }

                // Close modal after action
                bootstrap.Modal.getInstance(modal)?.hide();
            } catch (error) {
                console.error('Share action failed:', error);
                showToast('Failed to share conversation', 'error');
            }
        });
    });

    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Show the user permissions modal
 * @param {Array} scopes - Array of scope strings from the user's token
 */
export function showPermissionsModal(scopes) {
    const modal = document.getElementById('permissions-modal');
    const contentEl = document.getElementById('permissions-content');

    if (!modal || !contentEl) {
        console.error('Permissions modal elements not found');
        return;
    }

    // Render the scopes
    if (!scopes || scopes.length === 0) {
        contentEl.innerHTML = `
            <div class="alert alert-info mb-0">
                <i class="bi bi-info-circle me-2"></i>
                No special permissions have been assigned to your account.
            </div>
        `;
    } else {
        // Group scopes by prefix for better organization
        const groupedScopes = {};
        scopes.forEach(scope => {
            // Split by : or . to group related scopes
            const parts = scope.split(/[:.]/);
            const prefix = parts.length > 1 ? parts[0] : 'general';
            if (!groupedScopes[prefix]) {
                groupedScopes[prefix] = [];
            }
            groupedScopes[prefix].push(scope);
        });

        const groupHtml = Object.entries(groupedScopes)
            .map(
                ([group, groupScopes]) => `
                <div class="mb-3">
                    <h6 class="text-muted text-uppercase small mb-2">
                        <i class="bi bi-folder me-1"></i>${escapeHtml(group)}
                    </h6>
                    <div class="d-flex flex-wrap gap-2">
                        ${groupScopes.map(s => `<span class="badge bg-info text-dark">${escapeHtml(s)}</span>`).join('')}
                    </div>
                </div>
            `
            )
            .join('');

        contentEl.innerHTML = `
            <p class="text-muted mb-3">
                You have been granted the following permissions:
            </p>
            ${groupHtml}
            <div class="mt-3 pt-3 border-top">
                <p class="text-muted small mb-0">
                    <strong>Total:</strong> ${scopes.length} permission${scopes.length !== 1 ? 's' : ''}
                </p>
            </div>
        `;
    }

    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

export default {
    initModals,
    showRenameModal,
    showDeleteModal,
    showToolsModal,
    showToast,
    showHealthModal,
    showToolDetailsModal,
    showConversationInfoModal,
    showShareModal,
    showPermissionsModal,
};
