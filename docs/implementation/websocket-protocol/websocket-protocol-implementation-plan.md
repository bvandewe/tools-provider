# WebSocket Protocol v1.0.0 Implementation Plan

**Document Version:** 1.0.0
**Last Updated:** December 18, 2025
**Status:** Planning

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Scope & Objectives](#2-scope--objectives)
3. [Architecture Overview](#3-architecture-overview)
4. [Implementation Phases](#4-implementation-phases)
5. [Milestone Schedule](#5-milestone-schedule)
6. [Risk Assessment](#6-risk-assessment)
7. [Success Criteria](#7-success-criteria)
8. [Dependencies](#8-dependencies)

---

## 1. Executive Summary

This document outlines the implementation plan for the Agent Host WebSocket Protocol v1.0.0, enabling real-time bidirectional communication between the Agent Host backend (Python/FastAPI) and web clients (TypeScript/WebComponents).

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Approach** | Greenfield | Clean slate allows proper architecture alignment with protocol spec |
| **Frontend Stack** | Vanilla TS + WebComponents + Modular SASS | No framework dependencies, maximum portability |
| **Backend Stack** | FastAPI + Starlette WebSockets | Native async support, existing infrastructure |
| **Release Strategy** | Incremental (4 phases) | Reduces risk, enables early validation |
| **Testing Strategy** | Full scope (Unit + Integration + E2E) | Mission-critical real-time communication |

### Deliverables

1. **Backend**: WebSocket infrastructure integrated with Agent Host domain
2. **Frontend**: TypeScript client library + WebComponent widget system
3. **Testing**: Comprehensive test suites at all levels
4. **Documentation**: API docs, integration guides, troubleshooting

---

## 2. Scope & Objectives

### In Scope

| Category | Components |
|----------|------------|
| **Protocol Core** | Connection lifecycle, message routing, error handling, reconnection |
| **Control Plane** | Conversation management, widget lifecycle, flow control, audit telemetry |
| **Data Plane** | Content streaming, tool execution, user messages, response submission |
| **Widget System** | 19 widget types with full configuration and value schemas |
| **Canvas System** | 2D spatial layouts, connections, groups, layers, viewport control |
| **IFRAME Widget** | Secure sandboxed content with bidirectional messaging |
| **Presentation Mode** | Guided tours, bookmarks, step navigation |

### Out of Scope (Future Phases)

- Real-time collaboration (multiple users)
- Voice/video streaming
- Offline-first architecture
- Mobile native implementations

### Integration Points

The WebSocket implementation must integrate with existing Agent Host domain:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Host Domain                         │
├─────────────────────────────────────────────────────────────────┤
│  AgentDefinition  │  ConversationTemplate  │  Conversation      │
│  ConversationItem │  ItemContent           │  Application Cmds  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    WebSocket Protocol Layer                      │
├─────────────────────────────────────────────────────────────────┤
│  Connection Manager  │  Message Router  │  State Sync           │
│  Widget Renderer     │  Canvas Engine   │  Audit Pipeline       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Architecture Overview

### 3.1 Backend Architecture

```
src/agent-host/
├── application/
│   ├── protocol/              # ✅ COMPLETE - Pydantic models
│   │   ├── enums.py
│   │   ├── core.py
│   │   ├── system.py
│   │   ├── control.py
│   │   ├── data.py
│   │   ├── canvas.py
│   │   ├── iframe.py
│   │   ├── audit.py
│   │   └── widgets/
│   │
│   └── websocket/             # 🔲 TO BUILD
│       ├── __init__.py
│       ├── manager.py         # Connection lifecycle manager
│       ├── router.py          # Message type → handler routing
│       ├── handlers/          # Message handlers by category
│       │   ├── system.py
│       │   ├── control.py
│       │   ├── data.py
│       │   └── canvas.py
│       ├── state.py           # Connection state machine
│       └── broadcast.py       # Multi-connection broadcasting
│
├── api/
│   └── controllers/
│       └── websocket_controller.py  # 🔲 WebSocket endpoint
│
├── infrastructure/
│   └── websocket/             # 🔲 TO BUILD
│       ├── redis_pubsub.py    # Cross-instance messaging
│       └── connection_store.py # Connection registry
│
└── domain/
    └── events/                # 🔲 WebSocket domain events
        └── websocket_events.py
```

### 3.2 Frontend Architecture

```
src/agent-host/ui/
├── src/
│   ├── protocol/              # 🔲 TO BUILD
│   │   ├── types.ts           # ✅ COMPLETE - TypeScript interfaces
│   │   ├── client.ts          # WebSocket client class
│   │   ├── reconnect.ts       # Reconnection logic
│   │   ├── message-bus.ts     # Event-based message routing
│   │   └── state-machine.ts   # Connection state management
│   │
│   ├── widgets/               # 🔲 TO BUILD - WebComponents
│   │   ├── base/
│   │   │   ├── widget-base.ts
│   │   │   └── widget-registry.ts
│   │   ├── multiple-choice/
│   │   ├── free-text/
│   │   ├── code-editor/
│   │   ├── slider/
│   │   ├── drag-drop/
│   │   ├── graph-topology/
│   │   ├── document-viewer/
│   │   ├── hotspot/
│   │   ├── drawing/
│   │   ├── file-upload/
│   │   ├── rating/
│   │   ├── date-picker/
│   │   ├── dropdown/
│   │   ├── image/
│   │   ├── video/
│   │   ├── sticky-note/
│   │   ├── matrix-choice/
│   │   └── iframe/
│   │
│   ├── canvas/                # 🔲 TO BUILD
│   │   ├── canvas-engine.ts
│   │   ├── viewport.ts
│   │   ├── connections.ts
│   │   ├── groups.ts
│   │   ├── layers.ts
│   │   └── presentation.ts
│   │
│   ├── styles/                # 🔲 TO BUILD - Modular SASS
│   │   ├── _variables.scss
│   │   ├── _mixins.scss
│   │   ├── _widgets.scss
│   │   ├── _canvas.scss
│   │   └── main.scss
│   │
│   └── index.ts               # Public API exports
│
├── package.json
├── tsconfig.json
└── vite.config.ts             # Or rollup for library bundling
```

### 3.3 Message Flow

```
┌─────────┐                    ┌─────────────┐                    ┌─────────┐
│ Client  │                    │   Server    │                    │ Domain  │
└────┬────┘                    └──────┬──────┘                    └────┬────┘
     │                                │                                │
     │ ──── WebSocket Connect ──────► │                                │
     │                                │                                │
     │ ◄── system.connection.established ──                            │
     │                                │                                │
     │ ──── data.message.send ──────► │                                │
     │                                │ ──── ProcessMessageCommand ───►│
     │                                │                                │
     │                                │ ◄──── DomainEvent ─────────────│
     │                                │                                │
     │ ◄── data.content.chunk ─────── │                                │
     │ ◄── data.content.chunk ─────── │                                │
     │ ◄── data.content.complete ──── │                                │
     │                                │                                │
     │ ◄── data.widget.render ─────── │                                │
     │                                │                                │
     │ ──── data.response.submit ───► │                                │
     │                                │ ──── SubmitResponseCommand ───►│
     │                                │                                │
```

---

## 4. Implementation Phases

### Phase 1: Core Infrastructure (Weeks 1-3)

**Objective:** Establish reliable WebSocket communication foundation.

#### Backend Tasks

| ID | Task | Priority | Effort |
|----|------|----------|--------|
| B1.1 | WebSocket endpoint in FastAPI | P0 | 3d |
| B1.2 | Connection lifecycle manager | P0 | 4d |
| B1.3 | Message router with type discrimination | P0 | 3d |
| B1.4 | System message handlers (connect, ping, error) | P0 | 2d |
| B1.5 | Connection state machine | P0 | 2d |
| B1.6 | Redis PubSub for cross-instance messaging | P1 | 3d |
| B1.7 | Authentication integration (JWT + session) | P0 | 2d |
| B1.8 | Graceful shutdown handling | P1 | 1d |

#### Frontend Tasks

| ID | Task | Priority | Effort |
|----|------|----------|--------|
| F1.1 | WebSocket client class | P0 | 3d |
| F1.2 | Automatic reconnection with backoff | P0 | 2d |
| F1.3 | Connection state machine | P0 | 2d |
| F1.4 | Message bus (pub/sub for handlers) | P0 | 2d |
| F1.5 | Protocol message serialization | P0 | 1d |
| F1.6 | System message handlers | P0 | 1d |
| F1.7 | Connection status UI component | P1 | 1d |
| F1.8 | Debug/logging infrastructure | P1 | 1d |

#### Testing Tasks

| ID | Task | Priority | Effort |
|----|------|----------|--------|
| T1.1 | Backend unit tests for connection manager | P0 | 2d |
| T1.2 | Backend unit tests for message router | P0 | 1d |
| T1.3 | Frontend unit tests for client | P0 | 2d |
| T1.4 | Integration tests: connect/disconnect | P0 | 2d |
| T1.5 | Integration tests: reconnection scenarios | P1 | 2d |

#### Deliverables

- Working WebSocket connection with authentication
- Ping/pong keepalive
- Automatic reconnection
- Error handling and reporting

---

### Phase 2: Control Plane (Weeks 4-6)

**Objective:** Enable conversation and widget lifecycle management.

#### Backend Tasks

| ID | Task | Priority | Effort |
|----|------|----------|--------|
| B2.1 | Conversation config handler | P0 | 2d |
| B2.2 | Widget state management | P0 | 3d |
| B2.3 | Widget validation handler | P0 | 2d |
| B2.4 | Flow control handlers | P0 | 2d |
| B2.5 | Navigation handlers | P0 | 1d |
| B2.6 | Audit telemetry pipeline | P1 | 3d |
| B2.7 | Domain event → WebSocket broadcast | P0 | 3d |
| B2.8 | Conversation state persistence | P0 | 2d |

#### Frontend Tasks

| ID | Task | Priority | Effort |
|----|------|----------|--------|
| F2.1 | WebComponent base class | P0 | 3d |
| F2.2 | Widget registry and factory | P0 | 2d |
| F2.3 | Widget lifecycle management | P0 | 2d |
| F2.4 | Control message handlers | P0 | 2d |
| F2.5 | Conversation state store | P0 | 2d |
| F2.6 | Widget validation display | P0 | 1d |
| F2.7 | Navigation controls | P0 | 1d |
| F2.8 | Audit event collection | P1 | 2d |

#### Testing Tasks

| ID | Task | Priority | Effort |
|----|------|----------|--------|
| T2.1 | Widget lifecycle unit tests | P0 | 2d |
| T2.2 | State management unit tests | P0 | 2d |
| T2.3 | Integration: conversation flow | P0 | 3d |
| T2.4 | Integration: widget render/validate | P0 | 2d |

#### Deliverables

- Conversation initialization and configuration
- Widget rendering infrastructure
- State synchronization
- Validation feedback

---

### Phase 3: Data Plane (Weeks 7-9)

**Objective:** Enable content streaming, tool execution, and response handling.

#### Backend Tasks

| ID | Task | Priority | Effort |
|----|------|----------|--------|
| B3.1 | Content streaming (chunked) | P0 | 3d |
| B3.2 | Tool call dispatch | P0 | 3d |
| B3.3 | Tool result handling | P0 | 2d |
| B3.4 | User message processing | P0 | 2d |
| B3.5 | Response submission handler | P0 | 2d |
| B3.6 | Integration with AI agent backend | P0 | 4d |
| B3.7 | Rate limiting for data messages | P1 | 2d |

#### Frontend Tasks

| ID | Task | Priority | Effort |
|----|------|----------|--------|
| F3.1 | Content streaming display | P0 | 2d |
| F3.2 | Markdown/HTML rendering | P0 | 2d |
| F3.3 | Tool call UI (pending states) | P0 | 2d |
| F3.4 | Message input component | P0 | 2d |
| F3.5 | Response submission logic | P0 | 2d |
| F3.6 | Progress indicators | P1 | 1d |

#### Testing Tasks

| ID | Task | Priority | Effort |
|----|------|----------|--------|
| T3.1 | Streaming unit tests | P0 | 2d |
| T3.2 | Tool execution integration tests | P0 | 3d |
| T3.3 | E2E: Full conversation flow | P0 | 4d |

#### Deliverables

- Real-time content streaming
- Tool execution flow
- User message handling
- Response submission

---

### Phase 4: Advanced Features (Weeks 10-14)

**Objective:** Complete widget catalog, canvas system, and IFRAME support.

#### 4A: Widget Catalog (Weeks 10-11)

| ID | Widget | Priority | Effort |
|----|--------|----------|--------|
| W4.1 | Multiple Choice | P0 | 2d |
| W4.2 | Free Text | P0 | 1d |
| W4.3 | Code Editor | P1 | 3d |
| W4.4 | Slider | P0 | 1d |
| W4.5 | Drag & Drop | P1 | 4d |
| W4.6 | Graph Topology | P2 | 5d |
| W4.7 | Matrix Choice | P1 | 2d |
| W4.8 | Document Viewer | P1 | 3d |
| W4.9 | Hotspot | P1 | 3d |
| W4.10 | Drawing | P2 | 4d |
| W4.11 | File Upload | P1 | 2d |
| W4.12 | Rating | P0 | 1d |
| W4.13 | Date Picker | P0 | 1d |
| W4.14 | Dropdown | P0 | 1d |
| W4.15 | Image | P0 | 1d |
| W4.16 | Video | P1 | 3d |
| W4.17 | Sticky Note | P1 | 1d |

#### 4B: Canvas System (Weeks 12-13)

| ID | Task | Priority | Effort |
|----|------|----------|--------|
| C4.1 | Canvas engine (pan/zoom) | P1 | 4d |
| C4.2 | Viewport management | P1 | 2d |
| C4.3 | Widget positioning | P1 | 2d |
| C4.4 | Connection rendering | P1 | 3d |
| C4.5 | Group management | P2 | 2d |
| C4.6 | Layer system | P2 | 2d |
| C4.7 | Presentation mode | P2 | 3d |
| C4.8 | Bookmarks | P2 | 1d |
| C4.9 | Minimap | P2 | 2d |

#### 4C: IFRAME Widget (Week 14)

| ID | Task | Priority | Effort |
|----|------|----------|--------|
| I4.1 | IFRAME widget component | P1 | 2d |
| I4.2 | Sandbox configuration | P1 | 1d |
| I4.3 | PostMessage bridge | P1 | 2d |
| I4.4 | State synchronization | P1 | 2d |
| I4.5 | Security validation | P0 | 2d |

#### Testing Tasks

| ID | Task | Priority | Effort |
|----|------|----------|--------|
| T4.1 | Widget unit tests (all 19) | P0 | 5d |
| T4.2 | Canvas integration tests | P1 | 3d |
| T4.3 | IFRAME security tests | P0 | 2d |
| T4.4 | E2E: Canvas interactions | P1 | 3d |
| T4.5 | E2E: Widget catalog | P0 | 3d |

---

## 5. Milestone Schedule

```
Week  1  2  3  4  5  6  7  8  9  10 11 12 13 14
      ├──────────┼───────────┼───────────┼─────────────────┤
      │ Phase 1  │  Phase 2  │  Phase 3  │     Phase 4     │
      │   Core   │  Control  │   Data    │    Advanced     │
      └──────────┴───────────┴───────────┴─────────────────┘

Milestones:
  M1 (Week 3):  WebSocket connection works, reconnects, authenticated
  M2 (Week 6):  Widgets render, state syncs, validation works
  M3 (Week 9):  Full conversation flow with streaming
  M4 (Week 11): All P0/P1 widgets complete
  M5 (Week 14): Canvas and IFRAME complete, production-ready
```

### Release Checkpoints

| Milestone | Date | Scope | Release Type |
|-----------|------|-------|--------------|
| M1 | Week 3 | Core infrastructure | Internal alpha |
| M2 | Week 6 | Control plane | Internal beta |
| M3 | Week 9 | Data plane | Staging release |
| M4 | Week 11 | Widget catalog | Staging release |
| M5 | Week 14 | Full protocol | Production release |

---

## 6. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| WebSocket scaling issues | Medium | High | Early Redis PubSub integration, load testing |
| Browser compatibility | Low | Medium | Target modern browsers, progressive enhancement |
| Canvas performance | Medium | Medium | Virtual rendering, spatial indexing |
| IFRAME security | Low | High | Strict CSP, sandbox defaults, origin validation |
| AI backend integration | Medium | High | Mock endpoints early, clear API contracts |
| Widget complexity | High | Medium | Start with simple widgets, defer complex ones |

---

## 7. Success Criteria

### Phase 1 Success

- [ ] WebSocket connects with < 500ms latency
- [ ] Reconnection works within 5 attempts
- [ ] Authentication integrates with existing Keycloak
- [ ] 100% unit test coverage for connection manager

### Phase 2 Success

- [ ] Widget renders within 100ms of message receipt
- [ ] State syncs correctly on reconnection
- [ ] Validation errors display immediately
- [ ] Audit events capture at configured rate

### Phase 3 Success

- [ ] Streaming content displays progressively
- [ ] Tool calls complete end-to-end
- [ ] User messages persist to domain
- [ ] E2E tests pass for conversation flow

### Phase 4 Success

- [ ] All P0/P1 widgets functional
- [ ] Canvas pan/zoom smooth at 60fps
- [ ] IFRAME communication secure
- [ ] Full E2E test suite passes

---

## 8. Dependencies

### External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.109+ | WebSocket endpoints |
| Starlette | 0.35+ | WebSocket protocol |
| Redis | 7.0+ | PubSub for scaling |
| TypeScript | 5.3+ | Frontend type safety |
| Vite/Rollup | Latest | Build tooling |

### Internal Dependencies

| Dependency | Status | Required By |
|------------|--------|-------------|
| Protocol Pydantic models | ✅ Complete | Phase 1 |
| Protocol TypeScript types | ✅ Complete | Phase 1 |
| Agent Host domain | ✅ Exists | Phase 2 |
| Keycloak integration | ✅ Exists | Phase 1 |
| EventStoreDB | ✅ Exists | Phase 2 |

---

## Related Documents

- [Backend Implementation Guide](./backend-implementation-guide.md)
- [Frontend Implementation Guide](./frontend-implementation-guide.md)
- [Testing Strategy](./testing-strategy.md)
- [Protocol Specification](../specs/websocket-protocol-v1.md)
- [TypeScript Interfaces](../specs/websocket-protocol-v1.types.ts)

---

_Document maintained by: Development Team_
_Last review: December 18, 2025_
