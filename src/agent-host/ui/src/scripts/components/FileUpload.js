/**
 * FileUpload Component
 * Handles file selection, upload, and display of attached files
 */
import { api } from '../services/api.js';
import { showToast } from '../services/modals.js';

// Maximum file size in bytes (10MB)
const MAX_FILE_SIZE = 10 * 1024 * 1024;

// Allowed file extensions (must match backend)
const ALLOWED_EXTENSIONS = new Set([
    // Text files
    '.txt',
    '.md',
    '.json',
    '.csv',
    '.xml',
    '.yaml',
    '.yml',
    // Documents
    '.pdf',
    '.docx',
    '.doc',
    '.xlsx',
    '.xls',
    '.pptx',
    '.ppt',
    // Images
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.svg',
    '.webp',
    // Code
    '.py',
    '.js',
    '.ts',
    '.html',
    '.css',
    // Archives
    '.zip',
]);

// State
let attachedFiles = [];
let isUploading = false;

// DOM elements (set during init)
let uploadBtn = null;
let fileInput = null;
let attachedFilesContainer = null;

/**
 * Initialize the file upload component
 * @param {Object} elements - DOM elements
 * @param {HTMLElement} elements.uploadBtn - Upload button
 * @param {HTMLElement} elements.fileInput - Hidden file input
 * @param {HTMLElement} elements.attachedFilesContainer - Container for file badges
 */
export function initFileUpload(elements) {
    uploadBtn = elements.uploadBtn;
    fileInput = elements.fileInput;
    attachedFilesContainer = elements.attachedFilesContainer;

    if (!uploadBtn || !fileInput || !attachedFilesContainer) {
        console.warn('FileUpload: Missing required elements');
        return;
    }

    // Click upload button -> trigger file input
    uploadBtn.addEventListener('click', () => {
        if (!isUploading) {
            fileInput.click();
        }
    });

    // File selected
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop on chat area
    const chatArea = document.querySelector('.chat-area');
    if (chatArea) {
        chatArea.addEventListener('dragover', handleDragOver);
        chatArea.addEventListener('dragleave', handleDragLeave);
        chatArea.addEventListener('drop', handleDrop);
    }
}

/**
 * Enable/disable the upload button
 * @param {boolean} enabled - Whether to enable
 */
export function setUploadEnabled(enabled) {
    if (uploadBtn) {
        uploadBtn.disabled = !enabled;
    }
}

/**
 * Get list of attached files
 * @returns {Array} Array of attached file info
 */
export function getAttachedFiles() {
    return [...attachedFiles];
}

/**
 * Clear all attached files
 */
export function clearAttachedFiles() {
    attachedFiles = [];
    renderAttachedFiles();
}

/**
 * Check if there are any attached files
 * @returns {boolean}
 */
export function hasAttachedFiles() {
    return attachedFiles.length > 0;
}

/**
 * Get attached files as a message prefix
 * Returns text to prepend to user message indicating attached files
 * @returns {string}
 */
export function getAttachedFilesMessage() {
    if (attachedFiles.length === 0) return '';

    const fileList = attachedFiles.map(f => `\`${f.filename}\``).join(', ');
    return `[Attached files: ${fileList}. Use file_reader to read them.]\n\n`;
}

// =============================================================================
// Event Handlers
// =============================================================================

function handleFileSelect(event) {
    const files = event.target.files;
    if (files && files.length > 0) {
        uploadFiles(Array.from(files));
    }
    // Reset input so same file can be selected again
    event.target.value = '';
}

function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.add('drag-over');
}

function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove('drag-over');
}

function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove('drag-over');

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
        uploadFiles(Array.from(files));
    }
}

// =============================================================================
// Upload Logic
// =============================================================================

async function uploadFiles(files) {
    if (isUploading) return;

    for (const file of files) {
        await uploadSingleFile(file);
    }
}

