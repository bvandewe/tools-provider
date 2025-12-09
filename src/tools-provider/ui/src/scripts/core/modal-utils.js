/**
 * Modal Utility Functions
 *
 * Provides helpers for managing Bootstrap modal navigation,
 * especially for cross-referencing between entity modals.
 */

/**
 * Close any currently open modal and open a new one.
 * Handles Bootstrap's modal transition properly by waiting for hidden event.
 *
 * @param {string} currentModalSelector - CSS selector for the current modal (can be null)
 * @param {string} targetModalSelector - CSS selector for the target modal to open
 * @param {HTMLElement} context - The element context (usually `this` in a component)
 * @param {Function} [onTargetReady] - Optional callback to run before showing target modal
 * @returns {Promise<bootstrap.Modal>} The opened modal instance
 */
export async function navigateToModal(currentModalSelector, targetModalSelector, context, onTargetReady) {
    // Dynamically import bootstrap to avoid circular dependencies
    const bootstrap = await import('bootstrap');

    // Close current modal if specified and open
    if (currentModalSelector) {
        const currentModalEl = context.querySelector ? context.querySelector(currentModalSelector) : document.querySelector(currentModalSelector);

        if (currentModalEl) {
            const currentModal = bootstrap.Modal.getInstance(currentModalEl);
            if (currentModal) {
                // Wait for the modal to fully hide before opening the next one
                await new Promise(resolve => {
                    const onHidden = () => {
                        currentModalEl.removeEventListener('hidden.bs.modal', onHidden);
                        resolve();
                    };
                    currentModalEl.addEventListener('hidden.bs.modal', onHidden);
                    currentModal.hide();
                });
            }
        }
    }

    // Find and open target modal
    const targetModalEl = context.querySelector ? context.querySelector(targetModalSelector) : document.querySelector(targetModalSelector);

    if (!targetModalEl) {
        console.error(`Target modal not found: ${targetModalSelector}`);
        return null;
    }

    // Run the callback to prepare modal content before showing
    if (onTargetReady) {
        await onTargetReady(targetModalEl);
    }

    let targetModal = bootstrap.Modal.getInstance(targetModalEl);
    if (!targetModal) {
        targetModal = new bootstrap.Modal(targetModalEl);
    }
    targetModal.show();

    return targetModal;
}

/**
 * Close a modal by selector.
 *
 * @param {string} modalSelector - CSS selector for the modal to close
 * @param {HTMLElement} [context] - Optional element context
 * @returns {Promise<void>}
 */
export async function closeModal(modalSelector, context = document) {
    const bootstrap = await import('bootstrap');

    const modalEl = context.querySelector ? context.querySelector(modalSelector) : document.querySelector(modalSelector);

    if (!modalEl) return;

    const modal = bootstrap.Modal.getInstance(modalEl);
    if (!modal) return;

    return new Promise(resolve => {
        const onHidden = () => {
            modalEl.removeEventListener('hidden.bs.modal', onHidden);
            resolve();
        };
        modalEl.addEventListener('hidden.bs.modal', onHidden);
        modal.hide();
    });
}

/**
 * Dispatch a custom event to navigate to a different page and open a modal.
 * Useful for cross-entity navigation (e.g., from Group modal to Tool details).
 *
 * @param {string} pageName - The page to navigate to (e.g., 'tools', 'sources')
 * @param {string} modalAction - The action/modal to open (e.g., 'tool-details')
 * @param {Object} data - Data to pass to the modal
 */
export function dispatchNavigationEvent(pageName, modalAction, data) {
    // Dispatch event for app.js to handle page navigation
    document.dispatchEvent(
        new CustomEvent('navigate-to-entity', {
            bubbles: true,
            detail: {
                page: pageName,
                action: modalAction,
                data: data,
            },
        })
    );
}
