# Certification Program - Knowledge Manager Seed Data

> **Purpose:** Seed data for the `certification-program` namespace
> **Usage:** Load via knowledge-manager seed command or API on first deployment
> **Format:** YAML for human readability, converted to JSON for API calls

## Namespace Configuration

```yaml
# certification-program-namespace.yaml

namespace:
  id: 'certification-program'
  name: 'Certification Program Structure'
  description: |
    Defines the meta-structure of the certification program including:
    - Certification levels (Associate, Professional, Expert)
    - Certification types (Core, Concentration, Specialist)
    - Certification tracks (Enterprise, Security, DevNet, etc.)
    - Level invariants (Bloom's distributions, verb rules)

    This namespace is the source of truth for program-wide rules that
    blueprint-manager validates against during authoring.
  icon: 'bi-award'
  access_level: 'public'
  owner_tenant_id: null  # Global namespace
```

---

## Terms

### Certification Levels

```yaml
terms:

  # =========================================================================
  # CERTIFICATION LEVELS
  # =========================================================================

  - id: 'level-associate'
    term: 'Associate Level'
    definition: |
      Entry-level certification validating foundational knowledge and skills.

      **Target Audience:**
      - 0-2 years experience
      - Junior Network Administrator, Help Desk Technician

      **Cognitive Profile (Bloom's Taxonomy):**
      - Remember: 20-30%
      - Understand: 30-40%
      - Apply: 25-35%
      - Analyze: 5-15%
      - Evaluate: 0-5%
      - Create: 0%

      **Knowledge Profile:**
      - Breadth: Broad (cover many topics)
      - Depth: Shallow (surface-level understanding)
      - Integration: Low (topics largely independent)

      **Exam Characteristics:**
      - Duration: 90-120 minutes
      - Items: 90-120
      - Types: Multiple-choice, drag-and-drop, basic simulation
      - Pass rate target: 65-75%
    aliases:
      - 'CCA'
      - 'CCNA-level'
      - 'Entry Level'
      - 'Foundational'
    examples:
      - 'CCNA (200-301)'
      - 'DevNet Associate'
      - 'CyberOps Associate'
    context_hint: 'Use when discussing entry-level certifications or validating Associate blueprints'

  - id: 'level-professional'
    term: 'Professional Level'
    definition: |
      Mid-level certification validating comprehensive knowledge and practical skills.

      **Target Audience:**
      - 3-5 years experience
      - Network Engineer, Systems Engineer

      **Cognitive Profile (Bloom's Taxonomy):**
      - Remember: 10-15%
      - Understand: 15-25%
      - Apply: 30-40%
      - Analyze: 20-30%
      - Evaluate: 5-15%
      - Create: 0-5%

      **Knowledge Profile:**
      - Breadth: Focused (deeper in track area)
      - Depth: Moderate to deep (practical depth)
      - Integration: Moderate (cross-topic understanding)

      **Exam Characteristics:**
      - Duration: 120 minutes (core) + concentration
      - Items: 100-120 (core)
      - Types: Multiple-choice, simulation, testlet (scenario-based)
      - Pass rate target: 55-65%

      **Structure:**
      - Requires 1 Core exam + 1 Concentration exam
      - Core: Broad, foundational within track
      - Concentration: Deep, specialized focus
    aliases:
      - 'CCP'
      - 'CCNP-level'
      - 'Mid Level'
      - 'Practitioner'
    examples:
      - 'CCNP Enterprise (Core + Concentration)'
      - 'CCNP Security'
      - 'DevNet Professional'
    context_hint: 'Use when discussing mid-level certifications requiring practical experience'

  - id: 'level-expert'
    term: 'Expert Level'
    definition: |
      Elite certification validating expert-level mastery.

      **Target Audience:**
      - 5-8+ years experience
      - Senior Network Architect, Principal Engineer, Technical Leader

      **Cognitive Profile (Bloom's Taxonomy):**
      - Remember: 5-10%
      - Understand: 10-15%
      - Apply: 15-25%
      - Analyze: 25-35%
      - Evaluate: 15-25%
      - Create: 10-20%

      **Knowledge Profile:**
      - Breadth: Comprehensive (full domain coverage)
      - Depth: Expert (deep understanding)
      - Integration: High (cross-domain synthesis)

      **Exam Characteristics:**
      - Duration: 8 hours (practical lab)
      - Format: Hands-on lab exam
      - Types: Design module (2-3h) + Deploy module (5-6h)
      - Pass rate target: 20-35% (elite credential)

      **Prerequisites:**
      - Professional certification in same track
      - Extensive hands-on experience
    aliases:
      - 'CCIE'
      - 'CCIE-level'
      - 'Expert Level'
      - 'Elite'
    examples:
      - 'CCIE Enterprise Infrastructure'
      - 'CCIE Security'
      - 'CCIE Service Provider'
    context_hint: 'Use when discussing elite-level certifications with practical lab exams'
```

