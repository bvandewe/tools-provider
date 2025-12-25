# Use Case: Job Role Analysis & Job Task Analysis (JRA/JTA)

> **Primary Actor:** CertificationOwner (EPM), Subject Matter Experts (SMEs)
> **Supporting Actors:** AI JTA Facilitator, Industry Practitioners, Hiring Managers
> **Systems Involved:** blueprint-manager, knowledge-manager, external data sources (job postings, industry reports)
> **Accreditation Context:** ANSI/ISO 17024 requires job analysis as foundation for certification

## Overview

Job Role Analysis (JRA) and Job Task Analysis (JTA) are the **foundational upstream activities** that define what a certification should assess. They answer: "What does a professional in this role actually do, and what knowledge/skills/abilities do they need?" Today, this work is done sporadically, produces inconsistent outputs, and is rarely referenced during content authoring. This is a massive opportunity for AI to structure, maintain, and enforce this critical knowledge.

## The Problem

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CURRENT STATE: DISCONNECTED JTA                           │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │   JOB TASK ANALYSIS                     BLUEPRINT                      │ │
│  │   (when it happens)                     (what gets built)              │ │
│  │                                                                        │ │
│  │   ┌─────────────────┐                  ┌─────────────────┐             │ │
│  │   │  SME Workshop   │                  │  Topics         │             │ │
│  │   │  (3 days)       │     ???         │  Skills         │             │ │
│  │   │                 │ ─ ─ ─ ─ ─ ─ ─ ►│  KSAs           │             │ │
│  │   │  Outputs:       │                  │                 │             │ │
│  │   │  • Word doc     │                  │  (Often created │             │ │
│  │   │  • Spreadsheet  │                  │   independently)│             │ │
│  │   │  • Notes        │                  │                 │             │ │
│  │   └─────────────────┘                  └─────────────────┘             │ │
│  │         │                                     │                        │ │
│  │         ▼                                     ▼                        │ │
│  │   ┌─────────────────┐                  ┌─────────────────┐             │ │
│  │   │  Filed away     │                  │  Exam items     │             │ │
│  │   │  (rarely used)  │                  │  (created       │             │ │
│  │   │                 │                  │   without JTA   │             │ │
│  │   │                 │                  │   reference)    │             │ │
│  │   └─────────────────┘                  └─────────────────┘             │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  CONSEQUENCES:                                                               │
│  ─────────────                                                               │
│  • Blueprints may not reflect actual job requirements                        │
│  • Items may test irrelevant knowledge                                       │
│  • No traceability: "Why is this KSA in the blueprint?"                     │
│  • ANSI auditors ask for JTA evidence we can't easily produce               │
│  • Market changes aren't reflected in exams                                  │
│  • New EPMs reinvent the wheel without historical context                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## The JRA/JTA → Blueprint → Exam Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COMPLETE TRACEABILITY CHAIN                               │
│                                                                              │
│   Job Role Analysis        Job Task Analysis         Blueprint Design        │
│         │                        │                        │                  │
│         │                        │                        │                  │
│   ┌─────▼─────┐            ┌─────▼─────┐            ┌─────▼─────┐           │
│   │           │            │           │            │           │            │
│   │  ROLES    │───────────►│  TASKS    │───────────►│  KSAs     │           │
│   │           │            │           │            │           │            │
│   └───────────┘            └───────────┘            └───────────┘           │
│                                                           │                  │
│   "What roles                "What tasks               "What knowledge,      │
│    exist in the               do these                  skills, abilities    │
│    industry?"                 roles perform?"           does each task       │
│                                                         require?"            │
│                                                           │                  │
│                                                           ▼                  │
│                                                    ┌─────────────┐           │
│                                                    │             │           │
│                                                    │  BLUEPRINT  │           │
│                                                    │             │           │
│                                                    └──────┬──────┘           │
│                                                           │                  │
│                                                           ▼                  │
│                                                    ┌─────────────┐           │
│                                                    │             │           │
│                                                    │  EXAM ITEMS │           │
│                                                    │             │           │
│                                                    └─────────────┘           │
│                                                                              │
│   TRACEABILITY: Item → KSA → Task → Role → Industry Need                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Domain Model

