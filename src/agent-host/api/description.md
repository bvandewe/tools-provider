# Agent Host API

> **📚 Full Documentation:** [https://bvandewe.github.io/tools-provider/](https://bvandewe.github.io/tools-provider/)

---

## Overview

**Agent Host** is an AI-powered chat interface that connects users to the MCP Tools Provider. It provides a conversational interface where AI agents can discover and execute tools on behalf of authenticated users using natural language.

## Key Features

- **💬 Streaming Chat** — Real-time AI responses via Server-Sent Events (SSE)
- **🛠️ Tool Execution** — AI agents can call tools from upstream services
- **📝 Conversations** — Persistent conversation history with message threading
- **🎛️ Sessions** — Structured interactions with proactive agent capabilities
- **🏥 Health Monitoring** — Component health checks for debugging
- **⚙️ Settings Management** — Admin-configurable LLM and agent settings

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
| **Chat** | Send messages, manage conversations, and access tools |
| **Sessions** | Create and manage structured agent sessions |
| **Config** | Frontend configuration and available models |
| **Settings** | Admin settings for LLM, agent, and UI configuration |
| **Health** | System component health checks |
| **Files** | Workspace file uploads and downloads (proxied to Tools Provider) |
| **Auth** | OAuth2 login/logout and session management |

## Quick Start

1. **Authenticate** using the Authorize button or a Bearer token
2. **Start a Chat** via `POST /chat/send` with a message
3. **List Conversations** at `GET /chat/conversations`
4. **Check Available Tools** at `GET /chat/tools`

## Streaming Responses

The `POST /chat/send` endpoint returns a Server-Sent Events (SSE) stream with the following event types:

| Event | Description |
|-------|-------------|
| `stream_started` | Connection established with request_id |
| `content` | AI-generated text chunks |
| `tool_call` | Agent is calling a tool |
| `tool_result` | Tool execution result |
| `error` | Error occurred during processing |

---

_For architecture details, deployment guides, and troubleshooting, visit the [full documentation](https://bvandewe.github.io/tools-provider/)._
