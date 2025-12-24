/**
 * StatsManager - Statistics Display Management
 *
 * Handles stats card updates based on state changes.
 *
 * @module managers/StatsManager
 */

import { stateManager, StateKeys } from '../core/state-manager.js';

/**
 * StatsManager handles statistics display
 */
export class StatsManager {
    /**
     * Create StatsManager instance
     */
    constructor() {
        /** @type {boolean} */
        this._initialized = false;

        /** @type {Function[]} */
        this._unsubscribers = [];
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize stats manager
     */
    init() {
        if (this._initialized) {
            console.warn('[StatsManager] Already initialized');
            return;
        }

        this._subscribeToState();
        this._initialized = true;
        console.log('[StatsManager] Initialized');
    }

    /**
     * Cleanup and destroy
     */
    destroy() {
        this._unsubscribers.forEach(unsub => unsub());
        this._unsubscribers = [];
        this._initialized = false;
        console.log('[StatsManager] Destroyed');
    }

    /**
     * Subscribe to state changes
     * @private
     */
    _subscribeToState() {
        this._unsubscribers.push(
            stateManager.subscribe(StateKeys.NAMESPACE_COUNT, value => {
                this._updateStatElement('namespace-count', value);
            })
        );

        this._unsubscribers.push(
            stateManager.subscribe(StateKeys.TERM_COUNT, value => {
                this._updateStatElement('term-count', value);
            })
        );

        this._unsubscribers.push(
            stateManager.subscribe(StateKeys.RELATIONSHIP_COUNT, value => {
                this._updateStatElement('relationship-count', value);
            })
        );
    }

    // =========================================================================
    // Stats Updates
    // =========================================================================

    /**
     * Update stats display from current state
     */
    updateStats() {
        const namespaceCount = stateManager.get(StateKeys.NAMESPACE_COUNT, 0);
        const termCount = stateManager.get(StateKeys.TERM_COUNT, 0);
        const relationshipCount = stateManager.get(StateKeys.RELATIONSHIP_COUNT, 0);

        this._updateStatElement('namespace-count', namespaceCount);
        this._updateStatElement('term-count', termCount);
        this._updateStatElement('relationship-count', relationshipCount);
    }

    /**
     * Update a stat element
     * @private
     * @param {string} elementId - Element ID
     * @param {number|string} value - Value to display
     */
    _updateStatElement(elementId, value) {
        const el = document.getElementById(elementId);
        if (el) {
            el.textContent = value?.toString() ?? '-';
        }
    }
}

// =============================================================================
// Singleton Export
// =============================================================================

export const statsManager = new StatsManager();
