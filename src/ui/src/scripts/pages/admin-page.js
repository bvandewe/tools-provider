/**
 * Admin Page Component
 *
 * Admin page for system administration including circuit breaker management.
 */

import * as bootstrap from 'bootstrap';
import { eventBus } from '../core/event-bus.js';
import * as AdminAPI from '../api/admin.js';
import { showToast } from '../components/toast-notification.js';
import { isAuthenticated } from '../api/client.js';

class AdminPage extends HTMLElement {
    constructor() {
        super();
        this._circuitBreakers = null;
        this._tokenExchangeHealth = null;
        this._loading = true;
        this._eventSubscriptions = [];
    }

    connectedCallback() {
        this.render();
        this._loadData();
        this._subscribeToEvents();
    }

    disconnectedCallback() {
        this._unsubscribeFromEvents();
    }

    async _loadData() {
        if (!isAuthenticated()) {
            this._loading = false;
            this.render();
            return;
        }

        this._loading = true;
        this.render();

        try {
            const [circuitBreakers, health] = await Promise.all([AdminAPI.getCircuitBreakers(), AdminAPI.getTokenExchangeHealth()]);
            this._circuitBreakers = circuitBreakers;
            this._tokenExchangeHealth = health;
        } catch (error) {
            if (!error.message?.includes('Session expired')) {
                showToast('error', `Failed to load admin data: ${error.message}`);
            }
        } finally {
            this._loading = false;
            this.render();
        }
    }

    _subscribeToEvents() {
        // Subscribe to circuit breaker events for real-time updates
        this._eventSubscriptions.push(
            eventBus.subscribe('circuit_breaker:opened', data => {
                this._handleCircuitBreakerEvent('opened', data);
            }),
            eventBus.subscribe('circuit_breaker:closed', data => {
                this._handleCircuitBreakerEvent('closed', data);
            }),
            eventBus.subscribe('circuit_breaker:half_opened', data => {
                this._handleCircuitBreakerEvent('half_opened', data);
            })
        );
    }

    _unsubscribeFromEvents() {
        this._eventSubscriptions.forEach(unsub => unsub());
        this._eventSubscriptions = [];
    }

    _handleCircuitBreakerEvent(eventType, data) {
        showToast(eventType === 'opened' ? 'warning' : 'info', `Circuit breaker ${data.circuit_id} ${eventType}${data.was_manual ? ' (manual)' : ''}`);
        // Reload data to get fresh state
        this._loadData();
    }

    async _resetCircuitBreaker(type, key = null) {
        try {
            const result = await AdminAPI.resetCircuitBreaker(type, key);
            showToast('success', result.message);
            await this._loadData();
        } catch (error) {
            showToast('error', `Failed to reset circuit breaker: ${error.message}`);
        }
    }

    _getStateClass(state) {
        switch (state) {
            case 'closed':
                return 'success';
            case 'open':
                return 'danger';
            case 'half_open':
                return 'warning';
            default:
                return 'secondary';
        }
    }

    _getStateIcon(state) {
        switch (state) {
            case 'closed':
                return 'bi-check-circle-fill';
            case 'open':
                return 'bi-x-circle-fill';
            case 'half_open':
                return 'bi-exclamation-circle-fill';
            default:
                return 'bi-question-circle-fill';
        }
    }