async function uploadSingleFile(file) {
    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
        showToast(`File "${file.name}" is too large. Maximum size is 10MB.`, 'error');
        return;
    }

    // Validate extension
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.has(ext)) {
        showToast(`File type "${ext}" is not allowed.`, 'error');
        return;
    }

    // Check if already attached
    if (attachedFiles.some(f => f.filename === file.name)) {
        showToast(`File "${file.name}" is already attached.`, 'warning');
        return;
    }

    isUploading = true;
    setUploadButtonState('uploading');

    try {
        const result = await api.uploadFile(file);

        // Add to attached files
        attachedFiles.push({
            filename: result.filename,
            size_bytes: result.size_bytes,
            expires_at: result.expires_at,
            content_type: result.content_type,
        });

        renderAttachedFiles();
        showToast(`File "${result.filename}" uploaded successfully.`, 'success');
    } catch (error) {
        console.error('File upload failed:', error);
        showToast(error.message || 'Failed to upload file', 'error');
    } finally {
        isUploading = false;
        setUploadButtonState('ready');
    }
}

// =============================================================================
// UI Rendering
// =============================================================================

function setUploadButtonState(state) {
    if (!uploadBtn) return;

    const icon = uploadBtn.querySelector('i');

    switch (state) {
        case 'uploading':
            uploadBtn.disabled = true;
            if (icon) {
                icon.className = 'bi bi-arrow-repeat spin';
            }
            break;
        case 'ready':
        default:
            uploadBtn.disabled = false;
            if (icon) {
                icon.className = 'bi bi-paperclip';
            }
            break;
    }
}

function renderAttachedFiles() {
    if (!attachedFilesContainer) return;

    if (attachedFiles.length === 0) {
        attachedFilesContainer.classList.add('d-none');
        attachedFilesContainer.innerHTML = '';
        return;
    }

    attachedFilesContainer.classList.remove('d-none');
    attachedFilesContainer.innerHTML = attachedFiles
        .map(
            (file, index) => `
        <div class="file-badge" data-index="${index}">
            <i class="bi ${getFileIcon(file.filename)}"></i>
            <span class="file-name">${escapeHtml(file.filename)}</span>
            <span class="file-size">(${formatFileSize(file.size_bytes)})</span>
            <button type="button" class="btn-remove" title="Remove file">
                <i class="bi bi-x"></i>
            </button>
        </div>
    `
        )
        .join('');

    // Bind remove buttons
    attachedFilesContainer.querySelectorAll('.btn-remove').forEach(btn => {
        btn.addEventListener('click', e => {
            const badge = e.target.closest('.file-badge');
            const index = parseInt(badge.dataset.index, 10);
            removeAttachedFile(index);
        });
    });
}

function removeAttachedFile(index) {
    if (index >= 0 && index < attachedFiles.length) {
        const removed = attachedFiles.splice(index, 1)[0];
        renderAttachedFiles();
        showToast(`Removed "${removed.filename}"`, 'info');
    }
}

// =============================================================================
// Utilities
// =============================================================================

function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const iconMap = {
        // Documents
        pdf: 'bi-file-earmark-pdf',
        doc: 'bi-file-earmark-word',
        docx: 'bi-file-earmark-word',
        xls: 'bi-file-earmark-excel',
        xlsx: 'bi-file-earmark-excel',
        ppt: 'bi-file-earmark-ppt',
        pptx: 'bi-file-earmark-ppt',
        // Text/Code
        txt: 'bi-file-earmark-text',
        md: 'bi-file-earmark-text',
        json: 'bi-file-earmark-code',
        csv: 'bi-file-earmark-spreadsheet',
        xml: 'bi-file-earmark-code',
        yaml: 'bi-file-earmark-code',
        yml: 'bi-file-earmark-code',
        py: 'bi-file-earmark-code',
        js: 'bi-file-earmark-code',
        ts: 'bi-file-earmark-code',
        html: 'bi-file-earmark-code',
        css: 'bi-file-earmark-code',
        // Images
        png: 'bi-file-earmark-image',
        jpg: 'bi-file-earmark-image',
        jpeg: 'bi-file-earmark-image',
        gif: 'bi-file-earmark-image',
        svg: 'bi-file-earmark-image',
        webp: 'bi-file-earmark-image',
        // Archives
        zip: 'bi-file-earmark-zip',
    };
    return iconMap[ext] || 'bi-file-earmark';
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
