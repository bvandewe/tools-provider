/**
 * Access Policies API Module
 * Handles all access policy-related API operations
 */

import { apiRequestJson, apiRequest } from './client.js';

const BASE_URL = '/api/policies';

/**
 * Get all access policies
 * @param {Object} options
 * @param {boolean} [options.includeInactive=false]
 * @param {string} [options.groupId]
 * @returns {Promise<Array>}
 */
export async function getPolicies({ includeInactive = false, groupId = null } = {}) {
    const params = new URLSearchParams();
    if (includeInactive) params.append('include_inactive', 'true');
    if (groupId) params.append('group_id', groupId);

    const url = `${BASE_URL}/${params.toString() ? '?' + params.toString() : ''}`;
    return await apiRequestJson(url);
}

// Alias for backward compatibility
export { getPolicies as fetchPolicies };

/**
 * Get a single access policy by ID
 * @param {string} policyId
 * @returns {Promise<Object>}
 */
export async function getPolicy(policyId) {
    return await apiRequestJson(`${BASE_URL}/${policyId}`);
}

// Alias for backward compatibility
export { getPolicy as fetchPolicy };

/**
 * Define (create) a new access policy
 * @param {Object} policyData
 * @param {string} policyData.name
 * @param {Array<Object>} policyData.claim_matchers
 * @param {Array<string>} policyData.allowed_group_ids
 * @param {string} [policyData.description]
 * @param {number} [policyData.priority=0]
 * @returns {Promise<Object>}
 */
export async function createPolicy(policyData) {
    return await apiRequestJson(BASE_URL + '/', {
        method: 'POST',
        body: JSON.stringify(policyData),
    });
}

// Alias for backward compatibility
export { createPolicy as definePolicy };

/**
 * Update an access policy
 * @param {string} policyId
 * @param {Object} updates
 * @param {string} [updates.name]
 * @param {string} [updates.description]
 * @param {Array<Object>} [updates.claim_matchers]
 * @param {Array<string>} [updates.allowed_group_ids]
 * @param {number} [updates.priority]
 * @returns {Promise<Object>}
 */
export async function updatePolicy(policyId, updates) {
    return await apiRequestJson(`${BASE_URL}/${policyId}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
    });
}

/**
 * Delete an access policy
 * @param {string} policyId
 * @returns {Promise<void>}
 */
export async function deletePolicy(policyId) {
    const response = await apiRequest(`${BASE_URL}/${policyId}`, {
        method: 'DELETE',
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to delete policy');
    }
}

/**
 * Activate an access policy
 * @param {string} policyId
 * @returns {Promise<Object>}
 */
export async function activatePolicy(policyId) {
    return await apiRequestJson(`${BASE_URL}/${policyId}/activate`, {
        method: 'POST',
    });
}

// Alias for consistency with UI naming
export { activatePolicy as enablePolicy };

/**
 * Deactivate an access policy
 * @param {string} policyId
 * @param {string} [reason]
 * @returns {Promise<Object>}
 */
export async function deactivatePolicy(policyId, reason = null) {
    return await apiRequestJson(`${BASE_URL}/${policyId}/deactivate`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
    });
}

// Alias for consistency with UI naming
export { deactivatePolicy as disablePolicy };

// ============================================================================
// CLAIM MATCHER OPERATORS (for UI reference)
// ============================================================================

/**
 * Available claim matcher operators
 */
export const CLAIM_OPERATORS = [
    { value: 'equals', label: 'Equals', description: 'Exact match' },
    { value: 'not_equals', label: 'Not Equals', description: 'Does not match' },
    { value: 'contains', label: 'Contains', description: 'Contains substring or array element' },
    { value: 'not_contains', label: 'Not Contains', description: 'Does not contain' },
    { value: 'matches', label: 'Matches (Regex)', description: 'Regular expression match' },
    { value: 'in', label: 'In', description: 'Value is in comma-separated list' },
    { value: 'not_in', label: 'Not In', description: 'Value is not in comma-separated list' },
    { value: 'exists', label: 'Exists', description: 'Claim exists (any value)' },
];

/**
 * Common JWT claim paths for suggestions
 */
export const COMMON_CLAIM_PATHS = [
    { path: 'realm_access.roles', description: 'Keycloak realm roles' },
    { path: 'resource_access.{client}.roles', description: 'Keycloak client roles' },
    { path: 'groups', description: 'User groups' },
    { path: 'sub', description: 'User ID (subject)' },
    { path: 'email', description: 'User email' },
    { path: 'preferred_username', description: 'Username' },
    { path: 'department', description: 'Department (custom claim)' },
    { path: 'tenant_id', description: 'Tenant ID (multi-tenant)' },
];
