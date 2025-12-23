/**
 * Hotspot Widget Configuration - Visual Region Builder
 *
 * Configuration UI for the 'hotspot' widget type with interactive visual editor.
 *
 * Features:
 * - Visual region builder on image canvas
 * - Draw rectangles, circles, and polygons
 * - Drag to move regions
 * - Resize regions with handles
 * - Delete regions
 * - Live preview in modal
 * - Text-based fallback for advanced editing
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
 * Default colors for regions
 */
const REGION_COLORS = ['rgba(54, 162, 235, 0.4)', 'rgba(255, 99, 132, 0.4)', 'rgba(75, 192, 192, 0.4)', 'rgba(255, 206, 86, 0.4)', 'rgba(153, 102, 255, 0.4)', 'rgba(255, 159, 64, 0.4)'];

export class HotspotConfig extends WidgetConfigBase {
    constructor(containerEl, widgetType) {
        super(containerEl, widgetType);
        this._regions = [];
        this._selectedRegionId = null;
        this._drawingMode = null; // null, 'rect', 'circle', 'polygon'
        this._drawingState = null; // for tracking draw-in-progress
        this._polygonPoints = []; // for building polygons
        this._isDragging = false;
        this._dragOffset = { x: 0, y: 0 };
        this._imageLoaded = false;
    }

