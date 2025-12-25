# Certification Program Domain - Architecture Overview

> **Document Status:** Living document, capturing architectural decisions from design session (Dec 24, 2025)

## Executive Summary

This document describes the architecture for an **AI-augmented Certification Program platform** that supports all actors involved in creating, delivering, and maintaining professional certification exams.

The architecture separates concerns between:

1. **Generic Core Services** (domain-agnostic, reusable)
   - `agent-host`: Conversation orchestration, agent execution, UI widget delivery
   - `knowledge-manager`: Context expansion, graph/vector storage, namespace management
   - `tools-provider`: MCP tool discovery, execution, and access control

2. **Certification Domain Services** (domain-specific)
   - `blueprint-manager`: ExamBlueprint authoring, MQC/KSA definitions, SkillTemplate management
   - External systems: ExamContentAuthoring, pod-manager, grading-system, etc.

## Problem Statement

### Current Challenges

| Challenge | Impact |
|-----------|--------|
| **Static Exam Content** | Exposure risk—same content across cohorts enables cheating |
| **Long Practical Exams** | 5-8h exams with static content are vulnerable to content leaks |
| **Manual Content Authoring** | SMEs lack AI assistance for generating/validating items |
| **Proctor Context Gaps** | Proctors must query multiple systems for candidate context |
| **Actor Fragmentation** | Each actor (Owner, SME, Proctor, Candidate, Analyst) uses different tools |

### Target Outcomes

| Outcome | Metric |
|---------|--------|
| **Unique Content Per Candidate** | 100% of practical exam items templated |
| **AI-Assisted Authoring** | 50% reduction in SME authoring time |
| **Instant Proctor Context** | <2s response for any candidate query |
| **Unified Actor Experience** | All actors use conversational AI interface |
| **Content Exposure Mitigation** | Templated items resist memorization attacks |

## Service Topology

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              CERTIFICATION ECOSYSTEM                                 │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                        GENERIC CORE (Domain-Agnostic)                        │    │
│  │                                                                              │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │    │
│  │  │   agent-host    │  │ knowledge-manager│  │ tools-provider  │              │    │
│  │  │                 │  │                 │  │                 │              │    │
│  │  │ • Conversations │  │ • Namespaces    │  │ • Tool Discovery│              │    │
│  │  │ • AgentDefs     │  │ • Terms/Rules   │  │ • Tool Execution│              │    │
│  │  │ • Templates     │  │ • Graph/Vector  │  │ • Auth Propagate│              │    │
│  │  │ • UiWidgets     │  │ • Context API   │  │ • MCP Protocol  │              │    │
│  │  │ • Item Gen      │  │                 │  │                 │              │    │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │    │
│  │           │                    │                    │                        │    │
│  └───────────┼────────────────────┼────────────────────┼────────────────────────┘    │
│              │                    │                    │                             │
│              │         ┌──────────▼──────────┐         │                             │
│              │         │ DOMAIN ADAPTER LAYER │         │                             │
│              │         │ (CloudEvents + REST) │         │                             │
│              │         └──────────┬──────────┘         │                             │
│              │                    │                    │                             │
│  ┌───────────┼────────────────────┼────────────────────┼────────────────────────┐    │
│  │           │     CERTIFICATION DOMAIN (Domain-Specific)                        │    │
│  │           │                    │                    │                         │    │
│  │  ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐               │    │
│  │  │blueprint-manager│  │ ExamContent     │  │  Exam Delivery  │               │    │
│  │  │   (NEW)         │  │ Authoring (EXT) │  │  Platform (EXT) │               │    │
│  │  │                 │  │                 │  │                 │               │    │
│  │  │ • MQC Defs      │  │ • Forms         │  │ • Sessions      │               │    │
│  │  │ • ExamBlueprints│  │ • Items         │  │ • Proctoring    │               │    │
│  │  │ • SkillTemplates│  │ • Grading Rules │  │ • Candidate UI  │               │    │
│  │  │ • FormSpecs     │  │ • Review Workflow│ │                 │               │    │
│  │  │ • KSA Import    │  │                 │  │                 │               │    │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘               │    │
│  │           │                    │                    │                         │    │
│  │  ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐               │    │
│  │  │  track-manager  │  │  pod-manager    │  │ grading-system  │               │    │
│  │  │                 │  │                 │  │                 │               │    │
│  │  │ • Cert Tracks   │  │ • Pod Lifecycle │  │ • Rule Eval     │               │    │
│  │  │ • Prerequisites │  │ • Device Alloc  │  │ • Scoring       │               │    │
│  │  └─────────────────┘  │ • State Capture │  │ • Partial Credit│               │    │
│  │                       └─────────────────┘  └─────────────────┘               │    │
│  │                                                                               │    │
│  └───────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Generic Core Services

