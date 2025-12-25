# Certification Domain: Bounded Context Map

> **Status:** Approved
> **Version:** 1.0
> **Last Updated:** December 2025
> **Decision Authority:** Architecture Review (confirmed in conversation December 2025)

## Executive Summary

This document defines the bounded context boundaries for the Certification Program domain within the Mozart platform. After careful analysis of domain responsibilities, data lifecycles, and team ownership, we've identified **two bounded contexts** with distinct service implementations.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    CERTIFICATION DOMAIN - BOUNDED CONTEXT MAP                        │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                      BOUNDED CONTEXT 1: PROGRAM STRUCTURE                        ││
│  │                      (knowledge-manager: certification-program namespace)        ││
│  │                                                                                  ││
│  │   PURPOSE: Slowly-evolving reference data defining "what certification means"   ││
│  │                                                                                  ││
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        ││
│  │   │    Terms     │  │    Rules     │  │ Relationships│  │    Agents    │        ││
│  │   ├──────────────┤  ├──────────────┤  ├──────────────┤  ├──────────────┤        ││
│  │   │ • Levels     │  │ • Bloom dist │  │ • Level →    │  │ • Blueprint  │        ││
│  │   │   (Assoc,    │  │ • Verb usage │  │   prerequisite│  │   Assistant  │        ││
│  │   │   Prof, Exp) │  │ • Structure  │  │ • Track →    │  │ • Validation │        ││
│  │   │ • Types      │  │   constraints│  │   technology │  │   Advisor    │        ││
│  │   │   (Core,     │  │ • Naming     │  │ • Bloom →    │  │              │        ││
│  │   │   Conc, Spec)│  │   conventions│  │   verb assoc │  │              │        ││
│  │   │ • Tracks     │  │              │  │              │  │              │        ││
│  │   │ • Bloom      │  │              │  │              │  │              │        ││
│  │   │   Taxonomy   │  │              │  │              │  │              │        ││
│  │   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘        ││
│  │                                                                                  ││
│  │   PERSISTENCE: MongoDB (KnowledgeNamespace via MotorRepository)                 ││
│  │   LIFECYCLE: Long-lived, council-controlled, versioned, rarely changes          ││
│  │   INTEGRATION: Exposes validation queries, publishes term-updated events        ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                         │                                            │
│                                         │ CloudEvents (program structure changes)   │
│                                         │ Runtime validation queries               │
│                                         ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                      BOUNDED CONTEXT 2: EXAM CONTENT                             ││
│  │                      (blueprint-manager service)                                 ││
│  │                                                                                  ││
│  │   PURPOSE: Actively-authored exam definitions, the "working documents"          ││
│  │                                                                                  ││
│  │   ┌───────────────────────┐  ┌───────────────────────┐  ┌─────────────────────┐ ││
│  │   │     ExamBlueprint     │  │    SkillTemplate      │  │     FormSpec        │ ││
│  │   │     (Aggregate)       │  │     (Aggregate)       │  │    (Aggregate)      │ ││
│  │   ├───────────────────────┤  ├───────────────────────┤  ├─────────────────────┤ ││
│  │   │ • Topics & Skills     │  │ • Stem patterns       │  │ • Form structure    │ ││
│  │   │ • KSA Statements      │  │ • Difficulty levels   │  │ • Item slots        │ ││
│  │   │ • MQC Definition      │  │ • Distractor types    │  │ • Scoring rules     │ ││
│  │   │ • Lifecycle state     │  │ • Item type config    │  │ • Timing config     │ ││
│  │   │ • Mosaic sync status  │  │ • Reusable templates  │  │ • Delivery config   │ ││
│  │   └───────────────────────┘  └───────────────────────┘  └─────────────────────┘ ││
│  │                                                                                  ││
│  │   PERSISTENCE: EventStoreDB (audit trail) + MongoDB (read projections)          ││
│  │   LIFECYCLE: Dynamic authoring, versioned, workflow-driven                      ││
│  │   INTEGRATION: Publishes to Mosaic, receives validation from knowledge-manager  ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                         │                                            │
│                                         │ REST API (publish blueprint)              │
│                                         ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                      EXTERNAL SYSTEM: MOSAIC                                     ││
│  │                      (Content Authoring & Form Assembly)                         ││
│  │                                                                                  ││
│  │   Receives published blueprints via API, does NOT own blueprint definitions     ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Decision Rationale

### Why Two Bounded Contexts?

