/**
 * Graph Topology Widget Configuration
 *
 * Configuration UI for the 'graph_topology' widget type.
 *
 * Python Schema Reference (GraphTopologyConfig):
 * - mode: str (required) - "build" | "view"
 * - node_types: list[GraphNodeType] (required, alias: nodeTypes)
 * - edge_types: list[GraphEdgeType] (required, alias: edgeTypes)
 * - regions: list[GraphRegion] | None
 * - constraints: GraphConstraints | None
 * - initial_graph: Any | None (alias: initialGraph)
 * - toolbar: GraphToolbar | None
 * - validation: dict | None
 *
 * GraphNodeType: typeId, label, icon?, color?, maxInstances?, properties?
 * GraphEdgeType: typeId, label, style, color?, bidirectional?
 * GraphConstraints: minNodes, maxNodes, minEdges, maxEdges, allowCycles, allowSelfLoops, requireConnected
 * GraphToolbar: showNodePalette, showEdgeTools, showRegionTools, showLayoutTools
 *
 * @module admin/widget-config/graph-topology-config
 */

import { WidgetConfigBase } from './config-base.js';

/**
 * Mode options
 */
const MODE_OPTIONS = [
    { value: 'build', label: 'Build (user creates graph)' },
    { value: 'view', label: 'View (read-only display)' },
];

/**
 * Edge style options
 */
const EDGE_STYLE_OPTIONS = [
    { value: 'arrow', label: 'Arrow' },
    { value: 'line', label: 'Line' },
    { value: 'dashed-arrow', label: 'Dashed Arrow' },
    { value: 'double-arrow', label: 'Double Arrow' },
];

