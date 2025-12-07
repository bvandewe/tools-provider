/**
 * Policies Page Component
 *
 * Admin page for managing access policies.
 * Access policies map JWT claims to allowed tool groups.
 */

import * as bootstrap from 'bootstrap';
import { eventBus } from '../core/event-bus.js';
import * as PoliciesAPI from '../api/policies.js';
import * as GroupsAPI from '../api/groups.js';
import { showToast } from '../components/toast-notification.js';
import { PolicyCard } from '../components/policy-card.js';
import { isAuthenticated } from '../api/client.js';

class PoliciesPage extends HTMLElement {
    constructor() {
        super();
        this._policies = [];
        this._groups = []; // Available tool groups for selection
        this._loading = true;
        this._eventSubscriptions = [];
        this._currentViewPolicy = null; // For view-to-edit transition
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
        // Skip loading if not authenticated (avoids console errors)
        if (!isAuthenticated()) {
            this._loading = false;
            this._policies = [];
            this._groups = [];
            this.render();
            return;
        }

        this._loading = true;
        this.render();

        try {
            // Load policies and groups in parallel
            const [policies, groups] = await Promise.all([
                PoliciesAPI.getPolicies(),
                GroupsAPI.getGroups().catch(() => []), // Groups are optional for display
            ]);
            this._policies = policies;
            this._groups = groups;
        } catch (error) {
            // Don't show toast for auth errors - user will be redirected to login
            if (!error.message?.includes('Session expired')) {
                showToast('error', `Failed to load policies: ${error.message}`);
            }
            this._policies = [];
        } finally {
            this._loading = false;
            this.render();
        }
    }

    _subscribeToEvents() {
        this._eventSubscriptions.push(
            eventBus.subscribe('policy:created', () => this._loadData()),
            eventBus.subscribe('policy:updated', () => this._loadData()),
            eventBus.subscribe('policy:deleted', data => {
                this._policies = this._policies.filter(p => p.id !== data.policy_id);
                this.render();
            }),
            eventBus.subscribe('policy:enabled', data => {
                const policy = this._policies.find(p => p.id === data.policy_id);
                if (policy) {
                    policy.is_active = true;
                    this.render();
                }
            }),
            eventBus.subscribe('policy:disabled', data => {
                const policy = this._policies.find(p => p.id === data.policy_id);
                if (policy) {
                    policy.is_active = false;
                    this.render();
                }
            }),
            // Reload when groups change (they're referenced by policies)
            eventBus.subscribe('group:created', () => this._loadData()),
            eventBus.subscribe('group:deleted', () => this._loadData())
        );
    }

    _unsubscribeFromEvents() {
        this._eventSubscriptions.forEach(unsub => unsub());
        this._eventSubscriptions = [];
    }

    render() {
        const activeCount = this._policies.filter(p => p.is_active !== false).length;
        const matcherCount = this._policies.reduce((sum, p) => sum + (p.claim_matchers?.length || 0), 0);

        this.innerHTML = `
            <div class="policies-page">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h2 class="mb-1">
                            <i class="bi bi-shield-check text-primary me-2"></i>
                            Access Policies
                        </h2>
                        <p class="text-muted mb-0">
                            Define who can access which tools based on JWT claims
                        </p>
                    </div>
                    <button type="button" class="btn btn-primary" id="add-policy-btn">
                        <i class="bi bi-plus-lg me-2"></i>
                        Create Policy
                    </button>
                </div>

                ${this._renderStats(activeCount, matcherCount)}

                ${this._loading ? this._renderLoading() : this._renderPolicies()}
            </div>

            ${this._renderAddPolicyModal()}
            ${this._renderViewPolicyModal()}
            ${this._renderEditPolicyModal()}
        `;

        this._attachEventListeners();
    }

