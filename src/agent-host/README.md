# Agent Host

Backend-for-Frontend (BFF) service providing a chat interface for the MCP Tools Provider.

## Overview

The Agent Host enables end users to interact with curated tools through a natural language chat interface. Built with the **Neuroglia Framework** on FastAPI, it implements **CQRS** with **State-Based Persistence** (MongoDB).

### Core Capabilities

- **OAuth2 Authentication** via Keycloak (session cookies + JWT Bearer tokens)
- **WebSocket Protocol** for real-time bidirectional communication
- **Tool Discovery & Execution** from MCP Tools Provider with identity propagation
- **Multi-LLM Support** (Ollama local, OpenAI/Azure-compatible endpoints)
- **Proactive Conversations** with template-driven interactive widgets
- **Conversation Orchestrator** coordinating agents, templates, and widget flows

## Domain Model

The Agent Host uses three primary **AggregateRoots** persisted via `MotorRepository` (MongoDB):

| Aggregate | Purpose |
|-----------|---------|
| **Conversation** | Complete user-agent interaction with messages, template progress, scoring |
| **AgentDefinition** | Configures agent behavior: system prompt, tools, LLM settings, template reference |
| **ConversationTemplate** | Defines proactive flow: ordered items, timing, navigation, scoring rules |

```
┌─────────────────────┐     references      ┌──────────────────────┐
│   AgentDefinition   │────────────────────▶│ ConversationTemplate │
│                     │                     │                      │
│ • system_prompt     │                     │ • items[]            │
│ • tools[]           │                     │ • flow settings      │
│ • model             │                     │ • timing/scoring     │
└─────────────────────┘                     └──────────────────────┘
           │
           │ creates
           ▼
┌─────────────────────┐
│    Conversation     │
│                     │
│ • messages[]        │
│ • template_progress │
│ • status            │
└─────────────────────┘
```

## Features

### 🎨 Interactive Widget System

Widgets are rendered via WebSocket protocol with full lifecycle management:

| Category | Widget Type | Purpose |
|----------|-------------|---------|
| **Core** | `message` | Rich text/markdown display |
| **Display** | `text_display` | Static text content |
| | `image_display` | Image with captions |
| | `chart` | Data visualization charts |
| | `data_table` | Tabular data display |
| | `video` | Video playback |
| | `graph_topology` | Network/graph visualization |
| | `document_viewer` | PDF/document display |
| | `sticky_note` | Note-style content |
| **Input** | `multiple_choice` | Single-select options |
| | `checkbox_group` | Multi-select options |
| | `free_text` | Open text input |
| | `code_editor` | Syntax-highlighted code input |
| | `slider` | Numeric range selection |
| | `dropdown` | Searchable select |
| | `rating` | Stars/numeric/emoji/thumbs ratings |
| | `date_picker` | Date/time/datetime/range picker |
| | `matrix_choice` | Grid-based selection (Likert scales) |
| | `file_upload` | File attachment upload |
| **Interactive** | `hotspot` | Clickable image regions |
| | `drag_drop` | Category/sequence/graphical sorting |
| | `drawing` | Freehand drawing canvas |
| **Action** | `button` | Clickable action button |
| | `submit_button` | Form submission button |
| **Feedback** | `progress_bar` | Visual progress indicator |
| | `timer` | Countdown/count-up displays |
| **Embedded** | `iframe` | External content embedding |

Widgets support:

- **Multi-widget per ConversationItem**: Multiple widgets rendered together as a single UX step
- **Templated content**: LLM-generated content via Jinja-style instructions
- **Scoring**: Configurable max scores, correct answers, and feedback

### 🎭 Conversation Orchestrator

The Orchestrator is the central coordinator for conversation flows:

```
WebSocket Handler → Orchestrator → Specialized Handlers
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   MessageHandler  WidgetHandler   FlowHandler
         │               │               │
         ▼               ▼               ▼
   AgentRunner    ItemPresenter    FlowRunner
```

Key components:

- **MessageHandler**: User text message processing
- **WidgetHandler**: Widget response handling and scoring
- **FlowHandler**: Start/pause/cancel flow control
- **AgentRunner**: LLM execution with tool calling
- **ItemPresenter**: Template item presentation
- **FlowRunner**: Proactive flow execution
- **ConfigSender/ContentSender/WidgetSender**: Protocol message senders

### 📋 ConversationTemplate System

Templates define structured conversation flows:

```python
ConversationTemplate:
  ├── Flow Settings
  │   ├── agent_starts_first: bool
  │   ├── allow_navigation: bool
  │   └── enable_chat_input_initially: bool
  ├── Timing
  │   ├── min_duration_seconds
  │   └── max_duration_seconds
  ├── Display
  │   ├── display_progress_indicator
  │   ├── display_item_score
  │   └── append_items_to_view
  └── Items[]
      └── ConversationItem
          ├── id, order, title
          ├── enable_chat_input
          ├── instructions (Jinja template for LLM)
          └── Contents[]
              └── ItemContent
                  ├── widget_type
                  ├── stem, options
                  ├── correct_answer (never sent to client)
                  └── max_score
```

### 🔌 WebSocket Protocol v1.0

Real-time bidirectional communication using a CloudEvents-inspired envelope:

```javascript
{
  "id": "uuid",
  "type": "data.content.chunk",  // Hierarchical: plane.category.action
  "version": "1.0",
  "timestamp": "ISO8601",
  "source": "server",
  "conversationId": "uuid",
  "payload": { ... }
}
```

