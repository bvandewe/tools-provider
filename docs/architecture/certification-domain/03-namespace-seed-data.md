# Certification Program Namespace - Seed Data

> **Namespace ID:** `certification-program`
> **Purpose:** Reference data for certification program structure (levels, types, tracks, rules)
> **Service:** knowledge-manager
> **Status:** Seed Data Definition
> **Last Updated:** January 2025

## Overview

This document defines the seed data for the `certification-program` namespace in knowledge-manager. This namespace contains the slowly-evolving reference data that defines "what certification means" - the rules, constraints, and vocabulary that blueprint-manager uses for validation.

## Namespace Metadata

```yaml
namespace:
  id: "certification-program"
  name: "Certification Program Structure"
  description: |
    Reference data defining the certification program hierarchy, including
    certification levels (Associate/Professional/Expert), types (Core/Concentration/Specialist),
    tracks (Enterprise/Security/DevNet/etc.), and the validation rules that govern
    blueprint development. This namespace is managed by the Certification Council
    and changes infrequently.

  icon: "bi-award"
  access_level: "public"  # All services can read
  owner_tenant_id: null   # Global/shared namespace
  owner_user_id: "system"
```

## Terms

### Certification Levels

```yaml
terms:
  # === CERTIFICATION LEVELS ===

  - id: "level-associate"
    term: "Associate"
    definition: |
      Entry-level certification validating foundational knowledge and skills.
      Candidates demonstrate understanding of core concepts and ability to
      perform basic tasks under guidance. Target audience: 0-2 years experience.
    aliases:
      - "CCNA"
      - "Entry Level"
      - "Foundation"
    examples:
      - "CCNA (Cisco Certified Network Associate)"
      - "DevNet Associate"
    context_hint: "Use when referring to entry-level certifications"

  - id: "level-professional"
    term: "Professional"
    definition: |
      Mid-level certification validating comprehensive knowledge and practical
      skills. Candidates demonstrate ability to plan, implement, and troubleshoot
      complex solutions independently. Target audience: 3-5 years experience.
    aliases:
      - "CCNP"
      - "Mid Level"
    examples:
      - "CCNP Enterprise"
      - "CCNP Security"
      - "DevNet Professional"
    context_hint: "Use when referring to mid-level professional certifications"

  - id: "level-expert"
    term: "Expert"
    definition: |
      Elite certification validating expert-level mastery. Candidates demonstrate
      ability to design, deploy, and optimize complex enterprise solutions.
      Recognized as the gold standard in networking certification.
      Target audience: 5-8+ years experience.
    aliases:
      - "CCIE"
      - "Expert Level"
      - "Architect"
    examples:
      - "CCIE Enterprise Infrastructure"
      - "CCIE Security"
      - "DevNet Expert"
    context_hint: "Use when referring to expert-level certifications"
```

### Certification Types

```yaml
  # === CERTIFICATION TYPES ===

  - id: "type-core"
    term: "Core"
    definition: |
      Required foundational exam within a certification track. Covers broad,
      fundamental knowledge essential to the domain. Must be passed to earn
      the certification. One core exam per certification.
    aliases:
      - "Core Exam"
      - "Required Exam"
    examples:
      - "350-401 ENCOR (CCNP Enterprise Core)"
      - "350-701 SCOR (CCNP Security Core)"
      - "350-901 DevCOR (DevNet Professional Core)"
    context_hint: "The mandatory exam in a certification path"

  - id: "type-concentration"
    term: "Concentration"
    definition: |
      Specialized exam providing depth in a specific area. One concentration
      required alongside core to complete certification. Allows candidates
      to demonstrate specialized expertise within their track.
    aliases:
      - "Concentration Exam"
      - "Specialization"
      - "Elective"
    examples:
      - "300-410 ENARSI (Enterprise Advanced Routing)"
      - "300-420 ENSLD (Enterprise Design)"
      - "300-710 SNCF (Security Firepower)"
    context_hint: "Choose one concentration to complete certification"

  - id: "type-specialist"
    term: "Specialist"
    definition: |
      Standalone certification focused on specific technology or product.
      Does not require core exam. Validates focused expertise. Often tied
      to emerging or specialized technologies.
    aliases:
      - "Specialist Exam"
      - "Standalone"
      - "Technology Certification"
    examples:
      - "300-835 CLAUTO (Collaboration Automation)"
      - "700-xxx series exams"
    context_hint: "Independent certification for specific technology"
```

