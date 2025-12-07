/**
 * Tool Groups API Module
 * Handles all tool group-related API operations
 */

import { apiRequestJson, apiRequest } from './client.js';

const BASE_URL = '/api/toolgroups';

// ============================================================================
// SELECTOR FORMAT HELPERS
// ============================================================================

/**
 * Convert UI selector format to API format
 *
 * UI format: { type: 'name', pattern: 'user*' }
 * API format: { source_pattern: '*', name_pattern: 'user*', path_pattern: null, ... }
 *
 * @param {Object} uiSelector - UI format selector
 * @returns {Object} API format selector
 */
export function uiSelectorToApiFormat(uiSelector) {
    const apiSelector = {
        source_pattern: '*',
        name_pattern: '*',
        path_pattern: null,
        required_tags: [],
        excluded_tags: [],
    };

    // If it's already in API format (has source_pattern), return as-is
    if (uiSelector.source_pattern !== undefined) {
        return {
            source_pattern: uiSelector.source_pattern || '*',
            name_pattern: uiSelector.name_pattern || '*',
            path_pattern: uiSelector.path_pattern || null,
            required_tags: uiSelector.required_tags || [],
            excluded_tags: uiSelector.excluded_tags || [],
            selector_id: uiSelector.selector_id || uiSelector.id || null,
        };
    }

    // Convert from UI format based on type
    const { type, pattern } = uiSelector;
    if (!pattern) return apiSelector;

    switch (type) {
        case 'name':
            apiSelector.name_pattern = pattern;
            break;
        case 'source':
            apiSelector.source_pattern = pattern;
            break;
        case 'path':
            apiSelector.path_pattern = pattern;
            break;
        case 'tag':
            // Tags are comma-separated
            apiSelector.required_tags = pattern
                .split(',')
                .map(t => t.trim())
                .filter(t => t);
            break;
        default:
            apiSelector.name_pattern = pattern;
    }

    return apiSelector;
}

/**
 * Convert API selector format to UI format for display
 *
 * API format: { source_pattern: '*', name_pattern: 'user*', path_pattern: null, ... }
 * UI format: { type: 'name', pattern: 'user*', id: '...' }
 *
 * @param {Object} apiSelector - API format selector
 * @returns {Object} UI format selector
 */
export function apiSelectorToUiFormat(apiSelector) {
    // Determine the primary type based on which pattern is non-default
    let type = 'name';
    let pattern = '';

    if (apiSelector.required_tags && apiSelector.required_tags.length > 0) {
        type = 'tag';
        pattern = apiSelector.required_tags.join(', ');
    } else if (apiSelector.path_pattern && apiSelector.path_pattern !== '*') {
        type = 'path';
        pattern = apiSelector.path_pattern;
    } else if (apiSelector.source_pattern && apiSelector.source_pattern !== '*') {
        type = 'source';
        pattern = apiSelector.source_pattern;
    } else if (apiSelector.name_pattern && apiSelector.name_pattern !== '*') {
        type = 'name';
        pattern = apiSelector.name_pattern;
    }

    return {
        type,
        pattern,
        id: apiSelector.id,
        // Keep original API data for reference
        _apiData: apiSelector,
    };
}

/**
 * Convert array of UI selectors to API format
 * @param {Array} uiSelectors
 * @returns {Array}
 */
export function uiSelectorsToApiFormat(uiSelectors) {
    return uiSelectors
        .filter(s => s.pattern && s.pattern.trim()) // Filter empty patterns
        .map(uiSelectorToApiFormat);
}

// ============================================================================
// GROUP CRUD OPERATIONS
// ============================================================================

/**
 * Get all tool groups
 * @param {Object} options
 * @param {boolean} [options.includeInactive=false]
 * @param {string} [options.nameFilter]
 * @returns {Promise<Array>}
 */
export async function getGroups({ includeInactive = false, nameFilter = null } = {}) {
    const params = new URLSearchParams();
    if (includeInactive) params.append('include_inactive', 'true');
    if (nameFilter) params.append('name_filter', nameFilter);

    const url = `${BASE_URL}/${params.toString() ? '?' + params.toString() : ''}`;
    return await apiRequestJson(url);
}

// Alias for backward compatibility
export { getGroups as fetchToolGroups };

/**
 * Get a single tool group by ID
 * @param {string} groupId
 * @returns {Promise<Object>}
 */
export async function getGroup(groupId) {
    return await apiRequestJson(`${BASE_URL}/${groupId}`);
}

// Alias for backward compatibility
export { getGroup as fetchToolGroup };

/**
 * Get resolved tools for a group
 * @param {string} groupId
 * @returns {Promise<Object>}
 */
export async function getGroupTools(groupId) {
    return await apiRequestJson(`${BASE_URL}/${groupId}/tools`);
}

// Alias for backward compatibility
export { getGroupTools as fetchGroupTools };

/**
 * Create a new tool group with optional initial selectors and tools
 * @param {Object} groupData
 * @param {string} groupData.name
 * @param {string} [groupData.description='']
 * @param {Array} [groupData.selectors=[]] - UI format selectors
 * @param {Array} [groupData.explicit_tool_ids=[]]
 * @param {Array} [groupData.excluded_tool_ids=[]]
 * @returns {Promise<Object>}
 */
export async function createToolGroup(groupData) {
    // Convert UI selectors to API format
    const apiData = {
        name: groupData.name,
        description: groupData.description || '',
        selectors: groupData.selectors ? uiSelectorsToApiFormat(groupData.selectors) : [],
        explicit_tool_ids: groupData.explicit_tool_ids || [],
        excluded_tool_ids: groupData.excluded_tool_ids || [],
    };

    return await apiRequestJson(BASE_URL + '/', {
        method: 'POST',
        body: JSON.stringify(apiData),
    });
}

