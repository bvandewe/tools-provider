/**
 * Groups Page Component
 *
 * Admin page for managing tool groups.
 */

import * as bootstrap from 'bootstrap';
import { eventBus } from '../core/event-bus.js';
import * as GroupsAPI from '../api/groups.js';
import { apiSelectorToUiFormat, uiSelectorsToApiFormat } from '../api/groups.js';
import * as ToolsAPI from '../api/tools.js';
import { showToast } from '../components/toast-notification.js';
import { GroupCard } from '../components/group-card.js';
import { isAuthenticated } from '../api/client.js';
import { getToolDisplayName, getMethodClass, inferMethodFromName } from '../core/tool-utils.js';

class GroupsPage extends HTMLElement {
    constructor() {
        super();
        this._groups = [];
        this._allTools = []; // Cache all tools for preview
        this._loading = true;
        this._eventSubscriptions = [];
        this._editingGroup = null; // Track group being edited
        this._previewDebounceTimer = null;
        this._addToolsToGroupId = null; // Track group for adding tools
        this._toolSelectorSearchTerm = '';
        this._toolSelectorFilterMethod = null;
        this._toolSelectorFilterTag = null;
        this._toolSelectorFilterSource = null;
        this._toolSelectorSelectedIds = new Set();
        this._highlightedGroupId = null; // For cross-entity navigation highlight
    }

    connectedCallback() {
        this.render();
        this._loadGroups();
        this._subscribeToEvents();

        // Listen for filter requests (e.g., from policy details)
        this.addEventListener('open-filter-group', async e => {
            const { groupId } = e.detail || {};
            if (groupId) {
                // Wait for page to render
                await new Promise(resolve => setTimeout(resolve, 150));
                this._highlightedGroupId = groupId;
                this.render();
                // Scroll to the highlighted group
                setTimeout(() => {
                    const groupCard = this.querySelector(`group-card[data-group-id="${groupId}"]`);
                    if (groupCard) {
                        groupCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        groupCard.classList.add('highlight-flash');
                        setTimeout(() => groupCard.classList.remove('highlight-flash'), 2000);
                    }
                }, 200);
            }
        });
    }

    disconnectedCallback() {
        this._unsubscribeFromEvents();
    }

    async _loadGroups() {
        // Skip loading if not authenticated (avoids console errors)
        if (!isAuthenticated()) {
            this._loading = false;
            this._groups = [];
            this._allTools = [];
            this.render();
            return;
        }

        this._loading = true;
        this.render();

        try {
            // Load groups and tools in parallel
            const [groups, tools] = await Promise.all([GroupsAPI.getGroups(), ToolsAPI.getTools()]);
            this._groups = groups;
            this._allTools = tools;
        } catch (error) {
            // Don't show toast for auth errors - user will be redirected to login
            if (!error.message?.includes('Session expired')) {
                showToast('error', `Failed to load groups: ${error.message}`);
            }
            this._groups = [];
            this._allTools = [];
        } finally {
            this._loading = false;
            this.render();
        }
    }

    _subscribeToEvents() {
        this._eventSubscriptions.push(
            eventBus.subscribe('group:created', () => this._loadGroups()),
            eventBus.subscribe('group:updated', () => this._loadGroups()),
            eventBus.subscribe('group:deleted', data => {
                this._groups = this._groups.filter(g => g.id !== data.group_id);
                this.render();
            })
        );
    }

    _unsubscribeFromEvents() {
        this._eventSubscriptions.forEach(unsub => unsub());
        this._eventSubscriptions = [];
    }

    render() {
        // Count explicit tools (selector-based tools are resolved dynamically per group)
        const explicitTools = this._groups.reduce((sum, g) => sum + (g.explicit_tool_count || 0), 0);
        const groupsWithSelectors = this._groups.filter(g => (g.selector_count || g.selectors?.length) > 0).length;

        this.innerHTML = `
            <div class="groups-page">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h2 class="mb-1">
                            <i class="bi bi-collection text-primary me-2"></i>
                            Tool Groups
                        </h2>
                        <p class="text-muted mb-0">
                            Organize tools into logical groups for access control
                        </p>
                    </div>
                    <button type="button" class="btn btn-primary" id="add-group-btn">
                        <i class="bi bi-plus-lg me-2"></i>
                        Create Group
                    </button>
                </div>

                ${this._renderStats(explicitTools, groupsWithSelectors)}

                ${this._loading ? this._renderLoading() : this._renderGroups()}
            </div>

            ${this._renderAddGroupModal()}
            ${this._renderEditGroupModal()}
            ${this._renderToolSelectorModal()}
        `;

        this._attachEventListeners();
    }

