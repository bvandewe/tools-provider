# Changelog

All notable changes to this project will be documented in this file.

The format follows the recommendations of Keep a Changelog (https://keepachangelog.com) and the project aims to follow Semantic Versioning (https://semver.org).

## [Unreleased]

### Added

#### MCP Documentation Overhaul

- **MCP Tools Guide**: New comprehensive [mcp-tools.md](docs/architecture/mcp-tools.md) documenting Plugin mode (stdio), Remote mode (Streamable HTTP), transport interface, and execution flows
- **MCP Protocol Decision**: Rewrote [mcp-protocol-decision.md](docs/architecture/mcp-protocol-decision.md) from "We will NOT implement MCP" to "Hybrid MCP Integration" strategy
- **Source Registration Docs**: Updated [source-registration.md](docs/implementation/source-registration.md) with MCP source types, Plugin/Remote examples, transport selection
- **Tool Discovery Docs**: Updated [tool-discovery.md](docs/implementation/tool-discovery.md) with MCP tool discovery via `McpSourceAdapter`
- **Architecture Overview**: Updated [overview.md](docs/architecture/overview.md) with MCP sources in system diagram and Key Value Objects
- **Index & Features**: Updated landing pages with Multi-Source Integration and MCP modes
- **Getting Started**: Fixed outdated repo name, Python version, port numbers, and added service URLs

#### Remote MCP Server Tool Execution (tools-provider)

- **McpToolExecutor Service**: New service for executing tools via MCP protocol with DI configuration
- **HttpTransport SSE Support**: Added SSE response parsing for `call_tool` method to handle streaming responses
- **MCP Header Conversion**: TransportFactory now converts `MCP_HEADER_*` environment variables to HTTP headers (strips prefix, converts underscores to hyphens)
- **Source Projection Fix**: `SourceRegisteredProjectionHandler` now persists `mcp_config` to MongoDB read model

### Fixed

- **ExecuteToolCommand Handler**: Fixed `command.payload` → `command.arguments` for tool execution
- **McpToolExecutor DI Registration**: Moved service configuration before Mediator.configure() so handlers can inject it
- **Remote MCP Validation**: Headers now passed correctly during source registration validation

#### MCP Plugin Support - Phase 2 Infrastructure Layer (tools-provider)

- **IMcpTransport Interface**: Abstract base class defining MCP transport contract with `connect()`, `disconnect()`, `list_tools()`, `call_tool()` methods
- **StdioTransport**: Subprocess-based transport using stdin/stdout for JSON-RPC communication with MCP servers
- **MCP Protocol Models**: Complete JSON-RPC 2.0 message types (`McpRequest`, `McpResponse`, `McpError`, `McpNotification`, `McpToolResult`, `McpToolDefinition`, `McpServerInfo`)
- **TransportFactory**: Factory with connection pooling for SINGLETON lifecycle mode and transport creation for TRANSIENT mode
- **McpEnvironmentResolver**: Multi-source environment variable resolution (runtime > secrets file > config > OS env) with secret masking
- **MCP Error Hierarchy**: `McpTransportError`, `McpConnectionError`, `McpProtocolError`, `McpTimeoutError` for granular error handling
- **Infrastructure Tests**: 42 unit tests for MCP transport layer components

#### MCP Plugin Support - Phase 1 Domain Layer (tools-provider)

- **MCP Enums**: Added `SourceType.MCP`, `ExecutionMode.MCP_CALL`, `McpTransportType`, `PluginLifecycleMode` to support MCP plugin sources
- **McpSourceConfig Value Object**: Configuration for MCP plugins including manifest path, transport type, lifecycle mode, command, and environment variables
- **McpManifest Parser**: Parser for MCP `server.json` manifest files with support for multiple package registries (PyPI, NPM, Docker)
- **McpEnvironmentVariable**: Value object for environment variable definitions from MCP manifests
- **UpstreamSource Extension**: Extended aggregate to store `mcp_config` for MCP sources
- **Test Factories**: Added `McpSourceConfigFactory` and `McpManifestFactory` for test data generation

#### Architecture Documentation

- **Polyglot Entity Model**: Added comprehensive architecture documentation for multi-dimensional entities with Temporal, Intentional, Semantic, and Observational aspects
- **Polyglot User/Agent Architecture**: Added design for stateful AI agents with Knowledge Graph, Goals/Plans, and Telemetry aspects
- **MCP Plugin Implementation Plan**: Added detailed implementation plan for native MCP plugin support

#### Scope-Based Access Control UI (tools-provider + agent-host)

- **Source Scopes Management**: Added `required_scopes` input to Add/Edit Source modals for configuring source-level scope requirements
- **Source Details Display**: Required scopes shown as badges in source details modal
- **Tool Details Display**: Required scopes shown as badges in tool details modal (tools-provider and agent-host)
- **Tool Card Indicator**: Lock icon displayed on tool cards when tool has required scopes
- **Insufficient Scope Error Handling**: User-friendly "Permission Required" alert in agent-host when tool execution fails due to missing scopes
- **My Permissions Modal**: New "My Permissions" option in agent-host user dropdown showing user's OAuth2 scopes grouped by prefix

#### Scope-Based Access Control Backend (tools-provider)

- **SourceToolDto Enhancement**: Added `required_scopes` field to `SourceToolDto` and `SourceToolSummaryDto` for efficient querying
- **UpdateSourceCommand Extension**: `required_scopes` parameter added to allow updating source-level scopes
- **Backward Compatibility**: Event handlers use `getattr()` with defaults for replaying old events without `required_scopes` field

#### Scope-Based Access Control (tools-provider)

- **OpenAPI Scope Discovery**: `OpenAPISourceAdapter._extract_required_scopes()` automatically extracts OAuth2 scopes from operation security declarations during source registration
- **Scope Validation**: `ToolExecutor` validates user scopes before token exchange with `InsufficientScopeError` (403 Forbidden) for clear error feedback
- **Source-Level Scopes**: `UpstreamSource` aggregate supports `required_scopes` field to override auto-discovered scopes for all tools from a source
- **Token Exchange Enhancement**: Passes required scopes to `KeycloakTokenExchanger` for least-privilege token requests
- **Architecture Documentation**: Created [scope-based-access-control.md](docs/architecture/scope-based-access-control.md) with design principles, resolution hierarchy, and implementation details

#### SwaggerUI Security Enhancements (agent-host)

- **Dual Authentication**: `dependencies.py` now supports both session cookies (OAuth2 flow) and JWT Bearer tokens via `HTTPBearer` security scheme
- **OpenAPI Configuration**: Integrated `openapi_config.py` module with OAuth2 Authorization Code flow for Swagger UI authentication
- **API Description**: Added comprehensive [description.md](src/agent-host/api/description.md) for agent-host API documentation
- **Endpoint Docstrings**: Enhanced all controller endpoints with detailed Input/Output/Side Effects documentation

#### SwaggerUI Security Enhancements (tools-provider)

- **API Description**: Added comprehensive [description.md](src/tools-provider/api/description.md) for tools-provider API documentation

### Changed

#### Application Layer Restructuring (tools-provider)

- **Commands reorganized into semantic submodules**: Moved 36 command files into 7 entity-based subfolders under `application/commands/`:
  - `task/` - CreateTaskCommand, UpdateTaskCommand, DeleteTaskCommand
  - `source/` - RegisterSourceCommand, UpdateSourceCommand, DeleteSourceCommand, RefreshInventoryCommand
  - `tool/` - EnableToolCommand, DisableToolCommand, UpdateToolCommand, DeleteToolCommand, AddLabelToToolCommand, RemoveLabelFromToolCommand, CleanupOrphanedToolsCommand
  - `tool_group/` - 13 commands for CRUD, selectors, explicit tools, exclusions
  - `access_policy/` - DefineAccessPolicyCommand, UpdateAccessPolicyCommand, ActivateAccessPolicyCommand, DeactivateAccessPolicyCommand, DeleteAccessPolicyCommand
  - `label/` - CreateLabelCommand, UpdateLabelCommand, DeleteLabelCommand
  - `execution/` - ExecuteToolCommand

- **Queries reorganized into semantic submodules**: Moved 9 query files into 7 entity-based subfolders under `application/queries/`:
  - `task/` - GetTasksQuery, GetTaskByIdQuery
  - `source/` - GetSourcesQuery, GetSourceByIdQuery
  - `tool/` - GetSourceToolsQuery, GetToolByIdQuery, SearchToolsQuery, GetToolSummariesQuery, CheckToolSyncStatusQuery
  - `tool_group/` - GetToolGroupsQuery, GetToolGroupByIdQuery, GetGroupToolsQuery
  - `access_policy/` - GetAccessPoliciesQuery, GetAccessPolicyByIdQuery
  - `agent/` - GetAgentToolsQuery
  - `label/` - GetLabelsQuery, GetLabelByIdQuery, GetLabelSummariesQuery

- **BuiltinToolExecutor refactored**: Split 2196-line monolithic file into modular `builtin_tools/` submodule (148-line orchestrator):
  - `base.py` - Shared types (BuiltinToolResult, UserContext), constants, helpers
  - `fetch_tools.py` - fetch_url, web_search, wikipedia_query, browser_navigate
  - `utility_tools.py` - datetime, calculate, uuid, encode_decode, regex, json_transform, text_stats
  - `file_tools.py` - file_writer, file_reader, spreadsheet_read, spreadsheet_write
  - `memory_tools.py` - memory_store, memory_retrieve
  - `code_tools.py` - execute_python
  - `human_tools.py` - ask_human

### Fixed

#### Python Sandbox Execution (tools-provider)

- **RestrictedPython API fix**: Use `compile_restricted_exec` which returns `CompileResult` with `.errors` attribute instead of `compile_restricted` which returns raw `code` object
- **Missing builtins**: Added `len`, `str`, `int`, `float`, `enumerate`, `zip`, `map`, `filter`, `all`, `any`, common exceptions, and other safe builtins to the sandbox
- **Iterator support**: Added `_getiter_` guard required for `for` loops and comprehensions
- **REPL-style expression capture**: Last expression in code is now evaluated and returned (like Python REPL/Jupyter), eliminating need for explicit `result` variable

### Added

#### File Upload/Download System (tools-provider + agent-host)

- **FilesController** (tools-provider): New REST API for workspace file operations
  - `GET /api/files/` - List files in user's workspace with expiry info
  - `GET /api/files/{filename}` - Download file with temporary URL headers
  - `POST /api/files/upload` - Upload files (10MB limit, common extensions)
  - Files isolated per user via JWT `sub` claim
  - 24-hour TTL with automatic cleanup

- **FilesController** (agent-host): Proxy for `/api/files/*` routes
  - Enables direct file downloads from agent-generated links
  - Proxies to tools-provider `/api/files/*` endpoints

- **ToolsController** (agent-host): Proxy controller for tools-provider endpoints
  - Routes `/api/tools/files/*` to tools-provider `/api/files/*`
  - Forwards authentication headers and cookies
  - Enables same-origin access from UI without CORS issues

- **FileUpload.js** (agent-host UI): File upload component
  - Paperclip button in chat input area
  - Drag-and-drop support on chat area
  - File badges showing attached files
  - 10MB size limit, common file type validation
  - Automatic file message prefix for agent awareness

- **Per-user workspace isolation**: `BuiltinToolExecutor._get_workspace_dir()` now creates per-user directories

#### SSE Stream Optimization for File Tools (agent-host)

- **`_summarize_tool_result_for_stream()`**: New function in `react_agent.py`
  - File tools (`file_reader`, `file_writer`, `spreadsheet_read`, `spreadsheet_write`) stream metadata only
  - Prevents SSE parsing errors from large file content in browser
  - LLM still receives full content for reasoning via `result.to_llm_message()`
  - Other tools: full result if ≤1KB, truncated preview otherwise

#### Enhanced Agent Prompts with Built-in Tools Documentation (agent-host)

- **System prompt** (`settings.py`): Comprehensive built-in tools section
  - Categorized tool descriptions (Time, Web, Code, Memory, Files, Utilities)
  - Critical date/time awareness instructions
  - Guidance on tool chaining and file deliverables

- **Proactive agent prompts** (`proactive_agent.py`): Added built-in tools sections
  - Thinking session: Memory, web search, file creation guidance
  - Learning session: Code execution, file tracking, calculation tools
  - Default session: Complete tool list with use cases

#### Built-in Tool Enhancements (tools-provider)

- **fetch_url**: `save_as_file` parameter to override filename; auto-saves binary files to workspace
- **file_writer**: `is_binary` parameter for binary file support (base64 content)
- **file_reader**: Rejects binary files with helpful error messages and tool suggestions
- **spreadsheet_read**: Size limits (100KB result), cell truncation (500 chars), pagination hints
- **All file tools**: Now return `download_url` and `ttl_hours` in results

#### Tests for Built-in Tool File Handling (tools-provider)

- **test_builtin_tool_executor.py**: New test file
  - `TestFileWriter`: Text files, binary files with `is_binary`, extension validation
  - `TestFetchUrlSaveAsFile`: Path traversal prevention
  - `TestToolDefinitions`: Schema validation for new parameters

#### User-Scoped Memory for Built-in Tools (tools-provider)

- **UserContext dataclass**: Added to `BuiltinToolExecutor` for tracking user identity during tool execution
- **User-scoped memory storage**: Memory tools now isolate data per user
  - Redis keys: `agent:memory:{user_id}:{key}` format
  - File fallback: `/tmp/agent_memory/{user_id}/memory.json` per-user directories
- **JWT user extraction**: `ToolExecutor._extract_user_context()` extracts `sub` claim from agent token
- **Memory tool improvements**: Both `memory_store` and `memory_retrieve` respect user context

#### Updated Built-in Tools List (tools-provider)

- **17 built-in tools** now available (up from 8):
  - Utility: `fetch_url`, `get_current_datetime`, `calculate`, `generate_uuid`, `encode_decode`, `regex_extract`, `json_transform`, `text_stats`
  - Web & Search: `web_search`, `wikipedia_query`
  - Code Execution: `execute_python`
  - File Tools: `file_writer`, `file_reader`, `spreadsheet_read`, `spreadsheet_write`
  - Memory Tools: `memory_store`, `memory_retrieve`
  - Human Interaction: `ask_human`

### Fixed

#### Download Link Handling (agent-host)

- **sandbox: URL prefix**: Custom marked renderer strips `sandbox:` prefix from agent-generated file URLs
- **marked v15 API**: Updated link renderer to handle token-based API (object with `{href, title, text}` properties)
- **File route 404**: Added FilesController to handle `/api/files/*` routes directly (not via `/api/tools/`)

#### OpenAI Function Schema Compatibility (tools-provider)

- **json_transform schema fix**: Changed `"type": ["object", "array", "string"]` to proper `anyOf` pattern with explicit `items` for array type, fixing OpenAI API validation error

#### UI Dark Mode Consistency (tools-provider)

- **Table headers**: `.table-light` now uses dark gray background in dark mode
- **Card headers**: `.card-header` properly styled for dark mode
- **Disabled rows**: `.table-secondary` (disabled tools) uses dark styling
- **bg-light overrides**: All `.bg-light` elements now respect dark mode
- **Form controls**: Dark background and proper border colors
- **Code elements**: Pink text with subtle dark background

### Changed

#### Built-in Source Display (tools-provider)

- **Source card badge**: Built-in sources now show "Local" (green) instead of "Public" to clarify they execute in-process
- **Source details modal**: Shows "Local (No upstream auth needed)" for built-in sources
- **Built-in tools modal**: Updated to show all 17 tools organized by category with descriptions
- **Toast message**: Updated default tool count from 8 to 17

#### Built-in Source Infrastructure (tools-provider)

- **SourceType enum**: Added `BUILTIN` source type for built-in tool sources
- **BuiltinSourceAdapter**: Registered in adapter registry for built-in source handling
- **RegisterSourceCommand**: Skip URL validation for built-in sources (no upstream URL needed)
- **Docker config**: Added Redis memory configuration (DB3) with `REDIS_MEMORY_URL` and key prefix

### Added

#### Blueprint-Driven Evaluation System (agent-host)

- **Domain Models**: Complete blueprint system for assessment item generation
  - `Skill`: Blueprint defining how to generate items (stem templates, difficulty levels, distractor strategies)
  - `ExamBlueprint`: Complete exam definition with domains, skills, and configuration
  - `ExamDomain`: Section within an exam with skill references and item counts
  - `GeneratedItem`: LLM-generated assessment item with correct answer stored server-side
  - `EvaluationResults`: Final session results with per-domain breakdown

- **Application Services**: Item generation and session orchestration
  - `BlueprintStore`: Loads and caches YAML blueprints from `data/blueprints/` directory
  - `ItemGeneratorService`: LLM-based item generation from skill blueprints
  - `EvaluationSessionManager`: Orchestrates evaluation sessions with backend tool execution

- **Blueprint Files**: Phase 1 exam blueprints (Math + Networking)
  - Math: Two-digit addition, subtraction, single-digit multiplication
  - Networking: CIDR to subnet mask, network address calculation, host count
  - Exam blueprints: `math_fundamentals.yaml` (3 items), `networking_basics.yaml` (9 items)

- **Session Flow Fixes**: Multi-round evaluation sessions now work end-to-end
  - `SetPendingActionCommand` now calls `session.start_item()` before `set_pending_action()`
  - Items are properly tracked in `session.state.items[]` for response validation

- **UI Components**: Exam selection modal for evaluation sessions
  - `_exam_select.jinja`: Modal for choosing exam blueprint when starting evaluation

- **Documentation**: Session flow specification
  - `docs/specs/session-flow.md`: Architecture for proactive sessions, SSE lifecycle, answer security model

- **Tests**: Comprehensive test coverage for evaluation services

### Fixed

#### Proactive Session Fixes (agent-host)

- **Session items not tracked**: `SetPendingActionCommand` now calls `start_item()` to create items before setting pending action, ensuring responses can be validated
- **DateTime timezone mismatch**: `SessionItem.from_dict()` now ensures timezone-aware datetimes when parsing ISO strings, fixing `TypeError` on datetime subtraction in `submit_response()`

### Added

#### Multi-Mode Authentication for Upstream Sources (tools-provider)

- **AuthMode enum**: Four authentication levels for upstream service integration
  - `NONE`: No authentication (public APIs)
  - `API_KEY`: Static API key in header or query parameter
  - `CLIENT_CREDENTIALS`: OAuth2 client credentials grant (service-to-service)
  - `TOKEN_EXCHANGE`: RFC 8693 token exchange (user context delegation)

- **OAuth2ClientCredentialsService**: New service for client credentials flow
  - Token caching with configurable TTL buffer
  - Support for default service account and source-specific credentials
  - Async token acquisition with error handling

- **Frontend auth mode selection**: Dynamic UI for source registration
  - Auth mode dropdown in Add Source modal
  - Conditional credential fields based on selected mode
  - Auth mode badge on source cards and details modal

### Changed

- **ToolExecutor**: Multi-mode authentication support in `_get_upstream_token()` and `_render_headers()`
- **RegisterSourceCommand**: Now accepts `auth_mode` parameter and builds `AuthConfig` from mode-specific fields
- **SourceRegisteredProjectionHandler**: Projects `auth_mode` to MongoDB read model
- **RegisterSourceRequest**: Added `auth_mode` field to API request model

### Added

#### File-Based Secret Management for Upstream Credentials (tools-provider)

- **SourceSecretsStore**: New infrastructure service for managing upstream source credentials
  - YAML-based credential storage (`secrets/sources.yaml`) gitignored from repository
  - Supports HTTP Basic, API Key, OAuth2 client credentials, and Bearer token auth types
  - Kubernetes-native design: mount credentials from K8s Secret at runtime
  - Path resolution via `SOURCE_SECRETS_PATH` environment variable

- **Architecture documentation**: `docs/architecture/secret-management.md`
  - Design rationale for file-based vs event-sourced credential storage
  - YAML schema for source credentials with examples
  - Kubernetes deployment patterns and credential rotation procedures

### Fixed

#### OpenAPI Source Adapter Fixes (tools-provider)

- **Missing query parameters in URL templates**: `_build_url_template()` now extracts query parameters from OpenAPI spec and generates Jinja2 conditional templates for optional params
- **Non-standard JSON Schema types rejected by OpenAI**: Added `_normalize_type()` to convert non-standard types (e.g., `Str`→`string`, `Int`→`integer`) in both `_build_input_schema()` and `_simplify_schema()`

#### Tool Executor Fixes (tools-provider)

- **Auth header logging incorrectly showed "Bearer" for all auth types**: `_log_request()` now correctly masks `Basic ***` vs `Bearer ***` based on actual header content
- **HTTP Basic auth not applied**: `_render_headers()` now properly constructs `Authorization: Basic <base64>` header when `auth_mode=HTTP_BASIC` and credentials are available from secrets store

### Changed

#### Source Registration UI Improvements (tools-provider)

- **API Key / HTTP Basic credential fields removed**: These auth modes now display informational alerts explaining that credentials must be configured in `secrets/sources.yaml` after registration
- **Success toast includes source ID**: When registering sources with API Key or HTTP Basic auth, the success message now includes the source ID for easy copy/paste into the secrets file
- **Documentation links added**: Auth mode panels link to the secret management architecture docs

### Fixed

- **Auth mode not persisted**: Fixed projection handler missing `auth_mode` field
- **API key not sent**: Fixed `_build_auth_config` to build config from `auth_mode` fields
- **Test failures**: Fixed 6 pre-existing test failures (settings case, session expiration, rename integrity)

### Added

#### Proactive Agent Sessions (agent-host)

- **Session Aggregate**: Full DDD implementation with event sourcing for proactive learning sessions
  - `Session` aggregate with `SessionState`, status transitions, and pending action management
  - Domain events: `SessionCreatedDomainEvent`, `SessionStartedDomainEvent`, `SessionCompletedDomainEvent`
  - Value objects: `SessionConfig`, `ClientAction`, `ClientResponse`, `SessionItem`, `UiState`
  - Session types: LEARNING, THOUGHT, VALIDATION with appropriate control modes

- **Proactive Agent**: Agent that drives conversations proactively using client tools
  - `ProactiveAgent` with suspension/resumption for user interactions
  - Client tools: `present_choices`, `request_free_text`, `present_code_editor`
  - Session-specific system prompts for learning, thought, and validation modes
  - `AgentFactory` for creating agents based on session type

- **Question Bank Service**: Sample questions for learning sessions
  - 15 questions across Algebra, Geometry, and Python categories
  - Multiple choice, free text, and code editor question types
  - Answer validation and feedback generation

- **Interactive Widgets**: Web components for user interactions
  - `<ax-multiple-choice>`: Keyboard-navigable option selection
  - `<ax-free-text-prompt>`: Text input with validation
  - `<ax-code-editor>`: Code editor with line numbers and syntax hints

- **Session Management UI**: Sidebar-based session type selection
  - Mode selector dropdown (Chat, Learning, Thought, Evaluation)
  - Session list with pin/delete functionality
  - Session switching and history loading
  - End session button with confirmation

- **Comprehensive Test Suite**: Unit and E2E tests for proactive features
  - Domain model tests (`test_session_aggregate.py`, `test_session_models.py`)
  - Agent tests (`test_proactive_agent.py`, `test_agent_factory.py`, `test_client_tools.py`)
  - Infrastructure tests (`test_question_bank_service.py`)
  - E2E test fixtures with Playwright (`conftest.py`, `test_learning_sessions.py`)

### Changed

#### UI/UX Improvements (agent-host)

- **Chat Input Behavior**: Input hidden during proactive sessions, locked after session ends
- **Session Badges**: Display session type and status in sidebar
- **Tool Badges**: Fixed "Unknown Tool" display issue in chat messages
- **Mode Selector Visibility**: Hidden during evaluation sessions for lockdown mode
- **Simplified Learning Sessions**: Replaced category selection with single "Learning Session" option

### Fixed

#### Tool Execution Fixes

- **OpenTelemetry NoneType Warning**: Fixed span attribute handling in `ExecuteToolCommand` to skip `tool.validate_schema` when `None` instead of passing invalid type to OpenTelemetry
- **Redis Cache Connection**: Converted `RedisCacheService` to implement `HostedService` pattern for proper lifecycle management - Redis now connects on startup and disconnects on shutdown automatically

### Changed

#### Infrastructure Improvements

- **RedisCacheService as HostedService**: Refactored to use Neuroglia's `HostedService` pattern with `start_async()`/`stop_async()` lifecycle methods, aligning with framework conventions (like `CloudEventIngestor`)
- **API Documentation**: Updated agent controller docstrings to use correct `/api/agent/` path prefix

### Added

#### Proactive Agent Specification

- **Comprehensive Specification Document**: New `docs/specs/proactive-agent-specification.md` (~800 lines)
  - Defines Session aggregate as composition wrapper around Conversation
  - Specifies `reactive` vs `proactive` control modes
  - Documents Client Tool registry with 12+ UI widgets
  - Details agent loop suspension/resumption mechanism for user interactions
  - Includes API contracts for Session endpoints
  - Outlines 5-phase implementation plan
- **MkDocs Navigation**: Added Proactive Agent spec under Agent Host section

#### Implementation Documentation

- **Implementation Guide**: New `docs/implementation/` section documenting end-to-end data flows
- **Source Registration**: Detailed documentation of RegisterSourceCommand and projection handlers
- **Tool Discovery**: RefreshInventoryCommand flow with adapter architecture
- **Groups & Policies**: ToolGroup/AccessPolicy with correct AND/OR logic documentation
- **Agent Tools Query**: GetAgentToolsQuery resolution flow with caching strategy
- **Tool Execution**: ToolExecutor with token exchange, templates, and circuit breakers
- **MkDocs Navigation**: Added Implementation section to mkdocs.yml navigation

### Removed

- **Proactive Agent Draft**: Removed outdated `docs/specs/proactive-agent-draft.md` (superseded by comprehensive spec)

### Changed

#### Documentation Updates

- **README.md**: Updated to reflect current implementation state
  - Removed "_(planned)_" from ToolGroup and AccessPolicy (both fully implemented)
  - Added complete API endpoint tables for Tool Groups, Access Policies, and Agent endpoints
  - Updated project structure to show multi-app architecture (tools-provider, agent-host, upstream-sample)
  - Added Label entity to Domain Aggregates section
- **docs/index.md**: Updated Domain Entities section to reflect current implementation
  - Removed "_(planned)_" markers from ToolGroup
  - Added AccessPolicy and Label entities
  - Updated entity descriptions with current feature set

#### Tool Group Label Selector

- **Label Selector Type**: Tool Groups now support matching tools by Label IDs in addition to source, name, path, method, and tag patterns
- **ToolSelector Domain Model**: Added `required_label_ids` field and `label_ids` parameter to `matches()` method
- **Full Stack Implementation**: Backend commands/queries, REST API, and UI all support Label selectors
- **ToolSelectorFactory**: Added `create_method_selector()` and `create_label_selector()` factory methods for tests

#### Tool Editing Feature

- **Update Tool API**: New `PUT /api/tools/{tool_id}` endpoint to update tool_name and/or description
- **UpdateToolCommand**: CQRS command with handler for persisting tool metadata changes
- **SourceToolUpdatedDomainEvent**: New domain event for tool updates with CloudEvent publishing
- **Edit UI in Tool Details**: Tool Details modal now has Edit/Save/Cancel buttons for inline editing
- **Operation ID Display**: Tool Details modal shows read-only operation_id (original from upstream API)

#### Database Sync Diagnostics

- **Sync Status Endpoint**: New `GET /api/tools/diagnostics/sync-status` admin endpoint
- **CheckToolSyncStatusQuery**: Detects orphaned tools (exist in MongoDB but not EventStoreDB)
- **UI Warning Banner**: Tools page shows prominent warning when sync issues detected
- **Source-grouped Report**: Warning banner groups orphaned tools by source for easy resolution

#### UI Convenience Features

- **Roles Claim Option**: Added "roles" option to policy claim path dropdown for Keycloak compatibility
- **Source Tools Link**: Source cards now have clickable tool count that navigates to filtered Tools page
- **Scrollable Edit Modal**: Groups edit modal now scrollable for better UX with large tool lists
- **Swagger UI Link**: Added API documentation icon in footer linking to `/api/docs`

### Fixed

#### Tool Group Selector AND Logic

- **Backend Logic Fix**: Changed selector matching from OR to AND logic - tools must match ALL selectors in a group
- **Consistent Behavior**: Frontend already used AND logic, backend now matches

### Changed

- **Remove MCP Branding**: Removed "MCP" references from UI (Tools page title, footer copyright)
- **Method/Labels Passed**: Fixed `matches()` calls to include `method` and `label_ids` parameters

#### Tools Page Loading

- **Include Disabled Tools**: Tools page now loads all tools including disabled ones for admin management

### Changed

- **Edit Modal Tabs**: Groups edit modal reorganized with Tools/Explicit/Excluded tabs for better tool management
- **Tool Preview**: Edit modal tool preview now properly applies explicit inclusions and exclusions

#### Agent Host LLM Provider Infrastructure

- **LlmProviderFactory**: New factory pattern for runtime LLM provider selection supporting multiple providers (Ollama, OpenAI)
- **Model Routing**: Support for qualified model IDs (e.g., "openai:gpt-4o", "ollama:llama3.2:3b")
- **Singleton Registry**: Providers registered once during startup and reused at runtime
- **Redis Token Cache**: `OpenAiTokenCache` for OAuth2 token caching with automatic refresh and TTL management

#### Agent Host Multi-Provider Configuration

- **OpenAI Provider Settings**: Full configuration support for OpenAI-compatible APIs (standard OpenAI, Azure, Cisco Circuit)
- **Unified Error Handling**: `LlmProviderError` class with error codes, retryability, and provider context
- **ModelDefinition Dataclass**: Typed model definitions replacing pipe-delimited string format
- **LlmProviderType Enum**: Type-safe provider enumeration (OLLAMA, OPENAI)
- **Dual Auth Support**: API key and OAuth2 client credentials for OpenAI endpoints
- **Config Controller Enhanced**: New `/api/config/models` endpoint for dynamic model listing
- **App Settings DTO**: Updated to include OpenAI configuration and provider-aware model list

#### Agent Host UI Modular Architecture

- **UI Folder Restructured**: Moved `agent-host/ui/` to `agent-host/src/ui/` to match tools-provider structure
- **Refactored UI to ES6 Modules**: Split monolithic `app.js` into focused manager modules:
  - `config-manager.js`: App configuration loading, model selector initialization
  - `conversation-manager.js`: Conversation list rendering, CRUD, pinning
  - `draft-manager.js`: Message draft persistence with debounced auto-save
  - `message-renderer.js`: Chat message rendering, tool result merging
  - `sidebar-manager.js`: Sidebar collapse/expand, responsive behavior
  - `stream-handler.js`: SSE streaming for chat messages
  - `ui-manager.js`: UI state, status indicator, health check
  - `helpers.js`: Utility functions, storage helpers, device detection
- **Preserved Original**: Backup of original app in `app.original.js` for reference

#### Upstream Sample Service Persistence

- **MongoDB Integration**: Added Motor async driver for database operations
- **Collection Management**: Menu items, orders, and counters collections with indexes
- **Auto-increment IDs**: Sequence counter for order numbering
- **Order Cancel Endpoint**: New `POST /api/orders/{order_id}/cancel` for order cancellation
- **Persistent CRUD**: Menu and order routers now use MongoDB instead of in-memory storage
- **Kitchen Router Updates**: Integrated with MongoDB for order status management

#### Docker Compose Improvements

- **Service Configuration Refactored**: Cleaner YAML structure with improved environment variable organization
- **Multi-Provider Support**: Updated agent-host configuration for OpenAI provider settings

#### UpstreamSource Edit and Description Support

- **Description Field**: Added optional `description` field to UpstreamSource aggregate for human-readable documentation
- **Service URL Field**: Added explicit `url` field (service base URL) separate from `openapi_url` (spec URL)
- **Update Source API**: New `PATCH /api/sources/{id}` endpoint to update source name, description, and service URL
- **Edit Source Modal**: UI modal for editing existing sources (name, description, service URL) with read-only OpenAPI URL
- **Edit Button on Source Cards**: Quick access to edit source details from the source card

### Fixed

#### LLM Model Selection Not Applied

- **Field Name Mismatch**: Fixed model selection from UI not being used - `SendMessageRequest` expected `model` but frontend sent `model_id`
- **Factory Singleton Access**: Fixed `LlmProviderFactory.get_provider_for_model()` being called as static method instead of using the singleton instance

#### Circuit API (OpenAI Provider) Authentication

- **API Key Header Format**: Changed OAuth2 authentication header from `Authorization: Bearer {token}` to `api-key: {token}` for Cisco Circuit API compatibility

#### Tool Schema Array Format for LLM Function Calling

- **Missing Items in Array Schema**: Fixed OpenAI 400 error "array schema missing items" when calling LLM with tool definitions
- **Tools-Provider Fix**: Updated `_simplify_schema()` in `openapi_source_adapter.py` to preserve `items` for array types
- **Agent-Host Fix**: Enhanced `ToolParameter` model with `items`, `properties`, `full_schema` fields and `to_json_schema()` method to properly format schemas for both Ollama and OpenAI models

#### Helper Method Signature Corrections

- Fixed incorrect `not_found()` helper method calls across multiple command handlers
- Changed from string-based error messages to proper `entity_type, entity_key` parameters
- Affected files: `update_source_command.py`, `delete_label_command.py`, `update_task_command.py`, `update_label_command.py`, `send_message_command.py`, `get_conversation_query.py`, `chat_controller.py`

#### Agent Host UI UX Improvements

- **Copy Button for User Messages**: Extended copy button (with markdown/text/html formats) to user messages, not just assistant messages. Styled with semi-transparent theme for blue message background.
- **Login Animation**: Added subtle pulse animation to "Login to start chatting" text with bouncing arrow icon to draw attention when not authenticated.
- **Health Check on Login**: Automatically runs health check after user authenticates and updates the health icon (heart) with status color: green (healthy), orange (degraded), red (unhealthy/error), with pulsing animation while checking.
- **Conversation Info Modal**: New info button on conversation items shows detailed statistics including message count (user/assistant breakdown), estimated token count, byte size, tool calls summary, tools used badges, and timestamps.
- **Pin Conversations**: Pin important conversations to keep them at the top of the sidebar. Pinned conversations show a pin indicator and are stored in localStorage.
- **Share Conversations**: New share button opens a modal with export options:
  - Copy as JSON (full conversation export)
  - Copy as Text (readable chat format)
  - Download JSON file
  - Note: Direct sharing with Realm users via unique URL planned for future release.

#### Cross-Entity Navigation in Admin UI

- **Modal Navigation Utility**: New `modal-utils.js` module with `navigateToModal()`, `closeModal()`, and `dispatchNavigationEvent()` functions for proper modal transitions
- **Clickable Tool Names**: Tool names in Group cards now link to Tool Details modal (navigates to Tools page and opens modal)
- **Source Cross-Reference**: Tool Details modal now shows clickable source name that navigates to Sources page
- **Tool Count Links**: Source Details modal now shows clickable tool count that filters Tools page by source
- **Group Links in Policies**: Policy view modal now shows clickable group badges that navigate to Groups page
- **Highlight Flash Animation**: Cards scroll into view and flash with highlight when navigated to via cross-reference
- **Consistent Tool Name Formatting**: Human-friendly tool names displayed everywhere using `getToolDisplayName()` utility

#### Flexible Tool Selection for Group Creation

- **Tool Selection Checkboxes**: Added checkboxes to filtered tools in both grid and table views
- **Auto-Select All**: Filtered tools are automatically selected when filters are applied
- **Selection Control**: Users can individually select/deselect tools before creating a group
- **Dynamic Button Label**: "Create Group" button shows count of selected tools (not just filtered)
- **Human-Friendly Tool Names**: Tool IDs are converted to readable names (e.g., "create_menu_item_api_menu_post" → "Create Menu Item")
- **Method Badges**: Tool list items show HTTP method badges (GET, POST, etc.)
- **Exclude Tool Button**: Remove tools from groups by adding to exclusions list
- **Add Tools Modal**: Full-featured modal with search and filters to add tools to existing groups
- **New Tool Utils Module**: `tool-utils.js` with `formatToolName()`, `getToolDisplayName()`, `getMethodClass()`, `inferMethodFromName()`

#### Tool Source Info Feature (Admin Only)

- **Source Info Tab**: Admin users can now view tool source details in the tool call modal
- **Lazy Loading**: Source info is fetched on-demand when the tab is clicked
- **API Endpoint**: `GET /api/tools/{tool_id}/source` returns upstream source details
- **Flexible Lookup**: Accepts both full tool_id (`source_id:operation_id`) or operation_id only

#### OpenAPI URL Separation

- **New Field**: `openapi_url` added to UpstreamSource aggregate for storing OpenAPI spec URL separately from base URL
- **Domain Events**: Updated `SourceRegisteredDomainEvent` with `openapi_url` field
- **Backward Compatible**: Falls back to `url` field if `openapi_url` not provided

#### Agent Chat UI Enhancements

- **Tool Call Header**: Messages now show "ChatBot tool call..." or "ChatBot called N tools..." above badges
- **Roles in /me Endpoint**: Auth endpoint now returns user roles for frontend admin checks
- **Tool Results**: API now includes `tool_results` in conversation messages response
- **No Duplicate Tool Cards**: Inline tool cards are removed after message completion to avoid duplication
- **Conversation Sidebar Auto-Update**: New conversations now appear in sidebar immediately when first message is sent (conversation_id included in stream_started SSE event)
- **Human-Friendly Tool Names**: Tool names in Available Tools modal and chat badges now display formatted names (e.g., "List Menu Items" instead of "list_menu_items_api_menu_get")
- **Locale-Aware Timestamps**: Message timestamps now use `Intl.RelativeTimeFormat` for proper localization (no external dependencies)

#### Documentation

- **Screenshot Gallery**: Added tabbed screenshot view to docs homepage

### Fixed

- **Tool Source Lookup**: Fixed 400 error when looking up tool source by operation_id only
- **Tool Call Display in Chat**: Removed inline tool-call-card components during streaming; tool results now only show as compact badges in assistant messages. Fixed tool call badges appearing as separate messages on conversation reload by merging tool_results from empty-content assistant messages into the subsequent content message.
- **Tool Enable/Disable**: Fixed HTTP 500 error when toggling tools - SourceToolDto is now built manually from aggregate state instead of using mapper (handles complex type conversions)
- **Missing Tool ID Handling**: Added error toast and console logging when attempting to toggle a tool with missing ID

### Fixed

#### Token Exchange Issuer Mismatch Resolution

- **Root Cause**: Token exchange failed with "Invalid token issuer" because browser-issued tokens had `iss=http://localhost:8041` but containers couldn't resolve `localhost` to the Docker host.
- **Solution**: Added `extra_hosts: localhost:host-gateway` to containers (app, pizzeria-backend, agent-host, event-player) enabling them to reach Keycloak at `localhost:8041`.
- **Configuration Alignment**: Unified all `KEYCLOAK_URL` and `KEYCLOAK_URL_INTERNAL` to use `http://localhost:8041` for consistent issuer across browser and container contexts.
- **Impact**: Enables RFC 8693 token exchange for secure identity delegation to upstream services (e.g., pizzeria-backend), foundational for AgenticConversation aggregate.

### Added

#### Token Exchange Troubleshooting Case Study

- **New Documentation**: `docs/troubleshooting/token-exchange-case-study.md` - Comprehensive troubleshooting guide covering three root cause categories:
  - Case Study 1: URL Confusion (External vs Internal Docker network URLs)
  - Case Study 2: Stale Keycloak Configuration (volume persistence prevents re-import)
  - Case Study 3: Missing Audience Mapper (subject token must include token exchange client in `aud` claim)
- **Diagnostic Checklist**: Step-by-step debugging guide for token exchange failures.
- **Historical Context**: Documents Keycloak version evolution (24 → 26+) for reference.

### Changed

#### Documentation Alignment with Keycloak 26+

- **`docs/specs/tools-provider.md`**: Updated docker-compose example to reflect current implementation:
  - Keycloak 24.0 → 26.4 with modern admin credentials (`KC_BOOTSTRAP_ADMIN_USERNAME`)
  - Removed obsolete `KC_FEATURES=token-exchange` (enabled by default in Keycloak 26+)
  - EventStoreDB 24.2 → KurrentDB 25.1.0 with `KURRENTDB_*` environment variables
- **`docs/specs/design-review.md`**: Complete rewrite of §11.6 Keycloak Token Exchange:
  - Added MkDocs admonition for Keycloak 26+ Standard Token Exchange V2
  - Replaced legacy V1 permission-based config with V2 attribute-based config
  - Added V1 vs V2 comparison table for migration reference
  - Updated realm export JSON examples with `standard.token.exchange.enabled` attribute

### Added

#### Circuit Breaker CloudEvents & Admin UI

- **Domain Events**: New CloudEvents for circuit breaker state transitions:
  - `circuit_breaker.opened.v1` - Emitted when circuit opens (failure threshold reached or test failed)
  - `circuit_breaker.closed.v1` - Emitted when circuit closes (auto-recovery or manual reset)
  - `circuit_breaker.half_opened.v1` - Emitted when circuit enters half-open testing state
- **Event Publisher**: `CircuitBreakerEventPublisher` service publishes state changes to CloudEventBus.
- **Event Tracking**: Events include `circuit_id`, `circuit_type`, `source_id`, reason for transition, and `closed_by` username for manual resets.
- **Admin UI Page**: New "Admin" page in web interface for circuit breaker management:
  - View all circuit breaker states (Keycloak token exchange + per-source tool execution)
  - Health status visualization with color-coded state badges
  - One-click reset buttons for open circuit breakers
  - Token exchange health check with endpoint and cache info
- **API Client**: New `admin.js` API module for circuit breaker operations.

#### Circuit Breaker Admin API

- **Admin Controller**: New `/api/admin` endpoints for circuit breaker monitoring and management.
  - `GET /api/admin/circuit-breakers` - View state of all circuit breakers (token exchange and per-source tool execution).
  - `POST /api/admin/circuit-breakers/reset` - Manually reset circuit breakers after resolving issues.
  - `GET /api/admin/health/token-exchange` - Token exchange service health check with circuit breaker state.
- **CircuitBreaker.reset()**: New async method to manually reset circuit breakers to closed state.
- **ToolExecutor**: Added `reset_circuit_breaker()` and `reset_all_circuit_breakers()` methods.

#### Makefile Maintenance Rules

- Added `make reset-keycloak-db` rule to reset Keycloak database and re-import realm from export files.
- Added `make redis-flush` rule to flush all Redis data (clears sessions, forces re-login).

#### Token Exchange & Audience Support (RFC 8693)

- **Domain Layer**: Added `default_audience` field to `UpstreamSourceState` and `SourceRegisteredDomainEvent` for token exchange targeting.
- **Application Layer**: `RegisterSourceCommand` and `RefreshInventoryCommand` now support `default_audience` parameter for audience-scoped token exchange.
- **Integration Layer**: `SourceDto` includes `default_audience` field for read model queries.
- **API Layer**: `RegisterSourceRequest` accepts `default_audience` to specify target Keycloak client for token exchange.
- **OpenAPI Adapter**: `fetch_and_normalize()` accepts `default_audience` and applies it to all parsed tools' execution profiles.

#### Keycloak 26 V2 Token Exchange Configuration

- **Client Scope**: Added `pizzeria-audience` client scope with audience mapper for `pizzeria-backend`.
- **V2 Attribute**: Changed from `oauth2.token.exchange.grant.enabled` (V1 legacy) to `standard.token.exchange.enabled` (V2 standard) on:
  - `tools-provider-token-exchange` client (requester)
  - `pizzeria-backend` client (audience target)
- **Audience Mappers**: Added `audience-token-exchange` mapper to `tools-provider-backend`, `tools-provider-public`, and `agent-host` clients (required for subject tokens to include requester client in `aud` claim).
- **Pizzeria Backend**: Configurable audience verification via `VERIFY_AUDIENCE` and `EXPECTED_AUDIENCE` environment variables.
- **Test Script**: Added `scripts/test_token_exchange.py` demonstrating complete RFC 8693 token exchange flow.

### Changed

- Updated `SourceAdapter` abstract base class signature to include `default_audience` parameter.
- Projection handler now persists `default_audience` to MongoDB read model.

### Documentation

- **New**: `docs/troubleshooting/circuit-breaker.md` - Comprehensive guide for understanding, monitoring, and resetting circuit breakers.
- Comprehensive rewrite of `docs/security/keycloak-token-exchange-setup.md` for Keycloak 26.x+:
  - Standard token exchange V2 is now enabled by default (no feature flags needed)
  - Fine-Grained Admin Permissions no longer required for internal token exchange
  - **New section on V2 client scope configuration** for audience availability
  - Step-by-step configuration with audience mappers
  - Troubleshooting guide for common token exchange errors
  - Security best practices for production deployments

### Fixed

- **Agent Host**: Added `roles` scope to OAuth2 login request (required for token exchange audience mapper).
- **Keycloak Realm Export**: Added built-in OIDC client scope definitions (`openid`, `profile`, `email`, `roles`, `offline_access`) and `defaultDefaultClientScopes` for proper realm import.

---

#### Pizzeria Backend (Sample Upstream Service)

- New `upstream-sample/` directory with complete FastAPI service demonstrating RBAC with Keycloak.
- JWT Bearer token validation using Keycloak JWKS with role-based endpoint authorization.
- Keycloak clients `pizzeria-public` and `pizzeria-backend` added to realm export.
- Full menu, orders, and kitchen API with role-mapped access (user→Customer, developer→Chef, manager→Manager).

#### Session Cookie Isolation (Multi-App SSO Fix)

- Configurable `session_cookie_name` setting in both Tools Provider and Agent Host.
- Prevents cross-app session collision when multiple apps share same domain (localhost).
- Tools Provider uses `tools_session`, Agent Host uses `agent_session` cookie.
- Updated `docker-compose.yml` with `SESSION_COOKIE_NAME` and `AGENT_HOST_SESSION_COOKIE_NAME` env vars.
- Comprehensive session management documentation in `docs/security/session-management.md`.

### Changed

- Refactored auth controllers and dependencies to use `Request.cookies.get()` instead of `Cookie()` parameter.
- Changed `REDIS_ENABLED` default from `false` to `true` in docker-compose (required for sessions).
- Upgraded `neuroglia-python` from `^0.7.6` to `^0.7.8`.

### Documentation

- Rewrote `docs/security/session-management.md` as critical architecture guide for multi-app deployments.
- Added Mermaid diagram showing Redis database allocation and cookie isolation.
- Added troubleshooting guide for common session issues.
- Added `notes/NEUROGLIA_DECIMAL_HEURISTIC_BUG.md` documenting JSON deserializer issue.

---

#### Phase 4: Access Control & SSE (AccessPolicy Aggregate)

- **Domain Layer**: New `AccessPolicy` aggregate with `AccessPolicyState` for claims-based access control.
  - 8 domain events with `@cloudevent` decorators: Defined, Updated, MatchersUpdated, GroupsUpdated, PriorityUpdated, Activated, Deactivated, Deleted.
  - Repository interface: `AccessPolicyDtoRepository` with specialized query methods.
- **Application Layer**: Complete CQRS implementation with 5 command handlers and 2 query handlers.
  - Commands: DefineAccessPolicy, UpdateAccessPolicy, ActivateAccessPolicy, DeactivateAccessPolicy, DeleteAccessPolicy.
  - Queries: GetAccessPolicies (with filters), GetAgentTools (resolves tools for authenticated agent).
  - `AccessResolver` service for JWT claims evaluation against policies with Redis caching.
  - 9 projection handlers for read model synchronization.
- **Integration Layer**: `AccessPolicyDto` and `AccessPolicySummaryDto` with `@queryable` decorator and Motor repository.
- **API Layer**:
  - `PoliciesController` with admin CRUD endpoints at `/api/policies`.
  - `AgentController` with SSE endpoint at `/api/agent/sse` for real-time tool discovery.
  - REST endpoint at `/api/agent/tools` for one-time tool list retrieval.

#### Phase 3: Tool Curation & Grouping (ToolGroup Aggregate)

- **Domain Layer**: New `ToolGroup` aggregate with `ToolGroupState` for tool curation and grouping.
  - `ToolSelector` value object with pattern matching (source, name, path patterns) and tag filtering.
  - Domain events: Created, Updated, Deleted, Activated, Deactivated, SelectorAdded, SelectorRemoved, ToolAdded, ToolRemoved, ToolExcluded, ToolIncluded (all with `@cloudevent` decorators).
  - Repository interfaces: `ToolGroupRepository`, `ToolGroupReadRepository`.
- **Application Layer**: Complete CQRS implementation with 11 command handlers and 3 query handlers.
  - Commands: CreateToolGroup, UpdateToolGroup, DeleteToolGroup, ActivateToolGroup, DeactivateToolGroup, AddToolSelector, RemoveToolSelector, AddToolToGroup, RemoveToolFromGroup, ExcludeToolFromGroup, IncludeToolInGroup.
  - Queries: GetToolGroups (paginated), GetToolGroupById, GetGroupTools (with tool resolution).
  - Projection handlers for read model synchronization.
- **Integration Layer**: `ToolGroupDto` with `@queryable` decorator and Motor repository implementation.
- **API Layer**: `ToolGroupsController` with full REST endpoints at `/api/tool-groups`.
- **Testing**: 43 unit tests covering ToolGroup entity behavior, state transitions, and domain events.

#### Observability

- Comprehensive OpenTelemetry instrumentation for all ToolGroup command and query handlers.
  - Tracing: Span attributes for group IDs, names, statuses, and operation results.
  - Metrics: 12 new counters and 2 histograms for tool group operations.
- Extended `src/observability/metrics.py` with metrics for Sources, SourceTools, and ToolGroups.
- **Phase 4 Metrics**: Added 12 new metrics for AccessPolicy and agent access resolution:
  - AccessPolicy counters: `access_policies.defined`, `access_policies.updated`, `access_policies.deleted`, `access_policies.activated`, `access_policies.deactivated`.
  - AccessPolicy histogram: `access_policy.processing_time`.
  - Agent resolution counters: `agent.access_resolutions`, `agent.access_cache_hits`, `agent.access_cache_misses`, `agent.tools_resolved`, `agent.access_denied`.
  - Agent resolution histogram: `agent.resolution_time`.
- Instrumented all Phase 4 command handlers with metrics recording.
- Instrumented `GetAgentToolsQuery` and `AccessResolver` with cache hit/miss and resolution metrics.

### Changed

#### Backend

- Refactored authentication middleware configuration by moving detailed setup code from `main.py` to `DualAuthService.configure_middleware()` helper method for better separation of concerns and maintainability.
- Updated import statements formatting for improved code readability (multi-line imports consolidated).
- Refactored ToolGroup commands from single file into 11 separate files following one-command-per-file pattern.

#### Dependencies

- Updated `neuroglia-python` from 0.6.6 to 0.6.7.

### Fixed

- Fixed dependency injection for authentication middleware to properly resolve service provider.
- Fixed configuration issues in CI workflow for Git LFS checkout to ensure GitHub Pages deployment includes LFS assets.
- Fixed Bandit security scanner configuration to skip test directories and B101 (assert_used) check, eliminating 155 false positive warnings.
- Fixed `CleanupOrphanedToolsCommandHandler` to always delete from read model (MongoDB) regardless of write model (KurrentDB) result, resolving issue where orphaned tools showed `tools_deleted: 0`.

---

## [0.1.0] - 2025-11-11

### Added

#### Testing Infrastructure

- Comprehensive test suite with 60 tests achieving 98% coverage across domain, infrastructure, and application layers.
- pytest.ini configuration with custom markers (unit, integration, asyncio, auth, repository, command, query, slow, smoke).
- Test fixtures package with factories for Task, Token, and Session data generation.
- Test mixins providing reusable patterns: AsyncTestMixin, AssertionMixin, MockHelperMixin, SessionTestMixin.
- Domain layer tests (18 tests) validating Task entity behavior and domain events.
- Infrastructure tests (11 tests) for InMemorySessionStore and RedisSessionStore.
- Application layer tests (31 tests) for command handlers (create, update, delete) and query handlers (get tasks, get by id).
- Testing documentation at `docs/development/testing.md` with examples and best practices.

#### Documentation

- Security section (renamed from Authentication) with comprehensive authorization guide covering OAuth2/OIDC, BFF pattern, and RBAC.
- Observability documentation split into 8 focused documents:
  - Overview: High-level introduction and navigation hub (234 lines).
  - Architecture: Technical components, data flow, and diagrams (300 lines).
  - Getting Started: Quick start guide with 4 complete workflows (379 lines).
  - Configuration: Environment variables, OTEL Collector, and backend setup (489 lines).
  - Best Practices: Naming conventions, cardinality control, sampling strategies (558 lines).
  - Troubleshooting: Common issues and solutions with diagnosis steps (616 lines).
  - Metrics Instrumentation: Complete guide to all metric types with real code examples (918 lines).
  - Tracing Instrumentation: Distributed tracing patterns and context propagation (997 lines).
- GitHub Pages setup documentation for MkDocs deployment.
- Makefile reference guide.

#### Frontend Components

- Modular UI component structure in `src/ui/src/scripts/components/`:
  - `dashboard.js`: Task loading, CRUD operations, and workflow orchestration.
  - `modals.js`: Alert, confirm, and toast notification utilities.
  - `permissions.js`: Role-based access control helpers.
  - `task-card.js`: Card rendering with markdown support and collapsible behavior.
- Component-specific SCSS stylesheets in `src/ui/src/styles/components/`.
- Reusable Jinja2 template components in `src/ui/src/templates/components/`.
- Task editing UI with role-based field permissions:
  - Regular users: Edit title, description, status, priority.
  - Managers: Additional assignee assignment capability.
  - Admins: Full access including department field.
- Edit modal with markdown-enabled textarea and success toast notifications.
- Task card collapsible interface with toggle behavior and markdown rendering.
- Task card action icons (edit, info, delete) with Bootstrap tooltips.

#### Configuration

- `.vscode/copilot-context.md` instructions to guide AI agents on backend, frontend, documentation, and git practices.

### Changed

#### Backend

- Task entity methods updated to use aggregate root pattern instead of direct state manipulation.
- UpdateTaskCommand now properly emits domain events through aggregate methods.
- Task entity removed attribute delegation for cleaner separation of concerns.
- Department field support added to update command and API controllers.

#### Frontend

- UI codebase reorganized into modular component structure.
- Task cards now display assignee and department information.
- Improved card layout with proper collapsed/expanded states.
- Enhanced modal dialogs with scrollable content and better form visibility.

#### Documentation

- Authentication section renamed to Security for broader scope.
- Authorization Code Flow diagram corrected to show Backend-for-Frontend (BFF) pattern.
- Observability documentation backend tools updated from Jaeger to Tempo and Console Exporter to Prometheus.
- MkDocs navigation restructured with 8 organized observability entries.

#### Configuration

- Disabled automatic YAML formatting in the workspace to respect yamllint comment-spacing requirements.
- Increased the yamllint line-length limit to 250 characters to accommodate long Docker Compose entries.

### Fixed

- Task card toggle behavior now correctly uses `.task-header` class for header selection.
- Edit modal properly pre-fills all task fields including assignee and department.
- Role-based field visibility in edit modal working correctly (assignee for managers+, department for admins only).
- Domain events now properly emitted for all task updates.

### Security

- Uvicorn now binds to `127.0.0.1` by default; override via `APP_HOST` when exposing the service deliberately.
- RBAC enforcement in update command handler: users can only edit their own tasks, admins can edit any task.
- Permission checks in UI: edit/delete buttons only shown to authorized users.


---

## [0.1.0] - 2025-11-07

### Added

- Multi sub-app FastAPI architecture (API at `/api`, UI root) using Neuroglia patterns.
- OAuth2/OIDC integration with Keycloak (Authorization Code flow) and refresh endpoint `/api/auth/refresh`.
- RS256 JWT verification via JWKS with issuer and audience validation.
- Dual security schemes (OAuth2 Authorization Code + HTTP Bearer) in OpenAPI spec.
- Auto-refresh logic for access tokens with leeway configuration.
- Explicit expired token handling returning `401` with `WWW-Authenticate` header.
- Redis session store option (configurable backend) plus in-memory fallback.
- CQRS layer: commands (`create_task`, `update_task`), queries (`get_tasks`) and RBAC enforcement handlers.
- Observability metrics scaffold (`observability/metrics.py`).
- Project rename script `scripts/rename_project.py` supporting variant styles & dry-run.
- Rebranding documentation (README section) and rename integrity test.
- CONTRIBUTING guide with DCO sign-off instructions.
- Pull request template enforcing checklist & DCO sign-off.
- Apache 2.0 License adoption and README license section.

### Changed

- OpenAPI configuration upgraded to correctly apply security schemes to protected endpoints.
- README expanded with detailed project structure and template usage guidance.

### Fixed

- Missing Authorization header in Swagger UI by correcting scheme definitions.
- Legacy HS256 secret decoding replaced with proper RS256 JWKS verification.
- Markdown formatting issues in README and CONTRIBUTING (lists & fenced block spacing).

### Security

- Migration from HS256 static secret to RS256 with remote JWKS caching.
- Added issuer/audience claim validation toggles.
- Improved expired token feedback via standards-compliant `WWW-Authenticate` header.

### Removed

- Deprecated reliance on `JWT_SECRET_KEY` for RS256 tokens (retained only as legacy fallback context).

---

[0.1.0]: https://github.com/your-org/your-repo/releases/tag/v0.1.0
