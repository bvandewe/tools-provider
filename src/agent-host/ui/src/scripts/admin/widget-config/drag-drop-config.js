/**
 * Drag & Drop Widget Configuration
 *
 * Configuration UI for the 'drag_drop' widget type.
 *
 * Python Schema Reference (DragDropConfig):
 * - variant: DragDropVariant = "category" ("category" | "sequence" | "graphical")
 * - items: list[DragDropItem] (required) - each has id, content, reusable?, icon?
 * - zones: list[DragDropZone] | None - each has id, label, ordered?, slots?
 * - placeholders: list[DragDropPlaceholder] | None - for graphical variant
 * - background_image: str | None (alias: backgroundImage)
 * - background_size: dict | None (alias: backgroundSize)
 * - allow_multiple_per_zone: bool | None (alias: allowMultiplePerZone)
 * - require_all_placed: bool | None (alias: requireAllPlaced)
 * - shuffle_items: bool | None (alias: shuffleItems)
 * - show_zone_capacity: bool | None (alias: showZoneCapacity)
 * - show_slot_numbers: bool | None (alias: showSlotNumbers)
 * - show_placeholder_hints: bool | None (alias: showPlaceholderHints)
 * - snap_to_placeholder: bool | None (alias: snapToPlaceholder)
 * - allow_free_positioning: bool | None (alias: allowFreePositioning)
 *
 * @module admin/widget-config/drag-drop-config
 */

import { WidgetConfigBase } from './config-base.js';

/**
 * Variant options
 */
const VARIANT_OPTIONS = [
    { value: 'category', label: 'Category (sort into zones)' },
    { value: 'sequence', label: 'Sequence (order items)' },
    { value: 'graphical', label: 'Graphical (place on image)' },
];

export class DragDropConfig extends WidgetConfigBase {
    /**
     * Render the drag & drop widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        // Convert items array to text format
        const items = config.items || [];
        const itemsText = items
            .map(item => {
                if (typeof item === 'string') return item;
                let line = `${item.id}|${item.content}`;
                if (item.reusable) line += '|reusable';
                return line;
            })
            .join('\n');

        // Convert zones array to text format
        const zones = config.zones || [];
        const zonesText = zones
            .map(zone => {
                if (typeof zone === 'string') return zone;
                let line = `${zone.id}|${zone.label}`;
                if (zone.slots) line += `|${zone.slots}`;
                return line;
            })
            .join('\n');

        this.container.innerHTML = `
            <div class="widget-config widget-config-drag-drop">
                <div class="row g-2">
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Variant
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Type of drag & drop interaction."></i>
                        </label>
                        ${this.createSelect('config-variant', VARIANT_OPTIONS, config.variant || 'category')}
                    </div>
                    <div class="col-md-8">
                        <label class="form-label small mb-0">
                            Background Image URL
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Image URL for graphical variant background."></i>
                        </label>
                        ${this.createTextInput('config-background-image', config.background_image ?? config.backgroundImage ?? '', 'https://... (for graphical variant)')}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-6">
                        <label class="form-label small mb-0">
                            Draggable Items
                            <span class="text-danger">*</span>
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="One per line. Format: id|content or id|content|reusable"></i>
                        </label>
                        ${this.createTextarea('config-items', itemsText, 'item1|First Item\nitem2|Second Item\nitem3|Third Item|reusable', 5)}
                    </div>
                    <div class="col-md-6">
                        <label class="form-label small mb-0">
                            Drop Zones
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="One per line. Format: id|label or id|label|slots"></i>
                        </label>
                        ${this.createTextarea('config-zones', zonesText, 'zone1|Zone A\nzone2|Zone B|3', 5)}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-3">
                        ${this.createSwitch(
                            'config-shuffle-items',
                            `${this.uid}-shuffle-items`,
                            'Shuffle Items',
                            'Randomize item order on load.',
                            config.shuffle_items ?? config.shuffleItems ?? false
                        )}
                    </div>
                    <div class="col-md-3">
                        ${this.createSwitch(
                            'config-require-all',
                            `${this.uid}-require-all`,
                            'Require All Placed',
                            'All items must be placed to complete.',
                            config.require_all_placed ?? config.requireAllPlaced ?? false
                        )}
                    </div>
                    <div class="col-md-3">
                        ${this.createSwitch(
                            'config-allow-multiple',
                            `${this.uid}-allow-multiple`,
                            'Multiple Per Zone',
                            'Allow multiple items in each zone.',
                            config.allow_multiple_per_zone ?? config.allowMultiplePerZone ?? true
                        )}
                    </div>
                    <div class="col-md-3">
                        ${this.createSwitch(
                            'config-show-capacity',
                            `${this.uid}-show-capacity`,
                            'Show Zone Capacity',
                            'Display remaining slots in zones.',
                            config.show_zone_capacity ?? config.showZoneCapacity ?? false
                        )}
                    </div>
                </div>

                ${this.createCollapsibleSection(
                    `${this.uid}-advanced`,
                    'Advanced Options',
                    `
                    <div class="row g-2">
                        <div class="col-md-3">
                            ${this.createSwitch(
                                'config-show-slot-numbers',
                                `${this.uid}-show-slot-numbers`,
                                'Show Slot Numbers',
                                'Number each slot in zones.',
                                config.show_slot_numbers ?? config.showSlotNumbers ?? false
                            )}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch(
                                'config-show-hints',
                                `${this.uid}-show-hints`,
                                'Show Placeholder Hints',
                                'Display hints on placeholders (graphical).',
                                config.show_placeholder_hints ?? config.showPlaceholderHints ?? false
                            )}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch(
                                'config-snap',
                                `${this.uid}-snap`,
                                'Snap to Placeholder',
                                'Items snap to placeholders (graphical).',
                                config.snap_to_placeholder ?? config.snapToPlaceholder ?? true
                            )}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch(
                                'config-free-position',
                                `${this.uid}-free-position`,
                                'Free Positioning',
                                'Allow placing items anywhere (graphical).',
                                config.allow_free_positioning ?? config.allowFreePositioning ?? false
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
     * Parse items from textarea
     * @returns {Array} Parsed items array
     */
    parseItems() {
        const text = this.getInputValue('config-items', '');
        return text
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map(line => {
                const parts = line.split('|').map(p => p.trim());
                const item = {
                    id: parts[0],
                    content: parts[1] || parts[0],
                };
                if (parts[2] === 'reusable') {
                    item.reusable = true;
                }
                return item;
            });
    }