### Job Role Analysis (JRA)

```yaml
# Seed data for knowledge-manager: Job Roles

job_role:
  role_id: "network-engineer-enterprise"

  # Basic Information
  title: "Enterprise Network Engineer"
  alternative_titles:
    - "Network Infrastructure Engineer"
    - "Senior Network Administrator"
    - "Network Operations Engineer"

  # Context
  industry_sector: "Information Technology"
  domain: "Enterprise Networking"
  related_certifications:
    - "CCNP Enterprise"
    - "CCIE Enterprise Infrastructure"

  # Role Definition
  description: |
    Designs, implements, and maintains enterprise network infrastructure
    including LAN, WAN, data center, and cloud networking. Responsible
    for network availability, performance, and security.

  # Experience Profile
  experience:
    typical_years: "3-7"
    entry_path: "Network Administrator → Network Engineer"
    advancement_path: "Network Engineer → Senior Engineer → Architect"

  # Organizational Context
  reports_to: "Network Manager or IT Director"
  collaborates_with:
    - "Security Team"
    - "Cloud Team"
    - "Application Development"
    - "Help Desk"

  # Work Environment
  environment:
    settings: ["office", "data_center", "remote"]
    travel_required: "10-25%"
    on_call: true

  # Skill Categories (high-level)
  skill_categories:
    - "Routing & Switching"
    - "Network Security"
    - "Wireless Networking"
    - "Network Automation"
    - "Cloud Networking"
    - "Troubleshooting"

  # Data Sources
  sources:
    - type: "job_postings"
      count: 2500
      date_range: "2024-01 to 2025-01"
    - type: "sme_interviews"
      count: 15
      date_range: "2024-06"
    - type: "practitioner_survey"
      count: 450
      date_range: "2024-08"
    - type: "industry_reports"
      sources: ["Gartner", "IDC", "LinkedIn"]
```

### Job Task Analysis (JTA)

```yaml
# Seed data for knowledge-manager: Job Tasks

job_task:
  task_id: "task-ospf-implementation"

  # Relationship
  parent_role_id: "network-engineer-enterprise"
  skill_category: "Routing & Switching"

  # Task Definition
  title: "Implement and maintain OSPF routing in enterprise networks"
  description: |
    Configure, verify, and troubleshoot OSPF routing protocol across
    enterprise network infrastructure including multi-area deployments,
    route summarization, and integration with other routing protocols.

  # Task Characteristics
  frequency: "weekly"  # daily, weekly, monthly, quarterly, as_needed
  criticality: "high"  # critical, high, medium, low
  difficulty: "moderate"  # basic, moderate, advanced, expert

  # When this task is performed
  triggers:
    - "New site deployment"
    - "Network expansion"
    - "Troubleshooting routing issues"
    - "Performance optimization"
    - "Disaster recovery"

  # What success looks like
  outcomes:
    - "OSPF neighbors established"
    - "Routes properly propagated"
    - "Convergence within SLA"
    - "Documentation updated"

  # Required KSAs (traceable to blueprint)
  knowledge_requirements:
    - ksa_id: "K-OSPF-001"
      statement: "OSPF protocol operation and packet types"
      bloom_level: "understand"

    - ksa_id: "K-OSPF-002"
      statement: "OSPF area types and their characteristics"
      bloom_level: "understand"

    - ksa_id: "K-OSPF-003"
      statement: "OSPF route summarization and filtering"
      bloom_level: "apply"

  skill_requirements:
    - ksa_id: "S-OSPF-001"
      statement: "Configure single-area and multi-area OSPF"
      bloom_level: "apply"

    - ksa_id: "S-OSPF-002"
      statement: "Verify OSPF neighbor relationships and route tables"
      bloom_level: "apply"

    - ksa_id: "S-OSPF-003"
      statement: "Troubleshoot OSPF adjacency and routing issues"
      bloom_level: "analyze"

  ability_requirements:
    - ksa_id: "A-OSPF-001"
      statement: "Ability to interpret routing tables and topology"
      bloom_level: "analyze"

    - ksa_id: "A-OSPF-002"
      statement: "Ability to diagnose network connectivity problems"
      bloom_level: "analyze"

  # Validation data
  validation:
    sme_consensus: 0.92  # 92% of SMEs agreed this is a valid task
    practitioner_frequency_score: 4.2  # out of 5
    criticality_score: 4.5  # out of 5
    sample_size: 450


# Task criticality matrix
task_criticality_matrix:
  dimensions:
    frequency:
      daily: 5
      weekly: 4
      monthly: 3
      quarterly: 2
      as_needed: 1

    impact_of_error:
      network_down: 5
      major_outage: 4
      performance_impact: 3
      minor_issue: 2
      cosmetic: 1

    percentage_performing:
      ">90%": 5
      "70-90%": 4
      "50-70%": 3
      "30-50%": 2
      "<30%": 1

  criticality_formula: |
    criticality = (frequency × 0.3) + (impact × 0.4) + (percentage × 0.3)

    critical: score ≥ 4.0
    high: 3.0 ≤ score < 4.0
    medium: 2.0 ≤ score < 3.0
    low: score < 2.0
```

