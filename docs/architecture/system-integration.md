# System Integration & Architecture

This document provides a comprehensive overview of the MCP Tools Provider ecosystem, including all Docker services, the Agent Host integration, identity propagation, and future extension points.

## Table of Contents

1. [Infrastructure Services](#infrastructure-services)
2. [Tools Provider Runtime](#tools-provider-runtime)
3. [Tools Provider Provisioning](#tools-provider-provisioning)
4. [Agent Host Architecture](#agent-host-architecture)
5. [Identity Propagation](#identity-propagation)
6. [MCP Protocol Emulation](#mcp-protocol-emulation)
7. [Future Extensions](#future-extensions)

---

## Infrastructure Services

The Docker Compose orchestrates a complete development environment with 12 services working together:

```mermaid
flowchart TB
    subgraph User["End Users"]
        Browser["Browser"]
        APIClient["API Client"]
    end

    subgraph Frontend["Frontend Layer"]
        AgentUI["Agent Host UI<br/>:8050"]
        AdminUI["Tools Provider UI<br/>:8040"]
    end

    subgraph Application["Application Layer"]
        AgentHost["Agent Host<br/>(BFF + ReAct Agent)"]
        ToolsProvider["Tools Provider<br/>(Tool Registry + Proxy)"]
    end

    subgraph LLM["LLM Layer"]
        Ollama["Ollama<br/>:11434<br/>(llama3.2:3b)"]
    end

    subgraph Identity["Identity Layer"]
        Keycloak["Keycloak<br/>:8041<br/>(OAuth2/OIDC)"]
    end

    subgraph Persistence["Persistence Layer"]
        KurrentDB["KurrentDB<br/>:2113<br/>(Write Model)"]
        MongoDB["MongoDB<br/>:27017<br/>(Read Model)"]
        Redis["Redis<br/>:6379<br/>(Sessions/Cache)"]
    end

    subgraph Observability["Observability Layer"]
        EventPlayer["Event Player<br/>:8046"]
        OTELCollector["OTEL Collector<br/>:4317"]
    end

    subgraph Upstream["Upstream Services"]
        OpenAPI["OpenAPI Services"]
        Workflow["Workflow Engines"]
    end

    Browser --> AgentUI
    Browser --> AdminUI
    APIClient --> AgentHost
    APIClient --> ToolsProvider

    AgentUI --> AgentHost
    AdminUI --> ToolsProvider

    AgentHost --> ToolsProvider
    AgentHost --> Ollama
    AgentHost --> Keycloak
    AgentHost --> Redis
    AgentHost --> MongoDB

    ToolsProvider --> Keycloak
    ToolsProvider --> KurrentDB
    ToolsProvider --> MongoDB
    ToolsProvider --> Redis
    ToolsProvider --> Upstream

    ToolsProvider --> EventPlayer
    AgentHost --> OTELCollector
    ToolsProvider --> OTELCollector
```

### Service Inventory

| Service | Port | Purpose | Technology |
|---------|------|---------|------------|
| **Tools Provider** | 8040 | Tool registry, access control, execution proxy | FastAPI + Neuroglia |
| **Agent Host** | 8050 | Chat UI, ReAct agent, conversation management | FastAPI + Ollama |
| **Keycloak** | 8041 | OAuth2/OIDC identity provider, token exchange | Keycloak 26.x |
| **KurrentDB** | 2113 | Event store (write model) | KurrentDB 25.x |
| **MongoDB** | 27017 | Read model projections, conversations | MongoDB 6.0 |
| **Mongo Express** | 8044 | MongoDB admin UI | Mongo Express |
| **Redis** | 6379 | Sessions (DB 0), cache (DB 1), agent sessions (DB 2) | Redis 7 |
| **Redis Commander** | 8045 | Redis admin UI | Redis Commander |
| **Event Player** | 8046 | CloudEvent visualization and replay | Custom Go service |
| **OTEL Collector** | 4317/4318 | Telemetry ingestion (traces, metrics) | OpenTelemetry Collector |
| **UI Builder** | - | Parcel watch mode for both UIs | Node.js 20 |
| **Ollama** | 11434 | Local LLM inference (optional in Docker) | Ollama |

### Redis Database Allocation

```
DB 0: Tools Provider sessions (session cookies, OIDC state)
DB 1: Tools Provider cache (tool definitions, token exchange results)
DB 2: Agent Host sessions (conversation context, rate limiting)
```

---

## Tools Provider Runtime

At runtime, the Tools Provider acts as a **secure proxy** between AI agents and upstream services, enforcing access control and propagating identity.

### Runtime Flow: Agent Tool Discovery & Execution

```mermaid
sequenceDiagram
    autonumber
    participant User as End User
    participant Agent as Agent Host
    participant TP as Tools Provider
    participant AR as Access Resolver
    participant Cache as Redis Cache
    participant KC as Keycloak
    participant US as Upstream Service

    Note over User,US: Tool Discovery
    User->>Agent: "What can you do?"
    Agent->>TP: GET /api/agent/tools<br/>Authorization: Bearer {user_jwt}
    TP->>TP: Validate JWT (RS256)
    TP->>AR: resolve_agent_access(claims)
    AR->>Cache: Check cached access
    alt Cache Hit
        Cache-->>AR: allowed_group_ids
    else Cache Miss
        AR->>AR: Evaluate AccessPolicies
        AR->>Cache: Cache result (5 min TTL)
    end
    AR-->>TP: Set[group_ids]
    TP->>TP: Resolve tools from groups
    TP-->>Agent: List[ToolManifest]
    Agent-->>User: "I can search orders, check inventory..."

    Note over User,US: Tool Execution
    User->>Agent: "Search for order #12345"
    Agent->>Agent: LLM decides to call search_orders
    Agent->>TP: POST /api/agent/tools/call<br/>{name: "search_orders", arguments: {...}}
    TP->>TP: Validate access to tool
    TP->>TP: Validate arguments (JSON Schema)

    Note over TP,KC: Token Exchange (RFC 8693)
    TP->>KC: POST /token<br/>grant_type=token-exchange<br/>subject_token={user_jwt}<br/>audience={upstream_client_id}
    KC-->>TP: {access_token: upstream_token}

    TP->>US: GET /api/orders/12345<br/>Authorization: Bearer {upstream_token}
    US-->>TP: Order details
    TP-->>Agent: Tool result
    Agent->>Agent: LLM formats response
    Agent-->>User: "Order #12345 is shipped..."
```

### Key Runtime Components

#### 1. Agent Controller (`/api/agent/*`)

```python
# src/api/controllers/agent_controller.py
class AgentController(ControllerBase):
    """REST API for Host Applications (Agent Host)."""

    @get("/tools")
    async def get_tools(self, user: dict = Depends(get_current_user)):
        """Get tools accessible to this user based on JWT claims."""
        query = GetAgentToolsQuery(claims=user)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @post("/tools/call")
    async def execute_tool(self, request: ToolCallRequest, user: dict = Depends(get_current_user)):
        """Execute a tool with identity delegation via token exchange."""
        command = ExecuteToolCommand(
            tool_id=request.get_tool_id(),
            arguments=request.arguments,
            claims=user,
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)
```

#### 2. Access Resolver

Evaluates JWT claims against AccessPolicies to determine allowed ToolGroups:

```python
# src/application/services/access_resolver.py
class AccessResolver:
    """Resolves agent access rights based on JWT claims."""

    async def resolve_agent_access(self, claims: Dict[str, Any]) -> Set[str]:
        """
        1. Hash claims for cache key
        2. Check Redis cache
        3. Evaluate all active AccessPolicies
        4. Return union of allowed group IDs
        """
        cache_key = f"access:{self._hash_claims(claims)}"

        # Check cache first
        cached = await self._cache.get(cache_key)
        if cached:
            return set(json.loads(cached))

        # Evaluate policies (OR logic between policies)
        allowed_groups = await self._evaluate_policies(claims)

        # Cache result
        await self._cache.setex(cache_key, self.DEFAULT_CACHE_TTL, json.dumps(list(allowed_groups)))
        return allowed_groups
```

#### 3. Tool Executor

Proxies tool execution with token exchange and circuit breaker protection:

```python
# src/application/services/tool_executor.py
class ToolExecutor:
    """Executes tools by proxying requests to upstream services."""

    async def execute(self, tool_id: str, definition: ToolDefinition,
                      arguments: Dict, agent_token: str) -> ToolExecutionResult:
        """
        1. Validate arguments against JSON Schema
        2. Exchange agent token for upstream token
        3. Render Jinja2 templates (URL, headers, body)
        4. Execute HTTP request with circuit breaker
        5. Return result
        """
        # Token exchange
        upstream_token = await self._token_exchanger.exchange(
            subject_token=agent_token,
            audience=definition.execution_profile.audience,
        )

        # Execute with circuit breaker
        circuit = self._get_circuit(definition.source_id)
        result = await circuit.call(self._http_execute, definition, arguments, upstream_token)
        return result
```

---

## Tools Provider Provisioning

Provisioning is the administrative process of configuring what tools are available and who can access them.

### Provisioning Workflow

```mermaid
flowchart TB
    subgraph Admin["Admin Actions"]
        A1["1. Register Upstream Source"]
        A2["2. Refresh Inventory"]
        A3["3. Create Tool Groups"]
        A4["4. Define Access Policies"]
    end

    subgraph Source["Upstream Source"]
        S1["OpenAPI Spec"]
        S2["Discovered Tools"]
    end

    subgraph Groups["Tool Groups"]
        G1["Selectors<br/>(pattern matching)"]
        G2["Explicit Tools"]
        G3["Excluded Tools"]
    end

    subgraph Policies["Access Policies"]
        P1["ClaimMatchers<br/>(JWT rules)"]
        P2["Allowed Groups"]
    end

    A1 --> S1
    S1 --> A2
    A2 --> S2

    S2 --> A3
    A3 --> G1
    A3 --> G2
    A3 --> G3

    G1 --> A4
    G2 --> A4
    G3 --> A4
    A4 --> P1
    A4 --> P2
```

### 1. Registering Upstream Sources

An upstream source represents an external service (OpenAPI or Workflow) that provides tools:

```bash
# Register an OpenAPI source
POST /api/sources
{
  "name": "Order Management API",
  "url": "https://orders.example.com/openapi.json",
  "source_type": "OPENAPI",
  "auth_config": {
    "type": "oauth2_client_credentials",
    "client_id": "orders-api-client",
    "token_endpoint": "https://auth.example.com/token"
  }
}
```

**Domain Events Emitted:**

- `source.registered.v1` - Source created
- `source.inventory.ingested.v1` - Tools discovered after sync

### 2. Tool Discovery & Labeling

When an upstream source is synced, tools are automatically discovered from the OpenAPI spec:

```mermaid
flowchart LR
    subgraph Sync["Inventory Sync"]
        SPEC["OpenAPI Spec"] --> PARSE["Parse Operations"]
        PARSE --> TOOLS["Tool Definitions"]
    end

    subgraph Tool["Per-Tool Data"]
        NAME["name: searchOrders"]
        DESC["description: Search orders..."]
        SCHEMA["input_schema: {type: object...}"]
        EXEC["execution_profile: {method, url_template}"]
    end

    TOOLS --> NAME
    TOOLS --> DESC
    TOOLS --> SCHEMA
    TOOLS --> EXEC
```

**Tool Definition Structure:**

```python
@dataclass
class ToolDefinition:
    """A tool discovered from an upstream source."""
    id: str                        # {source_id}:{operation_id}
    name: str                      # e.g., "searchOrders"
    description: str               # From OpenAPI operation
    input_schema: Dict[str, Any]   # JSON Schema for arguments
    execution_profile: ExecutionProfile
    tags: List[str]                # For grouping/filtering
    is_enabled: bool               # Admin toggle
```

### 3. Creating Tool Groups

Tool Groups are curated collections of tools for access control:

```bash
# Create a Tool Group with selectors
POST /api/groups
{
  "name": "Finance Tools",
  "description": "Tools for finance team",
  "selectors": [
    {
      "source_pattern": "orders-*",
      "name_pattern": "*Order*",
      "required_tags": ["finance"]
    }
  ],
  "explicit_tool_ids": ["invoices:createInvoice"],
  "excluded_tool_ids": ["orders:deleteOrder"]
}
```

**Selector Logic:**

- Selectors use glob patterns (`*`, `?`)
- Multiple selectors = OR logic
- Explicit tools are always included
- Excluded tools are always removed

### 4. Defining Access Policies

Access Policies map JWT claims to allowed Tool Groups:

```bash
# Create an Access Policy
POST /api/policies
{
  "name": "Finance Team Access",
  "description": "Grant finance tools to finance department",
  "claim_matchers": [
    {
      "json_path": "realm_access.roles",
      "operator": "CONTAINS",
      "value": "finance_user"
    },
    {
      "json_path": "department",
      "operator": "EQUALS",
      "value": "finance"
    }
  ],
  "allowed_group_ids": ["finance-tools", "reporting-tools"],
  "priority": 100
}
```

**ClaimMatcher Operators:**

| Operator | Description | Example |
|----------|-------------|---------|
| `EQUALS` | Exact match | `department == "finance"` |
| `CONTAINS` | Array contains value | `roles.contains("admin")` |
| `MATCHES` | Regex match | `email.matches(".*@corp.com")` |
| `NOT_EQUALS` | Negation | `status != "suspended"` |
| `NOT_CONTAINS` | Array excludes | `!roles.contains("guest")` |

**Evaluation Logic:**

- Within a policy: ClaimMatchers use **AND** logic (all must match)
- Between policies: Use **OR** logic (any matching policy grants access)
- Higher priority policies are evaluated first

---

## Agent Host Architecture

The Agent Host is a **Backend-for-Frontend (BFF)** that provides a chat interface with tool-calling capabilities.

### Component Architecture

```mermaid
flowchart TB
    subgraph Browser["Browser"]
        ChatUI["Chat UI<br/>(WebComponents)"]
    end

    subgraph AgentHost["Agent Host"]
        subgraph API["API Layer"]
            AuthC["Auth Controller<br/>/auth/*"]
            ChatC["Chat Controller<br/>/chat/*"]
        end

        subgraph Services["Service Layer"]
            ChatSvc["ChatService"]
            TPClient["ToolProviderClient"]
        end

        subgraph Agent["Agent Layer"]
            ReAct["ReActAgent"]
            LLMProv["LlmProvider<br/>(Ollama)"]
        end

        subgraph Domain["Domain Layer"]
            Conv["Conversation<br/>(Aggregate)"]
            Msg["Messages"]
        end
    end

    subgraph External["External Services"]
        Ollama["Ollama LLM"]
        TP["Tools Provider"]
        KC["Keycloak"]
    end

    ChatUI --> AuthC
    ChatUI --> ChatC
    AuthC --> KC
    ChatC --> ChatSvc
    ChatSvc --> ReAct
    ChatSvc --> TPClient
    ChatSvc --> Conv
    ReAct --> LLMProv
    LLMProv --> Ollama
    TPClient --> TP
```

### ReAct Agent Pattern

The Agent Host implements the **ReAct** (Reasoning + Acting) pattern:

```mermaid
stateDiagram-v2
    [*] --> Observe: User message
    Observe --> Think: Build context
    Think --> Decide: LLM generates response

    Decide --> Act: Tool call requested
    Decide --> Respond: No tool calls

    Act --> Observe: Tool result
    Respond --> [*]: Stream response

    state Think {
        [*] --> BuildPrompt
        BuildPrompt --> CallLLM
        CallLLM --> ParseResponse
    }

    state Act {
        [*] --> ExecuteTool
        ExecuteTool --> AddResult
        AddResult --> [*]
    }
```

**ReAct Loop Implementation:**

```python
# agent-host/src/application/agents/react_agent.py
class ReActAgent(Agent):
    async def run_stream(self, context: AgentRunContext) -> AsyncIterator[AgentEvent]:
        messages = self._build_messages(context)

        for iteration in range(self._config.max_iterations):
            # Think: Call LLM
            response = await self._llm.chat(messages, tools=context.tools)

            # Decide: Check for tool calls
            if not response.has_tool_calls:
                # Respond: Yield final response
                yield AgentEvent(type=AgentEventType.RUN_COMPLETED, data={"response": response.content})
                return

            # Act: Execute tool calls
            for tool_call in response.tool_calls:
                result = await context.tool_executor(ToolExecutionRequest(
                    tool_name=tool_call.name,
                    arguments=tool_call.arguments,
                ))
                messages.append(result.to_llm_message())

            # Loop back to Observe with new context
```

### Chat Service Flow

```python
# agent-host/src/application/services/chat_service.py
class ChatService:
    async def send_message(self, conversation: Conversation,
                           user_message: str, access_token: str) -> AsyncIterator[dict]:
        # 1. Add user message to conversation aggregate
        conversation.add_user_message(user_message)
        await self._conversation_repo.update_async(conversation)

        # 2. Get available tools from Tools Provider
        tools = await self._tool_provider.get_tools(access_token)

        # 3. Build agent context
        run_context = AgentRunContext(
            user_message=user_message,
            conversation_history=conversation.get_context_messages(),
            tools=[self._tool_to_llm_definition(t) for t in tools],
            tool_executor=lambda req: self._execute_tool(req, access_token),
        )

        # 4. Stream agent events to client
        async for event in self._agent.run_stream(run_context):
            yield self._translate_event(event)

        # 5. Persist final state
        await self._conversation_repo.update_async(conversation)
```

---

## Identity Propagation

Identity propagation ensures that **end-user identity flows through the entire system**, enabling fine-grained access control at every layer.

### Why Identity Propagation Matters

```mermaid
flowchart LR
    subgraph Problem["Without Identity Propagation"]
        U1["User A"] --> Agent1["Agent"]
        U2["User B"] --> Agent1
        Agent1 --> |"Service Account"| API1["Upstream API"]
        API1 --> |"❌ Who called?"| Audit1["Audit Log"]
    end
```

```mermaid
flowchart LR
    subgraph Solution["With Identity Propagation"]
        U3["User A"] --> Agent2["Agent"]
        U4["User B"] --> Agent2
        Agent2 --> |"User A's Token"| API2["Upstream API"]
        Agent2 --> |"User B's Token"| API2
        API2 --> |"✅ User A called"| Audit2["Audit Log"]
    end
```

### Token Exchange Flow (RFC 8693)

```mermaid
sequenceDiagram
    autonumber
    participant User as End User
    participant Agent as Agent Host
    participant TP as Tools Provider
    participant KC as Keycloak
    participant US as Upstream Service

    Note over User,Agent: User authenticates
    User->>KC: Login (username/password)
    KC-->>User: user_jwt (aud: agent-host)

    Note over Agent,TP: Agent calls Tools Provider
    Agent->>TP: POST /api/agent/tools/call<br/>Authorization: Bearer {user_jwt}

    Note over TP,KC: Token Exchange
    TP->>KC: POST /realms/{realm}/protocol/openid-connect/token
    Note right of TP: grant_type: urn:ietf:params:oauth:grant-type:token-exchange<br/>subject_token: {user_jwt}<br/>audience: upstream-service-client<br/>requested_token_type: access_token
    KC->>KC: Validate subject_token
    KC->>KC: Check exchange permissions
    KC->>KC: Generate new token for audience
    KC-->>TP: upstream_jwt (aud: upstream-service, sub: user_id)

    Note over TP,US: Call upstream with exchanged token
    TP->>US: GET /api/resource<br/>Authorization: Bearer {upstream_jwt}
    US->>US: Validate JWT
    US->>US: Check user permissions
    US-->>TP: Resource data
    TP-->>Agent: Tool result
```

### Keycloak Token Exchange Configuration

```python
# src/infrastructure/adapters/keycloak_token_exchanger.py
class KeycloakTokenExchanger:
    """Implements RFC 8693 Token Exchange with caching and circuit breaker."""

    async def exchange(self, subject_token: str, audience: str) -> TokenExchangeResult:
        """
        Exchange an agent's access token for an upstream service token.

        Args:
            subject_token: The end-user's JWT from the agent
            audience: The Keycloak client ID of the upstream service

        Returns:
            TokenExchangeResult with the new access token
        """
        # Check cache first (key: hash of subject_token + audience)
        cache_key = self._cache_key(subject_token, audience)
        cached = await self._cache.get(cache_key)
        if cached and not cached.is_expired():
            return cached

        # Perform token exchange
        response = await self._http_client.post(
            f"{self._keycloak_url}/realms/{self._realm}/protocol/openid-connect/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "subject_token": subject_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "audience": audience,
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
            },
        )

        result = TokenExchangeResult(
            access_token=response["access_token"],
            expires_in=response["expires_in"],
        )

        # Cache with TTL buffer
        await self._cache.setex(cache_key, result.expires_in - 60, result)
        return result
```

### Benefits of Identity Propagation

| Benefit | Description |
|---------|-------------|
| **Audit Trail** | Upstream services log actual user identity |
| **Fine-grained Access** | Upstream can apply user-specific permissions |
| **Compliance** | Meets regulatory requirements (SOC2, GDPR) |
| **Least Privilege** | Tokens scoped to specific services |
| **Revocation** | Revoking user access affects all downstream calls |

---

## MCP Protocol Emulation

The Tools Provider does **NOT** implement the standard MCP (Model Context Protocol) specification. Instead, it provides an "MCP-like" API optimized for multi-tenant, secure environments.

### Why Not Standard MCP?

```mermaid
flowchart TB
    subgraph StandardMCP["Standard MCP"]
        MCP1["MCP Server"]
        Claude["Claude Desktop"]
        VSCode["VS Code"]
        MCP1 --- Claude
        MCP1 --- VSCode
        Note1["❌ No user identity<br/>❌ Service account only<br/>❌ No access control"]
    end

    subgraph OurApproach["Our Approach"]
        TP["Tools Provider"]
        AgentHost["Agent Host"]
        User["End User JWT"]
        TP --- AgentHost
        AgentHost --- User
        Note2["✅ User identity propagated<br/>✅ Per-user access control<br/>✅ Token exchange"]
    end
```

### Key Differences

| Aspect | Standard MCP | Our Implementation |
|--------|--------------|-------------------|
| **Authentication** | None / API key | JWT Bearer token (user identity) |
| **Authorization** | Server-wide | Per-user via AccessPolicies |
| **Tool Discovery** | Static list | Dynamic per-user based on claims |
| **Tool Execution** | Direct call | Proxied with token exchange |
| **Multi-tenancy** | Not supported | First-class support |

### How LLM Sees Our Tools

The Agent Host translates our tool manifests into the LLM's expected format:

```python
# agent-host/src/application/services/chat_service.py
def _tool_to_llm_definition(self, tool: Tool) -> LlmToolDefinition:
    """Convert our tool format to Ollama/OpenAI function format."""
    return LlmToolDefinition(
        name=tool.name,
        description=tool.description,
        parameters={
            "type": "object",
            "properties": {p.name: p.schema for p in tool.parameters},
            "required": [p.name for p in tool.parameters if p.required],
        },
    )
```

**Ollama API Format:**

```json
{
  "model": "llama3.2:3b",
  "messages": [...],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "searchOrders",
        "description": "Search orders by customer or date",
        "parameters": {
          "type": "object",
          "properties": {
            "customer_id": {"type": "string"},
            "from_date": {"type": "string", "format": "date"}
          },
          "required": ["customer_id"]
        }
      }
    }
  ]
}
```

The LLM doesn't know or care that:

1. Tools are fetched dynamically per-user
2. Tool execution goes through a proxy
3. Tokens are exchanged for upstream access

---

## Future Extensions

The architecture supports several planned extensions:

### 1. Multiple LLM Backends

```mermaid
flowchart TB
    subgraph LLMProviders["LLM Provider Interface"]
        Interface["LlmProvider<br/>(Abstract)"]
        Ollama["OllamaLlmProvider"]
        OpenAI["OpenAiLlmProvider"]
        Azure["AzureLlmProvider"]
        Anthropic["AnthropicLlmProvider"]
    end

    Interface --> Ollama
    Interface --> OpenAI
    Interface --> Azure
    Interface --> Anthropic

    subgraph Config["Per-User Configuration"]
        Claims["JWT Claims"]
        Settings["User Preferences"]
    end

    Config --> |"Select Provider"| Interface
```

**Implementation Path:**

- Abstract `LlmProvider` interface already exists
- Add `OpenAiLlmProvider`, `AzureLlmProvider`
- Configure per-user via JWT claims or preferences

### 2. Multiple System Prompts (RBAC)

```python
# Future: SystemPromptResolver
class SystemPromptResolver:
    """Resolve system prompt based on user claims."""

    def resolve(self, claims: Dict[str, Any]) -> str:
        if "admin" in claims.get("roles", []):
            return ADMIN_SYSTEM_PROMPT
        elif "developer" in claims.get("roles", []):
            return DEVELOPER_SYSTEM_PROMPT
        else:
            return DEFAULT_SYSTEM_PROMPT
```

### 3. Knowledge Base (RAG)

```mermaid
flowchart LR
    subgraph Ingestion["Document Ingestion"]
        Docs["Documents"]
        Chunk["Chunking"]
        Embed["Embedding"]
        VectorDB["Vector DB<br/>(Qdrant/Pinecone)"]
    end

    subgraph Query["Query Flow"]
        UserQ["User Question"]
        Retrieve["Retrieve Context"]
        Augment["Augment Prompt"]
        LLM["LLM"]
    end

    Docs --> Chunk --> Embed --> VectorDB
    UserQ --> Retrieve
    VectorDB --> Retrieve
    Retrieve --> Augment --> LLM
```

### 4. Conversation Features

| Feature | Description |
|---------|-------------|
| **Sharing** | Generate shareable links for conversations |
| **Pinning** | Pin important conversations to dashboard |
| **Export** | Export as Markdown, JSON, or PDF |
| **Branching** | Fork conversation from any point |
| **Templates** | Save and reuse conversation templates |

### 5. Additional Upstream Types

```mermaid
flowchart TB
    subgraph UpstreamTypes["Upstream Source Types"]
        OpenAPI["OpenAPI<br/>(Current)"]
        Workflow["Workflow Engine<br/>(Planned)"]
        MCP["MCP Servers<br/>(Planned)"]
        HTTP["Simple HTTP<br/>(Planned)"]
        GraphQL["GraphQL<br/>(Future)"]
    end

    ToolsProvider["Tools Provider"] --> OpenAPI
    ToolsProvider --> Workflow
    ToolsProvider --> MCP
    ToolsProvider --> HTTP
    ToolsProvider --> GraphQL
```

### 6. Multi-Modal Support

```python
# Future: Multi-modal message support
@dataclass
class MultiModalContent:
    type: Literal["text", "image", "audio", "file"]
    content: Union[str, bytes]
    mime_type: Optional[str] = None

class Conversation:
    def add_user_message(self, content: List[MultiModalContent]) -> str:
        """Add message with mixed content types."""
        ...
```

### Extension Architecture

All extensions follow the same patterns:

1. **Interface-based**: Define abstract interfaces
2. **DI-configured**: Register implementations in `main.py`
3. **Claims-driven**: Use JWT claims for personalization
4. **Event-sourced**: Emit domain events for all state changes
5. **Observable**: Include OpenTelemetry instrumentation

---

## Code References

| Component | File Location |
|-----------|---------------|
| Agent Controller | `src/api/controllers/agent_controller.py` |
| Access Resolver | `src/application/services/access_resolver.py` |
| Tool Executor | `src/application/services/tool_executor.py` |
| Token Exchanger | `src/infrastructure/adapters/keycloak_token_exchanger.py` |
| ReAct Agent | `agent-host/src/application/agents/react_agent.py` |
| Chat Service | `agent-host/src/application/services/chat_service.py` |
| Tool Provider Client | `agent-host/src/application/services/tool_provider_client.py` |
| Ollama Provider | `agent-host/src/infrastructure/adapters/ollama_llm_provider.py` |
| Access Policy Entity | `src/domain/entities/access_policy.py` |
| Tool Group Entity | `src/domain/entities/tool_group.py` |
| Upstream Source Entity | `src/domain/entities/upstream_source.py` |
