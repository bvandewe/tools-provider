# Use Case: Certification Program Design

> **Primary Actor:** Certification Council (Program Architects)
> **Supporting Actors:** CertificationOwner (EPM), AI Program Design Assistant
> **Systems Involved:** blueprint-manager, knowledge-manager, Mosaic (downstream)
> **Accreditation Context:** ANSI/ISO 17024 compliance required

## Overview

Certification Program Design defines the **meta-structure** that governs how individual certifications relate to each other. It establishes invariants between ExamBlueprints, defines what distinguishes certification levels, and ensures coherent progression paths. Today, this knowledge exists as tribal knowledge and scattered documents—a massive opportunity for AI-aided structuring, maintenance, and enforcement.

## The Problem

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CURRENT STATE: TRIBAL KNOWLEDGE                           │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │   "What makes CCNP harder than CCNA?"                                 │ │
│  │                                                                        │ │
│  │   Person A: "More topics, deeper coverage"                            │ │
│  │   Person B: "Higher Bloom's levels—more analysis, less recall"        │ │
│  │   Person C: "Prerequisites and experience requirements"               │ │
│  │   Person D: "I don't know, it's just... harder"                       │ │
│  │                                                                        │ │
│  │   Reality: All are partially right, none is documented                │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  CONSEQUENCES:                                                               │
│  ─────────────                                                               │
│  • Inconsistent difficulty across tracks (CCNP Security ≠ CCNP Enterprise)  │
│  • Blueprint authors interpret "Professional level" differently             │
│  • No enforceable validation that a blueprint meets level requirements      │
│  • ANSI audits require documentation we scramble to produce                 │
│  • New EPMs have no reference for what their level "should" look like       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Domain Model: Certification Program Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CERTIFICATION PROGRAM HIERARCHY                           │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  CERTIFICATION PROGRAM (e.g., "Cisco Certifications")                  │ │
│  │                                                                        │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │  │  CERTIFICATION TRACK (e.g., "Enterprise", "Security", "DevNet")  │ │ │
│  │  │                                                                  │ │ │
│  │  │  ┌────────────────────────────────────────────────────────────┐ │ │ │
│  │  │  │  CERTIFICATION LEVEL                                       │ │ │ │
│  │  │  │                                                            │ │ │ │
│  │  │  │  • Associate (CCNA)                                        │ │ │ │
│  │  │  │  • Professional (CCNP)                                     │ │ │ │
│  │  │  │  • Expert (CCIE)                                           │ │ │ │
│  │  │  │                                                            │ │ │ │
│  │  │  └────────────────────────────────────────────────────────────┘ │ │ │
│  │  │                                                                  │ │ │
│  │  │  ┌────────────────────────────────────────────────────────────┐ │ │ │
│  │  │  │  CERTIFICATION TYPE                                        │ │ │ │
│  │  │  │                                                            │ │ │ │
│  │  │  │  • Core (required, foundational)                           │ │ │ │
│  │  │  │  • Concentration (specialized depth)                       │ │ │ │
│  │  │  │  • Specialist (narrow, specific technology)                │ │ │ │
│  │  │  │                                                            │ │ │ │
│  │  │  └────────────────────────────────────────────────────────────┘ │ │ │
│  │  │                                                                  │ │ │
│  │  └──────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  EXAMPLE: CCNP Enterprise                                                    │
│  ─────────────────────────                                                   │
│  Track: Enterprise                                                           │
│  Level: Professional                                                         │
│  Structure:                                                                  │
│    • ENCOR (Core exam - required)                                           │
│    • + 1 Concentration exam (ENARSI, SD-WAN, etc.)                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Certification Level Invariants

### Level Definitions