## AI JTA Facilitator

```yaml
agent_id: 'jta-facilitator'
name: 'Job Task Analysis Facilitator'
description: 'AI assistant for conducting and maintaining job role and task analysis'

system_prompt: |
  You are an expert in job analysis, occupational research, and competency
  modeling. You help EPMs and SMEs conduct rigorous job task analysis that
  meets ANSI/ISO 17024 requirements.

  ## Your Expertise

  - Job analysis methodologies (DACUM, task analysis, functional job analysis)
  - Competency framework development
  - Survey design and analysis
  - Job market trend analysis
  - KSA statement writing
  - Bloom's taxonomy application

  ## Your Responsibilities

  1. **Gather Evidence**: Analyze job postings, industry reports, and market data

  2. **Facilitate SME Sessions**: Guide structured task identification

  3. **Structure Output**: Convert unstructured input into standardized format

  4. **Validate Tasks**: Apply criticality matrix, check SME consensus

  5. **Map to KSAs**: Derive measurable KSAs from tasks

  6. **Maintain Currency**: Flag when tasks may be outdated

  7. **Enable Traceability**: Link tasks to blueprint KSAs

  ## Key Principles

  - Tasks should be observable and measurable
  - KSAs must be derived from tasks, not invented
  - Evidence should come from multiple sources
  - SME input is essential but must be validated
  - Market trends should inform but not override practitioner reality

tools:
  # Analysis tools
  - jta.analyze_job_postings        # Analyze job posting corpus
  - jta.analyze_industry_reports    # Extract trends from reports
  - jta.compare_to_existing         # Compare to current task inventory
  - jta.identify_emerging_tasks     # Find new tasks in market data
  - jta.identify_declining_tasks    # Find tasks becoming obsolete

  # Facilitation tools
  - jta.start_sme_session          # Begin structured SME session
  - jta.capture_task               # Record task from SME input
  - jta.rate_task_criticality      # Apply criticality matrix
  - jta.validate_task_consensus    # Check SME agreement

  # Structuring tools
  - jta.generate_ksa_from_task     # Derive KSAs from task
  - jta.suggest_bloom_level        # Recommend Bloom's level
  - jta.check_ksa_quality          # Validate KSA statement

  # Traceability tools
  - jta.link_task_to_blueprint     # Create task→KSA link
  - jta.coverage_analysis          # Check blueprint covers all tasks
  - jta.gap_analysis               # Find tasks without KSAs

  # Knowledge management
  - knowledge.store_role           # Save role to knowledge graph
  - knowledge.store_task           # Save task to knowledge graph
  - knowledge.query_tasks          # Query existing tasks

conversation_template_id: 'jta-session-template'
access_control:
  allowed_roles: ['epm', 'sme', 'jta_facilitator']
```