    _renderStats(explicitTools, groupsWithSelectors) {
        return `
            <div class="row g-3 mb-4">
                <div class="col-6 col-md-4">
                    <div class="card bg-primary bg-opacity-10 border-0">
                        <div class="card-body py-3 text-center">
                            <div class="fs-3 fw-bold text-primary">${this._groups.length}</div>
                            <small class="text-muted">Groups</small>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-md-4">
                    <div class="card bg-success bg-opacity-10 border-0">
                        <div class="card-body py-3 text-center">
                            <div class="fs-3 fw-bold text-success">${groupsWithSelectors}</div>
                            <small class="text-muted">With Selectors</small>
                        </div>
                    </div>
                </div>
                <div class="col-12 col-md-4">
                    <div class="card bg-info bg-opacity-10 border-0">
                        <div class="card-body py-3 text-center">
                            <div class="fs-3 fw-bold text-info">
                                ${this._groups.filter(g => g.is_active === true || g.status === 'active').length}
                            </div>
                            <small class="text-muted">Active Groups</small>
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

    _renderGroups() {
        if (this._groups.length === 0) {
            return `
                <div class="text-center py-5">
                    <i class="bi bi-collection display-1 text-muted"></i>
                    <h4 class="mt-3 text-muted">No Groups Created</h4>
                    <p class="text-muted">Create a group to organize your tools</p>
                    <button type="button" class="btn btn-primary" data-action="add-first">
                        <i class="bi bi-plus-lg me-2"></i>
                        Create Your First Group
                    </button>
                </div>
            `;
        }

        return `
            <div class="row g-4">
                ${this._groups
                    .map(
                        group => `
                    <div class="col-12 col-md-6 col-lg-4">
                        <group-card data-group-id="${group.id}"></group-card>
                    </div>
                `
                    )
                    .join('')}
            </div>
        `;
    }

    _renderAddGroupModal() {
        return `
            <div class="modal fade" id="add-group-modal" tabindex="-1" aria-labelledby="addGroupModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content">
                        <form id="add-group-form">
                            <div class="modal-header">
                                <h5 class="modal-title" id="addGroupModalLabel">
                                    <i class="bi bi-collection me-2"></i>
                                    Create Tool Group
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="group-name" class="form-label">Name <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control" id="group-name" required
                                           placeholder="e.g., User Management Tools">
                                </div>
                                <div class="mb-3">
                                    <label for="group-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="group-description" rows="2"
                                              placeholder="Optional description of this group"></textarea>
                                </div>

                                <hr>
                                <h6 class="mb-3">
                                    <i class="bi bi-funnel me-2"></i>
                                    Tool Selectors
                                    <small class="text-muted fw-normal">(Define patterns to auto-include tools)</small>
                                </h6>

                                <div id="selectors-container">
                                    <div class="selector-row row g-2 mb-2">
                                        <div class="col-4">
                                            <select class="form-select form-select-sm selector-type">
                                                <option value="name">Name Pattern</option>
                                                <option value="method">HTTP Method</option>
                                                <option value="path">Path Pattern</option>
                                                <option value="tag">Tag</option>
                                                <option value="label">Label</option>
                                                <option value="source">Source</option>
                                            </select>
                                        </div>
                                        <div class="col-6">
                                            <input type="text" class="form-control form-control-sm selector-pattern"
                                                   placeholder="e.g., user*">
                                        </div>
                                        <div class="col-2">
                                            <button type="button" class="btn btn-outline-danger btn-sm w-100 remove-selector">
                                                <i class="bi bi-x"></i>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                <button type="button" class="btn btn-outline-secondary btn-sm" id="add-selector-btn">
                                    <i class="bi bi-plus me-1"></i>
                                    Add Selector
                                </button>

                                <hr>
                                <h6 class="mb-3">
                                    <i class="bi bi-eye me-2"></i>
                                    Tool Preview
                                    <small class="text-muted fw-normal">(Tools matching your selectors)</small>
                                </h6>
                                <div id="tool-preview-container" class="tool-preview-container">
                                    <div class="text-muted text-center py-3">
                                        <i class="bi bi-info-circle me-1"></i>
                                        Enter selector patterns above to preview matching tools
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-primary" id="submit-group-btn">
                                    <span class="spinner-border spinner-border-sm d-none me-2" id="submit-spinner"></span>
                                    Create Group
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
    }

    _attachEventListeners() {
        // Add group buttons
        this.querySelector('#add-group-btn')?.addEventListener('click', () => this._showAddModal());
        this.querySelector('[data-action="add-first"]')?.addEventListener('click', () => this._showAddModal());

        // Form submission
        this.querySelector('#add-group-form')?.addEventListener('submit', e => this._handleAddGroup(e));

        // Add selector button
        this.querySelector('#add-selector-btn')?.addEventListener('click', () => {
            this._addSelectorRow();
            this._updateToolPreview();
        });

        // Remove selector buttons (delegated) and update preview
        this.querySelector('#selectors-container')?.addEventListener('click', e => {
            if (e.target.closest('.remove-selector')) {
                const row = e.target.closest('.selector-row');
                const container = this.querySelector('#selectors-container');
                if (container.children.length > 1) {
                    row.remove();
                    this._updateToolPreview();
                }
            }
        });

        // Selector input changes trigger preview update
        this.querySelector('#selectors-container')?.addEventListener('input', e => {
            if (e.target.classList.contains('selector-pattern')) {
                this._updateToolPreview();
            }
        });
        this.querySelector('#selectors-container')?.addEventListener('change', e => {
            if (e.target.classList.contains('selector-type')) {
                this._updateToolPreview();
            }
        });

        // Bind data to group cards
        this.querySelectorAll('group-card').forEach(card => {
            const groupId = card.dataset.groupId;
            const group = this._groups.find(g => g.id === groupId);
            if (group) {
                card.data = group;
            }
        });

        // Listen for card events
        this.addEventListener('group-delete', e => {
            this._groups = this._groups.filter(g => g.id !== e.detail.id);
            this.render();
        });

        // Listen for edit events from group cards
        this.addEventListener('group-edit', e => {
            this._handleEditGroup(e.detail.data);
        });

        // Listen for add-tools events from group cards
        this.addEventListener('group-add-tools', e => {
            this._showToolSelectorModal(e.detail.id);
        });

        // Listen for group-updated events from group cards
        this.addEventListener('group-updated', () => {
            this._loadGroups();
        });
    }

    _showAddModal() {
        const modalEl = this.querySelector('#add-group-modal');
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
    }

    _addSelectorRow() {
        const container = this.querySelector('#selectors-container');
        const row = document.createElement('div');
        row.className = 'selector-row row g-2 mb-2';
        row.innerHTML = `
            <div class="col-4">
                <select class="form-select form-select-sm selector-type">
                    <option value="name">Name Pattern</option>
                    <option value="method">HTTP Method</option>
                    <option value="path">Path Pattern</option>
                    <option value="tag">Tag</option>
                    <option value="label">Label</option>
                    <option value="source">Source</option>
                </select>
            </div>
            <div class="col-6">
                <input type="text" class="form-control form-control-sm selector-pattern"
                       placeholder="e.g., user*">
            </div>
            <div class="col-2">
                <button type="button" class="btn btn-outline-danger btn-sm w-100 remove-selector">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        `;
        container.appendChild(row);
    }

