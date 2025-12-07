# Agent Host (BFF + Chatbot) Implementation Plan

**Document Version:** 1.0
**Date:** December 5, 2025
**Status:** Planning

## 1. Overview

This document outlines the implementation plan for the **Agent Host** service - a Backend-for-Frontend (BFF) that provides a Chat UI for end users to interact with tools exposed by the MCP Tools Provider.

### Architecture Position

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Docker Compose Stack                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────────┐     ┌───────────────────────────┐ │
│  │   Browser   │     │   Agent Host    │     │   MCP Tools Provider      │ │
│  │  (Chat UI)  │────▶│   (BFF + LLM)   │────▶│   (Tool Gateway)          │ │
│  │  Port 3000  │     │   Port 8050     │     │   Port 8040               │ │
│  └─────────────┘     └────────┬────────┘     └─────────────┬─────────────┘ │
│                               │                            │               │
│                               │                            ▼               │
│                               │              ┌───────────────────────────┐ │
│                               │              │   Upstream Services       │ │
│                               │              │   (Billing, HR, CRM...)   │ │
│                               │              └───────────────────────────┘ │
│                               │                                            │
│                               ▼                                            │
│                      ┌─────────────────┐     ┌───────────────────────────┐ │
│                      │     Ollama      │     │       Keycloak            │ │
│                      │   (Local LLM)   │     │   (Identity Provider)     │ │
│                      │   Port 11434    │     │   Port 8041               │ │
│                      └─────────────────┘     └───────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. Service Specification

### 2.1 Agent Host Service

| Attribute | Value |
|-----------|-------|
| **Name** | `agent-host` |
| **Container** | `tools-provider-agent-host` |
| **Port** | 8050 (Backend API) |
| **Frontend Port** | 3000 (if separate) or served from 8050 |
| **Language** | Python (FastAPI) - consistent with main app |
| **LLM Integration** | Ollama via `ollama-python` or `langchain-ollama` |

### 2.2 Ollama Service

| Attribute | Value |
|-----------|-------|
| **Name** | `ollama` |
| **Container** | `tools-provider-ollama` |
| **Port** | 11434 |
| **Image** | `ollama/ollama:latest` |
| **Default Model** | `llama3.2:3b` (small, fast for dev) |
| **GPU Support** | Optional (CPU works for dev) |

## 3. Port Allocation

Current port usage in `.env`:

| Port | Service | Status |
|------|---------|--------|
| 8040 | Tools Provider (app) | ✅ Used |
| 8041 | Keycloak | ✅ Used |
| 8042 | EventStoreDB | ✅ Used |
| 8043 | MongoDB | ✅ Used |
| 8044 | Mongo Express | ✅ Used |
| 8045 | Redis | ✅ Used |
| 8046 | Redis Commander | ✅ Used |
| 8047 | Event Player | ✅ Used |
| **8050** | **Agent Host (NEW)** | 🆕 Available |
| **11434** | **Ollama (NEW)** | 🆕 Available |

## 4. Implementation Phases

### Phase 1: Infrastructure Setup

- [ ] Add Ollama service to docker-compose.yml
- [ ] Add Agent Host service scaffold to docker-compose.yml
- [ ] Create `agent-host/` directory structure
- [ ] Add Keycloak client for agent-host (public client)
- [ ] Update .env with new ports

### Phase 2: Backend Implementation

- [ ] FastAPI application with OAuth2 login
- [ ] Session management (user JWT storage)
- [ ] Tools Provider BFF client (`/api/bff/tools`, `/api/bff/tools/call`)
- [ ] Ollama integration for chat completions
- [ ] Tool calling loop (LLM → tool execution → response)
- [ ] WebSocket support for streaming responses

### Phase 3: Frontend Implementation

- [ ] Simple chat UI (can use existing Parcel setup pattern)
- [ ] Keycloak JS adapter for login
- [ ] Message history display
- [ ] Tool execution visualization
- [ ] Streaming response display

### Phase 4: Integration Testing