## Workflow: AI-Facilitated JTA Session

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AI-FACILITATED JTA SESSION                                │
│                                                                              │
│  EPM/SME                       AI Facilitator              Knowledge Manager │
│     │                              │                            │            │
│     │  "Let's update the JTA      │                            │            │
│     │   for Network Engineer"     │                            │            │
│     │─────────────────────────────►                            │            │
│     │                              │                            │            │
│     │  "I'll prepare by analyzing │                            │            │
│     │   current market data..."   │                            │            │
│     │                              │                            │            │
│     │                              │──► Analyze 2,500 job posts │            │
│     │                              │──► Extract industry reports│            │
│     │                              │──► Load existing task inventory         │
│     │                              │                            │            │
│     │  Pre-Session Brief:          │                            │            │
│     │  ───────────────────          │                            │            │
│     │  "Based on market analysis:  │                            │            │
│     │                              │                            │            │
│     │   Emerging areas:            │                            │            │
│     │   • SD-WAN (mentioned 67%    │                            │            │
│     │     more than last year)     │                            │            │
│     │   • Network automation       │                            │            │
│     │     (Python, Ansible)        │                            │            │
│     │   • Cloud networking (AWS,   │                            │            │
│     │     Azure integration)       │                            │            │
│     │                              │                            │            │
│     │   Potentially declining:     │                            │            │
│     │   • Legacy frame relay       │                            │            │
│     │   • Manual CLI-only config   │                            │            │
│     │                              │                            │            │
│     │   Shall we start with        │                            │            │
│     │   emerging areas?"           │                            │            │
│     │◄─────────────────────────────│                            │            │
│     │                              │                            │            │
│     │  "Yes, let's define SD-WAN   │                            │            │
│     │   tasks"                     │                            │            │
│     │─────────────────────────────►│                            │            │
│     │                              │                            │            │
│     │  "Great. Based on job posts, │                            │            │
│     │   here are candidate tasks:  │                            │            │
│     │                              │                            │            │
│     │   1. Deploy SD-WAN overlay   │                            │            │
│     │   2. Migrate branch WAN to   │                            │            │
│     │      SD-WAN                  │                            │            │
│     │   3. Configure SD-WAN        │                            │            │
│     │      policies                │                            │            │
│     │   4. Troubleshoot SD-WAN     │                            │            │
│     │      connectivity            │                            │            │
│     │                              │                            │            │
│     │   Do these align with your   │                            │            │
│     │   experience? What's         │                            │            │
│     │   missing?"                  │                            │            │
│     │◄─────────────────────────────│                            │            │
│     │                              │                            │            │
│     │  "Yes, but add 'Integrate    │                            │            │
│     │   SD-WAN with security       │                            │            │
│     │   services' - that's 50% of  │                            │            │
│     │   real deployments"          │                            │            │
│     │─────────────────────────────►│                            │            │
│     │                              │                            │            │
│     │  "Great addition. Let me     │                            │            │
│     │   structure Task 5:          │                            │            │
│     │                              │                            │            │
│     │   Title: Integrate SD-WAN    │                            │            │
│     │   with security services     │                            │            │
│     │                              │                            │            │
│     │   Frequency?                 │                            │            │
│     │   (daily/weekly/monthly)"    │                            │            │
│     │◄─────────────────────────────│                            │            │
│     │                              │                            │            │
│     │  "Monthly, during new        │                            │            │
│     │   deployments"               │                            │            │
│     │─────────────────────────────►│                            │            │
│     │                              │                            │            │
│     │  "Criticality if done        │                            │            │
│     │   incorrectly?"              │                            │            │
│     │◄─────────────────────────────│                            │            │
│     │                              │                            │            │
│     │  "High - security gaps or    │                            │            │
│     │   broken connectivity"       │                            │            │
│     │─────────────────────────────►│                            │            │
│     │                              │                            │            │
│     │  "Got it. Now let me derive  │                            │            │
│     │   KSAs from this task:       │                            │            │
│     │                              │                            │            │
│     │   Knowledge:                 │                            │            │
│     │   • SD-WAN security service  │                            │            │
│     │     integration options      │                            │            │
│     │   • Traffic flow through     │                            │            │
│     │     SD-WAN security stack    │                            │            │
│     │                              │                            │            │
│     │   Skills:                    │                            │            │
│     │   • Configure SD-WAN         │                            │            │
│     │     security policies        │                            │            │
│     │   • Verify security service  │                            │            │
│     │     insertion                │                            │            │
│     │                              │                            │            │
│     │   Do these capture the       │                            │            │
│     │   essence?"                  │                            │            │
│     │◄─────────────────────────────│                            │            │
│     │                              │                            │            │
│     │   [Session continues...]     │                            │            │
│     │                              │                            │            │
│     │                              │──► Store task              │            │
│     │                              │──► Store KSAs              │            │
│     │                              │──► Create links            │            │
│     │                              │                            │            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Sources for AI Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    JTA DATA SOURCES                                          │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  1. JOB POSTINGS                                                       │ │
│  │                                                                        │ │
│  │  Sources: LinkedIn, Indeed, company career pages, Dice                 │ │
│  │  Volume: 10,000+ per role per year                                     │ │
│  │                                                                        │ │
│  │  AI extracts:                                                          │ │
│  │  • Required skills (frequency analysis)                                │ │
│  │  • Responsibilities (task candidates)                                  │ │
│  │  • Tool/technology mentions                                            │ │
│  │  • Experience requirements                                             │ │
│  │  • Certification requirements                                          │ │
│  │                                                                        │ │
│  │  Example insight: "Python mentioned in 67% of Network Engineer         │ │
│  │  postings in 2024 vs 34% in 2022 → automation skills emerging"        │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  2. INDUSTRY REPORTS                                                   │ │
│  │                                                                        │ │
│  │  Sources: Gartner, IDC, Forrester, IEEE, vendor whitepapers           │ │
│  │                                                                        │ │
│  │  AI extracts:                                                          │ │
│  │  • Technology adoption trends                                          │ │
│  │  • Skill demand forecasts                                              │ │
│  │  • Emerging technology areas                                           │ │
│  │  • Declining technology areas                                          │ │
│  │                                                                        │ │
│  │  Example insight: "Gartner predicts 60% of enterprises will have       │ │
│  │  SD-WAN by 2025 → high priority for JTA inclusion"                    │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  3. SME INTERVIEWS                                                     │ │
│  │                                                                        │ │
│  │  Method: AI-facilitated structured interviews                          │ │
│  │  Sample: 15-25 practitioners per role                                  │ │
│  │                                                                        │ │
│  │  AI facilitates:                                                       │ │
│  │  • Structured task elicitation                                         │ │
│  │  • Criticality rating                                                  │ │
│  │  • Frequency estimation                                                │ │
│  │  • KSA validation                                                      │ │
│  │                                                                        │ │
│  │  Example insight: "14 of 15 SMEs confirmed 'troubleshoot SD-WAN'       │ │
│  │  is a weekly task → high validity"                                     │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  4. PRACTITIONER SURVEYS                                               │ │
│  │                                                                        │ │
│  │  Method: Online survey to certified professionals                      │ │
│  │  Sample: 300-500 per role                                              │ │
│  │                                                                        │ │
│  │  AI analyzes:                                                          │ │
│  │  • Task frequency ratings                                              │ │
│  │  • Task criticality ratings                                            │ │
│  │  • Task difficulty ratings                                             │ │
│  │  • Emerging task suggestions                                           │ │
│  │                                                                        │ │
│  │  Example insight: "Survey shows 'implement zero trust' rated          │ │
│  │  4.2/5 criticality but only 2.1/5 frequency → emerging task"          │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  5. CERTIFICATION EXAM DATA (Internal)                                 │ │
│  │                                                                        │ │
│  │  Source: Exam analytics, candidate feedback                            │ │
│  │                                                                        │ │
│  │  AI identifies:                                                        │ │
│  │  • KSAs with poor discrimination (may not reflect job reality)         │ │
│  │  • Candidate complaints about relevance                                │ │
│  │  • Topics candidates find surprising                                   │ │
│  │                                                                        │ │
│  │  Example insight: "KSA 3.2.1 has low discrimination—practitioners      │ │
│  │  may not actually need this in the field"                              │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## JTA → Blueprint Traceability

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRACEABILITY ENFORCEMENT                                  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  BLUEPRINT COVERAGE ANALYSIS                                           │ │
│  │                                                                        │ │
│  │  Role: Enterprise Network Engineer                                     │ │
│  │  Blueprint: CCNP Enterprise Core (ENCOR)                               │ │
│  │                                                                        │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │  │  TASK → KSA COVERAGE                                             │ │ │
│  │  │                                                                  │ │ │
│  │  │  ✅ COVERED (85%)                                                │ │ │
│  │  │  • Configure OSPF routing          → KSA 2.1.1, 2.1.2, 2.1.3    │ │ │
│  │  │  • Implement VLAN and trunking     → KSA 1.2.1, 1.2.2           │ │ │
│  │  │  • Troubleshoot network issues     → KSA 5.1.x (multiple)       │ │ │
│  │  │  • Configure network security      → KSA 4.1.x (multiple)       │ │ │
│  │  │  [... 42 more tasks ...]                                         │ │ │
│  │  │                                                                  │ │ │
│  │  │  ⚠️ GAPS (15%)                                                   │ │ │
│  │  │  • Integrate SD-WAN with security  → NO KSA MAPPED              │ │ │
│  │  │    Recommendation: Add to Topic 3 or create new topic           │ │ │
│  │  │                                                                  │ │ │
│  │  │  • Automate network with Python    → KSA 6.1.1 (partial)        │ │ │
│  │  │    Recommendation: Expand automation coverage                   │ │ │
│  │  │                                                                  │ │ │
│  │  │  • Implement zero trust network    → NO KSA MAPPED              │ │ │
│  │  │    Note: Emerging task, consider for next revision              │ │ │
│  │  │                                                                  │ │ │
│  │  └──────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │  │  ORPHAN KSAs (no task mapping)                                   │ │ │
│  │  │                                                                  │ │ │
│  │  │  ⚠️ KSA 2.4.7: "Describe Frame Relay operation"                  │ │ │
│  │  │     Task status: DEPRECATED (no longer performed in field)       │ │ │
│  │  │     Recommendation: Remove from blueprint                        │ │ │
│  │  │                                                                  │ │ │
│  │  │  ⚠️ KSA 3.1.9: "Configure IPX routing"                           │ │ │
│  │  │     Task status: NOT FOUND IN JTA                                │ │ │
│  │  │     Recommendation: Review with SME or remove                    │ │ │
│  │  │                                                                  │ │ │
│  │  └──────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Integration with Content Authoring

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    JTA-INFORMED CONTENT AUTHORING                            │
│                                                                              │
│  When an author creates an item for KSA 3.2.1, they see:                    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  📋 KSA CONTEXT                                                        │ │
│  │                                                                        │ │
│  │  KSA: 3.2.1 - Configure SD-WAN fabric overlay                         │ │
│  │  Bloom's Level: Apply                                                  │ │
│  │                                                                        │ │
│  │  ────────────────────────────────────────────────────────────────────  │ │
│  │                                                                        │ │
│  │  📌 JOB TASK CONTEXT                                                   │ │
│  │                                                                        │ │
│  │  This KSA derives from:                                                │ │
│  │                                                                        │ │
│  │  Task: "Deploy SD-WAN overlay network"                                 │ │
│  │  Frequency: Monthly                                                    │ │
│  │  Criticality: High                                                     │ │
│  │                                                                        │ │
│  │  Typical scenario:                                                     │ │
│  │  "Enterprise deploying SD-WAN to 50 branch offices. Engineer must     │ │
│  │   configure overlay connectivity, ensure traffic routing, and         │ │
│  │   integrate with existing infrastructure."                             │ │
│  │                                                                        │ │
│  │  Common challenges (from SME interviews):                              │ │
│  │  • Overlay tunnel establishment issues                                 │ │
│  │  • Integration with existing routing                                   │ │
│  │  • Traffic policy configuration                                        │ │
│  │                                                                        │ │
│  │  ────────────────────────────────────────────────────────────────────  │ │
│  │                                                                        │ │
│  │  💡 AUTHORING GUIDANCE                                                 │ │
│  │                                                                        │ │
│  │  Items for this KSA should:                                            │ │
│  │  • Test configuration, not just recall                                 │ │
│  │  • Include realistic topology (branch + hub)                           │ │
│  │  • Require integration with existing network                           │ │
│  │  • Focus on common failure scenarios                                   │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Knowledge Graph Structure

