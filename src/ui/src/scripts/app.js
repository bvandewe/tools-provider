/**
 * Application Entry Point
 * Main application initialization and event handling
 */

import { checkAuth } from './api/client.js';
import { login, logout, showLoginForm, showDashboard } from './ui/auth.js';
import { loadTasks, initializeDashboard } from './ui/tasks.js';

/**
 * Initialize the application
 */
async function initializeApp() {
    // Check if user is authenticated
    const user = await checkAuth();

    if (user) {
        // User is logged in - show dashboard
        showDashboard(user);
        initializeDashboard();
        await loadTasks();
    } else {
        // Not logged in - show login button
        showLoginForm();
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Login button (redirect to Keycloak)
    const loginBtn = document.getElementById('login-btn');
    if (loginBtn) {
        loginBtn.addEventListener('click', login);
    }

    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
}

/**
 * Application startup
 */
document.addEventListener('DOMContentLoaded', async () => {
    setupEventListeners();
    await initializeApp();
});
