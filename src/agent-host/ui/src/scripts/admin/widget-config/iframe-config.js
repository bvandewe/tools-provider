/**
 * IFrame Widget Configuration
 *
 * Configuration UI for the 'iframe' widget type.
 *
 * Python Schema Reference (IframeConfig from protocol/iframe.py):
 * - widget_id: str (required, alias: widgetId)
 * - source: str (required)
 * - title: str | None
 * - sandbox: IframeSandboxConfig | None
 * - permissions: IframePermissionsConfig | None
 * - communication: IframeCommunicationConfig | None
 * - loading: IframeLoadingConfig | None
 * - layout: IframeLayoutConfig | None
 * - initial_state: dict | None (alias: initialState)
 *
 * @module admin/widget-config/iframe-config
 */

import { WidgetConfigBase } from './config-base.js';

export class IframeConfig extends WidgetConfigBase {
    /**
     * Render the iframe widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        const sandbox = config.sandbox || {};
        const permissions = config.permissions || {};
        const loading = config.loading || {};
        const layout = config.layout || {};
        const dimensions = layout.dimensions || {};

        this.container.innerHTML = `
            <div class="widget-config widget-config-iframe">
                <div class="row g-2">
                    <div class="col-md-8">
                        <label class="form-label small mb-0">
                            Source URL
                            <span class="text-danger">*</span>
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="URL of the content to embed in the iframe."></i>
                        </label>
                        ${this.createTextInput('config-source', config.source, 'https://example.com/embed')}
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small mb-0">
                            Title
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Accessible title for the iframe."></i>
                        </label>
                        ${this.createTextInput('config-title', config.title, 'Embedded content')}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Width
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Width in pixels or percentage."></i>
                        </label>
                        ${this.createTextInput('config-width', dimensions.width ?? '', '100%')}
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small mb-0">
                            Height
                            <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                               title="Height in pixels."></i>
                        </label>
                        ${this.createTextInput('config-height', dimensions.height ?? '', '400')}
                    </div>
                    <div class="col-md-3">
                        ${this.createSwitch('config-resizable', `${this.uid}-resizable`, 'Resizable', 'Allow users to resize the iframe.', layout.resizable ?? false)}
                    </div>
                    <div class="col-md-3">
                        ${this.createSwitch('config-movable', `${this.uid}-movable`, 'Movable', 'Allow users to move the iframe.', layout.movable ?? false)}
                    </div>
                </div>

                ${this.createCollapsibleSection(
                    `${this.uid}-sandbox`,
                    'Sandbox Permissions',
                    `
                    <p class="text-muted small mb-2">Control what the embedded content can do:</p>
                    <div class="row g-2">
                        <div class="col-md-4">
                            ${this.createSwitch(
                                'config-allow-scripts',
                                `${this.uid}-allow-scripts`,
                                'Allow Scripts',
                                'Allow JavaScript execution.',
                                sandbox.allow_scripts ?? sandbox.allowScripts ?? true
                            )}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch('config-allow-forms', `${this.uid}-allow-forms`, 'Allow Forms', 'Allow form submission.', sandbox.allow_forms ?? sandbox.allowForms ?? false)}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch(
                                'config-allow-same-origin',
                                `${this.uid}-allow-same-origin`,
                                'Allow Same Origin',
                                'Allow same-origin access (security risk).',
                                sandbox.allow_same_origin ?? sandbox.allowSameOrigin ?? false
                            )}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch('config-allow-popups', `${this.uid}-allow-popups`, 'Allow Popups', 'Allow opening new windows.', sandbox.allow_popups ?? sandbox.allowPopups ?? false)}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch(
                                'config-allow-modals',
                                `${this.uid}-allow-modals`,
                                'Allow Modals',
                                'Allow alert/confirm dialogs.',
                                sandbox.allow_modals ?? sandbox.allowModals ?? false
                            )}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch(
                                'config-allow-downloads',
                                `${this.uid}-allow-downloads`,
                                'Allow Downloads',
                                'Allow file downloads.',
                                sandbox.allow_downloads ?? sandbox.allowDownloads ?? false
                            )}
                        </div>
                    </div>
                `
                )}

                ${this.createCollapsibleSection(
                    `${this.uid}-permissions`,
                    'Feature Permissions',
                    `
                    <p class="text-muted small mb-2">Browser feature access:</p>
                    <div class="row g-2">
                        <div class="col-md-4">
                            ${this.createSwitch('config-perm-camera', `${this.uid}-perm-camera`, 'Camera', 'Allow camera access.', permissions.camera ?? false)}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch('config-perm-microphone', `${this.uid}-perm-microphone`, 'Microphone', 'Allow microphone access.', permissions.microphone ?? false)}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch('config-perm-geolocation', `${this.uid}-perm-geolocation`, 'Geolocation', 'Allow location access.', permissions.geolocation ?? false)}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch('config-perm-fullscreen', `${this.uid}-perm-fullscreen`, 'Fullscreen', 'Allow fullscreen mode.', permissions.fullscreen ?? false)}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch('config-perm-clipboard', `${this.uid}-perm-clipboard`, 'Clipboard', 'Allow clipboard access.', permissions.clipboard ?? false)}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch('config-perm-payment', `${this.uid}-perm-payment`, 'Payment', 'Allow payment APIs.', permissions.payment ?? false)}
                        </div>
                    </div>
                `
                )}

                ${this.createCollapsibleSection(
                    `${this.uid}-loading`,
                    'Loading Options',
                    `
                    <div class="row g-2">
                        <div class="col-md-3">
                            ${this.createSwitch(
                                'config-show-spinner',
                                `${this.uid}-show-spinner`,
                                'Show Spinner',
                                'Show loading spinner while iframe loads.',
                                loading.show_spinner ?? loading.showSpinner ?? true
                            )}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch(
                                'config-retry-on-error',
                                `${this.uid}-retry-on-error`,
                                'Retry on Error',
                                'Automatically retry if loading fails.',
                                loading.retry_on_error ?? loading.retryOnError ?? true
                            )}
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small mb-0">
                                Timeout (ms)
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="Loading timeout in milliseconds."></i>
                            </label>
                            ${this.createNumberInput('config-timeout', loading.timeout ?? '', '30000', { min: 1000 })}
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small mb-0">
                                Max Retries
                                <i class="bi bi-question-circle text-muted ms-1" data-bs-toggle="tooltip"
                                   title="Maximum retry attempts."></i>
                            </label>
                            ${this.createNumberInput('config-max-retries', loading.max_retries ?? loading.maxRetries ?? 3, '3', { min: 0, max: 10 })}
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
        config.source = this.getInputValue('config-source', '');

        const title = this.getInputValue('config-title');
        if (title) config.title = title;

        // Build sandbox config
        const sandbox = {};
        sandbox.allow_scripts = this.getChecked('config-allow-scripts');
        sandbox.allow_forms = this.getChecked('config-allow-forms');
        sandbox.allow_same_origin = this.getChecked('config-allow-same-origin');
        sandbox.allow_popups = this.getChecked('config-allow-popups');
        sandbox.allow_modals = this.getChecked('config-allow-modals');
        sandbox.allow_downloads = this.getChecked('config-allow-downloads');

        // Only include if not all defaults
        if (sandbox.allow_forms || sandbox.allow_same_origin || sandbox.allow_popups || sandbox.allow_modals || sandbox.allow_downloads || !sandbox.allow_scripts) {
            config.sandbox = sandbox;
        }

        // Build permissions config
        const permissions = {};
        permissions.camera = this.getChecked('config-perm-camera');
        permissions.microphone = this.getChecked('config-perm-microphone');
        permissions.geolocation = this.getChecked('config-perm-geolocation');
        permissions.fullscreen = this.getChecked('config-perm-fullscreen');
        permissions.clipboard = this.getChecked('config-perm-clipboard');
        permissions.payment = this.getChecked('config-perm-payment');

        // Only include if any permission is enabled
        if (Object.values(permissions).some(v => v)) {
            config.permissions = permissions;
        }

        // Build loading config
        const loading = {};
        const showSpinner = this.getChecked('config-show-spinner');
        if (!showSpinner) loading.show_spinner = false;

        const retryOnError = this.getChecked('config-retry-on-error');
        if (!retryOnError) loading.retry_on_error = false;

        const timeout = this.getIntValue('config-timeout');
        if (timeout !== null) loading.timeout = timeout;

        const maxRetries = this.getIntValue('config-max-retries');
        if (maxRetries !== null && maxRetries !== 3) loading.max_retries = maxRetries;

        if (Object.keys(loading).length > 0) {
            config.loading = loading;
        }

        // Build layout config
        const layout = {};
        const width = this.getInputValue('config-width');
        const height = this.getInputValue('config-height');

        if (width || height) {
            layout.dimensions = {};
            if (width) layout.dimensions.width = width;
            if (height) layout.dimensions.height = height;
        }

        if (this.getChecked('config-resizable')) layout.resizable = true;
        if (this.getChecked('config-movable')) layout.movable = true;

        if (Object.keys(layout).length > 0) {
            config.layout = layout;
        }

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const source = this.getInputValue('config-source');
        if (!source) {
            errors.push('Source URL is required');
        } else if (!source.startsWith('http://') && !source.startsWith('https://')) {
            errors.push('Source URL must be a valid HTTP/HTTPS URL');
        }

        return { valid: errors.length === 0, errors };
    }
}
