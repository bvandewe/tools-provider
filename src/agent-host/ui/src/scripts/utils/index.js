/**
 * Utils Module - Pure Utility Functions
 *
 * Provides pure functions with no side effects or external dependencies.
 * Organized by concern:
 * - dom: DOM manipulation helpers
 * - format: Text and data formatting
 * - storage: LocalStorage/SessionStorage helpers
 * - validation: Input validation functions
 */

// DOM utilities
export {
    escapeHtml,
    parseHtml,
    createElement,
    $,
    $$,
    show,
    hide,
    toggle,
    scrollToBottom,
    isNearBottom,
    isMobile,
    isTouchDevice,
    focus,
    trapFocus,
    MOBILE_BREAKPOINT,
} from './dom.js';

// Format utilities
export {
    truncate,
    capitalize,
    titleCase,
    camelToKebab,
    kebabToCamel,
    formatDate,
    formatDateTime,
    formatTime,
    formatRelativeTime,
    formatDuration,
    formatNumber,
    formatBytes,
    formatPercent,
} from './format.js';

// Storage utilities
export {
    STORAGE_KEYS,
    getItem,
    setItem,
    removeItem,
    hasItem,
    getKeysByPrefix,
    removeByPrefix,
    getPinnedConversations,
    savePinnedConversations,
    togglePinnedConversation,
    getPinnedSessions,
    savePinnedSessions,
    getSelectedModel,
    saveSelectedModel,
    getSidebarCollapsed,
    saveSidebarCollapsed,
    getTheme,
    saveTheme,
    getSelectedDefinitionId,
    saveSelectedDefinitionId,
} from './storage.js';

// Validation utilities
export {
    isNonEmptyString,
    isValidEmail,
    isValidUrl,
    isValidUuid,
    isValidNumber,
    isInRange,
    isPositiveInteger,
    isPlainObject,
    hasRequiredKeys,
    isNonEmptyArray,
    allItemsValid,
    createValidationResult,
    mergeValidationResults,
    validateRequired,
    validateLength,
    validateRange,
} from './validation.js';
