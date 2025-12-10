# Proactive Agent: Implementation Plan

**Version:** 1.0.0
**Date:** December 10, 2025
**Status:** `ACTIVE`

---

## Overview

This document provides the detailed implementation plan for the Proactive Agent MVP. Each task includes acceptance criteria, dependencies, and estimated effort.

**Estimation Key:**

- **S** = Small (2-4 hours)
- **M** = Medium (4-8 hours / 1 day)
- **L** = Large (2-3 days)
- **XL** = Extra Large (3-5 days)

---

## Phase 1: Core Infrastructure (Week 1-3)

### Week 1: Domain Model

#### 1.1 Session Enums & Value Objects

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Create `SessionType` enum | S | | ☐ |
| Create `ControlMode` enum | S | | ☐ |
| Create `SessionStatus` enum | S | | ☐ |
| Create `ValidationStatus` enum | S | | ☐ |
| Create `SessionConfig` dataclass | S | | ☐ |
| Create `SessionItem` dataclass | M | | ☐ |
| Create `ClientAction` dataclass | M | | ☐ |
| Create `ClientResponse` dataclass | S | | ☐ |
| Create `UiState` dataclass | S | | ☐ |

**File:** `src/agent-host/domain/models/session_models.py`

**Acceptance Criteria:**

- All value objects are immutable (frozen dataclasses)
- `ClientAction.to_sse_payload()` returns dict ready for JSON serialization
- Unit tests for serialization/deserialization

---

#### 1.2 Session Domain Events

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Create `SessionCreatedDomainEvent` | S | | ☐ |
| Create `SessionStartedDomainEvent` | S | | ☐ |
| Create `SessionCompletedDomainEvent` | S | | ☐ |
| Create `SessionTerminatedDomainEvent` | S | | ☐ |
| Create `SessionExpiredDomainEvent` | S | | ☐ |
| Create `SessionItemStartedDomainEvent` | S | | ☐ |
| Create `SessionItemCompletedDomainEvent` | S | | ☐ |
| Create `PendingActionSetDomainEvent` | S | | ☐ |
| Create `PendingActionClearedDomainEvent` | S | | ☐ |
| Create `ResponseSubmittedDomainEvent` | S | | ☐ |

**File:** `src/agent-host/domain/events/session_events.py`

**Acceptance Criteria:**

- All events decorated with `@cloudevent("session.*.v1")`
- Events contain only primitive/serializable data
- Unit tests for event creation

---

#### 1.3 Session Aggregate

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Create `SessionState` class | M | | ☐ |
| Create `Session` aggregate root | L | | ☐ |
| Implement `Session.create()` factory | M | | ☐ |
| Implement `Session.start()` | S | | ☐ |
| Implement `Session.set_pending_action()` | M | | ☐ |
| Implement `Session.submit_response()` | M | | ☐ |
| Implement `Session.complete()` | S | | ☐ |
| Implement `Session.terminate()` | S | | ☐ |
| Implement `Session.expire()` | S | | ☐ |
| Implement state query methods | S | | ☐ |
| Add `@dispatch` event handlers | M | | ☐ |

**File:** `src/agent-host/domain/entities/session.py`

**Acceptance Criteria:**

- Aggregate follows Neuroglia patterns (see `Task` in tools-provider)
- All state changes emit domain events
- Invalid state transitions raise `DomainError`
- Unit tests: >95% coverage

---

#### 1.4 Session Repository

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Create `SessionRepository` interface | S | | ☐ |
| Create `SessionDto` for read model | M | | ☐ |
| Implement `MongoSessionRepository` | M | | ☐ |

**Files:**

- `src/agent-host/domain/repositories/session_repository.py`
- `src/agent-host/integration/models/session_dto.py`
- `src/agent-host/integration/repositories/mongo_session_repository.py`

**Acceptance Criteria:**

- Repository interface matches `ConversationRepository` pattern
- DTO decorated with `@queryable`
- Integration test with real MongoDB

---

### Week 2: API Layer

#### 2.1 Session Commands

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Create `CreateSessionCommand` | M | | ☐ |
| Create `CreateSessionCommandHandler` | L | | ☐ |
| Create `SubmitClientResponseCommand` | M | | ☐ |
| Create `SubmitClientResponseCommandHandler` | L | | ☐ |
| Create `TerminateSessionCommand` | S | | ☐ |
| Create `TerminateSessionCommandHandler` | M | | ☐ |

**Directory:** `src/agent-host/application/commands/`

**Acceptance Criteria:**

- Commands return `OperationResult[SessionDto]`
- Handlers use `UnitOfWork` for persistence
- Command tests: >90% coverage