    /**
     * Render the hotspot widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        const imageSize = config.image_size ?? config.imageSize ?? { width: 800, height: 500 };

        // Parse and normalize regions
        this._regions = this._normalizeRegions(config.regions || []);

        this.container.innerHTML = `
            <div class="widget-config widget-config-hotspot" data-uid="${this.uid}">
                <!-- Image URL & Settings Row -->
                <div class="row g-2">
                    <div class="col-md-6">
                        ${this.createFormGroup(
                            'Image URL',
                            this.createTextInput('config-image', config.image ?? '', 'https://example.com/image.jpg'),
                            'URL of the background image for hotspot regions.',
                            true
                        )}
                    </div>
                    <div class="col-md-2">
                        ${this.createFormGroup(
                            'Selection Mode',
                            this.createSelect('config-selection-mode', SELECTION_MODE_OPTIONS, config.selection_mode ?? config.selectionMode ?? 'single'),
                            'Selection behavior.'
                        )}
                    </div>
                    <div class="col-md-2">
                        ${this.createFormGroup('Image Width', this.createNumberInput('config-image-width', imageSize.width, 100, 2000, 10), 'Width in px.', true)}
                    </div>
                    <div class="col-md-2">
                        ${this.createFormGroup('Image Height', this.createNumberInput('config-image-height', imageSize.height, 100, 2000, 10), 'Height in px.', true)}
                    </div>
                </div>

                <!-- Switches Row -->
                <div class="row g-2 mt-1">
                    <div class="col-auto">
                        ${this.createSwitch('config-show-labels', `${this.uid}-show-labels`, 'Show Labels', 'Display labels on regions.', config.show_labels ?? config.showLabels ?? true)}
                    </div>
                    <div class="col-auto">
                        ${this.createSwitch(
                            'config-hover',
                            `${this.uid}-hover`,
                            'Highlight on Hover',
                            'Highlight regions on mouse hover.',
                            config.highlight_on_hover ?? config.highlightOnHover ?? true
                        )}
                    </div>
                    <div class="col-auto">
                        ${this.createSwitch(
                            'config-feedback',
                            `${this.uid}-feedback`,
                            'Immediate Feedback',
                            'Show correctness feedback immediately.',
                            config.show_feedback_immediately ?? config.showFeedbackImmediately ?? false
                        )}
                    </div>
                </div>

                <!-- Visual Editor Section -->
                <div class="mt-3">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <label class="form-label small mb-0 fw-bold">
                            <i class="bi bi-bullseye me-1"></i>Clickable Regions
                            <span class="badge bg-secondary ms-1 region-count">${this._regions.length}</span>
                            <span class="text-danger">*</span>
                        </label>
                        <div class="btn-group btn-group-sm" role="group">
                            <button type="button" class="btn btn-outline-primary tool-btn" data-tool="select" title="Select & Move">
                                <i class="bi bi-cursor"></i>
                            </button>
                            <button type="button" class="btn btn-outline-success tool-btn" data-tool="rect" title="Draw Rectangle">
                                <i class="bi bi-square"></i>
                            </button>
                            <button type="button" class="btn btn-outline-success tool-btn" data-tool="circle" title="Draw Circle">
                                <i class="bi bi-circle"></i>
                            </button>
                            <button type="button" class="btn btn-outline-success tool-btn" data-tool="polygon" title="Draw Polygon (click points, double-click to finish)">
                                <i class="bi bi-pentagon"></i>
                            </button>
                            <button type="button" class="btn btn-outline-danger delete-region-btn" title="Delete Selected" disabled>
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>

                    <!-- Canvas Container -->
                    <div class="hotspot-editor-container border rounded position-relative" style="max-width: 100%; overflow: auto; background: #f8f9fa;">
                        <div class="hotspot-canvas-wrapper position-relative" style="display: inline-block;">
                            <img class="hotspot-background-image" crossorigin="anonymous" style="display: block; max-width: 100%;">
                            <svg class="hotspot-overlay position-absolute top-0 start-0" style="pointer-events: all;"></svg>
                            <div class="hotspot-loading text-center py-5" style="min-height: 200px;">
                                <div class="spinner-border spinner-border-sm text-secondary" role="status"></div>
                                <p class="text-muted small mt-2">Enter image URL above to load...</p>
                            </div>
                        </div>
                    </div>

                    <!-- Selected Region Editor -->
                    <div class="selected-region-editor mt-2 p-2 border rounded bg-light" style="display: none;">
                        <div class="row g-2 align-items-end">
                            <div class="col-md-2">
                                <label class="form-label small mb-0">Region ID</label>
                                <input type="text" class="form-control form-control-sm region-id-input" placeholder="region-1">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label small mb-0">Label</label>
                                <input type="text" class="form-control form-control-sm region-label-input" placeholder="Click here">
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small mb-0">Shape</label>
                                <input type="text" class="form-control form-control-sm region-shape-input" readonly>
                            </div>
                            <div class="col-md-2">
                                <div class="form-check mt-3">
                                    <input type="checkbox" class="form-check-input region-correct-input">
                                    <label class="form-check-label small">Correct</label>
                                </div>
                            </div>
                            <div class="col-md-3 text-end">
                                <button type="button" class="btn btn-sm btn-outline-primary apply-region-btn">
                                    <i class="bi bi-check"></i> Apply
                                </button>
                                <button type="button" class="btn btn-sm btn-outline-secondary deselect-btn">
                                    <i class="bi bi-x"></i> Deselect
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Regions List (Collapsible) -->
                    <div class="mt-2">
                        <a class="small text-muted" data-bs-toggle="collapse" href="#${this.uid}-regions-list" role="button">
                            <i class="bi bi-list-ul me-1"></i>View/Edit Region Data (Advanced)
                        </a>
                        <div class="collapse mt-2" id="${this.uid}-regions-list">
                            <textarea class="form-control form-control-sm font-monospace config-regions-text" rows="5"
                                      placeholder="region1|rect|10,20,100,80|Label A|correct"></textarea>
                            <div class="d-flex justify-content-between mt-1">
                                <small class="text-muted">Format: id|shape|coords[|label][|correct]</small>
                                <button type="button" class="btn btn-sm btn-outline-secondary parse-text-btn">
                                    <i class="bi bi-arrow-repeat"></i> Sync from Text
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Preview Button -->
                <div class="mt-3 d-flex justify-content-end">
                    <button class="btn btn-outline-info btn-sm config-preview-btn" type="button">
                        <i class="bi bi-eye me-1"></i>Preview Hotspot
                    </button>
                </div>

                <!-- Preview Modal -->
                ${this._renderPreviewModal()}
            </div>
        `;

        this._bindEvents();
        this._updateRegionsText();
        this._loadImage();
        this.initTooltips();
    }

    /**
     * Normalize regions to consistent format
     * @private
     */
    _normalizeRegions(regions) {
        return regions.map((region, idx) => {
            const normalized = {
                id: region.id || `region-${idx + 1}`,
                shape: region.shape || 'rect',
                label: region.label || '',
                correct: region.correct || false,
                coords: {},
                color: REGION_COLORS[idx % REGION_COLORS.length],
            };

            const coords = region.coords || {};

            if (normalized.shape === 'rect') {
                normalized.coords = {
                    x: coords.x ?? 0,
                    y: coords.y ?? 0,
                    width: coords.width ?? 100,
                    height: coords.height ?? 100,
                };
            } else if (normalized.shape === 'circle') {
                // Handle both cx/cy and x/y formats
                normalized.coords = {
                    cx: coords.cx ?? coords.x ?? 50,
                    cy: coords.cy ?? coords.y ?? 50,
                    r: coords.r ?? coords.radius ?? 50,
                };
            } else if (normalized.shape === 'polygon') {
                // Normalize points to [[x,y], [x,y], ...] format
                let points = coords.points || [];
                if (points.length > 0 && typeof points[0] === 'object' && !Array.isArray(points[0])) {
                    // Convert {x, y} objects to [x, y] arrays
                    points = points.map(p => [p.x ?? 0, p.y ?? 0]);
                }
                normalized.coords = { points };
            }

            return normalized;
        });
    }