### Certification Types

```yaml
  # =========================================================================
  # CERTIFICATION TYPES
  # =========================================================================

  - id: 'type-core'
    term: 'Core Exam'
    definition: |
      Required foundational exam within a certification track.

      **Characteristics:**
      - Required: Yes (must pass to earn certification)
      - Count per certification: 1
      - Breadth: Comprehensive within domain
      - Depth: Foundational to moderate

      **Blueprint Constraints:**
      - Minimum topics: 5
      - Maximum topics: 10
      - Coverage: All major domain areas

      Core exams establish the baseline knowledge that all professionals
      in a track must demonstrate, regardless of their specialization.
    aliases:
      - 'Core'
      - 'Foundation Exam'
      - 'Required Exam'
    examples:
      - '350-401 ENCOR (CCNP Enterprise Core)'
      - '350-701 SCOR (CCNP Security Core)'
      - '350-901 DevCOR (DevNet Professional Core)'
    context_hint: 'Use when discussing required foundational exams in a certification track'

  - id: 'type-concentration'
    term: 'Concentration Exam'
    definition: |
      Specialized depth exam that provides expertise in a specific area.

      **Characteristics:**
      - Required: One of set (choose from available options)
      - Count per certification: 1 from available options
      - Breadth: Narrow, focused area
      - Depth: Deep expertise

      **Blueprint Constraints:**
      - Minimum topics: 3
      - Maximum topics: 6
      - Specialization: Expert-level in focus area

      Concentration exams allow candidates to demonstrate specialized
      expertise while sharing a common core with others in the track.
    aliases:
      - 'Concentration'
      - 'Specialization Exam'
      - 'Elective'
    examples:
      - '300-410 ENARSI (Enterprise Advanced Routing)'
      - '300-420 ENSLD (Enterprise Design)'
      - '300-710 SNCF (Security Firepower)'
    context_hint: 'Use when discussing specialized depth exams in a certification'

  - id: 'type-specialist'
    term: 'Specialist Exam'
    definition: |
      Standalone certification focused on specific technology or product.

      **Characteristics:**
      - Required: No (standalone credential)
      - Standalone: Yes (does not require core exam)
      - Breadth: Very narrow
      - Depth: Deep in specific technology

      **Blueprint Constraints:**
      - Minimum topics: 2
      - Maximum topics: 4
      - Technology focus: Single technology or product

      Specialist certifications validate focused expertise without
      requiring the broader certification structure.
    aliases:
      - 'Specialist'
      - 'Technology Specialist'
      - 'Standalone Certification'
    examples:
      - '300-835 CLAUTO (Collaboration Automation)'
      - '300-920 DEVIOT (IoT Development)'
      - '700-xxx (Various Specialist exams)'
    context_hint: 'Use when discussing standalone technology-specific certifications'
```

### Certification Tracks

