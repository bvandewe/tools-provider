# Agent Host Low-Level Design

- **Document Version:** 1.0
- **Date:** December 5, 2025
- **Status:** ✅ Implemented

## 1. Overview

The Agent Host is a Backend-for-Frontend (BFF) service that provides a chat interface for end users to interact with tools exposed by the MCP Tools Provider. It implements identity propagation, LLM integration via Ollama, and tool execution orchestration.

## 2. Architecture Layers

Following Clean Architecture principles consistent with Tools Provider:

```
agent-host/
├── src/                           # Backend (Python/FastAPI)
│   ├── main.py                    # Application entry point
│   ├── api/                       # API Layer (Controllers, Dependencies)
│   │   ├── controllers/
│   │   │   ├── chat_controller.py
│   │   │   └── auth_controller.py
│   │   ├── dependencies.py
│   │   └── services/
│   │       └── auth_service.py
│   ├── application/               # Application Layer (CQRS)
│   │   ├── commands/
│   │   │   └── send_message_command.py
│   │   ├── queries/
│   │   │   └── get_conversation_query.py
│   │   ├── services/
│   │   │   ├── llm_service.py
│   │   │   └── tools_provider_client.py
│   │   └── settings.py
│   ├── domain/                    # Domain Layer
│   │   ├── entities/
│   │   │   └── conversation.py
│   │   ├── models/
│   │   │   ├── message.py
│   │   │   └── tool_call.py
│   │   └── repositories/
│   │       └── conversation_repository.py
│   ├── infrastructure/            # Infrastructure Layer
│   │   ├── repositories/
│   │   │   └── in_memory_conversation_repository.py
│   │   └── session_store.py
│   └── integration/               # Integration Layer (DTOs)
│       └── models/
│           └── conversation_dto.py
├── ui/                            # Frontend (Parcel + VanillaJS)
│   ├── src/
│   │   ├── templates/
│   │   ├── scripts/
│   │   └── styles/
│   ├── build-template.js
│   └── package.json
└── static/                        # Built UI assets
```

## 3. Domain Model

### 3.1 Conversation Entity

```python
@dataclass
class Conversation:
    """Represents a chat conversation with an end user."""
    id: str
    user_id: str
    messages: List[Message]
    created_at: datetime
    updated_at: datetime
```

### 3.2 Message Value Object

```python
@dataclass
class Message:
    """A single message in a conversation."""
    id: str
    role: MessageRole  # user, assistant, tool
    content: str
    tool_calls: Optional[List[ToolCall]]
    tool_call_id: Optional[str]  # For tool responses
    timestamp: datetime
```

### 3.3 ToolCall Value Object

```python
@dataclass
class ToolCall:
    """Represents a tool invocation by the LLM."""
    id: str
    tool_id: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    status: ToolCallStatus  # pending, completed, failed
```

## 4. Repository Pattern

### 4.1 Abstract Repository Interface

```python
# domain/repositories/conversation_repository.py
class ConversationRepository(ABC):
    """Abstract repository for conversation persistence."""

    @abstractmethod
    async def get_async(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        pass

    @abstractmethod
    async def get_by_user_async(self, user_id: str) -> List[Conversation]:
        """Get all conversations for a user."""
        pass

    @abstractmethod
    async def save_async(self, conversation: Conversation) -> None:
        """Save or update a conversation."""
        pass

    @abstractmethod
    async def delete_async(self, conversation_id: str) -> None:
        """Delete a conversation."""
        pass
```

### 4.2 In-Memory Implementation

```python
# infrastructure/repositories/in_memory_conversation_repository.py
class InMemoryConversationRepository(ConversationRepository):
    """In-memory conversation storage for development."""

    def __init__(self):
        self._conversations: Dict[str, Conversation] = {}
```

### 4.3 Future: Redis Implementation