```yaml
# Seed data for knowledge-manager: Certification Levels
certification_levels:

  associate:
    name: "Associate"
    code: "CCA"  # Cisco Certified Associate
    description: |
      Entry-level certification validating foundational knowledge and skills.
      Candidates demonstrate understanding of core concepts and ability to
      perform basic tasks under guidance.

    target_audience:
      experience_years: "0-2"
      typical_roles:
        - "Junior Network Administrator"
        - "Help Desk Technician"
        - "Network Support Specialist"
      prerequisites: "None (recommended training or self-study)"

    cognitive_profile:
      bloom_taxonomy_distribution:
        remember: "20-30%"    # Recall facts, terminology
        understand: "30-40%"  # Explain concepts, interpret
        apply: "25-35%"       # Use knowledge in situations
        analyze: "5-15%"      # Limited analysis
        evaluate: "0-5%"      # Minimal evaluation
        create: "0%"          # Not expected at this level

      prohibited_verbs:
        - "design"      # Too advanced
        - "architect"   # Too advanced
        - "optimize"    # Requires deep experience
        - "evaluate"    # Limited at this level

      encouraged_verbs:
        - "identify"
        - "describe"
        - "configure"   # Basic configuration
        - "verify"      # Basic verification
        - "troubleshoot"  # Guided troubleshooting

    knowledge_profile:
      breadth: "broad"      # Cover many topics
      depth: "shallow"      # Surface-level understanding
      integration: "low"    # Topics largely independent

    exam_characteristics:
      typical_duration: "90-120 minutes"
      item_count: "90-120 items"
      item_types:
        - "multiple-choice"
        - "drag-and-drop"
        - "simulation (basic)"
      pass_rate_target: "65-75%"  # Accessible entry point

    relationship_to_other_levels:
      prerequisite_for: ["professional"]
      builds_upon: null

  professional:
    name: "Professional"
    code: "CCP"  # Cisco Certified Professional
    description: |
      Mid-level certification validating comprehensive knowledge and practical
      skills. Candidates demonstrate ability to plan, implement, and troubleshoot
      complex solutions independently.

    target_audience:
      experience_years: "3-5"
      typical_roles:
        - "Network Engineer"
        - "Systems Engineer"
        - "Network Architect (junior)"
      prerequisites: "Associate certification OR equivalent experience"

    cognitive_profile:
      bloom_taxonomy_distribution:
        remember: "10-15%"
        understand: "15-25%"
        apply: "30-40%"
        analyze: "20-30%"
        evaluate: "5-15%"
        create: "0-5%"

      prohibited_verbs:
        - "list"        # Too basic
        - "define"      # Too basic (unless complex concept)

      encouraged_verbs:
        - "implement"
        - "troubleshoot"
        - "analyze"
        - "compare"
        - "optimize"    # Begin optimization
        - "integrate"

    knowledge_profile:
      breadth: "focused"      # Deeper in track area
      depth: "moderate-deep"  # Practical depth
      integration: "moderate" # Cross-topic understanding

    exam_characteristics:
      typical_duration: "120 minutes (core) + concentration"
      item_count: "100-120 items (core)"
      item_types:
        - "multiple-choice"
        - "simulation"
        - "testlet (scenario-based)"
      pass_rate_target: "55-65%"

    relationship_to_other_levels:
      prerequisite_for: ["expert"]
      builds_upon: ["associate"]

  expert:
    name: "Expert"
    code: "CCIE"  # Cisco Certified Internetwork Expert
    description: |
      Elite certification validating expert-level mastery. Candidates demonstrate
      ability to design, deploy, and optimize complex enterprise solutions.
      Recognized as the gold standard in networking certification.

    target_audience:
      experience_years: "5-8+"
      typical_roles:
        - "Senior Network Architect"
        - "Principal Engineer"
        - "Technical Leader"
        - "Consulting Engineer"
      prerequisites: "Professional certification + extensive experience"

    cognitive_profile:
      bloom_taxonomy_distribution:
        remember: "5-10%"
        understand: "10-15%"
        apply: "15-25%"
        analyze: "25-35%"
        evaluate: "15-25%"
        create: "10-20%"

      prohibited_verbs:
        - "list"
        - "define"
        - "describe"  # Only for complex concepts

      encouraged_verbs:
        - "design"
        - "architect"
        - "optimize"
        - "evaluate"
        - "diagnose"
        - "integrate"
        - "transform"

    knowledge_profile:
      breadth: "comprehensive"  # Full domain coverage
      depth: "expert"           # Deep understanding
      integration: "high"       # Cross-domain synthesis

    exam_characteristics:
      typical_duration: "8 hours (practical lab)"
      format: "hands-on lab exam"
      item_types:
        - "design module (2-3 hours)"
        - "deploy module (5-6 hours)"
      pass_rate_target: "20-35%"  # Elite credential

    relationship_to_other_levels:
      prerequisite_for: null
      builds_upon: ["professional"]
```

