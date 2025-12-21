/**
 * Hotspot Widget Component
 * Interactive image with clickable regions for selection.
 *
 * Attributes:
 * - image: URL of the background image
 * - image-size: JSON { width, height } of the image
 * - regions: JSON array of clickable regions [{ id, shape, coords, label?, correct? }]
 * - selection-mode: "single" or "multiple"
 * - show-labels: Show region labels on hover
 * - highlight-on-hover: Highlight regions on hover
 * - prompt: Question/instruction text
 *
 * Region shapes:
 * - rect: { x, y, width, height }
 * - circle: { cx, cy, r }
 * - polygon: { points: [[x1,y1], [x2,y2], ...] }
 *
 * Events:
 * - ax-region-click: Fired when a region is clicked
 * - ax-response: Fired with selected region(s)
 *
 * @example
 * <ax-hotspot
 *   image="/images/diagram.png"
 *   image-size='{"width":800,"height":600}'
 *   regions='[{"id":"r1","shape":"rect","coords":{"x":100,"y":100,"width":200,"height":150},"label":"Area A"}]'
 *   selection-mode="single"
 *   show-labels
 * ></ax-hotspot>
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

class AxHotspot extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'image', 'image-size', 'regions', 'selection-mode', 'show-labels', 'highlight-on-hover', 'prompt', 'show-feedback-immediately'];
    }

    constructor() {
        super();
        this._selectedRegions = new Set();
        this._hoveredRegion = null;
        this._imageLoaded = false;
        this._scale = 1;
    }

    // =========================================================================
    // Attribute Getters
    // =========================================================================

    get image() {
        return this.getAttribute('image') || '';
    }

    get imageSize() {
        return this.parseJsonAttribute('image-size', { width: 800, height: 600 });
    }

    get regions() {
        return this.parseJsonAttribute('regions', []);
    }

    get selectionMode() {
        return this.getAttribute('selection-mode') || 'single';
    }

    get showLabels() {
        return this.hasAttribute('show-labels');
    }

    get highlightOnHover() {
        return this.hasAttribute('highlight-on-hover');
    }

    get prompt() {
        return this.getAttribute('prompt') || '';
    }

    get showFeedbackImmediately() {
        return this.hasAttribute('show-feedback-immediately');
    }

    // =========================================================================
    // Value Interface
    // =========================================================================

    getValue() {
        const selectedIds = Array.from(this._selectedRegions);
        return { selectedRegions: selectedIds };
    }

    setValue(value) {
        this._selectedRegions.clear();
        if (value && typeof value === 'object' && Array.isArray(value.selectedRegions)) {
            value.selectedRegions.forEach(id => this._selectedRegions.add(id));
        } else if (Array.isArray(value)) {
            value.forEach(id => this._selectedRegions.add(id));
        } else if (value) {
            this._selectedRegions.add(value);
        }
        this._updateRegionStyles();
    }

    /**
     * Show feedback for regions (correct/incorrect)
     * @param {Object} feedback - Map of regionId to correct (true/false)
     */
    showFeedback(feedback) {
        if (!feedback || typeof feedback !== 'object') return;

        this._feedback = feedback;

        // Apply feedback classes to regions
        this.shadowRoot.querySelectorAll('.hotspot-region').forEach(el => {
            const regionId = el.dataset.regionId;
            if (feedback[regionId] === true) {
                el.classList.add('correct');
                el.classList.remove('incorrect');
            } else if (feedback[regionId] === false) {
                el.classList.add('incorrect');
                el.classList.remove('correct');
            }
        });

        // Apply to polygons too
        this.shadowRoot.querySelectorAll('polygon[data-region-id]').forEach(el => {
            const regionId = el.dataset.regionId;
            if (feedback[regionId] === true) {
                el.classList.add('correct');
                el.classList.remove('incorrect');
            } else if (feedback[regionId] === false) {
                el.classList.add('incorrect');
                el.classList.remove('correct');
            }
        });
    }

    validate() {
        const errors = [];

        if (this.required && this._selectedRegions.size === 0) {
            errors.push('Please select at least one region');
        }

        return { valid: errors.length === 0, errors, warnings: [] };
    }

    // =========================================================================
    // Styles
    // =========================================================================

    async getStyles() {
        return `
            ${await this.getBaseStyles()}

            :host {
                display: block;
                font-family: var(--ax-font-family, system-ui, -apple-system, sans-serif);
            }

            .widget-container {
                background: var(--ax-widget-bg, #f8f9fa);
                border: 1px solid var(--ax-border-color, #dee2e6);
                border-radius: var(--ax-border-radius, 12px);
                padding: var(--ax-padding, 1.25rem);
                margin: var(--ax-margin, 0.5rem 0);
            }

            .prompt {
                font-size: 1rem;
                font-weight: 500;
                color: var(--ax-text-color, #212529);
                margin-bottom: 1rem;
                line-height: 1.5;
            }

            .hotspot-container {
                position: relative;
                display: inline-block;
                max-width: 100%;
                line-height: 0;
            }

            .hotspot-image {
                display: block;
                max-width: 100%;
                height: auto;
                border-radius: 8px;
                user-select: none;
                -webkit-user-drag: none;
            }

            .hotspot-overlay {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
            }

            .hotspot-region {
                position: absolute;
                pointer-events: auto;
                cursor: pointer;
                transition: all 0.2s ease;
            }

            .hotspot-region.region-rect,
            .hotspot-region.region-circle {
                border: 2px solid transparent;
            }

            .hotspot-region:hover,
            .hotspot-region.hovered {
                border-color: var(--ax-primary-color, #0d6efd);
                background: rgba(13, 110, 253, 0.1);
            }

            .hotspot-region.selected {
                border-color: var(--ax-success-color, #198754);
                background: rgba(25, 135, 84, 0.2);
                box-shadow: 0 0 0 3px rgba(25, 135, 84, 0.3);
            }

            .hotspot-region.correct {
                border-color: var(--ax-success-color, #198754);
                background: rgba(25, 135, 84, 0.3);
            }

            .hotspot-region.incorrect {
                border-color: var(--ax-error-color, #dc3545);
                background: rgba(220, 53, 69, 0.3);
            }

            .hotspot-region.region-circle {
                border-radius: 50%;
            }

            .region-label {
                position: absolute;
                bottom: 100%;
                left: 50%;
                transform: translateX(-50%);
                padding: 0.25rem 0.5rem;
                background: rgba(0, 0, 0, 0.8);
                color: white;
                font-size: 0.75rem;
                border-radius: 4px;
                white-space: nowrap;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.15s;
                margin-bottom: 4px;
                line-height: 1.4;
            }

            .hotspot-region:hover .region-label,
            .hotspot-region.hovered .region-label,
            .hotspot-region.selected .region-label.show-always {
                opacity: 1;
            }

            /* SVG overlay for polygon shapes */
            .svg-overlay {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
            }

            .svg-overlay polygon {
                pointer-events: auto;
                cursor: pointer;
                fill: transparent;
                stroke: transparent;
                stroke-width: 2;
                transition: all 0.2s ease;
            }

            .svg-overlay polygon:hover,
            .svg-overlay polygon.hovered {
                stroke: var(--ax-primary-color, #0d6efd);
                fill: rgba(13, 110, 253, 0.1);
            }

            .svg-overlay polygon.selected {
                stroke: var(--ax-success-color, #198754);
                fill: rgba(25, 135, 84, 0.2);
            }

            .loading-state {
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 200px;
                color: var(--ax-text-muted, #6c757d);
            }

            .selection-indicator {
                margin-top: 1rem;
                padding: 0.75rem;
                background: var(--ax-primary-light, #e7f1ff);
                border-radius: 6px;
                font-size: 0.9rem;
            }

            .selection-list {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin-top: 0.5rem;
            }

            .selection-tag {
                display: inline-flex;
                align-items: center;
                gap: 0.25rem;
                padding: 0.25rem 0.5rem;
                background: var(--ax-primary-color, #0d6efd);
                color: white;
                border-radius: 4px;
                font-size: 0.85rem;
            }

            .selection-tag .remove-btn {
                background: none;
                border: none;
                color: white;
                cursor: pointer;
                padding: 0;
                font-size: 1rem;
                line-height: 1;
                opacity: 0.7;
            }

            .selection-tag .remove-btn:hover {
                opacity: 1;
            }

            /* Keyboard focus */
            .hotspot-region:focus {
                outline: 2px solid var(--ax-primary-color, #0d6efd);
                outline-offset: 2px;
            }

            /* Dark mode */
            @media (prefers-color-scheme: dark) {
                .widget-container {
                    --ax-widget-bg: #2d3748;
                    --ax-border-color: #4a5568;
                    --ax-text-color: #e2e8f0;
                    --ax-primary-light: #1e3a5f;
                }

                .region-label {
                    background: rgba(255, 255, 255, 0.9);
                    color: #212529;
                }
            }
        `;
    }

    // =========================================================================
    // Rendering
    // =========================================================================

    render() {
        const regions = this.regions;
        const rectCircleRegions = regions.filter(r => r.shape === 'rect' || r.shape === 'circle');
        const polygonRegions = regions.filter(r => r.shape === 'polygon');

        this.shadowRoot.innerHTML = `
            <style>${this._styles || ''}</style>
            <div class="widget-container">
                ${this.prompt ? `<div class="prompt">${this.renderMarkdown(this.prompt)}</div>` : ''}

                <div class="hotspot-container" role="application" aria-label="Interactive image hotspot">
                    ${
                        this.image
                            ? `
                        <img src="${this.image}"
                             class="hotspot-image"
                             alt="${this.prompt || 'Hotspot image'}"
                             draggable="false" />
                    `
                            : `
                        <div class="loading-state">No image specified</div>
                    `
                    }

                    <!-- Rect and Circle regions -->
                    <div class="hotspot-overlay">
                        ${rectCircleRegions.map(region => this._renderRegion(region)).join('')}
                    </div>

                    <!-- Polygon regions (SVG) -->
                    ${
                        polygonRegions.length > 0
                            ? `
                        <svg class="svg-overlay hotspot-svg-overlay"
                             viewBox="0 0 ${this.imageSize.width} ${this.imageSize.height}"
                             preserveAspectRatio="xMidYMid meet">
                            ${polygonRegions.map(region => this._renderPolygonRegion(region)).join('')}
                        </svg>
                    `
                            : ''
                    }
                </div>

                ${this._selectedRegions.size > 0 ? this._renderSelectionIndicator() : ''}
            </div>
        `;

        // Update scale after render
        this._updateScale();
    }

    _renderRegion(region) {
        const isSelected = this._selectedRegions.has(region.id);
        const coords = region.coords || {};
        let style = '';

        if (region.shape === 'rect') {
            const { x = 0, y = 0, width = 100, height = 50 } = coords;
            style = `
                left: ${(x / this.imageSize.width) * 100}%;
                top: ${(y / this.imageSize.height) * 100}%;
                width: ${(width / this.imageSize.width) * 100}%;
                height: ${(height / this.imageSize.height) * 100}%;
            `;
        } else if (region.shape === 'circle') {
            const { cx = 50, cy = 50, r = 25 } = coords;
            const diameter = r * 2;
            style = `
                left: ${((cx - r) / this.imageSize.width) * 100}%;
                top: ${((cy - r) / this.imageSize.height) * 100}%;
                width: ${(diameter / this.imageSize.width) * 100}%;
                height: ${(diameter / this.imageSize.height) * 100}%;
            `;
        }

        const classes = ['hotspot-region', `region-${region.shape}`, isSelected ? 'selected' : '', this._getFeedbackClass(region, isSelected)].filter(Boolean).join(' ');

        return `
            <div class="${classes}"
                 data-region-id="${region.id}"
                 style="${style}"
                 role="button"
                 tabindex="0"
                 aria-pressed="${isSelected}"
                 aria-label="${region.label || `Region ${region.id}`}">
                ${
                    region.label && this.showLabels
                        ? `
                    <span class="region-label ${isSelected ? 'show-always' : ''}">${this.escapeHtml(region.label)}</span>
                `
                        : ''
                }
            </div>
        `;
    }

    _renderPolygonRegion(region) {
        const isSelected = this._selectedRegions.has(region.id);
        const points = region.coords?.points || [];
        const pointsStr = points.map(p => p.join(',')).join(' ');

        const classes = [isSelected ? 'selected' : '', this._getFeedbackClass(region, isSelected)].filter(Boolean).join(' ');

        return `
            <polygon class="${classes}"
                     data-region-id="${region.id}"
                     points="${pointsStr}"
                     tabindex="0"
                     role="button"
                     aria-pressed="${isSelected}"
                     aria-label="${region.label || `Region ${region.id}`}" />
        `;
    }

    _renderSelectionIndicator() {
        const selectedRegions = this.regions.filter(r => this._selectedRegions.has(r.id));

        return `
            <div class="selection-indicator" role="status" aria-live="polite">
                <strong>Selected:</strong>
                <div class="selection-list">
                    ${selectedRegions
                        .map(
                            region => `
                        <span class="selection-tag">
                            ${this.escapeHtml(region.label || region.id)}
                            <button class="remove-btn" data-remove="${region.id}" aria-label="Remove selection">×</button>
                        </span>
                    `
                        )
                        .join('')}
                </div>
            </div>
        `;
    }

    _getFeedbackClass(region, isSelected) {
        if (!this.showFeedbackImmediately || !isSelected) return '';
        return region.correct ? 'correct' : region.correct === false ? 'incorrect' : '';
    }

    // =========================================================================
    // Scale Management
    // =========================================================================

    _updateScale() {
        const img = this.shadowRoot.querySelector('.hotspot-image');
        if (!img || !this._imageLoaded) return;

        const actualWidth = img.offsetWidth;
        this._scale = actualWidth / this.imageSize.width;
    }

    // =========================================================================
    // Events
    // =========================================================================

    bindEvents() {
        // Image load
        const img = this.shadowRoot.querySelector('.hotspot-image');
        if (img) {
            img.addEventListener('load', () => {
                this._imageLoaded = true;
                this._updateScale();
            });

            if (img.complete) {
                this._imageLoaded = true;
                this._updateScale();
            }
        }

        // Region click (rect/circle)
        this.shadowRoot.querySelectorAll('.hotspot-region').forEach(el => {
            el.addEventListener('click', () => this._handleRegionClick(el.dataset.regionId));
            el.addEventListener('keydown', e => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this._handleRegionClick(el.dataset.regionId);
                }
            });
        });

        // Polygon click
        this.shadowRoot.querySelectorAll('polygon[data-region-id]').forEach(el => {
            el.addEventListener('click', () => this._handleRegionClick(el.dataset.regionId));
            el.addEventListener('keydown', e => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this._handleRegionClick(el.dataset.regionId);
                }
            });
        });

        // Hover (if highlight enabled)
        if (this.highlightOnHover) {
            this.shadowRoot.querySelectorAll('.hotspot-region, polygon[data-region-id]').forEach(el => {
                el.addEventListener('mouseenter', () => {
                    this._hoveredRegion = el.dataset.regionId;
                    el.classList.add('hovered');
                });
                el.addEventListener('mouseleave', () => {
                    this._hoveredRegion = null;
                    el.classList.remove('hovered');
                });
            });
        }

        // Remove selection buttons
        this.shadowRoot.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', e => {
                e.stopPropagation();
                const regionId = btn.dataset.remove;
                this._selectedRegions.delete(regionId);
                this._updateRegionStyles();
                this._dispatchResponse();
            });
        });

        // Window resize
        window.addEventListener(
            'resize',
            this.debounce(() => this._updateScale(), 150)
        );
    }

    _handleRegionClick(regionId) {
        if (this.disabled || this.readonly) return;

        if (this.selectionMode === 'single') {
            const wasSelected = this._selectedRegions.has(regionId);
            this._selectedRegions.clear();
            if (!wasSelected) {
                this._selectedRegions.add(regionId);
            }
        } else {
            if (this._selectedRegions.has(regionId)) {
                this._selectedRegions.delete(regionId);
            } else {
                this._selectedRegions.add(regionId);
            }
        }

        const region = this.regions.find(r => r.id === regionId);

        this.dispatchEvent(
            new CustomEvent('ax-region-click', {
                bubbles: true,
                composed: true,
                detail: {
                    widgetId: this.widgetId,
                    regionId,
                    region,
                    isSelected: this._selectedRegions.has(regionId),
                },
            })
        );

        this._updateRegionStyles();
        this._dispatchResponse();

        // Announce for screen readers
        const label = region?.label || regionId;
        const action = this._selectedRegions.has(regionId) ? 'selected' : 'deselected';
        this.announce(`${label} ${action}`, 'polite');
    }

    _updateRegionStyles() {
        // Update rect/circle regions
        this.shadowRoot.querySelectorAll('.hotspot-region').forEach(el => {
            const isSelected = this._selectedRegions.has(el.dataset.regionId);
            el.classList.toggle('selected', isSelected);
            el.setAttribute('aria-pressed', isSelected);

            const label = el.querySelector('.region-label');
            if (label) {
                label.classList.toggle('show-always', isSelected);
            }
        });

        // Update polygon regions
        this.shadowRoot.querySelectorAll('polygon[data-region-id]').forEach(el => {
            const isSelected = this._selectedRegions.has(el.dataset.regionId);
            el.classList.toggle('selected', isSelected);
            el.setAttribute('aria-pressed', isSelected);
        });

        // Update selection indicator
        const indicator = this.shadowRoot.querySelector('.selection-indicator');
        if (indicator) {
            indicator.outerHTML = this._selectedRegions.size > 0 ? this._renderSelectionIndicator() : '';
            // Rebind remove buttons
            this.shadowRoot.querySelectorAll('.remove-btn').forEach(btn => {
                btn.addEventListener('click', e => {
                    e.stopPropagation();
                    this._selectedRegions.delete(btn.dataset.remove);
                    this._updateRegionStyles();
                    this._dispatchResponse();
                });
            });
        } else if (this._selectedRegions.size > 0) {
            this.shadowRoot.querySelector('.widget-container').insertAdjacentHTML('beforeend', this._renderSelectionIndicator());
        }
    }

    _dispatchResponse() {
        const value = this.getValue();
        this.dispatchEvent(
            new CustomEvent('ax-response', {
                bubbles: true,
                composed: true,
                detail: {
                    widgetId: this.widgetId,
                    itemId: this.itemId,
                    selectedRegions: value.selectedRegions,
                    timestamp: new Date().toISOString(),
                },
            })
        );
    }

    async loadStyles() {
        this._styles = await this.getStyles();
    }

    onAttributeChange(name, oldValue, newValue) {
        if (!this._initialized) return;
        this.render();
        this.bindEvents();
    }
}

// Register custom element
if (!customElements.get('ax-hotspot')) {
    customElements.define('ax-hotspot', AxHotspot);
}

export default AxHotspot;
