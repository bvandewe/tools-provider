/**
 * Tools API Module
 * Handles all tool-related API operations
 */

import { apiRequestJson, apiRequest } from './client.js';

const BASE_URL = '/api/tools';

/**
 * Get all tools with optional filtering
 * @param {Object} options
 * @param {string} [options.sourceId]
 * @param {boolean} [options.includeDisabled=false]
 * @param {boolean} [options.includeDeprecated=false]
 * @returns {Promise<Array>}
 */
export async function getTools({ sourceId = null, includeDisabled = false, includeDeprecated = false } = {}) {
    const params = new URLSearchParams();
    if (sourceId) params.append('source_id', sourceId);
    if (includeDisabled) params.append('include_disabled', 'true');
    if (includeDeprecated) params.append('include_deprecated', 'true');

    const url = `${BASE_URL}/${params.toString() ? '?' + params.toString() : ''}`;
    return await apiRequestJson(url);
}

// Alias for backward compatibility
export { getTools as fetchTools };

/**
 * Get tool summaries (lightweight)
 * @param {Object} options
 * @param {string} [options.sourceId]
 * @param {boolean} [options.includeDisabled=false]
 * @returns {Promise<Array>}
 */
export async function getToolSummaries({ sourceId = null, includeDisabled = false } = {}) {
    const params = new URLSearchParams();
    if (sourceId) params.append('source_id', sourceId);
    if (includeDisabled) params.append('include_disabled', 'true');

    const url = `${BASE_URL}/summaries${params.toString() ? '?' + params.toString() : ''}`;
    return await apiRequestJson(url);
}

// Alias for backward compatibility
export { getToolSummaries as fetchToolSummaries };

/**
 * Search tools
 * @param {string} query
 * @param {Object} options
 * @param {string} [options.sourceId]
 * @param {string} [options.tags] - Comma-separated tags
 * @param {boolean} [options.includeDisabled=false]
 * @returns {Promise<Array>}
 */
export async function searchTools(query, { sourceId = null, tags = null, includeDisabled = false } = {}) {
    const params = new URLSearchParams({ q: query });
    if (sourceId) params.append('source_id', sourceId);
    if (tags) params.append('tags', tags);
    if (includeDisabled) params.append('include_disabled', 'true');

    return await apiRequestJson(`${BASE_URL}/search?${params.toString()}`);
}

/**
 * Get a single tool by ID
 * @param {string} toolId
 * @returns {Promise<Object>}
 */
export async function getTool(toolId) {
    return await apiRequestJson(`${BASE_URL}/${encodeURIComponent(toolId)}`);
}

// Alias for backward compatibility
export { getTool as fetchTool };

/**
 * Enable a tool
 * @param {string} toolId
 * @returns {Promise<Object>}
 */
export async function enableTool(toolId) {
    return await apiRequestJson(`${BASE_URL}/${encodeURIComponent(toolId)}/enable`, {
        method: 'POST',
    });
}

/**
 * Disable a tool
 * @param {string} toolId
 * @param {string} [reason]
 * @returns {Promise<Object>}
 */
export async function disableTool(toolId, reason = null) {
    return await apiRequestJson(`${BASE_URL}/${encodeURIComponent(toolId)}/disable`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
    });
}

/**
 * Delete a tool
 * @param {string} toolId
 * @returns {Promise<void>}
 */
export async function deleteTool(toolId) {
    const response = await apiRequest(`${BASE_URL}/${encodeURIComponent(toolId)}`, {
        method: 'DELETE',
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to delete tool');
    }
}

/**
 * Cleanup orphaned tools
 * @param {boolean} [dryRun=true]
 * @returns {Promise<Object>}
 */
export async function cleanupOrphanedTools(dryRun = true) {
    const params = new URLSearchParams({ dry_run: dryRun.toString() });
    return await apiRequestJson(`${BASE_URL}/orphaned/cleanup?${params.toString()}`, {
        method: 'DELETE',
    });
}

/**
 * Add a label to a tool
 * @param {string} toolId
 * @param {string} labelId
 * @returns {Promise<Object>}
 */
export async function addLabelToTool(toolId, labelId) {
    return await apiRequestJson(`${BASE_URL}/${encodeURIComponent(toolId)}/labels/${encodeURIComponent(labelId)}`, {
        method: 'POST',
    });
}

/**
 * Remove a label from a tool
 * @param {string} toolId
 * @param {string} labelId
 * @returns {Promise<void>}
 */
export async function removeLabelFromTool(toolId, labelId) {
    const response = await apiRequest(`${BASE_URL}/${encodeURIComponent(toolId)}/labels/${encodeURIComponent(labelId)}`, {
        method: 'DELETE',
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to remove label from tool');
    }
}