```yaml
  # =========================================================================
  # CERTIFICATION TRACKS
  # =========================================================================

  - id: 'track-enterprise'
    term: 'Enterprise Track'
    definition: |
      Certifications focused on enterprise networking infrastructure.

      **Focus Areas:**
      - Enterprise network architecture
      - Routing and switching
      - Wireless infrastructure
      - SD-WAN and virtualization
      - Network assurance and automation

      **Certifications:**
      - CCNA Enterprise (Associate)
      - CCNP Enterprise (Professional)
      - CCIE Enterprise Infrastructure (Expert)
      - CCIE Enterprise Wireless (Expert)

      **Overlaps with:**
      - Service Provider (routing protocols)
      - Security (network security)
      - DevNet (automation)
    aliases:
      - 'Enterprise Infrastructure'
      - 'CCNP Enterprise'
      - 'Enterprise Networking'
    context_hint: 'Use when discussing enterprise network certifications'

  - id: 'track-security'
    term: 'Security Track'
    definition: |
      Certifications focused on network and cybersecurity.

      **Focus Areas:**
      - Network security architecture
      - Firewall and VPN technologies
      - Intrusion prevention
      - Identity management
      - Security operations

      **Certifications:**
      - CyberOps Associate (Associate)
      - CCNP Security (Professional)
      - CCIE Security (Expert)
    aliases:
      - 'Security'
      - 'CCNP Security'
      - 'Cybersecurity'
    context_hint: 'Use when discussing security-focused certifications'

  - id: 'track-devnet'
    term: 'DevNet Track'
    definition: |
      Certifications focused on network programmability and automation.

      **Focus Areas:**
      - Network automation with Python
      - REST APIs and SDKs
      - Infrastructure as Code
      - CI/CD for network operations
      - Application development on network platforms

      **Certifications:**
      - DevNet Associate (Associate)
      - DevNet Professional (Professional)
      - DevNet Expert (Expert - proposed)
    aliases:
      - 'DevNet'
      - 'Network Automation'
      - 'Programmability'
    context_hint: 'Use when discussing automation and programmability certifications'

  - id: 'track-service-provider'
    term: 'Service Provider Track'
    definition: |
      Certifications focused on service provider networks.

      **Focus Areas:**
      - MPLS and Segment Routing
      - BGP at scale
      - Service provider architecture
      - Network virtualization
      - Large-scale routing

      **Certifications:**
      - CCNP Service Provider (Professional)
      - CCIE Service Provider (Expert)

      **Overlaps with:**
      - Enterprise (routing protocols)
    aliases:
      - 'Service Provider'
      - 'CCNP Service Provider'
      - 'SP'
    context_hint: 'Use when discussing service provider network certifications'

  - id: 'track-collaboration'
    term: 'Collaboration Track'
    definition: |
      Certifications focused on unified communications and collaboration.

      **Focus Areas:**
      - Voice and video infrastructure
      - Unified communications
      - Contact center technologies
      - Collaboration applications

      **Certifications:**
      - CCNP Collaboration (Professional)
      - CCIE Collaboration (Expert)
    aliases:
      - 'Collaboration'
      - 'CCNP Collaboration'
      - 'Unified Communications'
      - 'UC'
    context_hint: 'Use when discussing collaboration and unified communications certifications'

  - id: 'track-data-center'
    term: 'Data Center Track'
    definition: |
      Certifications focused on data center networking and infrastructure.

      **Focus Areas:**
      - Data center architecture (Spine-Leaf, ACI)
      - Storage networking
      - Compute infrastructure
      - Data center automation
      - Cloud integration

      **Certifications:**
      - CCNP Data Center (Professional)
      - CCIE Data Center (Expert)
    aliases:
      - 'Data Center'
      - 'CCNP Data Center'
      - 'DC'
    context_hint: 'Use when discussing data center network certifications'
```

### Bloom's Taxonomy