Message planes:

- **system**: Connection lifecycle (connect, ping/pong, error)
- **control**: UI state (widget.render, chat.enabled, panel.header)
- **data**: Content (content.chunk, content.complete, widget.response)

### 🤖 AgentDefinition Configuration

Agent behavior is fully configurable:

```python
AgentDefinition:
  ├── Identity
  │   ├── name, description, icon
  │   └── owner_user_id
  ├── Behavior
  │   ├── system_prompt
  │   ├── tools[]  # Tool IDs from Tools Provider
  │   ├── model
  │   └── allow_model_selection
  ├── Template Reference
  │   └── conversation_template_id  # Links to ConversationTemplate
  └── Access Control
      ├── is_public
      ├── required_roles[]
      └── allowed_users[]
```

### 🎯 2D Canvas (In Progress)

Canvas-based conversation UI supporting:

- Pan/zoom viewport transformations
- Widget positioning with coordinates
- Connection/grouping support (planned)
- Spatial layouts beyond linear chat flow

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (UI)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ WebSocket   │  │  Widgets    │  │   Canvas    │             │
│  │  Client     │  │ (WebComp)   │  │  Manager    │             │
│  └──────┬──────┘  └─────────────┘  └─────────────┘             │
└─────────┼──────────────────────────────────────────────────────┘
          │ WebSocket Protocol v1.0
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Host (FastAPI)                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   WebSocket Controller                      ││
│  └──────────────────────────┬──────────────────────────────────┘│
│                             ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │               Conversation Orchestrator                     ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       ││
│  │  │ Message  │ │ Widget   │ │  Flow    │ │  Agent   │       ││
│  │  │ Handler  │ │ Handler  │ │ Handler  │ │  Runner  │       ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       ││
│  └──────────────────────────┬──────────────────────────────────┘│
│                             ▼                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │   Mediator    │  │ LLM Provider  │  │  Tool Provider    │   │
│  │   (CQRS)      │  │ (Ollama/OpenAI)│  │   Client         │   │
│  └───────┬───────┘  └───────────────┘  └─────────┬─────────┘   │
│          │                                       │              │
│          ▼                                       ▼              │
│  ┌───────────────┐                    ┌───────────────────────┐ │
│  │  MongoDB      │                    │   Tools Provider      │ │
│  │ (Motor)       │                    │   (MCP Gateway)       │ │
│  └───────────────┘                    └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# From the tools-provider root directory
make up          # Start Docker services (MongoDB, Redis, Keycloak)
make run-agent   # Run agent-host locally (port 8050)
```

Access the chat UI at <http://localhost:8050>

## Environment Variables

All settings use the `AGENT_HOST_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_HOST_TOOLS_PROVIDER_URL` | `http://tools-provider:8080` | Tools Provider internal URL |
| `AGENT_HOST_OLLAMA_URL` | `http://localhost:11434` | Ollama API URL |
| `AGENT_HOST_OLLAMA_MODEL` | `llama3.2:3b` | Default Ollama model |
| `AGENT_HOST_OPENAI_ENABLED` | `false` | Enable OpenAI provider |
| `AGENT_HOST_OPENAI_API_ENDPOINT` | - | OpenAI/Azure endpoint URL |
| `AGENT_HOST_KEYCLOAK_URL` | `http://localhost:8041` | Keycloak external URL |
| `AGENT_HOST_KEYCLOAK_URL_INTERNAL` | `http://keycloak:8080` | Keycloak internal URL |
| `AGENT_HOST_KEYCLOAK_REALM` | `tools-provider` | Keycloak realm |
| `AGENT_HOST_KEYCLOAK_CLIENT_ID` | `agent-host` | OAuth2 client ID |
| `AGENT_HOST_REDIS_URL` | `redis://redis:6379/2` | Redis URL (database 2) |
| `CONNECTION_STRINGS` | - | JSON: `{"mongo": "mongodb://..."}` |

## Development

```bash
cd src/agent-host
make setup       # Install Poetry deps + Node deps, build UI
make run         # Run with hot-reload on port 8050
make run-debug   # Run with LOG_LEVEL=DEBUG
make build-ui    # Rebuild frontend assets
make test        # Run tests
```

### Project Structure

```
src/agent-host/
├── api/
│   ├── controllers/        # REST + WebSocket endpoints
│   ├── dependencies.py     # FastAPI dependencies (auth, user)
│   └── services/           # AuthService, OpenAPI config
├── application/
│   ├── commands/           # CQRS command handlers
│   ├── queries/            # CQRS query handlers
│   ├── orchestrator/       # Conversation orchestrator
│   ├── protocol/           # WebSocket protocol types
│   ├── websocket/          # Connection manager, router
│   └── agents/             # LLM agent implementation
├── domain/
│   ├── entities/           # AggregateRoots (Conversation, AgentDefinition, ConversationTemplate)
│   ├── models/             # Value objects (ConversationItem, ItemContent, ClientAction)
│   └── events/             # DomainEvents
├── infrastructure/         # LLM providers, session stores
├── integration/            # DTOs, Motor repository implementations
└── ui/
    └── src/scripts/
        ├── protocol/       # WebSocket client
        ├── widgets/        # Web Components
        ├── canvas/         # 2D canvas management
        └── handlers/       # Event handlers
```
