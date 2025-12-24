/**
 * ThemeService - Theme Management
 *
 * Handles Bootstrap dark/light theme switching with persistence.
 *
 * @module services/ThemeService
 */

import { stateManager, StateKeys } from '../core/state-manager.js';

/**
 * Theme constants
 */
const THEME_KEY = 'km-theme';
const THEME_LIGHT = 'light';
const THEME_DARK = 'dark';

/**
 * ThemeService manages application theme (light/dark mode)
 */
export class ThemeService {
    /**
     * Create a new ThemeService instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {MediaQueryList|null} */
        this._mediaQuery = null;

        // Bind methods for callbacks
        this._handleSystemThemeChange = this._handleSystemThemeChange.bind(this);
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize theme functionality
     * Sets up toggle button and syncs icons with current theme
     */
    init() {
        if (this._initialized) {
            console.warn('[ThemeService] Already initialized');
            return;
        }

        // Sync icons with current theme (already set by inline script if present)
        const currentTheme = this.getTheme();
        this._updateThemeIcons(currentTheme);
        stateManager.set(StateKeys.THEME, currentTheme);

        // Set up toggle button
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                this.toggleTheme();
            });
        }

        // Listen for system theme changes
        this._mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        this._mediaQuery.addEventListener('change', this._handleSystemThemeChange);

        this._initialized = true;
        console.log('[ThemeService] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        if (this._mediaQuery) {
            this._mediaQuery.removeEventListener('change', this._handleSystemThemeChange);
            this._mediaQuery = null;
        }
        this._initialized = false;
        console.log('[ThemeService] Destroyed');
    }

    // =========================================================================
    // Theme Operations
    // =========================================================================

    /**
     * Get the current theme
     * @returns {string} 'light' or 'dark'
     */
    getTheme() {
        // Check localStorage first, then document attribute, then system preference
        const savedTheme = localStorage.getItem(THEME_KEY);
        if (savedTheme) return savedTheme;

        const docTheme = document.documentElement.getAttribute('data-bs-theme');
        if (docTheme) return docTheme;

        // Fall back to system preference
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        return systemPrefersDark ? THEME_DARK : THEME_LIGHT;
    }

    /**
     * Set the theme
     * @param {string} theme - 'light' or 'dark'
     */
    setTheme(theme) {
        console.log(`[ThemeService] Setting theme to: ${theme}`);
        document.documentElement.setAttribute('data-bs-theme', theme);
        localStorage.setItem(THEME_KEY, theme);
        this._updateThemeIcons(theme);
        stateManager.set(StateKeys.THEME, theme);
    }

    /**
     * Toggle between light and dark theme
     */
    toggleTheme() {
        const currentTheme = this.getTheme();
        const newTheme = currentTheme === THEME_DARK ? THEME_LIGHT : THEME_DARK;
        this.setTheme(newTheme);
    }

    // =========================================================================
    // Private Methods
    // =========================================================================

    /**
     * Update theme toggle button icons
     * @private
     * @param {string} theme - Current theme
     */
    _updateThemeIcons(theme) {
        const lightIcon = document.querySelector('.theme-icon-light');
        const darkIcon = document.querySelector('.theme-icon-dark');

        if (lightIcon && darkIcon) {
            if (theme === THEME_DARK) {
                lightIcon.classList.add('d-none');
                darkIcon.classList.remove('d-none');
            } else {
                lightIcon.classList.remove('d-none');
                darkIcon.classList.add('d-none');
            }
        }
    }

    /**
     * Handle system theme preference change
     * @private
     * @param {MediaQueryListEvent} e
     */
    _handleSystemThemeChange(e) {
        // Only apply if user hasn't explicitly set a preference
        if (!localStorage.getItem(THEME_KEY)) {
            this.setTheme(e.matches ? THEME_DARK : THEME_LIGHT);
        }
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const themeService = new ThemeService();
