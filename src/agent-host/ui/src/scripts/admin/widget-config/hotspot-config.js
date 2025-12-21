/**
 * Hotspot Widget Configuration
 *
 * Configuration UI for the 'hotspot' widget type.
 *
 * Python Schema Reference (HotspotConfig):
 * - image: str (required) - URL of the background image
 * - image_size: dict[str, int] (required, alias: imageSize) - {width, height}
 * - regions: list[HotspotRegion] (required) - clickable regions
 * - selection_mode: SelectionMode = "single" (alias: selectionMode) - "single" | "multiple"
 * - show_labels: bool | None (alias: showLabels)
 * - highlight_on_hover: bool | None (alias: highlightOnHover)
 * - show_feedback_immediately: bool | None (alias: showFeedbackImmediately)
 *
 * HotspotRegion:
 * - id: str
 * - shape: HotspotShape - "circle" | "rect" | "polygon"
 * - coords: dict[str, Any] - shape-specific coordinates
 * - label: str | None
 * - correct: bool | None
 *
 * @module admin/widget-config/hotspot-config
 */

import { WidgetConfigBase } from './config-base.js';

/**
 * Selection mode options
 */
const SELECTION_MODE_OPTIONS = [
    { value: 'single', label: 'Single Selection' },
    { value: 'multiple', label: 'Multiple Selection' },
];

/**
 * Shape options for regions
 */
const SHAPE_OPTIONS = [
    { value: 'rect', label: 'Rectangle' },
    { value: 'circle', label: 'Circle' },
    { value: 'polygon', label: 'Polygon' },
];

export class HotspotConfig extends WidgetConfigBase {
    /**
     * Render the hotspot widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        const imageSize = config.image_size ?? config.imageSize ?? { width: 800, height: 600 };

        // Convert regions to text format
        // Format: id|shape|coords|label|correct
        // coords: for rect: x,y,w,h | for circle: cx,cy,r | for polygon: x1,y1,x2,y2,...
        const regions = config.regions || [];
        const regionsText = regions
            .map(region => {
                let coordsStr = '';
                const coords = region.coords || {};
                if (region.shape === 'rect') {
                    coordsStr = `${coords.x ?? 0},${coords.y ?? 0},${coords.width ?? 100},${coords.height ?? 100}`;
                } else if (region.shape === 'circle') {
                    coordsStr = `${coords.cx ?? 0},${coords.cy ?? 0},${coords.r ?? 50}`;
                } else if (region.shape === 'polygon') {
                    coordsStr = (coords.points || []).flat().join(',');
                }
                const parts = [region.id, region.shape, coordsStr];
                if (region.label) parts.push(region.label);
                if (region.correct) parts.push('correct');
                return parts.join('|');
            })
            .join('\n');

        this.container.innerHTML = `
            <div class="widget-config widget-config-hotspot">
                <div class="row g-2">
                    <div class="col-md-8">
                        ${this.createFormGroup(
                            'Image URL',
                            this.createTextInput('config-image', config.image ?? '', 'https://example.com/image.jpg'),
                            'URL of the background image for hotspot regions.',
                            true
                        )}
                    </div>
                    <div class="col-md-4">
                        ${this.createFormGroup(
                            'Selection Mode',
                            this.createSelect('config-selection-mode', SELECTION_MODE_OPTIONS, config.selection_mode ?? config.selectionMode ?? 'single'),
                            'Single or multiple regions can be selected.'
                        )}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-3">
                        ${this.createFormGroup('Image Width', this.createNumberInput('config-image-width', imageSize.width, 100, 4000, 10), 'Width of the image in pixels.', true)}
                    </div>
                    <div class="col-md-3">
                        ${this.createFormGroup('Image Height', this.createNumberInput('config-image-height', imageSize.height, 100, 4000, 10), 'Height of the image in pixels.', true)}
                    </div>
                    <div class="col-md-6">
                        <div class="row g-2">
                            <div class="col-4">
                                ${this.createSwitch('config-show-labels', `${this.uid}-show-labels`, 'Show Labels', 'Display labels on regions.', config.show_labels ?? config.showLabels ?? false)}
                            </div>
                            <div class="col-4">
                                ${this.createSwitch(
                                    'config-hover',
                                    `${this.uid}-hover`,
                                    'Highlight on Hover',
                                    'Highlight regions on mouse hover.',
                                    config.highlight_on_hover ?? config.highlightOnHover ?? false
                                )}
                            </div>
                            <div class="col-4">
                                ${this.createSwitch(
                                    'config-feedback',
                                    `${this.uid}-feedback`,
                                    'Immediate Feedback',
                                    'Show correctness feedback immediately.',
                                    config.show_feedback_immediately ?? config.showFeedbackImmediately ?? false
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="mt-3">
                    ${this.createFormGroup(
                        'Clickable Regions',
                        this.createTextarea('config-regions', regionsText, 'region1|rect|10,20,100,80|Label A|correct\nregion2|circle|200,150,50|Label B', 6),
                        'One region per line. Format: id|shape|coords[|label][|correct]. ' + 'Coords: rect=x,y,w,h | circle=cx,cy,r | polygon=x1,y1,x2,y2,...',
                        true
                    )}
                </div>

                <div class="alert alert-info small mt-3 py-2">
                    <i class="bi bi-info-circle me-1"></i>
                    <strong>Region Coordinate Formats:</strong>
                    <ul class="mb-0 mt-1">
                        <li><strong>rect:</strong> x,y,width,height (top-left corner and size)</li>
                        <li><strong>circle:</strong> cx,cy,radius (center point and radius)</li>
                        <li><strong>polygon:</strong> x1,y1,x2,y2,x3,y3,... (list of vertex points)</li>
                    </ul>
                </div>
            </div>
        `;

        this.initTooltips();
    }

    /**
     * Parse regions from textarea
     * @returns {Array} Parsed regions array
     */
    parseRegions() {
        const text = this.getInputValue('config-regions', '');
        if (!text.trim()) return [];

        return text
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map(line => {
                const parts = line.split('|').map(p => p.trim());
                const region = {
                    id: parts[0],
                    shape: parts[1] || 'rect',
                    coords: this.parseCoords(parts[1] || 'rect', parts[2] || ''),
                };

                // Check remaining parts for label and correct flag
                for (let i = 3; i < parts.length; i++) {
                    if (parts[i] === 'correct') {
                        region.correct = true;
                    } else if (parts[i]) {
                        region.label = parts[i];
                    }
                }

                return region;
            });
    }

