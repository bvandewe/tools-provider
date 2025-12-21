# WebSocket Protocol v1.0.0 - Implementation Documents Index

**Last Updated:** December 18, 2025

---

## ⚠️ CRITICAL: Start Here

> **This is a foundational infrastructure change.**
>
> Before implementing ANY code:
>
> 1. **Read the [Implementation Prompt Template](./implementation-prompt-template.md)** - Required workflow
> 2. **Read the [Pattern Discovery Reference](./pattern-discovery-reference.md)** - Verified imports
> 3. **DO NOT guess Neuroglia imports** - They must be verified from the codebase

---

## Overview

This directory contains all implementation documentation for the WebSocket Protocol v1.0.0 feature. These documents provide sufficient detail to implement the complete system in a new development session.

---

## Document Inventory

### 🚨 Safety Documents (Read First)

| Document | Purpose |
|----------|---------|
| **[Implementation Prompt Template](./implementation-prompt-template.md)** | Standardized prompt for safe implementation |
| **[Pattern Discovery Reference](./pattern-discovery-reference.md)** | Verified Neuroglia imports and patterns |

### Specifications (Reference)

| Document | Location | Description |
|----------|----------|-------------|
| Protocol Specification | [websocket-protocol-v1.md](../../specs/websocket-protocol-v1.md) | Complete protocol spec (~5400 lines) |
| TypeScript Types | [websocket-protocol-v1.types.ts](../../specs/websocket-protocol-v1.types.ts) | All protocol interfaces (~1541 lines) |

### Implementation Guides

| Document | Location | Description |
|----------|----------|-------------|
| **Implementation Plan** | [websocket-protocol-implementation-plan.md](./websocket-protocol-implementation-plan.md) | Master plan with phases, milestones, risks |
| **Backend Guide** | [backend-implementation-guide.md](./backend-implementation-guide.md) | Python/FastAPI patterns (⚠️ verify imports) |
| **Frontend Guide** | [frontend-implementation-guide.md](./frontend-implementation-guide.md) | TypeScript/WebComponents patterns |
| **Testing Strategy** | [testing-strategy.md](./testing-strategy.md) | Test pyramid, tools, CI/CD |

### Phase Task Breakdowns

| Phase | Document | Duration | Focus |
|-------|----------|----------|-------|
| **Phase 1** | [phase-1-core-infrastructure.md](./phase-1-core-infrastructure.md) | Weeks 1-3 | WebSocket transport, connection management |
| **Phase 2** | [phase-2-control-plane.md](./phase-2-control-plane.md) | Weeks 4-6 | Widget lifecycle, state management |
| **Phase 3** | [phase-3-data-plane.md](./phase-3-data-plane.md) | Weeks 7-9 | Content streaming, tool execution |
| **Phase 4** | [phase-4-advanced-features.md](./phase-4-advanced-features.md) | Weeks 10-14 | Widget catalog, canvas, IFRAME |
| **Phase 5** | [phase-5-frontend-architecture.md](./phase-5-frontend-architecture.md) | Weeks 15-22 | **JS/SASS refactor, all 19 widgets, admin UI, canvas completion** |

### Existing Python Models

Located at `src/agent-host/application/protocol/`:

| Module | Content |
|--------|---------|
| `__init__.py` | Package exports |
| `enums.py` | All protocol enumerations |
| `core.py` | Base message classes |
| `system.py` | System message payloads |
| `audit.py` | Audit event payloads |
| `control.py` | Control message payloads |
| `data.py` | Data message payloads |
| `canvas.py` | Canvas message payloads |
| `iframe.py` | IFRAME message payloads |
| `widgets/` | Widget-specific configs |

---

## Quick Start for New Session

### ⚠️ Safe Implementation Workflow

