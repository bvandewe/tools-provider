/**
 * Widget Test Utilities
 * Helpers for testing web components in a DOM-like environment.
 */

/**
 * Create and mount a widget element
 * @param {string} tagName - Custom element tag
 * @param {Object} attributes - Attributes to set
 * @returns {HTMLElement}
 */
export function createWidget(tagName, attributes = {}) {
    const element = document.createElement(tagName);

    for (const [key, value] of Object.entries(attributes)) {
        if (typeof value === 'boolean') {
            if (value) element.setAttribute(key, '');
        } else if (typeof value === 'object') {
            element.setAttribute(key, JSON.stringify(value));
        } else {
            element.setAttribute(key, String(value));
        }
    }

    document.body.appendChild(element);
    return element;
}

/**
 * Clean up mounted elements
 */
export function cleanup() {
    document.body.innerHTML = '';
}

/**
 * Wait for custom element to be defined and connected
 * @param {HTMLElement} element
 */
export async function waitForElement(element) {
    await customElements.whenDefined(element.tagName.toLowerCase());
    await new Promise(resolve => setTimeout(resolve, 0));
}

/**
 * Simulate a click event
 * @param {HTMLElement} element
 */
export function click(element) {
    element.dispatchEvent(new MouseEvent('click', { bubbles: true, composed: true }));
}

/**
 * Simulate input event
 * @param {HTMLElement} element
 * @param {string} value
 */
export function input(element, value) {
    element.value = value;
    element.dispatchEvent(new Event('input', { bubbles: true }));
}

/**
 * Get element from shadow DOM
 * @param {HTMLElement} host
 * @param {string} selector
 * @returns {HTMLElement|null}
 */
export function shadowQuery(host, selector) {
    return host.shadowRoot?.querySelector(selector);
}

/**
 * Get all elements from shadow DOM
 * @param {HTMLElement} host
 * @param {string} selector
 * @returns {NodeList}
 */
export function shadowQueryAll(host, selector) {
    return host.shadowRoot?.querySelectorAll(selector) || [];
}

/**
 * Wait for next frame
 */
export function nextFrame() {
    return new Promise(resolve => requestAnimationFrame(resolve));
}

/**
 * Capture dispatched events
 * @param {HTMLElement} element
 * @param {string} eventName
 * @returns {Promise<CustomEvent>}
 */
export function captureEvent(element, eventName) {
    return new Promise(resolve => {
        element.addEventListener(eventName, resolve, { once: true });
    });
}
