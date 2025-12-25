# Use Case: Blueprint Authoring

> **Primary Actor:** CertificationOwner (EPM - Exam Program Manager)
> **Supporting Actors:** ExamAuthor (SME), AI Blueprint Assistant
> **Systems Involved:** Mosaic (primary), blueprint-manager, knowledge-manager, agent-host

## Overview

Blueprint Authoring is the process of defining WHAT an exam measures. It establishes the hierarchical structure of Topics → Skills → KSA Statements that constitute a Minimally Qualified Candidate (MQC).

## Current State (Mosaic-Centric)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CURRENT BLUEPRINT AUTHORING FLOW                        │
│                                                                              │
│  CertificationOwner                           Mosaic                         │
│        │                                         │                           │
│        │  1. Create Blueprint shell              │                           │
│        │────────────────────────────────────────►│                           │
│        │                                         │                           │
│        │  2. Define Topics (high-level)          │                           │
│        │────────────────────────────────────────►│                           │
│        │                                         │                           │
│        │  3. Assign SMEs to Topics               │                           │
│        │────────────────────────────────────────►│                           │
│        │                                         │                           │
│        │                    ┌────────────────────┤                           │
│        │                    │ SME Notification   │                           │
│        │                    ▼                    │                           │
│        │              ExamAuthor                 │                           │
│        │                    │                    │                           │
│        │                    │ 4. Add Skills      │                           │
│        │                    │───────────────────►│                           │
│        │                    │                    │                           │
│        │                    │ 5. Define KSAs     │                           │
│        │                    │───────────────────►│                           │
│        │                    │                    │                           │
│        │  6. Review & approve                    │                           │
│        │◄────────────────────────────────────────│                           │
│        │                                         │                           │
│        │  7. Publish Blueprint                   │                           │
│        │────────────────────────────────────────►│                           │
│        │                                         │                           │
│        │                    CloudEvent: blueprint.published.v1               │
│        │                                         │───────────────────────►   │
│        │                                         │                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Pain Points

| Pain Point | Impact | Root Cause |
|------------|--------|------------|
| **High-level KSAs** | Inconsistent item quality | KSAs too abstract, open to interpretation |
| **Manual refinement** | Slow iteration cycles | No AI assistance for KSA decomposition |
| **Siloed knowledge** | Repeated research | SMEs rediscover domain knowledge each cycle |
| **No measurability check** | Untestable objectives | KSAs not validated against measurement criteria |

## Future State (AI-Augmented)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AI-AUGMENTED BLUEPRINT AUTHORING                        │
│                                                                              │
│  CertificationOwner          agent-host              AI Assistant            │
│        │                         │                        │                  │
│        │  1. "Help me create a   │                        │                  │
│        │     networking cert     │                        │                  │
│        │     blueprint"          │                        │                  │
│        │────────────────────────►│                        │                  │
│        │                         │                        │                  │
│        │                         │  2. Fetch domain       │                  │
│        │                         │     context            │                  │
│        │                         │───────────────────────►│                  │
│        │                         │     knowledge-manager  │                  │
│        │                         │                        │                  │
│        │                         │  3. Suggest Topic      │                  │
│        │                         │     structure based    │                  │
│        │                         │     on industry        │                  │
│        │                         │     standards          │                  │
│        │◄────────────────────────│◄───────────────────────│                  │
│        │                         │                        │                  │
│        │  4. Refine Topics,      │                        │                  │
│        │     add constraints     │                        │                  │
│        │────────────────────────►│                        │                  │
│        │                         │                        │                  │
│        │                         │  5. Generate Skills    │                  │
│        │                         │     with measurable    │                  │
│        │                         │     KSA statements     │                  │
│        │◄────────────────────────│◄───────────────────────│                  │
│        │                         │                        │                  │
│        │  6. Validate KSAs are   │                        │                  │
│        │     measurable          │                        │                  │
│        │────────────────────────►│                        │                  │
│        │                         │                        │                  │
│        │                         │  7. Check each KSA     │                  │
│        │                         │     against Bloom's    │                  │
│        │                         │     taxonomy +         │                  │
│        │                         │     testability        │                  │
│        │                         │     criteria           │                  │
│        │◄────────────────────────│◄───────────────────────│                  │
│        │                         │                        │                  │
│        │  8. Approve & sync      │                        │                  │
│        │     to Mosaic           │                        │                  │
│        │────────────────────────►│                        │                  │
│        │                         │  9. Create Blueprint   │                  │
│        │                         │     via Mosaic API     │                  │
│        │                         │───────────────────────►│ tools-provider   │
│        │                         │     (MCP tool)         │ → Mosaic API     │
│        │                         │                        │                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## AI Agent Configuration

### Blueprint Architect Agent

