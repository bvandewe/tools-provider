# Agent Host

Backend-for-Frontend (BFF) service providing a chat interface for the MCP Tools Provider.

## Overview

The Agent Host enables end users to interact with curated tools through a natural language chat interface. It handles:

- OAuth2 authentication via Keycloak
- Tool discovery from MCP Tools Provider
- LLM integration via Ollama
- Tool execution with identity propagation

## Quick Start

```bash
# From the tools-provider root directory
docker-compose up agent-host ollama
```

Access the chat UI at http://localhost:8050

## Architecture

```
Browser → Agent Host (BFF) → Tools Provider → Upstream Services
              ↓
           Ollama (LLM)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TOOLS_PROVIDER_URL` | `http://app:8080` | Tools Provider internal URL |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model to use |
| `KEYCLOAK_URL` | `http://localhost:8041` | Keycloak external URL |
| `KEYCLOAK_URL_INTERNAL` | `http://keycloak:8080` | Keycloak internal URL |
| `KEYCLOAK_REALM` | `tools-provider` | Keycloak realm |
| `KEYCLOAK_CLIENT_ID` | `agent-host` | OAuth2 client ID |
| `REDIS_URL` | `redis://redis:6379/2` | Redis URL (database 2) |
| `SESSION_TTL_SECONDS` | `3600` | Session expiry in seconds |

## Development

```bash
cd agent-host
poetry install
poetry run uvicorn src.main:create_app --factory --reload --port 8050
```
