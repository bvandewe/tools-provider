# Implementation Plan: Native MCP Plugin Support (Minimal MVP)

**Version:** 2.0.0
**Status:** `DRAFT`
**Date:** December 15, 2025
**Target:** tools-provider v1.x (incremental feature)

---

## 1. Executive Summary

This document defines a **minimal, incremental** implementation plan for adding MCP (Model Context Protocol) plugins as a new source type, aligning with the existing `UpstreamSource`/`SourceTool` domain model.

### Design Philosophy

**MCP is just another SourceType.** We extend the existing patterns rather than create parallel domain entities:

| Current | Addition |
|---------|----------|
| `SourceType.OPENAPI` | `SourceType.MCP` |
| `ExecutionMode.SYNC_HTTP` | `ExecutionMode.MCP_CALL` |
| `OpenApiSpecParser` | `McpManifestParser` |
| `HttpToolExecutor` | `McpToolExecutor` |

### Success Criteria

- [ ] MCP plugins discoverable via existing `/api/sources` endpoints
- [ ] Tools from MCP plugins appear in `SourceTool` with `ExecutionMode.MCP_CALL`
- [ ] Tool execution routes to MCP transport based on execution mode
- [ ] Backward compatibility with existing OpenAPI sources
- [ ] No new domain aggregates (reuse `UpstreamSource`/`SourceTool`)

### Out of Scope (Deferred to Polyglot Entity Model)

- ❌ Neo4j graph projections
- ❌ Multi-dimensional aggregates
- ❌ Resource-oriented reconciliation (spec/status pattern)
- ❌ New domain entities (`McpPlugin` aggregate)

---

## 2. Architecture Decision

### 2.1 Why Extend UpstreamSource?

An MCP plugin is conceptually equivalent to an OpenAPI source:

| Concept | OpenAPI | MCP |
|---------|---------|-----|
| Specification | `openapi.json` | `server.json` manifest |
| Tools | Operations with `operationId` | Tools with `name` |
| Discovery | Parse OpenAPI spec | Parse MCP manifest + tools/list |
| Execution | HTTP request | MCP protocol (stdio/SSE) |
| Auth | Token exchange, API key | Environment variables |

### 2.2 Domain Model Extension

```
UpstreamSource (extended)
├── source_type: OPENAPI | WORKFLOW | BUILTIN | MCP  ← NEW
├── mcp_config: McpSourceConfig | None              ← NEW (for MCP-specific settings)
└── tools: list[SourceTool]

SourceTool (extended)
├── execution_mode: SYNC_HTTP | ASYNC_POLL | MCP_CALL  ← NEW
└── definition: ToolDefinition (unchanged)

McpSourceConfig (new value object)
├── manifest_path: str         # Path to server.json
├── transport_type: stdio|sse  # From manifest
├── lifecycle_mode: transient|singleton
├── environment: dict[str, str]  # Resolved env vars
└── runtime_hint: str          # uvx, docker, etc.
```

---

## 3. Implementation Phases

```
Phase 1: Domain Extension (Week 1)
├── Add SourceType.MCP enum
├── Add ExecutionMode.MCP_CALL enum
├── Create McpSourceConfig value object
├── Create McpManifest parser
└── Update UpstreamSource aggregate

Phase 2: Infrastructure (Week 1-2)
├── Create IMcpTransport interface
├── Implement StdioTransport
├── Create TransportFactory
└── Handle environment variable resolution

Phase 3: Application Layer (Week 2)
├── Create McpToolDiscoveryService
├── Update RegisterSourceCommand for MCP
├── Update SyncSourceCommand for MCP
└── Create McpToolExecutor

Phase 4: Integration & Testing (Week 3)
├── Route tool execution by mode
├── Integration tests
├── Update API documentation
└── Manual testing with cml-mcp
```

---

## 4. Phase 1: Domain Extension

### 4.1 Objectives

- Extend existing enums to support MCP
- Create value objects for MCP configuration
- Extend `UpstreamSource` to store MCP-specific config
- Create manifest parser

### 4.2 Tasks

