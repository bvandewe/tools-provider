/**
 * DOM Utilities - Pure DOM helper functions
 *
 * @module utils/dom
 */

// =============================================================================
// Constants
// =============================================================================

export const MOBILE_BREAKPOINT = 992;

// =============================================================================
// HTML Helpers
// =============================================================================

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML
 */
export function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Parse HTML string into DOM elements
 * @param {string} html - HTML string
 * @returns {DocumentFragment} Parsed elements
 */
export function parseHtml(html) {
    const template = document.createElement('template');
    template.innerHTML = html.trim();
    return template.content;
}

/**
 * Create an element with attributes and children
 * @param {string} tag - Element tag name
 * @param {Object} [attrs={}] - Attributes to set
 * @param {(string|Node)[]} [children=[]] - Child nodes or text
 * @returns {HTMLElement} Created element
 */
export function createElement(tag, attrs = {}, children = []) {
    const el = document.createElement(tag);

    Object.entries(attrs).forEach(([key, value]) => {
        if (key === 'className') {
            el.className = value;
        } else if (key === 'style' && typeof value === 'object') {
            Object.assign(el.style, value);
        } else if (key.startsWith('on') && typeof value === 'function') {
            el.addEventListener(key.slice(2).toLowerCase(), value);
        } else if (key === 'dataset' && typeof value === 'object') {
            Object.entries(value).forEach(([k, v]) => {
                el.dataset[k] = v;
            });
        } else {
            el.setAttribute(key, value);
        }
    });

    children.forEach(child => {
        if (typeof child === 'string') {
            el.appendChild(document.createTextNode(child));
        } else if (child instanceof Node) {
            el.appendChild(child);
        }
    });

    return el;
}

// =============================================================================
// Query Helpers
// =============================================================================

/**
 * Shorthand for querySelector
 * @param {string} selector - CSS selector
 * @param {ParentNode} [parent=document] - Parent element
 * @returns {Element|null} Found element
 */
export function $(selector, parent = document) {
    return parent.querySelector(selector);
}

/**
 * Shorthand for querySelectorAll returning array
 * @param {string} selector - CSS selector
 * @param {ParentNode} [parent=document] - Parent element
 * @returns {Element[]} Found elements
 */
export function $$(selector, parent = document) {
    return Array.from(parent.querySelectorAll(selector));
}

// =============================================================================
// Visibility & Scroll Helpers
// =============================================================================

/**
 * Show an element by removing d-none class
 * @param {Element} el - Element to show
 */
export function show(el) {
    if (el) el.classList.remove('d-none');
}

/**
 * Hide an element by adding d-none class
 * @param {Element} el - Element to hide
 */
export function hide(el) {
    if (el) el.classList.add('d-none');
}

/**
 * Toggle element visibility
 * @param {Element} el - Element to toggle
 * @param {boolean} [visible] - Force visible state
 */
export function toggle(el, visible) {
    if (el) {
        if (visible === undefined) {
            el.classList.toggle('d-none');
        } else {
            el.classList.toggle('d-none', !visible);
        }
    }
}

/**
 * Scroll element to bottom
 * @param {Element} el - Element to scroll
 * @param {boolean} [smooth=true] - Use smooth scrolling
 */
export function scrollToBottom(el, smooth = true) {
    if (!el) return;
    el.scrollTo({
        top: el.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto',
    });
}

/**
 * Check if element is scrolled near bottom
 * @param {Element} el - Element to check
 * @param {number} [threshold=100] - Pixels from bottom
 * @returns {boolean} True if near bottom
 */
export function isNearBottom(el, threshold = 100) {
    if (!el) return false;
    return el.scrollHeight - el.scrollTop - el.clientHeight <= threshold;
}

// =============================================================================
// Device & Viewport Helpers
// =============================================================================

/**
 * Check if current viewport is mobile
 * @returns {boolean} True if mobile viewport
 */
export function isMobile() {
    return window.innerWidth < MOBILE_BREAKPOINT;
}

/**
 * Check if device supports touch
 * @returns {boolean} True if touch device
 */
export function isTouchDevice() {
    return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
}

// =============================================================================
// Focus Helpers
// =============================================================================

/**
 * Focus an element if it exists
 * @param {Element} el - Element to focus
 */
export function focus(el) {
    if (el && typeof el.focus === 'function') {
        el.focus();
    }
}

/**
 * Trap focus within a container (for modals)
 * @param {Element} container - Container element
 * @returns {Function} Cleanup function to remove trap
 */
export function trapFocus(container) {
    const focusable = container.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstFocusable = focusable[0];
    const lastFocusable = focusable[focusable.length - 1];

    const handleKeydown = e => {
        if (e.key !== 'Tab') return;

        if (e.shiftKey) {
            if (document.activeElement === firstFocusable) {
                e.preventDefault();
                lastFocusable?.focus();
            }
        } else {
            if (document.activeElement === lastFocusable) {
                e.preventDefault();
                firstFocusable?.focus();
            }
        }
    };

    container.addEventListener('keydown', handleKeydown);
    firstFocusable?.focus();

    return () => container.removeEventListener('keydown', handleKeydown);
}
