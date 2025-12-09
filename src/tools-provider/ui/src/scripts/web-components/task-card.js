import { marked } from 'marked';
import { canEditTask } from '../components/permissions.js';

// Configure marked for safe rendering
marked.setOptions({
    breaks: true,
    gfm: true,
});

export class TaskCard extends HTMLElement {
    constructor() {
        super();
        this._task = null;
    }

    static get observedAttributes() {
        return ['task-id'];
    }

    get task() {
        return this._task;
    }

    set task(value) {
        this._task = value;
        this.render();
    }

    connectedCallback() {
        if (!this._task) {
            // If task is not set via property, try to parse from attribute if we supported that
            // But for complex objects, property is better.
        }
    }

    render() {
        if (!this._task) return;

        const task = this._task;
        const priorityBadge =
            {
                low: 'success',
                medium: 'warning',
                high: 'danger',
            }[task.priority] || 'secondary';

        const statusBadge =
            {
                pending: 'secondary',
                in_progress: 'info',
                completed: 'success',
            }[task.status] || 'secondary';

        const canEdit = canEditTask(task);
        const departmentBadge = task.department || '';

        // Format timestamps for tooltip
        const createdAt = new Date(task.created_at).toLocaleString();
        const updatedAt = task.updated_at ? new Date(task.updated_at).toLocaleString() : 'Never';
        const tooltipText = `<strong>Created:</strong> ${createdAt}<br><strong>Updated:</strong> ${updatedAt}`;

        // Create card footer with action icons
        let cardFooter = '';
        if (canEdit) {
            // Assuming showDeleteButton logic is handled by canEdit or passed in.
            // The original code had showDeleteButton param.
            // Let's assume if you can edit, you can delete for now, or add a property.
            const editIcon = canEdit
                ? `
                <i class="bi bi-pencil text-primary edit-task-icon"
                   role="button"
                   title="Edit Task"></i>`
                : '';

            const deleteIcon = canEdit // Using canEdit as proxy for delete permission for simplicity, or check permissions
                ? `
                <i class="bi bi-trash text-danger delete-task-icon"
                   role="button"
                   title="Delete Task"></i>`
                : '';

            if (editIcon || deleteIcon) {
                cardFooter = `
                    <div class="card-footer bg-transparent border-top-0 d-flex justify-content-end gap-2">
                        ${editIcon}
                        ${deleteIcon}
                    </div>
                `;
            }
        }

        this.innerHTML = `
            <div class="card h-100 shadow-sm task-card" data-task-id="${task.id}">
                <div class="card-header d-flex justify-content-between align-items-center bg-transparent">
                    <span class="badge bg-${priorityBadge} bg-opacity-10 text-${priorityBadge} border border-${priorityBadge}">
                        ${task.priority.toUpperCase()}
                    </span>
                    <span class="badge bg-${statusBadge}">${task.status.replace('_', ' ').toUpperCase()}</span>
                </div>
                <div class="card-body">
                    <h5 class="card-title text-truncate" title="${task.title}">${task.title}</h5>
                    ${departmentBadge ? `<h6 class="card-subtitle mb-2 text-muted"><small><i class="bi bi-building me-1"></i>${departmentBadge}</small></h6>` : ''}
                    <div class="card-text task-description mt-3">
                        ${marked.parse(task.description || '')}
                    </div>
                </div>
                <div class="card-footer bg-light text-muted small">
                    <div class="d-flex justify-content-between align-items-center">
                        <span data-bs-toggle="tooltip" data-bs-html="true" title="${tooltipText}">
                            <i class="bi bi-clock me-1"></i>${new Date(task.created_at).toLocaleDateString()}
                        </span>
                        ${task.assignee_id ? `<span title="Assignee: ${task.assignee_id}"><i class="bi bi-person me-1"></i>${task.assignee_id}</span>` : ''}
                    </div>
                </div>
                ${cardFooter}
            </div>
        `;

        // Add event listeners
        const editBtn = this.querySelector('.edit-task-icon');
        if (editBtn) {
            editBtn.addEventListener('click', e => {
                e.stopPropagation();
                this.dispatchEvent(
                    new CustomEvent('edit-task', {
                        detail: { taskId: task.id },
                        bubbles: true,
                    })
                );
            });
        }

        const deleteBtn = this.querySelector('.delete-task-icon');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', e => {
                e.stopPropagation();
                this.dispatchEvent(
                    new CustomEvent('delete-task', {
                        detail: { taskId: task.id },
                        bubbles: true,
                    })
                );
            });
        }

        // Initialize tooltips
        // Note: Bootstrap tooltips need to be initialized manually.
        // Since we are in a component, we might need to do this carefully.
        // For now, we'll rely on the global tooltip initialization or do it here if we import bootstrap.
        // But importing bootstrap JS here might be redundant if it's already in main.
    }
}

customElements.define('task-card', TaskCard);