### agent-host

**Responsibility:** Conversation orchestration between users (Actors) and data (via tools-provider and knowledge-manager).

**Generic Capabilities:**

- WebSocket-based conversation streaming
- AgentDefinition management (system prompts, tools, model config)
- ConversationTemplate for proactive flows
- UiWidget rendering (MCQ, code editor, free text, etc.)
- LLM-based item generation from templates

**Certification Instantiation:**

- Role-specific AgentDefinitions (one per actor type)
- ConversationTemplates mapped to FormSpecs
- Specialized item generation agents

### knowledge-manager

**Responsibility:** Structured domain knowledge with context expansion for AI agents.

**Generic Capabilities:**

- KnowledgeNamespace management (terms, relationships, rules)
- Graph traversal (Neo4j)
- Vector search (semantic similarity)
- Context expansion API

**Certification Instantiation:**

- Namespaces fed by blueprint-manager (MQC, KSA, SkillTemplates)
- Dynamic data from exam delivery systems
- Per-actor context scoping

### tools-provider

**Responsibility:** MCP tool discovery, access control, and execution with identity propagation.

**Generic Capabilities:**

- OpenAPI → MCP tool conversion
- Role-based tool access control
- OAuth2 token propagation to upstream services

**Certification Instantiation:**

- Wraps ExamContentAuthoring API
- Wraps pod-manager, grading-system APIs
- Actor-specific tool subsets

## Domain-Specific Services

### blueprint-manager (NEW)

**Responsibility:** Domain-specific service for ExamBlueprint authoring and SkillTemplate management.

**Capabilities:**

- MQC (Minimally Qualified Candidate) definition authoring
- ExamBlueprint CRUD (Topic → Skill → KSA hierarchy)
- SkillTemplate management (item generation specs)
- FormSpec creation (exam form structure)
- Unstructured document import (MQC/KSA extraction)

**Publishes to knowledge-manager:**

- Blueprint revisions (CloudEvents)
- SkillTemplate updates
- FormSpec updates

### External Systems (Existing)

| System | Responsibility | Integration |
|--------|---------------|-------------|
| ExamContentAuthoring | Forms, Items, Grading Rules | REST API via tools-provider |
| track-manager | Certification tracks, prerequisites | REST API |
| pod-manager | Pod lifecycle, device allocation | REST API + events |
| session-manager | Exam sessions, timing | REST API + events |
| exam-delivery-system | Candidate UI, proctoring | REST API |
| output-collectors | Device state capture | Event stream |
| grading-system | Rule evaluation, scoring | REST API |

## Key Design Decisions

### 1. Generic Core Remains Domain-Agnostic

The three core services (agent-host, knowledge-manager, tools-provider) contain no certification-specific logic. They can be reused for other domains (healthcare, finance, education).

### 2. blueprint-manager is the Domain Gateway

All certification-specific domain logic lives in blueprint-manager. It:

- Owns the ExamBlueprint aggregate
- Publishes structured data to knowledge-manager
- Provides FormSpecs that agent-host consumes

### 3. Static Agents with Role-Specific Configuration

No A2A (agent-to-agent) protocol needed. Each actor role has a pre-configured AgentDefinition with:

- Tailored system prompt
- Restricted tool access
- Appropriate knowledge namespaces

### 4. Templated Item Generation at Runtime

