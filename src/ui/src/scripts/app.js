/**
 * Application Entry Point
 * Main application initialization and event handling
 */

import { checkAuth } from './api/client.js';
import { login, logout, showLoginForm, showDashboard } from './ui/auth.js';
import { loadTasks, initializeDashboard } from './ui/tasks.js';
import { eventBus } from './core/event-bus.js';
import { getTheme, setTheme } from './core/theme.js';
import { startSessionMonitoring, stopSessionMonitoring } from './core/session-manager.js';

// Current page state
let currentPage = 'sources';

/**
 * Get the app name from the navbar brand
 */
function getAppName() {
    const navbarBrand = document.querySelector('.navbar-brand span');
    return navbarBrand?.textContent?.trim() || 'MCP Tools Provider';
}

/**
 * Update page/tab title
 */
function updatePageTitle(pageName = null) {
    const appName = getAppName();
    if (pageName) {
        document.title = `${pageName} - ${appName}`;
    } else {
        document.title = appName;
    }
}

/**
 * Update the login section title with app name
 */
function updateLoginTitle() {
    const appName = getAppName();
    const loginTitle = document.getElementById('login-title');
    if (loginTitle) {
        loginTitle.textContent = `Welcome to ${appName}`;
    }
    // Also update page title for login page
    updatePageTitle();
}

/**
 * Initialize the application
 */
async function initializeApp() {
    // Update login title with app name
    updateLoginTitle();

    // Fetch and display app version in footer
    fetchAppVersion();

    // Check if user is authenticated
    const user = await checkAuth();

    if (user) {
        // User is logged in - show admin dashboard
        showAdminDashboard(user);

        // Connect to SSE for real-time updates
        eventBus.connect();

        // Start session monitoring for expiration warnings
        startSessionMonitoring();

        // Update connection status indicator
        eventBus.subscribe('connected', () => updateConnectionStatus(true));
        eventBus.subscribe('disconnected', () => updateConnectionStatus(false));
    } else {
        // Not logged in - show login button
        showLoginForm();
    }
}

/**
 * Show the admin dashboard
 */
function showAdminDashboard(user) {
    // Hide login section
    const loginSection = document.getElementById('login-section');
    if (loginSection) loginSection.style.display = 'none';

    // Show admin dashboard
    const adminDashboard = document.getElementById('admin-dashboard');
    if (adminDashboard) adminDashboard.style.display = 'block';

    // Show admin navigation
    const adminNav = document.getElementById('admin-nav');
    if (adminNav) adminNav.style.display = 'flex';

    // Show user dropdown
    const userDropdown = document.getElementById('user-dropdown');
    if (userDropdown) {
        userDropdown.style.display = 'block';

        const userName = document.getElementById('user-name');
        if (userName) userName.textContent = user.name || user.preferred_username || 'User';
    }

    // Hide login button
    const loginBtn = document.getElementById('login-btn');
    if (loginBtn) loginBtn.style.display = 'none';

    // Navigate to default page
    navigateToPage('sources');
}

/**
 * Navigate to a specific page
 */
function navigateToPage(pageName) {
    const pageContent = document.getElementById('page-content');
    if (!pageContent) return;

    // Update navigation active state
    document.querySelectorAll('#admin-nav .nav-link').forEach(link => {
        link.classList.toggle('active', link.dataset.page === pageName);
    });

    // Create the appropriate page component
    const pageComponents = {
        sources: 'sources-page',
        tools: 'tools-page',
        groups: 'groups-page',
        policies: 'policies-page',
        labels: 'labels-page',
        admin: 'admin-page',
    };

    // Display names for page titles
    const pageDisplayNames = {
        sources: 'Sources',
        tools: 'Tools',
        groups: 'Groups',
        policies: 'Policies',
        labels: 'Labels',
        admin: 'Admin',
    };

    const componentName = pageComponents[pageName];
    if (componentName) {
        pageContent.innerHTML = `<${componentName}></${componentName}>`;
        currentPage = pageName;

        // Update page title
        updatePageTitle(pageDisplayNames[pageName] || pageName);
    }
}

/**
 * Update the connection status indicator
 */
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connection-status');
    if (!statusEl) return;

    if (connected) {
        statusEl.className = 'connection-indicator text-success';
        statusEl.innerHTML = '<i class="bi bi-wifi"></i>';
        statusEl.title = 'Connected - receiving real-time updates';
    } else {
        statusEl.className = 'connection-indicator text-secondary';
        statusEl.innerHTML = '<i class="bi bi-wifi-off"></i>';
        statusEl.title = 'Disconnected - reconnecting...';
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
        logoutBtn.addEventListener('click', e => {
            e.preventDefault();
            eventBus.disconnect();
            stopSessionMonitoring();
            logout();
        });
    }

    // Navigation tabs
    document.querySelectorAll('#admin-nav .nav-link').forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            const page = link.dataset.page;
            if (page) {
                navigateToPage(page);
            }
        });
    });

    // Cross-entity navigation events (e.g., from Group modal to Tool details)
    document.addEventListener('navigate-to-entity', e => {
        const { page, action, data } = e.detail;
        if (page) {
            // Navigate to the target page
            navigateToPage(page);

            // After a short delay to let the page render, trigger the modal action
            setTimeout(() => {
                const pageEl = document.querySelector(`${page}-page`);
                if (pageEl && action) {
                    pageEl.dispatchEvent(
                        new CustomEvent(`open-${action}`, {
                            detail: data,
                            bubbles: false,
                        })
                    );
                }
            }, 100);
        }
    });

    // Theme toggle
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = getTheme();
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            setTheme(newTheme);
            updateThemeIcons(newTheme);
        });

        // Initialize icons based on current theme
        updateThemeIcons(getTheme());
    }
}

/**
 * Update theme toggle icons
 */
function updateThemeIcons(theme) {
    const lightIcon = document.querySelector('.theme-icon-light');
    const darkIcon = document.querySelector('.theme-icon-dark');

    if (lightIcon && darkIcon) {
        if (theme === 'dark') {
            lightIcon.classList.add('d-none');
            darkIcon.classList.remove('d-none');
        } else {
            lightIcon.classList.remove('d-none');
            darkIcon.classList.add('d-none');
        }
    }
}

/**
 * Fetch and display app version from API
 */
async function fetchAppVersion() {
    const versionEl = document.getElementById('app-version');
    if (!versionEl) return;

    try {
        const response = await fetch('/health');
        if (response.ok) {
            const data = await response.json();
            versionEl.textContent = data.service?.version || data.version || '-';
        }
    } catch (error) {
        console.error('Failed to fetch app version:', error);
        versionEl.textContent = '-';
    }
}

/**
 * Application startup
 */
document.addEventListener('DOMContentLoaded', async () => {
    setupEventListeners();
    await initializeApp();
});