```yaml
# Entities and relationships for knowledge-manager

entities:
  # Roles
  - type: JobRole
    properties:
      role_id: string (PK)
      title: string
      description: text
      industry_sector: string
      experience_years: string

  # Tasks
  - type: JobTask
    properties:
      task_id: string (PK)
      title: string
      description: text
      frequency: enum (daily, weekly, monthly, quarterly, as_needed)
      criticality: enum (critical, high, medium, low)
      difficulty: enum (basic, moderate, advanced, expert)
      validation_score: float

  # KSAs
  - type: KSA
    properties:
      ksa_id: string (PK)
      ksa_type: enum (knowledge, skill, ability)
      statement: string
      bloom_level: enum

  # Evidence
  - type: JTAEvidence
    properties:
      evidence_id: string (PK)
      source_type: enum (job_posting, survey, interview, report)
      source_date: date
      raw_content: text
      extracted_insights: list[string]

relations:
  # Role → Task
  - from: JobRole
    to: JobTask
    type: PERFORMS
    properties:
      percentage_performing: float

  # Task → KSA
  - from: JobTask
    to: KSA
    type: REQUIRES
    properties:
      importance: float

  # KSA → Blueprint Topic
  - from: KSA
    to: BlueprintTopic
    type: ASSESSED_BY
    properties:
      weight: float

  # Task → Evidence
  - from: JobTask
    to: JTAEvidence
    type: SUPPORTED_BY
    properties:
      confidence: float

  # Role → Certification
  - from: JobRole
    to: Certification
    type: VALIDATED_BY
```

