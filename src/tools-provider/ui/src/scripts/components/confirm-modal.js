/**
 * Confirmation Modal Component
 *
 * A reusable confirmation dialog.
 *
 * Usage:
 *   import { confirm } from './confirm-modal.js';
 *   const confirmed = await confirm('Delete this item?', 'This action cannot be undone.');
 *   if (confirmed) { ... }
 */

import * as bootstrap from 'bootstrap';

class ConfirmModal extends HTMLElement {
    constructor() {
        super();
        this._modalInstance = null;
        this._resolvePromise = null;
        this._isShowing = false;
    }

    connectedCallback() {
        this.render();
    }

    render() {
        const title = this.getAttribute('title') || 'Confirm Action';
        const message = this.getAttribute('message') || 'Are you sure you want to proceed?';
        const confirmText = this.getAttribute('confirm-text') || 'Confirm';
        const cancelText = this.getAttribute('cancel-text') || 'Cancel';
        const variant = this.getAttribute('variant') || 'primary';

        const variantClass =
            {
                primary: 'btn-primary',
                danger: 'btn-danger',
                warning: 'btn-warning',
            }[variant] || 'btn-primary';

        const headerClass =
            {
                primary: '',
                danger: 'bg-danger text-white',
                warning: 'bg-warning text-dark',
            }[variant] || '';

        this.innerHTML = `
            <div class="modal fade" tabindex="-1" aria-labelledby="confirmModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header ${headerClass}">
                            <h5 class="modal-title" id="confirmModalLabel">${this._escapeHtml(title)}</h5>
                            <button type="button" class="btn-close ${variant === 'danger' ? 'btn-close-white' : ''}"
                                    data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <p class="mb-0">${this._escapeHtml(message)}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" id="cancel-btn">
                                ${this._escapeHtml(cancelText)}
                            </button>
                            <button type="button" class="btn ${variantClass}" id="confirm-btn">
                                ${this._escapeHtml(confirmText)}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        const modalEl = this.querySelector('.modal');

        // Create Bootstrap Modal instance
        this._modalInstance = new bootstrap.Modal(modalEl, {
            backdrop: 'static', // Prevent closing on backdrop click
            keyboard: false, // Prevent closing on Escape
        });

        // Event handlers for buttons
        this.querySelector('#confirm-btn').addEventListener('click', () => {
            this._resolve(true);
        });

        this.querySelector('#cancel-btn').addEventListener('click', () => {
            this._resolve(false);
        });

        // Close button in header
        this.querySelector('.btn-close').addEventListener('click', () => {
            this._resolve(false);
        });

        // Handle modal hidden event (for cleanup)
        modalEl.addEventListener('hidden.bs.modal', () => {
            // Only resolve if we haven't already (and we were showing)
            if (this._resolvePromise && this._isShowing) {
                this._resolvePromise(false);
                this._resolvePromise = null;
            }
            this._isShowing = false;
        });
    }

    show() {
        return new Promise(resolve => {
            this._resolvePromise = resolve;
            this._isShowing = true;
            this._modalInstance.show();
        });
    }

    _resolve(value) {
        if (this._resolvePromise) {
            const resolver = this._resolvePromise;
            this._resolvePromise = null;
            this._isShowing = false;
            this._modalInstance.hide();
            resolver(value);
        }
    }

    _escapeHtml(str) {
        if (str === null || str === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(str);
        return div.innerHTML;
    }
}

if (!customElements.get('confirm-modal')) {
    customElements.define('confirm-modal', ConfirmModal);
}

/**
 * Show a confirmation dialog and return a promise that resolves to true/false
 * @param {string} message - The confirmation message
 * @param {Object} options - Optional configuration
 * @returns {Promise<boolean>}
 */
export async function confirm(message, options = {}) {
    const { title = 'Confirm Action', confirmText = 'Confirm', cancelText = 'Cancel', variant = 'primary' } = options;

    const modal = document.createElement('confirm-modal');
    modal.setAttribute('title', title);
    modal.setAttribute('message', message);
    modal.setAttribute('confirm-text', confirmText);
    modal.setAttribute('cancel-text', cancelText);
    modal.setAttribute('variant', variant);
    document.body.appendChild(modal);

    // Wait a tick for connectedCallback to complete and Bootstrap Modal to initialize
    await new Promise(resolve => requestAnimationFrame(resolve));

    const result = await modal.show();

    // Cleanup after animation completes - ensure backdrop is removed
    setTimeout(() => {
        modal.remove();
        // Force cleanup any stray backdrops
        document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');
    }, 300);

    return result;
}

/**
 * Show a delete confirmation dialog
 */
export async function confirmDelete(itemName = 'this item') {
    return confirm(`Are you sure you want to delete ${itemName}? This action cannot be undone.`, {
        title: 'Confirm Delete',
        confirmText: 'Delete',
        variant: 'danger',
    });
}

export { ConfirmModal };