```python
# infrastructure/repositories/redis_conversation_repository.py (future)
class RedisConversationRepository(ConversationRepository):
    """Redis-backed conversation storage with TTL."""

    def __init__(self, redis_url: str, ttl_seconds: int = 3600):
        # Use Redis database 2 (separate from Tools Provider)
        self._redis = redis.from_url(redis_url)
        self._ttl = ttl_seconds
```

## 5. Application Services

### 5.1 LLM Service

```python
# application/services/llm_service.py
class LLMService:
    """Ollama integration for chat completions with tool calling."""

    def __init__(self, ollama_url: str, model: str):
        self._ollama_url = ollama_url
        self._model = model

    async def chat(
        self,
        messages: List[Message],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        """Send messages to Ollama and get response with optional tool calls."""
        pass
```

### 5.2 Tools Provider Client

```python
# application/services/tools_provider_client.py
class ToolsProviderClient:
    """HTTP client for MCP Tools Provider BFF API."""

    def __init__(self, base_url: str):
        self._base_url = base_url

    async def get_tools(self, user_token: str) -> List[ToolDefinition]:
        """Fetch available tools for the authenticated user."""
        # GET /api/bff/tools with Authorization: Bearer {token}
        pass

    async def call_tool(
        self,
        user_token: str,
        tool_id: str,
        arguments: Dict[str, Any],
    ) -> ToolCallResult:
        """Execute a tool via the Tools Provider."""
        # POST /api/bff/tools/call with Authorization: Bearer {token}
        pass
```

## 6. CQRS Commands

### 6.1 SendMessageCommand

```python
@dataclass
class SendMessageCommand(Command[OperationResult[MessageResponse]]):
    """Command to send a user message and get AI response."""

    conversation_id: Optional[str]  # None = create new conversation
    content: str
    user_id: str
    user_token: str  # For tool execution identity propagation
```

### 6.2 SendMessageCommandHandler

The handler implements the tool-calling loop:

```
1. Get or create conversation
2. Add user message
3. Fetch user's available tools from Tools Provider
4. Send to LLM with tools
5. If LLM requests tools:
   a. Execute each tool via Tools Provider
   b. Add tool results to messages
   c. Send back to LLM for final response
6. Add assistant response
7. Save conversation
8. Return response
```

## 7. API Endpoints

### 7.1 Chat Controller

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/conversations` | GET | List user's conversations |
| `/api/chat/conversations` | POST | Create new conversation |
| `/api/chat/conversations/{id}` | GET | Get conversation history |
| `/api/chat/conversations/{id}` | DELETE | Delete conversation |
| `/api/chat/conversations/{id}/messages` | POST | Send message |
| `/api/chat/conversations/{id}/messages/stream` | POST | Send message (SSE stream) |

### 7.2 Auth Controller

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | GET | Redirect to Keycloak |
| `/api/auth/callback` | GET | OAuth2 callback |
| `/api/auth/logout` | POST | Logout user |
| `/api/auth/me` | GET | Get current user info |

## 8. Session Management

### 8.1 Redis Session Store (Database 2)

```python
# Separate from Tools Provider:
# - Database 0: Tools Provider sessions
# - Database 1: Tools Provider cache
# - Database 2: Agent Host sessions

REDIS_URL = "redis://redis:6379/2"
```

### 8.2 Session Data

```python
@dataclass
class UserSession:
    """User session stored in Redis."""
    user_id: str
    access_token: str
    refresh_token: str
    token_expires_at: datetime
    user_info: Dict[str, Any]  # Claims from Keycloak
```

## 9. Configuration

### 9.1 Settings (Pydantic)

```python
class Settings(ApplicationSettings):
    """Agent Host application settings."""

    # Application
    app_name: str = "Agent Host"
    app_port: int = 8080

    # Tools Provider
    tools_provider_url: str = "http://app:8080"

    # Ollama
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:3b"

    # Keycloak
    keycloak_url: str = "http://keycloak:8080"
    keycloak_url_external: str = "http://localhost:8041"
    keycloak_realm: str = "tools-provider"
    keycloak_client_id: str = "agent-host"

    # Redis (Database 2 for sessions)
    redis_url: str = "redis://redis:6379/2"
    session_ttl_seconds: int = 3600
