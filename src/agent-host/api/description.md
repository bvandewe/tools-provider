# Agent Host API

> **📚 Full Documentation:** [https://bvandewe.github.io/tools-provider/](https://bvandewe.github.io/tools-provider/)

---

## Overview

**Agent Host** is an AI-powered chat interface that connects users to the MCP Tools Provider. It provides a conversational interface where AI agents can discover and execute tools on behalf of authenticated users using natural language.

## Key Features

TODO

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

TODO

## Quick Start

1. **Authenticate** using the Authorize button or a Bearer token
2. **Start a Chat** via `POST /chat/send` with a message
3. **List Conversations** at `GET /chat/conversations`
4. **Check Available Tools** at `GET /chat/tools`

## Streaming Responses

TODO

---

_For architecture details, deployment guides, and troubleshooting, visit the [full documentation](https://bvandewe.github.io/tools-provider/)._
