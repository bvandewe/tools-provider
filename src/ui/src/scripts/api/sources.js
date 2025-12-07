/**
 * Sources API Module
 * Handles all source-related API operations
 */

import { apiRequestJson, apiRequest } from './client.js';

const BASE_URL = '/api/sources';

/**
 * Get all sources
 * @param {Object} options
 * @param {boolean} [options.includeDisabled=false]
 * @param {string} [options.healthStatus]
 * @param {string} [options.sourceType]
 * @returns {Promise<Array>}
 */
export async function getSources({ includeDisabled = false, healthStatus = null, sourceType = null } = {}) {
    const params = new URLSearchParams();
    if (includeDisabled) params.append('include_disabled', 'true');
    if (healthStatus) params.append('health_status', healthStatus);
    if (sourceType) params.append('source_type', sourceType);

    const url = `${BASE_URL}/${params.toString() ? '?' + params.toString() : ''}`;
    return await apiRequestJson(url);
}

// Alias for backward compatibility
export { getSources as fetchSources };

/**
 * Get a single source by ID
 * @param {string} sourceId
 * @returns {Promise<Object>}
 */
export async function getSource(sourceId) {
    return await apiRequestJson(`${BASE_URL}/${sourceId}`);
}

// Alias for backward compatibility
export { getSource as fetchSource };

/**
 * Register a new source
 * @param {Object} sourceData
 * @param {string} sourceData.name
 * @param {string} sourceData.url
 * @param {string} [sourceData.source_type='openapi']
 * @param {string} [sourceData.auth_type]
 * @param {string} [sourceData.bearer_token]
 * @param {boolean} [sourceData.validate_url=true]
 * @returns {Promise<Object>}
 */
export async function registerSource(sourceData) {
    return await apiRequestJson(BASE_URL + '/', {
        method: 'POST',
        body: JSON.stringify(sourceData),
    });
}

/**
 * Refresh source inventory
 * @param {string} sourceId
 * @param {boolean} [force=false]
 * @returns {Promise<Object>}
 */
export async function refreshInventory(sourceId, force = false) {
    return await apiRequestJson(`${BASE_URL}/${sourceId}/refresh`, {
        method: 'POST',
        body: JSON.stringify({ force }),
    });
}

// Alias for backward compatibility
export { refreshInventory as refreshSourceInventory };

/**
 * Delete a source
 * @param {string} sourceId
 * @returns {Promise<void>}
 */
export async function deleteSource(sourceId) {
    const response = await apiRequest(`${BASE_URL}/${sourceId}`, {
        method: 'DELETE',
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to delete source');
    }
}
