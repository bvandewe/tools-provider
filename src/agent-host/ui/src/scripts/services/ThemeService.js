/**
 * ThemeService - Theme Management
 *
 * Handles Bootstrap dark/light theme switching with persistence.
 *
 * @module services/ThemeService
 */

/**
 * Theme constants
 */
const THEME_KEY = 'theme';
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

        // Sync icons with current theme (already set by inline script)
        const currentTheme = this.getTheme();
        this._updateThemeIcons(currentTheme);

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

    // =========================================================================
    // Theme Operations
    // =========================================================================

    /**
     * Get the current theme
     * @returns {string} 'light' or 'dark'
     */
    getTheme() {
        return document.documentElement.getAttribute('data-bs-theme') || THEME_LIGHT;
    }

    /**
     * Set the theme
     * @param {string} theme - 'light' or 'dark'
     */
    async setTheme(theme) {
        console.log(`[ThemeService] Setting theme to: ${theme}`);
        document.documentElement.setAttribute('data-bs-theme', theme);
        localStorage.setItem(THEME_KEY, theme);
        this._updateThemeIcons(theme);

        // Re-render web components that use shadow DOM (they need to update their styles)
        // Include chat components
        document.querySelectorAll('chat-message, tool-call-card').forEach(el => {
            if (el.render) {
                el.render();
            }
        });

        // Re-render all ax-* widget components (they use theme-dependent inline styles)
        // Also include ax-conversation-header for the header bar
        // Use refreshTheme() which reloads styles AND re-renders
        const widgets = document.querySelectorAll(
            'ax-conversation-header, ax-text-display, ax-image-display, ax-multiple-choice, ax-free-text-prompt, ax-code-editor, ax-slider, ax-checkbox-group, ax-dropdown, ax-rating, ax-date-picker, ax-matrix-choice, ax-drag-drop, ax-hotspot, ax-drawing, ax-submit-button, ax-progress-bar, ax-timer, ax-chart, ax-data-table, ax-iframe-widget'
        );
        console.log(`[ThemeService] Found ${widgets.length} widgets to update`);

        // Collect all refresh promises and await them
        const refreshPromises = [];
        widgets.forEach(el => {
            if (el.refreshTheme) {
                console.log(`[ThemeService] Calling refreshTheme on ${el.tagName}`);
                const result = el.refreshTheme();
                // If it returns a promise, collect it
                if (result && typeof result.then === 'function') {
                    refreshPromises.push(result);
                }
            } else if (el.render) {
                console.log(`[ThemeService] Calling render on ${el.tagName}`);
                el.render();
            }
        });

        // Wait for all async refreshes to complete
        if (refreshPromises.length > 0) {
            await Promise.all(refreshPromises);
            console.log(`[ThemeService] All ${refreshPromises.length} async refreshes completed`);
        }
    }

    /**
     * Toggle between light and dark theme
     * @returns {string} The new theme
     */
    toggleTheme() {
        const current = this.getTheme();
        const newTheme = current === THEME_LIGHT ? THEME_DARK : THEME_LIGHT;
        this.setTheme(newTheme);
        return newTheme;
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
        const lightIcon = document.getElementById('theme-icon-light');
        const darkIcon = document.getElementById('theme-icon-dark');

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
     * Handle system theme change
     * @private
     * @param {MediaQueryListEvent} e - Media query change event
     */
    _handleSystemThemeChange(e) {
        // Only auto-switch if user hasn't set a preference
        if (!localStorage.getItem(THEME_KEY)) {
            this.setTheme(e.matches ? THEME_DARK : THEME_LIGHT);
        }
    }

    // =========================================================================
    // Cleanup
    // =========================================================================

    /**
     * Cleanup resources
     */
    destroy() {
        if (this._mediaQuery) {
            this._mediaQuery.removeEventListener('change', this._handleSystemThemeChange);
            this._mediaQuery = null;
        }
        this._initialized = false;
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const themeService = new ThemeService();