### Certification Type Definitions

```yaml
# Seed data for knowledge-manager: Certification Types
certification_types:

  core:
    name: "Core"
    description: |
      Required foundational exam within a certification track.
      Covers broad, fundamental knowledge essential to the domain.
      Must be passed to earn the certification.

    characteristics:
      required: true
      count_per_certification: 1
      breadth: "comprehensive within domain"
      depth: "foundational to moderate"

    blueprint_constraints:
      min_topics: 5
      max_topics: 10
      coverage_requirement: "All major domain areas"

    examples:
      - "350-401 ENCOR (CCNP Enterprise Core)"
      - "350-701 SCOR (CCNP Security Core)"
      - "350-501 SPCOR (CCNP Service Provider Core)"
      - "350-901 DevCOR (DevNet Professional Core)"

  concentration:
    name: "Concentration"
    description: |
      Specialized exam that provides depth in a specific area.
      One concentration required alongside core to complete certification.
      Allows candidates to demonstrate specialized expertise.

    characteristics:
      required: "one_of_set"
      count_per_certification: "1 from available options"
      breadth: "narrow, focused area"
      depth: "deep"

    blueprint_constraints:
      min_topics: 3
      max_topics: 6
      specialization_depth: "expert-level in focus area"

    examples:
      - "300-410 ENARSI (Enterprise Advanced Routing)"
      - "300-420 ENSLD (Enterprise Design)"
      - "300-430 ENWLSI (Enterprise Wireless)"
      - "300-710 SNCF (Security Firepower)"

  specialist:
    name: "Specialist"
    description: |
      Standalone certification focused on specific technology or product.
      Does not require core exam. Validates focused expertise.
      Often tied to emerging or specialized technologies.

    characteristics:
      required: false
      standalone: true
      breadth: "very narrow"
      depth: "deep in specific technology"

    blueprint_constraints:
      min_topics: 2
      max_topics: 4
      technology_focus: "single technology or product"

    examples:
      - "300-835 CLAUTO (Collaboration Automation)"
      - "300-920 DEVIOT (IoT Development)"
      - "700-xxx (Specialist exams)"
```

## Cross-Level Invariants (Program Rules)

