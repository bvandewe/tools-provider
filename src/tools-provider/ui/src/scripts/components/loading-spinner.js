/**
 * Loading Spinner Component
 *
 * A simple, reusable loading indicator.
 *
 * Usage:
 *   <loading-spinner></loading-spinner>
 *   <loading-spinner size="lg" text="Loading data..."></loading-spinner>
 */

class LoadingSpinner extends HTMLElement {
    static get observedAttributes() {
        return ['size', 'text', 'visible'];
    }

    constructor() {
        super();
    }

    connectedCallback() {
        this.render();
    }

    attributeChangedCallback() {
        this.render();
    }

    render() {
        const size = this.getAttribute('size') || 'md';
        const text = this.getAttribute('text') || '';
        const visible = this.getAttribute('visible') !== 'false';

        const sizeClass =
            {
                sm: 'spinner-border-sm',
                md: '',
                lg: 'spinner-lg',
            }[size] || '';

        this.innerHTML = `
            <div class="loading-spinner-container ${visible ? '' : 'd-none'}">
                <div class="d-flex flex-column align-items-center justify-content-center py-4">
                    <div class="spinner-border text-primary ${sizeClass}" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    ${text ? `<p class="mt-2 text-muted mb-0">${this._escapeHtml(text)}</p>` : ''}
                </div>
            </div>
        `;
    }

    show(text = '') {
        if (text) this.setAttribute('text', text);
        this.setAttribute('visible', 'true');
    }

    hide() {
        this.setAttribute('visible', 'false');
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

if (!customElements.get('loading-spinner')) {
    customElements.define('loading-spinner', LoadingSpinner);
}

export { LoadingSpinner };
