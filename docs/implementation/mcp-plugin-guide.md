# MCP Plugin Integration Guide

**Status:** Implemented
**Updated:** December 2025

This guide covers how to register, configure, and use MCP (Model Context Protocol) plugins as tool sources in the Tools Provider.

---

## Overview

MCP plugins are first-class source types alongside OpenAPI and Workflow sources. They enable integration with any MCP-compatible tool server, such as the `cml-mcp` plugin for Cisco Modeling Labs.

### Key Concepts

| Concept | Description |
|---------|-------------|
| **MCP Source** | An `UpstreamSource` with `source_type: "mcp"` |
| **MCP Transport** | Communication protocol (stdio, sse, or http) |
| **MCP Tools** | Tools exposed by the MCP server via `tools/list` |
| **Lifecycle Mode** | How long the MCP server process runs |

---

## Registering an MCP Source

### Via REST API

```http
POST /api/sources
Authorization: Bearer <user_jwt>
Content-Type: application/json

{
  "name": "cml-mcp",
  "url": "file:///app/plugins/cml-mcp",
  "source_type": "mcp",
  "mcp_plugin_dir": "/app/plugins/cml-mcp",
  "mcp_manifest_path": "/app/plugins/cml-mcp/server.json",
  "mcp_transport_type": "stdio",
  "mcp_lifecycle_mode": "transient",
  "mcp_runtime_hint": "uvx",
  "mcp_command": "uvx cml-mcp-server",
  "mcp_env_vars": {
    "CML_URL": "${secrets:cml-url}",
    "CML_TOKEN": "${secrets:cml-token}"
  }
}
```

### Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "cml-mcp",
  "url": "file:///app/plugins/cml-mcp",
  "source_type": "mcp",
  "is_enabled": true,
  "health_status": "healthy",
  "inventory_count": 15
}
```

---

## MCP Configuration Options

### Transport Types

| Type | Description | Use Case |
|------|-------------|----------|
| `stdio` | Standard input/output | Local plugins, Python scripts |
| `sse` | Server-Sent Events | Remote servers, long-running |
| `http` | HTTP + SSE (Streamable) | Web-based MCP servers |

### Lifecycle Modes

| Mode | Description | Performance |
|------|-------------|-------------|
| `transient` | New process per call | Slower, isolated |
| `singleton` | Persistent process | Faster, shared state |

---

## Environment Variables

MCP plugins often require environment variables for configuration (API keys, URLs, etc.).

### Formats

| Format | Description | Example |
|--------|-------------|---------|
| `${secrets:name}` | From secret store | `${secrets:cml-token}` |
| `${env:NAME}` | From system environment | `${env:HOME}` |
| Plain value | Static value | `https://api.example.com` |

### Example Configuration

```json
{
  "mcp_env_vars": {
    "CML_URL": "${secrets:cml-url}",
    "CML_TOKEN": "${secrets:cml-token}",
    "LOG_LEVEL": "INFO"
  }
}
```

---

## Tool Discovery

After registration, the Tools Provider automatically:

1. Parses the MCP manifest (`server.json`)
2. Connects to the MCP server
3. Calls `tools/list` to discover available tools
4. Converts MCP tools to `SourceTool` entities

### Tool Schema Mapping

| MCP Field | SourceTool Field |
|-----------|------------------|
| `name` | `name` |
| `description` | `description` |
| `inputSchema` | `input_schema` |
| N/A | `execution_mode: MCP_CALL` |

---

## Tool Execution

Tools from MCP sources are executed via the MCP protocol:

```http
POST /api/tools/{tool_id}/execute
Authorization: Bearer <user_jwt>
Content-Type: application/json

{
  "arguments": {
    "lab_id": "lab1",
    "show_nodes": true
  }
}
```

### Execution Flow

1. Resolve environment variables from secret store
2. Get or create MCP transport (based on lifecycle mode)
3. Call `tools/call` with tool name and arguments
4. Return result content to caller

---

## MCP Manifest Format

The `server.json` manifest describes the MCP plugin:

```json
{
  "name": "cml-mcp",
  "title": "Cisco Modeling Labs MCP Server",
  "description": "MCP tools for CML network simulation",
  "version": "1.0.0",
  "packages": [
    {
      "registryType": "pypi",
      "identifier": "cml-mcp-server",
      "version": "1.0.0",
      "runtimeHint": "uvx",
      "transport": {
        "type": "stdio"
      },
      "environmentVariables": [
        {
          "name": "CML_URL",
          "description": "CML server URL",
          "isRequired": true,
          "isSecret": false,
          "format": "uri"
        },
        {
          "name": "CML_TOKEN",
          "description": "CML API token",
          "isRequired": true,
          "isSecret": true
        }
      ]
    }
  ]
}
```

---

## Error Handling

### Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| Missing environment variables | Required env vars not configured | Add to `mcp_env_vars` |
| Transport error | MCP server failed to start | Check plugin installation |
| Tool not found | Tool name mismatch | Refresh inventory |
| Timeout | MCP server unresponsive | Increase timeout, check logs |

### Health Status

| Status | Description |
|--------|-------------|
| `healthy` | MCP server responding |
| `unhealthy` | Connection issues |
| `degraded` | Partial functionality |
| `unknown` | Not yet checked |

---

## Best Practices

1. **Use transient mode for stateless tools** - Better isolation
2. **Use singleton mode for chatty tools** - Better performance
3. **Store secrets in secret store** - Never hardcode credentials
4. **Set appropriate timeouts** - MCP tools can be slow
5. **Monitor tool execution** - Use OpenTelemetry traces

---

## See Also

- [MCP Protocol Decision](../architecture/mcp-protocol-decision.md) - Why we use MCP for plugins
- [Source Registration](source-registration.md) - General source management
- [Tool Execution](tool-execution.md) - Tool invocation patterns
- [MCP Implementation Plan](mcp-plugin-implementation-plan.md) - Technical details