---

#### 2.2 Session Queries

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Create `GetSessionQuery` | S | | ☐ |
| Create `GetSessionQueryHandler` | M | | ☐ |
| Create `GetUserSessionsQuery` | S | | ☐ |
| Create `GetUserSessionsQueryHandler` | M | | ☐ |
| Create `GetSessionStateQuery` | S | | ☐ |
| Create `GetSessionStateQueryHandler` | M | | ☐ |

**Directory:** `src/agent-host/application/queries/`

**Acceptance Criteria:**

- Queries use read model (MongoDB)
- Proper authorization checks (user can only see own sessions)
- Query tests: >90% coverage

---

#### 2.3 Session Controller

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Create `SessionController` class | M | | ☐ |
| Implement `POST /api/sessions` | M | | ☐ |
| Implement `GET /api/sessions` | S | | ☐ |
| Implement `GET /api/sessions/{id}` | S | | ☐ |
| Implement `DELETE /api/sessions/{id}` | S | | ☐ |
| Implement `POST /api/sessions/{id}/respond` | M | | ☐ |
| Implement `GET /api/sessions/{id}/state` | M | | ☐ |
| Implement `GET /api/sessions/{id}/stream` (SSE) | L | | ☐ |

**File:** `src/agent-host/api/controllers/session_controller.py`

**Acceptance Criteria:**

- Controller follows `classy-fastapi` patterns
- All endpoints require authentication
- SSE endpoint streams session events
- API tests with TestClient

---

### Week 3: Integration & Testing

#### 3.1 Session-Conversation Integration

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Wire Session creation to Conversation creation | M | | ☐ |
| Update main.py DataAccessLayer config | M | | ☐ |
| Add Session projections for read model | L | | ☐ |
| Implement state restoration logic | M | | ☐ |

**Acceptance Criteria:**

- Creating a Session also creates linked Conversation
- Session events project to MongoDB read model
- State endpoint returns correct pending action

---

#### 3.2 Phase 1 Testing

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Unit tests: Domain models | L | | ☐ |
| Unit tests: Session aggregate | L | | ☐ |
| Unit tests: Commands | M | | ☐ |
| Unit tests: Queries | M | | ☐ |
| Integration tests: Repository | M | | ☐ |
| Integration tests: API endpoints | L | | ☐ |

**Acceptance Criteria:**

- Coverage report: >90% on domain layer
- All tests pass in CI

---

## Phase 2: MVP Widgets + Agent (Week 4-7)

### Week 4: Client Tool System

#### 4.1 Client Tool Registry

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Create `ClientToolDefinition` dataclass | M | | ☐ |
| Define `present_choices` tool | S | | ☐ |
| Define `request_free_text` tool | S | | ☐ |
| Define `present_code_editor` tool | S | | ☐ |
| Implement `is_client_tool()` helper | S | | ☐ |
| Implement `get_client_tool_manifest()` | M | | ☐ |
| Implement response validation logic | M | | ☐ |

**File:** `src/agent-host/application/agents/client_tools.py`

**Acceptance Criteria:**

- Tool definitions match JSON Schema format
- `get_client_tool_manifest()` returns LLM-compatible format
- Validation accepts valid responses, flags invalid gracefully

---

#### 4.2 Tool Interception

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Add `CLIENT_ACTION` to `AgentEventType` | S | | ☐ |
| Add `RUN_SUSPENDED` to `AgentEventType` | S | | ☐ |
| Add `RUN_RESUMED` to `AgentEventType` | S | | ☐ |
| Implement tool call interception in agent | L | | ☐ |
| Implement SSE emission for `client_action` | M | | ☐ |

**Files:**

- `src/agent-host/application/agents/base_agent.py`
- `src/agent-host/api/services/sse_service.py` (if needed)

**Acceptance Criteria:**

- Client tool calls do NOT go to tools-provider
- SSE stream emits `client_action` event with correct payload
- Server tools still route to tools-provider

---

### Week 5: Proactive Agent

#### 5.1 Proactive Agent Class

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Create `ProactiveAgent` class | M | | ☐ |
| Implement `start_session()` method | L | | ☐ |
| Implement `resume_with_response()` method | L | | ☐ |
| Implement `_proactive_loop()` | XL | | ☐ |
| Implement `_validate_response()` | M | | ☐ |
| Implement `_build_system_message()` | M | | ☐ |

**File:** `src/agent-host/application/agents/proactive_agent.py`

**Acceptance Criteria:**

