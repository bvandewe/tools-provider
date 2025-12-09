/**
 * Toast Notification Component
 *
 * A simple toast notification system using Bootstrap toasts.
 *
 * Usage:
 *   import { showToast } from './toast-notification.js';
 *   showToast('success', 'Item saved successfully');
 *   showToast('error', 'Failed to save item');
 */

import * as bootstrap from 'bootstrap';

const TOAST_CONTAINER_ID = 'toast-container';

class ToastNotification extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        this.render();
    }

    render() {
        const type = this.getAttribute('type') || 'info';
        const message = this.getAttribute('message') || '';
        const title = this.getAttribute('title') || this._getDefaultTitle(type);

        const { bgClass, icon } = this._getTypeStyles(type);

        this.innerHTML = `
            <div class="toast" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header ${bgClass} text-white">
                    <i class="bi ${icon} me-2"></i>
                    <strong class="me-auto">${this._escapeHtml(title)}</strong>
                    <small class="text-white-50">just now</small>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${this._escapeHtml(message)}
                </div>
            </div>
        `;

        // Initialize and show the toast
        const toastEl = this.querySelector('.toast');
        const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: 5000 });
        toast.show();

        // Remove element after toast hides
        toastEl.addEventListener('hidden.bs.toast', () => {
            this.remove();
        });
    }

    _getDefaultTitle(type) {
        const titles = {
            success: 'Success',
            error: 'Error',
            warning: 'Warning',
            info: 'Info',
        };
        return titles[type] || 'Notification';
    }

    _getTypeStyles(type) {
        const styles = {
            success: { bgClass: 'bg-success', icon: 'bi-check-circle-fill' },
            error: { bgClass: 'bg-danger', icon: 'bi-exclamation-circle-fill' },
            warning: { bgClass: 'bg-warning', icon: 'bi-exclamation-triangle-fill' },
            info: { bgClass: 'bg-info', icon: 'bi-info-circle-fill' },
        };
        return styles[type] || styles.info;
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

if (!customElements.get('toast-notification')) {
    customElements.define('toast-notification', ToastNotification);
}

/**
 * Get or create the toast container
 */
function getToastContainer() {
    let container = document.getElementById(TOAST_CONTAINER_ID);
    if (!container) {
        container = document.createElement('div');
        container.id = TOAST_CONTAINER_ID;
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1080';
        document.body.appendChild(container);
    }
    return container;
}

/**
 * Show a toast notification
 * @param {'success'|'error'|'warning'|'info'} type - The toast type
 * @param {string} message - The toast message
 * @param {string} [title] - Optional custom title
 */
export function showToast(type, message, title = '') {
    const container = getToastContainer();
    const toast = document.createElement('toast-notification');
    toast.setAttribute('type', type);
    toast.setAttribute('message', message);
    if (title) toast.setAttribute('title', title);
    container.appendChild(toast);
}

export { ToastNotification };