### Certification Tracks

```yaml
  # === CERTIFICATION TRACKS ===

  - id: "track-enterprise"
    term: "Enterprise"
    definition: |
      Certification track focused on enterprise networking infrastructure
      including routing, switching, wireless, and SD-WAN. Covers technologies
      used in campus and branch networks.
    aliases:
      - "Enterprise Networking"
      - "Routing & Switching"
      - "R&S"
    examples:
      - "CCNP Enterprise"
      - "CCIE Enterprise Infrastructure"
    context_hint: "For enterprise campus and branch networking"

  - id: "track-security"
    term: "Security"
    definition: |
      Certification track focused on network security including firewalls,
      VPNs, identity services, and threat defense. Covers security technologies
      across enterprise and service provider environments.
    aliases:
      - "Network Security"
      - "InfoSec"
    examples:
      - "CCNP Security"
      - "CCIE Security"
    context_hint: "For security-focused certifications"

  - id: "track-devnet"
    term: "DevNet"
    definition: |
      Certification track focused on network automation, programmability,
      and DevOps practices. Covers APIs, Python, Ansible, and software
      development for network infrastructure.
    aliases:
      - "Network Automation"
      - "Programmability"
      - "NetDevOps"
    examples:
      - "DevNet Associate"
      - "DevNet Professional"
    context_hint: "For automation and programmability certifications"

  - id: "track-collaboration"
    term: "Collaboration"
    definition: |
      Certification track focused on unified communications, video,
      and collaboration technologies. Covers voice, video, messaging,
      and collaboration applications.
    aliases:
      - "UC"
      - "Unified Communications"
      - "Voice"
    examples:
      - "CCNP Collaboration"
      - "CCIE Collaboration"
    context_hint: "For collaboration and UC certifications"

  - id: "track-service-provider"
    term: "Service Provider"
    definition: |
      Certification track focused on service provider technologies
      including MPLS, segment routing, and carrier-grade networking.
      Covers technologies used by ISPs and large carriers.
    aliases:
      - "SP"
      - "Carrier"
      - "ISP"
    examples:
      - "CCNP Service Provider"
      - "CCIE Service Provider"
    context_hint: "For service provider and carrier certifications"

  - id: "track-data-center"
    term: "Data Center"
    definition: |
      Certification track focused on data center technologies including
      Nexus switching, ACI, UCS, and storage networking. Covers
      technologies used in modern data center environments.
    aliases:
      - "DC"
      - "ACI"
      - "Nexus"
    examples:
      - "CCNP Data Center"
      - "CCIE Data Center"
    context_hint: "For data center infrastructure certifications"
```

### Bloom's Taxonomy

```yaml
  # === BLOOM'S TAXONOMY LEVELS ===

  - id: "bloom-remember"
    term: "Remember"
    definition: |
      Bloom's Taxonomy Level 1: Recall facts, terms, basic concepts, and answers.
      Items at this level test recognition and retrieval of information.
    aliases:
      - "Recall"
      - "Recognition"
      - "Level 1"
    examples:
      - "List the layers of the OSI model"
      - "Identify the default OSPF hello timer"
    context_hint: "Testing factual recall"

  - id: "bloom-understand"
    term: "Understand"
    definition: |
      Bloom's Taxonomy Level 2: Demonstrate understanding of facts and ideas
      by organizing, comparing, interpreting, and describing.
    aliases:
      - "Comprehension"
      - "Interpret"
      - "Level 2"
    examples:
      - "Explain the difference between TCP and UDP"
      - "Describe how OSPF establishes neighbor adjacencies"
    context_hint: "Testing comprehension and interpretation"

  - id: "bloom-apply"
    term: "Apply"
    definition: |
      Bloom's Taxonomy Level 3: Use acquired knowledge to solve problems
      in new situations. Apply concepts to perform tasks.
    aliases:
      - "Application"
      - "Implement"
      - "Level 3"
    examples:
      - "Configure OSPF on a router given specific requirements"
      - "Apply ACL rules to filter traffic"
    context_hint: "Testing practical application of knowledge"

  - id: "bloom-analyze"
    term: "Analyze"
    definition: |
      Bloom's Taxonomy Level 4: Examine and break information into components,
      determine relationships, identify causes. Troubleshooting scenarios.
    aliases:
      - "Analysis"
      - "Troubleshoot"
      - "Diagnose"
      - "Level 4"
    examples:
      - "Analyze show command output to identify the root cause"
      - "Determine why OSPF neighbors are stuck in EXSTART state"
    context_hint: "Testing analytical and troubleshooting skills"

  - id: "bloom-evaluate"
    term: "Evaluate"
    definition: |
      Bloom's Taxonomy Level 5: Make judgments based on criteria and standards.
      Justify decisions, compare solutions, assess trade-offs.
    aliases:
      - "Evaluation"
      - "Assess"
      - "Judge"
      - "Level 5"
    examples:
      - "Evaluate which routing protocol is best for a given scenario"
      - "Assess the security implications of a proposed design"
    context_hint: "Testing judgment and decision-making"

  - id: "bloom-create"
    term: "Create"
    definition: |
      Bloom's Taxonomy Level 6: Produce new or original work. Design solutions,
      build architectures, develop comprehensive plans.
    aliases:
      - "Design"
      - "Architect"
      - "Synthesize"
      - "Level 6"
    examples:
      - "Design a multi-site SD-WAN architecture"
      - "Create a migration plan from legacy to modern infrastructure"
    context_hint: "Testing design and synthesis abilities"
```