```

## 10. Docker Compose Integration

### 10.1 New Services

```yaml
# Ollama LLM
ollama:
  container_name: tools-provider-ollama
  image: ollama/ollama:latest
  ports:
    - "${OLLAMA_PORT:-11434}:11434"
  volumes:
    - ollama_data:/root/.ollama
  networks:
    - tools-provider-net

# Agent Host
agent-host:
  container_name: tools-provider-agent-host
  build:
    context: ./agent-host
    dockerfile: Dockerfile
  ports:
    - "${AGENT_HOST_PORT:-8050}:8080"
  environment:
    TOOLS_PROVIDER_URL: http://app:8080
    OLLAMA_URL: http://ollama:11434
    KEYCLOAK_URL_INTERNAL: http://keycloak:8080
    KEYCLOAK_URL: http://localhost:${KEYCLOAK_PORT:-8041}
    REDIS_URL: redis://redis:6379/2
  depends_on:
    - app
    - ollama
    - keycloak
    - redis
```

### 10.2 Environment Variables

```dotenv
# Agent Host
AGENT_HOST_PORT=8050

# Ollama
OLLAMA_PORT=11434
OLLAMA_MODEL=llama3.2:3b
```

## 11. Keycloak Client Configuration

Add to realm export:

```json
{
    "clientId": "agent-host",
    "name": "Agent Host Chat Application",
    "enabled": true,
    "publicClient": true,
    "protocol": "openid-connect",
    "redirectUris": ["http://localhost:8050/*"],
    "webOrigins": ["http://localhost:8050"],
    "standardFlowEnabled": true,
    "directAccessGrantsEnabled": false,
    "fullScopeAllowed": true
}
```

## 12. Sequence Diagram: Chat Flow

```
User        Browser      Agent Host       Tools Provider     Ollama
 │            │              │                  │               │
 │─ Login ───▶│              │                  │               │
 │            │─ OAuth2 ────▶│                  │               │
 │            │◀─ JWT ───────│                  │               │
 │            │              │                  │               │
 │─ Message ─▶│              │                  │               │
 │            │─ POST /chat ▶│                  │               │
 │            │              │─ GET /bff/tools ▶│               │
 │            │              │◀─ Tools ─────────│               │
 │            │              │                  │               │
 │            │              │─ Chat + Tools ──────────────────▶│
 │            │              │◀─ Tool Call Request ─────────────│
 │            │              │                  │               │
 │            │              │─ POST /bff/call ▶│               │
 │            │              │◀─ Tool Result ───│               │
 │            │              │                  │               │
 │            │              │─ Tool Result ───────────────────▶│
 │            │              │◀─ Final Response ────────────────│
 │            │              │                  │               │
 │            │◀─ Response ──│                  │               │
 │◀─ Display ─│              │                  │               │
```

## 13. Error Handling

| Error | HTTP Status | Action |
|-------|-------------|--------|
| Invalid token | 401 | Redirect to login |
| Tools Provider unavailable | 503 | Return friendly error |
| Ollama unavailable | 503 | Return friendly error |
| Tool execution failed | 200 | Include error in chat response |
| Rate limit exceeded | 429 | Return retry-after |

## 14. Security Considerations

1. **Token Storage:** User JWTs stored server-side in Redis, not in browser
2. **Session Cookies:** HTTPOnly, Secure, SameSite=Lax
3. **CORS:** Restricted to frontend origin
4. **Input Validation:** Sanitize user messages before LLM
5. **Tool Results:** Sanitize before display

## 15. Observability

Consistent with Tools Provider:

- OpenTelemetry tracing
- Prometheus metrics
- Structured logging

Key metrics:

- `agent_host_messages_total` - Messages processed
- `agent_host_tool_calls_total` - Tool executions
- `agent_host_llm_latency_seconds` - Ollama response time
- `agent_host_tool_latency_seconds` - Tool execution time
