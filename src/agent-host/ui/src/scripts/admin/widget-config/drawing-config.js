/**
 * Drawing Widget Configuration
 *
 * Configuration UI for the 'drawing' widget type.
 *
 * Python Schema Reference (DrawingConfig):
 * - canvas_size: dict[str, int] (required, alias: canvasSize) - {width, height}
 * - background_image: str | None (alias: backgroundImage)
 * - background_color: str | None (alias: backgroundColor)
 * - tools: DrawingToolsConfig (required)
 * - initial_drawing: Any | None (alias: initialDrawing)
 * - allow_undo: bool | None (alias: allowUndo)
 * - max_undo_steps: int | None (alias: maxUndoSteps)
 *
 * DrawingToolsConfig:
 * - pen: DrawingToolConfig | None
 * - highlighter: DrawingToolConfig | None
 * - eraser: DrawingToolConfig | None
 * - shapes: DrawingToolConfig | None
 * - text: DrawingToolConfig | None
 *
 * DrawingToolConfig:
 * - enabled: bool = True
 * - colors: list[str] | None
 * - sizes: list[int] | None
 * - opacity: float | None
 * - types: list[str] | None (for shapes)
 * - fonts: list[str] | None (for text)
 *
 * @module admin/widget-config/drawing-config
 */

import { WidgetConfigBase } from './config-base.js';

/**
 * Default tool colors
 */
const DEFAULT_COLORS = '#000000, #ff0000, #00ff00, #0000ff, #ffff00, #ff00ff, #00ffff, #ffffff';

/**
 * Default pen sizes
 */
const DEFAULT_SIZES = '1, 2, 4, 8, 12, 16';

/**
 * Default shape types
 */
const DEFAULT_SHAPES = 'rectangle, circle, line, arrow, triangle';

/**
 * Default fonts
 */
const DEFAULT_FONTS = 'Arial, Georgia, Courier New, Comic Sans MS';

