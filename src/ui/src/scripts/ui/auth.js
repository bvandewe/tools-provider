/**
 * Authentication UI Module
 * Handles login/logout UI interactions
 */

import { stopSessionMonitoring } from '../core/session-manager.js';

/**
 * Redirect to Keycloak login
 */
export function login() {
    window.location.href = '/api/auth/login';
}

/**
 * Redirect to logout
 */
export function logout() {
    // Stop session monitoring before logout
    stopSessionMonitoring();
    window.location.href = '/api/auth/logout';
}

/**
 * Show login form (hide dashboard)
 */
export function showLoginForm() {
    const loginSection = document.getElementById('login-section');
    const dashboardSection = document.getElementById('dashboard-section');
    const adminDashboard = document.getElementById('admin-dashboard');
    const adminNav = document.getElementById('admin-nav');
    const logoutBtn = document.getElementById('logout-btn');
    const userInfo = document.getElementById('user-info');
    const userDropdown = document.getElementById('user-dropdown');

    // Show login section
    if (loginSection) loginSection.style.display = 'flex';

    // Hide dashboard elements
    if (dashboardSection) dashboardSection.style.display = 'none';
    if (adminDashboard) adminDashboard.style.display = 'none';
    if (adminNav) adminNav.style.display = 'none';
    if (logoutBtn) logoutBtn.style.display = 'none';
    if (userDropdown) userDropdown.style.display = 'none';
    if (userInfo) userInfo.textContent = '';

    // Clear user roles from localStorage on logout
    localStorage.removeItem('user_roles');
}

/**
 * Show dashboard (hide login form)
 * @param {Object} user - User object from auth
 */
export function showDashboard(user) {
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('dashboard-section').style.display = 'block';
    document.getElementById('logout-btn').style.display = 'block';
    document.getElementById('user-info').textContent = `${user.preferred_username || user.email} (${user.email})`;

    // Store user roles in localStorage for UI role checks
    if (user.roles) {
        localStorage.setItem('user_roles', JSON.stringify(user.roles));
    }
}