```python
# Blueprint validation rules enforced by blueprint-manager
from dataclasses import dataclass
from enum import Enum

class CertificationLevel(Enum):
    ASSOCIATE = "associate"
    PROFESSIONAL = "professional"
    EXPERT = "expert"

class BloomLevel(Enum):
    REMEMBER = 1
    UNDERSTAND = 2
    APPLY = 3
    ANALYZE = 4
    EVALUATE = 5
    CREATE = 6

@dataclass
class LevelInvariant:
    """Rule that must hold for blueprints at a given level."""
    invariant_id: str
    level: CertificationLevel
    rule_type: str
    description: str
    validation_logic: str  # Pseudocode or reference
    severity: str  # "error" (blocks), "warning" (flags), "info" (suggests)


# Example invariants
LEVEL_INVARIANTS = [

    # Bloom's taxonomy enforcement
    LevelInvariant(
        invariant_id="BLOOM-001",
        level=CertificationLevel.ASSOCIATE,
        rule_type="bloom_distribution",
        description="Associate blueprints must have ≥50% items at Remember/Understand/Apply",
        validation_logic="sum(items.bloom in [1,2,3]) / total_items >= 0.50",
        severity="error"
    ),
    LevelInvariant(
        invariant_id="BLOOM-002",
        level=CertificationLevel.ASSOCIATE,
        description="Associate blueprints should not have >5% items at Evaluate/Create",
        validation_logic="sum(items.bloom in [5,6]) / total_items <= 0.05",
        severity="warning"
    ),
    LevelInvariant(
        invariant_id="BLOOM-003",
        level=CertificationLevel.EXPERT,
        description="Expert blueprints must have ≥40% items at Analyze/Evaluate/Create",
        validation_logic="sum(items.bloom in [4,5,6]) / total_items >= 0.40",
        severity="error"
    ),

    # Knowledge breadth/depth
    LevelInvariant(
        invariant_id="BREADTH-001",
        level=CertificationLevel.ASSOCIATE,
        description="Associate must cover ≥80% of track knowledge areas",
        validation_logic="covered_kas / track_total_kas >= 0.80",
        severity="error"
    ),
    LevelInvariant(
        invariant_id="DEPTH-001",
        level=CertificationLevel.PROFESSIONAL,
        description="Professional must have ≥30% items requiring multi-concept integration",
        validation_logic="items.integration_required / total_items >= 0.30",
        severity="warning"
    ),

    # Verb usage
    LevelInvariant(
        invariant_id="VERB-001",
        level=CertificationLevel.ASSOCIATE,
        description="Associate items should not use 'design' or 'architect' verbs",
        validation_logic="items.verb not in PROHIBITED_VERBS[associate]",
        severity="error"
    ),
    LevelInvariant(
        invariant_id="VERB-002",
        level=CertificationLevel.EXPERT,
        description="Expert items should minimize 'list', 'define', 'describe' verbs",
        validation_logic="items.verb in ['list','define','describe'] / total <= 0.10",
        severity="warning"
    ),

    # Experience assumptions
    LevelInvariant(
        invariant_id="EXP-001",
        level=CertificationLevel.ASSOCIATE,
        description="Associate items must not assume production network experience",
        validation_logic="items.experience_required <= 'lab_only'",
        severity="error"
    ),

    # Prerequisite knowledge
    LevelInvariant(
        invariant_id="PREREQ-001",
        level=CertificationLevel.PROFESSIONAL,
        description="Professional blueprints may assume Associate-level knowledge",
        validation_logic="item.assumed_knowledge <= professional_assumed",
        severity="info"
    ),
]
```

## AI Program Design Assistant

```yaml
agent_id: 'program-design-assistant'
name: 'Certification Program Design Assistant'
description: 'AI assistant for defining and validating certification program structure'

system_prompt: |
  You are an expert in certification program design, psychometrics, and
  competency-based assessment. You help Certification Council members and
  EPMs design coherent certification programs.

  ## Your Expertise

  - ANSI/ISO 17024 accreditation requirements
  - Bloom's Taxonomy application to assessment
  - Competency framework design
  - Certification level differentiation
  - Industry certification best practices

  ## Your Responsibilities

  1. **Structure Knowledge**: Help convert tribal knowledge into documented,
     enforceable program definitions

  2. **Validate Blueprints**: Check blueprints against level invariants

  3. **Ensure Consistency**: Flag when blueprints within a level diverge

  4. **Guide EPMs**: Help new EPMs understand what their level requires

  5. **Prepare for Audits**: Generate documentation for accreditation

  ## Key Principles

  - Level definitions should be measurable and objective
  - Invariants should be enforceable by systems, not just guidelines
  - Consistency across tracks matters for brand integrity
  - Changes to level definitions have broad downstream impact

tools:
  - program.get_level_definition      # Get level requirements
  - program.get_track_definition      # Get track structure
  - program.list_invariants           # List all program rules
  - program.validate_blueprint        # Check blueprint against rules
  - program.compare_blueprints        # Compare across tracks
  - program.get_bloom_distribution    # Analyze Bloom's in blueprint
  - program.suggest_improvements      # Recommend blueprint changes
  - knowledge.query_program_rules     # Query knowledge graph
  - knowledge.add_program_rule        # Add new rule to knowledge

conversation_template_id: null  # Open-ended design work
access_control:
  allowed_roles: ['certification_council', 'epm', 'program_architect']
```