| ID | Task | File(s) | Effort |
|----|------|---------|--------|
| 1.1 | Add `SourceType.MCP` to enum | `domain/enums/source.py` | 0.25h |
| 1.2 | Add `ExecutionMode.MCP_CALL` to enum | `domain/enums/source.py` | 0.25h |
| 1.3 | Create `McpTransportType` enum | `domain/enums/source.py` | 0.25h |
| 1.4 | Create `PluginLifecycleMode` enum | `domain/enums/source.py` | 0.25h |
| 1.5 | Create `McpSourceConfig` value object | `domain/models/mcp_config.py` | 1h |
| 1.6 | Create `McpManifest` parser | `domain/models/mcp_manifest.py` | 2h |
| 1.7 | Extend `UpstreamSourceState` with `mcp_config` | `domain/entities/upstream_source.py` | 1h |
| 1.8 | Unit tests for manifest parser | `tests/unit/domain/test_mcp_manifest.py` | 1h |

### 4.3 Implementation Details

#### 4.3.1 Enum Extensions

```python
# domain/enums/source.py

class SourceType(str, Enum):
    OPENAPI = "openapi"
    WORKFLOW = "workflow"
    BUILTIN = "builtin"
    MCP = "mcp"  # NEW: Model Context Protocol plugin


class ExecutionMode(str, Enum):
    SYNC_HTTP = "sync_http"
    ASYNC_POLL = "async_poll"
    MCP_CALL = "mcp_call"  # NEW: Execute via MCP protocol


class McpTransportType(str, Enum):
    """MCP transport protocol."""
    STDIO = "stdio"  # Subprocess with stdin/stdout
    SSE = "sse"      # Server-Sent Events (HTTP streaming)


class PluginLifecycleMode(str, Enum):
    """MCP plugin subprocess lifecycle."""
    TRANSIENT = "transient"   # Spawn per-request, kill after
    SINGLETON = "singleton"   # Keep-alive, reuse connection
```

#### 4.3.2 McpSourceConfig Value Object

```python
# domain/models/mcp_config.py

from dataclasses import dataclass
from domain.enums.source import McpTransportType, PluginLifecycleMode


@dataclass(frozen=True)
class McpEnvironmentVariable:
    """Environment variable definition from manifest."""
    name: str
    description: str
    is_required: bool
    is_secret: bool
    value: str | None = None  # Resolved value


@dataclass(frozen=True)
class McpSourceConfig:
    """MCP-specific configuration for an UpstreamSource.

    Stored as a sub-document in UpstreamSource for MCP sources.
    """
    manifest_path: str              # Absolute path to server.json
    plugin_dir: str                 # Directory containing the plugin
    transport_type: McpTransportType
    lifecycle_mode: PluginLifecycleMode
    runtime_hint: str               # uvx, docker, python, etc.
    command: list[str]              # Command to start the server
    environment: dict[str, str]     # Resolved environment variables
    env_definitions: list[McpEnvironmentVariable]  # Original definitions

    @staticmethod
    def from_manifest(manifest: "McpManifest", plugin_dir: str) -> "McpSourceConfig":
        """Create config from parsed manifest."""
        package = manifest.get_default_package()
        return McpSourceConfig(
            manifest_path=f"{plugin_dir}/server.json",
            plugin_dir=plugin_dir,
            transport_type=McpTransportType(package.transport_type),
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,  # Default
            runtime_hint=package.runtime_hint or "uvx",
            command=package.build_command(),
            environment={},  # To be resolved later
            env_definitions=[
                McpEnvironmentVariable(
                    name=env.name,
                    description=env.description,
                    is_required=env.is_required,
                    is_secret=env.is_secret,
                )
                for env in package.environment_variables
            ],
        )
```

#### 4.3.3 McpManifest Parser

