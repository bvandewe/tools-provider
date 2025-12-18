/**
 * Admin Main Entry Point
 *
 * Initializes the admin page and manages page navigation.
 */

import * as bootstrap from 'bootstrap';

// Make bootstrap available globally for modals
window.bootstrap = bootstrap;

import { initTheme } from '../services/theme.js';
import { api } from '../services/api.js';
import { DefinitionsManager } from './definitions-manager.js';
import { SettingsManager } from './settings-manager.js';
import { TemplatesManager } from './templates-manager.js';

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new AdminApp();
    app.init();
});

/**
 * Main admin application controller
 */
class AdminApp {
    constructor() {
        this.currentPage = 'definitions';
        this.user = null;
        this.definitionsManager = null;
        this.settingsManager = null;
        this.templatesManager = null;
    }

    async init() {
        console.log('🔧 Initializing Admin Panel...');

        // Initialize theme
        initTheme();

        // Check authentication
        await this.checkAuth();

        // Setup navigation
        this.setupNavigation();

        // Setup logout
        this.setupLogout();
    }

    async checkAuth() {
        try {
            // Use the same auth check as the main chat app
            const authData = await api.checkAuth();
            this.user = authData.user || authData || {};

            // Check if user has admin role
            const roles = this.user.roles || [];
            if (!roles.includes('admin')) {
                this.showAccessDenied();
                return;
            }

            this.showDashboard();

            // Initialize managers
            this.definitionsManager = new DefinitionsManager();
            await this.definitionsManager.init();

            this.settingsManager = new SettingsManager();
            this.settingsManager.init();

            this.templatesManager = new TemplatesManager();
            await this.templatesManager.init();
        } catch (error) {
            console.error('Auth check failed:', error);
            this.showLogin();
        }
    }

    showLogin() {
        document.getElementById('login-section').style.display = 'block';
        document.getElementById('admin-dashboard').style.display = 'none';
        document.getElementById('access-denied-section').style.display = 'none';

        // Setup login button
        const loginBtn = document.getElementById('login-btn');
        if (loginBtn) {
            loginBtn.addEventListener('click', () => {
                window.location.href = '/api/auth/login?return_url=/admin';
            });
        }
    }

    showDashboard() {
        document.getElementById('login-section').style.display = 'none';
        document.getElementById('admin-dashboard').style.display = 'block';
        document.getElementById('access-denied-section').style.display = 'none';

        // Update user name
        const userName = document.getElementById('user-name');
        if (userName && this.user) {
            userName.textContent = this.user.name || this.user.preferred_username || 'User';
        }
    }

    showAccessDenied() {
        document.getElementById('login-section').style.display = 'none';
        document.getElementById('admin-dashboard').style.display = 'none';
        document.getElementById('access-denied-section').style.display = 'block';
    }

    setupNavigation() {
        const navLinks = document.querySelectorAll('#admin-nav .nav-link');

        navLinks.forEach(link => {
            link.addEventListener('click', e => {
                e.preventDefault();
                const page = link.dataset.page;
                if (page) {
                    this.navigateTo(page);
                }
            });
        });
    }

    navigateTo(page) {
        // Update nav active state
        const navLinks = document.querySelectorAll('#admin-nav .nav-link');
        navLinks.forEach(link => {
            link.classList.toggle('active', link.dataset.page === page);
        });

        // Hide all pages
        const pages = document.querySelectorAll('.admin-page');
        pages.forEach(p => (p.style.display = 'none'));

        // Show selected page
        const selectedPage = document.getElementById(`${page}-page`);
        if (selectedPage) {
            selectedPage.style.display = 'block';
        }

        this.currentPage = page;
    }

    setupLogout() {
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', e => {
                e.preventDefault();
                // Use the same logout flow as the main chat page
                // This redirects to /api/auth/logout which properly cleans up the server session
                api.logout();
            });
        }
    }
}