export class GraphTopologyConfig extends WidgetConfigBase {
    /**
     * Render the graph topology widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        const constraints = config.constraints || {};
        const toolbar = config.toolbar || {};

        // Convert node types to text format: typeId|label|color|maxInstances
        const nodeTypes = config.node_types ?? config.nodeTypes ?? [];
        const nodeTypesText = nodeTypes.map(nt => [nt.type_id ?? nt.typeId, nt.label, nt.color || '', nt.max_instances ?? nt.maxInstances ?? ''].join('|').replace(/\|+$/, '')).join('\n');

        // Convert edge types to text format: typeId|label|style|color|bidirectional
        const edgeTypes = config.edge_types ?? config.edgeTypes ?? [];
        const edgeTypesText = edgeTypes
            .map(et => {
                const parts = [et.type_id ?? et.typeId, et.label, et.style || 'arrow'];
                if (et.color) parts.push(et.color);
                if (et.bidirectional) parts.push('bidirectional');
                return parts.join('|');
            })
            .join('\n');

        this.container.innerHTML = `
            <div class="widget-config widget-config-graph-topology">
                <div class="row g-2">
                    <div class="col-md-4">
                        ${this.createFormGroup('Mode', this.createSelect('config-mode', MODE_OPTIONS, config.mode || 'build'), 'Build mode allows user to create/edit graph.')}
                    </div>
                    <div class="col-md-8">
                        <div class="row g-2">
                            <div class="col-6">
                                ${this.createSwitch(
                                    'config-show-palette',
                                    `${this.uid}-show-palette`,
                                    'Node Palette',
                                    'Show node type palette.',
                                    toolbar.show_node_palette ?? toolbar.showNodePalette ?? true
                                )}
                            </div>
                            <div class="col-6">
                                ${this.createSwitch(
                                    'config-show-edge-tools',
                                    `${this.uid}-show-edge-tools`,
                                    'Edge Tools',
                                    'Show edge creation tools.',
                                    toolbar.show_edge_tools ?? toolbar.showEdgeTools ?? true
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-6">
                        ${this.createFormGroup(
                            'Node Types',
                            this.createTextarea('config-node-types', nodeTypesText, 'server|Server|#3498db|5\ndatabase|Database|#9b59b6\nclient|Client|#2ecc71', 5),
                            'One per line: typeId|label[|color][|maxInstances]',
                            true
                        )}
                    </div>
                    <div class="col-md-6">
                        ${this.createFormGroup(
                            'Edge Types',
                            this.createTextarea('config-edge-types', edgeTypesText, 'connects|Connects To|arrow|#333\nreads|Reads From|dashed-arrow', 5),
                            'One per line: typeId|label|style[|color][|bidirectional]',
                            true
                        )}
                    </div>
                </div>

                ${this.createCollapsibleSection(
                    `${this.uid}-constraints`,
                    'Constraints',
                    `
                    <div class="row g-2">
                        <div class="col-md-3">
                            ${this.createFormGroup('Min Nodes', this.createNumberInput('config-min-nodes', constraints.min_nodes ?? constraints.minNodes ?? '', 0, 100, 1), 'Minimum number of nodes.')}
                        </div>
                        <div class="col-md-3">
                            ${this.createFormGroup(
                                'Max Nodes',
                                this.createNumberInput('config-max-nodes', constraints.max_nodes ?? constraints.maxNodes ?? '', 1, 1000, 1),
                                'Maximum number of nodes.'
                            )}
                        </div>
                        <div class="col-md-3">
                            ${this.createFormGroup('Min Edges', this.createNumberInput('config-min-edges', constraints.min_edges ?? constraints.minEdges ?? '', 0, 100, 1), 'Minimum number of edges.')}
                        </div>
                        <div class="col-md-3">
                            ${this.createFormGroup(
                                'Max Edges',
                                this.createNumberInput('config-max-edges', constraints.max_edges ?? constraints.maxEdges ?? '', 0, 1000, 1),
                                'Maximum number of edges.'
                            )}
                        </div>
                    </div>
                    <div class="row g-2 mt-2">
                        <div class="col-md-4">
                            ${this.createSwitch(
                                'config-allow-cycles',
                                `${this.uid}-allow-cycles`,
                                'Allow Cycles',
                                'Allow circular paths in graph.',
                                constraints.allow_cycles ?? constraints.allowCycles ?? true
                            )}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch(
                                'config-allow-self-loops',
                                `${this.uid}-allow-self-loops`,
                                'Allow Self-Loops',
                                'Allow edges from node to itself.',
                                constraints.allow_self_loops ?? constraints.allowSelfLoops ?? false
                            )}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch(
                                'config-require-connected',
                                `${this.uid}-require-connected`,
                                'Require Connected',
                                'All nodes must be connected.',
                                constraints.require_connected ?? constraints.requireConnected ?? false
                            )}
                        </div>
                    </div>
                `
                )}

                ${this.createCollapsibleSection(
                    `${this.uid}-toolbar`,
                    'Toolbar Options',
                    `
                    <div class="row g-2">
                        <div class="col-md-6">
                            ${this.createSwitch(
                                'config-show-region-tools',
                                `${this.uid}-show-region-tools`,
                                'Region Tools',
                                'Show tools for creating regions.',
                                toolbar.show_region_tools ?? toolbar.showRegionTools ?? false
                            )}
                        </div>
                        <div class="col-md-6">
                            ${this.createSwitch(
                                'config-show-layout-tools',
                                `${this.uid}-show-layout-tools`,
                                'Layout Tools',
                                'Show auto-layout options.',
                                toolbar.show_layout_tools ?? toolbar.showLayoutTools ?? true
                            )}
                        </div>
                    </div>
                `
                )}
            </div>
        `;

        this.initTooltips();
    }

    /**
     * Parse node types from textarea
     * @returns {Array} Parsed node types
     */
    parseNodeTypes() {
        const text = this.getInputValue('config-node-types', '');
        if (!text.trim()) return [];

        return text
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map(line => {
                const parts = line.split('|').map(p => p.trim());
                const nodeType = {
                    type_id: parts[0],
                    label: parts[1] || parts[0],
                };
                if (parts[2]) nodeType.color = parts[2];
                if (parts[3]) {
                    const maxInst = parseInt(parts[3], 10);
                    if (!isNaN(maxInst)) nodeType.max_instances = maxInst;
                }
                return nodeType;
            });
    }

