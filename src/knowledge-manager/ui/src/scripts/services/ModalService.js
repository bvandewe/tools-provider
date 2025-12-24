/**
 * ModalService - Bootstrap Modal Management
 *
 * Provides centralized modal management and toast notifications.
 *
 * @module services/ModalService
 */

import * as bootstrap from 'bootstrap';

/**
 * ModalService manages Bootstrap modals and toast notifications
 */
export class ModalService {
    /**
     * Create a new ModalService instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Map<string, bootstrap.Modal>} */
        this._modals = new Map();

        /** @type {HTMLElement|null} */
        this._toastContainer = null;
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize the modal service
     */
    init() {
        if (this._initialized) {
            console.warn('[ModalService] Already initialized');
            return;
        }

        // Create toast container if not exists
        this._toastContainer = document.querySelector('.toast-container');
        if (!this._toastContainer) {
            this._toastContainer = document.createElement('div');
            this._toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(this._toastContainer);
        }

        this._initialized = true;
        console.log('[ModalService] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._modals.forEach(modal => {
            modal.dispose();
        });
        this._modals.clear();
        this._initialized = false;
        console.log('[ModalService] Destroyed');
    }

    // =========================================================================
    // Modal Management
    // =========================================================================

    /**
     * Get or create a Bootstrap modal instance
     * @param {string} modalId - Modal element ID
     * @returns {bootstrap.Modal|null}
     */
    getModal(modalId) {
        if (this._modals.has(modalId)) {
            return this._modals.get(modalId);
        }

        const element = document.getElementById(modalId);
        if (!element) {
            console.warn(`[ModalService] Modal element not found: ${modalId}`);
            return null;
        }

        const modal = new bootstrap.Modal(element);
        this._modals.set(modalId, modal);
        return modal;
    }

    /**
     * Show a modal
     * @param {string} modalId - Modal element ID
     */
    show(modalId) {
        const modal = this.getModal(modalId);
        if (modal) {
            modal.show();
        }
    }

    /**
     * Hide a modal
     * @param {string} modalId - Modal element ID
     */
    hide(modalId) {
        const modal = this.getModal(modalId);
        if (modal) {
            modal.hide();
        }
    }

    // =========================================================================
    // Toast Notifications
    // =========================================================================

    /**
     * Show a toast notification
     * @param {string} message - Toast message
     * @param {string} [type='info'] - Bootstrap color type (success, danger, warning, info)
     * @param {number} [duration=4000] - Auto-hide delay in ms
     */
    showToast(message, type = 'info', duration = 4000) {
        if (!this._toastContainer) {
            console.warn('[ModalService] Toast container not initialized');
            return;
        }

        const toastId = `toast-${Date.now()}`;
        const toastHtml = `
            <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;

        this._toastContainer.insertAdjacentHTML('beforeend', toastHtml);

        const toastEl = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: duration });

        toast.show();

        toastEl.addEventListener('hidden.bs.toast', () => {
            toastEl.remove();
        });
    }

    /**
     * Show a success toast
     * @param {string} message - Toast message
     */
    success(message) {
        this.showToast(message, 'success');
    }

    /**
     * Show an error toast
     * @param {string} message - Toast message
     */
    error(message) {
        this.showToast(message, 'danger');
    }

    /**
     * Show a warning toast
     * @param {string} message - Toast message
     */
    warning(message) {
        this.showToast(message, 'warning');
    }

    /**
     * Show an info toast
     * @param {string} message - Toast message
     */
    info(message) {
        this.showToast(message, 'info');
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const modalService = new ModalService();

/**
 * Convenience function for backward compatibility
 * @param {string} message - Toast message
 * @param {string} [type='info'] - Toast type
 */
export function showToast(message, type = 'info') {
    modalService.showToast(message, type);
}
