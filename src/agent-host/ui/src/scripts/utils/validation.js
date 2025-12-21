/**
 * Validation Utilities - Input validation functions
 *
 * @module utils/validation
 */

// =============================================================================
// String Validation
// =============================================================================

/**
 * Check if a value is a non-empty string
 * @param {*} value - Value to check
 * @returns {boolean} True if non-empty string
 */
export function isNonEmptyString(value) {
    return typeof value === 'string' && value.trim().length > 0;
}

/**
 * Check if string matches email format
 * @param {string} email - Email to validate
 * @returns {boolean} True if valid email format
 */
export function isValidEmail(email) {
    if (!email) return false;
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Check if string matches URL format
 * @param {string} url - URL to validate
 * @returns {boolean} True if valid URL
 */
export function isValidUrl(url) {
    if (!url) return false;
    try {
        new URL(url);
        return true;
    } catch {
        return false;
    }
}

/**
 * Check if string matches UUID format
 * @param {string} uuid - UUID to validate
 * @returns {boolean} True if valid UUID
 */
export function isValidUuid(uuid) {
    if (!uuid) return false;
    const re = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    return re.test(uuid);
}

// =============================================================================
// Number Validation
// =============================================================================

/**
 * Check if value is a valid number
 * @param {*} value - Value to check
 * @returns {boolean} True if valid number
 */
export function isValidNumber(value) {
    return typeof value === 'number' && !isNaN(value) && isFinite(value);
}

/**
 * Check if number is within range
 * @param {number} value - Value to check
 * @param {number} min - Minimum value (inclusive)
 * @param {number} max - Maximum value (inclusive)
 * @returns {boolean} True if in range
 */
export function isInRange(value, min, max) {
    return isValidNumber(value) && value >= min && value <= max;
}

/**
 * Check if value is a positive integer
 * @param {*} value - Value to check
 * @returns {boolean} True if positive integer
 */
export function isPositiveInteger(value) {
    return Number.isInteger(value) && value > 0;
}

// =============================================================================
// Object Validation
// =============================================================================

/**
 * Check if value is a plain object
 * @param {*} value - Value to check
 * @returns {boolean} True if plain object
 */
export function isPlainObject(value) {
    return value !== null && typeof value === 'object' && value.constructor === Object;
}

/**
 * Check if object has required keys
 * @param {Object} obj - Object to check
 * @param {string[]} keys - Required keys
 * @returns {boolean} True if all keys present
 */
export function hasRequiredKeys(obj, keys) {
    if (!isPlainObject(obj)) return false;
    return keys.every(key => key in obj);
}

// =============================================================================
// Array Validation
// =============================================================================

/**
 * Check if value is a non-empty array
 * @param {*} value - Value to check
 * @returns {boolean} True if non-empty array
 */
export function isNonEmptyArray(value) {
    return Array.isArray(value) && value.length > 0;
}

/**
 * Check if all array items pass a validator
 * @param {Array} arr - Array to check
 * @param {Function} validator - Validator function
 * @returns {boolean} True if all items pass
 */
export function allItemsValid(arr, validator) {
    if (!Array.isArray(arr)) return false;
    return arr.every(validator);
}

// =============================================================================
// Form Validation Result
// =============================================================================

/**
 * @typedef {Object} ValidationResult
 * @property {boolean} valid - Whether validation passed
 * @property {string[]} errors - List of error messages
 * @property {string[]} warnings - List of warning messages
 */

/**
 * Create a validation result
 * @param {boolean} valid - Whether valid
 * @param {string[]} [errors=[]] - Error messages
 * @param {string[]} [warnings=[]] - Warning messages
 * @returns {ValidationResult} Validation result
 */
export function createValidationResult(valid, errors = [], warnings = []) {
    return { valid, errors, warnings };
}

/**
 * Merge multiple validation results
 * @param {ValidationResult[]} results - Results to merge
 * @returns {ValidationResult} Merged result
 */
export function mergeValidationResults(results) {
    const merged = {
        valid: true,
        errors: [],
        warnings: [],
    };

    results.forEach(result => {
        if (!result.valid) merged.valid = false;
        merged.errors.push(...(result.errors || []));
        merged.warnings.push(...(result.warnings || []));
    });

    return merged;
}

// =============================================================================
// Field Validation
// =============================================================================

/**
 * Validate a required field
 * @param {*} value - Value to validate
 * @param {string} fieldName - Field name for error message
 * @returns {ValidationResult} Validation result
 */
export function validateRequired(value, fieldName) {
    if (value === null || value === undefined || value === '') {
        return createValidationResult(false, [`${fieldName} is required`]);
    }
    if (typeof value === 'string' && value.trim() === '') {
        return createValidationResult(false, [`${fieldName} is required`]);
    }
    return createValidationResult(true);
}

/**
 * Validate string length
 * @param {string} value - Value to validate
 * @param {string} fieldName - Field name for error message
 * @param {number} [minLength=0] - Minimum length
 * @param {number} [maxLength=Infinity] - Maximum length
 * @returns {ValidationResult} Validation result
 */
export function validateLength(value, fieldName, minLength = 0, maxLength = Infinity) {
    const errors = [];

    if (typeof value !== 'string') {
        return createValidationResult(false, [`${fieldName} must be a string`]);
    }

    if (value.length < minLength) {
        errors.push(`${fieldName} must be at least ${minLength} characters`);
    }

    if (value.length > maxLength) {
        errors.push(`${fieldName} must be at most ${maxLength} characters`);
    }

    return createValidationResult(errors.length === 0, errors);
}

/**
 * Validate number range
 * @param {number} value - Value to validate
 * @param {string} fieldName - Field name for error message
 * @param {number} [min=-Infinity] - Minimum value
 * @param {number} [max=Infinity] - Maximum value
 * @returns {ValidationResult} Validation result
 */
export function validateRange(value, fieldName, min = -Infinity, max = Infinity) {
    const errors = [];

    if (!isValidNumber(value)) {
        return createValidationResult(false, [`${fieldName} must be a valid number`]);
    }

    if (value < min) {
        errors.push(`${fieldName} must be at least ${min}`);
    }

    if (value > max) {
        errors.push(`${fieldName} must be at most ${max}`);
    }

    return createValidationResult(errors.length === 0, errors);
}
