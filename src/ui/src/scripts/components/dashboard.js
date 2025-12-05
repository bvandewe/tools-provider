/**
 * Dashboard Component
 * Manages the main task dashboard functionality
 */

import * as bootstrap from 'bootstrap';
import { fetchTasks, createTask as createTaskAPI, updateTask as updateTaskAPI, deleteTask as deleteTaskAPI, fetchTask } from '../api/tasks.js';
import { showAlert, showConfirm, showSuccessToast } from './modals.js';
import { canEditTask, getCurrentUserRoles } from './permissions.js';

// Singleton instance of the task form modal
let taskFormModal = null;

function getTaskFormModal() {
    if (!taskFormModal) {
        taskFormModal = document.createElement('task-form-modal');
        document.body.appendChild(taskFormModal);

        // Listen for form submission
        taskFormModal.addEventListener('submit-task', handleTaskFormSubmit);
    }
    return taskFormModal;
}

/**
 * Initialize dashboard event listeners
 */
export function initializeDashboard() {
    const createBtn = document.getElementById('open-create-task-btn');
    if (createBtn) {
        createBtn.addEventListener('click', () => {
            const modal = getTaskFormModal();
            modal.mode = 'create';
            modal.resetForm();

            // Set permissions for the form
            const roles = getCurrentUserRoles();
            const isAdmin = roles.includes('admin');
            const isManager = roles.includes('manager');
            modal.setPermissions(isAdmin, isManager);

            modal.show();
        });
    }
}

/**
 * Load and render tasks
 */
export async function loadTasks() {
    try {
        const tasks = await fetchTasks();
        const container = document.getElementById('tasks-container');
        container.innerHTML = ''; // Clear container

        if (tasks.length === 0) {
            container.innerHTML = '<div class="col"><p class="text-muted">No tasks found.</p></div>';
            return;
        }

        tasks.forEach(task => {
            const col = document.createElement('div');
            col.className = 'col-md-6 col-lg-4 mb-4';

            const taskCard = document.createElement('task-card');
            taskCard.task = task;

            // Listen for events from the component
            taskCard.addEventListener('edit-task', e => handleEditTask(e.detail.taskId));
            taskCard.addEventListener('delete-task', e => handleDeleteTask(e.detail.taskId));

            col.appendChild(taskCard);
            container.appendChild(col);
        });

        // Initialize tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    } catch (error) {
        console.error('Failed to load tasks:', error);
        const container = document.getElementById('tasks-container');
        container.innerHTML = '<div class="col"><p class="text-danger">Failed to load tasks. Please try again or contact support.</p></div>';
    }
}

/**
 * Handle task editing
 * @param {string} taskId - Task ID to edit
 */
async function handleEditTask(taskId) {
    try {
        const task = await fetchTask(taskId);

        // Check if user can edit this task
        if (!canEditTask(task)) {
            showAlert('Permission Denied', 'You do not have permission to edit this task.', 'warning');
            return;
        }

        const modal = getTaskFormModal();
        modal.mode = 'edit';
        modal.task = task;

        // Set permissions
        const roles = getCurrentUserRoles();
        const isAdmin = roles.includes('admin');
        const isManager = roles.includes('manager');
        modal.setPermissions(isAdmin, isManager);

        modal.show();
    } catch (error) {
        showAlert('Error Loading Task', 'Failed to load task details: ' + error.message, 'error');
    }
}

/**
 * Handle task form submission (create or update)
 * @param {CustomEvent} e
 */
async function handleTaskFormSubmit(e) {
    const { mode, data } = e.detail;
    const modal = getTaskFormModal();

    try {
        if (mode === 'create') {
            await createTaskAPI(data);
            showSuccessToast('Task created successfully!');
        } else {
            await updateTaskAPI(data.id, data);
            showSuccessToast('Task updated successfully!');
        }

        modal.hide();
        await loadTasks();
    } catch (error) {
        showAlert(`Error ${mode === 'create' ? 'Creating' : 'Updating'} Task`, error.message, 'error');
    }
}

/**
 * Handle task deletion
 * @param {string} taskId - Task ID to delete
 */
async function handleDeleteTask(taskId) {
    showConfirm('Delete Task', 'Are you sure you want to delete this task? This action cannot be undone.', async () => {
        try {
            await deleteTaskAPI(taskId);
            showSuccessToast('Task deleted successfully!');
            await loadTasks();
        } catch (error) {
            showAlert('Error Deleting Task', 'Failed to delete task: ' + error.message, 'error');
        }
    });
}