## Rules

### Bloom's Distribution Rules

```yaml
rules:
  # === BLOOM'S DISTRIBUTION RULES (per level) ===

  - id: "bloom-dist-associate"
    name: "Associate Level Bloom's Distribution"
    rule_type: "constraint"
    condition: "certification_level == 'associate'"
    rule_text: |
      For Associate-level blueprints:
      - Remember + Understand + Apply ≥ 50% of items
      - Analyze ≤ 15% of items
      - Evaluate + Create ≤ 5% of items

      Associate certifications focus on foundational knowledge (Remember/Understand)
      and basic practical skills (Apply). Higher cognitive levels are limited
      as candidates are not expected to have significant real-world experience.
    applies_to_term_ids:
      - "level-associate"
    priority: 1

  - id: "bloom-dist-professional"
    name: "Professional Level Bloom's Distribution"
    rule_type: "constraint"
    condition: "certification_level == 'professional'"
    rule_text: |
      For Professional-level blueprints:
      - Apply + Analyze ≥ 50% of items
      - Remember + Understand ≤ 25% of items
      - Evaluate ≤ 15% of items
      - Create ≤ 5% of items

      Professional certifications emphasize practical application and
      troubleshooting. Basic recall is minimized as assumed knowledge.
    applies_to_term_ids:
      - "level-professional"
    priority: 1

  - id: "bloom-dist-expert"
    name: "Expert Level Bloom's Distribution"
    rule_type: "constraint"
    condition: "certification_level == 'expert'"
    rule_text: |
      For Expert-level blueprints:
      - Analyze + Evaluate + Create ≥ 40% of items
      - Remember + Understand ≤ 15% of items
      - Apply: 20-35% of items

      Expert certifications require higher-order thinking with significant
      emphasis on analysis, evaluation, and design capabilities.
    applies_to_term_ids:
      - "level-expert"
    priority: 1
```

### Verb Usage Rules

```yaml
  # === VERB USAGE RULES ===

  - id: "verb-prohibited-associate"
    name: "Prohibited Verbs for Associate Level"
    rule_type: "constraint"
    condition: "certification_level == 'associate'"
    rule_text: |
      The following verbs are PROHIBITED in Associate-level KSA statements:
      - "design" - Requires expert-level synthesis
      - "architect" - Implies complex system design
      - "optimize" - Requires deep experience
      - "evaluate" - Limited at entry level
      - "transform" - Too advanced

      These verbs imply cognitive complexity beyond Associate level expectations.
      Use instead: identify, describe, configure, verify, explain.
    applies_to_term_ids:
      - "level-associate"
    priority: 2

  - id: "verb-prohibited-professional"
    name: "Discouraged Verbs for Professional Level"
    rule_type: "warning"
    condition: "certification_level == 'professional'"
    rule_text: |
      The following verbs should be MINIMIZED in Professional-level KSA statements:
      - "list" - Too basic (≤10% of items)
      - "define" - Too basic unless for complex concepts
      - "name" - Too basic

      Professional candidates should demonstrate application and analysis,
      not just recall. Basic recall verbs suggest content may be too easy.
    applies_to_term_ids:
      - "level-professional"
    priority: 2

  - id: "verb-required-expert"
    name: "Required Verbs for Expert Level"
    rule_type: "guideline"
    condition: "certification_level == 'expert'"
    rule_text: |
      Expert-level blueprints should include significant use of:
      - "design" - Architecture and solution design
      - "evaluate" - Trade-off analysis and judgment
      - "optimize" - Performance and efficiency
      - "diagnose" - Complex troubleshooting
      - "integrate" - Multi-system synthesis

      At least 30% of KSA statements should use these expert-level verbs.
    applies_to_term_ids:
      - "level-expert"
    priority: 2
```