1. **🚨 Read [Implementation Prompt Template](./implementation-prompt-template.md)** - Copy the prompt template
2. **🚨 Read [Pattern Discovery Reference](./pattern-discovery-reference.md)** - Verified imports only
3. **Read [Implementation Plan](./websocket-protocol-implementation-plan.md)** - Understand phases
4. **Choose a Phase** - Start with Phase 1 if greenfield
5. **Read existing code first:**
   - `src/agent-host/application/commands/conversation/create_conversation_command.py`
   - `src/agent-host/application/commands/command_handler_base.py`
6. **Use Phase Documents** - For specific task checklists
7. **Reference Protocol Spec** - For message format details

### What NOT to Do

❌ Do NOT copy code from backend-implementation-guide.md without verifying imports
❌ Do NOT guess Neuroglia imports
❌ Do NOT skip reading existing codebase patterns

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Browser)                     │
├─────────────────────────────────────────────────────────────┤
│  WebSocketClient → MessageBus → WidgetManager → Widgets     │
│                                      ↓                       │
│                              CanvasManager                   │
└───────────────────────────────┬─────────────────────────────┘
                                │ WebSocket
                                ↓
┌─────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                      │
├─────────────────────────────────────────────────────────────┤
│  WebSocket Endpoint → ConnectionManager → MessageRouter      │
│                              ↓                               │
│                    Handler Registry (System/Control/Data)    │
│                              ↓                               │
│                      Domain Commands                         │
│                              ↓                               │
│                      Agent Service (LLM)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend Framework | Vanilla TypeScript + WebComponents | User requirement, no framework |
| Build Tool | Vite | Fast HMR, modern ES modules |
| Backend WebSocket | Starlette native | Already in FastAPI |
| Scaling | Redis PubSub | Multi-instance broadcasting |
| State Management | Event-driven, per-connection | Simple, testable |
| Widget Isolation | Shadow DOM | Style encapsulation |

---

## Milestone Schedule

| Week | Milestone | Deliverable |
|------|-----------|-------------|
| 3 | M1 | WebSocket connects, system messages work |
| 6 | M2 | Widget lifecycle, state persistence |
| 9 | M3 | Full conversation with streaming |
| 14 | M4 | All widgets, canvas, IFRAME complete |

---

## File Structure (Target)

### Backend

```
src/agent-host/
├── application/
│   ├── protocol/           # ✅ EXISTS - Pydantic models
│   ├── websocket/          # TO CREATE
│   │   ├── connection_manager.py
│   │   ├── message_router.py
│   │   ├── handlers/
│   │   │   ├── system_handlers.py
│   │   │   ├── control_handlers.py
│   │   │   └── data_handlers.py
│   │   └── middleware/
│   │       └── rate_limit.py
│   └── events/
│       └── websocket/      # Domain event handlers
├── api/
│   └── controllers/
│       └── websocket_controller.py  # WebSocket endpoint
└── infrastructure/
    └── redis/
        └── pubsub.py       # Redis PubSub adapter
```

### Frontend

```
src/agent-host/ui/src/
├── types/
│   └── protocol.ts         # Copy from specs/
├── core/
│   ├── client.ts          # WebSocketClient
│   ├── reconnection.ts    # ReconnectionManager
│   ├── message-bus.ts     # MessageBus
│   └── state.ts           # StateManager
├── protocol/
│   ├── handlers/          # Message handlers
│   └── serialization.ts   # JSON serialization
├── widgets/
│   ├── base/
│   │   └── widget-base.ts
│   ├── registry.ts
│   ├── factory.ts
│   ├── display/           # Display widgets
│   └── input/             # Input widgets
├── canvas/
│   ├── canvas-manager.ts
│   ├── canvas-element.ts
│   └── connection.ts
├── components/
│   └── connection-status.ts
└── styles/
    ├── _variables.scss
    └── widgets/
```

---

## Related Resources

- [Copilot Instructions](../../.github/copilot-instructions.md) - Coding standards
- [Agent Host README](../../src/agent-host/README.md) - App overview
- [CQRS Pattern](../architecture/cqrs-pattern.md) - Command/Query pattern

---

_This index ensures all implementation context is discoverable for future development sessions._
