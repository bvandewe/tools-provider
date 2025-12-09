/**
 * Tool Utility Functions
 *
 * Provides helper functions for tool name formatting and manipulation.
 */

/**
 * Convert an operation_id/tool name to a human-friendly format.
 *
 * Examples:
 * - "create_menu_item_api_menu_post" -> "Create Menu Item"
 * - "get_user_by_id_api_users__user_id__get" -> "Get User By Id"
 * - "listAllOrders" -> "List All Orders"
 * - "POST_createNewItem" -> "Create New Item"
 *
 * @param {string} operationId - The operation ID or tool name
 * @returns {string} Human-friendly name
 */
export function formatToolName(operationId) {
    if (!operationId) return 'Unknown Tool';

    // If it's a full tool ID (source_id:operation_id), extract operation_id
    if (operationId.includes(':')) {
        operationId = operationId.split(':').pop();
    }

    // Remove common suffixes like _api_*, _get, _post, _put, _delete, _patch
    let name = operationId
        .replace(/_api_[a-z_]+_(get|post|put|delete|patch)$/i, '')
        .replace(/_(get|post|put|delete|patch)$/i, '')
        .replace(/^(get|post|put|delete|patch)_/i, '');

    // Handle camelCase
    name = name.replace(/([a-z])([A-Z])/g, '$1_$2');

    // Split by underscores, dashes, or double underscores
    const words = name
        .split(/[_\-]+/)
        .filter(word => word.length > 0)
        .filter(word => !['api', 'v1', 'v2'].includes(word.toLowerCase()));

    // Capitalize each word
    const formattedWords = words.map(word => {
        // Handle common abbreviations
        const upperWords = ['id', 'url', 'api', 'uuid', 'mcp'];
        if (upperWords.includes(word.toLowerCase())) {
            return word.toUpperCase();
        }
        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    });

    return formattedWords.join(' ') || 'Unknown Tool';
}

/**
 * Get a short display name from a tool ID.
 * Extracts the operation ID part and formats it nicely.
 *
 * @param {string} toolId - Full tool ID (source_id:operation_id)
 * @returns {string} Formatted display name
 */
export function getToolDisplayName(toolId) {
    if (!toolId) return 'Unknown Tool';

    // Extract operation_id from full tool ID
    const operationId = toolId.includes(':') ? toolId.split(':').pop() : toolId;
    return formatToolName(operationId);
}

/**
 * Get method badge class based on HTTP method.
 *
 * @param {string} method - HTTP method (GET, POST, etc.)
 * @returns {string} Bootstrap badge class
 */
export function getMethodClass(method) {
    const classes = {
        GET: 'bg-success',
        POST: 'bg-primary',
        PUT: 'bg-warning text-dark',
        PATCH: 'bg-info text-dark',
        DELETE: 'bg-danger',
    };
    return classes[(method || '').toUpperCase()] || 'bg-secondary';
}

/**
 * Infer HTTP method from tool name/operation_id.
 *
 * @param {string} name - Tool name or operation ID
 * @returns {string} Inferred HTTP method or 'GET' as default
 */
export function inferMethodFromName(name) {
    if (!name) return 'GET';

    const lowerName = name.toLowerCase();

    if (lowerName.includes('_post') || lowerName.startsWith('create') || lowerName.startsWith('add')) {
        return 'POST';
    }
    if (lowerName.includes('_put') || lowerName.startsWith('update') || lowerName.startsWith('replace')) {
        return 'PUT';
    }
    if (lowerName.includes('_patch') || lowerName.startsWith('patch') || lowerName.startsWith('modify')) {
        return 'PATCH';
    }
    if (lowerName.includes('_delete') || lowerName.startsWith('delete') || lowerName.startsWith('remove')) {
        return 'DELETE';
    }

    return 'GET';
}
