# Certification Domain Architecture

> **Status:** Design Phase
> **Last Updated:** January 2025

## Overview

This folder contains the architecture design documentation for the Certification Program domain, which extends the Mozart platform to support exam blueprint authoring, skill template management, and integration with downstream content systems (Mosaic, LDS).

## Document Index

| Document | Description |
|----------|-------------|
| [00-bounded-context-map.md](00-bounded-context-map.md) | Bounded context mapping, service boundaries, integration patterns |
| [01-exam-blueprint-aggregate.md](01-exam-blueprint-aggregate.md) | ExamBlueprint aggregate design (state, events, state machine) |
| [02-skill-template-aggregate.md](02-skill-template-aggregate.md) | SkillTemplate aggregate design (reusable item development guidance) |
| [03-namespace-seed-data.md](03-namespace-seed-data.md) | Certification-program namespace seed data for knowledge-manager |

## Key Architectural Decisions

### 1. Two Bounded Contexts

| Context | Service | Purpose |
|---------|---------|---------|
| **Program Structure** | knowledge-manager (namespace) | Slowly-evolving reference data: levels, types, tracks, validation rules |
| **Exam Content** | blueprint-manager (new service) | Actively-authored blueprints, skill templates, form specs |

**Rationale:** Program structure (what certification levels mean, what rules apply) changes quarterly/annually by Council decision. Exam content (individual blueprints) changes daily as authors work. Different change frequencies and ownership models warrant separation.

### 2. Dual Persistence for Aggregates

All aggregates in blueprint-manager use dual persistence:

- **EventStoreDB**: Full event history for audit trail (ANSI/ISO 17024 compliance)
- **MongoDB**: Projected read models for efficient queries

```python
# Repository configuration
EventSourcingRepository.configure(
    builder,
    entity_type=ExamBlueprint,
    key_type=str,
)
```

### 3. Many-to-Many SkillTemplate Linking

SkillTemplates are independent aggregates linked to Skills within Blueprints:

- Templates don't know which blueprints use them
- Blueprints store links with version information
- Cross-track, cross-blueprint sharing is supported
- Template deprecation doesn't break existing links

### 4. Non-Blocking Validation

Validation against program rules is **informational, not blocking**:

- blueprint-manager calls knowledge-manager for validation
- Validation results are attached to the blueprint
- Human reviewers see the results and decide whether to proceed
- Prevents over-rigid automation while providing AI-powered guidance

### 5. Mosaic as Downstream Consumer

blueprint-manager is the **source of truth** for exam definitions:

- Authors work in blueprint-manager (AI-assisted)
- Published blueprints are pushed to Mosaic via API
- Mosaic receives blueprints; it does not own them
- Changes in blueprint-manager trigger updates to Mosaic

## Service Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CERTIFICATION DOMAIN SERVICES                             │
│                                                                              │
│  ┌─────────────────────┐      ┌─────────────────────┐                       │
│  │   knowledge-manager │      │  blueprint-manager  │                       │
│  │   (existing)        │◄────▶│  (NEW SERVICE)      │                       │
│  │                     │      │                     │                       │
│  │  • certification-   │      │  • ExamBlueprint    │                       │
│  │    program namespace│      │  • SkillTemplate    │                       │
│  │  • Validation rules │      │  • FormSpec         │                       │
│  │  • Agent: Validator │      │                     │                       │
│  └─────────────────────┘      └──────────┬──────────┘                       │
│                                          │                                   │
│                                   Publish │ API                              │
│                                          │                                   │
│                                          ▼                                   │
│                               ┌─────────────────────┐                       │
│                               │      Mosaic         │                       │
│                               │   (Content Authoring)│                       │
│                               │                     │                       │
│                               │  • Item authoring   │                       │
│                               │  • Form assembly    │                       │
│                               │  • Localization     │                       │
│                               └──────────┬──────────┘                       │
│                                          │                                   │
│                                          ▼                                   │
│                               ┌─────────────────────┐                       │
│                               │      LDS/Delivery   │                       │
│                               │                     │                       │
│                               └─────────────────────┘                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Next Steps

### Implementation Priority

1. **Phase 1: Foundation**
   - [ ] Create `src/blueprint-manager/` directory structure
   - [ ] Implement value objects (CertificationLevel, BlueprintStatus, etc.)
   - [ ] Implement domain events

2. **Phase 2: ExamBlueprint Aggregate**
   - [ ] Implement ExamBlueprintState
   - [ ] Implement ExamBlueprint aggregate root
   - [ ] Create command handlers
   - [ ] Create query handlers

3. **Phase 3: SkillTemplate Aggregate**
   - [ ] Implement SkillTemplateState
   - [ ] Implement SkillTemplate aggregate root
   - [ ] Create command/query handlers

4. **Phase 4: Integration**
   - [ ] Implement Mosaic client
   - [ ] Implement knowledge-manager validation integration
   - [ ] Create MCP tools for tools-provider

5. **Phase 5: Seed Data**
   - [ ] Create seed script for certification-program namespace
   - [ ] Load namespace in knowledge-manager

## Related Documentation

### Domain Documentation

- [Certification Program Overview](../../domain/certification-program/00-overview.md)
- [Ubiquitous Language](../../domain/certification-program/01-ubiquitous-language.md)
- [Actor Roles](../../domain/certification-program/02-actor-roles.md)
- [Service Topology](../../domain/certification-program/03-service-topology.md)

### Aggregate Documentation

- [ExamBlueprint Aggregate](../../domain/certification-program/aggregates/exam-blueprint.md)
- [SkillTemplate Aggregate](../../domain/certification-program/aggregates/skill-template.md)
- [FormSpec Aggregate](../../domain/certification-program/aggregates/form-spec.md)

### Use Case Documentation

- [Blueprint Authoring](../../domain/certification-program/use-cases/blueprint-authoring.md)
- [Certification Program Design](../../domain/certification-program/use-cases/certification-program-design.md)

---

_Last updated: January 2025_