### Structure Rules

```yaml
  # === STRUCTURE RULES ===

  - id: "topic-weight-distribution"
    name: "Topic Weight Distribution"
    rule_type: "constraint"
    condition: "always"
    rule_text: |
      Blueprint topic weights must satisfy:
      - Sum of all topic weights = 100%
      - No single topic > 30% (prevents over-reliance on one area)
      - No topic < 5% (ensures meaningful coverage)
      - Core exams: 5-10 topics
      - Concentration exams: 3-6 topics
    applies_to_term_ids:
      - "type-core"
      - "type-concentration"
    priority: 1

  - id: "ksa-count-requirements"
    name: "KSA Count Requirements"
    rule_type: "guideline"
    condition: "always"
    rule_text: |
      Recommended KSA counts per exam type:
      - Core exams: 50-80 KSA statements
      - Concentration exams: 30-50 KSA statements
      - Specialist exams: 20-35 KSA statements

      Each skill should have 2-8 KSA statements for adequate coverage.
      Fewer than 2 suggests the skill is too narrow; more than 8 suggests
      the skill should be split.
    applies_to_term_ids:
      - "type-core"
      - "type-concentration"
      - "type-specialist"
    priority: 3

  - id: "skill-statement-format"
    name: "Skill Statement Format"
    rule_type: "constraint"
    condition: "always"
    rule_text: |
      All skill statements MUST:
      1. Begin with an action verb from Bloom's taxonomy
      2. Include a clear object (what is being acted upon)
      3. Optionally include context or conditions

      Format: [Verb] [Object] [(optional) Context]

      Examples:
      ✓ "Configure OSPF in a multi-area network"
      ✓ "Troubleshoot EIGRP neighbor adjacency issues"
      ✗ "OSPF configuration" (no verb)
      ✗ "Understand routing" (too vague)
    applies_to_term_ids: []
    priority: 1

  - id: "mqc-definition-required"
    name: "MQC Definition Required"
    rule_type: "constraint"
    condition: "status == 'ready_for_review'"
    rule_text: |
      Before submission for review, blueprints MUST have a complete
      Minimally Qualified Candidate (MQC) definition including:
      - Experience years range
      - Target job roles (at least 2)
      - Prerequisite knowledge (what is assumed)
      - Excluded knowledge (what is out of scope)
      - Passing standard description

      The MQC definition establishes the psychometric foundation for
      item development and cut score setting.
    applies_to_term_ids: []
    priority: 1
```

### Naming Convention Rules

```yaml
  # === NAMING CONVENTION RULES ===

  - id: "exam-code-format"
    name: "Exam Code Format"
    rule_type: "constraint"
    condition: "always"
    rule_text: |
      Exam codes must follow the format: XXX-XXX
      - First three digits: Certification family (350=Core, 300=Concentration, etc.)
      - Last three digits: Unique exam identifier

      Examples: 350-401, 300-410, 200-301
    applies_to_term_ids: []
    priority: 1

  - id: "topic-numbering"
    name: "Topic Numbering Convention"
    rule_type: "guideline"
    condition: "always"
    rule_text: |
      Topics should be numbered X.0 where X is the topic sequence:
      - 1.0 Architecture
      - 2.0 Virtualization
      - 3.0 Infrastructure

      Skills within topics: X.Y (e.g., 1.1, 1.2)
      KSA statements: X.Y.Z or X.Y.a (e.g., 1.1.1 or 1.1.a)
    applies_to_term_ids: []
    priority: 3
```

## Relationships

### Level Progression

```yaml
relationships:
  # === LEVEL PROGRESSION ===

  - id: "rel-assoc-to-prof"
    source_term_id: "level-associate"
    target_term_id: "level-professional"
    relationship_type: "PREREQUISITE_FOR"
    description: "Associate certification is a prerequisite for Professional"
    bidirectional: false
    weight: 1.0

  - id: "rel-prof-to-expert"
    source_term_id: "level-professional"
    target_term_id: "level-expert"
    relationship_type: "PREREQUISITE_FOR"
    description: "Professional certification is a prerequisite for Expert"
    bidirectional: false
    weight: 1.0
```

