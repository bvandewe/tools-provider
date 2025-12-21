/**
 * Image Display Widget Component
 * Displays single image or gallery with lightbox support.
 *
 * Attributes:
 * - src: Single image URL
 * - images: JSON array of {src, alt, caption?}
 * - alt: Alt text for single image
 * - caption: Caption text
 * - fit: "contain" | "cover" | "fill" (default: contain)
 * - gallery-mode: Enable gallery navigation
 * - lightbox: Enable click-to-enlarge
 *
 * Events:
 * - ax-image-click: Fired when image is clicked
 * - ax-image-change: Fired when gallery index changes
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

class AxImageDisplay extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'src', 'images', 'alt', 'caption', 'fit', 'gallery-mode', 'lightbox'];
    }

    constructor() {
        super();
        this._currentIndex = 0;
        this._lightboxOpen = false;
    }

    // Attribute getters
    get src() {
        return this.getAttribute('src') || '';
    }

    get images() {
        try {
            return JSON.parse(this.getAttribute('images') || '[]');
        } catch {
            return [];
        }
    }

    get alt() {
        return this.getAttribute('alt') || '';
    }

    get caption() {
        return this.getAttribute('caption') || '';
    }

    get fit() {
        return this.getAttribute('fit') || 'contain';
    }

    get galleryMode() {
        return this.hasAttribute('gallery-mode');
    }

    get lightbox() {
        return this.hasAttribute('lightbox');
    }

    // Get all images (single or gallery)
    get _allImages() {
        if (this.images.length > 0) {
            return this.images;
        }
        if (this.src) {
            return [{ src: this.src, alt: this.alt, caption: this.caption }];
        }
        return [];
    }

    get _currentImage() {
        return this._allImages[this._currentIndex] || null;
    }

    // Value interface
    getValue() {
        return { currentIndex: this._currentIndex, currentImage: this._currentImage };
    }

    setValue(value) {
        if (typeof value === 'number') {
            this._currentIndex = Math.max(0, Math.min(value, this._allImages.length - 1));
            this._updateDisplay();
        }
    }

    validate() {
        return { valid: true, errors: [], warnings: [] };
    }

    async getStyles() {
        return `
            ${await this.getBaseStyles()}

            :host {
                display: block;
                font-family: var(--font-family, system-ui, -apple-system, sans-serif);
            }

            .image-container {
                background: var(--widget-bg, #f8f9fa);
                border: 1px solid var(--widget-border, #dee2e6);
                border-radius: 12px;
                overflow: hidden;
            }

            .image-wrapper {
                position: relative;
                width: 100%;
                min-height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: var(--image-bg, #000);
            }

            .main-image {
                max-width: 100%;
                max-height: 400px;
                object-fit: ${this.fit};
                cursor: ${this.lightbox ? 'zoom-in' : 'default'};
            }

            .caption {
                padding: 0.75rem 1rem;
                font-size: 0.9rem;
                color: var(--text-muted, #6c757d);
                text-align: center;
                background: var(--caption-bg, #f8f9fa);
            }

            .gallery-nav {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 1rem;
                padding: 0.75rem;
                background: var(--nav-bg, #f8f9fa);
            }

            .nav-btn {
                width: 36px;
                height: 36px;
                border: none;
                border-radius: 50%;
                background: var(--btn-bg, #dee2e6);
                cursor: pointer;
                font-size: 1.2rem;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.15s ease;
            }

            .nav-btn:hover:not(:disabled) {
                background: var(--btn-hover-bg, #ced4da);
            }

            .nav-btn:disabled {
                opacity: 0.4;
                cursor: not-allowed;
            }

            .page-indicator {
                font-size: 0.9rem;
                color: var(--text-muted, #6c757d);
            }

            .thumbnails {
                display: flex;
                gap: 0.5rem;
                padding: 0.5rem;
                overflow-x: auto;
                background: var(--thumb-bg, #e9ecef);
            }

            .thumbnail {
                width: 60px;
                height: 60px;
                object-fit: cover;
                border-radius: 4px;
                cursor: pointer;
                opacity: 0.6;
                transition: opacity 0.15s ease;
                border: 2px solid transparent;
            }

            .thumbnail:hover {
                opacity: 0.8;
            }

            .thumbnail.active {
                opacity: 1;
                border-color: var(--primary-color, #0d6efd);
            }

            /* Lightbox */
            .lightbox {
                position: fixed;
                inset: 0;
                background: rgba(0, 0, 0, 0.9);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 9999;
                cursor: zoom-out;
            }

            .lightbox-image {
                max-width: 90vw;
                max-height: 90vh;
                object-fit: contain;
            }

            .lightbox-close {
                position: absolute;
                top: 1rem;
                right: 1rem;
                width: 40px;
                height: 40px;
                border: none;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.2);
                color: white;
                font-size: 1.5rem;
                cursor: pointer;
            }

            .error-state {
                padding: 2rem;
                text-align: center;
                color: var(--text-muted, #6c757d);
            }
        `;
    }

    render() {
        const images = this._allImages;
        const current = this._currentImage;

        if (!current) {
            this.shadowRoot.innerHTML = `
                <style>${this._styles || ''}</style>
                <div class="image-container">
                    <div class="error-state">No image to display</div>
                </div>
            `;
            return;
        }

        this.shadowRoot.innerHTML = `
            <style>${this._styles || ''}</style>
            <div class="image-container">
                <div class="image-wrapper">
                    <img class="main-image"
                         src="${current.src}"
                         alt="${current.alt || ''}"
                         loading="lazy"/>
                </div>
                ${current.caption ? `<div class="caption">${current.caption}</div>` : ''}
                ${this.galleryMode && images.length > 1 ? this._renderGalleryNav(images) : ''}
            </div>
            ${this._lightboxOpen ? this._renderLightbox(current) : ''}
        `;

        this._styles = this.shadowRoot.querySelector('style')?.textContent;
    }

    _renderGalleryNav(images) {
        return `
            <div class="gallery-nav">
                <button class="nav-btn" data-action="prev" ${this._currentIndex === 0 ? 'disabled' : ''}>‹</button>
                <span class="page-indicator">${this._currentIndex + 1} / ${images.length}</span>
                <button class="nav-btn" data-action="next" ${this._currentIndex >= images.length - 1 ? 'disabled' : ''}>›</button>
            </div>
            <div class="thumbnails">
                ${images
                    .map(
                        (img, i) => `
                    <img class="thumbnail ${i === this._currentIndex ? 'active' : ''}"
                         src="${img.src}" alt="${img.alt || ''}"
                         data-index="${i}" loading="lazy"/>
                `
                    )
                    .join('')}
            </div>
        `;
    }

    _renderLightbox(image) {
        return `
            <div class="lightbox" data-action="close-lightbox">
                <button class="lightbox-close" data-action="close-lightbox">×</button>
                <img class="lightbox-image" src="${image.src}" alt="${image.alt || ''}"/>
            </div>
        `;
    }

    async loadStyles() {
        this._styles = await this.getStyles();
    }

    bindEvents() {
        // Navigation buttons
        this.shadowRoot.addEventListener('click', e => {
            const action = e.target.dataset?.action || e.target.closest('[data-action]')?.dataset?.action;

            if (action === 'prev') this._navigate(-1);
            else if (action === 'next') this._navigate(1);
            else if (action === 'close-lightbox') this._closeLightbox();
            else if (e.target.classList.contains('main-image') && this.lightbox) this._openLightbox();
        });

        // Thumbnail clicks
        this.shadowRoot.querySelectorAll('.thumbnail').forEach(thumb => {
            thumb.addEventListener('click', () => {
                this._goToIndex(parseInt(thumb.dataset.index));
            });
        });

        // Keyboard navigation
        this.addEventListener('keydown', e => {
            if (e.key === 'ArrowLeft') this._navigate(-1);
            else if (e.key === 'ArrowRight') this._navigate(1);
            else if (e.key === 'Escape' && this._lightboxOpen) this._closeLightbox();
        });
    }

    _navigate(delta) {
        const newIndex = this._currentIndex + delta;
        if (newIndex >= 0 && newIndex < this._allImages.length) {
            this._goToIndex(newIndex);
        }
    }

    _goToIndex(index) {
        this._currentIndex = index;
        this.render();
        this.bindEvents();

        this.dispatchEvent(
            new CustomEvent('ax-image-change', {
                bubbles: true,
                composed: true,
                detail: { index, image: this._currentImage },
            })
        );
    }

    _openLightbox() {
        this._lightboxOpen = true;
        this.render();
        this.bindEvents();

        this.dispatchEvent(
            new CustomEvent('ax-image-click', {
                bubbles: true,
                composed: true,
                detail: { index: this._currentIndex, image: this._currentImage },
            })
        );
    }

    _closeLightbox() {
        this._lightboxOpen = false;
        this.render();
        this.bindEvents();
    }

    _updateDisplay() {
        this.render();
        this.bindEvents();
    }
}

customElements.define('ax-image-display', AxImageDisplay);

export default AxImageDisplay;
