/**
 * DefinitionRenderer - Definition Tiles UI Renderer
 *
 * Renders agent definition tiles in the welcome screen.
 * Listens to UI rendering events from handlers.
 *
 * @module renderers/DefinitionRenderer
 */

import { eventBus, Events } from '../core/event-bus.js';
import { selectDefinition, getDefinitionIcon, getSelectedDefinitionId } from '../domain/definition.js';

/**
 * DefinitionRenderer manages definition tile rendering
 */
export class DefinitionRenderer {
    /**
     * Create a new DefinitionRenderer instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {HTMLElement|null} Container for definition tiles */
        this._tilesContainer = null;

        /** @type {Function[]} */
        this._unsubscribers = [];

        // Bind handlers
        this._handleRenderTiles = this._handleRenderTiles.bind(this);
        this._handleUpdateSelection = this._handleUpdateSelection.bind(this);
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize definition renderer
     * @param {HTMLElement} container - Definition tiles container element
     */
    init(container) {
        if (this._initialized) {
            console.warn('[DefinitionRenderer] Already initialized');
            return;
        }

        this._tilesContainer = container;
        this._subscribeToEvents();
        this._initialized = true;

        console.log('[DefinitionRenderer] Initialized');
    }

    /**
     * Subscribe to rendering events
     * @private
     */
    _subscribeToEvents() {
        // Listen for render commands from handlers
        this._unsubscribers.push(eventBus.on(Events.UI_RENDER_DEFINITION_TILES, this._handleRenderTiles));

        this._unsubscribers.push(eventBus.on(Events.UI_UPDATE_DEFINITION_SELECTION, this._handleUpdateSelection));

        // Also listen to legacy event for backward compatibility
        this._unsubscribers.push(
            eventBus.on(Events.DEFINITION_LIST_LOADED, ({ definitions }) => {
                if (definitions) {
                    this.renderTiles(definitions);
                }
            })
        );
    }

    // =========================================================================
    // Event Handlers
    // =========================================================================

    /**
     * Handle render tiles event
     * @private
     * @param {Object} payload - Event payload
     */
    _handleRenderTiles({ definitions }) {
        this.renderTiles(definitions);
    }

    /**
     * Handle update selection event
     * @private
     * @param {Object} payload - Event payload
     */
    _handleUpdateSelection({ definitionId }) {
        this.updateTileSelection(definitionId);
    }

    // =========================================================================
    // Rendering
    // =========================================================================

    /**
     * Render definition tiles in the welcome screen
     * @param {Array} definitions - List of agent definitions
     */
    renderTiles(definitions) {
        if (!this._tilesContainer) return;

        this._tilesContainer.innerHTML = '';

        // Sort definitions alphabetically by name
        const sortedDefinitions = [...definitions].sort((a, b) => (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' }));

        sortedDefinitions.forEach(def => {
            const tile = document.createElement('button');
            tile.className = 'definition-tile';
            tile.dataset.definitionId = def.id;

            const icon = getDefinitionIcon(def);
            const hasTemplate = def.has_template || def.template_id;

            tile.innerHTML = `
                <div class="definition-tile-icon">
                    <i class="bi ${icon}"></i>
                    ${hasTemplate ? '<span class="proactive-badge" title="Has conversation template"><i class="bi bi-lightning-charge-fill"></i></span>' : ''}
                </div>
                <div class="definition-tile-content">
                    <h4 class="definition-tile-name">${this._escapeHtml(def.name)}</h4>
                    ${def.description ? `<p class="definition-tile-description">${this._escapeHtml(def.description)}</p>` : ''}
                </div>
            `;

            tile.addEventListener('click', () => {
                selectDefinition(def.id);
            });

            this._tilesContainer.appendChild(tile);
        });

        // Update selection state
        const selectedId = getSelectedDefinitionId();
        if (selectedId) {
            this.updateTileSelection(selectedId);
        }

        console.log(`[DefinitionRenderer] Rendered ${definitions.length} definition tiles`);
    }

    /**
     * Update the selected state of definition tiles
     * @param {string|null} selectedId - Selected definition ID (null to clear selection)
     */
    updateTileSelection(selectedId) {
        if (!this._tilesContainer) return;

        const tiles = this._tilesContainer.querySelectorAll('.definition-tile');
        tiles.forEach(tile => {
            const isSelected = tile.dataset.definitionId === selectedId;
            tile.classList.toggle('selected', isSelected);
        });
    }

    // =========================================================================
    // Utilities
    // =========================================================================

    /**
     * Escape HTML to prevent XSS
     * @private
     * @param {string} str - String to escape
     * @returns {string} Escaped string
     */
    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // =========================================================================
    // Getters
    // =========================================================================

    /**
     * Check if initialized
     * @returns {boolean}
     */
    get isInitialized() {
        return this._initialized;
    }

    // =========================================================================
    // Cleanup
    // =========================================================================

    /**
     * Cleanup resources
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._tilesContainer = null;
        this._initialized = false;
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const definitionRenderer = new DefinitionRenderer();