### Certification Type Requirements

```yaml
  # === CERTIFICATION TYPE REQUIREMENTS ===

  - id: "rel-core-required"
    source_term_id: "type-core"
    target_term_id: "level-professional"
    relationship_type: "REQUIRED_FOR"
    description: "Core exam is required for Professional certification"
    bidirectional: false
    weight: 1.0

  - id: "rel-conc-complements-core"
    source_term_id: "type-concentration"
    target_term_id: "type-core"
    relationship_type: "COMPLEMENTS"
    description: "Concentration exam complements core for complete certification"
    bidirectional: true
    weight: 0.8
```

### Track to Technology Associations

```yaml
  # === TRACK ASSOCIATIONS ===

  - id: "rel-ent-routing"
    source_term_id: "track-enterprise"
    target_term_id: "tech-routing"
    relationship_type: "COVERS"
    description: "Enterprise track covers routing technologies"
    bidirectional: false
    weight: 1.0

  - id: "rel-sec-firewall"
    source_term_id: "track-security"
    target_term_id: "tech-firewall"
    relationship_type: "COVERS"
    description: "Security track covers firewall technologies"
    bidirectional: false
    weight: 1.0

  - id: "rel-devnet-automation"
    source_term_id: "track-devnet"
    target_term_id: "tech-automation"
    relationship_type: "COVERS"
    description: "DevNet track covers automation technologies"
    bidirectional: false
    weight: 1.0
```

### Bloom Level to Verb Associations

```yaml
  # === BLOOM TO VERB ASSOCIATIONS ===

  - id: "rel-remember-verbs"
    source_term_id: "bloom-remember"
    target_term_id: "verbs-remember"
    relationship_type: "USES_VERBS"
    description: "Remember level uses: list, define, identify, name, recognize, recall"
    bidirectional: false
    weight: 1.0

  - id: "rel-understand-verbs"
    source_term_id: "bloom-understand"
    target_term_id: "verbs-understand"
    relationship_type: "USES_VERBS"
    description: "Understand level uses: describe, explain, interpret, compare, summarize"
    bidirectional: false
    weight: 1.0

  - id: "rel-apply-verbs"
    source_term_id: "bloom-apply"
    target_term_id: "verbs-apply"
    relationship_type: "USES_VERBS"
    description: "Apply level uses: configure, implement, apply, use, demonstrate"
    bidirectional: false
    weight: 1.0

  - id: "rel-analyze-verbs"
    source_term_id: "bloom-analyze"
    target_term_id: "verbs-analyze"
    relationship_type: "USES_VERBS"
    description: "Analyze level uses: troubleshoot, analyze, diagnose, differentiate, examine"
    bidirectional: false
    weight: 1.0

  - id: "rel-evaluate-verbs"
    source_term_id: "bloom-evaluate"
    target_term_id: "verbs-evaluate"
    relationship_type: "USES_VERBS"
    description: "Evaluate level uses: assess, evaluate, judge, justify, recommend"
    bidirectional: false
    weight: 1.0

  - id: "rel-create-verbs"
    source_term_id: "bloom-create"
    target_term_id: "verbs-create"
    relationship_type: "USES_VERBS"
    description: "Create level uses: design, architect, develop, build, plan"
    bidirectional: false
    weight: 1.0
```

### Level to Bloom Associations

```yaml
  # === LEVEL TO BLOOM ASSOCIATIONS ===

  - id: "rel-assoc-bloom-primary"
    source_term_id: "level-associate"
    target_term_id: "bloom-apply"
    relationship_type: "PRIMARY_BLOOM"
    description: "Associate level primarily targets Apply (with Remember/Understand)"
    bidirectional: false
    weight: 1.0

  - id: "rel-prof-bloom-primary"
    source_term_id: "level-professional"
    target_term_id: "bloom-analyze"
    relationship_type: "PRIMARY_BLOOM"
    description: "Professional level primarily targets Analyze (with Apply)"
    bidirectional: false
    weight: 1.0

  - id: "rel-expert-bloom-primary"
    source_term_id: "level-expert"
    target_term_id: "bloom-evaluate"
    relationship_type: "PRIMARY_BLOOM"
    description: "Expert level primarily targets Evaluate and Create"
    bidirectional: false
    weight: 1.0
```

## Loading Script