Items are generated at conversation start from SkillTemplates. The LLM:

- Instantiates template parameters
- Generates distractors
- Validates difficulty constraints

### 5. External Systems Wrapped via tools-provider

Existing APIs are exposed as MCP tools. This provides:

- Unified access control
- Identity propagation
- Consistent error handling

## Open Questions

> These questions were identified during the design session and need clarification.

### ExamContentAuthoring Platform

- [ ] Is this an existing production system with stable API, or still evolving?
- [ ] What operations does it support? (CRUD on forms? Item authoring? Review workflows?)
- [ ] Does it have webhooks/events for changes, or is it purely request-response?
- [ ] Is this where the static grading rules are defined today?

### Practical Exam Templating

- [ ] What are the variable dimensions in a practical exam? (IP ranges, hostnames, file paths, configs, task ordering?)
- [ ] Are there dependency constraints between tasks? ("Task 3 uses output from Task 2")
- [ ] How are grading rules expressed today? (Scripts? Declarative checks? Manual rubrics?)
- [ ] What makes current static content vulnerable to exposure?

### Pod/Device Architecture

- [ ] Is a "Pod" a virtual environment (like a lab VM cluster)?
- [ ] What does "device state" mean? (File system? Running services? Network config? Logs?)
- [ ] How is device state captured for grading? (Agent polling? Event push? Snapshot?)
- [ ] Can the grading system evaluate partial correctness, or is it binary pass/fail?

### Existing System Status

| System | Existing? | Notes |
|--------|-----------|-------|
| ExamContentAuthoring | TBD | |
| track-manager | TBD | |
| pod-manager | TBD | |
| devices-manager | TBD | |
| session-manager | TBD | |
| exam-delivery-system | TBD | |
| output-collectors | TBD | |
| grading-system | TBD | |
| analytics datasources | TBD | |

## Document Index

| Document | Description |
|----------|-------------|
| [01-ubiquitous-language.md](01-ubiquitous-language.md) | Domain glossary |
| [02-actor-roles.md](02-actor-roles.md) | Actor definitions and workflows |
| [03-service-topology.md](03-service-topology.md) | Detailed service boundaries |
| **Aggregates** | |
| [aggregates/exam-blueprint.md](aggregates/exam-blueprint.md) | ExamBlueprint aggregate |
| [aggregates/skill-template.md](aggregates/skill-template.md) | SkillTemplate format |
| [aggregates/form-spec.md](aggregates/form-spec.md) | FormSpec structure |
| [aggregates/practical-exam-template.md](aggregates/practical-exam-template.md) | Long-form practical templating |
| **Use Cases** | |
| [use-cases/blueprint-authoring.md](use-cases/blueprint-authoring.md) | Owner workflows |
| [use-cases/content-authoring.md](use-cases/content-authoring.md) | SME workflows |
| [use-cases/content-review.md](use-cases/content-review.md) | Reviewer workflows |
| [use-cases/item-generation.md](use-cases/item-generation.md) | Runtime item creation |
| [use-cases/exam-delivery.md](use-cases/exam-delivery.md) | Candidate experience |
| [use-cases/practical-exam.md](use-cases/practical-exam.md) | Lablets and long-form |
| [use-cases/proctoring.md](use-cases/proctoring.md) | Proctor support |
| [use-cases/analytics.md](use-cases/analytics.md) | Analyst workflows |
| **Integration** | |
| [integration/external-systems.md](integration/external-systems.md) | External system details |
| [integration/event-flows.md](integration/event-flows.md) | CloudEvent choreography |
| [integration/tools-mapping.md](integration/tools-mapping.md) | MCP tool definitions |
| **Innovation** | |
| [innovation/templated-practical-exams.md](innovation/templated-practical-exams.md) | 5-8h unique content |
| [innovation/document-ingestion.md](innovation/document-ingestion.md) | MQC/KSA extraction |
| [innovation/ai-agent-opportunities.md](innovation/ai-agent-opportunities.md) | Per-actor AI augmentation |

---

_Last updated: December 24, 2025_
