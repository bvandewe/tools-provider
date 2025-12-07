/**
 * Session Expired Modal Component
 *
 * Shows a modal notification when the user's session expires,
 * then redirects to login after a countdown.
 */

import * as bootstrap from 'bootstrap';

const REDIRECT_DELAY = 5; // seconds

class SessionExpiredModal extends HTMLElement {
    constructor() {
        super();
        this._modalInstance = null;
        this._countdownInterval = null;
        this._secondsRemaining = REDIRECT_DELAY;
    }

    connectedCallback() {
        this.render();
        this._modalInstance = new bootstrap.Modal(this.querySelector('.modal'), {
            backdrop: 'static',
            keyboard: false,
        });
    }

    render() {
        this.innerHTML = `
            <div class="modal fade" tabindex="-1" aria-labelledby="sessionExpiredModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header bg-warning text-dark">
                            <h5 class="modal-title" id="sessionExpiredModalLabel">
                                <i class="bi bi-clock-history me-2"></i>
                                Session Expired
                            </h5>
                        </div>
                        <div class="modal-body text-center">
                            <div class="mb-3">
                                <i class="bi bi-shield-lock display-1 text-warning"></i>
                            </div>
                            <p class="lead">Your session has expired.</p>
                            <p class="text-muted">
                                You will be redirected to the login page in
                                <span id="countdown-seconds" class="fw-bold">${REDIRECT_DELAY}</span> seconds.
                            </p>
                        </div>
                        <div class="modal-footer justify-content-center">
                            <button type="button" class="btn btn-primary" id="login-now-btn">
                                <i class="bi bi-box-arrow-in-right me-2"></i>
                                Login Now
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Set up login button
        this.querySelector('#login-now-btn').addEventListener('click', () => {
            this._redirectToLogin();
        });
    }

    show() {
        this._secondsRemaining = REDIRECT_DELAY;
        this._updateCountdown();
        this._modalInstance.show();
        this._startCountdown();
    }

    _startCountdown() {
        this._countdownInterval = setInterval(() => {
            this._secondsRemaining--;
            this._updateCountdown();

            if (this._secondsRemaining <= 0) {
                this._redirectToLogin();
            }
        }, 1000);
    }

    _updateCountdown() {
        const countdownEl = this.querySelector('#countdown-seconds');
        if (countdownEl) {
            countdownEl.textContent = this._secondsRemaining;
        }
    }

    _redirectToLogin() {
        if (this._countdownInterval) {
            clearInterval(this._countdownInterval);
        }
        window.location.href = '/api/auth/login';
    }

    disconnectedCallback() {
        if (this._countdownInterval) {
            clearInterval(this._countdownInterval);
        }
    }
}

if (!customElements.get('session-expired-modal')) {
    customElements.define('session-expired-modal', SessionExpiredModal);
}

/**
 * Show the session expired modal
 * Creates the element if it doesn't exist
 */
export function showSessionExpiredModal() {
    let modal = document.querySelector('session-expired-modal');
    if (!modal) {
        modal = document.createElement('session-expired-modal');
        document.body.appendChild(modal);
    }
    // Small delay to ensure component is connected
    setTimeout(() => modal.show(), 50);
}

export { SessionExpiredModal };