```yaml
  # =========================================================================
  # BLOOM'S TAXONOMY (Cognitive Levels)
  # =========================================================================

  - id: 'bloom-remember'
    term: 'Remember (Bloom Level 1)'
    definition: |
      Recall facts and basic concepts.

      **Action Verbs:** Define, list, identify, name, recall, recognize, state

      **Assessment Types:**
      - Terminology recall
      - Fact recognition
      - Basic identification

      **Level Distribution:**
      - Associate: 20-30%
      - Professional: 10-15%
      - Expert: 5-10%
    aliases:
      - 'Remember'
      - 'Recall'
      - 'Knowledge'
    context_hint: 'Lowest cognitive level - factual recall'

  - id: 'bloom-understand'
    term: 'Understand (Bloom Level 2)'
    definition: |
      Explain ideas or concepts.

      **Action Verbs:** Describe, explain, summarize, interpret, classify, compare

      **Assessment Types:**
      - Concept explanation
      - Process description
      - Comparison questions

      **Level Distribution:**
      - Associate: 30-40%
      - Professional: 15-25%
      - Expert: 10-15%
    aliases:
      - 'Understand'
      - 'Comprehension'
    context_hint: 'Second cognitive level - conceptual understanding'

  - id: 'bloom-apply'
    term: 'Apply (Bloom Level 3)'
    definition: |
      Use information in new situations.

      **Action Verbs:** Configure, implement, execute, use, demonstrate, solve

      **Assessment Types:**
      - Configuration tasks
      - Implementation scenarios
      - Procedure execution

      **Level Distribution:**
      - Associate: 25-35%
      - Professional: 30-40%
      - Expert: 15-25%
    aliases:
      - 'Apply'
      - 'Application'
    context_hint: 'Third cognitive level - practical application'

  - id: 'bloom-analyze'
    term: 'Analyze (Bloom Level 4)'
    definition: |
      Draw connections among ideas.

      **Action Verbs:** Troubleshoot, compare, differentiate, examine, investigate, diagnose

      **Assessment Types:**
      - Troubleshooting scenarios
      - Root cause analysis
      - Comparison analysis

      **Level Distribution:**
      - Associate: 5-15%
      - Professional: 20-30%
      - Expert: 25-35%
    aliases:
      - 'Analyze'
      - 'Analysis'
    context_hint: 'Fourth cognitive level - analytical thinking'

  - id: 'bloom-evaluate'
    term: 'Evaluate (Bloom Level 5)'
    definition: |
      Justify a decision or course of action.

      **Action Verbs:** Assess, recommend, prioritize, critique, judge, validate

      **Assessment Types:**
      - Decision justification
      - Solution recommendation
      - Design validation

      **Level Distribution:**
      - Associate: 0-5%
      - Professional: 5-15%
      - Expert: 15-25%
    aliases:
      - 'Evaluate'
      - 'Evaluation'
      - 'Judgment'
    context_hint: 'Fifth cognitive level - evaluative judgment'

  - id: 'bloom-create'
    term: 'Create (Bloom Level 6)'
    definition: |
      Produce new or original work.

      **Action Verbs:** Design, architect, develop, construct, plan, propose

      **Assessment Types:**
      - Network design
      - Architecture creation
      - Solution development

      **Level Distribution:**
      - Associate: 0%
      - Professional: 0-5%
      - Expert: 10-20%
    aliases:
      - 'Create'
      - 'Synthesis'
      - 'Design'
    context_hint: 'Highest cognitive level - creative synthesis'
```

---

## Rules (Level Invariants)

