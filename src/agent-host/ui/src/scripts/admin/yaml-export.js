/**
 * YAML Import/Export Utility
 *
 * Provides functionality to download and upload AgentDefinitions and ConversationTemplates
 * as YAML files from/to the backend API endpoints.
 *
 * The backend generates YAML in the exact format expected by the database seeder,
 * ensuring exported files can be re-imported without modification.
 */

const API_BASE = '/api';

/**
 * Download a file from a blob response
 * @param {Blob} blob - The blob content
 * @param {string} filename - The filename to use
 */
function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';

    document.body.appendChild(link);
    link.click();

    // Cleanup
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

/**
 * Export and download an AgentDefinition as YAML from the backend
 * @param {string} definitionId - The definition ID to export
 * @returns {Promise<void>}
 * @throws {Error} If the export fails
 */
export async function downloadDefinitionAsYaml(definitionId) {
    const response = await fetch(`${API_BASE}/admin/definitions/${definitionId}/export`, {
        credentials: 'include',
        headers: {
            Accept: 'application/x-yaml',
        },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `Export failed: ${response.status}`);
    }

    const blob = await response.blob();
    downloadBlob(blob, `${definitionId}.yaml`);
}

/**
 * Export and download a ConversationTemplate as YAML from the backend
 * @param {string} templateId - The template ID to export
 * @returns {Promise<void>}
 * @throws {Error} If the export fails
 */
export async function downloadTemplateAsYaml(templateId) {
    const response = await fetch(`${API_BASE}/admin/templates/${templateId}/export`, {
        credentials: 'include',
        headers: {
            Accept: 'application/x-yaml',
        },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `Export failed: ${response.status}`);
    }

    const blob = await response.blob();
    downloadBlob(blob, `${templateId}.yaml`);
}

/**
 * Import an AgentDefinition from a YAML file
 * @param {File} file - The YAML file to import
 * @returns {Promise<Object>} - The created definition
 * @throws {Error} If the import fails
 */
export async function importDefinitionFromYaml(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/admin/definitions/import`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `Import failed: ${response.status}`);
    }

    return response.json();
}

/**
 * Import a ConversationTemplate from a YAML file
 * @param {File} file - The YAML file to import
 * @returns {Promise<Object>} - The created template
 * @throws {Error} If the import fails
 */
export async function importTemplateFromYaml(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/admin/templates/import`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `Import failed: ${response.status}`);
    }

    return response.json();
}
