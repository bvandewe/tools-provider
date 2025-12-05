import * as bootstrap from 'bootstrap';

export class SuccessToast extends HTMLElement {
    constructor() {
        super();
        this.toastInstance = null;
    }

    connectedCallback() {
        this.render();
        this.toastInstance = new bootstrap.Toast(this.querySelector('.toast'));
    }

    render() {
        this.innerHTML = `
            <div class="toast-container position-fixed bottom-0 end-0 p-3">
                <div class="toast align-items-center text-white bg-success border-0" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="d-flex">
                        <div class="toast-body">
                            <i class="bi bi-check-circle me-2"></i>
                            <span id="toast-message">Task updated successfully!</span>
                        </div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                    </div>
                </div>
            </div>
        `;
    }

    show(message) {
        const messageEl = this.querySelector('#toast-message');
        if (messageEl) messageEl.textContent = message;

        if (this.toastInstance) {
            this.toastInstance.show();
        }
    }
}

customElements.define('success-toast', SuccessToast);