export class DrawingConfig extends WidgetConfigBase {
    /**
     * Render the drawing widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        const canvasSize = config.canvas_size ?? config.canvasSize ?? { width: 800, height: 600 };
        const tools = config.tools || {};
        const pen = tools.pen || {};
        const highlighter = tools.highlighter || {};
        const eraser = tools.eraser || {};
        const shapes = tools.shapes || {};
        const text = tools.text || {};

        this.container.innerHTML = `
            <div class="widget-config widget-config-drawing">
                <div class="row g-2">
                    <div class="col-md-3">
                        ${this.createFormGroup('Canvas Width', this.createNumberInput('config-width', canvasSize.width, 200, 2000, 10), 'Width of the drawing canvas.', true)}
                    </div>
                    <div class="col-md-3">
                        ${this.createFormGroup('Canvas Height', this.createNumberInput('config-height', canvasSize.height, 200, 2000, 10), 'Height of the drawing canvas.', true)}
                    </div>
                    <div class="col-md-3">
                        ${this.createFormGroup(
                            'Background Color',
                            this.createTextInput('config-bg-color', config.background_color ?? config.backgroundColor ?? '#ffffff', '#ffffff'),
                            'Canvas background color.'
                        )}
                    </div>
                    <div class="col-md-3">
                        ${this.createFormGroup('Max Undo Steps', this.createNumberInput('config-undo-steps', config.max_undo_steps ?? config.maxUndoSteps ?? 50, 0, 200, 1), 'Maximum undo history.')}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-9">
                        ${this.createFormGroup(
                            'Background Image',
                            this.createTextInput('config-bg-image', config.background_image ?? config.backgroundImage ?? '', 'https://example.com/background.jpg'),
                            'Optional background image URL.'
                        )}
                    </div>
                    <div class="col-md-3">
                        ${this.createSwitch('config-allow-undo', `${this.uid}-allow-undo`, 'Allow Undo', 'Enable undo/redo functionality.', config.allow_undo ?? config.allowUndo ?? true)}
                    </div>
                </div>

                ${this.createCollapsibleSection(
                    `${this.uid}-pen`,
                    'Pen Tool',
                    `
                    <div class="row g-2">
                        <div class="col-md-2">
                            ${this.createSwitch('config-pen-enabled', `${this.uid}-pen-enabled`, 'Enabled', '', pen.enabled ?? true)}
                        </div>
                        <div class="col-md-5">
                            ${this.createFormGroup('Colors', this.createTextInput('config-pen-colors', (pen.colors || []).join(', ') || DEFAULT_COLORS, DEFAULT_COLORS), 'Comma-separated hex colors.')}
                        </div>
                        <div class="col-md-5">
                            ${this.createFormGroup('Sizes', this.createTextInput('config-pen-sizes', (pen.sizes || []).join(', ') || DEFAULT_SIZES, DEFAULT_SIZES), 'Comma-separated stroke sizes.')}
                        </div>
                    </div>
                `
                )}

                ${this.createCollapsibleSection(
                    `${this.uid}-highlighter`,
                    'Highlighter Tool',
                    `
                    <div class="row g-2">
                        <div class="col-md-2">
                            ${this.createSwitch('config-highlighter-enabled', `${this.uid}-highlighter-enabled`, 'Enabled', '', highlighter.enabled ?? true)}
                        </div>
                        <div class="col-md-5">
                            ${this.createFormGroup(
                                'Colors',
                                this.createTextInput('config-highlighter-colors', (highlighter.colors || []).join(', ') || '#ffff00, #00ff00, #00ffff, #ff00ff', '#ffff00, #00ff00, #00ffff'),
                                'Comma-separated hex colors.'
                            )}
                        </div>
                        <div class="col-md-3">
                            ${this.createFormGroup('Opacity', this.createNumberInput('config-highlighter-opacity', highlighter.opacity ?? 0.4, 0.1, 1, 0.1), 'Opacity (0.1 - 1.0).')}
                        </div>
                    </div>
                `
                )}

                ${this.createCollapsibleSection(
                    `${this.uid}-eraser`,
                    'Eraser Tool',
                    `
                    <div class="row g-2">
                        <div class="col-md-3">
                            ${this.createSwitch('config-eraser-enabled', `${this.uid}-eraser-enabled`, 'Enabled', '', eraser.enabled ?? true)}
                        </div>
                        <div class="col-md-9">
                            ${this.createFormGroup(
                                'Sizes',
                                this.createTextInput('config-eraser-sizes', (eraser.sizes || []).join(', ') || '8, 16, 24, 32', '8, 16, 24, 32'),
                                'Comma-separated eraser sizes.'
                            )}
                        </div>
                    </div>
                `
                )}

                ${this.createCollapsibleSection(
                    `${this.uid}-shapes`,
                    'Shapes Tool',
                    `
                    <div class="row g-2">
                        <div class="col-md-3">
                            ${this.createSwitch('config-shapes-enabled', `${this.uid}-shapes-enabled`, 'Enabled', '', shapes.enabled ?? true)}
                        </div>
                        <div class="col-md-9">
                            ${this.createFormGroup(
                                'Shape Types',
                                this.createTextInput('config-shapes-types', (shapes.types || []).join(', ') || DEFAULT_SHAPES, DEFAULT_SHAPES),
                                'Comma-separated shape types.'
                            )}
                        </div>
                    </div>
                    <div class="row g-2 mt-2">
                        <div class="col-md-6">
                            ${this.createFormGroup(
                                'Colors',
                                this.createTextInput('config-shapes-colors', (shapes.colors || []).join(', ') || DEFAULT_COLORS, DEFAULT_COLORS),
                                'Comma-separated hex colors.'
                            )}
                        </div>
                        <div class="col-md-6">
                            ${this.createFormGroup(
                                'Sizes',
                                this.createTextInput('config-shapes-sizes', (shapes.sizes || []).join(', ') || DEFAULT_SIZES, DEFAULT_SIZES),
                                'Comma-separated stroke sizes.'
                            )}
                        </div>
                    </div>
                `
                )}

                ${this.createCollapsibleSection(
                    `${this.uid}-text`,
                    'Text Tool',
                    `
                    <div class="row g-2">
                        <div class="col-md-3">
                            ${this.createSwitch('config-text-enabled', `${this.uid}-text-enabled`, 'Enabled', '', text.enabled ?? true)}
                        </div>
                        <div class="col-md-9">
                            ${this.createFormGroup('Fonts', this.createTextInput('config-text-fonts', (text.fonts || []).join(', ') || DEFAULT_FONTS, DEFAULT_FONTS), 'Comma-separated font names.')}
                        </div>
                    </div>
                    <div class="row g-2 mt-2">
                        <div class="col-md-6">
                            ${this.createFormGroup(
                                'Colors',
                                this.createTextInput('config-text-colors', (text.colors || []).join(', ') || DEFAULT_COLORS, DEFAULT_COLORS),
                                'Comma-separated hex colors.'
                            )}
                        </div>
                        <div class="col-md-6">
                            ${this.createFormGroup(
                                'Sizes',
                                this.createTextInput('config-text-sizes', (text.sizes || []).join(', ') || '12, 14, 16, 20, 24, 32', '12, 14, 16, 20, 24, 32'),
                                'Comma-separated font sizes.'
                            )}
                        </div>
                    </div>
                `
                )}
            </div>
        `;

        this.initTooltips();
    }

    /**
     * Parse comma-separated string to array
     * @param {string} text - Comma-separated values
     * @returns {Array} Array of trimmed strings
     */
    parseList(text) {
        if (!text || !text.trim()) return null;
        return text
            .split(',')
            .map(s => s.trim())
            .filter(s => s.length > 0);
    }