    /**
     * Render preview modal
     * @private
     */
    _renderPreviewModal() {
        return `
            <div class="modal fade" id="${this.uid}-preview-modal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-bullseye me-2"></i>Hotspot Preview
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="hotspot-preview-container"></div>
                            <div class="mt-3">
                                <p class="text-muted small mb-1"><strong>Instructions:</strong> Click on regions to select them.</p>
                                <div class="preview-selection-display text-primary fw-bold"></div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Bind all event handlers
     * @private
     */
    _bindEvents() {
        // Tool buttons
        this.queryAll('.tool-btn').forEach(btn => {
            btn.addEventListener('click', e => {
                const tool = e.currentTarget.dataset.tool;
                this._setTool(tool);
            });
        });

        // Delete button
        this.query('.delete-region-btn')?.addEventListener('click', () => {
            this._deleteSelectedRegion();
        });

        // Image URL change
        this.query('.config-image')?.addEventListener('change', () => {
            this._loadImage();
        });

        // Image size change
        this.query('.config-image-width')?.addEventListener('change', () => this._updateCanvasSize());
        this.query('.config-image-height')?.addEventListener('change', () => this._updateCanvasSize());

        // Region editor inputs
        this.query('.region-id-input')?.addEventListener('change', () => this._applyRegionEdits());
        this.query('.region-label-input')?.addEventListener('change', () => this._applyRegionEdits());
        this.query('.region-correct-input')?.addEventListener('change', () => this._applyRegionEdits());
        this.query('.apply-region-btn')?.addEventListener('click', () => this._applyRegionEdits());
        this.query('.deselect-btn')?.addEventListener('click', () => this._selectRegion(null));

        // Text-based editing
        this.query('.parse-text-btn')?.addEventListener('click', () => this._parseFromText());

        // Preview button
        this.query('.config-preview-btn')?.addEventListener('click', () => this._showPreview());

        // Set default tool
        this._setTool('select');
    }

    /**
     * Load image from URL
     * @private
     */
    _loadImage() {
        const imageUrl = this.getInputValue('config-image', '');
        const img = this.query('.hotspot-background-image');
        const loading = this.query('.hotspot-loading');
        const svg = this.query('.hotspot-overlay');

        if (!imageUrl) {
            img.style.display = 'none';
            svg.style.display = 'none';
            loading.style.display = 'block';
            loading.innerHTML = '<p class="text-muted small py-5">Enter image URL above to load...</p>';
            this._imageLoaded = false;
            return;
        }

        loading.style.display = 'block';
        loading.innerHTML = '<div class="spinner-border spinner-border-sm text-secondary py-5" role="status"></div>';
        img.style.display = 'none';
        svg.style.display = 'none';

        img.onload = () => {
            this._imageLoaded = true;
            loading.style.display = 'none';
            img.style.display = 'block';
            svg.style.display = 'block';
            this._updateCanvasSize();
            this._renderRegions();
            this._bindCanvasEvents();
        };

        img.onerror = () => {
            this._imageLoaded = false;
            loading.style.display = 'block';
            loading.innerHTML = '<p class="text-danger small py-5"><i class="bi bi-exclamation-triangle me-1"></i>Failed to load image</p>';
            img.style.display = 'none';
            svg.style.display = 'none';
        };

        img.src = imageUrl;
    }

    /**
     * Update canvas/SVG size to match image dimensions
     * @private
     */
    _updateCanvasSize() {
        const width = parseInt(this.getInputValue('config-image-width', '800'), 10);
        const height = parseInt(this.getInputValue('config-image-height', '500'), 10);
        const img = this.query('.hotspot-background-image');
        const svg = this.query('.hotspot-overlay');

        if (img) {
            img.style.width = `${width}px`;
            img.style.height = `${height}px`;
        }

        if (svg) {
            svg.setAttribute('width', width);
            svg.setAttribute('height', height);
            svg.style.width = `${width}px`;
            svg.style.height = `${height}px`;
        }

        this._renderRegions();
    }

    /**
     * Bind mouse events on SVG canvas
     * @private
     */
    _bindCanvasEvents() {
        const svg = this.query('.hotspot-overlay');
        if (!svg) return;

        // Remove existing listeners by cloning
        const newSvg = svg.cloneNode(true);
        svg.parentNode.replaceChild(newSvg, svg);

        newSvg.addEventListener('mousedown', e => this._onMouseDown(e));
        newSvg.addEventListener('mousemove', e => this._onMouseMove(e));
        newSvg.addEventListener('mouseup', e => this._onMouseUp(e));
        newSvg.addEventListener('dblclick', e => this._onDoubleClick(e));
        newSvg.addEventListener('contextmenu', e => e.preventDefault());

        // Re-render after replacing SVG
        this._renderRegions();
    }

    /**
     * Get mouse position relative to SVG
     * @private
     */
    _getMousePos(e) {
        const svg = this.query('.hotspot-overlay');
        const rect = svg.getBoundingClientRect();
        return {
            x: Math.round(e.clientX - rect.left),
            y: Math.round(e.clientY - rect.top),
        };
    }

    /**
     * Mouse down handler
     * @private
     */
    _onMouseDown(e) {
        if (e.button !== 0) return; // Left click only
        const pos = this._getMousePos(e);

        if (this._drawingMode === 'rect' || this._drawingMode === 'circle') {
            // Start drawing
            this._drawingState = { startX: pos.x, startY: pos.y };
            this._selectRegion(null);
        } else if (this._drawingMode === 'polygon') {
            // Add point to polygon
            this._polygonPoints.push([pos.x, pos.y]);
            this._renderRegions();
        } else if (this._drawingMode === 'select') {
            // Check if clicking on a region
            const region = this._getRegionAtPoint(pos.x, pos.y);
            if (region) {
                this._selectRegion(region.id);
                this._isDragging = true;
                this._dragOffset = {
                    x: pos.x - this._getRegionCenter(region).x,
                    y: pos.y - this._getRegionCenter(region).y,
                };
            } else {
                this._selectRegion(null);
            }
        }
    }

    /**
     * Mouse move handler
     * @private
     */
    _onMouseMove(e) {
        const pos = this._getMousePos(e);

        if (this._drawingState && (this._drawingMode === 'rect' || this._drawingMode === 'circle')) {
            // Update drawing preview
            this._renderRegions();
            this._renderDrawingPreview(pos);
        } else if (this._isDragging && this._selectedRegionId) {
            // Move region
            this._moveRegion(this._selectedRegionId, pos.x - this._dragOffset.x, pos.y - this._dragOffset.y);
            this._renderRegions();
            this._updateRegionsText();
        }
    }

    /**
     * Mouse up handler
     * @private
     */
    _onMouseUp(e) {
        const pos = this._getMousePos(e);

        if (this._drawingState && (this._drawingMode === 'rect' || this._drawingMode === 'circle')) {
            // Finish drawing
            this._finishDrawing(pos);
            this._drawingState = null;
        }

        this._isDragging = false;
    }

    /**
     * Double click handler (for finishing polygons)
     * @private
     */
    _onDoubleClick(e) {
        if (this._drawingMode === 'polygon' && this._polygonPoints.length >= 3) {
            this._finishPolygon();
        }
    }

    /**
     * Finish drawing a rect or circle
     * @private
     */
    _finishDrawing(endPos) {
        const start = this._drawingState;
        if (!start) return;

        const minSize = 20; // Minimum region size

        if (this._drawingMode === 'rect') {
            const x = Math.min(start.startX, endPos.x);
            const y = Math.min(start.startY, endPos.y);
            const width = Math.abs(endPos.x - start.startX);
            const height = Math.abs(endPos.y - start.startY);

            if (width >= minSize && height >= minSize) {
                this._addRegion({
                    shape: 'rect',
                    coords: { x, y, width, height },
                });
            }
        } else if (this._drawingMode === 'circle') {
            const cx = start.startX;
            const cy = start.startY;
            const r = Math.round(Math.sqrt(Math.pow(endPos.x - cx, 2) + Math.pow(endPos.y - cy, 2)));

            if (r >= minSize / 2) {
                this._addRegion({
                    shape: 'circle',
                    coords: { cx, cy, r },
                });
            }
        }

        this._renderRegions();
    }

    /**
     * Finish drawing a polygon
     * @private
     */
    _finishPolygon() {
        if (this._polygonPoints.length >= 3) {
            this._addRegion({
                shape: 'polygon',
                coords: { points: [...this._polygonPoints] },
            });
        }
        this._polygonPoints = [];
        this._renderRegions();
    }

    /**
     * Add a new region
     * @private
     */
    _addRegion(regionData) {
        const id = `region-${Date.now()}`;
        const colorIdx = this._regions.length % REGION_COLORS.length;

        this._regions.push({
            id,
            shape: regionData.shape,
            coords: regionData.coords,
            label: '',
            correct: false,
            color: REGION_COLORS[colorIdx],
        });

        this._selectRegion(id);
        this._updateRegionsText();
        this._updateRegionCount();
    }

    /**
     * Delete selected region
     * @private
     */
    _deleteSelectedRegion() {
        if (!this._selectedRegionId) return;

        this._regions = this._regions.filter(r => r.id !== this._selectedRegionId);
        this._selectRegion(null);
        this._renderRegions();
        this._updateRegionsText();
        this._updateRegionCount();
    }

    /**
     * Move a region to new center position
     * @private
     */
    _moveRegion(regionId, newCenterX, newCenterY) {
        const region = this._regions.find(r => r.id === regionId);
        if (!region) return;

        if (region.shape === 'rect') {
            region.coords.x = Math.round(newCenterX - region.coords.width / 2);
            region.coords.y = Math.round(newCenterY - region.coords.height / 2);
        } else if (region.shape === 'circle') {
            region.coords.cx = Math.round(newCenterX);
            region.coords.cy = Math.round(newCenterY);
        } else if (region.shape === 'polygon') {
            const center = this._getRegionCenter(region);
            const dx = newCenterX - center.x;
            const dy = newCenterY - center.y;
            region.coords.points = region.coords.points.map(p => [Math.round(p[0] + dx), Math.round(p[1] + dy)]);
        }
    }

    /**
     * Get center point of a region
     * @private
     */
    _getRegionCenter(region) {
        if (region.shape === 'rect') {
            return {
                x: region.coords.x + region.coords.width / 2,
                y: region.coords.y + region.coords.height / 2,
            };
        } else if (region.shape === 'circle') {
            return { x: region.coords.cx, y: region.coords.cy };
        } else if (region.shape === 'polygon') {
            const points = region.coords.points || [];
            if (points.length === 0) return { x: 0, y: 0 };
            const sumX = points.reduce((s, p) => s + p[0], 0);
            const sumY = points.reduce((s, p) => s + p[1], 0);
            return { x: sumX / points.length, y: sumY / points.length };
        }
        return { x: 0, y: 0 };
    }

    /**
     * Get region at a specific point
     * @private
     */
    _getRegionAtPoint(x, y) {
        // Check in reverse order (top regions first)
        for (let i = this._regions.length - 1; i >= 0; i--) {
            const region = this._regions[i];
            if (this._pointInRegion(x, y, region)) {
                return region;
            }
        }
        return null;
    }

    /**
     * Check if point is inside a region
     * @private
     */
    _pointInRegion(x, y, region) {
        if (region.shape === 'rect') {
            const c = region.coords;
            return x >= c.x && x <= c.x + c.width && y >= c.y && y <= c.y + c.height;
        } else if (region.shape === 'circle') {
            const c = region.coords;
            const dist = Math.sqrt(Math.pow(x - c.cx, 2) + Math.pow(y - c.cy, 2));
            return dist <= c.r;
        } else if (region.shape === 'polygon') {
            return this._pointInPolygon(x, y, region.coords.points || []);
        }
        return false;
    }

    /**
     * Point in polygon test (ray casting)
     * @private
     */
    _pointInPolygon(x, y, points) {
        if (points.length < 3) return false;
        let inside = false;
        for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
            const xi = points[i][0],
                yi = points[i][1];
            const xj = points[j][0],
                yj = points[j][1];
            if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
                inside = !inside;
            }
        }
        return inside;
    }

    /**
     * Set active tool
     * @private
     */
    _setTool(tool) {
        this._drawingMode = tool === 'select' ? 'select' : tool;
        this._polygonPoints = [];
        this._drawingState = null;

        // Update button states
        this.queryAll('.tool-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tool === tool);
        });

        // Update cursor
        const svg = this.query('.hotspot-overlay');
        if (svg) {
            svg.style.cursor = tool === 'select' ? 'default' : 'crosshair';
        }

        this._renderRegions();
    }

    /**
     * Select a region
     * @private
     */
    _selectRegion(regionId) {
        this._selectedRegionId = regionId;
        this._renderRegions();

        const editor = this.query('.selected-region-editor');
        const deleteBtn = this.query('.delete-region-btn');

        if (regionId) {
            const region = this._regions.find(r => r.id === regionId);
            if (region) {
                this.query('.region-id-input').value = region.id;
                this.query('.region-label-input').value = region.label || '';
                this.query('.region-shape-input').value = region.shape;
                this.query('.region-correct-input').checked = region.correct || false;
                editor.style.display = 'block';
                deleteBtn.disabled = false;
            }
        } else {
            editor.style.display = 'none';
            deleteBtn.disabled = true;
        }
    }

    /**
     * Apply edits from region editor
     * @private
     */
    _applyRegionEdits() {
        if (!this._selectedRegionId) return;

        const region = this._regions.find(r => r.id === this._selectedRegionId);
        if (!region) return;

        const newId = this.query('.region-id-input').value.trim();
        if (newId && newId !== region.id) {
            // Check for duplicate
            if (!this._regions.some(r => r.id === newId)) {
                region.id = newId;
                this._selectedRegionId = newId;
            }
        }

        region.label = this.query('.region-label-input').value;
        region.correct = this.query('.region-correct-input').checked;

        this._renderRegions();
        this._updateRegionsText();
    }

    /**
     * Render all regions on SVG
     * @private
     */
    _renderRegions() {
        const svg = this.query('.hotspot-overlay');
        if (!svg) return;

        let html = '';

        // Render existing regions
        this._regions.forEach((region, idx) => {
            const isSelected = region.id === this._selectedRegionId;
            const color = region.color || REGION_COLORS[idx % REGION_COLORS.length];
            const strokeColor = isSelected ? '#0d6efd' : 'rgba(0,0,0,0.5)';
            const strokeWidth = isSelected ? 3 : 2;

            if (region.shape === 'rect') {
                const c = region.coords;
                html += `
                    <rect x="${c.x}" y="${c.y}" width="${c.width}" height="${c.height}"
                          fill="${color}" stroke="${strokeColor}" stroke-width="${strokeWidth}"
                          data-region-id="${region.id}" style="cursor: move;" />
                `;
                if (region.label) {
                    html += `<text x="${c.x + c.width / 2}" y="${c.y + c.height / 2}"
                                   text-anchor="middle" dominant-baseline="middle"
                                   fill="#000" font-size="12" font-weight="bold" pointer-events="none">${this.escapeHtml(region.label)}</text>`;
                }
            } else if (region.shape === 'circle') {
                const c = region.coords;
                html += `
                    <circle cx="${c.cx}" cy="${c.cy}" r="${c.r}"
                            fill="${color}" stroke="${strokeColor}" stroke-width="${strokeWidth}"
                            data-region-id="${region.id}" style="cursor: move;" />
                `;
                if (region.label) {
                    html += `<text x="${c.cx}" y="${c.cy}"
                                   text-anchor="middle" dominant-baseline="middle"
                                   fill="#000" font-size="12" font-weight="bold" pointer-events="none">${this.escapeHtml(region.label)}</text>`;
                }
            } else if (region.shape === 'polygon') {
                const points = region.coords.points || [];
                const pointsStr = points.map(p => `${p[0]},${p[1]}`).join(' ');
                html += `
                    <polygon points="${pointsStr}"
                             fill="${color}" stroke="${strokeColor}" stroke-width="${strokeWidth}"
                             data-region-id="${region.id}" style="cursor: move;" />
                `;
                if (region.label && points.length > 0) {
                    const center = this._getRegionCenter(region);
                    html += `<text x="${center.x}" y="${center.y}"
                                   text-anchor="middle" dominant-baseline="middle"
                                   fill="#000" font-size="12" font-weight="bold" pointer-events="none">${this.escapeHtml(region.label)}</text>`;
                }
            }
        });

        // Render polygon-in-progress
        if (this._polygonPoints.length > 0) {
            const pointsStr = this._polygonPoints.map(p => `${p[0]},${p[1]}`).join(' ');
            html += `<polyline points="${pointsStr}" fill="none" stroke="#0d6efd" stroke-width="2" stroke-dasharray="5,5" />`;
            this._polygonPoints.forEach(p => {
                html += `<circle cx="${p[0]}" cy="${p[1]}" r="5" fill="#0d6efd" />`;
            });
        }

        svg.innerHTML = html;
    }

    /**
     * Render drawing preview (rect/circle in progress)
     * @private
     */
    _renderDrawingPreview(currentPos) {
        const svg = this.query('.hotspot-overlay');
        if (!svg || !this._drawingState) return;

        const start = this._drawingState;
        let previewHtml = '';

        if (this._drawingMode === 'rect') {
            const x = Math.min(start.startX, currentPos.x);
            const y = Math.min(start.startY, currentPos.y);
            const width = Math.abs(currentPos.x - start.startX);
            const height = Math.abs(currentPos.y - start.startY);
            previewHtml = `<rect x="${x}" y="${y}" width="${width}" height="${height}"
                                 fill="rgba(13,110,253,0.3)" stroke="#0d6efd" stroke-width="2" stroke-dasharray="5,5" />`;
        } else if (this._drawingMode === 'circle') {
            const r = Math.round(Math.sqrt(Math.pow(currentPos.x - start.startX, 2) + Math.pow(currentPos.y - start.startY, 2)));
            previewHtml = `<circle cx="${start.startX}" cy="${start.startY}" r="${r}"
                                   fill="rgba(13,110,253,0.3)" stroke="#0d6efd" stroke-width="2" stroke-dasharray="5,5" />`;
        }

        // Append preview to existing content
        svg.innerHTML += previewHtml;
    }

    /**
     * Update region count badge
     * @private
     */
    _updateRegionCount() {
        const badge = this.query('.region-count');
        if (badge) badge.textContent = this._regions.length;
    }

    /**
     * Update text representation of regions
     * @private
     */
    _updateRegionsText() {
        const textarea = this.query('.config-regions-text');
        if (!textarea) return;

        const text = this._regions
            .map(region => {
                let coordsStr = '';
                const coords = region.coords;

                if (region.shape === 'rect') {
                    coordsStr = `${coords.x},${coords.y},${coords.width},${coords.height}`;
                } else if (region.shape === 'circle') {
                    coordsStr = `${coords.cx},${coords.cy},${coords.r}`;
                } else if (region.shape === 'polygon') {
                    coordsStr = (coords.points || []).flat().join(',');
                }

                const parts = [region.id, region.shape, coordsStr];
                if (region.label) parts.push(region.label);
                if (region.correct) parts.push('correct');
                return parts.join('|');
            })
            .join('\n');

        textarea.value = text;
    }

    /**
     * Parse regions from text
     * @private
     */
    _parseFromText() {
        const textarea = this.query('.config-regions-text');
        if (!textarea) return;

        const text = textarea.value;
        if (!text.trim()) {
            this._regions = [];
        } else {
            this._regions = text
                .split('\n')
                .map(line => line.trim())
                .filter(line => line.length > 0)
                .map((line, idx) => {
                    const parts = line.split('|').map(p => p.trim());
                    const region = {
                        id: parts[0] || `region-${idx + 1}`,
                        shape: parts[1] || 'rect',
                        coords: this._parseCoords(parts[1] || 'rect', parts[2] || ''),
                        label: '',
                        correct: false,
                        color: REGION_COLORS[idx % REGION_COLORS.length],
                    };

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

        this._selectRegion(null);
        this._renderRegions();
        this._updateRegionCount();
    }

    /**
     * Parse coordinates from string
     * @private
     */
    _parseCoords(shape, coordsStr) {
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
            const points = [];
            for (let i = 0; i < values.length - 1; i += 2) {
                points.push([values[i], values[i + 1]]);
            }
            return { points };
        }

        return {};
    }

    /**
     * Show preview modal
     * @private
     */
    _showPreview() {
        const config = this.getValue();
        const modal = new bootstrap.Modal(document.getElementById(`${this.uid}-preview-modal`));
        modal.show();

        const container = this.query('.hotspot-preview-container');
        const selectionDisplay = this.query('.preview-selection-display');

        const width = config.image_size.width;
        const height = config.image_size.height;

        // Build preview HTML
        let html = `
            <div style="position: relative; display: inline-block;">
                <img src="${config.image}" style="width: ${width}px; height: ${height}px; display: block;" crossorigin="anonymous">
                <svg width="${width}" height="${height}" style="position: absolute; top: 0; left: 0;">
        `;

        config.regions.forEach((region, idx) => {
            const color = REGION_COLORS[idx % REGION_COLORS.length];

            if (region.shape === 'rect') {
                const c = region.coords;
                html += `<rect class="preview-region" data-id="${region.id}" x="${c.x}" y="${c.y}" width="${c.width}" height="${c.height}"
                              fill="${color}" stroke="rgba(0,0,0,0.5)" stroke-width="2" style="cursor: pointer;" />`;
            } else if (region.shape === 'circle') {
                const c = region.coords;
                html += `<circle class="preview-region" data-id="${region.id}" cx="${c.cx}" cy="${c.cy}" r="${c.r}"
                                fill="${color}" stroke="rgba(0,0,0,0.5)" stroke-width="2" style="cursor: pointer;" />`;
            } else if (region.shape === 'polygon') {
                const pointsStr = (region.coords.points || []).map(p => `${p[0]},${p[1]}`).join(' ');
                html += `<polygon class="preview-region" data-id="${region.id}" points="${pointsStr}"
                                 fill="${color}" stroke="rgba(0,0,0,0.5)" stroke-width="2" style="cursor: pointer;" />`;
            }
        });

        html += '</svg></div>';
        container.innerHTML = html;
        selectionDisplay.textContent = 'No region selected';

        // Add click handlers
        container.querySelectorAll('.preview-region').forEach(el => {
            el.addEventListener('click', () => {
                const id = el.dataset.id;
                const region = config.regions.find(r => r.id === id);

                // Toggle selection visual
                container.querySelectorAll('.preview-region').forEach(r => {
                    r.setAttribute('stroke-width', '2');
                    r.setAttribute('stroke', 'rgba(0,0,0,0.5)');
                });
                el.setAttribute('stroke-width', '4');
                el.setAttribute('stroke', '#0d6efd');

                selectionDisplay.textContent = `Selected: ${id}${region?.label ? ` (${region.label})` : ''}`;
            });
        });
    }

    /**
     * Get configuration values
     * @returns {Object} Widget configuration
     */
    getValue() {
        const config = {};

        config.image = this.getInputValue('config-image', '');

        config.image_size = {
            width: parseInt(this.getInputValue('config-image-width', '800'), 10),
            height: parseInt(this.getInputValue('config-image-height', '600'), 10),
        };

        config.regions = this._regions.map(r => ({
            id: r.id,
            shape: r.shape,
            coords: r.coords,
            label: r.label || undefined,
            correct: r.correct || undefined,
        }));

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

        if (this._regions.length < 1) {
            errors.push('At least 1 clickable region is required');
        }

        // Validate each region
        for (const region of this._regions) {
            if (!region.id) {
                errors.push('All regions must have an ID');
                break;
            }
            if (!['rect', 'circle', 'polygon'].includes(region.shape)) {
                errors.push(`Invalid shape "${region.shape}" for region "${region.id}"`);
            }
        }

        // Check for duplicate IDs
        const regionIds = this._regions.map(r => r.id);
        const uniqueIds = new Set(regionIds);
        if (regionIds.length !== uniqueIds.size) {
            errors.push('Region IDs must be unique');
        }

        return { valid: errors.length === 0, errors };
    }

    /**
     * Get correct answer
     * @returns {string|null} JSON string of correct region IDs
     */
    getCorrectAnswer() {
        const correctIds = this._regions.filter(r => r.correct).map(r => r.id);
        return correctIds.length > 0 ? JSON.stringify(correctIds) : null;
    }
}