    /**
     * Parse zones from textarea
     * @returns {Array} Parsed zones array
     */
    parseZones() {
        const text = this.getInputValue('config-zones', '');
        if (!text.trim()) return null;

        return text
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map(line => {
                const parts = line.split('|').map(p => p.trim());
                const zone = {
                    id: parts[0],
                    label: parts[1] || parts[0],
                };
                if (parts[2]) {
                    const slots = parseInt(parts[2], 10);
                    if (!isNaN(slots)) zone.slots = slots;
                }
                return zone;
            });
    }

    /**
     * Get configuration values matching Python schema
     * @returns {Object} Widget configuration
     */
    getValue() {
        const config = {};

        config.variant = this.getInputValue('config-variant', 'category');
        config.items = this.parseItems();

        const zones = this.parseZones();
        if (zones && zones.length > 0) {
            config.zones = zones;
        }

        const backgroundImage = this.getInputValue('config-background-image');
        if (backgroundImage) config.background_image = backgroundImage;

        const shuffleItems = this.getChecked('config-shuffle-items');
        if (shuffleItems) config.shuffle_items = true;

        const requireAll = this.getChecked('config-require-all');
        if (requireAll) config.require_all_placed = true;

        const allowMultiple = this.getChecked('config-allow-multiple');
        if (!allowMultiple) config.allow_multiple_per_zone = false;

        const showCapacity = this.getChecked('config-show-capacity');
        if (showCapacity) config.show_zone_capacity = true;

        const showSlotNumbers = this.getChecked('config-show-slot-numbers');
        if (showSlotNumbers) config.show_slot_numbers = true;

        const showHints = this.getChecked('config-show-hints');
        if (showHints) config.show_placeholder_hints = true;

        const snap = this.getChecked('config-snap');
        if (!snap) config.snap_to_placeholder = false;

        const freePosition = this.getChecked('config-free-position');
        if (freePosition) config.allow_free_positioning = true;

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const items = this.parseItems();
        if (items.length < 2) {
            errors.push('At least 2 draggable items are required');
        }

        const variant = this.getInputValue('config-variant', 'category');
        if (variant === 'category') {
            const zones = this.parseZones();
            if (!zones || zones.length < 1) {
                errors.push('Category variant requires at least 1 drop zone');
            }
        }

        if (variant === 'graphical') {
            const bgImage = this.getInputValue('config-background-image');
            if (!bgImage) {
                errors.push('Graphical variant requires a background image');
            }
        }

        // Check for duplicate IDs
        const itemIds = items.map(i => i.id);
        const uniqueItemIds = new Set(itemIds);
        if (itemIds.length !== uniqueItemIds.size) {
            errors.push('Item IDs must be unique');
        }

        return { valid: errors.length === 0, errors };
    }
}