## Workflow: Defining a New Certification Level

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NEW CERTIFICATION LEVEL DESIGN                            │
│                                                                              │
│  Council Member               AI Assistant              Knowledge Manager    │
│       │                            │                          │              │
│       │  "We're introducing a      │                          │              │
│       │   'Practitioner' level     │                          │              │
│       │   between Associate and    │                          │              │
│       │   Professional"            │                          │              │
│       │───────────────────────────►│                          │              │
│       │                            │                          │              │
│       │  "Great! Let me help       │                          │              │
│       │   define this level.       │                          │              │
│       │                            │                          │              │
│       │   Based on Associate and   │                          │              │
│       │   Professional definitions,│                          │              │
│       │   here's a suggested       │                          │              │
│       │   Practitioner profile:    │                          │              │
│       │                            │                          │              │
│       │   Experience: 2-3 years    │                          │              │
│       │   Bloom's: 15% R, 25% U,   │                          │              │
│       │            35% Ap, 20% An, │                          │              │
│       │            5% Ev           │                          │              │
│       │   Breadth: Focused         │                          │              │
│       │   Depth: Moderate          │                          │              │
│       │                            │                          │              │
│       │   Does this align with     │                          │              │
│       │   your vision?"            │                          │              │
│       │◄───────────────────────────│                          │              │
│       │                            │                          │              │
│       │  "Yes, but we want more    │                          │              │
│       │   emphasis on Apply"       │                          │              │
│       │───────────────────────────►│                          │              │
│       │                            │                          │              │
│       │  "Understood. Adjusting    │                          │              │
│       │   to 40% Apply. This       │                          │              │
│       │   means we need to define  │                          │              │
│       │   invariants that ensure   │                          │              │
│       │   Practitioner is harder   │                          │              │
│       │   than Associate but       │                          │              │
│       │   easier than Professional.│                          │              │
│       │                            │                          │              │
│       │   Proposed invariants:     │                          │              │
│       │   PRAC-001: Apply ≥ 35%    │                          │              │
│       │   PRAC-002: Analyze < 25%  │                          │              │
│       │   PRAC-003: No Create      │                          │              │
│       │                            │                          │              │
│       │   Shall I save these?"     │                          │              │
│       │◄───────────────────────────│                          │              │
│       │                            │                          │              │
│       │  "Yes, save and document"  │                          │              │
│       │───────────────────────────►│                          │              │
│       │                            │                          │              │
│       │                            │  Store level definition  │              │
│       │                            │  and invariants          │              │
│       │                            │─────────────────────────►│              │
│       │                            │                          │              │
│       │  "Done. The Practitioner   │                          │              │
│       │   level is now defined.    │                          │              │
│       │   All new blueprints at    │                          │              │
│       │   this level will be       │                          │              │
│       │   validated against these  │                          │              │
│       │   invariants."             │                          │              │
│       │◄───────────────────────────│                          │              │
│       │                            │                          │              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Blueprint Validation Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BLUEPRINT LEVEL VALIDATION                                │
│                                                                              │
│  EPM submits blueprint                                                       │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  AI VALIDATION ENGINE                                                │   │
│  │                                                                      │   │
│  │  1. Load level invariants for this blueprint's level                 │   │
│  │  2. Analyze blueprint content:                                       │   │
│  │     - Bloom's distribution across all KSAs                           │   │
│  │     - Verb usage in KSA statements                                   │   │
│  │     - Breadth coverage of knowledge areas                            │   │
│  │     - Depth indicators                                               │   │
│  │  3. Check each invariant                                             │   │
│  │  4. Generate validation report                                       │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  VALIDATION REPORT                                                   │   │
│  │                                                                      │   │
│  │  Blueprint: CCNP Enterprise Core (ENCOR) v2025.1                     │   │
│  │  Level: Professional                                                 │   │
│  │                                                                      │   │
│  │  ✅ PASSED (3)                                                       │   │
│  │  • BLOOM-003: 45% at Analyze/Evaluate/Create (≥40% required)        │   │
│  │  • DEPTH-001: 35% integration items (≥30% required)                 │   │
│  │  • VERB-002: 8% basic verbs (≤10% allowed)                          │   │
│  │                                                                      │   │
│  │  ⚠️ WARNINGS (1)                                                     │   │
│  │  • BREADTH-002: Topic 4.3 has only 3% coverage (recommend ≥5%)      │   │
│  │                                                                      │   │
│  │  ❌ FAILED (1)                                                       │   │
│  │  • PREREQ-002: KSA 2.1.4 assumes Expert-level knowledge             │   │
│  │    "Design multi-site EVPN fabric"—'Design' verb inappropriate      │   │
│  │    Suggestion: Reframe as "Implement" or "Configure"                │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Knowledge Graph Seeding

