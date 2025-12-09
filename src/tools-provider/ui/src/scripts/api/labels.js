/**
 * Labels API Module
 * Handles all label-related API operations
 */

import { apiRequestJson, apiRequest } from './client.js';

const BASE_URL = '/api/labels';

/**
 * Get all labels
 * @param {Object} options
 * @param {boolean} [options.includeDeleted=false]
 * @param {string} [options.nameFilter]
 * @returns {Promise<Array>}
 */
export async function getLabels({ includeDeleted = false, nameFilter = null } = {}) {
    const params = new URLSearchParams();
    if (includeDeleted) params.append('include_deleted', 'true');
    if (nameFilter) params.append('name_filter', nameFilter);

    const url = `${BASE_URL}/${params.toString() ? '?' + params.toString() : ''}`;
    return await apiRequestJson(url);
}

/**
 * Get label summaries (lightweight for dropdowns)
 * @returns {Promise<Array>}
 */
export async function getLabelSummaries() {
    return await apiRequestJson(`${BASE_URL}/summaries`);
}

/**
 * Get a single label by ID
 * @param {string} labelId
 * @returns {Promise<Object>}
 */
export async function getLabel(labelId) {
    return await apiRequestJson(`${BASE_URL}/${labelId}`);
}

/**
 * Create a new label
 * @param {Object} labelData
 * @param {string} labelData.name
 * @param {string} [labelData.description='']
 * @param {string} [labelData.color='#6c757d']
 * @returns {Promise<Object>}
 */
export async function createLabel(labelData) {
    return await apiRequestJson(BASE_URL + '/', {
        method: 'POST',
        body: JSON.stringify(labelData),
    });
}

/**
 * Update a label
 * @param {string} labelId
 * @param {Object} updates
 * @param {string} [updates.name]
 * @param {string} [updates.description]
 * @param {string} [updates.color]
 * @returns {Promise<Object>}
 */
export async function updateLabel(labelId, updates) {
    return await apiRequestJson(`${BASE_URL}/${labelId}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
    });
}

/**
 * Delete a label
 * @param {string} labelId
 * @returns {Promise<void>}
 */
export async function deleteLabel(labelId) {
    const response = await apiRequest(`${BASE_URL}/${labelId}`, {
        method: 'DELETE',
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to delete label');
    }
}