| Factor | Program Structure | Exam Content |
|--------|-------------------|--------------|
| **Change Frequency** | Quarterly/annually (Council decisions) | Daily (Author edits) |
| **Ownership** | Certification Council | EPMs & Authors |
| **Lifecycle** | Define once, enforce forever | Draft → Review → Publish → Retire |
| **Purpose** | "What the rules are" | "What the exam contains" |
| **Consistency Need** | Must be consistent across all exams | Per-exam variation allowed |
| **Audit Trail** | Version history needed | Full event history required |

### Why NOT Separate Services for Each?

The Program Structure bounded context does **not** warrant a new microservice because:

1. **knowledge-manager already has the right model**: Namespaces with Terms, Rules, and Relationships perfectly fit program structure (Levels = Terms, Bloom distributions = Rules, Level→prerequisite = Relationships)

2. **Low operational overhead**: Program structure changes are infrequent; adding a new service just for reference data adds deployment/monitoring cost without proportional benefit

3. **Agent integration**: knowledge-manager already hosts agents that can access program rules for validation advisory

4. **No separate scaling needs**: Unlike actively-authored blueprints, program structure queries are low-volume

## Context Integration Patterns

### 1. Upstream/Downstream Relationship

```
┌────────────────────────┐          ┌────────────────────────┐
│   knowledge-manager    │          │   blueprint-manager    │
│   (UPSTREAM)           │          │   (DOWNSTREAM)         │
│                        │          │                        │
│  • Defines the rules   │─────────▶│  • Follows the rules   │
│  • Publishes standards │          │  • Requests validation │
│  • Rarely changes      │          │  • Adapts to changes   │
└────────────────────────┘          └────────────────────────┘
         │                                    │
         │ CONFORMIST                         │ ANTI-CORRUPTION
         │ (blueprint-manager               │ LAYER (Mosaic
         │  conforms to rules)              │  has own model)
         │                                    │
         ▼                                    ▼
    CloudEvents:                         REST API:
    • rule.updated                       • POST /blueprints
    • term.created                       • PUT /blueprints/{id}
    • relationship.added
```

### 2. Shared Kernel: Certification Vocabulary

Both contexts share a common vocabulary defined as value objects:

```python
# Shared vocabulary (published package or inline definitions)
class CertificationLevel(str, Enum):
    """Certification level codes - shared across contexts."""
    ASSOCIATE = "associate"
    PROFESSIONAL = "professional"
    EXPERT = "expert"

class CertificationType(str, Enum):
    """Certification type codes - shared across contexts."""
    CORE = "core"
    CONCENTRATION = "concentration"
    SPECIALIST = "specialist"

class BloomLevel(int, Enum):
    """Bloom's Taxonomy levels - shared for consistency."""
    REMEMBER = 1
    UNDERSTAND = 2
    APPLY = 3
    ANALYZE = 4
    EVALUATE = 5
    CREATE = 6
```

### 3. Integration Events

#### From knowledge-manager → blueprint-manager

```yaml
# When program structure changes, blueprint-manager reacts
events:
  - type: com.cisco.certification-program.rule.updated.v1
    description: A validation rule was modified
    payload:
      rule_id: string
      namespace_id: "certification-program"
      previous_version: string
      new_version: string
    consumer_action: Invalidate cached rules, re-validate in-progress blueprints

  - type: com.cisco.certification-program.term.created.v1
    description: A new term (e.g., new track) was added
    payload:
      term_id: string
      term_type: string  # "level" | "type" | "track"
      name: string
    consumer_action: Make new term available in blueprint dropdowns
```

#### From blueprint-manager → knowledge-manager

```yaml
events:
  - type: com.cisco.blueprint-manager.blueprint.published.v1
    description: A blueprint was published to Mosaic
    payload:
      blueprint_id: string
      exam_code: string
      level: string
      track: string
      version: string
    consumer_action: Update knowledge graph with new blueprint entity
```

## Aggregate Ownership Matrix

| Aggregate | Service | Persistence | Event Types |
|-----------|---------|-------------|-------------|
| **KnowledgeNamespace** (with certification-program data) | knowledge-manager | MongoDB (MotorRepository) | term._, rule._, relationship.* |
| **ExamBlueprint** | blueprint-manager | EventStoreDB + MongoDB | blueprint.created, .updated, .submitted, .approved, .published, .retired |
| **SkillTemplate** | blueprint-manager | EventStoreDB + MongoDB | skill_template.created, .updated, .linked, .unlinked, .deprecated |
| **FormSpec** | blueprint-manager | EventStoreDB + MongoDB | form_spec.created, .updated, .linked, .activated |