// Alias for consistency with UI naming
export { createToolGroup as createGroup };

/**
 * Update a tool group's name and description
 * @param {string} groupId
 * @param {Object} updates
 * @param {string} [updates.name]
 * @param {string} [updates.description]
 * @returns {Promise<Object>}
 */
export async function updateToolGroup(groupId, updates) {
    return await apiRequestJson(`${BASE_URL}/${groupId}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
    });
}

/**
 * Delete a tool group
 * @param {string} groupId
 * @returns {Promise<void>}
 */
export async function deleteToolGroup(groupId) {
    const response = await apiRequest(`${BASE_URL}/${groupId}`, {
        method: 'DELETE',
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to delete tool group');
    }
}

// Alias for consistency with UI naming
export { deleteToolGroup as deleteGroup };

/**
 * Activate a tool group
 * @param {string} groupId
 * @returns {Promise<Object>}
 */
export async function activateToolGroup(groupId) {
    return await apiRequestJson(`${BASE_URL}/${groupId}/activate`, {
        method: 'POST',
    });
}

/**
 * Deactivate a tool group
 * @param {string} groupId
 * @param {string} [reason]
 * @returns {Promise<Object>}
 */
export async function deactivateToolGroup(groupId, reason = null) {
    return await apiRequestJson(`${BASE_URL}/${groupId}/deactivate`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
    });
}

// ============================================================================
// SYNC OPERATIONS (Diff-based updates)
// ============================================================================

/**
 * Sync selectors for a group (diff-based update)
 *
 * This performs a smart diff - only adding/removing selectors that changed.
 *
 * @param {string} groupId
 * @param {Array} selectors - UI format selectors
 * @returns {Promise<Object>}
 */
export async function syncSelectors(groupId, selectors) {
    const apiSelectors = uiSelectorsToApiFormat(selectors);

    return await apiRequestJson(`${BASE_URL}/${groupId}/selectors`, {
        method: 'PUT',
        body: JSON.stringify({ selectors: apiSelectors }),
    });
}

/**
 * Sync explicit and excluded tools for a group (diff-based update)
 *
 * @param {string} groupId
 * @param {Array} explicitToolIds - Tool IDs to explicitly include
 * @param {Array} excludedToolIds - Tool IDs to exclude
 * @returns {Promise<Object>}
 */
export async function syncTools(groupId, explicitToolIds, excludedToolIds) {
    return await apiRequestJson(`${BASE_URL}/${groupId}/tools`, {
        method: 'PUT',
        body: JSON.stringify({
            explicit_tool_ids: explicitToolIds || [],
            excluded_tool_ids: excludedToolIds || [],
        }),
    });
}

// ============================================================================
// SELECTOR MANAGEMENT (Individual operations)
// ============================================================================

/**
 * Add a selector to a tool group
 * @param {string} groupId
 * @param {Object} selectorData - UI or API format
 * @returns {Promise<Object>}
 */
export async function addSelector(groupId, selectorData) {
    const apiSelector = uiSelectorToApiFormat(selectorData);

    return await apiRequestJson(`${BASE_URL}/${groupId}/selectors`, {
        method: 'POST',
        body: JSON.stringify(apiSelector),
    });
}

/**
 * Remove a selector from a tool group
 * @param {string} groupId
 * @param {string} selectorId
 * @returns {Promise<void>}
 */
export async function removeSelector(groupId, selectorId) {
    const response = await apiRequest(`${BASE_URL}/${groupId}/selectors/${selectorId}`, {
        method: 'DELETE',
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to remove selector');
    }
}

// ============================================================================
// EXPLICIT TOOL MANAGEMENT
// ============================================================================

/**
 * Add an explicit tool to a group
 * @param {string} groupId
 * @param {string} toolId
 * @returns {Promise<Object>}
 */
export async function addExplicitTool(groupId, toolId) {
    return await apiRequestJson(`${BASE_URL}/${groupId}/tools`, {
        method: 'POST',
        body: JSON.stringify({ tool_id: toolId }),
    });
}

/**
 * Remove an explicit tool from a group
 * @param {string} groupId
 * @param {string} toolId
 * @returns {Promise<void>}
 */
export async function removeExplicitTool(groupId, toolId) {
    const response = await apiRequest(`${BASE_URL}/${groupId}/tools/${encodeURIComponent(toolId)}`, {
        method: 'DELETE',
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to remove explicit tool');
    }
}

// ============================================================================
// EXCLUSION MANAGEMENT
// ============================================================================

/**
 * Exclude a tool from a group
 * @param {string} groupId
 * @param {string} toolId
 * @param {string} [reason]
 * @returns {Promise<Object>}
 */
export async function excludeTool(groupId, toolId, reason = null) {
    return await apiRequestJson(`${BASE_URL}/${groupId}/exclusions`, {
        method: 'POST',
        body: JSON.stringify({ tool_id: toolId, reason }),
    });
}

/**
 * Include a tool in a group (remove from exclusions)
 * @param {string} groupId
 * @param {string} toolId
 * @returns {Promise<void>}
 */
export async function includeTool(groupId, toolId) {
    const response = await apiRequest(`${BASE_URL}/${groupId}/exclusions/${encodeURIComponent(toolId)}`, {
        method: 'DELETE',
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to include tool');
    }
}
