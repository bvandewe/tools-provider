# Project Spec: MCP Client Integration & Host Application

**Target System:** MCP Tools Provider (formerly Prism)
**Version:** 2.0 (Integration Focus)
**Date:** December 5, 2025
**Status:** Approved for Implementation

## 1\. Context & The "Identity Problem"

The **MCP Tools Provider** is designed as a secure, multi-tenant gateway. It filters tools based on the _End User's_ identity (e.g., `johndoe`), not the _Machine's_ identity.

**The Critical Constraint:**
Standard off-the-shelf MCP Clients (e.g., Claude Desktop, VS Code) typically run with static configuration. They cannot autonomously perform an OAuth2 Redirect Flow to log a user in, nor can they dynamically refresh tokens.

**The Requirement:**
To consume the MCP Tools Provider effectively, we must implement a **"Host Application"**. This application acts as the intermediary that manages the User Session and instantiates the AI Agent with the correct User Context.

-----

## 2\. Architecture: The Identity Propagation Flow

The Host Application serves as the "Backend-for-Frontend" (BFF). It bridges the browser (User) and the Infrastructure (MCP Tools Provider).

### The Data Flow

1. **User Login:** User logs into the **Host App Frontend** via Keycloak.
2. **Session:** Host App Backend receives the User's JWT (Access Token).
3. **Instantiation:** When the user sends a chat message, the Host App initializes an `MCPClient` instance.
4. **Propagation:** The Host App injects the User's JWT into the `Authorization` header of the MCP connection.
5. **Resolution:** The MCP Tools Provider receives the JWT, validates claims, and returns user-specific tools.

-----

## 3\. Component Specification: The "Host Application"

The maintainers must decide whether this component is built _inside_ the current repo or as a _separate_ project. Regardless of location, it must meet these specs:

### 3.1. Tech Stack Recommendation

- **Frontend:** React / Next.js / Vue (Chat UI).
- **Backend:** Python (FastAPI) or Node.js.
- **Agent Runtime:** LangChain, Rivet, or Vercel AI SDK.
- **Auth:** Keycloak OIDC Client.

### 3.2. Backend Logic (The "BFF")

The Host Backend is responsible for managing the connection to the MCP Tools Provider. It must not use a shared service account.

**Key Implementation Requirement (Python Example):**

```python
# In the Host Application Backend (e.g., chat_service.py)
from mcp import ClientSession, SSEClientTransport

async def process_user_query(user_query: str, user_jwt: str):
    """
    Spins up an ephemeral MCP connection for a specific user request.
    """

    # 1. Connect to the Provider using the USER'S Identity
    # This is the most critical line in the entire integration.
    transport = SSEClientTransport(
        url="http://mcp-provider:8000/sse",
        headers={
            "Authorization": f"Bearer {user_jwt}",  # <--- Identity Propagation
            "Accept": "text/event-stream"
        }
    )

    async with ClientSession(transport) as session:
        # 2. Fetch Tools (Provider filters these based on the JWT)
        available_tools = await session.list_tools()

        # 3. Inject Tools into LLM Context
        # (Example using generic LLM logic)
        response = await llm_engine.generate(
            prompt=user_query,
            tools=available_tools
        )

        # 4. Execute Tool (If LLM requests it)
        if response.tool_calls:
            # The session automatically re-uses the 'transport' headers
            # So the tool execution request ALSO carries the User JWT.
            result = await session.call_tool(response.tool_calls[0])
            return result
```

-----

## 4\. Implementation Strategy Options

The maintainers should choose one of the following paths for the repository structure.

### Option A: The "All-in-One" Stack (Recommended for PoC)

Include a lightweight Chat UI directly in the `docker-compose.yml`. This allows the project to be a self-contained, demonstrable product.

- **New Service:** `chat-ui` (Next.js/FastAPI).
- **Pros:** Instant "Time to Magic" for developers. proves the auth flow works.
- **Cons:** Tighter coupling.

### Option B: The "Headless" Provider (Enterprise Pattern)

Treat the MCP Tools Provider strictly as infrastructure (like a Database). The Chat App is a completely separate Git repository managed by a Frontend/Product team.

- **Pros:** Clean separation of concerns.
- **Cons:** Harder to test the full flow without mocking the client.

-----

## 5\. Updates to `docker-compose.yml` (For Option A)

If proceeding with **Option A**, add the Agent Host to the stack:

```yaml
  # ... Existing Keycloak, Postgres, Valkey, MCP-Provider ...

  # The User-Facing Chat Application
  agent-host:
    build: ./agent-host
    environment:
      - KEYCLOAK_URL=http://keycloak:8080
      - KEYCLOAK_REALM=prism-realm
      - KEYCLOAK_CLIENT_ID=prism-chat-ui # Public Client
      - MCP_PROVIDER_URL=http://mcp-provider:8000
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    ports:
      - "3000:3000" # User accesses this URL
    depends_on:
      - keycloak
      - mcp-provider
```

-----

## 6\. Acceptance Criteria

The system is considered "Ready" when:

1. **User Login:** I can log in to `localhost:3000` as `johndoe` (Role: Finance).
2. **Discovery:** The Agent Host connects to the Provider using John's token.
3. **Filtering:** The Agent only receives "Finance Tools" in the tool list.
4. **Execution:** When the Agent executes `create_invoice`, the Provider exchanges John's Token for a Billing Service Token and executes the request successfully.
5. **Audit:** Keycloak logs show the Token Exchange event associated with `johndoe`.