```python
# domain/models/mcp_manifest.py

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class McpEnvVarDefinition:
    """Environment variable definition from server.json."""
    name: str
    description: str
    is_required: bool
    is_secret: bool
    format: str = "string"


@dataclass
class McpPackage:
    """Package definition from server.json."""
    registry_type: str       # pypi, npm, docker
    identifier: str          # Package name
    version: str
    runtime_hint: str | None  # uvx, npx, docker
    transport_type: str      # stdio, sse
    environment_variables: list[McpEnvVarDefinition]

    def build_command(self) -> list[str]:
        """Build the command to start this MCP server."""
        if self.runtime_hint == "uvx":
            return ["uvx", self.identifier]
        elif self.runtime_hint == "npx":
            return ["npx", "-y", self.identifier]
        elif self.runtime_hint == "docker":
            return ["docker", "run", "-i", self.identifier]
        else:
            # Assume Python module
            return ["python", "-m", self.identifier.replace("-", "_")]


@dataclass
class McpManifest:
    """Parsed MCP server manifest (server.json).

    Schema: https://static.modelcontextprotocol.io/schemas/2025-10-17/server.schema.json
    """
    name: str
    title: str
    description: str
    version: str
    repository_url: str | None
    packages: list[McpPackage]

    @classmethod
    def parse(cls, manifest_path: str | Path) -> "McpManifest":
        """Parse server.json manifest file."""
        path = Path(manifest_path)
        if not path.exists():
            raise FileNotFoundError(f"Manifest not found: {path}")

        with path.open() as f:
            data = json.load(f)

        packages = []
        for pkg_data in data.get("packages", []):
            env_vars = [
                McpEnvVarDefinition(
                    name=env.get("name", ""),
                    description=env.get("description", ""),
                    is_required=env.get("isRequired", False),
                    is_secret=env.get("isSecret", False),
                    format=env.get("format", "string"),
                )
                for env in pkg_data.get("environmentVariables", [])
            ]
            packages.append(McpPackage(
                registry_type=pkg_data.get("registryType", "pypi"),
                identifier=pkg_data.get("identifier", ""),
                version=pkg_data.get("version", data.get("version", "0.0.0")),
                runtime_hint=pkg_data.get("runtimeHint"),
                transport_type=pkg_data.get("transport", {}).get("type", "stdio"),
                environment_variables=env_vars,
            ))

        return cls(
            name=data.get("name", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            version=data.get("version", "0.0.0"),
            repository_url=data.get("repository", {}).get("url"),
            packages=packages,
        )

    def get_default_package(self) -> McpPackage:
        """Get the first/default package for execution."""
        if not self.packages:
            raise ValueError("Manifest has no packages defined")
        return self.packages[0]
```

#### 4.3.4 UpstreamSourceState Extension

```python
# domain/entities/upstream_source.py - ADDITIONS

# In UpstreamSourceState class:

    # MCP-specific configuration (None for non-MCP sources)
    mcp_config: dict | None  # Serialized McpSourceConfig

# In UpstreamSourceState.__init__():
    self.mcp_config = None

# In on(SourceRegisteredDomainEvent):
    self.mcp_config = getattr(event, "mcp_config", None)
```

---

## 5. Phase 2: Infrastructure (Transport Layer)

### 5.1 Objectives

- Create abstraction for MCP transport
- Implement stdio transport for subprocess-based plugins
- Handle environment variable resolution
- Manage subprocess lifecycle

### 5.2 Tasks

| ID | Task | File(s) | Effort |
|----|------|---------|--------|
| 2.1 | Create `IMcpTransport` interface | `infrastructure/mcp/transport.py` | 0.5h |
| 2.2 | Create MCP protocol models | `infrastructure/mcp/models.py` | 1h |
| 2.3 | Implement `StdioTransport` | `infrastructure/mcp/stdio_transport.py` | 3h |
| 2.4 | Create `TransportFactory` | `infrastructure/mcp/transport_factory.py` | 1.5h |
| 2.5 | Environment variable resolver | `infrastructure/mcp/env_resolver.py` | 1h |
| 2.6 | Unit tests for transport | `tests/unit/infrastructure/test_mcp_transport.py` | 2h |

### 5.3 File Structure

```
src/tools-provider/
└── infrastructure/
    └── mcp/
        ├── __init__.py
        ├── models.py           # McpToolCall, McpToolResult
        ├── transport.py        # IMcpTransport interface
        ├── stdio_transport.py  # Subprocess implementation
        ├── transport_factory.py
        └── env_resolver.py     # Secret resolution
```

### 5.4 Implementation Details

#### 5.4.1 Transport Interface

```python
# infrastructure/mcp/transport.py

from abc import ABC, abstractmethod
from typing import Any


class IMcpTransport(ABC):
    """Interface for MCP protocol transports."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to MCP server."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to MCP server."""
        ...

    @abstractmethod
    async def list_tools(self) -> list[dict[str, Any]]:
        """Discover available tools from MCP server."""
        ...

    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool call and return result."""
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        ...
```

#### 5.4.2 Stdio Transport (Core Implementation)