## Validation Flow

The key integration pattern is **runtime validation** where blueprint-manager requests validation from knowledge-manager:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VALIDATION FLOW (Non-Blocking)                           │
│                                                                              │
│  User Action                blueprint-manager         knowledge-manager      │
│      │                            │                          │              │
│      │  Submit blueprint for      │                          │              │
│      │  review                    │                          │              │
│      │───────────────────────────►│                          │              │
│      │                            │                          │              │
│      │                            │  POST /api/validation    │              │
│      │                            │  { blueprint_snapshot,   │              │
│      │                            │    namespace: "cert-pgm"}│              │
│      │                            │─────────────────────────►│              │
│      │                            │                          │              │
│      │                            │                          │ Evaluate all │
│      │                            │                          │ applicable   │
│      │                            │                          │ rules        │
│      │                            │                          │              │
│      │                            │  { violations: [...],   │              │
│      │                            │    warnings: [...],     │              │
│      │                            │    passed: [...] }      │              │
│      │                            │◄─────────────────────────│              │
│      │                            │                          │              │
│      │  Blueprint submitted       │                          │              │
│      │  with validation report    │                          │              │
│      │  (errors = warnings,       │                          │              │
│      │   not blockers)            │                          │              │
│      │◄───────────────────────────│                          │              │
│      │                            │                          │              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Decision:** Validation violations are **informational, not blocking**. Human reviewers see the report and decide whether to proceed. This prevents the system from being overly rigid while still providing AI-powered guidance.

## SkillTemplate Cross-Context Sharing

SkillTemplates are owned by blueprint-manager but are designed for cross-blueprint and cross-track reuse:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SKILL TEMPLATE SHARING MODEL                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                      SkillTemplate Pool                                  ││
│  │                      (blueprint-manager)                                 ││
│  │                                                                         ││
│  │   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  ││
│  │   │ IP Routing        │  │ Network Security  │  │ Automation        │  ││
│  │   │ Troubleshooting   │  │ Analysis          │  │ Scripting         │  ││
│  │   ├───────────────────┤  ├───────────────────┤  ├───────────────────┤  ││
│  │   │ Tracks: ENT, SP   │  │ Tracks: SEC, ENT  │  │ Tracks: DEV, ALL  │  ││
│  │   │ Levels: ALL       │  │ Levels: PROF, EXP │  │ Levels: ALL       │  ││
│  │   └───────────────────┘  └───────────────────┘  └───────────────────┘  ││
│  │                                                                         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│           │                        │                        │               │
│           │                        │                        │               │
│           ▼                        ▼                        ▼               │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐         │
│  │ ENCOR       │          │ SCOR        │          │ DevCOR      │         │
│  │ Blueprint   │          │ Blueprint   │          │ Blueprint   │         │
│  │ (CCNP Ent)  │          │ (CCNP Sec)  │          │ (DevNet Pro)│         │
│  └─────────────┘          └─────────────┘          └─────────────┘         │
│                                                                              │
│  RELATIONSHIP: Many-to-Many linking via skill_template_id references       │
│  LIFECYCLE: Templates evolve independently; blueprints link specific version│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## External System Integration

### Mosaic (Downstream Consumer)

blueprint-manager **publishes** to Mosaic; it does NOT pull from Mosaic:

```
┌────────────────────────┐         ┌────────────────────────┐
│   blueprint-manager    │         │        Mosaic          │
│   (Source of Truth)    │         │   (Content Authoring)  │
│                        │         │                        │
│  ExamBlueprint         │────────▶│  Blueprint (received)  │
│  - author edits        │ Publish │  - item authoring      │
│  - approval workflow   │  API    │  - form assembly       │
│  - validation          │         │  - localization        │
└────────────────────────┘         └────────────────────────┘
         │                                    │
         │                                    │
         └──────────────┬─────────────────────┘
                        │
                        ▼
              ┌────────────────────────┐
              │    Delivery Systems    │
              │    (LDS, pod-manager)  │
              └────────────────────────┘
```

**Data Flow:**

1. EPM authors blueprint in blueprint-manager (AI-assisted)
2. Blueprint goes through approval workflow (DRAFT → REVIEW → APPROVED)
3. Upon approval, blueprint is **published** to Mosaic via API
4. Mosaic uses blueprint to enable item authoring and form assembly
5. Changes in blueprint-manager trigger updates to Mosaic