- [ ] End-to-end flow: Login → Chat → Tool Discovery → Tool Execution
- [ ] Role-based tool filtering verification
- [ ] Token exchange verification via Keycloak logs

## 5. Directory Structure

```
agent-host/
├── Dockerfile
├── pyproject.toml
├── README.md
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Settings (Pydantic)
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── keycloak.py           # Keycloak OIDC client
│   │   └── session.py            # Session management
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── ollama_client.py      # Ollama API client
│   │   └── tool_caller.py        # Tool calling loop
│   ├── tools_provider/
│   │   ├── __init__.py
│   │   └── client.py             # BFF API client
│   ├── api/
│   │   ├── __init__.py
│   │   ├── chat.py               # Chat endpoints
│   │   └── auth.py               # Auth endpoints
│   └── models/
│       ├── __init__.py
│       └── messages.py           # Pydantic models
├── static/                        # Frontend assets (if bundled)
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── tests/
    └── ...
```

## 6. Key Implementation Details

### 6.1 OAuth2 Login Flow

```python
# agent-host/src/auth/keycloak.py
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()
oauth.register(
    name='keycloak',
    client_id=settings.keycloak_client_id,
    client_secret=settings.keycloak_client_secret,  # If confidential
    server_metadata_url=f'{settings.keycloak_url}/realms/{settings.keycloak_realm}/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid profile email'},
)
```

### 6.2 Tools Provider Client

```python
# agent-host/src/tools_provider/client.py
import httpx
from typing import List, Dict, Any

class ToolsProviderClient:
    """Client for MCP Tools Provider BFF API."""

    def __init__(self, base_url: str = "http://app:8080"):
        self.base_url = base_url

    async def get_tools(self, user_token: str) -> List[Dict[str, Any]]:
        """Fetch available tools for the user."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/bff/tools",
                headers={"Authorization": f"Bearer {user_token}"}
            )
            response.raise_for_status()
            return response.json()

    async def call_tool(
        self,
        user_token: str,
        tool_id: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool on behalf of the user."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/bff/tools/call",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"tool_id": tool_id, "arguments": arguments}
            )
            response.raise_for_status()
            return response.json()
```

### 6.3 Ollama Tool Calling

```python
# agent-host/src/llm/tool_caller.py
import ollama
from typing import List, Dict, Any, Optional

class ToolCaller:
    """Manages the LLM tool-calling loop."""

    def __init__(
        self,
        tools_client: ToolsProviderClient,
        model: str = "llama3.2:3b"
    ):
        self.tools_client = tools_client
        self.model = model
        self.ollama = ollama.AsyncClient(host="http://ollama:11434")

    async def chat(
        self,
        user_message: str,
        user_token: str,
        history: List[Dict] = None
    ) -> str:
        """Process a user message with potential tool calls."""

        # 1. Fetch available tools for this user
        tools = await self.tools_client.get_tools(user_token)
        ollama_tools = self._convert_to_ollama_format(tools)

        # 2. Build messages
        messages = history or []
        messages.append({"role": "user", "content": user_message})

        # 3. Call LLM with tools
        response = await self.ollama.chat(
            model=self.model,
            messages=messages,
            tools=ollama_tools,
        )

        # 4. Handle tool calls if present
        if response.message.tool_calls:
            tool_results = []
            for tool_call in response.message.tool_calls:
                result = await self.tools_client.call_tool(
                    user_token=user_token,
                    tool_id=tool_call.function.name,
                    arguments=tool_call.function.arguments,
                )
                tool_results.append(result)

            # 5. Send tool results back to LLM for final response
            messages.append(response.message)
            messages.append({
                "role": "tool",
                "content": str(tool_results)
            })

            final_response = await self.ollama.chat(
                model=self.model,
                messages=messages,
            )
            return final_response.message.content

        return response.message.content

    def _convert_to_ollama_format(self, tools: List[Dict]) -> List[Dict]:
        """Convert Tools Provider format to Ollama tool format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["tool_id"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            }
            for tool in tools
        ]
```

## 7. Keycloak Configuration

Add new client for Agent Host in realm export:

