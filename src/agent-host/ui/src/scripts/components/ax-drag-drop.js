/**
 * Drag & Drop Widget Component
 * Supports three interaction variants: category, sequence, and graphical.
 *
 * Variants:
 * - category: Sort items into labeled drop zones
 * - sequence: Order items in a specific sequence
 * - graphical: Place items on a background image at specific positions
 *
 * Attributes:
 * - variant: "category" | "sequence" | "graphical"
 * - items: JSON array of draggable items [{ id, content, icon?, reusable? }]
 * - zones: JSON array of drop zones [{ id, label, ordered?, slots? }] (for category)
 * - placeholders: JSON array [{ id, region, accepts?, hint? }] (for graphical)
 * - background-image: URL for graphical variant
 * - prompt: Question/instruction text
 * - shuffle-items: Randomize initial item order
 * - require-all-placed: Require all items to be placed
 *
 * Events:
 * - ax-drop: Fired when an item is dropped
 * - ax-response: Fired with final placement data
 *
 * @example
 * <ax-drag-drop
 *   variant="category"
 *   items='[{"id":"a","content":"Apple"},{"id":"b","content":"Banana"}]'
 *   zones='[{"id":"fruits","label":"Fruits"},{"id":"veggies","label":"Vegetables"}]'
 * ></ax-drag-drop>
 */
import { AxWidgetBase, WidgetState } from './ax-widget-base.js';

class AxDragDrop extends AxWidgetBase {
    static get observedAttributes() {
        return [
            ...super.observedAttributes,
            'variant', 'items', 'zones', 'placeholders', 'background-image',
            'prompt', 'shuffle-items', 'require-all-placed', 'allow-multiple-per-zone'
        ];
    }

    constructor() {
        super();
        this._placements = new Map(); // itemId -> zoneId/placeholderId
        this._sequence = []; // For sequence variant
        this._positions = new Map(); // For graphical - itemId -> {x, y}
        this._draggedItem = null;
        this._originalItems = [];
        this._availableItems = [];
    }

    // =========================================================================
    // Attribute Getters
    // =========================================================================

    get variant() {
        const v = this.getAttribute('variant') || 'category';
        return ['category', 'sequence', 'graphical'].includes(v) ? v : 'category';
    }

    get items() {
        const items = this.parseJsonAttribute('items', []);
        return this.shuffleItems ? this._shuffle([...items]) : items;
    }

    get zones() {
        return this.parseJsonAttribute('zones', []);
    }

    get placeholders() {
        return this.parseJsonAttribute('placeholders', []);
    }

    get backgroundImage() {
        return this.getAttribute('background-image') || '';
    }

    get prompt() {
        return this.getAttribute('prompt') || '';
    }

    get shuffleItems() {
        return this.hasAttribute('shuffle-items');
    }

    get requireAllPlaced() {
        return this.hasAttribute('require-all-placed');
    }

