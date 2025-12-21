/**
 * Image Widget Configuration
 *
 * Configuration UI for the 'image' widget type.
 *
 * Python Schema Reference (ImageConfig):
 * - src: str (required)
 * - alt: str (required)
 * - caption: str | None
 * - width: int | None
 * - height: int | None
 * - object_fit: ObjectFit | None ("contain" | "cover" | "fill" | "none") (alias: objectFit)
 * - zoomable: bool | None
 * - max_zoom: float | None (alias: maxZoom)
 * - pannable: bool | None
 * - show_controls: bool | None (alias: showControls)
 * - downloadable: bool | None
 * - fallback_src: str | None (alias: fallbackSrc)
 * - lazy_load: bool | None (alias: lazyLoad)
 * - border_radius: int | None (alias: borderRadius)
 * - shadow: bool | None
 *
 * @module admin/widget-config/image-config
 */

import { WidgetConfigBase } from './config-base.js';

/**
 * Object fit options
 */
const OBJECT_FIT_OPTIONS = [
    { value: '', label: 'Default' },
    { value: 'contain', label: 'Contain (fit within)' },
    { value: 'cover', label: 'Cover (fill, may crop)' },
    { value: 'fill', label: 'Fill (stretch)' },
    { value: 'none', label: 'None (natural size)' },
];

export class ImageConfig extends WidgetConfigBase {
    /**
     * Render the image widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        this.container.innerHTML = `
            <div class="widget-config widget-config-image">
                <div class="row g-2">
                    <div class="col-md-8">
                        <label class="form-label small mb-0">
                            Image URL
                            <span class="text-danger">*</span>
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="URL of the image to display."></i>
                        </label>
                        ${this.createTextInput('config-src', config.src, 'https://example.com/image.jpg')}
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Alt Text
                            <span class="text-danger">*</span>
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Alternative text for accessibility."></i>
                        </label>
                        ${this.createTextInput('config-alt', config.alt, 'Describe the image')}
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-12">
                        <label class="form-label small mb-0">
                            Caption
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Optional caption displayed below the image."></i>
                        </label>
                        ${this.createTextInput('config-caption', config.caption, 'Optional image caption')}
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Width (px)
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Fixed width in pixels. Leave empty for auto."></i>
                        </label>
                        ${this.createNumberInput('config-width', config.width ?? '', 'Auto', { min: 1 })}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Height (px)
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Fixed height in pixels. Leave empty for auto."></i>
                        </label>
                        ${this.createNumberInput('config-height', config.height ?? '', 'Auto', { min: 1 })}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Object Fit
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="How the image should fit its container."></i>
                        </label>
                        ${this.createSelect('config-object-fit', OBJECT_FIT_OPTIONS, config.object_fit ?? config.objectFit ?? '')}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Border Radius (px)
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Corner rounding in pixels."></i>
                        </label>
                        ${this.createNumberInput('config-border-radius', config.border_radius ?? config.borderRadius ?? '', '0', { min: 0 })}
                    </div>
                </div>
                <div class="row g-2 mt-2">
                    <div class="col-md-3">
                        ${this.createSwitch('config-zoomable', `${this.uid}-zoomable`, 'Zoomable', 'Allow users to zoom into the image.', config.zoomable ?? false)}
                    </div>
                    <div class="col-md-3">
                        ${this.createSwitch('config-pannable', `${this.uid}-pannable`, 'Pannable', 'Allow users to pan around when zoomed.', config.pannable ?? false)}
                    </div>
                    <div class="col-md-3">
                        ${this.createSwitch('config-downloadable', `${this.uid}-downloadable`, 'Downloadable', 'Show download button.', config.downloadable ?? false)}
                    </div>
                    <div class="col-md-3">
                        ${this.createSwitch('config-shadow', `${this.uid}-shadow`, 'Shadow', 'Apply drop shadow to the image.', config.shadow ?? false)}
                    </div>
                </div>

                ${this.createCollapsibleSection(
                    `${this.uid}-advanced`,
                    'Advanced Options',
                    `
                    <div class="row g-2">
                        <div class="col-md-3">
                            ${this.createSwitch(
                                'config-show-controls',
                                `${this.uid}-show-controls`,
                                'Show Controls',
                                'Display zoom/pan control buttons.',
                                config.show_controls ?? config.showControls ?? false
                            )}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch('config-lazy-load', `${this.uid}-lazy-load`, 'Lazy Load', 'Defer loading until image is in viewport.', config.lazy_load ?? config.lazyLoad ?? true)}
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small mb-0">
                                Max Zoom
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="Maximum zoom level (e.g., 3 for 3x)."></i>
                            </label>
                            ${this.createNumberInput('config-max-zoom', config.max_zoom ?? config.maxZoom ?? '', '3', { min: 1, max: 10, step: 0.5 })}
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small mb-0">
                                Fallback URL
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="URL to display if main image fails to load."></i>
                            </label>
                            ${this.createTextInput('config-fallback-src', config.fallback_src ?? config.fallbackSrc ?? '', 'Optional fallback URL')}
                        </div>
                    </div>
                `
                )}
            </div>
        `;

        this.initTooltips();
    }

    /**
     * Get configuration values matching Python schema
     * @returns {Object} Widget configuration
     */
    getValue() {
        const config = {};

        // Required fields
        const src = this.getInputValue('config-src', '');
        config.src = src;

        const alt = this.getInputValue('config-alt', '');
        config.alt = alt;

        // Optional fields
        const caption = this.getInputValue('config-caption');
        if (caption) config.caption = caption;

        const width = this.getIntValue('config-width');
        if (width !== null) config.width = width;

        const height = this.getIntValue('config-height');
        if (height !== null) config.height = height;

        const objectFit = this.getInputValue('config-object-fit');
        if (objectFit) config.object_fit = objectFit;

        const borderRadius = this.getIntValue('config-border-radius');
        if (borderRadius !== null && borderRadius > 0) config.border_radius = borderRadius;

        const zoomable = this.getChecked('config-zoomable');
        if (zoomable) config.zoomable = true;

        const pannable = this.getChecked('config-pannable');
        if (pannable) config.pannable = true;

        const downloadable = this.getChecked('config-downloadable');
        if (downloadable) config.downloadable = true;

        const shadow = this.getChecked('config-shadow');
        if (shadow) config.shadow = true;

        const showControls = this.getChecked('config-show-controls');
        if (showControls) config.show_controls = true;

        const lazyLoad = this.getChecked('config-lazy-load');
        if (!lazyLoad) config.lazy_load = false;

        const maxZoom = this.getNumericValue('config-max-zoom');
        if (maxZoom !== null) config.max_zoom = maxZoom;

        const fallbackSrc = this.getInputValue('config-fallback-src');
        if (fallbackSrc) config.fallback_src = fallbackSrc;

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const src = this.getInputValue('config-src');
        if (!src) {
            errors.push('Image URL is required');
        } else if (!src.startsWith('http://') && !src.startsWith('https://') && !src.startsWith('/') && !src.startsWith('data:')) {
            errors.push('Image URL must be a valid URL or path');
        }

        const alt = this.getInputValue('config-alt');
        if (!alt) {
            errors.push('Alt text is required for accessibility');
        }

        const maxZoom = this.getNumericValue('config-max-zoom');
        if (maxZoom !== null && maxZoom < 1) {
            errors.push('Max zoom must be at least 1');
        }

        return { valid: errors.length === 0, errors };
    }
}