    /**
     * Parse coordinates based on shape type
     * @param {string} shape - Shape type
     * @param {string} coordsStr - Comma-separated coordinates
     * @returns {Object} Parsed coordinates object
     */
    parseCoords(shape, coordsStr) {
        const values = coordsStr.split(',').map(v => parseInt(v.trim(), 10) || 0);

        if (shape === 'rect') {
            return {
                x: values[0] ?? 0,
                y: values[1] ?? 0,
                width: values[2] ?? 100,
                height: values[3] ?? 100,
            };
        } else if (shape === 'circle') {
            return {
                cx: values[0] ?? 0,
                cy: values[1] ?? 0,
                r: values[2] ?? 50,
            };
        } else if (shape === 'polygon') {
            // Convert flat array to points array
            const points = [];
            for (let i = 0; i < values.length - 1; i += 2) {
                points.push([values[i], values[i + 1]]);
            }
            return { points };
        }

        return {};
    }

    /**
     * Get configuration values matching Python schema
     * @returns {Object} Widget configuration
     */
    getValue() {
        const config = {};

        config.image = this.getInputValue('config-image', '');

        config.image_size = {
            width: parseInt(this.getInputValue('config-image-width', '800'), 10),
            height: parseInt(this.getInputValue('config-image-height', '600'), 10),
        };

        config.regions = this.parseRegions();

        config.selection_mode = this.getInputValue('config-selection-mode', 'single');

        const showLabels = this.getChecked('config-show-labels');
        if (showLabels) config.show_labels = true;

        const highlightOnHover = this.getChecked('config-hover');
        if (highlightOnHover) config.highlight_on_hover = true;

        const showFeedback = this.getChecked('config-feedback');
        if (showFeedback) config.show_feedback_immediately = true;

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const image = this.getInputValue('config-image', '');
        if (!image) {
            errors.push('Image URL is required');
        }

        const imageWidth = parseInt(this.getInputValue('config-image-width', '0'), 10);
        const imageHeight = parseInt(this.getInputValue('config-image-height', '0'), 10);
        if (imageWidth < 100 || imageHeight < 100) {
            errors.push('Image dimensions must be at least 100x100 pixels');
        }

        const regions = this.parseRegions();
        if (regions.length < 1) {
            errors.push('At least 1 clickable region is required');
        }

        // Validate each region
        for (const region of regions) {
            if (!region.id) {
                errors.push('All regions must have an ID');
                break;
            }
            if (!['rect', 'circle', 'polygon'].includes(region.shape)) {
                errors.push(`Invalid shape "${region.shape}" for region "${region.id}"`);
            }
        }

        // Check for duplicate IDs
        const regionIds = regions.map(r => r.id);
        const uniqueIds = new Set(regionIds);
        if (regionIds.length !== uniqueIds.size) {
            errors.push('Region IDs must be unique');
        }

        return { valid: errors.length === 0, errors };
    }

    /**
     * Get correct answer (regions marked as correct)
     * @returns {Array} Array of correct region IDs
     */
    getCorrectAnswer() {
        const regions = this.parseRegions();
        return regions.filter(r => r.correct).map(r => r.id);
    }
}