    async _handleAddGroup(e) {
        e.preventDefault();

        const form = e.target;
        const submitBtn = form.querySelector('#submit-group-btn');
        const spinner = form.querySelector('#submit-spinner');

        // Collect selectors in UI format (API module handles conversion)
        const selectors = [];
        form.querySelectorAll('.selector-row').forEach(row => {
            const type = row.querySelector('.selector-type').value;
            const pattern = row.querySelector('.selector-pattern').value.trim();
            if (pattern) {
                selectors.push({ type, pattern });
            }
        });

        const groupData = {
            name: form.querySelector('#group-name').value.trim(),
            description: form.querySelector('#group-description').value.trim() || undefined,
            selectors: selectors, // API module converts to API format
            explicit_tool_ids: [],
            excluded_tool_ids: [],
        };

        submitBtn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            const newGroup = await GroupsAPI.createToolGroup(groupData);
            this._groups.push(newGroup);

            // Close modal and reset form
            const modal = bootstrap.Modal.getInstance(this.querySelector('#add-group-modal'));
            modal.hide();
            form.reset();

            showToast('success', `Group "${groupData.name}" created successfully`);
            this.render();
        } catch (error) {
            showToast('error', `Failed to create group: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    }

    // =========================================================================
    // EDIT GROUP METHODS
    // =========================================================================

    _renderEditGroupModal() {
        return `
            <div class="modal fade" id="edit-group-modal" tabindex="-1" aria-labelledby="editGroupModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable">
                    <div class="modal-content">
                        <form id="edit-group-form">
                            <div class="modal-header">
                                <h5 class="modal-title" id="editGroupModalLabel">
                                    <i class="bi bi-pencil me-2"></i>
                                    Edit Tool Group
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="edit-group-name" class="form-label">Name <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control" id="edit-group-name" required
                                           placeholder="e.g., User Management Tools">
                                </div>
                                <div class="mb-3">
                                    <label for="edit-group-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="edit-group-description" rows="2"
                                              placeholder="Optional description of this group"></textarea>
                                </div>

                                <hr>
                                <div class="d-flex justify-content-between align-items-center mb-3">
                                    <h6 class="mb-0">
                                        <i class="bi bi-funnel me-2"></i>
                                        Tool Selectors
                                    </h6>
                                    <button type="button" class="btn btn-outline-secondary btn-sm" id="edit-add-selector-btn">
                                        <i class="bi bi-plus me-1"></i>
                                        Add Selector
                                    </button>
                                </div>

                                <div id="edit-selectors-container">
                                    <!-- Selectors will be populated dynamically -->
                                </div>

                                <hr>
                                <h6 class="mb-3">
                                    <i class="bi bi-wrench me-2"></i>
                                    Tool Management
                                </h6>

                                <!-- Tabs for Tools / Explicit / Excluded -->
                                <ul class="nav nav-tabs" id="edit-group-tools-tabs" role="tablist">
                                    <li class="nav-item" role="presentation">
                                        <button class="nav-link active" id="edit-tools-tab" data-bs-toggle="tab"
                                                data-bs-target="#edit-tools-pane" type="button" role="tab"
                                                aria-controls="edit-tools-pane" aria-selected="true">
                                            <i class="bi bi-list-check me-1"></i>Tools
                                            <span class="badge bg-secondary ms-1" id="edit-tools-count">0</span>
                                        </button>
                                    </li>
                                    <li class="nav-item" role="presentation">
                                        <button class="nav-link" id="edit-explicit-tab" data-bs-toggle="tab"
                                                data-bs-target="#edit-explicit-pane" type="button" role="tab"
                                                aria-controls="edit-explicit-pane" aria-selected="false">
                                            <i class="bi bi-plus-circle me-1"></i>Explicit
                                            <span class="badge bg-success ms-1" id="edit-explicit-count">0</span>
                                        </button>
                                    </li>
                                    <li class="nav-item" role="presentation">
                                        <button class="nav-link" id="edit-excluded-tab" data-bs-toggle="tab"
                                                data-bs-target="#edit-excluded-pane" type="button" role="tab"
                                                aria-controls="edit-excluded-pane" aria-selected="false">
                                            <i class="bi bi-dash-circle me-1"></i>Excluded
                                            <span class="badge bg-danger ms-1" id="edit-excluded-count">0</span>
                                        </button>
                                    </li>
                                </ul>

                                <div class="tab-content border border-top-0 rounded-bottom p-3" id="edit-group-tools-content">
                                    <!-- Tools Tab (resolved/computed) -->
                                    <div class="tab-pane fade show active" id="edit-tools-pane" role="tabpanel"
                                         aria-labelledby="edit-tools-tab">
                                        <small class="text-muted d-block mb-2">
                                            <i class="bi bi-info-circle me-1"></i>
                                            Read-only preview of tools matching selectors (includes explicit, excludes excluded)
                                        </small>
                                        <div id="edit-tool-preview-container" class="tool-preview-container"
                                             style="max-height: 300px; overflow-y: auto;">
                                            <div class="text-muted text-center py-3">
                                                <i class="bi bi-info-circle me-1"></i>
                                                Enter selector patterns above to preview matching tools
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Explicit Tab (editable) -->
                                    <div class="tab-pane fade" id="edit-explicit-pane" role="tabpanel"
                                         aria-labelledby="edit-explicit-tab">
                                        <small class="text-muted d-block mb-2">
                                            <i class="bi bi-info-circle me-1"></i>
                                            Tools explicitly added to this group (always included regardless of selectors)
                                        </small>
                                        <div class="input-group mb-2">
                                            <input type="text" class="form-control form-control-sm"
                                                   id="edit-explicit-search" placeholder="Search tools to add...">
                                            <button type="button" class="btn btn-outline-secondary btn-sm"
                                                    id="edit-add-explicit-btn">
                                                <i class="bi bi-plus"></i>
                                            </button>
                                        </div>
                                        <div id="edit-explicit-list" class="tool-list-container"
                                             style="max-height: 250px; overflow-y: auto;">
                                            <div class="text-muted text-center py-2">No explicit tools added</div>
                                        </div>
                                    </div>

                                    <!-- Excluded Tab (editable) -->
                                    <div class="tab-pane fade" id="edit-excluded-pane" role="tabpanel"
                                         aria-labelledby="edit-excluded-tab">
                                        <small class="text-muted d-block mb-2">
                                            <i class="bi bi-info-circle me-1"></i>
                                            Tools explicitly excluded from this group (never included even if matched by selectors)
                                        </small>
                                        <div class="input-group mb-2">
                                            <input type="text" class="form-control form-control-sm"
                                                   id="edit-excluded-search" placeholder="Search tools to exclude...">
                                            <button type="button" class="btn btn-outline-secondary btn-sm"
                                                    id="edit-add-excluded-btn">
                                                <i class="bi bi-plus"></i>
                                            </button>
                                        </div>
                                        <div id="edit-excluded-list" class="tool-list-container"
                                             style="max-height: 250px; overflow-y: auto;">
                                            <div class="text-muted text-center py-2">No tools excluded</div>
                                        </div>
                                    </div>
                                </div>

                                <hr>
                                <div class="d-flex justify-content-between align-items-center mb-3">
                                    <h6 class="mb-0">
                                        <i class="bi bi-toggle-on me-2"></i>
                                        Status
                                    </h6>
                                </div>
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" id="edit-group-active">
                                    <label class="form-check-label" for="edit-group-active">Active</label>
                                </div>
                                <small class="text-muted">Inactive groups are not used in access policy resolution</small>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-primary" id="edit-submit-group-btn">
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

    _handleEditGroup(group) {
        if (!group) return;

        this._editingGroup = group;

        // Initialize explicit/excluded tool IDs from group data
        this._editExplicitToolIds = (group.explicit_tool_ids || []).map(t => (typeof t === 'string' ? t : t.tool_id));
        this._editExcludedToolIds = (group.excluded_tool_ids || []).map(t => (typeof t === 'string' ? t : t.tool_id));

        // Populate form fields
        const nameInput = this.querySelector('#edit-group-name');
        const descInput = this.querySelector('#edit-group-description');
        const activeCheck = this.querySelector('#edit-group-active');
        const selectorsContainer = this.querySelector('#edit-selectors-container');

        if (nameInput) nameInput.value = group.name || '';
        if (descInput) descInput.value = group.description || '';
        if (activeCheck) activeCheck.checked = group.status === 'active';

        // Populate selectors - convert API format to UI format
        if (selectorsContainer) {
            selectorsContainer.innerHTML = '';
            const selectors = group.selectors || [];

            if (selectors.length === 0) {
                // Add one empty row
                this._addEditSelectorRow();
            } else {
                selectors.forEach(sel => {
                    // Convert from API format (source_pattern, name_pattern, etc.) to UI format (type, pattern)
                    const uiSelector = apiSelectorToUiFormat(sel);
                    this._addEditSelectorRow(uiSelector.type, uiSelector.pattern);
                });
            }
        }

        // Attach edit-specific listeners
        this.querySelector('#edit-add-selector-btn')?.addEventListener('click', () => {
            this._addEditSelectorRow();
            this._updateEditToolPreview();
        });
        this.querySelector('#edit-group-form')?.addEventListener('submit', e => this._handleSaveGroup(e));
        this.querySelector('#edit-selectors-container')?.addEventListener('click', e => {
            if (e.target.closest('.remove-selector')) {
                const row = e.target.closest('.selector-row');
                const container = this.querySelector('#edit-selectors-container');
                if (container.children.length > 1) {
                    row.remove();
                    this._updateEditToolPreview();
                }
            }
        });

        // Selector input changes trigger preview update
        this.querySelector('#edit-selectors-container')?.addEventListener('input', e => {
            if (e.target.classList.contains('selector-pattern')) {
                this._updateEditToolPreview();
            }
        });
        this.querySelector('#edit-selectors-container')?.addEventListener('change', e => {
            if (e.target.classList.contains('selector-type')) {
                this._updateEditToolPreview();
            }
        });

        // Attach explicit/excluded tool list handlers
        this._attachEditToolListHandlers();

        // Render explicit and excluded tool lists
        this._renderEditExplicitList();
        this._renderEditExcludedList();

        // Show modal
        const modalEl = this.querySelector('#edit-group-modal');
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();

        // Trigger initial preview after modal is shown
        setTimeout(() => this._updateEditToolPreview(), 100);
    }

    /**
     * Attach event handlers for explicit/excluded tool list management
     */
    _attachEditToolListHandlers() {
        // Explicit tools - search and add
        const explicitSearchInput = this.querySelector('#edit-explicit-search');
        const addExplicitBtn = this.querySelector('#edit-add-explicit-btn');
        if (explicitSearchInput && addExplicitBtn) {
            addExplicitBtn.onclick = () => this._showToolSearchDropdown(explicitSearchInput, 'explicit');
            explicitSearchInput.addEventListener('keydown', e => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this._showToolSearchDropdown(explicitSearchInput, 'explicit');
                }
            });
        }

        // Excluded tools - search and add
        const excludedSearchInput = this.querySelector('#edit-excluded-search');
        const addExcludedBtn = this.querySelector('#edit-add-excluded-btn');
        if (excludedSearchInput && addExcludedBtn) {
            addExcludedBtn.onclick = () => this._showToolSearchDropdown(excludedSearchInput, 'excluded');
            excludedSearchInput.addEventListener('keydown', e => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this._showToolSearchDropdown(excludedSearchInput, 'excluded');
                }
            });
        }

        // Remove buttons in lists
        this.querySelector('#edit-explicit-list')?.addEventListener('click', e => {
            const removeBtn = e.target.closest('.remove-tool-btn');
            if (removeBtn) {
                const toolId = removeBtn.dataset.toolId;
                this._editExplicitToolIds = this._editExplicitToolIds.filter(id => id !== toolId);
                this._renderEditExplicitList();
                this._updateEditToolPreview();
            }
        });

        this.querySelector('#edit-excluded-list')?.addEventListener('click', e => {
            const removeBtn = e.target.closest('.remove-tool-btn');
            if (removeBtn) {
                const toolId = removeBtn.dataset.toolId;
                this._editExcludedToolIds = this._editExcludedToolIds.filter(id => id !== toolId);
                this._renderEditExcludedList();
                this._updateEditToolPreview();
            }
        });
    }

    /**
     * Show a dropdown with search results for adding tools
     */
    async _showToolSearchDropdown(inputEl, listType) {
        const query = inputEl.value.trim();
        if (query.length < 2) {
            showToast('info', 'Enter at least 2 characters to search');
            return;
        }

        try {
            const results = await ToolsAPI.searchTools(query, { includeDisabled: false });
            if (!results || results.length === 0) {
                showToast('info', 'No tools found matching your search');
                return;
            }

            // Filter out already added tools
            const existingIds = listType === 'explicit' ? this._editExplicitToolIds : this._editExcludedToolIds;
            const availableTools = results.filter(t => !existingIds.includes(t.id));

            if (availableTools.length === 0) {
                showToast('info', 'All matching tools are already in the list');
                return;
            }

            // Show as a simple dropdown under the input
            this._showToolPickerPopup(inputEl, availableTools, listType);
        } catch (error) {
            console.error('Failed to search tools:', error);
            showToast('error', `Search failed: ${error.message}`);
        }
    }

    /**
     * Show a popup with tool results to pick from
     */
    _showToolPickerPopup(inputEl, tools, listType) {
        // Remove any existing popup
        const existingPopup = this.querySelector('.tool-picker-popup');
        if (existingPopup) existingPopup.remove();

        const popup = document.createElement('div');
        popup.className = 'tool-picker-popup card shadow position-absolute';
        popup.style.zIndex = '1060';
        popup.style.maxHeight = '200px';
        popup.style.overflowY = 'auto';
        popup.style.width = '100%';

        popup.innerHTML = `
            <div class="list-group list-group-flush">
                ${tools
                    .slice(0, 10)
                    .map(
                        t => `
                    <button type="button" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
                            data-tool-id="${this._escapeHtml(t.id)}">
                        <span>
                            <strong class="small">${this._escapeHtml(t.tool_name || t.name)}</strong>
                            <br><small class="text-muted">${this._escapeHtml(t.source_name || t.source_id || '')}</small>
                        </span>
                        <i class="bi bi-plus text-primary"></i>
                    </button>
                `
                    )
                    .join('')}
                ${tools.length > 10 ? `<div class="list-group-item text-muted small">+ ${tools.length - 10} more results</div>` : ''}
            </div>
        `;

        // Position popup below input
        const parent = inputEl.closest('.input-group') || inputEl.parentElement;
        parent.style.position = 'relative';
        parent.appendChild(popup);

        // Handle click on tool item
        popup.addEventListener('click', e => {
            const item = e.target.closest('[data-tool-id]');
            if (item) {
                const toolId = item.dataset.toolId;
                if (listType === 'explicit') {
                    this._editExplicitToolIds.push(toolId);
                    this._renderEditExplicitList();
                } else {
                    this._editExcludedToolIds.push(toolId);
                    this._renderEditExcludedList();
                }
                this._updateEditToolPreview();
                popup.remove();
                inputEl.value = '';
            }
        });

        // Close popup when clicking outside
        const closePopup = e => {
            if (!popup.contains(e.target) && e.target !== inputEl) {
                popup.remove();
                document.removeEventListener('click', closePopup);
            }
        };
        setTimeout(() => document.addEventListener('click', closePopup), 0);
    }

    /**
     * Render the explicit tools list
     */
    _renderEditExplicitList() {
        const container = this.querySelector('#edit-explicit-list');
        const countBadge = this.querySelector('#edit-explicit-count');
        if (!container) return;

        const toolIds = this._editExplicitToolIds || [];
        if (countBadge) countBadge.textContent = toolIds.length;

        if (toolIds.length === 0) {
            container.innerHTML = '<div class="text-muted text-center py-2">No explicit tools added</div>';
            return;
        }

        container.innerHTML = toolIds
            .map(
                toolId => `
            <div class="d-flex justify-content-between align-items-center border-bottom py-1">
                <span class="small text-truncate" style="max-width: 80%;">${this._escapeHtml(toolId)}</span>
                <button type="button" class="btn btn-sm btn-link text-danger remove-tool-btn p-0" data-tool-id="${this._escapeHtml(toolId)}">
                    <i class="bi bi-x-circle"></i>
                </button>
            </div>
        `
            )
            .join('');
    }

    /**
     * Render the excluded tools list
     */
    _renderEditExcludedList() {
        const container = this.querySelector('#edit-excluded-list');
        const countBadge = this.querySelector('#edit-excluded-count');
        if (!container) return;

        const toolIds = this._editExcludedToolIds || [];
        if (countBadge) countBadge.textContent = toolIds.length;

        if (toolIds.length === 0) {
            container.innerHTML = '<div class="text-muted text-center py-2">No tools excluded</div>';
            return;
        }

        container.innerHTML = toolIds
            .map(
                toolId => `
            <div class="d-flex justify-content-between align-items-center border-bottom py-1">
                <span class="small text-truncate" style="max-width: 80%;">${this._escapeHtml(toolId)}</span>
                <button type="button" class="btn btn-sm btn-link text-danger remove-tool-btn p-0" data-tool-id="${this._escapeHtml(toolId)}">
                    <i class="bi bi-x-circle"></i>
                </button>
            </div>
        `
            )
            .join('');
    }

    _addEditSelectorRow(type = 'name', pattern = '') {
        const container = this.querySelector('#edit-selectors-container');
        if (!container) return;

        const row = document.createElement('div');
        row.className = 'selector-row row g-2 mb-2';
        row.innerHTML = `
            <div class="col-4">
                <select class="form-select form-select-sm selector-type">
                    <option value="name" ${type === 'name' ? 'selected' : ''}>Name Pattern</option>
                    <option value="method" ${type === 'method' ? 'selected' : ''}>HTTP Method</option>
                    <option value="path" ${type === 'path' ? 'selected' : ''}>Path Pattern</option>
                    <option value="tag" ${type === 'tag' ? 'selected' : ''}>Tag</option>
                    <option value="label" ${type === 'label' ? 'selected' : ''}>Label</option>
                    <option value="source" ${type === 'source' ? 'selected' : ''}>Source</option>
                </select>
            </div>
            <div class="col-6">
                <input type="text" class="form-control form-control-sm selector-pattern"
                       placeholder="e.g., user*" value="${this._escapeHtml(pattern)}">
            </div>
            <div class="col-2">
                <button type="button" class="btn btn-outline-danger btn-sm w-100 remove-selector">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        `;
        container.appendChild(row);
    }

    async _handleSaveGroup(e) {
        e.preventDefault();

        if (!this._editingGroup?.id) return;

        const form = e.target;
        const submitBtn = form.querySelector('#edit-submit-group-btn');
        const spinner = form.querySelector('#edit-submit-spinner');

        const newName = form.querySelector('#edit-group-name').value.trim();
        const newDescription = form.querySelector('#edit-group-description').value.trim();
        const isActive = form.querySelector('#edit-group-active').checked;

        // Collect selectors in UI format (API module handles conversion)
        const selectors = [];
        form.querySelectorAll('.selector-row').forEach(row => {
            const type = row.querySelector('.selector-type').value;
            const pattern = row.querySelector('.selector-pattern').value.trim();
            if (pattern) {
                selectors.push({ type, pattern });
            }
        });

        submitBtn.disabled = true;
        spinner.classList.remove('d-none');

        try {
            // Update name/description
            await GroupsAPI.updateToolGroup(this._editingGroup.id, {
                name: newName,
                description: newDescription || null,
            });

            // Sync selectors (diff-based update)
            await GroupsAPI.syncSelectors(this._editingGroup.id, selectors);

            // Sync explicit and excluded tools (diff-based update)
            await GroupsAPI.syncTools(this._editingGroup.id, this._editExplicitToolIds || [], this._editExcludedToolIds || []);

            // Handle activation/deactivation
            const wasActive = this._editingGroup.status === 'active';
            if (isActive && !wasActive) {
                await GroupsAPI.activateToolGroup(this._editingGroup.id);
            } else if (!isActive && wasActive) {
                await GroupsAPI.deactivateToolGroup(this._editingGroup.id);
            }

            // Close modal
            const modal = bootstrap.Modal.getInstance(this.querySelector('#edit-group-modal'));
            modal.hide();

            showToast('success', `Group "${newName}" updated successfully`);

            // Reload groups to get fresh data
            await this._loadGroups();
        } catch (error) {
            showToast('error', `Failed to update group: ${error.message}`);
        } finally {
            submitBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    }

    // =========================================================================
    // TOOL PREVIEW METHODS
    // =========================================================================

    /**
     * Update tool preview for the create modal
     */
    _updateToolPreview() {
        if (this._previewDebounceTimer) {
            clearTimeout(this._previewDebounceTimer);
        }
        this._previewDebounceTimer = setTimeout(() => {
            this._renderToolPreview('selectors-container', 'tool-preview-container');
        }, 300);
    }

    /**
     * Update tool preview for the edit modal
     */
    _updateEditToolPreview() {
        if (this._previewDebounceTimer) {
            clearTimeout(this._previewDebounceTimer);
        }
        this._previewDebounceTimer = setTimeout(() => {
            this._renderToolPreview('edit-selectors-container', 'edit-tool-preview-container');
        }, 300);
    }

    /**
     * Render tool preview based on selectors in the specified container
     */
    _renderToolPreview(selectorContainerId, previewContainerId) {
        const selectorContainer = this.querySelector(`#${selectorContainerId}`);
        const previewContainer = this.querySelector(`#${previewContainerId}`);

        if (!selectorContainer || !previewContainer) return;

        // Collect selectors
        const selectors = [];
        selectorContainer.querySelectorAll('.selector-row').forEach(row => {
            const type = row.querySelector('.selector-type')?.value;
            const pattern = row.querySelector('.selector-pattern')?.value?.trim();
            if (pattern) {
                selectors.push({ type, pattern });
            }
        });

        if (selectors.length === 0) {
            previewContainer.innerHTML = `
                <div class="text-muted text-center py-3">
                    <i class="bi bi-info-circle me-1"></i>
                    Enter selector patterns above to preview matching tools
                </div>
            `;
            // Update tab badge
            const toolsCountBadge = this.querySelector('#edit-tools-count');
            if (toolsCountBadge) toolsCountBadge.textContent = '0';
            return;
        }

        // Find matching tools (applies explicit inclusions and exclusions)
        const matchingTools = this._findMatchingToolsWithOverrides(selectors);

        // Update tab badge
        const toolsCountBadge = this.querySelector('#edit-tools-count');
        if (toolsCountBadge) toolsCountBadge.textContent = matchingTools.length;

        if (matchingTools.length === 0) {
            previewContainer.innerHTML = `
                <div class="text-warning text-center py-3">
                    <i class="bi bi-exclamation-triangle me-1"></i>
                    No tools match the current selectors
                </div>
            `;
            return;
        }

        // Render matching tools
        const maxDisplay = 10;
        const displayTools = matchingTools.slice(0, maxDisplay);
        const remaining = matchingTools.length - maxDisplay;

        previewContainer.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span class="badge bg-success">${matchingTools.length} tool${matchingTools.length !== 1 ? 's' : ''} matching</span>
            </div>
            <div class="list-group list-group-flush tool-preview-list" style="max-height: 200px; overflow-y: auto;">
                ${displayTools
                    .map(
                        tool => `
                    <div class="list-group-item list-group-item-action py-2 px-3 d-flex justify-content-between align-items-center">
                        <div>
                            <span class="fw-medium">${this._escapeHtml(tool.tool_name)}</span>
                            <small class="text-muted ms-2">${this._escapeHtml(tool.source_name)}</small>
                            ${tool._explicit ? '<i class="bi bi-plus-circle-fill text-success ms-1" title="Explicitly included"></i>' : ''}
                        </div>
                        <div>
                            <span class="badge bg-secondary text-uppercase" style="font-size: 0.65rem;">${tool.method}</span>
                        </div>
                    </div>
                `
                    )
                    .join('')}
                ${
                    remaining > 0
                        ? `
                    <div class="list-group-item py-2 px-3 text-muted text-center">
                        <i class="bi bi-three-dots me-1"></i>
                        and ${remaining} more tool${remaining !== 1 ? 's' : ''}
                    </div>
                `
                        : ''
                }
            </div>
        `;
    }

    /**
     * Find tools that match selectors, including explicit additions and excluding exclusions
     */
    _findMatchingToolsWithOverrides(selectors) {
        if (!this._allTools || this._allTools.length === 0) return [];

        const explicitIds = this._editExplicitToolIds || [];
        const excludedIds = this._editExcludedToolIds || [];

        // Start with selector-matched tools
        const matchedBySelector = this._allTools.filter(tool => {
            // Exclude excluded tools first
            if (excludedIds.includes(tool.id)) return false;
            // A tool matches if ALL selectors match (AND logic)
            return selectors.every(sel => this._toolMatchesSelector(tool, sel));
        });

        // Add explicit tools that aren't already matched
        const matchedIds = new Set(matchedBySelector.map(t => t.id));
        const explicitTools = this._allTools.filter(tool => explicitIds.includes(tool.id) && !matchedIds.has(tool.id) && !excludedIds.includes(tool.id)).map(tool => ({ ...tool, _explicit: true }));

        return [...matchedBySelector, ...explicitTools];
    }

    /**
     * Find tools that match the given selectors (AND logic between selectors)
     */
    _findMatchingTools(selectors) {
        if (!this._allTools || this._allTools.length === 0) return [];

        return this._allTools.filter(tool => {
            // A tool matches if ALL selectors match (AND logic)
            return selectors.every(sel => this._toolMatchesSelector(tool, sel));
        });
    }

    /**
     * Check if a tool matches a single selector
     */
    _toolMatchesSelector(tool, selector) {
        const { type, pattern } = selector;

        switch (type) {
            case 'name':
                return this._matchesPattern(pattern, tool.tool_name);
            case 'method':
                return this._matchesPattern(pattern, tool.method || '');
            case 'path':
                return this._matchesPattern(pattern, tool.path || '');
            case 'tag':
                // Tag matching: check if any tool tag matches the pattern
                const tags = tool.tags || [];
                return tags.some(tag => this._matchesPattern(pattern, tag));
            case 'label':
                // Label matching: check if tool has any of the required label IDs
                const toolLabelIds = tool.label_ids || [];
                const requiredLabels = pattern
                    .split(',')
                    .map(l => l.trim())
                    .filter(l => l);
                return requiredLabels.every(labelId => toolLabelIds.includes(labelId));
            case 'source':
                return this._matchesPattern(pattern, tool.source_name || '');
            default:
                return false;
        }
    }

    /**
     * Check if a value matches a glob-style pattern
     * Supports: * (any chars), ? (single char), regex: prefix
     */
    _matchesPattern(pattern, value) {
        if (!pattern || pattern === '*') return true;
        if (!value) return false;

        // Regex pattern
        if (pattern.startsWith('regex:')) {
            try {
                const regex = new RegExp(pattern.slice(6), 'i');
                return regex.test(value);
            } catch (e) {
                return false;
            }
        }

        // Glob pattern - convert to regex
        const regexPattern = pattern
            .replace(/[.+^${}()|[\]\\]/g, '\\$&') // Escape special chars except * and ?
            .replace(/\*/g, '.*')
            .replace(/\?/g, '.');

        try {
            const regex = new RegExp(`^${regexPattern}$`, 'i');
            return regex.test(value);
        } catch (e) {
            return false;
        }
    }

    // =========================================================================
    // TOOL SELECTOR MODAL METHODS
    // =========================================================================

    _renderToolSelectorModal() {
        return `
            <div class="modal fade" id="tool-selector-modal" tabindex="-1" aria-labelledby="toolSelectorModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="toolSelectorModalLabel">
                                <i class="bi bi-plus-circle me-2"></i>
                                Add Tools to Group
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row g-3 mb-3">
                                <div class="col-12 col-md-4">
                                    <div class="input-group">
                                        <span class="input-group-text"><i class="bi bi-search"></i></span>
                                        <input type="text" class="form-control" placeholder="Search tools..."
                                               id="tool-selector-search">
                                    </div>
                                </div>
                                <div class="col-6 col-md-2">
                                    <select class="form-select" id="tool-selector-method">
                                        <option value="">All Methods</option>
                                        <option value="GET">GET</option>
                                        <option value="POST">POST</option>
                                        <option value="PUT">PUT</option>
                                        <option value="PATCH">PATCH</option>
                                        <option value="DELETE">DELETE</option>
                                    </select>
                                </div>
                                <div class="col-6 col-md-3">
                                    <select class="form-select" id="tool-selector-tag">
                                        <option value="">All Tags</option>
                                    </select>
                                </div>
                                <div class="col-6 col-md-3">
                                    <select class="form-select" id="tool-selector-source">
                                        <option value="">All Sources</option>
                                    </select>
                                </div>
                            </div>

                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="tool-selector-select-all">
                                    <label class="form-check-label" for="tool-selector-select-all">
                                        Select All Filtered
                                    </label>
                                </div>
                                <span class="badge bg-primary" id="tool-selector-count">0 selected</span>
                            </div>

                            <div id="tool-selector-list" class="tool-selector-list border rounded"
                                 style="max-height: 400px; overflow-y: auto;">
                                <!-- Tools will be populated dynamically -->
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="tool-selector-add-btn" disabled>
                                <span class="spinner-border spinner-border-sm d-none me-2" id="tool-selector-spinner"></span>
                                Add Selected Tools
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _showToolSelectorModal(groupId) {
        this._addToolsToGroupId = groupId;
        this._toolSelectorSearchTerm = '';
        this._toolSelectorFilterMethod = null;
        this._toolSelectorFilterTag = null;
        this._toolSelectorFilterSource = null;
        this._toolSelectorSelectedIds.clear();

        // Populate filter dropdowns
        this._populateToolSelectorFilters();

        // Render initial tool list
        this._renderToolSelectorList();

        // Attach event listeners
        this._attachToolSelectorListeners();

        // Show modal
        const modalEl = this.querySelector('#tool-selector-modal');
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
    }

    _populateToolSelectorFilters() {
        // Populate tags dropdown
        const tagSelect = this.querySelector('#tool-selector-tag');
        if (tagSelect) {
            const uniqueTags = [...new Set(this._allTools.flatMap(t => t.tags || []))].sort();
            tagSelect.innerHTML = `
                <option value="">All Tags</option>
                ${uniqueTags.map(tag => `<option value="${this._escapeHtml(tag)}">${this._escapeHtml(tag)}</option>`).join('')}
            `;
        }

        // Populate sources dropdown
        const sourceSelect = this.querySelector('#tool-selector-source');
        if (sourceSelect) {
            const sourceMap = new Map();
            this._allTools.forEach(t => {
                if (t.source_id && !sourceMap.has(t.source_id)) {
                    sourceMap.set(t.source_id, t.source_name || t.source_id);
                }
            });
            const uniqueSources = [...sourceMap.entries()].sort((a, b) => a[1].localeCompare(b[1]));
            sourceSelect.innerHTML = `
                <option value="">All Sources</option>
                ${uniqueSources.map(([id, name]) => `<option value="${this._escapeHtml(id)}">${this._escapeHtml(name)}</option>`).join('')}
            `;
        }
    }

    _getFilteredToolsForSelector() {
        return this._allTools.filter(tool => {
            // Filter by search term
            if (this._toolSelectorSearchTerm) {
                const term = this._toolSelectorSearchTerm.toLowerCase();
                const matches =
                    tool.tool_name?.toLowerCase().includes(term) ||
                    tool.name?.toLowerCase().includes(term) ||
                    tool.description?.toLowerCase().includes(term) ||
                    tool.path?.toLowerCase().includes(term);
                if (!matches) return false;
            }

            // Filter by method
            if (this._toolSelectorFilterMethod && tool.method?.toUpperCase() !== this._toolSelectorFilterMethod) {
                return false;
            }

            // Filter by tag
            if (this._toolSelectorFilterTag && !tool.tags?.includes(this._toolSelectorFilterTag)) {
                return false;
            }

            // Filter by source
            if (this._toolSelectorFilterSource && tool.source_id !== this._toolSelectorFilterSource) {
                return false;
            }

            return true;
        });
    }

    _renderToolSelectorList() {
        const listContainer = this.querySelector('#tool-selector-list');
        if (!listContainer) return;

        const filteredTools = this._getFilteredToolsForSelector();

        if (filteredTools.length === 0) {
            listContainer.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-search me-2"></i>
                    No tools match your filters
                </div>
            `;
            return;
        }

        listContainer.innerHTML = filteredTools
            .map(tool => {
                const isSelected = this._toolSelectorSelectedIds.has(tool.id);
                const displayName = tool.tool_name || getToolDisplayName(tool.id);
                const method = (tool.method || 'GET').toUpperCase();
                const methodClass = getMethodClass(method);

                return `
                <div class="tool-selector-item d-flex align-items-center p-2 border-bottom ${isSelected ? 'bg-primary bg-opacity-10' : ''}"
                     data-tool-id="${this._escapeHtml(tool.id)}">
                    <div class="form-check me-3">
                        <input class="form-check-input tool-selector-checkbox" type="checkbox"
                               data-tool-id="${this._escapeHtml(tool.id)}" ${isSelected ? 'checked' : ''}>
                    </div>
                    <span class="badge ${methodClass} me-2" style="font-size: 0.7rem;">${method}</span>
                    <div class="flex-grow-1 overflow-hidden">
                        <div class="fw-medium text-truncate">${this._escapeHtml(displayName)}</div>
                        <div class="small text-muted text-truncate">${this._escapeHtml(tool.source_name || '')} - ${this._escapeHtml(tool.path || '')}</div>
                    </div>
                </div>
            `;
            })
            .join('');

        // Update count
        this._updateToolSelectorCount();
    }

    _updateToolSelectorCount() {
        const countBadge = this.querySelector('#tool-selector-count');
        const addBtn = this.querySelector('#tool-selector-add-btn');
        const count = this._toolSelectorSelectedIds.size;

        if (countBadge) {
            countBadge.textContent = `${count} selected`;
        }
        if (addBtn) {
            addBtn.disabled = count === 0;
        }
    }

    _attachToolSelectorListeners() {
        // Search input
        const searchInput = this.querySelector('#tool-selector-search');
        if (searchInput) {
            searchInput.value = '';
            searchInput.addEventListener('input', e => {
                this._toolSelectorSearchTerm = e.target.value;
                this._renderToolSelectorList();
            });
        }

        // Method filter
        this.querySelector('#tool-selector-method')?.addEventListener('change', e => {
            this._toolSelectorFilterMethod = e.target.value || null;
            this._renderToolSelectorList();
        });

        // Tag filter
        this.querySelector('#tool-selector-tag')?.addEventListener('change', e => {
            this._toolSelectorFilterTag = e.target.value || null;
            this._renderToolSelectorList();
        });

        // Source filter
        this.querySelector('#tool-selector-source')?.addEventListener('change', e => {
            this._toolSelectorFilterSource = e.target.value || null;
            this._renderToolSelectorList();
        });

        // Select all checkbox
        this.querySelector('#tool-selector-select-all')?.addEventListener('change', e => {
            const isChecked = e.target.checked;
            const filteredTools = this._getFilteredToolsForSelector();

            if (isChecked) {
                filteredTools.forEach(tool => this._toolSelectorSelectedIds.add(tool.id));
            } else {
                filteredTools.forEach(tool => this._toolSelectorSelectedIds.delete(tool.id));
            }

            this._renderToolSelectorList();
        });

        // Individual tool checkboxes (delegated)
        this.querySelector('#tool-selector-list')?.addEventListener('change', e => {
            if (e.target.classList.contains('tool-selector-checkbox')) {
                const toolId = e.target.dataset.toolId;
                if (e.target.checked) {
                    this._toolSelectorSelectedIds.add(toolId);
                } else {
                    this._toolSelectorSelectedIds.delete(toolId);
                }
                this._updateToolSelectorCount();

                // Update row highlight
                const row = e.target.closest('.tool-selector-item');
                if (row) {
                    row.classList.toggle('bg-primary', e.target.checked);
                    row.classList.toggle('bg-opacity-10', e.target.checked);
                }
            }
        });

        // Clicking on row toggles selection
        this.querySelector('#tool-selector-list')?.addEventListener('click', e => {
            const item = e.target.closest('.tool-selector-item');
            if (item && !e.target.classList.contains('form-check-input')) {
                const checkbox = item.querySelector('.tool-selector-checkbox');
                if (checkbox) {
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        });

        // Add button
        this.querySelector('#tool-selector-add-btn')?.addEventListener('click', () => {
            this._handleAddToolsToGroup();
        });
    }

    async _handleAddToolsToGroup() {
        if (!this._addToolsToGroupId || this._toolSelectorSelectedIds.size === 0) return;

        const addBtn = this.querySelector('#tool-selector-add-btn');
        const spinner = this.querySelector('#tool-selector-spinner');

        if (addBtn) addBtn.disabled = true;
        if (spinner) spinner.classList.remove('d-none');

        try {
            const toolIds = [...this._toolSelectorSelectedIds];
            let addedCount = 0;

            for (const toolId of toolIds) {
                try {
                    await GroupsAPI.addExplicitTool(this._addToolsToGroupId, toolId);
                    addedCount++;
                } catch (err) {
                    console.warn(`Failed to add tool ${toolId}:`, err);
                }
            }

            // Close modal
            const modal = bootstrap.Modal.getInstance(this.querySelector('#tool-selector-modal'));
            modal.hide();

            showToast('success', `Added ${addedCount} tool${addedCount !== 1 ? 's' : ''} to group`);

            // Reload groups to refresh data
            await this._loadGroups();
        } catch (error) {
            showToast('error', `Failed to add tools: ${error.message}`);
        } finally {
            if (addBtn) addBtn.disabled = false;
            if (spinner) spinner.classList.add('d-none');
        }
    }

    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

if (!customElements.get('groups-page')) {
    customElements.define('groups-page', GroupsPage);
}

export { GroupsPage };
