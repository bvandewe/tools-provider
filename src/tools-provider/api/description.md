# MCP Tools Provider API

> **📚 Full Documentation:** [https://bvandewe.github.io/tools-provider/](https://bvandewe.github.io/tools-provider/)

---

## Overview

The **MCP Tools Provider** is a service that dynamically discovers, manages, and executes tools from upstream OpenAPI services on behalf of authenticated users. It acts as a central hub for AI agents to access business tools with proper authentication and authorization.

## Key Features

- **🔍 Tool Discovery** — Automatically discovers tools from OpenAPI specifications registered as upstream sources
- **🔐 Identity Delegation** — Uses OAuth2 token exchange to execute tools with end-user identity
- **🏷️ Tool Groups & Labels** — Organize tools into logical groups with selectors and labels
- **📋 Access Policies** — Fine-grained access control based on JWT claims
- **📡 Real-time Updates** — SSE endpoint for live tool availability notifications
- **🔄 Event Sourcing** — Full audit trail via EventStoreDB with CQRS architecture

## Authentication

This API supports two authentication methods that can be used interchangeably:

### 1. OAuth2 Authorization Code Flow (Swagger UI)

Click the **Authorize** button above to authenticate via Keycloak. Your access token will be automatically included in subsequent requests.

### 2. JWT Bearer Token (Programmatic Access)

Include your JWT access token in the `Authorization` header:

```http
Authorization: Bearer <your_jwt_access_token>
```

## API Sections

| Section | Description |
|---------|-------------|
| **Agent** | Endpoints for AI agents to discover and execute tools |
| **Sources** | Register and manage upstream OpenAPI services |
| **Tools** | Browse, search, and manage discovered tools |
| **Tool Groups** | Create logical groupings of tools with selectors |
| **Policies** | Define access policies based on JWT claims |
| **Labels** | Create and manage tool labels for organization |
| **Files** | Workspace file management for agent deliverables |
| **Auth** | OAuth2 login/logout and session management |

## Quick Start

1. **Authenticate** using the Authorize button or a Bearer token
2. **Browse Sources** at `GET /sources` to see registered upstream services
3. **Explore Tools** at `GET /tools` to view available tools
4. **Execute Tools** via `POST /agent/tools/call` (for AI agents)

## Rate Limits & Best Practices

- Use `GET /tools/summaries` for lightweight tool listings
- Leverage SSE at `GET /agent/sse` for real-time updates instead of polling
- Cache tool manifests client-side when possible

---

_For architecture details, deployment guides, and troubleshooting, visit the [full documentation](https://bvandewe.github.io/tools-provider/)._