## Maintenance Workflow: Keeping JTA Current

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTINUOUS JTA MAINTENANCE                                │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  AI MONITORING (Continuous)                                            │ │
│  │                                                                        │ │
│  │  Monitors:                                                             │ │
│  │  • Job posting trends (weekly scrape)                                  │ │
│  │  • Industry report publications (monthly)                              │ │
│  │  • Certification exam statistics (quarterly)                           │ │
│  │  • Practitioner feedback (ongoing)                                     │ │
│  │                                                                        │ │
│  │  Triggers alerts when:                                                 │ │
│  │  • New skill mentioned in >20% of postings (emerging)                  │ │
│  │  • Existing skill drops below 10% (declining)                          │ │
│  │  • Industry report highlights new technology                           │ │
│  │  • Exam items show poor relevance signals                              │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  ALERT EXAMPLE                                                         │ │
│  │                                                                        │ │
│  │  🔔 JTA Currency Alert                                                 │ │
│  │                                                                        │ │
│  │  Role: Enterprise Network Engineer                                     │ │
│  │  Last full JTA: 18 months ago                                          │ │
│  │                                                                        │ │
│  │  Market changes detected:                                              │ │
│  │                                                                        │ │
│  │  📈 EMERGING:                                                          │ │
│  │  • "SASE" mentioned in 45% of postings (was 12%)                      │ │
│  │  • "Network automation" up 23% YoY                                     │ │
│  │  • "Cloud networking" now in 67% of postings                          │ │
│  │                                                                        │ │
│  │  📉 DECLINING:                                                         │ │
│  │  • "Frame Relay" now in <1% of postings                               │ │
│  │  • "ISDN" effectively zero                                            │ │
│  │                                                                        │ │
│  │  Recommendation: Schedule JTA refresh session                          │ │
│  │                                                                        │ │
│  │  [Schedule Session] [View Details] [Dismiss]                           │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Acceptance Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| **Task inventory completeness** | % of job activities captured | > 90% |
| **Task validation** | SME consensus score | > 0.80 |
| **KSA traceability** | % of KSAs linked to tasks | 100% |
| **Blueprint coverage** | % of critical tasks assessed | > 95% |
| **JTA currency** | Age of oldest task validation | < 3 years |
| **Author access** | % of authors who see JTA context | 100% |
| **ANSI documentation** | Time to produce JTA evidence | < 2 hours |

## Open Questions

1. **Automation level**: How much of JTA can be fully automated vs AI-assisted?
2. **SME recruitment**: How to ensure diverse SME representation?
3. **Cross-track reuse**: Can tasks be shared across related certifications?
4. **Vendor neutrality**: How to handle vendor-specific vs generic tasks?
5. **International variation**: Do job tasks vary significantly by region?
6. **Update frequency**: What triggers a JTA refresh vs minor update?

---

_Last updated: December 25, 2025_