```python
# infrastructure/mcp/stdio_transport.py

import asyncio
import json
import logging
from typing import Any

from infrastructure.mcp.transport import IMcpTransport

logger = logging.getLogger(__name__)


class StdioTransport(IMcpTransport):
    """MCP transport using subprocess with stdin/stdout."""

    def __init__(
        self,
        command: list[str],
        environment: dict[str, str],
        cwd: str | None = None,
    ):
        self._command = command
        self._environment = environment
        self._cwd = cwd
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0

    async def connect(self) -> None:
        """Spawn subprocess and initialize MCP session."""
        import os

        env = {**os.environ, **self._environment}

        self._process = await asyncio.create_subprocess_exec(
            *self._command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=self._cwd,
        )

        # Send initialize request
        await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "tools-provider", "version": "1.0.0"},
        })

        logger.info(f"MCP transport connected: {' '.join(self._command)}")

    async def disconnect(self) -> None:
        """Terminate subprocess."""
        if self._process:
            self._process.terminate()
            await self._process.wait()
            self._process = None
            logger.info("MCP transport disconnected")

    async def list_tools(self) -> list[dict[str, Any]]:
        """Get tools from MCP server."""
        response = await self._send_request("tools/list", {})
        return response.get("tools", [])

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute tool call via MCP protocol."""
        response = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        return response

    @property
    def is_connected(self) -> bool:
        return self._process is not None and self._process.returncode is None

    async def _send_request(self, method: str, params: dict) -> dict:
        """Send JSON-RPC request and read response."""
        if not self._process or not self._process.stdin or not self._process.stdout:
            raise RuntimeError("Transport not connected")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        # Send request
        request_bytes = json.dumps(request).encode() + b"\n"
        self._process.stdin.write(request_bytes)
        await self._process.stdin.drain()

        # Read response
        response_line = await self._process.stdout.readline()
        if not response_line:
            raise RuntimeError("MCP server closed connection")

        response = json.loads(response_line.decode())

        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")

        return response.get("result", {})
```

---

## 6. Phase 3: Application Layer

### 6.1 Objectives

- Create service to discover tools from MCP plugins
- Extend existing commands to handle MCP sources
- Create executor for MCP tool calls
- Route execution based on `ExecutionMode`

### 6.2 Tasks

| ID | Task | File(s) | Effort |
|----|------|---------|--------|
| 3.1 | Create `McpToolDiscoveryService` | `application/services/mcp_tool_discovery_service.py` | 2h |
| 3.2 | Update `RegisterSourceCommand` for MCP | `application/commands/register_source_command.py` | 1h |
| 3.3 | Update `SyncSourceCommand` for MCP | `application/commands/sync_source_command.py` | 1.5h |
| 3.4 | Create `McpToolExecutor` | `application/services/mcp_tool_executor.py` | 2h |
| 3.5 | Update `ToolExecutionService` routing | `application/services/tool_execution_service.py` | 1h |
| 3.6 | Update settings with MCP config | `application/settings.py` | 0.5h |

### 6.3 Implementation Details

#### 6.3.1 McpToolDiscoveryService

```python
# application/services/mcp_tool_discovery_service.py

from domain.models.mcp_manifest import McpManifest
from domain.models.mcp_config import McpSourceConfig
from domain.models import ToolDefinition, ToolParameter, ExecutionProfile
from domain.enums import ExecutionMode
from infrastructure.mcp.stdio_transport import StdioTransport


class McpToolDiscoveryService:
    """Service to discover tools from MCP plugins."""

    async def discover_tools(
        self,
        config: McpSourceConfig,
    ) -> list[ToolDefinition]:
        """Connect to MCP server and list available tools."""

        transport = StdioTransport(
            command=config.command,
            environment=config.environment,
            cwd=config.plugin_dir,
        )

        try:
            await transport.connect()
            mcp_tools = await transport.list_tools()

            return [
                self._convert_mcp_tool(tool)
                for tool in mcp_tools
            ]
        finally:
            await transport.disconnect()

    def _convert_mcp_tool(self, mcp_tool: dict) -> ToolDefinition:
        """Convert MCP tool schema to ToolDefinition."""
        input_schema = mcp_tool.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        parameters = [
            ToolParameter(
                name=param_name,
                description=param_schema.get("description", ""),
                type=param_schema.get("type", "string"),
                required=param_name in required,
                default=param_schema.get("default"),
            )
            for param_name, param_schema in properties.items()
        ]

        return ToolDefinition(
            name=mcp_tool["name"],
            description=mcp_tool.get("description", ""),
            parameters=parameters,
            execution_profile=ExecutionProfile(mode=ExecutionMode.MCP_CALL),
        )
```

#### 6.3.2 McpToolExecutor