    _renderStats(activeCount, matcherCount) {
        return `
            <div class="row g-3 mb-4">
                <div class="col-6 col-md-3">
                    <div class="card bg-primary bg-opacity-10 border-0">
                        <div class="card-body py-3 text-center">
                            <div class="fs-3 fw-bold text-primary">${this._policies.length}</div>
                            <small class="text-muted">Total Policies</small>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card bg-success bg-opacity-10 border-0">
                        <div class="card-body py-3 text-center">
                            <div class="fs-3 fw-bold text-success">${activeCount}</div>
                            <small class="text-muted">Active</small>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card bg-info bg-opacity-10 border-0">
                        <div class="card-body py-3 text-center">
                            <div class="fs-3 fw-bold text-info">${matcherCount}</div>
                            <small class="text-muted">Claim Rules</small>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card bg-warning bg-opacity-10 border-0">
                        <div class="card-body py-3 text-center">
                            <div class="fs-3 fw-bold text-warning">${this._groups.length}</div>
                            <small class="text-muted">Tool Groups</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _renderLoading() {
        return `
            <div class="d-flex justify-content-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
    }

    _renderPolicies() {
        if (this._policies.length === 0) {
            return `
                <div class="text-center py-5">
                    <i class="bi bi-shield display-1 text-muted"></i>
                    <h4 class="mt-3 text-muted">No Policies Defined</h4>
                    <p class="text-muted">Create a policy to control access to tool groups based on JWT claims</p>
                    <button type="button" class="btn btn-primary" data-action="add-first">
                        <i class="bi bi-plus-lg me-2"></i>
                        Create Your First Policy
                    </button>
                </div>
            `;
        }

        return `
            <div class="row g-4">
                ${this._policies
                    .map(
                        policy => `
                    <div class="col-12 col-lg-6">
                        <policy-card data-policy-id="${policy.id}"></policy-card>
                    </div>
                `
                    )
                    .join('')}
            </div>
        `;
    }