    /**
     * Parse edge types from textarea
     * @returns {Array} Parsed edge types
     */
    parseEdgeTypes() {
        const text = this.getInputValue('config-edge-types', '');
        if (!text.trim()) return [];

        return text
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map(line => {
                const parts = line.split('|').map(p => p.trim());
                const edgeType = {
                    type_id: parts[0],
                    label: parts[1] || parts[0],
                    style: parts[2] || 'arrow',
                };
                // Check remaining parts for color and bidirectional
                for (let i = 3; i < parts.length; i++) {
                    if (parts[i] === 'bidirectional') {
                        edgeType.bidirectional = true;
                    } else if (parts[i].startsWith('#')) {
                        edgeType.color = parts[i];
                    }
                }
                return edgeType;
            });
    }

    /**
     * Get configuration values matching Python schema
     * @returns {Object} Widget configuration
     */
    getValue() {
        const config = {};

        config.mode = this.getInputValue('config-mode', 'build');
        config.node_types = this.parseNodeTypes();
        config.edge_types = this.parseEdgeTypes();

        // Build constraints object
        const constraints = {};

        const minNodes = this.getInputValue('config-min-nodes');
        if (minNodes !== '') constraints.min_nodes = parseInt(minNodes, 10);

        const maxNodes = this.getInputValue('config-max-nodes');
        if (maxNodes !== '') constraints.max_nodes = parseInt(maxNodes, 10);

        const minEdges = this.getInputValue('config-min-edges');
        if (minEdges !== '') constraints.min_edges = parseInt(minEdges, 10);

        const maxEdges = this.getInputValue('config-max-edges');
        if (maxEdges !== '') constraints.max_edges = parseInt(maxEdges, 10);

        const allowCycles = this.getChecked('config-allow-cycles');
        if (!allowCycles) constraints.allow_cycles = false;

        const allowSelfLoops = this.getChecked('config-allow-self-loops');
        if (allowSelfLoops) constraints.allow_self_loops = true;

        const requireConnected = this.getChecked('config-require-connected');
        if (requireConnected) constraints.require_connected = true;

        if (Object.keys(constraints).length > 0) {
            config.constraints = constraints;
        }

        // Build toolbar object
        const toolbar = {};

        const showPalette = this.getChecked('config-show-palette');
        if (!showPalette) toolbar.show_node_palette = false;

        const showEdgeTools = this.getChecked('config-show-edge-tools');
        if (!showEdgeTools) toolbar.show_edge_tools = false;

        const showRegionTools = this.getChecked('config-show-region-tools');
        if (showRegionTools) toolbar.show_region_tools = true;

        const showLayoutTools = this.getChecked('config-show-layout-tools');
        if (!showLayoutTools) toolbar.show_layout_tools = false;

        if (Object.keys(toolbar).length > 0) {
            config.toolbar = toolbar;
        }

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const nodeTypes = this.parseNodeTypes();
        if (nodeTypes.length < 1) {
            errors.push('At least 1 node type is required');
        }

        const edgeTypes = this.parseEdgeTypes();
        if (edgeTypes.length < 1) {
            errors.push('At least 1 edge type is required');
        }

        // Check for duplicate node type IDs
        const nodeIds = nodeTypes.map(n => n.type_id);
        const uniqueNodeIds = new Set(nodeIds);
        if (nodeIds.length !== uniqueNodeIds.size) {
            errors.push('Node type IDs must be unique');
        }

        // Check for duplicate edge type IDs
        const edgeIds = edgeTypes.map(e => e.type_id);
        const uniqueEdgeIds = new Set(edgeIds);
        if (edgeIds.length !== uniqueEdgeIds.size) {
            errors.push('Edge type IDs must be unique');
        }

        // Validate edge styles
        const validStyles = ['arrow', 'line', 'dashed-arrow', 'double-arrow'];
        for (const et of edgeTypes) {
            if (!validStyles.includes(et.style)) {
                errors.push(`Invalid edge style "${et.style}" for "${et.type_id}"`);
            }
        }

        return { valid: errors.length === 0, errors };
    }
}
