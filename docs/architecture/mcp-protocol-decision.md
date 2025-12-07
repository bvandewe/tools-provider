# Architecture Decision Record: MCP Protocol Compatibility

**ADR-005: MCP Tools Provider API Design**
**Date:** December 5, 2025
**Status:** Accepted
**Deciders:** Principal Engineer, System Architect

## Context

The MCP Tools Provider exposes endpoints for AI agents to discover and execute tools. The question arose whether these endpoints should implement the official [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) JSON-RPC specification to enable compatibility with standard MCP clients like Claude Desktop or VS Code.

## Decision

**We will NOT implement MCP-compliant JSON-RPC endpoints.**

Instead, we maintain our purpose-built REST API designed specifically for the Host Application (BFF) pattern required by our identity propagation architecture.

## Rationale

### 1. Fundamental Incompatibility with Identity Model

| Aspect | Standard MCP Protocol | MCP Tools Provider |
|--------|----------------------|-------------------|
| **Identity Model** | Machine identity (static API key) | End-user identity (dynamic JWT) |
| **Token Source** | Static configuration | OAuth2 user session |
| **Tool Filtering** | Server-side, usually static | Dynamic, based on JWT claims |
| **Token Exchange** | Not part of MCP spec | **Core requirement** |

Standard MCP clients (Claude Desktop, VS Code) cannot:

- Perform OAuth2 login flows
- Inject per-user JWT tokens
- Refresh expired tokens dynamically

### 2. The Required Architecture

Our system requires a **Host Application (BFF)** pattern where:

```
┌──────────────┐      ┌─────────────────┐      ┌───────────────────┐
│  Browser     │      │  Host App (BFF) │      │ MCP Tools Provider│
│  (End User)  │      │  (Custom App)   │      │  (This Service)   │
└──────┬───────┘      └────────┬────────┘      └─────────┬─────────┘
       │                       │                         │
       │ 1. Login via Keycloak │                         │
       │──────────────────────►│                         │
       │                       │                         │
       │ 2. User sends chat    │                         │
       │──────────────────────►│                         │
       │                       │                         │
       │                       │ 3. Connect with USER JWT│
       │                       │ Authorization: Bearer   │
       │                       │────────────────────────►│
       │                       │                         │
       │                       │ 4. Get user-filtered    │
       │                       │    tools                │
       │                       │◄────────────────────────│
       │                       │                         │
       │                       │ 5. Execute tool with    │
       │                       │    USER JWT             │
       │                       │────────────────────────►│
       │                       │                         │ 6. Token Exchange
       │                       │                         │    (user→upstream)
```

The "MCP Client" in our architecture is the **Host App**, not a standard MCP client.

### 3. Security Concerns

Adding MCP-compliant endpoints could:

- **Create false expectations** that Claude Desktop can connect directly
- **Bypass security controls** by suggesting a simpler integration path
- **Increase attack surface** with an additional API contract to maintain

### 4. Complexity vs. Value

| Option | Complexity | Value Add |
|--------|------------|-----------|
| REST API only | Low | High (serves Host App perfectly) |
| REST + MCP JSON-RPC | High | Zero (no compatible clients) |

## API Design

The BFF API is exposed under `/api/bff/` prefix:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/bff/tools` | GET | List tools accessible to the authenticated user |
| `/api/bff/tools/call` | POST | Execute a tool with user's identity delegation |
| `/api/bff/sse` | GET | SSE stream for real-time tool updates |

### Authentication

All endpoints require `Authorization: Bearer <user_jwt>` header where:

- The JWT is the **end-user's** access token from Keycloak
- The Host App obtains this token via standard OAuth2 flow
- The token is used for:
  1. Access policy evaluation (tool filtering)
  2. RFC 8693 token exchange (identity delegation to upstream services)

### Example: Host App Integration

```python
# In the Host Application Backend (e.g., chat_service.py)
async def process_user_query(user_query: str, user_jwt: str):
    """Execute a user query using MCP Tools Provider."""

    async with httpx.AsyncClient() as client:
        # 1. Get available tools for THIS user
        tools_response = await client.get(
            "http://mcp-provider:8040/api/bff/tools",
            headers={"Authorization": f"Bearer {user_jwt}"}
        )
        tools = tools_response.json()

        # 2. Let LLM decide which tool to use
        llm_response = await llm.generate(
            prompt=user_query,
            tools=tools
        )

        # 3. Execute tool if LLM requests it
        if llm_response.tool_call:
            result = await client.post(
                "http://mcp-provider:8040/api/bff/tools/call",
                headers={"Authorization": f"Bearer {user_jwt}"},
                json={
                    "tool_id": llm_response.tool_call.name,
                    "arguments": llm_response.tool_call.arguments
                }
            )
            return result.json()
```

## Consequences

### Positive

- **Simpler architecture**: Single REST API to maintain
- **Clearer security model**: No ambiguity about client requirements
- **Better for our use case**: Optimized for BFF pattern
- **Documentation clarity**: Explicit that Host App is required

### Negative

- **No off-the-shelf MCP client support**: Cannot use Claude Desktop directly
- **Custom integration required**: Host App must be built

### Mitigations

- Provide reference Host App implementation in documentation
- Include example code in `docs/specs/integration-draft.md`
- Consider adding a sample `agent-host` service in docker-compose (Option A from integration spec)

## Related Documents

- [Integration Draft Specification](../specs/integration-draft.md)
- [Token Exchange Setup Guide](../security/keycloak-token-exchange-setup.md)
- [CQRS Pattern](./cqrs-pattern.md)

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification)
- [RFC 8693: OAuth 2.0 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693)