- Agent loop suspends when client tool is called
- Agent resumes correctly with user response
- System prompts are session-type-specific
- Agent tests with mocked LLM

---

#### 5.2 Agent Factory Update

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Update agent factory for session type | M | | ☐ |
| Wire ProactiveAgent to session controller | M | | ☐ |
| Implement streaming integration | L | | ☐ |

**Acceptance Criteria:**

- Session type determines agent type (reactive vs proactive)
- Streaming works for proactive sessions

---

### Week 6: Frontend Widgets (Part 1)

#### 6.1 Frontend Infrastructure

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Update stream handler for `client_action` | M | | ☐ |
| Update stream handler for `state` | M | | ☐ |
| Create `ax-client-action-renderer` | L | | ☐ |
| Implement chat input lock/unlock | M | | ☐ |
| Implement widget component registration | M | | ☐ |

**Directory:** `src/agent-host/ui/src/`

**Acceptance Criteria:**

- `client_action` events render correct widget
- Chat input disabled when widget active
- Widget responses POST to `/api/sessions/{id}/respond`

---

#### 6.2 Multiple Choice Widget

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Create `ax-multiple-choice` component | L | | ☐ |
| Implement option rendering | M | | ☐ |
| Implement selection state | M | | ☐ |
| Implement `ax-response` event emission | S | | ☐ |
| Style component (CSS) | M | | ☐ |
| Add keyboard navigation | S | | ☐ |
| Add ARIA accessibility | S | | ☐ |

**File:** `src/agent-host/ui/src/components/ax-multiple-choice.js`

**Acceptance Criteria:**

- Renders options as buttons
- Click/tap selects option
- Emits `{selection, index}` on selection
- Keyboard: Arrow keys navigate, Enter selects
- Screen reader compatible

---

#### 6.3 Free Text Widget

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Create `ax-free-text-prompt` component | L | | ☐ |
| Implement textarea with character count | M | | ☐ |
| Implement min/max length validation | M | | ☐ |
| Implement submit button state | S | | ☐ |
| Style component (CSS) | M | | ☐ |
| Add ARIA accessibility | S | | ☐ |

**File:** `src/agent-host/ui/src/components/ax-free-text-prompt.js`

**Acceptance Criteria:**

- Renders prompt + textarea
- Character count updates in real-time
- Submit disabled until min length met
- Emits `{text}` on submit

---

### Week 7: Code Editor Widget

#### 7.1 Monaco Integration

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Install Monaco Editor package | S | | ☐ |
| Configure Parcel for Monaco workers | M | | ☐ |
| Create Monaco loader utility | L | | ☐ |
| Test lazy loading | M | | ☐ |

**Acceptance Criteria:**

- Monaco loads on-demand (not in initial bundle)
- Web workers configured correctly
- Python syntax highlighting works

---

#### 7.2 Code Editor Widget

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Create `ax-code-editor` component | L | | ☐ |
| Implement Monaco initialization | L | | ☐ |
| Implement language selection | M | | ☐ |
| Implement initial code support | S | | ☐ |
| Implement submit button | S | | ☐ |
| Style component (CSS) | M | | ☐ |
| Add resize handle | M | | ☐ |

**File:** `src/agent-host/ui/src/components/ax-code-editor.js`

**Acceptance Criteria:**

- Monaco editor renders correctly
- Python syntax highlighting works
- Initial code populates editor
- Emits `{code}` on submit
- Editor resizable

---

#### 7.3 Integration Testing

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Integration test: multiple_choice flow | L | | ☐ |
| Integration test: free_text flow | L | | ☐ |
| Integration test: code_editor flow | L | | ☐ |
| Integration test: mixed widget session | XL | | ☐ |

**Acceptance Criteria:**

- Full round-trip: Agent → Widget → Response → Agent
- State restoration after refresh

---

## Phase 3: Polish & Demo (Week 8-9)

### Week 8: E2E Testing & Sample Data

#### 8.1 E2E Test Suite

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Setup Playwright test infrastructure | M | | ☐ |
| E2E: Start LearningSession | L | | ☐ |
| E2E: Complete multiple choice question | L | | ☐ |
| E2E: Complete free text question | L | | ☐ |
| E2E: Complete code editor question | L | | ☐ |
| E2E: Session completion flow | L | | ☐ |
| E2E: Page refresh state restoration | L | | ☐ |
| E2E: Session termination | M | | ☐ |
| E2E: Error handling scenarios | L | | ☐ |

**Directory:** `src/agent-host/tests/e2e/`

**Acceptance Criteria:**

- All E2E tests pass in CI
- Tests run against real backend (not mocked)
- Coverage of happy path + key edge cases

