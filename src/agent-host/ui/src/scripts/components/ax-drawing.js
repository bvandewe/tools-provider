/**
 * Drawing Widget Component
 * Freehand SVG drawing canvas with multiple tools.
 *
 * Attributes:
 * - canvas-size: JSON { width, height }
 * - background-image: URL of background image
 * - background-color: Canvas background color
 * - tools: JSON tool configuration
 * - initial-drawing: JSON of initial drawing data
 * - allow-undo: Enable undo functionality
 * - max-undo-steps: Maximum undo history (default: 50)
 * - prompt: Question/instruction text
 *
 * Tools configuration:
 * - pen: { enabled, colors, sizes }
 * - highlighter: { enabled, colors, sizes, opacity }
 * - eraser: { enabled, sizes }
 * - shapes: { enabled, types }
 * - text: { enabled, fonts, sizes }
 *
 * Events:
 * - ax-draw: Fired on each stroke
 * - ax-response: Fired with drawing data
 *
 * @example
 * <ax-drawing
 *   canvas-size='{"width":800,"height":600}'
 *   tools='{"pen":{"enabled":true},"eraser":{"enabled":true}}'
 *   allow-undo
 * ></ax-drawing>
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

class AxDrawing extends AxWidgetBase {
    static get observedAttributes() {
        return [...super.observedAttributes, 'canvas-size', 'background-image', 'background-color', 'tools', 'initial-drawing', 'allow-undo', 'max-undo-steps', 'prompt'];
    }

    constructor() {
        super();

        // Drawing state
        this._isDrawing = false;
        this._currentPath = [];
        this._strokes = [];
        this._undoStack = [];
        this._redoStack = [];

        // Current tool settings
        this._currentTool = 'pen';
        this._currentColor = '#000000';
        this._currentSize = 3;
        this._currentOpacity = 1;

        // Canvas reference
        this._canvas = null;
        this._ctx = null;
    }

    // =========================================================================
    // Attribute Getters
    // =========================================================================

    get canvasSize() {
        return this.parseJsonAttribute('canvas-size', { width: 600, height: 400 });
    }

    get backgroundImage() {
        return this.getAttribute('background-image') || '';
    }

    get backgroundColor() {
        return this.getAttribute('background-color') || '#ffffff';
    }

    get tools() {
        return this.parseJsonAttribute('tools', {
            pen: { enabled: true, colors: this._defaultColors, sizes: [1, 2, 3, 5, 8] },
            highlighter: { enabled: true, colors: this._highlighterColors, sizes: [10, 15, 20], opacity: 0.4 },
            eraser: { enabled: true, sizes: [10, 20, 30] },
            shapes: { enabled: false },
            text: { enabled: false },
        });
    }

    get initialDrawing() {
        return this.parseJsonAttribute('initial-drawing', null);
    }

    get allowUndo() {
        return this.hasAttribute('allow-undo');
    }

    get maxUndoSteps() {
        return parseInt(this.getAttribute('max-undo-steps')) || 50;
    }

    get prompt() {
        return this.getAttribute('prompt') || '';
    }

    get _defaultColors() {
        return ['#000000', '#dc3545', '#198754', '#0d6efd', '#6f42c1', '#fd7e14', '#6c757d'];
    }

    get _highlighterColors() {
        return ['#ffc107', '#20c997', '#e83e8c', '#6f42c1', '#17a2b8'];
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    async connectedCallback() {
        await super.connectedCallback();

        // Initialize canvas
        this._initCanvas();

        // Load initial drawing
        if (this.initialDrawing) {
            this._loadDrawing(this.initialDrawing);
        }
    }

    // =========================================================================
    // Value Interface
    // =========================================================================

    getValue() {
        return {
            strokes: this._strokes,
            canvasSize: this.canvasSize,
            dataUrl: this._canvas?.toDataURL('image/png'),
        };
    }

    setValue(value) {
        if (value?.strokes) {
            this._loadDrawing(value);
        }
    }

    validate() {
        const errors = [];

        if (this.required && this._strokes.length === 0) {
            errors.push('Please draw something on the canvas');
        }

        return { valid: errors.length === 0, errors, warnings: [] };
    }

    /**
     * Clear the canvas
     */
    clear() {
        this._saveToUndo();
        this._strokes = [];
        this._redraw();
        this._dispatchDraw();
    }

    /**
     * Undo last stroke
     */
    undo() {
        if (!this.allowUndo || this._undoStack.length === 0) return;

        this._redoStack.push([...this._strokes]);
        this._strokes = this._undoStack.pop();
        this._redraw();
    }

    /**
     * Redo last undone stroke
     */
    redo() {
        if (!this.allowUndo || this._redoStack.length === 0) return;

        this._undoStack.push([...this._strokes]);
        this._strokes = this._redoStack.pop();
        this._redraw();
    }

    /**
     * Export canvas as data URL
     */
    toDataURL(type = 'image/png', quality = 1) {
        if (!this._canvas) {
            // Return minimal valid data URL for testing environments
            return 'data:image/png;base64,';
        }
        try {
            const result = this._canvas.toDataURL(type, quality);
            // Handle jsdom returning undefined
            if (typeof result !== 'string') {
                return 'data:image/png;base64,';
            }
            return result;
        } catch (e) {
            // Handle SecurityError or other canvas issues
            return 'data:image/png;base64,';
        }
    }

    // =========================================================================
    // Styles
    // =========================================================================

    async getStyles() {
        const isDark = this._isDarkTheme();
        return `
            ${await this.getBaseStyles()}

            :host {
                display: block;
                font-family: var(--ax-font-family, system-ui, -apple-system, sans-serif);

                /* Theme-aware variables */
                --ax-widget-bg: ${isDark ? '#21262d' : '#f8f9fa'};
                --ax-border-color: ${isDark ? '#30363d' : '#dee2e6'};
                --ax-text-color: ${isDark ? '#e2e8f0' : '#212529'};
                --ax-text-muted: ${isDark ? '#8b949e' : '#6c757d'};
                --ax-hover-bg: ${isDark ? '#30363d' : '#f0f0f0'};
                --ax-toolbar-bg: ${isDark ? '#0d1117' : '#e9ecef'};
                --ax-primary-light: ${isDark ? '#1f3a5f' : '#e7f1ff'};
                --ax-tool-btn-bg: ${isDark ? '#21262d' : 'white'};
                --ax-tool-btn-border: ${isDark ? '#30363d' : 'transparent'};
            }
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

            .drawing-area {
                display: flex;
                flex-direction: column;
                gap: 0.75rem;
            }

            /* Toolbar */
            .toolbar {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                padding: 0.5rem;
                background: var(--ax-toolbar-bg, #e9ecef);
                border-radius: 8px;
            }

            .tool-group {
                display: flex;
                gap: 0.25rem;
                padding: 0.25rem;
                background: rgba(255,255,255,0.5);
                border-radius: 6px;
            }

            .tool-btn {
                width: 36px;
                height: 36px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: 1px solid transparent;
                border-radius: 6px;
                background: white;
                cursor: pointer;
                font-size: 1.1rem;
                transition: all 0.15s;
            }

            .tool-btn:hover {
                background: var(--ax-hover-bg, #f0f0f0);
            }

            .tool-btn.active {
                border-color: var(--ax-primary-color, #0d6efd);
                background: var(--ax-primary-light, #e7f1ff);
            }

            .tool-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            /* Color picker */
            .color-picker {
                display: flex;
                gap: 0.25rem;
                align-items: center;
            }

            .color-swatch {
                width: 24px;
                height: 24px;
                border: 2px solid transparent;
                border-radius: 50%;
                cursor: pointer;
                transition: transform 0.15s;
            }

            .color-swatch:hover {
                transform: scale(1.1);
            }

            .color-swatch.active {
                border-color: var(--ax-text-color, #212529);
            }

            .color-custom {
                width: 28px;
                height: 28px;
                padding: 0;
                border: 1px solid var(--ax-border-color, #dee2e6);
                border-radius: 50%;
                cursor: pointer;
            }

            /* Size picker */
            .size-picker {
                display: flex;
                gap: 0.25rem;
                align-items: center;
            }

            .size-btn {
                display: flex;
                align-items: center;
                justify-content: center;
                width: 28px;
                height: 28px;
                border: 1px solid var(--ax-border-color, #dee2e6);
                border-radius: 50%;
                background: white;
                cursor: pointer;
            }

            .size-btn:hover {
                background: var(--ax-hover-bg, #f0f0f0);
            }

            .size-btn.active {
                border-color: var(--ax-primary-color, #0d6efd);
                background: var(--ax-primary-light, #e7f1ff);
            }

            .size-dot {
                background: currentColor;
                border-radius: 50%;
            }

            /* Canvas container */
            .canvas-wrapper {
                position: relative;
                border: 2px solid var(--ax-border-color);
                border-radius: 8px;
                overflow: hidden;
                cursor: crosshair;
            }

            .drawing-canvas {
                display: block;
                touch-action: none;
            }

            .canvas-background {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                object-fit: contain;
                pointer-events: none;
            }

            /* Status bar */
            .status-bar {
                display: flex;
                justify-content: space-between;
                font-size: 0.8rem;
                color: var(--ax-text-muted);
            }

            /* Tool buttons */
            .tool-btn, .size-btn {
                background: var(--ax-tool-btn-bg);
                border-color: var(--ax-tool-btn-border);
                color: var(--ax-text-color);
            }
        `;
    }

    // =========================================================================
    // Rendering
    // =========================================================================

    render() {
        const tools = this.tools;
        const size = this.canvasSize;

        this.shadowRoot.innerHTML = `
            <style>${this._styles || ''}</style>
            <div class="widget-container">
                ${this.prompt ? `<div class="prompt">${this.renderMarkdown(this.prompt)}</div>` : ''}

                <div class="drawing-area">
                    ${this._renderToolbar(tools)}

                    <div class="canvas-wrapper" style="max-width: ${size.width}px">
                        ${
                            this.backgroundImage
                                ? `
                            <img src="${this.backgroundImage}" class="canvas-background" alt="" />
                        `
                                : ''
                        }
                        <canvas class="drawing-canvas"
                                width="${size.width}"
                                height="${size.height}"
                                role="img"
                                aria-label="Drawing canvas"></canvas>
                    </div>

                    <div class="status-bar">
                        <span>Tool: ${this._currentTool} | Size: ${this._currentSize}px</span>
                        <span>${this._strokes.length} stroke(s)</span>
                    </div>
                </div>
            </div>
        `;
    }

    _renderToolbar(tools) {
        return `
            <div class="toolbar" role="toolbar" aria-label="Drawing tools">
                <!-- Tool selection -->
                <div class="tool-group" role="radiogroup" aria-label="Tool">
                    ${
                        tools.pen?.enabled
                            ? `
                        <button class="tool-btn ${this._currentTool === 'pen' ? 'active' : ''}"
                                data-tool="pen"
                                aria-label="Pen"
                                title="Pen">✏️</button>
                    `
                            : ''
                    }
                    ${
                        tools.highlighter?.enabled
                            ? `
                        <button class="tool-btn ${this._currentTool === 'highlighter' ? 'active' : ''}"
                                data-tool="highlighter"
                                aria-label="Highlighter"
                                title="Highlighter">🖍️</button>
                    `
                            : ''
                    }
                    ${
                        tools.eraser?.enabled
                            ? `
                        <button class="tool-btn ${this._currentTool === 'eraser' ? 'active' : ''}"
                                data-tool="eraser"
                                aria-label="Eraser"
                                title="Eraser">🧹</button>
                    `
                            : ''
                    }
                </div>

                <!-- Color picker -->
                ${
                    this._currentTool !== 'eraser'
                        ? `
                    <div class="color-picker tool-group" role="radiogroup" aria-label="Color">
                        ${this._getToolColors()
                            .map(
                                color => `
                            <button class="color-swatch ${this._currentColor === color ? 'active' : ''}"
                                    style="background: ${color}"
                                    data-color="${color}"
                                    aria-label="Color ${color}"
                                    title="${color}"></button>
                        `
                            )
                            .join('')}
                        <input type="color" class="color-custom" value="${this._currentColor}" aria-label="Custom color">
                    </div>
                `
                        : ''
                }

                <!-- Size picker -->
                <div class="size-picker tool-group" role="radiogroup" aria-label="Size">
                    ${this._getToolSizes()
                        .map(
                            size => `
                        <button class="size-btn ${this._currentSize === size ? 'active' : ''}"
                                data-size="${size}"
                                aria-label="Size ${size}"
                                title="${size}px">
                            <span class="size-dot" style="width: ${Math.min(size, 16)}px; height: ${Math.min(size, 16)}px"></span>
                        </button>
                    `
                        )
                        .join('')}
                </div>

                <!-- Actions -->
                <div class="tool-group">
                    ${
                        this.allowUndo
                            ? `
                        <button class="tool-btn undo-btn"
                                aria-label="Undo"
                                title="Undo (Ctrl+Z)"
                                ${this._undoStack.length === 0 ? 'disabled' : ''}>↩️</button>
                        <button class="tool-btn redo-btn"
                                aria-label="Redo"
                                title="Redo (Ctrl+Y)"
                                ${this._redoStack.length === 0 ? 'disabled' : ''}>↪️</button>
                    `
                            : ''
                    }
                    <button class="tool-btn clear-btn" aria-label="Clear" title="Clear canvas">🗑️</button>
                </div>
            </div>
        `;
    }

    _getToolColors() {
        const tools = this.tools;
        if (this._currentTool === 'highlighter') {
            return tools.highlighter?.colors || this._highlighterColors;
        }
        return tools.pen?.colors || this._defaultColors;
    }

    _getToolSizes() {
        const tools = this.tools;
        switch (this._currentTool) {
            case 'highlighter':
                return tools.highlighter?.sizes || [10, 15, 20];
            case 'eraser':
                return tools.eraser?.sizes || [10, 20, 30];
            default:
                return tools.pen?.sizes || [1, 2, 3, 5, 8];
        }
    }

    // =========================================================================
    // Canvas Management
    // =========================================================================

    _initCanvas() {
        this._canvas = this.shadowRoot.querySelector('.drawing-canvas');
        if (!this._canvas) return;

        this._ctx = this._canvas.getContext('2d');

        // Guard against null context (e.g., in jsdom test environment)
        if (!this._ctx) return;

        // Set initial styles
        this._ctx.lineCap = 'round';
        this._ctx.lineJoin = 'round';

        // Fill background
        this._ctx.fillStyle = this.backgroundColor;
        this._ctx.fillRect(0, 0, this._canvas.width, this._canvas.height);
    }

    _redraw() {
        if (!this._ctx || !this._canvas) return;

        // Clear and fill background
        this._ctx.fillStyle = this.backgroundColor;
        this._ctx.fillRect(0, 0, this._canvas.width, this._canvas.height);

        // Redraw all strokes
        this._strokes.forEach(stroke => this._drawStroke(stroke));

        // Update status
        this._updateStatus();
    }

    _drawStroke(stroke) {
        if (!this._ctx || stroke.points.length < 2) return;

        this._ctx.beginPath();
        this._ctx.strokeStyle = stroke.color;
        this._ctx.lineWidth = stroke.size;
        this._ctx.globalAlpha = stroke.opacity;

        // Handle eraser
        if (stroke.tool === 'eraser') {
            this._ctx.globalCompositeOperation = 'destination-out';
        } else {
            this._ctx.globalCompositeOperation = 'source-over';
        }

        this._ctx.moveTo(stroke.points[0].x, stroke.points[0].y);

        for (let i = 1; i < stroke.points.length; i++) {
            this._ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
        }

        this._ctx.stroke();
        this._ctx.globalAlpha = 1;
        this._ctx.globalCompositeOperation = 'source-over';
    }

    _loadDrawing(data) {
        if (data.strokes) {
            this._strokes = data.strokes;
            this._redraw();
        }
    }

    _saveToUndo() {
        if (!this.allowUndo) return;

        this._undoStack.push([...this._strokes.map(s => ({ ...s, points: [...s.points] }))]);

        // Limit undo stack size
        while (this._undoStack.length > this.maxUndoSteps) {
            this._undoStack.shift();
        }

        // Clear redo stack on new action
        this._redoStack = [];
    }

    _updateStatus() {
        const statusBar = this.shadowRoot.querySelector('.status-bar');
        if (statusBar) {
            statusBar.innerHTML = `
                <span>Tool: ${this._currentTool} | Size: ${this._currentSize}px</span>
                <span>${this._strokes.length} stroke(s)</span>
            `;
        }

        // Update undo/redo buttons
        const undoBtn = this.shadowRoot.querySelector('.undo-btn');
        const redoBtn = this.shadowRoot.querySelector('.redo-btn');
        if (undoBtn) undoBtn.disabled = this._undoStack.length === 0;
        if (redoBtn) redoBtn.disabled = this._redoStack.length === 0;
    }

    // =========================================================================
    // Events
    // =========================================================================

    bindEvents() {
        const canvas = this.shadowRoot.querySelector('.drawing-canvas');
        if (!canvas) return;

        // Mouse events
        canvas.addEventListener('mousedown', e => this._startDrawing(e));
        canvas.addEventListener('mousemove', e => this._draw(e));
        canvas.addEventListener('mouseup', () => this._stopDrawing());
        canvas.addEventListener('mouseleave', () => this._stopDrawing());

        // Touch events
        canvas.addEventListener('touchstart', e => {
            e.preventDefault();
            this._startDrawing(e.touches[0]);
        });
        canvas.addEventListener('touchmove', e => {
            e.preventDefault();
            this._draw(e.touches[0]);
        });
        canvas.addEventListener('touchend', () => this._stopDrawing());

        // Tool buttons
        this.shadowRoot.querySelectorAll('[data-tool]').forEach(btn => {
            btn.addEventListener('click', () => {
                this._currentTool = btn.dataset.tool;

                // Reset to default size for tool
                const sizes = this._getToolSizes();
                if (!sizes.includes(this._currentSize)) {
                    this._currentSize = sizes[Math.floor(sizes.length / 2)];
                }

                // Set opacity for highlighter
                if (this._currentTool === 'highlighter') {
                    this._currentOpacity = this.tools.highlighter?.opacity || 0.4;
                } else {
                    this._currentOpacity = 1;
                }

                this._updateToolbar();
            });
        });

        // Color swatches
        this.shadowRoot.querySelectorAll('[data-color]').forEach(btn => {
            btn.addEventListener('click', () => {
                this._currentColor = btn.dataset.color;
                this._updateToolbar();
            });
        });

        // Custom color
        const customColor = this.shadowRoot.querySelector('.color-custom');
        customColor?.addEventListener('change', e => {
            this._currentColor = e.target.value;
            this._updateToolbar();
        });

        // Size buttons
        this.shadowRoot.querySelectorAll('[data-size]').forEach(btn => {
            btn.addEventListener('click', () => {
                this._currentSize = parseInt(btn.dataset.size);
                this._updateToolbar();
            });
        });

        // Action buttons
        this.shadowRoot.querySelector('.undo-btn')?.addEventListener('click', () => this.undo());
        this.shadowRoot.querySelector('.redo-btn')?.addEventListener('click', () => this.redo());
        this.shadowRoot.querySelector('.clear-btn')?.addEventListener('click', () => {
            if (confirm('Clear the entire canvas?')) {
                this.clear();
            }
        });

        // Keyboard shortcuts
        this.addEventListener('keydown', e => {
            if (e.ctrlKey || e.metaKey) {
                if (e.key === 'z') {
                    e.preventDefault();
                    this.undo();
                } else if (e.key === 'y') {
                    e.preventDefault();
                    this.redo();
                }
            }
        });
    }

    _startDrawing(e) {
        if (this.disabled || this.readonly || !this._ctx) return;

        this._isDrawing = true;
        this._saveToUndo();
        this.clearError(); // Clear validation error on interaction

        const pos = this._getPosition(e);
        this._currentPath = [pos];

        // Start drawing immediately
        this._ctx.beginPath();
        this._ctx.strokeStyle = this._currentTool === 'eraser' ? this.backgroundColor : this._currentColor;
        this._ctx.lineWidth = this._currentSize;
        this._ctx.globalAlpha = this._currentOpacity;

        if (this._currentTool === 'eraser') {
            this._ctx.globalCompositeOperation = 'destination-out';
        }

        this._ctx.moveTo(pos.x, pos.y);
    }

    _draw(e) {
        if (!this._isDrawing || !this._ctx) return;

        const pos = this._getPosition(e);
        this._currentPath.push(pos);

        this._ctx.lineTo(pos.x, pos.y);
        this._ctx.stroke();
        this._ctx.beginPath();
        this._ctx.moveTo(pos.x, pos.y);
    }

    _stopDrawing() {
        if (!this._isDrawing) return;

        this._isDrawing = false;
        if (this._ctx) {
            this._ctx.globalAlpha = 1;
            this._ctx.globalCompositeOperation = 'source-over';
        }

        // Save stroke
        if (this._currentPath.length > 1) {
            this._strokes.push({
                tool: this._currentTool,
                color: this._currentColor,
                size: this._currentSize,
                opacity: this._currentOpacity,
                points: this._currentPath,
            });

            this._dispatchDraw();
        }

        this._currentPath = [];
        this._updateStatus();
    }

    _getPosition(e) {
        const rect = this._canvas.getBoundingClientRect();
        const scaleX = this._canvas.width / rect.width;
        const scaleY = this._canvas.height / rect.height;

        return {
            x: (e.clientX - rect.left) * scaleX,
            y: (e.clientY - rect.top) * scaleY,
        };
    }

    _updateToolbar() {
        // Update tool button active states
        this.shadowRoot.querySelectorAll('[data-tool]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tool === this._currentTool);
        });

        // Update color swatch active states
        this.shadowRoot.querySelectorAll('[data-color]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.color === this._currentColor);
        });

        // Update size button active states
        this.shadowRoot.querySelectorAll('[data-size]').forEach(btn => {
            btn.classList.toggle('active', parseInt(btn.dataset.size) === this._currentSize);
        });

        // Handle color picker visibility - remove from DOM for eraser (tests expect element to not exist)
        const colorPicker = this.shadowRoot.querySelector('.color-picker');
        if (this._currentTool === 'eraser' && colorPicker) {
            // Remove color picker from DOM
            colorPicker.remove();
        } else if (this._currentTool !== 'eraser' && !colorPicker) {
            // Need to re-render toolbar to add color picker back
            this._fullToolbarUpdate();
            return;
        }

        this._updateStatus();
    }

    _fullToolbarUpdate() {
        const toolbar = this.shadowRoot.querySelector('.toolbar');
        if (!toolbar) return;

        toolbar.outerHTML = this._renderToolbar(this.tools);

        // Rebind events
        this.shadowRoot.querySelectorAll('[data-tool]').forEach(btn => {
            btn.addEventListener('click', () => {
                this._currentTool = btn.dataset.tool;
                const sizes = this._getToolSizes();
                if (!sizes.includes(this._currentSize)) {
                    this._currentSize = sizes[Math.floor(sizes.length / 2)];
                }
                if (this._currentTool === 'highlighter') {
                    this._currentOpacity = this.tools.highlighter?.opacity || 0.4;
                } else {
                    this._currentOpacity = 1;
                }
                this._updateToolbar();
            });
        });

        this.shadowRoot.querySelectorAll('[data-color]').forEach(btn => {
            btn.addEventListener('click', () => {
                this._currentColor = btn.dataset.color;
                this._updateToolbar();
            });
        });

        const customColor = this.shadowRoot.querySelector('.color-custom');
        customColor?.addEventListener('change', e => {
            this._currentColor = e.target.value;
            this._updateToolbar();
        });

        this.shadowRoot.querySelectorAll('[data-size]').forEach(btn => {
            btn.addEventListener('click', () => {
                this._currentSize = parseInt(btn.dataset.size);
                this._updateToolbar();
            });
        });

        this.shadowRoot.querySelector('.undo-btn')?.addEventListener('click', () => this.undo());
        this.shadowRoot.querySelector('.redo-btn')?.addEventListener('click', () => this.redo());
        this.shadowRoot.querySelector('.clear-btn')?.addEventListener('click', () => {
            if (confirm('Clear the entire canvas?')) {
                this.clear();
            }
        });

        this._updateStatus();
    }

    _dispatchDraw() {
        const value = this.getValue();
        const detail = {
            widgetId: this.widgetId,
            strokeCount: this._strokes.length,
            value: value,
        };

        // Emit ax-draw for draw-specific handling
        this.dispatchEvent(
            new CustomEvent('ax-draw', {
                bubbles: true,
                composed: true,
                detail: detail,
            })
        );

        // Emit ax-selection for confirmation mode
        this.dispatchEvent(
            new CustomEvent('ax-selection', {
                bubbles: true,
                composed: true,
                detail: detail,
            })
        );

        // Emit ax-response for auto-submit mode
        this.dispatchEvent(
            new CustomEvent('ax-response', {
                bubbles: true,
                composed: true,
                detail: detail,
            })
        );
    }

    async loadStyles() {
        this._styles = await this.getStyles();
    }
}

// Register custom element
if (!customElements.get('ax-drawing')) {
    customElements.define('ax-drawing', AxDrawing);
}

export default AxDrawing;
