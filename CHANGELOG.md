# Changelog

All notable changes to this project will be documented in this file.

The format follows the recommendations of Keep a Changelog (https://keepachangelog.com) and the project aims to follow Semantic Versioning (https://semver.org).

## [Unreleased]

### Added

#### Implementation Documentation

- **Implementation Guide**: New `docs/implementation/` section documenting end-to-end data flows
- **Source Registration**: Detailed documentation of RegisterSourceCommand and projection handlers
- **Tool Discovery**: RefreshInventoryCommand flow with adapter architecture
- **Groups & Policies**: ToolGroup/AccessPolicy with correct AND/OR logic documentation
- **Agent Tools Query**: GetAgentToolsQuery resolution flow with caching strategy
- **Tool Execution**: ToolExecutor with token exchange, templates, and circuit breakers
- **MkDocs Navigation**: Added Implementation section to mkdocs.yml navigation

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
