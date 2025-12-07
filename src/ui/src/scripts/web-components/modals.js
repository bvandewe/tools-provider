import * as bootstrap from 'bootstrap';

export class AlertModal extends HTMLElement {
    constructor() {
        super();
        this.modalInstance = null;
    }

    connectedCallback() {
        this.render();
        this.modalInstance = new bootstrap.Modal(this.querySelector('.modal'));
    }

    render() {
        this.innerHTML = `
            <div class="modal fade" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title d-flex align-items-center">
                                <i class="bi bi-exclamation-circle me-2" id="alert-icon"></i>
                                <span id="alert-title">Alert</span>
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <p id="alert-message"></p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    show(title, message, type = 'error') {
        const titleEl = this.querySelector('#alert-title');
        const messageEl = this.querySelector('#alert-message');
        const iconEl = this.querySelector('#alert-icon');

        if (titleEl) titleEl.textContent = title;
        if (messageEl) messageEl.textContent = message;

        const iconMap = {
            error: 'bi-x-circle text-danger',
            warning: 'bi-exclamation-triangle text-warning',
            info: 'bi-info-circle text-info',
            success: 'bi-check-circle text-success',
        };

        if (iconEl) iconEl.className = `bi ${iconMap[type] || iconMap.error} me-2`;

        if (this.modalInstance) {
            this.modalInstance.show();
        }
    }
}

customElements.define('alert-modal', AlertModal);
// Note: ConfirmModal is defined in components/confirm-modal.js with Promise-based API
