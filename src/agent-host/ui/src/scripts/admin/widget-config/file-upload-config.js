/**
 * File Upload Widget Configuration
 *
 * Configuration UI for the 'file_upload' widget type.
 *
 * Python Schema Reference (FileUploadConfig):
 * - accept: list[str] (required) - allowed MIME types/extensions
 * - max_file_size: int (required, alias: maxFileSize) - max size in bytes
 * - max_files: int (required, alias: maxFiles) - maximum number of files
 * - min_files: int | None (alias: minFiles)
 * - allow_drag_drop: bool | None (alias: allowDragDrop)
 * - show_preview: bool | None (alias: showPreview)
 * - preview_max_height: int | None (alias: previewMaxHeight)
 * - upload_endpoint: str (required, alias: uploadEndpoint)
 * - upload_method: str | None (alias: uploadMethod) - "POST" | "PUT"
 * - upload_headers: dict | None (alias: uploadHeaders)
 * - auto_upload: bool | None (alias: autoUpload)
 * - show_progress: bool | None (alias: showProgress)
 * - allow_remove: bool | None (alias: allowRemove)
 * - placeholder: str | None
 * - helper_text: str | None (alias: helperText)
 *
 * @module admin/widget-config/file-upload-config
 */

import { WidgetConfigBase } from './config-base.js';

/**
 * Upload method options
 */
const UPLOAD_METHOD_OPTIONS = [
    { value: 'POST', label: 'POST' },
    { value: 'PUT', label: 'PUT' },
];

/**
 * Common file type presets
 */
const FILE_TYPE_PRESETS = {
    images: '.jpg,.jpeg,.png,.gif,.webp,image/*',
    documents: '.pdf,.doc,.docx,.txt,.rtf,application/pdf',
    spreadsheets: '.xls,.xlsx,.csv,application/vnd.ms-excel',
    code: '.js,.ts,.py,.java,.c,.cpp,.h,.json,.xml,.yaml,.yml',
    audio: '.mp3,.wav,.ogg,.flac,audio/*',
    video: '.mp4,.webm,.avi,.mov,video/*',
    any: '*',
};

export class FileUploadConfig extends WidgetConfigBase {
    /**
     * Render the file upload widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        // Convert accept array to comma-separated string
        const accept = config.accept || [];
        const acceptText = accept.join(', ');

        // Convert max file size from bytes to MB for display
        const maxSizeMB = config.max_file_size ?? config.maxFileSize ?? 10485760;
        const maxSizeDisplay = Math.round(maxSizeMB / 1048576);

        this.container.innerHTML = `
            <div class="widget-config widget-config-file-upload">
                <div class="row g-2">
                    <div class="col-md-8">
                        ${this.createFormGroup(
                            'Upload Endpoint',
                            this.createTextInput('config-endpoint', config.upload_endpoint ?? config.uploadEndpoint ?? '', '/api/upload'),
                            'Server endpoint URL for file uploads.',
                            true
                        )}
                    </div>
                    <div class="col-md-4">
                        ${this.createFormGroup(
                            'Upload Method',
                            this.createSelect('config-method', UPLOAD_METHOD_OPTIONS, config.upload_method ?? config.uploadMethod ?? 'POST'),
                            'HTTP method for upload.'
                        )}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-12">
                        ${this.createFormGroup(
                            'Accepted File Types',
                            this.createTextInput('config-accept', acceptText, '.pdf, .doc, .docx, image/*, application/pdf'),
                            'Comma-separated MIME types or extensions.',
                            true
                        )}
                    </div>
                </div>

                <div class="mb-2">
                    <small class="text-muted">
                        <strong>Presets:</strong>
                        ${Object.entries(FILE_TYPE_PRESETS)
                            .map(([key, value]) => `<a href="#" class="preset-link me-2" data-preset="${value}">${key}</a>`)
                            .join('')}
                    </small>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-3">
                        ${this.createFormGroup('Max File Size (MB)', this.createNumberInput('config-max-size', maxSizeDisplay, 1, 1000, 1), 'Maximum size per file in megabytes.', true)}
                    </div>
                    <div class="col-md-3">
                        ${this.createFormGroup('Max Files', this.createNumberInput('config-max-files', config.max_files ?? config.maxFiles ?? 1, 1, 100, 1), 'Maximum number of files allowed.', true)}
                    </div>
                    <div class="col-md-3">
                        ${this.createFormGroup('Min Files', this.createNumberInput('config-min-files', config.min_files ?? config.minFiles ?? '', 0, 100, 1), 'Minimum required files.')}
                    </div>
                    <div class="col-md-3">
                        ${this.createFormGroup(
                            'Preview Height',
                            this.createNumberInput('config-preview-height', config.preview_max_height ?? config.previewMaxHeight ?? '', 50, 500, 10),
                            'Max height for previews (px).'
                        )}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-6">
                        ${this.createFormGroup(
                            'Placeholder Text',
                            this.createTextInput('config-placeholder', config.placeholder ?? '', 'Drag files here or click to browse...'),
                            'Text shown in upload area.'
                        )}
                    </div>
                    <div class="col-md-6">
                        ${this.createFormGroup(
                            'Helper Text',
                            this.createTextInput('config-helper', config.helper_text ?? config.helperText ?? '', 'Maximum 10MB per file'),
                            'Additional help text below upload area.'
                        )}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-2">
                        ${this.createSwitch('config-drag-drop', `${this.uid}-drag-drop`, 'Drag & Drop', 'Allow drag and drop uploads.', config.allow_drag_drop ?? config.allowDragDrop ?? true)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-preview', `${this.uid}-preview`, 'Show Preview', 'Show file previews.', config.show_preview ?? config.showPreview ?? true)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-auto-upload', `${this.uid}-auto-upload`, 'Auto Upload', 'Upload immediately on select.', config.auto_upload ?? config.autoUpload ?? false)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-progress', `${this.uid}-progress`, 'Show Progress', 'Display upload progress.', config.show_progress ?? config.showProgress ?? true)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-allow-remove', `${this.uid}-allow-remove`, 'Allow Remove', 'Allow removing files.', config.allow_remove ?? config.allowRemove ?? true)}
                    </div>
                </div>
            </div>
        `;

        this.initTooltips();
        this.initPresetLinks();
    }

    /**
     * Initialize preset link click handlers
     */
    initPresetLinks() {
        const links = this.container.querySelectorAll('.preset-link');
        links.forEach(link => {
            link.addEventListener('click', e => {
                e.preventDefault();
                const preset = link.dataset.preset;
                const input = this.container.querySelector('[data-field="config-accept"]');
                if (input) input.value = preset;
            });
        });
    }