    get allowMultiplePerZone() {
        return this.hasAttribute('allow-multiple-per-zone');
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    async connectedCallback() {
        // Initialize items
        this._originalItems = this.parseJsonAttribute('items', []);
        this._availableItems = this.shuffleItems 
            ? this._shuffle([...this._originalItems]) 
            : [...this._originalItems];
        
        await super.connectedCallback();
    }

    // =========================================================================
    // Value Interface
    // =========================================================================

    getValue() {
        switch (this.variant) {
            case 'category':
                return this._getCategoryValue();
            case 'sequence':
                return this._sequence.map(id => this._originalItems.find(item => item.id === id));
            case 'graphical':
                return Array.from(this._positions.entries()).map(([itemId, pos]) => ({
                    itemId,
                    ...pos
                }));
            default:
                return null;
        }
    }

    _getCategoryValue() {
        const result = {};
        this.zones.forEach(zone => {
            result[zone.id] = [];
        });
        
        this._placements.forEach((zoneId, itemId) => {
            if (result[zoneId]) {
                result[zoneId].push(itemId);
            }
        });
        
        return result;
    }

    setValue(value) {
        if (this.variant === 'category' && typeof value === 'object') {
            this._placements.clear();
            Object.entries(value).forEach(([zoneId, itemIds]) => {
                itemIds.forEach(itemId => this._placements.set(itemId, zoneId));
            });
        } else if (this.variant === 'sequence' && Array.isArray(value)) {
            this._sequence = value.map(item => typeof item === 'string' ? item : item.id);
        } else if (this.variant === 'graphical' && Array.isArray(value)) {
            this._positions.clear();
            value.forEach(({ itemId, x, y, placeholderId }) => {
                this._positions.set(itemId, { x, y, placeholderId });
            });
        }
        this.render();
        this.bindEvents();
    }

    validate() {
        const errors = [];
        const warnings = [];

        if (this.requireAllPlaced) {
            const unplacedCount = this._getUnplacedItems().length;
            if (unplacedCount > 0) {
                errors.push(`Please place all items (${unplacedCount} remaining)`);
            }
        }

        return { valid: errors.length === 0, errors, warnings };
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
                --zone-bg: #f8f9fa;
                --zone-border: #dee2e6;
                --zone-hover: #e9ecef;
                --item-bg: #ffffff;
                --item-border: #dee2e6;
                --item-shadow: 0 2px 4px rgba(0,0,0,0.1);
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

            .drag-drop-container {
                display: flex;
                flex-direction: column;
                gap: 1.5rem;
            }

            /* Item pool (available items) */
            .item-pool {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                padding: 1rem;
                background: var(--zone-bg);
                border: 2px dashed var(--zone-border);
                border-radius: 8px;
                min-height: 60px;
            }

            .item-pool.empty {
                justify-content: center;
                align-items: center;
                color: var(--ax-text-muted, #6c757d);
                font-style: italic;
            }

            /* Draggable items */
            .drag-item {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem 1rem;
                background: var(--item-bg);
                border: 1px solid var(--item-border);
                border-radius: 6px;
                box-shadow: var(--item-shadow);
                cursor: grab;
                user-select: none;
                transition: transform 0.15s, box-shadow 0.15s;
                font-size: 0.9rem;
            }

            .drag-item:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }

            .drag-item.dragging {
                opacity: 0.5;
                cursor: grabbing;
            }

            .drag-item .item-icon {
                font-size: 1.1rem;
            }

            /* Drop zones */
            .zones-container {
                display: flex;
                flex-wrap: wrap;
                gap: 1rem;
            }

            .drop-zone {
                flex: 1;
                min-width: 200px;
                padding: 1rem;
                background: var(--zone-bg);
                border: 2px solid var(--zone-border);
                border-radius: 8px;
                min-height: 100px;
                transition: border-color 0.15s, background 0.15s;
            }

            .drop-zone.drag-over {
                border-color: var(--ax-primary-color, #0d6efd);
                background: var(--ax-primary-light, #e7f1ff);
            }

            .zone-label {
                font-weight: 600;
                margin-bottom: 0.75rem;
                padding-bottom: 0.5rem;
                border-bottom: 1px solid var(--zone-border);
                color: var(--ax-text-color, #212529);
            }

            .zone-items {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
                min-height: 50px;
            }

            .zone-items.horizontal {
                flex-direction: row;
                flex-wrap: wrap;
            }

            .zone-placeholder {
                padding: 0.75rem;
                border: 1px dashed var(--zone-border);
                border-radius: 4px;
                text-align: center;
                color: var(--ax-text-muted, #6c757d);
                font-size: 0.85rem;
            }

            /* Sequence variant */
            .sequence-container {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }

            .sequence-slot {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 0.5rem;
                background: var(--zone-bg);
                border: 2px dashed var(--zone-border);
                border-radius: 6px;
                min-height: 48px;
                transition: border-color 0.15s, background 0.15s;
            }

            .sequence-slot.drag-over {
                border-color: var(--ax-primary-color, #0d6efd);
                background: var(--ax-primary-light, #e7f1ff);
            }

            .sequence-slot.filled {
                border-style: solid;
            }

            .slot-number {
                width: 28px;
                height: 28px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: var(--ax-primary-color, #0d6efd);
                color: white;
                border-radius: 50%;
                font-weight: 600;
                font-size: 0.85rem;
                flex-shrink: 0;
            }

            /* Graphical variant */
            .graphical-container {
                position: relative;
                display: inline-block;
            }

            .graphical-background {
                display: block;
                max-width: 100%;
                height: auto;
                border-radius: 8px;
            }

            .graphical-placeholder {
                position: absolute;
                border: 2px dashed var(--zone-border);
                border-radius: 4px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: rgba(255,255,255,0.8);
                transition: border-color 0.15s, background 0.15s;
            }

            .graphical-placeholder.drag-over {
                border-color: var(--ax-primary-color, #0d6efd);
                background: rgba(13, 110, 253, 0.2);
            }

            .graphical-placeholder.filled {
                border-style: solid;
                background: rgba(255,255,255,0.95);
            }

            .placeholder-hint {
                font-size: 0.75rem;
                color: var(--ax-text-muted, #6c757d);
                text-align: center;
                padding: 0.25rem;
            }

            /* Remove button on placed items */
            .remove-btn {
                padding: 0 0.25rem;
                background: none;
                border: none;
                color: var(--ax-text-muted, #6c757d);
                cursor: pointer;
                font-size: 1rem;
                line-height: 1;
                opacity: 0.6;
                transition: opacity 0.15s;
            }

            .remove-btn:hover {
                opacity: 1;
                color: var(--ax-error-color, #dc3545);
            }

            /* Dark mode */
            @media (prefers-color-scheme: dark) {
                :host {
                    --zone-bg: #2d3748;
                    --zone-border: #4a5568;
                    --zone-hover: #374151;
                    --item-bg: #1a202c;
                    --item-border: #4a5568;
                }
            }
        `;
    }

    // =========================================================================
    // Rendering
    // =========================================================================

    render() {
        const content = this._renderVariant();
        
        this.shadowRoot.innerHTML = `
            <style>${this._styles || ''}</style>
            <div class="widget-container" role="application" aria-label="${this.prompt || 'Drag and drop interaction'}">
                ${this.prompt ? `<div class="prompt">${this.renderMarkdown(this.prompt)}</div>` : ''}
                <div class="drag-drop-container">
                    ${content}
                </div>
            </div>
        `;
    }

    _renderVariant() {
        switch (this.variant) {
            case 'category':
                return this._renderCategoryVariant();
            case 'sequence':
                return this._renderSequenceVariant();
            case 'graphical':
                return this._renderGraphicalVariant();
            default:
                return '<div class="error-message">Unknown variant</div>';
        }
    }

    _renderCategoryVariant() {
        const unplacedItems = this._getUnplacedItems();
        const zones = this.zones;

        return `
            <!-- Available items pool -->
            <div class="item-pool ${unplacedItems.length === 0 ? 'empty' : ''}" 
                 data-zone="pool"
                 role="list"
                 aria-label="Available items">
                ${unplacedItems.length > 0 
                    ? unplacedItems.map(item => this._renderDragItem(item)).join('')
                    : 'All items placed'
                }
            </div>

            <!-- Drop zones -->
            <div class="zones-container">
                ${zones.map(zone => this._renderDropZone(zone)).join('')}
            </div>
        `;
    }

    _renderDropZone(zone) {
        const zoneItems = this._originalItems.filter(item => 
            this._placements.get(item.id) === zone.id
        );

        return `
            <div class="drop-zone" 
                 data-zone="${zone.id}"
                 role="listbox"
                 aria-label="${zone.label}">
                <div class="zone-label">${this.escapeHtml(zone.label)}</div>
                <div class="zone-items ${zone.ordered ? '' : 'horizontal'}">
                    ${zoneItems.length > 0 
                        ? zoneItems.map(item => this._renderDragItem(item, true)).join('')
                        : `<div class="zone-placeholder">Drop items here</div>`
                    }
                </div>
            </div>
        `;
    }

    _renderSequenceVariant() {
        const totalSlots = this._originalItems.length;
        const unplacedItems = this._originalItems.filter(item => 
            !this._sequence.includes(item.id)
        );

        return `
            <!-- Available items pool -->
            <div class="item-pool ${unplacedItems.length === 0 ? 'empty' : ''}" 
                 data-zone="pool"
                 role="list"
                 aria-label="Available items">
                ${unplacedItems.length > 0 
                    ? unplacedItems.map(item => this._renderDragItem(item)).join('')
                    : 'All items placed'
                }
            </div>

            <!-- Sequence slots -->
            <div class="sequence-container" role="list" aria-label="Sequence order">
                ${Array.from({ length: totalSlots }, (_, i) => {
                    const itemId = this._sequence[i];
                    const item = itemId ? this._originalItems.find(it => it.id === itemId) : null;
                    return this._renderSequenceSlot(i, item);
                }).join('')}
            </div>
        `;
    }

    _renderSequenceSlot(index, item) {
        return `
            <div class="sequence-slot ${item ? 'filled' : ''}" 
                 data-slot="${index}"
                 role="listitem">
                <span class="slot-number">${index + 1}</span>
                ${item 
                    ? this._renderDragItem(item, true)
                    : '<span class="zone-placeholder" style="flex:1">Drop item here</span>'
                }
            </div>
        `;
    }

    _renderGraphicalVariant() {
        const placeholders = this.placeholders;
        const unplacedItems = this._getUnplacedItems();

        return `
            <!-- Available items pool -->
            <div class="item-pool ${unplacedItems.length === 0 ? 'empty' : ''}" 
                 data-zone="pool"
                 role="list"
                 aria-label="Available items">
                ${unplacedItems.length > 0 
                    ? unplacedItems.map(item => this._renderDragItem(item)).join('')
                    : 'All items placed'
                }
            </div>

            <!-- Graphical canvas -->
            <div class="graphical-container">
                ${this.backgroundImage 
                    ? `<img src="${this.backgroundImage}" class="graphical-background" alt="Background" />`
                    : ''
                }
                ${placeholders.map(ph => this._renderGraphicalPlaceholder(ph)).join('')}
            </div>
        `;
    }

    _renderGraphicalPlaceholder(placeholder) {
        const region = placeholder.region || {};
        const item = this._originalItems.find(it => {
            const pos = this._positions.get(it.id);
            return pos?.placeholderId === placeholder.id;
        });

        const style = `
            left: ${region.x || 0}px;
            top: ${region.y || 0}px;
            width: ${region.width || 100}px;
            height: ${region.height || 60}px;
        `;

        return `
            <div class="graphical-placeholder ${item ? 'filled' : ''}"
                 data-placeholder="${placeholder.id}"
                 style="${style}"
                 role="listitem"
                 aria-label="${placeholder.hint || 'Drop zone'}">
                ${item 
                    ? this._renderDragItem(item, true)
                    : `<span class="placeholder-hint">${this.escapeHtml(placeholder.hint || '')}</span>`
                }
            </div>
        `;
    }

    _renderDragItem(item, inZone = false) {
        return `
            <div class="drag-item" 
                 draggable="true" 
                 data-item-id="${item.id}"
                 role="option"
                 aria-grabbed="false"
                 tabindex="0">
                ${item.icon ? `<span class="item-icon">${item.icon}</span>` : ''}
                <span class="item-content">${this.escapeHtml(item.content)}</span>
                ${inZone ? `<button class="remove-btn" aria-label="Remove ${item.content}" data-remove="${item.id}">×</button>` : ''}
            </div>
        `;
    }

    _getUnplacedItems() {
        return this._originalItems.filter(item => {
            if (this.variant === 'sequence') {
                return !this._sequence.includes(item.id);
            } else if (this.variant === 'graphical') {
                return !this._positions.has(item.id);
            } else {
                return !this._placements.has(item.id);
            }
        });
    }

    // =========================================================================
    // Events
    // =========================================================================

    bindEvents() {
        // Drag start
        this.shadowRoot.querySelectorAll('.drag-item').forEach(el => {
            el.addEventListener('dragstart', (e) => this._handleDragStart(e));
            el.addEventListener('dragend', (e) => this._handleDragEnd(e));
            
            // Keyboard support
            el.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this._handleKeyboardDrag(el);
                }
            });
        });

        // Drop zones (category)
        this.shadowRoot.querySelectorAll('.drop-zone, .item-pool').forEach(zone => {
            zone.addEventListener('dragover', (e) => this._handleDragOver(e));
            zone.addEventListener('dragleave', (e) => this._handleDragLeave(e));
            zone.addEventListener('drop', (e) => this._handleDrop(e));
        });

        // Sequence slots
        this.shadowRoot.querySelectorAll('.sequence-slot').forEach(slot => {
            slot.addEventListener('dragover', (e) => this._handleDragOver(e));
            slot.addEventListener('dragleave', (e) => this._handleDragLeave(e));
            slot.addEventListener('drop', (e) => this._handleSequenceDrop(e));
        });

        // Graphical placeholders
        this.shadowRoot.querySelectorAll('.graphical-placeholder').forEach(ph => {
            ph.addEventListener('dragover', (e) => this._handleDragOver(e));
            ph.addEventListener('dragleave', (e) => this._handleDragLeave(e));
            ph.addEventListener('drop', (e) => this._handleGraphicalDrop(e));
        });

        // Remove buttons
        this.shadowRoot.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const itemId = btn.dataset.remove;
                this._removeItem(itemId);
            });
        });
    }

    _handleDragStart(e) {
        const itemEl = e.target.closest('.drag-item');
        if (!itemEl) return;

        this._draggedItem = itemEl.dataset.itemId;
        itemEl.classList.add('dragging');
        itemEl.setAttribute('aria-grabbed', 'true');
        
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', this._draggedItem);
    }

    _handleDragEnd(e) {
        const itemEl = e.target.closest('.drag-item');
        if (itemEl) {
            itemEl.classList.remove('dragging');
            itemEl.setAttribute('aria-grabbed', 'false');
        }
        this._draggedItem = null;
        
        // Clear all drag-over states
        this.shadowRoot.querySelectorAll('.drag-over').forEach(el => {
            el.classList.remove('drag-over');
        });
    }

    _handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        e.currentTarget.classList.add('drag-over');
    }

    _handleDragLeave(e) {
        e.currentTarget.classList.remove('drag-over');
    }

    _handleDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');
        
        const itemId = e.dataTransfer.getData('text/plain') || this._draggedItem;
        if (!itemId) return;

        const zoneId = e.currentTarget.dataset.zone;
        
        if (zoneId === 'pool') {
            // Return to pool
            this._placements.delete(itemId);
        } else if (zoneId) {
            // Check if zone can accept more items
            if (!this.allowMultiplePerZone) {
                // Remove existing item from this zone
                for (const [id, zone] of this._placements) {
                    if (zone === zoneId) {
                        this._placements.delete(id);
                        break;
                    }
                }
            }
            this._placements.set(itemId, zoneId);
        }

        this._dispatchDropEvent(itemId, zoneId);
        this.render();
        this.bindEvents();
    }

    _handleSequenceDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');
        
        const itemId = e.dataTransfer.getData('text/plain') || this._draggedItem;
        if (!itemId) return;

        const slotIndex = parseInt(e.currentTarget.dataset.slot);
        
        // Remove item from current position if already in sequence
        const currentIndex = this._sequence.indexOf(itemId);
        if (currentIndex !== -1) {
            this._sequence.splice(currentIndex, 1);
        }
        
        // Insert at new position
        this._sequence[slotIndex] = itemId;

        this._dispatchDropEvent(itemId, `slot-${slotIndex}`);
        this.render();
        this.bindEvents();
    }

    _handleGraphicalDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');
        
        const itemId = e.dataTransfer.getData('text/plain') || this._draggedItem;
        if (!itemId) return;

        const placeholderId = e.currentTarget.dataset.placeholder;
        const placeholder = this.placeholders.find(p => p.id === placeholderId);
        
        if (!placeholder) return;

        // Remove existing item from this placeholder
        for (const [id, pos] of this._positions) {
            if (pos.placeholderId === placeholderId) {
                this._positions.delete(id);
                break;
            }
        }

        // Remove item from its previous position
        this._positions.delete(itemId);

        // Place item
        this._positions.set(itemId, {
            x: placeholder.region?.x || 0,
            y: placeholder.region?.y || 0,
            placeholderId
        });

        this._dispatchDropEvent(itemId, placeholderId);
        this.render();
        this.bindEvents();
    }

    _removeItem(itemId) {
        if (this.variant === 'sequence') {
            const index = this._sequence.indexOf(itemId);
            if (index !== -1) {
                this._sequence[index] = undefined;
            }
        } else if (this.variant === 'graphical') {
            this._positions.delete(itemId);
        } else {
            this._placements.delete(itemId);
        }

        this.render();
        this.bindEvents();
    }

    _handleKeyboardDrag(el) {
        // Simple keyboard-based item moving (cycle through zones)
        const itemId = el.dataset.itemId;
        const zones = this.variant === 'category' ? this.zones : [];
        
        if (this.variant === 'category' && zones.length > 0) {
            const currentZone = this._placements.get(itemId);
            const currentIndex = currentZone ? zones.findIndex(z => z.id === currentZone) : -1;
            const nextIndex = (currentIndex + 1) % zones.length;
            
            this._placements.set(itemId, zones[nextIndex].id);
            this._dispatchDropEvent(itemId, zones[nextIndex].id);
            this.render();
            this.bindEvents();
            
            this.announce(`Moved to ${zones[nextIndex].label}`, 'polite');
        }
    }

    _dispatchDropEvent(itemId, targetId) {
        this.dispatchEvent(new CustomEvent('ax-drop', {
            bubbles: true,
            composed: true,
            detail: {
                widgetId: this.widgetId,
                itemId,
                targetId,
                value: this.getValue()
            }
        }));
    }

    // =========================================================================
    // Utilities
    // =========================================================================

    _shuffle(array) {
        const shuffled = [...array];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
    }

    async loadStyles() {
        this._styles = await this.getStyles();
    }
}

// Register custom element
if (!customElements.get('ax-drag-drop')) {
    customElements.define('ax-drag-drop', AxDragDrop);
}

export default AxDragDrop;