## Namespace Seed Data

The `certification-program` namespace in knowledge-manager is seeded with:

### Terms (16+)

- Certification Levels: Associate, Professional, Expert
- Certification Types: Core, Concentration, Specialist
- Certification Tracks: Enterprise, Security, DevNet, Collaboration, Service Provider
- Bloom's Taxonomy: Remember, Understand, Apply, Analyze, Evaluate, Create

### Rules (14+)

- Bloom distribution requirements per level
- Verb usage rules (prohibited/encouraged per level)
- Structure constraints (min/max topics, coverage requirements)
- Naming conventions

### Relationships (20+)

- Level prerequisites (Associate → Professional → Expert)
- Track technology associations
- Bloom level → verb associations
- Type requirements per track

See: [certification-program-namespace.md](../domain/certification-program/seed-data/certification-program-namespace.md)

## Service Folder Structure

### blueprint-manager (New Service)

```
src/blueprint-manager/
├── __init__.py
├── main.py                      # FastAPI application, DAL configuration
├── pyproject.toml
├── pytest.ini
├── Makefile
├── api/
│   ├── __init__.py
│   ├── dependencies.py          # Auth, mediator injection
│   ├── description.md
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── blueprints_controller.py
│   │   ├── skill_templates_controller.py
│   │   └── form_specs_controller.py
│   └── services/
│       ├── __init__.py
│       └── mosaic_client.py     # Mosaic API integration
├── application/
│   ├── __init__.py
│   ├── settings.py
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── create_blueprint_command.py
│   │   ├── update_blueprint_command.py
│   │   ├── submit_for_review_command.py
│   │   ├── approve_blueprint_command.py
│   │   ├── publish_blueprint_command.py
│   │   ├── retire_blueprint_command.py
│   │   ├── create_skill_template_command.py
│   │   ├── link_skill_template_command.py
│   │   ├── create_form_spec_command.py
│   │   └── link_form_spec_command.py
│   └── queries/
│       ├── __init__.py
│       ├── get_blueprint_query.py
│       ├── list_blueprints_query.py
│       ├── get_skill_template_query.py
│       ├── list_skill_templates_query.py
│       ├── get_form_spec_query.py
│       └── search_skill_templates_query.py
├── domain/
│   ├── __init__.py
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── exam_blueprint.py
│   │   ├── skill_template.py
│   │   └── form_spec.py
│   ├── events/
│   │   ├── __init__.py
│   │   ├── blueprint_events.py
│   │   ├── skill_template_events.py
│   │   └── form_spec_events.py
│   ├── value_objects/
│   │   ├── __init__.py
│   │   ├── certification_level.py
│   │   ├── certification_type.py
│   │   ├── bloom_level.py
│   │   ├── blueprint_status.py
│   │   ├── topic.py
│   │   ├── skill.py
│   │   └── ksa_statement.py
│   └── services/
│       ├── __init__.py
│       └── validation_service.py
├── infrastructure/
│   ├── __init__.py
│   └── mosaic_adapter.py
├── integration/
│   ├── __init__.py
│   └── models/
│       ├── __init__.py
│       ├── blueprint_dto.py
│       ├── skill_template_dto.py
│       └── form_spec_dto.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── domain/
│   │   ├── test_exam_blueprint.py
│   │   ├── test_skill_template.py
│   │   └── test_form_spec.py
│   ├── application/
│   │   ├── commands/
│   │   └── queries/
│   └── integration/
└── static/
```

## Next Steps

1. **Create blueprint-manager service** following the folder structure above
2. **Implement ExamBlueprint aggregate** with dual-persistence pattern
3. **Implement SkillTemplate aggregate** with linking capabilities
4. **Create MCP tools** for blueprint authoring via tools-provider
5. **Seed certification-program namespace** in knowledge-manager
6. **Implement Mosaic client** for publish integration

## Related Documents

- [ExamBlueprint Aggregate Design](../domain/certification-program/aggregates/exam-blueprint.md)
- [SkillTemplate Aggregate Design](../domain/certification-program/aggregates/skill-template.md)
- [FormSpec Aggregate Design](../domain/certification-program/aggregates/form-spec.md)
- [Certification Program Design Use Case](../domain/certification-program/use-cases/certification-program-design.md)
- [Blueprint Authoring Use Case](../domain/certification-program/use-cases/blueprint-authoring.md)

---

_Last updated: December 2025_
