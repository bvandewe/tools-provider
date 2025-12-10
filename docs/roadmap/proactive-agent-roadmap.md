# Proactive Agent: Executive Roadmap

**Version:** 1.0.0
**Date:** December 10, 2025
**Status:** `APPROVED`

---

## Executive Summary

This roadmap outlines the delivery of **Proactive Agent** capabilities for the Agent Host platform. Unlike the current Reactive Agent (user-driven chat), the Proactive Agent **drives conversations** using structured UI widgets—enabling guided learning, assessments, surveys, and approval workflows.

### Business Value

| Capability | Impact |
|------------|--------|
| **Guided Learning** | Agent-led skill development with structured inputs |
| **Code Assessment** | Real-time code editor for technical evaluations |
| **Data Collection** | Surveys and forms with validation |
| **Decision Workflows** | Approval chains with confirmation dialogs |

### Target: MVP Demo

- **3 Core Widgets:** Multiple Choice, Free Text, Code Editor (Monaco)
- **1 Session Type:** LearningSession (Mathematics domain)
- **Full Test Coverage:** >90% unit, integration, E2E

---

## Timeline Overview

```
Dec 2025                        Jan 2026                        Feb 2026
   |                               |                               |
   ├── Phase 1 ──────────────────► │                               │
   │   Core Infrastructure         │                               │
   │   (3 weeks)                   │                               │
   │                               ├── Phase 2 ──────────────────► │
   │                               │   MVP Widgets + Agent          │
   │                               │   (4 weeks)                    │
   │                               │                               ├── Phase 3 ────►
   │                               │                               │   Polish + Demo
   │                               │                               │   (2 weeks)
   │                               │                               │
   ▼                               ▼                               ▼
Week 1-3                       Week 4-7                       Week 8-9
```

**Total Estimated Duration: 9-11 weeks**

---

## Phase 1: Core Infrastructure

**Duration:** 3 weeks
**Goal:** Session management foundation, ready for agent integration

### Milestones

| Week | Milestone | Deliverable |
|------|-----------|-------------|
| 1 | Domain Model | Session aggregate, events, repository |
| 2 | API Layer | Session CRUD, SSE streaming endpoints |
| 3 | Integration | Session ↔ Conversation wiring, state persistence |

### Success Criteria

- [ ] Session aggregate with full event sourcing
- [ ] Session API endpoints functional (create, get, respond, stream)
- [ ] State restoration works after page refresh
- [ ] Unit tests: >90% coverage on domain layer

### Key Risks

| Risk | Mitigation |
|------|------------|
| Event schema design churn | Freeze schema after Week 1 design review |
| MongoDB/EventStoreDB sync issues | Reuse proven patterns from tools-provider |

---

## Phase 2: MVP Widgets + Proactive Agent

**Duration:** 4 weeks
**Goal:** Working proactive agent with 3 core widgets

### Milestones

| Week | Milestone | Deliverable |
|------|-----------|-------------|
| 4 | Client Tool System | Tool registry, interception, SSE events |
| 5 | Proactive Agent | Agent loop with suspension/resumption |
| 6 | Frontend Widgets | Multiple Choice, Free Text components |
| 7 | Code Editor | Monaco integration, syntax highlighting |

### Success Criteria

- [ ] Agent can present `multiple_choice` and receive response
- [ ] Agent can request `free_text` input
- [ ] Agent can present `code_editor` with Python syntax highlighting
- [ ] Agent loop suspends/resumes correctly
- [ ] Chat input locks when widget is active
- [ ] Integration tests: full proactive flow

### Key Deliverables

```
┌─────────────────────────────────────────────────────────┐
│                    MVP DEMO FLOW                        │
├─────────────────────────────────────────────────────────┤
│  1. User starts LearningSession (Mathematics)           │
│  2. Agent presents: "What topic?" [Multiple Choice]     │
│  3. User selects: "Algebra"                             │
│  4. Agent presents: "Solve for x" [Free Text]           │
│  5. User types: "x = 5"                                 │
│  6. Agent presents: "Write function" [Code Editor]      │
│  7. User writes Python code                             │
│  8. Agent evaluates and provides feedback               │
└─────────────────────────────────────────────────────────┘
```