    _formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';
        const date = new Date(timestamp * 1000); // Unix timestamp
        return date.toLocaleString();
    }

    _renderCircuitBreakerCard(id, state, type, sourceId = null) {
        const stateClass = this._getStateClass(state.state);
        const stateIcon = this._getStateIcon(state.state);
        const isOpen = state.state === 'open';

        return `
            <div class="col-md-6 col-lg-4">
                <div class="card h-100 border-${stateClass}">
                    <div class="card-header d-flex justify-content-between align-items-center bg-${stateClass} bg-opacity-10">
                        <div>
                            <i class="bi ${stateIcon} text-${stateClass} me-2"></i>
                            <span class="fw-semibold">${id}</span>
                        </div>
                        <span class="badge bg-${stateClass}">${state.state.toUpperCase()}</span>
                    </div>
                    <div class="card-body">
                        <div class="mb-2">
                            <small class="text-muted">Type:</small>
                            <span class="ms-2">${type}</span>
                        </div>
                        ${
                            sourceId
                                ? `
                            <div class="mb-2">
                                <small class="text-muted">Source:</small>
                                <span class="ms-2">${sourceId}</span>
                            </div>
                        `
                                : ''
                        }
                        <div class="mb-2">
                            <small class="text-muted">Failure Count:</small>
                            <span class="ms-2 ${state.failure_count > 0 ? 'text-warning' : ''}">${state.failure_count}</span>
                        </div>
                        ${
                            state.last_failure_time
                                ? `
                            <div class="mb-2">
                                <small class="text-muted">Last Failure:</small>
                                <span class="ms-2 text-danger">${this._formatTimestamp(state.last_failure_time)}</span>
                            </div>
                        `
                                : ''
                        }
                    </div>
                    <div class="card-footer bg-transparent">
                        <button
                            class="btn btn-sm btn-outline-primary reset-circuit-btn"
                            data-type="${type}"
                            data-key="${sourceId || ''}"
                            ${!isOpen ? 'disabled' : ''}
                            title="${isOpen ? 'Reset circuit breaker to closed state' : 'Circuit is already closed'}"
                        >
                            <i class="bi bi-arrow-counterclockwise me-1"></i>
                            Reset
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    render() {
        if (this._loading) {
            this.innerHTML = `
                <div class="d-flex justify-content-center align-items-center" style="min-height: 200px;">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `;
            return;
        }

        const cb = this._circuitBreakers;
        const health = this._tokenExchangeHealth;

        // Token exchange circuit breaker
        let tokenExchangeCard = '';
        if (cb?.token_exchange) {
            tokenExchangeCard = this._renderCircuitBreakerCard('Keycloak Token Exchange', cb.token_exchange, 'token_exchange');
        }

        // Tool execution circuit breakers
        let toolExecutionCards = '';
        if (cb?.tool_execution) {
            const entries = Object.entries(cb.tool_execution);
            if (entries.length > 0) {
                toolExecutionCards = entries.map(([key, state]) => this._renderCircuitBreakerCard(key, state, 'tool_execution', state.source_id || key)).join('');
            } else {
                toolExecutionCards = `
                    <div class="col-12">
                        <div class="alert alert-info mb-0">
                            <i class="bi bi-info-circle me-2"></i>
                            No tool execution circuit breakers have been created yet.
                            They are created on first tool execution for each source.
                        </div>
                    </div>
                `;
            }
        }

        // Health check info
        let healthInfo = '';
        if (health) {
            healthInfo = `
                <div class="card mb-4">
                    <div class="card-header">
                        <i class="bi bi-heart-pulse me-2"></i>
                        Token Exchange Health
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-4">
                                <div class="d-flex align-items-center">
                                    <i class="bi ${health.healthy ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger'} fs-4 me-2"></i>
                                    <div>
                                        <div class="fw-semibold">Status</div>
                                        <div class="${health.healthy ? 'text-success' : 'text-danger'}">${health.healthy ? 'Healthy' : 'Unhealthy'}</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="text-muted small">Token Endpoint</div>
                                <div class="text-break small">${health.token_endpoint || 'N/A'}</div>
                            </div>
                            <div class="col-md-4">
                                <div class="text-muted small">Local Cache Size</div>
                                <div>${health.local_cache_size ?? 'N/A'} tokens</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        this.innerHTML = `
            <div class="container-fluid">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h2>
                        <i class="bi bi-gear-wide-connected me-2"></i>
                        System Administration
                    </h2>
                    <button class="btn btn-outline-primary" id="refresh-admin-btn">
                        <i class="bi bi-arrow-clockwise me-1"></i>
                        Refresh
                    </button>
                </div>

                ${healthInfo}

                <h4 class="mb-3">
                    <i class="bi bi-lightning-charge me-2"></i>
                    Circuit Breakers
                </h4>

                <div class="alert alert-info mb-4">
                    <i class="bi bi-info-circle me-2"></i>
                    <strong>Circuit Breakers</strong> protect the system from cascading failures.
                    When a service fails repeatedly, the circuit <strong>opens</strong> to prevent further requests.
                    After a recovery timeout, it enters <strong>half-open</strong> state to test recovery.
                    You can <strong>reset</strong> an open circuit after resolving the underlying issue.
                </div>

                <h5 class="mb-3">Token Exchange (Keycloak)</h5>
                <div class="row g-3 mb-4">
                    ${tokenExchangeCard || '<div class="col-12"><p class="text-muted">No token exchange circuit breaker data.</p></div>'}
                </div>

                <h5 class="mb-3">Tool Execution (Per-Source)</h5>
                <div class="row g-3 mb-4">
                    ${toolExecutionCards}
                </div>

                ${
                    Object.keys(cb?.tool_execution || {}).length > 0
                        ? `
                    <div class="mt-3">
                        <button class="btn btn-outline-warning" id="reset-all-tool-breakers-btn">
                            <i class="bi bi-arrow-counterclockwise me-1"></i>
                            Reset All Tool Execution Circuit Breakers
                        </button>
                    </div>
                `
                        : ''
                }
            </div>
        `;

        // Attach event listeners
        this._attachEventListeners();
    }

    _attachEventListeners() {
        // Refresh button
        const refreshBtn = this.querySelector('#refresh-admin-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this._loadData());
        }

        // Individual reset buttons
        this.querySelectorAll('.reset-circuit-btn').forEach(btn => {
            btn.addEventListener('click', e => {
                const type = e.currentTarget.dataset.type;
                const key = e.currentTarget.dataset.key || null;
                this._resetCircuitBreaker(type, key);
            });
        });

        // Reset all tool execution button
        const resetAllBtn = this.querySelector('#reset-all-tool-breakers-btn');
        if (resetAllBtn) {
            resetAllBtn.addEventListener('click', () => {
                this._resetCircuitBreaker('tool_execution', 'all');
            });
        }
    }
}

// Define custom element
customElements.define('admin-page', AdminPage);

export { AdminPage };
