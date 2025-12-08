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
 * @param {Function} onRefresh - Optional callback to refresh tools list
 */
export function showToolsModal(tools, onRefresh = null) {
    const toolsList = document.getElementById('tools-list');
    const toolsModal = document.getElementById('tools-modal');
    const refreshBtn = document.getElementById('tools-refresh-btn');

    if (!toolsList || !toolsModal) {
        console.error('Tools modal elements not found');
        return;
    }

    // Render tools list
    renderToolsList(toolsList, tools);

    // Set up refresh button
    if (refreshBtn && onRefresh) {
        refreshBtn.classList.remove('d-none');
        refreshBtn.onclick = async () => {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Refreshing...';
            try {
                const newTools = await onRefresh();
                renderToolsList(toolsList, newTools);
                showToast('Tools refreshed', 'success');
            } finally {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Refresh';
            }
        };
    } else if (refreshBtn) {
        refreshBtn.classList.add('d-none');
    }

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

export default {
    initModals,
    showRenameModal,
    showDeleteModal,
    showToolsModal,
    showToast,
    showHealthModal,
};