---

#### 8.2 Sample Question Bank

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Design Mathematics question schema | M | | ☐ |
| Create Algebra questions (5) | M | | ☐ |
| Create Geometry questions (5) | M | | ☐ |
| Create Coding challenges (5) | L | | ☐ |
| Create question bank API/service | L | | ☐ |
| Integrate with ProactiveAgent | M | | ☐ |

**Files:**

- `src/agent-host/infrastructure/services/question_bank_service.py`
- `src/agent-host/data/sample_questions.json`

**Acceptance Criteria:**

- 15 sample questions across 3 categories
- Questions include: text, multiple choice options, expected answers
- Coding challenges include: prompt, initial code, test cases

---

### Week 9: Demo Preparation

#### 9.1 Demo Script

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Write demo script (5-minute walkthrough) | M | | ☐ |
| Create demo user account | S | | ☐ |
| Pre-seed demo data | S | | ☐ |
| Practice demo flow | M | | ☐ |
| Prepare backup demo (video) | M | | ☐ |

**Acceptance Criteria:**

- Demo script covers all 3 widgets
- Demo can be given by any team member
- Backup video in case of technical issues

---

#### 9.2 Documentation

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Update README with proactive agent | M | | ☐ |
| Update mkdocs site | M | | ☐ |
| Create widget developer guide | L | | ☐ |
| Update API documentation | M | | ☐ |
| Update CHANGELOG | S | | ☐ |

**Acceptance Criteria:**

- All new endpoints documented
- Widget guide explains how to add new widgets
- mkdocs site builds without errors

---

#### 9.3 Final Polish

| Task | Size | Owner | Status |
|------|------|-------|--------|
| Fix any remaining bugs | L | | ☐ |
| Performance optimization | M | | ☐ |
| Accessibility audit | M | | ☐ |
| 48-hour soak test | - | | ☐ |
| Final code review | M | | ☐ |

**Acceptance Criteria:**

- No critical bugs
- Widget response time <100ms
- State restoration <500ms
- All accessibility issues resolved

---

## Task Summary by Phase

| Phase | Total Tasks | Estimated Effort |
|-------|-------------|------------------|
| Phase 1: Infrastructure | 45 | 3 weeks |
| Phase 2: Widgets + Agent | 42 | 4 weeks |
| Phase 3: Polish + Demo | 25 | 2 weeks |
| **Total** | **112** | **9 weeks** |

---

## Definition of Done

A task is considered **DONE** when:

1. ✅ Code implemented and self-reviewed
2. ✅ Unit tests written (>90% coverage for new code)
3. ✅ Integration tests pass
4. ✅ Code passes linting (ruff, prettier)
5. ✅ Documentation updated (if applicable)
6. ✅ PR reviewed and approved
7. ✅ Merged to main branch
8. ✅ Deployed to dev environment

---

## Dependencies Graph

```
Phase 1 (Foundation)
├── 1.1 Enums/Value Objects ──┐
├── 1.2 Domain Events ────────┼──► 1.3 Session Aggregate ──► 1.4 Repository
│                             │
└─────────────────────────────┘
                                        │
                                        ▼
Phase 2 (Features)                  2.1 Commands ──┐
                                    2.2 Queries ───┼──► 2.3 Controller
                                                   │
        4.1 Client Tool Registry ──────────────────┼──► 5.1 ProactiveAgent
                                                   │
        6.1 Frontend Infrastructure ───────────────┼──► 6.2 Multiple Choice
                                                   │    6.3 Free Text
                                                   │
        7.1 Monaco Integration ────────────────────┴──► 7.2 Code Editor

Phase 3 (Quality)
├── 8.1 E2E Tests
├── 8.2 Sample Question Bank
└── 9.x Demo + Polish
```

---

## Risk Register

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| Monaco bundle too large | Medium | Medium | Lazy load, tree shaking | |
| SSE reconnection issues | Low | High | State endpoint, heartbeat | |
| LLM hallucinating wrong tools | Low | Medium | Clear system prompts | |
| Test flakiness | Medium | Medium | Retry logic, deterministic tests | |
| Scope creep | Medium | High | Freeze scope after Phase 1 | |

---

## Communication Plan

| Event | Frequency | Audience | Format |
|-------|-----------|----------|--------|
| Daily standup | Daily | Team | Sync/Async |
| Sprint review | Weekly | Stakeholders | Demo |
| Roadmap update | Bi-weekly | Executives | Email/Deck |
| Milestone completion | On milestone | All | Announcement |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-10 | AI Assistant | Initial plan |
