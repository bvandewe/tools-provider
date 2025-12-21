/**
 * Services Module - External Services and Side Effects
 *
 * Provides services for interacting with external systems:
 * - api: HTTP API client
 * - auth: Authentication and session management
 * - theme: Theme switching
 * - modals: Bootstrap modal management
 * - settings: Admin settings
 */

// API client
export { api } from './api.js';

// Auth service
export {
    checkAuth,
    getCurrentUser,
    isAuthenticated,
    isAdmin,
    getUserScopes,
    getUserDisplayName,
    startSessionMonitoring,
    stopSessionMonitoring,
    handleSessionExpired,
    setUnauthorizedHandler,
    logout,
    getLoginUrl,
    getLogoutUrl,
} from './auth.js';

// Theme service
export {
    getTheme,
    setTheme,
    toggleTheme,
    initTheme,
} from './theme.js';

// Modal service
export {
    initModals,
    showToolsModal,
    showToast,
    showHealthModal,
    showPermissionsModal,
    showRenameModal,
    showDeleteModal,
    showDeleteAllUnpinnedModal,
} from './modals.js';

// Settings service (admin only)
export {
    initSettings,
    updateAdminButtonVisibility,
} from './settings.js';