```yaml
rules:

  # =========================================================================
  # BLOOM'S DISTRIBUTION RULES
  # =========================================================================

  - id: 'bloom-001'
    name: 'Associate Lower Cognitive Requirement'
    condition: 'blueprint.level == "associate"'
    rule_text: |
      Associate blueprints must have ≥50% items at Remember/Understand/Apply
      (Bloom levels 1-3). This ensures the exam is accessible to entry-level
      candidates who are still building foundational knowledge.
    rule_type: 'validation'
    priority: 1
    applies_to_term_ids:
      - 'level-associate'

  - id: 'bloom-002'
    name: 'Associate Higher Cognitive Limit'
    condition: 'blueprint.level == "associate"'
    rule_text: |
      Associate blueprints should not have >5% items at Evaluate/Create
      (Bloom levels 5-6). These higher cognitive levels require experience
      that entry-level candidates typically lack.
    rule_type: 'validation'
    priority: 2
    applies_to_term_ids:
      - 'level-associate'

  - id: 'bloom-003'
    name: 'Expert Higher Cognitive Requirement'
    condition: 'blueprint.level == "expert"'
    rule_text: |
      Expert blueprints must have ≥40% items at Analyze/Evaluate/Create
      (Bloom levels 4-6). Expert candidates must demonstrate advanced
      analytical and design capabilities.
    rule_type: 'validation'
    priority: 1
    applies_to_term_ids:
      - 'level-expert'

  - id: 'bloom-004'
    name: 'Professional Balanced Distribution'
    condition: 'blueprint.level == "professional"'
    rule_text: |
      Professional blueprints should have 30-40% items at Apply (Bloom level 3)
      and 20-30% at Analyze (Bloom level 4). This balances practical skills
      with analytical capability.
    rule_type: 'validation'
    priority: 2
    applies_to_term_ids:
      - 'level-professional'

  # =========================================================================
  # VERB USAGE RULES
  # =========================================================================

  - id: 'verb-001'
    name: 'Associate Prohibited Verbs'
    condition: 'blueprint.level == "associate"'
    rule_text: |
      Associate items should not use the following verbs in KSA statements:
      - "design" (requires advanced experience)
      - "architect" (requires advanced experience)
      - "optimize" (requires deep experience)
      - "evaluate" (limited at this level)

      These verbs imply cognitive levels beyond entry-level expectations.
    rule_type: 'validation'
    priority: 1
    applies_to_term_ids:
      - 'level-associate'

  - id: 'verb-002'
    name: 'Associate Encouraged Verbs'
    condition: 'blueprint.level == "associate"'
    rule_text: |
      Associate items should prefer the following verbs in KSA statements:
      - "identify" - recognize components, symptoms, or states
      - "describe" - explain concepts at a foundational level
      - "configure" - perform basic configuration tasks
      - "verify" - confirm expected state or behavior
      - "troubleshoot" - guided troubleshooting with defined paths
    rule_type: 'suggestion'
    priority: 3
    applies_to_term_ids:
      - 'level-associate'

  - id: 'verb-003'
    name: 'Expert Discouraged Verbs'
    condition: 'blueprint.level == "expert"'
    rule_text: |
      Expert items should minimize the following verbs in KSA statements:
      - "list" - too basic for expert level
      - "define" - too basic (unless complex concept)
      - "describe" - only for complex concepts

      These verbs imply cognitive levels below expert expectations.
      Items using these verbs should represent ≤10% of the blueprint.
    rule_type: 'validation'
    priority: 2
    applies_to_term_ids:
      - 'level-expert'

  - id: 'verb-004'
    name: 'Expert Encouraged Verbs'
    condition: 'blueprint.level == "expert"'
    rule_text: |
      Expert items should prefer the following verbs in KSA statements:
      - "design" - create network architectures
      - "architect" - plan complex solutions
      - "optimize" - improve performance and efficiency
      - "evaluate" - assess and recommend solutions
      - "diagnose" - identify root causes in complex scenarios
      - "integrate" - combine technologies cohesively
      - "transform" - convert or migrate architectures
    rule_type: 'suggestion'
    priority: 3
    applies_to_term_ids:
      - 'level-expert'

  # =========================================================================
  # KNOWLEDGE PROFILE RULES
  # =========================================================================

  - id: 'knowledge-001'
    name: 'Associate Breadth Requirement'
    condition: 'blueprint.level == "associate"'
    rule_text: |
      Associate blueprints must cover ≥80% of track knowledge areas.
      Entry-level candidates need broad foundational exposure across
      the entire domain before specializing.
    rule_type: 'validation'
    priority: 1
    applies_to_term_ids:
      - 'level-associate'

  - id: 'knowledge-002'
    name: 'Professional Integration Requirement'
    condition: 'blueprint.level == "professional"'
    rule_text: |
      Professional blueprints should have ≥30% items requiring multi-concept
      integration. Candidates at this level must demonstrate ability to
      connect concepts across topics.
    rule_type: 'validation'
    priority: 2
    applies_to_term_ids:
      - 'level-professional'

  - id: 'knowledge-003'
    name: 'Expert Cross-Domain Synthesis'
    condition: 'blueprint.level == "expert"'
    rule_text: |
      Expert blueprints must include scenarios requiring cross-domain
      synthesis. Expert candidates must demonstrate ability to integrate
      knowledge across the entire track domain.
    rule_type: 'validation'
    priority: 1
    applies_to_term_ids:
      - 'level-expert'

  # =========================================================================
  # EXPERIENCE ASSUMPTION RULES
  # =========================================================================

  - id: 'experience-001'
    name: 'Associate No Production Assumption'
    condition: 'blueprint.level == "associate"'
    rule_text: |
      Associate items must not assume production network experience.
      All scenarios should be achievable with lab-only experience
      or equivalent training exercises.
    rule_type: 'validation'
    priority: 1
    applies_to_term_ids:
      - 'level-associate'

  - id: 'experience-002'
    name: 'Professional Assumed Knowledge'
    condition: 'blueprint.level == "professional"'
    rule_text: |
      Professional blueprints may assume Associate-level knowledge
      as a prerequisite. Items do not need to re-cover foundational
      concepts that Associate certification validates.
    rule_type: 'information'
    priority: 3
    applies_to_term_ids:
      - 'level-professional'

  - id: 'experience-003'
    name: 'Expert Real-World Scenarios'
    condition: 'blueprint.level == "expert"'
    rule_text: |
      Expert items should be based on realistic enterprise scenarios
      that require judgment calls similar to production environments.
      Candidates should demonstrate experience-based decision making.
    rule_type: 'suggestion'
    priority: 2
    applies_to_term_ids:
      - 'level-expert'

  # =========================================================================
  # BLUEPRINT STRUCTURE RULES
  # =========================================================================

  - id: 'structure-001'
    name: 'Minimum Topics'
    condition: 'blueprint.type in ["core", "concentration"]'
    rule_text: |
      All blueprints must have at least 2 topics.
      A single-topic blueprint lacks the breadth required for certification.
    rule_type: 'validation'
    priority: 1

  - id: 'structure-002'
    name: 'Topic Weights Must Sum to 100%'
    condition: 'always'
    rule_text: |
      Topic weights must sum to exactly 100% (±0.1% for rounding).
      This ensures proper representation in Form assembly.
    rule_type: 'validation'
    priority: 1

  - id: 'structure-003'
    name: 'Skills Per Topic'
    condition: 'always'
    rule_text: |
      Each topic must have at least 1 skill defined.
      Empty topics indicate incomplete blueprint development.
    rule_type: 'validation'
    priority: 1

  - id: 'structure-004'
    name: 'KSA Per Skill'
    condition: 'always'
    rule_text: |
      Each skill must have at least 1 KSA statement defined.
      Skills without KSAs cannot be measured in the exam.
    rule_type: 'validation'
    priority: 1

  - id: 'structure-005'
    name: 'Core Exam Topic Minimum'
    condition: 'blueprint.type == "core"'
    rule_text: |
      Core exams must have at least 5 topics to ensure comprehensive
      coverage of the track's foundational knowledge areas.
    rule_type: 'validation'
    priority: 1
    applies_to_term_ids:
      - 'type-core'

  - id: 'structure-006'
    name: 'Concentration Topic Maximum'
    condition: 'blueprint.type == "concentration"'
    rule_text: |
      Concentration exams should have no more than 6 topics.
      Concentrations should be focused, not broad.
    rule_type: 'validation'
    priority: 2
    applies_to_term_ids:
      - 'type-concentration'
```