```json
{
    "clientId": "agent-host",
    "name": "Agent Host Chat Application",
    "enabled": true,
    "publicClient": true,
    "protocol": "openid-connect",
    "redirectUris": [
        "http://localhost:8050/*",
        "http://localhost:3000/*"
    ],
    "webOrigins": [
        "http://localhost:8050",
        "http://localhost:3000"
    ],
    "standardFlowEnabled": true,
    "directAccessGrantsEnabled": true,
    "fullScopeAllowed": true
}
```

## 8. Docker Compose Additions

```yaml
  # 🤖 Ollama (Local LLM)
  # http://localhost:11434
  ollama:
    container_name: tools-provider-ollama
    image: ollama/ollama:latest
    ports:
      - "${OLLAMA_PORT:-11434}:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - tools-provider-net
    # Pull default model on startup
    entrypoint: >
      sh -c "
      ollama serve &
      sleep 5 &&
      ollama pull llama3.2:3b &&
      wait
      "

  # 💬 Agent Host (BFF + Chat UI)
  # http://localhost:8050
  agent-host:
    container_name: tools-provider-agent-host
    build:
      context: ./agent-host
      dockerfile: Dockerfile
    ports:
      - "${AGENT_HOST_PORT:-8050}:8080"
    environment:
      LOG_LEVEL: DEBUG

      # Tools Provider Connection
      TOOLS_PROVIDER_URL: http://app:8080

      # Ollama Connection
      OLLAMA_URL: http://ollama:11434
      OLLAMA_MODEL: llama3.2:3b

      # Keycloak Configuration
      KEYCLOAK_URL: ${KEYCLOAK_URL:-http://localhost:8041}
      KEYCLOAK_URL_INTERNAL: http://keycloak:8080
      KEYCLOAK_REALM: ${KEYCLOAK_REALM:-tools-provider}
      KEYCLOAK_CLIENT_ID: agent-host

      # Session Configuration
      SESSION_SECRET: agent-host-session-secret-change-in-production
    networks:
      - tools-provider-net
    depends_on:
      - app
      - ollama
      - keycloak

volumes:
  # ... existing volumes ...
  ollama_data:
```

## 9. Environment Variables (.env additions)

```dotenv
# Agent Host Settings
AGENT_HOST_PORT=8050

# Ollama Settings
OLLAMA_PORT=11434
OLLAMA_MODEL=llama3.2:3b
```

## 10. Acceptance Criteria

The implementation is complete when:

1. **User Login:** User can log in to Agent Host at `http://localhost:8050` via Keycloak
2. **Chat Interface:** User sees a chat UI after login
3. **Tool Discovery:** Agent Host fetches user-specific tools from Tools Provider
4. **LLM Integration:** User messages are processed by Ollama
5. **Tool Execution:** When LLM requests a tool, Agent Host calls Tools Provider
6. **Identity Propagation:** Tool execution uses the user's JWT for token exchange
7. **Response Display:** Tool results are shown in the chat

## 11. Testing Scenarios

### Scenario 1: Finance User

- Login as `admin` (has `admin`, `manager` roles)
- Should see tools from groups accessible to `admin` or `manager`
- Execute a tool → verify token exchange in Keycloak logs

### Scenario 2: Regular User

- Login as `user` (has only `user` role)
- Should see fewer tools than admin
- Verify tool filtering works correctly

### Scenario 3: Tool Execution

- Ask LLM "What tools do I have access to?"
- Ask LLM to execute a specific tool
- Verify the response includes tool results

## 12. Open Questions

Before implementation, clarify:

1. **Frontend Complexity:**
   - Simple HTML/JS (like current UI) or React/Vue?
   - Recommendation: Start simple, iterate

2. **Session Storage:**
   - In-memory (single instance) or Redis (scalable)?
   - Recommendation: Redis for consistency with Tools Provider

3. **Conversation History:**
   - In-memory per session or persisted to MongoDB?
   - Recommendation: In-memory for PoC, persist later

4. **Streaming:**
   - SSE for streaming LLM responses?
   - Recommendation: Yes, better UX

---

**Next Step:** Review this plan and confirm before implementation.