```yaml
# Entities to seed in knowledge-manager

entities:
  - type: CertificationProgram
    id: "cisco-certifications"
    properties:
      name: "Cisco Certifications"
      accreditation: "ANSI/ISO 17024"
      version: "2.0"  # Certifications 2.0 (2020)

  - type: CertificationLevel
    id: "level-associate"
    properties:
      name: "Associate"
      code: "CCA"
      experience_years: "0-2"
      bloom_primary: ["remember", "understand", "apply"]

  - type: CertificationLevel
    id: "level-professional"
    properties:
      name: "Professional"
      code: "CCP"
      experience_years: "3-5"
      bloom_primary: ["apply", "analyze"]

  - type: CertificationLevel
    id: "level-expert"
    properties:
      name: "Expert"
      code: "CCIE"
      experience_years: "5-8+"
      bloom_primary: ["analyze", "evaluate", "create"]

  - type: CertificationType
    id: "type-core"
    properties:
      name: "Core"
      required: true
      breadth: "comprehensive"

  - type: CertificationType
    id: "type-concentration"
    properties:
      name: "Concentration"
      required: "one_of_set"
      depth: "specialized"

  - type: CertificationTrack
    id: "track-enterprise"
    properties:
      name: "Enterprise"
      domain: "Enterprise Networking"

relations:
  - from: "cisco-certifications"
    to: "level-associate"
    type: "HAS_LEVEL"

  - from: "level-associate"
    to: "level-professional"
    type: "PREREQUISITE_FOR"

  - from: "level-professional"
    to: "level-expert"
    type: "PREREQUISITE_FOR"

  - from: "track-enterprise"
    to: "type-core"
    type: "REQUIRES"

  - from: "track-enterprise"
    to: "type-concentration"
    type: "REQUIRES_ONE_OF"
```

## Acceptance Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| **Level definitions documented** | % of levels with complete definition | 100% |
| **Invariants enforceable** | % of invariants with validation logic | 100% |
| **Blueprint validation** | % of blueprints validated before publish | 100% |
| **Cross-track consistency** | Variance in difficulty within level | < 15% |
| **ANSI audit readiness** | Hours to produce documentation | < 4 hours |
| **New EPM onboarding** | Time to understand level requirements | < 1 day |

## Open Questions

1. **Invariant Strictness**: Should invariant violations block blueprint publication, or just warn?
2. **Track Variations**: Can different tracks have different Bloom's distributions at the same level?
3. **Historical Blueprints**: How to handle existing blueprints that don't meet new invariants?
4. **Market Alignment**: Should level definitions adapt to industry changes, or remain stable?
5. **Specialist Exams**: Do Specialist certifications have level invariants, or are they independent?

---

_Last updated: December 25, 2025_