```python
"""Script to seed the certification-program namespace in knowledge-manager."""

import asyncio
from datetime import UTC, datetime

from application.commands.create_namespace_command import CreateNamespaceCommand
from application.commands.add_term_command import AddTermCommand
from application.commands.add_rule_command import AddRuleCommand
from application.commands.add_relationship_command import AddRelationshipCommand

async def seed_certification_program_namespace(mediator):
    """Seed the certification-program namespace with reference data."""

    # 1. Create namespace
    create_ns = CreateNamespaceCommand(
        namespace_id="certification-program",
        name="Certification Program Structure",
        description="Reference data for certification program hierarchy...",
        icon="bi-award",
        access_level="public",
        user_id="system",
    )
    await mediator.execute_async(create_ns)

    # 2. Add terms (levels, types, tracks, bloom)
    terms = [
        # Certification Levels
        {"id": "level-associate", "term": "Associate", "definition": "...", ...},
        {"id": "level-professional", "term": "Professional", "definition": "...", ...},
        {"id": "level-expert", "term": "Expert", "definition": "...", ...},
        # ... (all terms from above)
    ]

    for term_data in terms:
        add_term = AddTermCommand(
            namespace_id="certification-program",
            term_id=term_data["id"],
            term=term_data["term"],
            definition=term_data["definition"],
            aliases=term_data.get("aliases", []),
            examples=term_data.get("examples", []),
            context_hint=term_data.get("context_hint", ""),
            user_id="system",
        )
        await mediator.execute_async(add_term)

    # 3. Add rules
    rules = [
        {"id": "bloom-dist-associate", "name": "Associate Level Bloom's Distribution", ...},
        # ... (all rules from above)
    ]

    for rule_data in rules:
        add_rule = AddRuleCommand(
            namespace_id="certification-program",
            rule_id=rule_data["id"],
            name=rule_data["name"],
            rule_type=rule_data["rule_type"],
            condition=rule_data["condition"],
            rule_text=rule_data["rule_text"],
            applies_to_term_ids=rule_data.get("applies_to_term_ids", []),
            priority=rule_data.get("priority", 1),
            user_id="system",
        )
        await mediator.execute_async(add_rule)

    # 4. Add relationships
    relationships = [
        {"id": "rel-assoc-to-prof", "source": "level-associate", "target": "level-professional", ...},
        # ... (all relationships from above)
    ]

    for rel_data in relationships:
        add_rel = AddRelationshipCommand(
            namespace_id="certification-program",
            relationship_id=rel_data["id"],
            source_term_id=rel_data["source"],
            target_term_id=rel_data["target"],
            relationship_type=rel_data["relationship_type"],
            description=rel_data.get("description", ""),
            bidirectional=rel_data.get("bidirectional", False),
            weight=rel_data.get("weight", 1.0),
            user_id="system",
        )
        await mediator.execute_async(add_rel)

    print("✅ certification-program namespace seeded successfully")
```

## Validation Query Example

When blueprint-manager requests validation:

```python
# Request from blueprint-manager
POST /api/v1/namespaces/certification-program/validate
{
    "entity_type": "exam_blueprint",
    "entity_snapshot": {
        "id": "bp-12345",
        "exam_code": "350-401",
        "level": "professional",
        "type": "core",
        "track": "enterprise",
        "topics": [...],
        "bloom_distribution": {
            "1": 5,   # Remember: 5%
            "2": 10,  # Understand: 10%
            "3": 35,  # Apply: 35%
            "4": 40,  # Analyze: 40%
            "5": 8,   # Evaluate: 8%
            "6": 2    # Create: 2%
        }
    }
}

# Response from knowledge-manager
{
    "validated_at": "2025-01-15T10:30:00Z",
    "results": [
        {
            "rule_id": "bloom-dist-professional",
            "rule_name": "Professional Level Bloom's Distribution",
            "passed": true,
            "severity": "constraint",
            "message": "Bloom distribution meets Professional level requirements"
        },
        {
            "rule_id": "verb-prohibited-professional",
            "rule_name": "Discouraged Verbs for Professional Level",
            "passed": true,
            "severity": "warning",
            "message": "No discouraged verbs found in KSA statements"
        },
        {
            "rule_id": "topic-weight-distribution",
            "rule_name": "Topic Weight Distribution",
            "passed": true,
            "severity": "constraint",
            "message": "Topic weights sum to 100% with valid distribution"
        }
    ],
    "summary": {
        "passed": 3,
        "warnings": 0,
        "errors": 0
    }
}
```

---

_Last updated: January 2025_