---

## Relationships

```yaml
relationships:

  # =========================================================================
  # LEVEL PROGRESSIONS
  # =========================================================================

  - source_term_id: 'level-associate'
    target_term_id: 'level-professional'
    relationship_type: 'PREREQUISITE_FOR'
    description: 'Associate certification is a prerequisite for Professional'
    bidirectional: false
    weight: 1.0

  - source_term_id: 'level-professional'
    target_term_id: 'level-expert'
    relationship_type: 'PREREQUISITE_FOR'
    description: 'Professional certification is a prerequisite for Expert'
    bidirectional: false
    weight: 1.0

  # =========================================================================
  # TYPE RELATIONSHIPS
  # =========================================================================

  - source_term_id: 'type-core'
    target_term_id: 'type-concentration'
    relationship_type: 'REQUIRES'
    description: 'Core exam is required alongside Concentration for certification'
    bidirectional: false
    weight: 1.0

  # =========================================================================
  # TRACK OVERLAPS
  # =========================================================================

  - source_term_id: 'track-enterprise'
    target_term_id: 'track-service-provider'
    relationship_type: 'OVERLAPS_WITH'
    description: 'Enterprise and Service Provider share routing protocol topics'
    bidirectional: true
    weight: 0.3

  - source_term_id: 'track-enterprise'
    target_term_id: 'track-security'
    relationship_type: 'OVERLAPS_WITH'
    description: 'Enterprise and Security share network security topics'
    bidirectional: true
    weight: 0.2

  - source_term_id: 'track-enterprise'
    target_term_id: 'track-devnet'
    relationship_type: 'OVERLAPS_WITH'
    description: 'Enterprise and DevNet share automation topics'
    bidirectional: true
    weight: 0.15

  - source_term_id: 'track-enterprise'
    target_term_id: 'track-data-center'
    relationship_type: 'OVERLAPS_WITH'
    description: 'Enterprise and Data Center share switching/VXLAN topics'
    bidirectional: true
    weight: 0.2

  # =========================================================================
  # BLOOM'S LEVEL PROGRESSIONS
  # =========================================================================

  - source_term_id: 'bloom-remember'
    target_term_id: 'bloom-understand'
    relationship_type: 'PRECEDES'
    description: 'Remember is the foundation for Understand'
    bidirectional: false
    weight: 1.0

  - source_term_id: 'bloom-understand'
    target_term_id: 'bloom-apply'
    relationship_type: 'PRECEDES'
    description: 'Understand is the foundation for Apply'
    bidirectional: false
    weight: 1.0

  - source_term_id: 'bloom-apply'
    target_term_id: 'bloom-analyze'
    relationship_type: 'PRECEDES'
    description: 'Apply is the foundation for Analyze'
    bidirectional: false
    weight: 1.0

  - source_term_id: 'bloom-analyze'
    target_term_id: 'bloom-evaluate'
    relationship_type: 'PRECEDES'
    description: 'Analyze is the foundation for Evaluate'
    bidirectional: false
    weight: 1.0

  - source_term_id: 'bloom-evaluate'
    target_term_id: 'bloom-create'
    relationship_type: 'PRECEDES'
    description: 'Evaluate is the foundation for Create'
    bidirectional: false
    weight: 1.0

  # =========================================================================
  # LEVEL TO BLOOM ASSOCIATIONS
  # =========================================================================

  - source_term_id: 'level-associate'
    target_term_id: 'bloom-remember'
    relationship_type: 'EMPHASIZES'
    description: 'Associate level emphasizes Remember cognitive level'
    bidirectional: false
    weight: 0.25

  - source_term_id: 'level-associate'
    target_term_id: 'bloom-understand'
    relationship_type: 'EMPHASIZES'
    description: 'Associate level emphasizes Understand cognitive level'
    bidirectional: false
    weight: 0.35

  - source_term_id: 'level-associate'
    target_term_id: 'bloom-apply'
    relationship_type: 'EMPHASIZES'
    description: 'Associate level emphasizes Apply cognitive level'
    bidirectional: false
    weight: 0.30

  - source_term_id: 'level-professional'
    target_term_id: 'bloom-apply'
    relationship_type: 'EMPHASIZES'
    description: 'Professional level emphasizes Apply cognitive level'
    bidirectional: false
    weight: 0.35

  - source_term_id: 'level-professional'
    target_term_id: 'bloom-analyze'
    relationship_type: 'EMPHASIZES'
    description: 'Professional level emphasizes Analyze cognitive level'
    bidirectional: false
    weight: 0.25

  - source_term_id: 'level-expert'
    target_term_id: 'bloom-analyze'
    relationship_type: 'EMPHASIZES'
    description: 'Expert level emphasizes Analyze cognitive level'
    bidirectional: false
    weight: 0.30

  - source_term_id: 'level-expert'
    target_term_id: 'bloom-evaluate'
    relationship_type: 'EMPHASIZES'
    description: 'Expert level emphasizes Evaluate cognitive level'
    bidirectional: false
    weight: 0.20

  - source_term_id: 'level-expert'
    target_term_id: 'bloom-create'
    relationship_type: 'EMPHASIZES'
    description: 'Expert level emphasizes Create cognitive level'
    bidirectional: false
    weight: 0.15
```

