/**
 * Theme Switcher - Bootstrap 5.3+ native dark/light mode
 *
 * Uses the data-bs-theme attribute for native Bootstrap theming.
 * Persists preference to localStorage.
 */

const THEME_KEY = 'tools-provider-theme';
const THEME_AUTO = 'auto';
const THEME_LIGHT = 'light';
const THEME_DARK = 'dark';

/**
 * Get stored theme preference
 * @returns {string} 'auto', 'light', or 'dark'
 */
function getStoredTheme() {
    return localStorage.getItem(THEME_KEY) || THEME_AUTO;
}

/**
 * Store theme preference
 * @param {string} theme
 */
function setStoredTheme(theme) {
    localStorage.setItem(THEME_KEY, theme);
}

/**
 * Get the preferred theme based on system preference
 * @returns {string} 'light' or 'dark'
 */
function getPreferredTheme() {
    const stored = getStoredTheme();
    if (stored !== THEME_AUTO) {
        return stored;
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? THEME_DARK : THEME_LIGHT;
}

/**
 * Apply theme to document
 * @param {string} theme - 'light' or 'dark'
 */
function applyTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);

    // Update theme toggle button icon if present
    updateThemeIcon(theme);
}

/**
 * Update the theme toggle button icon
 * @param {string} theme
 */
function updateThemeIcon(theme) {
    const lightIcon = document.querySelector('.theme-icon-light');
    const darkIcon = document.querySelector('.theme-icon-dark');
    const autoIcon = document.querySelector('.theme-icon-auto');

    if (lightIcon) lightIcon.classList.toggle('d-none', theme !== THEME_LIGHT);
    if (darkIcon) darkIcon.classList.toggle('d-none', theme !== THEME_DARK);
    if (autoIcon) autoIcon.classList.toggle('d-none', getStoredTheme() !== THEME_AUTO);

    // Update dropdown active state
    const stored = getStoredTheme();
    document.querySelectorAll('[data-theme-value]').forEach(el => {
        el.classList.toggle('active', el.dataset.themeValue === stored);
        el.setAttribute('aria-pressed', el.dataset.themeValue === stored);
    });
}

/**
 * Set theme and persist preference
 * @param {string} theme - 'auto', 'light', or 'dark'
 */
export function setTheme(theme) {
    setStoredTheme(theme);

    if (theme === THEME_AUTO) {
        applyTheme(getPreferredTheme());
    } else {
        applyTheme(theme);
    }

    // Dispatch custom event for components that need to react
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
}

/**
 * Initialize theme system
 */
export function initTheme() {
    // Apply theme immediately to prevent flash
    applyTheme(getPreferredTheme());

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        if (getStoredTheme() === THEME_AUTO) {
            applyTheme(e.matches ? THEME_DARK : THEME_LIGHT);
        }
    });

    // Set up theme toggle buttons after DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        // Update icons to match current state
        updateThemeIcon(getPreferredTheme());

        // Set up click handlers for theme switcher
        document.querySelectorAll('[data-theme-value]').forEach(el => {
            el.addEventListener('click', e => {
                e.preventDefault();
                const theme = el.dataset.themeValue;
                setTheme(theme);
            });
        });
    });
}

/**
 * Get current theme
 * @returns {string} Current applied theme ('light' or 'dark')
 */
export function getCurrentTheme() {
    return document.documentElement.getAttribute('data-bs-theme') || THEME_LIGHT;
}

/**
 * Get stored theme preference
 * @returns {string} 'auto', 'light', or 'dark'
 */
export function getThemePreference() {
    return getStoredTheme();
}

/**
 * Toggle between light and dark theme
 */
export function toggleTheme() {
    const current = getCurrentTheme();
    setTheme(current === THEME_LIGHT ? THEME_DARK : THEME_LIGHT);
}

// Initialize theme on module load (before DOMContentLoaded)
initTheme();

// Aliases for backward compatibility
export { getCurrentTheme as getTheme };

export { THEME_AUTO, THEME_LIGHT, THEME_DARK };