    /**
     * Get configuration values matching Python schema
     * @returns {Object} Widget configuration
     */
    getValue() {
        const config = {};

        config.upload_endpoint = this.getInputValue('config-endpoint', '');
        config.upload_method = this.getInputValue('config-method', 'POST');

        // Parse accept types
        const acceptText = this.getInputValue('config-accept', '');
        config.accept = acceptText
            .split(',')
            .map(t => t.trim())
            .filter(t => t.length > 0);

        // Convert MB to bytes
        const maxSizeMB = parseInt(this.getInputValue('config-max-size', '10'), 10);
        config.max_file_size = maxSizeMB * 1048576;

        config.max_files = parseInt(this.getInputValue('config-max-files', '1'), 10);

        const minFiles = this.getInputValue('config-min-files');
        if (minFiles !== '') {
            config.min_files = parseInt(minFiles, 10);
        }

        const previewHeight = this.getInputValue('config-preview-height');
        if (previewHeight !== '') {
            config.preview_max_height = parseInt(previewHeight, 10);
        }

        const placeholder = this.getInputValue('config-placeholder');
        if (placeholder) config.placeholder = placeholder;

        const helperText = this.getInputValue('config-helper');
        if (helperText) config.helper_text = helperText;

        const dragDrop = this.getChecked('config-drag-drop');
        if (!dragDrop) config.allow_drag_drop = false;

        const showPreview = this.getChecked('config-preview');
        if (!showPreview) config.show_preview = false;

        const autoUpload = this.getChecked('config-auto-upload');
        if (autoUpload) config.auto_upload = true;

        const showProgress = this.getChecked('config-progress');
        if (!showProgress) config.show_progress = false;

        const allowRemove = this.getChecked('config-allow-remove');
        if (!allowRemove) config.allow_remove = false;

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const endpoint = this.getInputValue('config-endpoint', '');
        if (!endpoint) {
            errors.push('Upload endpoint is required');
        }

        const acceptText = this.getInputValue('config-accept', '');
        if (!acceptText.trim()) {
            errors.push('At least one accepted file type is required');
        }

        const maxSize = parseInt(this.getInputValue('config-max-size', '0'), 10);
        if (maxSize < 1) {
            errors.push('Max file size must be at least 1 MB');
        }

        const maxFiles = parseInt(this.getInputValue('config-max-files', '0'), 10);
        if (maxFiles < 1) {
            errors.push('Max files must be at least 1');
        }

        const minFiles = this.getInputValue('config-min-files');
        if (minFiles !== '') {
            const min = parseInt(minFiles, 10);
            if (min > maxFiles) {
                errors.push('Min files cannot exceed max files');
            }
        }

        return { valid: errors.length === 0, errors };
    }
}
