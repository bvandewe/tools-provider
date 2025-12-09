/**
 * Tasks UI Module
 * Re-exports from modular components for backward compatibility
 */

export { loadTasks, initializeDashboard } from '../components/dashboard.js';
export { showAlert, showConfirm, showSuccessToast } from '../components/modals.js';
export { getCurrentUserRoles, canEditTask, canDeleteTasks } from '../components/permissions.js';
