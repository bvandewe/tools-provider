import * as bootstrap from 'bootstrap';

export class TaskFormModal extends HTMLElement {
    constructor() {
        super();
        this.modalInstance = null;
        this._mode = 'create'; // 'create' or 'edit'
        this._task = null;
    }

    connectedCallback() {
        this.render();
        this.setupEventListeners();
    }

    set mode(value) {
        this._mode = value;
        this.updateTitle();
    }

    get mode() {
        return this._mode;
    }

    set task(value) {
        this._task = value;
        if (value) {
            this.populateForm(value);
        }
    }

    get task() {
        return this._task;
    }

    render() {
        this.innerHTML = `
            <div class="modal fade" id="taskFormModal" tabindex="-1">
                <div class="modal-dialog modal-dialog-scrollable modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="modalTitle">Create New Task</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="task-form" class="d-flex flex-column h-100">
                                <input type="hidden" id="task-id">
                                <div class="mb-3">
                                    <label for="task-title" class="form-label">Title</label>
                                    <input type="text" class="form-control" id="task-title" required>
                                </div>
                                <div class="mb-3 flex-grow-1 d-flex flex-column">
                                    <label for="task-description" class="form-label">Description</label>
                                    <textarea class="form-control flex-grow-1" id="task-description" required
                                        placeholder="You can use markdown formatting:&#10;- **bold** for bold text&#10;- *italic* for italic text&#10;- # Heading for headers&#10;- - item for lists"></textarea>
                                    <small class="form-text text-muted">Supports Markdown formatting</small>
                                </div>
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <label for="task-priority" class="form-label">Priority</label>
                                        <select class="form-select" id="task-priority">
                                            <option value="low">Low</option>
                                            <option value="medium" selected>Medium</option>
                                            <option value="high">High</option>
                                        </select>
                                    </div>
                                    <div class="col-md-6">
                                        <label for="task-status" class="form-label">Status</label>
                                        <select class="form-select" id="task-status">
                                            <option value="pending" selected>Pending</option>
                                            <option value="in_progress">In Progress</option>
                                            <option value="completed">Completed</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="row mb-3">
                                    <div class="col-md-6" id="department-section">
                                        <label for="task-department" class="form-label">Department</label>
                                        <input type="text" class="form-control" id="task-department"
                                            placeholder="Leave empty for no department">
                                        <div class="form-text">Enter the department for this task</div>
                                    </div>
                                    <div class="col-md-6" id="assignee-section">
                                        <label for="task-assignee" class="form-label">Assignee ID</label>
                                        <input type="text" class="form-control" id="task-assignee"
                                            placeholder="Leave empty for unassigned">
                                        <div class="form-text">Enter the user ID to assign this task to</div>
                                    </div>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="submit-btn">Create Task</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.modalElement = this.querySelector('#taskFormModal');
        this.modalInstance = new bootstrap.Modal(this.modalElement);
    }

    setupEventListeners() {
        const submitBtn = this.querySelector('#submit-btn');
        submitBtn.addEventListener('click', () => this.handleSubmit());
    }

    updateTitle() {
        const titleEl = this.querySelector('#modalTitle');
        const submitBtn = this.querySelector('#submit-btn');
        if (this._mode === 'edit') {
            titleEl.textContent = 'Edit Task';
            submitBtn.textContent = 'Update Task';
        } else {
            titleEl.textContent = 'Create New Task';
            submitBtn.textContent = 'Create Task';
        }
    }

    populateForm(task) {
        this.querySelector('#task-id').value = task.id || '';
        this.querySelector('#task-title').value = task.title || '';
        this.querySelector('#task-description').value = task.description || '';
        this.querySelector('#task-priority').value = task.priority || 'medium';
        this.querySelector('#task-status').value = task.status || 'pending';
        this.querySelector('#task-department').value = task.department || '';
        this.querySelector('#task-assignee').value = task.assignee_id || '';
    }

    resetForm() {
        this.querySelector('#task-form').reset();
        this.querySelector('#task-id').value = '';
        this._task = null;
    }

    show() {
        this.modalInstance.show();
    }

    hide() {
        this.modalInstance.hide();
    }

    handleSubmit() {
        const formData = {
            title: this.querySelector('#task-title').value,
            description: this.querySelector('#task-description').value,
            priority: this.querySelector('#task-priority').value,
            status: this.querySelector('#task-status').value,
            department: this.querySelector('#task-department').value || null,
            assignee_id: this.querySelector('#task-assignee').value || null,
        };

        if (this._mode === 'edit') {
            formData.id = this.querySelector('#task-id').value;
        }

        this.dispatchEvent(
            new CustomEvent('submit-task', {
                detail: {
                    mode: this._mode,
                    data: formData,
                },
                bubbles: true,
            })
        );
    }

    setPermissions(isAdmin, isManager) {
        const assigneeSection = this.querySelector('#assignee-section');
        const departmentSection = this.querySelector('#department-section');

        if (assigneeSection) {
            assigneeSection.style.display = isAdmin || isManager ? 'block' : 'none';
        }
        if (departmentSection) {
            departmentSection.style.display = isAdmin ? 'block' : 'none';
        }
    }
}

customElements.define('task-form-modal', TaskFormModal);