```yaml
agent_id: 'blueprint-architect'
name: 'Blueprint Architect'
description: 'Assists CertificationOwners in creating well-structured, measurable exam blueprints'

system_prompt: |
  You are an expert psychometrician and instructional designer assisting in
  certification exam blueprint development.

  Your responsibilities:
  1. Help decompose high-level certification goals into measurable Topics and Skills
  2. Ensure KSA statements follow Bloom's Taxonomy and are objectively measurable
  3. Validate topic weights align with job task analysis data
  4. Suggest appropriate cognitive levels for each skill
  5. Identify gaps in coverage or overlapping objectives

  Key principles:
  - Every KSA must be testable with objective criteria
  - Prefer action verbs: configure, troubleshoot, analyze, design (not "understand")
  - Balance breadth vs depth based on exam time constraints
  - Consider practical vs theoretical skill distribution

tools:
  - mosaic.get_blueprint
  - mosaic.create_blueprint
  - mosaic.update_blueprint
  - mosaic.get_industry_standards  # e.g., CompTIA, Cisco cert frameworks
  - knowledge.search_domain_terms
  - knowledge.get_related_skills
  - knowledge.validate_ksa_measurability

conversation_template_id: null  # Open-ended conversation
access_control:
  allowed_roles: ['certification_owner', 'exam_architect']
```

## MCP Tools Required

### Mosaic Integration Tools

| Tool | Operation | Description |
|------|-----------|-------------|
| `mosaic.get_blueprints` | Query | List blueprints with filters |
| `mosaic.get_blueprint` | Query | Get blueprint by ID with full structure |
| `mosaic.create_blueprint` | Command | Create new blueprint shell |
| `mosaic.add_topic` | Command | Add topic to blueprint |
| `mosaic.add_skill` | Command | Add skill to topic |
| `mosaic.add_ksa` | Command | Add KSA statement to skill |
| `mosaic.update_ksa` | Command | Refine KSA statement |
| `mosaic.submit_for_review` | Command | Submit blueprint for review |
| `mosaic.publish_blueprint` | Command | Publish approved blueprint |

### Knowledge-Manager Tools

| Tool | Operation | Description |
|------|-----------|-------------|
| `knowledge.search_domain` | Query | Search for related concepts in namespace |
| `knowledge.get_skill_hierarchy` | Query | Get skill relationships |
| `knowledge.validate_measurability` | Query | Check if KSA is objectively measurable |
| `knowledge.suggest_cognitive_level` | Query | Suggest Bloom's level from KSA text |

## Event Flow

```
Mosaic                          Event Broker                    Services
  │                                  │                              │
  │  blueprint.created.v1            │                              │
  │─────────────────────────────────►│                              │
  │                                  │────────────────────────────► │
  │                                  │     knowledge-manager:       │
  │                                  │     index new terms          │
  │                                  │                              │
  │  blueprint.topic.added.v1        │                              │
  │─────────────────────────────────►│                              │
  │                                  │────────────────────────────► │
  │                                  │     knowledge-manager:       │
  │                                  │     update namespace         │
  │                                  │                              │
  │  blueprint.published.v1          │                              │
  │─────────────────────────────────►│                              │
  │                                  │────────────────────────────► │
  │                                  │     blueprint-manager:       │
  │                                  │     sync for item generation │
  │                                  │                              │
```

## Measurability Validation

A key innovation is AI-assisted validation of KSA measurability:

```python
# knowledge-manager/application/queries/validate_ksa_measurability.py

@dataclass
class ValidateKSAMeasurabilityQuery:
    ksa_statement: str
    skill_type: str  # knowledge, skill, attitude
    context: str  # certification domain

@dataclass
class MeasurabilityResult:
    is_measurable: bool
    confidence: float
    issues: list[str]
    suggestions: list[str]
    cognitive_level: str
    recommended_item_types: list[str]

# Example evaluation:
# Input: "Understand networking concepts"
# Output:
#   is_measurable: False
#   issues: ["'Understand' is not an observable behavior"]
#   suggestions: ["Replace with: 'Explain the purpose of the OSI model layers'"]
#   cognitive_level: "Remember/Understand"
#   recommended_item_types: ["multiple_choice", "matching"]
```

## Acceptance Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| **KSA Measurability** | % of KSAs passing validation | > 95% |
| **Blueprint Coverage** | Topics align with job task analysis | 100% |
| **Cognitive Distribution** | Balance across Bloom's levels | Per blueprint spec |
| **Time to Blueprint** | Days from start to published | -50% vs current |
| **SME Effort** | Hours spent on refinement | -40% vs current |

## Open Questions

1. **Mosaic Sync Strategy**: Should blueprint-manager maintain a local copy, or always query Mosaic?
2. **Conflict Resolution**: What if AI suggestions conflict with Mosaic's validation rules?
3. **Versioning**: How to handle blueprint versions across systems?
4. **Audit Trail**: Where is the source of truth for who changed what?

---

_Last updated: December 25, 2025_