### Key Risks

| Risk | Mitigation |
|------|------------|
| Monaco bundle size | Lazy load, use web worker |
| SSE reconnection edge cases | State endpoint for recovery |

---

## Phase 3: Polish, Testing & Demo

**Duration:** 2 weeks
**Goal:** Production-ready MVP, executive demo

### Milestones

| Week | Milestone | Deliverable |
|------|-----------|-------------|
| 8 | E2E Testing | Playwright tests, coverage reports |
| 9 | Demo Polish | Sample Question Bank, demo script |

### Success Criteria

- [ ] E2E tests cover happy path + edge cases
- [ ] Sample Mathematics Question Bank (10-15 questions)
- [ ] Demo script prepared (5-minute walkthrough)
- [ ] Documentation updated
- [ ] No critical bugs in 48-hour soak test

### Demo Scenario

**Title:** "Proactive Learning Agent - Mathematics Assessment"

1. **Start Session** → Agent introduces itself, explains the assessment
2. **Topic Selection** → Multiple choice: Algebra, Geometry, Calculus
3. **Concept Question** → Free text: Define a variable
4. **Coding Challenge** → Code editor: Write a function to solve quadratic equation
5. **Feedback Loop** → Agent evaluates, provides hints, moves to next question
6. **Completion** → Summary of performance, areas for improvement

---

## Post-MVP: Phase 4+ (Future)

**Timeline:** TBD based on MVP feedback
**Scope:** Advanced widgets, additional session types

### Planned Widgets (Priority Order)

| Widget | Complexity | Use Case |
|--------|------------|----------|
| `confirmation` | Low | Approval workflows |
| `rating_scale` | Low | Feedback collection |
| `drag_drop_simple` | Medium | Matching exercises |
| `drag_drop_category` | Medium | Categorization tasks |
| `hot_spot` | High | Image-based interactions |
| `graphical_builder` | High | Diagram construction |
| `iframe_form` | Medium | External form embedding |
| `file_upload` | Medium | Document submission |

### Planned Session Types

| Type | Mode | Use Case |
|------|------|----------|
| `ValidationSession` | Proactive | Competency certification |
| `SurveySession` | Proactive | Data collection |
| `ApprovalSession` | Proactive | Decision workflows |
| `WorkflowSession` | Proactive | Multi-step processes |

---

## Resource Requirements

### Team Allocation

| Role | Allocation | Responsibilities |
|------|------------|------------------|
| Full-Stack Developer(s) | 100% | All phases, full-stack |

### External Dependencies

| Dependency | Source | Status |
|------------|--------|--------|
| Monaco Editor | npm: `monaco-editor` | Available |
| EventStoreDB | Existing infrastructure | Ready |
| MongoDB | Existing infrastructure | Ready |
| Keycloak | Existing infrastructure | Ready |

### Infrastructure

- No new infrastructure required
- Existing Docker Compose environment sufficient for development
- Same deployment pipeline as current agent-host

---

## Success Metrics

### MVP Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test Coverage | >90% | pytest-cov, Playwright |
| Widget Response Time | <100ms | Performance tests |
| State Restoration | <500ms | E2E tests |
| Demo Completion | 100% | Manual verification |

### Long-term KPIs (Post-MVP)

| KPI | Description |
|-----|-------------|
| Session Completion Rate | % of sessions completed vs abandoned |
| Widget Interaction Time | Average time to respond to each widget type |
| Error Rate | % of sessions with errors/crashes |
| User Satisfaction | Feedback scores from pilot users |

---

## Approvals

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Technical Lead | | | |
| Product Owner | | | |
| Executive Sponsor | | | |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-10 | AI Assistant | Initial roadmap |
