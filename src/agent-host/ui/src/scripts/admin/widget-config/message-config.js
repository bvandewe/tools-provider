/**
 * Message Widget Configuration
 *
 * Configuration UI for the 'message' widget type.
 * Message widgets display text only (no user input).
 *
 * Python Schema Reference: No specific config - message uses stem only
 *
 * @module admin/widget-config/message-config
 */

import { WidgetConfigBase } from './config-base.js';

export class MessageConfig extends WidgetConfigBase {
    /**
     * Render the message widget configuration UI
     * @param {Object} config - Widget configuration (unused for message)
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        this.container.innerHTML = `
            <div class="widget-config widget-config-message">
                <p class="text-muted small mb-0">
                    <i class="bi bi-info-circle me-1"></i>
                    Message widgets display text only (no user input).
                    The message content is defined in the Stem field above.
                </p>
            </div>
        `;
    }

    /**
     * Get configuration values
     * @returns {Object} Empty config object (message has no config)
     */
    getValue() {
        return {};
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Always valid
     */
    validate() {
        return { valid: true, errors: [] };
    }
}
