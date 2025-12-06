/**
 * Theme Service
 * Handles Bootstrap dark/light theme switching with persistence
 */

const THEME_KEY = 'theme';
const THEME_LIGHT = 'light';
const THEME_DARK = 'dark';

/**
 * Get the current theme
 * @returns {string} 'light' or 'dark'
 */
export function getTheme() {
    return document.documentElement.getAttribute('data-bs-theme') || THEME_LIGHT;
}

/**
 * Set the theme
 * @param {string} theme - 'light' or 'dark'
 */
export function setTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
    updateThemeIcons(theme);

    // Re-render web components that use shadow DOM (they need to update their styles)
    document.querySelectorAll('chat-message, tool-call-card').forEach(el => {
        if (el.render) {
            el.render();
        }
    });
}

/**
 * Toggle between light and dark theme
 * @returns {string} The new theme
 */
export function toggleTheme() {
    const current = getTheme();
    const newTheme = current === THEME_LIGHT ? THEME_DARK : THEME_LIGHT;
    setTheme(newTheme);
    return newTheme;
}

/**
 * Update theme toggle button icons
 * @param {string} theme - Current theme
 */
function updateThemeIcons(theme) {
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
 * Initialize theme functionality
 * Sets up toggle button and syncs icons with current theme
 */
export function initTheme() {
    // Sync icons with current theme (already set by inline script)
    const currentTheme = getTheme();
    updateThemeIcons(currentTheme);

    // Set up toggle button
    const toggleBtn = document.getElementById('theme-toggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            toggleTheme();
        });
    }

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        // Only auto-switch if user hasn't set a preference
        if (!localStorage.getItem(THEME_KEY)) {
            setTheme(e.matches ? THEME_DARK : THEME_LIGHT);
        }
    });
}

export default {
    getTheme,
    setTheme,
    toggleTheme,
    initTheme,
};