    /**
     * Parse comma-separated numbers
     * @param {string} text - Comma-separated numbers
     * @returns {Array} Array of integers
     */
    parseNumberList(text) {
        if (!text || !text.trim()) return null;
        return text
            .split(',')
            .map(s => parseInt(s.trim(), 10))
            .filter(n => !isNaN(n));
    }

    /**
     * Build tool config object
     * @param {string} prefix - Tool prefix (e.g., 'pen', 'highlighter')
     * @param {boolean} hasTypes - Whether tool has types array
     * @param {boolean} hasFonts - Whether tool has fonts array
     * @returns {Object|null} Tool config or null if defaults
     */
    buildToolConfig(prefix, hasTypes = false, hasFonts = false) {
        const tool = {};

        const enabled = this.getChecked(`config-${prefix}-enabled`);
        if (!enabled) {
            tool.enabled = false;
            return tool;
        }

        const colors = this.parseList(this.getInputValue(`config-${prefix}-colors`));
        if (colors && colors.length > 0) tool.colors = colors;

        const sizes = this.parseNumberList(this.getInputValue(`config-${prefix}-sizes`));
        if (sizes && sizes.length > 0) tool.sizes = sizes;

        if (prefix === 'highlighter') {
            const opacity = parseFloat(this.getInputValue('config-highlighter-opacity', '0.4'));
            if (!isNaN(opacity)) tool.opacity = opacity;
        }

        if (hasTypes) {
            const types = this.parseList(this.getInputValue(`config-${prefix}-types`));
            if (types && types.length > 0) tool.types = types;
        }

        if (hasFonts) {
            const fonts = this.parseList(this.getInputValue(`config-${prefix}-fonts`));
            if (fonts && fonts.length > 0) tool.fonts = fonts;
        }

        return Object.keys(tool).length > 0 ? tool : null;
    }

    /**
     * Get configuration values matching Python schema
     * @returns {Object} Widget configuration
     */
    getValue() {
        const config = {};

        config.canvas_size = {
            width: parseInt(this.getInputValue('config-width', '800'), 10),
            height: parseInt(this.getInputValue('config-height', '600'), 10),
        };

        const bgColor = this.getInputValue('config-bg-color');
        if (bgColor && bgColor !== '#ffffff') config.background_color = bgColor;

        const bgImage = this.getInputValue('config-bg-image');
        if (bgImage) config.background_image = bgImage;

        const allowUndo = this.getChecked('config-allow-undo');
        if (!allowUndo) config.allow_undo = false;

        const maxUndoSteps = parseInt(this.getInputValue('config-undo-steps', '50'), 10);
        if (maxUndoSteps !== 50) config.max_undo_steps = maxUndoSteps;

        // Build tools config
        const tools = {};

        const pen = this.buildToolConfig('pen');
        if (pen) tools.pen = pen;

        const highlighter = this.buildToolConfig('highlighter');
        if (highlighter) tools.highlighter = highlighter;

        const eraser = this.buildToolConfig('eraser');
        if (eraser) tools.eraser = eraser;

        const shapes = this.buildToolConfig('shapes', true);
        if (shapes) tools.shapes = shapes;

        const text = this.buildToolConfig('text', false, true);
        if (text) tools.text = text;

        config.tools = tools;

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const width = parseInt(this.getInputValue('config-width', '0'), 10);
        const height = parseInt(this.getInputValue('config-height', '0'), 10);

        if (width < 200 || height < 200) {
            errors.push('Canvas dimensions must be at least 200x200 pixels');
        }

        // Check that at least one tool is enabled
        const penEnabled = this.getChecked('config-pen-enabled');
        const highlighterEnabled = this.getChecked('config-highlighter-enabled');
        const eraserEnabled = this.getChecked('config-eraser-enabled');
        const shapesEnabled = this.getChecked('config-shapes-enabled');
        const textEnabled = this.getChecked('config-text-enabled');

        if (!penEnabled && !highlighterEnabled && !shapesEnabled && !textEnabled) {
            errors.push('At least one drawing tool must be enabled');
        }

        return { valid: errors.length === 0, errors };
    }
}