    _renderAddPolicyModal() {
        // Build group options
        const groupOptions = this._groups.map(g => `<option value="${g.id}">${g.name}</option>`).join('');

        return `
            <div class="modal fade" id="add-policy-modal" tabindex="-1" aria-labelledby="addPolicyModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content">
                        <form id="add-policy-form">
                            <div class="modal-header">
                                <h5 class="modal-title" id="addPolicyModalLabel">
                                    <i class="bi bi-shield-plus me-2"></i>
                                    Create Access Policy
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <!-- Basic Info -->
                                <div class="row mb-3">
                                    <div class="col-8">
                                        <label for="policy-name" class="form-label">Name <span class="text-danger">*</span></label>
                                        <input type="text" class="form-control" id="policy-name" required
                                               placeholder="e.g., Finance Team Access">
                                    </div>
                                    <div class="col-4">
                                        <label for="policy-priority" class="form-label">Priority</label>
                                        <input type="number" class="form-control" id="policy-priority"
                                               min="0" value="0" placeholder="0">
                                        <small class="text-muted">Higher = evaluated first</small>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label for="policy-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="policy-description" rows="2"
                                              placeholder="Optional description of this policy"></textarea>
                                </div>

                                <hr>

                                <!-- Claim Matchers Section -->
                                <h6 class="mb-3">
                                    <i class="bi bi-funnel me-2"></i>
                                    JWT Claim Matchers <span class="text-danger">*</span>
                                    <small class="text-muted fw-normal">(All conditions must match - AND logic)</small>
                                </h6>
                                <p class="small text-muted mb-3">
                                    Define which JWT claims must be present for this policy to apply.
                                    Use JSONPath expressions like <code>realm_access.roles</code> to match Keycloak roles.
                                </p>

                                <div id="matchers-container">
                                    <div class="matcher-row row g-2 mb-2">
                                        <div class="col-4">
                                            <input type="text" class="form-control form-control-sm matcher-path"
                                                   placeholder="realm_access.roles" list="common-claim-paths">
                                        </div>
                                        <div class="col-3">
                                            <select class="form-select form-select-sm matcher-operator">
                                                <option value="equals">Equals</option>
                                                <option value="contains" selected>Contains</option>
                                                <option value="matches">Matches (Regex)</option>
                                                <option value="not_equals">Not Equals</option>
                                                <option value="not_contains">Not Contains</option>
                                                <option value="in">In (comma-sep)</option>
                                                <option value="not_in">Not In</option>
                                                <option value="exists">Exists</option>
                                            </select>
                                        </div>
                                        <div class="col-4">
                                            <input type="text" class="form-control form-control-sm matcher-value"
                                                   placeholder="e.g., admin">
                                        </div>
                                        <div class="col-1">
                                            <button type="button" class="btn btn-outline-danger btn-sm w-100 remove-matcher">
                                                <i class="bi bi-x"></i>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                <datalist id="common-claim-paths">
                                    <option value="realm_access.roles">
                                    <option value="groups">
                                    <option value="email">
                                    <option value="preferred_username">
                                    <option value="sub">
                                    <option value="department">
                                </datalist>
                                <button type="button" class="btn btn-outline-secondary btn-sm mb-3" id="add-matcher-btn">
                                    <i class="bi bi-plus me-1"></i>
                                    Add Claim Matcher
                                </button>

                                <hr>

                                <!-- Allowed Groups Section -->
                                <h6 class="mb-3">
                                    <i class="bi bi-collection me-2"></i>
                                    Allowed Tool Groups <span class="text-danger">*</span>
                                    <small class="text-muted fw-normal">(Groups this policy grants access to)</small>
                                </h6>

                                ${
                                    this._groups.length === 0
                                        ? `
                                    <div class="alert alert-warning small">
                                        <i class="bi bi-exclamation-triangle me-2"></i>
                                        No tool groups available. Create a tool group first before creating a policy.
                                    </div>
                                `
                                        : `
                                    <div class="mb-3">
                                        <select class="form-select" id="policy-groups" multiple size="4" required>
                                            ${groupOptions}
                                        </select>
                                        <small class="text-muted">Hold Ctrl/Cmd to select multiple groups</small>
                                    </div>
                                `
                                }
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-primary" id="submit-policy-btn"
                                        ${this._groups.length === 0 ? 'disabled' : ''}>
                                    <span class="spinner-border spinner-border-sm d-none me-2" id="submit-spinner"></span>
                                    Create Policy
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
    }

    _renderViewPolicyModal() {
        return `
            <div class="modal fade" id="view-policy-modal" tabindex="-1" aria-labelledby="viewPolicyModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="viewPolicyModalLabel">
                                <i class="bi bi-shield-check me-2"></i>
                                Policy Details
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body" id="view-policy-content">
                            <!-- Content populated dynamically -->
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" id="view-to-edit-btn">
                                <i class="bi bi-pencil me-2"></i>Edit Policy
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _renderEditPolicyModal() {
        // Build group options
        const groupOptions = this._groups.map(g => `<option value="${g.id}">${g.name}</option>`).join('');

        return `
            <div class="modal fade" id="edit-policy-modal" tabindex="-1" aria-labelledby="editPolicyModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content">
                        <form id="edit-policy-form">
                            <input type="hidden" id="edit-policy-id">
                            <div class="modal-header">
                                <h5 class="modal-title" id="editPolicyModalLabel">
                                    <i class="bi bi-pencil-square me-2"></i>
                                    Edit Access Policy
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <!-- Basic Info -->
                                <div class="row mb-3">
                                    <div class="col-8">
                                        <label for="edit-policy-name" class="form-label">Name <span class="text-danger">*</span></label>
                                        <input type="text" class="form-control" id="edit-policy-name" required
                                               placeholder="e.g., Finance Team Access">
                                    </div>
                                    <div class="col-4">
                                        <label for="edit-policy-priority" class="form-label">Priority</label>
                                        <input type="number" class="form-control" id="edit-policy-priority"
                                               min="0" value="0" placeholder="0">
                                        <small class="text-muted">Higher = evaluated first</small>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label for="edit-policy-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="edit-policy-description" rows="2"
                                              placeholder="Optional description of this policy"></textarea>
                                </div>
                                <div class="mb-3">
                                    <div class="form-check form-switch">
                                        <input class="form-check-input" type="checkbox" id="edit-policy-active" checked>
                                        <label class="form-check-label" for="edit-policy-active">Policy Active</label>
                                    </div>
                                </div>

                                <hr>

                                <!-- Claim Matchers Section -->
                                <h6 class="mb-3">
                                    <i class="bi bi-funnel me-2"></i>
                                    JWT Claim Matchers <span class="text-danger">*</span>
                                    <small class="text-muted fw-normal">(All conditions must match - AND logic)</small>
                                </h6>

                                <div id="edit-matchers-container">
                                    <!-- Matchers populated dynamically -->
                                </div>
                                <datalist id="edit-common-claim-paths">
                                    <option value="realm_access.roles">
                                    <option value="groups">
                                    <option value="email">
                                    <option value="preferred_username">
                                    <option value="sub">
                                    <option value="department">
                                    <option value="roles">
                                </datalist>
                                <button type="button" class="btn btn-outline-secondary btn-sm mb-3" id="edit-add-matcher-btn">
                                    <i class="bi bi-plus me-1"></i>
                                    Add Claim Matcher
                                </button>

                                <hr>

                                <!-- Allowed Groups Section -->
                                <h6 class="mb-3">
                                    <i class="bi bi-collection me-2"></i>
                                    Allowed Tool Groups <span class="text-danger">*</span>
                                </h6>

                                ${
                                    this._groups.length === 0
                                        ? `
                                    <div class="alert alert-warning small">
                                        <i class="bi bi-exclamation-triangle me-2"></i>
                                        No tool groups available.
                                    </div>
                                `
                                        : `
                                    <div class="mb-3">
                                        <select class="form-select" id="edit-policy-groups" multiple size="4" required>
                                            ${groupOptions}
                                        </select>
                                        <small class="text-muted">Hold Ctrl/Cmd to select multiple groups</small>
                                    </div>
                                `
                                }
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-primary" id="edit-submit-policy-btn">
                                    <span class="spinner-border spinner-border-sm d-none me-2" id="edit-submit-spinner"></span>
                                    Save Changes
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
    }

    _attachEventListeners() {
        // Add policy buttons
        this.querySelector('#add-policy-btn')?.addEventListener('click', () => this._showAddModal());
        this.querySelector('[data-action="add-first"]')?.addEventListener('click', () => this._showAddModal());

        // Form submission
        this.querySelector('#add-policy-form')?.addEventListener('submit', e => this._handleAddPolicy(e));
        this.querySelector('#edit-policy-form')?.addEventListener('submit', e => this._handleEditPolicy(e));

        // Add matcher button
        this.querySelector('#add-matcher-btn')?.addEventListener('click', () => this._addMatcherRow());
        this.querySelector('#edit-add-matcher-btn')?.addEventListener('click', () => this._addEditMatcherRow());

        // Remove matcher buttons (delegated)
        this.querySelector('#matchers-container')?.addEventListener('click', e => {
            if (e.target.closest('.remove-matcher')) {
                const row = e.target.closest('.matcher-row');
                const container = this.querySelector('#matchers-container');
                if (container.children.length > 1) {
                    row.remove();
                }
            }
        });

        // Remove matcher buttons for edit form (delegated)
        this.querySelector('#edit-matchers-container')?.addEventListener('click', e => {
            if (e.target.closest('.remove-matcher')) {
                const row = e.target.closest('.matcher-row');
                const container = this.querySelector('#edit-matchers-container');
                if (container.children.length > 1) {
                    row.remove();
                }
            }
        });

        // View to edit transition
        this.querySelector('#view-to-edit-btn')?.addEventListener('click', () => {
            const viewModal = bootstrap.Modal.getInstance(this.querySelector('#view-policy-modal'));
            viewModal?.hide();
            if (this._currentViewPolicy) {
                this._showEditModal(this._currentViewPolicy);
            }
        });

        // Bind data to policy cards
        this.querySelectorAll('policy-card').forEach(card => {
            const policyId = card.dataset.policyId;
            const policy = this._policies.find(p => p.id === policyId);
            if (policy) {
                card.groups = this._groups; // Pass groups for name resolution
                card.data = policy;
            }
        });

        // Listen for card events
        this.addEventListener('policy-delete', e => {
            this._policies = this._policies.filter(p => p.id !== e.detail.id);
            this.render();
        });

        this.addEventListener('policy-view', e => {
            this._showViewModal(e.detail.data);
        });

        this.addEventListener('policy-edit', e => {
            this._showEditModal(e.detail.data);
        });
    }

    _showAddModal() {
        const modalEl = this.querySelector('#add-policy-modal');
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
    }

    _addMatcherRow() {
        const container = this.querySelector('#matchers-container');
        const row = document.createElement('div');
        row.className = 'matcher-row row g-2 mb-2';
        row.innerHTML = `
            <div class="col-4">
                <input type="text" class="form-control form-control-sm matcher-path"
                       placeholder="realm_access.roles" list="common-claim-paths">
            </div>
            <div class="col-3">
                <select class="form-select form-select-sm matcher-operator">
                    <option value="equals">Equals</option>
                    <option value="contains" selected>Contains</option>
                    <option value="matches">Matches (Regex)</option>
                    <option value="not_equals">Not Equals</option>
                    <option value="not_contains">Not Contains</option>
                    <option value="in">In (comma-sep)</option>
                    <option value="not_in">Not In</option>
                    <option value="exists">Exists</option>
                </select>
            </div>
            <div class="col-4">
                <input type="text" class="form-control form-control-sm matcher-value"
                       placeholder="e.g., admin">
            </div>
            <div class="col-1">
                <button type="button" class="btn btn-outline-danger btn-sm w-100 remove-matcher">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        `;
        container.appendChild(row);
    }

    async _handleAddPolicy(e) {
        e.preventDefault();

        const form = e.target;
        const submitBtn = form.querySelector('#submit-policy-btn');
        const spinner = form.querySelector('#submit-spinner');

        // Collect claim matchers
        const claimMatchers = [];
        form.querySelectorAll('.matcher-row').forEach(row => {
            const jsonPath = row.querySelector('.matcher-path').value.trim();
            const operator = row.querySelector('.matcher-operator').value;
            const value = row.querySelector('.matcher-value').value.trim();

            // Only add if path is provided (value can be empty for 'exists' operator)
            if (jsonPath) {
                claimMatchers.push({
                    json_path: jsonPath,
                    operator: operator,
                    value: value,
                });
            }
        });

        // Validate at least one matcher
        if (claimMatchers.length === 0) {
            showToast('error', 'Please add at least one claim matcher');
            return;
        }

        // Collect selected group IDs
        const groupSelect = form.querySelector('#policy-groups');
        const allowedGroupIds = Array.from(groupSelect?.selectedOptions || []).map(opt => opt.value);

        if (allowedGroupIds.length === 0) {
            showToast('error', 'Please select at least one tool group');
            return;
        }

        // Build policy data matching API expected format
        const policyData = {
            name: form.querySelector('#policy-name').value.trim(),
            claim_matchers: claimMatchers,
            allowed_group_ids: allowedGroupIds,
            description: form.querySelector('#policy-description').value.trim() || undefined,
            priority: parseInt(form.querySelector('#policy-priority').value, 10) || 0,
        };

        submitBtn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            const newPolicy = await PoliciesAPI.createPolicy(policyData);
            this._policies.push(newPolicy);

            // Close modal and reset form
            const modal = bootstrap.Modal.getInstance(this.querySelector('#add-policy-modal'));
            modal.hide();
            form.reset();

            showToast('success', `Policy "${policyData.name}" created successfully`);
            this.render();
        } catch (error) {
            showToast('error', `Failed to create policy: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    }

    _showViewModal(policy) {
        if (!policy) return;

        this._currentViewPolicy = policy;
        const content = this.querySelector('#view-policy-content');
        if (!content) return;

        // Get group names for display
        const groupNames = (policy.allowed_group_ids || []).map(id => {
            const group = this._groups.find(g => g.id === id);
            return group ? group.name : id.substring(0, 8) + '...';
        });

        content.innerHTML = `
            <div class="mb-4">
                <div class="d-flex justify-content-between align-items-start mb-3">
                    <div>
                        <h4 class="mb-1">${this._escapeHtml(policy.name)}</h4>
                        ${policy.description ? `<p class="text-muted mb-0">${this._escapeHtml(policy.description)}</p>` : ''}
                    </div>
                    <div class="d-flex gap-2">
                        <span class="badge bg-info">Priority: ${policy.priority || 0}</span>
                        <span class="badge ${policy.is_active !== false ? 'bg-success' : 'bg-secondary'}">
                            ${policy.is_active !== false ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                </div>
            </div>

            <hr>

            <h6 class="mb-3"><i class="bi bi-funnel me-2"></i>Claim Matchers</h6>
            ${
                policy.claim_matchers?.length > 0
                    ? `
                <div class="table-responsive mb-4">
                    <table class="table table-sm table-bordered">
                        <thead class="table-light">
                            <tr>
                                <th>Claim Path</th>
                                <th>Operator</th>
                                <th>Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${policy.claim_matchers
                                .map(
                                    m => `
                                <tr>
                                    <td><code>${this._escapeHtml(m.json_path)}</code></td>
                                    <td>${m.operator}</td>
                                    <td>${this._escapeHtml(m.value || '(any)')}</td>
                                </tr>
                            `
                                )
                                .join('')}
                        </tbody>
                    </table>
                </div>
            `
                    : '<p class="text-muted">No claim matchers defined</p>'
            }

            <h6 class="mb-3"><i class="bi bi-collection me-2"></i>Allowed Tool Groups</h6>
            ${
                groupNames.length > 0
                    ? `
                <div class="d-flex flex-wrap gap-2">
                    ${groupNames
                        .map(
                            name => `
                        <span class="badge bg-success bg-opacity-10 text-success border border-success">
                            <i class="bi bi-collection me-1"></i>${this._escapeHtml(name)}
                        </span>
                    `
                        )
                        .join('')}
                </div>
            `
                    : '<p class="text-muted">No groups assigned</p>'
            }

            <hr class="mt-4">

            <div class="row text-muted small">
                <div class="col-6">
                    <strong>Policy ID:</strong><br>
                    <code>${policy.id}</code>
                </div>
                <div class="col-6">
                    <strong>Created:</strong><br>
                    ${policy.created_at ? new Date(policy.created_at).toLocaleString() : 'Unknown'}
                </div>
            </div>
        `;

        const modalEl = this.querySelector('#view-policy-modal');
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
    }

    _showEditModal(policy) {
        if (!policy) return;

        const modalEl = this.querySelector('#edit-policy-modal');
        if (!modalEl) return;

        // Populate form fields
        this.querySelector('#edit-policy-id').value = policy.id;
        this.querySelector('#edit-policy-name').value = policy.name || '';
        this.querySelector('#edit-policy-description').value = policy.description || '';
        this.querySelector('#edit-policy-priority').value = policy.priority || 0;
        this.querySelector('#edit-policy-active').checked = policy.is_active !== false;

        // Populate matchers
        const matchersContainer = this.querySelector('#edit-matchers-container');
        matchersContainer.innerHTML = '';

        const matchers = policy.claim_matchers || [];
        if (matchers.length === 0) {
            // Add one empty row
            this._addEditMatcherRow();
        } else {
            matchers.forEach(m => this._addEditMatcherRow(m));
        }

        // Select allowed groups
        const groupSelect = this.querySelector('#edit-policy-groups');
        if (groupSelect) {
            Array.from(groupSelect.options).forEach(opt => {
                opt.selected = (policy.allowed_group_ids || []).includes(opt.value);
            });
        }

        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
    }

    _addEditMatcherRow(matcher = null) {
        const container = this.querySelector('#edit-matchers-container');
        if (!container) return;

        const row = document.createElement('div');
        row.className = 'matcher-row row g-2 mb-2';

        const operators = ['equals', 'contains', 'matches', 'not_equals', 'not_contains', 'in', 'not_in', 'exists'];
        const operatorOptions = operators.map(op => `<option value="${op}" ${matcher?.operator === op ? 'selected' : ''}>${this._formatOperator(op)}</option>`).join('');

        row.innerHTML = `
            <div class="col-4">
                <input type="text" class="form-control form-control-sm matcher-path"
                       placeholder="realm_access.roles" list="edit-common-claim-paths"
                       value="${this._escapeHtml(matcher?.json_path || '')}">
            </div>
            <div class="col-3">
                <select class="form-select form-select-sm matcher-operator">
                    ${operatorOptions}
                </select>
            </div>
            <div class="col-4">
                <input type="text" class="form-control form-control-sm matcher-value"
                       placeholder="e.g., admin" value="${this._escapeHtml(matcher?.value || '')}">
            </div>
            <div class="col-1">
                <button type="button" class="btn btn-outline-danger btn-sm w-100 remove-matcher">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        `;
        container.appendChild(row);
    }

    _formatOperator(op) {
        const labels = {
            equals: 'Equals',
            contains: 'Contains',
            matches: 'Matches (Regex)',
            not_equals: 'Not Equals',
            not_contains: 'Not Contains',
            in: 'In (comma-sep)',
            not_in: 'Not In',
            exists: 'Exists',
        };
        return labels[op] || op;
    }

    async _handleEditPolicy(e) {
        e.preventDefault();

        const form = e.target;
        const submitBtn = form.querySelector('#edit-submit-policy-btn');
        const spinner = form.querySelector('#edit-submit-spinner');

        const policyId = form.querySelector('#edit-policy-id').value;

        // Collect claim matchers
        const claimMatchers = [];
        form.querySelectorAll('.matcher-row').forEach(row => {
            const jsonPath = row.querySelector('.matcher-path').value.trim();
            const operator = row.querySelector('.matcher-operator').value;
            const value = row.querySelector('.matcher-value').value.trim();

            if (jsonPath) {
                claimMatchers.push({
                    json_path: jsonPath,
                    operator: operator,
                    value: value,
                });
            }
        });

        if (claimMatchers.length === 0) {
            showToast('error', 'Please add at least one claim matcher');
            return;
        }

        // Collect selected group IDs
        const groupSelect = form.querySelector('#edit-policy-groups');
        const allowedGroupIds = Array.from(groupSelect?.selectedOptions || []).map(opt => opt.value);

        if (allowedGroupIds.length === 0) {
            showToast('error', 'Please select at least one tool group');
            return;
        }

        const policyData = {
            name: form.querySelector('#edit-policy-name').value.trim(),
            claim_matchers: claimMatchers,
            allowed_group_ids: allowedGroupIds,
            description: form.querySelector('#edit-policy-description').value.trim() || undefined,
            priority: parseInt(form.querySelector('#edit-policy-priority').value, 10) || 0,
        };

        const newIsActive = form.querySelector('#edit-policy-active').checked;

        // Find the current policy to check if active state changed
        const currentPolicy = this._policies.find(p => p.id === policyId);
        const wasActive = currentPolicy?.is_active !== false;

        submitBtn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            // Update the policy fields
            const updatedPolicy = await PoliciesAPI.updatePolicy(policyId, policyData);

            // Handle activation state change separately
            if (newIsActive !== wasActive) {
                if (newIsActive) {
                    await PoliciesAPI.activatePolicy(policyId);
                } else {
                    await PoliciesAPI.deactivatePolicy(policyId);
                }
            }

            // Update local state
            const index = this._policies.findIndex(p => p.id === policyId);
            if (index !== -1) {
                this._policies[index] = { ...this._policies[index], ...updatedPolicy, is_active: newIsActive };
            }

            // Close modal
            const modal = bootstrap.Modal.getInstance(this.querySelector('#edit-policy-modal'));
            modal?.hide();

            showToast('success', `Policy "${policyData.name}" updated successfully`);
            this.render();
        } catch (error) {
            showToast('error', `Failed to update policy: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    }

    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

if (!customElements.get('policies-page')) {
    customElements.define('policies-page', PoliciesPage);
}

export { PoliciesPage };