```python
# application/services/mcp_tool_executor.py

from domain.entities.source_tool import SourceTool
from domain.entities.upstream_source import UpstreamSource
from domain.models.mcp_config import McpSourceConfig
from infrastructure.mcp.transport_factory import TransportFactory


class McpToolExecutor:
    """Executes tool calls via MCP protocol."""

    def __init__(self, transport_factory: TransportFactory):
        self._transport_factory = transport_factory

    async def execute(
        self,
        tool: SourceTool,
        source: UpstreamSource,
        arguments: dict,
        user_claims: dict,
    ) -> dict:
        """Execute tool via MCP transport."""

        config = McpSourceConfig.from_dict(source.state.mcp_config)
        transport = await self._transport_factory.get_transport(config)

        try:
            result = await transport.call_tool(
                tool_name=tool.state.operation_id,
                arguments=arguments,
            )
            return {
                "success": True,
                "content": result.get("content", []),
                "is_error": result.get("isError", False),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
```

#### 6.3.3 Settings Addition

```python
# application/settings.py - Add these settings

    # MCP Plugin Configuration
    mcp_plugins_dir: str = Field(default="./src/tools", env="MCP_PLUGINS_DIR")
    mcp_discovery_enabled: bool = Field(default=True, env="MCP_DISCOVERY_ENABLED")
```

---

## 7. Phase 4: Integration & Testing

### 7.1 Objectives

- Complete integration of MCP into existing flows
- Comprehensive testing with `cml-mcp` reference plugin
- Documentation updates

### 7.2 Tasks

| ID | Task | File(s) | Effort |
|----|------|---------|--------|
| 4.1 | Integration test: register MCP source | `tests/integration/test_mcp_source.py` | 2h |
| 4.2 | Integration test: sync MCP tools | `tests/integration/test_mcp_tools.py` | 2h |
| 4.3 | Integration test: execute MCP tool | `tests/integration/test_mcp_execution.py` | 2h |
| 4.4 | Manual test with cml-mcp | N/A | 1h |
| 4.5 | Update API documentation | `docs/` | 1h |
| 4.6 | Update README with MCP section | `README.md` | 0.5h |

---

## 8. API Usage Examples

### 8.1 Register an MCP Source

```bash
# POST /api/sources
{
  "name": "cml-mcp",
  "description": "Cisco Modeling Labs MCP Plugin",
  "source_type": "mcp",
  "url": "file:///app/src/tools/cml-mcp",  # Plugin directory
  "mcp_config": {
    "lifecycle_mode": "transient",
    "environment": {
      "CML_URL": "https://cml.example.com",
      "CML_USERNAME": "admin"
    }
  }
}
```

### 8.2 Sync Tools from MCP Source

```bash
# POST /api/sources/{source_id}/sync

# Response includes discovered tools:
{
  "tools_discovered": 12,
  "tools": [
    {
      "name": "get_labs",
      "description": "List all labs",
      "execution_mode": "mcp_call"
    }
  ]
}
```

### 8.3 Execute MCP Tool

```bash
# POST /api/tools/execute
{
  "tool_id": "cml-mcp:get_labs",
  "arguments": {
    "show_all": true
  }
}
```

---

## 9. Effort Summary

| Phase | Tasks | Effort (hours) |
|-------|-------|----------------|
| Phase 1: Domain Extension | 8 | 6 |
| Phase 2: Infrastructure | 6 | 9 |
| Phase 3: Application Layer | 6 | 8 |
| Phase 4: Integration & Testing | 6 | 8.5 |
| **Total** | **26** | **31.5** |

**Estimated duration: 3 weeks** (assuming 12 hours/week)

---

## 10. Definition of Done

- [ ] `SourceType.MCP` recognized by all existing source endpoints
- [ ] MCP tools appear in `/api/tools` with correct execution mode
- [ ] Tool execution routes correctly to MCP transport
- [ ] `cml-mcp` plugin works end-to-end
- [ ] Unit tests cover manifest parsing and transport
- [ ] Integration tests cover full workflow
- [ ] No breaking changes to existing OpenAPI sources

---

## 11. Future Enhancements (Out of Scope)

These features are deferred to the **Polyglot Entity Model** implementation:

1. **Graph Projections** - Neo4j relationships between sources/tools/policies
2. **Resource Reconciliation** - K8s-style spec/status with health monitoring
3. **SSE Transport** - Remote MCP servers via HTTP streaming
4. **Plugin Cloning** - `git clone` workflow for plugin installation
5. **Plugin Management UI** - Frontend for plugin configuration

---

## 12. References

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [cml-mcp Reference Plugin](./src/tools/cml-mcp/)
- [Existing UpstreamSource Pattern](../architecture/event-sourcing.md)
