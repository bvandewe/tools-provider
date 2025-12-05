/**
 * Modal Utilities
 * Handles modal dialogs and toast notifications
 */

/**
 * Show alert modal
 * @param {string} title - Modal title
 * @param {string} message - Alert message
 * @param {string} type - Alert type ('error', 'warning', 'info', 'success')
 */
export function showAlert(title, message, type = 'error') {
    let modal = document.querySelector('alert-modal');
    if (!modal) {
        modal = document.createElement('alert-modal');
        document.body.appendChild(modal);
    }
    modal.show(title, message, type);
}

/**
 * Show confirmation modal
 * @param {string} title - Modal title
 * @param {string} message - Confirmation message
 * @param {Function} onConfirm - Callback function when confirmed
 */
export function showConfirm(title, message, onConfirm) {
    let modal = document.querySelector('confirm-modal');
    if (!modal) {
        modal = document.createElement('confirm-modal');
        document.body.appendChild(modal);
    }
    modal.show(title, message, onConfirm);
}

/**
 * Show success toast message
 * @param {string} message - Message to display
 */
export function showSuccessToast(message = 'Task updated successfully!') {
    let toast = document.querySelector('success-toast');
    if (!toast) {
        toast = document.createElement('success-toast');
        document.body.appendChild(toast);
    }
    toast.show(message);
}
