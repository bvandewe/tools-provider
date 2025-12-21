/**
 * Format Utilities - Text and data formatting functions
 *
 * @module utils/format
 */

// =============================================================================
// Text Formatting
// =============================================================================

/**
 * Truncate text to max length with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @param {string} [suffix='...'] - Suffix to add when truncated
 * @returns {string} Truncated text
 */
export function truncate(text, maxLength, suffix = '...') {
    if (!text || text.length <= maxLength) return text || '';
    return text.slice(0, maxLength - suffix.length) + suffix;
}

/**
 * Capitalize first letter of string
 * @param {string} str - String to capitalize
 * @returns {string} Capitalized string
 */
export function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Convert string to title case
 * @param {string} str - String to convert
 * @returns {string} Title case string
 */
export function titleCase(str) {
    if (!str) return '';
    return str.replace(/\w\S*/g, txt =>
        txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase()
    );
}

/**
 * Convert camelCase to kebab-case
 * @param {string} str - String to convert
 * @returns {string} Kebab case string
 */
export function camelToKebab(str) {
    if (!str) return '';
    return str.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase();
}

/**
 * Convert kebab-case to camelCase
 * @param {string} str - String to convert
 * @returns {string} Camel case string
 */
export function kebabToCamel(str) {
    if (!str) return '';
    return str.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
}

// =============================================================================
// Date & Time Formatting
// =============================================================================

/**
 * Format a date for display
 * @param {Date|string|number} date - Date to format
 * @param {Intl.DateTimeFormatOptions} [options] - Formatting options
 * @returns {string} Formatted date
 */
export function formatDate(date, options = {}) {
    const d = date instanceof Date ? date : new Date(date);
    if (isNaN(d.getTime())) return '';

    const defaults = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    };

    return d.toLocaleDateString(undefined, { ...defaults, ...options });
}

/**
 * Format a date with time
 * @param {Date|string|number} date - Date to format
 * @returns {string} Formatted date and time
 */
export function formatDateTime(date) {
    const d = date instanceof Date ? date : new Date(date);
    if (isNaN(d.getTime())) return '';

    return d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

/**
 * Format time only
 * @param {Date|string|number} date - Date to format
 * @returns {string} Formatted time
 */
export function formatTime(date) {
    const d = date instanceof Date ? date : new Date(date);
    if (isNaN(d.getTime())) return '';

    return d.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
    });
}

/**
 * Format relative time (e.g., "5 minutes ago")
 * @param {Date|string|number} date - Date to format
 * @returns {string} Relative time string
 */
export function formatRelativeTime(date) {
    const d = date instanceof Date ? date : new Date(date);
    if (isNaN(d.getTime())) return '';

    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return 'just now';
    if (diffMin < 60) return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ago`;
    if (diffHour < 24) return `${diffHour} hour${diffHour !== 1 ? 's' : ''} ago`;
    if (diffDay < 7) return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`;

    return formatDate(d);
}

/**
 * Format duration in seconds to human readable
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration (e.g., "5:30" or "1:05:30")
 */
export function formatDuration(seconds) {
    if (typeof seconds !== 'number' || isNaN(seconds)) return '0:00';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

// =============================================================================
// Number Formatting
// =============================================================================

/**
 * Format number with thousand separators
 * @param {number} num - Number to format
 * @param {number} [decimals=0] - Decimal places
 * @returns {string} Formatted number
 */
export function formatNumber(num, decimals = 0) {
    if (typeof num !== 'number' || isNaN(num)) return '0';
    return num.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    });
}

/**
 * Format bytes to human readable size
 * @param {number} bytes - Bytes to format
 * @param {number} [decimals=1] - Decimal places
 * @returns {string} Formatted size (e.g., "1.5 MB")
 */
export function formatBytes(bytes, decimals = 1) {
    if (bytes === 0) return '0 Bytes';
    if (typeof bytes !== 'number' || isNaN(bytes)) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
}

/**
 * Format percentage
 * @param {number} value - Value (0-1 or 0-100)
 * @param {boolean} [isDecimal=true] - If true, value is 0-1
 * @param {number} [decimals=0] - Decimal places
 * @returns {string} Formatted percentage
 */
export function formatPercent(value, isDecimal = true, decimals = 0) {
    if (typeof value !== 'number' || isNaN(value)) return '0%';
    const percent = isDecimal ? value * 100 : value;
    return `${percent.toFixed(decimals)}%`;
}