---

## Loading Instructions

### Via API

```python
# Example Python script to load seed data

import httpx
import yaml

async def load_certification_program_namespace():
    """Load the certification-program namespace seed data."""

    with open("certification-program-namespace.yaml") as f:
        seed_data = yaml.safe_load(f)

    async with httpx.AsyncClient(base_url="http://localhost:8002") as client:
        # Create namespace
        response = await client.post(
            "/api/namespaces",
            json=seed_data["namespace"]
        )
        namespace_id = response.json()["id"]

        # Add terms
        for term in seed_data["terms"]:
            await client.post(
                f"/api/namespaces/{namespace_id}/terms",
                json=term
            )

        # Add rules
        for rule in seed_data["rules"]:
            await client.post(
                f"/api/namespaces/{namespace_id}/rules",
                json=rule
            )

        # Add relationships
        for rel in seed_data["relationships"]:
            await client.post(
                f"/api/namespaces/{namespace_id}/relationships",
                json=rel
            )

        print(f"✅ Loaded certification-program namespace with:")
        print(f"   - {len(seed_data['terms'])} terms")
        print(f"   - {len(seed_data['rules'])} rules")
        print(f"   - {len(seed_data['relationships'])} relationships")
```

### Via Make Command

```makefile
# In knowledge-manager Makefile

seed-certification-program:
 @echo "🌱 Seeding certification-program namespace..."
 python scripts/load_seed_data.py --namespace certification-program
```
